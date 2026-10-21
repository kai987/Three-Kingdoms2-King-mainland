"""Opening postings preserve membership while balancing unresolved garrisons."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.garrison_postings import apply_postings


def fixture(count=8):
    names = dict(shujun='蜀郡', hanzhong='汉中', bajun='巴郡', badong='巴东',
                 zitong='梓潼', enemy='敌城', vacant='空城', yanmen='雁门')
    data = dict(cities=[dict(id=key, name=value) for key, value in names.items()],
                active_cities=list(names), rules=dict(city_officer_capacity=30),
                factions=[dict(id='a', city='shujun'), dict(id='b', city='enemy')],
                initial_owners={key: 'b' if key == 'enemy' else 'neutral' if key == 'vacant' else 'a'
                                for key in names},
                links=[['bajun', 'enemy'], ['badong', 'enemy'], ['shujun', 'vacant']],
                initial_officers=[], initial_free_officers=[dict(person_id='free', city='shujun')],
                era_assignments={}, appearance_locations={'future': 'zitong', 'free': 'shujun'},
                people=[dict(person_id='untouched', profile=dict(virtue=60))])
    for i in range(count):
        pid = f'p{i:03}'
        data['initial_officers'].append(dict(person_id=pid, city='shujun', troops=i * 13,
                                            ruler=i == 0, resolve_death_year=i == 1))
        data['era_assignments'][pid] = dict(faction='a', status='serving', source_city=None,
                                            city='shujun', year_state='available')
    return data


class GarrisonPostingTests(unittest.TestCase):
    def test_exact_source_cities_precede_fallback_and_ruler_keeps_seat(self):
        data = fixture(6)
        data['era_assignments']['p000']['source_city'] = '漢中'
        data['era_assignments']['p001'].update(source_city='漢中',
            source_city_reference={'url': 'https://example.test/scenario', 'scope': 'game_posting'})
        data['era_assignments']['p002']['source_city'] = 'enemy'
        before = deepcopy(data)
        audit = apply_postings(data)
        rows = {row['person_id']: row for row in data['initial_officers']}
        self.assertEqual(rows['p000']['city'], 'shujun')
        self.assertEqual(rows['p001']['city'], 'hanzhong')
        self.assertIn(rows['p002']['city'], ('bajun', 'badong'))
        self.assertEqual(audit['source_counts']['matched_source_city'], 1)
        self.assertEqual(audit['source_counts']['source_city_not_owned_by_faction'], 1)
        self.assertEqual(data['era_assignments']['p001']['placement_basis'], 'reviewed_SAN14_source_city_to_board')
        self.assertEqual(data['people'], before['people'])
        self.assertEqual(data['initial_free_officers'], before['initial_free_officers'])
        self.assertEqual(data['appearance_locations']['future'], 'zitong')
        for old, new in zip(before['initial_officers'], data['initial_officers']):
            self.assertEqual({k: v for k, v in old.items() if k != 'city'},
                             {k: v for k, v in new.items() if k != 'city'})
            self.assertEqual(data['appearance_locations'][new['person_id']], new['city'])

    def test_remainder_balances_total_frontier_garrisons_deterministically(self):
        data = fixture(13)
        for pid in ('p001', 'p002', 'p003'):
            data['era_assignments'][pid]['source_city'] = 'bajun'
        twin = deepcopy(data)
        audit = apply_postings(data)
        self.assertEqual(audit, apply_postings(twin))
        counts = Counter(row['city'] for row in data['initial_officers'])
        self.assertEqual(counts['bajun'], 6)
        self.assertEqual(counts['badong'], 6)
        self.assertEqual(counts['shujun'], 1)
        self.assertEqual(audit['factions']['a']['frontier_cities'], ['badong', 'bajun'])

    def test_capacity_overflow_spills_to_owned_interior_without_changing_faction(self):
        data = fixture(12)
        for pid in ('p001', 'p002', 'p003'):
            data['era_assignments'][pid]['source_city'] = '漢中'
        audit = apply_postings(data, capacity=2)
        counts = Counter(row['city'] for row in data['initial_officers'])
        self.assertEqual(max(counts.values()), 2)
        self.assertEqual(counts['hanzhong'], 2)
        self.assertEqual(audit['source_counts']['source_city_full'], 1)
        self.assertGreater(audit['modes']['authored_frontier_full_owned_capacity_fallback'], 0)
        self.assertEqual(len(data['initial_officers']), 12)
        self.assertTrue(all(data['initial_owners'][row['city']] == 'a' for row in data['initial_officers']))

    def test_neutral_border_is_not_enemy_and_proxy_is_explicit_fallback(self):
        data = fixture(6)
        data['links'] = [['shujun', 'vacant']]
        data['era_assignments']['p001']['source_city'] = '新野'
        audit = apply_postings(data, source_aliases={'新野': 'hanzhong'})
        self.assertEqual(audit['source_counts']['source_board_proxy_not_exact_city'], 1)
        self.assertEqual(audit['factions']['a']['frontier_cities'], [])
        self.assertEqual(audit['modes']['authored_no_enemy_frontier_owned_balance'], 5)
        self.assertEqual(max(audit['factions']['a']['city_rosters'].values()), 1)

    def test_attested_yanmen_appointment_is_pinned_ahead_of_source(self):
        data = fixture(5)
        posting = dict(city='yanmen', basis='attested_yanmen_post_227', person_id='p001')
        data['era_assignments']['p001'].update(source_city='漢中', posting_reference=posting)
        audit = apply_postings(data)
        row = next(row for row in data['initial_officers'] if row['person_id'] == 'p001')
        self.assertEqual(row['city'], 'yanmen')
        record = next(row for row in audit['postings'] if row['person_id'] == 'p001')
        self.assertEqual(record['basis'], 'attested_yanmen_post_227')
        self.assertEqual(record['prior_posting'], posting)

    def test_invalid_rosters_fail_before_mutating_any_input(self):
        cases = []
        data = fixture(13); cases.append((data, dict(capacity=2)))
        data = fixture(); data['initial_officers'].append(deepcopy(data['initial_officers'][0])); cases.append((data, {}))
        data = fixture(); data['era_assignments']['p001']['faction'] = 'b'; cases.append((data, {}))
        data = fixture(); data['initial_free_officers'].append(dict(person_id='p001', city='shujun')); cases.append((data, {}))
        for data, options in cases:
            with self.subTest(options=options, officers=len(data['initial_officers'])):
                before = deepcopy(data)
                with self.assertRaises(ValueError):
                    apply_postings(data, **options)
                self.assertEqual(data, before)

    def test_all_released_chapters_keep_existing_people_and_capacity(self):
        index = json.loads((ROOT / 'game/data/main-scenarios-v8/index.json').read_text())
        for filename in index['catalogs']:
            data = json.loads((ROOT / 'game/data' / filename).read_text())
            before = deepcopy(data)
            audit = apply_postings(data)
            self.assertEqual(len(audit['postings']), len(before['initial_officers']))
            self.assertEqual(data['people'], before['people'])
            self.assertEqual(data['initial_free_officers'], before['initial_free_officers'])
            self.assertLessEqual(max(Counter(row['city'] for row in data['initial_officers']).values()), 30)
            for old, new in zip(before['initial_officers'], data['initial_officers']):
                self.assertEqual(old['person_id'], new['person_id'])
                self.assertEqual(old['troops'], new['troops'])
                self.assertEqual(before['initial_owners'][old['city']], data['initial_owners'][new['city']])
            if data['start_year'] == 227:
                person = next(row for row in data['people'] if row['name'] == '牵招')['person_id']
                self.assertEqual(next(row for row in data['initial_officers'] if row['person_id'] == person)['city'], 'yanmen')


if __name__ == '__main__':
    unittest.main()
