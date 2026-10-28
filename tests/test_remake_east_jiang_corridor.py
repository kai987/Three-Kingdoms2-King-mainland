"""Eastern approaches retain real city control and separate river departures."""
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


def read(name):
    return json.loads((ROOT / name).read_text())


def travel_for(data):
    travel = TravelCampaign()
    travel.catalog = SimpleNamespace(data=data,
        links={frozenset(pair) for pair in data['links']})
    return travel


def state_for(data, friendly, year=217, month=7):
    return SimpleNamespace(year=year, month=month, turn=0,
        cities={city['id']: SimpleNamespace(id=city['id'],
                    owner='friendly' if city['id'] in friendly else 'enemy')
                for city in data['cities']},
        extension={'travel': {'discovered': []}})


class EastJiangSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read('game/config/campaigns/shared.json')['catalog']

    def test_only_one_city_edge_joins_the_existing_donghai_approach(self):
        pair = {'xiapi', 'danyang'}
        roads = [row for row in self.data['regional_roads']
                 if {row['from'], row['to']} == pair]
        routes = [row for row in self.data['travel_routes']
                  if {row['from'], row['to']} == pair and row['mode'] == 'land']
        self.assertEqual((len(roads), len(routes)), (1, 1))
        self.assertEqual(sum(set(edge) == pair for edge in self.data['links']), 1)
        road, route = roads[0], routes[0]
        self.assertEqual(route['draw'], road['draw'])
        self.assertEqual(route['history'], road['history'])
        self.assertIs(route['history']['is_proven_exact_Han_alignment'], False)
        self.assertIs(route['history']['is_proven_permanent_bridge'], False)
        self.assertIn('三國志/卷49', route['history']['source'])
        self.assertNotIn('availability', route)
        self.assertNotIn('closures', route)
        positions = {city['id']: city['position'] for city in self.data['cities']}
        self.assertEqual(road['draw'][0]['points'][0], positions['xiapi'])
        self.assertEqual(road['draw'][-1]['points'][-1], positions['danyang'])
        # A road may cross rivers, but cannot silently draw through an
        # unrelated castle while its logical edge omits that city's control.
        for part in road['draw']:
            for first, last in zip(part['points'], part['points'][1:]):
                dx, dy = last[0]-first[0], last[1]-first[1]
                for city, center in positions.items():
                    if city in pair:
                        continue
                    fraction = max(0, min(1, ((center[0]-first[0])*dx
                        + (center[1]-first[1])*dy)/(dx*dx+dy*dy)))
                    distance2 = (first[0]+fraction*dx-center[0])**2 \
                        + (first[1]+fraction*dy-center[1])**2
                    self.assertGreater(distance2, 24**2, city)
        for field in ('travel_routes', 'regional_roads'):
            self.assertFalse(any({row['from'], row['to']} == {'donghai', 'danyang'}
                                 for row in self.data[field]))

    def test_land_ferry_departures_do_not_invent_opening_dates_or_new_weather(self):
        travel, before = travel_for(self.data), deepcopy(self.data)
        for year, month in ((184, 2), (207, 7), (225, 1), (256, 8), (263, 5)):
            state = state_for(self.data, {'xiapi', 'danyang'}, year, month)
            for source, target in (('xiapi', 'danyang'), ('danyang', 'xiapi')):
                with self.subTest(date=(year, month), source=source), using_backend('python'):
                    quote = travel._travel_path(state, source, target, 'friendly',
                                                'land', adjacent=True)
                    self.assertEqual(quote['path'], [source, target])
                    self.assertEqual(len(quote['routes']), 1)
                    self.assertIsNone(quote['routes'][0]['hazard'])
                    self.assertIsNone(travel._travel_path(state, source, target,
                                        'friendly', 'river', adjacent=True))
        self.assertEqual(self.data, before)


class EastJiangCompiledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read('game/data/campaigns/217-07.json')

    def test_donghai_uses_xiapi_and_cannot_march_through_hostile_xiapi(self):
        travel = travel_for(self.data)
        for backend in ('python', 'rust'):
            for source, target in (('donghai', 'danyang'), ('danyang', 'donghai')):
                with self.subTest(backend=backend, source=source), using_backend(backend):
                    state = state_for(self.data, {'donghai', 'xiapi', 'danyang'})
                    quote = travel._travel_path(state, source, target, 'friendly', 'land')
                    self.assertIsNotNone(quote)
                    self.assertEqual(quote['path'], [source, 'xiapi', target])
                    self.assertEqual({row['id'] for row in quote['routes']},
                                     {'donghai:xiapi:land', 'xiapi:danyang:land'})
                    self.assertEqual(quote['days'], sum(row['days'] for row in quote['routes']))
                    self.assertIsNone(travel._travel_path(state, source, target,
                                        'friendly', 'land', adjacent=True))
                    state.cities['xiapi'].owner = 'enemy'
                    self.assertIsNone(travel._travel_path(state, source, target,
                                                         'friendly', 'land'))

    def test_compiled_eastern_corridor_has_only_its_two_city_endpoints(self):
        geometry = read('game/config/route-geometry.json')['routes']['xiapi:danyang:land']
        self.assertEqual([(row['from'], row['to']) for row in geometry['city_sections']],
                         [('xiapi', 'danyang')])
        positions = {city['id']: city['position'] for city in self.data['cities']}
        self.assertEqual(geometry['parts'][0]['start'], positions['xiapi'])
        self.assertEqual(geometry['parts'][-1]['end'], positions['danyang'])
        self.assertGreater(geometry['parts'][0]['length_px'], geometry['parts'][0]['chord_px'])

    def test_fu_to_jiangyang_changes_rivers_at_jiangzhou_without_a_direct_river_edge(self):
        travel = travel_for(self.data)
        pair = {'fuxian', 'jiangyang'}
        self.assertFalse(any({row['from'], row['to']} == pair
                             for row in self.data['travel_routes']))
        for backend in ('python', 'rust'):
            for source, target in (('fuxian', 'jiangyang'), ('jiangyang', 'fuxian')):
                with self.subTest(backend=backend, source=source), using_backend(backend):
                    state = state_for(self.data, {'fuxian', 'bajun', 'jiangyang'})
                    quote = travel._travel_path(state, source, target, 'friendly', 'fastest')
                    self.assertEqual(quote['path'], [source, 'bajun', target])
                    self.assertEqual(quote['modes'], ['river'])
                    self.assertEqual({row['id'] for row in quote['routes']},
                                     {'fuxian:bajun:river', 'jiangyang:bajun:river'})
                    # Explicit river selection remains one city departure;
                    # fastest can combine legs while retaining the port stop.
                    self.assertIsNone(travel._travel_path(state, source, target,
                                                         'friendly', 'river'))
                    river_names = [{part['name_tc'] for part in row['river_segments']}
                                   for row in quote['routes']]
                    self.assertIn({'涪水', '嘉陵水'}, river_names)
                    self.assertIn({'長江'}, river_names)
                    state.cities['bajun'].owner = 'enemy'
                    self.assertIsNone(travel._travel_path(state, source, target,
                                                         'friendly', 'fastest'))


if __name__ == '__main__':
    unittest.main()
