"""Shared harbour approaches, mountain links and actual travel transactions."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake.march_core import using_backend


def read(name):
    return json.loads((ROOT / name).read_text())


class RouteCorridorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = read('game/config/route-corridors.json')
        cls.navigation = read('game/config/navigation-geometry.json')
        cls.shared = read('game/config/campaigns/shared.json')['catalog']
        cls.catalogs = [Catalog(ROOT / 'game/data' / name)
                       for name in read('game/data/campaigns/index.json')['catalogs']]

    def test_three_harbour_approaches_reuse_the_painted_corridor_in_both_directions(self):
        self.assertEqual(set(self.spec['access_overrides']), {'liaodong', 'lelang', 'kuaiji'})
        for city, points in self.spec['access_overrides'].items():
            self.assertEqual(points[0], self.catalogs[0].map_cities[city]['position'])
            expected = points + [self.navigation['ports'][city]]
            count = 0
            for row in self.navigation['routes']:
                if city not in (row['from'], row['to']):
                    continue
                actual = row['draw'][0]['points'] if row['from'] == city else list(reversed(row['draw'][-1]['points']))
                self.assertEqual(actual, expected, (city, row['from'], row['to']))
                count += 1
            self.assertEqual(count, len(self.navigation['coastal_cities']) - 1)

    def test_ship_geometry_is_continuous_city_to_port_to_city_for_every_current_route(self):
        positions = {c['id']: c['position'] for c in self.shared['cities']}
        for catalog in self.catalogs:
            for field in ('travel_routes', 'sea_routes', 'exploration_routes'):
                for row in catalog.data[field]:
                    if row['mode'] != 'sea':
                        continue
                    draw = row['draw']
                    with self.subTest(campaign=catalog.data['id'], route=row['id'], field=field):
                        self.assertEqual(draw[0]['points'][0], positions[row['from']])
                        self.assertEqual(draw[-1]['points'][-1], positions[row['to']])
                        for a, b in zip(draw, draw[1:]):
                            self.assertEqual(a['points'][-1], b['points'][0])

    def test_existing_route_physics_and_all_city_positions_are_unchanged(self):
        original = {r['id']: r for r in self.shared['travel_routes']}
        physical_fields = ('from', 'to', 'mode', 'terrain', 'distance_km', 'land_km', 'sea_km', 'days')
        for catalog in self.catalogs:
            self.assertEqual(catalog.data['cities'], self.shared['cities'])
            self.assertEqual(catalog.data['city_coordinates'], self.shared['city_coordinates'])
            compiled = {r['id']: r for r in catalog.data['travel_routes']}
            for key, row in original.items():
                self.assertEqual({k: compiled[key][k] for k in physical_fields},
                                 {k: row[k] for k in physical_fields}, (catalog.data['id'], key))
            self.assertEqual(len(compiled), len(original) + 2)

    def test_new_roads_share_one_northern_approach_and_are_explicit_mountain_game_corridors(self):
        expected = {'bajun': (467.7, 32), 'fuling': (446.1, 30)}
        for catalog in self.catalogs:
            roads = [r for r in catalog.data['regional_roads'] if r['from'] == 'zangke' and r['to'] in expected]
            self.assertEqual(len(roads), 2)
            self.assertEqual(roads[0]['draw'][0], roads[1]['draw'][0])
            for road in roads:
                self.assertEqual(road['draw'][0]['points'][0], catalog.map_cities['zangke']['position'])
                self.assertEqual(road['draw'][-1]['points'][-1], catalog.map_cities[road['to']]['position'])
                self.assertIs(road['history']['is_proven_direct_Han_road'], False)
                self.assertIn('華陽國志', road['history']['source'])
                route = next(r for r in catalog.data['travel_routes']
                             if r['from'] == 'zangke' and r['to'] == road['to'])
                self.assertEqual((route['distance_km'], route['days']), expected[road['to']])
                self.assertEqual(route['terrain'], 'mountain')
                self.assertEqual(sum(set(edge) == {'zangke', road['to']} for edge in catalog.data['links']), 1)

    def test_actual_transfers_use_new_roads_both_directions_and_arrive_at_the_correct_ten_day_boundary(self):
        catalog = next(c for c in self.catalogs if c.data['id'] == 'mainland217-07')
        for target, turns in (('bajun', 4), ('fuling', 3)):
            for backend in ('python', 'rust'):
                with self.subTest(target=target, backend=backend), using_backend(backend):
                    game = Campaign(catalog)
                    game.command('new', dict(faction='shu', seed=2026), 0)
                    for a, b in (('zangke', target), (target, 'zangke')):
                        quote = game._travel_path(game.state, a, b, 'shu', 'land', adjacent=True)
                        self.assertEqual(quote['path'], [a, b])
                        self.assertEqual(quote['turns'], turns)
                    source = game.state.cities['zangke']
                    # Controlled placement isolates movement; this does not
                    # claim the empty opening city had a historical garrison.
                    origin = next(c for c in game.state.cities.values() if c.owner == 'shu'
                                  and any(i != game.state.extension['leaders']['shu'] for i in c.roster.officer_ids))
                    ident = next(i for i in origin.roster.officer_ids if i != game.state.extension['leaders']['shu'])
                    origin.roster.officer_ids.remove(ident)
                    source.roster.officer_ids.append(ident)
                    game.validate(game.state)
                    initial_grain = source.grain
                    rng = deepcopy(game.state.rng)
                    game.command('transfer', dict(source='zangke', target=target,
                                 officers=[ident], route_mode='land'), game.revision)
                    self.assertEqual(game.state.cities['zangke'].grain, initial_grain - 5)
                    march = game.state.extension['travel']['marches'][0]
                    self.assertEqual(march['arrival_turn'], game.state.turn + turns)
                    for _ in range(turns - 1):
                        game._complete_turn(game.state)
                        self.assertEqual(game.state.phase, 'city')
                    game._complete_turn(game.state)
                    self.assertEqual(game.state.phase, 'arrivals')
                    game.command('arrivals', {}, game.revision)
                    self.assertIn(ident, game.state.cities[target].roster.officer_ids)
                    self.assertNotIn(ident, game.state.cities['zangke'].roster.officer_ids)
                    self.assertFalse(game.state.extension['travel']['marches'])
                    self.assertEqual(game.state.rng, rng)
                    restored = Campaign(catalog)
                    restored.load_save(game.export_save(), 0)
                    self.assertEqual(restored.export_save(), game.export_save())


if __name__ == '__main__':
    unittest.main()
