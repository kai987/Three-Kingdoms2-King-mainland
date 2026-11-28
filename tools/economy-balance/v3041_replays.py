"""Replay archived checkpoints without changing their weather, ownership or RNG."""
from argparse import ArgumentParser, Namespace
from collections import Counter, defaultdict
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
from remake import city_economy, grain_units, logistics, transport_capacity, transport_coordination
from remake.campaign import digest, verified_save_content
from v3031_experiments import options as capacity_options
import v303_capacity_audit as capacity_replay
import v231_replay as winter_replay
from v231_observe import CampaignObservation
from v3041_campaigns import settings

GROUPS = ('T0', 'T2', 'T3', 'T5')


def enable(stack, game, name, observe):
    flags = settings(name)
    if name in ('T4', 'T5'):
        stack.enter_context(transport_capacity.fixed_replay(game.state, capacity_options('D2')))
    if name in ('T2', 'T3', 'T5'):
        transport_coordination.initialize(game.state, flags[transport_coordination.FIELD],
                                          flags[transport_coordination.OPTIONS])
    if observe:
        stack.enter_context(transport_coordination.observing(observe, shadow=name == 'T1'))


def fixed_case(task, *, include_deadline_settlement=False):
    from v3021_checkpoints import campaign, configure

    def context(stack, fixture, group):
        configure(stack, fixture['strategy'], fixture['weather'])
        game = campaign(fixture['scenario'])
        game.load_save(fixture['save'], 0)
        enable(stack, game, group, None)
        return game

    with patch.object(capacity_replay, 'replay_context', context):
        return capacity_replay.fixed_replay(task, include_deadline_settlement=include_deadline_settlement)


def fixed_accounted_case(task, *, record_meal=None, include_deadline_settlement=False):
    target_keys = {(row['owner'], row['target']) for row in task[2]}
    capacity, coordination, provisions = [], [], defaultdict(dict)
    observe = transport_capacity.observing
    settle_grain = city_economy.settle_turn_grain

    def monitored(record):
        def collect(kind, row):
            if kind in ('departure', 'terminal'):
                capacity.append(dict(event=kind, **row))
            record(kind, row)
        return observe(collect)

    class SourceRations(CampaignObservation):
        def write(self, kind, row):
            key = row['owner'], row['city']
            provisions[key][row['turn']] = row['missing']
            if record_meal is not None and key in target_keys:
                record_meal(row)

    rations = SourceRations(None, flows=True)

    def settle(game, state):
        rations.city_meal(game, state)
        return settle_grain(game, state)

    def record(kind, row):
        if kind == 'dispatch':
            coordination.append(row)

    with (patch.object(transport_capacity, 'observing', monitored),
          patch.object(city_economy, 'settle_turn_grain', settle),
          transport_coordination.observing(record)):
        data, sources, trace = fixed_case(task, include_deadline_settlement=include_deadline_settlement)

    launches = {row['id']: row for row in capacity if row['event'] == 'departure'}
    endings = {row['id']: row for row in capacity if row['event'] == 'terminal'}
    actual = {row['convoy']: row for row in coordination if row['convoy']}
    account = {}
    for ident, depart in launches.items():
        if ((depart['owner'], depart['target']) not in target_keys
                or depart['purpose'] not in ('ordinary', 'strategic', 'regional') or not depart['cargo']['grain']):
            continue
        end = endings.get(ident)
        claimed = actual.get(ident)
        start = (depart['turn']-1)*10
        days = max(0, end['end_tick']-start) if end else None
        free = (end['reusable_turn']-1)*10-end['end_tick'] if end and end['reusable_turn'] else 0
        after = provisions[depart['owner'], depart['source']]
        days_observed = [value for turn, value in after.items() if turn >= depart['turn']]
        books = claimed['books_used'] if claimed else depart['command_books']+(depart['purpose'] == 'regional')
        account[ident] = dict(convoy=ident, books=books, escorts=depart['officers'], terminal=end,
            issued_stock_grain=depart['cargo']['grain'], start_turn=depart['turn'],
            source=depart['source'], target=depart['target'], owner=depart['owner'],
            officer_days=(days*sum(type(key) is int for key in depart['officers']) +
                max(0, free)*sum(type(key) is int for key in end['received_officers'])) if end else None,
            clerk_days=(days*sum(type(key) is str for key in depart['officers']) +
                max(0, free)*sum(type(key) is str for key in end['received_officers'])) if end else None,
            source_shortage_turns=sum(value > 0 for value in days_observed),
            source_grain_shortage=sum(days_observed), source_turns_observed=len(days_observed))
    for row in data:
        qualified = [record for record in account.values() if record['owner'] == row['owner']
                     and record['target'] == row['target'] and record['start_turn'] < row['deadline_turn']]
        row.update(fixed_dispatches=len(qualified), books_spent=sum(record['books'] for record in qualified),
            measured_officer_days=sum(record['officer_days'] or 0 for record in qualified),
            measured_clerk_days=sum(record['clerk_days'] or 0 for record in qualified),
            staff_period_incomplete=sum(record['officer_days'] is None for record in qualified),
            sources_with_post_departure_shortage=sorted({record['source'] for record in qualified
                                                        if record['source_shortage_turns']}))
    trace['related_dispatch_accounts'] = list(account.values())
    return data, sources, trace


def fixed(args):
    spec = Namespace(prior=args.reference, output=args.output, checkpoints=args.checkpoints,
                     groups=args.group, workers=args.workers)
    capacity_replay.fixed(spec, replay=fixed_accounted_case if args.account else fixed_case)


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
    tasks = [(p, name, args.turns, args.output/'events') for p in paths for name in args.group]
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
        turns=len(timings), full_turn_cpu_p50=median(timings),
        full_turn_cpu_p95=timings[(95*len(timings)-1)//100],
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


def historical(args, *, capture_state=None):
    from v3021_checkpoints import campaign, configure
    from v3031_replays import convoy_snapshot

    results = []
    for sample in args.samples:
        raw_id, raw_path = sample.split(',', 1)
        ident, path = int(raw_id), Path(raw_path)
        fixture = capacity_replay.checkpoint(path)
        if 'save' not in fixture:
            frame = verified_save_content(fixture)
            state = frame['state']
            fixture = dict(save=fixture, scenario=frame['scenario'].removeprefix('mainland'), seed=state['seed'],
                           strategy=state['extension'].get('ai_logistics_strategy_version', 211),
                           weather=state['extension'].get('weather_rules_version', 0))
        for group in args.group:
            game = campaign(fixture['scenario'])
            receipts, snapshots = [], []
            transport_event = logistics._event

            def account(kind, row):
                if row.get('id') == ident:
                    receipts.append(dict(event=kind, row=row))

            def assets(engine, state, event, convoy, **values):
                result = transport_event(engine, state, event, convoy, **values)
                if event == 'transport_returned' and convoy['id'] == ident:
                    receipts.append(dict(event='returned_assets', row=dict(
                        turn=state.turn, city=convoy['target'], owner=convoy['owner'], cargo=dict(convoy['cargo']))))
                return result

            with ExitStack() as stack:
                configure(stack, fixture['strategy'], fixture['weather'], detailed=True)
                game.load_save(fixture['save'], 0)
                initial = digest(game.to_dict())
                enable(stack, game, group, None)
                stack.enter_context(transport_capacity.observing(account))
                stack.enter_context(patch.object(logistics, '_event', assets))
                for _ in range(args.turns + 1):
                    with grain_units.using(game.state):
                        state = convoy_snapshot(game, ident)
                        if state is not None:
                            convoy = next(row for row in logistics._pool(game.state)['convoys'] if row['id'] == ident)
                            state['aboard_resources'] = dict(convoy['cargo'])
                    snapshots.append(dict(turn=game.state.turn, convoy=state))
                    if capture_state is not None and state is not None:
                        capture_state(game, state)
                    if len(snapshots) > args.turns or game.state.phase == 'finished':
                        break
                    game.command('observe_turn', {}, game.revision)
                if snapshots[0]['convoy'] is None:
                    raise ValueError(f'Convoy {ident} missing at its historical opening')
            results.append(dict(group=group, checkpoint=path.name, scenario=fixture['scenario'],
                seed=fixture['seed'], strategy=fixture['strategy'], winter=fixture['weather'], convoy=ident,
                checkpoint_sha256=sha256(path.read_bytes()), initial_state_sha256=initial,
                snapshots=snapshots, receipts=receipts, final_state_sha256=digest(game.to_dict())))
            print(ident, group, 'turns', len(snapshots)-1, 'still_active', snapshots[-1]['convoy'] is not None,
                  flush=True)
    to_json(args.output/'historical-convoy-safety.json',
            dict(source=git('rev-parse', 'HEAD').decode().strip(), results=results))


def main():
    parser = ArgumentParser(description=__doc__)
    phases = parser.add_subparsers(dest='mode', required=True)
    for name, fn in (('fixed', fixed), ('south', south), ('performance', performance), ('historical', historical)):
        phase = phases.add_parser(name)
        phase.set_defaults(execute=fn)
        phase.add_argument('output', type=Path)
        if name != 'historical':
            phase.add_argument('--workers', type=int, default=3)
        if name in ('fixed', 'south'):
            phase.add_argument('reference', type=Path)
            phase.add_argument('checkpoints', nargs='+', type=Path)
        else:
            phase.add_argument('samples', nargs='+')
        if name != 'performance':
            phase.add_argument('--group', nargs='+', choices=(*GROUPS, 'T4'),
                               default=['T0', 'T3'] if name == 'historical' else list(GROUPS))
        if name != 'fixed':
            phase.add_argument('--turns', type=int, default=9 if name == 'south' else 3)
        if name == 'fixed':
            phase.add_argument('--account', action='store_true')
    args = parser.parse_args()
    args.execute(args)


if __name__ == '__main__':
    main()
