"""Native castle favicon formats, exact pixels and reproducible build boundary."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


icon = module('native_site_icon', 'tools/site-icon/build.py')
png = module('site_icon_png_reader', 'game/build_portrait_manifest.py')


class NativeSiteIconTests(unittest.TestCase):
    def test_pngs_have_only_opaque_native_gold_and_black_integer_pixels(self):
        rows = json.loads((ROOT / icon.SOURCE).read_text())['native_castle_sprite']['rows']
        expected = {(x, y - 2) for y, row in enumerate(rows) for x, value in enumerate(row)
                    if value in (2, 6)}
        for size in (32, 180):
            with self.subTest(size=size):
                raw = (ROOT / f'game/assets/site-icon-{size}.png').read_bytes()
                dimensions, rgba = png.png_pixels(raw, (size, size))
                self.assertEqual(dimensions, (size, size))
                colors = {tuple(rgba[i:i+4]) for i in range(0, len(rgba), 4)}
                self.assertEqual(colors, {icon.GOLD, icon.BLACK})
                scale = size // 8
                left, top = (size - 8 * scale) // 2, (size - 6 * scale) // 2
                for y in range(size):
                    for x in range(size):
                        cell = ((x - left) // scale, (y - top) // scale)
                        actual = tuple(rgba[(y * size + x) * 4:(y * size + x + 1) * 4])
                        self.assertEqual(actual, icon.GOLD if cell in expected else icon.BLACK)

    def test_ico_has_four_complete_classic_dib_sizes_and_no_hidden_payload(self):
        raw = (ROOT / 'game/favicon.ico').read_bytes()
        self.assertEqual(struct.unpack_from('<HHH', raw), (0, 1, 4))
        offset = 6 + 4 * 16
        for index, size in enumerate((16, 32, 48, 64)):
            width, height, colors, reserved, planes, bits, length, start = struct.unpack_from('<BBBBHHII', raw, 6 + index * 16)
            self.assertEqual((width, height, colors, reserved, planes, bits), (size, size, 0, 0, 1, 32))
            self.assertEqual(start, offset)
            header = struct.unpack_from('<IiiHHIIiiII', raw, start)
            self.assertEqual(header[:7], (40, size, size * 2, 1, 32, 0, size * size * 4))
            self.assertEqual(length, 40 + size * size * 4 + ((size + 31) // 32) * 4 * size)
            dib = raw[start + 40:start + 40 + size * size * 4]
            rgba = bytes(channel for y in reversed(range(size)) for x in range(size)
                         for channel in (dib[(y * size + x) * 4 + 2], dib[(y * size + x) * 4 + 1],
                                         dib[(y * size + x) * 4], dib[(y * size + x) * 4 + 3]))
            self.assertEqual({rgba[i+3] for i in range(0, len(rgba), 4)}, {255})
            if size == 32:
                _, native_png = png.png_pixels((ROOT / 'game/assets/site-icon-32.png').read_bytes(), (32, 32))
                self.assertEqual(rgba, native_png)
            self.assertFalse(any(raw[start + 40 + size * size * 4:start + length]))
            offset += length
        self.assertEqual(offset, len(raw))

    def test_svg_uses_the_same_native_silhouette_without_embedded_external_assets(self):
        svg = ElementTree.fromstring((ROOT / 'game/favicon.svg').read_bytes())
        self.assertEqual(svg.attrib['viewBox'], '0 0 8 8')
        self.assertEqual(svg.attrib['shape-rendering'], 'crispEdges')
        group = svg.find('{http://www.w3.org/2000/svg}g')
        self.assertEqual(group.attrib, {'fill': '#f8d878'})
        rows = json.loads((ROOT / icon.SOURCE).read_text())['native_castle_sprite']['rows']
        expected = {(x, y - 1) for y, row in enumerate(rows) for x, value in enumerate(row) if value in (2, 6)}
        self.assertEqual({(int(cell.attrib['x']), int(cell.attrib['y'])) for cell in group}, expected)
        self.assertTrue(all(cell.attrib['width'] == cell.attrib['height'] == '1' for cell in group))
        self.assertNotIn(b'href=', (ROOT / 'game/favicon.svg').read_bytes())

    def test_check_rebuild_is_read_only_and_rejects_stale_files(self):
        before = (ROOT / icon.SOURCE).read_bytes()
        icon.build(check=True)
        self.assertEqual((ROOT / icon.SOURCE).read_bytes(), before)
        with tempfile.TemporaryDirectory(prefix='tk2-site-icon-') as directory:
            root = Path(directory)
            source = root / icon.SOURCE
            source.parent.mkdir(parents=True)
            source.write_bytes(before)
            icon.build(root=root)
            icon.build(check=True, root=root)
            target = root / 'game/favicon.ico'
            target.write_bytes(b'stale')
            with self.assertRaisesRegex(ValueError, 'Site icon is stale'):
                icon.build(check=True, root=root)
            self.assertEqual(target.read_bytes(), b'stale')
            self.assertEqual(source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
