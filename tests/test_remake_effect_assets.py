"""Original one-shot PCM, isolation evidence and authored UI assignments."""
import array
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]


class OriginalEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/assets/audio/effects.json').read_text())

    def test_shipped_pcm_and_allowlist_match_every_original_binding(self):
        spec = importlib.util.spec_from_file_location('effects_static_server', ROOT / 'game/serve.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        routes = module.audio_effect_static_assets()
        assets = {row['path']: row for row in self.data['effects'].values()}
        self.assertEqual(set(assets), set(routes))
        self.assertEqual(len(assets), 13)
        for path, row in assets.items():
            with self.subTest(path=path):
                raw = (ROOT / 'game' / routes[path][0]).read_bytes()
                self.assertEqual(routes[path][1], 'audio/wav')
                self.assertEqual(len(raw), row['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
                with wave.open(io.BytesIO(raw)) as stream:
                    self.assertEqual((stream.getnchannels(), stream.getsampwidth(), stream.getframerate()), (2, 2, 48000))
                    self.assertAlmostEqual(stream.getnframes() / 48000, row['duration'])
                    pcm = stream.readframes(stream.getnframes())
                self.assertEqual(hashlib.sha256(pcm).hexdigest(), row['provenance']['exported_pcm_sha256'])
                values = array.array('h', pcm)
                if sys.byteorder != 'little':
                    values.byteswap()
                self.assertGreater(max(map(abs, values)), 100)
                self.assertTrue(.05 < row['duration'] < 5)
                self.assertFalse(row['provenance']['source_loop'])

    def test_isolated_original_driver_proof_does_not_claim_natural_input(self):
        self.assertEqual(self.data['schema'], 'tk2-original-effects-v1')
        self.assertEqual(self.data['rom_sha256'], '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82')
        required = {'click', 'confirm', 'cancel', 'attack', 'tactic_88', 'tactic_8d', 'tactic_91', 'tactic_95',
                    'duel_start', 'duel_refused', 'duel_strike', 'duel_guard', 'duel_feint', 'duel_withdraw'}
        self.assertTrue(required <= self.data['effects'].keys())
        for key, row in self.data['effects'].items():
            with self.subTest(key=key):
                proof = row['provenance']
                self.assertEqual(row['kind'], 'original_rom_capture')
                self.assertEqual(proof['capture_kind'], 'isolated_original_driver_fixture')
                self.assertTrue(proof['not_natural_gameplay'])
                self.assertFalse(proof['rom_modified'])
                self.assertFalse(proof['emulator_code_modified'])
                self.assertEqual(proof['cpu_registers']['pc'], proof['ram_caller_address'])
                self.assertEqual(proof['original_reset'], 0xE57F)
                self.assertEqual(proof['warmup_original_nmi_ticks'], 180)
                self.assertLessEqual(proof['pre_cue_silence_peak_int16'], 1)
                self.assertTrue(proof['only_requested_slots_active'])
                self.assertEqual(len(proof['requested_slot_offsets']), row['request']['descriptor_count'])
                self.assertEqual(*proof['repeat_full_pcm_sha256'])
                self.assertEqual(*proof['repeat_frame_trace_sha256'])
                self.assertIn(row['adoption_kind'], {'original_context', 'authorial_ui_reuse'})
        for key in ['click', 'cancel', 'duel_strike', 'victory', 'defeat']:
            self.assertEqual(self.data['effects'][key]['adoption_kind'], 'authorial_ui_reuse')
        self.assertNotIn('turn', self.data['effects'], 'The web-only ten-day transition has an authored fallback')

    def test_original_tactic_tables_reproduce_all16_bindings(self):
        tables = {}
        for row in self.data['original_tactic_tables']:
            raw = bytes.fromhex(row['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            tables[row['name']] = raw
        expected = [tables['tactic_visual_to_sound'][visual // 2] for visual in tables['tactic_id_to_visual']]
        self.assertEqual(len(expected), 16)
        self.assertEqual(expected, self.data['tactic_index_sequence_ids'])
        for sequence in expected:
            self.assertEqual(self.data['effects'][f'tactic_{sequence:02x}']['request']['id'], sequence)

    def test_offline_capture_tools_remain_pinned_and_separate_from_game(self):
        tool = ROOT / 'tools/audio/capture_effects.py'
        recorder = ROOT / 'tools/audio/capture_original.py'
        self.assertEqual(hashlib.sha256(tool.read_bytes()).hexdigest(), self.data['tool_sha256'])
        self.assertEqual(hashlib.sha256(recorder.read_bytes()).hexdigest(), self.data['recorder_sha256'])
        self.assertNotIn('recovered.', tool.read_text())
        self.assertNotIn('capture_effects', (ROOT / 'game/serve.py').read_text())


if __name__ == '__main__':
    unittest.main()
