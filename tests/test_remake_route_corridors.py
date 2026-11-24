"""Shared harbour approaches, mountain links and actual travel transactions."""
from copy import deepcopy
from hashlib import sha256
from itertools import pairwise
from math import atan2, ceil, cos, radians, sin, sqrt
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake.march_core import using_backend
from remake.march_supply import estimate
from remake import treasures
from game.build_portrait_manifest import png_pixels


def read(name):
    return json.loads((ROOT / name).read_text())


def geographic_distance(first, second):
    """Independent atan2 great-circle reference for route calibration."""
    lon1, lat1 = map(radians, first)
    lon2, lat2 = map(radians, second)
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.009 * 2 * atan2(sqrt(h), sqrt(1-h))


class RouteCorridorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = read('game/config/route-corridors.json')
        cls.navigation = read('game/config/navigation-geometry.json')
        cls.shared = read('game/config/campaigns/shared.json')['catalog']
        cls.geometry = read('game/config/route-geometry.json')
        cls.catalogs = [Catalog(ROOT / 'game/data' / name)
                       for name in read('game/data/campaigns/index.json')['catalogs']]

    def expected_regular_port_connections(self, city):
        limited_ports = self.spec.get('limited_port_connections', {})
        regular_pairs = len(self.navigation['coastal_cities']) - len(limited_ports) - 1
        return regular_pairs + sum(city in origins for origins in limited_ports.values())

    def test_harbour_approaches_reuse_the_painted_corridor_in_both_directions(self):
        self.assertEqual(set(self.spec['access_overrides']), {'liaodong', 'kuaiji', 'jiaozhi'})
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
            self.assertEqual(count, self.expected_regular_port_connections(city))

    def test_revised_northeast_ports_use_the_current_ocean(self):
        revision = self.navigation['coastal_revision']
        raw = (ROOT / revision['source']).read_bytes()
        self.assertEqual(revision['source_sha256'], sha256(raw).hexdigest())
        self.assertEqual(revision['region'], self.spec['coastal_revision']['region'])
        (width, _), rgba = png_pixels(raw, (1352, 1024))
        for city, hint in self.spec['coastal_revision']['ports'].items():
            with self.subTest(city=city):
                x, y = self.navigation['ports'][city]
                self.assertLessEqual((x-hint[0])**2 + (y-hint[1])**2, 12**2)
                offset = (y*width + x)*4
                red, green, blue = rgba[offset:offset+3]
                self.assertTrue(blue > 140 and blue > red*1.4 and blue > green*1.3)

    def test_beihai_solid_road_ends_on_dry_ground_at_its_sea_lane(self):
        approach = self.spec['shore_access_overrides']['beihai']
        city, shore = approach
        port = self.navigation['ports']['beihai']
        revision = self.navigation['coastal_revision']
        (width, _), rgba = png_pixels((ROOT / revision['source']).read_bytes(), (1352, 1024))
        # The road's 4.1 px outer stroke has a round cap. Check the ground
        # under the stroke ends on the land side of the shoreline.
        for y in range(shore[1] - 2, city[1] + 1):
            for x in range(min(city[0], shore[0]) - 2, max(city[0], shore[0]) + 3):
                offset = (y*width + x)*4
                red, green, blue = rgba[offset:offset+3]
                self.assertFalse(blue > 60 and blue > red*1.4 and blue > green*1.3, (x, y))
        checked = 0
        for row in self.navigation['routes']:
            if row['from'] == 'beihai':
                land, sea = (leg['points'] for leg in row['draw'][:2])
            elif row['to'] == 'beihai':
                land, sea = (leg['points'][::-1] for leg in reversed(row['draw'][1:]))
            else:
                continue
            self.assertEqual(land, approach)
            self.assertEqual(sea[:2], [shore, port])
            checked += 1
        self.assertEqual(checked, self.expected_regular_port_connections('beihai'))

    def test_daifang_shore_approach_ends_before_open_water(self):
        approach = self.spec['shore_access_overrides']['daifang']
        self.assertEqual(approach[0], [1296, 190])
        self.assertEqual(approach[-1], [1283, 201])
        source = read('game/config/terrain-art.json')['world_surface']
        crop = source['crop']
        size, mask = png_pixels((ROOT / source['path']).read_bytes(), (crop['width'], crop['height']))
        pixel = lambda x, y: mask[((y-crop['y'])*size[0] + x-crop['x'])*4 + 1]
        for a, b in pairwise(approach):
            steps = 2*max(abs(a[0]-b[0]), abs(a[1]-b[1]))
            self.assertTrue(all(pixel(*(round(u+(v-u)*i/steps) for u, v in zip(a, b)))
                                for i in range(steps+1)))
        self.assertEqual(pixel(1283, 202), 0)
        row = next(r for r in self.navigation['routes']
                   if (r['from'], r['to']) == ('beihai', 'daifang'))
        self.assertEqual(row['draw'][-1]['points'], approach[::-1])
        self.assertEqual(row['draw'][1]['points'][-1], approach[-1])

    def test_luzon_navigation_uses_its_drawn_footprint_and_taiwan_only(self):
        config = self.navigation['island_coastline']
        outline = read(config['source'])['luzon']['outline']
        self.assertEqual(config['outline_sha256'],
                         sha256(json.dumps(outline, separators=(',', ':')).encode()).hexdigest())
        route, = [row for row in self.navigation['routes'] if 'luzon' in (row['from'], row['to'])]
        self.assertEqual((route['from'], route['to']), ('yizhou', 'luzon'))
        self.assertEqual(route['draw'][-1]['points'], self.spec['shore_access_overrides']['luzon'][::-1])
        sea = route['draw'][1]['points']
        self.assertEqual(sea[-1], [1134, 925])
        self.assertEqual(sea[-2], self.navigation['ports']['luzon'])

    def test_donglai_crossing_is_a_known_sea_route_in_every_opening(self):
        city = 'donglai'
        route_id = 'liaodong:donglai:sea'
        self.assertIn(city, self.shared['travel_hazards']['coastal_cities'])
        for catalog in self.catalogs:
            data = catalog.data
            with self.subTest(campaign=data['id']):
                self.assertIn(city, data['active_cities'])
                self.assertIn(['liaodong', city], data['links'])
                routes = {}
                for field in ('travel_routes', 'sea_routes'):
                    routes[field] = [r for r in data[field]
                                     if r['mode'] == 'sea' and city in (r['from'], r['to'])]
                    self.assertEqual([r['id'] for r in routes[field]], [route_id])
                self.assertEqual(routes['travel_routes'], routes['sea_routes'])
                self.assertFalse(any(city in (r['from'], r['to']) for r in data['exploration_routes']))
                route, = routes['sea_routes']
                self.assertFalse(route['discovery_candidate'])
                self.assertIn('《三國志・公孫度傳》', route['history']['basis'])
        approaches = self.spec['shore_access_overrides'][city]
        lanes = [row for row in self.navigation['routes'] if city in (row['from'], row['to'])]
        self.assertEqual([(row['from'], row['to']) for row in lanes], [('liaodong', city)])
        approach = lanes[0]['draw']
        self.assertEqual(approach[-1]['points'], approaches[::-1])
        self.assertEqual(approach[1]['points'][-2:], [self.navigation['ports'][city], approaches[-1]])

    def test_donglai_crossing_quotes_both_directions_and_survives_save(self):
        catalog = next(c for c in self.catalogs if c.data['id'] == 'mainland263-05')
        route = next(row for row in catalog.data['sea_routes'] if row['id'] == 'liaodong:donglai:sea')
        for backend in ('python', 'rust'):
            with self.subTest(backend=backend), using_backend(backend):
                game = Campaign(catalog)
                game.command('new', dict(faction='wei', seed=2026), 0)
                state = game.state
                self.assertEqual(state.extension['travel']['discovered'], [])
                for source, target in (('liaodong', 'donglai'), ('donglai', 'liaodong')):
                    quote = game._travel_path(state, source, target, 'wei', 'sea')
                    self.assertEqual(quote['path'], [source, target])
                    leg, = quote['routes']
                    self.assertEqual(leg['id'], route['id'])
                    self.assertIsNone(game._travel_path(state, source, target, 'wei', 'explore'))
                officer = next(i for i in state.cities['liaodong'].roster.officer_ids
                               if state.officers[i].troops > 0)
                game.command('transfer', dict(source='liaodong', target='donglai',
                                              officers=[officer], route_mode='sea'), game.revision)
                self.assertEqual(game.state.extension['travel']['marches'][0]['quote']['routes'][0]['id'],
                                 route['id'])
                saved = game.export_save()
                restored = Campaign(catalog)
                restored.load_save(saved, 0)
                self.assertEqual(restored.export_save(), saved)

    def test_jiaozhi_port_access_shares_the_exact_existing_eastern_trunk(self):
        points = self.spec['access_overrides']['jiaozhi']
        roads = read('game/config/road-centers.json')
        # The native road's first straight ends at the entry to its rounded
        # corner. Share that straight exactly, then split toward the harbour.
        origin = [386, 854]
        corner_entry = [435.2512601228404, 842.111764797935]
        self.assertIn('L' + ' '.join(map(str, corner_entry)), roads['original_paths'][52])
        self.assertEqual(points[0], [387, 853])
        self.assertEqual(points[2], corner_entry)
        a = points[1]
        cross = ((a[0]-origin[0])*(corner_entry[1]-origin[1])
                 -(a[1]-origin[1])*(corner_entry[0]-origin[0]))
        self.assertAlmostEqual(cross, 0, places=8)
        self.assertEqual(points[-1], [452, 864])
        self.assertEqual(self.navigation['ports']['jiaozhi'], [452, 876])
        self.assertNotIn([416, 860], points, 'The old parallel southern approach is removed')

    def test_ship_geometry_is_continuous_city_to_port_to_city_for_every_current_route(self):
        for catalog in self.catalogs:
            positions = {key: city['position'] for key, city in catalog.map_cities.items()}
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

    def test_existing_logical_routes_and_all_city_positions_are_preserved(self):
        original = {r['id']: r for r in self.shared['travel_routes']}
        identity_fields = ('from', 'to', 'mode', 'terrain')
        positions = [(city['id'], city['position']) for city in self.shared['cities']]
        coordinates = self.shared['city_coordinates']
        for catalog in self.catalogs:
            self.assertEqual([(c['id'], c['position']) for c in catalog.data['cities'][:len(positions)]],
                             positions)
            self.assertEqual({city: catalog.data['city_coordinates'][city] for city in coordinates},
                             coordinates)
            compiled = {r['id']: r for r in catalog.data['travel_routes']}
            for key, row in original.items():
                self.assertEqual({k: compiled[key][k] for k in identity_fields},
                                 {k: row[k] for k in identity_fields}, (catalog.data['id'], key))
                self.assertEqual(compiled[key]['timing_geometry']['schema'], 'tk2-route-timing-v1')
            self.assertEqual(len(compiled), len(original) + len(self.navigation['land_roads'])
                             + len(self.navigation.get('river_routes', [])) + 1)
            self.assertEqual(compiled['yizhou:luzon:sea']['mode'], 'sea')

    def test_northwest_city_positions_follow_the_yellow_and_wei_banks(self):
        catalog = self.catalogs[0]
        positions = {city: row['position'] for city, row in catalog.map_cities.items()}
        ground = ROOT / 'game/map-source/hydrology-ground.png'
        (width, _), rgba = png_pixels(ground.read_bytes(), (1352, 1024))
        for city in ('jincheng', 'longxi', 'nanan', 'tianshui'):
            with self.subTest(city=city):
                x, y = positions[city]
                water = []
                for row in range(y - 25, y + 16):
                    i = (row * width + x) * 4
                    red, green, blue = rgba[i:i+3]
                    if blue >= 120 and blue > max(red, green) + 40:
                        water.append(row)
                self.assertTrue(water)
                self.assertLess(max(water), y - 8)

        hanyang_x, hanyang_y = positions['tianshui']
        wudu_x, wudu_y = positions['wudu']
        self.assertGreater(wudu_y, hanyang_y + 30)
        self.assertLess(abs(wudu_x - hanyang_x), 16)

    def test_northwest_route_geometry_reuses_junctions_and_reaches_the_new_sites(self):
        catalog = self.catalogs[-1]
        positions = {city: row['position'] for city, row in catalog.map_cities.items()}
        geometry = self.geometry['routes']
        timed_routes = {route['id']: route for route in catalog.data['travel_routes']}
        for identity in ('jincheng:longxi:land', 'hanzhong:wudu:land', 'longxi:tianshui:land',
                         'fufeng:tianshui:land', 'jincheng:wuwei:land', 'wuwei:zhangye:land',
                         'zhangye:xihai:land', 'jincheng:shuofang:river'):
            with self.subTest(route=identity):
                route = geometry[identity]
                first, last = route['parts'][0], route['parts'][-1]
                self.assertEqual(first['start'], positions[route['from']])
                self.assertEqual(last['end'], positions[route['to']])
                self.assertTrue(all(a['end'] == b['start'] for a, b in pairwise(route['parts'])))
                measured = timed_routes[identity]['timing_geometry']['parts']
                self.assertEqual([part['length_px'] for part in measured],
                                 [part['length_px'] for part in route['parts']])

        sections = geometry['longxi:tianshui:land']['city_sections']
        self.assertEqual([(row['from'], row['to']) for row in sections],
                         [('longxi', 'nanan'), ('nanan', 'tianshui')])

        for west, east in (('tianshui:guangwei:land', 'fufeng:guangwei:land'),
                           ('wuwei:xijun:land', 'zhangye:xijun:land')):
            self.assertEqual(geometry[west]['parts'][0]['pieces'][-1],
                             geometry[east]['parts'][0]['pieces'][-1])

        routes = read('game/config/map-source.json')['presentation']['expansion_connections']
        shared_roads = {(route['from'], route['to']): [part['points'] for part in route['draw']]
                   for route in routes if (route['from'], route['to']) in
                   {('xiping', 'wuwei'), ('xiping', 'jincheng'), ('wuwei', 'jincheng')}}
        west, north = shared_roads['xiping', 'wuwei']
        self.assertEqual(shared_roads['xiping', 'jincheng'], [west, shared_roads['wuwei', 'jincheng'][1]])
        self.assertEqual(shared_roads['wuwei', 'jincheng'][0], north[::-1])

    def test_new_roads_share_one_northern_approach_and_are_explicit_mountain_game_corridors(self):
        expected = {'bajun', 'fuling'}
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
                curve = self.geometry['routes'][route['id']]['parts'][0]
                coordinates = catalog.data['city_coordinates']
                rules = catalog.data['travel_rules']
                distance = round(geographic_distance(coordinates['zangke'], coordinates[road['to']])
                                 * curve['length_px']/curve['chord_px'] * rules['detours']['mountain'], 1)
                self.assertEqual(route['distance_km'], distance)
                self.assertEqual(route['days'], ceil(distance/rules['speeds']['mountain']))
                self.assertEqual(route['terrain'], 'mountain')
                self.assertEqual(sum(set(edge) == {'zangke', road['to']} for edge in catalog.data['links']), 1)

    def test_actual_transfers_use_new_roads_both_directions_and_arrive_at_the_correct_ten_day_boundary(self):
        data = deepcopy(next(c for c in self.catalogs if c.data['id'] == 'mainland217-07').data)
        # This fixture isolates route timing and its RNG-free land movement;
        # unrelated monthly city disasters are tested by the facility suite.
        data.setdefault('facility_rules', {})['disasters_enabled'] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'route-movement.json'
            path.write_text(json.dumps(data, ensure_ascii=False))
            catalog = Catalog(path)
        for target in ('bajun', 'fuling'):
            route = next(r for r in catalog.data['travel_routes']
                         if {r['from'], r['to']} == {'zangke', target} and r['mode'] == 'land')
            turns = ceil(route['days']/10)
            for backend in ('python', 'rust'):
                with self.subTest(target=target, backend=backend), using_backend(backend):
                    game = Campaign(catalog)
                    game.command('new', dict(faction='shu', seed=2026), 0)
                    for a, b in (('zangke', target), (target, 'zangke')):
                        quote = game._travel_path(game.state, a, b, 'shu', 'land', adjacent=True)
                        self.assertEqual(quote['path'], [a, b])
                        self.assertEqual(quote['days'], route['days'])
                        self.assertEqual(quote['turns'], turns)
                    source = game.state.cities['zangke']
                    # Controlled placement isolates movement; this does not
                    # claim the empty opening city had a historical garrison.
                    origin = next(c for c in game.state.cities.values() if c.owner == 'shu'
                                  and any(i != game.state.extension['leaders']['shu'] for i in c.roster.officer_ids))
                    ident = next(i for i in origin.roster.officer_ids if i != game.state.extension['leaders']['shu'])
                    origin.roster.officer_ids.remove(ident)
                    source.roster.officer_ids.append(ident)
                    treasures.synchronize(game,game.state)
                    game.validate(game.state)
                    initial_grain = source.grain
                    rng = deepcopy(game.state.rng)
                    game.command('transfer', dict(source='zangke', target=target,
                                 officers=[ident], route_mode='land'), game.revision)
                    march = game.state.extension['travel']['marches'][0]
                    self.assertEqual(game.state.cities['zangke'].grain,
                                     initial_grain-estimate(game.state,[ident],march['quote']))
                    self.assertEqual(march['supply']['consumed'],0)
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
