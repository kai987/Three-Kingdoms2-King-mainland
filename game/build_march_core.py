#!/usr/bin/env python3
"""Reproducibly build the shared marching core; no campaign data is rewritten."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CRATE = ROOT / 'crates' / 'march-core'
TARGET = ROOT / 'build' / 'march-core-target'


def run(*args):
    env = dict(os.environ)
    cargo_home = Path(env.get('CARGO_HOME', Path.home() / '.cargo')).resolve()
    env.pop('RUSTFLAGS', None)
    env['CARGO_ENCODED_RUSTFLAGS'] = '\x1f'.join((f'--remap-path-prefix={ROOT}=/workspace',
                                                 f'--remap-path-prefix={cargo_home}=/cargo'))
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def replace_bytes(path, content, mode=0o644):
    # Keep already-running native hosts and HTTP readers on a complete old file.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + '.', delete=False) as output:
        temporary = Path(output.name)
        output.write(content)
    try:
        if mode is not None:
            temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify source/artifact integrity; require byte equality on the recorded build host')
    args = parser.parse_args()
    compiler = subprocess.check_output(['rustc', '-vV'], text=True)
    version = next(line.split(': ', 1)[1] for line in compiler.splitlines() if line.startswith('release: '))
    host = next(line.split(': ', 1)[1] for line in compiler.splitlines() if line.startswith('host: '))
    if version != '1.93.0':
        raise SystemExit('Use Rust1.93.0 for reproducible marching artifacts')
    common = ('--manifest-path', str(CRATE / 'Cargo.toml'), '--target-dir', str(TARGET), '--locked', '--release')
    run('cargo', 'build', *common)
    suffix = 'libmarch_core.dylib' if sys.platform == 'darwin' else 'march_core.dll' if sys.platform == 'win32' else 'libmarch_core.so'
    native = ROOT / 'build' / 'march-core'
    native.mkdir(parents=True, exist_ok=True)
    for name in (suffix, 'march-core-json.exe' if sys.platform == 'win32' else 'march-core-json'):
        origin = TARGET / 'release' / name
        replace_bytes(native / name, origin.read_bytes(), origin.stat().st_mode)
    run('cargo', 'build', *common, '--target', 'wasm32-unknown-unknown', '--lib')
    binary = (TARGET / 'wasm32-unknown-unknown' / 'release' / 'march_core.wasm').read_bytes()
    manifest = dict(abi=1, crate='march-core', rust='1.93.0', target='wasm32-unknown-unknown',
                    build_host=host, builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    file='march_core.wasm', bytes=len(binary), sha256=hashlib.sha256(binary).hexdigest(),
                    sources_sha256={str(p.relative_to(CRATE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted([CRATE / 'Cargo.toml', CRATE / 'Cargo.lock'] +
                                                    list((CRATE / 'src').rglob('*.rs')) +
                                                    list((CRATE / 'tests').rglob('*.rs')))})
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    output = ROOT / 'game' / 'wasm'
    if args.check:
        committed = (output / 'march_core.wasm').read_bytes()
        recorded = json.loads((output / 'manifest.json').read_bytes())
        if len(committed) != recorded.get('bytes') or hashlib.sha256(committed).hexdigest() != recorded.get('sha256'):
            raise SystemExit('Committed marching WASM does not match its integrity manifest')
        portable = set(manifest) - {'build_host', 'bytes', 'sha256'}
        if set(recorded) != set(manifest) or any(recorded[key] != manifest[key] for key in portable):
            raise SystemExit('Marching sources/toolchain differ from the committed artifact manifest')
        if recorded['build_host'] == host:
            if committed != binary or (output / 'manifest.json').read_bytes() != encoded:
                raise SystemExit('Same-host marching rebuild is not byte-identical')
        else:
            print(json.dumps(dict(cross_host=True, recorded_host=recorded['build_host'], build_host=host,
                                  committed_sha256=recorded['sha256'], rebuilt_sha256=manifest['sha256'],
                                  next_check='Run parity against BOTH committed and rebuilt WASM')))
    else:
        output.mkdir(parents=True, exist_ok=True)
        replace_bytes(output / 'march_core.wasm', binary)
        replace_bytes(output / 'manifest.json', encoded)
    print(json.dumps(dict(native=str(native / suffix), wasm_bytes=len(binary), sha256=manifest['sha256'])))


if __name__ == '__main__':
    main()
