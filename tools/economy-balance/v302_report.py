"""Build V3.0.2 comparisons from completed real runs and validated receipts."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
from hashlib import file_digest, sha256
from io import TextIOWrapper
from pathlib import Path
import gzip
import json
import zipfile

from common import to_csv, to_json
from remake import climate_regions, logistics, strategic_granary
from remake.regional_procurement import landed_cents
from v301_report import faction_survival, market_flows, order_flows, pct, quoted_market, supply
from v302_experiments import PRIOR, case_dir

KEYS = ('wave','scenario','seed','strategy','weather','requested_months')
FROZEN = ('monthly.csv','cities.csv','factions.csv','shortages.csv','convoys.csv','battles.csv',
          'supply-requests.csv','troop-flows.csv')
MACRO = ('unpaid_city_turns','rations_missing','gold_stock','grain_stock','market_stock','population',
         'active_troops','reserves','ai_sorties','battles','convoy_hunger_losses','convoy_arrived','convoy_grain_arrived',
         'convoy_route_grain_loss','convoy_weather_grain_loss','monthly_regular_grain','monthly_gold','monthly_fixed_grain')
BRIDGE = ('proactive_requested','proactive_dispatched','winter_dispatched','strategic_load','grain_committed',
          'strategic_delivered','timely_grain','late_grain','cancelled','failed','repeated_target_blocked',
          'source_safety_rejections','source_shortage_later','relay_planned','relay_second_leg','relay_net_delivered',
          'relay_hub_grain','leg_delivery_grain')


@contextmanager
def csv_file(p):
    read = gzip.open if p.suffix=='.gz' else open
    with read(p,'rt',encoding='utf-8',newline='') as stream:
        yield csv.DictReader(stream)


def value(row,key):
    cell = row.get(key,'')
    return int(cell) if cell else 0


def name(run):
    return {key:run[key] for key in (*KEYS,'group')}


def jsonl(file):
    with gzip.open(file,'rt',encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def needed_history(directory, run, totals):
    monthly = list(csv_file_rows(directory/'monthly.csv'))
    checkpoints = [row for row in monthly if value(row,'elapsed_months') in (0,60,120,180,240)]
    totals['milestones'].extend(dict(name(run), elapsed_months=value(r,'elapsed_months'),
        year=value(r,'year'), month=value(r,'month'), **{key:value(r,key) for key in MACRO}) for r in checkpoints)
    return monthly[0], monthly[-1]


def csv_file_rows(path):
    with csv_file(path) as rows:
        yield from rows


def stock_observations(run,directory,shortages,exports):
    active = run['reserve_options'] is not None
    last_city, regions, released, used_sources = {}, Counter(), Counter(), defaultdict(list)
    rejection, measures, perf, orders, receipts, relays = Counter(),Counter(),Counter(),{},set(),{}
    reserve_issues = 0
    idle_since, uses = {}, Counter()
    for row in jsonl(directory/'strategic-granary-events.jsonl.gz'):
        event = row['event']
        if event == 'city_forecast':
            key = row['city']
            last_city[key] = row
            if not row['reserve'] or uses[key]:
                idle_since[key] = row['turn']
                uses[key] = 0
            idle_since.setdefault(key,row['turn'])
            if row['reserve'] < 0 or row['reserve'] > row['total']:
                reserve_issues += 1
            measures['reserve_sample_grain'] += row['reserve']
            measures['reserve_samples'] += 1
            measures['sample_front_available'] += max(0,row['total']-row['reserve']) if row['roles']['frontline'] else 0
            measures['sample_front_count'] += bool(row['roles']['frontline'])
            if row['winter'] and row['region']:
                months, chance, cold, _ = climate_regions.REGIONS[row['region']]
                typical = {month for month,level in zip(climate_regions.WINTER_MONTHS,cold) if level>=2}
                typical |= set(months) if chance>=strategic_granary.RULES['cold_reserve_min_chance'] else set()
                if row['month'] not in typical:
                    measures['prewinter_funded'] += min(row['winter'],row['reserve'])
                    measures['prewinter_target'] += row['winter']
        elif event in ('reserve_released','reserve_added'):
            measures[event] += 1
            if event == 'reserve_released':
                released[row['reason']] -= row['delta']
                uses[row['city']] += 1
        elif event in ('dispatch_requested','dispatch_blocked'):
            if event=='dispatch_requested':
                measures.update(proactive_requested=1,requested_grain=row['grain'],
                    timely_route_coverage=bool(row['timely_net']),legal_capacity=bool(row['legal']))
                rejection.update(row['rejections'])
            else:
                rejection[row['reason']] += 1
        elif event.startswith('order_'):
            order = orders.setdefault(row['id'],{})
            if event in order and event in ('order_dispatched','order_delivered','order_reserved'):
                reserve_issues += 1
            order[event] = row
        elif event == 'escort_receipt':
            if row['order_id'] in receipts or not logistics.valid_grain_receipt(
                    {key:row[key] for key in logistics.RECEIPT_FIELDS}):
                reserve_issues += 1
            receipts.add(row['order_id'])
            measures.update(escort_receipt=1,hunger_losses=row['hunger_losses'],escort_food=row['escort_food'])
        elif event == 'dispatch_work':
            perf.update({key:value for key,value in row.items() if key in
                {'route_pairs','route_batches','candidate_pairs','route_cache_hits','risk_cache_hits'}})
        elif event.startswith('relay_'):
            measures[event] += 1
            if event=='relay_hub_receipt' and not row['received']:
                measures['empty_relay_receipts'] += 1
            relays.setdefault(row['id'],{})[event] = row
        elif event == 'emergency_refill':
            measures.update(emergency_refills=1,emergency_refill_grain=row['grain'])
        elif event == 'return_shelter':
            measures['return_shelters'] += 1
    seen_convoys = set()
    for ident,line in orders.items():
        held, dispatched, received, ended = (line.get('order_'+event) for event in
                                             ('reserved','dispatched','delivered','closed'))
        if held:
            measures['grain_committed'] += held['load']+held['rations']
        if dispatched:
            convoy = dispatched['convoy_id']
            if convoy in seen_convoys or not held:
                reserve_issues += 1
            seen_convoys.add(convoy)
            measures['strategic_load'] += dispatched['load']
            measures[dispatched['priority']+'_dispatched'] += 1
            used_sources[dispatched['source']].append((dispatched['dispatch_turn'],dispatched['owner']))
        if received:
            if not dispatched:
                reserve_issues += 1
            grain = received['delivered_grain']
            measures['leg_delivery_grain'] += grain
            if ident in relays:
                measures['relay_hub_grain'] += grain
            else:
                measures['strategic_delivered'] += grain
                measures['timely_grain' if received['delivered_turn']<received['deadline'] else 'late_grain'] += grain
        if ended and ended['status'] in ('failed','cancelled'):
            measures[ended['status']] += 1
        exports['grain-commitment-account'].append(dict(name(run),order=ident,
            source=(held or dispatched)['source'],target=(held or dispatched)['target'],
            intermediate_relay_leg=ident in relays,
            grain_committed=held['load']+held['rations'] if held else 0,
            load=dispatched['load'] if dispatched else 0,
            convoy=dispatched['convoy_id'] if dispatched else None,
            dispatched_turn=dispatched['dispatch_turn'] if dispatched else None,
            deadlines=(held or dispatched)['deadline'], delivered=received['delivered_grain'] if received else None,
            delivery_turn=received['delivered_turn'] if received else None,
            status=ended['status'] if ended else 'active', reason=ended['reason'] if ended else None,
            reference_price=(held or dispatched)['reference_price'],
            actual_cost_cents=ended['actual_cost'] if ended else None))
    for ident,line in relays.items():
        second = line.get('relay_second_leg')
        actual = orders.get(second['second_order'],{}).get('order_delivered') if second else None
        if actual:
            measures['relay_net_delivered'] += actual['delivered_grain']
        order = line.get('relay_planned') or next(iter(line.values()))
        exports['regional-transit-comparison'].append(dict(name(run),first=ident,source=order['source'],
            hub=order['hub'],target=order['target'],first_received=line.get('relay_hub_receipt',{}).get('received'),
            second=second['second_order'] if second else None, second_delivered=actual['delivered_grain'] if actual else None,
            outcome='forwarded' if second else 'cancelled' if 'relay_cancelled' in line else 'active'))
    for row in shortages:
        key,turn,owner = row['city'],value(row,'turn'),row['owner']
        measures['source_shortage_later'] += any(source_owner==owner and 0<=turn-issued<=9
                                                 for issued,source_owner in used_sources[key])
    for row in last_city.values():
        if row['region']:
            regions[row['region']] += row['total']
    stock, goal = sum(r['reserve'] for r in last_city.values()),sum(r['target'] for r in last_city.values())
    summary = dict(strategic_stock=stock,strategic_target=goal,
        target_fulfilment_pct=pct(sum(min(r['reserve'],r['target']) for r in last_city.values()),goal),
        reserve_releases=measures['reserve_released'], reserve_added=measures['reserve_added'],
        reserve_grain_released=sum(released.values()),
        reserve_turnover_pct=pct(sum(released.values()),measures['reserve_sample_grain']/measures['reserve_samples'])
            if measures['reserve_samples'] else None,
        estimated_unused_end_grain=sum(r['reserve'] for r in last_city.values()
                                       if not r['roles']['frontline'] and r['gap']==0),
        long_idle_reserve_pct=pct(sum(r['reserve'] for city,r in last_city.items()
            if r['turn']-idle_since[city]>=9 and not uses[city]),stock),
        below_target=sum(r['reserve']<r['target'] for r in last_city.values()),
        above_target=sum(r['reserve']>r['target'] for r in last_city.values()),
        prewinter_target=measures['prewinter_target'],prewinter_funded=measures['prewinter_funded'],
        prewinter_fulfilment_pct=pct(measures['prewinter_funded'],measures['prewinter_target']),
        reserve_audit_errors=reserve_issues, emergency_refills=measures['emergency_refills'],
        emergency_refill_grain=measures['emergency_refill_grain'], legal_shelters=measures['return_shelters'],
        empty_relay_receipts=measures['empty_relay_receipts'] if run['reserve_options'] and
                             run['reserve_options']['relay'] else 'not_applicable')
    shipping = {key:measures[key] for key in BRIDGE}
    shipping.update(repeated_target_blocked=rejection['already_committed'],
                    source_safety_rejections=rejection['source_safety'], timely_route_coverage=measures['timely_route_coverage'],
                    requested_grain=measures['requested_grain'],legal_capacity=measures['legal_capacity'],
                    candidate_forecast_frontline_grain=round(measures['sample_front_available']/measures['sample_front_count'],3)
                         if measures['sample_front_count'] else None)
    fields = dict(posted_reserve_fields=active,**{key:value if active else 'not_applicable' for key,value in summary.items()})
    dispatch = run['reserve_options'] and run['reserve_options']['proactive']
    ship_fields = {key:value if dispatch else 'not_applicable' for key,value in shipping.items()}
    exports['strategic-granary-comparison'].append(dict(name(run),**fields))
    exports['proactive-dispatch-comparison'].append(dict(name(run),**ship_fields))
    exports['winter-reserve-comparison'].append(dict(name(run),**{key:fields[key] for key in
        ('prewinter_target','prewinter_funded','prewinter_fulfilment_pct')},
        dispatched=ship_fields['winter_dispatched']))
    exports['reserve-release-comparison'].extend(dict(name(run),reason=reason,grain=grain) for reason,grain in sorted(released.items()))
    exports['shortage-reason-comparison'].extend(dict(name(run),reason=reason,count=count) for reason,count in sorted(rejection.items()))
    return fields,ship_fields,perf,regions


def convoy_hunger(run,directory,terminal,exports):
    losses=defaultdict(Counter)
    delivered={row['convoy_id']:int(row['delivered_tick']) for row in terminal
               if row['delivered_tick'] not in ('','null')}
    for row in csv_file_rows(directory/'convoy-resolution-daily.csv.gz'):
        ident=row['convoy_id']
        escort,reserve=(value(row,field) for field in ('escort_hunger_loss','reserve_hunger_loss'))
        if escort or reserve:
            returning=ident in delivered and value(row,'tick')>delivered[ident]
            side='after_delivery' if returning else 'before_or_without_delivery'
            losses[ident].update({side+'_escort':escort,side+'_reserve':reserve})
    totals=Counter()
    departures={}
    if losses:
        departures={row['convoy_id']:row for row in csv_file_rows(directory/'convoys.csv')
                    if row['stage']=='departed' and row['convoy_id'] in losses}
    for row in terminal:
        ident=row['convoy_id']
        actual=losses.pop(ident, {})
        if sum(actual.values())!=value(row,'escort_hunger_loss')+value(row,'reserve_hunger_loss'):
            raise ValueError(f'Convoy {ident} daily losses differ from the terminal escort record')
        if actual:
            totals.update(actual)
            departure=departures[ident]
            exports['convoy-hunger-comparison'].append(dict(name(run),convoy_id=ident,
                owner=row['owner'],source=departure['source'],target=departure['target'],
                delivered_tick=delivered.get(ident),terminal_status=row['terminal_status'],
                initial_escort=row['initial_escort'],remaining_escort=row['current_escort'],
                **{key:actual.get(key,0) for key in ('before_or_without_delivery_escort',
                    'before_or_without_delivery_reserve','after_delivery_escort','after_delivery_reserve')}))
    if losses:
        raise ValueError('Unmatched daily convoy hunger records')
    return len(delivered),totals


def describe(run,directory,exports):
    tag = name(run)
    initial, final = needed_history(directory,run,exports)
    shortages = list(csv_file_rows(directory/'shortages.csv'))
    fields,shipping,work,regions = stock_observations(run,directory,shortages,exports)
    ending, flow, _ = market_flows(directory)
    balances = Counter()
    for row in flow.values():
        balances.update(row)
    if sum(ending.values())!=value(final,'market_stock'):
        raise ValueError('Published market stock does not match final transaction receipts')
    for side,grain,gold in (('buy','grain_bought','purchase_gold'),('sell','grain_sold','sale_gold')):
        if (balances[side+'_grain'],balances[side+'_gold'])!=(value(final,grain),value(final,gold)):
            raise ValueError('Market grain or gold receipts differ from the official game totals')
    _,price_bands=quoted_market(directory,ending)
    exports['market-price-bands'].extend(dict(tag,region=region,buy=buy,sell=sell,stock_band=band,samples=count)
            for (region,buy,sell,band),count in sorted(price_bands.items()))
    orders,_,_=order_flows(directory)
    purchased=Counter()
    regional_delivery=0
    for ident, events in orders.items():
        buy=events['regional_purchase']
        dispatch=events.get('regional_dispatch',{})
        arrival=events.get('regional_delivery',{})
        close=events.get('regional_transport_closed',{})
        sold=events.get('regional_sale',{})
        volume=arrival.get('grain',0)
        regional_delivery+=volume
        purchased.update({(buy['purpose'],'grain'):buy['grain'],(buy['purpose'],'gold'):buy['gold']})
        ref=buy.get('reference_price')
        cost=(landed_cents(buy['gold'],close['extra_rations'],ref,volume) if ref is not None
              else 'not_collected') if close and volume else None
        exports['landed-cost-comparison'].append(dict(tag,order=ident,source=buy['source'],
            target=buy['target'],purpose=buy['purpose'],purchased=buy['grain'],gold=buy['gold'],
            sent=dispatch.get('grain'),delivered=arrival.get('grain'),estimate_cents_per_thousand=buy['landed_cents'],
            estimate_net_grain=buy['estimated_net'], reference_price=ref,actual_cents_per_thousand=cost,
            actual_extra_rations=close.get('extra_rations'), actual_rations=close.get('rations_used'),
            route_loss=close.get('cargo_route_loss'),weather_loss=close.get('cargo_weather_loss'),
            cash_result=(sold['gold']-buy['gold']) if sold else None, close_reason=close.get('close_reason')))
    for purpose in ('procurement','trade'):
        for resource in ('grain','gold'):
            debited=sum(v['buy_'+resource] for (_,channel),v in flow.items() if channel=='regional_'+purpose)
            if debited!=purchased[purpose,resource]:
                raise ValueError('Regional purchase differs from physical market receipts')
    score = {key:value(final,key) for key in MACRO}
    mean = run['performance']['mean_turn_cpu_seconds']
    overall,winter=supply(run,directory,'supply-episodes-weather-aware.csv')
    convoy=run['transport_survival']
    grounds = Counter()
    for row in shortages:
        missing=value(row,'missing')
        grounds['measured'] += 1
        grounds['local'] += value(row,'other_stock')>=missing
        for key,metric in (('reserve_surplus','surplus_covered'),('legal_route_surplus','legal_surplus_covered')):
            evidence = row.get(key)
            if evidence not in (None,'','null','not_collected','not_applicable'):
                grounds[metric+'_sampled'] += 1
                grounds[metric] += json.loads(evidence)['3']>=missing
        timely=row.get('timely_new_shipment') or ''
        if timely not in ('','null','not_collected','not_applicable'):
            grounds['observer_timely_shipment_rows'] += 1
            grounds['timely_legal_coverage'] += int(timely)>=missing
    spatial = dict(grounds, faction_gap=grounds['measured']-grounds['local'],
        local=grounds['local'], legal_coverage_pct=pct(grounds['legal_surplus_covered'],grounds['legal_surplus_covered_sampled']),
        regional_stock_hhi=round(sum((v/sum(regions.values()))**2 for v in regions.values()),7) if sum(regions.values()) else None)
    winter_shortages=[row for row in shortages if value(row,'month') in climate_regions.WINTER_MONTHS]
    weather_metrics = dict(winter_requested=winter.get('required',0) if run['weather'] else 'not_applicable',
        winter_delivered_timely=winter.get('timely',0) if run['weather'] else 'not_applicable',
        winter_timely_percent=pct(winter.get('timely',0),winter.get('required',0)) if run['weather'] else None,
        winter_shortage_city_turns=len(winter_shortages) if run['weather'] else 'not_applicable',
        winter_shortage_grain=sum(value(row,'missing') for row in winter_shortages) if run['weather'] else 'not_applicable',
        annual_requested=overall.get('required',0),annual_delivered_timely=overall.get('timely',0))
    exports['winter-army-supply-comparison'].append(dict(tag,**weather_metrics))
    exports['spatial-grain-imbalance'].append(dict(tag,**spatial))
    performance=dict(cpu=run['performance']['total_turn_cpu_seconds'],wall=run['seconds'],mean_cpu=mean,
        cpu_p50=run['performance']['percentiles']['cpu']['50'],cpu_p95=run['performance']['percentiles']['cpu']['95'],
        wall_p50=run['performance']['percentiles']['wall']['50'],wall_p95=run['performance']['percentiles']['wall']['95'],
        worker_rss=run['performance']['worker_peak_rss_bytes'],route_queries=run['performance'].get('route_queries','not_collected'),
        granary_route_pairs=work['route_pairs'],granary_route_batches=work['route_batches'],
        granary_candidate_pairs=work['candidate_pairs'],granary_route_cache_hit_pct=pct(work['route_cache_hits'],
            work['route_cache_hits']+work['route_pairs']),granary_risk_cache_hits=work['risk_cache_hits'])
    exports['performance-comparison'].append(dict(tag,**performance))
    flows = run['audit']['categories']
    for item in flows:
        exports['warehouse-resource-account'].append(dict(tag,**item))
        if item['resource']=='gold':
            exports['fiscal-resource-account'].append(dict(tag,**item))
    safe = dict(transport_departed=convoy['dispatched'],safely_resolved=convoy['safe_ended'],
        terminated=convoy['ended'],unresolved=convoy['unresolved'],hunger=convoy['totals']['escort_hunger_loss'],
        reserve_hunger=convoy['totals']['reserve_hunger_loss'],max_blocked_days=convoy['max_effective_stall'],
        live_personnel_received=convoy['safe_personnel'],lost_all_escorts=convoy['all_escorts_lost'],
        outcome_counts=convoy['states'])
    dated = list(csv_file_rows(directory/'convoy-survival.csv'))
    docked=[r for r in dated if r['terminal_status'] in ('returned_home','received_elsewhere')]
    delivered, losses=convoy_hunger(run,directory,dated,exports)
    safe.update(real_docked=len(docked),cargo_delivered=delivered,
        after_delivery_escort_hunger=losses['after_delivery_escort'],
        after_delivery_reserve_hunger=losses['after_delivery_reserve'],
        initial_escort=convoy['totals']['initial_escort'],
        live_escort_received=sum(value(r,'current_escort') for r in docked))
    safe['escort_hunger_survival_pct']=pct(safe['initial_escort']-safe['hunger'],safe['initial_escort'])
    safe['escort_reception_pct']=pct(safe['live_escort_received'],safe['initial_escort'])
    safe['no_receiving_node'] = sum(r['terminal_status']=='no_friendly_city' for r in dated)
    safe['docked_after_all_escort_hunger'] = sum(
        value(r,'initial_escort')>0 and value(r,'escort_hunger_loss')>=value(r,'initial_escort')
        and r['terminal_status'] in ('returned_home','received_elsewhere') for r in dated)
    exports['convoy-return-safety'].append(dict(tag,**safe))
    score.update(completed_turns=run['completed_turns'],initial_grain=value(initial,'grain_stock'),initial_gold=value(initial,'gold_stock'),
        shortage_rate_pct=pct(score['unpaid_city_turns'],value(final,'owned_city_turns')),
        grain_per_thousand_population=pct(score['grain_stock']*10,score['population']),
        gold_per_thousand_population=pct(score['gold_stock']*10,score['population']),
        grain_per_thousand_active=pct(score['grain_stock']*10,score['active_troops']),
        city_resource_mismatches=run['audit']['city_resource_mismatches'],
        city_postings=run['audit']['city_postings'], market_checks=balances['samples'],
        market_restock=balances['replenished']-balances['overflow'],market_overflow=balances['overflow'],
        market_bought=balances['buy_grain'],market_sold=balances['sell_grain'],
        market_paid=balances['buy_gold'],market_income=balances['sell_gold'],
        regional_orders=len(orders) if run['market_stage'] else 'not_applicable',
        regional_purchased=purchased['procurement','grain'] if run['market_stage'] else 'not_applicable',
        regional_delivered=regional_delivery if run['market_stage'] else 'not_applicable',
        automatic_commercial_orders='not_applicable',
        convoy_safe_pct=pct(safe['safely_resolved'],safe['transport_departed']),
        convoy_delivery_pct=pct(safe['cargo_delivered'],safe['transport_departed']),
        convoy_return_escort_hunger=safe['after_delivery_escort_hunger'],
        escort_hunger_survival_pct=safe['escort_hunger_survival_pct'],
        escort_reception_pct=safe['escort_reception_pct'],
        net_gold=score['gold_stock']-value(initial,'gold_stock'),
        **faction_survival(directory),**weather_metrics,**fields,**shipping,**spatial,
        mean_turn_cpu=mean)
    return dict(tag,**score)


def baseline_checks(archive, run, folder):
    group = {'S0':'R0','S1':'R2'}.get(run['group'])
    if not group:
        return []
    prior = json.loads(archive.read('data/simulation-manifest.json'))['simulations']
    matches = [r for r in prior if r['group']==group and all(r[k]==run[k] for k in ('scenario','seed','strategy','weather'))
               and r['months']>=run['requested_months']]
    if not matches:
        return []
    old = min(matches,key=lambda r:r['months'])
    cutoff = run['requested_months']
    tag = name(run)
    results = []
    for file in FROZEN:
        local_path = folder/file
        reference = old['path']+'/'+file
        if not local_path.is_file():
            continue
        if old['months']==cutoff:
            recorded = archive.read(reference)
            actual = local_path.read_bytes()
            equal = actual==recorded
            before,after = sha256(recorded).hexdigest(),sha256(actual).hexdigest()
            basis='byte_exact'
        elif file in ('monthly.csv','cities.csv','factions.csv'):
            with TextIOWrapper(archive.open(reference),encoding='utf-8',newline='') as stream:
                sample = csv.DictReader(stream)
                old_rows = [row for row in sample if value(row,'elapsed_months')<=cutoff]
            new_rows = list(csv_file_rows(local_path))
            before,after = (sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest() for rows in (old_rows,new_rows))
            equal = old_rows==new_rows
            basis='same_cutoff_rows'
        else:
            continue
        results.append(dict(tag,artifact=file,comparison=basis,archive=reference,
                            archived_sha256=before,actual_sha256=after,equal=equal))
    return results


def percent_delta(after,before):
    return pct(after-before,before)


def paired(rows):
    groups = defaultdict(dict)
    for row in rows:
        groups[tuple(row[k] for k in KEYS)][row['group']]=row
    for values in groups.values():
        for candidate,data in values.items():
            for baseline in ('S0','S1'):
                if candidate==baseline or baseline not in values:
                    continue
                old=values[baseline]
                if data['completed_turns']!=old['completed_turns']:
                    continue
                tag={key:data[key] for key in KEYS}
                checks={}
                for metric in (data.keys() & old.keys()) - set(KEYS):
                    a,b=data[metric],old[metric]
                    if type(a) in (int,float) and type(b) in (int,float):
                        checks[metric]=(a,b,round(a-b,8),percent_delta(a,b))
                for metric,(after,before,delta,percent) in sorted(checks.items()):
                    threshold = None
                    if baseline == 'S1' and candidate not in ('S0','S1'):
                        if metric in ('unpaid_city_turns','rations_missing','mean_turn_cpu'):
                            threshold = (30 if metric == 'mean_turn_cpu' else 20, percent, 'relative_pct')
                        elif metric in ('winter_timely_percent','small_faction_survival_percent'):
                            threshold = (-5 if metric=='winter_timely_percent' else -10,delta,'percentage_points')
                    over = None
                    if threshold:
                        t,m,_=threshold
                        if m is not None:
                            over = m > t if t>0 else m<t
                        elif t>0 and before==0:
                            over = after>0
                    result = dict(tag,group=candidate,baseline=baseline,metric=metric,before=before,
                                  after=after,delta=delta,change_pct=percent,alert=over)
                    yield result


def write_or_empty(path, rows):
    if rows:
        to_csv(path,rows)
    else:
        path.write_text('status\nnot_applicable\n',encoding='utf-8')


def compare_replay_assets(name,before,after):
    paths=(before/name,after/name)
    hashes=[]
    for path in paths:
        reader=gzip.open if path.suffix=='.gz' else open
        with reader(path,'rb') as stream:
            hashes.append(file_digest(stream,'sha256').hexdigest())
    result=dict(frozen=hashes[0],fixed=hashes[1],raw_equal=hashes[0]==hashes[1],mode='exact')
    result['equal']=result['raw_equal']
    if not result['equal'] and name=='warehouse-postings.csv.gz':
        accounts=[]
        for path in paths:
            by_account=defaultdict(list)
            for row in csv_file_rows(path):
                by_account[row['city'],row['resource']].append(row)
            accounts.append(by_account)
        result.update(mode='ordered_postings_per_city_resource',equal=accounts[0]==accounts[1])
    if not result['equal'] and name=='strategic-granary-events.jsonl.gz':
        frozen,fixed=(list(jsonl(path)) for path in paths)
        empty={row['id']:row for row in frozen if row['event']=='relay_hub_receipt' and row['received']==0}
        closed={row['id']:row for row in fixed if row['event']=='relay_cancelled' and row['reason']=='empty_receipt'}
        identity=('turn','year','month','day','owner','source','hub','target','deadline')
        if (empty and empty.keys()==closed.keys() and
                all(old[key]==closed[ident][key] for ident,old in empty.items() for key in identity) and
                not any(row['event']=='relay_hub_receipt' and row['id'] in empty for row in fixed)):
            def unrelated(row):
                return not (row['event'] in ('relay_hub_receipt','relay_cancelled') and row['id'] in empty)
            result.update(mode='documented_zero_receipt_event_transition',transition_orders=sorted(empty),
                          equal=list(filter(unrelated,frozen))==list(filter(unrelated,fixed)))
    return result


def relay_reruns(root, rerun_folder):
    comparisons=[]
    files=(*FROZEN,'convoy-survival.csv','route-changes.csv','convoy-ledger.csv.gz',
           'convoy-resolution-daily.csv.gz','strategic-granary-events.jsonl.gz',
           'warehouse-postings.csv.gz','market-stock-flow.csv.gz')
    planned={tuple(row) for path in rerun_folder.glob('planned-*.json') for row in json.loads(path.read_text())}
    for case in sorted(planned):
        baseline, rerun=(case_dir(folder,case) for folder in (root,rerun_folder))
        records=[folder/'run-v302.json' for folder in (baseline,rerun)]
        if not all(path.is_file() for path in records):
            continue
        before, after=(json.loads(path.read_text()) for path in records)
        assets={name:compare_replay_assets(name,baseline,rerun) for name in files} if (
            before['outcome']==after['outcome']=='complete') else {}
        comparisons.append(dict(run=case,baseline=before['source'],fixed=after['source'],files=assets,
                           after_output=after['output'],complete=bool(assets),
                           equal=bool(assets) and all(row['equal'] for row in assets.values())))
    return dict(planned=len(planned),reported=len(comparisons),
                matched=sum(row['equal'] for row in comparisons),comparisons=comparisons)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--prior',type=Path,default=PRIOR)
    parser.add_argument('--relay-reruns',type=Path)
    args=parser.parse_args()
    root=args.output
    planned = {tuple(row) for path in root.glob('planned-*.json') for row in json.loads(path.read_text())}
    data=root/'data';data.mkdir(exist_ok=True)
    scores,manifest,checks,errors=[],[],[],[]
    exports=defaultdict(list)
    with zipfile.ZipFile(args.prior) as archive:
        for case in sorted(planned):
            folder=case_dir(root,case)
            raw=folder/'run-v302.json'
            if not raw.is_file():
                manifest.append(dict(zip(('wave','group','seed','scenario','strategy','weather','requested_months'),case),
                                     outcome='pending_or_interrupted'))
                continue
            run=json.loads(raw.read_text())
            manifest.append({k:run.get(k) for k in (*KEYS,'group','output','outcome','source','tree_sha256',
                'catalog_sha256','map_sha256','weather_seed','market_stage','emergency','reserve_options',
                'full_months','completed_turns','rule_versions','failure','audit','performance','backend')})
            if run['outcome'] not in ('complete','natural_end'):
                continue
            try:
                scores.append(describe(run,folder,exports))
                checks.extend(baseline_checks(archive,run,folder))
            except Exception as exc:
                errors.append(dict(name(run),error=str(exc)))
    differences=list(paired(scores))
    grouped = defaultdict(list)
    for row in scores:
        grouped[tuple(row[key] for key in KEYS)].append((row['group'],row['completed_turns']))
    for key, completed in grouped.items():
        if len({turns for _,turns in completed})>1:
            exports['unpaired-horizons'].append(dict(zip(KEYS,key),completed=dict(completed)))
    exports.update({'scenario-scores':scores,'pairwise':differences,
        'balance-alerts':[row for row in differences if row['alert'] is True],
        'baseline-verification':checks,'long-term-economy-comparison':exports.pop('milestones',[]),
        'report-audit-errors':errors})
    for key,rows in exports.items():
        if rows:
            # Optional counters never disappear from the schema because a
            # particular scenario produced no such event.
            schema=list(dict.fromkeys(field for row in rows for field in row))
            rows=[{field:row.get(field) for field in schema} for row in rows]
        write_or_empty(data/f'{key}.csv',rows)
    to_json(data/'simulation-manifest.json',dict(schema='tk2-strategic-granary-v302-validation-v1',simulations=manifest))
    status=dict(total=len(manifest),outcomes=dict(Counter(row['outcome'] for row in manifest)),
                frozen_checks=len(checks),frozen_equal=sum(row['equal'] for row in checks),
                accounting_failures=errors,warning_count=len(exports['balance-alerts']))
    reruns=relay_reruns(root,args.relay_reruns or root.parent/'postfix')
    if reruns['planned']:
        affected=[row for row in scores if type(row['empty_relay_receipts']) is int and row['empty_relay_receipts']]
        matched={tuple(replay['run']) for replay in reruns['comparisons'] if replay['equal']}
        status['empty_relay_receipts']=sum(row['empty_relay_receipts'] for row in affected)
        reruns['affected_cases']=[dict(name(row), empty_receipts=row['empty_relay_receipts'],
            verified=tuple(row[key] for key in ('wave','group','seed','scenario','strategy',
                                                'weather','requested_months')) in matched) for row in affected]
        reruns['affected_count']=len(affected)
        reruns['affected_revalidated']=sum(row['verified'] for row in reruns['affected_cases'])
        status['relay_fix_reruns']={k:v for k,v in reruns.items() if k not in ('comparisons','affected_cases')}
        to_json(data/'relay-fix-reruns.json',reruns)
    to_json(data/'report-status.json',status)
    print(json.dumps(status,ensure_ascii=False))


if __name__ == '__main__':
    main()
