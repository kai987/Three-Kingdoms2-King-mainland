"""Agriculture V2 boundaries, authoritative previews and saved version compatibility."""
from decimal import Decimal, localcontext
from pathlib import Path
from random import Random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from campaign_fixtures import controlled_catalog
from remake import city_development, city_economy, economy_rules, grain_market, grain_units
from remake.campaign import Campaign, digest
from remake.session import CampaignSession


def reference_adjusted(base, population, town, land, opening_land, tax, opening_tax):
    """Independent high-precision oracle for the design formula."""
    cap, percent = {1: (50_000, 103), 2: (90_000, 104), 3: (150_000, 105)}[town]

    def land_yield(value):
        first = Decimal(min(value, 300)) * Decimal('0.75')
        middle = Decimal(max(min(value, 600) - 300, 0)) * Decimal('0.60')
        last = Decimal(max(value - 600, 0)) * Decimal('0.50')
        return first + middle + last

    with localcontext() as context:
        context.prec = 75
        residents = Decimal(min(population, cap)) / 100_000
        reference_land = Decimal(60 + opening_land)
        developed = reference_land + land_yield(land) - land_yield(opening_land)
        return int(2 * base * residents ** Decimal('0.7') * percent / 100 *
                   developed / reference_land * tax / opening_tax)


class AgricultureV2Tests(unittest.TestCase):
    def test_jiangxia_preview_live_and_upgrade_at_low_population(self):
        path = ROOT / 'game/data/campaigns/208-10.json'
        session = CampaignSession([path])
        opening = session.preview_city('mainland208-10', 'jiangxia')['city']
        view = session.command('new', dict(faction='shu', seed=2026), 0)
        self.assertEqual(opening['grain_balance'], dict(production=1228, upkeep=2542, civilian=492, net=-1806))
        self.assertEqual(view['catalog']['city_agriculture']['jiangxia'], opening['agriculture'])
        self.assertEqual(opening['agriculture']['net_grain'], -2346)
        projection = view['catalog']['facilities']['cities']['jiangxia']['develop']['agriculture']
        self.assertEqual(projection['after'],
                         dict(population_cap=90000, town_bonus_percent=4, civilian_grain=656,
                              regular_grain=1240, net_grain=-2498))
        snapshot = session.export_save()
        self.assertEqual(session.view()['catalog']['city_agriculture']['jiangxia'], opening['agriculture'])
        self.assertEqual(session.export_save(), snapshot)
        facility = view['catalog']['facilities']['cities']['jiangxia']
        actor = facility['eligible_actors'][0]
        upgraded = session.command('develop_town', {'city': 'jiangxia', 'actor': actor}, view['revision'])
        result = upgraded['catalog']['city_agriculture']['jiangxia']
        self.assertEqual({k: result[k] for k in projection['after']}, projection['after'])

    def test_jiangxia_population_and_full_land_reference(self):
        rows = {
            0: (0, 0, 0), 100: (24, 24, 24), 1000: (120, 122, 122), 2000: (196, 198, 200),
            27300: (1228, 1240, 1252), 50000: (1876, 1894, 1912), 70000: (1876, 2398, 2420),
            90000: (1876, 2858, 2886), 150000: (1876, 2858, 4128),
            500000: (1876, 2858, 4128), 1999999: (1876, 2858, 4128),
        }
        self.assertGreater(economy_rules.population_multiplier(150_000), 2)
        for pop, expected in rows.items():
            actual = tuple(2 * economy_rules.adjusted_grain(740, pop, town, 114, 114, 60, 60)
                           for town in (1, 2, 3))
            self.assertEqual(actual, expected, pop)
        for town, population, production, bill in ((1, 50000, 12456, 900), (2, 90000, 18980, 2160),
                                                     (3, 150000, 27400, 4500)):
            self.assertEqual(2 * economy_rules.adjusted_grain(740, population, town, 999, 114, 100, 60), production)
            self.assertEqual(city_economy.civilian_grain(population, town), bill)

    def test_land_and_tax_edges_damage_and_recovery(self):
        increments = {1: 15, 299: 15, 300: 15, 301: 12, 599: 12, 600: 12, 601: 10, 998: 10, 999: 10}
        self.assertEqual(economy_rules.land_yield_units(0), 0)
        for point, increment in increments.items():
            self.assertEqual(economy_rules.land_yield_units(point)-economy_rules.land_yield_units(point-1), increment)
        for opening in (0, 114, 299, 600, 999):
            self.assertEqual(*economy_rules.land_factors(opening, opening))
            for land in (0, *increments):
                for tax in (50, 60, 70, 80, 90, 100):
                    expected = reference_adjusted(740, 27300, 1, land, opening, tax, 60)
                    self.assertEqual(economy_rules.adjusted_grain(740, 27300, 1, land, opening, tax, 60), expected)
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        state = game.state
        city = 'xiangyang'
        before = city_economy.monthly_income(game, city, state)['grain']
        for damage in (0, 10, 25, 50):
            state.extension['facilities']['cities'][city]['damage'] = damage
            self.assertEqual(city_economy.monthly_income(game, city, state)['grain'], 2 * ((before // 2) * (100-damage) // 100))
        state.extension['facilities']['cities'][city]['damage'] = 0
        development = state.extension['city_development']['cities'][city]
        opening_land = development['baseline']['land']
        city_development.on_disaster(game, state, city, 'flood', 25)
        self.assertLess(city_economy.monthly_income(game, city, state)['grain'], before)
        development['land'] = opening_land
        self.assertEqual(city_economy.monthly_income(game, city, state)['grain'], before)

    def test_1200_seeded_random_agricultural_cases(self):
        rng = Random(20261124)
        for index in range(1200):
            town, base = rng.randint(1, 3), rng.randint(0, 100000)
            pop = rng.randrange(0, 1_999_999)
            land, opening = rng.randrange(1000), rng.randrange(1000)
            current_tax, opening_tax = (50 + 10*rng.randrange(6) for _ in range(2))
            args = base, pop, town, land, opening, current_tax, opening_tax
            actual = economy_rules.adjusted_grain(*args)
            self.assertEqual(actual, reference_adjusted(*args), (index, args))
            self.assertGreaterEqual(actual, 0)
            self.assertEqual(actual, economy_rules.adjusted_grain(*args))
            self.assertGreaterEqual(economy_rules.adjusted_grain(base, pop+100, town, land, opening, current_tax, opening_tax), actual)
            self.assertGreaterEqual(economy_rules.adjusted_grain(base, pop, town, land+1, opening, current_tax, opening_tax), actual)
            cap = {1: 50_000, 2: 90_000, 3: 150_000}[town]
            saturated = economy_rules.adjusted_grain(base, cap, town, land, opening, current_tax, opening_tax)
            self.assertEqual(saturated, economy_rules.adjusted_grain(base, cap+100, town, land, opening, current_tax, opening_tax))
            bill = city_economy.civilian_grain(pop, town)
            self.assertGreaterEqual(bill, 0)
            self.assertEqual(bill, (pop * (town+2) * 30 + 4999) // 5000)

    def test_old_unmarked_save_preserves_published_rule_and_stock(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        state = game.state
        self.assertEqual(economy_rules.version(state), 2)
        save = game.export_save()
        save['state']['extension'].pop(economy_rules.FIELD)
        save['state']['extension'].pop(grain_market.FIELD)
        save['checksum'] = digest({k: v for k, v in save.items() if k!='checksum'})
        old = Campaign(game.catalog)
        old.load_save(save, 0)
        self.assertEqual(old.export_save(), save)
        self.assertEqual(economy_rules.version(old.state), 1)
        for city, row in old.state.extension['city_development']['cities'].items():
            self.assertEqual(city_development.adjust_income(old, old.state, city, {'grain': 400})['grain'], 400)
            self.assertEqual(city_economy.civilian_grain(row['population'], 1, state=old.state),
                             city_economy.civilian_grain(row['population'], 3, state=old.state))
        for compact in (False, True):
            restored = Campaign(game.catalog)
            restored.load_save(game.export_save(compact=compact), 0)
            self.assertEqual(economy_rules.version(restored.state), 2)
            self.assertEqual(restored.to_dict(), game.to_dict())
        self.assertEqual(grain_units.denominator(), 50)
