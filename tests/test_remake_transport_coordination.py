"""Shared resource allocation, dated receipts, and campaign round trips."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from random import Random
import sys
from unittest import TestCase
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))

from remake import command_books, domestic, faction_economy, grain_dispatch, grain_units, logistics, staging_supply
from remake import regional_market, transport_candidates, transport_coordination as coordination
from remake.campaign import Campaign, Catalog, verified_save_content
from remake.errors import GameError
from remake.march_core import backend_status, using_backend
from remake.transport_allocation import Candidate, compatible, select
from remake.transport_demands import Demand, city_shortage


class Headless(Campaign):
    def view(self):
        return {}


def offer(demand, source='a', officer=1, *, channel='ordinary', books=1, net=500, tick=10):
    return Candidate(demand, channel, source, str(demand.target), (officer,), 'land', tick, tick,
                     net, net, net, 20, 10, 10, books, {})


class CoordinationTests(TestCase):
    def game(self, *, enabled=True, capacity=False, faction='observer', version=3041, **rules):
        engine = Headless(Catalog(ROOT/'game/data/campaigns/208-10.json'), record_journal=False)
        kwargs = {coordination.FIELD: version} if enabled else {}
        if capacity:
            kwargs.update(transport_capacity_rules_version=303)
        engine.command('new', dict(faction=faction, seed=2026, lifespan='none', **kwargs, **rules), 0)
        return engine

    def test_shadow_matches_old_rules_through_actual_turns(self):
        control, shadow = self.game(enabled=False), self.game(enabled=False)
        observed = Counter()
        for _ in range(3):
            control.command('observe_turn', {}, control.revision)
            with coordination.observing(lambda kind, _row: observed.update((kind,)), shadow=True):
                shadow.command('observe_turn', {}, shadow.revision)
            self.assertEqual(shadow.export_save(), control.export_save())
        self.assertGreater(observed['scheduler'], 0)
        self.assertNotIn(coordination.POOL, shadow.state.extension)

    def test_version_is_independent_and_reads_both_save_formats_across_backends(self):
        game = self.game()
        for other in ('transport_capacity_rules_version', 'transshipment_rules_version',
                      'weather_forecast_version', 'strategic_granary_rules_version'):
            self.assertNotIn(other, game.state.extension)
        game.command('observe_turn', {}, game.revision)
        self.assertEqual(game.state.extension[coordination.FIELD], 3041)
        with using_backend('auto'):
            native = backend_status()['engine'] == 'rust'
        for packed in (False, True):
            with self.subTest(compact=packed):
                saved = game.export_save(compact=packed)
                for backend in ('python', 'rust'):
                    if backend == 'rust' and not native:
                        continue
                    with using_backend(backend):
                        restored = Headless(game.catalog, record_journal=False)
                        restored.load_save(saved, 0)
                        self.assertEqual(restored.export_save(compact=packed), saved)
                        restored.command('observe_turn', {}, restored.revision)
                        domain = verified_save_content(restored.export_save(compact=packed))
                        if backend == 'python':
                            expected = domain
                        else:
                            self.assertEqual(domain, expected)

    def test_cannot_run_the_same_phase_twice_or_issue_player_orders(self):
        game = self.game(faction='wu')
        game.command('end_turn', {}, game.revision)
        state = game.state
        with grain_units.using(state):
            domestic.prepare_ai(game, state, 'wei')
            city = next(key for key, row in state.cities.items() if row.owner == 'wei')
            coordination.request(state, 'wei', city, 100_000, 800, 3)
            coordination.run(game, state, 'wei', 'urgent')
            before = game.export_save()
            restored = Headless(game.catalog, record_journal=False)
            restored.load_save(before, 0)
            self.assertFalse(coordination.run(restored, restored.state, 'wei', 'urgent'))
            self.assertFalse(coordination.run(restored, restored.state, 'wu', 'urgent'))
            self.assertEqual(restored.export_save(), before)

    def test_timeline_counts_each_installment_once_and_keeps_uncertain_grain_conditional(self):
        from types import SimpleNamespace
        state = self.game().state
        city = state.cities['jiangxia']
        city.grain = 0
        timeline = [(0, 100, 120), (0, 100, 0), (0, 80, 0)]
        gaps, _, _ = faction_economy.balance(0, timeline)
        forecast = SimpleNamespace(timeline=timeline, first_missing=100, gaps=gaps, conditional_receipts={1: 40})
        plan = SimpleNamespace(owner=city.owner, cities={city.id: forecast}, budgets={city.id: {'reserved_grain': 0}})
        row = city_shortage(None, state, plan, city.id)
        self.assertEqual((row.requested, row.reliable, row.conditional, row.remaining), (280, 120, 40, 160))
        self.assertEqual(row.channels, ('local', 'ordinary', 'granary', 'regional'))
        self.assertEqual((row.after(row.deadline-1), row.after(row.deadline)), (160, 60))
        self.assertNotEqual(row.key, Demand(city.owner, 'march', 1, 0, row.deadline, 500, 500).key)
        forecast.timeline = [(0, 0, 200), (0, 100, 0)]
        forecast.gaps = faction_economy.balance(0, forecast.timeline)[0]
        covered = city_shortage(None, state, plan, city.id)
        self.assertEqual((covered.reliable, covered.remaining), (100, 0))

    def test_real_convoy_uses_one_book_actual_escort_and_safe_source_stock(self):
        import test_remake_logistics as fixtures

        game = Headless(fixtures.transport_catalog(rear=True), record_journal=False)
        game.command('new', dict(faction='wei', seed=2026, **{coordination.FIELD: 3041}), 0)
        fixtures.LogisticsTests().fill(game, 'xiangyang', 6)
        game.command('end_turn', {}, game.revision)
        state = game.state
        source, target = (state.cities[k] for k in ('xiangyang', 'nanjun'))
        source.grain, target.grain, target.gold = 150_000, 0, 0
        with grain_units.using(state):
            domestic.prepare_ai(game, state, source.owner)
            start = command_books.remaining(state, source.owner)
            quote_calls = []
            recorded = []
            real = logistics._supply_routes

            def supply_routes(game, state, owner, pairs, policy):
                quote_calls.append(tuple(pairs))
                return real(game, state, owner, pairs, policy)

            with coordination.observing(lambda event, row: recorded.append((event, row))), patch.object(
                    logistics, '_supply_routes', supply_routes):
                self.assertTrue(coordination.run(game, state, source.owner, 'urgent'))
            departures = [row for row in logistics._pool(state)['convoys'] if row['owner'] == source.owner]
            self.assertEqual(len(departures), 1)
            row, = departures
            self.assertEqual((row['source'], row['target']), (source.id, target.id))
            self.assertEqual(command_books.remaining(state, source.owner), start - 1)
            self.assertEqual(source.grain, 150_000 - row['cargo']['grain'] - row['journeys'][0]['supply']['loaded'])
            self.assertEqual(state.extension['officer_actions'][str(row['officers'][0])], state.turn)
            self.assertTrue(quote_calls)
            self.assertFalse(coordination.run(game, state, source.owner, 'urgent'))
        game.validate(state)

    def test_granary_capacity_weather_and_transshipment_can_coexist(self):
        game = self.game(capacity=True, strategic_granary_rules_version=302,
                         regional_market_rules_version=301, weather_rules_version=23,
                         weather_forecast_version=231, transshipment_rules_version=304,
                         transport_emergency_rules_version=222)
        for _ in range(2):
            game.command('observe_turn', {}, game.revision)
        expected = {
            key: game.state.extension[key] for key in (
                'strategic_granary_rules_version', 'regional_market_rules_version', 'weather_rules_version',
                'weather_forecast_version', 'transport_emergency_rules_version',
                'transshipment_rules_version', 'transport_capacity_rules_version', coordination.FIELD)
        }
        self.assertEqual(list(expected.values()), [302, 301, 23, 231, 222, 304, 303, 3041])
        self.assertEqual(game.state.extension['transshipment']['plans'], {})

    def test_one_receipt_may_credit_only_one_episode_and_excludes_returns(self):
        game = self.game()
        state = game.state
        city = state.cities['danyang']
        ledger = state.extension[coordination.POOL]['convoys']
        link = dict(owner=city.owner, key='city', demand='episode', kind='city', target=city.id,
                    deadline=20, cap=600, channel='ordinary')
        convoy = dict(id=21, target=city.id, target_march=None)
        output = []
        with coordination.observing(lambda event, row: output.append((event, row))):
            ledger['21'] = link
            coordination.transport_event(state, 'transport_arrived', convoy, 710, tick=10)
            coordination.transport_event(state, 'transport_arrived', convoy, 710, tick=10)
            ledger['21'] = dict(link)
            coordination.transport_event(state, 'transport_returned', convoy, 120)
            ledger['21'] = dict(link)
            state.cities[city.id].owner = 'wei'
            coordination.transport_event(state, 'transport_arrived', convoy, 50, tick=11)
        self.assertEqual([(row['credited'], row['unallocated']) for _, row in output],
                         [(600, 110), (0, 120), (0, 50)])
        self.assertEqual(state.extension[coordination.POOL]['completed'][link['owner']], 1)

    def test_market_failure_keeps_purchased_stock_and_does_not_debit_dispatch(self):
        from remake import facilities, market_pricing, grain_market
        from remake.regional_procurement import Planner
        game = self.game()
        state = game.state
        state.phase = 'ai'
        target = state.cities['danyang']
        owner = target.owner
        domestic.prepare_ai(game, state, owner)
        market_pricing.initialize(state, market_pricing.PROCUREMENT)
        with grain_units.using(state):
            # The actual regional market requires stock plus both orders.
            capital = state.cities['lujiang']
            capital.gold = 20_000
            capital.grain = 50_000
            market = grain_market.row(state, capital.id)
            self.assertGreater(market['stock'], 0)
            plan = faction_economy.plan(game, state, owner, coordinated=True)
            options, _ = Planner(game, state, owner, decision=plan, automatic=True).options(target, 1000, deadline=30)
            self.assertTrue(options)
            quote = options[0]
            source = state.cities[quote['source']]
            before = source.grain, source.gold, command_books.remaining(state, owner)
            expected = facilities.emergency_quote(game, state, source, quote['cargo'])
            candidate = replace(offer(Demand(owner, 'city', target.id, 1, 70, 1000, 1000),
                                      source.id, quote['actor'], channel='regional', books=2), offer=quote)
            with patch.object(logistics, 'dispatch', side_effect=GameError('test revalidation failure')):
                result = transport_candidates.commit(game, state, candidate)
            self.assertEqual(result, (None, 0, expected['grain']))
            self.assertEqual((source.grain, source.gold, command_books.remaining(state, owner)),
                             (before[0]+expected['grain'], before[1]-expected['gold'], before[2]-1))
            self.assertFalse(list(logistics._pool(state)['convoys']))
            self.assertTrue(regional_market.conflicts(state, quote))

    def test_priority_keeps_unique_donor_and_defers_tiny_discretionary_freight(self):
        first = Demand('han', 'city', 'x', 1, 30, 500, 500)
        second = Demand('han', 'city', 'y', 1, 40, 500, 500)
        preferred, alternative = offer(first), offer(first, 'b', 'clerk-000001')
        sole = offer(second)
        self.assertIs(select([preferred, alternative, sole], 2, efficient=True), alternative)
        discretionary = replace(first, priority=5)
        game = self.game()
        logic = transport_candidates.Pass(game, game.state, 'han', efficient=True)
        self.assertFalse(logic._usable(offer(discretionary, net=7)))
        self.assertTrue(logic._usable(offer(first, net=7)))
        self.assertIsNone(select([offer(discretionary, books=2)], 2, efficient=True, reserve_for_orders=1))
        self.assertIs(select([sole], 1, efficient=True, reserve_for_orders=1), sole)

    def test_bounded_deterministic_conflicts_in_1200_resource_draws(self):
        rng = Random(3041)
        for _ in range(1200):
            books, reserve = rng.randrange(7), rng.randrange(3)
            demands = [Demand('han', 'city', str(i), rng.randrange(7), rng.randrange(11, 61), 500, 500)
                       for i in range(4)]
            choices = [offer(rng.choice(demands), str(rng.randrange(3)),
                             rng.choice((1, 2, 'clerk-000001')), books=rng.randrange(1, 3), net=rng.randrange(501))
                       for i in range(8)]
            # A candidate's stable identity is unique within a real planning pass.
            choices = list({row.key: row for row in choices}.values())
            picked = select(choices, books, efficient=True, reserve_for_orders=reserve)
            self.assertEqual(select(reversed(choices), books, efficient=True, reserve_for_orders=reserve), picked)
            if picked is not None:
                self.assertLessEqual(picked.command_books, books-(reserve if picked.demand.priority >= 3 else 0))
                self.assertFalse(compatible(picked, picked, books))
                for other in choices:
                    if compatible(picked, other, books):
                        self.assertNotEqual(other.source, picked.source)
                        self.assertNotEqual(other.escorts, picked.escorts)
                        self.assertNotEqual(other.demand.key, picked.demand.key)

    def recovery(self, features=None, **rules):
        flags = {} if features is None else {coordination.OPTIONS: {
            'features': {key: key in features for key in coordination.FEATURES}}}
        return self.game(version=coordination.RECOVERY, **flags, **rules)

    def test_pagination_checks_the_thirteenth_demand_and_refreshes_completed_demands(self):
        game = self.recovery({'pagination'})
        state = game.state
        state.phase = 'ai'
        owner = 'wei'
        keys = sorted(key for key, city in state.cities.items() if city.owner == owner)[:14]
        self.assertEqual(len(keys), 14)
        missing = {key: Demand(owner, 'city', key, 1 if i < 13 else 2, 40+i, 500, 500)
                   for i, key in enumerate(keys)}
        blocked, priority = keys[:12], keys[12]
        visited, launched, events = [], [], []

        def build(*args):
            page = args[0]
            visited.append(tuple(row.target for row in page))
            return [offer(row) for row in page if row.target not in blocked]

        def commit(_game, _state, row):
            launched.append(row.demand.target)
            del missing[row.demand.target]
            return True, True, None

        with (patch.object(coordination, '_discover', side_effect=lambda *_:
                            (list(missing.values()), None, None)),
              patch.object(transport_candidates.Pass, 'build', side_effect=build),
              patch.object(coordination, '_commit', side_effect=commit),
              coordination.observing(lambda event, row: events.append((event, row)))):
            with grain_units.using(state):
                self.assertTrue(coordination.run(game, state, owner, 'urgent'))
                self.assertFalse(coordination.run(game, state, owner, 'urgent'))
        self.assertEqual(visited[:2], [tuple(blocked), (priority,)])
        self.assertEqual(launched, keys[12:])
        self.assertTrue(any(e == 'demand' and row['outcome'] == 'checked_no_executable_quote'
                            for e, row in events))

    def test_invalid_quote_tries_the_next_offer_and_partial_purchase_rebuilds(self):
        for paid in (False, True):
            with self.subTest(paid=paid):
                game = self.recovery({'pagination'})
                state = game.state
                state.phase = 'ai'
                target = next(city.id for city in state.cities.values() if city.owner == 'wei')
                demand = Demand('wei', 'city', target, 1, 30, 500, 500)
                rows = [offer(demand, 'a'), offer(demand, 'b')]
                calls = []
                live = True

                def build(demands, plan, army, convoys, refused):
                    return [row for row in rows if row.key not in refused]

                def commit(_, __, candidate):
                    nonlocal live
                    calls.append(candidate.source)
                    if candidate.source == 'a':
                        return False, paid, 'compound_purchase_retained' if paid else 'stale_quote'
                    live = False
                    return True, True, None

                with (patch.object(coordination, '_discover', side_effect=lambda *_:
                                    ([demand] if live else [], None, None)),
                      patch.object(transport_candidates.Pass, 'build', side_effect=build) as search,
                      patch.object(coordination, '_commit', side_effect=commit),
                      grain_units.using(state)):
                    self.assertTrue(coordination.run(game, state, 'wei', 'urgent'))
                self.assertEqual(calls, ['a', 'b'])
                self.assertEqual(search.call_count, 2 if paid else 1)

    def test_budget_deferral_is_distinct_from_a_failed_quote(self):
        game = self.recovery({'pagination'})
        state = game.state
        state.phase = 'ai'
        keys = [key for key, city in state.cities.items() if city.owner == 'wei'][:13]
        rows = [Demand('wei', 'city', key, 1, 30, 500, 500) for key in keys]
        events = {}
        def observe(event, row):
            if event == 'demand':
                events[row['target']] = row['outcome']
        with (patch.object(coordination, '_discover', return_value=(rows, None, None)),
              patch.object(coordination, 'SEARCH_TARGETS', 12),
              patch.object(transport_candidates.Pass, 'build', return_value=[]),
              coordination.observing(observe), grain_units.using(state)):
            self.assertFalse(coordination.run(game, state, 'wei', 'urgent'))
        self.assertEqual(list(events.values()).count('search_budget'), 1)
        self.assertEqual(list(events.values()).count('checked_no_executable_quote'), 12)

    def test_ninth_route_and_alternative_source_survive_complete_candidate_search(self):
        game = self.recovery({'diversity'})
        operation = transport_candidates.Pass(game, game.state, 'wei', efficient=True, features={'diversity': True})
        demand = Demand('wei', 'city', 'danyang', 1, 30, 500, 500)
        routes = list(range(9))
        self.assertEqual([row for row in operation._route_shortlist(routes) if row == 8], [8])
        legacy = transport_candidates.Pass(game, game.state, 'wei', efficient=True)
        self.assertNotIn(8, legacy._route_shortlist(routes))
        raw = [offer(demand, 'a', officer) for officer in range(1, 6)]
        alternative = offer(demand, 'b', 6)
        with patch.object(operation, '_city_routes', return_value=raw+[alternative]):
            selected = operation.build([demand], None, None, None, set())
        self.assertIn(alternative, selected)
        self.assertEqual(len(selected), transport_candidates.MAX_OFFERS)
        other = offer(replace(demand, target='jiangxia', deadline=40))
        self.assertIs(select([*selected, other], 2, efficient=True), alternative)

    def test_requote_pays_higher_return_cost_with_a_smaller_legal_load(self):
        game = self.recovery({'requote'})
        operation = transport_candidates.Pass(game, game.state, 'wei', efficient=True, features={'requote': True})
        network = SimpleNamespace(shipment=lambda row, amount, due: (row['rations'], min(row['limit'], amount), due))
        demand = Demand('wei', 'city', 'henan', 1, 40, 800, 800, installments=((40, 800),))
        terms = dict(days=10, rations=100, limit=800, free=900, capacity={'physical_capacity': 730})
        self.assertEqual(operation._granary_quote(network, terms, demand, (10, 21, 20, 200, None, None)),
                         (200, 530, 5))
        self.assertIsNone(operation._granary_quote(network, terms, demand, (10, 21, 20, 950, None, None)))
        self.assertEqual(terms['rations'], 100)

    def test_actual_appointments_and_ordinary_reserves_do_not_masquerade_as_approved_orders(self):
        game = self.recovery({'preparation'})
        state = game.state
        city = next(city for city in state.cities.values() if city.owner == 'wei')
        enemy = next(c for c in state.cities.values() if c.owner not in ('wei', 'neutral'))
        owner = city.owner
        coordination.request(state, owner, city.id, 40_000, 900, 8, target=enemy.id, purpose='military_candidate')
        coordination.request(state, owner, city.id, 800, 10, 2)
        goals = state.extension[coordination.POOL]['support'][owner]['goals']
        with grain_units.using(state):
            plan = faction_economy.plan(game, state, owner, coordinated=True)
        from remake.transport_demands import preparations
        result = preparations(state, plan, goals)[city.id]
        self.assertEqual([(priority, due, kind, grain) for priority, due, _, kind, grain, _ in result],
                         [(5, 8, 'military_candidate', 40_000), (6, 2, 'front_reserve', 800)])
        enemy.owner = owner
        result = preparations(state, plan, goals)[city.id]
        self.assertEqual([row[3] for row in result], ['front_reserve'])

    def test_transit_honors_the_real_booking_and_never_draws_the_same_lock_twice(self):
        game = self.recovery({'transit'})
        state = game.state
        city = state.cities['jiangxia']
        city.grain = 1700
        rows = [dict(city=city.id, army=59, route_day=6, reserved=600),
                dict(city=city.id, army=60, route_day=8, reserved=300)]
        with patch.object(staging_supply, 'active', side_effect=lambda _state: iter(rows)):
            stock = staging_supply.available(state, city, army=59)
            self.assertEqual(stock, 1400)
            self.assertEqual(staging_supply.refill_budget(game, state, city, 59, 6, stock, {city.id: 700}),
                             (700, 600, 700))
            self.assertEqual(staging_supply.refill_budget(game, state, city, 59, 5, stock, {city.id: 700}),
                             (100, 0, 700))
            self.assertEqual(staging_supply.refill_budget(game, state, city, 61, 6, 800, {city.id: 850}),
                             (0, 0, 850))

    def test_powered_forward_receipt_does_not_reset_original_due_date_or_double_credit(self):
        game = self.recovery({})
        city = game.state.cities['jiangxia']
        state = game.state
        ledger = state.extension[coordination.POOL]['convoys']
        demand = Demand(city.owner, 'city', city.id, 1, 40, 500, 500, original=20,
                        installments=((20, 100), (40, 400)))
        link = dict(owner=city.owner, key=demand.key, demand=demand.episode, kind='city', target=city.id,
                    deadline=20, current_deadline=40, cap=500, original_cap=100, channel='ordinary')
        self.assertEqual(demand.original_balance(), 100)
        self.assertEqual(demand.after(20), 400)
        probe = dict(id=25, target=city.id, target_march=None)
        ledger['25'] = link
        events = []
        with coordination.observing(lambda kind, row: events.append((kind, row))):
            coordination.transport_event(state, 'transport_arrived', probe, 300, tick=20)
            coordination.transport_event(state, 'transport_arrived', probe, 300, tick=20)
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0][1]['credited'], events[0][1]['timely'], events[0][1]['timely_current']),
                         (300, 0, 300))

    def test_short_emergency_life_saving_delivery_is_not_subject_to_stock_economics(self):
        game = self.recovery({'economics'})
        operation = transport_candidates.Pass(game, game.state, 'wei', efficient=True, features={'economics': True})
        demand = Demand('wei', 'city', 'henan', 1, 50, 400, 400)
        tiny = replace(offer(demand, net=400), days=21, return_days=5, rations=20)
        self.assertTrue(operation._usable(tiny))
        self.assertFalse(operation._usable(replace(tiny, demand=replace(demand, priority=6, kind='front_reserve'))))

    def test_incremental_forecasts_match_100_dynamic_stock_states_and_reuse_only_unchanged_inputs(self):
        game = self.recovery({'incremental'})
        state = game.state
        city = state.cities['jiangxia']
        memo = {}
        beginning = game.to_dict()
        forecast = faction_economy._forecast
        actual = city.grain
        with grain_units.using(state), patch.object(faction_economy, '_forecast', wraps=forecast) as calls:
            start = faction_economy.plan(game, state, city.owner, coordinated=True, forecast_memo=memo)
            self.assertEqual(calls.call_count, len(start.cities))
            for i in range(100):
                city.grain = i*113
                compute = faction_economy.plan(game, state, city.owner, coordinated=True, forecast_memo=memo)
                verify = faction_economy.plan(game, state, city.owner, coordinated=True)
                self.assertEqual(compute, verify)
            self.assertLessEqual(calls.call_count, len(start.cities)*101 + 100)
            city.grain = actual
        self.assertEqual(game.to_dict(), beginning)

    def test_recovery_run_is_deterministic_with_incremental_mode_and_readonly_observer(self):
        original = self.recovery(set(coordination.FEATURES)-{'incremental'}, strategic_granary_rules_version=302,
                                 weather_rules_version=23, weather_forecast_version=231)
        incremental = self.recovery(strategic_granary_rules_version=302,
                                    weather_rules_version=23, weather_forecast_version=231)
        for _ in range(3):
            original.command('observe_turn', {}, original.revision)
            with coordination.observing(lambda *_: None):
                incremental.command('observe_turn', {}, incremental.revision)
            expected, observed = original.to_dict(), incremental.to_dict()
            expected['extension'][coordination.POOL]['features']['incremental'] = True
            self.assertEqual(expected, observed)
        for compact in (False, True):
            save = incremental.export_save(compact=compact)
            for backend in ('python', 'rust'):
                with using_backend('auto'):
                    if backend == 'rust' and backend_status()['engine'] != 'rust':
                        continue
                with using_backend(backend):
                    restored = Headless(incremental.catalog, record_journal=False)
                    restored.load_save(save, 0)
                    self.assertEqual(restored.export_save(compact=compact), save)
