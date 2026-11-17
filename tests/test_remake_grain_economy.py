"""Monthly ration billing, fine-grained openings and legacy provision receipts."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from campaign_fixtures import advance_month, confirm_default_placement, controlled_catalog
from remake import city_economy, grain_units, march_supply
from remake.campaign import Campaign
from remake.session import CampaignSession


class GrainEconomyTests(unittest.TestCase):
    def test_opening_preview_and_live_city_use_the_same_balance(self):
        path = ROOT / 'game/data/campaigns/208-10.json'
        session = CampaignSession([path])
        opening = session.preview_city('mainland208-10', 'jiangxia')['city']
        self.assertEqual(opening['grain_balance'], dict(production=740, upkeep=1486, net=-746))
        live = session.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        self.assertEqual(live['catalog']['grain_people_per_day'], 100)
        self.assertEqual(live['catalog']['city_grain_balance']['jiangxia'], opening['grain_balance'])
        self.assertEqual(live['game']['cities']['jiangxia']['grain'], opening['grain'])
        self.assertEqual(march_supply.cost(10_000, 0, 30), 3000)

    def test_monthly_bill_has_one_rounding_and_caps_withdrawal_at_stock(self):
        game = Campaign(controlled_catalog())
        game.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        state = game.state
        city = state.cities['xiangyang']
        upkeep = city_economy.garrison_grain(game, state)[city.id]
        stocks = city.grain
        production = city_economy.income_at(game.catalog.data, city.id, state.year, state.month)['grain']
        self.assertEqual(city_economy.garrison_grain_cost(game.catalog.data, city.id, state.year,
                                                       state.month, 999, 333), 85)
        advance_month(game)
        self.assertEqual(city.grain, stocks + production - upkeep)

        state = game.state
        city = state.cities['xiangyang']
        game.catalog.data['city_income'][city.id]['grain'] = 0
        city.grain = 1
        soldiers = deepcopy(state.soldiers)
        advance_month(game)
        self.assertEqual(city.grain, 0)
        self.assertEqual(state.soldiers['lost'], soldiers['lost'])
        self.assertTrue(any('驻军粮草不足' in line for line in state.log))

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
        self.assertEqual(fresh['catalog']['grain_people_per_day'], 100)
        self.assertEqual(fresh['game']['cities']['xiangyang']['grain'],
                         10 * game.catalog.opening_garrisons[0]['xiangyang']['grain'])


if __name__ == '__main__':
    unittest.main()
