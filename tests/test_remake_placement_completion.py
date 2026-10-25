"""Current dated plans, calendar behavior and canonical rebuild invariants."""
from copy import deepcopy
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, GameError, canonical
from remake.officers import (CapacityError, CityRoster, YearState, select_deployment,
                            transfer_officers, year_state)
from remake.session import CampaignSession
from campaign_fixtures import advance_month


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
        cls.index = read('game/data/campaigns/index.json')
        cls.catalogs = {}
        for filename in cls.index['catalogs']:
            catalog = Catalog(ROOT / 'game/data' / filename)
            date = catalog.data['start_year'], catalog.data['start_month']
            key = date + (catalog.data['scenario_variant'],) if catalog.data.get('scenario_variant') else date
            cls.catalogs[key] = catalog
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
        advance_month(game)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)

    def test_all_current_catalogs_have_complete_stable_person_and_board_identities(self):
        self.assertEqual(len(self.catalogs), 29)
        self.assertEqual(self.index['schema'], 'tk2-campaign-index-v1')
        self.assertEqual(self.index['default'], 'mainland217-07')
        portrait_people = self.portrait_index['people']
        stable = self.catalogs[217, 7]
        shared_board = ('cities', 'links', 'city_foundings', 'travel_routes',
                        'travel_hazards', 'sea_routes', 'exploration_routes', 'world')
        for date, catalog in self.catalogs.items():
            data = catalog.data
            with self.subTest(date=date):
                self.assertEqual(data['id'], f'mainland{date[0]}-{date[1]:02d}' + ('-' + date[2] if len(date) == 3 else ''))
                self.assertEqual(data['schema'], 'tk2-campaign-v1')
                self.assertNotIn('content_generation', data)
                self.assertEqual(catalog.rules.city_officer_capacity, 99)
                self.assertEqual(catalog.rules.battle_officers_per_side, 10)
                self.assertEqual(len(data['people']), 1030)
                for key in shared_board:
                    self.assertEqual(data[key], stable.data[key], key)
                self.assertEqual(set(catalog.ids), set(portrait_people))
                for person in data['people']:
                    self.assertEqual(person['runtime_id'], stable.ids[person['person_id']])
                    self.assertIsNotNone(person['profile']['virtue'])
                    self.assertIn(portrait_people[person['person_id']]['kind'], ('nes_original', 'generated'))
                if date in ((249, 1), (263, 5)):
                    for city in ('liaodong', 'lelang', 'daifang'):
                        self.assertEqual(data['initial_owners'][city], 'wei')
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
            for city, founding in catalog.data['city_foundings'].items():
                opening = founding['year'], founding.get('month', 1)
                before = (opening[0], opening[1] - 1) if opening[1] > 1 else (opening[0] - 1, 12)
                with self.subTest(date=date, city=city, opening=opening):
                    self.assertNotIn(city, catalog.active_city_ids(*before))
                    self.assertIn(city, catalog.active_city_ids(*opening))
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

    def test_meng_da_is_actually_stationed_at_xincheng_for_wei(self):
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

    def test_qian_zhao_is_actually_stationed_at_yanmen_for_wei(self):
        pid = 'san14-candidate-0236'
        game = self.game((227, 2))
        assignment = game.catalog.data['era_assignments'][pid]
        self.assertEqual(assignment['faction'], 'wei')
        self.assertEqual(assignment['city'], 'yanmen')
        self.assertEqual(assignment['posting_reference']['basis'], 'attested_yanmen_post_227')
        self.assertEqual(assignment['appearance_plan']['city'], 'yanmen')
        self.assertIn(game.catalog.ids[pid], game.state.cities['yanmen'].roster.officer_ids)

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

    def test_all_current_saves_roundtrip_and_retired_scenario_ids_are_atomic_rejections(self):
        for date in self.catalogs:
            with self.subTest(date=date):
                game = self.game(date)
                saved = game.export_save()
                restored = Campaign(game.catalog)
                restored.load_save(saved, 0)
                self.assertEqual(canonical(restored.export_save()), canonical(saved))
        session = CampaignSession([ROOT / 'game/data' / name for name in self.index['catalogs']])
        session.command('new', dict(scenario='mainland217-07', faction='wu', seed=2026), session.revision)
        saved, revision = session.export_save(), session.revision
        for retired in ('mainland217-07-v14', 'mainland217-07-v15', 'mainland217-v3'):
            with self.subTest(retired=retired):
                with self.assertRaises(GameError):
                    session.command('new', dict(scenario=retired, faction='wu', seed=2026), session.revision)
                invalid = deepcopy(saved)
                invalid['scenario'] = retired
                with self.assertRaises(GameError):
                    session.load_save(invalid, session.revision)
                self.assertEqual(session.export_save(), saved)
                self.assertEqual(session.revision, revision)
                self.assertEqual(session.game.catalog.rules.city_officer_capacity, 99)

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

    def test_canonical_rebuild_preserves_sources_catalogs_and_portrait_bytes(self):
        paths = list((ROOT / 'game/config/campaigns').rglob('*.json'))
        paths += list((ROOT / 'game/data/campaigns').glob('*.json'))
        paths += [ROOT / 'game/assets/portraits/index.json',
                  ROOT / 'game/config/portrait-identity-map.json',
                  ROOT / 'game/config/portrait-originals.json',
                  ROOT / 'game/config/portrait-generated.json']
        before = {p: file_hash(p) for p in paths}
        result = subprocess.run([sys.executable, '-B', 'game/build_campaigns.py', '--check'],
                                cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['catalogs'], 29)
        # Fail any attempt to read a generated catalog while independently
        # rebuilding. Canonical inputs alone must reproduce every current byte.
        with tempfile.TemporaryDirectory() as directory:
            script = r'''import importlib.util, pathlib, sys
root = pathlib.Path.cwd()
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = pathlib.Path(args[0]).resolve()
        if path.is_relative_to(root / 'game/data'):
            raise AssertionError('Generated catalog was used as a build input')
sys.addaudithook(audit)
spec = importlib.util.spec_from_file_location('canonical_builder', root / 'game/build_campaigns.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.build(output=pathlib.Path(sys.argv[1]))
'''
            subprocess.run([sys.executable, '-B', '-c', script, directory], cwd=ROOT,
                           check=True, capture_output=True, text=True)
            generated = Path(directory)
            self.assertEqual({p.name for p in generated.glob('*.json')},
                             {p.name for p in (ROOT / 'game/data/campaigns').glob('*.json')})
            for rebuilt in generated.glob('*.json'):
                self.assertEqual(rebuilt.read_bytes(), (ROOT / 'game/data/campaigns' / rebuilt.name).read_bytes())
        self.assertEqual(before, {p: file_hash(p) for p in paths})


if __name__ == '__main__':
    unittest.main()
