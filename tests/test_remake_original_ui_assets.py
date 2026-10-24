"""Original UI source identity, exact 4x pixels, and publication boundaries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


serve = module('original_ui_server', 'game/serve.py')
web = module('original_ui_web', 'game/build_web.py')
png = module('original_ui_png', 'game/build_portrait_manifest.py')


class OriginalUIAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'game/assets/original-ui/index.json').read_text())

    def test_assets_keep_capture_provenance_and_exact_four_times_pixels(self):
        data = self.manifest
        self.assertEqual(data['schema'], 'tk2-original-ui-v1')
        self.assertEqual(data['provenance'], 'original-capture-derived')
        self.assertFalse(data['native_dimensions_confirmed'])
        self.assertEqual({row['id'] for row in data['assets']}, set(serve.ORIGINAL_UI_IDS))
        self.assertEqual(len(data['assets']), 14)
        for row in data['assets']:
            with self.subTest(asset=row['id']):
                self.assertFalse(row['native_dimensions_confirmed'])
                self.assertEqual(row['provenance'], 'original-capture-derived')
                source = ROOT / row['source_file']
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), row['source_sha256'])
                preview = row['source_crop']
                original = ROOT / 'game' / preview['path'].lstrip('/')
                # Reference crop bytes are retained; the resampled copy is a separate file.
                self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), row['reference_crop_sha256'])
                decoded = {}
                for field in ('source_crop', 'pixel_base', 'display_4x'):
                    item = row[field]
                    raw = (ROOT / 'game' / item['path'].lstrip('/')).read_bytes()
                    self.assertEqual(len(raw), item['bytes'])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
                    size, pixels = png.png_pixels(raw, (item['width'], item['height']))
                    decoded[field] = (size, pixels)
                (width, height), base = decoded['pixel_base']
                size, scaled = decoded['display_4x']
                self.assertEqual(size, (width * 4, height * 4))
                expected = bytearray()
                for y in range(height):
                    line = b''.join(base[(y * width + x) * 4:(y * width + x + 1) * 4] * 4
                                    for x in range(width))
                    expected.extend(line * 4)
                self.assertEqual(scaled, bytes(expected), '4x must add no blended or invented pixels')

    def test_release_publishes_only_known_images_and_styles(self):
        declared = {item['path'] for item in self.manifest['files']}
        expected = declared | {'/assets/original-ui/index.json'}
        self.assertEqual(set(serve.original_ui_static_assets()), expected)
        assets = web.static_allowlist()
        self.assertTrue(all(path.lstrip('/') in assets for path in expected))
        for name in ('original-ui.js', 'original-ui.css', 'command-menu.css',
                     'facilities-ui.css', 'equipment-ui.css'):
            self.assertIn(name, assets)
        self.assertFalse(any(name.startswith(('art/', 'native-source/')) or
                             name.endswith(('.nes', '.state')) for name in assets))
        self.assertNotIn('assets/original-ui/unlisted.png', assets)

    def test_replaced_image_or_parent_symlink_cannot_escape_the_static_root(self):
        for relative in ('source/command-city.png', 'pixel-base/command-city.png',
                         'command-city-4x.png'):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as folder:
                here = Path(folder) / 'game'
                destination = here / 'assets/original-ui' / relative
                destination.parent.mkdir(parents=True)
                outside = Path(folder) / 'private'
                outside.write_bytes(b'not a public asset')
                destination.symlink_to(outside)
                with self.assertRaises(FileNotFoundError):
                    serve.static_file_bytes(here, str(destination.relative_to(here)))


if __name__ == '__main__':
    unittest.main()
