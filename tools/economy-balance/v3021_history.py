"""Reconstruct shortage, custody and return evidence from immutable V3.0.2 logs."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import gzip
import json
from math import ceil
from pathlib import Path
from statistics import median, mean

from common import to_csv, to_json
from v302_report import csv_file_rows, jsonl

SCENARIOS = ('184-02', '208-10')
GROUPS = ('S1', 'S2', 'S3', 'S4')
ORIGINAL_RETURNS = (
    ('long/w221/S3/211/2026/240/184-02',2170),
    ('long/w221/S3/211/2026/240/208-10',1228),
    ('holdout/w221/S3/211/2034/60/207-09',219),
)
UNAVAILABLE = ('', 'null', 'not_applicable', 'not_collected', None)


def n(row,key):
    value = row.get(key)
    return int(value) if value not in UNAVAILABLE else None


def months(row,key):
    value = row.get(key)
    return json.loads(value) if value not in UNAVAILABLE else {}


def percentile(values,q):
    return values[ceil(len(values)*q)-1] if values else None


def events(directory):
    fore, requests, blocked, shipments, delivered = {}, {}, set(), {}, {}
    reasons = Counter()
    for row in jsonl(directory/'strategic-granary-events.jsonl.gz'):
        kind = row['event']
        if kind == 'city_forecast':
            fore[row['turn'],row['city'],row['owner']] = row
        elif kind == 'dispatch_requested':
            requests[row['turn'],row['target'],row['owner']] = row
            reasons.update(row['rejections'])
        elif kind == 'dispatch_blocked' and row.get('reason') == 'already_committed':
            blocked.add((row['turn'],row['target'],row['owner']))
        elif kind == 'order_dispatched':
            shipments[row['id']] = row
        elif kind == 'order_delivered':
            delivered[row['id']] = row
    return fore, requests, blocked, shipments, delivered, reasons


def timelines(directory, hot, observed, shortages, pair):
    postings = defaultdict(dict)
    with gzip.open(directory/'warehouse-postings.csv.gz','rt',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['city'] not in hot:
                continue
            period = postings[int(row['turn']),row['city']]
            res, category = row['resource'],row['category']
            if res in ('grain','gold','reserves'):
                period.setdefault(res+'_opening',n(row,'balance_before'))
                period[res+'_closing'] = n(row,'balance_after')
                if res == 'grain':
                    ledger = period.setdefault('grain_categories',Counter())
                    ledger[category] += n(row,'delta')
            elif res == 'ownership':
                period.setdefault('ownership_events',[]).append([row['balance_before'],row['balance_after']])
    market = defaultdict(Counter)
    with gzip.open(directory/'market-stock-flow.csv.gz','rt',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['city'] in hot:
                bucket = market[int(row['turn']),row['city']]
                bucket['closing_market_stock'] = n(row,'stock')
                bucket[row['kind']+'_volume'] += n(row,'grain') or 0
    forces = {(int(row['turn']),row['target']) for row in csv_file_rows(directory/'troop-flows.csv')
              if row['target'] in hot and any(row['kind'].startswith(k) for k in
                  ('officer','battle','garrison','march','convoy','stationed'))}
    forecasts = defaultdict(list)
    for (turn,city,_), brief in observed.items():
        if city in hot:
            forecasts[turn,city].append(brief)
    balances = defaultdict(dict)
    for (turn,city), row in sorted(postings.items()):
        for resource in ('grain','gold','reserves'):
            balances[city].setdefault(resource,row.get(resource+'_opening'))
            close = row.get(resource+'_closing')
            if close is not None:
                balances[city][resource] = close
        owner = row.get('ownership_events',[])
        candidates = forecasts.get((turn,city),[])
        city_market = market.get((turn,city),{})
        yield dict(pair,command_start_turn=turn, city=city, warehouse_grain=balances[city].get('grain'),
            warehouse_gold=balances[city].get('gold'),reserves=balances[city].get('reserves'),
            grain_postings=dict(row.get('grain_categories',{})),ownership_events=owner,
            market_stock_close=city_market.get('closing_market_stock'),market_flows=dict(city_market),
            forecast_observations=candidates, observed_troop_flow=(turn,city) in forces,
            shortage_debit_same_turn=shortages.get((turn,city)))


def shortage_rows(directory, pair, hot, facts):
    fore, requests, blocked, shipments, received, reasons = facts
    shortages = list(csv_file_rows(directory/'shortages.csv'))
    by_city, source_events = defaultdict(list), []
    lookup = {(int(row['turn']),row['city'],row['owner']):row for row in shortages}
    for row in shortages:
        key = (int(row['turn']),row['city'],row['owner'])
        turn, city, owner = key
        need = n(row,'missing')
        refs = [item for offset in range(10) if (item := requests.get((turn-offset,city,owner)))]
        previous_forecast = [brief for offset in range(1,10) if (
            brief := fore.get((turn-offset,city,owner)))]
        l0 = n(row,'other_stock')
        l1, l2 = (months(row,k).get('3') for k in ('reserve_surplus','legal_route_surplus'))
        raw_timely_placeholder = n(row,'timely_new_shipment')
        has_block = any((turn-offset,city,owner) in blocked for offset in range(1,10))
        flags = []
        if l0 is not None and l0 < need:
            flags.append('faction_stock_below_bill')
        if l0 is not None and l0 >= need and l1 is not None and l1 < need:
            flags.append('reserve_surplus_below_bill')
        if l1 is not None and l1 >= need and l2 is not None and l2 < need:
            flags.append('legal_surplus_below_bill')
        if any('no_eligible_escort' in candidate['rejections'] for candidate in refs):
            flags.append('prior_candidate_escort_rejection')
        if any('source_convoy_limit' in candidate['rejections'] for candidate in refs):
            flags.append('prior_candidate_source_limit')
        if has_block:
            flags.append('prior_target_has_order')
        if any(candidate['delayed_receipts'] for candidate in refs):
            flags.append('prior_receipt_at_risk')
        fields = dict(pair,turn=turn,year=n(row,'year'),month=n(row,'month'),day=n(row,'day'),
            city=city,owner=owner,only_hotspot=city in hot,required=n(row,'required'),missing=need,
            stationed_before=n(row,'stationed_before'),reserves_before=n(row,'reserves_before'),
            actual_active_losses=n(row,'active_lost'),actual_reserve_losses=n(row,'reserve_lost'),
            faction_other_stock=l0, surplus_after_3mo_floor=l1, legally_reachable_surplus_3mo=l2,
            qualified_lift=None, recorded_timely_new_shipment=None,
            raw_timely_new_shipment_placeholder=raw_timely_placeholder,actual_timely_new_receipt=None,
            forecast_recent_gap=previous_forecast[0]['gap'] if previous_forecast else None,
            headroom_basis=row['headroom_basis'],observed_associations=flags,causal_attribution='not_established')
        by_city[city].append(fields)
    for shipment in shipments.values():
        turn, source, owner = shipment['turn'], shipment['source'], shipment['owner']
        followed = [(turn+offset,n(row,'missing')) for offset in (1,2,3) if (
            row:=lookup.get((turn+offset,source,owner)))]
        event = received.get(shipment['id'])
        source_events.append(dict(pair,order=shipment['id'],source=source,target=shipment['target'],
            turn=turn,departure_debit=shipment['load']+shipment['rations'],
            confirmed_predeparture=fore.get((turn,source,owner),{}).get('total'),
            actual_target_received=event['delivered_grain'] if event else None,
            actual_delivery_turn=event['delivered_turn'] if event else None,
            deadline=shipment['deadline'], subsequent_shortages_3turns=followed,
            budget_error_confirmed=None))
    return by_city, source_events


def nine_turn_followup(directory, pair, data, facts):
    fore, _, _, shipments, _, _ = facts
    sources = defaultdict(list)
    for order in shipments.values():
        sources[order['source'],order['owner']].append(order)
    picked = []
    for city, shortages in data.items():
        for debit in shortages:
            turn, owner = debit['turn'], debit['owner']
            prior = [r for r in sources[city,owner] if 0<=turn-r['turn']<=9]
            if prior:
                picked.append((debit, sorted(prior,key=lambda r:(r['turn'],r['id']))))
    keys = {(row['turn']-offset,row['city']) for row,_ in picked for offset in range(10)}
    ledger = defaultdict(list)
    with gzip.open(directory/'warehouse-postings.csv.gz','rt',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            key = (int(row['turn']),row['city'])
            if key in keys and row['resource'] in ('grain','ownership'):
                ledger[key].append(row)
    troop = defaultdict(list)
    for row in csv_file_rows(directory/'troop-flows.csv'):
        for city in {row['source'],row['target']}:
            key = int(row['turn']),city
            if key in keys:
                troop[key].append({k:row[k] for k in ('turn','kind','source','target','active','reserves')})
    for debit, orders in picked:
        turn, city, owner = (debit[k] for k in ('turn','city','owner'))
        evidence = []
        for sent in orders:
            at = sent['turn']
            forecast = fore.get((at,city,owner),{})
            debit_expected = sent['load']+sent['rations']
            posted = [row for row in ledger[at,city] if row['owner']==owner and row['category']=='convoy_load']
            closing = posted[-1] if len(posted)==2 and sum(n(row,'delta') for row in posted)==-debit_expected else None
            if len(posted)==1 and n(posted[0],'delta')==-debit_expected:
                closing=posted[0]
            evidence.append(dict(order=sent['id'],turn=at,load=sent['load'],ration_bag=sent['rations'],
                exact_closing_stock=n(closing,'balance_after') if closing else None,
                observed_stock_at_forecast=forecast.get('total'),protected_tag=forecast.get('reserve'),
                published_storage_target=forecast.get('target')))
        following, movements, ownership = Counter(), [], []
        for period in range(orders[0]['turn'],turn+1):
            for row in ledger[period,city]:
                if row['resource']=='ownership':
                    ownership.append([period,row['balance_before'],row['balance_after']])
                elif row['owner']==owner:
                    following[row['category']] += n(row,'delta')
            movements.extend(troop[period,city])
        yield dict(pair,turn=turn,city=city,owner=owner,required=debit['required'],missing=debit['missing'],
            active_troops=debit['stationed_before'],reserves=debit['reserves_before'],matched_orders=evidence,
            grain_postings_by_category=dict(following),troop_flows=movements,ownership_changes=ownership,
            attribution='insufficient_counterfactual_evidence')


def historical(root, out):
    causes, depth, city_ledger, source_events, exports, months = [], [], [], [], [], []
    caps, prospects, counts, nine_turn = [], [], [], []
    for scenario in SCENARIOS:
        exact = root/f'long/w221/S3/211/2026/240/{scenario}'
        ranked = Counter()
        for row in csv_file_rows(exact/'shortages.csv'):
            ranked[row['city']] += int(row['missing'])
        hot = {city for city,_ in ranked.most_common(5)}
        for group in GROUPS:
            d = root/f'long/w221/{group}/211/2026/240/{scenario}'
            pair = dict(scenario=scenario,group=group,seed=2026,strategy=211,weather=221)
            facts = events(d)
            by_city, posts = shortage_rows(d,pair,hot,facts)
            fore, _, blocked, shipments, delivered, reasons = facts
            causes.extend(row for rows in by_city.values() for row in rows)
            source_events += posts
            if group=='S3':
                nine_turn.extend(nine_turn_followup(d,pair,by_city,facts))
            shortage_debits = {(r['turn'],r['city']):r['missing'] for city in hot for r in by_city[city]}
            city_ledger += timelines(d,hot,fore,shortage_debits,pair)
            months.extend(dict(pair, **{key:r[key] for key in ('elapsed_months','elapsed_turns','year','month',
                'city','owner','population','land','industry','town','gold_stock','grain_stock','market_stock',
                'monthly_regular_grain','monthly_fixed_grain','strategic_reserve_target','stationed_active_troops',
                'city_reserve_troops','sustainable_stationed_troops')})
                for r in csv_file_rows(d/'cities.csv') if r['city'] in hot)
            counts.extend(dict(pair, reason=name, rejected_candidate_pairs=n, distinct_source_assessments=None)
                          for name, n in reasons.items())
            caps.append(dict(pair,pair_rejections=reasons['source_convoy_limit'],
                lost_qualified_grain=None,lost_timely_grain=None,note='capacity counterfactual not captured in V3.0.2'))
            prospects += [dict(pair,turn=turn,target=target,owner=owner,
                old_forecast_gap=fore.get((turn,target,owner),{}).get('gap'),
                old_reliable=fore.get((turn,target,owner),{}).get('reliable'),
                old_risky=fore.get((turn,target,owner),{}).get('risk'), remaining_dispatch_quantity=None)
                for turn,target,owner in sorted(blocked)]
            for city, rows in by_city.items():
                for period in range(4):
                    selected = [r for r in rows if period*180<r['turn']<=(period+1)*180]
                    if not selected:
                        continue
                    values = sorted(r['missing'] for r in selected)
                    longest = streak = 0
                    prior = -2
                    for event in selected:
                        streak = streak+1 if event['turn']==prior+1 else 1
                        longest = max(longest,streak)
                        prior = event['turn']
                    depth.append(dict(pair,city=city,period_years=f'{period*5+1}-{(period+1)*5}',
                        shortage_turns=len(values),missing=sum(values),mean_missing=round(mean(values),2),
                        median_missing=median(values),p90=percentile(values,.90),p95=percentile(values,.95),
                        longest_streak=longest,fraction_of_bill=round(sum(values)/sum(r['required'] for r in selected),6),
                        active_lost=sum(r['actual_active_losses'] for r in selected),
                        reserve_lost=sum(r['actual_reserve_losses'] for r in selected)))
            exports.append(dict(pair, measured_shortage_turns=sum(map(len, by_city.values())),
                source_dispatches=len(shipments), dispatch_with_following_shortage=sum(
                    bool(row['subsequent_shortages_3turns']) for row in posts),
                budget_faults_confirmed=None, actual_timely_grain=sum(row['delivered_grain']
                    for row in delivered.values() if row['delivered_turn']<row['deadline'])))
    for label, rows in (
        ('shortage-root-cause',causes),('shortage-severity-comparison',depth),('top-city-turn-ledger',city_ledger),
        ('top-city-monthly-facts',months),
        ('source-shortage-causality',source_events),('source-convoy-limit-analysis',caps),
        ('source-shortage-nine-turn-window',nine_turn),
        ('duplicate-candidate-analysis',counts),('existing-delivery-coverage',prospects)):
        to_csv(out/f'{label}.csv',rows)
    to_json(out/'historical-observation-status.json',exports)


def returning(root,out):
    facts = []
    for relative, ident in ORIGINAL_RETURNS:
        directory = root/relative
        case = dict(path=f'observed/{relative}',convoy=ident)
        for name in ('convoy-events.csv','convoy-survival.csv','convoy-terminal-events.csv',
                     'emergency-transport-decisions.csv','emergency-local-refills.csv'):
            case[name[:-4]] = [r for r in csv_file_rows(directory/name) if n(r,'convoy_id') == ident]
        for name, key in (('convoy-ledger.csv.gz','convoy_id'),('transport-progress-daily.csv.gz','convoy')):
            with gzip.open(directory/name,'rt',encoding='utf-8') as stream:
                case[name[:-7]] = [r for r in csv.DictReader(stream) if n(r,key)==ident]
        facts.append(case)
    to_json(out/'historical-return-traces.json',facts)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('observed',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    historical(args.observed,args.output)
    returning(args.observed,args.output)


if __name__=='__main__':
    main()
