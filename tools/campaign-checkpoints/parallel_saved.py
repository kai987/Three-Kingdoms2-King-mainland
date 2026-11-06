"""Verify an accepted saved-campaign journal in four isolated processes.

The four legs are Python/Rust x observed/baseline, with unchanged per-leg
budgets. --leg runs exactly one of these explicitly named legs. This is
recorded-command verification, never an adaptive campaign or seed search.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

_spec = importlib.util.spec_from_file_location('_parallel_saved_replay', Path(__file__).with_name('replay_saved.py'))
replay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay)
cp = replay.checkpoints
LEGS = ('python-observed', 'python-baseline', 'rust-observed', 'rust-baseline')


def sources():
    result = cp.source_hashes()
    for p in (Path(__file__).resolve(), Path(replay.__file__).resolve()):
        result[str(p.relative_to(cp.ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def identity(catalog, saved, rows, spec):
    transcript = hashlib.sha256()
    for row in rows:
        transcript.update((cp.canonical([row['command'],row['payload'],row['state_sha256']])+'\n').encode())
    return dict(catalog_sha256=cp.digest(catalog.data), origin_save_sha256=cp.digest(saved),
                journal_sha256=cp.digest(rows), command_sha256=transcript.hexdigest(), settings=spec)


def validate_leg(leg, row, expected, before, folder):
    """Missing/mislabeled/stale workers cannot certify a four-leg result."""
    if not isinstance(row,dict):
        raise ValueError('Worker report must be an object: '+leg)
    backend, observed = leg.split('-')
    if (row.get('backend') != backend or row.get('observe') is not (observed == 'observed')
            or row.get('identity') != expected or row.get('sources_before') != before
            or row.get('sources_after') != before
            or row.get('verification_status') not in ('passed','incomplete','failed')):
        raise ValueError('Worker identity/source mismatch: '+leg)
    if row['verification_status'] == 'passed':
        if type(row.get('command_count')) is not int or row['command_count'] != expected['command_count']:
            raise ValueError('Worker command count mismatch: '+leg)
        if row.get('command_sha256') != expected['command_sha256']:
            raise ValueError('Worker command transcript mismatch: '+leg)
        final = json.loads((folder/'final.save.json').read_text())
        if cp.digest(final) != row.get('final_save_sha256'):
            raise ValueError('Worker final file mismatch: '+leg)
    return row


def stop_worker(process):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def leg_main(args, catalog, saved, rows, spec):
    folder = cp.output_directory(args.output_dir)
    before = sources()
    backend, mode = args.leg.split('-')
    row = replay.replay_leg(catalog, saved, rows, spec, backend, folder, observe=mode == 'observed')
    after = sources()
    row.update(identity=dict(identity(catalog,saved,rows,spec), command_count=len(rows)),
               sources_before=before, sources_after=after)
    if before != after:
        row.update(verification_status='failed', stop_reason='sources_changed')
    cp.write(folder/'leg-report.json', row)
    return row


def run(args, catalog, saved, rows, spec, provenance):
    replay.sequence(rows)
    if not isinstance(provenance,dict) or not all(isinstance(provenance.get(k),str) and provenance[k].strip()
            for k in ('origin','selection_policy','classification')):
        raise ValueError('Explicit origin, selection_policy and classification required')
    output = cp.output_directory(args.output_dir)
    before, expected = sources(), dict(identity(catalog,saved,rows,spec), command_count=len(rows))
    cp.write(output/'origin.save.json', saved)
    cp.write(output/'provenance.json', provenance)
    (output/'input-commands.jsonl').write_text(''.join(cp.canonical(r)+'\n' for r in rows))
    report = dict(schema='tk2-parallel-saved-replay-v1', policy=replay.SavedCheckpointReplay.policy,
        identity=expected, provenance=provenance, sources_before=before, legs=[],
        verification_status='running', parallel_processes=4,
        classification='Exact recorded sequence; not four additional adaptive campaign runs')
    cp.write(output/'report.json', report)
    jobs = []
    try:
        for leg in LEGS:
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '--leg', leg,
                '--scenario', args.scenario, '--start-save', str(output/'origin.save.json'),
                '--journal', str(output/'input-commands.jsonl'), '--provenance', str(output/'provenance.json'),
                '--turns', str(spec['turns']), '--max-seconds', str(spec['max_seconds']),
                '--max-commands', str(spec['max_commands']), '--output-dir', str(output/leg)]
            with (output/(leg+'.log')).open('w') as stream:
                process = subprocess.Popen(command, cwd=cp.ROOT, stdout=stream, stderr=subprocess.STDOUT)
            jobs.append((leg, process, time.monotonic()))
            cp.write(output/'workers.json', [dict(leg=key, pid=p.pid, command=p.args) for key,p,_ in jobs])
        for leg, process, started in jobs:
            try:
                # Grace permits interpreter/startup/final evidence I/O, not
                # more game commands: replay_leg enforces its original budget.
                code = process.wait(timeout=max(0, spec['max_seconds']+60-(time.monotonic()-started)))
                row = json.loads((output/leg/'leg-report.json').read_text())
                validate_leg(leg, row, expected, before, output/leg)
                if code != 0 and row['verification_status'] == 'passed':
                    raise ValueError('Successful worker report with nonzero exit')
            except subprocess.TimeoutExpired:
                stop_worker(process)
                row = dict(backend=leg.split('-')[0], observe=leg.endswith('-observed'),
                    verification_status='incomplete', stop_reason='worker_wall_time', initialized=False)
            except (ValueError, KeyError, OSError) as exc:
                row = dict(backend=leg.split('-')[0], observe=leg.endswith('-observed'),
                    verification_status='failed', stop_reason='worker_evidence_error', error=str(exc), initialized=False)
            report['legs'].append(row)
            cp.write(output/'report.json', report)
    except OSError as exc:
        report['legs'].append(dict(verification_status='failed', stop_reason='worker_launch_error',error=str(exc)))
    finally:
        for _,process,_ in jobs:
            stop_worker(process)
    states = [r['verification_status'] for r in report['legs']]
    status = ('failed' if len(states)!=4 or 'failed' in states else
              'incomplete' if 'incomplete' in states else 'passed')
    signatures = [(r.get('command_count'),r.get('command_sha256'),r.get('final_save_sha256'))
        for r in report['legs']]
    parity = 'passed' if status=='passed' and all(r==signatures[0] for r in signatures) else 'unverified'
    if status=='passed' and parity!='passed': status='failed'
    after = sources()
    raw_equal = False
    if parity == 'passed':
        try:
            raw_equal = all((output/leg/'final.save.json').read_bytes()==(output/LEGS[0]/'final.save.json').read_bytes()
                            and (output/leg/'commands.jsonl').read_bytes()==(output/LEGS[0]/'commands.jsonl').read_bytes()
                            for leg in LEGS)
        except OSError:
            raw_equal = False
        if not raw_equal: status,parity='failed','failed'
    origin_unchanged = cp.digest(saved)==expected['origin_save_sha256']
    report.update(verification_status=status if before==after and origin_unchanged else 'failed', parity=parity,
        sources_after=after, sources_unchanged=before==after,
        origin_unchanged=origin_unchanged, complete_raw_save_and_journal_equal=raw_equal)
    cp.write(output/'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--start-save', type=Path, required=True)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--turns', type=int, default=36)
    parser.add_argument('--max-commands', type=int, default=5000)
    parser.add_argument('--max-seconds', type=float, default=300)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--leg', choices=LEGS, help='Run one explicit independent leg instead of all four')
    args = parser.parse_args(argv)
    try:
        catalog = cp.indexed_catalog(args.scenario)
        saved = json.loads(args.start_save.read_text())
        rows = replay.sequence([json.loads(line) for line in args.journal.read_text().splitlines() if line.strip()])
        spec = cp.settings(catalog,saved['state']['player'],saved['state']['seed'],args.turns,args.max_commands,args.max_seconds)
        provenance = json.loads(args.provenance.read_text())
        if not isinstance(provenance,dict) or not all(isinstance(provenance.get(k),str) and provenance[k].strip()
                for k in ('origin','selection_policy','classification')):
            raise ValueError('Explicit origin, selection_policy and classification required')
        report = leg_main(args,catalog,saved,rows,spec) if args.leg else run(args,catalog,saved,rows,spec,provenance)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({k:report.get(k) for k in ('verification_status','parity','sources_unchanged')},ensure_ascii=False))
    return 0 if report['verification_status']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
