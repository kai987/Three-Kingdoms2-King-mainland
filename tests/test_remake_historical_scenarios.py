"""Reviewed historical factions, border ownership and dated opening personnel.

Assertions use the published catalogs and actual campaign initialization/save
services. Region proxies in the history audit are not treated as proof that a
whole historical commandery was controlled by a particular governor.
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Campaign, Catalog


HAN_SUI_CHAPTERS = (
    '190-01', '191-10', '194-06', '196-06', '198-03', '200-01',
    '202-06', '207-09', '208-10', '211-07-tongguan', '212-12',
)
HAN_SUI_OFFICERS = {
    'san14-candidate-0166',  # Han Sui
    'san14-candidate-0030',  # Yan Xing
    'san14-candidate-0475',  # Chenggong Ying, service begins in189
}
EARLY_GOVERNORS = {
    'yingchuan': ('kong_zhou', 'san14-candidate-0270'),
    'dongjun': ('qiao_mao', 'san14-candidate-0209'),
    'henei': ('wang_kuang', 'san14-candidate-0047'),
    'shanyang': ('yuan_yi', 'san14-candidate-0024'),
    'dongping': ('bao_xin', 'san14-candidate-0826'),
}
GOVERNORS_191 = {
    'chenliu': ('zhang_miao', 'san14-candidate-0653'),
    'shanyang': ('yuan_yi', 'san14-candidate-0024'),
    'dongping': ('bao_xin', 'san14-candidate-0826'),
}
JINGNAN = {
    'changsha': ('han_xuan', {'san14-candidate-0158', 'san14-candidate-0271',
                            'san14-candidate-0189'}),
    'wuling': ('jin_xuan', {'san14-candidate-0223', 'san14-candidate-0204'}),
    'guiyang': ('zhao_fan', {'san14-candidate-0654', 'san14-candidate-0668',
                           'san14-candidate-0831'}),
    'lingling': ('liu_du', {'san14-candidate-0949', 'san14-candidate-0934',
                          'san14-candidate-0228'}),
}


class HistoricalScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / 'game/data'
        index = json.loads((directory / 'campaigns/index.json').read_text())
        cls.catalogs = {}
        for name in index['catalogs']:
            catalog = Catalog(directory / name)
            cls.catalogs[catalog.data['id']] = catalog
        cls.people = json.loads((ROOT / 'game/config/campaigns/people.json').read_text())['people']

    def catalog(self, chapter):
        return self.catalogs['mainland' + chapter]

    def game(self, chapter, faction=None):
        catalog = self.catalog(chapter)
        game = Campaign(catalog)
        game.state = game._new(faction or next(iter(catalog.factions)), 2026)
        game.validate(game.state)
        return game

    def assert_ruler(self, game, faction, person_id):
        ident = game.catalog.ids[person_id]
        self.assertEqual(game.state.extension['leaders'][faction], ident)
        self.assertEqual(game.catalog.data['faction_rulers'][faction], ident)
        self.assertEqual(game.state.officers[ident].faction_id, faction)
        row = next(row for row in game.catalog.data['initial_officers']
                   if row['person_id'] == person_id)
        self.assertIs(row['ruler'], True)

    def test_han_sui_is_an_independent_ruler_in_all_eleven_relevant_openings(self):
        for chapter in HAN_SUI_CHAPTERS:
            with self.subTest(chapter=chapter):
                game = self.game(chapter, 'han_sui')
                self.assertEqual(game.catalog.factions['han_sui']['city'], 'jincheng')
                self.assertEqual(game.state.cities['jincheng'].owner, 'han_sui')
                self.assert_ruler(game, 'han_sui', 'san14-candidate-0166')
                for person_id in HAN_SUI_OFFICERS:
                    ident = game.catalog.ids[person_id]
                    officer = game.state.officers[ident]
                    assignment = game.catalog.data['era_assignments'][person_id]
                    self.assertEqual(officer.faction_id, 'han_sui')
                    self.assertEqual(assignment['faction'], 'han_sui')
                    self.assertIn(ident, game.state.cities[assignment['city']].roster.officer_ids)
        self.assertIn('han_sui', self.catalog('188-06').factions)
        for chapter in ('184-02', '215-08', '217-07', '219-07', '221-07',
                        '225-07', '227-02', '234-02', '238-01', '249-01', '263-05'):
            with self.subTest(no_han_sui=chapter):
                self.assertNotIn('han_sui', self.catalog(chapter).factions)

    def test_tongguan_border_cities_do_not_assume_later_cao_control(self):
        for chapter in ('211-07-tongguan', '212-12'):
            with self.subTest(chapter=chapter):
                game = self.game(chapter, 'han_sui')
                for city in ('wudu', 'yinping'):
                    self.assertEqual(game.catalog.data['initial_owners'][city], 'neutral')
                    self.assertEqual(game.state.cities[city].owner, 'neutral')

    def test_188_sun_jian_governs_changsha_after_ou_xings_defeat(self):
        game = self.game('188-06', 'sun_jian')
        expected = {'san14-candidate-0551', 'san14-candidate-0703',
                    'san14-candidate-0247', 'san14-candidate-0176',
                    'san14-candidate-0390'}
        self.assertNotIn('ou_xing', game.catalog.factions)
        self.assertEqual(game.catalog.factions['sun_jian']['city'], 'changsha')
        self.assertEqual(game.state.cities['changsha'].owner, 'sun_jian')
        self.assert_ruler(game, 'sun_jian', 'san14-candidate-0551')
        stationed = {game.state.officers[ident].person_id
                     for ident in game.state.cities['changsha'].roster.officer_ids}
        self.assertEqual(stationed, expected)
        for person_id in expected:
            with self.subTest(person_id=person_id):
                officer = game.state.officers[game.catalog.ids[person_id]]
                self.assertEqual(officer.faction_id, 'sun_jian')
                assignment = game.catalog.data['era_assignments'][person_id]
                self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                                 ('serving', 'sun_jian', 'changsha'))
        excluded = 'san14-candidate-0065'
        self.assertEqual(game.catalog.data['era_assignments'][excluded]['status'], 'scenario_excluded')
        self.assertNotIn(game.catalog.ids[excluded], game.state.officers)
        definition = game.catalog.definitions[excluded]
        self.assertEqual(definition.death_year, self.people[excluded]['death_year'])
        game._spawn_eligible(game.state)
        self.assertNotIn(game.catalog.ids[excluded], game.state.officers)
        game.validate(game.state)

    def test_212_december_has_the_actual_entry_frontier_and_no_retired_guards(self):
        game = self.game('212-12', 'shu')
        self.assertEqual((game.state.year, game.state.month), (212, 12))
        self.assertNotIn('mainland211-07', self.catalogs)
        for city in ('jiameng', 'fuxian'):
            self.assertEqual(game.state.cities[city].owner, 'shu')
        self.assertEqual(game.catalog.factions['wu']['city'], 'danyang')
        self.assert_ruler(game, 'gongsun', 'san14-candidate-0264')
        self.assertEqual(game.state.extension['leaders']['gongsun'], 263)
        retired = {'san14-candidate-0632', 'san14-candidate-0854',
                   'san14-candidate-0274'}  # Zhang Song, Yang Huai, Gao Pei
        initial = {row['person_id'] for row in game.catalog.data['initial_officers']}
        free = {row['person_id'] for row in game.catalog.data.get('initial_free_officers', [])}
        self.assertTrue(retired.isdisjoint(initial | free))
        for person_id in retired:
            self.assertNotIn(game.catalog.ids[person_id], game.state.officers)
        # A monthly appearance pass may not undo the explicit opening deaths.
        game._spawn_eligible(game.state)
        for person_id in retired:
            self.assertNotIn(game.catalog.ids[person_id], game.state.officers)
        game.validate(game.state)

    def test_jingnan_prefects_have_their_named_subordinates_instead_of_empty_retinues(self):
        game = self.game('208-10', 'han_xuan')
        for city, (faction, expected) in JINGNAN.items():
            with self.subTest(city=city):
                self.assertEqual(game.state.cities[city].owner, faction)
                members = {officer.person_id for officer in game.state.officers.values()
                           if officer.faction_id == faction}
                self.assertEqual(members, expected)
                stationed = {game.state.officers[ident].person_id
                             for ident in game.state.cities[city].roster.officer_ids}
                self.assertEqual(stationed, expected)

    def test_early_governors_and_191_dongjun_follow_their_dated_posts(self):
        game = self.game('190-01')
        for city, (faction, person_id) in EARLY_GOVERNORS.items():
            with self.subTest(city=city):
                self.assertEqual(game.state.cities[city].owner, faction)
                self.assert_ruler(game, faction, person_id)
        self.assertEqual(game.state.cities['shangdang'].owner, 'zhang_yang')
        game = self.game('191-10', 'wei')
        self.assertEqual(game.state.cities['dongjun'].owner, 'wei')
        for city, (faction, person_id) in GOVERNORS_191.items():
            with self.subTest(chapter='191-10', city=city):
                self.assertEqual(game.state.cities[city].owner, faction)
                self.assert_ruler(game, faction, person_id)
        self.assertNotIn('qiao_mao', game.catalog.factions)

    def test_same_named_zhang_cheng_officers_keep_distinct_ids_and_allegiances(self):
        expected = {
            'san14-candidate-0634': ('wu', 633, 178, 197, 244),
            'san14-candidate-0635': ('wei', 634, 156, 184, 215),
        }
        profile_fields = ('health_max', 'martial_strength', 'intellect',
                          'virtue', 'terrain_affinity')
        for chapter in ('207-09', '208-10'):
            game = self.game(chapter)
            for person_id, (faction, ident, birth, service, death) in expected.items():
                with self.subTest(chapter=chapter, person_id=person_id):
                    self.assertEqual(game.catalog.ids[person_id], ident)
                    definition = game.catalog.definitions[person_id]
                    self.assertEqual(definition.name, '张承')
                    self.assertEqual((definition.birth_year, definition.service_year,
                                      definition.death_year), (birth, service, death))
                    officer = game.state.officers[ident]
                    self.assertEqual(officer.person_id, person_id)
                    self.assertEqual(officer.faction_id, faction)
                    self.assertEqual(tuple(getattr(officer.profile, key) for key in profile_fields),
                                     (80, 69, 75, 72, 0))
                    self.assertEqual(game.catalog.by_id[ident]['profile'],
                                     self.people[person_id]['profile'])
                    assignment = game.catalog.data['era_assignments'][person_id]
                    self.assertEqual(assignment['faction'], faction)
                    city = game.state.cities[assignment['city']]
                    self.assertEqual(city.owner, faction)
                    self.assertIn(ident, city.roster.officer_ids)

    def test_defeated_xu_gong_remains_alive_and_unaligned_in_wu(self):
        person_id = 'san14-candidate-0211'
        for chapter in ('196-06', '198-03', '200-01'):
            with self.subTest(chapter=chapter):
                game = self.game(chapter)
                ident = game.catalog.ids[person_id]
                officer = game.state.officers[ident]
                assignment = game.catalog.data['era_assignments'][person_id]
                self.assertEqual((assignment['status'], assignment['city']), ('free', 'wujun'))
                self.assertTrue(officer.alive)
                self.assertIsNone(officer.faction_id)
                self.assertEqual(game.state.extension['free_locations'][str(ident)], 'wujun')
                self.assertFalse(any(ident in city.roster.officer_ids
                                     for city in game.state.cities.values()))
                self.assertEqual(game.catalog.by_id[ident]['profile'],
                                 self.people[person_id]['profile'])
                if chapter == '200-01':
                    # His death year does not prove that he was dead in January.
                    self.assertEqual((game.state.year, game.state.month), (200, 1))
                    self.assertEqual(game.catalog.definitions[person_id].death_year, 200)

    def test_pre_210_lingnan_nodes_follow_their_parent_regions(self):
        for chapter, cangwu_owner in (('200-01', 'neutral'), ('202-06', 'neutral'),
                                      ('207-09', 'wu_ju'), ('208-10', 'wu_ju')):
            with self.subTest(chapter=chapter):
                game = self.game(chapter)
                self.assertEqual(game.state.cities['hepu'].owner, 'shi_xie')
                self.assertEqual(game.state.cities['gaoliang'].owner, 'shi_xie')
                self.assertEqual(game.state.cities['cangwu'].owner, cangwu_owner)
                self.assertEqual(game.state.cities['linhe'].owner, cangwu_owner)
        # Historical corrections do not rewrite this existing fictional opening.
        fictional = self.game('209-06')
        self.assertTrue(fictional.catalog.data['main_scenario']['fictional'])
        for city in ('gaoliang', 'linhe'):
            self.assertEqual(fictional.state.cities[city].owner, 'wu')

    def test_added_factions_can_start_and_restore_a_real_json_save(self):
        targets = [(chapter, 'han_sui') for chapter in HAN_SUI_CHAPTERS]
        targets += [('188-06', 'sun_jian')]
        targets += [('190-01', faction) for faction, _ in EARLY_GOVERNORS.values()]
        targets += [('191-10', faction) for faction, _ in GOVERNORS_191.values()]
        targets += [('208-10', faction) for faction, _ in JINGNAN.values()]
        for chapter, faction in targets:
            with self.subTest(chapter=chapter, faction=faction):
                game = Campaign(self.catalog(chapter))
                response = game.command('new', dict(faction=faction, seed=2026), 0)
                self.assertEqual(response['game']['player'], faction)
                self.assertEqual(game.state.phase, 'city')
                self.assertEqual(game.state.rng.draws, 0)
                leader = game.state.extension['leaders'][faction]
                self.assertTrue(game.state.officers[leader].alive)
                self.assertTrue(any(city.owner == faction and leader in city.roster.officer_ids
                                    for city in game.state.cities.values()))
                saved = json.loads(json.dumps(game.export_save(), ensure_ascii=False))
                restored = Campaign(game.catalog)
                restored.load_save(saved, 0)
                self.assertEqual(restored.export_save(), saved)
                self.assertEqual(restored.to_dict(), game.to_dict())
                restored.validate(restored.state)

    def test_all_openings_keep_stable_abilities_and_consistent_bounded_garrisons(self):
        self.assertEqual(len(self.catalogs), 29)
        historical = [catalog for catalog in self.catalogs.values()
                      if not catalog.data['main_scenario'].get('fictional', False)]
        self.assertEqual(len(historical), 23)
        for catalog in self.catalogs.values():
            with self.subTest(chapter=catalog.data['id']):
                self.assertEqual(set(catalog.ids), set(self.people))
                for row in catalog.data['people']:
                    original = self.people[row['person_id']]
                    self.assertEqual(row['runtime_id'], original['runtime_id'])
                    self.assertEqual(row['profile'], original['profile'])
                game = Campaign(catalog)
                game.state = game._new(next(iter(catalog.factions)), 2026)
                game.validate(game.state)
                self.assertEqual(catalog.rules.city_officer_capacity, 99)
                self.assertEqual(catalog.rules.battle_officers_per_side, 10)
                for faction, metadata in catalog.factions.items():
                    self.assertEqual(game.state.cities[metadata['city']].owner, faction,
                                     'An opening capital must still belong to its displayed faction')
                seen = set()
                for city in game.state.cities.values():
                    self.assertLessEqual(len(city.roster.officer_ids), 99)
                    for ident in city.roster.officer_ids:
                        self.assertNotIn(ident, seen)
                        seen.add(ident)
                        officer = game.state.officers[ident]
                        assignment = catalog.data['era_assignments'][officer.person_id]
                        self.assertEqual(officer.faction_id, city.owner)
                        context = (catalog.data['id'], officer.person_id, city.id)
                        self.assertEqual(assignment['status'], 'serving', context)
                        self.assertEqual(assignment['faction'], city.owner, context)
                        self.assertEqual(assignment['city'], city.id, context)


if __name__ == '__main__':
    unittest.main()
