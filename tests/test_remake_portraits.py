"""Native portrait assets, exact identity evidence and reproducible provenance."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('portrait_builder', ROOT / 'game/build_portrait_manifest.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def read(path):
    return json.loads((ROOT / path).read_text())


class PortraitIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = builder.identities()
        cls.mapping = read('game/config/portrait-identity-map.json')
        cls.records = {p['original_id']: p for p in cls.mapping['records']}
        cls.originals = read('game/config/portrait-originals.json')

    def test_all_237_name_records_have_original_byte_and_image_evidence(self):
        self.assertEqual(set(self.records), set(range(237)))
        evidence = self.mapping['evidence']
        self.assertTrue(evidence['numeric_ids_are_authored'])
        self.assertEqual(builder.sha((ROOT / 'game' / evidence['path'].lstrip('/')).read_bytes()), evidence['sha256'])
        bound = []
        for original_id, row in self.records.items():
            with self.subTest(original_id=original_id):
                proof = row['evidence']
                raw = bytes.fromhex(proof['name_glyph_record_hex'])
                self.assertEqual(len(raw), 13)
                self.assertEqual(builder.sha(raw), proof['rom_name_record_sha256'])
                self.assertEqual(proof['name_glyph_atlas'], evidence['path'])
                self.assertEqual(proof['name_glyph_atlas_cell'], [original_id % 16 * 64, original_id // 16 * 32, 64, 32])
                self.assertEqual(proof['rom_name_record_offset'], 142788 + 13 * original_id)
                self.assertTrue(row['transcribed_name'])
                if row['person_id'] is not None:
                    self.assertIn(row['person_id'], self.people)
                    self.assertEqual(row['status'], 'manual_name_glyph_match')
                    bound.append(row['person_id'])
        self.assertEqual(len(bound), len(set(bound)))
        self.assertEqual(len(bound), 220)
        self.assertEqual(len(self.people) - len(bound), 803)

    def test_independently_reviewed_names_do_not_bind_similar_people(self):
        self.assertEqual(self.records[108]['transcribed_name'], '諸葛瞻')
        self.assertEqual(self.records[108]['person_id'], 'san14-candidate-0437')
        self.assertEqual(self.records[137]['transcribed_name'], '孫権')
        self.assertEqual(self.records[137]['person_id'], 'san14-candidate-0553')
        self.assertEqual(self.records[217]['person_id'], 'san14-candidate-0914')
        self.assertEqual(self.records[223]['transcribed_name'], '留平')
        self.assertEqual(self.records[223]['person_id'], 'san14-candidate-0957')
        pending = {11, 39, 40, 53, 60, 62, 83, 84, 105, 115, 148, 152, 172, 195, 209, 215, 236}
        self.assertEqual({k for k, row in self.records.items() if row['person_id'] is None}, pending)
        # The two current Zhang Nan records must not be collapsed into one ROM ID.
        self.assertEqual(self.records[152]['transcribed_name'], '張南')
        self.assertIsNone(self.records[152]['person_id'])
        self.assertNotEqual(self.people['san14-candidate-0651']['runtime_id'], self.people['san14-candidate-0652']['runtime_id'])
        bound = {r['person_id'] for r in self.records.values()}
        self.assertTrue({'san14-candidate-0433', 'san14-candidate-0544', 'san14-candidate-0651', 'san14-candidate-0652'}.isdisjoint(bound))

    def test_all_originals_archive_native_pixels_and_actual_original_sharing(self):
        originals = self.originals
        self.assertEqual(originals['native_size'], [32, 40])
        self.assertEqual(set(originals['by_original_id']), {str(i) for i in range(237)})
        hashes = set()
        for key, row in originals['by_original_id'].items():
            with self.subTest(original_id=key):
                item, pixels = builder.image_record(row)
                self.assertEqual(item['path'], f'/assets/portraits/original/{int(key):03d}.png')
                self.assertEqual(row['original_id'], int(key))
                self.assertEqual(row['frame'], 0)
                self.assertEqual(len(pixels), 32 * 40 * 4)
                self.assertEqual(sum(bool(pixels[i]) for i in range(3, len(pixels), 4)), row['opaque_pixels'])
                hashes.add(item['rgba_sha256'])
        self.assertEqual(len(hashes), 183)
        witness = originals['palette']['native_witness']
        self.assertEqual(witness['original_id'], 131)
        self.assertEqual(witness['opaque_pixel_mismatches'], 0)
        self.assertEqual(witness['opaque_pixels_compared'], 734)
        self.assertEqual(originals['by_original_id']['131']['rgba_sha256'], '8be0d907b85d3412665e812cc76c550e638c7443e1cf50421e68b06f23a6a64b')


class PortraitReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = builder.build()

    def test_all_1023_people_have_real_assets_and_explicit_provenance(self):
        index = self.index
        self.assertEqual(index['counts'], {
            'people': 1023, 'nes_original': 220, 'generated': 803, 'original_archive': 237,
            'original_unique_pixels': 183, 'bound_original_unique_pixels': 179,
            'generated_unique_pixels': 803, 'original_identity_pending': 17})
        self.assertEqual(set(index['people']), set(builder.identities()))
        self.assertEqual(set(index['by_runtime_id']), {str(i) for i in range(1024)} - {'1005'})
        self.assertEqual((index['width'], index['height']), (32, 40))
        for person_id, row in index['people'].items():
            with self.subTest(person_id=person_id):
                self.assertTrue((ROOT / 'game' / row['path'].lstrip('/')).is_file())
                if row['kind'] == 'generated':
                    self.assertEqual(row['path'], f'/assets/portraits/generated/{person_id}.png')
                    self.assertIsNone(row['original_id'])
                    self.assertEqual(row['source'], 'imagegen_new_pixel_art')
                    self.assertEqual(row['art_direction_basis'], 'authorial_game_art_not_historical_likeness')
                else:
                    self.assertEqual(row['source'], 'pinned_ROM_static_frame0')
                    self.assertIn(row['original_id'], range(237))

    def test_rebuilding_is_deterministic_and_does_not_mutate_campaign_catalogs(self):
        index_path = ROOT / 'game/assets/portraits/index.json'
        self.assertEqual(index_path.read_bytes(), (json.dumps(self.index, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
        catalogs = read('game/data/campaigns/index.json')['catalogs']
        before = {p: builder.sha((ROOT / 'game/data' / p).read_bytes()) for p in catalogs}
        self.assertEqual(builder.build(), self.index)
        after = {p: builder.sha((ROOT / 'game/data' / p).read_bytes()) for p in catalogs}
        self.assertEqual(after, before)

    def test_incomplete_or_misrepresented_new_art_cannot_publish_a_manifest(self):
        original_read = builder.read
        source = original_read('game/config/portrait-generated.json')
        first = next(iter(source['by_person_id']))
        second = list(source['by_person_id'])[1]

        def fail_with(change, message):
            bad = deepcopy(source)
            change(bad)
            def modified(path):
                return bad if path == 'game/config/portrait-generated.json' else original_read(path)
            with patch.object(builder, 'read', side_effect=modified):
                with self.assertRaisesRegex(ValueError, message):
                    builder.build()

        fail_with(lambda data: data['by_person_id'].pop(first), 'coverage')
        fail_with(lambda data: data['by_person_id'][first].update(source='original_NES_art'), 'provenance')
        fail_with(lambda data: data['by_person_id'][first].update(png_sha256='0' * 64), 'hash mismatch')
        fail_with(lambda data: data['by_person_id'][first].update(source_atlas='../untrusted.png'), 'Invalid art source')
        fail_with(lambda data: data['by_person_id'][first].update(source_atlas_sha256='0' * 64), 'atlas hash mismatch')
        def duplicate_cell(data):
            for key in ('source_atlas', 'source_atlas_sha256', 'cell_index'):
                data['by_person_id'][second][key] = data['by_person_id'][first][key]
        fail_with(duplicate_cell, 'source cell is assigned to more than one person')


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def filtered_png(filter_kind):
    """An independently encoded gradient exercises all standard PNG row filters."""
    width, height, channels = 32, 40, 4
    pixels = bytes((x * 3 + y * 7 + c * 47) % 256 for y in range(height) for x in range(width) for c in range(channels))
    stride, encoded, previous = width * channels, bytearray(), bytes(width * channels)
    for y in range(height):
        row = pixels[y * stride:(y + 1) * stride]
        encoded.append(filter_kind)
        for i, value in enumerate(row):
            left = row[i - channels] if i >= channels else 0
            up, corner = previous[i], previous[i - channels] if i >= channels else 0
            if filter_kind == 0:
                predictor = 0
            elif filter_kind == 1:
                predictor = left
            elif filter_kind == 2:
                predictor = up
            elif filter_kind == 3:
                predictor = (left + up) // 2
            else:
                prediction = left + up - corner
                predictor = min((left, up, corner), key=lambda v: abs(prediction - v))
            encoded.append((value - predictor) % 256)
        previous = row
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    raw = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) + png_chunk(b'IDAT', zlib.compress(encoded)) + png_chunk(b'IEND', b'')
    return raw, pixels


class PortraitIntegrityTests(unittest.TestCase):
    def test_supported_png_filter_encodings_produce_identical_native_pixels(self):
        for kind in range(5):
            with self.subTest(png_filter=kind):
                raw, pixels = filtered_png(kind)
                size, decoded = builder.png_pixels(raw)
                self.assertEqual(size, (32, 40))
                self.assertEqual(decoded, pixels)

    def test_asset_paths_and_png_corruption_fail_closed(self):
        row = read('game/config/portrait-originals.json')['by_original_id']['131']
        for path in ('https://invalid.example/a.png', '/assets/portraits/original/../131.png', '/assets/portraits/generated/a.svg', '/assets/portraits/generated/a.png?x=1'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'asset path'):
                builder.image_record(dict(row, path=path))
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            builder.image_record(dict(row, rgba_sha256='0' * 64))
        raw, _ = filtered_png(0)
        corrupt = bytearray(raw)
        corrupt[45] ^= 1
        with self.assertRaisesRegex(ValueError, 'CRC mismatch'):
            builder.png_pixels(corrupt)
        for invalid in (raw[:-1], raw + b'extra', b'not a png'):
            with self.subTest(invalid=invalid[:16]), self.assertRaises(ValueError):
                builder.png_pixels(invalid)


if __name__ == '__main__':
    unittest.main()
