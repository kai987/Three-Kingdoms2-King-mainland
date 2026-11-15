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
from remake.city_economy import frontier_maintenance, frontier_outposts_view, income_at, profile_at
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
    data['links'].append(['nanyang', 'nanjun'])
    data['travel_routes'].append(land_route('nanyang', 'nanjun'))
    return catalog


class FrontierEconomyTests(unittest.TestCase):
    def test_outpost_month_has_no_production_and_only_food_scales_with_troops(self):
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
                self.assertEqual(outpost.gold, outpost_start['gold'])
                self.assertEqual(outpost.grain, outpost_start['grain'] - cost(troops, 0, 30))
                self.assertEqual(outpost.reserves, outpost_start['reserves'])
                self.assertEqual(rear.gold, rear_start['gold'] + 35 - 10)
                self.assertEqual(rear.grain, rear_start['grain'] + 90)
                self.assertEqual(state.soldiers, original['soldiers'])
                self.assertEqual(sum(state.officers[i].troops for i in outpost.roster.officer_ids), troops)

                before_restore = deepcopy(game.to_dict()['cities'])
                advance_month(game)
                outpost, rear = state.cities['nanyang'], state.cities['nanjun']
                self.assertEqual((state.year, state.month), (218, 1))
                self.assertEqual(outpost.gold, before_restore['nanyang']['gold'] + 35)
                self.assertEqual(outpost.grain, before_restore['nanyang']['grain'] + 90)
                self.assertEqual(rear.gold, before_restore['nanjun']['gold'] + 35)
                self.assertEqual(outpost.owner, 'wei')

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
        self.assertIn('尚缺7金', state.log[-1])
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
        zero = dict(gold=0, grain=0, reserves=0)
        setup = dict(monthly_maintenance=10, sponsor_city='nanjun')
        opening = session.preview_city(data['id'], 'nanyang')['city']
        self.assertEqual(opening['profile']['kind'], 'frontier_outpost')
        self.assertEqual(opening['income'], zero)
        self.assertEqual(opening['frontier_outpost'], setup)
        self.assertNotIn('kind', profile_at(data, 'nanyang', 217, 11))
        self.assertEqual(income_at(data, 'nanyang', 218, 1), data['city_income']['nanyang'])
        result = session.command('new', dict(faction='wei', seed=310), 0)['catalog']
        self.assertEqual(result['frontier_outposts']['nanyang'], setup)
        self.assertEqual(result['city_income']['nanyang'], zero)
        self.assertEqual(result['scenarios'][0]['city_profiles']['nanyang']['kind'], 'frontier_outpost')


if __name__ == '__main__':
    unittest.main()
