"""Retain original byte evidence while the campaign uses its new stat policy."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
sys.path.insert(0, str(ROOT / 'source'))
from officer_stat_sources import validate_original_virtue
from remake.officers import convert_profile


def read(name):
    return json.loads((ROOT / name).read_text())


class OriginalStatEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = read('game/config/campaigns/people.json')['people']
        cls.reference = read('game/config/references/original-officer-stats.json')
        cls.identities = read('game/config/portrait-identity-map.json')

    def test_all237_bytes_and220_exact_identity_bindings_are_retained(self):
        bound = validate_original_virtue(self.people, self.reference, self.identities)
        self.assertEqual(len(bound), 220)
        self.assertEqual(self.reference['identity_source_sha256'], sha256(
            (ROOT / 'game/config/portrait-identity-map.json').read_bytes()).hexdigest())
        self.assertEqual(self.reference['audit']['changed_people'], 214)
        self.assertEqual(self.reference['audit']['prior_default_changes'], 89)
        self.assertEqual(self.reference['audit']['prior_design_changes'], 125)
        self.assertEqual(self.reference['audit']['unchanged_original_values'], 6)
        self.assertEqual(sum(row['person_id'] is None for row in self.reference['records']), 17)
        for pid, person in self.people.items():
            if pid in bound:
                self.assertEqual(person['pre_campaign_stat_policy_v1']['virtue_design']['status'],
                                 'verified_original')
                # Martial, intellect and charisma share the current 99 scale.
                stats = person['profile']['source_stats']
                for field in ('martial_strength', 'intellect', 'charisma'):
                    if stats.get(field) is not None:
                        self.assertEqual(person['profile']['virtue' if field == 'charisma' else field],
                                         min(99, stats[field]))

    def test_yan_yan_and_liu_bei_original_values_are_evidence_not_active_virtue_priority(self):
        rows = {r['original_id']: r for r in self.reference['records']}
        for ident, name, value in ((63, '严颜', 86), (222, '刘备', 99)):
            row = rows[ident]
            raw = bytes.fromhex(row['record_hex'])
            person = self.people[row['person_id']]
            self.assertEqual(person['name'], name)
            self.assertEqual(raw[4], value)
            archived = person['pre_campaign_stat_policy_v1']['virtue_design']
            self.assertEqual(archived['rom_offset'], 0x22010 + ident*12 + 4)
            self.assertEqual(archived['virtue'], value)
            self.assertEqual(person['profile']['virtue'],
                             min(99, person['profile']['source_stats']['charisma']))
            self.assertFalse(person['virtue_design']['is_historical_fact'])
        self.assertEqual(self.people['san14-candidate-0231']['profile']['virtue'], 77)
        self.assertEqual(self.people['san14-candidate-0952']['profile']['virtue'], 99)

    def test_retained_byte_reference_rejects_tampering_but_does_not_override_new_policy(self):
        for field, value in (('virtue', 60), ('person_id', 'wrong-person'), ('record_hex', '00'*12)):
            reference = deepcopy(self.reference)
            next(row for row in reference['records'] if row['original_id'] == 63)[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'reference bytes'):
                validate_original_virtue(self.people, reference, self.identities)
        people = deepcopy(self.people)
        people['san14-candidate-0231']['profile']['virtue'] = 60
        self.assertEqual(len(validate_original_virtue(people, self.reference, self.identities)), 220,
                         'Byte provenance is checked separately from current campaign stat policy')
        design = dict(status='configured_design', sources=[dict(work='Historical assessment')],
                      dimensions=dict(care=90, fairness=90, integrity=90, trust=90))
        for lower in (design, dict(status='configured_default', virtue=60)):
            result = convert_profile(legacy=dict(virtue=86), virtue_design=lower,
                                     san14_stats=dict(martial_strength=82, intellect=69))
            self.assertEqual((result.virtue, result.martial_strength, result.intellect), (86, 82, 69))
            self.assertEqual(result.basis['virtue'], 'verified_legacy_record')
            result = convert_profile(legacy=dict(virtue=86), virtue_design=lower,
                                     san14_stats=dict(martial_strength=82, intellect=69, charisma=77))
            self.assertEqual(result.virtue, 77)

    def test_all29_scenario_sources_retain_original_evidence_and_use_current_virtue_policy(self):
        from build_campaigns import load_sources
        _, catalogs = load_sources(timing=False)
        self.assertEqual(len(catalogs), 29)
        for catalog in catalogs:
            people = {p['person_id']: p for p in catalog['people']}
            self.assertEqual(len(validate_original_virtue(people, self.reference, self.identities)), 220)
            charisma = [p for p in people.values() if type(p['profile']['source_stats'].get('charisma')) is int]
            fallback = [p for p in people.values() if type(p['profile']['source_stats'].get('charisma')) is not int]
            self.assertEqual((len(charisma), len(fallback)), (1000, 30))
            for person in charisma:
                self.assertEqual(person['profile']['virtue'], min(99, person['profile']['source_stats']['charisma']))
                self.assertEqual(person['virtue_design']['status'], 'san14_charisma')
            self.assertTrue(all(p['profile']['virtue'] == 60 for p in fallback))
            self.assertEqual(people['san14-candidate-0952']['profile']['virtue'], 99)
            self.assertEqual(people['san14-candidate-0231']['profile']['virtue'], 77)


if __name__ == '__main__':
    unittest.main()
