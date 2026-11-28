"""Replay the original logistics fixtures under matched V3.0.4.1.2 settings."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import cProfile
from contextlib import ExitStack
import gzip
import json
from math import ceil
from pathlib import Path
from statistics import median
from unittest.mock import patch

from common import git, sha256, to_csv, to_json
from remake import command_books, convoy_relief, facilities, faction_economy, grain_dispatch, grain_units
from remake import logistics, logistics_strategy, strategic_granary, transport_demands
from remake import transport_capacity, transport_coordination as coordination, transport_emergency
from remake.campaign import digest
import v3041_replays as legacy
import v30411_audit as audit
import v30411_replays as previous


MATCHED = {'K0': 'U0', 'K1': 'U6', 'L0': 'V0', 'L1': 'V2'}
GROUPS = ('K0', 'K1', 'K2', 'L0', 'L1', 'L2',
          'K2-no-cache', 'L2-no-cache', 'K2-no-transit', 'L2-no-transit')
HISTORICAL = {**previous.HISTORICAL_WINDOWS}
enable_previous = previous.enable


def settings(group):
    if group in MATCHED:
        return previous.settings(MATCHED[group])
    options = {}
    if group.startswith('L'):
        options.update(previous.settings('V0'))
    features = {name: True for name in sorted(coordination.CONSUMPTION_FEATURES)}
    if group.endswith('-no-cache'):
        features['route_reuse'] = False
    if group.endswith('-no-transit'):
        features['transit'] = False
    options.update({coordination.FIELD: coordination.CONSUMPTION,
                    coordination.OPTIONS: {'features': features}})
    return options


def enable(stack, game, group, observer):
    if group in MATCHED:
        return enable_previous(stack, game, MATCHED[group], observer)
    if group.startswith('L'):
        enable_previous(stack, game, 'V0', None)
    flags = settings(group)
    coordination.initialize(game.state, flags[coordination.FIELD], flags[coordination.OPTIONS])
    if observer is not None:
        stack.enter_context(coordination.observing(observer))


def verified_inputs(root, reference):
    local = previous.checked_inputs(root)
    archived = json.loads(reference.read_bytes())
    keys = ('group', 'label', 'file', 'sha256', 'restored')
    expected = {tuple(row.get(key) for key in keys) for row in archived}
    if {tuple(row.get(key) for key in keys) for row in local} != expected:
        raise ValueError('Replay inputs differ from the archived manifest')
    return archived


def quantiles(values):
    values = sorted(values)
    return {'p50': median(values), 'p95': values[ceil(.95 * len(values)) - 1], 'max': values[-1]}


def rule_snapshot(game):
    ext = game.state.extension
    keys = ('economy_rules_version', 'logistics_rules_version', 'weather_rules_version',
            'winter_weather', 'winter_forecast_version', 'weather_forecast_version',
            'transport_emergency_rules_version', 'regional_market_rules_version',
            'strategic_granary_rules_version', 'transport_capacity_rules_version',
            'transport_capacity_options', 'transshipment_rules_version',
            'transport_coordination_rules_version')
    result = {key: ext.get(key, 0) for key in keys}
    result['winter_weather'] = result['winter_weather'].get('options', {}) if result['winter_weather'] else {}
    result['effective_capacity_options'] = (dict(ext[transport_capacity.POOL]['features'])
        if transport_capacity.enabled(game.state) else None)
    return result


def fixed_task(task, output):
    path, group, targets, returning = task
    with patch.object(previous, 'enable', enable):
        return audit.safety_case((path, group, targets, returning), output=output,
                                 capacity_limit=2 if group.startswith('L') else 1, actual=True)


def constraint_task(task, output):
    path, group, _, _ = task
    focus = ('anding', 'donglai', 'fufeng')
    owner = 'wei'
    trace, snapshots = [], []
    discover = coordination._discover
    command = legacy.winter_replay.HeadlessCampaign.command

    def sample(game, state, plan, demands, *, stage):
        groups, blocked = grain_dispatch._donors(game, state, plan, coordinated=coordination.enabled(state),
                                               reserve=coordination.feature(state, 'reserve'))
        selected = {key: (escort, floor) for rows in groups.values() for key, escort, _, floor in rows}
        slots = transport_capacity.activity(state)
        donors = [
            dict(city=key, gold=state.cities[key].gold, grain=state.cities[key].grain, selected_escort=selected.get(key, (None,))[0],
                 commitments=budget['reserved_grain'], safety_floor=budget['safety_reserve'],
                 eligible_export=budget['exportable'], active_slots=transport_capacity.active_count(
                     state, state.cities[key], slots), dispatched=transport_capacity.dispatch_count(state, key),
                 exclusion=blocked.get(key))
            for key, budget in plan.budgets.items()
        ]
        known = {row.target: row for row in demands if row.kind == 'city'}
        for key in focus:
            city = state.cities[key]
            forecast = plan.cities.get(key)
            if not forecast:
                continue
            demand = known.get(key)
            offers = facilities.emergency_quote(game, state, city, forecast.monthly*2)
            snapshots.append(dict(stage=stage, turn=state.turn, owner=owner, city=key,
                grain=city.grain, gold=city.gold, command_books=command_books.remaining(state, owner),
                market_stock=offers['market_stock'], market_rate=offers['rate'], max_local_purchase=offers['grain'],
                local_purchase_blocker=offers['blocked_reason'], reliable_receipts=forecast.receipts,
                conditional_receipts=forecast.conditional_receipts, dated_inbound=forecast.convoy_receipts,
                next_city_bills=[due for _,due,_ in forecast.timeline], first_gap=forecast.first_missing,
                current_deadline=demand.deadline if demand else None, origins=donors))

    def capture(game, state, faction, plan, priority, additional):
        result = discover(game, state, faction, plan, priority, additional)
        if faction == owner:
            sample(game, state, plan, result[0], stage=priority)
        return result

    def city_snapshot(game, action, payload, revision):
        if action == 'observe_turn':
            state = game.state
            before = digest(game.to_dict())
            with grain_units.using(state):
                plan = faction_economy.plan(game, state, owner, granary=strategic_granary.enabled(state),
                                           coordinated=coordination.enabled(state))
                demands = [row for key in focus if key in plan.cities and (
                    row := transport_demands.city_shortage(game, state, plan, key))]
                sample(game, state, plan, demands, stage='opening')
            assert before == digest(game.to_dict()), 'Read-only constraints changed the checkpoint'
        return command(game, action, payload, revision)

    def record(kind, row):
        if row.get('owner') == owner and (kind in ('dispatch','dispatch_failed','transport_departed') or
                kind in ('candidate','demand','receipt') and row.get('demand_target', row.get('target')) in focus):
            trace.append(dict(event=kind, **row))

    def bind(stack, game, variant, callback):
        enable(stack, game, variant, callback)
        stack.enter_context(coordination.observing(record))

    with (patch.object(previous, 'enable', bind), patch.object(coordination, '_discover', capture),
          patch.object(legacy.winter_replay.HeadlessCampaign, 'command', city_snapshot)):
        result = audit.safety_case(task, output=output, capacity_limit=2 if group.startswith('L') else 1, actual=True)
    return dict(result, resource_availability=snapshots, focus_decision_trace=trace)


def account_trace(game):
    state = game.to_dict()
    pool = state['extension'].get(coordination.POOL)
    if pool is not None:
        # Only the intentionally different performance option is excluded.
        pool['features'].pop('route_reuse', None)
    return {'state': digest(state), 'rng': state['rng']}


def inspection(task):
    phase, item, path, group, output, repeat = task
    command = legacy.winter_replay.HeadlessCampaign.command
    selections, postings, hashes, rules = [], [], [], []
    actual = None
    observed = phase in ('south', 'equivalence')
    city = item['label'] if phase == 'south' else None
    turns = 9 if phase == 'south' else 3
    if phase == 'south':
        city = path.name.split('-', 1)[1].removesuffix('.json.gz')
    name = f"{item['label']}-{group}"

    def tracing_enable(stack, game, variant, callback):
        enable(stack, game, variant, callback)
        if phase == 'equivalence':
            def capture(kind, row):
                if kind in ('candidate', 'dispatch', 'dispatch_failed', 'receipt', 'demand'):
                    selections.append(dict(event=kind, **row))
            stack.enter_context(coordination.observing(capture))
            stack.enter_context(transport_capacity.observing(
                lambda kind, row: postings.append(dict(event=kind, **row))))
        elif phase == 'south':
            def capture_receipt(kind, row):
                if row.get('target') == city or row.get('source') == city:
                    postings.append(dict(event=kind, **row))
            stack.enter_context(transport_capacity.observing(capture_receipt))
        rules.append(rule_snapshot(game))

    def trace(game, action, payload, revision):
        outcome = command(game, action, payload, revision)
        if action == 'observe_turn' and phase == 'equivalence':
            hashes.append(account_trace(game))
        return outcome

    def record(kind, row):
        if kind != 'city_meal_settled' or row['city'] == city:
            actual.write(json.dumps(dict(event=kind, **row), ensure_ascii=False,
                                    separators=(',', ':')) + '\n')

    with ExitStack() as stack:
        stack.enter_context(patch.object(legacy, 'enable', tracing_enable))
        if phase == 'equivalence':
            stack.enter_context(patch.object(legacy.winter_replay.HeadlessCampaign, 'command', trace))
        if phase == 'south':
            prefix = output/'actual'
            prefix.mkdir(parents=True, exist_ok=True)
            actual = stack.enter_context(gzip.open(prefix/f'{name}.jsonl.gz', 'wt', compresslevel=2,
                                                    encoding='utf-8'))
            stack.enter_context(logistics_strategy.observing(record))
        endpoint = legacy.inspect_checkpoint
        if phase == 'profile':
            profile = cProfile.Profile()
            endpoint = lambda *args, **kwargs: profile.runcall(legacy.inspect_checkpoint, *args, **kwargs)
        result = endpoint(path, item['scenario'], item['strategy'], group, turns,
                          observation=observed, city=city,
                          events_path=output/'decisions'/f'{name}.jsonl.gz' if city else None)
        if phase == 'profile':
            profile.dump_stats(output/f'{name}.prof')
    result.update(label=item['label'], recorded_rules=rules[0], repeat=repeat)
    if phase == 'south':
        result['actual_ledger'] = str((prefix/f'{name}.jsonl.gz').relative_to(output))
        result['local_physical_receipts'] = postings
    if phase == 'equivalence':
        result['hashes'] = hashes
        result['formal_candidate_sequence'] = digest(selections)
        result['transport_receipts'] = digest(postings)
        result['decision_records'] = len(selections)
        result['resource_records'] = len(postings)
    return result


def historical_task(task):
    path, ident, group, output = task
    output = output/'individual'/ident/group
    danger = None

    def capture(game, snapshot):
        nonlocal danger
        if danger is not None or snapshot['node'] is None or snapshot['source_owner'] == snapshot['owner']:
            return
        state = game.state
        opening = digest(game.to_dict())
        evidence = []
        row = next(row for row in logistics._pool(state)['convoys'] if row['id'] == 3634)
        with grain_units.using(state):
            for coordinated in (False, True):
                planner = convoy_relief.Planner(game, state, row['owner'], coordinated=coordinated)
                plan = faction_economy.plan(game, state, row['owner'], granary=strategic_granary.enabled(state),
                                            coordinated=coordinated)
                for key, budget in plan.budgets.items():
                    city = state.cities[key]
                    quote, reason = planner.quote(city, planner.targets.get(row['id']), budget=budget)
                    evidence.append(dict(coordinated=coordinated, city=key, available_grain=city.grain,
                        failure=reason, quote=quote))
            rejected_former_home = not transport_emergency.can_receive(game, state, row, state.cities[row['source']])
        assert opening == digest(game.to_dict()), 'Same-state observation changed the checkpoint'
        # Keep the exact naturally reached state, including military orders and receipts.
        saved = game.export_save(compact=True)
        evidence_path = output/'danger-state-3634.save.json.gz'
        output.mkdir(parents=True, exist_ok=True)
        with gzip.open(evidence_path, 'wt', encoding='utf-8') as stream:
            json.dump(saved, stream, ensure_ascii=False, separators=(',', ':'))
        notes = [note for note in game.to_dict().get('log', [])[-100:]
                 if '武都' in str(note) or 'wudu' in str(note)]
        danger = dict(snapshot=snapshot, state_sha256=opening, relevant_geography_notes=notes,
                      file=f'individual/{ident}/{group}/{evidence_path.name}',
                      save_sha256=sha256(evidence_path.read_bytes()), rejected_former_home=rejected_former_home,
                      available_plans=evidence)

    with patch.object(legacy, 'enable', enable):
        legacy.historical(argparse.Namespace(samples=[f'{ident},{path}'], group=[group],
            output=output, turns=HISTORICAL[ident]), capture_state=capture if ident=='3634' else None)
    result = json.loads((output/'historical-convoy-safety.json').read_bytes())['results'][0]
    if result['convoy'] != int(ident) or result['group'] != group:
        raise ValueError(f'Historical output does not match convoy {ident} and group {group}')
    if ident == '3634':
        result['same_state_danger'] = danger
    return result


def perform(task):
    phase, payload, output = task
    if phase == 'constraints':
        result = constraint_task(payload, output)
    elif phase == 'fixed':
        result = fixed_task(payload, output)
    elif phase == 'historical':
        result = historical_task((*payload, output))
    else:
        item, path, group, repeat = payload
        result = inspection((phase, item, path, group, output, repeat))
    identity = [result.get('label', result.get('fixture', result.get('convoy'))), result['group'],
                result.get('repeat', 0)]
    to_json(output/'runs'/('-'.join(map(str, identity)) + '.json'), result)
    print(*identity, 'completed', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('fixed', 'constraints', 'south', 'performance', 'profile', 'equivalence', 'historical'))
    parser.add_argument('inputs', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--group', nargs='+', choices=GROUPS, required=True)
    parser.add_argument('--checkpoint', nargs='+')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--repeats', type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = verified_inputs(args.inputs, args.reference)
    group = {'profile': 'performance', 'equivalence': 'performance',
             'constraints': 'fixed'}.get(args.phase, args.phase)
    inputs = [item for item in records if item['restored'] and item['group'] == group]
    if group == 'historical':
        inputs.extend(dict(item, label=item['name'].split('-')[1].split('.')[0])
            for item in records if item['group'] == 'fixed' and item['name'] in
            ('convoy-219.json.gz', 'convoy-1228.json.gz'))
    if args.checkpoint:
        inputs = [item for item in inputs if item['label'] in args.checkpoint]
        if len(inputs) != len(args.checkpoint):
            raise ValueError('One or more checkpoint labels could not be resolved')
    if group == 'fixed':
        tasks = audit.fixed_tasks(args.inputs, inputs, args.group)
    elif group == 'historical':
        tasks = [(args.inputs/item['file'], item['label'], name) for item in inputs for name in args.group]
    else:
        def repeats(item):
            if args.phase != 'performance':
                return 1
            return args.repeats or (10 if item['label'] == 'north-snow' else 3)
        tasks = [(item, args.inputs/item['file'], name, repeat) for item in inputs
                 for repeat in range(repeats(item)) for name in args.group]
    config = {'phase': args.phase, 'source': git('rev-parse', 'HEAD').decode().strip(),
              'working_patch_sha256': sha256(git('diff', 'HEAD', '--binary')),
              'input_manifest_sha256': sha256(args.reference.read_bytes()),
              'groups': {name: settings(name) for name in args.group}}
    to_json(args.output/'manifest.json', dict(config, tasks=len(tasks), status='running'))
    kwargs = {'max_workers': 1, 'max_tasks_per_child': 1} if args.phase == 'performance' else {
        'max_workers': args.workers}
    rows = []
    with ProcessPoolExecutor(**kwargs) as pool:
        jobs = (pool.submit(perform, (args.phase, task, args.output)) for task in tasks)
        for job in as_completed(list(jobs)):
            rows.append(job.result())
    to_json(args.output/'results.json', dict(config, results=rows, status='complete'))
    if args.phase == 'performance':
        groups = defaultdict(list)
        for row in rows:
            groups[row['label'], row['group']].append(row)
        summary = []
        for (label, name), sample in sorted(groups.items()):
            assert all(row['final'] == sample[0]['final'] for row in sample)
            summary.append(dict(checkpoint=label, group=name, runs=len(sample),
                **quantiles([cpu for row in sample for cpu in row['cpu']]),
                peak_memory_bytes=max(row['peak_memory_bytes'] for row in sample),
                route_queries=sum(row['route_search_calls'] for row in sample)))
        to_csv(args.output/'scheduler-performance-profile.csv', summary)


if __name__ == '__main__':
    main()
