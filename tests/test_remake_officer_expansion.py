"""Reviewed v13 identities, dated rosters, high IDs and frozen-save boundaries."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from remake.campaign import Campaign, Catalog, SeedRng
from remake.officers import YearState, select_deployment, virtue_score, year_state


def read(path):
    return json.loads((ROOT/path).read_text())


class OfficerExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = read('game/data/main-scenarios-v13/index.json')
        cls.spec = read('game/config/officer-expansion-v13.json')
        cls.catalogs = {}
        for path in cls.index['catalogs']:
            catalog = Catalog(ROOT/'game/data'/path)
            cls.catalogs[catalog.data['start_year'], catalog.data['start_month']] = catalog

    def game(self, year, month, side='shu'):
        game = Campaign(self.catalogs[year, month])
        game.state = game._new(side, 2026)
        game.validate(game.state)
        return game

    def roundtrip(self, game):
        saved = game.export_save()
        restored = Campaign(game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)
        return restored

    def test_23_unique_additions_keep_old1000_people_and_world_per_chapter(self):
        self.assertEqual(len(self.catalogs), 25)
        self.assertEqual(len(self.spec['people']), 23)
        additions = {p['person_id'] for p in self.spec['people']}
        fields = ('cities', 'city_foundings', 'active_cities', 'initial_owners', 'rules',
                  'links', 'sea_links', 'initial_resources', 'initial_city_resources',
                  'city_income', 'world', 'travel_rules', 'travel_routes', 'travel_hazards',
                  'sea_routes', 'exploration_routes', 'faction_rulers')
        for date, catalog in self.catalogs.items():
            with self.subTest(date=date):
                data = catalog.data
                prior = read(f'game/data/main-scenarios-v12/{date[0]}-{date[1]:02d}.json')
                self.assertEqual(data['people'][:1000], prior['people'])
                self.assertEqual({p['person_id'] for p in data['people'][1000:]}, additions)
                # The withdrawn Xun Xu slot remains reserved; later IDs are
                # never compacted or silently reassigned to another person.
                self.assertEqual(set(catalog.by_id), set(range(1024))-{1005})
                self.assertEqual(len(catalog.definitions), 1023)
                self.assertEqual(data['officer_count'], 1023)
                self.assertEqual(data['coverage']['library'], 1023)
                self.assertEqual(data['coverage']['san14_abilities'], 1000)
                self.assertEqual(data['content_generation'], 13)
                for field in fields:
                    self.assertEqual(data[field], prior[field], field)
                known = {label for p in prior['people'] for label in [p['name'], *p.get('aliases', [])]}
                for person in data['people'][1000:]:
                    labels = {person['name'], *person['aliases']}
                    self.assertFalse(known & labels, person['name'])
                    known.update(labels)

    def test_new_profile_sources_and_virtues_distinguish_design_from_SAN14(self):
        catalog = self.catalogs[263, 5]
        spec = {p['person_id']:p for p in self.spec['people']}
        statuses = Counter()
        for person in catalog.data['people'][1000:]:
            entry = spec[person['person_id']]
            profile, virtue = person['profile'], person['virtue_design']
            self.assertEqual(profile['source_stats'], {})
            self.assertEqual(person['ability_source']['kind'], 'historical_authorial_game_design')
            self.assertTrue(person['ability_source']['source_urls'])
            self.assertTrue(all(url.startswith('https://') for url in person['ability_source']['source_urls']))
            self.assertFalse(person['configuration']['is_historical_measurement'])
            self.assertFalse(catalog.profiles[person['runtime_id']].missing)
            self.assertEqual(profile['health_max'], 80)
            self.assertIn(profile['terrain_affinity'], (0, 1, 2))
            self.assertEqual(person['chronology_design'], entry['chronology'])
            if entry['chronology']['death_year'] is None:
                self.assertEqual(person['death_year'], entry['chronology']['retirement_year'])
                self.assertIn('not_historical_death', entry['chronology']['precision']['retirement_year'])
            statuses[virtue['status']] += 1
            if virtue['status'] == 'configured_design':
                self.assertEqual(profile['virtue'], virtue_score(virtue['dimensions']))
                self.assertTrue(virtue['sources'])
            else:
                self.assertEqual(virtue['policy_id'], 'virtue-default-60-2026-10-21')
                self.assertEqual(virtue['authority'], 'explicit_user_instruction')
                self.assertEqual(profile['virtue'], 60)
                self.assertEqual(virtue['sources'], [])
                self.assertIsNone(virtue['dimensions'])
        self.assertEqual(statuses, {'configured_design':11, 'configured_default':12})

    def test_catalog_count_is_explicit_and_runtime_ids_are_not_byte_masked(self):
        catalog = self.catalogs[263, 5]
        self.assertEqual(catalog.rules.runtime_capacity, 1200)
        self.assertEqual(catalog.rules.officer_id(1023), 1023)
        self.assertEqual(catalog.name(1023), '虞昺')
        self.assertEqual(Campaign(catalog).view()['catalog']['library_count'], 1023)
        old = Catalog(ROOT/'game/data/main-scenarios-v12/263-05.json')
        self.assertEqual(Campaign(old).view()['catalog']['library_count'], 1000)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'catalog.json'
            for count in (True, 1022, 1201):
                data = deepcopy(catalog.data);data['officer_count'] = count
                file.write_text(json.dumps(data, ensure_ascii=False))
                with self.assertRaises((ValueError, AssertionError)):
                    Catalog(file)

    def test_variant_names_find_existing_people_instead_of_expanding_them_twice(self):
        catalog = self.catalogs[263, 5]
        view = Campaign(catalog).view()['catalog']
        old_path = list(sys.path)
        try:
            sys.path.insert(0, str(ROOT/'game'))
            from build_officer_expansion import new_people
        finally:
            sys.path[:] = old_path
        self.assertNotIn('historical-expansion-0006', catalog.definitions)
        self.assertNotIn(1005, catalog.by_id)
        for alias,pid,ident in [('荀勖','san14-candidate-0397',396),
                                ('施績','san14-candidate-0388',387)]:
            self.assertEqual(catalog.ids[pid], ident)
            self.assertIn(alias, catalog.data['additional_person_aliases'][pid])
            # The browser searches the same view names and aliases, while the
            # published first1000 person records themselves remain unchanged.
            matches = [p for p in view['library'] if alias in [p['name'], *p['aliases']]]
            self.assertEqual([p['id'] for p in matches], [ident])
            self.assertEqual(matches[0]['person_id'], pid)
            self.assertFalse(any(p['name']==alias for p in catalog.data['people'][1000:]))
            # A future edit cannot reintroduce a known semantic duplicate just
            # because its spelling is absent from the frozen person record.
            invalid = deepcopy(self.spec)
            candidate = deepcopy(invalid['people'][0])
            candidate.update(person_id='historical-expansion-0099', name=alias,
                             aliases=[alias], name_japanese=alias)
            invalid['people'].append(candidate);invalid['new_count'] += 1
            with self.assertRaisesRegex(ValueError, 'Duplicate historical name/alias: '+alias):
                new_people(invalid, catalog.data['people'][:1000])

    def test_all219_openings_obey_dates_capacity_and_representative_save_roundtrips(self):
        starts = 0
        for date, catalog in self.catalogs.items():
            self.assertEqual(catalog.rules.city_officer_capacity, 30)
            self.assertEqual(catalog.rules.battle_officers_per_side, 10)
            for side in catalog.factions:
                with self.subTest(date=date, side=side):
                    game = Campaign(catalog);game.state = game._new(side, 2026)
                    game.validate(game.state);starts += 1
                    for city in game.state.cities.values():
                        self.assertLessEqual(len(city.roster.officer_ids), 30)
                        for ident in city.roster.officer_ids:
                            self.assertEqual(game.state.officers[ident].faction_id, city.owner)
                    for ident, officer in game.state.officers.items():
                        self.assertIn(year_state(catalog.definitions[officer.person_id], date[0]),
                                      (YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW))
                        if ident >= 1000:
                            windows = catalog.data['appearance_windows'][officer.person_id]
                            self.assertTrue(any(tuple(w['start']) <= date <= tuple(w['end']) for w in windows))
            # One full envelope roundtrip per chapter, independently of player.
            game = self.game(*date, side=next(iter(catalog.factions)))
            self.roundtrip(game)
        self.assertEqual(starts, 219)

    def test_reviewed_rosters_fill_real_gaps_and_explicit263_transfers_are_separate(self):
        catalog = self.catalogs[208, 10]
        prior = read('game/data/main-scenarios-v12/208-10.json')
        before = Counter(prior['initial_owners'][r['city']] for r in prior['initial_officers'])
        after = Counter(catalog.data['initial_owners'][r['city']] for r in catalog.data['initial_officers'])
        self.assertEqual(before['liu_zhang'], 1)
        self.assertGreaterEqual(after['liu_zhang'], 18)
        self.assertGreater(after['ma_teng'], before['ma_teng'])
        self.assertGreater(after['zhang_lu'], before['zhang_lu'])
        for date, current in self.catalogs.items():
            old = read(f'game/data/main-scenarios-v12/{date[0]}-{date[1]:02d}.json')
            for item in current.data['officer_expansion']['restored_memberships']:
                self.assertIn(old['era_assignments'][item['person_id']]['status'],
                              ('pending_history', 'pending_faction', 'pending_location', 'free'))
                self.assertTrue(item['proof']['sources'])
                self.assertEqual(current.data['era_assignments'][item['person_id']]['faction'], item['faction'])
        game = self.game(263, 5, 'wei')
        records = game.catalog.data['officer_expansion']['historical_transfers']
        expected = {'san14-candidate-0242':'shu', 'san14-candidate-0730':'wu', 'san14-candidate-0491':'wu'}
        self.assertEqual({r['person_id'] for r in records}, set(expected))
        for item in records:
            self.assertEqual(item['before_faction'], expected[item['person_id']])
            self.assertEqual(item['after_faction'], 'wei');self.assertTrue(item['sources'])
            self.assertEqual(game.state.officers[game.catalog.ids[item['person_id']]].faction_id, 'wei')
        self.assertTrue(all(not c.data['officer_expansion']['historical_transfers']
                            for date,c in self.catalogs.items() if date != (263,5)))

    def test_new_high_id_can_be_recruited_and_transferred_with_real_commands(self):
        game = self.game(227, 2)
        ident = game.catalog.ids['historical-expansion-0019'] # Ma Cheng, not old Ma Chao.
        self.assertGreater(ident, 999)
        state = game.state
        city = next(c for c in state.cities.values() if ident in c.roster.officer_ids)
        # Controlled released-officer fixture preserves profile, location and
        # soldier conservation; recruitment/transfer below use actual commands.
        officer = state.officers[ident]
        city.reserves += officer.troops;officer.troops = 0
        city.roster.officer_ids.remove(ident);officer.faction_id = None;officer.loyalty = 0
        state.extension['free_locations'][str(ident)] = city.id
        game.validate(state)
        actor = city.roster.officer_ids[0]
        state.rng.state = next(seed for seed in range(1,1000) if SeedRng(seed).next()%100 < 15)
        game.command('recruit_officer', dict(city=city.id, actor=actor, officer=ident), game.revision)
        self.assertEqual(game.state.officers[ident].faction_id, 'shu')
        self.assertIn(ident, game.state.cities[city.id].roster.officer_ids)
        game._complete_month(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
        game.validate(game.state)
        destination = next(key for key in game._neighbors(city.id,game.state)
                           if key in game.state.cities and game.state.cities[key].owner=='shu'
                           and len(game.state.cities[key].roster.officer_ids)<30)
        game.command('transfer', dict(source=city.id,target=destination,officers=[ident]), game.revision)
        march = game.state.extension['travel']['marches'][-1]
        self.assertEqual(march['officers'], [ident])
        self.assertIn(ident, game.state.cities[city.id].roster.officer_ids)
        self.roundtrip(game)

    def test_future_person_waits_for_exact_career_month_and_appears_free_only_once(self):
        game = self.game(249, 1, 'wu')
        ident = game.catalog.ids['historical-expansion-0021'] # Zhu Xiong:252-05 window, not January.
        self.assertNotIn(ident, game.state.officers)
        while (game.state.year,game.state.month) < (252,4):
            game._complete_month(game.state);game._spawn_eligible(game.state)
            game._reconcile_factions(game.state);game.validate(game.state)
        self.assertNotIn(ident, game.state.officers)
        game._complete_month(game.state);game._spawn_eligible(game.state)
        game._reconcile_factions(game.state);game.validate(game.state)
        self.assertEqual((game.state.year,game.state.month),(252,5))
        self.assertIn(ident, game.state.officers)
        self.assertIsNone(game.state.officers[ident].faction_id)
        self.assertEqual(game.state.extension['free_locations'][str(ident)], 'danyang')
        saved = game.export_save();game._spawn_eligible(game.state)
        self.assertEqual(game.export_save(), saved)
        self.roundtrip(game)

    def test_expired_career_does_not_spawn_and_new_battle_ids_remain_distinct(self):
        game = self.game(263, 5, 'wei')
        ident = game.catalog.ids['historical-expansion-0005'] # Ren Kai remains alive beyond265 window.
        city = next(c for c in game.state.cities.values() if ident in c.roster.officer_ids)
        officer = game.state.officers.pop(ident);city.roster.officer_ids.remove(ident)
        city.reserves += officer.troops
        # Isolate a missed career window with actual calendar bookkeeping, but
        # no intermediate spawn/AI. The final spawn must not invent a late entry.
        while (game.state.year,game.state.month) < (266,1):
            game._complete_month(game.state);game._reconcile_factions(game.state)
        game._spawn_eligible(game.state);game.validate(game.state)
        self.assertNotIn(ident, game.state.officers)
        game = self.game(263, 5, 'wu')
        ident = game.catalog.ids['historical-expansion-0024']
        city = next(c for c in game.state.cities.values() if ident in c.roster.officer_ids)
        self.assertEqual(select_deployment(city.roster,[ident],game.state.officers),(1023,))

    def test_explicit_single_year_career_enters263_then_retires264_without_resurrection(self):
        game = self.game(249, 1, 'shu')
        pid = 'historical-expansion-0017' # Li Qiu's service and death both occur in263.
        ident = game.catalog.ids[pid]
        windows = game.catalog.data['appearance_windows'][pid]
        self.assertTrue(any(w.get('resolve_death_year') for w in windows))
        while (game.state.year,game.state.month) < (262,12):
            game._complete_month(game.state);game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
            if game.state.month == 1:
                game.validate(game.state)
        self.assertNotIn(ident, game.state.officers)
        game._complete_month(game.state);game._spawn_eligible(game.state)
        game._reconcile_factions(game.state);game.validate(game.state)
        self.assertEqual((game.state.year,game.state.month),(263,1))
        self.assertTrue(game.state.officers[ident].alive)
        self.assertIsNone(game.state.officers[ident].faction_id)
        self.assertEqual(game.state.extension['free_locations'][str(ident)], 'guanghan')
        while (game.state.year,game.state.month) < (264,1):
            game._complete_month(game.state);game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
        game.validate(game.state)
        self.assertFalse(game.state.officers[ident].alive)
        saved = game.export_save();game._spawn_eligible(game.state)
        self.assertEqual(game.export_save(), saved)
        self.roundtrip(game)

    def test_offline_rebuild_is_stable_across_hash_seeds_and_old_save_stays_1000(self):
        paths = sorted((ROOT/'game/data').rglob('*.json'))
        before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        for seed in ('7','31'):
            subprocess.run([sys.executable,'-B','game/build_officer_expansion.py'],cwd=ROOT,
                env={**os.environ,'PYTHONHASHSEED':seed},check=True,capture_output=True)
            self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        old = Campaign(Catalog(ROOT/'game/data/main-scenarios-v12/263-05.json'))
        old.state = old._new('wei',2026)
        restored = self.roundtrip(old)
        self.assertEqual(len(restored.catalog.definitions),1000)
        self.assertTrue(all(i<1000 for i in restored.state.officers))


if __name__=='__main__':
    unittest.main()
