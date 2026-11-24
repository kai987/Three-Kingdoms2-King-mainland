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
from remake.city_economy import frontier_maintenance, frontier_outposts_view, garrison_grain_cost, income_at, profile_at, civilian_grain, town_level, settle_turn_grain
from remake.session import CampaignSession
from test_remake_economy_v2 import reference_adjusted


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
                pop = original['extension']['city_development']['cities']
                # Both level-2 towns have 68,500 residents.
                grain_produced = 2_872
                civilian = civilian_grain(pop['nanyang']['population'], 2, state=game.state)
                ordinary = civilian + garrison_grain_cost(game.catalog.data, 'nanyang', 217, 11, troops, 0)
                frontier = civilian + ((troops + 17) * 3 + 9) // 10
                expected = ordinary * 2 // 3 + frontier - frontier * 2 // 3
                advance_month(game)
                state = game.state
                outpost, rear = state.cities['nanyang'], state.cities['nanjun']
                outpost_start, rear_start = (original['cities'][key] for key in ('nanyang', 'nanjun'))
                self.assertEqual((state.year, state.month), (217, 12))
                self.assertEqual(outpost.gold, outpost_start['gold'] + 35)
                self.assertEqual(outpost.grain, outpost_start['grain'] + grain_produced - expected)
                self.assertEqual(outpost.reserves, outpost_start['reserves'] + 17)
                self.assertEqual(rear.gold, rear_start['gold'] + 35 - 15)
                rear_civilian = civilian_grain(pop['nanjun']['population'], 2, state=state)
                rear_garrison = garrison_grain_cost(game.catalog.data, 'nanjun', 217, 12, 120, 1200)
                self.assertEqual(rear.grain, rear_start['grain'] + grain_produced - rear_civilian - rear_garrison)
                self.assertEqual(state.soldiers, dict(original['soldiers'], recruited=17))
                self.assertEqual(sum(state.officers[i].troops for i in outpost.roster.officer_ids), troops)

                before_restore = deepcopy(game.to_dict()['cities'])
                advance_month(game)
                outpost, rear = state.cities['nanyang'], state.cities['nanjun']
                self.assertEqual((state.year, state.month), (218, 1))
                self.assertEqual(outpost.gold, before_restore['nanyang']['gold'] + 35)
                ordinary = civilian + garrison_grain_cost(game.catalog.data, 'nanyang', 218, 1, troops, 34)
                expected = frontier * 2 // 3 + ordinary - ordinary * 2 // 3
                self.assertEqual(outpost.grain, before_restore['nanyang']['grain'] + grain_produced - expected)
                self.assertEqual(rear.gold, before_restore['nanjun']['gold'] + 35)
                self.assertEqual(outpost.owner, 'wei')

    def test_grain_caps_at_town_limit_while_other_production_and_upkeep_keep_scaling(self):
        game = Campaign(frontier_catalog(troops=0))
        game.command('new', dict(faction='wei', seed=310), 0)
        state = game.state
        outpost, rear = (state.cities[key] for key in ('nanyang', 'nanjun'))
        development = state.extension['city_development']['cities'][outpost.id]
        development['population'] *= 2
        start = outpost.gold, outpost.grain, outpost.reserves, rear.gold
        advance_month(game)
        people = civilian_grain(development['population'], 2, state=state)
        after = people + 11  # 34 reserves, each at 50% of the basic ration for 30 days
        need = people * 2 // 3 + after - after * 2 // 3
        production = 2 * reference_adjusted(900, 90_000, 2, development['land'],
                                           development['baseline']['land'], 60, 60)
        self.assertEqual((outpost.gold, outpost.grain, outpost.reserves, rear.gold),
                         (start[0] + 70, start[1] + production - need, start[2] + 34, start[3] + 35 - 30))
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
                # Keep the test at the assigned population through month-end.
                state.cities['nanyang'].grain += civilian_grain(population, 2, state=state)
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
        self.assertEqual((outpost.gold, outpost.grain), (outpost_gold, 1))
        self.assertIn('尚缺12金', state.log[-1])
        settle_turn_grain(game, state)
        self.assertEqual(outpost.grain, 0)

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
                    settle_turn_grain(game, state)
                population = state.extension['city_development']['cities'][outpost.id]['population']
                civil = civilian_grain(population, town_level(game, state, outpost.id), state=state)
                self.assertEqual(before - outpost.grain, civil - civil * 2 // 3)

    def test_opening_and_active_api_report_dated_economy(self):
        data = frontier_catalog().data
        data['start_month'] = 12
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'frontier.json'
            path.write_text(json.dumps(data, ensure_ascii=False))
            session = CampaignSession([path])
        setup = dict(monthly_maintenance=15, sponsor_city='nanjun')
        opening = session.preview_city(data['id'], 'nanyang')['city']
        income = dict(data['city_income']['nanyang'], grain=2_872)
        self.assertEqual(opening['profile']['kind'], 'frontier_outpost')
        self.assertEqual(opening['income'], income)
        self.assertEqual(opening['frontier_outpost'], setup)
        self.assertNotIn('kind', profile_at(data, 'nanyang', 217, 11))
        self.assertEqual(income_at(data, 'nanyang', 218, 1), dict(income, grain=900))
        result = session.command('new', dict(faction='wei', seed=310), 0)['catalog']
        self.assertEqual(result['frontier_outposts']['nanyang'], setup)
        self.assertEqual(result['city_income']['nanyang'], income)
        self.assertEqual(result['scenarios'][0]['city_profiles']['nanyang']['kind'], 'frontier_outpost')


if __name__ == '__main__':
    unittest.main()
