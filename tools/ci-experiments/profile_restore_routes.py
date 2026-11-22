"""Compare per-leg and batched Rust route validation during original saves."""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, redirect_stdout
from functools import wraps
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns, process_time_ns
import unittest
from unittest.mock import patch

from batch_restore_routes import RestoreBatch


COMMIT = 'df2b51043bfccda36946c8c6d81bb68928eaefa4'
CASES = {
    '217': ('217-07.json', 'test_217_wei_six_turns_staff_arrival_combat_and_real_convoys',
            388, 89, 'abb12811d3e0d0ef2655e5d0d6a8cd49bfa130d89cb5b788be4bc46c82f6bd24', 1955533152, 405),
    '263': ('263-05.json', 'test_263_shu_six_turns_offices_ai_and_frontline_transport',
            101, 29, 'c2e242448708b66555e27b93716445c57d7a6e2aa142e567042b1c394e6093ef', 1843471694, 488),
}
TEST_FILE = 'tests/test_remake_delegation_replay.py'


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


def install_native_timers(patches, adapter, timings):
    def during_restore(original, label):
        measured = timings.wrap(original, label)

        @wraps(original)
        def wrapped(*args, **kwargs):
            if timings.stack and timings.stack[0][0] == 'save.restore':
                return measured(*args, **kwargs)
            return original(*args, **kwargs)

        return wrapped

    original = adapter._call
    scalar = timings.wrap(original, 'route.scalar')
    batch = timings.wrap(original, 'route.batch')

    @wraps(original)
    def call(lib, request):
        if timings.stack and timings.stack[0][0] == 'save.restore':
            operation = request['op']
            if operation in ('allowed', 'evaluate_leg', 'route_allowed'):
                return scalar(lib, request)
            if operation == 'restore_route_legs':
                return batch(lib, request)
        return original(lib, request)

    patches.enter_context(patch.object(adapter, '_call', call))
    for name, label in (('_encode_request', 'rust.encode'), ('_call_bytes', 'rust.native')):
        original = getattr(adapter, name)
        patches.enter_context(patch.object(adapter, name, during_restore(original, label)))


def run_checks(mode):
    from copy import deepcopy
    from test_remake_hazard_marches import HazardMarchTests
    from test_remake_logistics import LogisticsTests
    from test_remake_march_supply import MarchSupplyTests
    from test_remake_delegation_replay import HeadlessCampaign
    from remake.campaign import Campaign, digest
    from remake.errors import GameError

    class HistoryRestoreTest(HazardMarchTests):
        def test_rejects_resigned_march_history_and_retains_live_game(self):
            game = self.game('wu')
            self.empty(game, 'yizhou', 'wu')
            ids = game.state.cities['hepu'].roster.officer_ids[:3]
            self.set_troops(game, ids, 10000)
            game.command('transfer', dict(source='hepu', target='yizhou', officers=ids,
                                          route_mode='explore'), game.revision)
            self.empty(game, 'yizhou', 'wei')
            self.arrive(game)
            original = game.export_save()
            clone = HeadlessCampaign(game.catalog)
            clone.load_save(json.loads(json.dumps(original)), 0)
            self.assertEqual(clone.export_save(), original)
            restored_before = deepcopy(clone.state.rng)
            revision = clone.revision
            for field, value in (('days', 9999), ('id', 'absent-historical-route')):
                with self.subTest(field=field):
                    changed = deepcopy(original)
                    march = changed['state']['extension']['travel']['marches'][0]
                    self.assertTrue(march['history'])
                    march['history'][0]['quote']['routes'][0][field] = value
                    changed['checksum'] = digest({k: v for k, v in changed.items() if k != 'checksum'})
                    with self.assertRaises(GameError):
                        clone.load_save(changed, revision)
                    self.assertEqual(clone.revision, revision)
                    self.assertEqual(clone.state.rng, restored_before)
                    self.assertEqual(clone.export_save(), original)

    cases = unittest.TestSuite([
        HazardMarchTests('test_altered_weather_casualties_or_discovery_saves_are_rejected_atomically'),
        MarchSupplyTests('test_supply_save_tampering_rejected_without_changing_current_campaign'),
        LogisticsTests('test_signed_cargo_quote_and_weather_tampering_reject_atomically'),
        HistoryRestoreTest('test_rejects_resigned_march_history_and_retains_live_game'),
    ])
    prototype = RestoreBatch()
    with ExitStack() as patches:
        if mode == 'batch':
            prototype.install(patches, Campaign)
        result = unittest.TextTestRunner(verbosity=2).run(cases)
    assert result.testsRun == 4 and result.wasSuccessful() and not result.skipped
    if mode == 'batch':
        assert prototype.stats['batches'] and prototype.stats['direction_results']
        assert prototype.stats['leg_results'] and prototype.stats['fallbacks']
    print(mode, 'passed all valid/invalid restore checks', dict(prototype.stats))


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def run_case(scenario, mode, output):
    if git('rev-parse', 'HEAD') != COMMIT:
        raise RuntimeError(f'Expected pinned source {COMMIT}')
    git('diff', '--exit-code', 'HEAD')
    sys.path.insert(0, str(Path('tests').resolve()))
    import test_remake_delegation_replay as replay
    from remake import march_core

    filename, method, restores, checkpoints, save, rng_state, rng_draws = CASES[scenario]
    timings = Timings()
    if mode.startswith('check-'):
        run_checks(mode.removeprefix('check-'))
        return
    assert march_core.backend_status()['engine'] == 'rust'
    case = replay.DelegationReplayTests(method)
    stdout = io.StringIO()
    prototype = RestoreBatch()
    with ExitStack() as patches:
        if mode == 'batch':
            prototype.install(patches, replay.Campaign)
        install_native_timers(patches, march_core, timings)
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

    native = Path('build/march-core/libmarch_core.so')
    paths = (TEST_FILE, 'source/remake', f'game/data/campaigns/{filename}')
    report = dict(mode=mode, wall_ns=wall_ns, cpu_ns=cpu_ns, runner=os.environ['RUNNER_NAME'],
                  source=COMMIT, input_objects={path: git('rev-parse', f'HEAD:{path}') for path in paths},
                  native_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
                  case=case.id(), proof=proof, rows=timings.rows, views=timings.views,
                  batch_stats=dict(prototype.stats),
                  view_times=timings.view_times, restores=timings.restores, saves=timings.save_checksums)
    Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


def compare(evidence):
    for scenario in CASES:
        reports = [json.loads((evidence / f'{scenario}-{mode}.json').read_text())
                   for mode in ('baseline', 'batch')]
        reference, detailed = reports
        for key in ('source', 'runner', 'input_objects', 'native_sha256', 'case', 'views', 'restores', 'saves'):
            assert reference[key] == detailed[key], (scenario, key)
        for report in reports:
            report['proof'].pop('elapsed_seconds')
        assert reference['proof'] == detailed['proof']
        old_calls = reference['rows']['save.restore/route.scalar/rust.native']['calls']
        new_calls = detailed['rows']['save.restore/route.batch/rust.native']['calls']
        scalar = detailed['rows'].get('save.restore/route.scalar/rust.native', {}).get('calls', 0)
        assert new_calls == detailed['batch_stats']['batches'] <= len(detailed['restores'])
        assert new_calls > 0 and new_calls + scalar < old_calls
        assert not detailed['batch_stats'].get('fallbacks')
        print(f'{scenario}: route native calls {old_calls} -> {new_calls + scalar} ({scalar} scalar).')
        print(f'{scenario}: {len(detailed["restores"])} restores with RNG, {len(detailed["saves"])} save exports, '
              f'{len(detailed["views"])} complete views match in execution order.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('baseline', 'batch', 'check-baseline', 'check-batch', 'compare'))
    parser.add_argument('path', type=Path)
    parser.add_argument('--scenario', choices=CASES, default='217')
    args = parser.parse_args()
    if args.mode == 'compare':
        compare(args.path)
    else:
        run_case(args.scenario, args.mode, args.path)


if __name__ == '__main__':
    main()
