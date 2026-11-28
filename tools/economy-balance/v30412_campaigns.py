"""Run gated, same-engine logistics campaign pairs with exact scenario and seed identities."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import ROOT, git, sha256, to_json
from observe import RecordedCampaign
from remake import command_books, grain_market, logistics_strategy, transport_capacity, transport_coordination
from v231_observe import FIVE, LONG, QUICK, run
from v30412_replays import quantiles, rule_snapshot, settings


HOLDOUT = ((2047, '184-02', 211), (2048, '208-10', 212))
D2_FAST = (QUICK[0], QUICK[2], QUICK[3])
WAVES = {
    'quick': (24, QUICK, D2_FAST),
    'five': (60, (*FIVE, (2031, '190-01', 211)), (*D2_FAST, QUICK[-1])),
    'long': (240, LONG, (LONG[1],)),
    'holdout': (60, HOLDOUT, HOLDOUT),
}
BACKGROUND = {'D0': ('K0', 'K2'), 'D2': ('L0', 'L2')}
REQUIRED_GATE = {'quick': 'fixed', 'five': 'quick', 'long': 'five', 'holdout': 'freeze'}


def support_count(orders, buying, departures):
    result = Counter()
    for order in orders:
        turn, owner, city, kind, spent = order
        key = (turn, owner, city)
        if kind == 'trade_grain' and buying[key]:
            buying[key] -= 1
            result['market_books'] += spent
        elif kind == 'dispatch_transport' and key in departures:
            result['transport_books'] += spent
        elif kind in ('resupply_march', 'requisition_grain', 'emergency_grain'):
            result['direct_relief_books'] += spent
    result['total'] = sum(result.values())
    return dict(result)


def run_pair_side(task):
    output, spec = task
    variant = spec['variant']
    base = output/variant
    path = base/'campaigns'/spec['wave']/'F4'/f"{spec['scenario']}-{spec['seed']}-{spec['strategy']}"
    path.mkdir(parents=True, exist_ok=True)
    proof = path/'run-v3041.json'
    identity = dict(spec, options=settings(variant), winter_221=False)
    if proof.exists():
        prior = json.loads(proof.read_bytes())
        if (prior['case'] == identity and prior['result']['outcome'] in ('complete', 'natural_end')):
            return prior
        raise ValueError(f'Mismatched existing campaign {path}')
    if (path/'run-v231.json').exists():
        raise ValueError(f'Unattested existing campaign {path}')
    original = RecordedCampaign.command
    original_spend, original_trade = command_books.spend, grain_market.transfer
    rules, orders, departures = [], [], set()
    metrics, monthly = Counter(), defaultdict(Counter)
    buying, grain_market_volume = Counter(), Counter()
    preparation = Counter()
    coverage_marks = set()
    intervals = defaultdict(Counter)

    def command(game, action, payload, revision):
        if action != 'new':
            return original(game, action, payload, revision)
        result = original(game, action, dict(payload, **settings(variant)), revision)
        rules.append(rule_snapshot(game))
        state = game.state
        if (rules[-1]['weather_rules_version'] != 23 or rules[-1]['weather_forecast_version'] != 231
                or rules[-1]['regional_market_rules_version'] != 301
                or rules[-1]['strategic_granary_rules_version'] != 302
                or rules[-1]['transshipment_rules_version']
                or ('L' == variant[0]) != transport_capacity.enabled(state, 'concurrency')):
            raise ValueError(f'Unexpected experimental background for {variant}: {rules[-1]}')
        return result

    def spend(state, city, kind):
        spent = original_spend(state, city, kind)
        if spent:
            orders.append((state.turn, city.owner, city.id, kind, spent))
        return spent

    def buy(state, city, direction, grain, **details):
        result = original_trade(state, city, direction, grain, **details)
        if direction == 'buy' and grain:
            order = (state.turn, details.get('payer', city))
            if order[1] in state.cities:
                buying[order[0], state.cities[order[1]].owner, order[1]] += 1
            grain_market_volume[details.get('channel', 'unknown')] += grain
        return result

    def actual(kind, row):
        values = {}
        if kind == 'city_meal_settled':
            values = dict(city_food_required=row['required_grain'], city_food_paid=row['paid_grain'],
                city_food_missing=row['missing_grain'], resident_due=row['resident_due'],
                garrison_due=row['garrison_due'], shortage_city_turns=int(row['missing_grain'] > 0))
            key = row['owner'], row['city']
            intervals[key]['current'] = intervals[key]['current'] + 1 if row['missing_grain'] else 0
            intervals[key]['maximum'] = max(intervals[key]['maximum'], intervals[key]['current'])
        elif kind == 'unit_meal_settled':
            label = row['unit_kind']
            values = {f'{label}_food_{metric}': row[f'{metric}_grain'] for metric in ('required', 'paid', 'missing')}
            values.update({f'{label}_hunger_days': int(row['hunger_day']), f'{label}_hunger_losses': row['losses']})
            refill = row['refill']
            if refill and label == 'march':
                values.update(transit_requested=refill['requested_refill'], transit_received=refill['actual_received_grain'])
        elif kind == 'forecast_requote':
            values['requotes_observed'] = 1
        metrics.update(values)
        monthly[row['event_year'], row['event_month']].update(values)

    def track(stream, kind, row):
        stream.write(json.dumps(dict(event=kind, **row), ensure_ascii=False, separators=(',', ':'))+'\n')

    def capacity(kind, row):
        if kind == 'departure' and (row['cargo']['grain'] or row['purpose'] in ('army','convoy_relief','relief')):
            departures.add((row['turn'], row['owner'], row['source']))
        track(convoys, kind, row)

    def coordination(kind, row):
        if kind == 'military_preparation_request':
            key = row['turn'], row['owner'], row['city'], row['plan']
            if key not in coverage_marks:
                preparation[row['purpose']] += row['requested']
                coverage_marks.add(key)
        track(scheduler, kind, row)

    with ExitStack() as stack:
        scheduler = stack.enter_context(gzip.open(path/'coordination.jsonl.gz', 'wt', compresslevel=2, encoding='utf-8'))
        convoys = stack.enter_context(gzip.open(path/'capacity.jsonl.gz', 'wt', compresslevel=2, encoding='utf-8'))
        stack.enter_context(transport_coordination.observing(coordination, shadow=variant in ('K0', 'L0')))
        stack.enter_context(transport_capacity.observing(capacity))
        stack.enter_context(logistics_strategy.observing(actual))
        stack.enter_context(patch.object(command_books, 'spend', spend))
        stack.enter_context(patch.object(grain_market, 'transfer', buy))
        stack.enter_context(patch.object(RecordedCampaign, 'command', command))
        result = run(base, dict(spec, group='F4'))
    final = path/'terminal-save.json.gz'
    result['observed_actual_grain'] = dict(metrics)
    result['observed_actual_grain']['longest_city_shortage_streak'] = max(
        (row['maximum'] for row in intervals.values()), default=0)
    result['whole_grain_security_books'] = support_count(orders, buying, departures)
    result['whole_grain_market_volume'] = dict(grain_market_volume)
    result['military_preparation_requested'] = dict(preparation)
    result['runtime_setup_options'] = rules[0]
    with gzip.open(path/'actual-consumption-by-month.json.gz', 'wt', encoding='utf-8') as stream:
        json.dump([dict(year=year, month=month, **totals) for (year, month), totals in sorted(monthly.items())], stream)
    summary = dict(case=identity, result=result, scenario_sha256=sha256(
        (ROOT/'game/data/campaigns'/f"{spec['scenario']}.json").read_bytes()),
        terminal_checksum=json.loads(gzip.decompress(final.read_bytes()))['checksum'] if final.exists() else None,
        output=str(path.relative_to(output)))
    to_json(proof, summary)
    print(variant, spec['scenario'], spec['strategy'], spec['seed'], result['completed_turns'], result['outcome'], flush=True)
    return summary


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('wave', choices=WAVES)
    parser.add_argument('gate', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--background', nargs='+', choices=BACKGROUND, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    gate = json.loads(args.gate.read_bytes())
    source = git('rev-parse', 'HEAD').decode().strip()
    patch_hash = sha256(git('diff', 'HEAD', '--binary', '--', 'source', 'game', 'crates'))
    engine_sha = gate['engine_sha']
    changed_rules = git('diff', '--name-only', engine_sha, source, '--', 'source', 'game', 'crates')
    if (gate['stage'] != REQUIRED_GATE[args.wave] or changed_rules
            or patch_hash != sha256(b'') or set(args.background) - set(gate['admitted_backgrounds'])):
        raise ValueError('Campaign requires the verified, clean engine from the preceding stage gate')
    months, d0, d2 = WAVES[args.wave]
    plan = []
    for setup in args.background:
        for seed, scene, strategy in d0 if setup == 'D0' else d2:
            for variant in BACKGROUND[setup]:
                plan.append(dict(wave=args.wave, scenario=scene, strategy=strategy, seed=seed, variant=variant,
                                 months=months, source=source, engine_sha=engine_sha, source_diff_sha256=patch_hash))
    to_json(args.output/f'{args.wave}-plan.json', dict(cases=plan, gate_sha256=sha256(args.gate.read_bytes()),
             runner_sha256=sha256(Path(__file__).read_bytes())))
    completed = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks = [pool.submit(run_pair_side, (args.output, spec)) for spec in plan]
        for future in as_completed(tasks):
            completed.append(future.result()['case'])
    to_json(args.output/f'{args.wave}-completed.json', completed)


if __name__ == '__main__':
    main()
