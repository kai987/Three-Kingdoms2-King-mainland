"""Recalculate coordination acceptance tables from committed transactions and raw logs."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import ExitStack
from functools import lru_cache
import csv
import gzip
import json
from pathlib import Path
from tempfile import SpooledTemporaryFile

from common import Catalog, ROOT, sha256, to_csv, to_json
from remake.campaign import verified_save_content
from v23_report import NORTH
from v231_report import military


IDENTITY = ('wave', 'scenario', 'seed', 'strategy', 'variant')
MACRO = ('unpaid_city_turns', 'rations_missing', 'ai_sorties', 'battles', 'convoy_dispatched',
         'convoy_hunger_losses', 'convoy_failed', 'convoy_weather_grain_loss')
PAIRS = (('T0', 'T1'), ('T0', 'T2'), ('T0', 'T3'), ('T2', 'T3'), ('T4', 'T5'))
RATE_THRESHOLDS = dict(timely_grain_rate=-5, original_deadline_grain_rate=-5, timely_order_rate=-5,
                       small_faction_survival_rate=-10)
RATIO_THRESHOLDS = dict(unpaid_city_turns=20, rations_missing=20, mean_turn_cpu=30)


def table(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def ledger(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        yield from map(json.loads, stream)


def rate(top, bottom, *, scale=1):
    return scale*top/bottom if bottom else None


def emit(path, rows):
    rows = list(rows)
    if rows:
        keys = dict.fromkeys(key for row in rows for key in row)
        to_csv(path, ({key: row.get(key) for key in keys} for row in rows))


class CsvSpool:
    """Retain all observed fields without holding the whole matrix in memory."""

    def __init__(self, stream):
        self.stream = stream
        self.columns = {}

    def append(self, rows):
        for row in rows:
            self.columns.update(dict.fromkeys(row))
            self.stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n')

    def export(self, path):
        self.stream.seek(0)
        to_csv(path, ({key: row.get(key) for key in self.columns}
                      for row in map(json.loads, self.stream)))


def transport_accounts(folder, observed, coordination):
    launches, ends = {}, {}
    delivered, people = defaultdict(list), defaultdict(Counter)
    for row in ledger(folder/'capacity.jsonl.gz'):
        ident = row.get('id')
        if row['event'] == 'departure':
            launches[ident] = row
        elif row['event'] == 'terminal':
            ends[ident] = row
        elif row['event'] == 'delivery':
            delivered[ident].append(row)
    for row in observed:
        if row['kind'] != 'convoy_grain_daily':
            continue
        ident = row['unit_id'] if 'unit_id' in row else row.get('convoy_id', row.get('convoy'))
        if ident is None:
            continue
        people[ident].update(escort_troop_days=row.get('person_days', 0),
                             paid_rations=row.get('paid', 0), ice_rations=row.get('paid', 0)
                             if row.get('reason') == 'ice' else 0)

    committed = {row['convoy']: row for row in coordination if row['event'] == 'dispatch'
                 and row.get('convoy') is not None}
    slots, totals, by_purpose = [], Counter(), defaultdict(Counter)
    for ident, row in launches.items():
        end = ends.get(ident)
        raw_arrivals = delivered[ident]
        net = sum(r['cargo']['grain'] for r in raw_arrivals)
        initial = row['cargo']['grain']
        departure = (row['turn']-1)*10
        crew = row['officers']
        origin_days = max(0, end['end_tick']-departure) if end else None
        reusable = end['reusable_turn'] if end else None
        cooldown = max(0, (reusable-1)*10-end['end_tick']) if reusable else 0
        officer_days = (origin_days*sum(type(i) is int for i in crew) +
                        cooldown*sum(type(i) is int for i in end['received_officers'])) if end else None
        clerk_days = (origin_days*sum(type(i) is str for i in crew) +
                      cooldown*sum(type(i) is str for i in end['received_officers'])) if end else None
        actual = committed.get(ident)
        books = actual['books_used'] if actual else row['command_books'] + (row['purpose'] == 'regional')
        slots.append(dict(convoy=ident, owner=row['owner'], source=row['source'], target=row['target'],
            launch_turn=row['turn'], mode=row['profile']['mode'], purpose=row['purpose'],
            priority=actual['priority'] if actual else None, officers=crew, active_at_dispatch=row['active'],
            dispatched_this_turn=row['dispatch_count'], outbound_days=row['outbound_days'],
            origin_slot_days=origin_days, officer_occupation_days=officer_days,
            clerk_occupation_days=clerk_days, allocated_books=books, initial_grain=initial,
            delivered_grain=net, terminal=end['outcome'] if end else None,
            received_turns=[r['turn'] for r in raw_arrivals], protected_rations=row['rations'],
            actual_rations=end['ration_spent'] if end else None,
            hunger_losses=end['hunger_losses'] if end else None,
            cargo_receipt=end['cargo_receipt'] if end else None, **people[ident]))
        if not initial:
            continue
        measured = Counter(grain_orders=1, grain_order_books=books, actual_received_grain=net,
            unknown_grain_return=int(end is None), second_slot_grain_orders=int(row['active'] == 2),
            small_long_grain_orders=int(initial < 1000 and row['outbound_days'] >= 20))
        if end and origin_days:
            measured.update(slot_days=origin_days, finished_net=net, finished_orders=1)
            if officer_days and all(type(i) is int for i in crew):
                measured.update(officer_days=officer_days, pure_officer_net=net)
            if clerk_days and all(type(i) is str for i in crew):
                measured.update(clerk_days=clerk_days, pure_clerk_net=net)
        totals.update(measured)
        by_purpose[row['purpose']].update(measured)

    def efficiency(counts):
        return dict(counts, net_per_book=rate(counts['actual_received_grain'], counts['grain_order_books']),
            net_per_officer_day=rate(counts['pure_officer_net'], counts['officer_days']),
            net_per_clerk_day=rate(counts['pure_clerk_net'], counts['clerk_days']),
            net_per_slot_day=rate(counts['finished_net'], counts['slot_days']),
            mean_completed_period=rate(counts['slot_days'], counts['finished_orders']))

    return slots, efficiency(totals), [dict(purpose=purpose, **efficiency(counts))
                                      for purpose, counts in sorted(by_purpose.items())]


def demand_episodes(first, candidates, dispatches, receipts, through):
    """Measure one demand once and count only actual receipts."""
    history = defaultdict(list)
    for key, row in first.items():
        if row['unresolved'] > 0:
            history[row['demand_id']].append((key, row))
    sent = defaultdict(list)
    for row in dispatches:
        sent[row['demand_id']].append(row)
    results = []
    for identifier, observations in sorted(history.items()):
        opening = observations[0][1]
        deadline = opening['original_deadline']
        valid = [quote for key, _ in observations for quote in candidates[key]
                 if quote['timely_net'] > 0 and (quote['turn']-1)*10 < deadline]
        actual = [row for row in sent[identifier] if (row['turn']-1)*10 < deadline]
        results.append(dict(demand_id=identifier, owner=opening['owner'], target=opening['target'],
            target_kind=opening['target_kind'], initial_priority=opening['priority'],
            earliest_priority=min(row['priority'] for _, row in observations),
            original_deadline=deadline, deadline_observed=through >= deadline,
            initial_gap=opening['unresolved'], has_timely_quote=bool(valid),
            eligible_sources=sorted({quote['source'] for quote in valid}),
            largest_timely_quote=max((quote['timely_net'] for quote in valid), default=0),
            actual_dispatches=sum(row['convoy'] is not None for row in actual),
            immediate_purchases=sum(row['immediate_received'] > 0 for row in actual),
            timely_credited=receipts[identifier], original_gap_credited=min(opening['unresolved'], receipts[identifier])))
    return results


def source_outcomes(climate, dispatches, through):
    by_city = defaultdict(dict)
    for row in climate:
        if row['kind'] == 'city_rations':
            by_city[row['owner'], row['city']][row['turn']] = row
    for dispatch in dispatches:
        if dispatch['source'] == dispatch['target']:
            continue
        observed = by_city[dispatch['owner'], dispatch['source']]
        turns = range(dispatch['turn'], dispatch['turn']+9)
        samples = [observed[turn] for turn in turns if turn <= through and turn in observed]
        yield dict(dispatch, observed_source_turns=len(samples),
                   post_dispatch_missing_grain=sum(row['missing'] for row in samples),
                   post_dispatch_shortage_turns=sum(row['missing'] > 0 for row in samples))


@lru_cache(maxsize=16)
def regions(scenario):
    catalog = Catalog(ROOT/'game/data/campaigns'/f'{scenario}.json')
    return {key: row['climate_region_id'] for key, row in catalog.climate.cities.items()}


def city_indicators(path, scenario, last_month, alive):
    holdings, cold, stock = Counter(), Counter(), Counter()
    longest_shortage = 0
    geography = regions(scenario)
    for row in table(path):
        owner, region = row['owner'], geography.get(row['city'], 'unmapped')
        longest_shortage = max(longest_shortage, int(row['max_food_shortage_streak']))
        if row['elapsed_months'] == '0' and owner != 'neutral':
            holdings[owner] += 1
            cold[owner] += region in NORTH
        if row['elapsed_months'] == last_month:
            stock[region] += int(row['grain_stock'])
    northern = {owner for owner in holdings if 2*cold[owner] >= holdings[owner]}
    stock_total = sum(stock.values())
    return dict(northern_factions=len(northern), surviving_northern_factions=len(northern & alive),
                northern_survival_rate=rate(len(northern & alive), len(northern), scale=100),
                maximum_city_shortage_streak=longest_shortage,
                largest_region_grain_share=rate(max(stock.values(), default=0), stock_total, scale=100),
                region_final_grain=dict(stock))


def read_run(path):
    proof = json.loads(path.read_text())
    case, run = proof['case'], proof['result']
    identity = {key: case[key] for key in IDENTITY}
    folder = path.parent
    complete = run['outcome'] in ('complete', 'natural_end')
    manifest = dict(identity, output=proof['output'], source=case['source'],
        source_diff_sha256=case['source_diff_sha256'], scenario_sha256=proof['scenario_sha256'],
        engine_worktree_diff_sha256=run['worktree_diff_sha256'],
        map_sha256=run['map_sha256'], backend=run['backend'], completed_turns=run['completed_turns'],
        full_months=run['full_months'], requested_months=case['months'], outcome=run['outcome'],
        options=case['options'], input_rule_versions=run['rule_versions'], launch_weather_221=case['winter_221'],
        terminal_checksum=proof['terminal_checksum'], failure=run.get('failure'))
    if not complete:
        return manifest, None, {}
    csv_root = folder/case['scenario']
    monthly = table(csv_root/'monthly.csv')
    factions = table(csv_root/'factions.csv')
    opening = {r['faction'] for r in factions if r['elapsed_months'] == '0'
               and r['faction'] != 'neutral' and 0 < int(r['cities']) <= 3}
    alive = {r['faction'] for r in factions if r['elapsed_months'] == monthly[-1]['elapsed_months']
             and int(r['cities']) > 0}
    hashes = {name: sha256((csv_root/f'{name}.csv').read_bytes()) for name in ('monthly', 'factions', 'cities')}
    terminal = verified_save_content(json.loads(gzip.decompress((folder/'terminal-save.json.gz').read_bytes())))
    manifest.update(table_sha256=hashes, rng=terminal['state']['rng'])
    latest = monthly[-1]
    # The campaign observer publishes cumulative counters at each monthly checkpoint.
    score = dict(identity, full_months=run['full_months'], completed_turns=run['completed_turns'],
        **{key: int(latest[key]) for key in MACRO})
    score.update(city_indicators(csv_root/'cities.csv', case['scenario'], monthly[-1]['elapsed_months'], alive))
    score.update(final_population=int(monthly[-1]['population']), final_grain=int(monthly[-1]['grain_stock']),
                 final_gold=int(monthly[-1]['gold_stock']), final_active_troops=int(monthly[-1]['active_troops']),
                 small_factions=len(opening), surviving_small_factions=len(opening & alive),
                 small_faction_survival_rate=rate(len(opening & alive), len(opening), scale=100),
                 mean_turn_cpu=run['performance'].get('mean_turn_cpu_seconds'),
                 resource_mismatches=run['warehouse_audit']['city_resource_mismatches'])
    climate = list(ledger(folder/'events.jsonl.gz'))
    score['maximum_single_city_food_gap'] = max((r['missing'] for r in climate if r['kind'] == 'city_rations'),
                                               default=None)
    totals, requests, receipts, orders = military(run, table(folder/'supply-episodes-weather-aware.csv'),
        (row for row in climate if row['kind'] == 'army_convoy'))
    score.update(totals)
    for name in ('requested_grain', 'timely_received_grain', 'late_received_grain', 'unresolved_grain',
                 'no_dispatch_unresolved_grain', 'timely_at_original_deadline', 'matured_orders',
                 'timely_positive_receipt_orders'):
        score.setdefault(name, 0)
    coordination = list(ledger(folder/'coordination.jsonl.gz'))
    slots, use, by_purpose = transport_accounts(folder, climate, coordination)
    score.update(use)
    events = defaultdict(list)
    for row in coordination:
        events[row['event']].append(row)
    first = {}
    for row in events['demand']:
        key = row['turn'], row['demand_id']
        first.setdefault(key, row)
    candidates = defaultdict(list)
    for row in events['candidate']:
        candidates[row['turn'], row['demand_id']].append(row)
    dispatches = {(row['turn'], row['demand_id']) for row in events['dispatch']}
    receipts_by_demand = Counter()
    for row in events['receipt']:
        assert row['received'] == row['credited'] + row['unallocated']
        receipts_by_demand[row['demand_id']] += row['timely']
    days = run['completed_turns']*10
    episodes = demand_episodes(first, candidates, events['dispatch'], receipts_by_demand, days)
    matured = [r for r in episodes if r['deadline_observed'] and r['earliest_priority'] <= 2]
    feasible = [r for r in matured if r['has_timely_quote']]
    source_audit = list(source_outcomes(climate, events['dispatch'], run['completed_turns']))
    concurrent = 2 if case['options'].get('transport_capacity_options', {}).get('concurrency') else 1
    escrow = Counter((row['owner'], row['launch_turn'], escort) for row in slots for escort in row['officers'])
    score.update(simultaneous_escort_overlaps=sum(n-1 for n in escrow.values() if n > 1),
        transport_position_overruns=sum(row['active_at_dispatch'] > concurrent for row in slots),
        repeated_origin_dispatches=sum(row['dispatched_this_turn'] > 1 for row in slots))
    if events['demand']:
        seen_receipts = Counter(r['convoy'] for r in events['receipt'] if r['convoy'] is not None)
        score.update(urgent_episodes=len(matured), feasible_urgent_episodes=len(feasible),
            quote_only_urgent_episodes=sum(not (r['actual_dispatches'] or r['immediate_purchases']) for r in feasible),
            urgent_initial_gap_covered=sum(r['original_gap_credited'] for r in matured),
            duplicate_convoy_receipts=sum(n-1 for n in seen_receipts.values() if n > 1),
            cross_city_dispatches=len(source_audit),
            fully_observed_source_dispatches=sum(r['observed_source_turns'] == 9 for r in source_audit),
            followed_by_source_shortage=sum(r['post_dispatch_shortage_turns'] > 0 for r in source_audit),
            insufficient_book_postings=sum(r['books_used'] != r['books'] for r in events['dispatch']))
    funnel = []
    for key, row in first.items():
        ready = candidates[key]
        successful = key in dispatches
        funnel.append(dict(row, L0=row['unresolved'] > 0, L1=row['donor_stock'] > 0,
            L2=True if any(r['channel'] in ('ordinary', 'granary', 'army', 'convoy') for r in ready) else None,
            L3=True if any(r['mode'] for r in ready) else None, L4=True if ready else None,
            L5=True if any(r['mode'] for r in ready) else None, L6=True if ready else None,
            L7=any(r['timely_net'] > 0 for r in ready), L8=successful,
            episode_timely_receipt=receipts_by_demand[row['demand_id']]))
    shadow = []
    for row in events['shadow_recommendation']:
        competing = [d for d in slots if d['owner'] == row['owner'] and d['launch_turn'] == row['turn']
                     and d['source'] == row['source']]
        shadow.append(dict(row, actual_same_source=[r['convoy'] for r in competing],
            actual_targets=[r['target'] for r in competing], actual_purposes=[r['purpose'] for r in competing],
            actual_overlapping_escorts=[r['convoy'] for r in competing if set(r['officers']) & set(row['escorts'])],
            same_target=any(r['target'] == row['target'] for r in competing)))
    resource_claims = defaultdict(set)
    for row in events['candidate']:
        for escort in row['escorts']:
            resource_claims[row['turn'], row['owner'], row['phase'], row['source'], escort].add(row['demand_id'])
    people = [dict(turn=turn, owner=owner, phase=phase, source=source, escort=escort,
                   competing_demands=sorted(demands))
              for (turn, owner, phase, source, escort), demands in resource_claims.items() if len(demands) > 1]
    priority = defaultdict(Counter)
    for row in events['dispatch']:
        priority[row['priority'], row['channel']].update(dispatches=1, books=row['books_used'])
    priority_summary = [dict(priority=p, channel=channel, **counts)
                        for (p, channel), counts in sorted(priority.items())]
    merges = (dict(row, common_shortage=row['requested'], deducted_reliable_arrivals=row['reliable'],
                   combined_alternatives=len(row['channels'])) for row in first.values()
              if row['target_kind'] == 'city' and row['requested'] and row['reliable'] and len(row['channels']) > 1)

    exports = {'transport-demand-ledger': first.values(),
        'demand-deduplication': (r for r in first.values() if len(r['channels']) > 1),
        'demand-receipt-allocation': events['receipt'], 'transport-candidate-comparison': events['candidate'],
        'transport-resource-allocation': events['dispatch'], 'transport-shadow-comparison': shadow,
        'transport-command-budget': events['scheduler'], 'origin-slot-priority': slots,
        'transport-priority-distribution': priority_summary,
        'officer-allocation-conflicts': (r for r in people if type(r['escort']) is int),
        'clerk-allocation-conflicts': (r for r in people if type(r['escort']) is str),
        'source-grain-allocation': (r for r in events['dispatch'] if r['source'] != r['target']),
        'transport-demand-episodes': episodes,
        'emergency-demand-dispatch-funnel': (r for r in funnel if r['priority'] <= 2),
        'unserved-demand-root-cause': (r for r in funnel if not r['L8']),
        'feasible-but-not-dispatched': (r for r in funnel if r['L7'] and not r['L8']),
        'transport-task-deferral': (r for r in first.values() if r['outcome']),
        'transport-batch-consolidation': merges,
        'small-load-transport-audit': (row for row in slots if 0 < row['initial_grain'] < 1000),
        'compound-procurement-receipts': (r for r in (*events['dispatch'], *events['dispatch_failed'])
                                         if r['channel'] == 'regional'),
        'source-safety-after-dispatch': source_audit,
        'transport-revalidation-results': events['dispatch_failed'],
        'military-grain-request-ledger': requests, 'military-grain-receipt-ledger': receipts,
        'unmet-military-demand': (r for r in requests if r['unresolved_grain']),
        'comparable-dispatch-deadlines': orders,
        'convoy-hunger-comparison': (r for r in slots if r['hunger_losses']),
        'convoy-return-safety': (r for r in slots if r['terminal'] is not None),
        'weather-cargo-loss-audit': (r for r in climate if r['kind'] == 'convoy_weather_cargo'),
        'officer-unit-efficiency': [use], 'transport-efficiency-by-purpose': by_purpose}
    result = {key: [dict(identity, **r) for r in rows] for key, rows in exports.items()}
    return manifest, score, result


def comparisons(scores, *, pairs_to_compare=PAIRS, extra=()):
    groups = defaultdict(dict)
    for row in scores:
        key = tuple(row[name] for name in IDENTITY[:-1])
        groups[key][row['variant']] = row
    warnings, pairs = [], []
    for group, rows in sorted(groups.items()):
        for base, candidate in pairs_to_compare:
            if {base, candidate} - rows.keys():
                continue
            a, b = rows[base], rows[candidate]
            identity = dict(zip(IDENTITY[:-1], group, strict=True), baseline=base, candidate=candidate)
            compared = list(dict.fromkeys((*MACRO, *RATE_THRESHOLDS, *RATIO_THRESHOLDS,
                'net_per_book', 'net_per_officer_day', 'net_per_clerk_day', 'requested_grain',
                'timely_received_grain', 'unresolved_grain', 'no_dispatch_unresolved_grain',
                'small_long_grain_orders', 'second_slot_grain_orders', 'net_per_slot_day',
                'mean_completed_period', 'northern_survival_rate', 'maximum_city_shortage_streak',
                'largest_region_grain_share', 'maximum_single_city_food_gap', *extra)))
            for metric in compared:
                old, new = a.get(metric), b.get(metric)
                same_months = a['full_months'] == b['full_months']
                matched = same_months and a['completed_turns'] == b['completed_turns']
                delta = new-old if matched and old is not None and new is not None else None
                relative = rate(delta, old, scale=100) if delta is not None else None
                record = dict(identity, metric=metric, baseline_value=old, candidate_value=new,
                              delta=delta, percent_change=relative, comparable_months=same_months,
                              comparable_turns=matched)
                pairs.append(record)
                if metric in RATE_THRESHOLDS and delta is not None and delta < RATE_THRESHOLDS[metric]:
                    warnings.append(dict(record, threshold=RATE_THRESHOLDS[metric], unit='percentage_points'))
                elif metric in RATIO_THRESHOLDS and relative is not None and relative > RATIO_THRESHOLDS[metric]:
                    warnings.append(dict(record, threshold=RATIO_THRESHOLDS[metric], unit='percent'))
                elif metric in RATIO_THRESHOLDS and old == 0 and delta is not None and delta > 0:
                    warnings.append(dict(record, threshold=RATIO_THRESHOLDS[metric], unit='zero_baseline'))
    return pairs, warnings


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('observed', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases, scores, streams = [], [], {}
    with ExitStack() as stack:
        for path in sorted(args.observed.rglob('run-v3041.json')):
            case, score, outputs = read_run(path)
            cases.append(case)
            if score is not None:
                scores.append(score)
            for kind, result in outputs.items():
                if not result:
                    continue
                if kind not in streams:
                    file = stack.enter_context(SpooledTemporaryFile(max_size=512*1024, mode='w+t', encoding='utf-8'))
                    streams[kind] = CsvSpool(file)
                streams[kind].append(result)
        for name, spool in streams.items():
            spool.export(args.output/f'{name}.csv')
    pairs, warnings = comparisons(scores)
    baseline = {}
    for row in cases:
        key = tuple(row[field] for field in IDENTITY[:-1])
        baseline.setdefault(key, {})[row['variant']] = row
    identity_proof = []
    for key, groups in baseline.items():
        if {'T0', 'T1'} <= groups.keys():
            rows = [groups[name] for name in ('T0', 'T1')]
            fields = ['terminal_checksum', 'rng', 'table_sha256']
            match = {field: rows[0].get(field) == rows[1].get(field) for field in fields
                     if all(row.get(field) is not None for row in rows)}
            identity_proof.append(dict(zip(IDENTITY[:-1], key, strict=True), **match))
    to_json(args.output/'simulation-manifest.json', cases)
    to_json(args.output/'report-status.json', dict(cases=len(cases), scored=len(scores),
        failed=[row for row in cases if row['outcome'] not in ('complete', 'natural_end')],
        balance_alerts=len(warnings), shadow_identity=identity_proof))
    emit(args.output/'baseline-verification.csv', identity_proof)
    emit(args.output/'scenario-scores.csv', scores)
    emit(args.output/'pairwise.csv', pairs)
    emit(args.output/'balance-alerts.csv', warnings)
    emit(args.output/'winter-grain-timely-comparison.csv',
         (r for r in scores if r.get('requested_grain')))
    emit(args.output/'winter-order-timely-comparison.csv',
         (r for r in scores if r.get('matured_orders')))
    safety = ('urgent_episodes', 'feasible_urgent_episodes', 'quote_only_urgent_episodes',
              'urgent_initial_gap_covered', 'duplicate_convoy_receipts', 'cross_city_dispatches',
              'fully_observed_source_dispatches', 'followed_by_source_shortage',
              'insufficient_book_postings', 'simultaneous_escort_overlaps', 'transport_position_overruns',
              'repeated_origin_dispatches', 'resource_mismatches')
    emit(args.output/'coordination-safety-totals.csv',
         (dict((key, r.get(key)) for key in (*IDENTITY, *safety)) for r in scores))


if __name__ == '__main__':
    main()
