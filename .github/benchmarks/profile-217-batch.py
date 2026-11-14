"""Run the original 217 case with timing and output checks around the native batch."""
import argparse
from collections import Counter
from contextlib import ExitStack, redirect_stdout
from functools import wraps
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns, process_time_ns
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'source')]

from remake import march_core as adapter
from remake.campaign import digest
import test_remake_delegation_replay as replay

ADAPTER = 'source/remake/march_core.py'
TEST = 'tests/test_remake_delegation_replay.py'
SCENARIO = 'game/data/campaigns/217-07.json'
NATIVE = 'build/march-core/libmarch_core.so'
EXPECTED = {
    TEST: '4704f3c986f550bcf21eccbbaeb9ca3983267d02441f1af5d0a0236484df6831',
    SCENARIO: '5543a82af78d2a649606cf14b9741ccf44d4f1b16d2cdec24a00e0f996c91661',
    NATIVE: '9d222a77196b8bb7ad5e827ddcb38b3ecdc3b1c1984ebf0ab8a2f63c463dc553',
}
EXPECTED_SAVES = '355e916b253c67fe37c0ee0f75385d6bc3ba45b19c98eca428ae1ca63a33f74b'
EXPECTED_RESTORES = 'acef98bd65742159638ffdf17bedc221971ea6356385f86e66835c8d0daa7cfa'
METHOD = 'test_217_wei_six_turns_staff_arrival_combat_and_real_convoys'


class Timings:
    def __init__(self):
        self.views = []
        self.quotes = []
        self.save_exports = 0
        self.save_restores = 0
        self.saves = sha256()
        self.restores = sha256()

    def view(self, original):
        @wraps(original)
        def measured(game):
            start, cpu_start = perf_counter_ns(), process_time_ns()
            value = original(game)
            cpu = process_time_ns() - cpu_start
            wall = perf_counter_ns() - start
            caller = sys._getframe(1).f_code.co_name
            self.views.append(dict(site=caller, wall_ns=wall, cpu_ns=cpu, output=digest(value)))
            return value
        return measured

    def export(self, original):
        @wraps(original)
        def observed(*args, **kwargs):
            value = original(*args, **kwargs)
            self.save_exports += 1
            self.saves.update(bytes.fromhex(value['checksum']))
            return value
        return observed

    def restore(self, original):
        @wraps(original)
        def observed(game, payload, revision):
            value = original(game, payload, revision)
            self.save_restores += 1
            self.restores.update(bytes.fromhex(payload['checksum']))
            rng = game.state.rng
            self.restores.update(f'{rng.state}:{rng.draws}\n'.encode())
            return value
        return observed


def trial(variant, adapter_ref):
    hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXPECTED}
    assert hashes == EXPECTED, hashes
    expected_adapter = subprocess.check_output(['git', 'show', f'{adapter_ref}:{ADAPTER}'], cwd=ROOT)
    assert Path(adapter.__file__).read_bytes() == expected_adapter
    # Count batch dispatches directly at the Rust ABI boundary. Registration
    # uses the same ABI, so the adapter's total call counter alone is insufficient.
    with adapter.using_backend('rust'):
        lib = adapter._load()
        assert lib is not None
    native = lib.march_call
    dispatches = 0

    def observed_native(source, length):
        # All ABI requests are JSON objects. Decode the request only while a
        # bulk quote is in flight, then count the one actual 'batch' operation.
        nonlocal dispatches
        if timing_batch:
            operation = json.loads(adapter.ctypes.string_at(source, length))['op']
            if operation == 'batch':
                dispatches += 1
        return native(source, length)

    timers = Timings()
    timing_batch = False
    original_invoke = adapter.invoke

    @wraps(original_invoke)
    def invoke(operation, *args, **kwargs):
        nonlocal timing_batch
        if operation != 'batch':
            return original_invoke(operation, *args, **kwargs)
        before = dispatches
        timing_batch = True
        start, cpu_start = perf_counter_ns(), process_time_ns()
        try:
            value = original_invoke(operation, *args, **kwargs)
        finally:
            timing_batch = False
        cpu = process_time_ns() - cpu_start
        wall = perf_counter_ns() - start
        timers.quotes.append(dict(wall_ns=wall, cpu_ns=cpu, calculations=dispatches - before))
        return value

    case = replay.DelegationReplayTests(METHOD)
    result_text = io.StringIO()
    with ExitStack() as patches:
        patches.enter_context(patch.object(adapter, 'invoke', invoke))
        patches.enter_context(patch.object(lib, 'march_call', observed_native))
        patches.enter_context(patch.object(replay.Campaign, 'view', timers.view(replay.Campaign.view)))
        patches.enter_context(patch.object(replay.Campaign, 'export_save', timers.export(replay.Campaign.export_save)))
        patches.enter_context(patch.object(replay.Campaign, 'load_save', timers.restore(replay.Campaign.load_save)))
        with redirect_stdout(result_text):
            start, cpu_start = perf_counter_ns(), process_time_ns()
            result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
            cpu = process_time_ns() - cpu_start
            wall = perf_counter_ns() - start

    assert result.testsRun == 1 and not result.skipped and result.wasSuccessful()
    proof, = [row for row in map(json.loads, result_text.getvalue().splitlines()) if row.get('scenario') == '217-07.json']
    assert proof['actual_json_restores'] == {'rust': 681}
    assert proof['full_view_checkpoints'] == 136
    assert proof['final_save_sha256'] == '802e2ec528c453ab8316cf90c9b77099d860e38d208434382afc4c57d9f5fd6f'
    assert proof['final_rng'] == {'state': 4007548128, 'draws': 398}
    assert timers.save_exports == 1499 and timers.save_restores == 681
    assert timers.saves.hexdigest() == EXPECTED_SAVES
    assert timers.restores.hexdigest() == EXPECTED_RESTORES
    assert Counter(row['site'] for row in timers.views) == {'presentation_checkpoint': 136, 'view': 44}
    assert len(timers.views) == len(timers.quotes) == 180
    assert all(row['calculations'] in (0, 1) for row in timers.quotes)
    if variant == 'baseline':
        assert dispatches == 180
    return dict(variant=variant, adapter_ref=adapter_ref, adapter_sha256=sha256(expected_adapter).hexdigest(),
                runner=os.environ.get('RUNNER_NAME'), run_id=os.environ.get('GITHUB_RUN_ID'),
                commit=os.environ.get('GITHUB_SHA'), input_hashes=hashes, proof=proof,
                save_export_sequence_sha256=timers.saves.hexdigest(),
                restored_save_and_rng_sequence_sha256=timers.restores.hexdigest(),
                replay_wall_ns=wall, replay_cpu_ns=cpu, views=timers.views, quotes=timers.quotes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('variant', choices=('baseline', 'optimized'))
    parser.add_argument('adapter_ref')
    args = parser.parse_args()
    print(json.dumps(trial(args.variant, args.adapter_ref), separators=(',', ':'), sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
