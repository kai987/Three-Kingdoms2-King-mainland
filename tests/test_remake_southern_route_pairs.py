"""The Xinggu–Jiaozhi mountain corridor is playable and retains its evidence limits."""
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


class SouthernRoutePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']

    def test_direct_march_works_both_ways_before_and_after_the_commandery_is_named(self):
        travel = TravelCampaign()
        travel.catalog = SimpleNamespace(data=self.data,
            links={frozenset(pair) for pair in self.data['links']})
        before = deepcopy(self.data['travel_hazards'])
        for year, month in ((184, 2), (224, 12), (225, 1), (263, 5), (280, 7)):
            state = SimpleNamespace(year=year, month=month, turn=0,
                cities={city['id']: SimpleNamespace(id=city['id'], owner='enemy')
                        for city in self.data['cities']},
                extension={'travel': {'discovered': []}})
            for source, target in (('xinggu', 'jiaozhi'), ('jiaozhi', 'xinggu')):
                with self.subTest(date=(year, month), source=source), using_backend('python'):
                    quote = travel._travel_path(state, source, target, 'friendly',
                                                'land', adjacent=True)
                    self.assertEqual(quote['path'], [source, target])
                    self.assertEqual(len(quote['routes']), 1)
                    leg = quote['routes'][0]
                    self.assertEqual(leg['mode'], 'land')
                    self.assertEqual(leg['terrain'], 'mountain')
                    self.assertEqual(leg['sea_km'], 0)
                    self.assertIsNone(leg['hazard'])
        self.assertEqual(self.data['travel_hazards'], before)

    def test_late_mixed_transport_evidence_does_not_claim_an_exact_han_highway(self):
        pair = {'xinggu', 'jiaozhi'}
        roads = [road for road in self.data['regional_roads']
                 if {road['from'], road['to']} == pair]
        routes = [route for route in self.data['travel_routes']
                  if {route['from'], route['to']} == pair]
        self.assertEqual((len(roads), len(routes)), (1, 1))
        road, route = roads[0], routes[0]
        self.assertEqual(road['draw'], route['draw'])
        self.assertEqual(route['history'], road['history'])
        history = road['history']
        self.assertIs(history['is_proven_exact_Han_alignment'], False)
        self.assertIs(history['is_proven_all_land_Han_highway'], False)
        self.assertTrue(history['regional_proxy_before_225'])
        self.assertIn('晉書/卷057', history['source'])
        self.assertIn('華陽國志/卷四', history['additional_source'])
        self.assertIn('280', history['basis'])
        self.assertIn('水陸並通', history['basis'])
        self.assertNotIn('availability', route)
        self.assertNotIn('closures', route)
        positions = {city['id']: city['position'] for city in self.data['cities']}
        self.assertEqual(road['draw'][0]['points'][0], positions['xinggu'])
        self.assertEqual(road['draw'][-1]['points'][-1], positions['jiaozhi'])
        self.assertFalse(any({row['from'], row['to']} == pair and row['mode'] == 'river'
                             for row in self.data['travel_routes']))


if __name__ == '__main__':
    unittest.main()
