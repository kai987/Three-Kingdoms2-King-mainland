"""Compare the released and parsed route caches in the original 217 and 263 replays."""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, redirect_stdout
from functools import wraps
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from time import perf_counter_ns, process_time_ns
import unittest
from unittest.mock import patch


COMMIT = 'df2b51043bfccda36946c8c6d81bb68928eaefa4'
CASES = {
    '217': ('217-07.json', 'test_217_wei_six_turns_staff_arrival_combat_and_real_convoys',
            388, 89, 'abb12811d3e0d0ef2655e5d0d6a8cd49bfa130d89cb5b788be4bc46c82f6bd24', 1955533152, 405),
    '263': ('263-05.json', 'test_263_shu_six_turns_offices_ai_and_frontline_transport',
            101, 29, 'c2e242448708b66555e27b93716445c57d7a6e2aa142e567042b1c394e6093ef', 1843471694, 488),
}
TEST_FILE = 'tests/test_remake_delegation_replay.py'
NATIVE_SHA256 = '03e5c576409d43a2a2a3abc3f89ef9724fa60fc41bc9ebc184682bdc1fa0d1a9'


class Timings:
    def __init__(self):
        self.rows = defaultdict(Counter)
        self.stack = []
        self.save_checksums = []
        self.restores = []
        self.views = []
        self.view_times = defaultdict(Counter)

    def wrap(self, original, label, *, child=False, after=None):
        @wraps(original)
        def measured(*args, **kwargs):
            if child and not self.stack:
                return original(*args, **kwargs)
            path = self.stack[-1][0] + '/' + label if self.stack else label
            frame = [path, 0, 0]
            self.stack.append(frame)
            wall_start, cpu_start = perf_counter_ns(), process_time_ns()
            try:
                result = original(*args, **kwargs)
            finally:
                cpu = process_time_ns() - cpu_start
                wall = perf_counter_ns() - wall_start
                self.stack.pop()
                if self.stack:
                    self.stack[-1][1] += wall
                    self.stack[-1][2] += cpu
                self.rows[path].update(calls=1, wall_ns=wall, cpu_ns=cpu,
                                       self_wall_ns=wall - frame[1], self_cpu_ns=cpu - frame[2])
            if after:
                after(args, result, sys._getframe(1).f_code.co_name, wall)
            return result

        return measured

    def save(self, _args, result, _site, _wall):
        self.save_checksums.append(result['checksum'])

    def restore(self, args, _result, _site, _wall):
        game, payload, _revision = args
        rng = dict(vars(game.state.rng))
        assert rng == payload['state']['rng'], 'RNG changed at restore'
        self.restores.append({'save': payload['checksum'], 'rng': rng})

    def view(self, args, result, site, wall):
        game = args[0]
        encoded = json.dumps(result, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()
        self.views.append(dict(site=site, turn=game.state.turn, phase=game.state.phase,
                               sha256=hashlib.sha256(encoded).hexdigest()))
        self.view_times[site].update(calls=1, wall_ns=wall)
        self.view_times[game.state.phase].update(calls=1, wall_ns=wall)



class ReplayWireJSON:
    def __init__(self, timings, checkpoint):
        self.checkpoint = checkpoint
        self.encode = timings.wrap(json.dumps, 'wire.encode')
        self.decode = timings.wrap(json.loads, 'wire.decode')

    def dumps(self, *args, **kwargs):
        function = self.encode if sys._getframe(1).f_code is self.checkpoint else json.dumps
        return function(*args, **kwargs)

    def loads(self, *args, **kwargs):
        function = self.decode if sys._getframe(1).f_code is self.checkpoint else json.loads
        return function(*args, **kwargs)


def copy_plan(value):
    """Prepare shallow copies plus replacements for mutable JSON descendants."""
    shallow_copy = value.copy
    items = value.items() if type(value) is dict else enumerate(value)
    nested = [(key, copy_plan(item)) for key, item in items
              if type(item) is dict or type(item) is list]
    if not nested:
        return shallow_copy

    def copy():
        result = shallow_copy()
        for key, make_child in nested:
            result[key] = make_child()
        return result

    return copy


def call_plan(plan):
    return plan()


def parsed_batch(adapter, timings=None):
    prepare = copy_plan if timings is None else timings.wrap(copy_plan, 'route.prepare')
    fresh = call_plan if timings is None else timings.wrap(call_plan, 'route.copy')

    def batch(lib, data, payload):
        request = adapter._encode_request(dict(payload, data=adapter.config_for(data), op='batch'),
                                          sort_keys=True)
        cached = adapter._last_batch
        if cached is not None and request == cached[0]:
            return fresh(cached[1])

        response = adapter._call_bytes(lib, request)
        plan = prepare(adapter._decode_reply(response))
        result = fresh(plan)
        adapter._last_batch = (request, plan)
        return result

    return batch


def install_route_timers(patches, adapter, timings, mode):
    batch = parsed_batch(adapter, timings) if mode == 'cached' else adapter._batch
    patches.enter_context(patch.object(adapter, '_batch', timings.wrap(batch, 'route.batch')))

    def wrap_batch_child(original, label):
        measured = timings.wrap(original, label)

        @wraps(original)
        def wrapped(*args, **kwargs):
            if timings.stack and timings.stack[-1][0].split('/')[-1] == 'route.batch':
                return measured(*args, **kwargs)
            return original(*args, **kwargs)

        return wrapped

    for name, label in (('_call_bytes', 'route.native'), ('_decode_reply', 'route.decode'),
                        ('_encode_request', 'route.encode')):
        original = getattr(adapter, name)
        patches.enter_context(patch.object(adapter, name, wrap_batch_child(original, label)))


def route_counts(rows):
    totals = Counter()
    for path, stats in rows.items():
        parts = path.split('/')
        if 'route.batch' in parts:
            totals[parts[-1]] += stats['calls']
    hits = totals['route.batch'] - totals['route.native']
    return totals, hits


def check_cache(mode):
    from copy import deepcopy
    import test_remake_march_core as tests
    from remake import march_core as adapter

    assert adapter.backend_status()['engine'] == 'rust'
    suite = unittest.TestSuite([tests.MarchNativeParityTests(
        'test_batch_reuses_only_equal_requests_and_returns_independent_quotes')])
    with ExitStack() as patches:
        if mode == 'cached':
            patches.enter_context(patch.object(adapter, '_batch', parsed_batch(adapter)))
        outcome = unittest.TextTestRunner(verbosity=2).run(suite)
        assert outcome.wasSuccessful() and outcome.testsRun == 1 and not outcome.skipped
        with patch.object(adapter, '_last_batch', None), patch.object(
                adapter, '_decode_reply', wraps=adapter._decode_reply) as decode, patch.object(
                adapter, '_call_bytes', wraps=adapter._call_bytes) as native:
            config = tests.synthetic_config()
            request = dict(cities=[dict(id=key, owner='friendly') for key in ('s', 'a', 'b', 't')],
                           year=217, month=7, discovered=[], player='friendly')
            first = adapter.invoke('batch', data=config, **request)
            expected = deepcopy(first)
            second = adapter.invoke('batch', data=config, **request)
            second['s:t:fastest']['routes'][0]['provenance']['keep'].append('updated')
            second.pop('s:t:fastest')
            returned = adapter.invoke('batch', data=config, **request)
            assert first == returned == expected
            assert native.call_count == 1
            assert decode.call_count == (1 if mode == 'cached' else 3)
            print(f'{mode}: after two cache hits, native calls={native.call_count}, '
                  f'JSON parses={decode.call_count}, nested caller mutations isolated.')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def run_case(scenario, mode, output):
    if git('rev-parse', 'HEAD') != COMMIT:
        raise RuntimeError(f'Expected pinned source {COMMIT}')
    git('diff', '--exit-code', 'HEAD')
    sys.path.insert(0, str(Path('tests').resolve()))
    import test_remake_delegation_replay as replay
    from remake import march_core

    native = Path('build/march-core/libmarch_core.so')
    native_sha256 = hashlib.sha256(native.read_bytes()).hexdigest()
    assert native_sha256 == NATIVE_SHA256
    if mode.startswith('check-'):
        check_cache(mode.removeprefix('check-'))
        return

    filename, method, restores, checkpoints, save, rng_state, rng_draws = CASES[scenario]
    timings = Timings()
    assert march_core.backend_status()['engine'] == 'rust'
    case = replay.DelegationReplayTests(method)
    stdout = io.StringIO()
    with ExitStack() as patches:
        install_route_timers(patches, march_core, timings, mode)
        for name, label, capture in (
            ('export_save', 'save.export', timings.save),
            ('load_save', 'save.restore', timings.restore),
            ('view', 'view.full', timings.view),
        ):
            original = getattr(replay.Campaign, name)
            patches.enter_context(patch.object(replay.Campaign, name, timings.wrap(original, label, after=capture)))
        proxy = ReplayWireJSON(timings, replay.DelegationReplayTests.checkpoint.__code__)
        patches.enter_context(patch.object(replay, 'json', proxy))
        start, cpu_start = perf_counter_ns(), process_time_ns()
        with redirect_stdout(stdout):
            result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
        cpu_ns, wall_ns = process_time_ns() - cpu_start, perf_counter_ns() - start
    print(stdout.getvalue(), end='', flush=True)
    assert result.testsRun == 1 and result.wasSuccessful() and not result.skipped
    proof, = (row for row in map(json.loads, stdout.getvalue().splitlines()) if row.get('scenario') == filename)
    assert proof['actual_json_restores'] == {'rust': restores}
    assert proof['full_view_checkpoints'] == checkpoints
    assert proof['final_save_sha256'] == save
    assert proof['final_rng'] == {'state': rng_state, 'draws': rng_draws}
    assert len(timings.restores) == timings.rows['wire.encode']['calls'] == timings.rows['wire.decode']['calls'] == restores
    assert sum(row['site'] == 'presentation_checkpoint' for row in timings.views) == checkpoints
    git('diff', '--exit-code', 'HEAD')

    paths = (TEST_FILE, 'source/remake', f'game/data/campaigns/{filename}')
    report = dict(mode=mode, wall_ns=wall_ns, cpu_ns=cpu_ns, runner=os.environ['RUNNER_NAME'],
                  source=COMMIT, input_objects={path: git('rev-parse', f'HEAD:{path}') for path in paths},
                  native_sha256=native_sha256,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  case=case.id(), proof=proof, rows=timings.rows, views=timings.views,
                  view_times=timings.view_times, restores=timings.restores, saves=timings.save_checksums)
    Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


def compare(evidence):
    for scenario in CASES:
        baseline, cached = [json.loads((evidence / f'{scenario}-{mode}.json').read_text())
                            for mode in ('baseline', 'cached')]
        for key in ('source', 'runner', 'input_objects', 'native_sha256', 'case', 'views', 'restores', 'saves'):
            assert baseline[key] == cached[key], (scenario, key)
        for report in (baseline, cached):
            report['proof'].pop('elapsed_seconds')
        assert baseline['proof'] == cached['proof']
        totals, hits = route_counts(baseline['rows'])
        optimized, new_hits = route_counts(cached['rows'])
        assert hits == new_hits and hits > 0
        assert totals['route.native'] == optimized['route.native']
        assert totals['route.batch'] == optimized['route.batch']
        assert totals['route.decode'] == totals['route.batch']
        assert optimized['route.decode'] == optimized['route.native']
        assert optimized['route.copy'] == optimized['route.batch']
        assert optimized['route.prepare'] == optimized['route.native']
        print(f'{scenario}: {len(cached["restores"])} restored saves with RNG, {len(cached["saves"])} save exports, '
              f'{len(cached["views"])} complete views match in execution order; '
              f'{hits} hits and {optimized["route.native"]} native misses in both modes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('baseline', 'cached', 'check-baseline', 'check-cached', 'compare'))
    parser.add_argument('path', type=Path)
    parser.add_argument('--scenario', choices=CASES, default='217')
    args = parser.parse_args()
    if args.mode == 'compare':
        compare(args.path)
    else:
        run_case(args.scenario, args.mode, args.path)


if __name__ == '__main__':
    main()
