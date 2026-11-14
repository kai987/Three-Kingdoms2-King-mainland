#!/usr/bin/env python3
"""Run every campaign unittest file once across deterministic CI shards.

The CI backends use reviewed module timings. Missing timings affect scheduling
only; every selected module is loaded by the standard unittest loader.
--list-only reads filenames without importing campaign modules or running tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter
import unittest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / 'tests'
SOURCE = ROOT / 'source'
REGISTRY = ROOT / 'tools/ci/test-groups.json'
DURATIONS = ROOT / 'tools/ci/campaign-durations.json'
GROUPS = frozenset(('boot', 'audio', 'map', 'scenarios', 'people', 'economy', 'logistics', 'battle', 'cloud', 'save', 'portraits'))
TIERS = frozenset(('global', 'related', 'compatibility', 'full'))
SHARD_COUNT = 6
BACKENDS = ('python', 'rust')
UNMEASURED_MS = 60_000


def discover_files(directory=TESTS):
    directory = Path(directory)
    return sorted(directory.rglob('test_remake_*.py'),
                  key=lambda path: path.relative_to(directory).as_posix())


def load_registry(path=REGISTRY, tests=TESTS, root=ROOT):
    """Closed explicit inventory: new/stale files fail before any test import."""
    raw = Path(path).read_bytes()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate Python test registry key: ' + key)
            result[key] = value
        return result
    document = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(document, dict) or document.get('schema') != 'tk2-ci-python-groups-v1' or not isinstance(document.get('modules'), dict):
        raise ValueError('Invalid Python test registry')
    modules = document['modules']
    for name, row in modules.items():
        relative = Path(name)
        if (not isinstance(name, str) or relative.is_absolute() or '..' in relative.parts
                or not name.startswith('tests/') or not relative.name.startswith('test_remake_')
                or relative.suffix != '.py' or not isinstance(row, dict)
                or row.get('tier') not in TIERS):
            raise ValueError(f'Invalid registered Python module: {name}')
        groups = row.get('groups', [])
        if (not isinstance(groups, list) or any(not isinstance(group, str) for group in groups)
                or len(groups) != len(set(groups))
                or not set(groups) <= GROUPS or row['tier'] == 'related' and not groups):
            raise ValueError(f'Invalid Python groups: {name}')
        identities = row.get('scenario_ids', [])
        if not isinstance(identities, list) or any(not isinstance(value, str) for value in identities):
            raise ValueError(f'Invalid Python scenario selection: {name}')
    actual = {path.relative_to(root).as_posix() for path in discover_files(tests)}
    if actual != set(modules):
        unregistered = sorted(actual - set(modules))
        missing = sorted(set(modules) - actual)
        raise ValueError(f'Python test inventory differs: unregistered={unregistered}; missing={missing}')
    return document, hashlib.sha256(raw).hexdigest()


def select_shard(files, shard, shards):
    if shards < 1 or not 1 <= shard <= shards:
        raise ValueError('Require --shards >= 1 and 1 <= --shard <= --shards')
    return list(files)[shard - 1::shards]


def load_durations(backend, path=DURATIONS):
    value = json.loads(Path(path).read_text())
    if (not isinstance(value, dict) or value.get('schema') != 'tk2-campaign-module-durations-v1'
            or set(value.get('backends', {})) != set(BACKENDS)):
        raise ValueError('Invalid campaign module timings')
    timings = value['backends'][backend]
    if not isinstance(timings, dict) or not timings or any(
            type(ms) is not int or not 0 < ms <= 40 * 60_000 for ms in timings.values()):
        raise ValueError('Campaign module timings must be positive bounded milliseconds')
    return {ROOT / path: ms for path, ms in timings.items()}


def partition_modules(files, shards, *, durations=None):
    """Validate a closed partition before any test module is imported."""
    complete = list(files)
    if len(complete) != len(set(complete)):
        raise ValueError('Duplicate campaign test file in the shard inventory')
    if durations is None:
        groups = [select_shard(complete, index, shards) for index in range(1, shards + 1)]
    else:
        groups, totals = [[] for _ in range(shards)], [0] * shards
        for path in sorted(complete, key=lambda path: (-durations.get(path, UNMEASURED_MS), path)):
            index = min(range(shards), key=lambda i: (totals[i], len(groups[i]), i))
            groups[index].append(path)
            totals[index] += durations.get(path, UNMEASURED_MS)
        for group in groups:
            group.sort()
    flattened = [filename for group in groups for filename in group]
    if any(not group for group in groups) or len(flattened) != len(complete) or set(flattened) != set(complete):
        raise ValueError('Campaign shards must be nonempty and cover every registered file exactly once')
    return groups


def partition_files(files, shards=SHARD_COUNT, *, durations=None):
    if shards != SHARD_COUNT:
        raise ValueError(f'Full CI requires exactly {SHARD_COUNT} campaign shards per backend')
    return partition_modules(files, shards, durations=durations)


class TimedModule(unittest.TestSuite):
    def __init__(self, tests, path, timings):
        super().__init__([tests])
        self.path = path
        self.timings = timings

    def run(self, result, debug=False):
        start = perf_counter()
        try:
            return super().run(result, debug)
        finally:
            self.timings[self.path] = max(1, round((perf_counter() - start) * 1000))


def load_suite(files, tests=TESTS, source=SOURCE, *, timings=None):
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
        selected = loader.loadTestsFromName(module)
        if timings is None:
            suite.addTests(selected)
        else:
            suite.addTest(TimedModule(selected, f'tests/{filename.relative_to(tests).as_posix()}', timings))
    return suite


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', required=True, type=int)
    parser.add_argument('--shards', required=True, type=int)
    parser.add_argument('--list-only', action='store_true')
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--timings', type=Path)
    args = parser.parse_args(argv)
    files = discover_files()
    backend = os.environ.get('MARCH_CORE_BACKEND', 'auto')
    try:
        _, registry_sha256 = load_registry(args.registry)
        durations = load_durations(backend) if backend in BACKENDS else None
        groups = partition_files(files, args.shards, durations=durations)
        select_shard([], args.shard, args.shards)
        selected = groups[args.shard - 1]
    except ValueError as error:
        parser.error(str(error))
    if not selected:
        parser.error('This shard has no campaign test files; refusing an empty test run')
    summary = dict(backend=backend,
                   shard=args.shard, shards=args.shards,
                   file_count=len(selected), all_file_count=len(files), registry_sha256=registry_sha256,
                   files=[path.relative_to(ROOT).as_posix() for path in selected])
    if durations is not None:
        summary['estimated_ms'] = sum(durations.get(path, UNMEASURED_MS) for path in selected)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    if args.list_only:
        return 0
    timings = {} if args.timings else None
    suite = load_suite(selected, timings=timings)
    print(f'Campaign shard {args.shard}/{args.shards}: '
          f'{len(selected)} files, {suite.countTestCases()} cases', flush=True)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    if args.timings:
        args.timings.parent.mkdir(parents=True, exist_ok=True)
        args.timings.write_text(json.dumps(dict(summary, passed=result.wasSuccessful(),
                                                module_ms=timings), sort_keys=True) + '\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
