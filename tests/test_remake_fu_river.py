"""The attested Fu corridor shares lower Jialing water and keeps river risks."""
from collections import deque
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from math import ceil, dist
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'game'), str(ROOT / 'source')]
from river_network import build, compile_network
from remake.march_core import using_backend
from remake.route_hazards import evaluate_leg

NS = {'svg': 'http://www.w3.org/2000/svg'}
SPEC = importlib.util.spec_from_file_location('fu_river_png_reader',
                                             ROOT / 'game/build_portrait_manifest.py')
png_reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(png_reader)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def rect_pixels(group):
    result = set()
    for rect in group.findall('svg:rect', NS):
        x, y, width, height = (int(rect.get(key)) for key in ('x', 'y', 'width', 'height'))
        result.update((xx-136, yy) for xx in range(x, x+width) for yy in range(y, y+height))
    return result


class FuRiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = read('game/config/river-network.json')
        cls.water_config = read('game/config/water-corrections.json')
        cls.positions = {city['id']: city['position'] for city in
                         read('game/config/campaigns/shared.json')['catalog']['cities']}
        cls.svg = ET.parse(ROOT / 'game/map-source/historic-water.svg').getroot()
        cls.group = cls.svg.find('.//svg:g[@data-authorial-addition="fu-dianjiang"]', NS)
        cls.pixels = rect_pixels(cls.group)
        cls.compiled = build()
        cls.routes = {row['id']: row for row in cls.compiled['routes']}

    def test_fu_branch_uses_a_continuous_4px_stroke_and_only_joins_jialing_at_dianjiang(self):
        self.assertEqual((self.group.get('data-river'), self.group.get('data-basin')), ('fu', 'yangtze'))
        for rect in self.group.findall('svg:rect', NS):
            self.assertEqual((rect.get('width'), rect.get('height'), rect.get('fill')),
                             ('2', '2', '#002af8'))
            self.assertEqual((int(rect.get('x')) % 2, int(rect.get('y')) % 2), (0, 0))
        seen, queue = {next(iter(self.pixels))}, deque([next(iter(self.pixels))])
        while queue:
            x, y = queue.popleft()
            for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if point in self.pixels and point not in seen:
                    seen.add(point)
                    queue.append(point)
        self.assertEqual(seen, self.pixels)
        overlaps = {}
        for group in self.svg.findall('.//svg:g', NS):
            if group is self.group:
                continue
            identity = group.get('data-river') or group.get('data-lake')
            if identity:
                overlaps.setdefault(identity, set()).update(rect_pixels(group) & self.pixels)
        self.assertEqual({key for key, pixels in overlaps.items() if pixels}, {'jialing'})
        self.assertEqual(overlaps['jialing'], {(x, y) for x in range(368, 372) for y in range(534, 538)})
        for city, (cx, cy) in self.positions.items():
            self.assertFalse(any(cx-16 <= x < cx+16 and cy-16 <= y < cy+16
                                 for x, y in self.pixels), city)

    def test_ports_and_shared_lower_reach_do_not_require_a_stop_at_another_city(self):
        route = self.routes['fuxian:bajun:river']
        self.assertEqual((len(self.routes), self.compiled['reach_count']), (45, 49))
        self.assertEqual([part['reach_id'] for part in route['draw'][1:-1]],
                         ['fu:fuxian:dianjiang', 'jialing:dianjiang:bajun'])
        self.assertEqual(route['draw'][0]['points'], [[294, 462], [316, 462]])
        self.assertEqual(route['draw'][-1], self.routes['baxi:bajun:river']['draw'][-1])
        self.assertEqual(route['draw'][-2], self.routes['baxi:bajun:river']['draw'][-2])
        self.assertEqual(route['draw'][1]['points'][-1], route['draw'][2]['points'][0])
        self.assertEqual(route['draw'][1]['points'][-1], [370, 536])
        self.assertEqual(route['draw'][-1]['points'][-1], self.positions['bajun'])
        self.assertEqual(self.spec['nodes']['jialing:dianjiang']['geo'], [106.28, 29.97])
        self.assertEqual(self.spec['nodes']['fu:fuxian']['geo'], [104.77, 31.45])
        self.assertNotIn('via', route)
        self.assertTrue(all(segment['downstream_from'] == 'fuxian' for segment in route['river_segments']))
        before = deepcopy(self.spec)
        compile_network(self.spec, self.positions)
        self.assertEqual(self.spec, before)

    def test_fu_reach_samples_stay_on_the_new_branch(self):
        reach = next(row for row in self.spec['reaches'] if row['id'] == 'fu:fuxian:dianjiang')
        for a, b in zip(reach['points'], reach['points'][1:]):
            count = max(1, ceil(dist(a, b)))
            for i in range(count+1):
                point = (round(a[0]+(b[0]-a[0])*i/count), round(a[1]+(b[1]-a[1])*i/count))
                self.assertIn(point, self.pixels)
        config = self.water_config['fu_corridor']
        self.assertEqual(config['points'], reach['points'])
        self.assertEqual((config['pixel'], config['width']), (2, 4))
        self.assertEqual(self.water_config['sources']['game/map-source/historic-water.svg'],
                         sha256((ROOT / 'game/map-source/historic-water.svg').read_bytes()).hexdigest())

    def test_historical_record_does_not_become_an_invented_opening_date_or_new_speed(self):
        route = self.routes['fuxian:bajun:river']
        history = route['history']
        self.assertIn('https://zh.wikisource.org/wiki/三國志/卷31', history['sources'])
        self.assertIn('https://zh.wikisource.org/wiki/後漢書/卷18', history['sources'])
        self.assertIn('非首通年代', history['basis'])
        self.assertIn('全年雙向大艦', history['limits'])
        self.assertIn('今合川', history['limits'])
        self.assertNotIn('availability', route)
        self.assertNotIn('from', history)
        self.assertNotIn('to', history)
        self.assertEqual(self.spec['rivers']['fu']['speed_key'], 'yangtze')
        self.assertEqual({segment['speed_key'] for segment in route['river_segments']}, {'yangtze'})

    def test_rendered_fu_pixels_are_blue_and_the_new_branch_covers_no_mountain_pixels(self):
        size = (1352, 1024)
        _, original = png_reader.png_pixels((ROOT / 'game/map-source/road-ground.png').read_bytes(), size)
        _, rendered = png_reader.png_pixels((ROOT / 'game/map-source/hydrology-ground.png').read_bytes(), size)
        for x, y in self.pixels:
            offset = (y*size[0]+x)*4
            self.assertEqual(rendered[offset:offset+4], bytes((0, 42, 248, 255)), (x, y))
            red, green, blue = original[offset:offset+3]
            self.assertTrue(green >= 120 or blue > 140 and blue > red*1.4 and blue > green*1.3,
                            'The branch stays on green valley ground or the existing confluence')
        for y in range(450, 542):
            for x in range(310, 378):
                if (x, y) not in self.pixels:
                    offset = (y*size[0]+x)*4
                    self.assertEqual(rendered[offset:offset+4], original[offset:offset+4], (x, y))

    def test_generated_fu_quotes_keep_existing_flow_speeds_without_ocean_season_or_losses(self):
        catalog = read('game/data/campaigns/249-01.json')
        route = next(row for row in catalog['river_routes'] if row['id'] == 'fuxian:bajun:river')
        original = deepcopy(route)
        quotes = {}
        for source, target, flow, speed in (('fuxian', 'bajun', 'downstream', 50),
                                            ('bajun', 'fuxian', 'upstream', 20)):
            previous = None
            for backend in ('python', 'rust'):
                for month in (1, 7):
                    with using_backend(backend):
                        quote = evaluate_leg(catalog, route, source, target, month)
                    self.assertIsNone(quote['hazard'])
                    self.assertEqual((quote['flow'], quote['speed_km_per_day']), (flow, speed))
                    self.assertTrue(all(segment['flow'] == flow for segment in quote['river_segments']))
                    self.assertEqual(quote['sea_km'], 0)
                    if previous is not None:
                        self.assertEqual(quote, previous)
                    previous = quote
            quotes[flow] = previous
        self.assertGreater(quotes['upstream']['days'], quotes['downstream']['days'])
        self.assertEqual(route, original)


if __name__ == '__main__':
    unittest.main()
