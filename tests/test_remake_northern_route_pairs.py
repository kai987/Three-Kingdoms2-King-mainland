"""Northern regional roads allow direct marches without invented opening dates."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.march_core import using_backend
from remake.travel import TravelCampaign

PAIRS = (('yan', 'bohai'), ('fanyang', 'hejian'), ('dongjun', 'chenliu'))


class NorthernRoutePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']

    def test_adjacent_marches_work_both_ways_despite_hostile_surrounding_cities(self):
        travel = TravelCampaign()
        travel.catalog = SimpleNamespace(data=self.data,
            links={frozenset(pair) for pair in self.data['links']})
        for year, month in ((184, 1), (207, 7), (225, 1), (263, 5)):
            for a, b in PAIRS:
                state = SimpleNamespace(year=year, month=month, turn=0,
                    cities={city['id']: SimpleNamespace(id=city['id'], owner='enemy')
                            for city in self.data['cities']},
                    extension={'travel': {'discovered': []}})
                for source, target in ((a, b), (b, a)):
                    with self.subTest(date=(year, month), source=source, target=target), using_backend('python'):
                        quote = travel._travel_path(state, source, target, 'friendly',
                                                    'land', adjacent=True)
                        self.assertEqual(quote['path'], [source, target])
                        self.assertEqual(len(quote['routes']), 1)
                        self.assertEqual(quote['routes'][0]['mode'], 'land')
                        self.assertEqual({quote['routes'][0]['from'], quote['routes'][0]['to']}, {a, b})

    def test_each_road_is_independent_and_labels_the_historical_evidence_limit(self):
        positions = {city['id']: city['position'] for city in self.data['cities']}
        for a, b in PAIRS:
            with self.subTest(pair=(a, b)):
                roads = [road for road in self.data['regional_roads']
                         if {road['from'], road['to']} == {a, b}]
                routes = [route for route in self.data['travel_routes']
                          if {route['from'], route['to']} == {a, b} and route['mode'] == 'land']
                self.assertEqual((len(roads), len(routes)), (1, 1))
                road, route = roads[0], routes[0]
                self.assertEqual(road['draw'], route['draw'])
                self.assertEqual(road['draw'][0]['points'][0], positions[a])
                self.assertEqual(road['draw'][-1]['points'][-1], positions[b])
                self.assertEqual(route['terrain'], 'plain')
                self.assertEqual(route['history'], road['history'])
                self.assertIs(route['history']['is_proven_exact_Han_alignment'], False)
                self.assertTrue(route['history']['source'].startswith('https://zh.wikisource.org/'))
                self.assertNotIn('availability', route)
                self.assertNotIn('closures', route)
                # The renderer recognizes explicit vertices near city centers;
                # these independent corridors do not create unrelated stops.
                for point in road['draw'][0]['points'][1:-1]:
                    self.assertFalse(any((point[0]-center[0])**2 + (point[1]-center[1])**2 <= 9
                                         for city, center in positions.items() if city not in (a, b)))

    def test_liaoxi_to_beihai_keeps_its_exploration_sea_status(self):
        pair = {'liaoxi', 'beihai'}
        self.assertFalse(any({row['from'], row['to']} == pair
                             for row in self.data['travel_routes']))
        self.assertFalse(any({row['from'], row['to']} == pair
                             for row in self.data['sea_routes']))
        unknown = [row for row in self.data['exploration_routes']
                   if {row['from'], row['to']} == pair]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0]['mode'], 'sea')
        self.assertTrue(unknown[0]['discovery_candidate'])


if __name__ == '__main__':
    unittest.main()
