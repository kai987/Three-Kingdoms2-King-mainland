"""Per-item art identity and publication boundaries; game rules remain untouched."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


serve = module('equipment_icons_server', 'game/serve.py')
web = module('equipment_icons_web', 'game/build_web.py')
png = module('equipment_icons_png', 'game/build_portrait_manifest.py')


class EquipmentIcons(unittest.TestCase):
    def test_every_item_has_distinct_reviewed_art_and_preserved_source(self):
        data = json.loads((ROOT / 'game/assets/equipment-icons/index.json').read_text())
        self.assertEqual(data['schema'], 'tk2-equipment-icons-v1')
        self.assertEqual(data['provenance'], 'remake-equipment-icon')
        self.assertEqual(data['generator'], 'built-in-imagegen')
        rows = data['assets']
        self.assertEqual({(row['slot'], row['item']) for row in rows},
                         {('weapon', i) for i in range(29)} | {('armor', i) for i in range(8)})
        self.assertEqual(len({row['sha256'] for row in rows}), 37)
        for row in rows:
            raw = (ROOT / 'game' / row['path'].lstrip('/')).read_bytes()
            self.assertEqual(raw[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', raw[16:24]), (128, 128))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            self.assertEqual(len(raw), row['bytes'])
            unused_size, pixels = png.png_pixels(raw, (128, 128))
            colors = {pixels[i:i+4] for i in range(0, len(pixels), 4)}
            self.assertTrue(any(color[3] == 0 for color in colors), 'Exterior remains transparent')
            self.assertTrue(any(color[3] == 255 for color in colors), 'Icon is not blank')
            self.assertTrue(all(color[3] in (0, 255) for color in colors), 'No blended alpha edge')
            self.assertLessEqual(len(colors), 7, 'Six color retro palette plus transparency')
            source = ROOT / row['source_file']
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), row['source_sha256'])

    def test_only_fixed_runtime_icons_are_published_with_subpath_build(self):
        declared = serve.equipment_icon_static_assets()
        expected = {'/assets/equipment-icons/index.json'} | {
            f'/assets/equipment-icons/{slot}-{i}.png'
            for slot, count in (('weapon', 29), ('armor', 8)) for i in range(count)}
        self.assertEqual(set(declared), expected)
        allowed = web.static_allowlist()
        self.assertTrue(all(name.lstrip('/') in allowed for name in expected))
        self.assertFalse(any('equipment-icons-v1' in name or name.endswith('-source.png')
                             for name in allowed))
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder) / 'game'
            target = here / 'assets/equipment-icons/weapon-0.png'
            target.parent.mkdir(parents=True)
            outside = Path(folder) / 'private'
            outside.write_text('private')
            target.symlink_to(outside)
            with self.assertRaises(FileNotFoundError):
                serve.static_file_bytes(here, str(target.relative_to(here)))


if __name__ == '__main__':
    unittest.main()
