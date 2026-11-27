"""Replay archived checkpoints without changing their weather, ownership or RNG."""
from argparse import ArgumentParser, Namespace
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
from resource import RUSAGE_SELF, getrusage
from statistics import median
import sys
from time import process_time
from unittest.mock import patch

from common import git, sha256, to_csv, to_json
from remake import logistics, transport_capacity, transport_coordination
from remake.campaign import digest
from v3031_experiments import options as capacity_options
import v303_capacity_audit as capacity_replay
import v231_replay as winter_replay
from v3041_campaigns import settings

GROUPS = ('T0', 'T2', 'T3', 'T5')


def enable(stack, game, name, observe):
    flags = settings(name)
    if name == 'T5':
        stack.enter_context(transport_capacity.fixed_replay(game.state, capacity_options('D2')))
    if name in ('T2', 'T3', 'T5'):
        transport_coordination.initialize(game.state, flags[transport_coordination.FIELD],
                                          flags[transport_coordination.OPTIONS])
    if observe:
        stack.enter_context(transport_coordination.observing(observe, shadow=name == 'T1'))


def fixed_case(task):
    from v3021_checkpoints import campaign, configure

    def context(stack, fixture, group):
        configure(stack, fixture['strategy'], fixture['weather'])
        game = campaign(fixture['scenario'])
        game.load_save(fixture['save'], 0)
        enable(stack, game, group, None)
        return game

    with patch.object(capacity_replay, 'replay_context', context):
        return capacity_replay.fixed_replay(task)


def fixed(args):
    spec = Namespace(prior=args.reference, output=args.output, checkpoints=args.checkpoints,
                     groups=args.group, workers=args.workers)
    capacity_replay.fixed(spec, replay=fixed_case)


def inspect_checkpoint(path, scenario, strategy, group, turns, *, observation, city=None, events_path=None):
    original = winter_replay.HeadlessCampaign.load_save
    events, work = [], Counter()

    def sample(event, row):
        if event == 'scheduler':
            work.update({key: row.get(key, 0) for key in (
                'scheduler_cpu', 'demand_count', 'candidate_count', 'pruned_candidates', 'pruned_demands',
                'economic_plans', 'trip_cache_hits', 'measured_trips', 'committed', 'failed')})
        if events_path is not None and (event == 'scheduler' or city in (row.get('target'), row.get('demand_target'))):
            events.append(dict(kind=event, **row))

    with ExitStack() as stack:
        def load(game, data, revision):
            result = original(game, data, revision)
            opening = game.to_dict()
            enable(stack, game, group, sample if observation else None)
            result_data.update(input_state_sha256=digest(opening), input_rng=opening['rng'])
            return result

        result_data = {}
        stack.enter_context(patch.object(winter_replay.HeadlessCampaign, 'load_save', load))
        began = process_time()
        metrics = winter_replay.play(path, scenario, strategy, 'F4', turns, city=city, observe=observation)
        runtime = process_time()-began
    if events_path is not None:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(events_path, 'wt', encoding='utf-8') as out:
            for row in events:
                out.write(json.dumps(row, ensure_ascii=False)+'\n')
    return dict(metrics, **result_data, group=group, checkpoint=path.name,
                checkpoint_sha256=sha256(path.read_bytes()), scheduler=dict(work), profiled_cpu=runtime,
                peak_memory_bytes=getrusage(RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024))


def south_case(task):
    path, variant, turns, output = task
    city = path.name.split('-', 1)[1].removesuffix('.json.gz')
    result = inspect_checkpoint(path, '208-10', 211, variant, turns, observation=True, city=city,
                                events_path=output/f'{city}-{variant}.jsonl.gz')
    print(city, variant, 'missing', result['missing'], flush=True)
    return result


def south(args):
    reference = capacity_replay.read_csv(args.reference)
    original = {row['checkpoint']:row for row in reference if row['group'] == 'F4'}
    assert len(original) == 8
    paths = [args.checkpoints[0]/key for key in sorted(original)]
    for path in paths:
        assert sha256(path.read_bytes()) == original[path.name]['source'], path
    tasks = [(p, name, args.turns, args.output/'events') for p in paths for name in GROUPS]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(south_case, tasks))
    to_json(args.output/'southern-basin-replay.json', dict(source=git('rev-parse', 'HEAD').decode().strip(),
                                                          results=results))
    rows = []
    for row in results:
        opening = row['initial']['legal']
        before = int(original[row['checkpoint']]['missing'])
        rows.append(dict(checkpoint=row['checkpoint'], sha256=row['checkpoint_sha256'],
            city=row['city'], group=row['group'], owner=opening['owner'], legal_sources=opening['legal_sources'],
            minimum_eta=opening['minimum_eta'], other_faction_stock=opening['other_faction_stock'],
            missing=row['missing'], previous_F4_missing=before, delta=row['missing']-before,
            shortage_turns=row['shortages'], settlement_turn=row['final']['turn'],
            convoy_grain=sum(receipt['grain'] for receipt in row['market_transport_receipts']
                if receipt['city'] == row['city']), blockers=opening['blockers']))
    to_csv(args.output/'city-shortage-checkpoint-replay.csv', rows)


def performance_case(task):
    label, scene, strategy, path, turns, group, observation = task
    series = [inspect_checkpoint(path, scene, strategy, group, turns, observation=observation)
              for _ in range(3)]
    sample = series[0]
    assert all(row['final'] == sample['final'] for row in series)
    timings = sorted(t for row in series for t in row['cpu'])
    totals = Counter()
    for row in series:
        totals.update(row['scheduler'])
    return dict(label=label, scenario=scene, strategy=strategy, checkpoint=path.name,
        sha256=sample['checkpoint_sha256'], group=group, observation=observation, repeats=len(series),
        turns=len(timings), full_turn_cpu_p50=median(timings), full_turn_cpu_p95=timings[-1],
        route_queries=sum(row['route_search_calls'] for row in series),
        peak_memory=max(row['peak_memory_bytes'] for row in series), **dict(totals),
        final=sample['final'], measurements=series)


def performance(args):
    tasks = []
    for spec in args.samples:
        label, scene, raw_strategy, raw_path = spec.split(',', 3)
        for group in args.group:
            for observe in (False, True):
                tasks.append((label, scene, int(raw_strategy), Path(raw_path), args.turns, group, observe))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(performance_case, tasks))
    for plain, observed in zip(rows[::2], rows[1::2], strict=True):
        assert plain['final'] == observed['final']
    to_json(args.output/'scheduler-performance-profile.json',
            dict(source=git('rev-parse', 'HEAD').decode().strip(), results=rows))
    fields = list(dict.fromkeys(key for row in rows for key in row if key not in ('final', 'measurements')))
    to_csv(args.output/'scheduler-performance-profile.csv', ({key: row.get(key) for key in fields} for row in rows))


def main():
    parser = ArgumentParser(description=__doc__)
    phases = parser.add_subparsers(dest='mode', required=True)
    for name, fn in (('fixed', fixed), ('south', south), ('performance', performance)):
        phase = phases.add_parser(name)
        phase.set_defaults(execute=fn)
        phase.add_argument('output', type=Path)
        phase.add_argument('--workers', type=int, default=3)
        if name != 'performance':
            phase.add_argument('reference', type=Path)
            phase.add_argument('checkpoints', nargs='+', type=Path)
        else:
            phase.add_argument('samples', nargs='+')
        phase.add_argument('--group', nargs='+', choices=GROUPS, default=list(GROUPS) if name == 'fixed' else ['T0', 'T3'])
        phase.add_argument('--turns', type=int, default=9 if name == 'south' else 3)
    args = parser.parse_args()
    args.execute(args)


if __name__ == '__main__':
    main()
