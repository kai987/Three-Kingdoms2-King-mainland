"""Reviewed221 identity coverage retains all237 bytes and the old220 joins."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('original_stat_import_review',
    Path(__file__).with_name('import_original_stats.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OriginalIdentityCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identities = json.loads((ROOT / 'game/config/portrait-identity-map.json').read_text())
        cls.reference = json.loads((ROOT / 'game/config/references/original-officer-stats.json').read_text())

    def test_reviewed_coverage_derives221_and16_without_rebinding_old220(self):
        expected = dict(original_records=237, bound_people=221, unbound_original_records=16)
        self.assertEqual(MODULE.reviewed_coverage(self.identities), expected)
        self.assertEqual({key: self.reference[key] for key in expected}, expected)
        self.assertEqual(self.reference['identity_source_sha256'],
            sha256((ROOT / 'game/config/portrait-identity-map.json').read_bytes()).hexdigest())

    def test_all237_factual_raw_records_are_unchanged_from_f65d3ab(self):
        keys = ('original_id', 'transcribed_name', 'rom_offset', 'record_hex',
                'record_sha256', 'virtue', 'experience_raw')
        facts = [{key: row[key] for key in keys} for row in self.reference['records']]
        digest = sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True,
                                  separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(digest, '2c4cfbdcba4bd77daff7a32a39fd2c4cad3568b2c869bfbea9e54760482636d1')
        for row in self.reference['records']:
            raw = bytes.fromhex(row['record_hex'])
            self.assertEqual(len(raw), MODULE.ORIGINAL_RECORD_SIZE)
            self.assertEqual(row['record_sha256'], sha256(raw).hexdigest())
            self.assertEqual(row['virtue'], raw[4])

    def test_reassigning_any_old_identity_or_glyph_evidence_is_rejected(self):
        for field, forged in (('person_id', 'different-person'), ('transcribed_name', 'different-name')):
            data = deepcopy(self.identities)
            row = next(row for row in data['records'] if row['person_id']
                       and row['person_id'] != MODULE.WANG_JIAN)
            row[field] = forged
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'original220 identity bindings changed'):
                MODULE.reviewed_coverage(data)

    def test_new_wang_jian_review_cannot_bind_a_different_raw_record(self):
        for field, forged in (('person_id', 'wrong-wang-jian'), ('transcribed_name', '唐代王建')):
            data = deepcopy(self.identities)
            row = data['records'][11]
            row[field] = forged
            with self.subTest(field=field), self.assertRaises(ValueError):
                MODULE.reviewed_coverage(data)
        data = deepcopy(self.identities)
        data['records'][11]['identity_context']['public_table_source_row_id'] = 'cnblogs-line-0001'
        with self.assertRaisesRegex(ValueError, 'Only reviewed Wang Jian'):
            MODULE.reviewed_coverage(data)

    def test_bad_rom_cannot_write_people_or_refresh_the_archived_policy(self):
        path = ROOT / 'game/config/campaigns/people.json'
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Different ROM'):
            MODULE.import_stats(b'not the reviewed ROM')
        self.assertEqual(path.read_bytes(), before)

    def test_retained_check_cannot_reapply_original_virtue_to_current_people(self):
        paths = [ROOT / 'game/config/campaigns/people.json',
                 ROOT / 'game/config/references/original-officer-stats.json']
        before = {path: path.read_bytes() for path in paths}
        result = MODULE.verify_retained_reference()
        self.assertEqual((result['bound_people'], result['unbound_original_records']), (221, 16))
        self.assertEqual(result['historical_first_import_people'], 220)
        self.assertEqual(result['historical_first_import_audit'], dict(changed_people=214,
            prior_default_changes=89, prior_design_changes=125, unchanged_original_values=6))
        self.assertEqual({path: path.read_bytes() for path in paths}, before)


if __name__ == '__main__':
    unittest.main()
