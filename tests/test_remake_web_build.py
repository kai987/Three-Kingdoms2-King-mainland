"""Static releases preserve catalog identity and expose only approved inputs."""
from pathlib import Path
import gzip
from html.parser import HTMLParser
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tk2_build_web', ROOT / 'game/build_web.py')
WEB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEB)


class WebBuildBoundaries(unittest.TestCase):
    def test_project_paths_are_relative_without_changing_external_urls(self):
        html = WEB.rewrite_html(b'<link href="/style.css">\n  <script src="/app.js" defer></script><a href="https://example.com/">link</a>')
        self.assertIn(b'href="style.css?v=', html)
        self.assertIn(b'src="app.js?v=', html)
        self.assertIn(b'https://example.com/', html)
        self.assertLess(html.index(b'paths.js'), html.index(b'browser-engine.js'))
        self.assertLess(html.index(b'browser-engine.js'), html.index(b'app.js'))
        self.assertEqual(WEB.rewrite_css(b"src:url('/assets/font.woff');x:url(https://x/)", 'style.css'),
                         b"src:url('assets/font.woff');x:url(https://x/)")

    def test_local_script_and_stylesheet_versions_hash_the_published_contents(self):
        assets = {'style.css': b'published-relative-css', 'app.js': b'current-app',
                  'paths.js': b'current-paths', 'browser-engine.js': b'current-engine',
                  'browser-engine-worker.js': b'current-worker'}
        raw = (b'<link href="/style.css?theme=pixel&amp;v=old#font">\n'
               b'<link href="https://external.example/theme.css">\n'
               b'  <script src="/app.js?v=old" defer></script>')
        rewritten = WEB.rewrite_html(raw, assets)
        self.assertIn(('href="style.css?theme=pixel&amp;v=' + WEB.sha256(assets['style.css'])
                       + '#font"').encode(), rewritten)
        for name in ('app.js', 'paths.js', 'browser-engine.js'):
            self.assertIn(('src="' + name + '?v=' + WEB.sha256(assets[name]) + '"').encode(), rewritten)
        self.assertIn(('data-worker-sha256="' + WEB.sha256(assets['browser-engine-worker.js'])
                       + '"').encode(), rewritten)
        self.assertIn(b'href="https://external.example/theme.css"', rewritten)
        self.assertNotIn(b'v=old', rewritten)
        with self.assertRaisesRegex(ValueError, 'Invalid HTML asset path'):
            WEB.rewrite_html(b'  <script src="/../private.js"></script>', assets)

    def test_safe_read_rejects_symlinks_and_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'target').write_bytes(b'public')
            (root / 'link').symlink_to(root / 'target')
            for path in ('link', '../target', '/target'):
                with self.assertRaises(ValueError):
                    WEB.safe_read(root, path)
            self.assertEqual(WEB.safe_read(root, 'target'), b'public')

    def test_terrain_image_cache_key_tracks_the_published_bitmap(self):
        assets = {'map-terrain.js': b'terrain-loader',
                  'assets/map-western-range.png': b'current-map-image',
                  'paths.js': b'paths', 'browser-engine.js': b'engine',
                  'browser-engine-worker.js': b'worker'}
        raw = b'  <script src="/map-terrain.js" data-art-sha256="stale" defer></script>'
        first = WEB.rewrite_html(raw, assets)
        assets['assets/map-western-range.png'] = b'updated-map-image'
        second = WEB.rewrite_html(raw, assets)
        self.assertNotEqual(first, second)
        self.assertIn(('data-art-sha256="' + WEB.sha256(b'updated-map-image') + '"').encode(), second)
        self.assertNotIn(b'data-art-sha256="stale"', second)

    def test_output_refuses_unrecognized_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'keep.txt').write_text('unrelated')
            with self.assertRaisesRegex(ValueError, 'unrecognized'):
                WEB.build(root)
            self.assertEqual((root / 'keep.txt').read_text(), 'unrelated')

    def test_failed_terrain_preflight_preserves_the_previous_release(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'release'
            (output / 'runtime').mkdir(parents=True)
            identity = json.dumps({'schema': WEB.BUILD_SCHEMA}).encode()
            (output / 'runtime/build.json').write_bytes(identity)
            (output / 'index.html').write_bytes(b'previous playable release')
            failure = WEB.subprocess.CalledProcessError(1, ['terrain-art', '--check'])
            with patch.object(WEB.subprocess, 'run', side_effect=failure):
                with self.assertRaises(WEB.subprocess.CalledProcessError):
                    WEB.build(output)
            self.assertEqual((output / 'runtime/build.json').read_bytes(), identity)
            self.assertEqual((output / 'index.html').read_bytes(), b'previous playable release')
            self.assertEqual(sorted(path.name for path in Path(folder).iterdir()), ['release'])

    def test_server_allowlist_does_not_publish_private_config_or_history(self):
        assets = WEB.static_allowlist()
        for required in ('app.js', 'paths.js', 'browser-engine-worker.js', 'wasm/march_core.wasm',
                         'locales/ui-ja.json', 'assets/map-western-range.png'):
            self.assertIn(required, assets)
        self.assertNotIn('config/cloud-save-public.json', assets)
        self.assertNotIn('data/campaigns/index.json', assets)
        self.assertFalse(any(name.startswith(('map-source/', 'art/', '.env')) for name in assets))


@unittest.skipUnless((ROOT / 'tools/web-runtime/node_modules/pyodide/package.json').is_file(),
                     'Install the pinned browser runtime to test the release artifact')
class WebReleaseArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='tk2-web-build-test-')
        cls.output = Path(cls.folder.name) / 'release'
        cls.before = {path: WEB.sha256(path.read_bytes())
                      for path in (ROOT / 'game/data/campaigns').glob('*.json')}
        WEB.build(cls.output)
        cls.manifest = json.loads((cls.output / 'runtime/engine-manifest.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_catalog_original_bytes_and_save_identity_remain_exact(self):
        rows = self.manifest['catalogs']
        self.assertEqual(len(rows), len(self.before) - 1)
        self.assertEqual(self.manifest['initial_scenario'], 'mainland184-02')
        for row in rows:
            original = ROOT / row['path'].removeprefix('/tk2/')
            raw = original.read_bytes()
            self.assertEqual(gzip.decompress((self.output / row['url']).read_bytes()), raw)
            self.assertEqual(WEB.sha256(raw), row['sha256'])
            self.assertEqual(len(raw), row['bytes'])
        self.assertEqual(self.before, {path: WEB.sha256(path.read_bytes()) for path in self.before})

    def test_python_paths_and_previews(self):
        with zipfile.ZipFile(self.output / self.manifest['python_bundle']['url']) as bundle:
            names = set(bundle.namelist())
            self.assertIn('source/remake/session.py', names)
            self.assertIn('source/remake/browser_runtime.py', names)
            self.assertIn('game/assets/map-presentation.json', names)
            self.assertFalse(any(name.endswith(('.pyc', '.nes')) or '/config/' in name for name in names))
        previews = json.loads((self.output / self.manifest['previews']['url']).read_text())
        self.assertEqual([row['id'] for row in previews], [row['id'] for row in self.manifest['catalogs']])
        self.assertTrue(all(row['initial_owners'] and row['faction_resources'] for row in previews))

    def test_publication_hashes_and_cloud_callback_boundaries(self):
        identity = json.loads((self.output / 'runtime/build.json').read_text())
        self.assertEqual(self.manifest['build_commit'], identity['commit'])
        for name, row in identity['files'].items():
            raw = (self.output / name).read_bytes()
            self.assertEqual(row, {'sha256': WEB.sha256(raw), 'bytes': len(raw)}, name)
        self.assertEqual(identity['content_sha256'], WEB.sha256(WEB.json_bytes(identity['files'])))
        cloud = json.loads((self.output / 'cloud-config.json').read_text())
        if cloud.get('enabled'):
            self.assertEqual(cloud['confirmationRedirectUrl'],
                             'https://kai987.github.io/Three-Kingdoms2-King-mainland/')
        else:
            self.assertNotIn('confirmationRedirectUrl', cloud)
        self.assertNotIn('localhost', json.dumps(cloud))
        self.assertNotIn('127.0.0.1', json.dumps(cloud))
        self.assertLessEqual(set(cloud), {'enabled', 'url', 'publishableKey', 'slots',
                                         'confirmationRedirectUrl'})
        self.assertFalse((self.output / 'config/cloud-save-public.json').exists())
        for name, expected in WEB.PYODIDE_HASHES.items():
            self.assertEqual(WEB.sha256((self.output / 'vendor/pyodide' / name).read_bytes()), expected)
        self.assertTrue((self.output / '.nojekyll').exists())

    def test_html_asset_versions_match_the_exact_release_files(self):
        tags = []

        class Entries(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'link'):
                    tags.append((tag, dict(attrs)))

        Entries().feed((self.output / 'index.html').read_text())
        for tag, attrs in tags:
            address = WEB.urlsplit(attrs['src' if tag == 'script' else 'href'])
            if address.scheme or address.netloc:
                continue
            self.assertFalse(address.path.startswith('/'))
            self.assertEqual(dict(WEB.parse_qsl(address.query))['v'],
                             WEB.sha256((self.output / address.path).read_bytes()))
            if address.path == 'browser-engine.js':
                self.assertEqual(attrs['data-worker-sha256'],
                                 WEB.sha256((self.output / 'browser-engine-worker.js').read_bytes()))


if __name__ == '__main__':
    unittest.main()
