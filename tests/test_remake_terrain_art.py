"""Terrain art preserves current rivers, routes and city locations.

These tests inspect the final visible map pixels.  The old full-map artwork is
not a rendering baseline: current road/water changes always take precedence.
"""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'game/config/terrain-art.json'
NS = {'svg': 'http://www.w3.org/2000/svg'}
CITY_POSITIONS_SHA = 'acea6eb244f854a602f5594d33a6d62bddc1677c8ab321168a7e21876206076d'
APPROVED_ART_RGBA_SHA = '5bbd57a0a685f6aa7fea017c1647925487edc35be062f2410c7b82dff10a2617'


def module():
    spec = importlib.util.spec_from_file_location('tested_terrain_art', ROOT / 'game/build_terrain_art.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


class CurrentMapTerrainArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = module()
        cls.config = json.loads((ROOT / CONFIG).read_bytes())
        cls.cities_before = (ROOT / cls.config['cities']).read_bytes()
        cls.png, cls.receipt, cls.details = cls.builder.render()
        cls.width, cls.height = cls.details['size']
        cls.base = cls.details['base_pixels']
        cls.output = cls.details['output_pixels']
        cls.art = cls.details['art_mask']
        cls.protected = cls.details['protected_mask']
        cls.applied = cls.details['applied_mask']
        cls.island_changes = cls.details['island_changes']
        cls.surface_changes = cls.details['surface_changes']
        cls.shore_changes = bytes(a or b for a, b in zip(cls.island_changes, cls.surface_changes))

    @classmethod
    def pixel(cls, pixels, x, y):
        index = (y * cls.width + x) * 4
        return pixels[index:index + 4]

    def assert_same_pixels(self, indices, message):
        bad = next((index for index in indices
                    if self.base[index*4:index*4+4] != self.output[index*4:index*4+4]), None)
        self.assertIsNone(bad, message + ('' if bad is None else f' at ({bad % self.width},{bad // self.width})'))

    def test_current_base_is_exact_outside_the_art_delta_and_inside_all_protection(self):
        count = self.width * self.height
        self.assertEqual((self.width, self.height), (1352, 1024))
        for mask in (self.art, self.protected, self.applied, self.island_changes, self.surface_changes):
            self.assertEqual(len(mask), count)
            self.assertLessEqual(set(mask), {0, 1})
        self.assert_same_pixels((n for n in range(count) if not self.art[n] and not self.shore_changes[n]),
                                'Only the rendered ground, ocean and edited islands differ from the base')
        self.assert_same_pixels((n for n in range(count) if self.protected[n] and not self.shore_changes[n]),
                                'Current water, banks, road corridors and castles take precedence in mountain art')
        self.assertFalse(any(self.applied[n] and (not self.art[n] or self.protected[n])
                             for n in range(count)))

    def test_applied_pixels_are_the_retained_native_art_without_blending(self):
        crop = self.details['crop']
        self.assertEqual(crop, dict(x=0, y=280, width=288, height=432))
        source = self.config['art_source']
        size, pixels = self.builder.png_pixels((ROOT / source['path']).read_bytes(),
                                               (crop['width'], crop['height']))
        self.assertEqual(size, (288, 432))
        self.assertEqual(pixels, self.details['source_pixels'])
        self.assertEqual(set(pixels[3::4]), {0, 255})
        opaque = sum(alpha == 255 for alpha in pixels[3::4])
        self.assertEqual(opaque, 63868, 'The retained crop contains the approved art delta only')
        self.assertGreater(sum(self.applied), 50000,
                           'Infrastructure protection must still retain the approved mountain landscape')
        for y in range(crop['height']):
            for x in range(crop['width']):
                local = (y * crop['width'] + x) * 4
                index = (y + crop['y']) * self.width + x + crop['x']
                if self.applied[index]:
                    self.assertEqual(pixels[local + 3], 255)
                    self.assertEqual(self.output[index*4:index*4+4], pixels[local:local+4])
                if not pixels[local + 3]:
                    self.assertEqual(pixels[local:local+4], bytes(4))
        _, decoded = self.builder.png_pixels(self.png, (self.width, self.height))
        self.assertEqual(decoded, self.output)

    def test_transparent_source_reconstructs_the_independently_pinned_approved_art(self):
        approval = self.config['approval']
        self.assertEqual(approval['original_asset_rgba_sha256'], APPROVED_ART_RGBA_SHA)
        _, immutable = self.builder.png_pixels((ROOT / approval['immutable_baseline']).read_bytes(),
                                              (self.width, self.height))
        rebuilt = bytearray(immutable)
        source = self.details['source_pixels']
        crop = self.details['crop']
        changed = 0
        for y in range(crop['height']):
            for x in range(crop['width']):
                local = (y * crop['width'] + x) * 4
                if not source[local+3]:
                    continue
                index = ((y+crop['y']) * self.width + x+crop['x']) * 4
                pixel = source[local:local+4]
                self.assertNotEqual(pixel, immutable[index:index+4], (x, y))
                rebuilt[index:index+4] = pixel
                changed += 1
        self.assertEqual(changed, 63868)
        self.assertEqual(sha256(rebuilt).hexdigest(), APPROVED_ART_RGBA_SHA,
                         'The small transparent source must retain exactly the approved native artwork')

    def test_fu_and_extended_yangtze_blue_pixels_and_two_pixel_banks_survive(self):
        document = ET.fromstring((ROOT / 'game/map-source/historic-water.svg').read_bytes())
        groups = {group.get('data-authorial-addition'): group
                  for group in document.findall('.//svg:g[@data-authorial-addition]', NS)}
        self.assertTrue({'fu-dianjiang', 'upper-jinsha-visual'} <= set(groups))
        blue = bytes((0, 42, 248, 255))
        _, hydrology = self.builder.png_pixels((ROOT / self.config['hydrology']).read_bytes(),
                                              (self.width, self.height))
        targets = set()
        for identity in ('fu-dianjiang', 'upper-jinsha-visual'):
            points = set()
            for rect in groups[identity].findall('svg:rect', NS):
                x, y, width, height = (int(rect.attrib[key]) for key in ('x', 'y', 'width', 'height'))
                # The retained original SVG projection is translate(-136 0).
                points.update((xx - 136, yy) for xx in range(x, x + width)
                              for yy in range(y, y + height))
            self.assertTrue(points, identity)
            visible_blue = 0
            for x, y in points:
                self.assertEqual(self.pixel(hydrology, x, y), blue, (identity, x, y))
                base = self.pixel(self.base, x, y)
                # The current native road layer legitimately crosses the
                # extended Jinsha. Keep those road/bridge pixels exactly;
                # every blue pixel visible in the current base stays blue.
                self.assertEqual(self.pixel(self.output, x, y), base, (identity, x, y))
                if base == blue:
                    visible_blue += 1
                if identity == 'fu-dianjiang':
                    self.assertEqual(base, blue, (identity, x, y))
                targets.update(yy * self.width + xx
                               for yy in range(max(0, y-2), min(self.height, y+3))
                               for xx in range(max(0, x-2), min(self.width, x+3)))
            self.assertGreater(visible_blue, len(points) // 2,
                               'The current visible river remains substantially continuous between road crossings')
        self.assert_same_pixels(targets, 'A current river bank cannot be replaced by old mountain art')

    def test_existing_water_banks_and_current_road_repairs_survive_the_art_crop(self):
        _, hydrology = self.builder.png_pixels((ROOT / self.config['hydrology']).read_bytes(),
                                              (self.width, self.height))
        crop = self.details['crop']
        banks = set()
        for y in range(crop['y'], crop['y'] + crop['height']):
            for x in range(crop['x'], crop['x'] + crop['width']):
                r, g, b, _ = self.pixel(hydrology, x, y)
                if b >= 120 and b > r+40 and b > g+40:
                    banks.update(yy * self.width + xx
                                 for yy in range(max(0, y-2), min(self.height, y+3))
                                 for xx in range(max(0, x-2), min(self.width, x+3)))
        self.assertTrue(banks)
        self.assert_same_pixels(banks, 'All current western water and its banks remain current')
        # Independent evidence of the old-full-map bug: every repaired current
        # map pixel must survive, including road changes as well as new blue.
        _, legacy = self.builder.png_pixels(
            (ROOT / self.config['approval']['immutable_baseline']).read_bytes(),
            (self.width, self.height))
        changed = [n for n in range(self.width * self.height)
                   if self.base[n*4:n*4+4] != legacy[n*4:n*4+4]]
        self.assertGreater(len(changed), 1000)
        self.assert_same_pixels((n for n in changed if not self.shore_changes[n]),
                                'Updated roads and water cannot regress outside the coastal edits')

    def test_islands_contract_by_one_quarter_under_fixed_castles_and_access_roads(self):
        _, ground = self.builder.png_pixels((ROOT / self.config['hydrology']).read_bytes(),
                                            (self.width, self.height))
        expected = {'yizhou': ((1140, 703), [1102, 638, 1202, 798]),
                    'zhuya': ((565, 885), [484, 871, 594, 990])}
        for city, (center, original_bounds) in expected.items():
            with self.subTest(city=city):
                spec = self.config['islands'][city]
                result = self.receipt['islands'][city]
                self.assertEqual(result['before_bounds'], original_bounds)
                before, after = result['before_bounds'], result['after_bounds']
                for axis in (0, 1):
                    old_length = before[axis+2] - before[axis] + 1
                    new_length = after[axis+2] - after[axis] + 1
                    self.assertAlmostEqual(new_length, old_length * .75, delta=1)
                self.assertAlmostEqual(result['land_pixels_after'] / result['land_pixels_before'],
                                       .75 ** 2, delta=.01)
                self.assertTrue(self.builder.blue_water(self.pixel(self.output, *spec['pivot'])))
                self.assertEqual(self.pixel(self.output, *center), bytes((255, 255, 255, 255)))
                left, top, right, bottom = spec['region']
                cells = (y * self.width + x for y in range(top, bottom) for x in range(left, right))
                fixed = [i for i in cells if self.base[i*4:i*4+4] != ground[i*4:i*4+4]]
                self.assertGreater(len(fixed), 600, 'Both the castle and the access road must be present')
                self.assert_same_pixels(fixed, 'The baked castle and access road remain at native coordinates')
        self.assertGreater(sum(self.island_changes), 10_000)
        for index, changed in enumerate(self.island_changes):
            if changed:
                x, y = index % self.width, index // self.width
                self.assertTrue(any(left <= x < right and top <= y < bottom
                                    for left, top, right, bottom in (spec['region'] for spec in self.config['islands'].values())))

    def test_northeast_shorelines_and_city_sites_match_the_revised_terrain(self):
        _, ground = self.builder.png_pixels((ROOT / self.config['hydrology']).read_bytes(),
                                            (self.width, self.height))
        sea = {'bohai_bay': (1004, 166), 'liaodong_bay': (1088, 125),
               'laizhou_bay': (1058, 207), 'bohai_strait': (1130, 178),
               'yellow_sea': (1188, 211), 'jeju_channel': (1295, 343),
               'korea_southwest_sea': (1282, 310)}
        land = {'liaodong_peninsula': (1160, 135), 'shandong_peninsula': (1158, 228),
                'korean_peninsula': (1300, 303), 'jeju': (1295, 364)}
        for expected, locations in ((True, sea), (False, land)):
            for name, (x, y) in locations.items():
                with self.subTest(name=name):
                    self.assertEqual(self.builder.blue_water(self.pixel(ground, x, y)), expected)
                    if not self.surface_changes[y*self.width+x]:
                        self.assertEqual(self.pixel(self.output, x, y), self.pixel(ground, x, y))
        shared = json.loads(self.cities_before)['catalog']['cities']
        positions = {city['id']: city['position'] for city in shared}
        expansion = json.loads((ROOT / 'game/config/campaigns/city-expansion-map.json').read_bytes())
        positions.update({city: entry['position'] for city, entry in expansion['cities'].items()})
        revised = {'liaoxi': [1037, 127], 'changli': [1117, 72], 'bohai': [951, 191],
                   'jinan': [973, 227], 'qi': [1010, 233], 'beihai': [1046, 250],
                   'lelang': [1276, 157], 'daifang': [1296, 190]}
        for city, point in revised.items():
            with self.subTest(city=city):
                self.assertEqual(positions[city], point)
                self.assertFalse(self.builder.blue_water(self.pixel(ground, *point)))

    def test_world_surface_rebuilds_land_and_sea_beneath_the_current_foreground(self):
        _, ground = self.builder.png_pixels((ROOT / self.config['hydrology']).read_bytes(),
                                            (self.width, self.height))
        sea_in_other_regions = [(1320, 480), (1250, 820), (850, 960)]
        for x, y in sea_in_other_regions:
            with self.subTest(sea=(x, y)):
                self.assertTrue(self.surface_changes[y*self.width+x])
                self.assertTrue(self.builder.blue_water(self.pixel(self.output, x, y)))
        redrawn_land = [(1166, 117), (1099, 257), (1080, 264), (1322, 279)]
        for x, y in redrawn_land:
            with self.subTest(land=(x, y)):
                self.assertTrue(self.surface_changes[y*self.width+x])
                r, g, b, _ = self.pixel(self.output, x, y)
                self.assertGreater(g, max(r, b)+75)
        self.assertGreater(sum(self.surface_changes), 300000)
        self.assertEqual(sum(self.surface_changes), self.receipt['stats']['surface_pixels_changed'])
        for index, change in enumerate(self.surface_changes):
            if change:
                pixel = slice(index*4, index*4+4)
                self.assertEqual(self.base[pixel], ground[pixel])
                self.assertNotIn(ground[pixel], (bytes((0, 42, 248, 255)), bytes((33, 69, 255, 255))))

    def test_luzon_is_shifted_south_and_clipped_at_the_map_edge(self):
        luzon = self.receipt['scenery']['luzon']
        self.assertEqual(luzon['bounds'], [1094, 924, 1186, self.height-1])
        self.assertEqual(luzon['land_pixels'], 5677)
        self.assertGreater(max(y for _, y in self.config['luzon']['outline']), self.height)
        self.assertGreater(luzon['bounds'][1], self.receipt['islands']['yizhou']['after_bounds'][3])
        for x, y in ((1135, 936), (1145, 949), (1150, self.height-1)):
            with self.subTest(point=(x, y)):
                self.assertTrue(self.builder.blue_water(self.pixel(self.base, x, y)))
                r, g, b, _ = self.pixel(self.output, x, y)
                self.assertGreater(g, max(r, b)+75)
        self.assertTrue(self.builder.blue_water(self.pixel(self.output, 1265, 1002)))
        self.assertTrue(self.builder.blue_water(self.pixel(self.output, 1135, 880)))

    def test_luzon_ridge_cores_reuse_the_existing_terrain_pixels(self):
        source = ROOT / self.config['world_surface']['original_surface']
        _, terrain = self.builder.png_pixels(source.read_bytes(), (self.width, self.height))
        for (x, y), (sx, sy) in [((1137, 964), (969, 589)), ((1162, 958), (1002, 616)),
                                 ((1144, 1015), (825, 762))]:
            with self.subTest(pixel=(x, y)):
                donor = self.pixel(terrain, sx, sy)
                self.assertLess(max(donor[:3]), 70)
                self.assertEqual(self.pixel(self.output, x, y), donor)

    def test_redrawn_coasts_round_the_rim_and_transition_at_native_resolution(self):
        profiles = {
            'bohai': (975, 176, 1, 0), 'liaodong': (1158, 112, -1, 0),
            'shandong': (1122, 214, 0, -1), 'korea': (1286, 246, -1, 0),
        }
        for region, (x, y, dx, dy) in profiles.items():
            with self.subTest(region=region):
                transect = [self.pixel(self.output, x+offset*dx, y+offset*dy)
                            for offset in range(20)]
                first_ocean = next(i for i, pixel in enumerate(transect) if pixel[2] > 225)
                edge = transect[:first_ocean]
                self.assertGreater(transect[0][1], 140)
                self.assertTrue(any(24 < g < 160 and g > b for _, g, b, _ in edge[:5]))
                dark_width = sum(max(pixel[:3]) < 45 for pixel in edge)
                self.assertLessEqual(3, dark_width)
                self.assertLessEqual(dark_width, 8)
                self.assertLessEqual(first_ocean, 16)
                self.assertGreaterEqual(len({pixel[2] for pixel in edge}), 8)

    def test_render_is_deterministic_and_preserves_all_115_city_positions(self):
        png, receipt, details = self.builder.render()
        self.assertEqual(png, self.png)
        self.assertEqual(receipt, self.receipt)
        self.assertEqual(details['output_pixels'], self.output)
        self.assertEqual((ROOT / self.config['cities']).read_bytes(), self.cities_before)
        cities = json.loads(self.cities_before)['catalog']['cities']
        positions = {city['id']: city['position'] for city in cities}
        self.assertEqual(len(positions), 115)
        self.assertEqual(positions['jingzhao'], [497, 336])
        self.assertEqual(sha256(canonical(positions)).hexdigest(), CITY_POSITIONS_SHA)
        self.assertEqual(receipt['positions_sha256'], CITY_POSITIONS_SHA)
        castle_boxes = {y*self.width+x for city, (cx, cy) in positions.items() if city not in self.config['islands']
                        for y in range(max(0, cy-16), min(self.height, cy+16))
                        for x in range(max(0, cx-16), min(self.width, cx+16))}
        self.assert_same_pixels((n for n in castle_boxes if not self.surface_changes[n]),
                                'City boxes outside redrawn ground retain the current base')

    def test_check_rejects_a_stale_pinned_source_without_reading_or_writing_other_files(self):
        config = deepcopy(self.config)
        crop = config['art_source']['crop']
        pixels = bytearray(self.details['source_pixels'])
        pixel = next(index for index in range(0, len(pixels), 4) if pixels[index+3] == 255)
        pixels[pixel] ^= 1
        changed_source = self.builder.png_encode((crop['width'], crop['height']), bytes(pixels))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / CONFIG
            path.parent.mkdir(parents=True)
            path.write_bytes(json.dumps(config, ensure_ascii=False).encode())
            source = root / config['art_source']['path']
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(changed_source)
            output, receipt = root / config['output'], root / config['manifest']
            output.parent.mkdir(parents=True, exist_ok=True)
            receipt.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b'unchanged output sentinel')
            receipt.write_bytes(b'unchanged receipt sentinel')
            with self.assertRaisesRegex(ValueError, '(?i)source.*hash|hash.*source'):
                self.builder.build(check=True, root=root, config_path=CONFIG)
            self.assertEqual(output.read_bytes(), b'unchanged output sentinel')
            self.assertEqual(receipt.read_bytes(), b'unchanged receipt sentinel')
            self.assertEqual(source.read_bytes(), changed_source)


if __name__ == '__main__':
    unittest.main()
