"""Nine-turn food recovery through normal diplomatic and domestic orders."""
from pathlib import Path
import unittest

from test_remake_diplomacy import diplomacy_catalog
from remake import city_economy, domestic, grain_relief, grain_units, march_supply
from remake.campaign import Campaign, Catalog
from remake.strategic_ai import StrategicAI


class GrainRecoveryTests(unittest.TestCase):
    def start(self, *, producing=False):
        def configure(data):
            if producing:
                data['city_income']['jiangxia']['grain'] = 10

        game = Campaign(diplomacy_catalog(configure=configure))
        game.command('new', dict(faction='shu', seed=2026), 0)
        return game

    def test_three_month_threshold_uses_future_harvest_and_prioritizes_land(self):
        game = self.start(producing=True)
        state = game.state
        city = state.cities['jiangxia']
        city.grain = 0
        row = grain_relief.forecasts(game, state, 'shu', turns=9)[city.id]
        city.grain = -row.balances[-1] + 1
        self.assertNotIn(city.id, grain_relief.recovery(game, state, 'shu')[1])
        city.grain -= 1
        self.assertEqual(grain_relief.recovery(game, state, 'shu')[1][city.id].zero_in, 9)
        domestic.appointments(state, 'shu')['civil'] = 146
        land = state.extension['city_development']['cities'][city.id]['land']
        game.command('end_turn', {}, game.revision)
        recovered = game.state
        self.assertGreater(recovered.extension['city_development']['cities'][city.id]['land'], land)
        order = recovered.extension['command_books']['factions']['shu']['orders'][0]
        self.assertEqual((order['kind'], order['city']), ('develop_land', city.id))

    def test_empty_city_buys_food_via_the_market_before_other_orders(self):
        game = self.start()
        city = game.state.cities['jiangxia']
        city.grain = 0
        domestic.appointments(game.state, 'shu')['civil'] = 146
        old_gold = city.gold
        game.command('end_turn', {}, game.revision)
        receipt = next(row for row in game.state.extension['events']['items'] if row['kind'] == 'grain_traded')
        self.assertEqual(receipt['city_ids'], ['jiangxia'])
        self.assertEqual(receipt['details']['direction'], 'buy')
        self.assertEqual(receipt['details']['grain'], receipt['details']['batches'] * 1000)
        self.assertEqual(game.state.cities['jiangxia'].grain, receipt['details']['grain'])
        self.assertEqual(game.state.cities['jiangxia'].gold, old_gold - receipt['details']['gold'])
        self.assertEqual(game.state.extension['command_books']['factions']['shu']['orders'][0]['kind'],
                         'trade_grain')

    def test_low_faction_stock_seeks_nearby_alliance_and_pauses_offensive_plan(self):
        game = self.start()
        state = game.state
        city = state.cities['nanyang']
        city.grain = 1
        self.assertEqual(StrategicAI(game, state).grain_outlook('wei')[0], 1)
        StrategicAI(game, state).plan('wei')
        self.assertIn('wei', state.extension['ai_strategy'])
        game.command('end_turn', {}, game.revision)
        game.command('ai', dict(turn=game.state.turn), game.revision)
        self.assertNotIn('wei', game.state.extension['ai_strategy'])
        self.assertFalse(any(row['kind'] == 'attack' and row['owner'] == 'wei'
                             for row in game.state.extension['travel']['marches']))
        treaty = next(row for row in game.state.extension['events']['items']
                      if row['kind'] == 'diplomacy_result' and row['factions'][0] == 'wei')
        self.assertEqual(treaty['details']['action'], 'alliance')
        self.assertTrue(any(row['kind'] == 'grain_traded' and row['factions'] == ['wei']
                            for row in game.state.extension['events']['items']))

    def test_current_field_rates_officer_weight_and_transported_reserve_rations(self):
        path = Path(__file__).resolve().parents[1] / 'game/data/campaigns/217-07.json'
        data = Catalog(path).data
        self.assertTrue(city_economy.frontier_outpost_at(data, 'shuofang', 217, 7))
        self.assertEqual(city_economy.garrison_grain_cost(data, 'shuofang', 217, 7, 1000, 1000), 600)
        self.assertEqual(city_economy.garrison_grain_cost(data, 'jiangxia', 217, 7, 1000, 1000), 348)
        self.assertEqual(city_economy.civilian_grain(1000), 60)
        self.assertEqual(march_supply.required_grain(100, 1, 10, 50), 50)
        with grain_units.using({'extension': {'grain_scale': 10}}):
            self.assertEqual(march_supply.required_grain(100, 1, 10, 50), 25)
