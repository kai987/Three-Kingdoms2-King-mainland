"""Date-aware city stocks preserve the released catalogs and live-game rules."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))
from remake.campaign import Campaign, Catalog, canonical
from build_economy_campaigns import city_values, phase_at, scale, validate_spec

FIELDS = ('gold', 'grain', 'reserves')


def read(path):
    return json.loads((ROOT / path).read_text())


class DatedScenarioEconomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = read('game/data/main-scenarios-v14/index.json')
        cls.spec = read('game/config/scenario-economy.json')
        cls.catalogs = {}
        for path in cls.index['catalogs']:
            catalog = Catalog(ROOT / 'game/data' / path)
            cls.catalogs[catalog.data['start_year'], catalog.data['start_month']] = catalog

    def game(self, date=(217, 7), side='wu'):
        game = Campaign(self.catalogs[date])
        game.state = game._new(side, 2026)
        game.validate(game.state)
        return game

    def test_all25_openings_change_only_economy_and_keep_rosters_and_map(self):
        self.assertEqual(len(self.catalogs), 25)
        self.assertEqual(self.index['default'], 'mainland217-07-v14')
        unchanged = ('people', 'rules', 'initial_owners', 'initial_officers',
                     'initial_free_officers', 'era_assignments', 'appearance_locations',
                     'appearance_windows', 'factions', 'faction_rulers', 'cities',
                     'active_cities', 'city_foundings', 'links', 'travel_rules',
                     'travel_routes', 'travel_hazards', 'exploration_routes', 'world')
        for date, catalog in self.catalogs.items():
            data = catalog.data
            prior = read(f'game/data/main-scenarios-v13/{date[0]}-{date[1]:02d}.json')
            with self.subTest(date=date):
                self.assertEqual(data['content_generation'], 14)
                self.assertEqual(data['id'], prior['id'].replace('-v13', '-v14'))
                for key in unchanged:
                    self.assertEqual(data[key], prior[key], key)
                self.assertEqual(data['city_economy']['source_catalog'], prior['id'])
                self.assertEqual(data['city_economy']['reference_date'], list(date))
                self.assertEqual(data['main_scenario']['city_economy'], self.spec['schema'])
                self.assertTrue(all(r['troops'] == 300 for r in data['initial_officers']))
                patterns = {tuple(data['initial_city_resources'][key][field] for field in FIELDS)
                            for key in data['active_cities']}
                self.assertGreaterEqual(len(patterns), 25)
                for city in data['cities']:
                    key = city['id']
                    for values in (data['initial_city_resources'][key], data['city_income'][key]):
                        self.assertEqual(set(values), set(FIELDS))
                        self.assertTrue(all(type(value) is int and 0 < value < 100000 for value in values.values()))
                    profile = data['city_profiles'][key]
                    self.assertEqual(profile['tier'], prior['city_profiles'][key]['tier'])
                    self.assertIs(profile['is_SAN14_starting_resources'], False)
                    self.assertEqual(profile['economy_reference_date'], list(date))
                    self.assertTrue(profile['economy_period_label_tc'])
                    self.assertTrue(profile['economy_period_label_ja'])

    def test_city_history_has_rises_and_falls_instead_of_uniform_late_growth(self):
        def stock(date, city, field='grain'):
            return self.catalogs[date].data['initial_city_resources'][city][field]
        # January190 is still before the configured February destruction boundary.
        self.assertGreater(stock((190, 1), 'henan'), stock((191, 10), 'henan'))
        self.assertGreater(stock((221, 7), 'henan'), stock((191, 10), 'henan'))
        self.assertGreater(stock((197, 7), 'yingchuan'), stock((196, 6), 'yingchuan'))
        self.assertGreater(stock((234, 2), 'danyang'), stock((211, 7), 'danyang'))
        self.assertLess(stock((263, 5), 'danyang'), stock((249, 1), 'danyang'))
        self.assertLess(stock((219, 7), 'hanzhong'), stock((217, 7), 'hanzhong'))
        self.assertGreater(stock((227, 2), 'hanzhong', 'reserves'), stock((219, 7), 'hanzhong', 'reserves'))
        self.assertLess(stock((263, 5), 'shujun'), stock((221, 7), 'shujun'))
        for field in FIELDS:
            self.assertGreater(stock((249, 1), 'wei', field), stock((200, 1), 'wei', field))
        # Every city's opening stock actually differs across released dates.
        for city in self.catalogs[217, 7].map_cities:
            values = {tuple(c.data['initial_city_resources'][city][field] for field in FIELDS)
                      for c in self.catalogs.values()}
            self.assertGreater(len(values), 1, city)

    def test_month_boundaries_and_city_size_are_explicit_not_random(self):
        prior = read('game/data/main-scenarios-v13/196-06.json')
        before, _, _ = city_values(prior, self.spec, 'yingchuan', (196, 7))
        after, _, _ = city_values(prior, self.spec, 'yingchuan', (196, 8))
        for field in FIELDS:
            self.assertGreater(after[field], before[field])
        before, _, _ = city_values(prior, self.spec, 'henan', (190, 1))
        after, _, _ = city_values(prior, self.spec, 'henan', (190, 2))
        for field in FIELDS:
            self.assertLess(after[field], before[field])
        before, _, _ = city_values(prior, self.spec, 'danyang', (229, 8))
        after, _, profile = city_values(prior, self.spec, 'danyang', (229, 9))
        self.assertEqual(profile['economy_date_precision'], 'attested_annal_month')
        for field in FIELDS:
            self.assertGreater(after[field], before[field])
        city = 'shujun'
        actual, income, _ = city_values(prior, self.spec, city, (217, 7))
        ordinary = deepcopy(prior)
        for section, values in (('initial_city_resources', dict(gold=1200, grain=3800, reserves=1200)),
                                ('city_income', dict(gold=35, grain=90, reserves=30))):
            ordinary[section][city] = values
        normal, normal_income, _ = city_values(ordinary, self.spec, city, (217, 7))
        for field in FIELDS:
            self.assertGreater(actual[field], normal[field])
            self.assertGreater(income[field], normal_income[field])
        self.assertEqual(scale(1, [50], 1), 1)
        self.assertEqual(scale(125, [100], 10), 130)
        self.assertEqual(phase_at([dict(from_date=[196, 8])], (196, 7)), None)

    def test_every_faction_can_start_and_soldier_initial_ledger_matches_new_reserves(self):
        starts = 0
        for date, catalog in self.catalogs.items():
            for side in catalog.factions:
                with self.subTest(date=date, side=side):
                    game = Campaign(catalog)
                    game.state = game._new(side, 2026)
                    game.validate(game.state)
                    self.assertEqual(game.state.rng.draws, 0)
                    self.assertEqual(game.state.soldiers['initial'],
                        sum(city.reserves for city in game.state.cities.values()) +
                        sum(officer.troops for officer in game.state.officers.values()))
                    for city in game.state.cities.values():
                        self.assertEqual(tuple(getattr(city, field) for field in FIELDS),
                                         tuple(catalog.data['initial_city_resources'][city.id][field] for field in FIELDS))
                        self.assertLessEqual(len(city.roster.officer_ids), 30)
                    starts += 1
        self.assertGreaterEqual(starts, 200)

    def test_monthly_income_and_real_spending_preserve_live_stocks_and_rng(self):
        game = self.game()
        city = next(c for c in game.state.cities.values()
                    if c.owner == game.state.player and c.roster.officer_ids and c.gold > 100 and c.grain > 100)
        officer = city.roster.officer_ids[0]
        before = city.gold, city.grain, city.reserves
        game.command('recruit', dict(city=city.id), game.revision)
        city = game.state.cities[city.id]
        self.assertLess(city.gold, before[0])
        self.assertLess(city.grain, before[1])
        self.assertGreater(city.reserves, before[2])
        recruited_reserves = city.reserves
        game.command('allocate', dict(city=city.id, officer=officer, troops=310), game.revision)
        self.assertEqual(game.state.cities[city.id].reserves, recruited_reserves - 10)
        before = {key: tuple(getattr(c, field) for field in FIELDS) for key, c in game.state.cities.items()}
        rng = deepcopy(game.state.rng)
        recruited = game.state.soldiers['recruited']
        game._complete_month(game.state)
        expected_recruits = 0
        for key, city in game.state.cities.items():
            expected = game.catalog.data['city_income'][key] if city.owner != 'neutral' else dict.fromkeys(FIELDS, 0)
            self.assertEqual(tuple(getattr(city, field) for field in FIELDS),
                             tuple(before[key][i] + expected[field] for i, field in enumerate(FIELDS)))
            expected_recruits += expected['reserves']
        self.assertEqual(game.state.soldiers['recruited'] - recruited, expected_recruits)
        self.assertEqual(game.state.rng, rng)
        game.validate(game.state)
        saved = game.export_save()
        restored = Campaign(game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(canonical(restored.export_save()), canonical(saved))

    def test_foundation_still_transfers_actual_parent_resources_not_future_static_stocks(self):
        game = self.game((249, 1))
        # Direct calendar-service boundary fixture: historical event only opens
        # the node, while actual holdings and current resources are conserved.
        while (game.state.year, game.state.month) < (257, 1):
            game._complete_month(game.state)
            game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
        game.validate(game.state)
        key, rule = 'linhai', game.catalog.data['city_foundings']['linhai']
        parent = game.state.cities[rule['parent']]
        parent.gold, parent.grain = 1011, 4021
        before = {field: getattr(parent, field) for field in FIELDS}
        recruits = game.state.soldiers['recruited']
        game._complete_month(game.state)
        child = game.state.cities[key]
        income = game.catalog.data['city_income'][key] if child.owner != 'neutral' else dict.fromkeys(FIELDS, 0)
        for field in FIELDS:
            self.assertEqual(getattr(child, field), before[field] // rule['resource_divisor'] + income[field])
        self.assertEqual(child.owner, parent.owner)
        self.assertLess(child.gold, game.catalog.data['initial_city_resources'][key]['gold'])
        # Calendar death review may move existing troops but never invents them.
        self.assertGreaterEqual(game.state.soldiers['recruited'], recruits)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)

    def test_source_marks_balance_design_and_rebuild_keeps_all_released_bytes(self):
        self.assertTrue(self.spec['sources'])
        self.assertIn('no numerical value', self.spec['scope'].lower())
        with self.assertRaises(ValueError):
            malformed = deepcopy(self.spec)
            malformed['regions']['hebei']['cities'].append('henan')
            validate_spec(malformed, self.catalogs[217, 7].map_cities)
        paths = list((ROOT / 'game/data').rglob('*.json'))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        subprocess.run([sys.executable, '-B', 'game/build_economy_campaigns.py'], cwd=ROOT,
                       check=True, capture_output=True)
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        old = Campaign(Catalog(ROOT / 'game/data/main-scenarios-v13/217-07.json'))
        old.state = old._new('wu', 2026)
        old.validate(old.state)
        saved = old.export_save()
        restored = Campaign(old.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(canonical(restored.export_save()), canonical(saved))
        self.assertEqual(old.state.cities['hepu'].gold, 1200)
        self.assertNotEqual(self.catalogs[217, 7].data['initial_city_resources']['hepu']['gold'], 1200)


if __name__ == '__main__':
    unittest.main()
