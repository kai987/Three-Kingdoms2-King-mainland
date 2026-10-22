"""The optional4x art has an exact offline PNG allowlist, not a public tree."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('enhanced_battle_server', ROOT/'game/serve.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


def paths(value):
    if isinstance(value, dict):
        if 'path' in value:
            yield value['path']
        for row in value.values():
            yield from paths(row)
    elif isinstance(value, list):
        for row in value:
            yield from paths(row)


class EnhancedBattleStaticTests(unittest.TestCase):
    def fixture(self, folder, data=None):
        here = Path(folder)/'game'
        base = here/'assets/battle-enhanced'
        base.mkdir(parents=True)
        data = data or dict(schema='tk2-battle-enhanced-v1', scale=4,
                            sprites={'rider': {'frames': [{'path': '/assets/battle-enhanced/listed.png'}]}})
        (base/'index.json').write_text(json.dumps(data))
        (base/'listed.png').write_bytes(b'allowed bytes')
        return here, base

    def test_real_manifest_only_lists_shipped_pngs(self):
        data = json.loads((ROOT/'game/assets/battle-enhanced/index.json').read_text())
        result = server.enhanced_battle_static_assets(ROOT/'game')
        expected = set(paths(data)) | {'/assets/battle-enhanced/index.json'}
        self.assertEqual(set(result), expected)
        self.assertGreaterEqual(len(result), 100)
        for public, (relative, mime) in result.items():
            self.assertEqual(public.lstrip('/'), relative)
            self.assertEqual(mime, 'image/png' if public.endswith('.png') else 'application/json; charset=utf-8')
            self.assertEqual(server.static_file_bytes(ROOT/'game', relative), (ROOT/'game'/relative).read_bytes())

    def test_forged_paths_and_unlisted_art_are_never_registered(self):
        bad = ['/assets/battle-enhanced/source.nes', '/assets/battle-enhanced/source.state',
               '/assets/battle-enhanced/../secret.png', '/assets/battle-enhanced/sub/secret.png',
               '/assets/battle-enhanced/%2e%2e.png', '/assets/battle-enhanced/fake.svg',
               '/assets/battle-original/duelist-00.png', 'https://example.com/a.png']
        with tempfile.TemporaryDirectory() as folder:
            data = dict(schema='tk2-battle-enhanced-v1', scale=4,
                        entries=[{'path': p} for p in ['/assets/battle-enhanced/listed.png', *bad]])
            here, base = self.fixture(folder, data)
            (base/'unlisted.png').write_bytes(b'not public')
            result = server.enhanced_battle_static_assets(here)
            self.assertEqual(set(result), {'/assets/battle-enhanced/index.json', '/assets/battle-enhanced/listed.png'})

    def test_missing_and_malformed_manifests_cannot_scan_the_tree(self):
        for value in ('{', json.dumps({'schema': 'bad'}), json.dumps({'schema': 'tk2-battle-enhanced-v1', 'scale': 3})):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                here, base = self.fixture(folder)
                (base/'index.json').write_text(value)
                self.assertNotIn('/assets/battle-enhanced/listed.png', server.enhanced_battle_static_assets(here))
                (base/'index.json').unlink()
                self.assertNotIn('/assets/battle-enhanced/listed.png', server.enhanced_battle_static_assets(here))

    def test_replaced_symlinks_cannot_expose_original_sources_or_private_bytes(self):
        for where in ('assets', 'battle-enhanced', 'index.json', 'listed.png'):
            with self.subTest(where=where), tempfile.TemporaryDirectory() as folder:
                here, base = self.fixture(folder)
                before = server.enhanced_battle_static_assets(here)
                public = '/assets/battle-enhanced/' + ('index.json' if where == 'index.json' else 'listed.png')
                selected = here/'assets' if where == 'assets' else base if where == 'battle-enhanced' else base/where
                outside = Path(folder)/('moved-'+where)
                selected.rename(outside)
                selected.symlink_to(outside, target_is_directory=outside.is_dir())
                self.assertNotIn('/assets/battle-enhanced/listed.png', server.enhanced_battle_static_assets(here))
                with self.assertRaises(FileNotFoundError):
                    server.static_file_bytes(here, before[public][0])


if __name__ == '__main__':
    unittest.main()
