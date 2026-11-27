"""Shared resource allocation, dated receipts, and campaign round trips."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from random import Random
import sys
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))

from remake import command_books, domestic, faction_economy, grain_units, logistics
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
    def game(self, *, enabled=True, capacity=False, faction='observer'):
        engine = Headless(Catalog(ROOT/'game/data/campaigns/208-10.json'), record_journal=False)
        kwargs = {coordination.FIELD: 3041} if enabled else {}
        if capacity:
            kwargs.update(transport_capacity_rules_version=303)
        engine.command('new', dict(faction=faction, seed=2026, lifespan='none', **kwargs), 0)
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
