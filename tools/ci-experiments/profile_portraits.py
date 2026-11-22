#!/usr/bin/env python3
"""Measure the untouched #65 portrait suite with in-memory timing probes."""
import contextlib
import functools
import hashlib
import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns
import unittest


SOURCE = 'df2b51043bfccda36946c8c6d81bb68928eaefa4'
BUILDER = 'game/build_portrait_manifest.py'
TESTS = 'tests/test_remake_portraits.py'

# Complete statements in the pinned files, including their original assertions.
# Keep benchmark fingerprints separate from the production SHA-256 timings.
BUILDER_PROBES = [
    (90, 90, 'png_inflate'),
    (93, 124, 'png_scanlines'),
    (203, 204, 'pixels:enhanced_opacity'),
    (208, 211, 'pixels:enhanced_nearest'),
    (244, 253, 'pixels:refined'),
    (293, 304, 'pixels:white'),
    (357, 373, 'pixels:redrawn'),
    (606, 629, 'pixels:retainer_crop'),
    (631, 645, 'pixels:retainer_detail'),
    (751, 755, 'pixels:generated'),
]
TEST_PROBES = [(224, 245, 'pixels:test_historical_additions')]


def timed_code(path, probes):
    lines = path.read_text().splitlines(keepends=True)
    for first, last, label in sorted(probes, reverse=True):
        indent = lines[first - 1][:-len(lines[first - 1].lstrip())]
        original = lines[first - 1:last]
        lines[first - 1:last] = [
            f'{indent}with profiler.measure({label!r}):\n',
            *['    ' + line if line.strip() else line for line in original],
        ]
    return compile(''.join(lines), str(path), 'exec')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


class Profile:
    def __init__(self):
        self.ns = Counter()
        self.calls = Counter()
        self.sites = defaultdict(Counter)
        self.sizes = defaultdict(Counter)
        self.seen = set()
        self.build_seen = None
        self.builds = []
        self.sequence = hashlib.sha256()

    @contextlib.contextmanager
    def measure(self, label):
        start = perf_counter_ns()
        try:
            yield
        finally:
            self.ns[label] += perf_counter_ns() - start
            self.calls[label] += 1

    def wrap_png(self, original):
        @functools.wraps(original)
        def decode(raw, expected_size=(32, 40)):
            caller = sys._getframe(1)
            site = caller.f_code.co_name
            start = perf_counter_ns()
            try:
                size, pixels = original(raw, expected_size)
            except Exception:
                self.ns['png_decode'] += perf_counter_ns() - start
                self.calls['png_failed'] += 1
                raise

            duration = perf_counter_ns() - start
            self.ns['png_decode'] += duration
            self.calls['png_success'] += 1
            with self.measure('profiler_fingerprints'):
                digest = hashlib.sha256(raw).digest()
                key = (digest, expected_size)
                repeated = key in self.seen
                self.seen.add(key)
                if self.build_seen is not None:
                    if key in self.build_seen:
                        self.calls['png_repeat_within_build'] += 1
                    elif repeated:
                        self.calls['png_first_in_build_seen_earlier'] += 1
                    self.build_seen.add(key)
                self.sequence.update(digest)
                self.sequence.update(repr(size).encode())
                self.sequence.update(hashlib.sha256(pixels).digest())
                size_label = f'{size[0]}x{size[1]}'
                for group in (self.sites[site], self.sizes[size_label]):
                    group.update(calls=1, ns=duration)
                    if repeated:
                        group.update(repeated=1, repeated_ns=duration)
                if repeated:
                    self.calls['png_repeat'] += 1
                    self.ns['png_repeat'] += duration
            return size, pixels

        return decode

    def wrap_build(self, original):
        @functools.wraps(original)
        def build():
            before_ns = self.ns.copy()
            before_calls = self.calls.copy()
            self.build_seen = set()
            result = None
            start = perf_counter_ns()
            try:
                result = original()
                return result
            finally:
                duration = perf_counter_ns() - start
                with self.measure('profiler_fingerprints'):
                    manifest = None
                    if result is not None:
                        encoded = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
                        manifest = hashlib.sha256(encoded).hexdigest()
                    self.builds.append(dict(
                        wall_ns=duration,
                        result_sha256=manifest,
                        unique_png=len(self.build_seen),
                        calls=dict(self.calls - before_calls),
                        ns=dict(self.ns - before_ns),
                    ))
                self.build_seen = None

        return build


def main(output):
    source = git('rev-parse', 'HEAD')
    if source != SOURCE:
        raise RuntimeError(f'Expected {SOURCE}, got {source}')
    pinned_paths = (BUILDER, TESTS, 'game/assets/portraits', 'art/portraits', 'game/config')
    git('diff', '--exit-code', 'HEAD', '--', *pinned_paths)
    objects = {path: git('rev-parse', f'HEAD:{path}') for path in pinned_paths}

    sys.path.insert(0, str(Path.cwd()))
    from source.remake import march_core

    backend = os.environ['MARCH_CORE_BACKEND']
    if march_core.backend_status()['engine'] != backend:
        raise RuntimeError('Unexpected game backend')

    profiler = Profile()
    test_path = Path(TESTS).resolve()
    spec = importlib.util.spec_from_file_location('test_remake_portraits', test_path)
    test = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = test
    test.profiler = profiler
    exec(timed_code(test_path, TEST_PROBES), vars(test))
    builder = test.builder
    builder.profiler = profiler
    exec(timed_code(Path(BUILDER).resolve(), BUILDER_PROBES), vars(builder))
    builder.png_pixels = profiler.wrap_png(builder.png_pixels)
    builder.build = profiler.wrap_build(builder.build)
    builder.sha = profiler.measure('validation_sha256')(builder.sha)

    loader = unittest.defaultTestLoader
    suite = loader.loadTestsFromModule(test)
    test_ids = [f'{cls.__name__}.{method}'
                for cls in vars(test).values()
                if isinstance(cls, type) and issubclass(cls, unittest.TestCase)
                for method in loader.getTestCaseNames(cls)]
    start = perf_counter_ns()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    wall = perf_counter_ns() - start
    git('diff', '--exit-code', 'HEAD', '--', *pinned_paths)
    report = dict(
        source=source, objects=objects, backend=march_core.backend_status(),
        runner=os.environ.get('RUNNER_NAME'), python=sys.version, wall_ns=wall,
        tests=result.testsRun, test_ids=test_ids, skips=len(result.skipped),
        calls=dict(profiler.calls), ns=dict(profiler.ns),
        png_sizes=profiler.sizes, png_sites=profiler.sites,
        png_unique=len(profiler.seen), png_sequence_sha256=profiler.sequence.hexdigest(),
        builds=profiler.builds,
    )
    Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f'{backend}: {result.testsRun} tests in {wall / 1e9:.2f}s, '
          f'{profiler.calls["png_success"]} successful PNG decodes, '
          f'{profiler.calls["png_repeat"]} repeated')
    if not result.wasSuccessful() or result.skipped or result.testsRun != len(test_ids):
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1])
