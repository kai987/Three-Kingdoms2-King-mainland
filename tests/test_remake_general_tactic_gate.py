"""B7BE thresholds against independent unchanged-ROM CPU observations.

The literal witnesses were collected on 2026-11-06 from the pinned ROM
26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82.
CI neither reads the ROM/Research Archive nor imports a CPU emulator. Original
AI difficulty bonuses and one byte-domain100 probe remain explicitly distinct
from the remake's shared human-bonus10, intellect0..99 contract.
"""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from remake import tactic_effects
from remake.campaign import SeedRng


# name, actorI,targetI,actorTier,targetTier,distance,originalBonus,
# original threshold (None means no sampling), migrated threshold.
# These37 expectations are original CPU outputs, not production-generated
# values. The two original AI-only bonuses intentionally map to fixed10 here;
# the100-stat helper probe is outside the modern profile domain and is rejected.
CPU_VECTORS = (
    ('equal_d0', 60, 60, 0, 0, 0, 10, 25, 25),
    ('equal_d1', 60, 60, 0, 0, 1, 10, 20, 20),
    ('equal_d2', 60, 60, 0, 0, 2, 10, 15, 15),
    ('equal_d3', 60, 60, 0, 0, 3, 10, 10, 10),
    ('equal_d4', 60, 60, 0, 0, 4, 10, 5, 5),
    ('equal_d5', 60, 60, 0, 0, 5, 10, 5, 5),
    ('equal_d6', 60, 60, 0, 0, 6, 10, None, 0),
    ('diagonal_max_axis', 60, 60, 0, 0, 4, 10, 5, 5),
    ('packed14_to16', 60, 60, 0, 0, 1, 10, 20, 20),
    ('packed14_to17', 60, 60, 0, 0, 2, 10, 15, 15),
    ('negative_gaps', 10, 99, 0, 7, 1, 10, 20, 20),
    ('knowledge_only', 80, 60, 0, 7, 2, 10, 35, 35),
    ('level_only', 10, 99, 7, 0, 1, 10, 34, 34),
    ('signed127', 99, 0, 4, 0, 1, 10, 95, 95),
    ('signed128', 98, 0, 5, 0, 1, 10, 5, 5),
    ('signed129', 99, 0, 5, 0, 1, 10, 5, 5),
    ('signed133', 99, 0, 7, 0, 1, 10, 5, 5),
    ('source_stat100', 100, 0, 7, 0, 1, 10, 5, None),
    ('negative_table_final_sign_only', 99, 0, 7, 0, 4, 10, 95, 95),
    ('controller0_level1', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller0_level2', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller0_level3', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller1_level1', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller1_level2', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller1_level3', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller2_level1', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller2_level2', 80, 60, 2, 0, 2, 10, 39, 39),
    ('controller2_level3', 80, 60, 2, 0, 2, 10, 39, 39),
    ('original_AI_level1_shared_bonus', 80, 60, 2, 0, 2, 5, 34, 39),
    ('original_AI_level2_shared_bonus', 80, 60, 2, 0, 2, 10, 39, 39),
    ('original_AI_level3_shared_bonus', 80, 60, 2, 0, 2, 20, 49, 39),
    ('sample4_threshold5', 60, 60, 0, 0, 5, 10, 5, 5),
    ('sample5_threshold5', 60, 60, 0, 0, 5, 10, 5, 5),
    ('sample19_threshold20', 60, 60, 0, 0, 1, 10, 20, 20),
    ('sample20_threshold20', 60, 60, 0, 0, 1, 10, 20, 20),
    ('sample94_threshold95', 99, 0, 4, 0, 1, 10, 95, 95),
    ('sample95_threshold95', 99, 0, 4, 0, 1, 10, 95, 95),
)


def officer(intellect=60, tier=0, *, experience=0):
    return SimpleNamespace(profile=SimpleNamespace(intellect=intellect, virtue=70),
                           tier=tier, experience=experience, loyalty=60)


def context(actor_id=1, target_id=2, *, actor_point=(10, 14), target_point=(10, 15)):
    """Minimal read-only quote context; no battle initialization or command."""
    actor, target = dict(id=actor_id, troops=500), dict(id=target_id, troops=500)
    state = SimpleNamespace(officers={actor_id:officer(), target_id:officer()},
                            rng=SeedRng(381), extension={'difficulty':'normal'})
    battle = dict(attackers=[actor], defenders=[target], round=1, outcome=None,
                  extended={'tactical':{'positions':{
                      str(actor_id):dict(zip(('x', 'y'), actor_point)),
                      str(target_id):dict(zip(('x', 'y'), target_point))}}})
    return state, battle, actor, target


class GeneralTacticGateTests(unittest.TestCase):
    def test_independent_original_cpu_vectors_and_explicit_shared_rule_exceptions(self):
        self.assertEqual(len(CPU_VECTORS), 37)
        exceptions = []
        for name, ai, ti, al, tl, distance, source_bonus, source, expected in CPU_VECTORS:
            with self.subTest(witness=name):
                args = ai, ti, al, tl, distance
                if expected is None:
                    with self.assertRaises(ValueError):
                        tactic_effects.general_threshold(*args)
                    exceptions.append(name)
                else:
                    self.assertEqual(tactic_effects.general_threshold(*args), expected)
                    if source is not None and source_bonus == 10:
                        self.assertEqual(expected, source)
                    elif source_bonus != 10:
                        exceptions.append(name)
        self.assertEqual(exceptions, ['source_stat100', 'original_AI_level1_shared_bonus',
                                      'original_AI_level3_shared_bonus'])

    def test_final_signed_byte_boundary_is_not_an_ordinary_clamp95(self):
        # Actor tier7 against tier0. Adjacent knowledge93 gives127;94 gives128.
        # Different distances move that discontinuity. Expectations are literal.
        for args, expected in (
            ((88, 0, 7, 0, 0), 95), ((89, 0, 7, 0, 0), 5),
            ((93, 0, 7, 0, 1), 95), ((94, 0, 7, 0, 1), 5),
            ((98, 0, 7, 0, 2), 95), ((99, 0, 7, 0, 2), 5),
            ((99, 0, 7, 0, 3), 95), ((99, 0, 7, 0, 4), 95),
            ((99, 0, 7, 0, 5), 95), ((0, 99, 0, 7, 4), 5),
        ):
            with self.subTest(args=args):
                self.assertEqual(tactic_effects.general_threshold(*args), expected)

    def test_negative_stat_and_tier_gaps_do_not_reduce_the_other_positive_bonus(self):
        for args, expected in (
            ((0, 99, 0, 7, 1), 20), ((0, 0, 0, 0, 1), 20),
            ((80, 60, 0, 7, 2), 35), ((80, 60, 7, 7, 2), 35),
            ((0, 99, 7, 0, 2), 29), ((99, 99, 7, 0, 2), 29),
            ((99, 0, 0, 7, 5), 95), ((0, 99, 0, 7, 5), 5),
        ):
            self.assertEqual(tactic_effects.general_threshold(*args), expected)

    def test_all_valid_distance_bytes_keep_range_six_and_above_at_zero(self):
        self.assertEqual([tactic_effects.general_threshold(60, 60, 0, 0, d)
                          for d in range(6)], [25, 20, 15, 10, 5, 5])
        for distance in range(6, 256):
            for ai, ti, al, tl in ((0, 99, 0, 7), (99, 0, 7, 0)):
                with self.subTest(distance=distance):
                    self.assertEqual(tactic_effects.general_threshold(ai, ti, al, tl, distance), 0)

    def test_every_scalar_is_strictly_bounded_even_on_an_out_of_range_target(self):
        valid = [60, 40, 2, 1, 1]
        bounds = ((0, 99), (0, 99), (0, 7), (0, 7), (0, 255))
        for index, (low, high) in enumerate(bounds):
            for value in (low, high):
                args = valid.copy(); args[index] = value
                self.assertIs(type(tactic_effects.general_threshold(*args)), int)
            for value in (low-1, high+1, True, False, None, '1', 1.0, [], {}):
                for far in (False, True):
                    args = valid.copy()
                    if far:
                        args[4] = 6
                    args[index] = value
                    with self.subTest(argument=index, value=value, far=far):
                        with self.assertRaises(ValueError):
                            tactic_effects.general_threshold(*args)

    def test_two_argument_and_none_distance_calls_preserve_the_legacy_kernel(self):
        for ai, ti, expected in ((60, 60, 60), (60, 61, 59), (61, 60, 60),
                                 (0, 99, 10), (99, 0, 95)):
            actor, target = officer(ai, 7), officer(ti, 0)
            self.assertEqual(tactic_effects.general_chance(actor, target), expected)
            self.assertEqual(tactic_effects.general_chance(actor, target, distance=None), expected)
        self.assertEqual(tactic_effects.general_chance(officer(), officer(), distance=1), 20)

    def test_explicit_distance_uses_saved_tier_or_existing_experience_fallback(self):
        actor, target = officer(60, None, experience=15000), officer(60, None, experience=0)
        before = deepcopy((actor, target))
        self.assertEqual(tactic_effects.general_chance(actor, target, distance=1), 34)
        # Explicit tier is authoritative even when experience would imply7.
        actor.tier = 0
        self.assertEqual(tactic_effects.general_chance(actor, target, distance=1), 20)
        self.assertEqual(before[1], target)
        self.assertEqual(actor.experience, 15000)
        for value in (True, -1, 256, 1.0, '1'):
            with self.assertRaises(ValueError):
                tactic_effects.general_chance(actor, target, distance=value)

    def test_modern_distance_is_visible_chebyshev_without_removing_a_second_row(self):
        # Original packed14->16 becomes visible14->15, not14->14. Original
        # packed14->17 becomes visible14->16. The quote consumes visible cells.
        for start, end, expected in (
            ((10, 14), (10, 15), 20), ((10, 14), (10, 16), 15),
            ((10, 10), (14, 13), 5), ((10, 10), (15, 15), 5),
            ((10, 10), (16, 10), 0), ((10, 10), (10, 16), 0),
        ):
            with self.subTest(start=start, end=end):
                state, battle, actor, target = context(actor_point=start, target_point=end)
                self.assertEqual(tactic_effects.success_chance(state, battle, actor, target), expected)

    def test_modern_quote_reads_live_positions_not_unit_or_observer_labels(self):
        state, battle, actor, target = context('clerk-000001', 255)
        actor.update(x=0, y=0); target.update(x=30, y=18)
        battle['extended'].update(observer='defenders', source='far-city', target='other-city')
        self.assertEqual(tactic_effects.success_chance(state, battle, actor, target), 20)
        battle['extended']['tactical']['positions']['255'] = dict(x=10, y=16)
        self.assertEqual(tactic_effects.success_chance(state, battle, actor, target), 15)
        state.extension['difficulty'] = 'hard'
        state.officers['clerk-000001'].profile.intellect = 80
        state.officers[255].profile.intellect = 60
        state.officers['clerk-000001'].tier = 2
        self.assertEqual(tactic_effects.success_chance(state, battle, actor, target), 39)

    def test_actual_dispatch_ids_and_generic_previews_share_one_probability(self):
        # The original B02B prefixes reached B7BE for precisely these IDs.
        self.assertEqual(tactic_effects.GENERAL_TACTICS,
                         (0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15))
        state, battle, actor, target = context()
        before = deepcopy((state, battle))
        with patch.object(SeedRng, 'next', side_effect=AssertionError('preview RNG')):
            for tid in (0, 1, 3, 4, 6, 7, 9, 12, 13, 14):
                quote = tactic_effects.preview(state, battle, actor, target,
                                               'attackers', 'defenders', tid)
                self.assertEqual(quote, dict(schema=tactic_effects.SCHEMA, tactic=tid,
                    success_percent=20, success_gate='shared_native', distance=1, shared_bonus=10))
            self.assertIsNone(tactic_effects.preview(state, battle, actor, target,
                                                    'attackers', 'defenders', 11))
            # Conversion keeps its independently recovered loyalty gate,
            # without being decorated as a new common-gate tactic.
            conversion = tactic_effects.preview(state, battle, actor, target,
                                                 'attackers', 'defenders', 8)
            self.assertEqual(conversion['success_percent'], 23)
            self.assertNotIn('success_gate', conversion)
            self.assertNotIn('distance', conversion)
        self.assertEqual((state, battle), before)

    def test_modern_quote_rejects_invalid_visible_coordinates_without_repairing_them(self):
        for axis, invalid in (('x', -1), ('x', 31), ('y', -1), ('y', 19),
                              ('x', True), ('y', False), ('x', 1.0), ('y', '14')):
            state, battle, actor, target = context()
            battle['extended']['tactical']['positions']['2'][axis] = invalid
            before = deepcopy((state, battle))
            with self.subTest(axis=axis, value=invalid):
                with self.assertRaises(ValueError):
                    tactic_effects.success_chance(state, battle, actor, target)
                self.assertEqual((state, battle), before)

    def test_old_battles_do_not_acquire_a_grid_or_new_probability_on_read(self):
        state, battle, actor, target = context()
        battle['extended'].pop('tactical')
        before = deepcopy((state, battle))
        self.assertEqual(tactic_effects.success_chance(state, battle, actor, target), 60)
        self.assertEqual((state, battle), before)
        self.assertNotIn('tactical', battle['extended'])

    def test_preview_and_repeated_quotes_do_not_initialize_state_or_consume_rng(self):
        for modern in (False, True):
            for distance in (1, 6):
                state, battle, actor, target = context(actor_point=(10, 10),
                                                        target_point=(10+distance, 10))
                if not modern:
                    battle['extended'].pop('tactical')
                before = deepcopy((state, battle))
                expected = 60 if not modern else 20 if distance == 1 else 0
                with patch.object(SeedRng, 'next', side_effect=AssertionError('pure quote drew RNG')):
                    for difficulty in ('easy', 'normal', 'hard'):
                        state.extension['difficulty'] = difficulty
                        for _ in range(2):
                            self.assertEqual(tactic_effects.success_chance(state, battle, actor, target), expected)
                            quote = tactic_effects.preview(state, battle, actor, target,
                                                           'attackers', 'defenders', 2)
                            self.assertEqual(quote['success_percent'], expected)
                            self.assertEqual(quote['failure_without_rng'], expected == 0)
                            self.assertEqual(quote['failure_rng_draws'], 0 if expected == 0 else 1)
                            # Returned presentation dictionaries must not alias
                            # current positions or create saved condition rows.
                            quote['success_percent'] = -1
                state.extension['difficulty'] = 'normal'
                self.assertEqual((state, battle), before)
                self.assertNotIn('conditions', battle['extended'])
                self.assertNotIn('supply', battle['extended'])


if __name__ == '__main__':
    unittest.main()
