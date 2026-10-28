"""Authorial treasure/reward rules, exact assets, pure previews and AI parity."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import treasures, command_books
from remake.campaign import SeedRng
from remake.errors import GameError
from remake.officers import GameRules


class FixtureGame:
    def __init__(self):
        self.catalog = SimpleNamespace(rules=GameRules(99, 10, 1200),
            factions={'one': {}, 'two': {}}, data=dict(city_profiles={
                'capital': dict(tier='giant'), 'border': dict(tier='normal'),
                'large': dict(tier='large'), 'neutral': dict(tier='normal'),
                'lone': dict(tier='normal'), 'new': dict(tier='normal')}))

    def _march_ids(self, state):
        return {ident for group in ('travel', 'logistics')
            for row in state.extension.get(group, {}).get('marches' if group == 'travel' else 'convoys', [])
            for ident in row.get('officers', [])}

    def _emit_event(self, state, kind, **values):
        state.events.append(deepcopy(dict(kind=kind, **values)))


def fixture(seed=2):
    game = FixtureGame()
    rows = [(1, 'one', 70, 75, 80), (2, 'one', 95, 85, 80), (3, 'one', 60, 65, 80),
            (4, 'one', 80, 70, 60), (5, 'one', 80, 70, 70),
            (6, 'two', 60, 60, 80), (7, 'two', 65, 65, 80),
            ('clerk-000001', 'one', 60, 60, 80)]
    officers = {ident: SimpleNamespace(runtime_id=ident, person_id=f'person-{ident}',
        profile=SimpleNamespace(virtue=virtue, intellect=intellect, martial_strength=70, health_max=99),
        health=health, loyalty=100 if ident in (1, 6) else 50, troops=300, faction_id=owner,
        alive=True, experience=0, weapon_id=0, armor_id=0)
        for ident, owner, virtue, intellect, health in rows}
    city_rows = [('capital', 'one', [1, 2, 3]), ('border', 'one', [4, 5]),
                 ('large', 'two', [6, 7]), ('neutral', 'neutral', []),
                 ('lone', 'one', ['clerk-000001'])]
    cities = {key: SimpleNamespace(id=key, owner=owner, gold=500, grain=1000, reserves=100,
        roster=SimpleNamespace(officer_ids=roster), action_used=False) for key, owner, roster in city_rows}
    state = SimpleNamespace(year=217, month=7, day=1, turn=1, player='one', phase='city',
        rng=SeedRng(seed), cities=cities, officers=officers, battle=None, events=[],
        soldiers=dict(initial=2900, recruited=0, lost=0), extension=dict(
            leaders=dict(one=1, two=6), officer_actions={}, ended_factions=[],
            pending_succession={}, travel=dict(marches=[]), logistics=dict(convoys=[])))
    command_books.initialize(game, state)
    game.catalog.map_cities = {key: {} for key in cities}
    state.extension['treasury'] = treasures.empty(game, state)
    treasures.validate(game, state)
    return game, state


def exhaust_books(state,owner='one'):
    # Model earlier accepted commands through the real ledger, without minting
    # extra resources or relaxing the production service checks.
    city=next(city for city in state.cities.values() if city.owner==owner)
    for _ in range(command_books.remaining(state,owner)):
        command_books.spend(state,city,'search_treasure')


class TreasuresTests(unittest.TestCase):
    def fails(self, game, state, fn, payload):
        before = deepcopy(state)
        with self.assertRaises((GameError, ValueError, TypeError)):
            fn(game, state, payload, 'one')
        self.assertEqual(state, before, 'Invalid commands must not spend, act, sample RNG or emit events')

    def test_opening_tiers_neutral_and_pure_governor_views(self):
        game, state = fixture()
        pool = state.extension['treasury']
        self.assertEqual({key: row['treasure'] for key, row in pool['cities'].items()},
                         dict(capital=6, border=2, large=4, neutral=0, lone=2))
        self.assertEqual(pool['ledger'], dict(initial=14, found=0, spent=0, sold=0, lost=0))
        self.assertEqual(pool['cities']['capital']['governor'], 1, 'Present ruler precedes higher-virtue officers')
        self.assertEqual(pool['cities']['border']['governor'], 5, 'Health breaks a virtue/intellect tie')
        self.assertEqual(pool['cities']['lone']['governor'], 'clerk-000001')
        before = deepcopy(state)
        for _ in range(3):
            view = treasures.view(game, state)
            self.assertFalse(view['cities']['large']['can_manage'])
            self.assertTrue(view['cities']['capital']['can_search'])
            self.assertEqual(len(view['cities']['capital']['reward_targets']), 2)
        self.assertEqual(state, before)
        view['cities']['capital']['reward_targets'][0]['gold_rewards'][0]['gain'] = 99
        view['factions']['one']['policy']['enabled'] = True
        self.assertEqual(state, before, 'View containers cannot alias mutable treasury policy or quotes')

    def test_governor_manual_selection_auto_restore_and_unavailability(self):
        game, state = fixture()
        treasures.set_governor(game, state, dict(city='capital', officer=2), 'one')
        row = state.extension['treasury']['cities']['capital']
        self.assertEqual((row['governor'], row['governor_mode']), (2, 'manual'))
        self.assertFalse(state.cities['capital'].action_used)
        self.assertEqual(state.extension['officer_actions'], {})
        treasures.synchronize(game, state)
        self.assertEqual(row['governor'], 2)
        treasures.set_governor(game, state, dict(city='capital', officer=None), 'one')
        self.assertEqual((row['governor'], row['governor_mode']), (1, 'auto'))
        treasures.set_governor(game, state, dict(city='capital', officer=2), 'one')
        state.extension['travel']['marches'] = [dict(officers=[2])]
        treasures.synchronize(game, state)
        self.assertEqual((row['governor'], row['governor_mode']), (1, 'auto'))
        self.fails(game, state, treasures.set_governor, dict(city='capital', officer=2))
        self.fails(game, state, treasures.set_governor, dict(city='capital', officer=7))
        self.fails(game, state, treasures.set_governor, dict(city='neutral', officer=None))

    def test_search_success_and_failure_use_exactly_one_draw_and_one_action(self):
        for seed, success in ((2, True), (1, False)):
            with self.subTest(seed=seed):
                game, state = fixture(seed)
                city, before = state.cities['capital'], deepcopy(state)
                expected_rng = deepcopy(state.rng)
                expected_rng.next()
                result = treasures.search(game, state, dict(city='capital', actor=1), 'one')
                self.assertEqual(result['success'], success)
                self.assertEqual(state.rng, expected_rng)
                self.assertEqual((city.gold, city.action_used), (480, True))
                self.assertEqual(state.extension['officer_actions'], {'1': 1})
                self.assertEqual(treasures.count(state, 'capital'), 6 + int(success))
                self.assertEqual(state.extension['treasury']['ledger']['found'], int(success))
                self.assertEqual(state.events[-1]['kind'], 'treasure_found' if success else 'treasure_search_failed')
                self.assertEqual(state.events[-1]['details']['amount'], int(success))
                self.assertEqual(state.officers, before.officers)
                self.assertEqual(state.soldiers, before.soldiers)
                treasures.validate(game, state)

    def test_search_prechecks_capacity_funds_phase_actor_and_payload_before_rng(self):
        for tweak, payload in (
            (lambda g, s: treasures.credit(s, 'border', 97, reason='found'), dict(city='border', actor=4)),
            (lambda g, s: setattr(s.cities['border'], 'gold', 19), dict(city='border', actor=4)),
            (lambda g, s: setattr(s, 'phase', 'battle'), dict(city='border', actor=4)),
            (lambda g, s: exhaust_books(s), dict(city='border', actor=4)),
            (lambda g, s: setattr(s.officers[4], 'health', 0), dict(city='border', actor=4)),
            (lambda g, s: s.extension['travel']['marches'].append(dict(officers=[4])), dict(city='border', actor=4)),
            (lambda g, s: None, dict(city='border', actor=True)),
            (lambda g, s: None, dict(city='border', actor=4, unknown=1)),
        ):
            game, state = fixture()
            tweak(game, state)
            self.fails(game, state, treasures.search, payload)

    def test_same_city_and_actor_can_use_all_three_books_with_atomic_exhaustion(self):
        game,state=fixture();city=state.cities['capital']
        city.action_used=True
        state.extension['officer_actions']['2']=state.turn
        initial=deepcopy(state)
        for expected in (2,1,0):
            treasures.search(game,state,dict(city=city.id,actor=2),'one')
            self.assertEqual(command_books.remaining(state,'one'),expected)
        self.assertEqual(city.gold,initial.cities['capital'].gold-60)
        self.assertEqual(state.rng.draws,initial.rng.draws+3)
        self.assertEqual([row['city'] for row in state.extension['command_books']['factions']['one']['orders']],['capital']*3)
        self.fails(game,state,treasures.search,dict(city='border',actor=4))
        self.assertFalse(treasures.view(game,state)['cities']['border']['can_search'])
        command_books.validate(game,state)
        treasures.validate(game,state)

    def test_governor_and_policy_management_remain_free_after_pool_exhaustion(self):
        game,state=fixture();exhaust_books(state)
        before=deepcopy(state)
        treasures.set_governor(game,state,dict(city='capital',officer=2),'one')
        treasures.set_policy(game,state,dict(faction='one',policy=dict(enabled=True)),'one')
        self.assertEqual(state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(state.cities,before.cities)
        self.assertEqual(state.rng,before.rng)
        self.assertEqual(state.extension['officer_actions'],before.extension['officer_actions'])
        self.assertTrue(treasures.view(game,state)['cities']['capital']['can_manage'])
        self.assertEqual(state.extension['treasury']['cities']['capital']['governor'],2)
        command_books.validate(game,state)

    def test_reward_quote_intervals_match_exact_formula_and_cap_without_rng(self):
        game, state = fixture()
        state.officers[2].loyalty = 98
        before = deepcopy(state)
        target = next(r for r in treasures.view(game, state)['cities']['capital']['reward_targets'] if r['id'] == 2)
        self.assertEqual(state, before)
        for amount in range(1, 101):
            interval, = [r for r in target['gold_rewards'] if r['min'] <= amount <= r['max']]
            expected = min(2, max(1, (amount * 120 + 2999) // 3000))
            self.assertEqual((interval['gain'], interval['loyalty']), (expected, 98 + expected))
        self.assertEqual(target['treasure_reward'], dict(amount=1, gain=2, loyalty=100))
        rng = deepcopy(state.rng)
        original = deepcopy(state.officers[2])
        treasures.reward(game, state, dict(city='capital', officer=2, kind='gold', amount=100), 'one')
        self.assertEqual(state.officers[2].loyalty, 100)
        original.loyalty = 100
        self.assertEqual(state.officers[2], original)
        self.assertEqual(state.rng, rng)
        self.assertEqual(state.cities['capital'].gold, 400)
        self.assertEqual(state.extension['officer_actions'], {'1': 1})
        self.assertEqual(state.events[-1]['details']['gain'], 2)
        self.assertEqual(state.events[-1]['person_ids'], ['person-1', 'person-2'])
        treasures.validate(game, state)

    def test_governor_can_receive_faction_reward_in_a_one_officer_clerk_city(self):
        game, state = fixture()
        ids = set(state.officers)
        treasures.reward(game, state, dict(city='lone', officer='clerk-000001', kind='treasure', amount=1), 'one')
        self.assertEqual(state.officers['clerk-000001'].loyalty, 58)
        self.assertEqual(treasures.count(state, 'lone'), 1)
        self.assertEqual(state.extension['treasury']['ledger']['spent'], 1)
        self.assertEqual(state.extension['officer_actions']['clerk-000001'], state.turn)
        self.assertEqual(state.events[-1]['person_ids'], ['person-clerk-000001'])
        self.assertEqual(set(state.officers), ids)
        treasures.validate(game, state)

    def test_unpaid_clerk_cannot_govern_search_sell_or_receive_reward(self):
        game, state = fixture()
        state.extension['civil_staff'] = dict(people={'clerk-000001': dict(working=False)})
        treasures.synchronize(game, state)
        before = deepcopy(state)
        view = treasures.view(game, state)['cities']['lone']
        self.assertIsNone(view['governor'])
        self.assertEqual(view['eligible_actors'], [])
        self.assertFalse(view['can_search'] or view['can_sell'] or view['can_reward'])
        self.assertEqual(state, before)
        for fn, payload in (
            (treasures.search, dict(city='lone', actor='clerk-000001')),
            (treasures.sell, dict(city='lone', actor='clerk-000001', amount=1)),
            (treasures.reward, dict(city='lone', officer='clerk-000001', kind='gold', amount=1)),
            (treasures.set_governor, dict(city='lone', officer='clerk-000001')),
        ):
            self.fails(game, state, fn, payload)
        treasures.validate(game, state)

    def test_rewards_reject_cap_rulers_marching_actors_and_invalid_costs_without_spending(self):
        for payload in (
            dict(city='capital', officer=1, kind='gold', amount=10),
            dict(city='capital', officer=2, kind='gold', amount=0),
            dict(city='capital', officer=2, kind='gold', amount=101),
            dict(city='capital', officer=2, kind='gold', amount=True),
            dict(city='capital', officer=2, kind='treasure', amount=2),
            dict(city='capital', officer=2, kind='unknown', amount=1),
        ):
            game, state = fixture()
            self.fails(game, state, treasures.reward, payload)
        for key in ('full', 'actor_exhausted', 'target_marching', 'books_used'):
            game, state = fixture()
            if key == 'full':
                state.officers[2].loyalty = 100
            elif key == 'actor_exhausted':
                for ident in state.cities['capital'].roster.officer_ids:
                    state.officers[ident].health = 0
            elif key == 'target_marching':
                state.extension['travel']['marches'].append(dict(officers=[2]))
            else:
                exhaust_books(state)
            self.fails(game, state, treasures.reward, dict(city='capital', officer=2, kind='gold', amount=10))
        game, state = fixture()
        state.extension['officer_actions']['2'] = 1
        treasures.reward(game, state, dict(city='capital', officer=2, kind='gold', amount=1), 'one')
        self.assertEqual(state.officers[2].loyalty, 51, 'An already-active recipient may still receive a faction award')

    def test_sell_batch_quotes_funds_ceiling_and_conservation(self):
        game, state = fixture()
        before_rng, before_officers = deepcopy(state.rng), deepcopy(state.officers)
        self.assertEqual(treasures.view(game, state)['cities']['capital']['sell_max'], 6)
        treasures.sell(game, state, dict(city='capital', actor=2, amount=3), 'one')
        self.assertEqual((treasures.count(state, 'capital'), state.cities['capital'].gold), (3, 800))
        self.assertEqual(state.extension['treasury']['ledger']['sold'], 3)
        self.assertEqual(state.rng, before_rng)
        self.assertEqual(state.officers, before_officers)
        treasures.validate(game, state)
        for amount in (0, 7, True, 1.5):
            game, state = fixture()
            self.fails(game, state, treasures.sell, dict(city='capital', actor=2, amount=amount))
        game, state = fixture()
        state.cities['capital'].gold = 99999950
        self.assertEqual(treasures.view(game, state)['cities']['capital']['sell_max'], 0)
        self.fails(game, state, treasures.sell, dict(city='capital', actor=2, amount=1))

    def test_capture_and_late_city_split_keep_existing_assets_and_new_owner(self):
        game, state = fixture()
        initial = state.extension['treasury']['ledger']['initial']
        city = state.cities['capital']
        city.owner = 'two'
        for ident in city.roster.officer_ids:
            state.officers[ident].faction_id = 'two'
        treasures.synchronize(game, state)
        self.assertEqual(treasures.count(state, 'capital'), 6)
        self.assertEqual(state.extension['treasury']['cities']['capital']['owner'], 'two')
        state.cities['new'] = SimpleNamespace(id='new', owner='two', roster=SimpleNamespace(officer_ids=[]),
            gold=0, grain=0, reserves=0, action_used=False)
        treasures.synchronize(game, state)
        self.assertEqual(treasures.count(state, 'new'), 0, 'Synchronizing a founded node must not mint an opening stock')
        self.assertEqual(treasures.inherit_city(state, 'new', 'capital'), 1)
        self.assertEqual((treasures.count(state, 'new'), treasures.count(state, 'capital')), (1, 5))
        self.assertEqual(state.extension['treasury']['ledger']['initial'], initial)
        treasures.validate(game, state)

    def test_transit_credit_return_and_weather_loss_are_counted_once(self):
        game, state = fixture()
        treasures.debit(state, 'capital', 3)
        convoy = dict(officers=[], cargo=dict(treasure=3))
        state.extension['logistics']['convoys'].append(convoy)
        treasures.validate(game, state)
        convoy['cargo']['treasure'] -= 1
        treasures.record_loss(state, 1)
        treasures.validate(game, state)
        treasures.credit(state, 'border', 2)
        convoy['cargo']['treasure'] = 0
        treasures.validate(game, state)
        self.assertEqual(state.extension['treasury']['ledger']['lost'], 1)
        before = deepcopy(state)
        with self.assertRaises(GameError):
            treasures.debit(state, 'capital', 4)
        self.assertEqual(state, before)

    def test_policy_validation_and_shared_player_ai_once_per_turn(self):
        game, state = fixture()
        for policy in ({'enabled': 1}, {'target_loyalty': 0}, {'target_loyalty': 101},
                       {'gold_budget': -1}, {'gold_floor': True}, {'treasure_floor': 100},
                       {'prefer': 'unknown'}, {'unknown': 1}):
            self.fails(game, state, treasures.set_policy, dict(faction='one', policy=policy))
        treasures.set_policy(game, state, dict(faction='one', policy=dict(enabled=True,
            target_loyalty=90, gold_budget=100, gold_floor=100, treasure_floor=1)), 'one')
        ai = deepcopy(state)
        ai.player, ai.phase = 'two', 'ai'
        rng = deepcopy(state.rng)
        first = treasures.auto_turn(game, state, 'one')
        second = treasures.auto_turn(game, ai, 'one')
        self.assertEqual(first, second)
        self.assertEqual(state.officers, ai.officers)
        self.assertEqual(state.cities, ai.cities)
        self.assertEqual(state.extension['treasury'], ai.extension['treasury'])
        self.assertEqual(state.rng, rng)
        self.assertLessEqual(sum(r['amount'] for r in first if r['kind'] == 'gold'), 100)
        self.assertTrue(all(row['treasure'] >= 1 for key, row in state.extension['treasury']['cities'].items()
                            if state.cities[key].owner == 'one'))
        before = deepcopy(state)
        self.assertEqual(treasures.auto_turn(game, state, 'one'), [])
        self.assertEqual(state, before)
        treasures.validate(game, state)

    def test_idle_ai_uses_shared_sales_searches_actor_order_and_replayable_rng(self):
        game, state = fixture()
        state.player, state.phase = 'two', 'ai'
        state.cities['capital'].gold = 15
        state.cities['lone'].action_used = True
        treasures.debit(state, 'border', 1, reason='spent')
        before = deepcopy(state)
        manual = deepcopy(state)
        # Highest intellect actor2 beats the capital's ruler1; tied border
        # intellect/virtue uses the stable reference, without a health tie-break.
        treasures.search(game, manual, dict(city='border', actor=4), 'one')
        treasures.sell(game, manual, dict(city='capital', actor=2, amount=1), 'one')
        result = treasures.ai_idle_turn(game, state, 'one')
        self.assertEqual(len(result), 2)
        # The explicit manual replay uses the same lexical city order, so the
        # command-book ledger and event sequence agree as well as the resources.
        self.assertEqual(state, manual)
        self.assertEqual(state.extension['officer_actions'], {'4': 1, '2': 1})
        self.assertEqual((state.cities['capital'].gold, treasures.count(state, 'capital')), (115, 5))
        replay = deepcopy(before)
        self.assertEqual(treasures.ai_idle_turn(game, replay, 'one'), result)
        self.assertEqual(replay, state)
        finished = deepcopy(state)
        self.assertEqual(treasures.ai_idle_turn(game, state, 'one'), [])
        self.assertEqual(state, finished)
        self.assertEqual(state.soldiers, before.soldiers)
        self.assertEqual(state.officers, before.officers)
        treasures.validate(game, state)

    def test_idle_ai_respects_floors_books_actor_availability_and_search_threshold(self):
        for case in ('floor', 'funds', 'books', 'in_transit', 'phase'):
            with self.subTest(case=case):
                game, state = fixture()
                state.player, state.phase = 'two', 'ai'
                # Retain old activity markers deliberately; only the shared
                # book balance and actual service conditions may block work.
                for city in state.cities.values():
                    city.action_used = city.id != 'border'
                if case in ('funds', 'books', 'in_transit'):
                    treasures.debit(state, 'border', 1, reason='spent')
                if case == 'floor':
                    state.cities['border'].gold = 0
                    state.extension['treasury']['factions']['one']['treasure_floor'] = 2
                elif case == 'funds':
                    state.cities['border'].gold = 119
                elif case == 'books':
                    exhaust_books(state)
                elif case == 'in_transit':
                    state.extension['travel']['marches'] = [dict(officers=[4, 5])]
                else:
                    state.phase = 'battle'
                before = deepcopy(state)
                self.assertEqual(treasures.ai_idle_turn(game, state, 'one'), [])
                self.assertEqual(state, before)

    def test_strict_schema_and_treasure_ledger_reject_tampering(self):
        mutations = [lambda s: s.extension['treasury'].update(extra=1),
            lambda s: s.extension['treasury']['cities']['capital'].update(treasure=True),
            lambda s: s.extension['treasury']['cities']['capital'].update(treasure=100),
            lambda s: s.extension['treasury']['cities']['capital'].update(owner='two'),
            lambda s: s.extension['treasury']['cities']['capital'].update(governor=7, governor_mode='manual'),
            lambda s: s.extension['treasury']['ledger'].update(found=1),
            lambda s: s.extension['treasury']['auto_turns'].update(one=2)]
        for mutate in mutations:
            game, state = fixture()
            mutate(state)
            with self.assertRaises((ValueError, GameError)):
                treasures.validate(game, state)
        game, state = fixture()
        treasures.debit(state, 'capital', 1)
        state.extension['logistics']['convoys'].append(dict(cargo=dict(treasure=True)))
        with self.assertRaisesRegex(ValueError, 'convoy assets'):
            treasures.validate(game, state)


if __name__ == '__main__':
    unittest.main()
