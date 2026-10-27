"""Native portrait assets, exact identity evidence and reproducible provenance."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
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
        self.assertEqual(len(bound), 221)
        self.assertEqual(len(self.people) - len(bound), 831)

    def test_independently_reviewed_names_do_not_bind_similar_people(self):
        self.assertEqual(self.records[108]['transcribed_name'], '諸葛瞻')
        self.assertEqual(self.records[108]['person_id'], 'san14-candidate-0437')
        self.assertEqual(self.records[137]['transcribed_name'], '孫権')
        self.assertEqual(self.records[137]['person_id'], 'san14-candidate-0553')
        self.assertEqual(self.records[217]['person_id'], 'san14-candidate-0914')
        self.assertEqual(self.records[223]['transcribed_name'], '留平')
        self.assertEqual(self.records[223]['person_id'], 'san14-candidate-0957')
        self.assertEqual(self.records[11]['person_id'], 'historical-wang-jian-liaodong')
        self.assertEqual(self.records[11]['identity_context']['public_table_city_label'], '辽东')
        pending = {39, 40, 53, 60, 62, 83, 84, 105, 115, 148, 152, 172, 195, 209, 215, 236}
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

    def test_all_canonical_people_have_real_assets_and_explicit_provenance(self):
        index = self.index
        self.assertEqual(index['counts'], {
            'people': 1052, 'nes_original': 221, 'generated': 831, 'original_archive': 237,
            'original_unique_pixels': 183, 'bound_original_unique_pixels': 179,
            'generated_unique_pixels': 831, 'original_identity_pending': 16})
        self.assertEqual(set(index['people']), set(builder.identities()))
        self.assertEqual(set(index['by_runtime_id']), {str(i) for i in range(1053)} - {'1005'})
        self.assertEqual((index['width'], index['height']), (32, 40))
        for person_id, row in index['people'].items():
            with self.subTest(person_id=person_id):
                self.assertTrue((ROOT / 'game' / row['path'].lstrip('/')).is_file())
                if row['kind'] == 'generated':
                    self.assertEqual(row['path'], f'/assets/portraits/generated/{person_id}.png')
                    self.assertIsNone(row['original_id'])
                    self.assertEqual(row['source'], 'imagegen_new_pixel_art')
                    self.assertEqual(row['art_direction_basis'], 'authorial_game_art_not_historical_likeness')
                    # All831 additions, including the earlier803 identities,
                    # require the real4x display asset; optional HD support in
                    # the generic parser must not hide a missing released one.
                    enhanced = row['enhanced']
                    expected_size = (index['width'] * 4, index['height'] * 4)
                    self.assertEqual((enhanced['width'], enhanced['height']), expected_size)
                    image_size, _ = builder.png_pixels(
                        (ROOT / 'game' / enhanced['path'].lstrip('/')).read_bytes(), expected_size)
                    self.assertEqual(image_size, (128, 160))
                else:
                    self.assertEqual(row['source'], 'pinned_ROM_static_frame0')
                    self.assertIn(row['original_id'], range(237))

    def test_historical_additions_have_retained_natives_and_real_redrawn_detail(self):
        canonical = read('game/config/campaigns/people.json')
        expected = ['historical-song-jian', 'historical-lu-xing',
                    'historical-tang-pu', 'historical-li-tong-jiaozhi',
                    'historical-beigong-boyu', 'historical-li-wenhou', 'historical-bian-zhang']
        self.assertEqual(canonical['order'][1023:1030], expected)
        self.assertEqual(canonical['order'][1030:],
                         [row['person_id'] for row in read('art/portraits/retainer-additions-v1/plan.json')['people']])
        released = [[pid, canonical['people'][pid]['runtime_id']] for pid in canonical['order'][:1023]]
        self.assertEqual(builder.sha(json.dumps(released, separators=(',', ':')).encode()),
                         '0fb983fdb518092176cd672f32a4c079b6143741b5d6eaee804336b364fdf21d')
        published1027 = [[pid, canonical['people'][pid]['runtime_id']] for pid in canonical['order'][:1027]]
        self.assertEqual(builder.sha(json.dumps(published1027, separators=(',', ':')).encode()),
                         'b54bda62e7fd0ec52a6dc92fec213978827a14067569265d55117c69b22b8c7d')
        published1029 = [[pid, canonical['people'][pid]['runtime_id']] for pid in canonical['order'][:1029]]
        self.assertEqual(builder.sha(json.dumps(published1029, separators=(',', ':')).encode()),
                         'd3300e904f938234f25ca56c2e82e67c97c5f68d99b55533f1671966a7bf385b')
        generated = read('game/config/portrait-generated.json')['by_person_id']
        hd = read('game/config/portrait-enhanced.json')['people']
        legacy = {}
        for batch in ('historical-additions-v1', 'northwest-rising-v1', 'bian-zhang-v1'):
            legacy.update(read(f'art/portraits/{batch}/enhanced-records.json')['people'])
        redraw_plan = read('art/portraits/supplement-hd-v2/plan.json')
        self.assertEqual(redraw_plan['schema'], 'tk2-portrait-redraw-v2')
        self.assertEqual(redraw_plan['size'], [128, 160])
        self.assertEqual(set(redraw_plan['people']), set(expected))
        old_hashes = {row['rgba_sha256'] for pid, row in generated.items() if pid not in expected}
        new_hashes = set()
        for number, pid in enumerate(expected, 1024):
            with self.subTest(person_id=pid):
                person, native_row, enhanced_row = canonical['people'][pid], generated[pid], hd[pid]
                self.assertEqual(person['runtime_id'], number)
                self.assertEqual(person['profile']['source_stats'], {})
                self.assertEqual(person['profile']['virtue'], 60)
                self.assertEqual(person['initialization']['health'], 80)
                self.assertEqual(person['pre_campaign_stat_policy_v1']['checkpoint_kind'],
                                 'new_person_initial_authorial_profile')
                self.assertEqual(person['ability_source']['kind'], 'historical_authorial_game_design')
                self.assertNotIn(native_row['rgba_sha256'], old_hashes | new_hashes)
                new_hashes.add(native_row['rgba_sha256'])
                native = builder.png_pixels((ROOT / 'game' / native_row['path'].lstrip('/')).read_bytes(), (32, 40))[1]
                enlarged = builder.png_pixels((ROOT / 'game' / enhanced_row['path'].lstrip('/')).read_bytes(), (128, 160))[1]
                self.assertEqual(enhanced_row['source_path'], native_row['path'])
                self.assertEqual(enhanced_row['source_sha256'], native_row['png_sha256'])
                provenance = enhanced_row['provenance']
                self.assertEqual(self.index['people'][pid]['enhanced']['rendering'], 'redrawn128')
                self.assertEqual(provenance['base_method'], 'identity_preserving_redrawn128')
                self.assertIs(provenance['qa']['nearest4xExact'], False)
                self.assertEqual(native_row['png_sha256'], legacy[pid]['source_sha256'])
                self.assertEqual(provenance['original_enhanced_sha256'], legacy[pid]['sha256'])
                archived = (ROOT / provenance['original_enhanced']).read_bytes()
                self.assertEqual(builder.sha(archived), legacy[pid]['sha256'])
                binding = redraw_plan['people'][pid]
                self.assertEqual(binding['native']['path'], 'game' + native_row['path'])
                self.assertEqual(binding['native']['sha256'], legacy[pid]['source_sha256'])
                self.assertEqual(binding['native']['rgba_sha256'], native_row['rgba_sha256'])
                self.assertEqual(binding['original_enhanced']['sha256'], legacy[pid]['sha256'])
                for key in ('generated_source', 'prompt', 'redraw_plan'):
                    self.assertEqual(builder.sha((ROOT / provenance[key]).read_bytes()),
                                     provenance[key + '_sha256'])
                self.assertEqual({tuple(native[i:i+4]) for i in range(0, len(native), 4)},
                                 {(0, 0, 0, 0), (255, 255, 255, 255),
                                  (247, 162, 71, 255), (158, 65, 0, 255)})
                different = 0
                palette = {tuple(enlarged[i:i+4]) for i in range(0, len(enlarged), 4)}
                for y in range(160):
                    for x in range(128):
                        at = (y * 128 + x) * 4
                        source_at = ((y // 4) * 32 + x // 4) * 4
                        different += enlarged[at:at+4] != native[source_at:source_at+4]
                self.assertGreaterEqual(different, 1024)
                self.assertGreater(len(palette), 4)
                self.assertLessEqual(len(palette), 16)
                self.assertEqual(provenance['qa']['changedPixels'], different)
                self.assertEqual(provenance['qa']['paletteSize'], len(palette))
                blocks = sum(len({enlarged[((by * 4 + y) * 128 + bx * 4 + x) * 4:
                                          ((by * 4 + y) * 128 + bx * 4 + x) * 4 + 4]
                                  for y in range(4) for x in range(4)}) > 1
                             for by in range(40) for bx in range(32))
                self.assertGreaterEqual(blocks, 20)
                self.assertEqual(provenance['qa']['nonUniformBlocks4x4'], blocks)
                self.assertTrue(all(enlarged[i] in (0, 255) for i in range(3, len(enlarged), 4)))

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

    def test_optional_enhancement_is_merged_without_replacing_primary_records(self):
        config_path = ROOT / builder.ENHANCED_CONFIG
        original_is_file, original_bytes, original_read = Path.is_file, Path.read_bytes, builder.read
        present = False
        person_id = 'san14-candidate-0440'
        variant = {'path': '/assets/portraits/enhanced/' + person_id + '.png', 'width': 128, 'height': 160}
        config, raw = {'fixture': 'optional enhanced manifest'}, b'{"fixture":"optional enhanced manifest"}'

        def exists(path):
            return present if path == config_path else original_is_file(path)

        def contents(path):
            return raw if path == config_path else original_bytes(path)

        def source(path):
            return config if path == builder.ENHANCED_CONFIG else original_read(path)

        with patch.object(Path, 'is_file', new=exists), patch.object(Path, 'read_bytes', new=contents), \
                patch.object(builder, 'read', side_effect=source), \
                patch.object(builder, 'enhanced_records', return_value={person_id: variant}) as validate:
            baseline = builder.build()
            present = True
            enhanced = builder.build()
        self.assertNotIn('portrait-enhanced.json', baseline['sources'])
        self.assertEqual(enhanced['sources']['portrait-enhanced.json'], builder.sha(raw))
        self.assertEqual(enhanced['counts'], baseline['counts'])
        self.assertEqual((enhanced['width'], enhanced['height']), (32, 40))
        self.assertEqual(enhanced['by_runtime_id'], baseline['by_runtime_id'])
        self.assertEqual(enhanced['people'][person_id]['enhanced'], variant)
        for current_id, row in baseline['people'].items():
            expected = dict(row, enhanced=variant) if current_id == person_id else row
            self.assertEqual(enhanced['people'][current_id], expected)
        validate.assert_called_once()
        self.assertIs(validate.call_args.args[0], config)
        self.assertEqual(validate.call_args.args[1][person_id]['path'], baseline['people'][person_id]['path'])


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def solid_png(width, height, rgba):
    pixels = bytes(rgba) * width * height
    stride = width * 4
    scanlines = b''.join(b'\0' + pixels[y * stride:(y + 1) * stride] for y in range(height))
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    raw = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) + png_chunk(b'IDAT', zlib.compress(scanlines)) + png_chunk(b'IEND', b'')
    return raw, pixels


class EnhancedPortraitTests(unittest.TestCase):
    """Derivatives remain optional and tied to the exact original person source."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        root_patch = patch.object(builder, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.person = 'san14-candidate-0440'
        self.other_person = 'san14-candidate-0001'
        native, _ = solid_png(32, 40, (247, 162, 71, 255))
        other_native, _ = solid_png(32, 40, (158, 65, 0, 255))
        self.primary = {
            self.person: {'path': '/assets/portraits/original/109.png', 'png_sha256': builder.sha(native)},
            self.other_person: {'path': '/assets/portraits/generated/' + self.other_person + '.png', 'png_sha256': builder.sha(other_native)},
        }
        for person, content in ((self.person, native), (self.other_person, other_native)):
            source_path = self.root / 'game' / self.primary[person]['path'].lstrip('/')
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(content)
        self.image, self.pixels = solid_png(128, 160, (255, 187, 89, 255))
        self.output_path = self.root / 'game/assets/portraits/enhanced' / (self.person + '.png')
        self.output_path.parent.mkdir(parents=True)
        self.output_path.write_bytes(self.image)
        reference = self.root / builder.ENHANCED_REFERENCE
        reference.parent.mkdir(parents=True)
        reference.write_bytes(self.image)
        self.record = {
            'path': '/assets/portraits/enhanced/' + self.person + '.png', 'width': 128, 'height': 160,
            'source_path': self.primary[self.person]['path'],
            'source_sha256': self.primary[self.person]['png_sha256'],
            'sha256': builder.sha(self.image), 'pixel_sha256': builder.sha(self.pixels),
            'method': 'identity_preserving_pixel_enhancement', 'provenance': {'tool': 'test_color_study'},
        }
        self.data = {
            'schema': 'tk2-enhanced-portraits-v1', 'width': 128, 'height': 160,
            'approved_reference': {'path': builder.ENHANCED_REFERENCE, 'sha256': builder.sha(self.image)},
            'people': {self.person: self.record},
        }

    def bad(self, change, message):
        data = deepcopy(self.data)
        change(data)
        with self.assertRaisesRegex(ValueError, message):
            builder.enhanced_records(data, self.primary)

    def test_partial_and_empty_sets_are_optional_and_do_not_replace_originals(self):
        before = deepcopy(self.primary)
        self.assertEqual(builder.enhanced_records(self.data, self.primary), {
            self.person: {'path': self.record['path'], 'width': 128, 'height': 160}})
        empty = dict(self.data, people={})
        self.assertEqual(builder.enhanced_records(empty, self.primary), {})
        self.assertEqual(self.primary, before)
        self.assertEqual(self.output_path.read_bytes(), self.image)

    def test_invalid_manifest_shape_or_reference_cannot_be_merged(self):
        for invalid in (None, [], {}, dict(self.data, schema='unapproved'),
                        dict(self.data, width=32), dict(self.data, people=[])):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                builder.enhanced_records(invalid, self.primary)
        self.bad(lambda d: d.update(approved_reference=None), 'reference path')
        self.bad(lambda d: d['approved_reference'].update(path='../untrusted.png'), 'reference path')
        self.bad(lambda d: d['approved_reference'].update(sha256=123), 'reference hash')
        self.bad(lambda d: d['approved_reference'].update(sha256='0' * 64), 'reference hash mismatch')
        (self.root / builder.ENHANCED_REFERENCE).unlink()
        with self.assertRaisesRegex(ValueError, 'reference hash mismatch'):
            builder.enhanced_records(self.data, self.primary)

    def test_nearest_rendering_is_explicit_and_rejects_unknown_values(self):
        for value in (None, True, 4, 'unknown'):
            with self.subTest(rendering=value):
                self.bad(lambda d: d['people'][self.person].update(rendering=value), 'rendering')
        self.bad(lambda d: d['people'][self.person].update(rendering='nearest4x'), 'source method')
        self.record.update(rendering='nearest4x', provenance={'base_method': 'native32x40_exact_nearest4x'})
        with self.assertRaisesRegex(ValueError, 'pixels do not preserve'):
            builder.enhanced_records(self.data, self.primary)

    def test_approved_reference_is_a_real_128_by_160_image(self):
        raw, _ = solid_png(32, 40, (255, 187, 89, 255))
        (self.root / builder.ENHANCED_REFERENCE).write_bytes(raw)
        self.data['approved_reference']['sha256'] = builder.sha(raw)
        with self.assertRaisesRegex(ValueError, '128x160'):
            builder.enhanced_records(self.data, self.primary)

    def test_paths_and_source_hashes_preserve_person_identity(self):
        for path in ('https://invalid.example/a.png', '/assets/portraits/enhanced/../a.png',
                     '/assets/portraits/enhanced/a.png?x=1', '/assets/portraits/original/109.png'):
            with self.subTest(path=path):
                self.bad(lambda d: d['people'][self.person].update(path=path), 'asset path')
        self.bad(lambda d: d['people'][self.person].update(path='/assets/portraits/enhanced/' + self.other_person + '.png'), 'different person')
        self.bad(lambda d: d['people'][self.person].update(source_path=self.primary[self.other_person]['path']), 'source/person')
        self.bad(lambda d: d['people'][self.person].update(source_sha256='0' * 64), 'source/person')
        self.bad(lambda d: d['people'].update({'unknown-person': deepcopy(self.record)}), 'Unknown enhanced')
        self.bad(lambda d: d['people'].update({self.person: None}), 'Invalid enhanced portrait record')

    def test_dimensions_hashes_and_provenance_are_verified(self):
        self.bad(lambda d: d['people'][self.person].update(width=32), 'dimensions mismatch')
        for key in ('source_sha256', 'sha256', 'pixel_sha256'):
            with self.subTest(hash=key):
                self.bad(lambda d: d['people'][self.person].update({key: None}), 'Missing enhanced portrait hashes')
        self.bad(lambda d: d['people'][self.person].update(sha256='0' * 64), 'PNG hash mismatch')
        self.bad(lambda d: d['people'][self.person].update(pixel_sha256='0' * 64), 'pixel hash mismatch')
        self.bad(lambda d: d['people'][self.person].update(method='unreviewed_face_replacement'), 'provenance')
        self.bad(lambda d: d['people'][self.person].update(provenance='unknown'), 'provenance')

    def test_output_png_header_and_binary_alpha_are_checked(self):
        raw, pixels = solid_png(32, 40, (255, 187, 89, 255))
        self.output_path.write_bytes(raw)
        self.record.update(sha256=builder.sha(raw), pixel_sha256=builder.sha(pixels))
        with self.assertRaisesRegex(ValueError, '128x160'):
            builder.enhanced_records(self.data, self.primary)
        raw, pixels = solid_png(128, 160, (255, 187, 89, 128))
        self.output_path.write_bytes(raw)
        self.record.update(sha256=builder.sha(raw), pixel_sha256=builder.sha(pixels))
        with self.assertRaisesRegex(ValueError, 'partial transparency'):
            builder.enhanced_records(self.data, self.primary)

    def test_missing_assets_and_symlinks_outside_enhanced_directory_fail_closed(self):
        self.output_path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing or outside'):
            builder.enhanced_records(self.data, self.primary)
        external = self.root / 'outside.png'
        external.write_bytes(self.image)
        self.output_path.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'missing or outside'):
            builder.enhanced_records(self.data, self.primary)


class RedrawnPortraitTests(unittest.TestCase):
    """New HD art needs measured detail and retained, identity-bound sources."""

    def setUp(self):
        EnhancedPortraitTests.setUp(self)
        self.person = 'historical-lu-xing'
        self.native, self.native_pixels = solid_png(32, 40, (247, 162, 71, 255))
        self.old_hd, self.old_pixels = solid_png(128, 160, (247, 162, 71, 255))
        self.native_path = 'game/assets/portraits/generated/' + self.person + '.png'
        native_file = self.root / self.native_path
        native_file.parent.mkdir(parents=True, exist_ok=True)
        native_file.write_bytes(self.native)
        self.primary = {self.person: {'name': '吕兴', 'path': self.native_path.removeprefix('game'),
                                     'png_sha256': builder.sha(self.native)}}
        self.art = 'art/portraits/supplement-hd-v2/'
        self.archived_path = self.art + 'original-enhanced/' + self.person + '.png'
        self.source_path = self.art + 'sources/' + self.person + '.png'
        self.prompt_path = self.art + 'prompts/' + self.person + '.txt'
        self.plan_path = self.art + 'plan.json'
        self.image, self.pixels = self.pattern_png(6)
        for path, content in ((self.archived_path, self.old_hd), (self.source_path, self.image),
                              (self.prompt_path, b'Fixture: preserve this identity in limited pixel colors.')):
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
        self.output_path = self.root / 'game/assets/portraits/enhanced' / (self.person + '.png')
        self.record = {'path': '/assets/portraits/enhanced/' + self.person + '.png',
                       'width': 128, 'height': 160, 'source_path': self.primary[self.person]['path'],
                       'source_sha256': builder.sha(self.native),
                       'method': 'identity_preserving_pixel_enhancement', 'rendering': 'redrawn128',
                       'provenance': {'base_method': 'identity_preserving_redrawn128',
                                      'redraw_plan': self.plan_path,
                                      'generated_source': self.source_path,
                                      'generated_source_sha256': builder.sha(self.image),
                                      'prompt': self.prompt_path,
                                      'prompt_sha256': builder.sha((self.root / self.prompt_path).read_bytes()),
                                      'original_enhanced': self.archived_path,
                                      'original_enhanced_sha256': builder.sha(self.old_hd)}}
        self.plan = {'schema': 'tk2-portrait-redraw-v2', 'size': [128, 160], 'people': {
            self.person: {'name': '吕兴',
                          'native': {'path': self.native_path, 'sha256': builder.sha(self.native),
                                     'rgba_sha256': builder.sha(self.native_pixels)},
                          'original_enhanced': {'path': self.archived_path, 'sha256': builder.sha(self.old_hd),
                                                'rgba_sha256': builder.sha(self.old_pixels)},
                          **{key: self.record['provenance'][key] for key in
                             ('generated_source', 'generated_source_sha256', 'prompt', 'prompt_sha256')}}}}
        self.write_plan()
        self.set_output(self.image, self.pixels)
        self.data['people'] = {self.person: self.record}

    @staticmethod
    def pattern_png(colors, coarse_blocks=False):
        palette = [(247, 162, 71, 255), (223, 121, 34, 255), (158, 65, 0, 255),
                   (255, 218, 128, 255), (255, 255, 255, 255), (0, 0, 0, 0)]
        palette += [(80 + n * 5, 40 + n * 3, 5 + n, 255) for n in range(max(0, colors - len(palette)))]
        pixels = bytes(channel for y in range(160) for x in range(128)
                       for channel in palette[((y // 4) * 32 + x // 4 if coarse_blocks else y * 128 + x) % colors])
        scan = b''.join(b'\0' + pixels[y * 128 * 4:(y + 1) * 128 * 4] for y in range(160))
        header = struct.pack('>IIBBBBB', 128, 160, 8, 6, 0, 0, 0)
        raw = (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header)
               + png_chunk(b'IDAT', zlib.compress(scan)) + png_chunk(b'IEND', b''))
        return raw, pixels

    def write_plan(self):
        content = (json.dumps(self.plan, ensure_ascii=False, indent=2) + '\n').encode()
        (self.root / self.plan_path).write_bytes(content)
        self.record['provenance']['redraw_plan_sha256'] = builder.sha(content)

    def set_output(self, raw, pixels):
        self.output_path.write_bytes(raw)
        self.record.update(sha256=builder.sha(raw), pixel_sha256=builder.sha(pixels))
        changed = sum(pixels[i:i+4] != self.old_pixels[i:i+4] for i in range(0, len(pixels), 4))
        palette = {pixels[i:i+4] for i in range(0, len(pixels), 4)}
        blocks = sum(len({pixels[((by * 4 + y) * 128 + bx * 4 + x) * 4:
                                 ((by * 4 + y) * 128 + bx * 4 + x) * 4 + 4]
                          for y in range(4) for x in range(4)}) > 1
                     for by in range(40) for bx in range(32))
        self.record['provenance']['qa'] = dict(size=[128, 160], paletteSize=len(palette),
                                              changedPixels=changed, nearest4xExact=False,
                                              source_size=[128, 160], nonUniformBlocks4x4=blocks)

    def reject(self, change):
        data = deepcopy(self.data)
        change(data['people'][self.person])
        with self.assertRaises(ValueError):
            builder.enhanced_records(data, self.primary)

    def test_real_redraw_with_bound_sources_and_archives_is_accepted(self):
        self.assertEqual(builder.enhanced_records(self.data, self.primary), {
            self.person: {'path': self.record['path'], 'width': 128, 'height': 160,
                          'rendering': 'redrawn128'}})
        self.assertEqual((self.root / self.native_path).read_bytes(), self.native)
        self.assertEqual((self.root / self.archived_path).read_bytes(), self.old_hd)

    def test_redraw_requires_every_provenance_file_and_hash(self):
        for key in ('base_method', 'redraw_plan', 'redraw_plan_sha256', 'generated_source',
                    'generated_source_sha256', 'prompt', 'prompt_sha256',
                    'original_enhanced', 'original_enhanced_sha256', 'qa'):
            with self.subTest(field=key):
                self.reject(lambda row: row['provenance'].pop(key))
        self.reject(lambda row: row['provenance'].update(base_method='native32x40_exact_nearest4x'))
        for key in ('redraw_plan_sha256', 'generated_source_sha256', 'prompt_sha256', 'original_enhanced_sha256'):
            with self.subTest(hash=key):
                self.reject(lambda row: row['provenance'].update({key: '0' * 64}))

    def test_qa_must_match_real_pixels_not_just_a_claim(self):
        for key, value in (('size', [32, 40]), ('paletteSize', 4), ('changedPixels', 1023),
                           ('nearest4xExact', True), ('nonUniformBlocks4x4', 19),
                           ('source_size', [64, 80])):
            with self.subTest(qa=key):
                self.reject(lambda row: row['provenance']['qa'].update({key: value}))
        self.set_output(self.old_hd, self.old_pixels)
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)

    def test_redraw_palette_is_limited_even_with_honest_qa(self):
        self.set_output(*self.pattern_png(17))
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)

    def test_recolored_coarse_blocks_are_not_high_resolution_redraws(self):
        self.set_output(*self.pattern_png(6, coarse_blocks=True))
        self.assertGreaterEqual(self.record['provenance']['qa']['changedPixels'], 1024)
        self.assertEqual(self.record['provenance']['qa']['nonUniformBlocks4x4'], 0)
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)

    def test_mutated_source_or_missing_old_hd_is_rejected(self):
        (self.root / self.source_path).write_bytes(self.old_hd)
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)
        (self.root / self.source_path).write_bytes(self.image)
        tiny, _ = solid_png(32, 40, (247, 162, 71, 255))
        (self.root / self.source_path).write_bytes(tiny)
        self.plan['people'][self.person]['generated_source_sha256'] = builder.sha(tiny)
        self.record['provenance']['generated_source_sha256'] = builder.sha(tiny)
        self.record['provenance']['qa']['source_size'] = [32, 40]
        self.write_plan()
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)
        (self.root / self.source_path).write_bytes(self.image)
        self.plan['people'][self.person]['generated_source_sha256'] = builder.sha(self.image)
        self.record['provenance']['generated_source_sha256'] = builder.sha(self.image)
        self.record['provenance']['qa']['source_size'] = [128, 160]
        (self.root / self.archived_path).write_bytes(self.image)
        self.plan['people'][self.person]['original_enhanced'].update(
            sha256=builder.sha(self.image), rgba_sha256=builder.sha(self.pixels))
        self.record['provenance']['original_enhanced_sha256'] = builder.sha(self.image)
        self.write_plan()
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)
        (self.root / self.archived_path).write_bytes(self.old_hd)
        self.plan['people'][self.person]['original_enhanced'].update(
            sha256=builder.sha(self.old_hd), rgba_sha256=builder.sha(self.old_pixels))
        self.record['provenance']['original_enhanced_sha256'] = builder.sha(self.old_hd)
        self.write_plan()
        (self.root / self.archived_path).unlink()
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)

    def test_plan_cannot_substitute_another_person_or_native(self):
        self.plan['people']['historical-song-jian'] = self.plan['people'].pop(self.person)
        self.write_plan()
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)
        self.plan['people'][self.person] = self.plan['people'].pop('historical-song-jian')
        self.plan['people'][self.person]['native']['sha256'] = '0' * 64
        self.write_plan()
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)

    def test_matching_hashes_do_not_allow_source_path_traversal(self):
        outside = self.root / 'outside.png'
        outside.write_bytes(self.image)
        self.plan['people'][self.person]['generated_source'] = 'art/portraits/supplement-hd-v2/../../../outside.png'
        self.record['provenance']['generated_source'] = self.plan['people'][self.person]['generated_source']
        self.write_plan()
        with self.assertRaises(ValueError):
            builder.enhanced_records(self.data, self.primary)


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
