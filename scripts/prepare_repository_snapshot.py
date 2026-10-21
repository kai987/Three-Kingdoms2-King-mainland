#!/usr/bin/env python3
"""List the portable Git delivery without deleting or rewriting frozen evidence.

Large native traces, ROM bytes, toolchains and sealed ZIPs remain local. The
explicit list is also suitable for `git add -f --pathspec-from-file=...`.
"""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
STATIC_TYPES = {'.json', '.md', '.csv', '.py', '.c', '.h', '.asm', '.patch',
                '.inc', '.txt', '.cpp', '.hpp', '.common'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    DOCS.mkdir(exist_ok=True)
    chosen = set()
    omitted_static = []
    local_groups = defaultdict(lambda: {'files': 0, 'bytes': 0})
    for base, dirs, files in os.walk(ROOT / 'analysis'):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for name in files:
            path = Path(base) / name
            rel = path.relative_to(ROOT)
            size = path.stat().st_size
            is_trace = any(p.startswith(('runtime', 'exploratory', 'ancestry',
                                        'portal-metadata', 'native', 'frames'))
                           for p in rel.parts[1:-1])
            local_only = bool(set(rel.parts) & {'assets', 'raw', 'rom', 'trace', 'byte-source'})
            include = (path.suffix == '.md' or
                       (not is_trace and not local_only and
                        path.suffix in STATIC_TYPES and size <= 2 * 1024**2))
            if include:
                chosen.add(rel.as_posix())
            else:
                group = local_groups[rel.parts[1]]
                group['files'] += 1
                group['bytes'] += size
                if not is_trace and not local_only and path.suffix in STATIC_TYPES:
                    omitted_static.append({'path': rel.as_posix(), 'bytes': size,
                                           'sha256': sha(path), 'reason': 'large_static_evidence_retained_locally'})

    for folder in ('.github', 'source/recovered', 'source/readable_c', 'source/remake',
                   'tests', 'game', 'scripts', 'expansion', 'docs'):
        for base, dirs, files in os.walk(ROOT / folder, followlinks=False):
            dirs[:] = [d for d in dirs if d not in {'node_modules', '__pycache__', '.git'}
                       and not (Path(base) / d).is_symlink()]
            for name in files:
                path = Path(base) / name
                if (not path.is_symlink() and name != '.DS_Store' and
                        path.suffix not in {'.pyc', '.pyo'}):
                    chosen.add(path.relative_to(ROOT).as_posix())
    chosen.update({'README.md', 'LICENSE', '.gitignore', '.gitattributes',
                   'requirements.txt', 'source/README.md'})
    for path in (ROOT / 'outputs').rglob('*'):
        if path.is_file() and (path.suffix == '.xlsx' or path.name in {
                'workbook-validation.json', 'workbook-remake-validation.json'}):
            chosen.add(path.relative_to(ROOT).as_posix())

    inventory = {
        'schema': 'source-publication-v1',
        'scope': 'recovered source, selected evidence, v42 map and independent96-city remake campaign',
        'independent_remake_runtime_added': True,
        'raw_evidence_deleted': False,
        'game_runtime_modified': False,
        'original_rom_included': False,
        'full_rom_byte_source_included': False,
        'historical_frozen_archives_retained': True,
        'large_static_evidence_retained_locally': sorted(omitted_static, key=lambda x: x['path']),
        'other_local_analysis_files_by_directory': dict(sorted(local_groups.items())),
    }
    (DOCS / 'publication-inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    chosen.update({'docs/repository-files.txt', 'docs/publication-inventory.json'})
    for name in chosen:
        path = ROOT / name
        assert path.is_file() or name == 'docs/repository-files.txt', name
        assert not path.is_symlink(), name
        assert not name.startswith(('source/byte-source/', 'build/', '.toolchain/', 'tools/rea/')), name
        assert not set(Path(name).parts) & {'node_modules', '__pycache__', '.git'}, name
    (DOCS / 'repository-files.txt').write_text('\n'.join(sorted(chosen)) + '\n')
    print(json.dumps({'files': len(chosen),
                      'bytes': sum((ROOT / name).stat().st_size for name in chosen),
                      'large_static_files_local': len(omitted_static)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
