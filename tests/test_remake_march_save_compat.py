"""Real eight-case save/RNG baselines and cross-backend campaign compatibility.

The large arithmetic/vector ABI matrix stays in test_remake_march_core.py.
No checksum fields or historical baseline hashes are normalized.
"""
from copy import deepcopy
import json
import unittest
from test_remake_march_core import (ROOT, CASES, HeadlessCampaign as Campaign, Catalog, canonical,
    campaign_result, using_backend)
import test_remake_march_core as matrix

class MarchReferenceBaselineTests(unittest.TestCase):
    def test_current_python_campaign_save_and_rng_hashes(self):
        expected = json.loads((ROOT / 'tests/fixtures/march-python-baseline.json').read_text())
        with using_backend('python'):
            for case in CASES:
                with self.subTest(case=case[0]):
                    self.assertEqual(canonical(campaign_result(case)), canonical(expected[case[0]]))


class MarchCampaignNativeCompatibilityTests(unittest.TestCase):
    setUpClass = classmethod(matrix.MarchNativeParityTests.setUpClass.__func__)

    def test_three_natural_ai_ten_day_turns_preserve_each_command_state_save_and_rng(self):
        catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')
        reference_game, native_game = Campaign(catalog), Campaign(catalog)
        transcript, phases, saw_march = [], set(), False

        def dispatch(kind, payload):
            nonlocal saw_march
            with using_backend('python'):
                reference_game.command(kind, deepcopy(payload), reference_game.revision)
                expected_state = canonical(reference_game.to_dict())
                expected_save = canonical(reference_game.export_save())
            with using_backend('rust'):
                native_game.command(kind, deepcopy(payload), native_game.revision)
                actual_state = canonical(native_game.to_dict())
                actual_save = canonical(native_game.export_save())
            transcript.append((kind, payload))
            label = f'command{len(transcript)}: {kind} {payload}'
            self.assertEqual(actual_state, expected_state, label)
            self.assertEqual(actual_save, expected_save, label)
            self.assertEqual(native_game.revision, reference_game.revision, label)
            self.assertEqual(native_game.journal, reference_game.journal, label)
            self.assertEqual((native_game.state.rng.state, native_game.state.rng.draws),
                             (reference_game.state.rng.state, reference_game.state.rng.draws), label)
            saw_march |= bool(reference_game.state.extension['travel']['marches'])

        dispatch('new', dict(faction='wu', seed=2026))
        for _ in range(100):
            state = reference_game.state
            phases.add(state.phase)
            if state.turn >= 4 and state.phase == 'city':
                break
            if state.phase == 'city':
                kind, payload = 'end_turn', {}
            elif state.phase == 'ai':
                kind, payload = 'ai', {'turn': state.turn}
            elif state.phase == 'arrivals':
                kind, payload = 'arrivals', {}
            elif state.phase == 'battle':
                kind, payload = 'retreat', {'battle_id': state.battle['id']}
            elif state.phase == 'result':
                kind, payload = 'settle', {'battle_id': state.battle['id']}
            else:
                self.fail(f'Unexpected natural replay phase: {state.phase}; commands={transcript}')
            dispatch(kind, payload)
        else:
            self.fail(f'Natural AI replay exceeded100commands: {transcript}')
        self.assertEqual((reference_game.state.year, reference_game.state.month, reference_game.state.day), (217, 8, 1))
        self.assertTrue({'ai', 'arrivals'} <= phases)
        self.assertTrue(saw_march, 'Natural AI must queue a real march')
        self.assertGreater(reference_game.state.rng.draws, 0)

    def test_full_campaigns_and_cross_backend_pending_save_loads_match_reference(self):
        expected = json.loads((ROOT / 'tests/fixtures/march-python-baseline.json').read_text())
        for backend, alternate in (('rust', 'python'), ('python', 'rust')):
            with using_backend(backend):
                for case in CASES:
                    with self.subTest(backend=backend, case=case[0]):
                        self.assertEqual(canonical(campaign_result(case, alternate)), canonical(expected[case[0]]))


if __name__ == '__main__':
    unittest.main()
