#!/usr/bin/env python3
"""Build a self-contained GitHub Pages game without rebuilding its catalogs.

Install the pinned core first: npm ci --prefix tools/web-runtime --ignore-scripts
Then: python3 -B game/build_web.py [--output build/web]
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
from html import escape, unescape
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'game'
PYODIDE_VERSION = '314.0.7'
APPROVED_PRODUCTION_REDIRECT = 'https://kai987.github.io/Three-Kingdoms2-King-mainland/'
PYODIDE_HASHES = {
    'pyodide.js': '3141b814715a72e59b51b1b18b9ceae5bf19f7c852417e431bb0a34feadf825c',
    'pyodide.mjs': '6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109',
    'pyodide.asm.mjs': 'f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635',
    'pyodide.asm.wasm': 'cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6',
    'python_stdlib.zip': 'fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a',
    'pyodide-lock.json': '5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010',
}
LICENSE_HASH = '1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5'
EXTRA_ASSETS = ('paths.js', 'browser-engine.js', 'browser-engine-worker.js')
BUILD_SCHEMA = 'tk2-static-build-v1'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def safe_read(root, name):
    """Only regular files inside a source root; never follow asset symlinks."""
    relative = PurePosixPath(name)
    if relative.is_absolute() or not relative.parts or '..' in relative.parts:
        raise ValueError('Invalid source path: ' + name)
    target = root
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError('Symlink cannot be published: ' + name)
    target.resolve().relative_to(root.resolve())
    return target.read_bytes()


def static_allowlist():
    """Reuse the server's literal allowlist and its validated manifest expansion.

    Parsing the assignment avoids starting an HTTP server or copying all of
    game/. A new allowed asset automatically joins the next static release.
    """
    source = HERE / 'serve.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    assignments = [node for node in main.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'static' for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError('Expected one explicit server static allowlist')
    assets = ast.literal_eval(assignments[0].value)
    spec = importlib.util.spec_from_file_location('tk2_static_allowlist', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for helper in ('portrait_static_assets', 'civil_portrait_static_assets',
                   'audio_effect_static_assets', 'original_ui_static_assets', 'equipment_icon_static_assets',
                   'battle_static_assets', 'enhanced_battle_static_assets'):
        assets.update(getattr(module, helper)())
    for name in EXTRA_ASSETS:
        assets['/' + name] = (name, 'text/javascript; charset=utf-8')
    return {('index.html' if url == '/' else url.lstrip('/')): name
            for url, (name, unused_mime) in assets.items()}


def rewrite_html(raw, assets=None):
    html = raw.decode('utf-8')
    html = re.sub(r'\b(src|href)=([\"\'])/(?!/)', r'\1=\2', html)
    first_script = html.find('  <script ')
    if first_script < 0:
        raise ValueError('Missing game script entry')
    worker = (assets or {}).get('browser-engine-worker.js')
    if worker is None:
        worker = safe_read(HERE, 'browser-engine-worker.js')
    html = (html[:first_script] + '  <script src="paths.js" defer></script>\n'
            + '  <script src="browser-engine.js" data-worker-sha256="' + sha256(worker)
            + '" defer></script>\n' + html[first_script:])

    def version_tag(match):
        tag = match[0]
        attribute = 'src' if match[1].lower() == 'script' else 'href'

        def version_url(found):
            value = urlsplit(unescape(found[2]))
            if value.scheme or value.netloc or not value.path:
                return found[0]
            relative = PurePosixPath(value.path)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Invalid HTML asset path: ' + value.path)
            name = relative.as_posix()
            content = assets.get(name) if assets is not None else safe_read(HERE, name)
            if content is None:
                return found[0]
            query = [(key, item) for key, item in parse_qsl(value.query, keep_blank_values=True)
                     if key != 'v']
            query.append(('v', sha256(content)))
            address = urlunsplit(('', '', value.path, urlencode(query), value.fragment))
            return attribute + '=' + found[1] + escape(address, quote=True) + found[1]

        tag = re.sub(r'\b' + attribute + r'\s*=\s*([\"\'])([^\"\']*)\1',
                     version_url, tag, flags=re.IGNORECASE)
        terrain = (assets or {}).get('assets/map-western-range.png')
        if (terrain is not None and match[1].lower() == 'script'
                and re.search(r'\bsrc\s*=\s*([\"\'])map-terrain\.js(?:[?#][^\"\']*)?\1',
                              tag, flags=re.IGNORECASE)):
            # The runtime image is loaded after HTML parsing. Tie its cache key
            # to this release's bitmap rather than the script's code version.
            tag = re.sub(r'\sdata-art-sha256\s*=\s*([\"\'])[^\"\']*\1', '', tag,
                         flags=re.IGNORECASE)
            tag = tag[:-1] + ' data-art-sha256="' + sha256(terrain) + '">'
        return tag

    html = re.sub(r'<(script|link)\b[^>]*>', version_tag, html, flags=re.IGNORECASE)
    return html.encode('utf-8')


def rewrite_css(raw, name):
    # Styles live next to index.html today; retain the correct relative font URL
    # if a later allowlisted stylesheet is in a subdirectory.
    prefix = '../' * len(PurePosixPath(name).parent.parts)
    return re.sub(rb'url\(([\"\']?)/(?!/)',
                  lambda match: b'url(' + match[1] + prefix.encode(), raw)


def put(output, name, raw):
    relative = PurePosixPath(name)
    if relative.is_absolute() or not relative.parts or '..' in relative.parts:
        raise ValueError('Invalid output path: ' + name)
    path = output / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def python_bundle(output):
    files = [(path.relative_to(ROOT).as_posix(), safe_read(ROOT, path.relative_to(ROOT).as_posix()))
             for path in sorted((ROOT / 'source/remake').rglob('*.py'))]
    files.append(('game/assets/map-presentation.json', safe_read(HERE, 'assets/map-presentation.json')))
    archive = output / 'runtime/python.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, raw in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, raw, compresslevel=9)
    return {'url': 'runtime/python.zip', 'sha256': sha256(archive.read_bytes())}


def runtime_catalogs(output):
    index = json.loads(safe_read(HERE, 'data/campaigns/index.json'))
    rows, paths = [], []
    for name in index['catalogs']:
        raw = safe_read(HERE, 'data/' + name)
        data = json.loads(raw)
        identity = data['id']
        if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', identity):
            raise ValueError('Invalid catalog identity')
        if any(row['id'] == identity for row in rows):
            raise ValueError('Duplicate catalog identity')
        url = f'runtime/catalogs/{identity}.json.gz'
        # Hash the exact original input, not JSON parsed and serialized again.
        # Catalog.sha256 and save import compatibility depend on those bytes.
        put(output, url, gzip.compress(raw, compresslevel=9, mtime=0))
        rows.append({'id': identity, 'url': url, 'path': '/tk2/game/data/' + name,
                     'sha256': sha256(raw), 'bytes': len(raw)})
        paths.append(HERE / 'data' / name)
    if not rows:
        raise ValueError('No campaign catalogs')
    sys.path.insert(0, str(ROOT / 'source'))
    from remake.session import CampaignSession
    previews = json_bytes(CampaignSession(paths)._scenario_previews())
    put(output, 'runtime/scenario-previews.json', previews)
    return rows, {'url': 'runtime/scenario-previews.json', 'sha256': sha256(previews)}


def copy_pyodide(output):
    base = ROOT / 'tools/web-runtime'
    package = base / 'node_modules/pyodide'
    try:
        installed = json.loads((package / 'package.json').read_text())['version']
    except FileNotFoundError:
        raise ValueError('Run npm ci --prefix tools/web-runtime --ignore-scripts first') from None
    if installed != PYODIDE_VERSION:
        raise ValueError('Incorrect Pyodide version')
    for name, expected in PYODIDE_HASHES.items():
        raw = safe_read(package, name)
        if sha256(raw) != expected:
            raise ValueError('Pinned Pyodide core hash mismatch: ' + name)
        put(output, 'vendor/pyodide/' + name, raw)
    license_raw = safe_read(base, 'LICENSE-PYODIDE')
    if sha256(license_raw) != LICENSE_HASH:
        raise ValueError('Pinned Pyodide license hash mismatch')
    put(output, 'vendor/pyodide/LICENSE', license_raw)


def write_cloud_config(output):
    sys.path.insert(0, str(ROOT / 'source'))
    from remake.cloud_config import public_config
    config = public_config(HERE / 'config/cloud-save-public.json')
    # This exact production URL was explicitly approved and added to the shared
    # project's redirect allowlist. Never infer an auth destination from the
    # browser, a build argument or the local development configuration.
    if config.get('enabled'):
        config['confirmationRedirectUrl'] = APPROVED_PRODUCTION_REDIRECT
    put(output, 'cloud-config.json', json_bytes(config))


def build(output):
    output = Path(output)
    if output.is_symlink():
        raise ValueError('Output cannot be a symlink')
    output = output.resolve()
    if output in ROOT.parents:
        raise ValueError('Output cannot replace a repository ancestor')
    if output == ROOT or any(output == protected or protected in output.parents
                             for protected in (HERE, ROOT / 'source', ROOT / '.git', ROOT / 'tools')):
        raise ValueError('Output cannot replace source or repository metadata')
    if output.exists() and any(output.iterdir()):
        marker = output / 'runtime/build.json'
        try:
            known = json.loads(marker.read_text())['schema'] == BUILD_SCHEMA
        except (OSError, ValueError, KeyError):
            known = False
        if not known:
            raise ValueError('Refusing to replace an unrecognized nonempty output directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='tk2-web-', dir=output.parent))
    try:
        # The displayed mountain-art map must contain the current water/roads,
        # rather than an older complete bitmap that hides source-map edits.
        subprocess.run([sys.executable, '-B', str(HERE / 'build_terrain_art.py'), '--check'],
                       cwd=ROOT, check=True, stdout=subprocess.PIPE)
        assets = {}
        for name, source in static_allowlist().items():
            raw = safe_read(HERE, source)
            if name.endswith('.css'):
                raw = rewrite_css(raw, name)
            assets[name] = raw
        assets['index.html'] = rewrite_html(assets['index.html'], assets)
        for name, raw in assets.items():
            put(staging, name, raw)
        commit = os.environ.get('GITHUB_SHA') or subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        copy_pyodide(staging)
        write_cloud_config(staging)
        catalogs, previews = runtime_catalogs(staging)
        initial_scenario = 'mainland184-02'
        if not any(row['id'] == initial_scenario for row in catalogs):
            raise ValueError('The default Yellow Turban campaign is required')
        manifest = {'schema': 'tk2-browser-engine-v1', 'pyodide_version': PYODIDE_VERSION,
                    'build_commit': commit,
                    'python_bundle': python_bundle(staging), 'previews': previews,
                    'catalogs': catalogs, 'initial_scenario': initial_scenario}
        put(staging, 'runtime/engine-manifest.json', json_bytes(manifest))
        put(staging, '.nojekyll', b'')
        files = {path.relative_to(staging).as_posix(): {'sha256': sha256(path.read_bytes()),
                                                     'bytes': path.stat().st_size}
                 for path in sorted(staging.rglob('*')) if path.is_file()}
        identity = {'schema': BUILD_SCHEMA, 'commit': commit, 'pyodide_version': PYODIDE_VERSION,
                    'files': files, 'content_sha256': sha256(json_bytes(files))}
        put(staging, 'runtime/build.json', json_bytes(identity))
        if output.exists():
            shutil.rmtree(output)
        staging.replace(output)
        return identity
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', '--out', type=Path, default=ROOT / 'build/web')
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({'output': str(args.output.resolve()), 'files': len(result['files']),
                      'bytes': sum(row['bytes'] for row in result['files'].values()),
                      'commit': result['commit'], 'content_sha256': result['content_sha256']}))


if __name__ == '__main__':
    main()
