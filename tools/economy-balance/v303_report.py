"""Recalculate the V3.0.3 validation tables from completed physical game receipts."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import chain
import json
from math import ceil
from pathlib import Path
from shutil import copyfile
from statistics import mean

from common import to_json
from remake import logistics
from v302_experiments import map_sha
from v302_report import KEYS, csv_file_rows, describe, jsonl, pct
from v3021_report import candidate_metrics, file_sha, matches, output, read, severity
from v303_experiments import WAVES, options

SUCCESS = {'complete','natural_end'}
IDENTITY = (*KEYS,'economy_background','group')
EMPTY_PATCH = sha256(b'').hexdigest()
GUARDS = {
    'unpaid_city_turns':(20,'percent_up'),'rations_missing':(20,'percent_up'),
    'mean_turn_cpu':(30,'percent_up'),'winter_timely_percent':(5,'points_down'),
    'small_faction_survival_percent':(10,'points_down'),
}
GATES = {
    'python-complete':'Python 完整清單與本地化重跑','rust-complete':'Rust 完整清單與本地化重跑',
    'light-final':'固定 WASM、Rust crate、Node、WASM 差分',
    'node-review':'最終介面 Node 回歸',
    'web-reviewed':'可重現的瀏覽器發行包','pyodide-final':'實際 WASM／CPU 同版存讀和命令回放',
    'browser-localized':'繁中桌面／日文觸控水陸雙運隊及錯誤文案','browser-suite':'桌面及觸控完整回歸',
    'backend-parity':'候選同存檔 Rust／Python 領域狀態','save-parity':'同版存檔及相同起點的候選實際行為',
    'focused-authority':'物流、應急、糧倉、區域市場與運力雙後端',
    'fixed-final':'89 個固定需求及 23 個返程來源','physical-route-controls':'純河段物理與城市方針裝載校驗',
    'census-final':'29 個劇本的實際路段普查',
    'historical-1860':'歷史 1860 號 G1／C4 續跑','historical-short':'歷史三組運隊 G1／C4 續跑',
}
COPY_TABLES = {'transport-capacity-by-route','mixed-route-bottlenecks',
               'capacity-counterfactual','transport-capability-funnel'}
RUNTIME_REGRESSION = {'none','not_collected','not_applicable','null','','not_observed'}
CONTROL_METRICS = ('population','active_troops','grain_stock','gold_stock','reserves','battles',
                   'ai_sorties','unpaid_city_turns','rations_missing','convoy_grain_sent','convoy_grain_arrived')


def ratio(numerator,denominator):
    return round(numerator/denominator,8) if denominator else None


def labels(run):
    return {key:run[key] for key in IDENTITY}


def key_for(wave,background,group,row):
    seed,scene,strategy,weather,months=row
    return (wave,scene,seed,strategy,weather,months,background,group)


def requested():
    for wave,groups in (('quick',('C0','C1','C2','C2p','C3','C4')),
                        ('five',('C0','C4')),('long',('C0','C4')),('holdout',('C0','C4'))):
        for row in WAVES[wave]:
            for group in groups:
                yield key_for(wave,'G1',group,row)
    yield key_for('quick','G1','C1b',WAVES['quick'][0])
    for row in WAVES['five']:
        seed,scene,strategy,weather,_=row
        if (scene,strategy,weather)==('208-10',212,221):
            for group in ('C0','C4'):
                yield key_for('five','G4',group,row)
        if scene in ('184-02','208-10') and (strategy,weather)==(211,221):
            for group in ('C0','C4'):
                yield key_for('five','G0',group,row)


def sample_hashes(folder):
    assets=('monthly.csv','cities.csv','factions.csv','shortages.csv','convoys.csv','transport-capacity-events.jsonl.gz',
            'strategic-granary-events.jsonl.gz','convoy-survival.csv')
    return {name:file_sha(folder/name) for name in assets if (folder/name).is_file()}


def metadata(run,path,origin,relative):
    choices=('source','head','tree_sha256','worktree_diff_sha256','catalog_sha256','map_sha256',
             'weather_seed','emergency','market_stage','reserve_options','transport_capacity_options',
             'rule_versions','start_date','last_date','completed_turns','backend','parameters')
    return dict(labels(run),status=run['outcome'],input=origin,relative_path=relative,
                run_sha256=file_sha(path),**{key:run.get(key) for key in choices},
                sample_sha256=sample_hashes(path.parent))


def select(args,archived):
    required=set(requested())
    frozen=(args.build/'final-source.txt').read_text().strip()
    selected={}
    for origin in ('reviewed','final'):
        root=args.build/origin
        for path in sorted(root.glob('*/observed/*/*/*/*/*/*/*/run-v302.json')):
            run=read(path)
            key=tuple(run[k] for k in IDENTITY)
            if key not in required or key in selected:
                continue
            prior_disabled=(origin=='final' and run['group']=='C0'
                            and run['source']==args.prior_disabled)
            if (run['source']!=frozen and not prior_disabled) or '_working' in path.parts:
                continue
            meta=metadata(run,path,origin,path.parent.relative_to(root).as_posix())
            if run['outcome'] in SUCCESS:
                valid=(matches(run,run['scenario'],run['seed'],run['strategy'],run['weather'],run['requested_months'])
                       and run['worktree_diff_sha256']==EMPTY_PATCH
                       and (run['head']==run['source'] or prior_disabled and run['head']==frozen)
                       and run['transport_capacity_options']==options(run['group']))
                if not valid:
                    meta.update(status='metadata_mismatch')
            elif run.get('failure'):
                failure=run['failure']
                reason=failure.get('message') if isinstance(failure,dict) else failure
                meta['failure']=reason
            selected[key]=(run,path.parent,meta)
    for converted,path,reference in archived:
        key=tuple(converted[k] for k in IDENTITY)
        if key in required and key not in selected:
            meta=metadata(converted,path/'run-v302.json','historical',
                          reference['relative_path'])
            meta.update(reference_archive_sha256=reference['run_sha256'],
                        evidence='historical_g1_runtime_equivalence',
                        transport_capacity_options=None)
            selected[key]=(converted,path,meta)
    plans=[]
    for key in sorted(required):
        plans.append(selected[key][2] if key in selected else dict(zip(IDENTITY,key),status='not_completed'))
    return [(run,path) for run,path,meta in selected.values() if meta['status'] in SUCCESS], plans


def historical(args,out):
    records,g0,g1=[],[],[]
    archive=read(args.prior_summary/'data/simulation-manifest.json')['simulations']
    for meta in archive:
        if meta['group'] not in ('G0','G1') or meta['wave'] not in ('winter','dry','long'):
            continue
        candidates=[root/meta['relative_path']/'run-v302.json' for root in args.prior_observed]
        path=next((p for p in candidates if p.is_file() and file_sha(p)==meta['run_sha256']),None)
        if path is None:
            records.append(dict(meta,comparison_status='original_run_not_available'))
            continue
        raw=read(path)
        valid=(file_sha(path)==meta['run_sha256']
               and matches(raw,meta['scenario'],meta['seed'],meta['strategy'],meta['weather'],meta['requested_months'])
               and raw['rule_versions']==meta['rules_version'])
        records.append(dict(meta,sample_sha256=sample_hashes(path.parent),
                            comparison_status='verified_historical_reference' if valid else 'metadata_mismatch'))
        if valid and meta['group']=='G0':
            wave='five' if meta['wave'] in ('winter','dry') else 'long'
            g0.append((dict(raw,wave=wave,group='historical-G0',economy_background='G0'),path.parent))
        if valid and meta['group']=='G1':
            wave='five' if meta['wave'] in ('winter','dry') else 'long'
            g1.append((dict(raw,wave=wave,group='C0',economy_background='G1'),path.parent,meta))
    to_json(out/'sources/historical-economic-references.json',records)
    return g0,g1


def get_shortages(folder):
    return {(row['owner'],row['city'],int(row['turn'])) for row in csv_file_rows(folder/'shortages.csv')
            if int(row['missing'])>0}


def recorded_departures(folder):
    return {(int(row['convoy_id']),int(row['turn']),row['owner'],row['source'])
            for row in csv_file_rows(folder/'convoys.csv') if row['stage']=='departed'}


def source_shortage_after(departure,owner,source,horizon,completed,shortages):
    deadline=departure+horizon
    if deadline>completed:
        return None
    return any((owner,source,turn) in shortages for turn in range(departure+1,deadline+1))


def source_shortage_summary(evidence,basis):
    accounted=[case for case in evidence if case is not None]
    return dict(source_shortage_9_turn_numerator=sum(accounted),
                source_shortage_9_turn_denominator=len(accounted),
                source_shortage_9_turn_percent=pct(sum(accounted),len(accounted)),
                source_shortage_9_turn_basis=basis)


def route_modes(census):
    flows={}
    for row in census:
        key=tuple(row[name] for name in ('scenario','map_route','source','target'))
        flows[key]={step['kind'].removeprefix('river_') for step in json.loads(row['physical_stages'])
                    if step['kind'].startswith('river_')}
    return flows


def count_mode(name,rows):
    n=len(rows)
    counts=Counter()
    for row in rows:
        for key in ('loaded_grain','loaded_rations','actual_delivered_grain','rated_capacity',
                    'rated_grain','rated_rations','route_loss','weather_loss','observed_rations',
                    'observed_escort_days','receipt_cooldown_person_days','command_books','hunger_losses'):
            counts[key]+=row[key] or 0
        counts['observed_completed_days']+=row['actual_cycle_days'] or 0
        counts['terminated']+=row['terminal']!='right_censored'
        counts['positive_arrivals']+=row['actual_delivered_grain']>0
        counts['persons_sent']+=row['persons_sent']
        counts['persons_received']+=row['persons_received']
        counts['catalog_capacity_samples']+=row['rated_capacity'] is not None
        counts['dangerous_stalled']+=row['end_status']=='dangerous_stalled'
        if row['actual_cycle_days'] is not None:
            counts['completed_net']+=row['actual_delivered_grain']
    return dict(mode=name,departures=n,
        **{key:counts[key] for key in (
            'loaded_grain','loaded_rations','actual_delivered_grain','rated_capacity','rated_grain','rated_rations',
            'route_loss','weather_loss','observed_rations','observed_escort_days','receipt_cooldown_person_days',
            'command_books','hunger_losses','observed_completed_days','terminated','positive_arrivals',
            'persons_sent','persons_received','catalog_capacity_samples','dangerous_stalled','completed_net')},
        right_censored=n-counts['terminated'],
        occupancy_person_days=counts['observed_escort_days']+counts['receipt_cooldown_person_days'],
        total_utilization=ratio(counts['rated_grain']+counts['rated_rations'],counts['rated_capacity']),
        grain_utilization=ratio(counts['rated_grain'],counts['rated_capacity']),
        net_per_closed_convoy_day=ratio(counts['completed_net'],counts['observed_completed_days']),
        net_per_observed_escort_day=ratio(counts['actual_delivered_grain'],
            counts['observed_escort_days']+counts['receipt_cooldown_person_days']),
        net_per_transport_command=ratio(counts['actual_delivered_grain'],counts['command_books']),
        received_person_share=ratio(counts['persons_received'],counts['persons_sent']),
        termination_share=ratio(counts['terminated'],n))


def transport(run,folder,flows,tables):
    scope=labels(run)
    stream=folder/'transport-capacity-events.jsonl.gz'
    if not stream.exists():
        if not all((folder/name).is_file() for name in ('convoys.csv','shortages.csv')):
            return {}
        shortages=get_shortages(folder)
        return source_shortage_summary(
            (source_shortage_after(departure,owner,source,9,run['completed_turns'],shortages)
             for _,departure,owner,source in recorded_departures(folder)),
            'historical_departures_and_shortages')
    starts,ends,delivery,held={}, {}, {}, {}
    blockers,simultaneous=Counter(),Counter()
    unique=defaultdict(set)
    marks,occupation=defaultdict(Counter),defaultdict(Counter)
    rejects=defaultdict(list)
    for row in jsonl(stream):
        kind=row['event']
        ident=row.get('id')
        if kind=='departure':
            if ident in starts:
                raise ValueError('Duplicate physical departure')
            starts[ident]=row
            for person in row['officers']:
                if person in held:
                    marks[ident]['duplicate_person']+=1
                held[person]=ident
            simultaneous[row['active'],row['dispatch_count']]+=1
        elif kind=='terminal':
            if ident in ends:
                marks[ident]['duplicate_terminal']+=1
            ends[ident]=row
            for person in row['original_officers']:
                if held.get(person)==ident:
                    del held[person]
        elif kind=='delivery':
            if ident in delivery:
                marks[ident]['duplicate_delivery']+=1
            delivery[ident]=row
        elif kind in ('reroute','reroute_blocked'):
            cap=row['capacity']
            marks[ident][kind]+=1
            if kind=='reroute' and cap is not None and row['total']>cap:
                marks[ident]['reroute_limit_violation']+=1
            if kind=='reroute_blocked':
                rejects[ident].append(dict(turn=row['turn'],city=row['city'],target=row['target'],
                    total=row['total'],required_rations=row['required_rations'],capacity=cap))
        elif kind=='source_offer' and row['targets']:
            reason=row['reason'] or 'eligible'
            if reason=='source_convoy_limit':
                reason=('current_turn_dispatch_limit' if row['dispatch_count'] else 'active_origin_limit')
            blockers[reason]+=1
            unique[reason].add((row['turn'],row['owner'],row['source']))
            for exclusion,n in row['exclusions'].items():
                blockers['officer:'+exclusion]+=n
                unique['officer:'+exclusion].add((row['turn'],row['owner'],row['source']))
    for row in csv_file_rows(folder/'convoy-resolution-daily.csv.gz'):
        day=occupation[int(row['convoy_id'])]
        day['escort_days']+=int(row['current_officers'])+int(row['current_civil_staff'])
        day['days']+=1
    for row in csv_file_rows(folder/'transport-progress-daily.csv.gz'):
        day=occupation[int(row['convoy'])]
        day['ration']+=int(row['paid'] or 0)
        day['route_loss']+=int(row['route_loss'] or 0)
        day['weather_loss']+=int(row['incident_loss'] or 0)
        if row['phase']=='returning' and int(row['moved'] or 0)>0:
            day['return_days']+=1
        if not int(row['moved'] or 0):
            day['waiting_days']+=1
    survival={int(row['convoy_id']):row for row in csv_file_rows(folder/'convoy-survival.csv')}
    shortages=get_shortages(folder)
    terminal_load={row['id']:row for row in run['terminal']['convoy_loads']}
    receipts=[]
    measured_rejections=sum(blockers[reason] for reason in blockers if not reason.startswith('officer:'))
    for reason,count in sorted(blockers.items()):
        tables['transport-capacity-blockers'].append(dict(scope,reason=reason,
            counted=count,unique_source_turns=len(unique[reason]),source_assessments=measured_rejections))
    for (active,dispatched),count in sorted(simultaneous.items()):
        tables['origin-concurrency-usage'].append(dict(scope,active=active,dispatched=dispatched,departures=count))
    flags=run['transport_capacity_options'] or {}
    for ident,start in starts.items():
        end=ends.get(ident)
        cargo=start['cargo']['grain']
        bag=start['rations']
        rated=start['profile']['physical_capacity']
        mode=start['profile']['mode']
        audit=marks[ident]
        if start['active']>(2 if flags.get('concurrency') else 1):
            audit['origin_limit_violation']+=1
        if start['dispatch_count']>(2 if flags.get('double_dispatch') else 1):
            audit['dispatch_limit_violation']+=1
        if (flags.get('physical_capacity') and rated is not None and cargo+bag>rated):
            audit['departure_limit_violation']+=1
        if cargo>start['policy_grain']:
            audit['policy_limit_violation']+=1
        entry=delivery.get(ident,{})
        actual=entry.get('cargo',{}).get('grain',0)
        history=survival.get(ident,{})
        observed=occupation[ident]
        river_flows=set().union(*(flows.get((scope['scenario'],leg['id'],leg['from'],leg['to']),set())
                                  for leg in start['legs']))
        first_tick=(start['turn']-1)*10
        result='right_censored' if end is None else end['outcome']
        cycle=None
        cooldown=0
        if end is not None:
            cycle=end['end_tick']-first_tick
            if cycle<0:
                raise ValueError('Arrival precedes departure')
            if end['reusable_turn'] is not None:
                cooldown=max(0,(end['reusable_turn']-1)*10-end['end_tick'])*len(end['received_officers'])
            bag_account=end['rations']
            if bag_account['loaded']+bag_account['received']!=sum(bag_account[x] for x in
                    ('consumed','to_cargo','remaining')):
                audit['ration_account_mismatch']+=1
            if end['cargo_receipt'] and not logistics.valid_grain_receipt(end['cargo_receipt']):
                audit['cargo_account_mismatch']+=1
            if end['cargo_receipt'] and end['cargo_receipt']['cargo_delivered']!=actual:
                audit['delivery_receipt_mismatch']+=1
        elif ident not in terminal_load:
            audit['unknown_termination']+=1
        source_risk={f'source_shortage_in_{horizon}':source_shortage_after(
            start['turn'],start['owner'],start['source'],horizon,run['completed_turns'],shortages)
            for horizon in (1,3,9)}
        receipts.append(dict(scope,convoy=ident,owner=start['owner'],source=start['source'],target=start['target'],
            delivered_city=entry.get('target'),purpose=start['purpose'],mode=mode,route_mode=start['route_mode'],
            path=start['path'],legs=start['legs'],river_flows=sorted(river_flows),
            dispatch_turn=start['turn'],dispatch_date=[start[k] for k in ('year','month','day')],
            delivery_turn=entry.get('turn'),delivery_date=None if not entry else [entry[k] for k in ('year','month','day')],
            terminal_tick=end['end_tick'] if end is not None else None,reusable_turn=None if end is None else end['reusable_turn'],
            terminal=result,end_status=history.get('terminal_status'),
            physical_capacity=rated,policy_grain=start['policy_grain'],bottleneck=start['profile']['bottleneck'],
            loaded_grain=cargo,loaded_rations=bag,rated_capacity=rated,rated_grain=cargo if rated else 0,
            rated_rations=bag if rated else 0,expected_grain=start['estimated_net'],actual_delivered_grain=actual,
            route_loss=observed['route_loss'],weather_loss=observed['weather_loss'],
            estimated_outward_days=start['outbound_days'],
            arrival_boundary_days=None if not entry else (entry['turn']-start['turn'])*10,
            actual_cycle_days=cycle,actual_return_moving_days=observed['return_days'],
            route_wait_observed_days=observed['waiting_days'],observed_rations=observed['ration'],
            observed_escort_days=observed['escort_days'],receipt_cooldown_person_days=cooldown,
            persons_sent=len(start['officers']),persons_received=0 if end is None else len(end['received_officers']),
            escort_ids=start['officers'],initial_escort_troops=start['escort_troops'],
            hunger_losses=int(history.get('escort_hunger_loss') or 0),
            grain_remaining_at_cutoff=terminal_load.get(ident,{}).get('cargo_grain'),
            bag_remaining_at_cutoff=terminal_load.get(ident,{}).get('escort_bag'),
            command_books=start['command_books'],active_after_dispatch=start['active'],
            dispatches_this_turn=start['dispatch_count'], reroutes=audit['reroute'],capacity_blocked_attempts=rejects[ident],
            ledger_issues={name:n for name,n in audit.items() if n and name not in ('reroute','reroute_blocked')},
            **source_risk))
    aggregate=count_mode('all',receipts)
    for name in ('land','river','sea','mixed','stationary'):
        subset=[r for r in receipts if r['mode']==name]
        tables['transport-mode-throughput'].append(dict(scope,dimension='physical',**count_mode(name,subset)))
    for name in ('downstream','upstream','still'):
        subset=[r for r in receipts if r['river_flows']==[name]]
        tables['transport-mode-throughput'].append(dict(scope,dimension='one_river_flow',**count_mode(name,subset)))
    tables['officer-turnover-comparison'].append(dict(scope,**aggregate))
    tables['transport-dispatch-receipts'].extend(receipts)
    keyed={(ident,row['turn'],row['owner'],row['source']) for ident,row in starts.items()}
    if keyed!=recorded_departures(folder):
        raise ValueError(f'Departure observer disagrees with the original ledger: {scope}')
    source_risk=source_shortage_summary(
        (row['source_shortage_in_9'] for row in receipts),'verified_capacity_departures_and_shortages')
    return dict(physical_transport_departures=len(starts),actual_transport_grain=aggregate['actual_delivered_grain'],
        transport_net_per_escort_day=aggregate['net_per_observed_escort_day'],
        transport_net_per_command_book=aggregate['net_per_transport_command'],
        origin_limit_assessments=blockers['active_origin_limit'],
        origin_limit_distinct_source_turns=len(unique['active_origin_limit']),
        minimum_retained_officer_assessments=blockers['officer:below_minimum_retained_officers'],
        portable_transport_ledger_issues=sum(sum(r['ledger_issues'].values()) for r in receipts),
        prohibited_capacity_reroutes=sum(len(r['capacity_blocked_attempts']) for r in receipts),
        **source_risk)


def composition(run,folder,tables):
    scratch=defaultdict(list)
    score=describe(run,folder,scratch)
    details=defaultdict(list)
    candidate_metrics(run,folder,details)
    result={}
    for name in ('winter-army-supply-comparison','convoy-return-safety','performance-comparison',
                 'convoy-hunger-comparison'):
        tables[name].extend(dict(row,economy_background=run['economy_background']) for row in scratch[name])
    for name in ('comparable-dispatch-deadlines','residual-demand-comparison','existing-delivery-follow-up'):
        tables[name].extend(dict(row,economy_background=run['economy_background']) for row in details[name])
    for key in ('proactive_requested','proactive_dispatched','strategic_load','strategic_delivered',
                'timely_grain','late_grain','winter_dispatched','source_safety_rejections'):
        result[key]=score.get(key)
    if run['reserve_options'] is None:
        result=dict.fromkeys(result,None)
    tables['proactive-dispatch-comparison'].append(dict(labels(run),**result))
    score.pop('timely_legal_coverage',None)
    score.pop('observer_timely_shipment_rows',None)
    return dict(score,economy_background=run['economy_background'],**{
        key:value for key,value in severity(run,folder).items() if key not in (*KEYS,'group')})


def compare(scores):
    samples=defaultdict(dict)
    historic={}
    for row in scores:
        key=tuple(row[k] for k in KEYS)
        if row['group']=='historical-G0':
            historic[key]=row
        else:
            samples[key,row['economy_background']][row['group']]=row
    for (key,background),groups in sorted(samples.items()):
        for group,after in sorted(groups.items()):
            if group=='C0':
                continue
            controls={'C0':groups.get('C0')}
            if group=='C4':
                controls['historical-G0']=historic.get(key)
            for base,before in controls.items():
                if before is None or before['completed_turns']!=after['completed_turns']:
                    continue
                overlap=(before.keys() & after.keys())-set(IDENTITY)
                for metric in sorted(overlap):
                    a,b=before[metric],after[metric]
                    if type(a) not in (int,float) or type(b) not in (int,float):
                        continue
                    delta=round(b-a,8)
                    relative=pct(delta,a)
                    alert=None
                    if metric in GUARDS:
                        limit,unit=GUARDS[metric]
                        alert=((relative>limit if relative is not None else b>0)
                                if unit=='percent_up' else delta < -limit)
                    yield dict(zip(KEYS,key),economy_background=background,group=group,baseline=base,
                               metric=metric,before=a,after=b,change=delta,change_percent=relative,warning=alert)


def gates(args,out):
    status={}
    for key,title in GATES.items():
        flag=args.build/'checks'/f'{key}.exit'
        log=args.build/'logs'/f'{key}.log'
        code=int(flag.read_text()) if flag.is_file() else None
        status[key]=dict(check=title,status='not_completed' if code is None else
                         'pass' if code==0 else 'fail',exit_code=code,
                         log=None if not log.is_file() else 'logs/'+log.name,
                         sha256=None if not log.is_file() or code is None else file_sha(log))
    to_json(out/'checks/technical-gates.json',status)
    return status


def fixed_results(args,out):
    locations=(args.build/'reviewed/audits',args.build/'final/audits')
    counts=Counter()
    for label in COPY_TABLES:
        name=f'{label}.csv'
        path=next((root/name for root in locations if (root/name).is_file()),None)
        if path:
            copyfile(path,out/'data'/name)
    route=out/'data/transport-capacity-by-route.csv'
    if not route.exists():
        return {},{},{}
    disjoint=defaultdict(Counter)
    route_rows=list(csv_file_rows(route))
    for row in route_rows:
        disjoint[row['scenario']][row['mode']]+=1
        disjoint[row['scenario']]['catalog_'+row['catalog_mode']]+=1
        if row['potential_cargo'] not in RUNTIME_REGRESSION:
            disjoint[row['scenario']]['eligible_snapshot_routes']+=1
        if row.get('candidate_ai_potential') not in RUNTIME_REGRESSION | {None,'0'}:
            disjoint[row['scenario']]['operating_ai_eligible_routes']+=1
        old_policy=row.get('operating_v302_policy_max')
        if old_policy is not None and row['physical_capacity']!='null':
            change=int(row['physical_capacity'])-int(old_policy)
            disjoint[row['scenario']]['capacity_above_operating_policy']+=change>0
            disjoint[row['scenario']]['capacity_below_operating_policy']+=change<0
        difference=row['physical_capacity_vs_policy']
        if difference not in RUNTIME_REGRESSION:
            delta=int(difference)
            disjoint[row['scenario']]['nominal_above_policy']+=delta>0
            disjoint[row['scenario']]['nominal_below_policy']+=delta<0
        counts[row['mode']]+=1
    by_scenario=['land','mixed','river','sea','stationary','catalog_land','catalog_river','catalog_sea',
                 'eligible_snapshot_routes','operating_ai_eligible_routes','nominal_above_policy',
                 'nominal_below_policy','capacity_above_operating_policy','capacity_below_operating_policy']
    output(out/'data/route-census-by-scenario.csv',
           [dict(scenario=key,**{field:row[field] for field in by_scenario})
            for key,row in sorted(disjoint.items())])
    counts['scenario_count']=len(disjoint)
    counts['direction_rows']=len(route_rows)
    counts['map_directions']=len({(r['map_route'],r['source'],r['target']) for r in route_rows})
    counts['sea_with_land_access']=sum(r['catalog_mode']=='sea' and r['mode']=='mixed' for r in route_rows)
    counts['unique_pure_water_directions']=len({(r['map_route'],r['source'],r['target']) for r in route_rows
                                                 if r['mode'] in ('river','sea')})
    fixed=out/'data/transport-capability-funnel.csv'
    if not fixed.is_file():
        return dict(counts),{},route_modes(route_rows)
    totals=defaultdict(Counter)
    for row in csv_file_rows(fixed):
        collection=totals[row['group']]
        collection['targets']+=1
        # Per-target L0–L4 share the same source stock. Sum only actual,
        # uniquely attributed L5 shipments from the single replay.
        for key in ('l1_donor_surplus','l2_legal_outbound_surplus','l3_qualified_gross',
                    'l4_estimated_net_upper_bound'):
            collection[key+'_positive_targets']+=int(row[key])>0
        receipts=json.loads(row['l5_actual_receipts'])
        receipts=[r for r in receipts if r['purpose'] in ('ordinary','strategic','regional')]
        if row['l5_actual_reception']=='null':
            collection['targets_censored']+=1
        else:
            arrived=sum(r['cargo']['grain'] for r in receipts)
            collection['l5_received']+=arrived
            collection['l5_with_supply']+=arrived>0
            collection['l5_full']+=arrived>=int(row['first_uncovered_grain'])
            collection['l5_strategic_received']+=int(row['l5_strategic_reception'])
    counterfactual=out/'data/capacity-counterfactual.csv'
    for row in csv_file_rows(counterfactual):
        collection=totals[row['group']]
        collection['returning_samples']+=1
        collection['qualified_source_sample']+=row['donor_qualified']=='true'
        collection['timely_quote_sample']+=bool(json.loads(row['timely_quotes']))
        eligible=[x for x in json.loads(row['actual_shipments'])
                  if x['purpose'] in ('ordinary','strategic','regional')]
        collection['actual_dispatch_receipt_sample']+=bool(eligible)
    for copy in ('fixed-capacity-replay-traces.json','fixed-replay-inputs.json'):
        root=locations[0]
        if (root/copy).is_file():
            copyfile(root/copy,out/'checks'/copy)
    return dict(counts),{key:dict(value) for key,value in totals.items()},route_modes(route_rows)


def performance(args,out):
    traces=[]
    for disabled in sorted((args.build/'checks').glob('*-disabled.json')):
        released=disabled.with_name(disabled.name.replace('-disabled','-released'))
        if not released.is_file():
            continue
        a,b=read(released),read(disabled)
        if a['checkpoint_sha256']!=b['checkpoint_sha256']:
            continue
        for before,after in zip(a['checks'],b['checks'],strict=True):
            traces.append(dict(checkpoint=disabled.stem.removesuffix('-disabled'),
                sha256=a['checkpoint_sha256'],turn=before['turn'],released_state=before['checksum'],
                candidate_disabled_state=after['checksum'],same_state=before['checksum']==after['checksum'],
                same_rng=before['rng']==after['rng'],same_decisions=before['decisions']==after['decisions'],
                released_turn_cpu=before['cpu'],disabled_turn_cpu=after['cpu']))
    output(out/'data'/'performance-state-parity.csv',traces)
    path=out/'checks/fixed-capacity-replay-traces.json'
    detail=[]
    if path.is_file():
        for row in read(path):
            times=[item['cpu'] for item in row['checks']]
            if times:
                ordered=sorted(times)
                detail.append({key:row[key] for key in ('group','fixture','fixture_sha256','scenario','strategy','seed')}
                    | dict(turns=len(times),mean_cpu_seconds=mean(times),p95_cpu_seconds=ordered[ceil(len(times)*.95)-1]))
    output(out/'data'/'fixed-state-performance.csv',detail)
    return dict(sampled_turns=len(traces),exact_turns=sum(row['same_state'] and row['same_rng'] and
                                                       row['same_decisions'] for row in traces))


def baseline_verification(args,out,runs,archived):
    cases={}
    for run,folder,reference in archived:
        key=tuple(run[k] for k in ('scenario','seed','strategy','weather'))
        data=cases.setdefault(key,[])
        data.append((run,folder,reference))
    measured=[]
    for run,folder in runs:
        if run['group']!='C0' or run['economy_background']!='G1' or 'transport_capacity_options' not in run:
            continue
        key=tuple(run[k] for k in ('scenario','seed','strategy','weather'))
        for old,previous,reference in cases.get(key,()):
            old_rows={int(row['elapsed_turns']):tuple(row[field] for field in CONTROL_METRICS)
                      for row in csv_file_rows(previous/'monthly.csv')}
            overlap=diffs=0
            for row in csv_file_rows(folder/'monthly.csv'):
                tick=int(row['elapsed_turns'])
                if tick in old_rows:
                    overlap+=1
                    diffs+=tuple(row[field] for field in CONTROL_METRICS)!=old_rows[tick]
            measured.append(dict(labels(run),candidate=run['source'],historical=old['source'],
                candidate_horizon=run['requested_months'],historical_horizon=old['requested_months'],
                matched_boundaries=overlap,mismatched_boundaries=diffs,metrics=list(CONTROL_METRICS),
                historical_run_sha256=reference['run_sha256'],historical_monthly_sha256=file_sha(previous/'monthly.csv'),
                observed_monthly_sha256=file_sha(folder/'monthly.csv')))
    preserved=args.prior_summary/'data/performance-state-parity.csv'
    prior=list(csv_file_rows(preserved))
    domains=('same_state','same_rng','same_candidate_order_and_receipts')
    states={field:dict(matches=sum(row[field]=='true' for row in prior),
                       sampled=sum(row[field]!='null' for row in prior)) for field in domains}
    if args.use_verified_baselines and (not measured or any(row['mismatched_boundaries'] for row in measured)
            or not prior or any(not row['sampled'] or row['matches']!=row['sampled'] for row in states.values())):
        raise ValueError('The reused historical control needs matching state and resource evidence')
    output(out/'data/baseline-verification.csv',measured)
    to_json(out/'sources/baseline-runtime-equivalence.json',
        dict(archived_g1_g2_sha256=file_sha(preserved),historical_fixed_runtime_matches=states,
             historical_fixed_boundaries=len(prior),observed_prefix_pairs=len(measured),
             comparable_boundary_metrics=list(CONTROL_METRICS),
             matching_boundaries=sum(row['matched_boundaries']-row['mismatched_boundaries'] for row in measured),
             differences=sum(row['mismatched_boundaries'] for row in measured)))


def report(args):
    out=args.output
    for folder in ('data','docs','checks','sources'):
        (out/folder).mkdir(parents=True,exist_ok=True)
    historical_runs,baselines=historical(args,out)
    runs,planned=select(args,baselines if args.use_verified_baselines else [])
    baseline_verification(args,out,runs,baselines)
    route_counts,fixed,flows=fixed_results(args,out)
    tables=defaultdict(list)
    scores=[]
    for run,folder in sorted(chain(runs,historical_runs),key=lambda pair:tuple(pair[0][key] for key in IDENTITY)):
        score=composition(run,folder,tables)
        score.update(transport(run,folder,flows,tables))
        if (run['reserve_options'] is None):
            for key in ('strategic_delivered','timely_grain','late_grain'):
                score[key]=None
        scores.append(score)
        print(*[run[key] for key in IDENTITY],flush=True)
    first=list(dict.fromkeys(key for row in scores for key in row))
    scores=[{key:row.get(key) for key in first} for row in scores]
    pairs=list(compare(scores))
    warnings=[row for row in pairs if row['warning']]
    output(out/'data/scenario-scores.csv',scores,IDENTITY)
    output(out/'data/pairwise.csv',pairs)
    output(out/'data/balance-alerts.csv',warnings)
    phase_metrics={'unpaid_city_turns','rations_missing','grain_stock','gold_stock','battles','ai_sorties',
                   'longest_streak','p95','median','min','convoy_hunger_losses','strategic_delivered',
                   'regional_delivered','winter_timely_percent','small_faction_survival_percent','mean_turn_cpu',
                   'source_shortage_9_turn_percent','transport_net_per_escort_day','transport_net_per_command_book'}
    for phase,name in (('holdout','holdout-comparison'),('long','long-term-economy-comparison')):
        output(out/'data'/f'{name}.csv',[row for row in pairs if row['wave']==phase and
               row['group']=='C4' and row['metric'] in phase_metrics])
    for name in ('transport-mode-throughput','origin-concurrency-usage','officer-turnover-comparison',
                 'transport-capacity-blockers','transport-dispatch-receipts','proactive-dispatch-comparison',
                 'comparable-dispatch-deadlines','convoy-return-safety','convoy-hunger-comparison',
                 'winter-army-supply-comparison','performance-comparison',
                 'residual-demand-comparison','existing-delivery-follow-up'):
        output(out/'data'/f'{name}.csv',tables[name])
    receipts=tables['transport-dispatch-receipts']
    for name,keys in (
            ('transport-capacity-utilization',('convoy','mode','physical_capacity','policy_grain','loaded_grain','loaded_rations')),
            ('origin-dispatch-slots',('convoy','owner','source','dispatch_turn','active_after_dispatch','dispatches_this_turn')),
            ('officer-transport-occupation',('convoy','mode','escort_ids','dispatch_turn','delivery_turn','terminal_tick',
                                               'reusable_turn','observed_escort_days','receipt_cooldown_person_days','terminal'))):
        output(out/'data'/f'{name}.csv',[{k:row[k] for k in IDENTITY+keys} for row in receipts])
    perf=performance(args,out)
    checked=gates(args,out)
    for name in ('physical-route-controls.json','save-parity.json','browser-suite-proof.json','backend-suite-proof.json'):
        source=args.build/'checks'/name
        if source.is_file():
            copyfile(source,out/'checks'/name)
    summarized=dict(source=(args.build/'final-source.txt').read_text().strip(),
        states={state:sum(m['status']==state for m in planned) for state in sorted({r['status'] for r in planned})},
        planned_runs=len(planned),completed_runs=len(runs),fixed=fixed,route_census=route_counts,performance=perf,
        archived_runtime_equivalent_runs=sum(row.get('input')=='historical' for row in planned),
        accounting_issues=sum(row['portable_transport_ledger_issues'] or 0 for row in scores),
        city_resource_mismatches=sum(row.get('city_resource_mismatches') or 0 for row in scores),
        balance_warnings=len(warnings),gates={name:row['status'] for name,row in checked.items()})
    to_json(out/'data'/'report-status.json',summarized)
    web_build=args.build/'logs/web-reviewed.log'
    web={} if not web_build.is_file() else read(web_build)
    to_json(out/'data'/'simulation-manifest.json',dict(simulations=planned,source=summarized['source'],
        map_sha256=map_sha(),baseline_release=args.release,
        frozen_at=(args.build/'candidate-frozen-at.txt').read_text().strip(),
        interface_source=(args.build/'interface-source.txt').read_text().strip(),
        web_content_sha256=web.get('content_sha256'),web_build_commit=web.get('commit')))
    return summarized


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--prior-summary',type=Path,required=True)
    parser.add_argument('--prior-observed',type=Path,action='append',default=[])
    parser.add_argument('--prior-disabled',required=True)
    parser.add_argument('--release',required=True)
    parser.add_argument('--use-verified-baselines',action='store_true')
    args=parser.parse_args()
    status=report(args)
    print(json.dumps(status,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
