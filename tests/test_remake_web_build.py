"""Static releases preserve catalog identity and expose only approved inputs."""
from pathlib import Path
from copy import deepcopy
import gzip
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import subprocess
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

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


class SoldierCombatStaticBoundaries(unittest.TestCase):
    PREFIX = '/assets/soldier-combat-actions-v1/'

    def fixture(self, folder):
        here = Path(folder) / 'game'
        base = here / self.PREFIX.lstrip('/')
        base.mkdir(parents=True)
        def chunk(kind, value):
            return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value) & 0xffffffff)
        png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 64, 8, 6, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress((b'\0' + bytes(256 * 4)) * 64)) + chunk(b'IEND', b''))
        types = {}
        for kind in ('infantry', 'archer', 'cavalry', 'general'):
            types[kind] = {}
            for action in (('melee', 'ranged') if kind == 'archer' else ('melee',)):
                types[kind][action] = {}
                phases = ('ready', 'windup', 'strike', 'recover') if action == 'melee' else ('nock', 'draw', 'release', 'recover')
                for side in ('friendly', 'enemy'):
                    name = f'{kind}-{action}-{side}.png'
                    (base / name).write_bytes(png)
                    types[kind][action][side] = dict(path=self.PREFIX + name, width=256, height=64,
                        facing='right', anchor=dict(x=8, y=16), sha256=hashlib.sha256(png).hexdigest(),
                        frames=[dict(phase=phase, source_rect=[n * 64, 0, 64, 64]) for n, phase in enumerate(phases)])
        proof = json.dumps(dict(schema='tk2-soldier-combat-actions-provenance-v1', originals_retained=True)).encode()
        (base / 'provenance.json').write_bytes(proof)
        data = dict(schema='tk2-soldier-combat-actions-v1', scale=4, logical_size=[16, 16],
                    frame_size=[64, 64], frames_per_action=4, originals_retained=True, types=types,
                    provenance=dict(path=self.PREFIX + 'provenance.json', sha256=hashlib.sha256(proof).hexdigest()))
        (base / 'index.json').write_text(json.dumps(data))
        return here, base, data

    def test_literal_ten_atlases_and_provenance_are_the_only_publishable_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            here, base, data = self.fixture(folder)
            (base / 'old-save.json').write_text('private')
            (base / 'source.png').write_bytes(b'private study')
            result = SERVER.soldier_combat_static_assets(here)
            expected = {self.PREFIX + name for name in ('index.json', 'provenance.json')}
            expected.update(row['path'] for actions in data['types'].values()
                            for sides in actions.values() for row in sides.values())
            self.assertEqual(len(expected), 12)
            self.assertEqual(set(result), expected)
            self.assertTrue(all(path.lstrip('/') == value[0] for path, value in result.items()))

    def test_missing_corrupt_and_rehashed_wrong_size_png_fail_closed(self):
        for mutation in ('missing', 'corrupt', 'wrong-size'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                here, base, data = self.fixture(folder)
                target = base / 'infantry-melee-friendly.png'
                if mutation == 'missing':
                    target.unlink()
                elif mutation == 'corrupt':
                    target.write_bytes(b'changed pixels')
                else:
                    raw = bytearray(target.read_bytes())
                    raw[16:20] = struct.pack('>I', 255)
                    target.write_bytes(raw)
                    data['types']['infantry']['melee']['friendly']['sha256'] = hashlib.sha256(raw).hexdigest()
                    (base / 'index.json').write_text(json.dumps(data))
                self.assertEqual(SERVER.soldier_combat_static_assets(here), {})

    def test_forged_action_geometry_phase_or_path_cannot_widen_the_allowlist(self):
        changes = [lambda d: d.update(schema='wrong'), lambda d: d.update(scale=2),
                   lambda d: d.update(logical_size=[32, 32]), lambda d: d.update(frames_per_action=8),
                   lambda d: d['types']['infantry'].update(ranged=deepcopy(d['types']['archer']['ranged'])),
                   lambda d: d['types']['general']['melee'].pop('enemy'),
                   lambda d: d['types']['archer']['ranged']['friendly']['frames'][2].update(phase='windup'),
                   lambda d: d['types']['infantry']['melee']['friendly']['frames'][1].update(source_rect=[0, 0, 64, 64]),
                   lambda d: d['types']['infantry']['melee']['friendly'].update(path='/etc/passwd'),
                   lambda d: d['types']['infantry']['melee']['friendly'].update(path=self.PREFIX + '../private.png'),
                   lambda d: d['provenance'].update(path=self.PREFIX + 'old-save.json'),
                   lambda d: d.update(originals_retained=False)]
        for number, change in enumerate(changes):
            with self.subTest(change=number), tempfile.TemporaryDirectory() as folder:
                here, base, data = self.fixture(folder)
                change(data)
                (base / 'index.json').write_text(json.dumps(data))
                self.assertEqual(SERVER.soldier_combat_static_assets(here), {})

    def test_symlinked_asset_parents_manifest_provenance_and_atlas_are_refused(self):
        for entry in ('assets', 'soldier-combat-actions-v1', 'index.json', 'provenance.json', 'infantry-melee-friendly.png'):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as folder:
                here, base, data = self.fixture(folder)
                target = here / 'assets' if entry == 'assets' else base if entry == 'soldier-combat-actions-v1' else base / entry
                original = target.with_name(target.name + '.private')
                target.rename(original)
                target.symlink_to(original, target_is_directory=original.is_dir())
                self.assertEqual(SERVER.soldier_combat_static_assets(here), {})

    def test_current_shipped_manifest_is_in_static_release_but_studies_are_private(self):
        published = SERVER.soldier_combat_static_assets(ROOT / 'game')
        self.assertEqual(len(published), 12)
        built = WEB.static_allowlist()
        self.assertEqual({name for name in built if name.startswith(self.PREFIX.lstrip('/'))},
                         {name.lstrip('/') for name in published})
        self.assertFalse(any(name.startswith('art/') for name in built))


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
            self.assertIn('source/remake/troop_types.py', names)
            self.assertIn('game/assets/map-presentation.json', names)
            for name in ('game/assets/battlefields/index.json',
                         'game/config/battlefield-city-bindings.json',
                         'game/config/references/original-battle-tactics-v1.json',
                         'game/config/references/officer-troop-types-v1.json'):
                self.assertIn(name,names,'The actual WASM rules need the original tactical data')
            public_rules={'game/config/battlefield-city-bindings.json',
                          'game/config/references/original-battle-tactics-v1.json',
                          'game/config/references/officer-troop-types-v1.json'}
            troop_policy='game/config/references/officer-troop-types-v1.json'
            self.assertEqual(bundle.read(troop_policy),(ROOT/troop_policy).read_bytes(),
                             'WASM must receive the same reviewed troop-type policy as Python')
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
