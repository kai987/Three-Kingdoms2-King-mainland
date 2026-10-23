#!/usr/bin/env python3
"""Run every campaign unittest file once across deterministic CI shards.

Sorted file paths are dealt round-robin. No timing cache or test-name filter
can omit tests; every selected module is loaded by the standard unittest loader.
--list-only reads filenames without importing campaign modules or running tests.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / 'tests'
SOURCE = ROOT / 'source'


def discover_files(directory=TESTS):
    directory = Path(directory)
    return sorted(directory.rglob('test_remake_*.py'),
                  key=lambda path: path.relative_to(directory).as_posix())


def select_shard(files, shard, shards):
    if shards < 1 or not 1 <= shard <= shards:
        raise ValueError('Require --shards >= 1 and 1 <= --shard <= --shards')
    return list(files)[shard - 1::shards]


def load_suite(files, tests=TESTS, source=SOURCE):
    # Match unittest discovery's importable tests directory and retain the repo
    # root for test-time helpers. Individual existing modules may prepend source.
    for directory in (source, ROOT, tests):
        identity = str(Path(directory).resolve())
        if identity in sys.path:
            sys.path.remove(identity)
        sys.path.insert(0, identity)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for filename in files:
        relative = Path(filename).relative_to(tests).with_suffix('')
        module = '.'.join(relative.parts)
        # Handles module load_tests hooks and import errors in the same way as
        # unittest discovery; import failures remain failing tests, never skips.
        suite.addTests(loader.loadTestsFromName(module))
    return suite


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', required=True, type=int)
    parser.add_argument('--shards', required=True, type=int)
    parser.add_argument('--list-only', action='store_true')
    args = parser.parse_args(argv)
    files = discover_files()
    try:
        selected = select_shard(files, args.shard, args.shards)
    except ValueError as error:
        parser.error(str(error))
    if not selected:
        parser.error('This shard has no campaign test files; refusing an empty test run')
    summary = dict(backend=os.environ.get('MARCH_CORE_BACKEND', 'auto'),
                   shard=args.shard, shards=args.shards,
                   file_count=len(selected), all_file_count=len(files),
                   files=[path.relative_to(ROOT).as_posix() for path in selected])
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    if args.list_only:
        return 0
    suite = load_suite(selected)
    print(f'Campaign shard {args.shard}/{args.shards}: '
          f'{len(selected)} files, {suite.countTestCases()} cases', flush=True)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
