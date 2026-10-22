"""Native battle assets ship offline through an exact PNG allowlist.

These tests use the standard library PNG decoder already used for portraits;
CI does not need Pillow, a ROM, archived states or an emulator for this group.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


server = module('battle_asset_server', ROOT/'game/serve.py')
png = module('battle_asset_png', ROOT/'game/build_portrait_manifest.py')
HEX = re.compile(r'[0-9a-f]{64}\Z')
ASSET = re.compile(r'/assets/battle-original/[A-Za-z0-9_-]+\.png\Z')


def walk(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


class BattleAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/'game/assets/battle-original/index.json').read_text())
        cls.entries = list(walk(cls.manifest))

    def fixture(self, folder, manifest=None):
        here = Path(folder)/'game'
        base = here/'assets/battle-original'
        base.mkdir(parents=True)
        data = manifest or dict(schema='tk2-battle-original-v1',sprites=[dict(path='/assets/battle-original/listed.png')])
        (base/'index.json').write_text(json.dumps(data))
        (base/'listed.png').write_bytes(b'allowed fixture bytes')
        return here, base

    def test_every_shipped_png_has_exact_hash_size_and_original_capture_provenance(self):
        manifest = self.manifest
        self.assertEqual(manifest['schema'], 'tk2-battle-original-v1')
        self.assertEqual(manifest['rom_sha256'], '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82')
        self.assertEqual(manifest['palette']['name'], 'royaltea')
        self.assertFalse(manifest['build']['runtime_requires_rom'])
        self.assertFalse(manifest['build']['runtime_requires_emulator'])
        self.assertGreaterEqual(len(self.entries), 18)
        actual = set()
        for entry in self.entries:
            with self.subTest(path=entry['path']):
                self.assertRegex(entry['path'], ASSET)
                path = ROOT/'game'/entry['path'].lstrip('/')
                self.assertFalse(path.is_symlink())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'])
                size, pixels = png.png_pixels(path.read_bytes(), (entry['width'],entry['height']))
                self.assertEqual(size, (entry['width'],entry['height']))
                self.assertEqual(len(pixels),size[0]*size[1]*4)
                proof=entry['source']
                for key in ('screenshot_sha256','capture_sha256'):
                    self.assertRegex(proof[key], HEX)
                self.assertEqual(proof['resolution'],[256,240])
                self.assertEqual(proof['engine']['core_sha256'],manifest['core']['original_capture_core_sha256'])
                self.assertEqual(proof['pixel_format'],1)
                self.assertEqual(len(proof['ppu']['palette_indices']),32)
                self.assertEqual(len(proof['ppu']['chr_banks']),8)
                self.assertEqual(len(proof['ppu']['oam_records']),64)
                actual.add(path.name)
        self.assertEqual(actual,{p.name for p in (ROOT/'game/assets/battle-original').glob('*.png')})

    def test_native_layout_transparency_and_facing_keep_complete_riders(self):
        shape=self.manifest['native_resolution']
        self.assertEqual((shape['width'],shape['height'],shape['main_height'],shape['panel_height']),(256,240,160,80))
        self.assertEqual((shape['duel_name_height'],shape['duel_arena_height']),(64,96))
        for key in ('plain','tactical','mountain','water'):
            row=self.manifest['backgrounds'][key]
            self.assertEqual((row['width'],row['height']),(256,160))
        for kind,facing in [('infantry','right'),('infantry_enemy','left'),('duelist','right'),('duelist_enemy','left')]:
            row=self.manifest['sprites'][kind]
            self.assertEqual(row['facing'],facing)
            self.assertGreaterEqual(len(row['frames']),2)
            for frame in row['frames']:
                size=(16,16) if kind.startswith('infantry') else (96,96)
                self.assertEqual((frame['width'],frame['height']),size)
                self.assertEqual(frame['anchor'],dict(x=size[0]//2,y=size[1]))
                _,pixels=png.png_pixels((ROOT/'game'/frame['path'].lstrip('/')).read_bytes(),size)
                alpha=pixels[3::4]
                self.assertEqual(set(alpha),{0,255})
                if kind.startswith('duelist'):
                    # Keep the original low, crouched enemy pose; a clipped
                    # horse tail alone must not pass as a complete native frame.
                    occupied=[(i%size[0],i//size[0])for i,value in enumerate(alpha)if value]
                    self.assertGreater(len(occupied),300)
                    self.assertGreaterEqual(max(x for x,y in occupied)-min(x for x,y in occupied)+1,48)
                    self.assertGreaterEqual(max(y for x,y in occupied)-min(y for x,y in occupied)+1,28)
        self.assertEqual(self.manifest['intentionally_unavailable_effects'],['fire','arrow','impact','rock'])

    def test_complete_attack_formations_are_exact_opposing_native_capture_layers(self):
        """Do not replace the original mixed armies with repeated map tokens."""
        _,ground=png.png_pixels((ROOT/'game/assets/battle-original/plain.png').read_bytes(),(256,160))
        for pose,witness in enumerate(('attack','attack_advance')):
            row=self.manifest['witnesses'][witness]
            _,pixels=png.png_pixels((ROOT/'game'/row['path'].lstrip('/')).read_bytes(),(256,240))
            for kind,left,facing in [('attack_formation',0,'right'),('attack_formation_enemy',128,'left')]:
                formation=self.manifest['sprites'][kind]
                self.assertEqual(formation['facing'],facing)
                self.assertEqual(len(formation['frames']),2)
                frame=formation['frames'][pose]
                self.assertEqual((frame['width'],frame['height']),(128,160))
                self.assertEqual(frame['anchor'],dict(x=64,y=160))
                self.assertEqual(frame['source']['screenshot_sha256'],row['source']['screenshot_sha256'])
                self.assertEqual(frame['source']['source_rect'],[left,0,left+128,160])
                _,actual=png.png_pixels((ROOT/'game'/frame['path'].lstrip('/')).read_bytes(),(128,160))
                expected=bytearray()
                for y in range(160):
                    for x in range(left,left+128):
                        at=(y*256+x)*4
                        rgb=pixels[at:at+3]
                        expected.extend(rgb)
                        expected.append(0 if rgb==ground[at:at+3] else 255)
                self.assertEqual(actual,bytes(expected),'Every army pixel must come from its original frame; only grass becomes transparent')
                self.assertEqual(set(actual[3::4]),{0,255})
                occupied=[i for i,a in enumerate(actual[3::4])if a]
                self.assertGreater(len(occupied),500)
                self.assertGreater(max(i//128 for i in occupied)-min(i//128 for i in occupied),100)
                self.assertGreater(len({actual[i*4:i*4+3]for i in occupied}),2)

    def test_server_lists_exactly_manifest_pngs_and_no_source_or_unlisted_files(self):
        static=server.battle_static_assets(ROOT/'game')
        expected={entry['path'] for entry in self.entries}|{'/assets/battle-original/index.json'}
        self.assertEqual(set(static),expected)
        for path,(relative,mime)in static.items():
            self.assertEqual(relative,path.lstrip('/'))
            self.assertEqual(mime,'image/png' if path.endswith('.png') else 'application/json; charset=utf-8')
        self.assertNotIn('/assets/battle-original/source.nes',static)
        self.assertNotIn('/assets/battle-original/source.state',static)
        self.assertNotIn('/assets/battle-original/not-listed.png',static)

    def test_forged_manifest_paths_cannot_allow_rom_states_subdirs_or_traversal(self):
        invalid=['/assets/battle-original/source.nes','/assets/battle-original/source.state',
            '/assets/battle-original/../outside.png','/assets/battle-original/sub/inside.png',
            '/assets/battle-original/%2e%2e/outside.png','/assets/other.png',
            'https://example.com/file.png','/assets/battle-original/evil.svg']
        data=dict(schema='tk2-battle-original-v1',assets=[{'path':'/assets/battle-original/listed.png'}]+[{'path':p}for p in invalid])
        with tempfile.TemporaryDirectory() as folder:
            here,base=self.fixture(folder,data)
            (base/'not-listed.png').write_bytes(b'not allowed')
            (base/'source.nes').write_bytes(b'not a public ROM')
            (base/'source.state').write_bytes(b'not a public state')
            static=server.battle_static_assets(here)
            self.assertEqual(set(static),{'/assets/battle-original/index.json','/assets/battle-original/listed.png'})
            for path in invalid:self.assertNotIn(path,static)
            self.assertNotIn('/assets/battle-original/not-listed.png',static)

    def test_missing_wrong_schema_and_broken_json_never_scan_directory(self):
        for value in ('{',json.dumps({'schema':'not-battle','assets':[{'path':'/assets/battle-original/listed.png'}]})):
            with self.subTest(value=value),tempfile.TemporaryDirectory() as folder:
                here,base=self.fixture(folder)
                (base/'index.json').write_text(value)
                self.assertNotIn('/assets/battle-original/listed.png',server.battle_static_assets(here))
                (base/'index.json').unlink()
                self.assertNotIn('/assets/battle-original/listed.png',server.battle_static_assets(here))

    def test_symlinked_asset_folder_manifest_and_png_are_refused_at_registration(self):
        for where in ('assets','battle-original','index.json','listed.png'):
            with self.subTest(where=where),tempfile.TemporaryDirectory() as folder:
                here,base=self.fixture(folder)
                selected=(here/'assets')if where=='assets' else base if where=='battle-original' else base/where
                moved=Path(folder)/('moved-'+where)
                selected.rename(moved);selected.symlink_to(moved,target_is_directory=moved.is_dir())
                static=server.battle_static_assets(here)
                self.assertNotIn('/assets/battle-original/listed.png',static)
                if where!='listed.png':self.assertFalse(static)

    def test_replaced_after_registration_symlink_still_cannot_read_another_game_file(self):
        for outside in (False,True):
            for where in ('listed.png','index.json','battle-original','assets'):
                with self.subTest(outside=outside,where=where),tempfile.TemporaryDirectory() as folder:
                    here,base=self.fixture(folder)
                    static=server.battle_static_assets(here)
                    public='/assets/battle-original/'+('index.json'if where=='index.json' else 'listed.png')
                    self.assertIn(public,static)
                    selected=(here/'assets')if where=='assets' else base if where=='battle-original' else base/where
                    target=(Path(folder)if outside else here)/('private-'+where)
                    selected.rename(target)
                    selected.symlink_to(target,target_is_directory=target.is_dir())
                    with self.assertRaises(FileNotFoundError):
                        server.static_file_bytes(here,static[public][0])

    def test_png_corruption_and_mismatched_dimension_are_detected_offline(self):
        entry=self.manifest['sprites']['duelist']['frames'][0]
        data=(ROOT/'game'/entry['path'].lstrip('/')).read_bytes()
        altered=bytearray(data);altered[-5]^=1
        with self.assertRaises(ValueError):png.png_pixels(bytes(altered),(96,96))
        with self.assertRaises(ValueError):png.png_pixels(data,(95,96))
        self.assertNotEqual(hashlib.sha256(bytes(altered)).hexdigest(),entry['sha256'])


if __name__=='__main__':unittest.main()
