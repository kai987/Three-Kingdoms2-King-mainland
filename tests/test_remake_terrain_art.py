"""Approved mountains must not replace current rivers, roads or city locations.

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
CITY_POSITIONS_SHA = '91a45ddd1005028f4f20779946104df3bab590aab30a0c63c1d17f24a810d38d'
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
        for mask in (self.art, self.protected, self.applied):
            self.assertEqual(len(mask), count)
            self.assertLessEqual(set(mask), {0, 1})
        self.assert_same_pixels((n for n in range(count) if not self.art[n]),
                                'The transparent source cannot restore any old full-map pixel')
        self.assert_same_pixels((n for n in range(count) if self.protected[n]),
                                'Current water, banks, road corridors and castles take precedence')
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
        self.assert_same_pixels(changed, 'Updated roads and water cannot regress to the older art background')

    def test_render_is_deterministic_and_preserves_all_115_city_positions(self):
        png, receipt, details = self.builder.render()
        self.assertEqual(png, self.png)
        self.assertEqual(receipt, self.receipt)
        self.assertEqual(details['output_pixels'], self.output)
        self.assertEqual((ROOT / self.config['cities']).read_bytes(), self.cities_before)
        cities = json.loads(self.cities_before)['catalog']['cities']
        positions = {city['id']: city['position'] for city in cities}
        self.assertEqual(len(positions), 115)
        self.assertEqual(sha256(canonical(positions)).hexdigest(), CITY_POSITIONS_SHA)
        self.assertEqual(receipt['positions_sha256'], CITY_POSITIONS_SHA)
        castle_boxes = {y*self.width+x for cx, cy in positions.values()
                        for y in range(max(0, cy-16), min(self.height, cy+16))
                        for x in range(max(0, cx-16), min(self.width, cx+16))}
        self.assert_same_pixels(castle_boxes, 'All 115 native 32px city boxes retain the current base')

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
