"""Han Sui and Ma Teng remain separate in historical and live IF openings.

Material totals and complete garrisons are fixed here explicitly. The later
ruler review changes only the named allocations tested below; its prior totals
are retained separately so updating a roster cannot create money, grain or men.
No Git checkout, network response, or player save is used as a test oracle.
"""
from hashlib import sha256
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Catalog
from remake.session import CampaignSession


HAN_SUI = 'san14-candidate-0166'
MEMBERS = {HAN_SUI, 'san14-candidate-0030', 'san14-candidate-0475'}
HISTORICAL_OPENINGS = {
    '188-06', '190-01', '191-10', '194-06', '196-06', '198-03',
    '200-01', '202-06', '207-09', '208-10', '211-07-tongguan', '212-12',
}
# serving, free, troops, gold, grain, reserves, Ma-family capital,
# unaffected initial-garrison hash, immutable person/ability hash.
PRE_RETAINER_BASELINES = {
    '197-07': (270, 169, 81000, 137820, 477325, 146180, 'wuwei',
        'c7ea4b81cdca56393d41a19d1e9c876e9cf7639725f1bfe775bd52ec214b43a9',
        'ab9e4252c752bc8e5159a97d947fee89d9ad96cd5d4b0ee5c05a236ef2a4d9a5'),
    '201-05': (290, 127, 87000, 148290, 525325, 158350, 'wuwei',
        '8e716c3470348bd2b02d83474fb89b8118211e16f56967607e67dbc3c84be4ab',
        'b84b47046cbe2a1e0bc9f53cb5ff49c35633a831c05043a95b713e1adf564088'),
    '209-06': (389, 39, 116700, 148630, 523825, 157170, 'wuwei',
        'a1577b08dc1bbbb06e8d3d2b3b065b4fc5c49f24a04760ec8c0297c26b1bf448',
        'b84b47046cbe2a1e0bc9f53cb5ff49c35633a831c05043a95b713e1adf564088'),
    '210-11': (378, 55, 113400, 148630, 523825, 157170, 'wuwei',
        '8441bcaf876984b113e3bd263e1842428286cdd757c937ee796d8827f39131de',
        'a6aac56a7b4441783c4fe572bf687808c57ce98aab599777055e7bb8c534a8f2'),
    '212-06': (378, 39, 113400, 157380, 550975, 172000, 'henan',
        'ae2c80af3005646844a2f505716a6f11f26ee2d65b4397fcf69d032583dd1a67',
        '01346a510190fc4e1b7b874770f3a1b58c831fcf2518a15fb039193f34089ffd'),
}

# Replayed against f65d3ab before accepting the retainer review. These hashes
# remain above as a separate oracle; new people must not erase the old checks.
# Current serving/free counts change only through the frozen, named review.
BASELINES = {
    '197-07': (275, 172, 82500, 137820, 477325, 144680, 'wuwei',
        '5210972bf1f3e1f54be6e900980c1eefd5630d42e71a374149218403476b6d87',
        '531fceb5390ac03a0f4a27b5feff776e991902f81df9cd98e6796434e8300cc5'),
    '201-05': (294, 130, 88200, 148290, 525325, 157150, 'wuwei',
        'b3e8d3b921fcac7ebca7b5b796607c4eb7645c77dc1d85149bd9f52849dea9fd',
        'b372f01a022b92bcf1da7ce4530c5de3a5b90ffa18af4fa893bcd461edc1d809'),
    '209-06': (392, 46, 117600, 148630, 523825, 156270, 'wuwei',
        'e2674abee0335b386c97f6a2a0392ed8ca5bcf8781f901917aa766e5401b4c01',
        'b372f01a022b92bcf1da7ce4530c5de3a5b90ffa18af4fa893bcd461edc1d809'),
    '210-11': (381, 60, 114300, 148630, 523825, 156270, 'wuwei',
        'cb434a4db7fd560e862e72c3c3ab1ac1b4cec967d178046077c9438a3abcf126',
        'c87363e212257fc9e0d77a4761764f9acc0e4e39cde5a6e0060775799d3b944c'),
    '212-06': (382, 42, 114600, 157380, 550975, 170800, 'henan',
        'b9c282b7b88cbefeab5a5f6ec06e7961ce6531f00c168bc8dc7b2009e7434141',
        '69c59ba7ea15a1b46f85fe58536b685ad8619ea44c019f5eb15b85775c1f590c'),
}
BASE_PEOPLE_SHA256 = '0aaaeb86c6414b250ec6b3bab35c14d9f989bd108b24017719c57691f7a7acd3'
BASE_EQUIPMENT_SHA256 = '9a8b24cfca5812d2e0ccc038626a8aec8ca7d7672a6b7927d9dfc9ce8f906601'
DATE_CORRECTIONS = {
    'san14-candidate-0190': (221, 220),
    'san14-candidate-0475': (220, 230),
    'san14-candidate-0693': (211, 228),
    'san14-candidate-0969': (211, 212),
}

# Before the independent-ruler audit: serving, free, troops, gold, grain,
# reserves. 188 frees Liu/Guan/Zhang; 197 frees Xu Gong; 210 only changes the
# Gongsun ruler flags; 212 equips the restored Kang from Liaodong's reserves.
PRIOR_OPENINGS = {
    '188-06': (114, 227, 34200, 147640, 520075, 153660),
    '197-07': (271, 168, 81300, 137820, 477325, 145880),
    '210-11': (378, 55, 113400, 148630, 523825, 157170),
    '212-06': (377, 39, 113100, 157380, 550975, 172300),
}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False).encode()).hexdigest()


class HanSuiIfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ROOT / 'game/data'
        index = json.loads((root / 'campaigns/index.json').read_text())
        cls.paths = [root / value for value in index['catalogs']]
        cls.catalogs = {catalog.data['id'].removeprefix('mainland'): catalog
                        for catalog in map(Catalog, cls.paths)}
        cls.if_paths = [root / 'campaigns' / (chapter + '.json')
                        for chapter in BASELINES]
        cls.review = json.loads((ROOT / 'game/config/references/retainer-affiliation-review.json').read_text())
        cls.decisions = {row['id']: row for row in cls.review['scenarios']}
        canonical = json.loads((ROOT / 'game/config/campaigns/people.json').read_text())
        cls.base_order = canonical['order'][:1030]
        cls.base_ids = set(cls.base_order)
        cls.base_snapshot = dict(order=cls.base_order,
                                 people={pid: canonical['people'][pid] for pid in cls.base_order})
        cls.new_ids = set(canonical['order'][1030:])

    def legacy_attributes(self, data):
        """Restore only explicitly reviewed death-year fields for the f65 hash.

        Full current hashes are asserted separately. No game state, save,
        native parity input, stat, equipment or unreviewed year is normalized.
        """
        rows = {row['person_id']: {key: deepcopy(row[key]) for key in
                ('runtime_id', 'birth_year', 'service_year', 'death_year', 'profile', 'initialization')}
                for row in data['people'] if row['person_id'] in self.base_ids}
        for correction in self.decisions[data['id']]['chronology']:
            pid = correction['person_id']
            self.assertIn(pid, DATE_CORRECTIONS)
            before, after = DATE_CORRECTIONS[pid]
            self.assertEqual((correction['before'], correction['death_year']), (before, after))
            self.assertEqual(rows[pid]['death_year'], after)
            self.assertEqual((rows[pid]['birth_year'], rows[pid]['service_year']),
                             (correction['birth_year'], correction['service_year']))
            rows[pid]['death_year'] = before
        self.assertEqual(set(rows), self.base_ids)
        return rows

    def legacy_garrisons(self, data):
        """Reconstruct f65 rows only from the accepted before/after decisions."""
        current = {row['person_id']: row for row in data['initial_officers']}
        free = {row['person_id']: row for row in data['initial_free_officers']}
        changes = {row['person_id']: row for row in self.decisions[data['id']]['changes']}
        restored, missing = {}, []
        for pid in self.base_order:
            row, review = current.get(pid), changes.get(pid)
            if review:
                if row is not None:
                    actual = dict(status='serving', faction=data['initial_owners'][row['city']],
                                  city=row['city'], ruler=bool(row.get('ruler')), troops=row['troops'])
                elif pid in free:
                    actual = dict(status='free', faction=None, city=free[pid]['city'], ruler=False, troops=0)
                else:
                    era = data['era_assignments'][pid]
                    actual = dict(status=era['status'], faction=era.get('faction'),
                                  city=era.get('city'), ruler=False, troops=0)
                self.assertEqual(actual, review['after'], pid)
                old = review['before']
                if old['status'] != 'serving':
                    continue
                row = (dict(row) if row is not None else
                       dict(person_id=pid, resolve_death_year=False))
                row.update(city=old['city'], troops=old['troops'], ruler=old['ruler'])
                restored[pid] = dict(row, owner=old['faction'])
                if pid not in current:
                    missing.append(pid)
            elif row is not None:
                restored[pid] = dict(row, owner=data['initial_owners'][row['city']])
        # Retain every still-serving old officer's actual relative order. Only
        # the explicitly freed old rows are reinserted at their original pool
        # position; rebuilding the current rows in sorted order could hide a
        # command/AI ordering change unrelated to the historical correction.
        ordered = [row['person_id'] for row in data['initial_officers']
                   if row['person_id'] in restored]
        rank = {pid: index for index, pid in enumerate(self.base_order)}
        for pid in missing:
            at = next((index for index, other in enumerate(ordered) if rank[other] > rank[pid]), len(ordered))
            ordered.insert(at, pid)
        self.assertEqual(set(ordered), set(restored))
        return [restored[pid] for pid in ordered]

    def test_old_canonical_objects_and_equipment_are_not_rewritten_by_new_retainers(self):
        self.assertEqual(self.review['base_commit'], 'f65d3abae2c2c50293c5cf08d07f49413d60cbf6')
        self.assertEqual(self.review['base_person_count'], 1030)
        self.assertEqual(self.review['person_count'], 1052)
        self.assertEqual(self.review['base_people_snapshot_sha256'], BASE_PEOPLE_SHA256)
        self.assertEqual(digest(self.base_snapshot), BASE_PEOPLE_SHA256)
        self.assertEqual(len(self.new_ids), 22)
        self.assertEqual(self.new_ids, {row['person_id'] for row in self.review['new_people']})
        for chapter, catalog in self.catalogs.items():
            with self.subTest(chapter=chapter):
                equipment = {pid: row for pid, row in catalog.data['equipment_initial'].items()
                             if pid in self.base_ids}
                self.assertEqual(set(equipment), self.base_ids)
                self.assertEqual(digest(equipment), BASE_EQUIPMENT_SHA256)

    def test_ma_teng_and_ma_chao_are_not_han_sui_retainers_in_any_of_29_openings(self):
        for chapter, catalog in self.catalogs.items():
            with self.subTest(chapter=chapter):
                for person in ('san14-candidate-0771', 'san14-candidate-0769'):
                    assignment = catalog.data['era_assignments'][person]
                    self.assertNotEqual(assignment.get('faction'), 'han_sui', person)
                    for row in catalog.data['initial_officers']:
                        if row['person_id'] == person:
                            self.assertNotEqual(catalog.data['initial_owners'][row['city']],
                                                'han_sui', person)
        early = self.catalogs['184-02'].data
        self.assertEqual(early['faction_rulers']['ma_teng'], 770)
        self.assertEqual(early['initial_owners']['wuwei'], 'ma_teng')
        self.assertEqual(early['era_assignments']['san14-candidate-0771']['faction'], 'ma_teng')
        # Entering Cao Cao's court is distinct from being Han Sui's retainer;
        # do not "fix" the later historical Ma Teng back into Ma Chao's army.
        for chapter in ('208-10', '211-07-tongguan'):
            data = self.catalogs[chapter].data
            self.assertEqual(data['era_assignments']['san14-candidate-0771']['faction'], 'wei')
            self.assertEqual(data['era_assignments']['san14-candidate-0769']['faction'], 'ma_teng')
            self.assertEqual(data['faction_rulers']['ma_teng'], 768)

    def test_188_preview_start_and_save_keep_both_independent_rulers(self):
        session = CampaignSession([ROOT / 'game/data/campaigns/188-06.json'])
        before = session.to_dict()
        preview = session.view()['catalog']['scenarios'][0]
        factions = {row['id']: row for row in preview['factions']}
        self.assertEqual((factions['ma_teng']['city'], factions['ma_teng']['ruler_person_id']),
                         ('wuwei', 'san14-candidate-0771'))
        self.assertEqual((factions['han_sui']['city'], factions['han_sui']['ruler_person_id']),
                         ('jincheng', HAN_SUI))
        for faction, city, person in (('ma_teng', 'wuwei', 'san14-candidate-0771'),
                                       ('han_sui', 'jincheng', HAN_SUI)):
            self.assertEqual(preview['initial_owners'][city], faction)
            data = session.preview_city('mainland188-06', city)['city']
            self.assertEqual(data['owner'], faction)
            rulers = {row['person_id'] for row in data['officers'] if row['is_ruler']}
            self.assertEqual(rulers, {person})
            self.assertEqual(preview['faction_officers'][faction], len(data['officers']))
            expected = ({'san14-candidate-0771', 'san14-candidate-0830'} if faction == 'ma_teng'
                        else {HAN_SUI, 'san14-candidate-0030', 'san14-candidate-0474'})
            self.assertEqual({row['person_id'] for row in data['officers']}, expected)
        self.assertEqual(session.to_dict(), before)
        for faction in ('ma_teng', 'han_sui'):
            session.command('new', dict(scenario='mainland188-06', faction=faction, seed=2026),
                            session.revision)
            state = session.game.state
            self.assertEqual(state.player, faction)
            self.assertEqual(state.rng.draws, 0)
            self.assertEqual(state.extension['leaders']['ma_teng'], 770)
            self.assertEqual(state.extension['leaders']['han_sui'], 165)
            for owner, city, ident in (('ma_teng', 'wuwei', 770), ('han_sui', 'jincheng', 165)):
                self.assertEqual(state.cities[city].owner, owner)
                self.assertIn(ident, state.cities[city].roster.officer_ids)
                self.assertEqual(state.officers[ident].faction_id, owner)
                self.assertEqual(state.officers[ident].loyalty, 100)
            self.assertEqual(set(state.cities['wuwei'].roster.officer_ids), {770, 829})
            self.assertEqual(set(state.cities['jincheng'].roster.officer_ids), {165, 29, 473})
            self.assertEqual(state.officers[829].faction_id, 'ma_teng')
            self.assertNotIn(474, state.officers, 'Chenggong Ying is not eligible until189')
            session.game.validate(state)
            saved = json.loads(json.dumps(session.export_save(), ensure_ascii=False))
            original = session.to_dict()
            restored = CampaignSession([ROOT / 'game/data/campaigns/188-06.json'])
            restored.load_save(saved, restored.revision)
            self.assertEqual(restored.export_save(), saved)
            self.assertEqual(restored.to_dict(), original)
            restored.game.validate(restored.game.state)

    def test_188_separation_conserves_materials_people_and_other_garrisons(self):
        data = self.catalogs['188-06'].data
        actual = (len(data['initial_officers']), len(data['initial_free_officers']),
                  sum(row['troops'] for row in data['initial_officers']),
                  *(sum(data['initial_city_resources'].get(city, data['initial_resources'])[field]
                        for city in data['active_cities'])
                    for field in ('gold', 'grain', 'reserves')))
        self.assertEqual(actual, (109, 232, 32700, 147640, 520075, 155160))
        prior = PRIOR_OPENINGS['188-06']
        self.assertEqual((actual[3], actual[4], actual[2] + actual[5]),
                         (prior[3], prior[4], prior[2] + prior[5]))
        for person_id in ('san14-candidate-0952', 'san14-candidate-0147',
                          'san14-candidate-0656'):
            assignment = data['era_assignments'][person_id]
            self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                             ('free', None, 'zhongshan'))
            self.assertNotIn(person_id, {row['person_id'] for row in data['initial_officers']})
            self.assertIn(person_id, {row['person_id'] for row in data['initial_free_officers']})
        attributes = {row['person_id']: {key: row[key] for key in
                      ('runtime_id', 'birth_year', 'service_year', 'death_year',
                       'profile', 'initialization')} for row in data['people']}
        self.assertEqual(digest(attributes),
                         '891d0f3e935fb65d53d48918aeeaf2483113d430eb49d13d9c95b6cb277b5546')
        self.assertEqual(digest(self.legacy_attributes(data)),
                         '68c5a3ec40e611f85733e230ae7b6d599b0c7aa810102e6355120831e18b5e50')
        other = [dict(row, owner=data['initial_owners'][row['city']])
                 for row in data['initial_officers']
                 if row['person_id'] not in {'san14-candidate-0771', 'san14-candidate-0830'}]
        self.assertEqual(digest(other),
                         '484aff796fd3196d5d83cf1c98f3a08e26f292ec5823909de5552d8dca2b000e')
        legacy_other = [row for row in self.legacy_garrisons(data)
                        if row['person_id'] not in {'san14-candidate-0771', 'san14-candidate-0830'}]
        self.assertEqual(digest(legacy_other),
                         '2b32526869b318818e5f6fbdcde81d45add73628a6a0c75b1da534d712123fe7')

    def test_all_29_openings_do_not_make_han_sui_a_ma_family_retainer(self):
        self.assertEqual(len(self.catalogs), 29)
        expected_independent = HISTORICAL_OPENINGS | set(BASELINES)
        for chapter, catalog in self.catalogs.items():
            with self.subTest(chapter=chapter):
                era = catalog.data['era_assignments'][HAN_SUI]
                self.assertNotEqual(era.get('faction'), 'ma_teng')
                if chapter in expected_independent:
                    self.assertEqual((era['status'], era['faction'], era['city']),
                                     ('serving', 'han_sui', 'jincheng'))
                    self.assertEqual(catalog.data['faction_rulers']['han_sui'], 165)
                    self.assertEqual(catalog.data['initial_owners']['jincheng'], 'han_sui')
                elif chapter == '184-02':
                    self.assertEqual((era['status'], era['faction'], era['city']),
                                     ('free', None, 'jincheng'))
                    self.assertNotIn('han_sui', catalog.factions)
                else:
                    self.assertNotEqual(era['status'], 'serving')
                    self.assertNotIn('han_sui', catalog.factions)

    def test_if_previews_show_the_actual_ruler_and_three_members_without_starting(self):
        session = CampaignSession(self.if_paths)
        before = session.to_dict()
        scenarios = {row['id']: row for row in session.view()['catalog']['scenarios']}
        for chapter, baseline in BASELINES.items():
            with self.subTest(chapter=chapter):
                key = 'mainland' + chapter
                preview = scenarios[key]
                factions = {row['id']: row for row in preview['factions']}
                self.assertEqual(factions['han_sui']['city'], 'jincheng')
                self.assertEqual(factions['han_sui']['ruler_person_id'], HAN_SUI)
                self.assertEqual(factions['ma_teng']['city'], baseline[6])
                self.assertNotEqual(factions['han_sui']['ruler_person_id'],
                                    factions['ma_teng']['ruler_person_id'])
                self.assertEqual(preview['initial_owners']['jincheng'], 'han_sui')
                self.assertEqual(preview['faction_officers']['han_sui'], 3)
                city = session.preview_city(key, 'jincheng')['city']
                self.assertEqual(city['owner'], 'han_sui')
                self.assertEqual({row['person_id'] for row in city['officers']}, MEMBERS)
                self.assertEqual({row['person_id'] for row in city['officers'] if row['is_ruler']},
                                 {HAN_SUI})
                self.assertEqual(sum(row['troops'] for row in city['officers']), 900)
                self.assertEqual(preview['faction_resources']['han_sui'],
                                 dict(cities=1, **{field: city[field]
                                      for field in ('gold', 'grain', 'reserves')}))
        self.assertEqual(session.to_dict(), before)
        self.assertIsNone(session.game.state)

    def test_all_five_can_start_as_han_sui_and_restore_after_switching_factions(self):
        for chapter, baseline in BASELINES.items():
            with self.subTest(chapter=chapter):
                session = CampaignSession(self.if_paths)
                key = 'mainland' + chapter
                response = session.command('new', dict(scenario=key, faction='han_sui',
                                                       seed=2026), session.revision)
                game = session.game
                self.assertEqual(response['game']['player'], 'han_sui')
                self.assertEqual(game.state.phase, 'city')
                self.assertEqual(game.state.rng.draws, 0)
                self.assertEqual(game.state.extension['leaders']['han_sui'], 165)
                self.assertEqual(game.state.officers[165].loyalty, 100)
                self.assertEqual(game.state.cities['jincheng'].owner, 'han_sui')
                stationed = game.state.cities['jincheng'].roster.officer_ids
                self.assertEqual({game.state.officers[ident].person_id for ident in stationed},
                                 MEMBERS)
                for ident in stationed:
                    self.assertEqual(game.state.officers[ident].faction_id, 'han_sui')
                self.assertEqual(game.state.cities[baseline[6]].owner, 'ma_teng')
                game.validate(game.state)
                saved = json.loads(json.dumps(session.export_save(), ensure_ascii=False))
                before = session.to_dict()
                session.command('new', dict(scenario=key, faction='ma_teng', seed=99),
                                session.revision)
                session.load_save(saved, session.revision)
                self.assertEqual(session.export_save(), saved)
                self.assertEqual(session.to_dict(), before)
                session.game.validate(session.game.state)

    def test_separation_conserves_materials_stats_and_every_unaffected_garrison(self):
        for chapter, baseline in BASELINES.items():
            with self.subTest(chapter=chapter):
                data = self.catalogs[chapter].data
                actual = (len(data['initial_officers']), len(data['initial_free_officers']),
                          sum(row['troops'] for row in data['initial_officers']),
                          *(sum(data['initial_city_resources'].get(city,
                                  data['initial_resources'])[field]
                                for city in data['active_cities'])
                            for field in ('gold', 'grain', 'reserves')))
                self.assertEqual(actual, baseline[:6])
                prior = PRIOR_OPENINGS.get(chapter, baseline[:6])
                self.assertEqual((actual[3], actual[4], actual[2] + actual[5]),
                                 (prior[3], prior[4], prior[2] + prior[5]))
                if chapter == '197-07':
                    assignment = data['era_assignments']['san14-candidate-0211']
                    self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                                     ('free', None, 'wujun'))
                    for faction, person_id, city in (
                            ('hua_xin', 'san14-candidate-0091', 'yuzhang'),
                            ('zang_ba', 'san14-candidate-0525', 'donghai'),
                            ('zhang_xiu', 'san14-candidate-0625', 'nanyang')):
                        self.assertEqual(data['faction_rulers'][faction],
                                         self.catalogs[chapter].ids[person_id])
                        self.assertEqual(data['initial_owners'][city], faction)
                if chapter in ('210-11', '212-06'):
                    self.assertEqual(data['faction_rulers']['gongsun'], 263)
                    kang = next(row for row in data['initial_officers']
                                if row['person_id'] == 'san14-candidate-0264')
                    gong = next(row for row in data['initial_officers']
                                if row['person_id'] == 'san14-candidate-0263')
                    self.assertEqual((kang['ruler'], gong['ruler']), (True, False))
                    self.assertEqual((kang['troops'], gong['troops']), (300, 300))
                    self.assertEqual(data['initial_city_resources']['liaodong']['reserves'],
                                     1240 if chapter == '210-11' else 940)
                # Jincheng had no garrison before this correction. Only the
                # three authored Han Sui members should occupy it afterward.
                other = [dict(row, owner=data['initial_owners'][row['city']])
                         for row in data['initial_officers']
                         if row['person_id'] not in MEMBERS]
                self.assertEqual(digest(other), baseline[7])
                attributes = {row['person_id']: {key: row[key] for key in
                              ('runtime_id', 'birth_year', 'service_year', 'death_year',
                               'profile', 'initialization')} for row in data['people']}
                self.assertEqual(digest(attributes), baseline[8])
                old = PRE_RETAINER_BASELINES[chapter]
                legacy_other = [row for row in self.legacy_garrisons(data)
                                if row['person_id'] not in MEMBERS]
                self.assertEqual(digest(legacy_other), old[7])
                self.assertEqual(digest(self.legacy_attributes(data)), old[8])
                ma_family = next(row for row in data['factions'] if row['id'] == 'ma_teng')
                self.assertEqual(ma_family['city'], baseline[6])


if __name__ == '__main__':
    unittest.main()
