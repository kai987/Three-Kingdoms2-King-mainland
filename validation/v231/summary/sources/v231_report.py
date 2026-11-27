"""Produce auditable V2.3.1 climate, supply and economy comparisons."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import re
import shutil

from common import ROOT, TOOL_ROOT, git, sha256, to_csv, to_json
from remake.campaign import digest, verified_save_content
from v221_report import supply as legacy_supply
from v23_report import NORTH, published_gates
from v231_observe import cases as expected_cases

WINTER = (11,12,1,2,3)
IDENTITY = ('wave','group','scenario','seed','strategy')
MACRO = {'shortage_city_turns':'unpaid_city_turns','grain_gap':'rations_missing',
         'convoy_hunger_losses':'convoy_hunger_losses','grain_stock':'grain_stock',
         'market_stock':'market_stock','battles':'battles','population':'population',
         'active_troops':'active_troops','convoy_dispatched':'convoy_dispatched',
         'convoy_returned':'convoy_returned','convoy_grain_arrived':'convoy_grain_arrived'}
WATCH = {'shortage_city_turns':(20,False),'grain_gap':(20,False),'winter_grain_rate':(5,True),
         'winter_order_rate':(5,True),'small_survival':(10,True),'mean_turn_cpu':(30,False)}


def rows(path):
    with path.open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream))


def events(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def value(data,key):
    item=data.get(key)
    if item in (None,'','null','not_applicable','not_collected'):
        return None
    try:
        return int(item)
    except ValueError:
        return float(item)


def percentage(numerator,denominator):
    return 100*numerator/denominator if denominator else None


def emit(folder,name,result,headers=()):
    items=list(result)
    path=folder/(name+'.csv')
    if items:
        to_csv(path,items)
    else:
        path.write_text(','.join(headers)+'\n',encoding='utf-8')


def month_at(case,tick):
    return (case['start_date'][1]-1+max(0,tick-1)//30)%12+1


def military(case,episode_rows,convoy_events):
    request_ledger,receipt_ledger=[],[]
    totals=Counter()
    for row in episode_rows:
        opened=int(row['first_request_time'])
        request=value(row,'original_required_grain')+value(row,'additional_required_grain')
        timely=int(row['timely_delivered_grain'])
        late=int(row['late_delivered_grain'])
        remain=int(row['remaining_unmet_grain'])
        assert request==timely+late+remain
        winter=month_at(case,opened) in WINTER
        entry=dict(episode=row['supply_episode_id'],army=int(row['army_id']),owner=row['faction_id'],opened=opened,
            winter=winter,requested_grain=request,original_deadline=int(row['original_shortage_deadline']),
            final_deadline=int(row['updated_shortage_deadline']),first_actual_shortage=value(row,'actual_shortage_tick'),
            timely_received_grain=timely,late_received_grain=late,remaining_unmet_grain=remain,
            convoy_ids=json.loads(row['assigned_convoy_ids']),status=row['terminal_status'])
        cancelled=remain if entry['status']=='cancelled_no_longer_needed' else 0
        receipts=json.loads(row['actual_deliveries'])
        before_original=sum(r['credited'] for r in receipts if r['day']<=entry['original_deadline'])
        entry.update(covered_by_other_channel=sum(r['credited'] for r in receipts if r['kind']!='convoy'),
            cancelled_due_to_target_change=cancelled,unresolved_grain=remain-cancelled,
            timely_at_original_deadline=before_original,progress=row['progress'],
            resolved_at=value(row,'resolved_time'),failure_reason=row['failure_reason'],
            blockers=json.loads(row['blockers']),hunger_losses=value(row,'hunger_losses'))
        entry['never_dispatched']=not entry['convoy_ids']
        request_ledger.append(entry)
        for item in receipts:
            receipt_ledger.append(dict(episode=entry['episode'],army=entry['army'],owner=entry['owner'],
                winter_request=winter,winter_receipt=month_at(case,item['day']) in WINTER,
                before_original_deadline=item['day']<=entry['original_deadline'],**item))
        if winter:
            totals.update(requests=1,requested_grain=request,timely_received_grain=timely,late_received_grain=late,
                unresolved_grain=entry['unresolved_grain'],covered_by_other_channel=entry['covered_by_other_channel'],
                cancelled_due_to_target_change=cancelled,never_dispatched=entry['never_dispatched'],
                timely_at_original_deadline=before_original,
                no_dispatch_unresolved_grain=entry['unresolved_grain'] if entry['never_dispatched'] else 0)
    convoys=defaultdict(list)
    for row in convoy_events:
        convoys[row['convoy']].append(row)
    orders=[]
    active=set(item['id'] for item in case.get('terminal',{}).get('convoy_loads',()))
    for ident,history in sorted(convoys.items()):
        start=next((r for r in history if r['event']=='transport_departed'),None)
        if start is None:
            continue
        delivered=[r for r in history if r['event']=='transport_arrived' and r['grain']>0]
        deadline=start['original_eta'] or start['first_arrival_turn']
        mature=deadline<=case['completed_turns']+1
        winter=start['month'] in WINTER
        arrived_before=[r for r in delivered if r['turn']<=deadline]
        cancelled=not delivered and ident not in active and any(
            r['event']=='transport_returned' or r['reason'] in ('army_supplied','rendezvous_expired') for r in history)
        order=dict(convoy=ident,army=start['army'],owner=start['owner'],origin=start['source'],target=start['target'],
            departure_turn=start['turn'],winter_dispatch=winter,original_demand=start['original_request'],
            original_demand_deadline=start['original_need_deadline'],original_order_deadline=deadline,
            grain_dispatched=start['grain'],rations_dispatched=start['rations'],matured=mature,
            timely=bool(arrived_before),late=bool(delivered and not arrived_before),
            no_receipt=not delivered,pending=not mature and not delivered,cancelled=cancelled,
            delivered_grain=sum(r['grain'] for r in delivered),
            received_turn=min((r['turn'] for r in delivered),default=None))
        orders.append(order)
        if winter:
            totals.update(matured_orders=mature,timely_positive_receipt_orders=mature and order['timely'],
                          late_orders=mature and order['late'],no_receipt_orders=mature and order['no_receipt'],
                          pending_orders=order['pending'],cancelled_orders=cancelled)
    totals['timely_grain_rate']=percentage(totals['timely_received_grain'],totals['requested_grain'])
    totals['original_deadline_grain_rate']=percentage(totals['timely_at_original_deadline'],totals['requested_grain'])
    totals['timely_order_rate']=percentage(totals['timely_positive_receipt_orders'],totals['matured_orders'])
    return totals,request_ledger,receipt_ledger,orders


def aggregate_warehouse(postings,regions):
    totals={}
    labels={}
    serial=Counter()
    previous={}
    translated={'regular_income':'regular_production','civil_bonus':'civil_bonus','harvest_bonus':'harvest_bonus',
                'city_consumption':'resident_and_garrison_paid','payroll':'military_and_civil_payroll',
                'payroll.pay_city':'military_and_civil_payroll',
                'recruitment':'recruitment_grain','convoy_load':'cargo_and_rations_dispatched',
                'convoy_delivery':'combined_transport_received','convoy_ration_transfer':'transport_rations_dispatched',
                'facilities.month_rollover':'disaster_grain_loss','convoy_receipt':'convoy_return_or_baggage',
                'travel._queue_march':'army_dispatch_grain','battle_reinforcements._order':'reinforcement_grain',
                'diplomacy._request_grain':'allied_aid','convoy_emergency_refill':'convoy_emergency_refill'}
    for row in postings:
        if row['resource']!='grain':
            continue
        city=row['city']
        stamp=(row['year'],row['month'],row['owner'])
        if previous.get(city)!=stamp:
            serial[city]+=1
            previous[city]=stamp
        key=(city,serial[city])
        account=totals.get(key)
        if account is None:
            account=Counter(opening_grain=row['balance_before'])
            totals[key]=account
        else:
            assert account['closing_grain']==row['balance_before'],(city,row['turn'],row['site'])
        category=translated.get(row['category'],'other_verified_postings')
        if row['category']=='market_exchange':
            category='market_purchase' if row['delta']>0 else 'market_sale'
        if row['category'] in ('march_ration_transfer','march_supply.advance_unit'):
            category='army_city_refill'
        account[category]+=row['delta']
        account['closing_grain']=row['balance_after']
        account['net_postings']+=row['delta']
        labels[key]=dict(city=city,region=regions.get(city,'unmapped'),year=row['year'],month=row['month'],
                         owner=row['owner'],segment=key[1])
    for key,account in totals.items():
        assert account['opening_grain']+account['net_postings']==account['closing_grain']
        fields=(*dict.fromkeys(translated.values()),'market_purchase','market_sale','army_city_refill','other_verified_postings',
                'opening_grain','net_postings','closing_grain')
        yield dict(**labels[key],**{name:account[name] for name in fields},
                   regional_purchase_received=None,strategic_transport_received=None,ordinary_transport_received=None,
                   resident_consumption=None,garrison_consumption=None,transport_cargo_dispatched=None,
                   protected_rations_dispatched=None,capture_grain_change=None)


def city_shortages(city_rows,postings,regions):
    history=defaultdict(list)
    for row in city_rows:
        if regions.get(row['city'])=='southern_basins':
            history[row['city']].append(row)
    tallies,before,context=[],[],[]
    for city, months in sorted(history.items()):
        unpaid=[item for item in months if item['missing']]
        if not unpaid:
            continue
        severe=next((row for row in unpaid if row['missing']*4>=row['required']),None)
        longest=streak=0
        last=-2
        for row in unpaid:
            streak=streak+1 if row['turn']==last+1 else 1
            longest=max(streak,longest)
            last=row['turn']
        tallies.append(dict(city=city,shortage_city_turns=len(unpaid),grain_gap=sum(r['missing'] for r in unpaid),
            longest_streak=longest,first_shortage=unpaid[0]['turn'],
            first_severe=severe['turn'] if severe else None,
            first_severe_year=severe['year'] if severe else None,first_severe_month=severe['month'] if severe else None,
            owner_at_first_severe=severe['owner'] if severe else None,
            garrison_at_first_severe=severe['active'] if severe else None,
            market_stock_at_first_severe=severe['market_stock'] if severe else None))
        if severe:
            start=severe['turn']-9
            before.extend(dict(row) for row in postings.get(city,()) if start<=row['turn']<severe['turn'])
            context.extend(row for row in months if start<=row['turn']<=severe['turn'])
    by_count={row['city']:position for position,row in enumerate(sorted(tallies,key=lambda r:-r['shortage_city_turns']),1)}
    by_gap={row['city']:position for position,row in enumerate(sorted(tallies,key=lambda r:-r['grain_gap']),1)}
    return [dict(row,frequency_rank=by_count[row['city']],gap_rank=by_gap[row['city']])
            for row in tallies],before,context


class Case:
    def __init__(self,path,regions):
        self.run=json.loads(path.read_text(encoding='utf-8'))
        self.path=path.parent
        if self.run['wave']=='root':
            self.run['wave']='long'
        self.identity={key:self.run[key] for key in IDENTITY}
        base=self.path/self.run['scenario']
        self.world={int(row['elapsed_months']):row for row in rows(base/'monthly.csv')}
        self.factions=rows(base/'factions.csv')
        self.month=max(self.world)
        self.regions=defaultdict(Counter)
        holdings=Counter()
        northern=Counter()
        for row in rows(base/'cities.csv'):
            month=int(row['elapsed_months'])
            region=regions.get(row['city'],'unmapped')
            part=self.regions[month,region]
            part.update(unpaid_city_turns=int(row['unpaid_city_turns']),grain_stock=int(row['grain_stock']))
            if month==0 and row['owner']!='neutral':
                holdings[row['owner']]+=1
                northern[row['owner']]+=region in NORTH
        self.northern_factions={owner for owner in holdings if northern[owner]*2>=holdings[owner]}
        convoy_events=[]
        posts=[]
        rations=[]
        self.climate=[]
        self.agriculture=defaultdict(Counter)
        self.preparation=[]
        self.planning=[]
        self.checkpoints=[]
        self.cargo=Counter()
        for row in events(self.path/'events.jsonl.gz'):
            kind=row.pop('kind')
            if kind=='army_convoy':
                convoy_events.append(row)
            elif kind=='agriculture_year':
                self.climate.append(row)
            elif kind=='agricultural_preparation':
                self.preparation.append(row)
            elif kind=='agricultural_income':
                key=row['region'],row['year'],row['month']
                self.agriculture[key].update(regular=row['regular'],adjusted=row['adjusted'],
                                             adjustment=row['adjusted']-row['regular'])
            elif kind in ('army_demand_observed','army_reliable_inbound'):
                fields=('turn','army','owner','required','deadline','urgent','stopped','window_count','covered','uncovered')
                self.planning.append(dict(event=kind,**dict.fromkeys(fields)) | row)
            elif kind=='shortage_checkpoint':
                self.checkpoints.append(row)
            elif kind=='warehouse_posting' and self.identity['scenario']=='208-10' and self.identity['strategy']==211:
                posts.append(row)
            elif kind=='city_rations':
                rations.append(row)
            elif kind=='convoy_grain_daily':
                self.cargo.update(paid_rations=row['paid'],ice_wait_rations=row['paid'] if row['reason']=='ice' else 0,
                    return_rations=row['paid'] if row['phase']=='returning' else 0,cargo_rations=row['cargo_to_bag'],
                    base_rations=row['base_rations'] or 0,weather_extra_rations=row['weather_extra_rations'] or 0,
                    person_days=row['person_days'])
                if row['base_rations'] is None:
                    self.cargo['incomplete_component_days']+=bool(row['paid'])
                elif row['base_rations']<0:
                    self.cargo['incomplete_component_days']+=1
                self.cargo['measured_days']+=1
        self.military,self.requests,self.receipts,self.orders=military(self.run,
            rows(self.path/'supply-episodes-weather-aware.csv'),convoy_events)
        _,legacy=legacy_supply(self.run,self.path,'supply-episodes-weather-aware.csv')
        for previous,current in (('required','requested_grain'),('timely','timely_received_grain'),
                                 ('late','late_received_grain')):
            assert legacy.get(previous,0)==self.military[current],(self.identity,previous)
        self.military['legacy_unmet_including_cancellations']=legacy.get('unmet',0)
        self.accounts=list(aggregate_warehouse(posts,regions)) if rations else []
        grouped=defaultdict(list)
        for posting in posts:
            if posting['resource']=='grain' or (posting['resource']=='ownership' and
                                               posting['site']!='strategic_ai.war_budget'):
                grouped[posting['city']].append(posting)
        self.shortages,self.before,self.shortage_context=(
            city_shortages(rations,grouped,regions) if rations else ([],[],[]))

    def score(self,month):
        snapshot=self.world[month]
        small={row['faction'] for row in self.factions if int(row['elapsed_months'])==0
               and row['faction']!='neutral' and 1<=int(row['cities'])<=3}
        living={row['faction'] for row in self.factions if int(row['elapsed_months'])==month and int(row['cities'])}
        complete=month==self.month
        return dict(months=month,source=self.run['source'],provenance='observed',
            **{target:value(snapshot,key) for target,key in MACRO.items()},
            winter_grain_rate=self.military['timely_grain_rate'] if complete else None,
            winter_order_rate=self.military['timely_order_rate'] if complete else None,
            small_survival=percentage(len(small & living),len(small)),
            northern_survival=percentage(len(self.northern_factions & living),len(self.northern_factions)),
            grain_per_thousand_person_days=(1000*value(snapshot,'convoy_grain_arrived')/self.cargo['person_days']
                                           if complete and self.cargo['person_days'] else None),
            mean_turn_cpu=self.run['performance']['mean_turn_cpu_seconds'] if complete else None)


def prior_cases(summary):
    source=json.loads((summary/'data/report-status.json').read_text(encoding='utf-8'))['source']
    for row in rows(summary/'data/scenario-scores.csv'):
        if row['wave'] not in ('long','five','holdout') or row['group'] not in ('W0','W4'):
            continue
        identity={key:row[key] for key in IDENTITY}
        identity.update(group={'W0':'F0','W4':'F2'}[identity['group']],seed=int(row['seed']),strategy=int(row['strategy']))
        yield identity,dict(months=int(row['elapsed_months']),source=source,provenance='v23_original',
            **{key:value(row,key) for key in MACRO},winter_grain_rate=None,
            winter_order_rate=value(row,'winter_timely'),small_survival=value(row,'small_survival'),
            northern_survival=value(row,'northern_survival'),grain_per_thousand_person_days=None,
            mean_turn_cpu=value(row,'mean_turn_cpu'))


def matrix(observed,prior):
    cohorts=defaultdict(dict)
    for identity, score in prior:
        key=tuple(identity[k] for k in IDENTITY if k!='group')
        cohorts[key][identity['group']]=score
    for case in observed:
        key=tuple(case.identity[k] for k in IDENTITY if k!='group')
        cohorts[key][case.identity['group']]=case.score(case.month)
    scores,pairs,alerts=[],[],[]
    for (wave,scenario,seed,strategy),cases in sorted(cohorts.items()):
        ident=dict(wave=wave,scenario=scenario,seed=seed,strategy=strategy)
        for group,result in sorted(cases.items()):
            scores.append(dict(**ident,group=group,**result))
        for left,right in (('F0','F2'),('F0','F4'),('F1','F3'),('F2','F4'),('F3','F4'),('W2','F2')):
            if not {left,right}<=cases.keys():
                continue
            a,b=cases[left],cases[right]
            if a['months']!=b['months']:
                continue
            fields=(*MACRO,*[k for k in WATCH if k not in MACRO],
                    'northern_survival','grain_per_thousand_person_days')
            pairs.append(dict(**ident,reference=left,candidate=right,months=a['months'],
                **{f'reference_{key}':a[key] for key in fields},**{key:b[key] for key in fields}))
            for metric,(limit,points) in WATCH.items():
                old,new=a[metric],b[metric]
                change=(None if old is None or new is None else
                        old-new if points else percentage(new-old,old))
                alerts.append(dict(**ident,reference=left,candidate=right,months=a['months'],metric=metric,
                    reference_value=old,candidate_value=new,change=change,threshold=limit,
                    units='percentage_points' if points else 'percent',
                    alert=(change>limit if change is not None else old==0 and new is not None and new>0 and not points)))
    return scores,pairs,alerts


def fixed_route_exports(data,phases):
    measured=[]
    maxima=[]
    weather_rows=[]
    controlled=[]
    for phase in phases:
        for row in rows(data/f'{phase}-cross-month-route-prediction.csv'):
            visible=json.loads(row['visible'])
            current=visible.get(row['region'],{})
            base,expected=value(row,'base_days'),value(row,'new_days')
            splits=tuple(value(row,key) for key in ('visible_extra','seasonal_extra','predicted_ice_wait_days'))
            ration_splits=tuple(value(row,key) for key in ('base_rations','visible_rations','seasonal_rations','waiting_rations'))
            measured.append(dict(phase=phase,seed=row['seed'],region=row['region'],date=[int(row[key])
                for key in ('year','month','day')],route_ids=json.loads(row['route_ids']),base=base,expected=expected,
                weather_parts=splits,expected_rations=value(row,'new_rations'),ration_parts=ration_splits,
                exact_cost_split=(base+sum(splits)==expected and sum(ration_splits)==value(row,'new_rations')),
                currently_blocked=row['currently_blocked'],freeze_risk=value(row,'freeze_risk'),
                actual_ice_wait=value(row,'actual_ice_wait_days'),return_freeze_risk=value(row,'return_freeze_risk'),
                actual_return_ice_wait=value(row,'actual_return_ice_wait_days'),
                new_net=value(row,'new_net'),actual_net=value(row,'actual_net'),old23_net=value(row,'old23_net')))
            maxima.append(dict(phase=phase,seed=row['seed'],region=row['region'],month=row['month'],day=row['day'],
                current_depth=current.get('depth'),current_snow=current.get('severity'),
                current_cold=current.get('cold'),normal_days=base,forecast_days=expected,
                actual_days=value(row,'actual_days'),maximum_quoted_days=value(row,'conservative_days'),
                deadline_covered=value(row,'actual_days')<=value(row,'conservative_days')))
            # The same explicitly fixed service level for all forecast generations.
            deadline=base+10
            funded=(5*value(row,'base_rations')+3)//4
            if row['currently_blocked']=='null':
                actual=(value(row,'actual_days')<=deadline and value(row,'actual_rations')<=funded)
                for model in ('old221','old23','new'):
                    eligible=value(row,model+'_days')<=deadline and value(row,model+'_rations')<=funded
                    controlled.append(dict(phase=phase,seed=row['seed'],region=row['region'],model=model,
                        controlled_deadline_days=deadline,controlled_ration_budget=funded,
                        actual_before_deadline=value(row,'actual_days')<=deadline,
                        actual_rations_covered=value(row,'actual_rations')<=funded,actual_feasible=actual,
                        forecast_feasible=eligible,false_rejection=actual and not eligible,
                        false_acceptance=eligible and not actual))
        normals=data/f'{phase}-monthly-weather-joint-distribution.csv'
        if normals.is_file():
            weather_rows.extend(dict(phase=phase,**row) for row in rows(normals))
    assert all(row['exact_cost_split'] for row in measured)
    emit(data,'monthly-weather-joint-distribution',weather_rows)
    emit(data,'visible-snowpack-conditionals',maxima)
    emit(data,'cross-month-snowpack-forecast',[r for r in maxima if int(r['month']) in (3,4)])
    emit(data,'forecast-double-count-audit',measured)
    emit(data,'controlled-route-service-level',controlled)
    emit(data,'route-cargo-loss-forecast',[{k:r[k] for k in ('phase','seed','region','date','route_ids',
         'new_net','actual_net','old23_net')} for r in measured])
    emit(data,'river-freeze-forecast-comparison',[{k:r[k] for k in ('phase','seed','region','date','route_ids',
         'currently_blocked','freeze_risk','actual_ice_wait','return_freeze_risk','actual_return_ice_wait')}
         for r in measured])
    metrics=[dict(phase=phase,**row) for phase in phases
             for row in rows(data/f'climate-forecast-{phase}.csv')]
    emit(data,'route-eta-error-comparison',[r for r in metrics if r['metric']=='days'])
    emit(data,'route-ration-error-comparison',[r for r in metrics if r['metric'] in ('rations','return')])


def scenario_preparation(cases,pairs):
    def index(row):
        return tuple(row[k] for k in ('wave','scenario','seed','strategy'))
    by_id={(index(case.identity),case.identity['group']):case for case in cases}
    for row in pairs:
        if (row['reference'],row['candidate'])!=('F3','F4'):
            continue
        a,b=(by_id[index(row),group] for group in ('F3','F4'))
        yield dict(**{key:row[key] for key in ('wave','scenario','seed','strategy','months')},
            baseline_requests=len(a.preparation),candidate_requests=len(b.preparation),
            market_grain=sum(p['grain'] for p in b.preparation if p['method']=='market'),
            dispatched_grain=sum(p['grain'] for p in b.preparation if p['method']!='market'),
            change_in_city_turns=row['shortage_city_turns']-row['reference_shortage_city_turns'],
            change_in_grain_gap=row['grain_gap']-row['reference_grain_gap'])


def matched_agricultural_ledgers(cases):
    cohorts=defaultdict(dict)
    for case in cases:
        same=tuple(case.identity[field] for field in ('wave','scenario','seed','strategy'))
        cohorts[same][case.identity['group']]=case
    checks=[]
    for (wave,scene,seed,strategy),groups in sorted(cohorts.items()):
        for left,right in (('F1','F3'),('F2','F4'),('F3','F4')):
            if not {left,right}<=groups.keys():
                continue
            a,b=({(row['year'],row['region']):row for row in groups[group].climate} for group in (left,right))
            shared=sorted(a.keys()&b.keys())
            assert all(a[key]==b[key] for key in shared),(wave,scene,seed,strategy,left,right)
            checks.append(dict(wave=wave,scenario=scene,seed=seed,strategy=strategy,
                control=left,candidate=right,compared=len(shared),exclusive_to_control=len(a)-len(shared),
                exclusive_to_candidate=len(b)-len(shared),agriculture_sha256=digest([a[key] for key in shared])))
    return checks


def history_index(historical):
    references='https://github.com/kai987/Three-Kingdoms2-King-mainland/tree/codex/winter-agriculture-v23-validation-archives/validation/v23/summary'
    by_id={ident:row for row in historical['historical_artifacts'] if row['outcome']=='replayed'
           for ident in row['present']}
    return [dict(convoy=ident,kind='replayed' if ident in by_id else 'prior_evidence',
                 artifact=by_id.get(ident,{}).get('file'),sha256=by_id.get(ident,{}).get('sha256'),
                 checkpoints=len(by_id.get(ident,{}).get('trace',())) if ident in by_id else None,
                 reference=references) for ident in sorted(historical['historic_replayed']+historical['historic_quoted'])]


def tech_gates(source):
    gates=published_gates(source)
    for name,gate in gates.items():
        log=(source/gate['log']).read_text(encoding='utf-8')
        numbers={}
        for label,pattern in (
                ('tests',r'Ran (\d+) tests?|(?:^|\n)ℹ tests (\d+)|Rust/WASM parity: (\d+)'),
                ('passed',r'(\d+) passed|(?:^|\n)ℹ pass (\d+)'),
                ('skipped',r'skipped=(\d+)|(\d+) skipped'),
                ('commands',r'real requests,|"requests":(\d+)')):
            match=re.search(pattern,log)
            if match:
                found=next((value for value in match.groups() if value),None)
                if found:
                    numbers[label]=int(found)
        if name=='full-browser-final':
            tests=source/'checks/full-browser-results.json'
            if tests.is_file():
                numbers.update(json.loads(tests.read_text())['stats'])
        gate.update(results=numbers)
    return gates


def confirmed_detail(source,cases):
    primary={case.identity['group']:case for case in cases if case.identity['wave']=='long'
             and case.identity['scenario']=='208-10' and case.identity['strategy']==211}
    result={}
    for artifact in sorted((source/'detailed/campaigns/long').glob('*/208-10-2026-211/run-v231.json')):
        run=json.loads(artifact.read_text())
        group=run['group']
        if group not in primary or run['outcome']!='complete':
            continue
        base=primary[group]
        generated=artifact.parent
        checked={}
        for file in ('monthly.csv','factions.csv','cities.csv'):
            origin,actual=((folder/'208-10'/file).read_bytes() for folder in (base.path,generated))
            assert origin==actual,(file,group)
            checked[file]=sha256(actual)

        def terminal(folder):
            with gzip.open(folder/'terminal-save.json.gz','rt',encoding='utf-8') as stream:
                data=json.load(stream)
            return verified_save_content(data.get('save',data))['state']

        before,after=map(terminal,(base.path,generated))
        assert before==after,group
        transfers=[]
        preparation=[]
        delivered={}
        city_food={}
        for event in events(generated/'events.jsonl.gz'):
            if event['kind']=='convoy_transaction':
                transfers.append(event)
                if event['event']=='transport_arrived':
                    delivered[event['convoy']]=event
            elif event['kind']=='agriculture_preparation_detail':
                preparation.append(event)
            elif event['kind']=='city_rations':
                city_food[event['city'],event['turn']]=event['missing']
        outcomes={(frame['year'],frame['region']):frame for frame in base.climate}
        for action in preparation:
            receipt=delivered.get(action['convoy'])
            outcome=outcomes.get((action['year'],action['region']),{})
            action.update(actual_receipt_turn=receipt['turn'] if receipt else None,
                actual_receipt_grain=receipt['grain'] if receipt else None,
                finalized_agriculture_status=outcome.get('agriculture_status'),
                finalized_agriculture_multiplier=outcome.get('agriculture_multiplier'),
                post_receipt_missing_known_window=None)
            if receipt:
                window=[city_food.get((action['city'],turn)) for turn in range(receipt['turn']+1,receipt['turn']+10)]
                if None not in window:
                    action['post_receipt_missing_known_window']=sum(window)
        result[group]=dict(proof=dict(domain_sha256=digest(after),rng=after['rng'],macro=checked,
            source=run['source'],detail_observer_sha256=run['detail_observer_sha256']),
            transfers=transfers,preparation=preparation)
    return result


def channel_accounts(cases,details):
    channels={'regional_market':'regional_purchase_received','strategic_granary':'strategic_transport_received',
              'ordinary':'ordinary_transport_received'}
    flows=defaultdict(Counter)
    for group,detail in details.items():
        for row in detail['transfers']:
            if row['posted'] is None:
                continue
            year,month,*_=row['posted']
            account=flows[group,row['city'],row['owner'],year,month]
            if row['event']=='transport_departed':
                account.update(transport_cargo_dispatched=-row['grain'],protected_rations_dispatched=-row['rations'])
            elif row['channel'] in channels:
                account[channels[row['channel']]]+=row['grain']
    for case in cases:
        region_rows=[row for row in case.accounts if row['region']=='southern_basins' and case.identity['wave']=='long']
        city_month=Counter((row['city'],row['owner'],row['year'],row['month']) for row in region_rows)
        group=case.identity['group']
        for values in region_rows:
            row=dict(values)
            key=(row['city'],row['owner'],row['year'],row['month'])
            if group in details and city_month[key]==1 and case.identity['strategy']==211:
                candidate=flows[group,*key]
                for known,specific in (('combined_transport_received',tuple(channels.values())),
                                       ('cargo_and_rations_dispatched',('transport_cargo_dispatched',
                                                                        'protected_rations_dispatched'))):
                    if sum(candidate[field] for field in specific)==row[known]:
                        row.update({field:candidate[field] for field in specific})
            yield dict(**case.identity,**row)


def build(source,older,baseline,output):
    summary=baseline
    data,docs,checks,sources=(output/name for name in ('data','docs','checks','sources'))
    for d in (data,docs,checks,sources):
        d.mkdir(parents=True,exist_ok=True)
    regions={row['city_id']:row['region'] for row in rows(summary/'data/city-climate-audit.csv')}
    inputs=sorted(source.glob('campaigns/*/*/*/run-v231.json'))+sorted(older.glob('campaigns/root/*/*/run-v231.json'))
    cases=[Case(path,regions) for path in inputs if json.loads(path.read_text())['outcome'] in ('complete','natural_end')]
    details=confirmed_detail(source,cases)
    if details:
        to_json(checks/'detailed-ledger-identity.json',{key:row['proof'] for key,row in details.items()})
        emit(data,'channel-transport-actual-ledger',(dict(group=group,**row) for group,case in sorted(details.items())
                                                     for row in case['transfers']))
        emit(data,'agriculture-risk-preparation-detail',(dict(group=group,**row) for group,case in sorted(details.items())
                                                         for row in case['preparation']))
    scores,pairs,alerts=matrix(cases,prior_cases(summary))
    for name,result in (('scenario-scores',scores),('pairwise',pairs),('balance-alerts',alerts),
                        ('long-term-economy-comparison',[r for r in pairs if r['wave']=='long']),
                        ('holdout-comparison',[r for r in pairs if r['wave']=='holdout']),
                        ('convoy-return-safety',[{k:r[k] for k in ('wave','scenario','seed','strategy',
                            'reference','candidate','months','convoy_returned','reference_convoy_returned',
                            'convoy_grain_arrived','reference_convoy_grain_arrived')} for r in pairs]),
                        ('convoy-hunger-comparison',[{k:r[k] for k in (*IDENTITY[0:1],'scenario','seed','strategy',
                            'reference','candidate','months','convoy_hunger_losses','reference_convoy_hunger_losses')} for r in pairs])):
        emit(data,name,result)
    for name,property_name in (('military-grain-request-ledger','requests'),('military-grain-receipt-ledger','receipts'),
        ('winter-order-timely-comparison','orders'),('agricultural-year-summary','climate'),
        ('agriculture-risk-preparation-ledger','preparation'),('southern-basin-shortage-root-cause','shortages'),
        ('city-shortage-checkpoints','checkpoints'),('military-planning-evaluations','planning'),
        ('prior-nine-turn-city-shortage-context','shortage_context')):
        emit(data,name,(dict(**case.identity,**row) for case in cases for row in getattr(case,property_name)),IDENTITY)
    emit(data,'winter-grain-timely-comparison',(dict(**case.identity,**{
        key:case.military[key] for key in ('requests','requested_grain','timely_received_grain','late_received_grain',
        'unresolved_grain','covered_by_other_channel','cancelled_due_to_target_change','never_dispatched',
        'no_dispatch_unresolved_grain','timely_at_original_deadline','original_deadline_grain_rate',
        'legacy_unmet_including_cancellations',
        'timely_grain_rate','matured_orders','timely_positive_receipt_orders','late_orders','no_receipt_orders',
        'pending_orders','cancelled_orders','timely_order_rate')}) for case in cases))
    emit(data,'unmet-military-demand',(dict(**case.identity,**row) for case in cases for row in case.requests
                                               if row['unresolved_grain']),IDENTITY)
    emit(data,'regional-grain-flow-account',channel_accounts(cases,details),IDENTITY)
    emit(data,'prior-nine-turn-city-grain-postings',(dict(**case.identity,**row) for case in cases
                                           if case.identity['wave']=='long' for row in case.before),IDENTITY)
    emit(data,'regional-climate-economic-balance',(dict(**case.identity,region=region,months=month,**{
        key:part[key] for key in ('unpaid_city_turns','grain_stock')}) for case in cases
        for (month,region),part in sorted(case.regions.items()) if month in (0,case.month)))
    emit(data,'regional-agriculture-overview',(dict(**case.identity,region=region,year=year,month=month,**part)
        for case in cases for (region,year,month),part in sorted(case.agriculture.items())),IDENTITY)
    preparation=scenario_preparation(cases,pairs)
    emit(data,'agriculture-risk-preparation-ablation',preparation,IDENTITY)
    climate_identity=matched_agricultural_ledgers(cases)
    emit(data,'agricultural-weather-identity',climate_identity,IDENTITY)
    emit(data,'weather-cargo-loss-audit',(dict(**case.identity,old_separate_incident_field=value(case.world[case.month],
        'convoy_weather_grain_loss'),all_route_loss=value(case.world[case.month],'convoy_route_grain_loss'),
        base_route_loss=(case.run['cargo_audit']['route_weather_inclusive']
                         -case.run['cargo_audit']['route_weather_increment']) if case.run['cargo_audit'] else None,
        cargo_remaining=sum(row['cargo_grain'] for row in case.run['terminal']['convoy_loads']),
        rations_remaining=sum(row['escort_bag'] for row in case.run['terminal']['convoy_loads']),
        emergency_refill=next((row['amount'] for row in case.run['warehouse_audit']['categories']
            if row['category']=='convoy_emergency_refill' and row['resource']=='grain'
            and row['direction']=='debit'),0),
        observed_convoy_days=case.cargo['measured_days'] or None,
        **{key:(case.run['cargo_audit'] or {}).get(key) for key in
            ('route_weather_inclusive','route_weather_increment','incident_weather')},**{
        key:(case.cargo[key] if case.cargo and (not case.cargo['incomplete_component_days'] or key not in
             ('base_rations','weather_extra_rations')) else None)
        for key in ('paid_rations','base_rations','weather_extra_rations','ice_wait_rations','return_rations','cargo_rations')})
        for case in cases))
    emit(data,'performance-comparison',(dict(**case.identity,**case.run['performance']) for case in cases))
    for phase in ('calibrate','holdout'):
        climate=older/'normals'/phase
        routes=source/'routes'/phase
        if not (routes/'fixed-route-manifest.json').is_file():
            routes=older/'routes'/phase
        for origin,name in ((climate/'monthly-weather-joint-distribution.csv',f'{phase}-monthly-weather-joint-distribution.csv'),
                            (routes/'cross-month-route-prediction.csv',f'{phase}-cross-month-route-prediction.csv'),
                            (routes/'route-forecast-errors.csv',f'climate-forecast-{phase}.csv'),
                            (climate/'normals-manifest.json',f'{phase}-normals-manifest.json'),
                            (routes/'fixed-route-manifest.json',f'{phase}-fixed-route-manifest.json')):
            shutil.copy2(origin,data/name)
    phases=['calibrate','holdout']
    adverse=source/'routes/adverse'
    if (adverse/'fixed-route-manifest.json').is_file():
        phases.append('adverse')
        for original,label in (('cross-month-route-prediction.csv','adverse-cross-month-route-prediction.csv'),
                               ('fixed-route-manifest.json','adverse-fixed-route-manifest.json'),
                               ('route-forecast-errors.csv','climate-forecast-adverse.csv')):
            shutil.copy2(adverse/original,data/label)
    emit(data,'cross-month-route-prediction',(dict(phase=phase,**row)
         for phase in phases for row in rows(data/f'{phase}-cross-month-route-prediction.csv')))
    fixed_route_exports(data,phases)
    for folder, filename in (('replays','city-shortage-checkpoint-replay.csv'),
                             ('performance','forecast-performance-profile.csv')):
        proof=source/folder/filename
        if proof.is_file():
            shutil.copy2(proof,data/filename)
    gates=tech_gates(source)
    to_json(checks/'technical-gates.json',gates)
    for dirname,filename in (('compatibility','compatibility.json'),('checks','baseline-identity.json'),
            ('checks','observer-equivalence.json'),('performance','forecast-performance.json'),
            ('replays','shortage-replay-detail.json'),('checks','historical-convoy-2.json'),
            ('checks','browser-test-source.json')):
        proof=source/dirname/filename
        if proof.is_file():
            shutil.copy2(proof,checks/filename)
    if (checks/'compatibility.json').is_file():
        historical=json.loads((checks/'compatibility.json').read_text())
        emit(data,'historical-transport-replay-index',history_index(historical))
    photos=checks/'screenshots'
    photos.mkdir(exist_ok=True)
    for shot in sorted((source/'technical/browser-v231').glob('*.png')):
        shutil.copy2(shot,photos/shot.name)
    for doc in (TOOL_ROOT/'docs/winter-agriculture-v231').glob('*.md'):
        shutil.copy2(doc,docs/doc.name)
    for file in ('v231_observe.py','v231_normals.py','v231_routes.py','v231_report.py','v231_replay.py',
                 'v231_compat.py','v231_package.py','v231_ledger.py','v231_verify.py'):
        p=TOOL_ROOT/'tools/economy-balance'/file
        if p.is_file():
            shutil.copy2(p,sources/p.name)
    for name in ('winter_forecast.py','winter_forecast_normals.py'):
        shutil.copy2(ROOT/'source/remake'/name,sources/name)
    to_json(data/'simulation-manifest.json',dict(source=(source/'frozen-source.txt').read_text().strip(),
        runs=[{key:case.run.get(key) for key in (*IDENTITY,'source','options','catalog_sha256','map_sha256',
            'runner_sha256','months','completed_turns','outcome','output','backend','rule_versions',
            'parameters','worktree_diff_sha256','warehouse_audit')} for case in cases],
        prior_summary_commit='0cffc207e229f63767ecc4347ad2179f761615a4'))
    result=render(docs,data,checks,cases,pairs,alerts,gates)
    to_json(data/'report-status.json',result)
    members=sorted(path for path in output.rglob('*') if path.is_file() and path.name not in ('SHA256SUMS.txt','validation-manifest.json'))
    to_json(data/'validation-manifest.json',dict(files=[dict(path=str(path.relative_to(output)),bytes=path.stat().st_size,
        sha256=sha256(path.read_bytes())) for path in members]))
    members.append(data/'validation-manifest.json')
    (output/'SHA256SUMS.txt').write_text(''.join(f'{sha256(path.read_bytes())}  {path.relative_to(output)}\n'
        for path in sorted(members)),encoding='utf-8')
    return result


def md(folder,name,title,body):
    (folder/(name+'.md')).write_text('# '+title+'\n\n'+body.strip()+'\n',encoding='utf-8')


def table(names,body):
    def cells(items):
        return '| '+' | '.join(str(item).replace('|','\\|') for item in items)+' |'
    return '\n'.join([cells(names),cells(['---']*len(names)),*(cells(row) for row in body)])


def integer(number):
    return '未采集' if number is None else f'{number:,}'


def percent(number):
    return '—' if number is None else f'{number:.1f}%'


def find_pair(pairs,wave,scene,seed,strategy,reference='F2',candidate='F4'):
    return next((r for r in pairs if (r['wave'],r['scenario'],r['seed'],r['strategy'],r['reference'],r['candidate'])
                 ==(wave,scene,seed,strategy,reference,candidate)),None)


def forecast_report(docs,data):
    results={(r['model'],r['metric']):r for r in rows(data/'climate-forecast-holdout.csv')}
    routes=[r for r in rows(data/'visible-snowpack-conditionals.csv') if r['phase']=='holdout']
    winter=[r for r in rows(data/'river-freeze-forecast-comparison.csv') if r['phase']=='holdout']
    metrics=[]
    improvements={}
    for key,label in (('days','抵达日数'),('rations','去程口粮权重'),('return','返程口粮权重'),('net','到货粮')):
        old,new=(results[model,key] for model in ('old23','new'))
        a,b=(value(record,'absolute_error') for record in (old,new))
        improvements[key]=100*(a-b)/a
        metrics.append((label,new['samples'],f'{a:,.2f}',f'{b:,.2f}',percent(improvements[key]),
                        percent(100*value(old,'underestimates')),percent(100*value(new,'underestimates'))))
    snow=[r for r in routes if r['region']=='liaodong' and r['month']=='4' and int(r['current_depth'])]
    ice_delays=[r for r in winter if value(r,'actual_ice_wait')]
    missed_ice=sum(not value(r,'freeze_risk') for r in ice_delays)
    conservative=sum(r['deadline_covered']=='true' for r in routes)
    controlled=defaultdict(Counter)
    for r in rows(data/'controlled-route-service-level.csv'):
        if r['phase']=='holdout':
            controlled[r['model']].update(sample=1, false_rejections=r['false_rejection']=='true',
                false_acceptances=r['false_acceptance']=='true')
    adverse=[r for r in rows(data/'cross-month-route-prediction.csv') if r['phase']=='adverse']
    severe=[r for r in adverse if value(r,'actual_ice_wait_days')]
    flooded=sum(value(r,'predicted_ice_wait_days')>0 for r in severe)
    april=[r for r in adverse if r['region']=='liaodong' and r['month']=='4'
           and json.loads(r['visible'])['liaodong']['depth']>0]
    hard_wait=[r for r in severe if r['currently_blocked']!='null']
    a15=next((value(r,'absolute_error') for r in rows(data/'route-eta-error-comparison.csv')
              if r['phase']=='adverse' and r['model']=='old23'),None)
    b15=next((value(r,'absolute_error') for r in rows(data/'route-eta-error-comparison.csv')
              if r['phase']=='adverse' and r['model']=='new'),None)
    adverse_note=(f'独立严寒特意采样包含 {len(adverse)} 条路线，涵盖金城往朔方单向河路和辽东跨季陆路。'
        f'旧版至新版 ETA MAE 为 {a15:.2f} → {b15:.2f} 天。'
        f'实际去程冰封等待 {len(severe)} 例，预报识别 {flooded} 例，其中 {len(hard_wait)} 例出发时已冰封。'
        f'另有 {len(april)} 条辽东 4 月出发路线观测到积雪。此批样本单列。\n\n' if adverse else '')
    md(docs,'forecast-calibration-results','固定路线预测验证',(
        f'独立保留样本 {len(routes)} 条。每条路线配对复用同一地理路径、实际天气和出发检查点，由实际逐日行程内核复放。\n\n'
        +table(('指标','样本','V2.3 MAE','V2.3.1 MAE','改善','V2.3 低估率','V2.3.1 低估率'),metrics)
        +f'\n\n保守 ETA 覆盖实际抵达日或更晚的样本为 {conservative}/{len(routes)}。'
        f'观察到实际去程冰封等待 {len(ice_delays)} 例，其中零预计风险 {missed_ice} 例。'
        f'辽东 4 月有积雪的保留出发样本为 {len(snow)}。近端积雪与中期季节正常值分别取数。\n\n'
        '所有固定路线的时间和口粮分项均精确加总。去程和回程实际跟随同一组物理路线，返点按实际去程到达时点计算。'
        '返程预测从预计去程抵达时开始。口粮权重为路线内核计量单位。'
        f'对当前可进入的固定保留路线另设置统一模拟门槛（平时日数加 10 天、平时口粮权重的 125%），'
        f'旧 V2.3 误拒 {controlled["old23"]["false_rejections"]} 例，V2.3.1 误拒 '
        f'{controlled["new"]["false_rejections"]} 例，均使用同一实际成本核验。该对照采用受控预算，'
        '实际 AI 另受城市库存、兵员、路线资格和其他命令限制。\n\n'+adverse_note+
        '[逐路线源数据](../data/holdout-cross-month-route-prediction.csv) · '
        '[成本拆分核对](../data/forecast-double-count-audit.csv) · '
        '[冰封对照](../data/river-freeze-forecast-comparison.csv)'))
    return dict(samples=len(routes),improvement_percent=improvements,item_metrics=metrics,
                actual_ice_wait_cases=len(ice_delays),missed_ice_cases=missed_ice,conservative_coverage=conservative,
                adverse_samples=len(adverse),adverse_waits=len(severe),adverse_waits_predicted=flooded,
                adverse_currently_blocked=len(hard_wait),april_snow_samples=len(april),
                adverse_eta_mae_before=a15,adverse_eta_mae_after=b15)


def military_report(docs,cases):
    cohorts=defaultdict(Counter)
    fields=('requests','requested_grain','timely_received_grain','late_received_grain','unresolved_grain',
            'timely_at_original_deadline','no_dispatch_unresolved_grain','matured_orders','timely_positive_receipt_orders')
    for case in cases:
        if case.identity['wave']!='smoke':
            cohorts[case.identity['wave'],case.identity['group']].update({key:case.military[key] for key in fields})
    for metric in cohorts.values():
        metric['quantity_rate']=percentage(metric['timely_received_grain'],metric['requested_grain'])
        metric['order_rate']=percentage(metric['timely_positive_receipt_orders'],metric['matured_orders'])
    md(docs,'military-supply-results','军事补给统计',(
        table(('批次','组','需求数','请求粮','及时实收粮','数量及时率','未满足粮','未发运未满足粮',
               '及时运队／已到期','运队及时率'),
            [(wave,group,integer(row['requests']),integer(row['requested_grain']),integer(row['timely_received_grain']),
              percent(row['quantity_rate']),integer(row['unresolved_grain']),integer(row['no_dispatch_unresolved_grain']),
              f"{row['timely_positive_receipt_orders']}/{row['matured_orders']}",percent(row['order_rate']))
             for (wave,group),row in sorted(cohorts.items())])
        +'\n\n每批只汇总批内的实际新采数据。同一种子跨观战批次重复出现。'
        '冬季为 11 月至翌年 3 月。数量表按冬季需求建档，运队表按冬季发运建档，回执另有实际收到日期。'
        '改变运单 ETA 不影响首次承诺期限。原申请时点口径单列。小样本保留分子和分母。'
        '完全无需求的比率为空。其他渠道计入实收子项。未满足粮含期末仍未解决的余额，排除目标变化取消的余额。\n\n'
        '[请求台账](../data/military-grain-request-ledger.csv) · [实际回执](../data/military-grain-receipt-ledger.csv) · '
        '[独立运单](../data/winter-order-timely-comparison.csv) · [计划观察](../data/military-planning-evaluations.csv)'))
    return {f'{wave}/{group}':dict(row) for (wave,group),row in sorted(cohorts.items())}


def southern_report(docs,data,cases):
    subset={case.identity['group']:case for case in cases if case.identity['wave']=='long' and
            case.identity['scenario']=='208-10' and case.identity['strategy']==211}
    if 'F2' not in subset:
        return None
    base=subset['F2']
    terminal=base.world[base.month]
    by_gap=sorted(base.shortages,key=lambda row:row['gap_rank'])[:20]
    by_frequency=sorted(base.shortages,key=lambda row:row['frequency_rank'])[:20]
    all_sources=base.run['cargo_audit']
    leading=sorted(by_gap,key=lambda row:-row['longest_streak'])
    replay_file=data/'city-shortage-checkpoint-replay.csv'
    replays=rows(replay_file) if replay_file.is_file() else []
    replay_cases=defaultdict(dict)
    for row in replays:
        replay_cases[row['city']][row['group']]=row
    probes=[]
    for key,groups in replay_cases.items():
        old=groups['F2']
        probes.append((key,'-'.join(map(str,json.loads(old['opening_date']))),old['owner'],
                       old['other_faction_stock'],old['legal_sources'],old['minimum_eta'],
                       old['missing'],groups['F3']['missing'],groups['F4']['missing']))
    def city_rank(data):
        return table(('城池 ID','缺粮城旬','累计缺粮','最长连续','首次严重月份','首次严重时所属'),
            [(r['city'],r['shortage_city_turns'],r['grain_gap'],r['longest_streak'],
              f"{r['first_severe_year']}-{r['first_severe_month']:02d}" if r['first_severe_year'] else '—',
              r['owner_at_first_severe'] or '—') for r in data])
    components=defaultdict(Counter)
    for case in subset.values():
        for (region,year,month),postings in case.agriculture.items():
            if region=='southern_basins':
                components[case.identity['group']].update(postings)
    rates=('regular_production','market_purchase','combined_transport_received','military_and_civil_payroll',
           'army_dispatch_grain','cargo_and_rations_dispatched','disaster_grain_loss')
    move_table=[]
    for group,case in sorted(subset.items()):
        ledger=Counter()
        for row in case.accounts:
            if row['region']=='southern_basins':
                ledger.update({key:row[key] for key in rates})
        move_table.append((group,case.regions[case.month,'southern_basins']['unpaid_city_turns'],
                           integer(value(case.world[case.month],'rations_missing')),
                           integer(components[group]['adjustment']),*(integer(ledger[key]) for key in rates)))
    ref=value(terminal,'rations_missing')
    same_replay=sum(len({group['missing'] for group in groups.values()})==1 for groups in replay_cases.values())
    classified=(data/'channel-transport-actual-ledger.csv').is_file()
    split_note=('赤壁 F2 和 F4 另采集运队的实际渠道、出粮、押运备粮及入账。逐月汇总只在细分结果与仓库实账一致时列出分项。'
                if classified else '原版仓库总运输可核实。渠道标签依赖补采的运输事件。')
    channels=('regional_purchase_received','strategic_transport_received','ordinary_transport_received')
    regional=defaultdict(Counter)
    if classified:
        for row in rows(data/'regional-grain-flow-account.csv'):
            if all(value(row,field) is not None for field in channels):
                regional[row['group']].update({field:value(row,field) for field in channels})
    channel_table=(
        '\n\n'+table(('组','区域市场运达粮','战略粮仓运达粮','普通运达粮','已分账合计'),
                    [(group,*(integer(totals[field]) for field in channels),integer(sum(totals.values())))
                     for group,totals in sorted(regional.items())])
        if regional else '')
    md(docs,'southern-basin-shortage-root-cause','赤壁 211 南方盆地缺粮溯源',(
        f'F2 实际复跑 {base.month} 个月，天下累计缺粮 {integer(ref)}，南方盆地缺粮 '
        f'{base.regions[base.month,"southern_basins"]["unpaid_city_turns"]:,} 城旬。三张逐月报表、期末完整状态和随机数与 V2.3 基准一致。'
        f'南方盆地直接农业调整为 {integer(components["F2"]["adjustment"])} 粮。'
        '以下粮账取自城市资源写入，每段库存满足期初加净过账等于期末。开局、接收与支出均保留；净变化不用于推断运输营运额。\n\n'
        +table(('组','盆地缺粮城旬','天下缺粮粮','直接农业调整','例行产粮写入','市场买粮','运输入城',
                '薪饷','出征','装车总粮','灾损'),move_table)
        +'\n\n## 按累计缺粮排名\n\n'+city_rank(by_gap)
        +'\n\n## 按缺粮城旬排名\n\n'+city_rank(by_frequency)
        +(f'\n\n最长连续案例为 {leading[0]["city"]}（{leading[0]["longest_streak"]} 旬）。' if leading else '')
        +'\n\n首次严重缺粮定义为当旬实缺达到应耗粮的四分之一。'
        '前九旬另收录逐笔粮账、实付和应付、所属、驻军与市场库存。'
        '经查，旧天气货损列计独立事件损失；地面雪况带来的货损写入实际路线扣粮。'
        f'本次从同一笔粮账分出 {all_sources["route_weather_increment"]:,} 点净天气附加货损。\n\n'
        +table(('检查点','开局日期','所属','同势力他城粮','合格来源','最短预计日数','F2 九旬缺口',
                'F3 九旬缺口','F4 九旬缺口'),probes)
        +'\n\n同一检查点仅切换预测和农业风险准备，从相同粮账续跑。'
        f'{len(replay_cases)} 个检查点中有 {same_replay} 个在三组的九旬缺口相同。'
        '巴东的最快合法报价为 47 天，起始检查点已有严重缺粮。建安的同势力他城有余额，但该检查点无合格调粮来源。'
        '已记录的限制包括来源安全储备、合格押运者、发运上限及实际路线。'
        '市场成交和运输入城均按实际事件记账。长期战局分叉时，战争、易主、市场及征召会同时改变粮源、粮耗和路线。'
        +split_note+channel_table+'\n\n'
        '[逐月粮账](../data/regional-grain-flow-account.csv) · [首次重缺前九旬](../data/prior-nine-turn-city-grain-postings.csv) · '
        '[当旬状态](../data/prior-nine-turn-city-shortage-context.csv) · [原始基线身份](../checks/baseline-identity.json)'))
    return dict(original_gap=ref,original_southern_turns=base.regions[base.month,'southern_basins']['unpaid_city_turns'],
        weather_cargo_increment=all_sources['route_weather_increment'],longest=leading[0] if leading else None,
        top_shortages=by_gap[:5],fixed_replay_cases=len(replay_cases),same_gap_replays=same_replay,comparisons=move_table)


def supporting_reports(docs,data,checks):
    reference=checks/'compatibility.json'
    witness=checks/'historical-convoy-2.json'
    if reference.is_file() and witness.is_file():
        q=json.loads(reference.read_text())
        s=json.loads(witness.read_text())['series']
        last=s[-1]
        accounted=(f'该存档读入时这支运队载粮 {s[0]["cargo"]["grain"]:,}，押运兵 {s[0]["escort_troops"]:,}。'
                   f'第 {last["turn"]} 旬仍有武将、{last["escort_troops"]:,} 兵和 '
                   f'{last["cargo"]["gold"]:,} 金，属于真实待返任务。' if last['present']
                   else f'第 {last["turn"]} 旬已通过当时状态机离开在途名册。')
        md(docs,'historical-transport-review','历史运队和存档兼容性',(
            f'重放 {", ".join(map(str,q["historic_replayed"]))}。历史档案引用 '
            f'{", ".join(map(str,q["historic_quoted"]))}。'
            '历史快照使用原始文件及原有规则版本。原 0、22、221、23 的回放保留状态及随机数。\n\n'
            +accounted+' 另见 V2.3 赤壁二十年原版观察器重跑。\n\n'
            '[原始广陵检查点追踪](../checks/historical-convoy-2.json) · [旧存档跨后端验证](../checks/compatibility.json)'))
    performance=data/'forecast-performance-profile.csv'
    if performance.is_file():
        records=rows(performance)
        md(docs,'performance-results','同一状态的预报性能',(
            '从四份真实检查点各重复三次。每次从固定存档开始并清空预报路线缓存，观测开关各独立测试。'
            '输出全旬 CPU 与墙钟分位数、新预报调用、缓存命中、搜路次数、候选数和进程峰值内存。'
            '开关观察的同一策略核对最终游戏状态与随机数。\n\n'
            +table(('检查点','剧本','观察','组','CPU P50 秒','CPU P95 秒','预报调用','缓存命中'),
                    [(r['checkpoint'],r['scene'],r['observation'],r['group'],
                      f"{value(r,'median_cpu'):.3f}",f"{value(r,'p95_cpu'):.3f}",r['estimate_calls'],r['cache_hits'])
                     for r in records])
            +'\n\n[逐指标](../data/forecast-performance-profile.csv) · [重复数据](../checks/forecast-performance.json)'))


def answer_report(docs,forecast,southern,military,pairs,technical,decision):
    red=find_pair(pairs,'long','208-10',2026,211)
    yellow=find_pair(pairs,'long','184-02',2026,211)
    reviewers=[find_pair(pairs,'holdout',scene,seed,s) for scene,seed,s in (('184-02',2043,211),('208-10',2044,212))]
    base=military.get('long/F2',{})
    target=military.get('long/F4',{})
    if not southern:
        return
    stats=forecast['item_metrics'][0]
    red_shortage=integer(red['grain_gap']) if red else '待验'
    changes=[
        '相同种子和天气选项下，实际降雪、积雪、融雪及河冰逐日对照一致。',
        '同种子各组的共有区域年度农业结算一致，具体产量还随城池状态而变。',
        f'辽东四月保留专测有 {forecast["april_snow_samples"]} 条路线存在余雪。',
        f'独立主样本 ETA 的平均绝对误差从 {stats[2]} 天降到 {stats[3]} 天。',
        '每段按前段预测抵达日取气候分箱，返程从预计去程抵达日开始。',
        '已核对固定路线的时间和口粮分项逐条精确加总。实际费用沿原日结算。',
        f'严寒样本实际冰封等待 {forecast["adverse_waits"]} 例，预测捕捉 {forecast["adverse_waits_predicted"]} 例。'
        '当前封冻由实际冰情掌管。',
        f'已补采二十年 F2 的冬季粮量及时率 {percent(base.get("quantity_rate"))}。'
        f'F4 三局合计的同口径及时率 {percent(target.get("quantity_rate"))}。分组及每局分母见军粮报告。',
        f'已补采二十年 F2 的运单及时率 {percent(base.get("order_rate"))}，'
        f'F4 三局合计为 {percent(target.get("order_rate"))}。两组覆盖范围见军粮报告。',
        f'已补采二十年 F2 的冬季未满足军粮 {integer(base.get("unresolved_grain"))}，'
        f'F4 三局合计 {integer(target.get("unresolved_grain"))}。',
        f'旧独立天气损耗列为零。真实路线损耗含 {southern["weather_cargo_increment"]:,} 点雪况附加扣粮。',
        '原版按累计缺粮排序为巴东、鄱阳、零陵、庐陵、武陵居前。建安按缺粮城旬排首位。',
        '原版早期严重短缺集中在 210 年江夏和庐陵，其次为 213 年巴东及 214 年宜都。',
        '原版南方盆地累计直接农业调整为 0，仓账表保留实际生产支出。',
        f'同气候的 240 个月配对显示南方盆地 {southern["original_southern_turns"]:,} 城旬降为 '
        f'{next((r[1] for r in southern["comparisons"] if r[0]=="F4"),"待验")} 城旬。'
        f'{southern["same_gap_replays"]} 个真实短期配对的后续缺口相同。',
        '战局变化同时影响兵力、消费、战争次数和物资重分配。逐城报告记录出征、灾害、市场及调粮写入。',
        '农业备粮通过 F3/F4 与固定状态对照。已记录实际准备，尚未证明其独立降低缺粮。',
        '市场直接成交可短期补货，运输和战略粮仓支持跨城供给。核对逐城收货和来源资格。',
        f'赤壁 211 运队饥损从 {integer(red["reference_convoy_hunger_losses"] if red else None)} 降到 '
        f'{integer(red["convoy_hunger_losses"] if red else None)}。',
        f'黄巾 211 二十年缺粮城旬从 {integer(yellow["reference_shortage_city_turns"] if yellow else None)} '
        f'降到 {integer(yellow["shortage_city_turns"] if yellow else None)}。',
        f'赤壁 211 累计缺口从 {southern["original_gap"]:,} 变为 {red_shortage}，目标为低于 498,473。',
        '两个独立保留种子有一升一降。' if all(reviewers) else '独立保留种子的最终验收有待齐备。',
        '区域差异见逐区库存和缺口。全局结果与战线转移有关，正式准入仍保留警戒。',
        '旧版状态、存档与跨后端验证已通过。' if technical else '兼容性及其他技术结果见门槛清单。',
        decision+'。',
    ]
    md(docs,'acceptance-answers','任务书验收问题',('\n'.join(f'{i}. {answer}'
        for i,answer in enumerate(changes,1))+'\n\n[长期平衡](long-term-balance-results.md) · '
        '[赤壁溯源](southern-basin-shortage-root-cause.md) · [军粮统计](military-supply-results.md) · '
        '[固定路线](forecast-calibration-results.md) · [技术门槛](validation-results.md)'))


def render(docs,data,checks,cases,pairs,alerts,gates):
    frozen=json.loads((data/'simulation-manifest.json').read_text())['source']
    requested=[row for wave in ('quick','five','holdout','long') for row in expected_cases(wave,frozen)]
    done={tuple(case.identity[k] for k in IDENTITY):case for case in cases}
    missing=[]
    for row in requested:
        found=done.get(tuple(row[k] for k in IDENTITY))
        if not found or found.run['months']!=row['months']:
            missing.append({key:row[key] for key in (*IDENTITY,'months')})
    required_gates=('native-check','rust-fmt','rust-crate','python-campaign','rust-campaign','node-tests',
        'wasm-parity','web-build','pyodide','full-browser-final','resupply-browser','climate-browser','forecast-browser',
        'save-compatibility','shortage-replay','forecast-performance','prior-features','forecast-specialty')
    absent=[name for name in required_gates if name not in gates]
    failed=[name for name in required_gates if name in gates and gates[name]['exit_code']]
    audited=sum(case.run['warehouse_audit']['city_resource_mismatches'] for case in cases)
    linked=('compatibility','baseline-identity','observer-equivalence','forecast-performance','shortage-replay-detail',
            'detailed-ledger-identity','historical-convoy-2')
    absent_proof=[name for name in linked if not (checks/(name+'.json')).is_file()]
    if 'detailed-ledger-identity' not in absent_proof:
        detailed=json.loads((checks/'detailed-ledger-identity.json').read_text())
        if not {'F2','F4'}<=detailed.keys():
            absent_proof.append('detailed-ledger-identity/F2+F4')
    technical_complete=not (absent or failed or absent_proof or audited)
    thresholds=[r for r in alerts if r['alert'] and r['wave'] in ('long','five','holdout')
                and r['candidate']=='F4' and r['reference'] in ('F0','F2')]
    review=[r for r in alerts if r['alert'] and r['wave']=='long' and r['candidate']=='F2' and r['reference']=='F0']
    forecast=forecast_report(docs,data)
    military=military_report(docs,cases)
    southern=southern_report(docs,data,cases)
    climate_rows=rows(data/'agricultural-weather-identity.csv')
    metrics=('shortage_city_turns','grain_gap','convoy_hunger_losses','battles')
    compare=[]
    for row in pairs:
        if row['wave'] in ('long','holdout'):
            compare.append((row['wave'],row['scenario'],row['seed'],row['strategy'],
               row['reference']+' → '+row['candidate'],
               *(integer(row['reference_'+key])+' → '+integer(row[key]) for key in metrics)))
    md(docs,'long-term-balance-results','长期平衡、保留种子与消融',(
        table(('批次','剧本','种子','策略','组','缺粮城旬','累计缺粮','运队饥损','战斗次数'),compare)
        +'\n\n经济警戒条件为缺粮城旬或缺口增加超过 20%、冬季两种及时率各下降超过 5 个百分点、'
        '小势力存续率下降超过 10 个百分点或旬均 CPU 增加超过 30%。'
        '完整 CSV 保留全部分组和阈值。小分母情形可查军粮独立样本。'
        '历年一场全国战局分叉会改变资源战略。性能判断另用同一检查点重复计时。\n\n'
        '[全部配对](../data/pairwise.csv) · [警戒列表](../data/balance-alerts.csv) · '
        '[保留种子](../data/holdout-comparison.csv) · [农业备粮消融](../data/agriculture-risk-preparation-ablation.csv)'))
    md(docs,'validation-results','技术门槛与存档验收',(
        f'冻结运行源码为 `{frozen}`。共完成 {len(requested)-len(missing)}/{len(requested)} 个要求的正式观战。'
        f'城市资源边界不平衡数 {audited}。'
        f'冻结天气对照逐日检查 519 天，真实配对另核对 {sum(int(row["compared"]) for row in climate_rows)} 条'
        '共享年度区域农业结算。\n\n'
        +table(('验证','退出码','实测计数','日志'),[(name,gate['exit_code'],
            ', '.join(f'{key}={val}' for key,val in gate['results'].items()) or '见对应日志',
            gate['log']) for name,gate in sorted(gates.items())])
        +f'\n\n缺少门槛或证据为 {", ".join(absent+absent_proof) or "无"}。失败门槛为 {", ".join(failed) or "无"}。'
        '浏览器首轮在 macOS 同步子进程等待标准输入结束时中断。测试载入临时自动生成的存档文件后重跑完整浏览器套件。'
        '浏览器执行同一冻结游戏源码。旧存档兼容记录、历史运队与跨后端检查点见结构化结果。\n\n'
        '[所有命令](../checks/technical-gates.json) · [存档兼容性](../checks/compatibility.json) · '
        '[历史运队索引](../data/historical-transport-replay-index.csv) · [观察器状态等价](../checks/observer-equivalence.json) · '
        '[同气候分组年度对照](../data/agricultural-weather-identity.csv)'))
    target=find_pair(pairs,'long','208-10',2026,211)
    target_met=bool(target and target['grain_gap']<498_473)
    fixed_passed=all(forecast['improvement_percent'][key]>=15 for key in ('days','rations','return'))
    promoted=not missing and technical_complete and target_met and fixed_passed and not thresholds
    decision='满足本轮候选阈值，仍保持实验开关' if promoted else '保留为默认关闭的实验候选'
    supporting_reports(docs,data,checks)
    answer_report(docs,forecast,southern,military,pairs,technical_complete,decision)
    md(docs,'next-stage-readiness','候选准入',(
        f'{decision}。固定路线三项主要误差的 15% 改善目标{"达到" if fixed_passed else "未达到"}。'
        f'赤壁 211 的累计缺粮目标{"达到" if target_met else "未达到或尚未测齐"}。'
        f'新版对历史基准的正式批次警戒有 {len(thresholds)} 条，含小样本和跨战局计时。'
        f'旧 W4 对旧 221 的二十年历史警戒有 {len(review)} 条。'
        '完整结果保留证据边界。正式新战役默认配置沿用当前规则。\n\n'
        '[长局与独立种子](long-term-balance-results.md) · [警戒线](../data/balance-alerts.csv) · '
        '[技术门槛](validation-results.md)'))
    md(docs.parent,'README','V2.3.1 气候风险预测验收',(
        f'{decision}。\n\n'
        '- [固定路线预测](docs/forecast-calibration-results.md)\n'
        '- [军事补给](docs/military-supply-results.md)\n'
        '- [赤壁缺粮溯源](docs/southern-basin-shortage-root-cause.md)\n'
        '- [长期平衡与保留种子](docs/long-term-balance-results.md)\n'
        '- [技术回归](docs/validation-results.md)\n'
        '- [任务书验收问题](docs/acceptance-answers.md)\n'
        '- [同状态性能](docs/performance-results.md)\n'
        '- [历史运队](docs/historical-transport-review.md)\n'
        '- [候选准入](docs/next-stage-readiness.md)\n'
        '- [数据字典](docs/data-dictionary.md)\n'
        '- [观战清单](data/simulation-manifest.json)\n'
        '- [报告状态](data/report-status.json)\n'
        '- [SHA-256 校验清单](SHA256SUMS.txt)'))
    return dict(source=frozen,decision=decision,default_enabled=False,formal_candidate_thresholds=promoted,
        technical_passed=technical_complete,missing_gates=absent,failed_gates=failed,missing_evidence=absent_proof,
        required_campaign_runs=len(requested),missing_runs=missing,runs=len(cases),warehouse_mismatches=audited,
        shared_agricultural_region_years=sum(int(row['compared']) for row in climate_rows),
        freeze_forecast=forecast,southern=southern,winter_military=military,red_flags=thresholds,
        long_prior_flags=review,chibi_gap_below_498473=target_met,official_enablement=False)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    for name in ('source','older','baseline','output'):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.source,args.older,args.baseline,args.output),ensure_ascii=False))
