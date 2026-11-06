"""Chain's fixed accepted samples and the shared optional condition service.

These are recovered-rule vectors and service tests, not new6502 experiments.
The casting caller owns its single success gate, connected-water traversal
and per-water-victim sampling; this pure service must never draw for either.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from remake import battle_conditions as conditions
from test_remake_phantom_condition import context, STAFF


class ChainConditionServiceTests(unittest.TestCase):
    def test_literal_attack_defend_duration_vectors_keep_phantom_api(self):
        for side, roll, expected in (('attackers', 0, 4), ('attackers', 1, 5),
                                     ('defenders', 0, 3), ('defenders', 1, 4)):
            with self.subTest(side=side, roll=roll):
                self.assertEqual(conditions.chain_duration(side, roll), expected)
        self.assertEqual(conditions.duration('attackers'), 3)
        self.assertEqual(conditions.duration('defenders'), 2)
        self.assertEqual(conditions.SCHEMA, 'tk2-battle-conditions-v1')

    def test_roll_and_side_boundaries_reject_coercion(self):
        for roll in (-1, 2, True, False, 0.0, 1.0, '0', '1', None, [], {}):
            with self.subTest(roll=roll), self.assertRaises(ValueError):
                conditions.chain_duration('attackers', roll)
        for side in (0, 128, True, None, 'attacker', 'defender', [], {}):
            with self.subTest(side=side), self.assertRaises(ValueError):
                conditions.chain_duration(side, 0)

    def test_each_supplied_sample_applies_exact_count_without_touching_legacy_flags(self):
        for side, target, roll, expected in (('attackers', 2, 0, 4), ('attackers', 2, 1, 5),
                                            ('defenders', 1, 0, 3), ('defenders', STAFF, 1, 4)):
            with self.subTest(side=side, roll=roll):
                _, battle = context()
                before = deepcopy(battle)
                self.assertEqual(conditions.apply_chain(battle, target, side, roll), expected)
                self.assertEqual(conditions.kind(battle, target), 'chain')
                self.assertEqual(conditions.remaining(battle, target), expected)
                self.assertTrue(conditions.movement_blocked(battle, target))
                self.assertEqual(battle['extended']['support'], before['extended']['support'])
                self.assertEqual(battle['attackers'], before['attackers'])
                self.assertEqual(battle['defenders'], before['defenders'])
                self.assertEqual(conditions.view(battle)['day'], 1)
                conditions.validate(battle)

    def test_old_missing_kind_queries_are_pure_and_never_infer_stunned(self):
        state, battle = context()
        before = deepcopy(battle)
        for ident in (1, 2, STAFF):
            self.assertIsNone(conditions.kind(battle, ident))
            self.assertEqual(conditions.remaining(battle, ident), 0)
            self.assertFalse(conditions.movement_blocked(battle, ident))
        self.assertIsNone(conditions.view(battle))
        conditions.validate(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(conditions.drop_removed(battle), [])
        self.assertFalse(conditions.clear(battle, 2))
        self.assertEqual(battle, before)
        self.assertNotIn('conditions', battle['extended'])

    def test_ongoing_legacy_initializes_only_on_actual_apply_at_current_day(self):
        _, battle = context()
        battle['round'] = 17
        before = deepcopy(battle['extended']['support'])
        self.assertIsNone(conditions.view(battle))
        conditions.apply_chain(battle, STAFF, 'defenders', 1)
        self.assertEqual(conditions.view(battle), dict(schema=conditions.SCHEMA, day=17,
            units={STAFF:dict(kind='chain', remaining=4)}))
        self.assertEqual(battle['extended']['support'], before)
        conditions.validate(battle)

    def test_cross_kind_recasts_overwrite_without_stacking_or_touching_other_unit(self):
        state, battle = context()
        conditions.apply(battle, 2, 'attackers')
        conditions.apply(battle, 1, 'defenders')
        other = deepcopy(conditions.view(battle)['units']['1'])
        self.assertEqual(conditions.kind(battle, 2), 'phantom')
        conditions.apply_chain(battle, 2, 'attackers', 1)
        self.assertEqual((conditions.kind(battle, 2), conditions.remaining(battle, 2)), ('chain', 5))
        battle['round'] = 2
        conditions.advance_daily(state, battle)
        self.assertEqual(conditions.remaining(battle, 2), 4)
        conditions.apply(battle, 2, 'attackers')
        self.assertEqual((conditions.kind(battle, 2), conditions.remaining(battle, 2)), ('phantom', 3))
        # The other unit only incurred its one genuine day decrement.
        self.assertEqual(conditions.view(battle)['units']['1'],
                         dict(kind=other['kind'], remaining=other['remaining']-1))
        conditions.apply_chain(battle, 2, 'attackers', 0)
        self.assertEqual(conditions.view(battle)['units']['2'], dict(kind='chain', remaining=4))
        conditions.validate(battle)

    def test_mixed_daily_clock_preserves_kind_stable_order_and_expiry(self):
        state, battle = context()
        conditions.apply_chain(battle, 2, 'attackers', 1)
        conditions.apply_chain(battle, 1, 'defenders', 0)
        conditions.apply(battle, STAFF, 'defenders')
        before = deepcopy(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, before, 'A half-turn/same-day call cannot tick')
        battle['round'] = 2
        self.assertEqual(conditions.advance_daily(state, battle), [
            dict(id='1', kind='chain', before=3, remaining=2),
            dict(id='2', kind='chain', before=5, remaining=4),
            dict(id=STAFF, kind='phantom', before=2, remaining=1)])
        once = deepcopy(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, once)
        battle['round'] = 3
        changes = conditions.advance_daily(state, battle)
        self.assertEqual(changes[-1], dict(id=STAFF, kind='phantom', before=1, remaining=0))
        self.assertIsNone(conditions.kind(battle, STAFF))
        self.assertEqual(conditions.kind(battle, 1), 'chain')
        battle['round'] = 4
        self.assertEqual(conditions.advance_daily(state, battle)[0],
                         dict(id='1', kind='chain', before=1, remaining=0))
        self.assertIsNone(conditions.kind(battle, 1))
        for day in (5, 6):
            battle['round'] = day
            conditions.advance_daily(state, battle)
        self.assertEqual(conditions.view(battle), dict(schema=conditions.SCHEMA, day=6, units={}))
        self.assertFalse(conditions.movement_blocked(battle, 2))
        conditions.validate(battle)

    def test_clear_and_drop_removed_handle_both_kinds_without_support_repair(self):
        for condition_kind in ('phantom', 'chain'):
            for cause in ('troops', 'health', 'surrender', 'absent'):
                with self.subTest(kind=condition_kind, cause=cause):
                    _, battle = context()
                    if condition_kind == 'phantom': conditions.apply(battle, 2, 'attackers')
                    else: conditions.apply_chain(battle, 2, 'attackers', 1)
                    if cause == 'troops': battle['defenders'][0]['troops'] = 0
                    if cause == 'health': battle['extended']['support']['2']['health'] = 0
                    if cause == 'surrender': battle['extended']['surrenders']['2'] = 600
                    if cause == 'absent': battle['defenders'].clear()
                    support = deepcopy(battle['extended']['support'])
                    with self.assertRaises(ValueError): conditions.validate(battle)
                    self.assertEqual(conditions.drop_removed(battle), ['2'])
                    self.assertEqual(conditions.drop_removed(battle), [])
                    self.assertEqual(conditions.view(battle)['units'], {})
                    self.assertEqual(battle['extended']['support'], support)
                    conditions.validate(battle)
        _, battle = context()
        conditions.apply_chain(battle, 2, 'attackers', 0)
        self.assertTrue(conditions.clear(battle, 2))
        self.assertFalse(conditions.clear(battle, 2))
        self.assertEqual(conditions.view(battle)['units'], {})
        self.assertIsNone(conditions.kind(battle, 2))

    def test_result_and_thirty_day_limit_leave_both_kinds_unchanged(self):
        for final_day, outcome in ((2, 'retreat'), (2, 'victory'), (31, 'retreat')):
            with self.subTest(day=final_day, outcome=outcome):
                state, battle = context()
                if final_day == 31: battle['round'] = 30
                conditions.apply_chain(battle, 2, 'attackers', 1)
                conditions.apply(battle, 1, 'defenders')
                battle.update(round=final_day, outcome=outcome)
                state.phase = 'result'
                before = deepcopy(battle)
                self.assertEqual(conditions.advance_daily(state, battle), [])
                self.assertEqual(battle, before)
                conditions.validate(battle)
        state, battle = context()
        battle['round'] = 30
        conditions.apply_chain(battle, 2, 'attackers', 1)
        battle['round'] = 31
        before = deepcopy(battle)
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, before)

    def test_zero_bag_credit_is_owned_by_food_service_not_condition_kind(self):
        state, battle = context()
        conditions.apply_chain(battle, 2, 'attackers', 1)
        # A completed meal may leave zero bags and useful fractional credit.
        # The condition service must neither read nor initialize that ledger.
        battle['extended']['supply'] = dict(sides={side:dict(remaining=0, credit_units=900)
                                                for side in conditions.SIDES})
        before = deepcopy(battle['extended']['supply'])
        battle['round'] = 2
        conditions.advance_daily(state, battle)
        self.assertEqual((conditions.kind(battle, 2), conditions.remaining(battle, 2)), ('chain', 4))
        self.assertEqual(battle['extended']['supply'], before)

    def test_new_chain_apply_rejects_bad_roll_target_or_phase_atomically(self):
        for target, side, roll in ((2, 'attackers', -1), (2, 'attackers', 2),
                                   (2, 'attackers', True), (2, 'attackers', 0.0),
                                   (2, 'wrong', 0), (1, 'attackers', 0),
                                   (2, 'defenders', 0), (True, 'attackers', 0),
                                   (999, 'attackers', 0)):
            with self.subTest(target=target, side=side, roll=roll):
                _, battle = context()
                before = deepcopy(battle)
                with self.assertRaises(ValueError): conditions.apply_chain(battle, target, side, roll)
                self.assertEqual(battle, before)
        for terminal in ('troops', 'health', 'surrender', 'outcome', 'timeout'):
            _, battle = context()
            if terminal == 'troops': battle['defenders'][0]['troops'] = 0
            if terminal == 'health': battle['extended']['support']['2']['health'] = 0
            if terminal == 'surrender': battle['extended']['surrenders']['2'] = 600
            if terminal == 'outcome': battle['outcome'] = 'retreat'
            if terminal == 'timeout': battle['round'] = 31
            before = deepcopy(battle)
            with self.assertRaises(ValueError): conditions.apply_chain(battle, 2, 'attackers', 0)
            self.assertEqual(battle, before)

    def test_kind_specific_schema_bounds_and_types_are_strict(self):
        _, original = context()
        conditions.apply_chain(original, 2, 'attackers', 1)
        for condition_kind, count in (('phantom', 1), ('phantom', 3), ('chain', 1), ('chain', 5)):
            battle = deepcopy(original)
            battle['extended']['conditions']['units']['2'] = dict(kind=condition_kind, remaining=count)
            conditions.validate(battle)
        invalid_rows = (None, [], {}, dict(kind='unknown', remaining=1),
            dict(kind='phantom', remaining=4), dict(kind='chain', remaining=6),
            dict(kind='chain', remaining=0), dict(kind='chain', remaining=-1),
            dict(kind='chain', remaining=True), dict(kind='chain', remaining=1.0),
            dict(kind='chain', remaining='1'), dict(kind=[], remaining=1),
            dict(kind={}, remaining=1), dict(kind=None, remaining=1),
            dict(kind='chain', remaining=1, extra=0))
        for index, invalid in enumerate(invalid_rows):
            with self.subTest(index=index):
                battle = deepcopy(original)
                battle['extended']['conditions']['units']['2'] = invalid
                before = deepcopy(battle)
                with self.assertRaises(ValueError): conditions.validate(battle)
                self.assertEqual(battle, before)

    def test_mixed_snapshot_and_serialized_roundtrip_are_pure(self):
        _, battle = context()
        conditions.apply_chain(battle, 2, 'attackers', 1)
        conditions.apply(battle, 1, 'defenders')
        before = deepcopy(battle)
        view = conditions.view(battle)
        view['units']['2']['remaining'] = 1
        view['units']['1']['kind'] = 'chain'
        self.assertEqual(battle, before)
        restored = json.loads(json.dumps(battle))
        conditions.validate(restored)
        self.assertEqual(conditions.view(restored), conditions.view(battle))
        self.assertEqual(conditions.kind(restored, 1), 'phantom')
        self.assertEqual(conditions.kind(restored, 2), 'chain')

    def test_active_clock_foreign_references_and_invalid_apply_do_not_repair(self):
        state, battle = context()
        conditions.apply_chain(battle, 2, 'attackers', 0)
        battle['round'] = 2
        with self.assertRaises(ValueError): conditions.view(battle)
        with self.assertRaises(ValueError): conditions.kind(battle, 2)
        conditions.advance_daily(state, battle)
        before = deepcopy(battle)
        with self.assertRaises(ValueError): conditions.apply_chain(battle, 2, 'attackers', 2)
        self.assertEqual(battle, before)
        battle['round'] = 4
        before = deepcopy(battle)
        with self.assertRaises(ValueError): conditions.advance_daily(state, battle)
        self.assertEqual(battle, before)
        battle = deepcopy(before)
        battle['round'] = 2
        battle['extended']['conditions']['units']['999'] = dict(kind='chain', remaining=1)
        before = deepcopy(battle)
        with self.assertRaises(ValueError): conditions.validate(battle)
        self.assertEqual(battle, before)


if __name__ == '__main__':
    unittest.main()
