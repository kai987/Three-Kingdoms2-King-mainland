"""Monthly ration billing, fine-grained openings and legacy provision receipts."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from campaign_fixtures import advance_month, confirm_default_placement, controlled_catalog
from remake import city_economy, domestic, grain_units, march_supply
from remake.campaign import Campaign
from remake.session import CampaignSession


class GrainEconomyTests(unittest.TestCase):
    def test_opening_preview_and_live_city_use_the_same_balance(self):
        path = ROOT / 'game/data/campaigns/208-10.json'
        session = CampaignSession([path])
        opening = session.preview_city('mainland208-10', 'jiangxia')['city']
        self.assertEqual(opening['grain_balance'], dict(production=1480, upkeep=2542, civilian=819, net=-1881))
        live = session.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        self.assertEqual(live['catalog']['grain_people_per_day'], 50)
        self.assertEqual(live['catalog']['city_grain_balance']['jiangxia'], opening['grain_balance'])
        self.assertEqual(live['game']['cities']['jiangxia']['grain'], opening['grain'])
        self.assertEqual(march_supply.cost(10_000, 0, 30), 6000)

    def test_grain_production_uses_one_land_point_and_one_thousand_people_per_step(self):
        session = CampaignSession([ROOT / 'game/data/campaigns/208-10.json'])
        session.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        game, state = session.game, session.game.state
        development = state.extension['city_development']['cities']['jiangxia']
        base = domestic._income(game, 'jiangxia', state)
        for population, expected in [(27_000, 1480), (27_900, 1480), (28_000, 1534), (28_900, 1534), (29_000, 1588)]:
            with self.subTest(population=population):
                development['population'] = population
                self.assertEqual(domestic._income(game, 'jiangxia', state)['grain'], expected)
        development['population'] = 27300
        for land, expected in [(0, 752), (27, 924), (113, 1472), (114, 1480), (115, 1486), (116, 1492), (999, 7124)]:
            with self.subTest(land=land):
                development['land'] = land
                income = domestic._income(game, 'jiangxia', state)
                self.assertEqual((income['grain'], income['gold']), (expected, base['gold']))
        development['land'] = 115
        facilities = state.extension['facilities']['cities']['jiangxia']
        facilities['damage'] = 1
        self.assertEqual(domestic._income(game, 'jiangxia', state)['grain'], 1470)
        facilities['damage'] = 0
        development['baseline']['population'] = 200
        development['population'] = 900
        self.assertEqual(domestic._income(game, 'jiangxia', state)['grain'], 0)
        development.update(population=1_000, land=114)
        self.assertEqual(domestic._income(game, 'jiangxia', state)['grain'], 1480)

    def test_monthly_bill_has_one_rounding_and_caps_withdrawal_at_stock(self):
        game = Campaign(controlled_catalog())
        game.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        state = game.state
        city = state.cities['xiangyang']
        upkeep = city_economy.garrison_grain(game, state)[city.id]
        stocks = city.grain
        production = 2 * city_economy.income_at(game.catalog.data, city.id, state.year, state.month)['grain']
        self.assertEqual(city_economy.garrison_grain_cost(game.catalog.data, city.id, state.year,
                                                       state.month, 999, 333), 210)
        advance_month(game)
        self.assertEqual(city.grain, stocks + production - upkeep - city_economy.civilian_grain(state.extension['city_development']['cities'][city.id]['population']))

        state = game.state
        city = state.cities['xiangyang']
        game.catalog.data['city_income'][city.id]['grain'] = 0
        city.grain = 1
        soldiers = deepcopy(state.soldiers)
        advance_month(game)
        self.assertEqual(city.grain, 0)
        self.assertGreater(state.soldiers['lost'], soldiers['lost'])
        self.assertTrue(any('本旬缺粮' in line for line in state.log))

    def test_partial_shortage_exact_payment_and_total_shortage_each_turn(self):
        for share in (0, 50, 100):
            with self.subTest(share=share):
                game = Campaign(controlled_catalog())
                game.command('new', {'faction': 'shu', 'seed': 2026}, 0)
                state = game.state
                city = state.cities['xiangyang']
                row = state.extension['city_development']['cities'][city.id]
                row.update(population=100000, governance=80, land=400, industry=300)
                before = dict(row)
                count = {i: state.officers[i].troops for i in city.roster.officer_ids}
                reserves, lost = city.reserves, state.soldiers['lost']
                need = (city_economy.garrison_grain(game,state)[city.id] + city_economy.civilian_grain(100000)) // 3
                city.grain = need * share // 100
                short = need - city.grain
                game._complete_turn(state)
                self.assertEqual(city.grain, 0)
                self.assertEqual(row.get('garrison_spirit',100), 100 - 100 * short // (10 * need))
                self.assertEqual(row['population'], 100000 - 100 * (1000 * short // (10 * need)))
                for field in ('land','industry','governance'):
                    self.assertEqual(row[field], before[field] - before[field] * short // (10 * need))
                self.assertEqual(city.reserves, reserves - reserves * short // (10 * need))
                for ident,troops in count.items():
                    self.assertEqual(state.officers[ident].troops, troops - troops * short // (10 * need))
                self.assertEqual(state.soldiers['lost'] - lost, reserves - city.reserves
                                 + sum(v - state.officers[i].troops for i,v in count.items()))
                game.validate(state)
                restored = Campaign(game.catalog)
                restored.load_save(game.export_save(compact=True),0)
                self.assertEqual(restored.to_dict(), game.to_dict())

    def test_legacy_march_can_resume_with_the_original_receipt_and_stock(self):
        create = Campaign._new

        def open_in_legacy_units(game, *args):
            with grain_units.using({'extension': {}}):
                state = create(game, *args)
            del state.extension[grain_units.FIELD]
            return state

        game = Campaign(controlled_catalog())
        with patch.object(Campaign, '_new', open_in_legacy_units):
            game.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        game.command('depart', {'source': 'xiangyang', 'target': 'nanyang', 'officers': [146]}, game.revision)
        saved = game.export_save()
        restored = Campaign(game.catalog)
        view = restored.load_save(saved, 0)
        self.assertEqual(view['catalog']['grain_people_per_day'], 1000)
        self.assertEqual(restored.export_save(), saved)
        supply = restored.state.extension['travel']['marches'][0]['supply']
        self.assertEqual(supply['loaded'], 10)
        restored.command('end_turn', {}, restored.revision)
        restored.command('ai', {'turn': restored.state.turn}, restored.revision)
        if restored.state.phase == 'arrivals':
            restored.command('arrivals', {}, restored.revision)
        self.assertEqual(restored.state.phase, 'battle')
        confirm_default_placement(restored)
        bags = restored.state.battle['extended']['supply']['sides']['attackers']
        self.assertEqual((bags['loaded'], bags['initial_credit']), (9, 720))
        battle_save = restored.export_save()
        in_battle = Campaign(game.catalog)
        in_battle.load_save(battle_save, 0)
        self.assertEqual(in_battle.export_save(), battle_save)

        fresh = restored.command('new', {'faction': 'shu', 'seed': 2026}, restored.revision)
        self.assertEqual(fresh['catalog']['grain_people_per_day'], 50)
        self.assertEqual(fresh['game']['cities']['xiangyang']['grain'],
                         10 * game.catalog.opening_garrisons[0]['xiangyang']['grain'])


if __name__ == '__main__':
    unittest.main()
