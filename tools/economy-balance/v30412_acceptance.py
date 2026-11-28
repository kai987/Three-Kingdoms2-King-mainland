"""Summarize observed consumption, real freight and matched rule experiments."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from common import to_csv, to_json

CHANNELS = ('local_market', 'ordinary_transport', 'regional_market', 'strategic_granary',
            'production', 'other_credit')
FREIGHT = frozenset(CHANNELS[1:4])
SUPPLY = frozenset(CHANNELS[:4])
PAIRS = (('K0', 'K1'), ('K0', 'K2'), ('K1', 'K2'), ('L0', 'L1'), ('L0', 'L2'), ('L1', 'L2'))


def minimum_consumed(postings, owner, original_due, channels):
    """Prove a lower bound under any admissible mixing of same-owner grain."""
    balance = received = consumed = 0
    for row in postings:
        if row['turn'] >= original_due:
            break
        if row['resource'] == 'ownership' or row['owner'] != owner:
            balance = 0
            continue
        delta = row['delta']
        if delta is None:
            continue
        if delta > 0 and row.get('supply_channel') in channels:
            received += delta
            balance += delta
        elif delta < 0 and row['category'] == 'city_consumption':
            forced = max(0, -delta - max(0, row['balance_before'] - balance))
            balance -= forced
            consumed += forced
        elif delta < 0:
            balance = max(0, balance + delta)
    return received, consumed


def rates(required, paid):
    return paid / required if required else None


def payment_bounds(resident, garrison, paid):
    if None in (resident, garrison, paid):
        return {key: None for key in ('resident_paid_min', 'resident_paid_max',
                                      'garrison_paid_min', 'garrison_paid_max')}
    return dict(resident_paid_min=max(0, paid-garrison), resident_paid_max=min(paid, resident),
                garrison_paid_min=max(0, paid-resident), garrison_paid_max=min(paid, garrison))


def latest_json(directory):
    payload = json.loads((directory/'results.json').read_bytes())
    if payload['status'] != 'complete':
        raise ValueError(f'Incomplete replay results: {directory}')
    return payload['results']


def fixed_data(results):
    grouped, accounts, attributions, sources = {}, [], [], []
    for run in results:
        group, checkpoint = run['group'], run['sha256']
        posts = run['target_postings']
        table = {(row['owner'], row['city'], row['settlement_tick']): row for row in run['actual']
                 if row['event'] == 'city_meal_settled'}
        for row in run['physical_targets']:
            owner, city, due = row['owner'], row['target'], row['deadline_turn']
            key = (checkpoint, owner, city, due)
            event = table.get((owner, city, (due - 1) * 10))
            historical = next(before for before in run['consumption']
                              if (before['owner'], before['city'], before['deadline']) == key[1:])
            requirement = event['required_grain'] if event else None
            paid = event['paid_grain'] if event else None
            missing = event['missing_grain'] if event else None
            if missing != historical['actual_missing'] or requirement != historical['required'] or paid != historical['paid']:
                raise ValueError(f'Actual debit disagrees with the prior observation method: {group} {key}')
            floor = {name: minimum_consumed(posts.get(city, ()), owner, due, channels)
                     for name, channels in (('all_supply', SUPPLY), ('physical', FREIGHT),
                         *((channel, {channel}) for channel in CHANNELS))}
            original = int(row['first_uncovered_grain'])
            deliveries = row['l5_actual_reception']
            entry = dict(group=group, scenario=row['scenario'], checkpoint_sha256=checkpoint, owner=owner,
                city=city, deadline_turn=due, settlement_tick=(due-1)*10, actual_observed=event is not None,
                population=event['population'] if event else None,
                active_garrison=event['active_garrison'] if event else None,
                reserve_troops=event['reserve_troops'] if event else None,
                resident_due=event['resident_due'] if event else None,
                garrison_due=event['garrison_due'] if event else None,
                required_grain=requirement, paid_grain=paid, missing_grain=missing,
                actual_payment_rate=rates(requirement, paid),
                grain_before_settlement=event['grain_before_settlement'] if event else None,
                grain_after_settlement=event['grain_after_settlement'] if event else None,
                original_projected_gap=original, timely_transport_grain=deliveries,
                first_physical_coverage=min(deliveries, original) if deliveries is not None else None,
                all_supply_consumed_minimum=floor['all_supply'][1] if event else None,
                local_grain_consumed_minimum=floor['local_market'][1] if event else None,
                local_only_paid=bool(event and requirement and not missing and not deliveries and
                                     floor['local_market'][1]),
                military_vs_resident_payment_split='pooled' if event else 'unobserved')
            entry.update(payment_bounds(entry['resident_due'], entry['garrison_due'], paid))
            grouped[group, key] = entry
            for name, (received, confirmed) in floor.items():
                attributions.append(dict(group=group, scenario=row['scenario'], checkpoint_sha256=checkpoint,
                    owner=owner, city=city, original_deadline_turn=due, channel=name,
                    warehouse_credits_through_observed_window=received,
                    consumption_through_deadline_minimum=confirmed if event else None,
                    credit_alone_proves_final_meal=False,
                    evidence_status=('lower_bound' if confirmed else 'no_attributable_consumption')
                    if event else 'deadline_debit_unobserved'))
        for row in run['returning_sources']:
            sources.append(row)
        accounts.append(dict(group=group, checkpoint_sha256=checkpoint,
            **{key: value for key, value in run['grain_account'].items() if key != 'categories'},
            **{f'market_{key}': value for key, value in run['market'].items()}, **run['safety']))
    return grouped, accounts, attributions, sources


def comparisons(rows):
    for baseline, candidate in PAIRS:
        keys = sorted({key for group, key in rows if group in (baseline, candidate)})
        for key in keys:
            before, after = rows.get((baseline, key), {}), rows.get((candidate, key), {})
            paired = before.get('actual_observed', False) and after.get('actual_observed', False)
            fields = ('required_grain', 'paid_grain', 'missing_grain', 'actual_payment_rate', 'population',
                      'active_garrison', 'reserve_troops', 'timely_transport_grain', 'first_physical_coverage',
                      'local_grain_consumed_minimum', 'all_supply_consumed_minimum')
            result = dict(pair=f'{baseline}-{candidate}', checkpoint_sha256=key[0], owner=key[1],
                city=key[2], deadline_turn=key[3], paired=paired,
                missing_before_observed=not before.get('actual_observed', False),
                missing_after_observed=not after.get('actual_observed', False),
                **{f'{side}_{field}': row.get(field) for side, row in (('before', before), ('after', after))
                   for field in fields})
            result.update(new_actual_shortage=before['missing_grain']==0 and after['missing_grain']>0 if paired else None,
                delta_actual_missing=after['missing_grain']-before['missing_grain'] if paired else None,
                requirement_reduction=max(0, before['required_grain']-after['required_grain']) if paired else None,
                paid_change=after['paid_grain']-before['paid_grain'] if paired else None,
                original_requirement_covered_by_payment=min(before['required_grain'], after['paid_grain'])
                    if paired else None)
            yield result


def fixed_report(root, out):
    records = latest_json(root/'fixed')
    data, safety, attribution, sources = fixed_data(records)
    rows = list(data.values())
    paired = list(comparisons(data))
    aggregates = []
    for pair in dict.fromkeys(row['pair'] for row in paired):
        full = [row for row in paired if row['pair'] == pair]
        comparable = [row for row in full if row['paired']]
        stat = dict(pair=pair, paired=len(comparable), unmatched=len(full)-len(comparable),
                    new_shortages=sum(row['new_actual_shortage'] for row in comparable),
                    worsened=sum(row['delta_actual_missing'] > 0 for row in comparable),
                    improved=sum(row['delta_actual_missing'] < 0 for row in comparable),
                    improved_with_lower_required=sum(row['delta_actual_missing'] < 0 and row['requirement_reduction'] > 0
                                                     for row in comparable))
        for side in ('before', 'after'):
            for measure in ('required_grain', 'paid_grain', 'missing_grain'):
                field = f'{side}_{measure}'
                stat[field] = sum(row[field] for row in comparable)
            stat[f'{side}_actual_payment_rate'] = rates(stat[f'{side}_required_grain'], stat[f'{side}_paid_grain'])
        aggregates.append(stat)
    physical = []
    for group in sorted({row['group'] for row in rows}):
        series = [row for row in rows if row['group'] == group]
        physical.append(dict(group=group, targets=len(series), actual_meals=sum(row['actual_observed'] for row in series),
            timely_transport_targets=sum(bool(row['timely_transport_grain']) for row in series),
            first_physical_fully_covered=sum((row['first_physical_coverage'] or 0) >= row['original_projected_gap']
                                             for row in series),
            first_physical_coverage=sum(row['first_physical_coverage'] or 0 for row in series),
            timely_transport_grain=sum(row['timely_transport_grain'] or 0 for row in series),
            market_funded_and_paid_without_timely_freight=sum(row['local_only_paid'] for row in series)))
    tables = {'actual-demand-coverage': rows, 'actual-city-consumption-comparison': paired,
              'fixed-first-meal-paired-effect': aggregates, 'effective-supply-channel-attribution': attribution,
              'fixed-physical-freight-comparison': physical, 'resource-safety': safety,
              'returning-slot-coverage-recovery': sources}
    cost, military, requotes = [], [], []
    for run in records:
        group, checkpoint = run['group'], run['sha256']
        base = run['effective']
        market_books = base.get('market_books', 0)
        transport_books = base.get('transport_books', 0)
        direct_books = base.get('direct_resupply_books', 0)
        total = market_books + transport_books + direct_books
        matched = [row for row in rows if row['group'] == group and row['checkpoint_sha256'] == checkpoint]
        proven = sum(row['all_supply_consumed_minimum'] or 0 for row in matched)
        cost.append(dict(group=group, checkpoint_sha256=checkpoint, market_books=market_books,
            physical_transport_books=transport_books, direct_resupply_books=direct_books,
            all_grain_security_books=total, actual_net_freight=base['actual_net_delivered'],
            local_market_purchase=base['city_market_grain'], regional_market_purchase=base['regional_purchased_grain'],
            physical_net_per_transport_book=rates(transport_books, base['actual_net_delivered']),
            local_purchase_per_market_book=rates(market_books, base['city_market_grain']),
            fixed_target_confirmed_supply_in_meals=proven,
            fixed_target_confirmed_supply_per_all_books=rates(total, proven)))
        for row in run['actual']:
            if row['event'] == 'forecast_requote':
                requotes.append(dict(group=group, checkpoint_sha256=checkpoint, **row))
        raw = root/'fixed'/'decision-traces'/f"{Path(run['fixture']).stem}-{group}.jsonl.gz"
        with gzip.open(raw, 'rt', encoding='utf-8') as stream:
            for row in map(json.loads, stream):
                if row['event'] in ('military_preparation_request', 'military_preparation_expired'):
                    military.append(dict(group=group, checkpoint_sha256=checkpoint, **row))
    tables.update({'all-grain-security-command-efficiency': cost, 'military-preparation-occupation': military,
                   'forecast-requote-results': requotes})
    to_json(out.parent/'checks'/'forecast-requote-observation.json',
        {'original_fixed_windows_observed': len(records), 'accepted_requotes_observed': len(requotes),
         'natural_economic_effect': 'unproven', 'controlled_case':
         'test_requote_pays_higher_return_cost_with_a_smaller_legal_load'})
    for city in ('anding', 'donglai'):
        cases = []
        for run in records:
            if not run['fixture'].startswith('chibi-long'):
                continue
            for event in run['actual']:
                if event.get('city') == city:
                    cases.append(dict(group=run['group'], scenario='208-10', checkpoint_sha256=run['sha256'], **event))
        tables[f'{city}-shortage-replay'] = cases
    for name, records in tables.items():
        if records:
            fields = tuple(dict.fromkeys(key for row in records for key in row))
            to_csv(out/f'{name}.csv', ({key: row.get(key) for key in fields} for row in records))


def state_equivalence(root, prior, out):
    previous = json.loads(prior.read_bytes())
    names = {'K0': 'U0', 'K1': 'U6', 'L0': 'V0', 'L1': 'V2'}
    old = {(row['fixture'], row['group']): row['checks'] for row in previous}
    checks = []
    for row in latest_json(root/'fixed'):
        if row['group'] not in names:
            continue
        expected = {item['turn']: item for item in old[row['fixture'], names[row['group']]]}
        actual = {item['turn']: item for item in row['checks']}
        paired = expected.keys() & actual.keys()
        checks.append(dict(group=row['group'], checkpoint_sha256=row['sha256'], replay=row['fixture'],
            turns=len(actual), previous_turns=len(expected), matched_turns=len(paired),
            rng_equal=expected.keys()==actual.keys() and all(expected[t]['rng']==actual[t]['rng'] for t in paired),
            state_equal=expected.keys()==actual.keys() and all(expected[t]['sha256']==actual[t]['sha256'] for t in paired)))
    to_csv(out/'old-rule-equivalence.csv', checks)
    cache = {}
    for row in latest_json(root/'equivalence'):
        cache[row['label'], row['group']] = row
    ratios = []
    for (label, name), plain in sorted(cache.items()):
        if not name.endswith('-no-cache'):
            continue
        actual = cache[label, name.removesuffix('-no-cache')]
        ratios.append(dict(checkpoint=label, group=actual['group'], checkpoint_sha256=actual['checkpoint_sha256'],
            **{key: actual[key] == plain[key] for key in ('hashes','formal_candidate_sequence','transport_receipts')},
            route_queries_with_cache=actual['route_search_calls'], route_queries_without_cache=plain['route_search_calls'],
            actual_communication_records=actual['decision_records'], actual_resource_records=actual['resource_records']))
    to_csv(out/'scheduler-decision-equivalence.csv', ratios)


def history_report(directory, out):
    cases = latest_json(directory)
    summary, timeline = [], []
    for case in cases:
        last = next(row for row in reversed(case['snapshots']) if row['convoy'] is not None)
        end = case['snapshots'][-1]
        lives = [row['row'] for row in case['receipts'] if row['event'] == 'terminal']
        grain = [row['row'] for row in case['receipts'] if row['event'] == 'delivery']
        end_record = lives[-1] if lives else {}
        summary.append(dict(group=case['group'], convoy=case['convoy'], checkpoint_sha256=case['checkpoint_sha256'],
            scenario=case['scenario'], start_turn=case['snapshots'][0]['turn'], end_turn=end['turn'],
            active=end['convoy'] is not None, actual_end=end_record.get('outcome'),
            received_officers=end_record.get('received_officers'), received_troops=end_record.get('troops_received'),
            observed_hunger=end_record.get('hunger_losses', last['convoy']['hunger']),
            last_onboard_grain=last['convoy']['bag'], last_original_city_owner=last['convoy']['source_owner'],
            actual_receipts=sum(row['cargo']['grain'] for row in grain)))
        if case['convoy'] == 3634:
            for row in case['snapshots']:
                timeline.append(dict(group=case['group'], checkpoint_sha256=case['checkpoint_sha256'],
                                     turn=row['turn'], **{k:v for k,v in (row['convoy'] or {}).items() if k!='turn'}))
    to_csv(out/'historical-convoy-regression.csv', summary)
    if timeline:
        fields = tuple(dict.fromkeys(key for row in timeline for key in row))
        to_csv(out/'historical-convoy-3634-policy-divergence.csv',
               ({key: row.get(key) for key in fields} for row in timeline))
        to_json(out.parent/'checks'/'historical-same-state-danger.json',
                [dict(group=case['group'], **case['same_state_danger']) for case in cases
                 if case.get('same_state_danger')])


def supply_report(root, out):
    results = latest_json(root/'south')
    compact, denied, safety, commitments, baxi = [], [], [], [], []
    for case in results:
        opening, final = case['initial'], case['final']
        city, specs = case['city'], case['recorded_rules']
        case_id = dict(checkpoint_sha256=case['checkpoint_sha256'], scenario=case['scene'], group=case['group'],
                       city=city, from_turn=opening['turn'], through_turn=final['turn'])
        with gzip.open(root/'south'/case['actual_ledger'], 'rt', encoding='utf-8') as stream:
            rows = [json.loads(line) for line in stream]
        bills = [row for row in rows if row['event'] == 'city_meal_settled']
        expected = case['missing']
        actual = sum(row['missing_grain'] for row in bills)
        if actual != expected:
            raise ValueError(f'Measurements disagree for {case_id}')
        compact.append(dict(case_id, weather=specs['weather_rules_version'],
            required=sum(row['required_grain'] for row in bills), paid=sum(row['paid_grain'] for row in bills),
            missing=actual, shortage_turns=sum(row['missing_grain'] > 0 for row in bills),
            population_ending=bills[-1]['population'] if bills else None,
            active_garrison_ending=bills[-1]['active_garrison'] if bills else None,
            available_legal_sources=opening['legal']['legal_sources'],
            actual_stock_ending=case['stock']))
        affected = {row['unit_id'] for row in rows if row['event'] == 'unit_meal_settled'
                    and row['unit_kind'] == 'march' and (row['current_city'] == city or city in row['route'])}
        army_totals, outcomes = defaultdict(Counter), defaultdict(dict)
        for row in rows:
            if row['event'] == 'staging_node' and row['city'] == city:
                commitments.append(dict(case_id, **{key: val for key, val in row.items() if key != 'city'}))
            if row['event'] != 'unit_meal_settled' or row['unit_kind'] != 'march' or row['unit_id'] not in affected:
                continue
            refill = row['refill']
            receipt_here = refill if row['current_city'] == city else None
            army_totals[row['unit_id']].update(required=row['required_grain'], paid=row['paid_grain'],
                shortage_days=int(row['hunger_day']), losses=row['losses'],
                requested_at_city=receipt_here['requested_refill'] if receipt_here else 0,
                received_at_city=receipt_here['actual_received_grain'] if receipt_here else 0)
            outcome = outcomes[row['unit_id']]
            if row.get('reached_route_endpoint'):
                outcome.update(actual_route_arrival=row['tick'], actual_route_endpoint=row['route'][-1])
            if row['retreat_requested']:
                outcome.setdefault('actual_withdrawal_request_tick', row['tick'])
            if row['unit_status'] == 'returning':
                outcome.setdefault('actual_returning_tick', row['tick'])
            if receipt_here and receipt_here['requested_refill'] > receipt_here['actual_received_grain']:
                denied.append(dict(case_id, owner=row['owner'], march_id=row['unit_id'], tick=row['tick'],
                    route=row['route'], current_city=row['current_city'],
                    next_legal_supply_node=row['next_legal_supply_node'],
                    remaining_rations=row['remaining_rations'], actual_hunger_day=row['hunger_day'],
                    actual_hunger_losses=row['losses'], **receipt_here))
        for ident, counts in army_totals.items():
            safety.append(dict(case_id, march_id=ident, **counts, **outcomes[ident]))
        if city == 'baxi':
            posting_grain = sum(post['delta'] for post in case['observed_postings']
                if post['resource']=='grain' and post['site']=='facilities._settle_grain_trade' and post['delta'] > 0)
            for army, counts in army_totals.items():
                courier = [row for row in rows if row['event']=='relief_handoff' and row['army']==army]
                baxi.append(dict(case_id, march_id=army, local_grain_bought=posting_grain,
                    actual_city_due=sum(row['required_grain'] for row in bills),
                    actual_city_paid=sum(row['paid_grain'] for row in bills), city_missing=actual,
                    physical_courier_grain=sum(row['grain'] for row in courier),
                    actual_courier_ticks=[row['tick'] for row in courier],
                    **counts, **outcomes[army]))
    for name, rows in (('southern-checkpoint-results', compact), ('transit-march-safety-comparison', safety),
                       ('baxi-city-and-army-balance', baxi),
                       ('transit-refill-denial-ledger', denied), ('transit-commitment-settlement', commitments)):
        if rows:
            fields = tuple(dict.fromkeys(key for row in rows for key in row))
            to_csv(out/f'{name}.csv', ({key: row.get(key) for key in fields} for row in rows))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('phase', choices=('fixed', 'south', 'all', 'equivalence', 'historical'))
    parser.add_argument('--prior', type=Path)
    args = parser.parse_args()
    if args.phase in ('fixed', 'all'):
        fixed_report(args.root, args.out)
    if args.phase in ('south', 'all'):
        supply_report(args.root, args.out)
    if args.phase == 'equivalence':
        if args.prior is None:
            parser.error('An earlier raw resource report is required for equivalence.')
        state_equivalence(args.root, args.prior, args.out)
    if args.phase == 'historical':
        history_report(args.root, args.out)


if __name__ == '__main__':
    main()
