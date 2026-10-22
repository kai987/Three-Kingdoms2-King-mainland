"""Portrait routes expose only exact index-listed PNGs and public UI assets."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tk2_game_serve', ROOT / 'game/serve.py')
serve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve)


class PortraitStaticTests(unittest.TestCase):
    def prepare(self, directory, people):
        here = Path(directory) / 'game'
        base = here / 'assets/portraits'
        for folder in ('original', 'generated', 'enhanced', 'evidence'):
            (base / folder).mkdir(parents=True)
        (base / 'index.json').write_text(json.dumps(dict(schema='tk2-portraits-v1', people=people)))
        return here, base

    def test_only_exact_manifest_pngs_join_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            people = dict(a={'path':'/assets/portraits/original/000.png'},
                          b={'path':'/assets/portraits/generated/person-1001.png'},
                          evidence={'path':'/assets/portraits/evidence/names.png'},
                          traversal={'path':'/assets/portraits/original/../../source.nes'},
                          remote={'path':'https://example.com/image.png'},
                          encoded={'path':'/assets/portraits/original/%2e%2e.png'},
                          folder={'path':'/assets/portraits/original/'},
                          query={'path':'/assets/portraits/original/000.png?x=1'})
            here, base = self.prepare(directory, people)
            assets = serve.portrait_static_assets(here)
            self.assertEqual(set(assets), {'/portraits.js','/portraits.css','/assets/portraits/index.json',
                '/assets/portraits/original/000.png','/assets/portraits/generated/person-1001.png'})
            self.assertEqual(assets['/assets/portraits/original/000.png'],('assets/portraits/original/000.png','image/png'))
            with self.assertRaises(FileNotFoundError):serve.static_file_bytes(here,'assets/portraits/original/000.png')
            (base/'original/000.png').write_bytes(b'controlled PNG fixture')
            self.assertEqual(serve.static_file_bytes(here,'assets/portraits/original/000.png'),b'controlled PNG fixture')

    def test_only_matching_enhanced_identity_is_added_and_original_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            people = {'person-1': {'path': '/assets/portraits/original/000.png',
                                  'enhanced': {'path': '/assets/portraits/enhanced/person-1.png',
                                               'width': 128, 'height': 160}}}
            here, base = self.prepare(directory, people)
            (base/'enhanced/person-1.png').write_bytes(b'controlled enhanced PNG fixture')
            (base/'enhanced/unindexed.png').write_bytes(b'not public')
            assets = serve.portrait_static_assets(here)
            self.assertIn('/assets/portraits/original/000.png', assets)
            self.assertEqual(assets['/assets/portraits/enhanced/person-1.png'],
                             ('assets/portraits/enhanced/person-1.png', 'image/png'))
            self.assertNotIn('/assets/portraits/enhanced/unindexed.png', assets)
            self.assertEqual(serve.static_file_bytes(here, assets['/assets/portraits/enhanced/person-1.png'][0]),
                             b'controlled enhanced PNG fixture')

    def test_malformed_enhanced_metadata_keeps_only_original_route(self):
        malformed = [None, [], 'enhanced/person-1.png', {},
                     {'path': '/assets/portraits/enhanced/person-1.png'},
                     {'path': '/assets/portraits/enhanced/person-1.png', 'width': 32, 'height': 40},
                     {'path': '/assets/portraits/enhanced/person-1.png', 'width': '128', 'height': 160},
                     {'path': '/assets/portraits/enhanced/person-1.png', 'width': 128, 'height': 159}]
        for metadata in malformed:
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as directory:
                here, _ = self.prepare(directory, {'person-1': {'path': '/assets/portraits/original/000.png',
                                                                'enhanced': metadata}})
                assets = serve.portrait_static_assets(here)
                self.assertIn('/assets/portraits/original/000.png', assets)
                self.assertFalse(any(path.startswith('/assets/portraits/enhanced/') for path in assets))

    def test_enhanced_paths_cannot_cross_people_or_escape_exact_png_route(self):
        paths = ['/assets/portraits/enhanced/person-2.png',
                 '/assets/portraits/enhanced/../original/000.png',
                 '/assets/portraits/enhanced/%2e%2e.png',
                 '/assets/portraits/enhanced/person-1.png?x=1',
                 '/assets/portraits/enhanced/person-1.svg',
                 '/assets/portraits/enhanced/person-1/',
                 'https://example.com/person-1.png',
                 '/assets/portraits/original/person-1.png']
        for path in paths:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                people = {'person-1': {'path': '/assets/portraits/original/000.png',
                                       'enhanced': {'path': path, 'width': 128, 'height': 160}}}
                here, _ = self.prepare(directory, people)
                assets = serve.portrait_static_assets(here)
                self.assertEqual(set(assets), {'/portraits.js', '/portraits.css', '/assets/portraits/index.json',
                                              '/assets/portraits/original/000.png'})
        with tempfile.TemporaryDirectory() as directory:
            people = {'../private': {'path': '/assets/portraits/original/000.png',
                                     'enhanced': {'path': '/assets/portraits/enhanced/../private.png',
                                                  'width': 128, 'height': 160}}}
            here, _ = self.prepare(directory, people)
            self.assertFalse(any(path.startswith('/assets/portraits/enhanced/')
                                 for path in serve.portrait_static_assets(here)))

    def test_enhanced_file_and_directory_symlinks_are_rejected_even_after_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            people = {'person-1': {'path': '/assets/portraits/original/000.png',
                                  'enhanced': {'path': '/assets/portraits/enhanced/person-1.png',
                                               'width': 128, 'height': 160}}}
            here, base = self.prepare(directory, people)
            inputs = Path(directory)/'private.png';inputs.write_bytes(b'not served')
            enhanced = base/'enhanced/person-1.png'
            enhanced.write_bytes(b'published PNG fixture')
            route = '/assets/portraits/enhanced/person-1.png'
            self.assertIn(route, serve.portrait_static_assets(here))
            enhanced.unlink();enhanced.symlink_to(inputs)
            self.assertNotIn(route, serve.portrait_static_assets(here))
            with self.assertRaises(FileNotFoundError):
                serve.static_file_bytes(here, 'assets/portraits/enhanced/person-1.png')
            enhanced.unlink();(base/'enhanced').rmdir()
            private_folder = Path(directory)/'private-portraits';private_folder.mkdir()
            (private_folder/'person-1.png').write_bytes(b'not served either')
            (base/'enhanced').symlink_to(private_folder, target_is_directory=True)
            self.assertNotIn(route, serve.portrait_static_assets(here))
            with self.assertRaises(FileNotFoundError):
                serve.static_file_bytes(here, 'assets/portraits/enhanced/person-1.png')

    def test_missing_bad_index_and_symlinks_never_expose_build_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            here, base = self.prepare(directory, {'a':{'path':'/assets/portraits/original/000.png'}})
            inputs = Path(directory) / 'private.nes';inputs.write_bytes(b'not served')
            (base/'original/000.png').symlink_to(inputs)
            self.assertNotIn('/assets/portraits/original/000.png',serve.portrait_static_assets(here))
            with self.assertRaises(FileNotFoundError):serve.static_file_bytes(here,'assets/portraits/original/000.png')
            with self.assertRaises(FileNotFoundError):serve.static_file_bytes(here,'../private.nes')
            index = base/'index.json';index.write_text('invalid JSON')
            self.assertEqual(len(serve.portrait_static_assets(here)),3)
            for value in (None, [], {'schema':'tk2-portraits-v1','people':[]}):
                index.write_text(json.dumps(value))
                self.assertEqual(len(serve.portrait_static_assets(here)),3)
            index.unlink();self.assertEqual(len(serve.portrait_static_assets(here)),3)
            index.symlink_to(inputs)
            self.assertEqual(len(serve.portrait_static_assets(here)),3)
            with self.assertRaises(FileNotFoundError):serve.static_file_bytes(here,'assets/portraits/index.json')


if __name__ == '__main__':unittest.main()
