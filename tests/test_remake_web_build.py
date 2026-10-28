"""Static releases preserve catalog identity and expose only approved inputs."""
from pathlib import Path
import gzip
from html.parser import HTMLParser
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tk2_build_web', ROOT / 'game/build_web.py')
WEB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEB)
SERVER_SPEC = importlib.util.spec_from_file_location('tk2_battlefield_asset_server', ROOT / 'game/serve.py')
SERVER = importlib.util.module_from_spec(SERVER_SPEC)
SERVER_SPEC.loader.exec_module(SERVER)


class BattlefieldStaticBoundaries(unittest.TestCase):
    def fixture(self, folder):
        here = Path(folder) / 'game'
        base = here / 'assets/battlefields'
        base.mkdir(parents=True)
        maps = {ident: dict(id=ident, path=f'/assets/battlefields/{ident}.png')
                for ident in ('original-00', 'original-29')}
        data = dict(schema='tk2-original-battlefields-v1', maps=maps)
        (base / 'index.json').write_text(json.dumps(data))
        for ident in maps:
            (base / (ident + '.png')).write_bytes(b'public fixture')
        return here, base, data

    def test_battlefield_allowlist_is_exactly_the_shipped_index_and_thirty_pngs(self):
        static = SERVER.battlefield_static_assets(ROOT / 'game')
        expected = {'/assets/battlefields/index.json'} | {
            f'/assets/battlefields/original-{index:02d}.png' for index in range(30)}
        self.assertEqual(set(static), expected)
        for path, (relative, mime) in static.items():
            self.assertEqual(relative, path.lstrip('/'))
            self.assertEqual(mime, 'image/png' if path.endswith('.png')
                             else 'application/json; charset=utf-8')
        published = WEB.static_allowlist()
        self.assertEqual({path for path in published if path.startswith('assets/battlefields/')},
                         {path.lstrip('/') for path in expected})
        self.assertIn('battlefields.js', published)
        self.assertIn('config/battlefield-city-bindings.json', published)

    def test_unlisted_out_of_range_and_forged_manifest_paths_are_never_published(self):
        invalid = ['/assets/battlefields/original-30.png', '/assets/battlefields/original-99.png',
                   '/assets/battlefields/original-00.state', '/assets/battlefields/source.nes',
                   '/assets/battlefields/../outside.png', '/assets/battlefields/sub/inside.png',
                   '/assets/battlefields/%2e%2e/outside.png', '/assets/other.png',
                   'https://example.invalid/source.png']
        with tempfile.TemporaryDirectory() as folder:
            here, base, data = self.fixture(folder)
            for path in invalid:
                # An attacker cannot replace a known row's exact fixed path.
                data['maps']['original-00']['path'] = path
                data['maps']['original-30'] = dict(id='original-30', path=path)
                (base / 'index.json').write_text(json.dumps(data))
                for name in ('original-30.png', 'original-99.png', 'source.nes', 'unlisted.png'):
                    (base / name).write_bytes(b'private or unlisted')
                with self.subTest(path=path):
                    self.assertEqual(set(SERVER.battlefield_static_assets(here)), {
                        '/assets/battlefields/index.json', '/assets/battlefields/original-29.png'})

    def test_missing_or_malformed_metadata_and_missing_png_do_not_scan_the_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            here, base, data = self.fixture(folder)
            (base / 'original-00.png').unlink()
            (base / 'unlisted.png').write_bytes(b'not public')
            self.assertEqual(set(SERVER.battlefield_static_assets(here)), {
                '/assets/battlefields/index.json', '/assets/battlefields/original-29.png'})
            for raw in ('{', '[]', '{}', json.dumps(dict(schema='wrong', maps=data['maps'])),
                        json.dumps(dict(schema='tk2-original-battlefields-v1', maps=[]))):
                with self.subTest(raw=raw):
                    (base / 'index.json').write_text(raw)
                    self.assertEqual(set(SERVER.battlefield_static_assets(here)),
                                     {'/assets/battlefields/index.json'})
            (base / 'index.json').unlink()
            self.assertEqual(set(SERVER.battlefield_static_assets(here)),
                             {'/assets/battlefields/index.json'})

    def test_symlinked_asset_parents_metadata_and_png_are_refused(self):
        for entry in ('assets', 'battlefields', 'index.json', 'original-00.png'):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as folder:
                here, base, data = self.fixture(folder)
                path = here / 'assets' if entry == 'assets' else base if entry == 'battlefields' else base / entry
                original = path.with_name(path.name + '.private')
                path.rename(original)
                path.symlink_to(original, target_is_directory=original.is_dir())
                result = SERVER.battlefield_static_assets(here)
                expected = {} if entry != 'original-00.png' else {
                    '/assets/battlefields/index.json': ('assets/battlefields/index.json', 'application/json; charset=utf-8'),
                    '/assets/battlefields/original-29.png': ('assets/battlefields/original-29.png', 'image/png')}
                self.assertEqual(result, expected)


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
            for name in ('game/assets/battlefields/index.json',
                         'game/config/battlefield-city-bindings.json',
                         'game/config/references/original-battle-tactics-v1.json'):
                self.assertIn(name,names,'The actual WASM rules need the original tactical data')
            public_rules={'game/config/battlefield-city-bindings.json',
                          'game/config/references/original-battle-tactics-v1.json'}
            self.assertFalse(any(name.endswith(('.pyc', '.nes'))
                or '/config/' in name and name not in public_rules for name in names))
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

    def test_battlefield_art_module_and_bindings_work_under_a_pages_project_prefix(self):
        expected = {'assets/battlefields/index.json'} | {
            f'assets/battlefields/original-{index:02d}.png' for index in range(30)}
        actual = {path.relative_to(self.output).as_posix()
                  for path in (self.output / 'assets/battlefields').rglob('*') if path.is_file()}
        self.assertEqual(actual, expected)
        for name in expected | {'battlefields.js', 'config/battlefield-city-bindings.json'}:
            self.assertEqual((self.output / name).read_bytes(), (ROOT / 'game' / name).read_bytes())
        html = (self.output / 'index.html').read_text()
        self.assertIn('src="battlefields.js?v=', html)
        self.assertNotIn('src="/battlefields.js', html)
        # Execute the actual published loader and path shim. The fake transport
        # only serves files below the project prefix, just like a Pages project.
        script = r'''
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const output=process.argv[1],prefix='/Three-Kingdoms2-King-mainland/',requests=[];
const window={document:{currentScript:{src:'https://example.invalid'+prefix+'paths.js?v=release'}}};
const context=vm.createContext({window,URL,console,setTimeout,clearTimeout,AbortController});
vm.runInContext(fs.readFileSync(path.join(output,'paths.js'),'utf8'),context);
window.fetch=async(address,options)=>{
 assert.equal(options.credentials,'same-origin');assert.ok(address.startsWith(prefix),address);requests.push(address);
 const relative=address.slice(prefix.length);assert.ok(!relative.includes('..'));
 const file=path.join(output,relative);return{ok:fs.existsSync(file),text:async()=>fs.readFileSync(file,'utf8')};
};
vm.runInContext(fs.readFileSync(path.join(output,'battlefields.js'),'utf8'),context);
(async()=>{
 const client=window.GameBattlefields;assert.ok(await client.load());assert.equal(client.status,'ready');
 assert.deepEqual(requests.sort(),[prefix+'assets/battlefields/index.json',prefix+'config/battlefield-city-bindings.json'].sort());
 for(const [city,binding]of Object.entries(client.bindings.cities)){
  const selected=client.resolve(city);assert.equal(selected.field.id,binding.map_id);
  const target=window.GamePaths.asset(selected.field.path);assert.ok(target.startsWith(prefix));
  assert.ok(fs.readFileSync(path.join(output,target.slice(prefix.length))).length>0);
 }
 console.log('published battlefield assets resolve below the Pages project prefix');
})().catch(error=>{console.error(error);process.exitCode=1});
'''
        result = subprocess.run(['node', '-e', script, str(self.output)], cwd=ROOT,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('published battlefield assets resolve below the Pages project prefix', result.stdout)


if __name__ == '__main__':
    unittest.main()
