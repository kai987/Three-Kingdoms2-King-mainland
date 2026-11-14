"""Profile exactly the existing 217 unittest in a selected shard's import context."""
import argparse
from collections import Counter
from contextlib import ExitStack
from functools import wraps
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
from time import perf_counter_ns, process_time_ns
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.ci import run_campaign_tests as runner

MODULE = 'test_remake_delegation_replay'
METHOD = 'DelegationReplayTests.test_217_wei_six_turns_staff_arrival_combat_and_real_convoys'
INPUT = ROOT / 'game/data/campaigns/217-07.json'
DURATIONS = {
    'baseline': ROOT / '.github/benchmarks/campaign-durations-before.json',
    'optimized': runner.DURATIONS,
}
MEASURES = ('save_export', 'json_encode', 'json_decode', 'save_restore', 'full_view')
EXPECTED_PROOF = {
    'scenario': '217-07.json',
    'actual_json_restores': {'rust': 681},
    'full_view_checkpoints': 136,
    'final_save_sha256': '802e2ec528c453ab8316cf90c9b77099d860e38d208434382afc4c57d9f5fd6f',
    'final_rng': {'state': 4007548128, 'draws': 398},
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cases(suite):
    for child in suite:
        if isinstance(child, unittest.TestSuite):
            yield from test_cases(child)
        else:
            yield child


def select_case(variant):
    started = perf_counter_ns()
    groups, _, expected_replays, _ = runner.partition_campaign(
        runner.discover_files(), runner.SHARD_COUNT, 'python', DURATIONS[variant]
    )
    selected = groups[0]
    whole = [ROOT / unit for unit in selected if '::' not in unit]
    replays = [unit.split('::', 1)[1] for unit in selected if '::' in unit]
    suite = runner.load_suite(whole, replay_cases=replays, expected_replays=expected_replays)
    candidates = list(test_cases(suite))
    case, = [test for test in candidates if test.id() == f'{MODULE}.{METHOD}']
    return case, {
        'candidate_count': len(candidates),
        'selected_case': case.id(),
        'selected_shard': 1,
        'duration_config_sha256': sha256(DURATIONS[variant]),
        'discovery_ns': perf_counter_ns() - started,
    }


class Timings:
    def __init__(self):
        self.rows = {name: Counter(calls=0, wall_ns=0, cpu_ns=0) for name in MEASURES}
        self.parents = []
        self.checkpoints = hashlib.sha256()
        self.restores = hashlib.sha256()

    def wrap(self, name, original, after=None):
        @wraps(original)
        def measured(*args, **kwargs):
            child = [0, 0]
            self.parents.append(child)
            wall_start = perf_counter_ns()
            cpu_start = process_time_ns()
            try:
                result = original(*args, **kwargs)
            finally:
                cpu = process_time_ns() - cpu_start
                wall = perf_counter_ns() - wall_start
                self.parents.pop()
                if self.parents:
                    self.parents[-1][0] += wall
                    self.parents[-1][1] += cpu
                row = self.rows[name]
                row['calls'] += 1
                row['wall_ns'] += wall - child[0]
                row['cpu_ns'] += cpu - child[1]
            if after:
                after(args, result)
            return result
        return measured

    def save_identity(self, _args, result):
        self.checkpoints.update(bytes.fromhex(result['checksum']))

    def restore_identity(self, args, _result):
        campaign, payload, _revision = args
        self.restores.update(bytes.fromhex(payload['checksum']))
        rng = campaign.state.rng
        self.restores.update(f'{rng.state}:{rng.draws}\n'.encode())


class CheckpointJSON:
    """Apply transport timers only to the round trip in checkpoint()."""
    def __init__(self, timings, checkpoint):
        self.checkpoint = checkpoint
        self.encode = timings.wrap('json_encode', json.dumps)
        self.decode = timings.wrap('json_decode', json.loads)

    def dumps(self, *args, **kwargs):
        fn = self.encode if sys._getframe(1).f_code is self.checkpoint else json.dumps
        return fn(*args, **kwargs)

    def loads(self, *args, **kwargs):
        fn = self.decode if sys._getframe(1).f_code is self.checkpoint else json.loads
        return fn(*args, **kwargs)


def trial(variant, view_profile=None):
    case, context = select_case(variant)
    replay = importlib.import_module(MODULE)
    campaign = replay.Campaign
    timings = Timings()
    result_text = io.StringIO()
    start = perf_counter_ns()
    cpu_start = process_time_ns()
    with ExitStack() as patches:
        patches.enter_context(patch.object(campaign, 'export_save',
            timings.wrap('save_export', campaign.export_save, timings.save_identity)))
        patches.enter_context(patch.object(campaign, 'load_save',
            timings.wrap('save_restore', campaign.load_save, timings.restore_identity)))
        view = timings.wrap('full_view', campaign.view)
        if view_profile is not None:
            view = view_profile.capture(view)
        patches.enter_context(patch.object(campaign, 'view', view))
        patches.enter_context(patch.object(replay, 'json',
            CheckpointJSON(timings, replay.DelegationReplayTests.checkpoint.__code__)))
        # The existing test emits the result after its final assertions.
        from contextlib import redirect_stdout
        with redirect_stdout(result_text):
            result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
    cpu = process_time_ns() - cpu_start
    wall = perf_counter_ns() - start
    if result.testsRun != 1 or result.skipped or not result.wasSuccessful():
        raise RuntimeError('The original 217 unittest failed or did not execute exactly once')
    proof, = [row for row in map(json.loads, result_text.getvalue().splitlines())
              if row.get('scenario') == '217-07.json']
    assert all(proof[key] == value for key, value in EXPECTED_PROOF.items()), proof
    for name in ('json_encode', 'json_decode', 'save_restore'):
        assert timings.rows[name]['calls'] == 681, timings.rows
    assert timings.rows['full_view']['calls'] >= 136
    return {
        'variant': variant,
        'input_sha256': sha256(INPUT),
        'runner': os.environ.get('RUNNER_NAME'),
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'commit': os.environ.get('GITHUB_SHA'),
        **context,
        'wall_ns': wall,
        'cpu_ns': cpu,
        'categories': timings.rows,
        'save_export_sequence_sha256': timings.checkpoints.hexdigest(),
        'restored_save_and_rng_sequence_sha256': timings.restores.hexdigest(),
        'proof': proof,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=DURATIONS)
    parser.add_argument('--list-only', action='store_true')
    args = parser.parse_args()
    if args.list_only:
        _, context = select_case(args.variant)
        print(json.dumps(context, sort_keys=True))
    else:
        print(json.dumps(trial(args.variant), sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
