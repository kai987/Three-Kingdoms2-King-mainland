"""Run matched transport coordination campaigns through the real turn engine."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import ROOT, git, sha256, to_json
from observe import RecordedCampaign
from remake import transport_capacity, transport_coordination
from v3031_experiments import options as capacity_options
from v231_observe import QUICK, FIVE, LONG, run

ADDITIONAL = (2031, '190-01', 211)
HOLDOUT = ((2045, '184-02', 211), (2046, '208-10', 212))
HISTORICAL = ((2041, '184-02', 211), (2042, '208-10', 212),
              (2043, '184-02', 211), (2044, '208-10', 212))
WAVES = dict(smoke=(QUICK[2:4], 2), quick=(QUICK, 24),
             five=((*FIVE, ADDITIONAL), 60), long=(LONG, 240),
             holdout=(HOLDOUT, 60), historical=(HISTORICAL, 60))


def settings(group):
    fields = {}
    if group in ('T4', 'T5'):
        fields.update(transport_capacity_rules_version=303,
                      transport_capacity_options=capacity_options('D2'))
    if group in ('T2', 'T3', 'T5'):
        fields.update(transport_coordination_rules_version=3041,
                      transport_coordination_options=dict(efficiency=group != 'T2'))
    return fields


def execute(task):
    output, spec = task
    group, wave = spec['variant'], spec['wave']
    base = output/group
    path = base/'campaigns'/wave/'F4'/f"{spec['scenario']}-{spec['seed']}-{spec['strategy']}"
    path.mkdir(parents=True, exist_ok=True)
    identity = dict(spec, options=settings(group))
    record_path = path/'run-v3041.json'
    if record_path.exists():
        past = json.loads(record_path.read_text())
        if past['case'] == identity and past['result']['outcome'] in ('complete', 'natural_end'):
            return past
    if (path/'run-v231.json').exists():
        raise ValueError(f'Unexpected existing run at {path}. Choose a new output directory.')
    original = RecordedCampaign.command

    def command(game, action, payload, revision):
        if action == 'new':
            payload = dict(payload, **settings(group))
            if spec.get('winter_221'):
                payload = {key: value for key, value in payload.items()
                           if key not in ('weather_options', 'weather_forecast_version')}
                payload['weather_rules_version'] = 221
        return original(game, action, payload, revision)

    with ExitStack() as stack:
        ledger = stack.enter_context(gzip.open(path/'coordination.jsonl.gz', 'wt', compresslevel=2, encoding='utf-8'))
        convoy = stack.enter_context(gzip.open(path/'capacity.jsonl.gz', 'wt', compresslevel=2, encoding='utf-8'))

        def track(stream, event, row):
            stream.write(json.dumps(dict(event=event, **row), ensure_ascii=False, separators=(',', ':')) + '\n')

        stack.enter_context(transport_coordination.observing(
            lambda event, row: track(ledger, event, row), shadow=group == 'T1'))
        stack.enter_context(transport_capacity.observing(lambda event, row: track(convoy, event, row)))
        stack.enter_context(patch.object(RecordedCampaign, 'command', command))
        result = run(base, dict(spec, group='F4'))
    final = path/'terminal-save.json.gz'
    proof = dict(case=identity, result=result, scenario_sha256=sha256(
        (ROOT/'game/data/campaigns'/f"{spec['scenario']}.json").read_bytes()),
        terminal_checksum=json.loads(gzip.decompress(final.read_bytes()))['checksum'] if final.exists() else None,
        output=str(path.relative_to(output)))
    to_json(record_path, proof)
    print(json.dumps(dict(case=identity, outcome=result['outcome'], turns=result['completed_turns']), ensure_ascii=False),
          flush=True)
    return proof


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('wave', choices=WAVES)
    parser.add_argument('output', type=Path)
    parser.add_argument('--group', nargs='+', choices=('T0', 'T1', 'T2', 'T3', 'T4', 'T5'), required=True)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--scenario', action='append')
    parser.add_argument('--strategy', action='append', type=int)
    parser.add_argument('--winter-221', action='store_true')
    args = parser.parse_args()
    source = git('rev-parse', 'HEAD').decode().strip()
    diff = sha256(git('diff', 'HEAD', '--binary', '--', 'source', 'game', 'tools', 'tests'))
    rows, months = WAVES[args.wave]
    tasks = [(args.output, dict(wave=args.wave, variant=group, scenario=scene, seed=seed, strategy=strategy,
               months=months, source=source, source_diff_sha256=diff, winter_221=args.winter_221))
             for seed, scene, strategy in rows for group in args.group
             if (not args.scenario or scene in args.scenario) and (not args.strategy or strategy in args.strategy)]
    if not tasks:
        parser.error('No campaign matches the requested filters')
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        reports = list(pool.map(execute, tasks))
    if any(row['result']['outcome'] not in ('complete', 'natural_end') for row in reports):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
