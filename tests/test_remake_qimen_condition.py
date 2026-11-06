"""Qimen service boundaries and independently calculated recovered-rule vectors.

No test here claims new6502 execution. Root's campaign layer owns real target
eligibility, success sampling, AP, day/food termination and atomic commands.
The controlled officer/army records below isolate the persistent high clock,
fixed-person source, seeded-modulo damage order and declared growth adaptation.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from remake import battle_conditions as conditions

STAFF = 'clerk-000001'


class Samples:
    def __init__(self, values=()):
        self.values = list(values)
        self.draws = 0

    def next(self):
        if self.draws >= len(self.values):
            raise AssertionError('Unexpected condition random sample')
        value = self.values[self.draws]
        self.draws += 1
        return value


def context(values=()):
    battle = dict(round=1, outcome=None,
        defenders=[dict(id=2, troops=999, martial=60), dict(id=4, troops=260, martial=70)],
        attackers=[dict(id=1, troops=700, martial=75), dict(id=3, troops=180, martial=65),
                   dict(id=STAFF, troops=300, martial=50)],
        extended=dict(support={str(ident):dict(health=80, stunned=1, guard=2)
                               for ident in (1, 2, 3, 4, STAFF)}, surrenders={}))
    officers = {ident:SimpleNamespace(person_id=conditions.QIMEN_PERSON if ident == 1 else str(ident),
        profile=SimpleNamespace(martial_strength=75), experience=0, tier=0, troops=999)
        for ident in (1, 2, 3, 4, STAFF)}
    return SimpleNamespace(phase='battle', rng=Samples(values), officers=officers,
        soldiers={ident:999 for ident in officers}), battle


def troop(battle, ident):
    return next(unit for side in conditions.SIDES for unit in battle[side] if unit['id'] == ident)


def next_day(state, battle):
    battle['round'] += 1
    return conditions.advance_daily(state, battle)


class QimenConditionServiceTests(unittest.TestCase):
    def test_fixed_side_sample_vectors_and_strict_duration_input(self):
        for side, roll, expected in (('attackers', 0, 6), ('attackers', 1, 7),
                ('attackers', 2, 8), ('attackers', 3, 9), ('defenders', 0, 5),
                ('defenders', 1, 6), ('defenders', 2, 7), ('defenders', 3, 8)):
            with self.subTest(side=side, roll=roll):
                self.assertEqual(conditions.qimen_duration(side, roll), expected)
        for roll in (-1, 4, True, False, 0.0, 3.0, '0', None, [], {}):
            with self.subTest(roll=roll), self.assertRaises(ValueError):
                conditions.qimen_duration('attackers', roll)
        for side in (0, 128, True, None, 'attacker', [], {}):
            with self.subTest(side=side), self.assertRaises(ValueError):
                conditions.qimen_duration(side, 0)

    def test_only_first_qimen_success_adds_complete_defender_first_order(self):
        state, battle = context()
        conditions.apply(battle, 2, 'attackers')
        before = deepcopy(battle['extended']['support'])
        self.assertNotIn('high_order', conditions.view(battle))
        self.assertEqual(conditions.apply_qimen(battle, 2, 'attackers', 3), 9)
        self.assertEqual(conditions.view(battle)['high_order'], ['2', '4', '1', '3', STAFF])
        self.assertEqual(conditions.kind(battle, 2), 'qimen')
        self.assertEqual(conditions.remaining(battle, 2), 9)
        self.assertTrue(conditions.movement_blocked(battle, 2))
        self.assertEqual(state.rng.draws, 0)
        self.assertEqual(battle['extended']['support'], before)
        conditions.validate(battle)

    def test_qimen_and_low_effects_overwrite_one_kind_without_losing_order(self):
        _, battle = context()
        conditions.apply_qimen(battle, 2, 'attackers', 3)
        order = deepcopy(conditions.view(battle)['high_order'])
        conditions.apply_chain(battle, 2, 'attackers', 0)
        self.assertEqual(conditions.view(battle)['units']['2'], dict(kind='chain', remaining=4))
        conditions.apply(battle, 2, 'attackers')
        self.assertEqual(conditions.view(battle)['units']['2'], dict(kind='phantom', remaining=3))
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        self.assertEqual(conditions.view(battle)['units']['2'], dict(kind='qimen', remaining=6))
        self.assertEqual(conditions.view(battle)['high_order'], order)

    def test_source_uses_fixed_person_on_either_side_without_zero_troop_or_hp_gate(self):
        for side in ('attackers', 'defenders'):
            state, battle = context()
            if side == 'defenders':
                source = troop(battle, 1)
                battle['attackers'].remove(source)
                battle['defenders'].append(source)
            source = troop(battle, 1)
            source['troops'] = 0
            battle['extended']['support']['1']['health'] = 1
            before = deepcopy(battle)
            self.assertEqual(conditions.qimen_source(state, battle), 1)
            self.assertEqual(battle, before)
            battle['extended']['surrenders']['1'] = 700
            self.assertIsNone(conditions.qimen_source(state, battle))
            battle['extended']['surrenders'].clear()
            state.officers[1].profile.martial_strength = 0
            self.assertIsNone(conditions.qimen_source(state, battle))
            state.officers[1].profile.martial_strength = 75
            state.officers[1].person_id = 'not-original109'
            self.assertIsNone(conditions.qimen_source(state, battle))
        state, battle = context()
        battle['attackers'].remove(troop(battle, 1))
        self.assertIsNone(conditions.qimen_source(state, battle))

    def test_new_cast_rejects_routed_target_but_existing_high_target_remains(self):
        state, battle = context([0])
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        troop(battle, 2)['troops'] = 0
        battle['extended']['support']['2']['health'] = 1
        before = deepcopy(battle)
        with self.assertRaises(ValueError): conditions.apply_qimen(battle, 2, 'attackers', 0)
        self.assertEqual(battle, before)
        self.assertEqual(conditions.drop_removed(battle), [])
        conditions.validate(battle)
        change = next_day(state, battle)[0]
        self.assertEqual(change, dict(id='2', kind='qimen', before=6, remaining=5,
            troops_before=0, troops_after=0, loss=0))
        self.assertEqual(state.rng.draws, 1, 'A present zero-men high target still samples')
        self.assertEqual(conditions.kind(battle, 2), 'qimen')

    def test_low_rout_cleanup_stays_strict_while_high_zero_men_are_retained(self):
        _, battle = context()
        conditions.apply_qimen(battle, 2, 'attackers', 1)
        conditions.apply_chain(battle, 4, 'attackers', 1)
        troop(battle, 2)['troops'] = troop(battle, 4)['troops'] = 0
        battle['extended']['support']['2']['health'] = 1
        self.assertEqual(conditions.drop_removed(battle), ['4'])
        self.assertEqual(conditions.kind(battle, 2), 'qimen')
        self.assertIsNone(conditions.kind(battle, 4))
        conditions.validate(battle)

    def test_damage_minimum_maximum_and_modulo_samples_use_saved_high_order(self):
        state, battle = context([0, 70, 71])
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        conditions.apply_qimen(battle, 4, 'attackers', 3)
        conditions.apply_qimen(battle, 3, 'defenders', 0)
        state.officers[1].experience = 999
        before_officer_troops = {i:o.troops for i,o in state.officers.items()}
        support, soldiers = deepcopy(battle['extended']['support']), deepcopy(state.soldiers)
        changes = next_day(state, battle)
        self.assertEqual(changes, [
            dict(id='2', kind='qimen', before=6, remaining=5, troops_before=999, troops_after=919, loss=80),
            dict(id='4', kind='qimen', before=9, remaining=8, troops_before=260, troops_after=110, loss=150),
            dict(id='3', kind='qimen', before=5, remaining=4, troops_before=180, troops_after=100, loss=80)])
        # Remaining low bytes151+110+100=361; floor361/2=180.
        self.assertEqual((state.officers[1].experience, state.officers[1].tier), (1179, 1))
        self.assertEqual(state.rng.draws, 3)
        self.assertEqual({i:o.troops for i,o in state.officers.items()}, before_officer_troops)
        self.assertEqual(state.soldiers, soldiers)
        self.assertEqual(battle['extended']['support'], support)
        self.assertEqual(troop(battle, 1)['martial'], 75)
        self.assertEqual(state.officers[1].profile.martial_strength, 75)

    def test_experience_sums_remaining_low_bytes_then_halves_once(self):
        state, battle = context([62, 14])
        troop(battle, 2)['troops'] = 261
        troop(battle, 4)['troops'] = 999
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        conditions.apply_qimen(battle, 4, 'attackers', 0)
        state.officers[1].experience = 999
        next_day(state, battle)
        self.assertEqual((troop(battle, 2)['troops'], troop(battle, 4)['troops']), (119, 905))
        # Low bytes119 and137 sum256, yielding128. Per-target division would
        # give127; actual losses142+94 are a different quantity altogether.
        self.assertEqual((state.officers[1].experience, state.officers[1].tier), (1127, 1))

    def test_low_clock_advances_without_source_while_high_pauses_and_day_syncs(self):
        state, battle = context()
        conditions.apply_qimen(battle, 2, 'attackers', 3)
        conditions.apply_chain(battle, 4, 'attackers', 0)
        conditions.apply(battle, STAFF, 'defenders')
        source = troop(battle, 1)
        battle['attackers'].remove(source)
        self.assertEqual(conditions.drop_removed(battle), [])
        changes = next_day(state, battle)
        self.assertEqual(changes, [dict(id='4', kind='chain', before=4, remaining=3),
            dict(id=STAFF, kind='phantom', before=2, remaining=1)])
        self.assertEqual(conditions.view(battle)['day'], 2)
        self.assertEqual(conditions.remaining(battle, 2), 9)
        self.assertEqual(troop(battle, 2)['troops'], 999)
        self.assertEqual(state.officers[1].experience, 0)
        self.assertEqual(state.rng.draws, 0)
        conditions.validate(battle)

    def test_source_reduced_to_zero_remains_source_for_same_and_next_day(self):
        state, battle = context([0, 0, 0, 0])
        state.officers[1].person_id = 'other-person'
        state.officers[2].person_id = conditions.QIMEN_PERSON
        troop(battle, 2)['troops'] = 20
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        conditions.apply_qimen(battle, 4, 'attackers', 0)
        changes = next_day(state, battle)
        self.assertEqual([(v['id'], v['loss']) for v in changes], [('2', 20), ('4', 80)])
        self.assertEqual(conditions.qimen_source(state, battle), 2)
        self.assertEqual(state.officers[2].experience, 90)  #0+180 remaining low.
        changes = next_day(state, battle)
        self.assertEqual([(v['id'], v['loss']) for v in changes], [('2', 0), ('4', 80)])
        self.assertEqual(state.officers[2].experience, 140) #0+100 remaining low.
        self.assertEqual(state.rng.draws, 4)
        self.assertEqual(conditions.remaining(battle, 2), 4)
        self.assertEqual(conditions.drop_removed(battle), [])

    def test_last_tick_still_samples_and_saturates_then_retains_empty_feature(self):
        state, battle = context([70])
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        row = battle['extended']['conditions']
        row['units']['2']['remaining'] = 1  # Explicit last-count boundary.
        troop(battle, 2)['troops'] = 1
        order = deepcopy(row['high_order'])
        self.assertEqual(next_day(state, battle), [dict(id='2', kind='qimen', before=1,
            remaining=0, troops_before=1, troops_after=0, loss=1)])
        self.assertEqual(conditions.view(battle), dict(schema=conditions.SCHEMA, day=2,
            units={}, high_order=order))
        once, xp = deepcopy(battle), state.officers[1].experience
        self.assertEqual(conditions.advance_daily(state, battle), [])
        self.assertEqual(battle, once)
        self.assertEqual(next_day(state, battle), [])
        self.assertEqual(state.rng.draws, 1)
        self.assertEqual(state.officers[1].experience, xp)
        self.assertEqual(conditions.view(battle)['high_order'], order)

    def test_conversion_reorders_current_armies_but_never_saved_damage_order(self):
        state, battle = context([0, 70])
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        conditions.apply_qimen(battle, 4, 'attackers', 0)
        order = deepcopy(conditions.view(battle)['high_order'])
        converted = troop(battle, 2)
        battle['defenders'].remove(converted)
        battle['attackers'].append(converted)
        conditions.validate(battle)
        changes = next_day(state, battle)
        self.assertEqual([(v['id'], v['loss']) for v in changes], [('2', 80), ('4', 150)])
        self.assertEqual(conditions.view(battle)['high_order'], order)

    def test_internal_clear_and_drop_prune_absent_order_but_not_rostered_surrender(self):
        for action in ('clear', 'drop'):
            state, battle = context()
            conditions.apply_qimen(battle, 2, 'attackers', 0)
            conditions.apply_qimen(battle, 4, 'attackers', 0)
            battle['defenders'].remove(troop(battle, 4))
            with self.assertRaises(ValueError): conditions.validate(battle)
            if action == 'clear': self.assertTrue(conditions.clear(battle, 4))
            else: self.assertEqual(conditions.drop_removed(battle), ['4'])
            self.assertEqual(conditions.view(battle)['high_order'], ['2', '1', '3', STAFF])
            conditions.validate(battle)
        state, battle = context()
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        order = deepcopy(conditions.view(battle)['high_order'])
        battle['extended']['surrenders']['2'] = 999
        self.assertEqual(conditions.drop_removed(battle), ['2'])
        self.assertEqual(conditions.view(battle)['high_order'], order)
        conditions.validate(battle)

    def test_current_growth_cap_tiers_do_not_mutate_profiles_or_battle_martial(self):
        for before, after, tier in ((0, 128, 0), (999, 1127, 1), (9999, 10127, 6),
                                     (14999, 15127, 7), (49998, 49999, 7), (49999, 49999, 7)):
            with self.subTest(experience=before):
                state, battle = context([62, 14])
                troop(battle, 2)['troops'] = 261
                troop(battle, 4)['troops'] = 999
                conditions.apply_qimen(battle, 2, 'attackers', 0)
                conditions.apply_qimen(battle, 4, 'attackers', 0)
                state.officers[1].experience = before
                profile, war = deepcopy(state.officers[1].profile), troop(battle, 1)['martial']
                next_day(state, battle)
                self.assertEqual((state.officers[1].experience, state.officers[1].tier), (after, tier))
                self.assertEqual(state.officers[1].profile, profile)
                self.assertEqual(troop(battle, 1)['martial'], war)

    def test_result_timeout_and_same_day_prevent_high_rng_damage_and_experience(self):
        for terminal in ('same_day', 'result', 'timeout'):
            state, battle = context()
            if terminal == 'timeout': battle['round'] = 30
            conditions.apply_qimen(battle, 2, 'attackers', 3)
            conditions.apply_chain(battle, 4, 'attackers', 1)
            if terminal != 'same_day': battle['round'] += 1
            if terminal == 'result': state.phase = 'result'; battle['outcome'] = 'retreat'
            if terminal == 'timeout': state.phase = 'result'; battle['outcome'] = 'retreat'
            before, officers, soldiers = deepcopy(battle), deepcopy(state.officers), deepcopy(state.soldiers)
            self.assertEqual(conditions.advance_daily(state, battle), [])
            self.assertEqual(battle, before)
            self.assertEqual(state.officers, officers)
            self.assertEqual(state.soldiers, soldiers)
            self.assertEqual(state.rng.draws, 0)

    def test_legacy_low_only_days_never_create_high_feature_or_touch_source_growth(self):
        state, battle = context()
        state.officers[1].experience, state.officers[1].tier = 2000, 0
        before = deepcopy(battle)
        self.assertIsNone(conditions.view(battle))
        self.assertEqual(conditions.qimen_source(state, battle), 1)
        self.assertEqual(battle, before)
        conditions.apply(battle, 2, 'attackers')
        conditions.apply_chain(battle, 4, 'attackers', 0)
        self.assertEqual(set(conditions.view(battle)), {'schema', 'day', 'units'})
        next_day(state, battle)
        self.assertEqual((conditions.remaining(battle, 2), conditions.remaining(battle, 4)), (2, 3))
        self.assertNotIn('high_order', conditions.view(battle))
        self.assertEqual((state.officers[1].experience, state.officers[1].tier), (2000, 0))
        self.assertEqual(state.rng.draws, 0)

    def test_high_order_and_kind_boundaries_fail_closed_without_read_mutation(self):
        _, original = context()
        conditions.apply_qimen(original, 2, 'attackers', 3)
        invalid_orders = (None, (), {}, [], ['2', '4', '1', '3', STAFF, '2'],
            ['2', '4', '1', '3'], ['2', '4', '01', '3', STAFF],
            ['2', '4', 1, '3', STAFF], ['2', '4', True, '3', STAFF],
            ['2', '4', [], '3', STAFF], ['2', '4', 'foreign', '3', STAFF])
        for order in invalid_orders:
            battle = deepcopy(original)
            battle['extended']['conditions']['high_order'] = order
            before = deepcopy(battle)
            with self.assertRaises(ValueError): conditions.validate(battle)
            self.assertEqual(battle, before)
        for count in (1, 5, 9):
            battle = deepcopy(original)
            battle['extended']['conditions']['units']['2']['remaining'] = count
            conditions.validate(battle)
        for count in (0, 10, True, 1.0, '1'):
            battle = deepcopy(original)
            battle['extended']['conditions']['units']['2']['remaining'] = count
            with self.assertRaises(ValueError): conditions.validate(battle)
        battle = deepcopy(original)
        del battle['extended']['conditions']['high_order']
        with self.assertRaises(ValueError): conditions.validate(battle)
        for condition_kind, count in (('phantom', 4), ('chain', 6), ('unknown', 1)):
            battle = deepcopy(original)
            battle['extended']['conditions']['units']['2'] = dict(kind=condition_kind, remaining=count)
            with self.assertRaises(ValueError): conditions.validate(battle)

    def test_order_survives_pure_snapshot_and_json_reload_with_identical_continuation(self):
        state, battle = context([70, 0])
        conditions.apply_qimen(battle, 2, 'attackers', 3)
        conditions.apply_qimen(battle, 4, 'attackers', 0)
        conditions.apply(battle, STAFF, 'defenders')
        saved = deepcopy(battle)
        view = conditions.view(battle)
        view['high_order'].reverse()
        view['units']['2']['remaining'] = 1
        self.assertEqual(battle, saved)
        restored_battle, restored_state = json.loads(json.dumps(saved)), deepcopy(state)
        conditions.validate(restored_battle)
        self.assertEqual(next_day(state, battle), next_day(restored_state, restored_battle))
        self.assertEqual(battle, restored_battle)
        self.assertEqual(state.officers, restored_state.officers)
        self.assertEqual(state.rng.draws, restored_state.rng.draws)

    def test_invalid_apply_and_clock_are_atomic_without_optional_order_creation(self):
        for target, side, roll in ((2, 'attackers', 4), (2, 'attackers', True),
                (2, 'wrong', 0), (1, 'attackers', 0), (999, 'attackers', 0)):
            _, battle = context()
            before = deepcopy(battle)
            with self.assertRaises(ValueError): conditions.apply_qimen(battle, target, side, roll)
            self.assertEqual(battle, before)
        state, battle = context()
        conditions.apply_qimen(battle, 2, 'attackers', 0)
        battle['round'] = 3
        before = deepcopy(battle)
        with self.assertRaises(ValueError): conditions.advance_daily(state, battle)
        self.assertEqual(battle, before)
        self.assertEqual(state.rng.draws, 0)


if __name__ == '__main__':
    unittest.main()
