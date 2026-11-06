"""Independent phantom clock/service boundaries, without success-gate guesses."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from remake import battle_conditions as conditions


STAFF = 'clerk-000001'


class NoRandom:
    def next(self):
        raise AssertionError('Phantom state must not draw random numbers')


def context():
    state = SimpleNamespace(phase='battle', rng=NoRandom())
    battle = dict(round=1, outcome=None,
        attackers=[dict(id=1, troops=500), dict(id=STAFF, troops=300)],
        defenders=[dict(id=2, troops=600)],
        extended=dict(support={str(ident):dict(health=80, stunned=1, guard=2)
                               for ident in (1, 2, STAFF)}, surrenders={}))
    return state, battle


class PhantomConditionServiceTests(unittest.TestCase):
    def test_fixed_original_side_durations_and_strict_input(self):
        self.assertEqual(conditions.duration('attackers'), 3)
        self.assertEqual(conditions.duration('defenders'), 2)
        for invalid in (0, 128, True, None, 'attacker', 'defender', []):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                conditions.duration(invalid)

    def test_missing_legacy_reads_and_noop_clears_never_create_or_infer_a_state(self):
        state, battle = context()
        before = deepcopy(battle)
        self.assertIsNone(conditions.view(battle))
        self.assertIsNone(conditions.validate(battle))
        self.assertEqual(conditions.remaining(battle, 2), 0)
        self.assertFalse(conditions.movement_blocked(battle, 2))
        self.assertFalse(conditions.clear(battle, 2))
        self.assertEqual(conditions.drop_removed(battle), [])
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, before)
        self.assertNotIn('conditions', battle['extended'])

    def test_apply_initializes_only_at_success_and_keeps_legacy_support_untouched(self):
        _, battle = context()
        support = deepcopy(battle['extended']['support'])
        self.assertEqual(conditions.apply(battle, 2, 'attackers'), 3)
        self.assertEqual(battle['extended']['conditions'], dict(schema=conditions.SCHEMA,
            day=1, units={'2':dict(kind='phantom', remaining=3)}))
        self.assertEqual(conditions.apply(battle, 1, 'defenders'), 2)
        self.assertTrue(conditions.movement_blocked(battle, 1))
        self.assertEqual(conditions.remaining(battle, 2), 3)
        self.assertEqual(battle['extended']['support'], support)
        conditions.validate(battle)

    def test_ongoing_legacy_battle_starts_clock_now_and_supports_generated_officers(self):
        _, battle = context()
        battle['round'] = 17
        self.assertEqual(conditions.apply(battle, STAFF, 'defenders'), 2)
        self.assertEqual(battle['extended']['conditions']['day'], 17)
        self.assertEqual(conditions.remaining(battle, STAFF), 2)
        conditions.validate(battle)

    def test_view_is_an_independent_pure_snapshot(self):
        _, battle = context()
        conditions.apply(battle, 2, 'attackers')
        before = deepcopy(battle)
        snapshot = conditions.view(battle)
        snapshot['units']['2']['remaining'] = 1
        snapshot['units'].clear()
        snapshot['day'] = 0
        self.assertEqual(battle, before)
        self.assertEqual(conditions.view(battle), before['extended']['conditions'])

    def test_each_completed_day_ticks_once_and_last_tick_expires_without_rng(self):
        state, battle = context()
        conditions.apply(battle, 2, 'attackers')
        conditions.apply(battle, 1, 'defenders')
        before = deepcopy(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, before, 'A same-round/half-turn hook cannot tick')
        battle['round'] = 2
        self.assertEqual(conditions.advance_daily(state, battle), [
            dict(id='1', kind='phantom', before=2, remaining=1),
            dict(id='2', kind='phantom', before=3, remaining=2)])
        once = deepcopy(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, once)
        battle['round'] = 3
        self.assertEqual(conditions.advance_daily(state, battle)[0],
                         dict(id='1', kind='phantom', before=1, remaining=0))
        self.assertEqual(conditions.remaining(battle, 1), 0)
        battle['round'] = 4
        conditions.advance_daily(state, battle)
        self.assertEqual(conditions.view(battle), dict(schema=conditions.SCHEMA, day=4, units={}))
        battle['round'] = 5
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(conditions.view(battle)['day'], 5)
        conditions.validate(battle)

    def test_active_stale_clock_and_multiday_skips_fail_without_mutation(self):
        state, battle = context()
        conditions.apply(battle, 2, 'attackers')
        battle['round'] = 2
        for reader in (conditions.validate, conditions.view):
            with self.assertRaises(ValueError):
                reader(battle)
        conditions.advance_daily(state, battle)
        conditions.validate(battle)
        battle['round'] = 4
        before = deepcopy(battle)
        with self.assertRaises(ValueError):
            conditions.advance_daily(state, battle)
        self.assertEqual(battle, before)

    def test_result_and_time_limit_stop_before_countdown(self):
        for reason, round_number in (('retreat', 2), ('victory', 2), ('defeat', 31)):
            with self.subTest(reason=reason):
                state, battle = context()
                if round_number == 31:
                    battle['round'] = 30
                conditions.apply(battle, 2, 'attackers')
                battle['round'] = round_number
                battle['outcome'] = reason
                state.phase = 'result'
                before = deepcopy(battle)
                self.assertEqual(conditions.advance_daily(state, battle), [])
                self.assertEqual(battle, before)
                conditions.validate(battle)
        state, battle = context()
        battle['round'] = 30
        conditions.apply(battle, 2, 'attackers')
        battle['round'] = 31
        before = deepcopy(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, before, 'The service also guards the30-day limit itself')

    def test_zero_bags_with_meal_credit_do_not_skip_a_live_day(self):
        state, battle = context()
        conditions.apply(battle, 2, 'attackers')
        # Food settlement is a caller-owned precondition. This auxiliary
        # snapshot represents its nonterminal zero-bag/remaining-credit result;
        # the condition service must not reimplement the ration ledger.
        battle['extended']['supply'] = dict(sides={side:dict(remaining=0, credit_units=900)
                                                for side in conditions.SIDES})
        supply = deepcopy(battle['extended']['supply'])
        battle['round'] = 2
        conditions.advance_daily(state, battle)
        self.assertEqual(conditions.remaining(battle, 2), 2)
        self.assertEqual(battle['extended']['supply'], supply)

    def test_clear_overwrite_and_empty_ledger_remain_explicit(self):
        state, battle = context()
        conditions.apply(battle, 2, 'attackers')
        battle['round'] = 2
        conditions.advance_daily(state, battle)
        self.assertEqual(conditions.remaining(battle, 2), 2)
        conditions.apply(battle, 2, 'attackers')
        self.assertEqual(conditions.remaining(battle, 2), 3, 'Recast overwrites, never stacks')
        self.assertTrue(conditions.clear(battle, 2))
        self.assertFalse(conditions.clear(battle, 2))
        self.assertEqual(conditions.view(battle), dict(schema=conditions.SCHEMA, day=2, units={}))
        conditions.validate(battle)

    def test_drop_removed_cleans_zero_troops_health_surrender_and_absent_roster(self):
        for cause in ('troops', 'health', 'surrender', 'absent'):
            with self.subTest(cause=cause):
                _, battle = context()
                conditions.apply(battle, 2, 'attackers')
                if cause == 'troops':
                    battle['defenders'][0]['troops'] = 0
                elif cause == 'health':
                    battle['extended']['support']['2']['health'] = 0
                elif cause == 'surrender':
                    battle['extended']['surrenders']['2'] = 600
                else:
                    battle['defenders'].clear()
                with self.assertRaises(ValueError):
                    conditions.validate(battle)
                self.assertEqual(conditions.drop_removed(battle), ['2'])
                self.assertEqual(conditions.drop_removed(battle), [])
                conditions.validate(battle)
                self.assertEqual(conditions.view(battle)['units'], {})

    def test_clear_can_remove_a_just_routed_target_without_repairing_support(self):
        _, battle = context()
        conditions.apply(battle, 2, 'attackers')
        battle['defenders'][0]['troops'] = 0
        before = deepcopy(battle['extended']['support'])
        self.assertTrue(conditions.clear(battle, 2))
        self.assertEqual(battle['extended']['support'], before)
        conditions.validate(battle)

    def test_invalid_apply_is_atomic_and_does_not_create_a_legacy_section(self):
        for target, side in ((1, 'attackers'), (2, 'defenders'), (999, 'attackers'),
                             (True, 'attackers'), (2, 'invalid')):
            with self.subTest(target=target, side=side):
                _, battle = context()
                before = deepcopy(battle)
                with self.assertRaises(ValueError):
                    conditions.apply(battle, target, side)
                self.assertEqual(battle, before)
        for terminal in ('troops', 'health', 'surrender', 'outcome', 'timeout'):
            _, battle = context()
            if terminal == 'troops': battle['defenders'][0]['troops'] = 0
            if terminal == 'health': battle['extended']['support']['2']['health'] = 0
            if terminal == 'surrender': battle['extended']['surrenders']['2'] = 600
            if terminal == 'outcome': battle['outcome'] = 'retreat'
            if terminal == 'timeout': battle['round'] = 31
            before = deepcopy(battle)
            with self.assertRaises(ValueError):
                conditions.apply(battle, 2, 'attackers')
            self.assertEqual(battle, before)

    def test_serialized_schema_quantities_references_and_clocks_are_strict(self):
        _, original = context()
        conditions.apply(original, 2, 'attackers')
        mutations = (
            lambda e:e.__setitem__('conditions', None),
            lambda e:e['conditions'].__setitem__('extra', 0),
            lambda e:e['conditions'].__setitem__('schema', 'unknown'),
            lambda e:e['conditions'].__setitem__('day', True),
            lambda e:e['conditions'].__setitem__('day', 0),
            lambda e:e['conditions'].__setitem__('day', 2),
            lambda e:e['conditions'].__setitem__('day', 1.0),
            lambda e:e['conditions'].__setitem__('units', []),
            lambda e:e['conditions']['units'].__setitem__('999', dict(kind='phantom', remaining=1)),
            lambda e:e['conditions']['units'].__setitem__(2, dict(kind='phantom', remaining=1)),
            lambda e:e['conditions']['units'].__setitem__('2', None),
            lambda e:e['conditions']['units']['2'].__setitem__('kind', 'chain'),
            lambda e:e['conditions']['units']['2'].__setitem__('remaining', 0),
            lambda e:e['conditions']['units']['2'].__setitem__('remaining', 4),
            lambda e:e['conditions']['units']['2'].__setitem__('remaining', True),
            lambda e:e['conditions']['units']['2'].__setitem__('remaining', 2.0),
            lambda e:e['conditions']['units']['2'].__setitem__('extra', 0),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                battle = deepcopy(original)
                mutate(battle['extended'])
                before = deepcopy(battle)
                with self.assertRaises(ValueError):
                    conditions.validate(battle)
                self.assertEqual(battle, before)


if __name__ == '__main__':
    unittest.main()
