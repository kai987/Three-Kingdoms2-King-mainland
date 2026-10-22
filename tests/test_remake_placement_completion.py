"""Complete dated placement plans are playable without rewriting old saves."""
from copy import deepcopy
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, canonical
from remake.garrison_postings import apply_postings
from remake.officers import (CapacityError, CityRoster, YearState, select_deployment,
                            transfer_officers, year_state)
from remake.session import CampaignSession


EXEMPT_OPENING = {'scenario_excluded', 'closed_career'}
PENDING = {'pending_history', 'pending_faction', 'pending_location', 'pending_capacity', 'pending_profile'}


def read(path):
    return json.loads((ROOT / path).read_text())


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_future_entry(catalog, person_id):
    """Find an eligible window/date from the published contract, not a builder."""
    definition = catalog.definitions[person_id]
    opening = catalog.data['start_year'], catalog.data['start_month']
    result = []
    for window in catalog.data['appearance_windows'].get(person_id, []):
        start = max(tuple(window['start']), opening, (definition.service_year, 1), (definition.birth_year, 1))
        end = tuple(window['end'])
        year, month = start
        while (year, month) <= end:
            state = year_state(definition, year)
            if state == YearState.AVAILABLE or (state == YearState.DEATH_YEAR_REVIEW and window.get('resolve_death_year') is True):
                if window['city'] in catalog.active_city_ids(year, month):
                    result.append(((year, month), window['city']))
                    break
            month += 1
            if month == 13:
                year += 1
                month = 1
    return min(result) if result else None


class PlacementCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = read('game/data/main-scenarios-v15/index.json')
        cls.catalogs = {}
        cls.parents = {}
        for filename in cls.index['catalogs']:
            catalog = Catalog(ROOT / 'game/data' / filename)
            date = catalog.data['start_year'], catalog.data['start_month']
            cls.catalogs[date] = catalog
            cls.parents[date] = Catalog(ROOT / f'game/data/main-scenarios-v14/{date[0]}-{date[1]:02d}.json')
        cls.portrait_index = read('game/assets/portraits/index.json')

    def game(self, date, faction=None):
        catalog = self.catalogs[date]
        game = Campaign(catalog)
        game.state = game._new(faction or next(iter(catalog.factions)), 2026)
        game.validate(game.state)
        return game

    def calendar_month(self, game):
        # Isolate real calendar/appearance services from AI conquest. Each month
        # still commits its actual resources, year receipts and city openings.
        game._complete_month(game.state)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)

    def test_all25_new_catalogs_keep_people_profiles_map_and_portrait_identities(self):
        self.assertEqual(len(self.catalogs), 25)
        self.assertEqual(set(self.catalogs), set(self.parents))
        self.assertEqual(self.index['default'], 'mainland217-07-v15')
        protected = ('people', 'cities', 'active_cities', 'city_foundings',
                     'links', 'travel_routes', 'travel_hazards', 'sea_routes', 'exploration_routes',
                     'world', 'initial_city_resources', 'city_income', 'faction_rulers')
        portrait_people = self.portrait_index['people']
        for date, catalog in self.catalogs.items():
            data, prior = catalog.data, self.parents[date].data
            with self.subTest(date=date):
                self.assertEqual(data['id'], prior['id'].replace('-v14', '-v15'))
                self.assertEqual(data['content_generation'], 15)
                self.assertEqual(catalog.rules.city_officer_capacity, 99)
                self.assertEqual(catalog.rules.battle_officers_per_side, 10)
                self.assertEqual(len(data['people']), 1023)
                for key in protected:
                    self.assertEqual(data[key], prior[key], key)
                expected_owners = dict(prior['initial_owners'])
                if date in ((249, 1), (263, 5)):
                    # Reviewed post238 Wei administration, explicitly scoped
                    # to these six corrections; all other holdings are frozen.
                    for city in ('liaodong', 'lelang', 'daifang'):
                        self.assertEqual(prior['initial_owners'][city], 'neutral')
                        expected_owners[city] = 'wei'
                self.assertEqual(data['initial_owners'], expected_owners)
                self.assertEqual(set(catalog.ids), set(portrait_people))
                for person in data['people']:
                    self.assertEqual(person['runtime_id'], self.parents[date].ids[person['person_id']])
                    self.assertIn(portrait_people[person['person_id']]['kind'], ('nes_original', 'generated'))
                self.assertTrue(data['placement_completion']['complete'])
                self.assertEqual(data['placement_completion']['pending'], 0)
                self.assertEqual(set(data['era_assignments']), set(catalog.ids))
                for assignment in data['era_assignments'].values():
                    self.assertIs(assignment['planning_complete'], True)
                    self.assertIsInstance(assignment['appearance_plan'], dict)
                    self.assertTrue(assignment['appearance_plan'])
                    self.assertNotIn(assignment['status'], PENDING)

    def test_available_people_are_present_or_explicitly_excluded_and_never_overfill(self):
        for date, catalog in self.catalogs.items():
            game = self.game(date)
            data = catalog.data
            with self.subTest(date=date):
                self.assertEqual(game.state.rng.draws, 0)
                self.assertEqual(len({o.person_id for o in game.state.officers.values()}), len(game.state.officers))
                for pid, definition in catalog.definitions.items():
                    assignment = data['era_assignments'][pid]
                    ident = catalog.ids[pid]
                    ys = year_state(definition, date[0])
                    if ys == YearState.AVAILABLE and assignment['status'] not in EXEMPT_OPENING:
                        self.assertIn(ident, game.state.officers, (date, definition.name, assignment))
                    if ys in (YearState.NOT_BORN, YearState.NOT_APPEARED, YearState.DEAD):
                        self.assertNotIn(ident, game.state.officers, (date, definition.name, ys))
                    if assignment['status'] in EXEMPT_OPENING:
                        self.assertNotIn(ident, game.state.officers, (date, definition.name, assignment['status']))
                roster_people = []
                for city in game.state.cities.values():
                    self.assertLessEqual(len(city.roster.officer_ids), 99)
                    roster_people.extend(city.roster.officer_ids)
                    for ident in city.roster.officer_ids:
                        self.assertEqual(game.state.officers[ident].faction_id, city.owner)
                self.assertEqual(len(roster_people), len(set(roster_people)))
                self.assertEqual(game.state.soldiers['initial'],
                    sum(c.reserves for c in game.state.cities.values()) +
                    sum(o.troops for o in game.state.officers.values()))

    def test_every_future_person_has_usable_dated_windows_and_an_open_city(self):
        future_count = 0
        for date, catalog in self.catalogs.items():
            for pid, definition in catalog.definitions.items():
                assignment = catalog.data['era_assignments'][pid]
                ys = year_state(definition, date[0])
                if ys not in (YearState.NOT_BORN, YearState.NOT_APPEARED) or assignment['status'] == 'scenario_excluded':
                    continue
                future_count += 1
                with self.subTest(date=date, person_id=pid):
                    windows = catalog.data['appearance_windows'].get(pid)
                    self.assertIsInstance(windows, list)
                    self.assertTrue(windows, definition.name)
                    for window in windows:
                        start, end = tuple(window['start']), tuple(window['end'])
                        self.assertLessEqual(start, end)
                        self.assertTrue(1 <= start[1] <= 12 and 1 <= end[1] <= 12)
                        self.assertIn(window['city'], catalog.map_cities)
                        self.assertIn(window['city'], catalog.active_city_ids(*start),
                                      'Use an already-open parent rather than placing an entrant in a future city')
                    self.assertIsNotNone(first_future_entry(catalog, pid), definition.name)
        self.assertGreater(future_count, 1000)

    def test_99_person_roster_boundary_preserves_the10_person_battle_limit(self):
        game = self.game((217, 7))
        side = Counter(o.faction_id for o in game.state.officers.values()
                       if o.faction_id and o.troops > 0).most_common(1)[0][0]
        ids = [i for i, o in game.state.officers.items() if o.faction_id == side and o.troops > 0]
        self.assertGreaterEqual(len(ids), 100)
        # Real people/profiles, isolated roster-service objects: a failed100th
        # transfer must leave both lists intact, not silently drop a person.
        destination = CityRoster('capacity-fixture', ids[:99], game.catalog.rules)
        source = CityRoster('source-fixture', [ids[99]], game.catalog.rules)
        before = source.officer_ids[:], destination.officer_ids[:]
        with self.assertRaises(CapacityError):
            transfer_officers(source, destination, source.officer_ids)
        self.assertEqual((source.officer_ids, destination.officer_ids), before)
        destination.officer_ids.pop()
        transfer_officers(source, destination, source.officer_ids)
        self.assertEqual(len(destination.officer_ids), 99)
        self.assertFalse(source.officer_ids)
        self.assertEqual(select_deployment(destination, destination.officer_ids[:10], game.state.officers),
                         tuple(destination.officer_ids[:10]))
        with self.assertRaises(ValueError):
            select_deployment(destination, destination.officer_ids[:11], game.state.officers)

    def test_meng_da_reviewed_city_is_used_without_changing_faction_when_unavailable(self):
        pid = 'san14-candidate-0849'
        for date in ((221, 7), (225, 7), (227, 2)):
            with self.subTest(date=date):
                game = self.game(date)
                ident = game.catalog.ids[pid]
                assignment = game.catalog.data['era_assignments'][pid]
                self.assertEqual(assignment['faction'], 'wei')
                self.assertEqual(assignment['city'], 'xincheng')
                self.assertEqual(assignment['posting_reference']['basis'], 'primary_referenced_career_posting')
                self.assertEqual(assignment['appearance_plan']['city'], 'xincheng')
                self.assertIn(ident, game.state.cities['xincheng'].roster.officer_ids)
                self.assertEqual(game.state.officers[ident].faction_id, 'wei')

        data = deepcopy(self.catalogs[225, 7].data)
        target = 'xincheng'
        faction_by_person = {row['person_id']: data['era_assignments'][row['person_id']]['faction']
                             for row in data['initial_officers']}
        wei_seat = next(f['city'] for f in data['factions'] if f['id'] == 'wei')
        self.assertNotEqual(wei_seat, target)
        # Begin with legal Wei origins while the formerly preferred city is
        # controlled by Shu. The posting service is not a defection mechanism.
        for row in data['initial_officers']:
            if row['city'] == target:
                self.assertEqual(faction_by_person[row['person_id']], 'wei')
                row['city'] = wei_seat
                data['era_assignments'][row['person_id']]['city'] = wei_seat
                data['appearance_locations'][row['person_id']] = wei_seat
        data['initial_owners'][target] = 'shu'
        audit = apply_postings(data)
        assignment = data['era_assignments'][pid]
        self.assertEqual(assignment['faction'], 'wei')
        self.assertNotEqual(assignment['city'], target)
        self.assertEqual(data['initial_owners'][assignment['city']], 'wei')
        record = next(row for row in audit['postings'] if row['person_id'] == pid)
        self.assertNotEqual(record['basis'], 'primary_referenced_career_posting')
        self.assertEqual(record['faction'], 'wei')
        for row in data['initial_officers']:
            self.assertEqual(data['initial_owners'][row['city']], faction_by_person[row['person_id']])
        self.assertTrue(all(count <= 99 for f in audit['factions'].values() for count in f['city_rosters'].values()))

    def test_qian_zhao_attested_yanmen_post_survives_only_for_its_original_faction(self):
        pid = 'san14-candidate-0236'
        game = self.game((227, 2))
        assignment = game.catalog.data['era_assignments'][pid]
        self.assertEqual(assignment['faction'], 'wei')
        self.assertEqual(assignment['city'], 'yanmen')
        self.assertEqual(assignment['posting_reference']['basis'], 'attested_yanmen_post_227')
        self.assertEqual(assignment['appearance_plan']['city'], 'yanmen')
        self.assertIn(game.catalog.ids[pid], game.state.cities['yanmen'].roster.officer_ids)

        # A changed final affiliation cannot inherit a pin recorded for Wei.
        # This is an explicit alternate-assignment fixture, not a history claim.
        sys.path.insert(0, str(ROOT / 'game'))
        try:
            from build_placement_campaigns import Planner
        finally:
            sys.path.pop(0)
        previous = deepcopy(self.parents[227, 2].data)
        old = previous['era_assignments'][pid]
        shu_seat = next(f['city'] for f in previous['factions'] if f['id'] == 'shu')
        self.assertEqual(old['posting_reference']['faction'], 'wei')
        old.update(faction='shu', city=shu_seat)
        next(r for r in previous['initial_officers'] if r['person_id'] == pid)['city'] = shu_seat
        previous['appearance_locations'][pid] = shu_seat
        result = Planner().build_catalog(previous)
        changed = result['era_assignments'][pid]
        self.assertEqual(changed['faction'], 'shu')
        self.assertEqual(result['initial_owners'][changed['city']], 'shu')
        self.assertNotEqual(changed['city'], 'yanmen')
        self.assertNotEqual(changed['posting_reference']['basis'], 'attested_yanmen_post_227')

    def test_real_calendar_boundaries_spawn_once_as_free_and_never_revive(self):
        # Exercise both unborn and not-yet-serving pools and multiple scenario
        # dates. Earliest upcoming entrants keep this a bounded calendar test.
        samples = []
        covered = set()
        for date, catalog in self.catalogs.items():
            options = []
            for pid, definition in catalog.definitions.items():
                state = year_state(definition, date[0])
                if state not in (YearState.NOT_BORN, YearState.NOT_APPEARED):
                    continue
                if catalog.data['era_assignments'][pid]['status'] == 'scenario_excluded':
                    continue
                entry = first_future_entry(catalog, pid)
                if entry:
                    months = (entry[0][0] - date[0]) * 12 + entry[0][1] - date[1]
                    options.append((state.value in covered, months, pid, entry, state.value))
            if options:
                _, _, pid, entry, state = min(options)
                samples.append((date, pid, entry))
                covered.add(state)
            if len(samples) >= 10 and len(covered) == 2:
                break
        self.assertEqual(covered, {'not_born', 'not_appeared'})
        self.assertGreaterEqual(len(samples), 10)
        for date, pid, (expected_date, expected_city) in samples:
            with self.subTest(date=date, person_id=pid, entry=expected_date):
                game = self.game(date)
                ident = game.catalog.ids[pid]
                self.assertNotIn(ident, game.state.officers)
                while (game.state.year, game.state.month) < expected_date:
                    game._spawn_eligible(game.state)
                    self.assertNotIn(ident, game.state.officers)
                    self.calendar_month(game)
                self.assertIn(ident, game.state.officers)
                officer = game.state.officers[ident]
                self.assertIsNone(officer.faction_id)
                self.assertEqual((officer.loyalty, officer.troops), (0, 0))
                self.assertEqual(game.state.extension['free_locations'][str(ident)], expected_city)
                self.assertFalse(any(ident in c.roster.officer_ids for c in game.state.cities.values()))
                before = game.to_dict()
                rng = deepcopy(game.state.rng)
                game._spawn_eligible(game.state)
                game._spawn_eligible(game.state)
                self.assertEqual(game.to_dict(), before)
                self.assertEqual(game.state.rng, rng)
                # A valid dead-free-officer fixture checks the irreversible ID
                # guard without pretending this is a natural combat death.
                officer.alive = False
                officer.health = 0
                game.validate(game.state)
                game._spawn_eligible(game.state)
                self.assertIs(game.state.officers[ident], officer)
                self.assertFalse(officer.alive)
                game.validate(game.state)

    def test_new_save_roundtrips_and_legacy_catalog_still_uses_its_own_capacity(self):
        for date in self.catalogs:
            with self.subTest(date=date):
                game = self.game(date)
                saved = game.export_save()
                restored = Campaign(game.catalog)
                restored.load_save(saved, 0)
                self.assertEqual(canonical(restored.export_save()), canonical(saved))
        old, new = self.parents[217, 7], self.catalogs[217, 7]
        session = CampaignSession([ROOT / 'game/data/main-scenarios-v14/217-07.json',
                                   ROOT / 'game/data/main-scenarios-v15/217-07.json'])
        session.command('new', {'scenario': old.data['id'], 'faction': 'wu', 'seed': 2026}, session.revision)
        saved = session.export_save()
        old_state = session.to_dict()
        session.command('new', {'scenario': new.data['id'], 'faction': 'wu', 'seed': 2026}, session.revision)
        self.assertEqual(session.game.catalog.rules.city_officer_capacity, 99)
        session.load_save(saved, session.revision)
        self.assertEqual(session.to_dict(), old_state)
        self.assertEqual(session.game.catalog.rules.city_officer_capacity, 30)
        self.assertEqual(session.game.catalog.sha256, old.sha256)

    def test_short_natural_campaign_progress_keeps_capacity_and_save_contracts(self):
        for date in ((184, 2), (217, 7), (249, 1)):
            side = 'han' if date == (184, 2) else 'wu'
            game = self.game(date, side)
            target_turn = game.state.turn + 2
            for _ in range(1500):
                if game.state.turn >= target_turn or game.state.phase == 'finished':
                    break
                phase = game.state.phase
                if phase == 'city':
                    game.command('end_turn', {}, game.revision)
                elif phase == 'ai':
                    game.command('ai', {'turn': game.state.turn}, game.revision)
                elif phase == 'battle':
                    game.command('retreat', {'battle_id': game.state.battle['id']}, game.revision)
                elif phase == 'result':
                    game.command('settle', {'battle_id': game.state.battle['id']}, game.revision)
                elif phase == 'arrivals':
                    game.command('arrivals', {}, game.revision)
                else:
                    self.fail(phase)
            self.assertGreaterEqual(game.state.turn, target_turn, (date, game.state.phase))
            game.validate(game.state)
            self.assertTrue(all(len(c.roster.officer_ids) <= 99 for c in game.state.cities.values()))
            saved = game.export_save()
            restored = Campaign(game.catalog)
            restored.load_save(saved, 0)
            self.assertEqual(restored.to_dict(), game.to_dict())

    def test_check_builder_preserves_all_published_catalog_and_portrait_bytes(self):
        parents = sorted((ROOT / 'game/data/main-scenarios-v14').glob('*.json'))
        self.assertEqual(len(parents), 26)
        for path in parents:
            relative = path.relative_to(ROOT).as_posix()
            released = subprocess.run(['git', 'show', 'HEAD:' + relative], cwd=ROOT,
                                      check=True, capture_output=True).stdout
            self.assertEqual(path.read_bytes(), released, relative)
        frozen = [p for p in (ROOT / 'game/data').rglob('*.json')
                  if 'main-scenarios-v15' not in p.parts]
        portrait_paths = [ROOT / 'game/assets/portraits/index.json',
                          ROOT / 'game/config/portrait-identity-map.json',
                          ROOT / 'game/config/portrait-originals.json',
                          ROOT / 'game/config/portrait-generated.json']
        all_paths = frozen + portrait_paths + list((ROOT / 'game/data/main-scenarios-v15').glob('*.json'))
        before = {p: file_hash(p) for p in all_paths}
        result = subprocess.run([sys.executable, '-B', 'game/build_placement_campaigns.py', '--check'],
                                cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertTrue(result.stdout.strip())
        self.assertEqual(before, {p: file_hash(p) for p in all_paths})


if __name__ == '__main__':
    unittest.main()
