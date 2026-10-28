"""A longer upper-Jinsha drawing must not move cities or create a water route.

The reviewed b6d0c16 geometry is pinned here as data, so these checks also run
in shallow CI checkouts without reading Git history or requiring Pillow.
"""
from collections import deque
from hashlib import sha256
import importlib.util
import json
from math import dist
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'svg': 'http://www.w3.org/2000/svg'}
ADDITION = 'upper-jinsha-visual'
LEGACY_WATER_SHA = '1b6d3702ef74362ad1f74d022fed7129e44968e7e3990899773f5b6fb4a21cb2'
CITY_POSITIONS_SHA = '80d1afa4da904731f5f99819b4e8e7a5fca1ff1a73d6d182ade237474fbb6a9a'
NETWORK_GEOMETRY_SHA = 'b6ce7eaf5fda2e5825a1a4644c49da7b5fed71d5422f9041b7c4dbc318a739b9'


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


png_reader = module('headwaters_png_reader', 'game/build_portrait_manifest.py')
network = module('headwaters_river_network', 'game/river_network.py')


def canonical_sha(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode()).hexdigest()


def rect_pixels(group):
    result = set()
    for rect in group.findall('svg:rect', NS):
        x, y, width, height = (int(rect.attrib[key])
                               for key in ('x', 'y', 'width', 'height'))
        # All source groups share the unchanged outer translate(-136 0).
        result.update((xx - 136, yy) for xx in range(x, x + width)
                      for yy in range(y, y + height))
    return result


def reachable(seed, allowed):
    seen, queue = {seed}, deque([seed])
    while queue:
        x, y = queue.popleft()
        for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if point in allowed and point not in seen:
                seen.add(point)
                queue.append(point)
    return seen


class YangtzeHeadwatersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg_raw = (ROOT / 'game/map-source/historic-water.svg').read_bytes()
        cls.svg = ET.fromstring(cls.svg_raw)
        cls.groups = cls.svg.findall('.//svg:g[@data-river]', NS)
        cls.addition = next(group for group in cls.groups
                            if group.get('data-authorial-addition') == ADDITION)
        cls.pixels = rect_pixels(cls.addition)
        cls.config = json.loads((ROOT / 'game/config/water-corrections.json').read_bytes())
        cls.map_source = json.loads((ROOT / 'game/config/map-source.json').read_bytes())
        cls.positions = cls.map_source['anchors']['positions']

    def test_legacy_rect_groups_and_outer_projection_remain_byte_exact(self):
        legacy, count = re.subn(
            rb'<g\b[^>]*\bdata-authorial-addition="upper-jinsha-visual"[^>]*>.*?</g>',
            b'', self.svg_raw, flags=re.DOTALL)
        self.assertEqual(count, 1)
        self.assertEqual(sha256(legacy).hexdigest(), LEGACY_WATER_SHA)
        self.assertEqual(self.svg.attrib['viewBox'], '0 0 1352 1024')
        outer = self.svg.find('svg:g', NS)
        self.assertEqual(outer.attrib['transform'], 'translate(-136 0)')
        self.assertEqual(outer.attrib['shape-rendering'], 'crispEdges')
        self.assertEqual(self.config['sources']['game/map-source/historic-water.svg'],
                         sha256(self.svg_raw).hexdigest())

    def test_new_head_is_a_connected_narrow_blue_grid_north_of_the_old_terminal(self):
        rects = self.addition.findall('svg:rect', NS)
        cells = []
        for rect in rects:
            self.assertEqual((rect.get('width'), rect.get('height'), rect.get('fill')),
                             ('2', '2', '#002af8'))
            x, y = int(rect.get('x')) - 136, int(rect.get('y'))
            self.assertEqual((x % 2, y % 2), (0, 0))
            cells.append((x, y))
        self.assertEqual(len(set(cells)), len(rects))
        self.assertEqual(len(self.pixels), len(rects) * 4)
        # A diagonal must share whole edges, rather than only touching at
        # corners and looking dotted after the source is rasterized.
        self.assertEqual(reachable(next(iter(self.pixels)), self.pixels), self.pixels)
        for y in range(480, 496):
            self.assertEqual({x for x, yy in self.pixels if yy == y}, set(range(158, 162)))
        left, right = min(x for x, _ in self.pixels)-1, max(x for x, _ in self.pixels)+1
        top, bottom = min(y for _, y in self.pixels)-1, max(y for _, y in self.pixels)+1
        background = {(x, y) for x in range(left, right+1) for y in range(top, bottom+1)} - self.pixels
        self.assertEqual(reachable((left, top), background), background,
                         'The continuous stroke must not enclose unpainted holes')
        source = self.config['yangtze_upper_source']
        self.assertEqual(source['source'], [160, 480])
        self.assertEqual(source['join'], [160, 602])
        self.assertEqual((source['pixel'], source['width'], source['color']),
                         (2, 4, '#002af8'))
        self.assertEqual((tuple(source['points'][0]), tuple(source['points'][-1])),
                         ((160, 480), (160, 602)))
        self.assertEqual(source['join'][1] - source['source'][1], 122)
        self.assertEqual(min(y for _, y in self.pixels), source['source'][1] - 2)

    def test_the_only_existing_water_join_is_the_original_yangtze_terminal(self):
        overlaps = {}
        min_water = set()
        for group in self.svg.findall('.//svg:g', NS):
            if group is self.addition:
                continue
            identity = group.get('data-river') or group.get('data-lake')
            if not identity:
                continue
            water = rect_pixels(group)
            overlaps.setdefault(identity, set()).update(self.pixels & water)
            if identity == 'min':
                min_water.update(water)
        self.assertEqual({key: value for key, value in overlaps.items() if value},
                         {'yangtze': {(160, 602), (161, 602), (160, 603), (161, 603)}})
        self.assertGreaterEqual(min(dist(a, b) for a in self.pixels for b in min_water), 43)

    def test_city_positions_and_32px_icon_boxes_are_preserved(self):
        self.assertEqual(canonical_sha(self.positions), CITY_POSITIONS_SHA)
        for city, (cx, cy) in self.positions.items():
            with self.subTest(city=city):
                self.assertFalse(any(cx-16 <= x < cx+16 and cy-16 <= y < cy+16
                                     for x, y in self.pixels))
                self.assertGreaterEqual(min(max(abs(x-cx), abs(y-cy))
                                            for x, y in self.pixels), 18)

    def test_render_paints_the_new_cells_and_preserves_the_surrounding_mountains(self):
        size = (1352, 1024)
        _, baseline = png_reader.png_pixels(
            (ROOT / 'game/map-source/road-ground.png').read_bytes(), size)
        _, rendered = png_reader.png_pixels(
            (ROOT / 'game/map-source/hydrology-ground.png').read_bytes(), size)
        for x, y in self.pixels:
            offset = (y * size[0] + x) * 4
            self.assertEqual(rendered[offset:offset+4], bytes((0, 42, 248, 255)), (x, y))
        # The whole surrounding western mountain/city region is unchanged
        # except the reviewed narrow river. This catches moved or
        # repainted slopes as well as accidental broad terrain replacement.
        for y in range(360, 760):
            for x in range(260):
                if (x, y) in self.pixels:
                    continue
                offset = (y * size[0] + x) * 4
                self.assertEqual(rendered[offset:offset+4], baseline[offset:offset+4], (x, y))
        # The reviewed corridor may touch a few foothill-shadow edges; it
        # must not run across the neighboring red/green mountain summits.
        peak_cores = ((150, 518, 174, 542), (168, 478, 196, 500),
                      (176, 550, 210, 576), (95, 538, 130, 570))
        self.assertFalse(any(left <= x <= right and top <= y <= bottom
                             for x, y in self.pixels
                             for left, top, right, bottom in peak_cores))

    def test_visual_extension_does_not_change_44_playable_routes_or_47_reaches(self):
        spec = json.loads((ROOT / 'game/config/river-network.json').read_bytes())
        geometry = {key: spec[key] for key in ('connections', 'nodes', 'ports', 'reaches')}
        self.assertEqual(canonical_sha(geometry), NETWORK_GEOMETRY_SHA)
        self.assertEqual((len(spec['connections']), len(spec['reaches'])), (44, 47))
        expected_ids = {row.get('id', f"{row['from']}:{row['to']}:river")
                        for row in spec['connections']}
        result = network.build()
        self.assertEqual(result['reach_count'], 47)
        self.assertEqual(len(result['routes']), 44)
        self.assertEqual({row['id'] for row in result['routes']}, expected_ids)
        self.assertFalse(any(ADDITION in identity for identity in spec['nodes']))
        self.assertFalse(any(ADDITION in row['id'] for row in spec['reaches']))


if __name__ == '__main__':
    unittest.main()
