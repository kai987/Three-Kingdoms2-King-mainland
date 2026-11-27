"""Run V3.0.4.1.1 experiments against hashes restored from previous real runs."""
from argparse import ArgumentParser, Namespace
from contextlib import contextmanager
from functools import partial
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import sha256, to_json
from remake import transport_coordination as coordination
import v3041_replays as legacy
from v3041_campaigns import settings as previous_settings
from v3031_experiments import options as capacity_options

OLD = {'U0': 'T0', 'U1': 'T3', 'V0': 'T4', 'V1': 'T5'}
PAGINATION = ('pagination',)
QUOTES = (*PAGINATION, 'diversity', 'requote')
SOURCE = (*QUOTES, 'reserve')
COMPETITION = (*SOURCE, 'preparation', 'transit')
FINAL = (*COMPETITION, 'economics', 'incremental')
OPTIONS = {'U2': PAGINATION, 'U3a': (*PAGINATION, 'diversity'), 'U3b': (*PAGINATION, 'requote'),
           'U3': QUOTES, 'U4': SOURCE, 'U5p': (*SOURCE, 'preparation'),
           'U5t': (*SOURCE, 'transit'), 'U5': COMPETITION, 'U6': FINAL,
           'U6-full': FINAL[:-1], 'V2': FINAL}
ALL_GROUPS = (*OLD, *OPTIONS)
old_enable = legacy.enable


def settings(group):
    if group in OLD:
        return previous_settings(OLD[group])
    fields = {coordination.FIELD: coordination.RECOVERY,
              coordination.OPTIONS: {'features': {name: name in OPTIONS[group] for name in coordination.FEATURES}}}
    if group == 'V2':
        fields.update(transport_capacity_rules_version=303,
                      transport_capacity_options=capacity_options('D2'))
    return fields


def enable(stack, game, group, observe):
    if group in OLD:
        return old_enable(stack, game, OLD[group], observe)
    if group == 'V2':
        old_enable(stack, game, 'T4', None)
    flags = settings(group)
    coordination.initialize(game.state, flags[coordination.FIELD], flags[coordination.OPTIONS])
    if observe is not None:
        stack.enter_context(coordination.observing(observe))


def fixed_with_trace(task, *, output):
    path, group, targets, _ = task
    keys = {(row['owner'], row['target']) for row in targets}
    opening = legacy.capacity_replay.checkpoint(path)['turn']
    recorded = []
    observer = coordination.observing

    @contextmanager
    def collect(record, *, shadow=False):
        def sample(event, row):
            record(event, row)
            target = row.get('demand_target', row.get('target'))
            if (event in ('candidate', 'demand', 'dispatch', 'dispatch_failed', 'receipt') and
                    (row.get('owner'), target) in keys or event in ('scheduler', 'military_preparation_request',
                    'military_preparation_expired', 'transit_refill_budget')):
                if event not in ('military_preparation_request', 'military_preparation_expired') or row['turn'] <= opening + 2:
                    recorded.append(dict(event=event, **row))
        with observer(sample, shadow=shadow):
            yield

    with (patch.object(legacy, 'enable', enable),
          patch.object(coordination, 'observing', collect)):
        rows, sources, trail = legacy.fixed_accounted_case(task)
    raw = output/'decision-traces'
    raw.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw/f'{path.stem}-{group}.jsonl.gz', 'wt', compresslevel=3, encoding='utf-8') as stream:
        for row in recorded:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n')
    return rows, sources, dict(trail, decision_events=len(recorded))


def checked_inputs(root):
    rows = json.loads((root/'input-manifest.json').read_bytes())
    for row in rows:
        if row['restored'] and sha256((root/row['file']).read_bytes()) != row['sha256']:
            raise ValueError(f"Replay input has changed: {row['file']}")
    return rows


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('fixed', 'south', 'performance', 'historical'))
    parser.add_argument('inputs', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--group', nargs='+', choices=ALL_GROUPS, required=True)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--prior-south', type=Path)
    parser.add_argument('--turns', type=int)
    args = parser.parse_args()
    manifest = checked_inputs(args.inputs)
    files = {row['label']: args.inputs/row['file'] for row in manifest
             if row['group'] == args.phase and row['restored']}
    if args.phase == 'fixed':
        spec = Namespace(prior=args.inputs/'reference', output=args.output,
                         checkpoints=list(files.values()), groups=args.group, workers=args.workers)
        legacy.capacity_replay.fixed(spec, replay=partial(fixed_with_trace, output=args.output))
    elif args.phase == 'historical':
        for convoy, periods in (('2', 34), ('3634', 12), ('1860', 12), ('2170', 9), ('45', 9), ('77', 9)):
            if convoy in files:
                with patch.object(legacy, 'enable', enable):
                    legacy.historical(Namespace(samples=[f'{convoy},{files[convoy]}'], group=args.group,
                                                output=args.output/convoy, turns=args.turns or periods))
    else:
        # Workers are spawned on macOS; configure the wrapped engine inside each worker.
        from concurrent.futures import ProcessPoolExecutor
        tasks = [(args.phase, row, files[row['label']], group, args.turns, args.output)
                 for row in manifest if row['group'] == args.phase and row['restored']
                 for group in args.group]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(other_case, tasks))
        if args.phase == 'south' and args.prior_south:
            baseline = {row['checkpoint']: row['missing'] for row in legacy.capacity_replay.read_csv(args.prior_south)
                        if row['group'] == 'T0'}
            for result in results:
                result['historical_t0_missing'] = int(baseline[result['label']])
        to_json(args.output/f'{args.phase}-results.json', dict(results=results,
                groups={group: settings(group) for group in args.group}))


def other_case(task):
    phase, spec, path, group, turns, output = task
    label = spec['label']
    with patch.object(legacy, 'enable', enable):
        if phase == 'south':
            city = path.name.split('-', 1)[1].removesuffix('.json.gz')
            result = legacy.inspect_checkpoint(path, spec['scenario'], spec['strategy'], group,
                turns or 9, observation=True, city=city, events_path=output/'events'/f'{city}-{group}.jsonl.gz')
            return dict(result, label=label)
        samples = [legacy.performance_case((label, spec['scenario'], spec['strategy'],
                   path, turns or 3, group, observed)) for observed in (False, True)]
    assert samples[0]['final'] == samples[1]['final'], (label, group)
    return dict(label=label, group=group, samples=samples)


if __name__ == '__main__':
    main()
