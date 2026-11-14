"""Reviewed historical factions, border ownership and dated opening personnel.

Assertions use the published catalogs and actual campaign initialization/save
services. Region proxies in the history audit are not treated as proof that a
whole historical commandery was controlled by a particular governor.
"""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Campaign, Catalog
from remake.dated_events import visible_factions
from remake.session import CampaignSession, faction_officer_counts, faction_resources


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


def expansion_material(data):
    plan = json.loads((ROOT / 'game/config/campaigns/city-expansion-openings.json').read_text())
    opened = set(plan['scenarios'][data['id']]['owners'])
    # These baselines predate opening the old county seats. Their existing
    # late-game stocks were already counted at the original opening dates.
    date = (data['start_year'], data['start_month'])
    for city, former_opening in (('wuchang', (221, 4)), ('jianan', (260, 10))):
        if city in data['active_cities'] and date < former_opening:
            opened.add(city)
    return tuple(sum(data['initial_city_resources'][city][field] for city in opened)
                 for field in ('gold', 'grain', 'reserves'))


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
                    'san14-candidate-0390', 'san14-candidate-0289',
                    'san14-candidate-0543'}
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

    def test_196_liu_bei_has_four_additional_retainers_at_xiapi(self):
        game = self.game('196-06', 'shu')
        city = game.state.cities['xiapi']
        self.assertEqual(game.catalog.factions['shu']['city'], 'xiapi')
        self.assertEqual(city.owner, 'shu')
        abilities = {
            'historical-xiahou-bo': (78, 53, 65),
            'historical-xue-yong': (75, 68, 77),
            'historical-yuan-chen': (73, 51, 75),
            'historical-liu-yan-shu': (41, 70, 75),
        }
        for person_id, stats in abilities.items():
            with self.subTest(person=person_id):
                ident = game.catalog.ids[person_id]
                officer = game.state.officers[ident]
                self.assertIn(ident, city.roster.officer_ids)
                self.assertEqual(officer.faction_id, 'shu')
                self.assertTrue(officer.alive)
                self.assertEqual((officer.profile.martial_strength, officer.profile.intellect,
                                  officer.profile.virtue), stats)

    def test_early_shu_retainers_follow_dated_openings_and_death_boundaries(self):
        last_opening = {
            'historical-xiahou-bo': (200, 1),
            'historical-xue-yong': (238, 1),
            'historical-yuan-chen': (238, 1),
            'historical-liu-yan-shu': (234, 2),
        }
        for scenario, catalog in self.catalogs.items():
            date = (catalog.data['start_year'], catalog.data['start_month'])
            serving = {row['person_id']: row for row in catalog.data['initial_officers']}
            for person_id, latest in last_opening.items():
                with self.subTest(scenario=scenario, person=person_id):
                    if not (196, 6) <= date <= latest:
                        self.assertNotIn(person_id, serving)
                        self.assertFalse(catalog.data['appearance_windows'][person_id])
                        continue
                    city = catalog.factions['shu']['city']
                    if person_id == 'historical-liu-yan-shu':
                        if date[0] in (215, 217, 219):
                            city = 'badong'
                        elif date == (227, 2):
                            city = 'hanzhong'
                    if person_id == 'historical-yuan-chen' and date >= (227, 2):
                        city = 'hanzhong'
                    self.assertEqual(serving[person_id]['city'], city)
                    self.assertEqual(catalog.data['initial_owners'][city], 'shu')
                    assignment = catalog.data['era_assignments'][person_id]
                    self.assertEqual((assignment['faction'], assignment['city']), ('shu', city))
                    self.assertEqual(catalog.data['appearance_locations'][person_id], city)
        for person_id in last_opening:
            chronology = self.people[person_id]['chronology_design']
            self.assertEqual(chronology['historical_death_year'],
                             234 if person_id == 'historical-liu-yan-shu' else None)
        for chapter, person_id, city in (
            ('200-01', 'historical-xiahou-bo', 'qiao'),
            ('234-02', 'historical-liu-yan-shu', 'shujun'),
            ('238-01', 'historical-yuan-chen', 'hanzhong'),
        ):
            with self.subTest(chapter=chapter):
                game = self.game(chapter, 'shu')
                ident = game.catalog.ids[person_id]
                self.assertTrue(game.state.officers[ident].alive)
                self.assertIn(ident, game.state.cities[city].roster.officer_ids)

    def test_guandu_liu_bei_and_zhang_fei_start_at_xiaopei_while_guan_yu_guards_xiapi(self):
        game = self.game('200-01', 'shu')
        self.assertEqual(game.catalog.factions['shu']['city'], 'qiao')
        self.assert_ruler(game, 'shu', 'san14-candidate-0952')
        for city, faction, person_id in (
            ('qiao', 'shu', 'san14-candidate-0952'),
            ('qiao', 'shu', 'san14-candidate-0656'),
            ('xiapi', 'shu', 'san14-candidate-0147'),
            ('jiyin', 'wei', 'san14-candidate-0971'),
            ('yingchuan', 'wei', 'san14-candidate-0999'),
        ):
            with self.subTest(city=city, person=person_id):
                ident = game.catalog.ids[person_id]
                self.assertEqual(game.state.cities[city].owner, faction)
                self.assertEqual(game.state.officers[ident].faction_id, faction)
                self.assertIn(ident, game.state.cities[city].roster.officer_ids)

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
                for metadata in visible_factions(catalog):
                    faction=metadata["id"]
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


class EarlyIndependentRulerTests(unittest.TestCase):
    """Coalition members keep their people when a local command is separated.

    These expectations describe the reviewed opening snapshots, including the
    explicitly approved Jiwu/Qiao and Kaiyang/Donghai regional proxies. They do
    not infer that every later ruler was already independent in earlier years.
    """

    CHAPTERS = ('188-06', '190-01', '194-06', '196-06', '197-07', '198-03', '200-01')
    CAO_190_CAMP = {
        'san14-candidate-0071', 'san14-candidate-0102', 'san14-candidate-0114',
        'san14-candidate-0124', 'san14-candidate-0333', 'san14-candidate-0365',
        'san14-candidate-0441', 'san14-candidate-0505', 'san14-candidate-0510',
        'san14-candidate-0511', 'san14-candidate-0514', 'san14-candidate-0518',
        'san14-candidate-0521', 'san14-candidate-0671', 'san14-candidate-0702',
        'san14-candidate-0816', 'san14-candidate-0913',
    }
    ZANG_GROUP = {
        'san14-candidate-0525', 'san14-candidate-0545',
        'san14-candidate-0308', 'san14-candidate-0014',
    }
    # Published69a6e8f active-world totals before changing any allegiances.
    # The frozen conservation boundary excludes future cities and the later
    # map expansion. Converting an officer to free/dead returns his 300
    # troops to the original city; restoring Fan Chou consumes 300 reserves.
    ACTIVE_WORLD_BASELINE = {
        '188-06': (147640, 520075, 187860),
        '190-01': (143240, 495475, 223570),
        '194-06': (139030, 480975, 232740),
        '196-06': (136810, 472400, 230410),
        '197-07': (137820, 477325, 227180),
        '198-03': (137830, 477325, 232880),
    }

    @classmethod
    def setUpClass(cls):
        cls.paths = [ROOT / f'game/data/campaigns/{chapter}.json'
                     for chapter in cls.CHAPTERS]
        cls.catalogs = {chapter: Catalog(path)
                        for chapter, path in zip(cls.CHAPTERS, cls.paths)}
        cls.people = json.loads((ROOT / 'game/config/campaigns/people.json').read_text())['people']

    def game(self, chapter, faction=None):
        catalog = self.catalogs[chapter]
        game = Campaign(catalog)
        game.command('new', dict(faction=faction or next(iter(catalog.factions)), seed=2026), 0)
        game.validate(game.state)
        return game

    def assert_posting(self, game, person_id, faction, city, *, ruler=False):
        catalog = game.catalog
        ident = catalog.ids[person_id]
        self.assertEqual(ident, self.people[person_id]['runtime_id'])
        self.assertEqual(catalog.by_id[ident]['profile'], self.people[person_id]['profile'])
        self.assertEqual(game.state.officers[ident].faction_id, faction)
        self.assertIn(ident, game.state.cities[city].roster.officer_ids)
        assignment = catalog.data['era_assignments'][person_id]
        self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                         ('serving', faction, city))
        self.assertEqual((assignment['posting_reference']['faction'],
                          assignment['posting_reference']['city']), (faction, city))
        self.assertEqual((assignment['appearance_plan']['status'],
                          assignment['appearance_plan']['city']), ('serving', city))
        self.assertEqual(catalog.data['appearance_locations'][person_id], city)
        initial = next(row for row in catalog.data['initial_officers']
                       if row['person_id'] == person_id)
        self.assertEqual(initial['ruler'], ruler)
        self.assertEqual(initial['troops'], 300)
        if ruler:
            self.assertEqual(catalog.data['faction_rulers'][faction], ident)
            self.assertEqual(game.state.extension['leaders'][faction], ident)
            self.assertEqual(catalog.factions[faction]['captain'], catalog.definitions[person_id].name)

    def assert_free_posting(self, game, person_id, city):
        ident = game.catalog.ids[person_id]
        officer = game.state.officers[ident]
        self.assertTrue(officer.alive)
        self.assertIsNone(officer.faction_id)
        self.assertEqual(game.state.extension['free_locations'][str(ident)], city)
        self.assertFalse(any(ident in c.roster.officer_ids for c in game.state.cities.values()))
        assignment = game.catalog.data['era_assignments'][person_id]
        self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                         ('free', None, city))
        self.assertEqual((assignment['appearance_plan']['status'],
                          assignment['appearance_plan']['city']), ('free', city))
        free = {row['person_id']: row for row in game.catalog.data['initial_free_officers']}
        self.assertEqual(free[person_id]['city'], city)
        self.assertEqual(game.catalog.data['appearance_locations'][person_id], city)

    def test_190_chenliu_governor_and_cao_camp_have_separate_leaders_and_retinues(self):
        game = self.game('190-01', 'zhang_miao')
        self.assertEqual(game.state.cities['chenliu'].owner, 'zhang_miao')
        self.assertEqual(game.state.cities['qiao'].owner, 'wei')
        self.assertEqual(game.catalog.factions['wei']['city'], 'qiao')
        self.assert_posting(game, 'san14-candidate-0653', 'zhang_miao', 'chenliu', ruler=True)
        self.assert_posting(game, 'san14-candidate-0021', 'zhang_miao', 'chenliu')
        for person_id in self.CAO_190_CAMP:
            with self.subTest(person_id=person_id):
                self.assert_posting(game, person_id, 'wei', 'qiao',
                                    ruler=person_id == 'san14-candidate-0521')
        self.assertEqual(faction_officer_counts(game.catalog)['wei'], 17)
        self.assert_posting(game, 'san14-candidate-0709', 'zhang_miao', 'chenliu')
        self.assert_posting(game, 'historical-zhao-chong', 'zhang_miao', 'chenliu')
        self.assertEqual(faction_officer_counts(game.catalog)['zhang_miao'], 4)
        # Zhang Chao was already a separate Donghai governor, not a spare
        # member to be moved to his brother's newly represented command.
        self.assert_posting(game, 'san14-candidate-0647', 'zhang_chao', 'donghai', ruler=True)
        self.assert_posting(game, 'san14-candidate-0512', 'zhang_chao', 'donghai')

    def test_northern_liu_bei_party_and_hua_xin_envoy_do_not_follow_wrong_overlords(self):
        game = self.game('188-06')
        for person_id in ('san14-candidate-0952', 'san14-candidate-0147', 'san14-candidate-0656'):
            self.assert_free_posting(game, person_id, 'zhongshan')
        self.assertNotIn('shu', game.catalog.factions)
        self.assert_posting(game, 'san14-candidate-0925', 'liu_yan', 'shujun', ruler=True)
        game._spawn_eligible(game.state)
        for person_id in ('san14-candidate-0952', 'san14-candidate-0147', 'san14-candidate-0656'):
            self.assert_free_posting(game, person_id, 'zhongshan')
        game = self.game('194-06')
        self.assert_free_posting(game, 'san14-candidate-0091', 'xiapi')
        self.assert_posting(game, 'san14-candidate-0080', 'wang_lang', 'kuaiji', ruler=True)

    def test_zhang_ji_commands_hongnong_before_nephews_undated_196_succession(self):
        for chapter in ('194-06', '196-06'):
            with self.subTest(chapter=chapter):
                game = self.game(chapter, 'zhang_ji')
                self.assertEqual(game.state.cities['hongnong'].owner, 'zhang_ji')
                self.assertEqual(game.catalog.factions['zhang_ji']['city'], 'hongnong')
                self.assert_posting(game, 'san14-candidate-0638', 'zhang_ji', 'hongnong', ruler=True)
                self.assert_posting(game, 'san14-candidate-0625', 'zhang_ji', 'hongnong')
                self.assertNotIn('zhang_xiu', game.catalog.factions)
                # Neither a later famous adviser nor an old Li Jue garrison
                # should be silently swept into the newly separated army.
                for person_id in ('san14-candidate-0092', 'san14-candidate-0296'):
                    officer = game.state.officers[game.catalog.ids[person_id]]
                    self.assertEqual(officer.faction_id, 'li_jue')
                before = game.to_dict()
                game._spawn_eligible(game.state)
                game._reconcile_factions(game.state)
                game.validate(game.state)
                self.assertEqual(game.to_dict(), before)

    def test_zang_bas_named_band_remains_distinct_from_liu_bei_and_lu_bu(self):
        game = self.game('196-06')
        self.assertEqual(game.state.cities['donghai'].owner, 'shu')
        for person_id in self.ZANG_GROUP:
            self.assert_free_posting(game, person_id, 'donghai')
        self.assert_posting(game, 'san14-candidate-0147', 'shu', 'donghai')
        for chapter in ('197-07', '198-03'):
            with self.subTest(chapter=chapter):
                game = self.game(chapter, 'zang_ba')
                self.assertEqual(game.state.cities['donghai'].owner, 'zang_ba')
                for person_id in self.ZANG_GROUP:
                    self.assert_posting(game, person_id, 'zang_ba', 'donghai',
                                        ruler=person_id == 'san14-candidate-0525')
                # The displaced regular garrison keeps its own allegiance.
                preserved = {
                    '197-07': ('shu', ('san14-candidate-0147', 'san14-candidate-0185',
                                      'san14-candidate-0656',
                                      'san14-candidate-0674', 'san14-candidate-0793')),
                    '198-03': ('lubu', ('san14-candidate-0043', 'san14-candidate-0188',
                                       'san14-candidate-0212', 'san14-candidate-0254',
                                       'san14-candidate-0456', 'san14-candidate-0507',
                                       'san14-candidate-0663', 'san14-candidate-0750')),
                }
                faction, person_ids = preserved[chapter]
                for person_id in person_ids:
                    ident = game.catalog.ids[person_id]
                    self.assertEqual(game.state.officers[ident].faction_id, faction)
                    city = game.catalog.data['era_assignments'][person_id]['city']
                    self.assertEqual(game.state.cities[city].owner, faction)
                    self.assertIn(ident, game.state.cities[city].roster.officer_ids)
                    self.assertNotEqual(city, 'donghai')
                if chapter == '197-07':
                    # Chang Xi's local band is not an ordinary Liu Bei unit.
                    self.assert_free_posting(game, 'san14-candidate-0409', 'donghai')

    def test_early_chronology_does_not_revive_governor_liu_dai_or_kill_fan_chou_in_192(self):
        liu_dai = 'san14-candidate-0947'
        for chapter in ('194-06', '196-06', '198-03', '200-01'):
            game = self.game(chapter)
            ident = game.catalog.ids[liu_dai]
            self.assertEqual(game.catalog.definitions[liu_dai].death_year, 192)
            self.assertNotIn(ident, game.state.officers)
            game._spawn_eligible(game.state)
            self.assertNotIn(ident, game.state.officers)
        # The explicitly fictional197 opening keeps its authored homonym.
        fictional = self.game('197-07')
        self.assertTrue(fictional.catalog.data['main_scenario']['fictional'])
        self.assertEqual(fictional.state.officers[fictional.catalog.ids[liu_dai]].faction_id, 'wei')
        game = self.game('194-06', 'li_jue')
        fan_chou = 'san14-candidate-0782'
        self.assertEqual(game.catalog.definitions[fan_chou].death_year, 195)
        self.assert_posting(game, fan_chou, 'li_jue', game.catalog.factions['li_jue']['city'])

    def test_valid_early_service_and_later_surrenders_are_not_split_again(self):
        expected = {
            '190-01': {'san14-candidate-0080': 'tao_qian', 'san14-candidate-0557': 'sun_jian'},
            '191-10': {'san14-candidate-0666': 'liu_yan'},
            '194-06': {'san14-candidate-0557': 'yuan_shu'},
            '198-03': {'san14-candidate-0080': 'wei', 'san14-candidate-0280': 'wei'},
            '200-01': {'san14-candidate-0091': 'wu', 'san14-candidate-0625': 'wei',
                        'san14-candidate-0037': 'yuan_shao', 'san14-candidate-0029': 'yuan_shao',
                        'san14-candidate-0034': 'yuan_shao', 'san14-candidate-0248': 'yuan_shao',
                        'san14-candidate-0769': 'ma_teng'},
        }
        for chapter, members in expected.items():
            catalog = self.catalogs.get(chapter) or Catalog(ROOT / f'game/data/campaigns/{chapter}.json')
            game = Campaign(catalog)
            game.state = game._new(next(iter(catalog.factions)), 2026)
            for person_id, faction in members.items():
                with self.subTest(chapter=chapter, person_id=person_id):
                    self.assertEqual(game.state.officers[catalog.ids[person_id]].faction_id, faction)

    def test_early_metadata_counts_and_available_manpower_match_actual_openings(self):
        for chapter, catalog in self.catalogs.items():
            with self.subTest(chapter=chapter):
                game = self.game(chapter)
                data = catalog.data
                serving = data['initial_officers']
                free = data['initial_free_officers']
                self.assertEqual(data['coverage']['initial_serving'], len(serving))
                self.assertEqual(data['coverage']['initial_free'], len(free))
                self.assertEqual(data['coverage']['planned_serving'], len(serving))
                max_roster = max(len(city.roster.officer_ids) for city in game.state.cities.values())
                self.assertEqual(data['coverage']['planned_max_city_roster'], max_roster)
                self.assertEqual(data['placement_completion']['reference_classes'], dict(Counter(
                    a['placement_review']['historical_certainty'] for a in data['era_assignments'].values())))
                self.assertEqual(data['placement_completion']['bases'], dict(Counter(
                    a['placement_review']['basis'] for a in data['era_assignments'].values())))
                counts = faction_officer_counts(catalog, game.state)
                self.assertEqual(faction_officer_counts(catalog), counts)
                self.assertEqual(faction_resources(catalog), faction_resources(catalog, game.state))
                for faction, metadata in catalog.factions.items():
                    self.assertEqual(metadata['initial_officers'], counts[faction])
                    leader = data['faction_rulers'][faction]
                    self.assertEqual(metadata['captain'], catalog.by_id[leader]['name'])
                    self.assertEqual(game.state.extension['leaders'][faction], leader)
                    self.assertEqual(game.state.cities[metadata['city']].owner, faction)
                if chapter in self.ACTIVE_WORLD_BASELINE:
                    totals = (sum(city.gold for city in game.state.cities.values()),
                              sum(city.grain for city in game.state.cities.values()),
                              sum(city.reserves for city in game.state.cities.values()) +
                              sum(officer.troops for officer in game.state.officers.values()))
                    expected = tuple(old + added for old, added in zip(
                        self.ACTIVE_WORLD_BASELINE[chapter], expansion_material(data)))
                    self.assertEqual(totals, expected)
                    self.assertEqual(game.state.soldiers['initial'], totals[2])

    def test_new_local_commands_start_preview_and_restore_without_changing_membership(self):
        session = CampaignSession(self.paths)
        targets = (('190-01', 'zhang_miao', 'chenliu'),
                   ('194-06', 'zhang_miao', 'chenliu'), ('194-06', 'zhang_ji', 'hongnong'),
                   ('196-06', 'zhang_ji', 'hongnong'), ('197-07', 'zang_ba', 'donghai'),
                   ('198-03', 'zang_ba', 'donghai'))
        for chapter, faction, city in targets:
            with self.subTest(chapter=chapter, faction=faction):
                scenario = 'mainland' + chapter
                response = session.command('new', dict(scenario=scenario, faction=faction,
                                                       seed=2026), session.revision)
                self.assertEqual(response['game']['player'], faction)
                self.assertEqual(session.game.state.phase, 'city')
                self.assertEqual(session.game.state.rng.draws, 0)
                save = json.loads(json.dumps(session.export_save(), ensure_ascii=False))
                leader = session.game.state.extension['leaders'][faction]
                preview = session.preview_city(scenario, city)['city']
                self.assertEqual(preview['owner'], faction)
                self.assertEqual([row['id'] for row in preview['officers'] if row['is_ruler']], [leader])
                summary = next(row for row in response['catalog']['scenarios'] if row['id'] == scenario)
                metadata = next(row for row in summary['factions'] if row['id'] == faction)
                self.assertEqual(metadata['ruler_person_id'], session.game.state.officers[leader].person_id)
                self.assertEqual(summary['initial_owners'][city], faction)
                self.assertEqual(summary['faction_officers'][faction], len(preview['officers']))
                self.assertEqual(session.export_save(), save)
                restored = CampaignSession(self.paths)
                restored.load_save(save, 0)
                self.assertEqual(restored.export_save(), save)
                self.assertEqual(restored.game.to_dict(), session.game.to_dict())
                restored.game.validate(restored.game.state)


class FrozenRulerAuditNegativeTests(unittest.TestCase):
    """A structurally plausible drift must still fail the authored review.

    Every mutation is an in-memory copy. Neither the accepted reference nor
    compiled catalogs are regenerated to make a negative example pass.
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'ruler_affiliation_negative_tests', ROOT / 'tools/scenario-history/ruler_audit.py')
        cls.checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.checker)
        reference = json.loads((ROOT / 'game/config/references/ruler-affiliation-review.json').read_text())
        cls.pool = {row['person_id']: row for row in reference['pool']}
        cls.decision = next(row for row in reference['scenarios'] if row['id'] == 'mainland194-06')
        cls.data = json.loads((ROOT / 'game/data/campaigns/194-06.json').read_text())
        cls.presentation = json.loads((ROOT / 'game/assets/map-presentation.json').read_text())['city_names']

    def check_copy(self, data=None, decision=None):
        return self.checker.check_catalog(data if data is not None else deepcopy(self.data),
                                          decision if decision is not None else deepcopy(self.decision),
                                          self.pool, self.presentation)

    def test_accepted_snapshot_matches_the_frozen_decision(self):
        result = self.check_copy()
        self.assertEqual(result['id'], 'mainland194-06')
        self.assertEqual(len(result['people']), 67)
        self.assertEqual(result['material'], self.decision['material'])

    def test_noncanonical_captain_is_rejected(self):
        data = deepcopy(self.data)
        next(row for row in data['factions'] if row['id'] == 'zhang_miao')['captain'] = '呂布'
        with self.assertRaisesRegex(ValueError, 'captain is not canonical ruler name'):
            self.check_copy(data)

    def test_another_valid_person_id_cannot_replace_the_reviewed_ruler(self):
        data = deepcopy(self.data)
        person = next(row for row in data['people'] if row['person_id'] == 'san14-candidate-0638')
        data['faction_rulers']['zhang_miao'] = person['runtime_id']
        next(row for row in data['factions'] if row['id'] == 'zhang_miao')['captain'] = person['name']
        with self.assertRaisesRegex(ValueError, 'frozen ruler/capital differs'):
            self.check_copy(data)

    def test_a_capital_cannot_point_to_an_allied_factions_city(self):
        data = deepcopy(self.data)
        next(row for row in data['factions'] if row['id'] == 'zhang_miao')['city'] = 'dongjun'
        with self.assertRaisesRegex(ValueError, 'ruler capital has wrong owner'):
            self.check_copy(data)

    def test_a_ruler_flag_cannot_be_removed_from_the_opening_roster(self):
        data = deepcopy(self.data)
        next(row for row in data['initial_officers']
             if row['person_id'] == 'san14-candidate-0653')['ruler'] = False
        with self.assertRaisesRegex(ValueError, 'ruler is not flagged at its own capital'):
            self.check_copy(data)

    def test_missing_and_duplicate_frozen_candidate_rows_are_rejected(self):
        decision = deepcopy(self.decision)
        decision['people'].pop()
        with self.assertRaisesRegex(ValueError, 'cover all 67 candidates exactly once'):
            self.check_copy(decision=decision)
        decision = deepcopy(self.decision)
        decision['people'].append(deepcopy(decision['people'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate person_id'):
            self.check_copy(decision=decision)

    def test_coherent_serving_reassignment_cannot_rewrite_the_frozen_affiliation(self):
        data = deepcopy(self.data)
        person_id = 'san14-candidate-0625'  # Zhang Xiu follows Zhang Ji, not Li Jue.
        destination = next(row for row in data['factions'] if row['id'] == 'li_jue')['city']
        era = data['era_assignments'][person_id]
        era.update(faction='li_jue', city=destination)
        era['posting_reference'].update(faction='li_jue', city=destination)
        era['appearance_plan']['city'] = destination
        data['appearance_locations'][person_id] = destination
        next(row for row in data['initial_officers'] if row['person_id'] == person_id)['city'] = destination
        for faction in data['factions']:
            if faction['id'] == 'zhang_ji':
                faction['initial_officers'] -= 1
            elif faction['id'] == 'li_jue':
                faction['initial_officers'] += 1
        # Identity, status, provenance counters and total carried manpower all
        # remain coherent. Only the independently frozen decision catches this.
        self.assertEqual(data['placement_completion'], self.data['placement_completion'])
        self.assertEqual(sum(row['troops'] for row in data['initial_officers']),
                         sum(row['troops'] for row in self.data['initial_officers']))
        with self.assertRaisesRegex(ValueError, 'frozen placement differs: ' + person_id):
            self.check_copy(data)

    def test_stale_placement_provenance_counter_is_rejected(self):
        data = deepcopy(self.data)
        key = next(iter(data['placement_completion']['bases']))
        data['placement_completion']['bases'][key] += 1
        with self.assertRaisesRegex(ValueError, 'placement provenance counter is stale: bases'):
            self.check_copy(data)

    def test_active_city_money_grain_and_manpower_cannot_drift(self):
        for field in ('gold', 'grain', 'reserves'):
            with self.subTest(field=field):
                data = deepcopy(self.data)
                data['initial_city_resources']['chenliu'][field] += 1
                with self.assertRaisesRegex(ValueError, 'totals differ from frozen pre-change material'):
                    self.check_copy(data)

    def test_unopened_future_city_stocks_are_outside_active_world_material_totals(self):
        data = deepcopy(self.data)
        inactive = next(city for city in data['initial_city_resources'] if city not in data['active_cities'])
        data['initial_city_resources'][inactive]['reserves'] += 100
        self.assertEqual(self.check_copy(data)['material'], self.decision['material'])

    def test_reviewed_lifetime_and_its_evidence_basis_cannot_silently_drift(self):
        person_id = 'san14-candidate-0782'  # Fan Chou: killed in195, not192.
        reviewed = next(row for row in self.decision['chronology'] if row['person_id'] == person_id)
        self.assertEqual(reviewed['death_year'], 195)
        for field, value in (('death_year', 192), ('chronology_basis', 'unreviewed_source_replacement')):
            with self.subTest(field=field):
                data = deepcopy(self.data)
                next(row for row in data['people'] if row['person_id'] == person_id)[field] = value
                with self.assertRaisesRegex(ValueError, 'frozen chronology differs: ' + person_id):
                    self.check_copy(data)


if __name__ == '__main__':
    unittest.main()
