"""The shipped original music is complete and separate from synthesized additions."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalMusicAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'game/assets/audio/index.json').read_text())

    def test_all_four_scene_assets_match_manifest_and_decode_contract(self):
        data = self.manifest
        self.assertEqual(data['schema'], 'tk2-original-audio-v1')
        self.assertEqual(set(data['tracks']), {'menu', 'strategy', 'battle', 'duel'})
        self.assertEqual(data['AV']['sample_rate'], 48000)
        for scene, row in data['tracks'].items():
            with self.subTest(scene=scene):
                slug = 'title' if scene == 'menu' else scene
                self.assertEqual(row['path'], f'/assets/audio/original/{slug}.mp3')
                path = ROOT / 'game' / row['path'].lstrip('/')
                raw = path.read_bytes()
                self.assertEqual(len(raw), row['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
                self.assertTrue(raw.startswith(b'ID3') or raw[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'))
                self.assertEqual(row['channels'], 2)
                self.assertEqual(row['sample_rate'], 48000)
                self.assertTrue(math.isfinite(row['duration']) and 20 < row['duration'] < 120)
                self.assertEqual(row['loop_start'], 0)
                self.assertEqual(row['loop_end'], row['duration'])
                self.assertAlmostEqual(row['duration'], row['provenance']['stereo_sample_frames'] / 48000)

    def test_original_identity_and_repeat_capture_evidence_are_explicit(self):
        data = self.manifest
        self.assertEqual(data['rom_sha256'], '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82')
        self.assertEqual(data['core']['name'], 'Nestopia')
        requests = {'menu': (0xB0, 7), 'strategy': (0x81, 7), 'battle': (0x1D, 7), 'duel': (0x12, 6)}
        for scene, row in data['tracks'].items():
            with self.subTest(scene=scene):
                self.assertEqual(row['kind'], 'original_rom_capture')
                self.assertEqual((row['request']['id'], row['request']['descriptor_count']), requests[scene])
                proof = row['provenance']
                self.assertFalse(proof['rom_modified'])
                self.assertFalse(proof['core_memory_modified'])
                self.assertEqual(proof['controller_inputs'], [])
                self.assertTrue(proof['whole_period_state_comparison'])
                self.assertIn('07F9 & 0F', proof['key_fields'], 'Vibrato phase is part of the music loop')
                self.assertEqual(len(proof['repeat_original_pcm_sha256']), 2)
                self.assertEqual(*proof['repeat_original_pcm_sha256'])
                self.assertEqual(proof['source_loop_frames'][1] - proof['source_loop_frames'][0], proof['period_frames'])
                self.assertEqual(proof['seam_fade_ms'], 4)
        self.assertIn('original rights', data['rights'])

    def test_offline_tool_is_pinned_and_runtime_does_not_import_it(self):
        tool = ROOT / 'tools/audio/capture_original.py'
        self.assertEqual(hashlib.sha256(tool.read_bytes()).hexdigest(), self.manifest['tool_sha256'])
        self.assertNotIn('recovered.', tool.read_text())
        server = (ROOT / 'game/serve.py').read_text()
        for row in self.manifest['tracks'].values():
            self.assertIn(repr(row['path']), server)
        self.assertNotIn('capture_original', server)
        self.assertFalse(any((ROOT / 'game/assets/audio').rglob('*.nes')))
        self.assertFalse(any((ROOT / 'game/assets/audio').rglob('*.state')))


if __name__ == '__main__':
    unittest.main()
