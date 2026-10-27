"""Retainer art release checks using only the standard-library PNG decoder.

The original studies and old bindings are frozen. New HD art must retain its
authored source and contain detail beyond the 32x40 compatibility derivative.
Pillow is used by the offline asset build, never imported by these tests.
"""
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('retainer_portrait_decoder',
                                             ROOT / 'game/build_portrait_manifest.py')
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)
PLAN = 'art/portraits/retainer-additions-v1/plan.json'
METHOD = 'retainer_authored_source_direct128_fixed_palette'
OLD_NATIVE_RECORDS_SHA = '28e0952d4a8d04987bbe058b5ee64045a051ade5de9537a9146ddcd0761cea52'
OLD_HD_RECORDS_SHA = '105e95b4f78b3b6848f381d3f616bfbb3f184aa5ecb93c538ca0085bf8930ca2'
OTHER_ORIGINAL_IDENTITIES_SHA = '9925d8436750da543bf9335ac223ef850261b20964b77a3265581cff510b586d'
IMMUTABLE_PLANS = {
    'art/portraits/plan.json': 'def53a9c0d1c2eadcf25f68581c4260ecdb6593f264b02b66a92988c6496cb4c',
    'art/portraits/enhancement-v1/plan.json': '4765e72c634e848c4190e235d496b44b3f45edef653069b556a509d78857711b',
    'art/portraits/historical-additions-v1/plan.json': 'e91452cc899b242928cfdf48844753e4c109113630e5a79466da94c4ed093aed',
    'art/portraits/northwest-rising-v1/plan.json': 'eebea02f2aac0ffd7c57978dcc6a0f8a7df84e761276133590c5e33c3fa62663',
    'art/portraits/bian-zhang-v1/plan.json': 'd1f8e7868f562c80b963d307a8d40b3de6a7da2a445a0bf105fdc56302dd0840',
    'art/portraits/supplement-hd-v2/plan.json': '4d07aae641216cb2f312f1a29021b26dcacbb675f2032419c06e18d95a1e9342',
    'game/config/portrait-originals.json': 'e5a0c34080960257c5bccfda1627377214e326ab437ccf35515111601d4ec751',
}
WARM_PALETTE = {
    (0, 0, 0, 0), (0, 0, 0, 255), (108, 46, 7, 255), (142, 56, 0, 255),
    (158, 65, 0, 255), (185, 85, 10, 255), (198, 99, 18, 255), (223, 121, 34, 255),
    (247, 162, 71, 255), (255, 187, 89, 255), (255, 218, 128, 255),
    (255, 214, 162, 255), (255, 235, 204, 255), (188, 189, 185, 255),
    (226, 226, 222, 255), (255, 255, 255, 255),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_bytes())


def canonical_sha(rows):
    return sha(json.dumps(rows, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode())


def png(path, size=None):
    raw = (ROOT / path).read_bytes()
    if size is None:
        size = struct.unpack('>II', raw[16:24])
    dimensions, pixels = decoder.png_pixels(raw, size)
    return raw, dimensions, pixels


def asset(path):
    return 'game' + path


def nearest4x(pixels):
    return b''.join(pixels[(y // 4 * 32 + x // 4) * 4:(y // 4 * 32 + x // 4) * 4 + 4]
                    for y in range(160) for x in range(128))


def non_uniform_blocks(pixels):
    return sum(len({pixels[((y + dy) * 128 + x + dx) * 4:
                          ((y + dy) * 128 + x + dx) * 4 + 4]
                    for dy in range(4) for dx in range(4)}) > 1
               for y in range(0, 160, 4) for x in range(0, 128, 4))


class LegacyPortraitPreservationTests(unittest.TestCase):
    def test_old_810_native_bindings_and_files_remain_exact(self):
        rows = {pid: row for pid, row in read('game/config/portrait-generated.json')['by_person_id'].items()
                if 'retainer_plan' not in row}
        self.assertEqual(len(rows), 810)
        self.assertEqual(canonical_sha(rows), OLD_NATIVE_RECORDS_SHA)
        for pid, row in rows.items():
            with self.subTest(person_id=pid):
                self.assertEqual(sha((ROOT / asset(row['path'])).read_bytes()), row['png_sha256'])

    def test_old_1030_hd_bindings_and_files_remain_exact(self):
        rows = {pid: row for pid, row in read('game/config/portrait-enhanced.json')['people'].items()
                if 'retainer_plan' not in row.get('provenance', {})}
        self.assertEqual(len(rows), 1030)
        self.assertEqual(canonical_sha(rows), OLD_HD_RECORDS_SHA)
        for pid, row in rows.items():
            with self.subTest(person_id=pid):
                self.assertEqual(sha((ROOT / asset(row['path'])).read_bytes()), row['sha256'])

    def test_approved_original_and_hd_study_plans_are_immutable(self):
        for path, expected in IMMUTABLE_PLANS.items():
            with self.subTest(path=path):
                self.assertEqual(sha((ROOT / path).read_bytes()), expected)

    def test_only_the_independently_reviewed_original11_identity_is_newly_bound(self):
        records = read('game/config/portrait-identity-map.json')['records']
        other = {str(row['original_id']): row for row in records if row['original_id'] != 11}
        self.assertEqual(canonical_sha(other), OTHER_ORIGINAL_IDENTITIES_SHA)
        row = next(row for row in records if row['original_id'] == 11)
        self.assertEqual(row['transcribed_name'], '王建')
        self.assertEqual(row['person_id'], 'historical-wang-jian-liaodong')
        self.assertEqual(row['identity_context']['public_table_source_row_id'], 'cnblogs-line-0229')
        self.assertEqual(row['identity_context']['public_table_city_label'], '辽东')


class RetainerPortraitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan_raw = (ROOT / PLAN).read_bytes()
        cls.plan = json.loads(cls.plan_raw)
        cls.native_manifest = read('game/config/portrait-generated.json')
        cls.native = cls.native_manifest['by_person_id']
        cls.bindings = read(str(Path(PLAN).parent / 'native-records.json'))['people']
        cls.enhanced_manifest = read('game/config/portrait-enhanced.json')
        cls.enhanced = cls.enhanced_manifest['people']
        cls.canonical = read('game/config/campaigns/people.json')['people']
        cls.ids = {person['person_id'] for person in cls.plan['people']}
        cls.generated_ids = {person['person_id'] for person in cls.plan['people']
                             if person['source_kind'] != 'original_portrait_redraw'}

    def test_exact_canonical_identity_and_manifest_bindings(self):
        self.assertEqual(self.plan['schema'], 'tk2-retainer-portrait-additions-v1')
        self.assertEqual(self.plan['native_size'], [32, 40])
        self.assertEqual(self.plan['enhanced_size'], [128, 160])
        self.assertEqual(len(self.ids), len(self.plan['people']))
        self.assertTrue(self.ids)
        self.assertEqual(self.ids, set(self.bindings))
        self.assertEqual(self.generated_ids, {pid for pid, row in self.native.items()
                                             if row.get('retainer_plan') == PLAN})
        self.assertEqual(self.ids, {pid for pid, row in self.enhanced.items()
                                   if row.get('provenance', {}).get('retainer_plan') == PLAN})
        summary = self.native_manifest['retainer_plan']
        self.assertEqual(summary['path'], PLAN)
        self.assertEqual(summary['sha256'], sha(self.plan_raw))
        self.assertEqual(summary['count'], len(self.ids))
        self.assertEqual(summary['generated_count'], len(self.generated_ids))
        self.assertEqual(summary['original_count'], len(self.ids - self.generated_ids))
        self.assertEqual(summary['method'], METHOD)
        self.assertEqual(len(self.native), 810 + len(self.generated_ids))
        self.assertEqual(len(self.enhanced), 1030 + len(self.ids))
        for person in self.plan['people']:
            pid = person['person_id']
            with self.subTest(person_id=pid):
                native, hd = self.bindings[pid], self.enhanced[pid]
                self.assertEqual(native['name'], person['name'])
                self.assertEqual(native['name'], self.canonical[pid]['name'])
                if pid in self.generated_ids:
                    self.assertEqual(native, self.native[pid])
                    self.assertEqual(native['path'], f'/assets/portraits/generated/{pid}.png')
                    self.assertEqual(native['native_kind'], 'generated')
                else:
                    self.assertNotIn(pid, self.native)
                    self.assertEqual(native['native_kind'], 'nes_original')
                    self.assertEqual(native['source'], 'pinned_ROM_static_frame0')
                    self.assertEqual(native['path'], person['native_original_path'].removeprefix('game'))
                    self.assertEqual(native['png_sha256'], person['native_original_sha256'])
                self.assertEqual(hd['path'], f'/assets/portraits/enhanced/{pid}.png')
                self.assertEqual(hd['source_path'], native['path'])
                self.assertEqual(hd['source_sha256'], native['png_sha256'])
                self.assertEqual(hd['method'], 'identity_preserving_pixel_enhancement')
                self.assertEqual(hd['rendering'], 'redrawn128')
                self.assertEqual(hd['provenance']['retainer_plan_sha256'], sha(self.plan_raw))
                self.assertEqual(hd['provenance']['base_method'], METHOD)
        for filename, rows in [('native-records.json', self.bindings), ('enhanced-records.json', self.enhanced)]:
            records = read(str(Path(PLAN).parent / filename))
            self.assertEqual(records['people'], {pid: rows[pid] for pid in self.ids})
            self.assertEqual(records['plan_sha256'], sha(self.plan_raw))

    def test_sources_are_retained_exactly_and_cells_are_never_reused(self):
        previous_cells = {(row['source_atlas'], row['cell_index']) for pid, row in self.native.items()
                          if pid not in self.ids and 'source_atlas' in row and 'cell_index' in row}
        assigned, decoded_sources = set(), {}
        for person in self.plan['people']:
            pid = person['person_id']
            with self.subTest(person_id=pid):
                native, hd = self.bindings[pid], self.enhanced[pid]
                proof = hd['provenance']
                source_path = person.get('source_atlas') or person['source_path']
                source = ROOT / source_path
                self.assertTrue(source.is_relative_to(ROOT / 'art/portraits'))
                self.assertFalse(source.is_symlink())
                self.assertEqual(sha(source.read_bytes()), person['source_sha256'])
                self.assertEqual(proof['original_source_sha256'], person['source_sha256'])
                self.assertEqual(proof['original_source_path'], source_path)
                if 'source_atlas' in person:
                    key = (source_path, person['cell_index'])
                    self.assertNotIn(key, previous_cells | assigned)
                    assigned.add(key)
                    self.assertEqual(person['grid'], [8, 8])
                    self.assertIs(type(person['cell_index']), int)
                    self.assertTrue(0 <= person['cell_index'] < 64)
                    self.assertEqual(proof['source_origin'], 'retained_unassigned_imagegen_cell')
                    self.assertIn('Previously authored, unassigned', proof['reuse_notice'])
                    self.assertIn('not newly generated', native['reuse_notice'])
                else:
                    if person['source_kind'] == 'original_portrait_redraw':
                        self.assertEqual(proof['source_origin'], 'identity_preserving_original_portrait_redraw')
                        original = read('game/config/portrait-originals.json')['by_original_id'][str(person['native_original_id'])]
                        self.assertEqual(original['path'], native['path'])
                        self.assertEqual(original['png_sha256'], native['png_sha256'])
                        self.assertEqual(original['rgba_sha256'], native['rgba_sha256'])
                    else:
                        self.assertEqual(person['source_kind'], 'imagegen_new_pixel_art')
                        self.assertEqual(proof['source_origin'], 'new_retained_imagegen_source')
                if source_path not in decoded_sources:
                    decoded_sources[source_path] = png(source_path, tuple(person['source_size']))
                _, size, pixels = decoded_sources[source_path]
                left, top, right, bottom = native['source_cell_box']
                expected_crop = b''.join(pixels[(y * size[0] + left) * 4:(y * size[0] + right) * 4]
                                         for y in range(top, bottom))
                crop_raw, crop_size, crop = png(proof['retained_source_crop'], (right - left, bottom - top))
                self.assertEqual(crop, expected_crop)
                self.assertEqual(sha(crop_raw), proof['retained_source_crop_sha256'])
                self.assertEqual(sha(crop), proof['retained_source_crop_rgba_sha256'])
                self.assertGreaterEqual(crop_size[0], 96)
                self.assertGreaterEqual(crop_size[1], 128)
                archive, _, native_pixels = png(proof['native_archive'], (32, 40))
                self.assertEqual(archive, (ROOT / asset(native['path'])).read_bytes())
                self.assertEqual(sha(archive), proof['native_archive_sha256'])
                self.assertEqual(sha(native_pixels), native['rgba_sha256'])

    def test_native_and_hd_files_are_unique_and_hd_has_real_fine_detail(self):
        old_native = {row['rgba_sha256'] for pid, row in self.native.items() if pid not in self.ids}
        old_hd = {row['pixel_sha256'] for pid, row in self.enhanced.items() if pid not in self.ids}
        new_native, new_hd = set(), set()
        for pid in sorted(self.ids):
            with self.subTest(person_id=pid):
                native, hd = self.bindings[pid], self.enhanced[pid]
                native_raw, _, small = png(asset(native['path']), (32, 40))
                hd_raw, _, large = png(asset(hd['path']), (128, 160))
                self.assertEqual(sha(native_raw), native['png_sha256'])
                self.assertEqual(sha(small), native['rgba_sha256'])
                self.assertEqual(sha(hd_raw), hd['sha256'])
                self.assertEqual(sha(large), hd['pixel_sha256'])
                self.assertNotIn(sha(small), old_native | new_native)
                self.assertNotIn(sha(large), old_hd | new_hd)
                new_native.add(sha(small))
                new_hd.add(sha(large))
                colors = {tuple(large[i:i + 4]) for i in range(0, len(large), 4)}
                self.assertTrue(colors <= WARM_PALETTE)
                self.assertTrue(5 <= len(colors) <= 16)
                self.assertEqual({color[3] for color in colors}, {0, 255})
                baseline = nearest4x(small)
                changes = sum(large[i:i + 4] != baseline[i:i + 4] for i in range(0, len(large), 4))
                blocks = non_uniform_blocks(large)
                self.assertGreaterEqual(changes, 1024)
                self.assertGreaterEqual(blocks, 20)
                qa = hd['provenance']['qa']
                self.assertEqual(qa['changedPixels'], changes)
                self.assertEqual(qa['nonUniformBlocks4x4'], blocks)
                self.assertEqual(qa['paletteSize'], len(colors))
                self.assertIs(qa['nearest4xExact'], False)
        self.assertEqual(len(new_native), len(self.ids))
        self.assertEqual(len(new_hd), len(self.ids))
        self.assertEqual(self.enhanced_manifest['counts']['source_unique'],
                         len({row['pixel_sha256'] for row in self.enhanced.values()}))

    def test_retainer_sources_cannot_escape_retained_paths_or_follow_symlinks(self):
        for path in ('art/portraits/retainer-additions-v1/../outside.png',
                     '/tmp/outside.png', 'game/assets/portraits/original/011.png',
                     'art/portraits/retainer-additions-v1/source\\outside.png'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                decoder.retainer_retained(path)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'art/portraits/retainer-additions-v1/source'
            source.mkdir(parents=True)
            outside = root / 'private.png'
            outside.write_bytes(b'not an art input')
            (source / 'person.png').symlink_to(outside)
            with patch.object(decoder, 'ROOT', root), self.assertRaisesRegex(ValueError, 'symlink'):
                decoder.retainer_retained('art/portraits/retainer-additions-v1/source/person.png')

    def test_a_retainer_cannot_claim_another_reviewed_original_id(self):
        pid = next(iter(self.ids - self.generated_ids))
        forged = deepcopy(self.bindings[pid])
        forged['native_original_id'] = (forged['native_original_id'] + 1) % 237
        records = dict(self.bindings, **{pid: forged})
        cache = {('records', 'native'): records}
        with self.assertRaisesRegex(ValueError, 'original portrait identity differs'):
            decoder.retainer_binding(pid, forged, cache)

    def test_rendering_markers_cannot_bypass_the_retainer_detail_validator(self):
        pid = next(person['person_id'] for person in self.plan['people'] if 'source_atlas' in person)
        reference = self.enhanced_manifest['approved_reference']
        for rendering in (None, 'nearest4x'):
            with self.subTest(rendering=rendering):
                forged = deepcopy(self.enhanced[pid])
                if rendering is None:
                    forged.pop('rendering')
                else:
                    forged['rendering'] = rendering
                manifest = dict(schema='tk2-enhanced-portraits-v1', width=128, height=160,
                                approved_reference=reference, people={pid: forged})
                with self.assertRaisesRegex(ValueError, 'direct128 source method'):
                    decoder.enhanced_records(manifest, {pid: self.bindings[pid]})
        old_branch = deepcopy(self.enhanced[pid])
        old_branch['provenance']['base_method'] = 'identity_preserving_redrawn128'
        with self.assertRaisesRegex(ValueError, 'plan path differs'):
            decoder.validate_redrawn(pid, old_branch, self.bindings[pid], b'')

    def test_detail_reports_are_recomputed_after_matching_the_archive_record(self):
        pid = next(person['person_id'] for person in self.plan['people'] if 'source_atlas' in person)
        row = self.enhanced[pid]
        pixels = png(asset(row['path']), (128, 160))[2]
        cache = {}
        decoder.validate_retainer_redrawn(pid, row, self.bindings[pid], pixels, cache)
        original_records = cache[('records', 'enhanced')]
        for key, wrong in (('changedPixels', 0), ('paletteSize', 4), ('nonUniformBlocks4x4', 0)):
            with self.subTest(field=key):
                forged = deepcopy(row)
                forged['provenance']['qa'][key] = wrong
                cache[('records', 'enhanced')] = dict(original_records, **{pid: forged})
                with self.assertRaisesRegex(ValueError, 'misreported authored detail'):
                    decoder.validate_retainer_redrawn(pid, forged, self.bindings[pid], pixels, cache)


if __name__ == '__main__':
    unittest.main()
