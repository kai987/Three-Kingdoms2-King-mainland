#!/usr/bin/env python3
"""Run every campaign unittest case once across deterministic CI shards.

The CI backends use reviewed timings for whole modules and independent replay
cases. --list-only shows the schedule without importing campaign modules.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
DELEGATION_REPLAY = 'tests/test_remake_delegation_replay.py'


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


def read_duration_config(path):
    value = json.loads(Path(path).read_text())
    if (not isinstance(value, dict) or value.get('schema') != 'tk2-campaign-module-durations-v1'
            or not isinstance(value.get('backends'), dict) or set(value['backends']) != set(BACKENDS)):
        raise ValueError('Invalid campaign module timings')
    return value


def timing_weights(timings):
    if not isinstance(timings, dict) or not timings or any(
            type(ms) is not int or not 0 < ms <= 40 * 60_000 for ms in timings.values()):
        raise ValueError('Campaign module timings must be positive bounded milliseconds')
    return timings


def load_durations(backend, path=DURATIONS):
    timings = timing_weights(read_duration_config(path)['backends'][backend])
    return {ROOT / path: ms for path, ms in timings.items()}


def partition_modules(files, shards, *, durations=None, start_ms=None):
    """Validate a closed partition before any test module is imported."""
    complete = list(files)
    if len(complete) != len(set(complete)):
        raise ValueError('Duplicate campaign test file in the shard inventory')
    if durations is None:
        groups = [select_shard(complete, index, shards) for index in range(1, shards + 1)]
    else:
        groups = [[] for _ in range(shards)]
        totals = list(start_ms) if start_ms is not None else [0] * shards
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


def partition_files(files, shards=SHARD_COUNT, *, durations=None, start_ms=None):
    if shards != SHARD_COUNT:
        raise ValueError(f'Full CI requires exactly {SHARD_COUNT} campaign shards per backend')
    return partition_modules(files, shards, durations=durations, start_ms=start_ms)


def partition_campaign(files, shards, backend, path=DURATIONS):
    """Return a complete schedule, weights, expected replay IDs and start estimates."""
    units = [filename.relative_to(ROOT).as_posix() for filename in files]
    if backend not in BACKENDS:
        return partition_files(units, shards), None, {}, None

    config = read_duration_config(path)
    durations = timing_weights(config['backends'][backend]).copy()
    cases = {}
    if 'replay_cases' in config:
        per_backend = config['replay_cases']
        if (not isinstance(per_backend, dict) or set(per_backend) != set(BACKENDS)
                or DELEGATION_REPLAY not in units):
            raise ValueError('Invalid delegation replay timings')
        cases = timing_weights(per_backend[backend])
        if (len(cases) < 2 or any(set(timing_weights(weights)) != set(cases) for weights in per_backend.values())
                or any(not re.fullmatch(r'DelegationReplayTests\.test_\w+', case) for case in cases)):
            raise ValueError('Delegation replay timings must name the same independent cases for both backends')
        units.remove(DELEGATION_REPLAY)
        for case, duration in cases.items():
            unit = f'{DELEGATION_REPLAY}::{case}'
            units.append(unit)
            durations[unit] = duration

    start_ms = None
    if 'shard_start_ms' in config:
        per_backend = config['shard_start_ms']
        if (not isinstance(per_backend, dict) or set(per_backend) != set(BACKENDS)
                or any(not isinstance(values, list) or len(values) != SHARD_COUNT
                       or any(type(value) is not int or not 0 <= value <= 40 * 60_000
                              for value in values)
                       for values in per_backend.values())):
            raise ValueError('Invalid campaign shard start estimates')
        # Capacity is shared by the matrix. Later jobs should leave enough room
        # for the measured wait before a runner slot becomes available.
        start_ms = per_backend[backend]

    groups = partition_files(units, shards, durations=durations, start_ms=start_ms)
    return groups, durations, cases, start_ms


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


def replay_inventory(loader, module, expected):
    def flatten(suite):
        for case in suite:
            if type(case) is unittest.TestSuite:
                yield from flatten(case)
            elif isinstance(case, unittest.TestCase):
                yield case
            else:
                raise ValueError('Delegation replay split requires standard unittest suites')

    discovered = list(flatten(loader.loadTestsFromName(module)))
    identity = {case.id().removeprefix(module + '.'): case for case in discovered}
    if set(identity) != set(expected) or len(discovered) != len(expected):
        raise ValueError('Delegation replay split inventory differs from unittest discovery')
    imported = sys.modules[module]
    if any(hasattr(imported, name) for name in ('load_tests', 'setUpModule', 'tearDownModule')):
        raise ValueError('Delegation replay split cannot share module fixtures or load hooks')
    for case in discovered:
        for name in ('setUpClass', 'tearDownClass'):
            implementation = getattr(type(case), name)
            original = getattr(unittest.TestCase, name).__func__
            if getattr(implementation, '__func__', implementation) is not original:
                raise ValueError('Delegation replay split cannot share class fixtures')
    return identity


def load_suite(files, tests=TESTS, source=SOURCE, *, timings=None, replay_cases=(),
               expected_replays=(), replay_timings=None):
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
    if replay_cases:
        module = Path(DELEGATION_REPLAY).stem
        inventory = replay_inventory(loader, module, expected_replays)
        for name in replay_cases:
            case = inventory[name]
            if replay_timings is None:
                suite.addTest(case)
            else:
                suite.addTest(TimedModule(unittest.TestSuite([case]), name, replay_timings))
    return suite


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', required=True, type=int)
    parser.add_argument('--shards', required=True, type=int)
    parser.add_argument('--list-only', action='store_true')
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--durations', type=Path, default=DURATIONS)
    parser.add_argument('--timings', type=Path)
    args = parser.parse_args(argv)
    files = discover_files()
    backend = os.environ.get('MARCH_CORE_BACKEND', 'auto')
    try:
        _, registry_sha256 = load_registry(args.registry)
        groups, durations, expected_replays, start_ms = partition_campaign(
            files, args.shards, backend, args.durations)
        select_shard([], args.shard, args.shards)
        selected = groups[args.shard - 1]
    except ValueError as error:
        parser.error(str(error))
    whole_modules = [unit for unit in selected if '::' not in unit]
    replay_cases = [unit.split('::', 1)[1] for unit in selected if '::' in unit]
    summary = dict(backend=backend, shard=args.shard, shards=args.shards,
                   file_count=len(whole_modules), all_file_count=len(files),
                   registry_sha256=registry_sha256, files=whole_modules)
    if durations is not None:
        summary['estimated_ms'] = sum(durations.get(unit, UNMEASURED_MS) for unit in selected)
    if start_ms is not None:
        summary['estimated_start_ms'] = start_ms[args.shard - 1]
    if expected_replays:
        summary['replay_cases'] = replay_cases
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    if args.list_only:
        return 0
    timings = {} if args.timings else None
    replay_timings = {} if args.timings and expected_replays else None
    try:
        suite = load_suite([ROOT / name for name in whole_modules], timings=timings,
                           replay_cases=replay_cases, expected_replays=expected_replays,
                           replay_timings=replay_timings)
    except ValueError as error:
        parser.error(str(error))
    print(f'Campaign shard {args.shard}/{args.shards}: '
          f'{len(whole_modules)} files, {suite.countTestCases()} cases', flush=True)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    if args.timings:
        report = dict(summary, passed=result.wasSuccessful(), module_ms=timings)
        if replay_timings is not None:
            report['replay_ms'] = replay_timings
        args.timings.parent.mkdir(parents=True, exist_ok=True)
        args.timings.write_text(json.dumps(report, sort_keys=True) + '\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
