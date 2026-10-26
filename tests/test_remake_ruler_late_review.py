"""Dated former rulers remain distinct from heirs, guests and unavailable people.

The reviewed openings must not turn a captive or a deposed sovereign into a
commandable officer, or resurrect a known death through annual appearance.
Gongsun Kang's 220 boundary is an explicit estimate, not a documented death year.
"""
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))

from build_campaigns import load_sources
from remake.campaign import Campaign, Catalog, canonical
from remake.session import faction_officer_counts


KANG = 'san14-candidate-0264'
GONG = 'san14-candidate-0263'
HUANG = 'san14-candidate-0265'
MA_CHAO = 'san14-candidate-0769'
GAO_DING = 'san14-candidate-0272'
LIU_DAI = 'san14-candidate-0947'
ZHAO_FAN = 'san14-candidate-0654'
YONG_KAI = 'san14-candidate-0855'

# Pre-review world soldiers include active cities only, never unused resources
# belonging to a city absent from that particular scenario.
KANG_OPENINGS = {
    '210-11': dict(reserves=1240, soldiers=270570, members=3),
    '212-06': dict(reserves=940, soldiers=285400, members=4),
    '217-07': dict(reserves=940, soldiers=283620, members=6),
    '219-07': dict(reserves=940, soldiers=281640, members=7),
}
DEAD_OPENINGS = {
    '202-06': (LIU_DAI,),
    '207-09': ('san14-candidate-0625',),  # Zhang Xiu: died before reaching Liucheng.
    '208-10': ('san14-candidate-0280', 'san14-candidate-0953'),
    '225-07': (MA_CHAO,),
    '227-02': (GAO_DING,),
    '234-02': (GAO_DING,),
    '238-01': (GAO_DING,),
    '249-01': (GAO_DING,),
}
UNAVAILABLE_OPENINGS = {
    '234-02': (GONG, HUANG),
    '235-01': (GONG,),  # This captivity is unrelated to the IF survival premise.
    '238-01': (GONG, HUANG),
    '263-05': ('san14-candidate-0529',),  # Deposed Cao Fang, still alive.
}
FREE_OPENINGS = {
    '207-09': {'san14-candidate-0029': 'liaodong',
               'san14-candidate-0034': 'liaodong'},
    '208-10': {YONG_KAI: 'jianning'},
    '211-07-tongguan': {ZHAO_FAN: 'guiyang', YONG_KAI: 'jianning'},
    '212-12': {ZHAO_FAN: 'guiyang'},
    '215-08': {ZHAO_FAN: 'guiyang'},
    '217-07': {ZHAO_FAN: 'guiyang'},
}


class LateRulerReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Canonical sources, rather than the generated files, are the input.
        # Route timing is unrelated to historical availability and identity.
        _, sources = load_sources(timing=False)
        cls.data = {row['id'].removeprefix('mainland'): row for row in sources}
        cls.raw_people = json.loads(
            (ROOT / 'game/config/campaigns/people.json').read_text())['people']
        cls.temp = tempfile.TemporaryDirectory(prefix='tk2-late-rulers-')
        cls.catalogs = {}

    @classmethod
    def tearDownClass(cls):
        cls.catalogs.clear()
        cls.temp.cleanup()

    def catalog(self, chapter):
        if chapter not in self.catalogs:
            path = Path(self.temp.name) / (chapter + '.json')
            path.write_text(json.dumps(self.data[chapter], ensure_ascii=False))
            self.catalogs[chapter] = Catalog(path)
        return self.catalogs[chapter]

    def game(self, chapter, faction=None):
        catalog = self.catalog(chapter)
        game = Campaign(catalog)
        game.state = game._new(faction or next(iter(catalog.factions)), 2026)
        game.validate(game.state)
        return game

    def assert_not_commandable(self, game, person_id):
        ident = game.catalog.ids[person_id]
        self.assertNotIn(ident, game.state.officers)
        self.assertNotIn(str(ident), game.state.extension['free_locations'])
        for city in game.state.cities.values():
            self.assertNotIn(ident, city.roster.officer_ids)
        self.assertNotIn(person_id, {
            row['person_id'] for row in game.catalog.data['initial_officers']})
        self.assertNotIn(person_id, {
            row['person_id'] for row in game.catalog.data['initial_free_officers']})

    def test_known_death_years_and_kang_estimate_are_separate_per_catalog(self):
        historical = {chapter: data for chapter, data in self.data.items()
                      if not data['main_scenario'].get('fictional', False)}
        self.assertEqual(len(historical), 23)
        deaths = {MA_CHAO: 222, GAO_DING: 225, LIU_DAI: 192}
        for chapter, data in historical.items():
            by_person = {row['person_id']: row for row in data['people']}
            for person_id, year in deaths.items():
                with self.subTest(chapter=chapter, person_id=person_id):
                    row = by_person[person_id]
                    self.assertEqual(row['death_year'], year)
                    self.assertEqual(row['chronology_basis'],
                                     'primary_text_death_year_correction')
            with self.subTest(chapter=chapter, estimated_kang=True):
                row = by_person[KANG]
                self.assertEqual(row['death_year'], 220)
                self.assertEqual(row['chronology_basis'],
                                 'primary_text_bounded_authorial_death_boundary_not_exact_year')
        # Shared SAN14 source chronology remains traceable and unchanged.
        self.assertEqual({pid: self.raw_people[pid]['death_year']
                          for pid in (*deaths, KANG)},
                         {MA_CHAO: 226, GAO_DING: 251, LIU_DAI: 202, KANG: 210})

    def test_ruler_swap_keeps_identity_captain_retainer_and_real_troop_totals(self):
        for chapter, expected in KANG_OPENINGS.items():
            with self.subTest(chapter=chapter):
                game = self.game(chapter, 'gongsun')
                catalog = game.catalog
                initial = {row['person_id']: row
                           for row in catalog.data['initial_officers']}
                kang_id, gong_id = catalog.ids[KANG], catalog.ids[GONG]
                self.assertEqual((kang_id, gong_id), (263, 262))
                self.assertEqual(catalog.data['faction_rulers']['gongsun'], kang_id)
                self.assertEqual(game.state.extension['leaders']['gongsun'], kang_id)
                self.assertEqual(catalog.factions['gongsun']['captain'],
                                 catalog.definitions[KANG].name)
                self.assertIn(catalog.definitions[KANG].name,
                              catalog.factions['gongsun']['name'])
                self.assertIs(initial[KANG]['ruler'], True)
                self.assertIs(initial[GONG]['ruler'], False)
                self.assertIs(initial[KANG]['resolve_death_year'], False)
                for ident in (kang_id, gong_id):
                    self.assertEqual(game.state.officers[ident].faction_id, 'gongsun')
                    self.assertEqual(game.state.officers[ident].troops, 300)
                    self.assertIn(ident, game.state.cities['liaodong'].roster.officer_ids)
                self.assertEqual(game.state.cities['liaodong'].reserves,
                                 expected['reserves'])
                actual = (sum(city.reserves for city in game.state.cities.values())
                          + sum(officer.troops for officer in game.state.officers.values()))
                self.assertEqual(actual, expected['soldiers'])
                self.assertEqual(game.state.soldiers,
                                 dict(initial=expected['soldiers'], recruited=0, lost=0))
                self.assertEqual(faction_officer_counts(catalog)['gongsun'],
                                 expected['members'])
                self.assertEqual(catalog.factions['gongsun']['initial_officers'],
                                 expected['members'])
                self.assertEqual(game.state.rng.draws, 0)

    def test_known_opening_deaths_are_excluded_instead_of_becoming_free(self):
        for chapter, people in DEAD_OPENINGS.items():
            game = self.game(chapter)
            for person_id in people:
                with self.subTest(chapter=chapter, person_id=person_id):
                    assignment = game.catalog.data['era_assignments'][person_id]
                    self.assertEqual(assignment['status'], 'chronology_excluded')
                    self.assertEqual(assignment['year_state'], 'dead')
                    self.assertEqual(assignment['exclusion_kind'],
                                     'primary_text_dead_by_opening')
                    self.assert_not_commandable(game, person_id)

    def test_living_captives_hostages_and_deposed_ruler_are_not_declared_dead(self):
        for chapter, people in UNAVAILABLE_OPENINGS.items():
            game = self.game(chapter)
            for person_id in people:
                with self.subTest(chapter=chapter, person_id=person_id):
                    assignment = game.catalog.data['era_assignments'][person_id]
                    self.assertEqual(assignment['status'], 'scenario_excluded')
                    self.assertEqual(assignment['year_state'], 'unavailable')
                    self.assertEqual(assignment['exclusion_kind'],
                                     'explicit_scenario_scope')
                    self.assertIsNone(assignment['faction'])
                    self.assertIsNone(assignment['city'])
                    self.assertEqual(game.catalog.definitions[person_id].death_year,
                                     self.raw_people[person_id]['death_year'])
                    self.assert_not_commandable(game, person_id)

    def test_excluded_people_do_not_respawn_or_return_on_signed_save_reload(self):
        chapters = set(DEAD_OPENINGS) | set(UNAVAILABLE_OPENINGS)
        for chapter in sorted(chapters):
            with self.subTest(chapter=chapter):
                game = self.game(chapter)
                people = DEAD_OPENINGS.get(chapter, ()) + UNAVAILABLE_OPENINGS.get(chapter, ())
                for person_id in people:
                    assignment = game.catalog.data['era_assignments'][person_id]
                    self.assertEqual(assignment['appearance_plan']['status'], 'excluded')
                    self.assertEqual(game.catalog.data['appearance_windows'][person_id], [])
                game._spawn_eligible(game.state)
                game._reconcile_factions(game.state)
                game.validate(game.state)
                saved = game.export_save()
                loaded = Campaign(game.catalog)
                loaded.load_save(saved, 0)
                loaded._spawn_eligible(loaded.state)
                loaded.validate(loaded.state)
                self.assertEqual(canonical(loaded.export_save()), canonical(saved))
                for person_id in people:
                    self.assert_not_commandable(loaded, person_id)

    def test_guests_fugitives_and_regional_people_keep_ids_without_false_allegiance(self):
        for chapter, places in FREE_OPENINGS.items():
            game = self.game(chapter)
            for person_id, city in places.items():
                with self.subTest(chapter=chapter, person_id=person_id):
                    ident = game.catalog.ids[person_id]
                    self.assertEqual(ident, self.raw_people[person_id]['runtime_id'])
                    assignment = game.catalog.data['era_assignments'][person_id]
                    self.assertEqual((assignment['status'], assignment['faction'],
                                      assignment['city']), ('free', None, city))
                    self.assertIsNone(game.state.officers[ident].faction_id)
                    self.assertEqual(game.state.officers[ident].troops, 0)
                    self.assertEqual(game.state.extension['free_locations'][str(ident)], city)
                    self.assertEqual(game.catalog.data['appearance_locations'][person_id], city)
                    self.assertNotIn(ident, game.state.extension['leaders'].values())
                    self.assertIn(person_id, {row['person_id'] for row in
                                             game.catalog.data['initial_free_officers']})
            game._spawn_eligible(game.state)
            game.validate(game.state)

    def test_225_user_exception_remains_active_with_resolved_death_year(self):
        game = self.game('225-07', 'nanman')
        for person_id in (GAO_DING, YONG_KAI, 'san14-candidate-0391'):
            with self.subTest(person_id=person_id):
                ident = game.catalog.ids[person_id]
                self.assertEqual(game.state.officers[ident].faction_id, 'nanman')
                row = next(row for row in game.catalog.data['initial_officers']
                           if row['person_id'] == person_id)
                self.assertIs(row['resolve_death_year'], True)
                self.assertIs(game.catalog.data['era_assignments'][person_id]
                              ['death_year_resolved'], True)
        self.assertEqual(game.state.extension['leaders']['nanman'],
                         game.catalog.ids['san14-candidate-0845'])

    def test_historical_corrections_do_not_rewrite_unrelated_if_membership(self):
        fictional = {chapter: data for chapter, data in self.data.items()
                     if data['main_scenario'].get('fictional', False)}
        self.assertEqual(len(fictional), 6)
        for chapter, data in fictional.items():
            by_person = {row['person_id']: row for row in data['people']}
            for person_id in (MA_CHAO, GAO_DING):
                with self.subTest(chapter=chapter, person_id=person_id):
                    self.assertEqual(by_person[person_id]['death_year'],
                                     self.raw_people[person_id]['death_year'])
        for chapter in ('210-11', '212-06'):
            game = self.game(chapter, 'shu')
            ident = game.catalog.ids[ZHAO_FAN]
            self.assertEqual(game.state.officers[ident].faction_id, 'shu')
            self.assertIn(ident, game.state.cities['guiyang'].roster.officer_ids)
        game = self.game('235-01', 'shu')
        self.assertEqual(game.state.officers[game.catalog.ids[GAO_DING]].faction_id, 'shu')

    def test_actual_subordinates_and_future_rulers_are_not_prematurely_split(self):
        examples = {
            '202-06': {'san14-candidate-0080': 'wei', 'san14-candidate-0091': 'wei',
                       'san14-candidate-0625': 'wei', 'san14-candidate-0285': 'liu_biao'},
            '207-09': {'san14-candidate-0280': 'wei', 'san14-candidate-0769': 'ma_teng'},
            '219-07': {'san14-candidate-0938': 'shu', 'san14-candidate-0262': 'gongsun',
                       'san14-candidate-0501': 'wei', 'san14-candidate-0526': 'wei'},
            '221-07': {'san14-candidate-0945': 'shu'},
            '227-02': {'san14-candidate-0262': 'gongsun'},
            '249-01': {'san14-candidate-0548': 'wu', 'san14-candidate-0344': 'wei',
                       'san14-candidate-0346': 'wei', 'san14-candidate-0348': 'wei',
                       'san14-candidate-0077': 'wei', 'san14-candidate-0152': 'wei',
                       'san14-candidate-0810': 'wei', 'san14-candidate-0438': 'wei'},
            '263-05': {'san14-candidate-0554': 'wu'},
        }
        for chapter, members in examples.items():
            game = self.game(chapter)
            for person_id, faction in members.items():
                with self.subTest(chapter=chapter, person_id=person_id):
                    ident = game.catalog.ids[person_id]
                    self.assertEqual(game.state.officers[ident].faction_id, faction)
                    self.assertNotIn(ident, game.state.extension['leaders'].values())
        for chapter in ('221-07', '225-07', '227-02'):
            game = self.game(chapter, 'gongsun')
            self.assertEqual(game.state.extension['leaders']['gongsun'],
                             game.catalog.ids[GONG])

    def test_profile_stats_and_initialization_are_not_changed_by_history_review(self):
        people = {KANG, GONG, HUANG, MA_CHAO, GAO_DING, LIU_DAI,
                  ZHAO_FAN, YONG_KAI, 'san14-candidate-0529',
                  'san14-candidate-0029', 'san14-candidate-0034',
                  'san14-candidate-0625', 'san14-candidate-0280',
                  'san14-candidate-0953'}
        for chapter, data in self.data.items():
            by_person = {row['person_id']: row for row in data['people']}
            for person_id in people:
                with self.subTest(chapter=chapter, person_id=person_id):
                    row = by_person[person_id]
                    self.assertEqual(row['profile'], self.raw_people[person_id]['profile'])
                    self.assertEqual(row['initialization'],
                                     self.raw_people[person_id]['initialization'])
                    self.assertEqual(row['birth_year'], self.raw_people[person_id]['birth_year'])
                    self.assertEqual(row['service_year'], self.raw_people[person_id]['service_year'])

    def test_corrected_faction_previews_count_the_actual_runtime_members(self):
        chapters = (set(KANG_OPENINGS) | set(DEAD_OPENINGS)
                    | set(UNAVAILABLE_OPENINGS) | set(FREE_OPENINGS))
        for chapter in sorted(chapters):
            game = self.game(chapter)
            actual = Counter(officer.faction_id for officer in game.state.officers.values()
                             if officer.faction_id is not None)
            self.assertEqual(faction_officer_counts(game.catalog), actual)
            for faction, metadata in game.catalog.factions.items():
                with self.subTest(chapter=chapter, faction=faction):
                    self.assertEqual(metadata['initial_officers'], actual[faction])
            stationed = []
            for city in game.state.cities.values():
                self.assertLessEqual(len(city.roster.officer_ids), 99)
                for ident in city.roster.officer_ids:
                    self.assertEqual(game.state.officers[ident].faction_id, city.owner)
                stationed.extend(city.roster.officer_ids)
            self.assertEqual(len(stationed), len(set(stationed)))
            self.assertEqual(len(stationed), sum(actual.values()))


if __name__ == '__main__':
    unittest.main()
