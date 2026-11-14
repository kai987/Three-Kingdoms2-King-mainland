"""Canonical July 225 opening roster and dated membership regressions."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from test_remake_historical_scenarios import ROOT, expansion_material
from remake.campaign import Campaign, Catalog


class Nanzhong225SetupTests(unittest.TestCase):
    """Exercise the canonical July 225 source independently of publication.

    The combined faction is an explicit requested opening arrangement. Tests
    preserve the shared person dates rather than treating July survival and
    subordinate relationships as historical facts.
    """

    MEMBERS = {
        'san14-candidate-0855': ('雍闿', 854, 'jianning'),
        'san14-candidate-0272': ('高定', 271, 'jianning'),
        'san14-candidate-0391': ('朱褒', 390, 'zangke'),
    }
    BASIS = 'user_requested_225_nanzhong_merge'
    LU_YUSHENG = 'san14-candidate-0898'

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'historical225_campaign_builder', ROOT / 'game/build_campaigns.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        source = builder.SOURCE
        cls.folder = tempfile.TemporaryDirectory(prefix='tk225-opening-test-')
        cls.addClassCleanup(cls.folder.cleanup)
        current = Path(cls.folder.name)
        (current / 'scenarios').mkdir()
        for name in ('people.json', 'shared.json'):
            shutil.copyfile(source / name, current / name)
        index = json.loads((source / 'index.json').read_text())
        entry = next(row for row in index['scenarios'] if row['id'] == 'mainland225-07')
        shutil.copyfile(source / entry['file'], current / entry['file'])
        (current / 'index.json').write_text(json.dumps(dict(
            schema=index['schema'], default=entry['id'], scenarios=[entry])))
        try:
            builder.SOURCE = current
            # Ownership/posting tests do not rebuild the separately hashed
            # rendering/timing artifact. Release integration validates it after
            # regenerating the campaign inputs in the usual order.
            _, catalogs = builder.load_sources(timing=False)
        finally:
            builder.SOURCE = source
        if len(catalogs) != 1:
            raise AssertionError('The July 225 regression must build exactly one source')
        catalog_file = current / '225-07.json'
        catalog_file.write_bytes(builder.encoded(catalogs[0]))
        cls.catalog = Catalog(catalog_file)
        cls.people = json.loads((source / 'people.json').read_text())['people']

    def game(self):
        game = Campaign(self.catalog)
        game.state = game._new('nanman', 2026)
        game.validate(game.state)
        return game

    def test_three_requested_officers_serve_meng_huo_at_their_opening_cities(self):
        game = self.game()
        self.assertEqual((game.state.year, game.state.month), (225, 7))
        self.assertEqual(game.state.cities['zangke'].owner, 'nanman')
        self.assertEqual(self.catalog.data['faction_rulers']['nanman'], 844)
        self.assertEqual(game.state.extension['leaders']['nanman'], 844)
        self.assertEqual(self.catalog.factions['nanman']['city'], 'jianning')
        self.assertEqual(game.state.officers[844].person_id, 'san14-candidate-0845')
        initial = {row['person_id']: row for row in self.catalog.data['initial_officers']}
        self.assertIs(initial['san14-candidate-0845']['ruler'], True)
        for person_id, (name, ident, city) in self.MEMBERS.items():
            with self.subTest(person_id=person_id):
                self.assertEqual(self.catalog.ids[person_id], ident)
                self.assertEqual(self.catalog.definitions[person_id].name, name)
                self.assertEqual(game.state.officers[ident].faction_id, 'nanman')
                self.assertIn(ident, game.state.cities[city].roster.officer_ids)
                self.assertIs(initial[person_id]['ruler'], False)
                assignment = self.catalog.data['era_assignments'][person_id]
                self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                                 ('serving', 'nanman', city))
                self.assertEqual(assignment['source_ruler'], '孟获')
                self.assertEqual(assignment['posting_reference']['faction'], 'nanman')
                self.assertEqual(assignment['posting_reference']['city'], city)
                self.assertEqual(assignment['appearance_plan']['city'], city)
                self.assertEqual(self.catalog.data['appearance_locations'][person_id], city)

    def test_other_garrisons_and_total_membership_are_preserved_without_duplicates(self):
        game = self.game()
        self.assertEqual(len(self.catalog.data['initial_officers']), 317)
        self.assertEqual(len(self.catalog.data['initial_free_officers']), 78)
        self.assertEqual(Counter(o.faction_id for o in game.state.officers.values()
                                 if o.faction_id),
                         dict(wei=127, shu=82, wu=79, nanman=16, shi_xie=7, gongsun=6))
        for faction, metadata in self.catalog.factions.items():
            self.assertEqual(metadata['initial_officers'], sum(
                o.faction_id == faction for o in game.state.officers.values()))
        # Moving the two requested officers must not convert their former
        # garrisons or move the already-configured Shu commanders with them.
        for city, person_ids in {
            'guanghan': ('san14-candidate-0072', 'san14-candidate-0440'),
            'wenshan': ('san14-candidate-0189', 'san14-candidate-0787'),
        }.items():
            self.assertEqual(game.state.cities[city].owner, 'shu')
            for person_id in person_ids:
                ident = self.catalog.ids[person_id]
                self.assertEqual(game.state.officers[ident].faction_id, 'shu')
                self.assertIn(ident, game.state.cities[city].roster.officer_ids)
        stationed = []
        for city in game.state.cities.values():
            self.assertLessEqual(len(city.roster.officer_ids), 99)
            for ident in city.roster.officer_ids:
                self.assertEqual(game.state.officers[ident].faction_id, city.owner)
            stationed.extend(city.roster.officer_ids)
        self.assertEqual(len(stationed), 317)
        self.assertEqual(len(stationed), len(set(stationed)))
        self.assertEqual(max(len(c.roster.officer_ids) for c in game.state.cities.values()),
                         self.catalog.data['coverage']['planned_max_city_roster'])
        self.assertEqual(game.state.rng.draws, 0)
        # Ma Chao died in222; excluding his anachronistic225 garrison returns
        # its300 soldiers to Chengdu instead of deleting or duplicating men.
        ma_chao = self.catalog.ids['san14-candidate-0769']
        self.assertNotIn(ma_chao, game.state.officers)
        self.assertEqual(self.catalog.definitions['san14-candidate-0769'].death_year, 222)
        chengdu = game.state.cities['shujun']
        self.assertEqual(chengdu.reserves + sum(game.state.officers[i].troops
            for i in chengdu.roster.officer_ids), 4190 + sum(
            row['troops'] for row in self.catalog.data['initial_officers'] if row['city'] == 'shujun'))
        self.assertEqual(game.state.soldiers['initial'],
                         271350 + expansion_material(self.catalog.data)[2])
        before = game.to_dict()
        game._spawn_eligible(game.state)
        game.validate(game.state)
        self.assertEqual(game.to_dict(), before)
        self.assertNotIn(ma_chao, game.state.officers)

    def test_lu_yusheng_serves_wu_in_wujun_at_the_opening(self):
        game = self.game()
        ident = self.catalog.ids[self.LU_YUSHENG]
        officer = game.state.officers[ident]
        row = next(row for row in self.catalog.data['initial_officers']
                   if row['person_id'] == self.LU_YUSHENG)
        self.assertEqual((row['city'], row['troops']), ('wujun', 300))
        _, opening_troops = self.catalog.opening_garrisons
        self.assertEqual((officer.person_id, officer.faction_id, officer.troops),
                         (self.LU_YUSHENG, 'wu', opening_troops[self.LU_YUSHENG]))
        self.assertIn(ident, game.state.cities['wujun'].roster.officer_ids)
        self.assertNotIn(self.LU_YUSHENG, {row['person_id']
                         for row in self.catalog.data['initial_free_officers']})
        assignment = self.catalog.data['era_assignments'][self.LU_YUSHENG]
        self.assertEqual((assignment['status'], assignment['faction'], assignment['city']),
                         ('serving', 'wu', 'wujun'))

    def test_user_july_exception_retains_shared_dates_and_reviewed_historical_exit(self):
        initial = {row['person_id']: row for row in self.catalog.data['initial_officers']}
        self.assertEqual(self.catalog.data['start_year'], 225)
        self.assertEqual(self.catalog.data['start_month'], 7)
        self.assertEqual(self.catalog.data['main_scenario']['chronology_overrides'], [])
        for person_id in self.MEMBERS:
            with self.subTest(person_id=person_id):
                definition = self.catalog.definitions[person_id]
                original = self.people[person_id]
                self.assertEqual((definition.birth_year, definition.service_year),
                                 (original['birth_year'], original['service_year']))
                expected_death = 225 if person_id == 'san14-candidate-0272' else original['death_year']
                self.assertEqual(definition.death_year, expected_death)
                review = self.catalog.data['era_assignments'][person_id]['placement_review']
                self.assertEqual(review['basis'], self.BASIS)
                self.assertEqual(review['historical_certainty'], 'authorial_region_placement')
                self.assertIn('https://zh.wikisource.org/zh-hant/三國志/卷43', review['source_urls'])
        # The shared third-party record is retained for provenance; historical
        # campaigns apply Gao Ding's attested225 death locally. July survival
        # in this user-requested combined faction remains an explicit exception.
        self.assertEqual(self.people['san14-candidate-0272']['death_year'], 251)
        gao_ding = self.catalog.by_id[self.catalog.ids['san14-candidate-0272']]
        self.assertEqual(gao_ding['chronology_basis'], 'primary_text_death_year_correction')
        for person_id in self.MEMBERS:
            self.assertEqual(self.catalog.definitions[person_id].death_year, 225)
            self.assertIs(initial[person_id]['resolve_death_year'], True)
            self.assertIs(self.catalog.data['era_assignments'][person_id]['death_year_resolved'], True)
        setup = self.catalog.data['main_scenario']['user_setup_overrides'][0]
        self.assertEqual(setup['city_owners'], {'zangke': 'nanman'})
        self.assertEqual({r['person_id'] for r in setup['members']}, set(self.MEMBERS))
        self.assertIs(setup['shared_chronology_changed'], False)
        self.assertNotIn('zangke', self.catalog.data['main_scenario']['historical_review']['city_owner_corrections'])
        for locale in ('zh-Hant', 'ja'):
            self.assertIn('225', self.catalog.data['main_scenario']['story_note_i18n'][locale])
        actual = Counter(a['placement_review']['basis']
                         for a in self.catalog.data['era_assignments'].values())
        self.assertEqual(dict(actual), self.catalog.data['placement_completion']['bases'])


if __name__ == '__main__':
    unittest.main()
