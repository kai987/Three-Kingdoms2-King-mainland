"""Current dated stocks, income and live territorial-resource conservation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, canonical
from remake import civil_staff, domestic, logistics
from remake.city_economy import (apply_opening_sizes, income_at, incomes_at,
                                 profile_at, profiles_at, tier_at)
from campaign_fixtures import advance_month

FIELDS = ('gold', 'grain', 'reserves')


def synchronize(game, state, **options):
    """Manual fixtures mirror transaction reconciliation without running work."""
    logistics.synchronize(game, state)
    domestic.synchronize(game, state)
    civil_staff.synchronize(game, state, **options)


def read(path):
    return json.loads((ROOT / path).read_text())


class DatedScenarioEconomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = read('game/data/campaigns/index.json')
        cls.catalogs = {}
        for path in cls.index['catalogs']:
            catalog = Catalog(ROOT / 'game/data' / path)
            cls.catalogs[catalog.data['start_year'], catalog.data['start_month']] = catalog

    def game(self, date=(217, 7), side='wu'):
        game = Campaign(self.catalogs[date])
        game.state = game._new(side, 2026)
        game.validate(game.state)
        return game

    def test_all25_current_openings_have_dated_nonuniform_stocks_and_income(self):
        self.assertEqual(len(self.catalogs), 25)
        self.assertEqual(self.index['default'], 'mainland217-07')
        for date, catalog in self.catalogs.items():
            data = catalog.data
            with self.subTest(date=date):
                self.assertEqual(data['schema'], 'tk2-campaign-v1')
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
                    self.assertIn(profile['tier'], ('normal', 'large', 'giant'))
                    self.assertIs(profile['is_SAN14_starting_resources'], False)
                    self.assertEqual(profile['economy_reference_date'], list(date))
                    self.assertEqual(profile['economy_numeric_basis'], 'authorial_remake_balance_not_historical_measurement')
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
        # Every city's opening stock actually differs across playable dates.
        for city in self.catalogs[217, 7].map_cities:
            values = {tuple(c.data['initial_city_resources'][city][field] for field in FIELDS)
                      for c in self.catalogs.values()}
            self.assertGreater(len(values), 1, city)

    def test_city_size_and_dated_precision_are_visible_in_playable_values(self):
        data = self.catalogs[217, 7].data
        self.assertEqual(data['city_profiles']['shujun']['tier'], 'giant')
        self.assertEqual(data['city_profiles']['guanghan']['tier'], 'normal')
        self.assertEqual(data['city_profiles']['shujun']['economy_region'],
                         data['city_profiles']['guanghan']['economy_region'])
        for section in ('initial_city_resources', 'city_income'):
            for field in FIELDS:
                self.assertGreater(data[section]['shujun'][field], data[section]['guanghan'][field])
        self.assertEqual(data['city_profiles']['yingchuan']['economy_date_precision'], 'attested_annal_month')
        self.assertEqual(self.catalogs[234, 2].data['city_profiles']['danyang']['economy_date_precision'],
                         'attested_annal_month')
        for date, catalog in self.catalogs.items():
            game = self.game(date, next(iter(catalog.factions)))
            self.assertEqual(game.state.rng.draws, 0)
            for key, city in game.state.cities.items():
                self.assertEqual(tuple(getattr(city, field) for field in FIELDS),
                                 tuple(catalog.data['initial_city_resources'][key][field] for field in FIELDS))

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
                        self.assertLessEqual(len(city.roster.officer_ids), 99)
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
        advance_month(game)
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
            advance_month(game)
            game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
        game.validate(game.state)
        key, rule = 'linhai', game.catalog.data['city_foundings']['linhai']
        parent = game.state.cities[rule['parent']]
        original_owner = parent.owner
        changed_owner = next(side for side in game.catalog.factions if side != original_owner)
        for ident in list(parent.roster.officer_ids):
            recipient = next(city for city in game.state.cities.values()
                             if city.id != parent.id and city.owner == original_owner
                             and len(city.roster.officer_ids) < 99)
            parent.roster.officer_ids.remove(ident)
            recipient.roster.officer_ids.append(ident)
        # This valid ownership fixture deliberately differs from the opening
        # history. The future node must inherit the actual current owner.
        parent.owner = changed_owner
        parent.gold, parent.grain = 1011, 4021
        synchronize(game, game.state, checks=False)
        game.validate(game.state)
        before = {field: getattr(parent, field) for field in FIELDS}
        recruits = game.state.soldiers['recruited']
        rng = deepcopy(game.state.rng)
        advance_month(game)
        child = game.state.cities[key]
        income = game.catalog.data['city_income'][key] if child.owner != 'neutral' else dict.fromkeys(FIELDS, 0)
        for field in FIELDS:
            self.assertEqual(getattr(child, field), before[field] // rule['resource_divisor'] + income[field])
        self.assertEqual(child.owner, changed_owner)
        self.assertNotEqual(child.owner, original_owner)
        self.assertEqual(game.state.rng, rng)
        for field in FIELDS:
            self.assertEqual(getattr(parent, field) + getattr(child, field),
                before[field] + game.catalog.data['city_income'][parent.id][field] + income[field])
        current = game.to_dict()
        game._open_dated_cities(game.state)
        self.assertEqual(game.to_dict(), current)
        self.assertLess(child.gold, game.catalog.data['initial_city_resources'][key]['gold'])
        # Calendar death review may move existing troops but never invents them.
        self.assertGreaterEqual(game.state.soldiers['recruited'], recruits)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)

    def test_canonical_provenance_preserves_sources_without_claiming_original_numeric_setups(self):
        provenance = read('game/config/campaigns/provenance.json')
        self.assertEqual(provenance['schema'], 'tk2-campaign-promotion-provenance-v1')
        self.assertEqual(len(provenance['promoted_catalogs']), 25)
        self.assertTrue(provenance['source_urls'])
        for row in provenance['source_files']:
            self.assertRegex(row['sha256'], r'^[a-f0-9]{64}$')
        for date, catalog in self.catalogs.items():
            with self.subTest(date=date):
                for profile in catalog.data['city_profiles'].values():
                    self.assertIs(profile['is_SAN14_starting_resources'], False)
                    self.assertEqual(profile['economy_numeric_basis'],
                                     'authorial_remake_balance_not_historical_measurement')
                game = self.game(date, next(iter(catalog.factions)))
                saved = game.export_save()
                restored = Campaign(game.catalog)
                restored.load_save(saved, 0)
                self.assertEqual(canonical(restored.export_save()), canonical(saved))

    def test_reviewed_city_sizes_and_opening_economy_apply_to_all25_dates(self):
        expected = {'jingzhao': 'large', 'qiao': 'large', 'bajun': 'large',
                    'wujun': 'large', 'kuaiji': 'large', 'chenliu': 'normal',
                    'shujun': 'giant'}
        for date, catalog in self.catalogs.items():
            with self.subTest(date=date):
                data = catalog.data
                self.assertEqual(data['city_scale_rules']['basis'],
                                 'user_authored_remake_city_scale_setting')
                for city, tier in dict(expected, danyang='giant' if date >= (240, 1) else 'large').items():
                    self.assertEqual(data['city_profiles'][city]['tier'], tier, city)
                    self.assertEqual(profile_at(data, city, *date)['tier'], tier)
                    self.assertEqual(income_at(data, city, *date), data['city_income'][city])
                # These two cities share an authored regional/production profile.
                # Their sole opening-size difference is reflected in every stock.
                # Canonical date values were already quantized before this size
                # edit; changing tiers may differ by at most two stock quanta.
                for field in FIELDS:
                    self.assertLessEqual(abs(data['initial_city_resources']['qiao'][field] -
                                             data['initial_city_resources']['chenliu'][field] * 2),
                                         data['city_scale_rules']['stock_quantum'][field] * 2)
                self.assertGreater(data['city_income']['qiao']['gold'], data['city_income']['chenliu']['gold'])
                self.assertGreater(data['city_income']['qiao']['grain'], data['city_income']['chenliu']['grain'])
                self.assertGreater(data['city_income']['qiao']['reserves'], data['city_income']['chenliu']['reserves'])

    def test_jianye_size_240_boundary_uses_opening_income_without_mutating_catalog(self):
        data = self.catalogs[238, 1].data
        before = canonical(data)
        self.assertEqual(tier_at(data, 'danyang', 239, 12), 'large')
        self.assertEqual(tier_at(data, 'danyang', 240, 1), 'giant')
        self.assertEqual(profile_at(data, 'danyang', 240, 1)['tier'], 'giant')
        self.assertEqual(profiles_at(data, 240, 1)['danyang']['tier'], 'giant')
        self.assertEqual(income_at(data, 'danyang', 239, 12), data['city_income']['danyang'])
        for field in FIELDS:
            # Half-up for a 3/2 increase, consistently recomputed from the opening.
            expected = (data['city_income']['danyang'][field] * 3 + 1) // 2
            self.assertEqual(income_at(data, 'danyang', 240, 1)[field], expected)
            self.assertEqual(income_at(data, 'danyang', 249, 1)[field], expected)
        self.assertEqual(incomes_at(data, 240, 1)['danyang'], income_at(data, 'danyang', 240, 1))
        late = self.catalogs[249, 1].data
        self.assertEqual(income_at(late, 'danyang', 263, 5), late['city_income']['danyang'],
                         'A post-upgrade opening is already scaled and must never scale twice')
        profile_at(data, 'danyang', 240, 1)['tier'] = 'corrupt'
        income_at(data, 'danyang', 240, 1)['gold'] = -1
        self.assertEqual(canonical(data), before)
        self.assertEqual(income_at(data, 'missing-city', 240, 1), None)
        zero = deepcopy(data)
        zero['city_income']['danyang']['gold'] = 0
        self.assertEqual(income_at(zero, 'danyang', 240, 1)['gold'], 0,
                         'A size upgrade must not invent an absent type of production')

    def test_city_scale_builder_rejects_double_application_and_changed_source_tier(self):
        data = read('game/config/campaigns/shared.json')['catalog']
        rules = read('game/config/city-scale-rules.json')
        opening = deepcopy(data)
        apply_opening_sizes(opening, rules)
        with self.assertRaisesRegex(ValueError, 'already applied'):
            apply_opening_sizes(opening, rules)
        data['city_profiles']['jingzhao']['tier'] = 'normal'
        with self.assertRaisesRegex(ValueError, 'Canonical source tier changed'):
            apply_opening_sizes(data, rules)


if __name__ == '__main__':
    unittest.main()
