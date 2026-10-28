"""Fuxian–Jiangzhou offers independent land and river departures in both directions."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.march_core import using_backend
from remake.travel import TravelCampaign


def travel_for(data):
    travel = TravelCampaign()
    travel.catalog = SimpleNamespace(data=data,
        links={frozenset(pair) for pair in data['links']})
    return travel


def hostile_state(data, year=217, month=7):
    return SimpleNamespace(year=year, month=month, turn=0,
        cities={city['id']: SimpleNamespace(id=city['id'], owner='enemy')
                for city in data['cities']},
        extension={'travel': {'discovered': []}})


class FuLandCorridorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']

    def test_direct_land_departure_does_not_require_the_hostile_northern_detour(self):
        travel = travel_for(self.data)
        before = deepcopy(self.data)
        for year, month in ((184, 2), (207, 7), (225, 7), (263, 5)):
            state = hostile_state(self.data, year, month)
            for source, target in (('fuxian', 'bajun'), ('bajun', 'fuxian')):
                with self.subTest(date=(year, month), source=source), using_backend('python'):
                    quote = travel._travel_path(state, source, target, 'friendly',
                                                'land', adjacent=True)
                    self.assertEqual(quote['path'], [source, target])
                    self.assertEqual(len(quote['routes']), 1)
                    self.assertEqual(quote['routes'][0]['terrain'], 'mountain')
                    self.assertIsNone(quote['routes'][0]['hazard'])
        self.assertEqual(self.data, before, 'Route previews are read-only and draw no new risk')

    def test_regional_road_joins_city_centers_and_does_not_claim_an_exact_han_highway(self):
        pair = {'fuxian', 'bajun'}
        roads = [road for road in self.data['regional_roads']
                 if {road['from'], road['to']} == pair]
        routes = [route for route in self.data['travel_routes']
                  if {route['from'], route['to']} == pair and route['mode'] == 'land']
        self.assertEqual((len(roads), len(routes)), (1, 1))
        self.assertEqual(sum(set(edge) == pair for edge in self.data['links']), 1)
        road, route = roads[0], routes[0]
        self.assertEqual(road['draw'], route['draw'])
        self.assertEqual(road['history'], route['history'])
        self.assertIs(route['history']['is_proven_exact_Han_alignment'], False)
        self.assertIn('後漢書/卷18', route['history']['source'])
        self.assertIn('三國志/卷44', route['history']['additional_source'])
        self.assertNotIn('availability', route)
        self.assertNotIn('closures', route)
        positions = {city['id']: city['position'] for city in self.data['cities']}
        self.assertEqual(road['draw'][0]['points'][0], positions['fuxian'])
        self.assertEqual(road['draw'][-1]['points'][-1], positions['bajun'])
        for point in road['draw'][0]['points'][1:-1]:
            self.assertFalse(any((point[0]-center[0])**2+(point[1]-center[1])**2 <= 9
                                 for city, center in positions.items() if city not in pair))


class FuCompiledCorridorContractTests(unittest.TestCase):
    def test_compiled_modes_are_direct_independent_and_keep_river_direction(self):
        data = json.loads((ROOT / 'game/data/campaigns/217-07.json').read_text())
        travel, state = travel_for(data), hostile_state(data)
        quotes = {}
        for source, target in (('fuxian', 'bajun'), ('bajun', 'fuxian')):
            for mode in ('land', 'river'):
                with self.subTest(source=source, mode=mode), using_backend('python'):
                    quote = travel._travel_path(state, source, target, 'friendly', mode, adjacent=True)
                    self.assertIsNotNone(quote)
                    self.assertEqual(quote['path'], [source, target])
                    self.assertEqual(len(quote['routes']), 1)
                    self.assertEqual(quote['modes'], [mode])
                    self.assertIsNone(quote['routes'][0]['hazard'])
                    quotes[source, mode] = quote
        self.assertEqual(quotes['fuxian', 'land']['days'], quotes['bajun', 'land']['days'])
        self.assertLess(quotes['fuxian', 'river']['days'], quotes['bajun', 'river']['days'])
        self.assertTrue(all(segment['flow'] == 'downstream'
                            for segment in quotes['fuxian', 'river']['routes'][0]['river_segments']))
        self.assertTrue(all(segment['flow'] == 'upstream'
                            for segment in quotes['bajun', 'river']['routes'][0]['river_segments']))
        self.assertTrue(any('涪' in segment['name_tc']
                            for segment in quotes['fuxian', 'river']['routes'][0]['river_segments']))


if __name__ == '__main__':
    unittest.main()
