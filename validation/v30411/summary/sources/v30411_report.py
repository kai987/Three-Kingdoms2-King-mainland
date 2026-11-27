"""Summarize completed fixed replays and retain historical and current cohorts separately."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import gzip
from hashlib import sha256
import json
from pathlib import Path

from common import to_csv, to_json
from v30411_replays import settings


GROUPS = {'T0': 'U0', 'T2': 'T2', 'T3': 'U1', 'T4': 'V0', 'T5': 'V1'}
GUIDES = dict(U0=(32, 30, 20833, 14), V0=(42, 37, 24659, 15))


def rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def trace_files(folder):
    trace = {row['fixture']: row['fixture_sha256']
             for row in json.loads((folder/'fixed-capacity-replay-traces.json').read_bytes())}
    for file in sorted((folder/'decision-traces').glob('*.jsonl.gz')):
        name, group = file.name.removesuffix('.jsonl.gz').rsplit('-', 1)
        checkpoint = trace[name+'.gz']
        with gzip.open(file, 'rt', encoding='utf-8') as stream:
            for line in stream:
                yield checkpoint, group, json.loads(line)


def key(row):
    return row['checkpoint_sha256'], row['owner'], row['target']


def summarize(fixed, returning):
    by_group = defaultdict(Counter)
    for row in fixed:
        group = row['group']
        by_group[group].update(targets=1)
        if row['l5_actual_reception'] not in ('', 'null', None):
            got = int(row['l5_actual_reception'])
            bill = int(row['first_uncovered_grain'])
            by_group[group].update(completed_windows=1, timely_targets=int(got>0), full_targets=int(got>=bill),
                                  actual_grain=got, first_gap_grain=min(got, bill))
    for row in returning:
        ships = json.loads(row['actual_shipments'])
        by_group[row['group']].update(returning_samples=1, returning_quoted=int(bool(json.loads(row['timely_quotes']))),
            returning_delivered=int(bool(ships)), returning_grain=sum(ship['grain'] for ship in ships))
    return [dict(group=group, **{
        column: values[column] for column in ('targets', 'completed_windows', 'timely_targets', 'full_targets',
            'actual_grain', 'first_gap_grain', 'returning_samples', 'returning_quoted',
            'returning_delivered', 'returning_grain')}) for group, values in sorted(by_group.items())]


def evidence(folder, focus=None):
    targets = defaultdict(lambda: defaultdict(list))
    scheduler, receipts, dispatches, preparations, expiry, transit = [], [], [], [], [], []
    for checkpoint, group, row in trace_files(folder):
        event = row['event']
        record = dict(checkpoint=checkpoint, group=group, **row)
        if event == 'scheduler':
            scheduler.append(record)
        elif event == 'military_preparation_request':
            preparations.append(record)
        elif event == 'military_preparation_expired':
            expiry.append(record)
        elif event == 'transit_refill_budget':
            transit.append(record)
        else:
            marker = (checkpoint, row.get('owner'), row.get('demand_target', row.get('target')))
            if focus is None or marker in focus:
                targets[group][marker].append(row)
            if event in ('dispatch', 'dispatch_failed'):
                dispatches.append(record)
            elif event == 'receipt':
                receipts.append(record)
    return targets, scheduler, receipts, dispatches, preparations, expiry, transit


def attr(history, discovered, integrated, current):
    base = {(row['group'], key(row)): row for row in history}
    new = {(row['group'], key(row)): row for row in current}
    aligned = {(row['group'], key(row)): row for row in integrated}
    index = (('T0', 'T3', 'U1', 'U6'), ('T4', 'T5', 'V1', 'V2'))
    for before, after, observed, candidate in index:
        for row in history:
            target = key(row)
            if (row['group'] != before or not int(row['l5_actual_reception'])
                    or int(base[after, target]['l5_actual_reception'])):
                continue
            baseline = base[after, target]
            due = int(row['deadline_turn'])
            events = [event for event in discovered[observed][target] if event['turn']<due]
            demands = [event for event in events if event['event']=='demand']
            valid = [event for event in events if event['event']=='candidate' and
                     (event['conservative_arrival'] if event['priority']<=2 else event['arrival']) < (due-1)*10]
            sent = [event for event in events if event['event']=='dispatch' and event['convoy'] is not None]
            purchased = sum(event['immediate_received'] for event in events if event['event']=='dispatch')
            failed = Counter(event['reason'] for event in events if event['event']=='dispatch_failed')
            statuses = Counter(event.get('outcome') or 'had_quote' for event in demands)
            issues = Counter()
            for demand in demands:
                issues.update(demand['blockers'])
            indicators = []
            if not demands:
                indicators.append('no_demand_observed')
            if statuses['candidate_limit']:
                indicators.append('some_passes_not_evaluated')
            if valid and not sent:
                indicators.append('eligible_deadline_quote_not_launched')
            if failed:
                indicators.append('revalidation_failed')
            if purchased:
                indicators.append('market_purchase_observed_consumer_attribution_separate')
            if sent:
                indicators.append('shipment_without_on_time_receipt')
            if not indicators:
                indicators.append('no_usable_deadline_quote_observed')
            chosen = [event for event in events if event['event'] in ('dispatch', 'dispatch_failed')]
            previous = json.loads(row['l5_actual_receipts'])
            yield dict(comparison=f'{before}-{after}', checkpoint=target[0], scenario=row['scenario'],
                turn=row['turn'], owner=target[1], target=target[2], deadline_turn=due,
                original_gap=row['first_uncovered_grain'], previous_received=row['l5_actual_reception'],
                previous_actual_receipts=previous, regressed_received=baseline['l5_actual_reception'],
                legacy_real_replay_reception=aligned[observed,target]['l5_actual_reception'],
                aligned_candidate_reception=new[candidate,target]['l5_actual_reception'],
                demand_events=len(demands), deadline_candidates=len(valid), actual_launches=len(sent),
                local_purchased_grain=purchased, statuses=dict(statuses), observed_offer_blockers=dict(issues),
                dispatch_failures=dict(failed), indicators=indicators,
                l0_original_need=int(row['first_uncovered_grain']),
                l1_demands_found=len(demands),
                l2_sources_with_proven_deadline_offer=sorted({event['source'] for event in valid}),
                l3_escorts_proven_by_offer=sorted({str(escort) for event in valid for escort in event['escorts']}),
                l4_deadline_compatible_offers=len(valid),
                l5_position_and_books_proven_by_commit=len(sent),
                l6_retained_offers_for_original_sources=sorted({event['source'] for event in valid}
                    & {receipt['source'] for receipt in previous}),
                l7_commit_attempts=len(chosen),
                l8_accepted_transactions=sum(event['event']=='dispatch' for event in chosen),
                l9_launched_convoys=[event['convoy'] for event in sent],
                l10_physical_receipts_before_due=int(aligned[observed,target]['l5_actual_reception']),
                l11_attributable_physical_coverage=min(int(row['first_uncovered_grain']),
                    int(aligned[observed,target]['l5_actual_reception'])))


def pairs(fixed, comparisons):
    by_group = {group: {key(row): row for row in fixed if row['group']==group}
                for group in {row['group'] for row in fixed}}
    for control, test in comparisons:
        if control not in by_group or test not in by_group:
            continue
        for known, before in sorted(by_group[control].items()):
            after = by_group[test][known]
            raw = int(before['l5_actual_reception']), int(after['l5_actual_reception'])
            need = int(before['first_uncovered_grain'])
            yield dict(control=control, candidate=test, checkpoint=known[0], owner=known[1], target=known[2],
                       turn=before['turn'], deadline=before['deadline_turn'], first_gap=need,
                       control_received=raw[0], candidate_received=raw[1],
                       control_coverage=min(need, raw[0]), candidate_coverage=min(need, raw[1]),
                       gained=raw[0]==0<raw[1], lost=raw[0]>0==raw[1],
                       source_control=json.loads(before['l5_actual_receipts']),
                       source_candidate=json.loads(after['l5_actual_receipts']))


def write(path, data, *, headers=()):
    data = list(data)
    if data:
        fields = dict.fromkeys(key for row in data for key in row)
        to_csv(path, ({field: row.get(field) for field in fields} for row in data))
    elif headers:
        with path.open('w',encoding='utf-8',newline='') as stream:
            csv.writer(stream,lineterminator='\n').writerow(headers)


def package(args):
    data, checks = args.output/'data', args.output/'checks'
    data.mkdir(parents=True, exist_ok=True)
    checks.mkdir(parents=True, exist_ok=True)
    historical = rows(args.prior/'summary/data/fixed-demand-replay.csv')
    historical_returns = rows(args.prior/'summary/data/returning-slot-replay.csv')
    integrated = args.runs/'baseline-fixed'
    ablation = args.runs/'fixed-ablation'
    exact = args.runs/'historical-attribution'
    fixed = rows(ablation/'transport-capability-funnel.csv')
    returning = rows(ablation/'capacity-counterfactual.csv')
    for path, table in (('transport-capability-funnel.csv', fixed), ('capacity-counterfactual.csv', returning)):
        for row in rows(integrated/path):
            if row['group'] in ('T0','T4'):
                table.append(dict(row, group=GROUPS[row['group']]))
    historical_replay = rows(exact/'transport-capability-funnel.csv')
    archive_by_id = {(GROUPS[row['group']], key(row)): row for row in historical}
    matches = [dict(group=row['group'], checkpoint=key(row)[0], owner=row['owner'], target=row['target'],
                    original=archive_by_id[row['group'],key(row)]['l5_actual_reception'],
                    replay=row['l5_actual_reception'],
                    matches_receipts=archive_by_id[row['group'],key(row)]['l5_actual_receipts']==row['l5_actual_receipts'],
                    matches_first_gap=archive_by_id[row['group'],key(row)]['first_uncovered_grain']==row['first_uncovered_grain'])
               for row in historical_replay]
    for row in matches:
        row['identical'] = row['original']==row['replay']
    write(data/'historical-fixed-baseline-verification.csv', matches)
    trial = args.runs/'rolling-deadline'
    if (trial/'transport-capability-funnel.csv').is_file():
        shifted = rows(trial/'transport-capability-funnel.csv')
        shifted_sources = rows(trial/'capacity-counterfactual.csv')
        write(data/'rolling-deadline-trial-summary.csv', summarize(shifted, shifted_sources))
        write(data/'rolling-deadline-trial-by-target.csv', pairs(fixed+shifted, (('U6','U6r'),('V2','V2r'))))
    fixed_totals, history_totals = summarize(fixed, returning), summarize(historical, historical_returns)
    write(data/'fixed-demand-coverage-recovery.csv', fixed_totals)
    write(data/'historical-fixed-demand-baseline.csv', history_totals)
    write(data/'fixed-target-raw-receipts.csv', fixed)
    write(data/'returning-slot-coverage-recovery.csv', returning)
    discovered, schedule, receipts, dispatches, prep, expiry, transit = evidence(ablation)
    legacy, *_ = evidence(exact)
    attribution = list(attr(historical, legacy, historical_replay, fixed))
    write(data/'fixed-demand-regression-attribution.csv', attribution)
    write(data/'alternative-source-comparison.csv', pairs(fixed, (
        ('U1','U2'), ('U2','U3a'), ('U2','U3b'), ('U2','U3'), ('U3','U4'),
        ('U4','U5p'), ('U4','U5t'), ('U4','U5'), ('U5','U6'), ('V1','V2'), ('U6','V2'))))
    outcomes = Counter((group, row['priority'], row['outcome']) for group, facts in discovered.items()
        for events in facts.values() for row in events if row['event']=='demand')
    write(data/'candidate-pagination-audit.csv', (dict(group=group, priority=priority, outcome=outcome, records=count)
        for (group, priority, outcome), count in sorted(outcomes.items(), key=lambda row: str(row[0]))))
    write(data/'candidate-pruning-loss.csv', pairs(fixed, (('U2','U3a'), ('U3a','U3'), ('U2','U3b'))))
    write(data/'forecast-requote-results.csv', (row for row in schedule if row.get('granary_requotes')),
          headers=('checkpoint','group','turn','owner','phase','granary_requotes'))
    write(data/'military-preparation-demand-ledger.csv', prep,
          headers=('checkpoint','group','turn','owner','city','plan','purpose','target','requested','deadline'))
    write(data/'military-preparation-expiry.csv', expiry,
          headers=('checkpoint','group','turn','owner','city','plan','purpose','deadline','reason'))
    write(data/'transit-grain-commitment-ledger.csv', transit,
          headers=('checkpoint','group','turn','owner','city','army','requested','allowed'))
    write(data/'candidate-observed-dispatches.csv', dispatches)
    write(data/'candidate-observed-receipts.csv', receipts)
    positions = Counter((row['group'], row['priority'], row['target_kind'], row['channel'])
        for row in dispatches if row['event']=='dispatch')
    write(data/'strategic-transport-purpose-audit.csv', (dict(group=k[0], priority=k[1], purpose=k[2],
        channel=k[3], dispatches=v) for k,v in sorted(positions.items())))
    write(data/'p3-resource-occupation.csv', (row for row in dispatches if row['priority']==3),
          headers=('checkpoint','group','turn','owner','source','target','priority','channel','convoy','load','books_used'))
    write(data/'small-load-by-priority.csv', (row for row in dispatches
        if row.get('convoy') is not None and 0<row['load']<1000 and row['outward_days']>=20),
        headers=('checkpoint','group','turn','owner','priority','convoy','channel','load','outward_days'))
    for phase, filename in (('south','south-results.json'), ('performance','performance-results.json')):
        path = args.runs/phase/filename
        isolated = args.runs/'performance-isolated'/filename
        if phase=='performance' and isolated.exists():
            path = isolated
        if not path.exists():
            continue
        samples = json.loads(path.read_bytes())['results']
        if phase=='south':
            write(data/'southern-checkpoint-results.csv', (dict(group=r['group'], city=r['city'], label=r['label'],
                opening_turn=r['initial']['turn'], stock=r['stock'], missing=r['missing'],
                original_t0=r.get('historical_t0_missing'), final_turn=r['final']['turn'],
                legal_sources=r['initial']['legal']['legal_sources']) for r in samples))
            for name, subset in (('city-and-march-grain-account', samples),
                                 ('baxi-grain-flow-replay', [r for r in samples if r['city']=='baxi'])):
                write(data/(name+'.csv'), (dict(group=r['group'], **posting)
                    for r in subset for posting in r['observed_postings']))
        else:
            write(data/'scheduler-performance-profile.csv', (dict({k: value for k,value in sample.items()
                if k not in ('final','measurements')}) for r in samples for sample in r['samples']))
    baxi_path = args.runs/'baxi-timeline/south-results.json'
    if baxi_path.is_file():
        cases = json.loads(baxi_path.read_bytes())['results']
        write(data/'baxi-actual-meals.csv', (dict(group=r['group'], **bill)
              for r in cases for bill in r['city_ration_settlements']))
        to_json(checks/'baxi-opening-transit-bookings.json',
                [dict(group=r['group'],initial=r['initial'],final=r['final'],actual_missing=r['missing'])
                 for r in cases])
    totals = {r['group']: r for r in fixed_totals}
    passes = {}
    for candidate, reference in (('U6','U0'),('V2','V0')):
        measured = totals[candidate]
        values = [measured[k] for k in ('timely_targets','full_targets','first_gap_grain','returning_delivered')]
        threshold = GUIDES[reference]
        passes[candidate] = dict(measured=values, target=threshold,
                                 covers=all(n>=m for n,m in zip(values,threshold,strict=True)))
    to_json(checks/'fixed-stage-status.json', dict(controls=history_totals, integrated=fixed_totals,
        target_order=['timely_targets','full_targets','first_gap_grain','returning_sources'],
        candidates=passes, exact_prior_pairs=len(matches), prior_identical=sum(row['identical'] for row in matches),
        prior_matching_receipts=sum(row['matches_receipts'] for row in matches),
        prior_matching_first_gaps=sum(row['matches_first_gap'] for row in matches),
        settings={group: settings(group) for group in sorted(totals)}, actual_historical_losses=len(attribution)))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=Path)
    parser.add_argument('prior', type=Path)
    parser.add_argument('output', type=Path)
    package(parser.parse_args())


if __name__ == '__main__':
    main()
