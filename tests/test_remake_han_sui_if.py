"""Han Sui and Ma Teng remain separate in historical and live IF openings.

The pre-fix material totals and unaffected garrisons are fixed here explicitly.
No Git checkout, network response, or player save is used as a test oracle.
"""
from hashlib import sha256
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
BASELINES = {
    '197-07': (271, 168, 81300, 137820, 477325, 145880, 'wuwei',
        '363d419b3f9f6a482a9e1a4dab51f841f5d5f9a4ab7b7c7fab080b7c88377770',
        'ab9e4252c752bc8e5159a97d947fee89d9ad96cd5d4b0ee5c05a236ef2a4d9a5'),
    '201-05': (290, 127, 87000, 148290, 525325, 158350, 'wuwei',
        '8e716c3470348bd2b02d83474fb89b8118211e16f56967607e67dbc3c84be4ab',
        'b84b47046cbe2a1e0bc9f53cb5ff49c35633a831c05043a95b713e1adf564088'),
    '209-06': (389, 39, 116700, 148630, 523825, 157170, 'wuwei',
        'a1577b08dc1bbbb06e8d3d2b3b065b4fc5c49f24a04760ec8c0297c26b1bf448',
        'b84b47046cbe2a1e0bc9f53cb5ff49c35633a831c05043a95b713e1adf564088'),
    '210-11': (378, 55, 113400, 148630, 523825, 157170, 'wuwei',
        '0eea64d7cd69ece0c55dec1ec44c31118d10703593647f3f6b58f9ffe907790f',
        '86839632dd1b854a7ff8430648e29b3cc02a77ce2a8fec0f8d4e232b3704230f'),
    '212-06': (377, 39, 113100, 157380, 550975, 172300, 'henan',
        '539edbefdf3871d2caf51350c1df2dd2b1f0ee8801993d7fc34ea97f125eb978',
        'b84b47046cbe2a1e0bc9f53cb5ff49c35633a831c05043a95b713e1adf564088'),
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
        self.assertEqual(actual, (114, 227, 34200, 147640, 520075, 153660))
        attributes = {row['person_id']: {key: row[key] for key in
                      ('runtime_id', 'birth_year', 'service_year', 'death_year',
                       'profile', 'initialization')} for row in data['people']}
        self.assertEqual(digest(attributes),
                         'b84b47046cbe2a1e0bc9f53cb5ff49c35633a831c05043a95b713e1adf564088')
        other = [dict(row, owner=data['initial_owners'][row['city']])
                 for row in data['initial_officers']
                 if row['person_id'] not in {'san14-candidate-0771', 'san14-candidate-0830'}]
        self.assertEqual(digest(other),
                         'df7a4eaf8bc6a91ec68d4a12ad3e943906536151c119773be1ab0a7d76353cfe')

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
                ma_family = next(row for row in data['factions'] if row['id'] == 'ma_teng')
                self.assertEqual(ma_family['city'], baseline[6])


if __name__ == '__main__':
    unittest.main()
