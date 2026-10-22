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
        for folder in ('original', 'generated', 'evidence'):
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
