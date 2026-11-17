from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from campaign_fixtures import advance_month, controlled_catalog
from remake.campaign import Campaign
from remake.city_development import LIMITS
from remake.city_economy import frontier_maintenance, frontier_outposts_view, garrison_grain_cost, income_at, profile_at
from remake.march_supply import cost
from remake.session import CampaignSession


def land_route(source, target, days=1):
    return {'id': f'controlled:{source}:{target}', 'from': source, 'to': target,
            'mode': 'land', 'terrain': 'plain', 'distance_km': 30, 'land_km': 30,
            'sea_km': 0, 'days': days}


def frontier_catalog(troops=480):
    catalog = controlled_catalog()
    data = catalog.data
    data['frontier_outposts'] = {'nanyang': dict(from_date=[217, 12], to_date=[218, 1],
        supply_cities=['nanjun'], upkeep_gold=10)}
    data['initial_owners']['nanjun'] = 'wei'
    data['initial_officers'][0]['troops'] = troops
    data['initial_city_resources']['nanyang']['reserves'] = 0
    data['city_income']['nanyang']['reserves'] = 17
    data['links'].append(['nanyang', 'nanjun'])
    data['travel_routes'].append(land_route('nanyang', 'nanjun'))
    return catalog


class FrontierEconomyTests(unittest.TestCase):
    def test_outpost_month_adds_local_production_and_feeds_its_garrison(self):
        for troops in (0, 480):
            with self.subTest(troops=troops):
                game = Campaign(frontier_catalog(troops))
                game.command('new', dict(faction='wei', seed=310), 0)
                original = deepcopy(game.to_dict())
                advance_month(game)
                state = game.state
                outpost, rear = state.cities['nanyang'], state.cities['nanjun']
                outpost_start, rear_start = (original['cities'][key] for key in ('nanyang', 'nanjun'))
                self.assertEqual((state.year, state.month), (217, 12))
                self.assertEqual(outpost.gold, outpost_start['gold'] + 35)
                self.assertEqual(outpost.grain, outpost_start['grain'] + 900 - cost(troops + 17, 0, 30))
                self.assertEqual(outpost.reserves, outpost_start['reserves'] + 17)
                self.assertEqual(rear.gold, rear_start['gold'] + 35 - 15)
                self.assertEqual(rear.grain, rear_start['grain'] + 855)
                self.assertEqual(state.soldiers, dict(original['soldiers'], recruited=17))
                self.assertEqual(sum(state.officers[i].troops for i in outpost.roster.officer_ids), troops)

                before_restore = deepcopy(game.to_dict()['cities'])
                advance_month(game)
                outpost, rear = state.cities['nanyang'], state.cities['nanjun']
                self.assertEqual((state.year, state.month), (218, 1))
                self.assertEqual(outpost.gold, before_restore['nanyang']['gold'] + 35)
                self.assertEqual(outpost.grain, before_restore['nanyang']['grain'] + 900 - garrison_grain_cost(game.catalog.data, 'nanyang', 218, 1, troops, 17))
                self.assertEqual(rear.gold, before_restore['nanjun']['gold'] + 35)
                self.assertEqual(outpost.owner, 'wei')

    def test_population_growth_scales_production_and_rear_city_upkeep(self):
        game = Campaign(frontier_catalog(troops=0))
        game.command('new', dict(faction='wei', seed=310), 0)
        state = game.state
        outpost, rear = (state.cities[key] for key in ('nanyang', 'nanjun'))
        development = state.extension['city_development']['cities'][outpost.id]
        development['population'] *= 2
        start = outpost.gold, outpost.grain, outpost.reserves, rear.gold
        advance_month(game)
        self.assertEqual((outpost.gold, outpost.grain, outpost.reserves, rear.gold),
                         (start[0] + 70, start[1] + 1800 - cost(34, 0, 30), start[2] + 34, start[3] + 35 - 30))
        self.assertEqual(frontier_outposts_view(game.catalog.data, state)[outpost.id]['monthly_maintenance'], 30)
        self.assertEqual(development['baseline']['population'] * 2, development['population'])
        game.validate(state)
        saved = game.export_save()
        restored = Campaign(game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)

    def test_population_fee_rounds_once_and_scales_through_the_population_cap(self):
        # The outpost starts with 68,500 people.
        for population, fee in ((68_600, 16), (LIMITS['population'], 438)):
            with self.subTest(population=population):
                game = Campaign(frontier_catalog(troops=0))
                game.command('new', dict(faction='wei', seed=310), 0)
                state = game.state
                development = state.extension['city_development']['cities']['nanyang']
                development['population'] = population
                game.validate(state)
                rear = state.cities['nanjun']
                opening_gold = rear.gold
                advance_month(game)
                self.assertEqual(frontier_outposts_view(game.catalog.data, state)['nanyang']['monthly_maintenance'], fee)
                self.assertEqual(rear.gold, opening_gold + 35 - fee)

    def test_sponsor_falls_back_to_reachable_rear_and_limits_payment_to_cash(self):
        game = Campaign(frontier_catalog())
        game.command('new', dict(faction='wei', seed=310), 0)
        data, state = game.catalog.data, game.state
        state.month = 12
        outpost, rear = state.cities['nanyang'], state.cities['nanjun']
        rear.gold = 3
        outpost.grain = 1
        data['frontier_outposts']['nanyang']['supply_cities'] = ['jiangxia']
        self.assertEqual(frontier_outposts_view(data, state)['nanyang']['sponsor_city'], rear.id)
        outpost_gold = outpost.gold
        frontier_maintenance(game, state)
        self.assertEqual(rear.gold, 0)
        self.assertEqual((outpost.gold, outpost.grain), (outpost_gold, 0))
        self.assertIn('尚缺12金', state.log[-1])
        self.assertIn('粮草尚缺', state.log[-1])

        route = data['travel_routes'][-1]
        route['closures'] = [{'from': [217, 12], 'to': [218, 1]}]
        rear.gold = 35
        self.assertIsNone(frontier_outposts_view(data, state)['nanyang']['sponsor_city'])
        frontier_maintenance(game, state)
        self.assertEqual(rear.gold, 35)
        self.assertIn('未连通己方郡城', state.log[-1])

    def test_food_already_allocated_to_march_or_battle_is_not_debited_twice(self):
        game = Campaign(frontier_catalog())
        game.command('new', dict(faction='wei', seed=310), 0)
        game.state.month = 12
        officer, = game.state.cities['nanyang'].roster.officer_ids
        for marching in (True, False):
            with self.subTest(marching=marching):
                state = deepcopy(game.state)
                if not marching:
                    state.battle = {'attackers': [], 'defenders': [{'id': officer}]}
                outpost = state.cities['nanyang']
                before = outpost.grain
                with patch.object(game, '_march_ids', return_value={officer} if marching else set()):
                    frontier_maintenance(game, state)
                self.assertEqual(outpost.grain, before)

    def test_opening_and_active_api_report_dated_economy(self):
        data = frontier_catalog().data
        data['start_month'] = 12
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'frontier.json'
            path.write_text(json.dumps(data, ensure_ascii=False))
            session = CampaignSession([path])
        income = dict(data['city_income']['nanyang'], grain=900)
        setup = dict(monthly_maintenance=15, sponsor_city='nanjun')
        opening = session.preview_city(data['id'], 'nanyang')['city']
        self.assertEqual(opening['profile']['kind'], 'frontier_outpost')
        self.assertEqual(opening['income'], income)
        self.assertEqual(opening['frontier_outpost'], setup)
        self.assertNotIn('kind', profile_at(data, 'nanyang', 217, 11))
        self.assertEqual(income_at(data, 'nanyang', 218, 1), income)
        result = session.command('new', dict(faction='wei', seed=310), 0)['catalog']
        self.assertEqual(result['frontier_outposts']['nanyang'], setup)
        self.assertEqual(result['city_income']['nanyang'], income)
        self.assertEqual(result['scenarios'][0]['city_profiles']['nanyang']['kind'], 'frontier_outpost')


if __name__ == '__main__':
    unittest.main()
