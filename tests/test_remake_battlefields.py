"""Real original city layouts, native pixels and offline-source boundaries."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('original_battlefields', ROOT / 'tools/battlefields/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class OriginalBattlefieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/assets/battlefields/index.json').read_text())

    def test_offline_checker_reconstructs_all_thirty_distinct_native_layouts(self):
        result = builder.check()
        self.assertEqual(result, dict(maps=30, unique_layouts=30, grid=[31, 19],
                                     native_pixels_verified=120832, observed_nes_colors=6,
                                     checker_requires_rom=False))
        self.assertEqual({p.name for p in builder.OUT.glob('*.png')},
                         {f'original-{i:02d}.png' for i in range(30)})
        self.assertFalse(self.data['build']['runtime_requires_rom'])
        self.assertFalse(self.data['build']['runtime_requires_archive'])
        self.assertFalse(self.data['build']['runtime_requires_emulator'])
        self.assertNotIn('from PIL', (ROOT / 'tools/battlefields/build.py').read_text())

    def test_attribute_row_is_skipped_and_markers_do_not_become_new_terrains(self):
        seen = set()
        for row in self.data['maps'].values():
            self.assertEqual(len(row['camps']), 1)
            for marker in row['markers'] + row['camps']:
                x, y = marker['x'], marker['y']
                self.assertEqual(marker['packed_y'], y if y < 15 else y + 1)
                self.assertNotEqual(marker['packed_y'], 15)
                self.assertEqual(row['tiles'][y][x], marker['raw_tile'])
                self.assertEqual(row['raw_classes'][y][x], marker['raw_class'])
                if marker['raw_class'] >= 6:
                    seen.add(marker['raw_class'])
                    self.assertEqual(row['classes'][y][x], 2)
            self.assertTrue(all(0 <= n <= 5 for line in row['classes'] for n in line))
        self.assertEqual(seen, {6, 7, 8})
        # The lowest original camp is below the skipped attribute row; exporting
        # a naive contiguous 19 rows would move/drop this confirmed native tile.
        self.assertEqual(self.data['maps']['original-29']['camps'][0]['packed_y'], 17)
        self.assertEqual(self.data['maps']['original-29']['camps'][0]['y'], 16)

    def test_original_witnesses_are_honest_fixture_captures_and_cover_every_color(self):
        proof = self.data['native_verification']
        self.assertEqual([w['original_city_index'] for w in proof['witnesses']], [5, 6, 9])
        self.assertEqual([w['verification']['checked_pixels'] for w in proof['witnesses']], [40704, 39680, 40448])
        observed = set()
        for witness in proof['witnesses']:
            self.assertFalse(witness['natural_gameplay'])
            self.assertTrue(witness['original_rom_unmodified'])
            self.assertTrue(witness['fixture_ram_changes'])
            self.assertEqual(witness['upper_map_bg_chr_pages'], [139, 137, 138, 136])
            observed.update(witness['verification']['observed_nes_color_pixels'])
        self.assertEqual(observed, set(self.data['decoder']['nes_to_rgba']))
        # Labels are preserved from a guide, not advertised as ROM-glyph proof.
        for row in self.data['maps'].values():
            self.assertIn('not a ROM-glyph-certified', row['provenance']['label_identity'])

    def test_tampered_native_palette_attribute_and_pixel_are_rejected(self):
        witness = deepcopy(self.data['native_verification']['witnesses'][2])
        screenshot = (ROOT / witness['screenshot']).read_bytes()
        decoder = self.data['decoder']
        # A changed native nametable attribute cannot be accepted merely because
        # the CHR tile IDs still match. Background palette selectors are checked.
        nmt = bytearray.fromhex(witness['ppu']['nametable']['hex'])
        nmt[960] ^= 3
        witness['ppu']['nametable']['hex'] = nmt.hex()
        with self.assertRaisesRegex(ValueError, 'attribute selector mismatch'):
            builder.verify_witness(decoder, self.data['maps'], witness, screenshot)
        witness = deepcopy(self.data['native_verification']['witnesses'][2])
        pixels = bytearray(builder.png_pixels(screenshot, (256, 240)))
        pixels[:256 * 160 * 4] = bytes((255, 255, 255, 255)) * (256 * 160)
        forged = builder.png_bytes(bytes(pixels), 256, 240)
        witness['screenshot_sha256'] = builder.sha(forged)
        with self.assertRaisesRegex(ValueError, 'Native pixel mismatch'):
            builder.verify_witness(decoder, self.data['maps'], witness, forged)

    def test_modified_layout_cannot_pass_with_a_new_png_hash(self):
        modified = deepcopy(self.data)
        modified['maps']['original-00']['tiles'][0][0] ^= 1
        with self.assertRaisesRegex(ValueError, 'Map differs from native source chunk'):
            builder.validate(modified, lambda path: b'', lambda path: b'')

    def test_wrong_rom_is_rejected_before_archive_access_or_output(self):
        manifest = (builder.OUT / 'index.json').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'wrong.nes'
            source.write_bytes(b'unrelated source')
            with self.assertRaisesRegex(ValueError, 'Pinned user ROM does not match'):
                builder.build(source, Path(temp) / 'missing-archive')
        self.assertEqual((builder.OUT / 'index.json').read_bytes(), manifest)


if __name__ == '__main__':
    unittest.main()
