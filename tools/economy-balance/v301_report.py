"""Recompute V3.0.1 results from recorded economy and physical transport receipts."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import gzip
from hashlib import file_digest, sha256
import io
import json
from pathlib import Path
from statistics import mean
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from common import ROOT, catalog_paths, git, to_json
from v22_report import faction_survival, write
from v221_report import supply
from v222_experiments import source_identity
from v301_experiments import ROOT as OUTPUT, stage_cases
from remake import economic_regions, market_pricing, route_hazards
from remake.regional_procurement import landed_cents

SCHEMA='tk2-regional-economy-v301-validation-v1'
WAVES=('initial','winter','long','holdout')
EXPECTED={case:wave for wave in WAVES for case in stage_cases(wave)}
CORE=('unpaid_city_turns','rations_missing','market_city_turns','markets_empty_samples',
      'battles','ai_sorties','convoy_dispatched','convoy_grain_arrived','convoy_hunger_losses',
      'grain_stock','gold_stock','population','active_troops','reserves','monthly_gold',
      'march_hunger_losses','ai_sortie_quote_blocked','requested_aid_refused')
PAIR_METRICS=('unpaid_city_turns','rations_missing','empty_market_percent','mean_buy',
      'regional_net_delivered','cross_region_delivered','winter_timely_percent','annual_timely_percent',
      'convoy_hunger_losses','convoy_grain_arrived','battles','ai_sorties',
      'gold_stock','grain_stock','population','active_troops','small_faction_survival_percent',
      'regional_end_inventory_hhi','mean_turn_cpu_seconds','p95_turn_wall_seconds')
AUDITED_BASELINE=('monthly.csv','factions.csv','cities.csv','shortages.csv','convoys.csv',
                  'regional-weather-daily.csv','river-ice-daily.csv','supply-episodes-weather-aware.csv')
OBSERVED_FILES=frozenset(AUDITED_BASELINE)|frozenset('run.json battles.csv troop-flows.csv action-capacity.csv '
    'army-convoys.csv army-requests.csv convoy-events.csv convoy-ledger.csv.gz convoy-resolution-daily.csv.gz '
    'convoy-relief-deliveries.csv convoy-relief-requests.csv convoy-survival.csv convoy-terminal-events.csv '
    'emergency-evacuation-plans.csv emergency-local-refills.csv emergency-transport-decisions.csv '
    'transport-progress-daily.csv.gz ice-transport-events.csv winter-cargo-impacts.csv weather-route-impacts.csv '
    'market-stock-flow.csv.gz city-market-prices.csv.gz market-price-changes.csv.gz regional-market-daily.csv.gz '
    'regional-market-monthly.csv regional-orders.jsonl route-changes.csv unresolved-convoy-cases.csv '
    'supply-episodes.csv supply-requests.csv'.split())
RECEIPTS=('cargo_rations','cargo_route_loss','cargo_weather_loss','cargo_delivered',
          'cargo_returned','cargo_abandoned','cargo_remaining')
SCRIPTS=('v301_experiments.py','v301_report.py','v301_replay_1706.py','v301_commercial_fixture.py')
ARCHIVE='three-kingdoms-regional-economy-v301-validation.zip'


def digest(path):
    with path.open('rb') as file:
        return file_digest(file,'sha256').hexdigest()


def rows(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8',newline='') as stream:
        yield from csv.DictReader(stream)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def n(row,key):
    return int(row[key])


def pct(amount,total):
    return round(amount*100/total,6) if total else None


def selected(identity,*keys):
    return {key:identity[key] for key in keys}


def match_digest(path,prior):
    if path.suffix=='.gz':
        with gzip.open(path,'rb') as a,gzip.open(prior,'rb') as b:
            actual,reference=file_digest(a,'sha256').hexdigest(),file_digest(b,'sha256').hexdigest()
    else:
        actual,reference=digest(path),digest(prior)
    return dict(file=path.name,actual=actual,reference=reference,equal=actual==reference)


def run_directory(root,case):
    seed,scenario,strategy,group,months,weather=case
    return root/'observed'/f'w{weather}'/f'{group}-{strategy}'/str(seed)/str(months)/scenario


def identity(case,run):
    seed,scenario,strategy,group,months,weather=case
    return dict(wave=EXPECTED[case],scenario=scenario,seed=seed,strategy=strategy,
                weather=weather,group=group,months=months,full_months=run['full_months'],outcome=run['outcome'])


def metadata(output):
    cities={}
    links={}
    for path in catalog_paths():
        data=read_json(path)
        scenario=data['id']
        for city in data['cities']:
            cities.setdefault(city['id'],dict(city=city['id'],name=city['name'],
                region=economic_regions.region(city['id']),
                region_name=economic_regions.REGIONS[economic_regions.region(city['id'])][0],
                map_x=city.get('x'),map_y=city.get('y')))
        for route in data['travel_routes']:
            a,b=route['from'],route['to']
            for origin,target in ((a,b),(b,a)):
                if not route_hazards.route_allowed(data,route,origin,target):
                    continue
                values=[route_hazards.evaluate_leg(data,route,origin,target,month) for month in range(1,13)]
                days=[row['days'] for row in values]
                key=route['id'],origin,target
                entry=links.setdefault(key,dict(route=route['id'],source=origin,
                    target=target,source_region=economic_regions.region(origin),target_region=economic_regions.region(target),
                    mode=route['mode'],terrain=route.get('terrain'),distance_km=route.get('distance_km'),
                    january_days=days[0],min_season_days=min(days),max_season_days=max(days),
                    one_way=not route_hazards.route_allowed(data,route,target,origin),catalogs=[]))
                if entry['january_days']!=days[0] or entry['one_way']==route_hazards.route_allowed(data,route,target,origin):
                    raise ValueError(f'Divergent immutable route definition: {route["id"]}')
                entry['catalogs'].append(scenario)
    if any(city['region']=='unassigned' for city in cities.values()):
        raise ValueError('A published city is missing regional geography')
    write(output,'city-economic-regions',sorted(cities.values(),key=lambda row:(row['region'],row['city'])))
    write(output,'regional-market-network',sorted(links.values(),key=lambda row:(row['source'],row['target'],row['route'])))
    examples=[]
    for quantity in (0,2000,2499,2500,4999,5000,9999,10000,15000,19999,20000,24999,25000,27000):
        band=market_pricing.inventory_band(quantity,10_000)
        adjust=market_pricing.ADJUSTMENTS[band]
        buy,sell=market_pricing.prices(11,9,-1,adjust)
        examples.append(dict(stock=quantity,monthly_supply=10000,band=market_pricing.BANDS[band],
            base_buy=11,base_sell=9,season=-1,adjustment=adjust,buy=buy,sell=sell,
            landed_cents_reference=landed_cents(80,500,10,9000)))
    write(output,'market-price-cases',examples)
    return len(cities),len(links)


def market_flows(directory):
    previous={}
    sums=defaultdict(Counter)
    dated=defaultdict(Counter)
    months=set()
    for row in rows(directory/'market-stock-flow.csv.gz'):
        city,channel=row['city'],row['channel']
        stock=n(row,'stock')
        opening=n(row,'opening_stock')
        if opening!=previous.get(city,0) or not 0<=stock<=n(row,'capacity'):
            raise ValueError((directory,'market predecessor or capacity',city,row))
        bucket=sums[city,channel or 'market_supply']
        bucket['samples']+=1
        if row['kind']=='restock':
            period=(city,n(row,'last_restock_month'))
            if period in months:
                raise ValueError((directory,'duplicate monthly restock',period))
            months.add(period)
            replenished,overflow=n(row,'restocked'),n(row,'overflow')
            if opening+replenished-overflow!=stock:
                raise ValueError((directory,'issuance balance',row))
            bucket.update(replenished=replenished,overflow=overflow)
        elif row['kind'] in ('buy','sell'):
            amount=n(row,'grain')
            if opening+(-amount if row['kind']=='buy' else amount)!=stock:
                raise ValueError((directory,'physical market transfer',row))
            bucket[row['kind']+'_grain']+=amount
            bucket[row['kind']+'_gold']+=n(row,'gold')
            dated[(economic_regions.region(city),n(row,'year')*12+n(row,'month'))][row['kind']]+=amount
        else:
            raise ValueError(row['kind'])
        previous[city]=stock
    return previous,sums,dated


def quoted_market(directory,expected):
    city_latest={}
    markets=defaultdict(Counter)
    histogram=Counter()
    for row in rows(directory/'city-market-prices.csv.gz'):
        city=row['city']
        quantity,supply_amount,buy,sell=n(row,'stock'),n(row,'supply'),n(row,'buy'),n(row,'sell')
        city_latest[city]=quantity
        bucket=markets[row['region']]
        bucket.update(samples=1,empty=int(quantity==0),severe=int(quantity*4<supply_amount),
                      ample=int(quantity>=2*supply_amount),total_stock=quantity,buy=buy,sell=sell)
        histogram[row['region'],buy,sell,row['band']]+=1
    if city_latest!=expected:
        raise ValueError((directory,'market stock at cutoff',set(city_latest)^set(expected)))
    return markets,histogram


def order_flows(directory):
    states={}
    plans=Counter()
    postings=defaultdict(Counter)
    for line in (directory/'regional-orders.jsonl').open(encoding='utf-8'):
        event=json.loads(line)
        kind=event['event']
        if kind=='warehouse_income':
            postings[event['channel']].update(grain=event['grain'],gold=event['gold'],entries=1)
            continue
        if kind=='regional_trade_gate':
            plans['commercial_'+event['reason']]+=1
            continue
        if kind.endswith('_plan'):
            plans[kind]+=1
            plans.update(event['work'])
            for attempt in event.get('attempts',[event]):
                plans['offers']+=attempt['candidates']
                plans.update({'rejected_'+reason:value for reason,value in attempt['rejections'].items()})
            continue
        order=states.setdefault(event['order_id'],{})
        if kind in order:
            raise ValueError((directory,'duplicate order receipt',kind,event['order_id']))
        order[kind]=event
    for order in states.values():
        purchase,dispatch,receipt,close,sale=(order.get('regional_'+step) for step in
            ('purchase','dispatch','delivery','transport_closed','sale'))
        if purchase is None or dispatch and dispatch['grain']!=purchase['grain']:
            raise ValueError((directory,'invalid market order dispatch',order))
        if receipt and (dispatch is None or receipt['grain']>purchase['grain']
                        or receipt['turn']<dispatch['turn']):
            raise ValueError((directory,'invalid delivery custody',order))
        if sale and (receipt is None or sale['grain']>receipt['grain']
                     or sale['turn']<receipt['turn'] or sale['target']!=receipt['position']):
            raise ValueError((directory,'invalid sale custody',order))
        if close and (dispatch is None or close['extra_rations']<0
                      or close['cargo_dispatched']+close['cargo_received']!=sum(close[key] for key in RECEIPTS)
                      or receipt and receipt['grain']!=close['cargo_delivered']):
            raise ValueError((directory,'invalid cargo custody',order))
    return states,plans,postings


def analyze(case,run,directory,exports):
    tag=identity(case,run)
    opened, *_, final=list(rows(directory/'monthly.csv'))
    actual_scope=run.get('warehouse_postings') is True
    ending,flow,dated_market=market_flows(directory)
    regions,histogram=quoted_market(directory,ending)
    orders,planning,postings=order_flows(directory)
    labels=run['market_stage']
    applicable=lambda value, stage: value if labels>=stage else 'not_applicable'
    output=defaultdict(Counter)
    paid=Counter()
    landed=0
    for order_id,order in orders.items():
        buy=order['regional_purchase']
        dispatch=order.get('regional_dispatch')
        delivery=order.get('regional_delivery')
        close=order.get('regional_transport_closed')
        sale=order.get('regional_sale')
        origin,target=buy['source'],buy['target']
        origin_region,target_region=map(economic_regions.region,(origin,target))
        category=buy['purpose']
        volume=delivery['grain'] if delivery else 0
        result=output[category]
        result.update(orders=1,purchased=buy['grain'],purchase_gold=buy['gold'],dispatches=int(dispatch is not None),
            deliveries=int(delivery is not None),delivered=volume,failed=int('regional_dispatch_failed' in order),
            cross_region_delivered=volume if origin_region!=target_region else 0,sold=sale['grain'] if sale else 0,
            sale_gold=sale['gold'] if sale else 0,still_in_transit=int(dispatch is not None and close is None))
        if buy['deadline'] is not None and delivery:
            result['timed_deliveries']+=1
            result['timely_deliveries']+=(delivery['turn']-buy['turn'])*10<buy['deadline']
        if close:
            paid.update({key:close[key] for key in ('rations_used','extra_rations','escort_base_grain',
                'escort_extra_grain','cargo_rations','cargo_returned','cargo_route_loss','cargo_weather_loss',
                'cargo_received','cargo_abandoned','cargo_remaining')})
        cash=(sale['gold'] if sale else 0)-buy['gold']
        ref=buy.get('reference_price')
        economic=(cash*1000-close['extra_rations']*ref if ref is not None else 'not_collected') if sale and close else None
        actual_cost=(landed_cents(buy['gold'],close['extra_rations'],ref,volume)
                     if ref is not None else 'not_collected') if close and volume else None
        row=dict(tag,order=order_id,purpose=category,automatic=buy['automatic'],source=origin,target=target,
            source_region=origin_region,target_region=target_region,buy_turn=buy['turn'],
            dispatch_turn=dispatch['turn'] if dispatch else None,arrival_turn=delivery['turn'] if delivery else None,
            actual_receiving_city=delivery['position'] if delivery else close['actual_city'] if close else None,
            grain_purchased=buy['grain'],grain_sent=dispatch['grain'] if dispatch else 0,grain_delivered=volume,
            grain_sold=sale['grain'] if sale else 0,source_stock_trade_gold=buy['gold'],
            destination_stock_trade_gold=sale['gold'] if sale else 0,route=buy['route'],modes=buy['route_types'])
        exports['commodity-grain-flow'].append(row)
        exports['landed-cost-comparison'].append(dict(row,estimated_net=buy['estimated_net'],
            estimated_days=buy['estimated_days'],estimated_grain_loss=buy['estimated_loss'],
            planned_escort_rations=buy['reserved_rations'],forecast_escort_rations=buy['expected_rations'],
            estimate_cents_per_thousand=buy['landed_cents'],actual_extra_grain=close['extra_rations'] if close else None,
            actual_cents_per_thousand=actual_cost,actual_reference_price=ref if ref is not None else 'not_collected',
            deadline_days=buy['deadline']))
        if category=='trade':
            exports['trade-profit-comparison'].append(dict(row,receipt_scope='spectator_matrix',net_cash=cash,
                unsold_receipt_grain=volume-row['grain_sold'],economic_milli=economic))
        landed+=buy['landed_cents']
    for side in ('buy','sell'):
        flow_side='grain_bought' if side=='buy' else 'grain_sold'
        gold_side='purchase_gold' if side=='buy' else 'sale_gold'
        observed=(sum(v[side+'_grain'] for v in flow.values()),sum(v[side+'_gold'] for v in flow.values()))
        if observed!=(n(final,flow_side),n(final,gold_side)):
            raise ValueError((directory,'market cash or grain receipts differ from official totals',side,observed))
    for purpose in ('procurement','trade'):
        source_rows=[entry for (_,channel),entry in flow.items() if channel=='regional_'+purpose]
        if sum(v['buy_grain'] for v in source_rows)!=output[purpose]['purchased']:
            raise ValueError((directory,'regional purchase differs from the physical market',purpose))
    for purpose in ('procurement','trade'):
        entry=output[purpose]
        level=2 if purpose=='procurement' else 3
        metrics=dict(tag,receipt_scope='automatic_observation',
            **{key:applicable(entry[key],level) for key in ('orders','purchased','purchase_gold','dispatches','deliveries',
                'delivered','sold','sale_gold','cross_region_delivered','failed','still_in_transit','timed_deliveries','timely_deliveries')})
        if purpose=='procurement':
            metrics.update(candidate_evaluations=applicable(planning['evaluations'],2),
                blocked={key[9:]:value for key,value in planning.items() if key.startswith('rejected_')})
        else:
            metrics.update(commercial_gates={key[11:]:value for key,value in planning.items() if key.startswith('commercial_')},
                net_cash=applicable(entry['sale_gold']-entry['purchase_gold'],3))
        exports['regional-'+purpose+'-comparison'].append(metrics)
    for (city,channel),values in sorted(flow.items()):
        exports['market-stock-flow'].append(dict(tag,city=city,region=economic_regions.region(city),
            channel=channel,**{key:values[key] for key in ('samples','replenished','overflow','buy_grain','sell_grain','buy_gold','sell_gold')},
            ending_stock=ending[city]))
    for (region,buy,sell,band),count in sorted(histogram.items()):
        exports['market-price-distribution'].append(dict(tag,region=region,band=band,buy=buy,sell=sell,city_samples=count))
    for region,values in sorted(regions.items()):
        exports['regional-market-shortages'].append(dict(tag,region=region,city_samples=values['samples'],
            empty=values['empty'],severe=values['severe'],ample=values['ample'],
            empty_percent=pct(values['empty'],values['samples'])))
    actual_shortages=defaultdict(Counter)
    for event in rows(directory/'shortages.csv'):
        label=economic_regions.region(event['city'])
        period=n(event,'year')*12+n(event,'month')
        actual_shortages[label,period].update(unpaid_city_turns=1,grain_shortage=n(event,'missing'))
    for row in rows(directory/'regional-market-monthly.csv'):
        values={key:n(row,key) for key in ('turn','year','month','day','markets','stock','capacity','supply')}
        values['in_transit']=int(row['in_transit'] or 0)
        region=row['region']
        period=values['year']*12+values['month']
        window=sum((dated_market[region,m] for m in range(period-2,period+1)),Counter())
        shortages=actual_shortages[region,period]
        exports['regional-supply-demand'].append(dict(tag,region=region,**values,
            buy_mean=float(row['buy_mean']),sell_mean=float(row['sell_mean']),stock_coverage=float(row['stock_coverage']),
            shortage_city_turns=shortages['unpaid_city_turns'],actual_warehouse_grain_gap=shortages['grain_shortage'],
            severe_markets=n(row,'severe'),ample_markets=n(row,'ample'),
            market_bought_during_month=dated_market[region,period]['buy'],
            market_sold_during_month=dated_market[region,period]['sell'],
            market_bought_three_calendar_months=window['buy'],market_sold_three_calendar_months=window['sell']))
    overall,winter=supply(run,directory,'supply-episodes-weather-aware.csv')
    performance=run['performance']
    meals=run['transport_survival']
    totals=meals['totals']
    values=dict(tag,**{key:n(final,key) for key in CORE},**faction_survival(directory))
    values.update(
        regional_orders=sum(s['orders'] for s in output.values()),
        regional_net_delivered=sum(s['delivered'] for s in output.values()),
        cross_region_delivered=sum(s['cross_region_delivered'] for s in output.values()),
        total_market_issued=sum(v['replenished'] for v in flow.values()),
        market_capacity_loss=sum(v['overflow'] for v in flow.values()),market_stock=sum(ending.values()),
        empty_market_percent=pct(sum(x['empty'] for x in regions.values()),sum(x['samples'] for x in regions.values())),
        mean_buy=round(sum(x['buy'] for x in regions.values())/sum(x['samples'] for x in regions.values()),5),
        mean_sell=round(sum(x['sell'] for x in regions.values())/sum(x['samples'] for x in regions.values()),5),
        average_landed_cents=round(landed/len(orders),4) if orders else None,
        stock_account='verified',annual_required=overall.get('required',0),annual_timely=overall.get('timely',0),
        winter_required=winter.get('required',0),winter_timely=winter.get('timely',0),
        annual_timely_percent=pct(overall.get('timely',0),overall.get('required',0)),
        winter_timely_percent=pct(winter.get('timely',0),winter.get('required',0)),
        mean_turn_cpu_seconds=performance['mean_turn_cpu_seconds'],
        p95_turn_wall_seconds=performance['percentiles']['wall']['95'],
        market_entries=sum(v['samples'] for v in flow.values()))
    end_regions=Counter()
    for city,quantity in ending.items():
        end_regions[economic_regions.region(city)]+=quantity
    values['regional_end_inventory_hhi']=round(sum(v*v for v in end_regions.values())/sum(ending.values())**2,7)
    gold_open=n(opened,'gold_stock')
    trade=output['trade']
    net=trade['sale_gold']-trade['purchase_gold']
    gold_posted=postings['regular']['gold'] if actual_scope else 'not_collected'
    exports['gold-inflation-comparison'].append(dict(tag,opening_gold=gold_open,closing_gold=values['gold_stock'],
        difference=values['gold_stock']-gold_open,percent_change=pct(values['gold_stock']-gold_open,gold_open),
        regular_gold_posted=gold_posted,ordinary_gold_price_basis='opening_and_monthly_snapshots',
        ordinary_monthly_gold_at_cutoff=values['monthly_gold'],
        total_market_purchases=sum(v['buy_gold'] for v in flow.values()),
        total_market_sales=sum(v['sell_gold'] for v in flow.values()),trade_cash_net=applicable(net,3),
        trade_cash_relative_to_real_regular_income_percent=pct(net,gold_posted) if actual_scope and labels==3 else
            ('not_applicable' if labels!=3 else 'not_collected')))
    all_convoys=list(rows(directory/'convoy-survival.csv'))
    worst=max(all_convoys,key=lambda r:n(r,'escort_hunger_loss')+n(r,'reserve_hunger_loss'),default=None)
    exports['convoy-hunger-comparison'].append(dict(tag,dispatched=meals['dispatched'],
        outstanding=meals['unresolved'],safe_ended=meals['safe_ended'],escort_hunger=totals['escort_hunger_loss'],
        reserve_hunger=totals['reserve_hunger_loss'],max_stalled_days=meals['max_effective_stall'],
        worst_convoy=worst['convoy_id'] if worst else None,
        worst_hunger=n(worst,'escort_hunger_loss')+n(worst,'reserve_hunger_loss') if worst else 0,
        route_loss=n(final,'convoy_route_grain_loss'),weather_loss=n(final,'convoy_weather_grain_loss')))
    exports['winter-army-supply-comparison'].append({**tag,**selected(values,'winter_required','winter_timely',
        'winter_timely_percent','annual_required','annual_timely','annual_timely_percent')})
    exports['performance-comparison'].append(dict(tag,cpu_mean=values['mean_turn_cpu_seconds'],
        cpu_p95=performance['percentiles']['cpu']['95'],cpu_max=performance['max_turn_cpu_seconds'],
        wall_p95=values['p95_turn_wall_seconds'],wall_max=performance['max_turn_seconds'],
        peak_rss_bytes=performance['worker_peak_rss_bytes'],route_queries=performance['route_queries'],
        regional_evaluations=applicable(planning['evaluations'],2),
        regional_route_searches=applicable(planning['route_searches'],2),
        candidate_sources=applicable(planning['candidate_sources'],2),
        regional_route_batch_cache_hit_percent=pct(planning['cache_hits'],planning['cache_hits']+planning['route_searches']),
        browser_turn_wait_ms='not_collected_in_headless_matrix'))
    exports['warehouse-resource-account'].append(dict(tag,account=(
        'actual_posting_receipts' if actual_scope else 'warehouse_credits_not_recorded_for_this_run'),
        ordinary_warehouse_grain=postings['regular']['grain'] if actual_scope else 'not_collected',
        ordinary_warehouse_gold=gold_posted,extra_civil_grain=postings['civil_bonus']['grain'] if actual_scope else 'not_collected',
        extra_harvest_grain=postings['harvest_bonus']['grain'] if actual_scope else 'not_collected',
        market_grain_issued=values['total_market_issued'],
        market_grain_bought=sum(v['buy_grain'] for v in flow.values()),
        market_grain_sold=sum(v['sell_grain'] for v in flow.values()),
        battle_market_grain=sum(v['buy_grain'] for (_,channel),v in flow.items() if channel=='battle'),
        all_convoy_grain_sent=n(final,'convoy_grain_sent'),all_convoy_grain_delivered=values['convoy_grain_arrived'],
        in_transit_grain=sum(c['cargo_grain'] for c in run['terminal']['convoy_loads']),
        **{key:applicable(paid[key],2) for key in ('cargo_returned','cargo_rations','cargo_route_loss','cargo_weather_loss',
            'escort_base_grain','escort_extra_grain','extra_rations','cargo_abandoned','cargo_remaining')},
        overflow=values['market_capacity_loss']))
    return values


def commercial_acceptance(evidence):
    result=[]
    for label, fixture in evidence.items():
        item=fixture['order']
        purchase=next(event['record'] for event in fixture['events'] if event['kind']=='regional_purchase')
        cash=item['sale_gold']-item['purchase_gold']
        result.append(dict(wave='controlled',scenario='controlled-real-node-rescue',seed=2026,strategy=211,
            weather=0,group='R3',months=0,full_months=0,outcome=item['status'],order=item['id'],
            purpose='trade',automatic=True,source=item['source'],target=item['target'],
            source_region=economic_regions.region(item['source']),target_region=economic_regions.region(item['target']),
            buy_turn=item['created'],dispatch_turn=item['created'],arrival_turn=item['delivered_turn'],
            actual_receiving_city=item['destination'],grain_purchased=item['purchased'],grain_sent=item['purchased'],
            grain_delivered=item['delivered'],grain_sold=item['sold'],source_stock_trade_gold=item['purchase_gold'],
            destination_stock_trade_gold=item['sale_gold'],route=purchase['route'],modes=purchase['route_types'],
            receipt_scope='controlled_'+label,net_cash=cash,unsold_receipt_grain=item['delivered']-item['sold'],
            economic_milli=cash*1000-item['actual_extra_rations']*item['reference_price']
            if item['status']=='sold' else None))
    return result


def comparisons(scores):
    cases=defaultdict(dict)
    for score in scores:
        key=tuple(score[field] for field in ('wave','scenario','seed','strategy','weather','months'))
        cases[key][score['group']]=score
    result=[]
    for groups in cases.values():
        for left,right in (('R0','R1'),('R1','R2'),('R0','R2'),('R2','R3')):
            if left not in groups or right not in groups:
                continue
            a,b=groups[left],groups[right]
            shared=min(a['full_months'],b['full_months'])
            row=dict(selected(b,'wave','scenario','seed','strategy','weather','months'),
                     base_group=left,candidate_group=right,common_months=shared,
                     same_cutoff=a['full_months']==b['full_months'])
            row.update({key:round(b[key]-a[key],6) if row['same_cutoff']
                        and a[key] is not None and b[key] is not None else None for key in PAIR_METRICS})
            for key in ('unpaid_city_turns','rations_missing','convoy_hunger_losses'):
                row[key+'_relative_pct']=pct(row[key],a[key]) if row[key] is not None else None
            row.update(shortage_turn_alert=(row['unpaid_city_turns_relative_pct']>20
                       if row['unpaid_city_turns_relative_pct'] is not None else None),
                shortage_grain_alert=(row['rations_missing_relative_pct']>20
                       if row['rations_missing_relative_pct'] is not None else None),
                winter_timeliness_alert=(row['winter_timely_percent'] < -5
                       if row['winter_timely_percent'] is not None else None))
            result.append(row)
    return result


def long_windows(case,run,directory):
    tag=identity(case,run)
    end=run['full_months']
    for row in rows(directory/'monthly.csv'):
        at=n(row,'elapsed_months')
        if at%60==0 or at==end:
            yield dict(tag,checkpoint_month=at,year=n(row,'year'),month=n(row,'month'),
                **{k:n(row,k) for k in ('gold_stock','grain_stock','market_stock','active_troops',
                    'reserves','population','unpaid_city_turns','rations_missing','convoy_grain_arrived',
                    'convoy_hunger_losses','ai_sorties','battles')})


def archive_crosscheck(prior,results):
    evidence=[]
    with ZipFile(prior['path']) as linked:
        members=set(linked.namelist())
        for case,run,directory in results:
            seed,scene,strategy,group,months,weather=case
            if group!='R0' or not weather:
                continue
            prefix=f'observed/J3-{strategy}/{seed}/{months}/{scene}/'
            if prefix+'run.json' not in members:
                continue
            archived=json.loads(linked.read(prefix+'run.json'))
            if any(run[key]!=archived[key] for key in ('catalog_sha256','weather_seed','completed_turns')):
                raise ValueError((prefix,'historic identity differs'))
            checks=[]
            for name in AUDITED_BASELINE:
                with linked.open(prefix+name) as original:
                    expected=file_digest(original,'sha256').hexdigest()
                actual=digest(directory/name)
                checks.append(dict(file=name,actual=actual,reference=expected,equal=actual==expected))
            evidence.append(dict(group=group,seed=seed,scenario=scene,strategy=strategy,months=months,member=prefix,
                                 checks=checks))
    return evidence


def historical_cases(weather_v221,weather_v222):
    records=[]
    for archive, fixtures in (
        (weather_v221,{126:'reproduction/convoy-126/diagnostic.jsonl',
                       1685:'reproduction/convoy-1685/diagnostic.jsonl'}),
        (weather_v222,{77:'reproduction/baseline/convoy-77/node-decisions.json',
                      2:'reproduction/baseline/convoy-2/node-decisions.json',
                      45:'reproduction/baseline/convoy-45/node-decisions.json',
                      1706:'observed/J3-212/2026/240/208-10/convoy-survival.csv'})):
        with ZipFile(archive['path']) as file:
            for convoy,member in fixtures.items():
                with file.open(member) as stream:
                    member_sha=file_digest(stream,'sha256').hexdigest()
                records.append(dict(convoy=convoy,archive=archive['path'],archive_sha256=archive['sha256'],
                    member=member,member_sha256=member_sha,scope='verified_prior_receipt'))
    return records


def discover(root):
    for case,wave in sorted(EXPECTED.items(),key=lambda item:(WAVES.index(item[1]),item[0])):
        seed,scenario,strategy,group,months,weather=case
        locations=[root]
        if group in ('R2','R3'):
            locations=[root/'final-candidates']
        if wave=='initial' and scenario=='208-10' and group in ('R0','R2'):
            locations.insert(0,root/'warehouse-account')
        directory=next((p for source in locations if (p:=run_directory(source,case)).joinpath('run.json').is_file()),None)
        if directory is None:
            continue
        run=read_json(directory/'run.json')
        key=(run['seed'],run['scenario'],run['strategy'],run['group'],run['requested_months'],run['weather'])
        if key!=case or run['outcome'] not in ('complete','natural_end'):
            raise ValueError((directory,'experiment failed or identity mismatch',key,run['failure']))
        yield case,run,directory


def compare_climate(results):
    matched=defaultdict(dict)
    for case,run,directory in results:
        seed,scene,strategy,group,months,weather=case
        if weather==221 and group in ('R0','R2'):
            matched[seed,scene,strategy,months][group]=(run,directory)
    output=[]
    for (seed,scene,strategy,months),arms in matched.items():
        if len(arms)!=2:
            continue
        a,first=arms['R0']
        b,second=arms['R2']
        adjacent=(a['weather_seed'],a['catalog_sha256'],a['emergency'])==(b['weather_seed'],b['catalog_sha256'],b['emergency'])
        if not adjacent:
            raise ValueError((seed,scene,strategy,months,'paired weather input differs'))
        checks=[match_digest(second/name,first/name) for name in ('regional-weather-daily.csv','river-ice-daily.csv')] \
            if a['completed_turns']==b['completed_turns'] else []
        output.append(dict(seed=seed,scenario=scene,strategy=strategy,months=months,
            weather_seed=a['weather_seed'],input_match=adjacent,days_identical=all(x['equal'] for x in checks) if checks else None,
            status='matched_cutoff' if checks else 'different_cutoff',files=checks))
    return output


def add_file(bundle,path,member,manifest):
    sha=digest(path)
    bundle.write(path,member,compress_type=ZIP_STORED if path.suffix in ('.gz','.png') else ZIP_DEFLATED)
    manifest.append(f'{sha}  {member}')


def deliver(root,results,report):
    paths=[]
    out=root/'exports'
    paths.extend((path,'data/'+path.name) for path in sorted(out.iterdir()) if path.is_file())
    paths.extend((path,'docs/'+path.name) for path in sorted((ROOT/'docs/regional-economy-v301').glob('*.md')))
    tool=ROOT/'tools/economy-balance'
    paths.extend((tool/name,'scripts/'+name) for name in SCRIPTS+('observer-config.json',))
    paths.extend((path,'sources/'+path.name) for folder in (root,root/'final-candidates',root/'warehouse-account')
                 for path in sorted((folder/'sources').glob('*.json')))
    evidence_names=set('baseline-matrix.log final-candidate-matrix.log baseline-confirmation.log warehouse-account.log '
        'convoy-1706-replay.log regional-market-tests.log node-tests.log rust-tests.log wasm-vectors.log '
        'browser-engine-smoke.log browser-ui.log regional-market-zh.png regional-market-ja-mobile.png '
        'web-build.log march-build.log full-suite.log prior-archives.json commercial-fixture.json '
        'regional-runtime-tests.log commercial-fixture.log locales-final.log python-shard-2-rerun.log '
        'browser-ui-local-market.log city-market-stock-zh.png gates-final.json regional-python-final.log'.split())
    evidence_names.update(f'{backend}-shard-{part}.log' for backend in ('python','rust') for part in range(1,7))
    paths.extend((path,'checks/'+path.name) for path in sorted((root/'checks').iterdir()) if path.name in evidence_names)
    replay=root/'replay-1706'
    for name in ('node-decisions.json','convoy-1706.json','regression-check.json'):
        if (replay/name).is_file():
            paths.append((replay/name,'historical/convoy-1706/'+name))
    for case, _, directory in results:
        prefix=run_directory(Path(),case).as_posix()
        paths.extend((path,prefix+'/'+path.name) for path in sorted(directory.iterdir())
                     if path.is_file() and path.name in OBSERVED_FILES)
    temporary=root/(ARCHIVE+'.writing')
    unique={}
    for path,member in paths:
        if member in unique and digest(unique[member])!=digest(path):
            raise ValueError(f'Duplicate package member with different content: {member}')
        unique[member]=path
    manifest=[]
    with ZipFile(temporary,'w',compression=ZIP_DEFLATED,compresslevel=6) as bundle:
        bundle.writestr('README.txt','三國大陸戰役 V3.0.1 · 開啟 docs/README.md 與 data/validation-manifest.json。\n')
        manifest.append(f'{sha256(bundle.read("README.txt")).hexdigest()}  README.txt')
        for member,path in sorted(unique.items()):
            add_file(bundle,path,member,manifest)
        bundle.writestr('SHA256SUMS.txt','\n'.join(manifest)+'\n')
    with ZipFile(temporary) as archive:
        for line in archive.read('SHA256SUMS.txt').decode().splitlines():
            expected,name=line.split('  ',1)
            with archive.open(name) as stream:
                if file_digest(stream,'sha256').hexdigest()!=expected:
                    raise ValueError(f'Invalid generated package member {name}')
    final=root/ARCHIVE
    temporary.replace(final)
    final.with_suffix('.zip.sha256').write_text(f'{digest(final)}  {final.name}\n',encoding='utf-8')
    return final,len(manifest)


def main():
    cli=ArgumentParser(description=__doc__)
    cli.add_argument('--root',type=Path,default=OUTPUT)
    cli.add_argument('--partial',action='store_true')
    cli.add_argument('--package',action='store_true')
    args=cli.parse_args()
    if args.partial and args.package:
        cli.error('A partial experiment cannot be published as a complete validation package.')
    root=args.root
    exports_dir=root/('draft-exports' if args.partial else 'exports')
    exports_dir.mkdir(parents=True,exist_ok=True)
    checks=root/'checks'
    archives=read_json(checks/'prior-archives.json')
    results=list(discover(root))
    if len(results)!=len(EXPECTED) and not args.partial:
        missing=set(EXPECTED)-{key for key,_,_ in results}
        raise ValueError(f'Missing required observations: {sorted(missing)}')
    cities,links=metadata(exports_dir)
    tables=defaultdict(list)
    scores=[]
    simulations=[]
    for case,run,directory in results:
        score=analyze(case,run,directory,tables)
        scores.append(score)
        simulations.append(dict(identity(case,run),path=run_directory(Path(),case).as_posix(),head=run['head'],
            catalog_sha256=run['catalog_sha256'],worktree_sha256=run['source_tree_sha256'],
            weather_seed=run['weather_seed'],rule_versions=run['rule_versions'],emergency=run['emergency'],
            market_stage=run['market_stage'],runtime=run['backend']['engine'],parameters=run['parameters']))
    historical=archive_crosscheck(archives[-1],results)
    archived_cases=historical_cases(*archives[-2:])
    audit_names=('monthly.csv','factions.csv','cities.csv','shortages.csv','convoys.csv','market-stock-flow.csv.gz',
                 'city-market-prices.csv.gz','supply-episodes-weather-aware.csv')
    controls=[]
    for group in ('R0','R1'):
        key=(2026,'208-10',211,group,60,0)
        reference=run_directory(root/'baseline-confirmation',key)
        original=run_directory(root,key)
        if reference.joinpath('run.json').is_file():
            for name in audit_names:
                controls.append(dict(group=group,**match_digest(reference/name,original/name)))
    warehouse_checks=[]
    for group,source in (('R0',root),('R2',root/'final-candidates')):
        key=(2026,'208-10',211,group,60,0)
        observed=run_directory(root/'warehouse-account',key)
        original=run_directory(source,key)
        if observed.joinpath('run.json').is_file() and original.joinpath('run.json').is_file():
            warehouse_checks.extend(dict(group=group,**match_digest(observed/name,original/name)) for name in audit_names)
    matrix_cmp=comparisons(scores)
    tables['scenario-scores']=scores
    tables['pairwise']=matrix_cmp
    tables['long-term-economy-comparison']=[sample for case,run,directory in results if EXPECTED[case]=='long'
                                          for sample in long_windows(case,run,directory)]
    if (checks/'commercial-fixture.json').is_file():
        tables['trade-profit-comparison'].extend(commercial_acceptance(read_json(checks/'commercial-fixture.json')))
    tables['baseline-verification']=[dict(kind='historical_weather',group=item['group'],scenario=item['scenario'],
        seed=item['seed'],strategy=item['strategy'],months=item['months'],member=item['member'],**check)
        for item in historical for check in item['checks']]
    tables['historical-convoy-references']=archived_cases
    names=['market-price-distribution','market-stock-flow','regional-supply-demand','regional-procurement-comparison',
           'regional-trade-comparison','landed-cost-comparison','commodity-grain-flow','regional-market-shortages',
           'trade-profit-comparison','gold-inflation-comparison','convoy-hunger-comparison','winter-army-supply-comparison',
           'scenario-scores','pairwise','long-term-economy-comparison','performance-comparison','warehouse-resource-account',
           'baseline-verification','historical-convoy-references']
    for name in names:
        write(exports_dir,name,tables[name],fields=('wave','scenario','seed','strategy','weather','group','months',
               'order','source','target','sale_gold','net_cash','unsold_receipt_grain','economic_milli')
               if name=='trade-profit-comparison' else ('wave','scenario','seed','strategy','weather','group','months'))
    map_paths=('game/config/map-source.json','game/config/route-corridors.json','game/config/route-geometry.json',
               'game/config/route-render-source.json','game/config/campaigns','game/data/campaigns','game/map-source',
               'game/assets/map-campaign.png','game/assets/map-presentation.json','game/assets/map-road-centers.png')
    market_build_files=git('ls-files','-z','--',*map_paths).decode().strip('\0').split('\0')
    hashes={name:digest(ROOT/name) for name in market_build_files if (ROOT/name).is_file()}
    report=dict(schema=SCHEMA,run_count=len(results),expected=len(EXPECTED),cities=cities,directed_connections=links,
        source=source_identity(),map_and_campaign_inputs=hashes,historical_archives=archives,
        historical_baseline_files=sum(len(entry['checks']) for entry in historical),
        historical_baseline_equal=sum(check['equal'] for entry in historical for check in entry['checks']),
        historical_baseline=historical,archived_convoys=archived_cases,final_control_checks=controls,
        paired_weather=compare_climate(results),warehouse_observer_readonly_checks=warehouse_checks,warehouse_posting_replays=[
            identity(case,run) for case,run,_ in results if run.get('warehouse_postings')],
        tags={'0':'observed zero','not_collected':'not recorded by that observer','not_applicable':'mechanism unavailable',
              'null':'undefined denominator, censored receipt or missing reference','partial':'expected required case pending'})
    to_json(exports_dir/'simulation-manifest.json',dict(schema=SCHEMA,simulations=simulations))
    to_json(exports_dir/'validation-manifest.json',report)
    print(json.dumps(dict(observed=len(results),expected=len(EXPECTED),cities=cities,routes=links,
        baseline_equal=report['historical_baseline_equal'],baseline_count=report['historical_baseline_files']),ensure_ascii=False))
    if args.package:
        path,count=deliver(root,results,report)
        print(json.dumps(dict(package=str(path),count=count,bytes=path.stat().st_size,sha256=digest(path))))


if __name__=='__main__':
    main()
