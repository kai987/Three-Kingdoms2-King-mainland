#!/usr/bin/env python3
"""Seal a small, exact-allowlist v23 supplement without changing v22.

Old evidence and the user's ROM remain external pinned inputs. This supplement
contains readable source, validators and new evidence; the full ROM byte source
and native binaries are deliberately outside its manifest.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, os, tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase23'
BASE_AUDIT = 'ca94229cff060e16b25f8f3e92eb752a94121af730ae70d114ce4ddf3a6d8eb8'
BASE_ZIP = '9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
GROUPS = ('source_and_validator_sha256', 'artifact_and_dependency_sha256')


def digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return digest(stream)


def allowed(path):
    parts = path.relative_to(ROOT).parts
    return (not any(p.startswith('exploratory') for p in parts)
            and not set(parts) & {'.git', '.toolchain', '.venv', '.venv-trace', 'node_modules', '__pycache__'}
            and path.name not in ('.DS_Store', 'package-receipt.json')
            and path.suffix not in ('.pyc', '.pyo', '.nes', '.dylib', '.zip'))


def main():
    audit_path = OUT / 'verification.json'
    audit = json.loads(audit_path.read_text())
    assert audit['status'] == 'passed'
    manifest = json.loads((OUT / 'delivery-manifest.json').read_text())
    base = ROOT / manifest['base_archive']['path']
    assert sha(base) == BASE_ZIP
    assert sha(ROOT / manifest['base_audit']['path']) == BASE_AUDIT
    assert not any(manifest[k] for k in ('original_ROM_included', 'rebuilt_ROM_included',
                                        'full_ROM_byte_source_included', 'canonical_v22_archive_replaced'))
    destination = ROOT / 'build/三国志2超级版-逆向分析-v23增量.zip'
    assert not destination.exists(), 'A frozen v23 supplement must never be overwritten'
    files = [ROOT / name for name in manifest['include_files']]
    for name in manifest['include_roots']:
        files.extend(p for p in (ROOT / name).rglob('*') if p.is_file() and allowed(p))
    assert all(p.is_file() and not p.is_symlink() and allowed(p) for p in files)
    expected = {str(p.relative_to(ROOT)): p for p in files}
    assert len(files) == len(expected)
    assert all(not n.startswith(('source/byte-source/', 'build/', '.toolchain/')) for n in expected)
    pins = {}
    for group in GROUPS:
        for name, pin in audit[group].items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert len(pin) == 64 and sha(ROOT / name) == pin, ('Stale audit', name)
            if name in pins:
                assert pins[name] == pin
            pins[name] = pin
    audit_sha = sha(audit_path)
    fd, temporary_name = tempfile.mkstemp(prefix='.phase23-incremental-', suffix='.zip', dir=ROOT / 'build')
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with ZipFile(temporary, 'w', compression=ZIP_DEFLATED, compresslevel=6) as archive:
            for name, path in sorted(expected.items()):
                archive.write(path, name)
        with ZipFile(temporary) as archive:
            assert set(archive.namelist()) == set(expected) and len(archive.namelist()) == len(expected)
            assert archive.testzip() is None
            for name, path in expected.items():
                with archive.open(name) as stream:
                    assert digest(stream) == sha(path), name
            for name, pin in pins.items():
                if name in expected:
                    with archive.open(name) as stream:
                        assert digest(stream) == pin, name
            assert hashlib.sha256(archive.read('analysis/phase23/verification.json')).hexdigest() == audit_sha
            with tempfile.TemporaryDirectory(prefix='three-kingdoms-phase23-extract-') as directory:
                for name, path in sorted(expected.items()):
                    assert sha(archive.extract(name, directory)) == sha(path), name
        assert sha(audit_path) == audit_sha and sha(base) == BASE_ZIP
        assert sha(ROOT / manifest['base_audit']['path']) == BASE_AUDIT
        for name, pin in pins.items():
            assert sha(ROOT / name) == pin, ('Changed during packaging', name)
        os.link(temporary, destination)
        assert sha(destination) == sha(temporary)
    finally:
        if temporary.exists():
            temporary.unlink()
    receipt = dict(schema='phase23-postZIP-incremental-receipt-v1', status='passed', version=23,
                   path=str(destination), sha256=sha(destination), archive_bytes=destination.stat().st_size,
                   file_count=len(expected), CRC_check='passed', exact_allowlist_check='passed',
                   all_file_byte_parity_checks=len(expected), all_file_extraction_checks=len(expected),
                   readable_source_file_checks=sum(n.startswith('source/') for n in expected),
                   included_dependency_pins=sum(n in expected for n in pins),
                   external_dependency_pins=sum(n not in expected for n in pins),
                   base_archive_preserved_sha256=sha(base), base_audit_preserved_sha256=BASE_AUDIT,
                   phase23_audit_sha256=audit_sha, canonical_v22_archive_replaced=False,
                   original_ROM_included=False, rebuilt_ROM_included=False,
                   full_ROM_byte_source_included=False, toolchain_included=False,
                   validator_path='scripts/package_phase23_incremental.py',
                   validator_sha256=sha(Path(__file__)), package_receipt_excluded_from_archive=True)
    (OUT / 'package-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
