"""All current city targets have explicit, evidence-labelled original-map choices."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_bytes())


class BattlefieldCityBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings = read('game/config/battlefield-city-bindings.json')
        cls.shared = read('game/config/campaigns/shared.json')['catalog']

    def test_every_city_has_one_authored_binding_and_all_30_original_layouts_are_used(self):
        spec = self.bindings
        cities = {row['id'] for row in self.shared['cities']}
        self.assertEqual(len(cities), 115)
        self.assertEqual(set(spec['cities']), cities)
        self.assertEqual(spec['city_count'], 115)
        self.assertEqual(set(spec['templates']), {f'original-{index:02d}' for index in range(30)})
        self.assertEqual({row['map_id'] for row in spec['cities'].values()}, set(spec['templates']))
        for city, row in spec['cities'].items():
            with self.subTest(city=city):
                self.assertIn(row['map_id'], spec['templates'])
                self.assertIn(row['kind'], {'direct_original', 'same_label_association', 'regional_reuse'})
                self.assertTrue(row['reason_tc'] and row['reason_ja'])

    def test_source_transcription_is_kept_literal_without_certifying_unread_rom_names(self):
        evidence = ROOT / 'game/config/references/original-facilities-v1.json'
        self.assertEqual(self.bindings['references'][0]['sha256'], sha256(evidence.read_bytes()).hexdigest())
        labels = read('game/config/references/original-facilities-v1.json')['records']
        for index, record in enumerate(labels):
            self.assertEqual(self.bindings['templates'][f'original-{index:02d}']['source_city_label'],
                             record['source_city_label'])
        # Same-name guide labels are associations, not completed glyph decoding.
        self.assertFalse(any(row['kind'] == 'direct_original' for row in self.bindings['cities'].values()))
        for index, raw in ((5, '西安阳'), (14, '予州'), (29, '永晶')):
            template = self.bindings['templates'][f'original-{index:02d}']
            self.assertEqual(template['source_city_label'], raw)
            self.assertEqual(template['identity_status'], 'unresolved_source_label')
            self.assertNotIn(raw, template['display_tc'])
            self.assertNotIn(raw, template['display_ja'])
            for row in self.bindings['cities'].values():
                if row['map_id'] == f'original-{index:02d}':
                    self.assertEqual(row['kind'], 'regional_reuse')

    def test_shifted_city_identities_do_not_inherit_the_old_first_30_city_order(self):
        choices = self.bindings['cities']
        self.assertEqual((choices['jianan']['map_id'], choices['jianan']['kind']),
                         ('original-17', 'same_label_association'))
        self.assertEqual(choices['yuzhang']['kind'], 'regional_reuse')
        self.assertEqual((choices['fuling']['map_id'], choices['fuling']['kind']),
                         ('original-27', 'same_label_association'))
        self.assertEqual(choices['bajun']['kind'], 'regional_reuse')
        self.assertEqual(choices['yiyang']['kind'], 'regional_reuse')
        self.assertIn('章陵', choices['yiyang']['reason_tc'])
        self.assertIn('不等同', choices['xiping']['reason_tc'])
        for city in ('yizhou', 'zhuya'):
            self.assertEqual(choices[city]['kind'], 'regional_reuse')
            self.assertIn('海島', choices[city]['reason_tc'])

    def test_all_29_compiled_campaign_targets_are_covered_without_changing_their_rules(self):
        count = 0
        for path in sorted((ROOT / 'game/data/campaigns').glob('*.json')):
            if path.name == 'index.json':
                continue
            catalog = json.loads(path.read_bytes())
            with self.subTest(catalog=path.name):
                self.assertLessEqual(set(catalog['active_cities']), set(self.bindings['cities']))
                self.assertEqual({city['id'] for city in catalog['cities']}, set(self.bindings['cities']))
                # One shared authoritative grid binding, never a per-campaign fork.
                self.assertNotIn('battlefield_city_bindings', catalog)
                self.assertEqual(catalog['rules']['battle_officers_per_side'], 10)
            count += 1
        self.assertEqual(count, 29)

    def test_shipped_original_library_joins_by_index_and_keeps_the_full_grid(self):
        library = read('game/assets/battlefields/index.json')
        self.assertEqual(library['schema'], self.bindings['library_schema'])
        self.assertEqual(library['grid'], dict(columns=31, rows=19, tile_size=16, width=496, height=304))
        self.assertEqual(set(library['maps']), set(self.bindings['templates']))
        for identity, template in self.bindings['templates'].items():
            field = library['maps'][identity]
            self.assertEqual(field['id'], identity)
            self.assertEqual(field['original_city_index'], template['original_city_index'])
            self.assertEqual(field['source_city_label'], template['source_city_label'])
            self.assertEqual((field['width'], field['height']), (496, 304))
            self.assertEqual([len(row) for row in field['tiles']], [31] * 19)
            self.assertEqual([len(row) for row in field['classes']], [31] * 19)


if __name__ == '__main__':
    unittest.main()
