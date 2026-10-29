#!/usr/bin/env python3
"""Run bounded CI replay fragments and require their exact backend parity.

The ordinary run.py CLI and its early two-campaign coverage gate stay intact.
Only the long middle campaign is split across runners; no single-backend
fragment is a successful parity result or an independently publishable gate.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tk2_ci_soak_replay', Path(__file__).with_name('run.py'))
soak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soak)

SCHEMA = 'tk2-campaign-soak-execution-v1'
POLICY = 'defensive-administrator-v3-shared-order-defense'
SEEDS = (3, 2026)
EXECUTIONS = tuple((case, seed, backend)
    for case in soak.CASES for seed in SEEDS
    for backend in (('python', 'rust') if case == 'middle' else ('both',)))
FIELDS = {'schema', 'head', 'run_id', 'run_attempt', 'policy', 'case', 'seed',
          'backend', 'catalog_sha256', 'requested_turns', 'report', 'failure', 'elapsed_seconds'}
RESULT_FIELDS = {'initial', 'final', 'completed_turns', 'requested_turns', 'coverage',
                 'commands', 'transport_receipts', 'succession', 'checkpoints', 'samples',
                 'command_sha256', 'final_save_sha256'}
HEAD = re.compile(r'^[a-f0-9]{40}(?:[a-f0-9]{24})?$')
HASH = re.compile(r'^[a-f0-9]{64}$')


def identity(head, run_id, attempt):
    if (not isinstance(head, str) or not HEAD.fullmatch(head)
            or type(run_id) is not int or run_id < 1
            or type(attempt) is not int or attempt < 1):
        raise ValueError('Invalid replay commit/run/attempt identity')


def catalog_sha(case):
    return hashlib.sha256((ROOT / 'game/data/campaigns' /
                           (soak.CASES[case]['scenario'] + '.json')).read_bytes()).hexdigest()


def fragment(case, seed, backend, *, head, run_id, attempt, progress=False):
    identity(head, run_id, attempt)
    if (case, seed, backend) not in EXECUTIONS or type(seed) is not int:
        raise ValueError('Unknown full-duration replay execution')
    record = dict(schema=SCHEMA, head=head, run_id=run_id, run_attempt=attempt,
        policy=POLICY, case=case, seed=seed, backend=backend,
        catalog_sha256=catalog_sha(case), requested_turns=soak.CASES[case]['turns'],
        report=None, failure=None, elapsed_seconds=0)
    started = time.monotonic()
    try:
        backends = ('python', 'rust') if backend == 'both' else (backend,)
        record['report'] = soak.run_case(case, seed, backends, progress=progress)
    except Exception as error:
        failure = dict(error=f'{type(error).__name__}: {error}')
        if hasattr(error, 'soak_context'):
            failure['context'] = error.soak_context
        record['failure'] = failure
    record['elapsed_seconds'] = round(time.monotonic() - started, 3)
    return record


def validate_result(result, duration):
    if (not isinstance(result, dict) or set(result) != RESULT_FIELDS
            or type(result['requested_turns']) is not int or result['requested_turns'] != duration
            or type(result['completed_turns']) is not int or not 0 <= result['completed_turns'] <= duration
            or not isinstance(result['coverage'], dict)
            or type(result['coverage'].get('crossed_year')) is not bool
            or not isinstance(result['succession'], list)
            or not isinstance(result['checkpoints'], list) or not isinstance(result['samples'], list)
            or not isinstance(result['commands'], dict) or not isinstance(result['transport_receipts'], dict)
            or not isinstance(result['initial'], dict) or not isinstance(result['final'], dict)
            or any(not isinstance(result[key], str) or not HASH.fullmatch(result[key])
                   for key in ('command_sha256', 'final_save_sha256'))):
        raise ValueError('Incomplete full-duration replay result')
    rng = result['final'].get('rng')
    if (not isinstance(rng, dict) or set(rng) != {'state', 'draws'}
            or type(rng['state']) is not int or not 0 <= rng['state'] <= 0xffffffff
            or type(rng['draws']) is not int or rng['draws'] < 0):
        raise ValueError('Incomplete replay RNG state')


def validate_execution(record, *, head, run_id, attempt):
    identity(head, run_id, attempt)
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError('Unknown replay execution fields')
    case, seed, backend = record['case'], record['seed'], record['backend']
    if (type(case) is not str or type(seed) is not int or type(backend) is not str
            or (case, seed, backend) not in EXECUTIONS
            or record['schema'] != SCHEMA or record['policy'] != POLICY
            or record['head'] != head or record['run_id'] != run_id or record['run_attempt'] != attempt
            or type(record['run_id']) is not int or type(record['run_attempt']) is not int
            or record['catalog_sha256'] != catalog_sha(case)
            or type(record['requested_turns']) is not int
            or record['requested_turns'] != soak.CASES[case]['turns']
            or type(record['elapsed_seconds']) not in (int, float)
            or not math.isfinite(record['elapsed_seconds']) or record['elapsed_seconds'] < 0):
        raise ValueError('Replay execution identity or duration mismatch')
    if record['failure'] is not None:
        raise ValueError('Replay execution did not finish successfully')
    report = record['report']
    expected_backends = ['python', 'rust'] if backend == 'both' else [backend]
    expected_parity = backend == 'both'
    if (not isinstance(report, dict) or report.get('case') != case
            or report.get('scenario') != soak.CASES[case]['scenario']
            or type(report.get('seed')) is not int or report['seed'] != seed
            or report.get('catalog_sha256') != record['catalog_sha256']
            or report.get('backends') != expected_backends
            or type(report.get('parity')) is not bool or report['parity'] != expected_parity):
        raise ValueError('Replay report does not match its execution identity')
    if case == 'early':
        if set(report) != {'case', 'scenario', 'seed', 'catalog_sha256', 'backends', 'parity', 'legs', 'coverage'}:
            raise ValueError('Early replay report fields')
        for leg in report['legs']:
            validate_result(leg['result'], record['requested_turns'])
        if report['coverage'] != soak.require_early_coverage(report['legs'], record['requested_turns']):
            raise ValueError('Early replay coverage was altered')
    else:
        if (set(report) != {'case', 'scenario', 'seed', 'catalog_sha256', 'faction',
                           'backends', 'parity', 'result', 'observations'}
                or report['faction'] != soak.CASES[case]['faction']):
            raise ValueError('Replay campaign fields or faction mismatch')
        result = report['result']
        validate_result(result, record['requested_turns'])
        if (result['completed_turns'] != record['requested_turns']
                or not result['coverage']['crossed_year'] or not result['succession']):
            raise ValueError('Insufficient full-duration replay coverage')
        if report['observations'] != soak.observations(result):
            raise ValueError('Replay observations differ from the actual result')
    return case, seed, backend


def merge(records, *, head, run_id, attempt, execution_result):
    """A successful executor matrix and every exact fragment are mandatory."""
    identity(head, run_id, attempt)
    if execution_result != 'success':
        raise ValueError('Replay executor matrix failed, was cancelled, skipped or is missing')
    indexed = {}
    for record in records:
        key = validate_execution(record, head=head, run_id=run_id, attempt=attempt)
        if key in indexed:
            raise ValueError('Duplicate replay execution')
        indexed[key] = record
    if set(indexed) != set(EXECUTIONS):
        raise ValueError('Missing full-duration replay executions')
    cases = []
    for case in soak.CASES:
        for seed in SEEDS:
            if case != 'middle':
                report = deepcopy(indexed[case, seed, 'both']['report'])
            else:
                left = indexed[case, seed, 'python']['report']
                right = indexed[case, seed, 'rust']['report']
                # run_leg already removes only the backend label from its full
                # result. Canonical JSON also distinguishes true/1 and 1/1.0,
                # unlike Python object equality, and rejects nonfinite values.
                comparable = lambda row: {k: v for k, v in row.items() if k not in {'backends', 'parity'}}
                if soak.canonical(comparable(left)) != soak.canonical(comparable(right)):
                    raise ValueError(f'Backend state/save/RNG/transcript divergence: {case} seed {seed}')
                report = deepcopy(left)
                report.update(backends=['python', 'rust'], parity=True)
            cases.append(report)
    return dict(schema='tk2-campaign-soak-v2', head=head, run_id=run_id, run_attempt=attempt,
                policy=POLICY, cases=cases, failures=[], execution_count=len(indexed))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('fragment', 'merge'):
        sub = commands.add_parser(name)
        sub.add_argument('--head', required=True)
        sub.add_argument('--run-id', required=True, type=int)
        sub.add_argument('--attempt', required=True, type=int)
        sub.add_argument('--output', required=True, type=Path)
        if name == 'fragment':
            sub.add_argument('--case', required=True, choices=soak.CASES)
            sub.add_argument('--seed', required=True, type=int, choices=SEEDS)
            sub.add_argument('--backend', required=True, choices=('both', 'python', 'rust'))
            sub.add_argument('--progress', action='store_true')
        else:
            sub.add_argument('--input-dir', required=True, type=Path)
            sub.add_argument('--execution-result', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fragment':
            result = fragment(args.case, args.seed, args.backend, head=args.head,
                run_id=args.run_id, attempt=args.attempt, progress=args.progress)
            write_json(args.output, result)
            print(json.dumps({k: result[k] for k in ('case', 'seed', 'backend', 'elapsed_seconds', 'failure')}, ensure_ascii=False))
            return int(result['failure'] is not None)
        paths = sorted(path for path in args.input_dir.rglob('*') if path.is_file() or path.is_symlink())
        if any(path.is_symlink() or path.suffix != '.json' for path in paths):
            raise ValueError('Unexpected replay artifact file')
        result = merge([json.loads(path.read_text()) for path in paths], head=args.head,
            run_id=args.run_id, attempt=args.attempt, execution_result=args.execution_result)
        write_json(args.output, result)
        print(json.dumps(dict(cases=len(result['cases']), executions=result['execution_count'], parity=True)))
        return 0
    except (ValueError, AssertionError, KeyError, TypeError) as error:
        write_json(args.output, dict(schema='tk2-campaign-soak-ci-failure-v1',
            head=args.head, run_id=args.run_id, run_attempt=args.attempt,
            error=f'{type(error).__name__}: {error}'))
        print(f'{type(error).__name__}: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
