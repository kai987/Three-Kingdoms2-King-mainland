"""Summarize verified observer outputs and package the reproducible V2.2 evidence."""
import argparse
from collections import Counter, defaultdict
import csv
from hashlib import file_digest
from itertools import product
import json
from pathlib import Path
from statistics import fmean, median
from zipfile import ZIP_DEFLATED, ZipFile

from common import TOOL_ROOT, to_csv, to_json
from observe import SCENARIOS
from remake.climate_regions import REGIONS
from v22_experiments import H, PRIORITY, W

SCHEMA='tk2-weather-v22-validation-v1'
CUMULATIVE=('unpaid_city_turns','rations_missing','battles','battle_troops_lost','ai_sorties',
            'march_days','convoy_days','march_rations','convoy_rations','march_hunger_losses',
            'convoy_hunger_losses','convoy_dispatched','convoy_arrived','convoy_failed','convoy_late_arrivals',
            'convoy_route_grain_loss','convoy_weather_grain_loss','grain_bought','emergency_grain_bought')
STOCKS=('grain_stock','gold_stock','market_stock','monthly_regular_grain','monthly_fixed_grain',
        'active_troops','reserves','population')
NORTH=frozenset(('liaodong','northern_frontier','northwest','qinling_highlands','north_china','central_plains'))
HORIZONS={'stages':12,'matrix':60,'long':240,'holdout':60}


def entries(file):
    if file.is_file():
        with file.open(encoding='utf-8',newline='') as handle:
            yield from csv.DictReader(handle)


def sha(path):
    with path.open('rb') as handle:
        return file_digest(handle,'sha256').hexdigest()


def integer(row,name):
    value=row.get(name)
    return int(value) if value not in (None,'','null','not_applicable','not_collected') else None


def ident(wave,run):
    return dict(wave=wave,group=run['group'],scenario=run['scenario'],seed=run['seed'],
                requested_months=run['requested_months'],full_months=run['full_months'],run_status=run['outcome'])


def tick_month(run, tick):
    return ((run['start_date'][1]-1)*30+max(0,tick-1))%360//30+1


def demand_metrics(directory,run):
    sums=Counter()
    winter=Counter()
    for row in entries(directory/'supply-episodes.csv'):
        values=dict(requests=1,required=integer(row,'original_required_grain')+integer(row,'additional_required_grain'),
                    timely=integer(row,'timely_delivered_grain'),late=integer(row,'late_delivered_grain'),
                    unmet=integer(row,'remaining_unmet_grain'))
        sums.update(values)
        if season(tick_month(run,int(row['first_request_time'])))=='winter':
            winter.update(values)
    result={}
    for prefix,bucket in (('army_supply_',sums),('winter_army_supply_',winter)):
        result.update((prefix+field,bucket[field]) for field in ('requests','required','timely','late','unmet'))
        result[prefix+'timely_percent']=round(100*bucket['timely']/bucket['required'],4) if bucket['required'] else None
    return result


def faction_survival(directory):
    frames=list(entries(directory/'factions.csv'))
    ends=max((int(row['elapsed_turns']) for row in frames),default=0)
    start={row['faction'] for row in frames if row['elapsed_turns']=='0' and row['faction']!='neutral'
           and 0<int(row['cities'])<=3}
    last={row['faction'] for row in frames if int(row['elapsed_turns'])==ends and int(row['cities'])>0}
    n=len(start&last)
    return dict(small_factions_opening=len(start),small_factions_surviving=n,
                small_faction_survival_percent=round(n*100/len(start),4) if start else None)


def score(wave,run,directory):
    frames=list(entries(directory/'monthly.csv'))
    result=ident(wave,run)
    finish=frames[-1]
    result.update({key:integer(finish,key) for key in (*CUMULATIVE,*STOCKS)})
    denominator=int(finish['owned_city_turns'])
    result['food_shortages_per_1000_owned_city_turns']=round(result['unpaid_city_turns']*1000/denominator,5) if denominator else None
    cities=defaultdict(list)
    for row in entries(directory/'cities.csv'):
        cities[int(row['elapsed_turns'])].append(row)
    result.update(oversized_garrison_final=sum(integer(row,'stationed_troops_above_sustainable') or 0
                  for row in cities[int(finish['elapsed_turns'])]),
                  max_city_food_shortage_streak=max((int(row['max_food_shortage_streak'])
                      for rows in cities.values() for row in rows),default=0),
                  blocked_faction_turns=sum(row['qualifies']=='true' and int(row['no_action_streak'])>=3
                      for row in entries(directory/'action-capacity.csv')))
    result.update(demand_metrics(directory,run),**faction_survival(directory))
    totals=run['weather_totals']
    applicable=run['stage']>=2
    for name in ('people_days','extra_grain','delay_work_units','blocked_days','extra_cargo'):
        enabled=applicable if name not in ('blocked_days','extra_cargo') else run['stage']>=(4 if name=='blocked_days' else 3)
        result[name]=totals.get(name,0) if enabled and run['outcome']!='error' else None
    people=result['people_days']
    result['winter_extra_grain_per_10000_traveller_days']=round(10000*result['extra_grain']/people,4) if people else None
    perf=run['performance']
    result.update(mean_turn_cpu_seconds=perf['mean_turn_cpu_seconds'],max_turn_cpu_seconds=perf['max_turn_cpu_seconds'],
                  mean_turn_wall_seconds=perf['mean_turn_seconds'],max_turn_wall_seconds=perf['max_turn_seconds'],
                  elapsed_seconds=run['seconds'],peak_rss_bytes=perf['worker_peak_rss_bytes'],
                  route_queries=perf['route_queries'],
                  rerouted_tasks=sum(row['status']=='rerouted' for row in entries(directory/'route-changes.csv')),
                  army_relief_replans=sum(row['kind']=='relief_replanned' for row in entries(directory/'army-requests.csv')),
                  region_updates=run['weather_observations']['regional-weather-daily']['rows'] if run['stage'] else None,
                  ice_updates=run['weather_observations']['river-ice-daily']['rows'] if run['stage']>=4 else None)
    return result,frames,cities


def season(month):
    return 'winter' if month in (11,12,1,2,3) else 'spring' if month in (4,5) else 'summer' if month in (6,7,8) else 'autumn'


def geography(region):
    if region in NORTH:
        return 'north'
    return 'huai_transition' if region=='huai_north_jing' else 'south' if region else 'unknown'


def seasonal(wave,run,directory,cities,mapping):
    counters=defaultdict(Counter)
    for row in entries(directory/'war-plans.csv'):
        if row['stage']=='assembled':
            counters[int(row['month']),geography(mapping.get(row['target']))].update(war_plans_assembled=1)
    for row in entries(directory/'battles.csv'):
        if row['defender']!='neutral' and (integer(row,'days') or 0)>0:
            counters[int(row['month']),geography(mapping.get(row['target']))].update(defensive_battles=1)
    for row in entries(directory/'winter-military-actions.csv'):
        month=int(row['month'])
        scope=month,geography(row['region'])
        c=counters[scope]
        action=row['action']
        facts=json.loads(row['details'])
        event=facts.get('event',{})
        if action=='battle_result':
            c.update(engagements=1,battle_deaths=event.get('lost',0),retreats=event.get('outcome') in ('retreat','defeat'))
        elif action=='attack_departed':
            c.update(sorties=1,quoted_sortie_days=facts['days'],quoted_sortie_rations=facts['rations'],
                     quoted_delay_days=max(0,facts['days']-facts['normal_days']))
        elif action=='sortie_quote':
            c.update(sortie_evaluations=1,sortie_evaluations_rejected=not facts['permitted'])
        elif action=='reinforcement_departed':
            c.update(reinforcements=1)
        elif action=='transport_departed':
            c.update(convoy_departures=1,convoy_grain_sent=facts['grain'])
        elif action=='transport_arrived':
            c.update(convoy_arrivals=1,convoy_grain_received=facts['grain'])
        elif action=='grain_traded' and event.get('direction')=='buy':
            c.update(grain_purchased=event['grain'],purchase_transactions=1)
        elif action=='winter_purchase':
            c.update(seasonal_grain_purchase=facts['grain'])
        elif action=='winter_stock_transport':
            c.update(preparation_dispatches=1)
    for row in entries(directory/'shortages.csv'):
        counters[int(row['month']),geography(mapping.get(row['city']))].update(missing_city_turns=1,city_grain_gap=int(row['missing']))
    for frames in cities.values():
        for row in frames:
            if row['owner']=='neutral':
                continue
            c=counters[int(row['month']),geography(mapping.get(row['city']))]
            c.update(faction_city_stock_sum=int(row['grain_stock']),city_stock_samples=1)
    for row in entries(directory/'weather-route-impacts.csv'):
        month=tick_month(run,int(row['tick']))
        c=counters[month,geography(mapping.get(row['source']))]
        c.update(extra_meal_grain=int(row['extra_grain']),weather_delay_units=int(row['delay']),
                 affected_travel_days=1,affected_unpaid_grain_numerator=int(row['missing']),
                 physical_ice_blocked_days=bool(row['blocked']))
    names=('war_plans_assembled','engagements','defensive_battles','battle_deaths','retreats','sorties',
           'quoted_sortie_days','quoted_sortie_rations',
           'quoted_delay_days','sortie_evaluations','sortie_evaluations_rejected','reinforcements',
           'convoy_departures','convoy_grain_sent','convoy_arrivals','convoy_grain_received','grain_purchased',
           'purchase_transactions','seasonal_grain_purchase','preparation_dispatches','missing_city_turns','city_grain_gap',
           'faction_city_stock_sum','city_stock_samples','extra_meal_grain','weather_delay_units','affected_travel_days',
           'affected_unpaid_grain_numerator','physical_ice_blocked_days')
    unavailable=set(names[-5:]) if run['stage']<2 else set()
    if run['stage']<4:
        unavailable.add('physical_ice_blocked_days')
    if run['stage']<5:
        unavailable.update(('seasonal_grain_purchase','preparation_dispatches'))
    for (month,zone),values in sorted(counters.items()):
        yield dict(ident(wave,run),month=month,season=season(month),geography=zone,**{
            key:values[key] if key not in unavailable else None for key in names})


def climate_stats(cases):
    windows=Counter()
    snow=Counter()
    duration=Counter()
    depth=Counter()
    ice=Counter()
    freezes=Counter()
    longest={}
    for _,run,folder in cases:
        key=(run['scenario'],run['seed'])
        if run['stage']>=4 and (key not in longest or run['completed_turns']>longest[key][0]):
            longest[key]=(run['completed_turns'],folder)
    for _,folder in longest.values():
        for line in entries(folder/'regional-weather-daily.csv'):
            region=line['region'];month=int(line['month']);day=int(line['day'])
            if month in REGIONS[region][0] and day%10==0:
                windows[region,month]+=1
            depth[region,int(line['depth'])]+=1
        for line in entries(folder/'snowfall-events.csv'):
            region=line['region'];month=int(line['month'])
            snow[region,month]+=1
            duration[region,int(line['severity']),int(line['ends'])-int(line['began'])+1]+=1
        start={}
        last_tick=0
        for line in entries(folder/'river-ice-daily.csv'):
            reach,status,tick=line['reach'],int(line['state']),int(line['tick'])
            ice[reach,status]+=1
            last_tick=max(last_tick,tick)
            if status==3 and reach not in start:
                start[reach]=tick
            elif status!=3 and reach in start:
                freezes[reach,tick-start.pop(reach),False]+=1
        for reach,tick in start.items():
            freezes[reach,last_tick-tick+1,True]+=1
    probability=(dict(region=k,month=m,eligible_ten_day_periods=windows[k,m],events=snow[k,m],
                      observed_percent=round(100*snow[k,m]/windows[k,m],4) if windows[k,m] else None,
                      configured_percent=REGIONS[k][1] if m in REGIONS[k][0] else 0)
                 for k,m in product(REGIONS,range(1,13)))
    return [list(probability),[dict(region=k,strength=s,days=d,events=n) for (k,s,d),n in sorted(duration.items())],
            [dict(region=k,depth=d,days=n) for (k,d),n in sorted(depth.items())],
            [dict(reach=k,state=s,days=n) for (k,s),n in sorted(ice.items())],
            [dict(reach=k,days=d,censored=c,events=n) for (k,d,c),n in sorted(freezes.items())]]


def pairwise(scores):
    lookup={(r['wave'],r['group'],r['scenario'],r['seed'],r['requested_months']):r for r in scores}
    for (wave,group,scenario,seed,horizon),changed in sorted(lookup.items()):
        bases={'H1':('H0',),'H2':('H0',),'H3':('H2','H1'),'W1':('W0',),
               'W2':('W1',),'W3':('W2',),'W4':('W3',),'W5':('W4',)}.get(group,())
        for base in bases:
            prior=lookup.get((wave,base,scenario,seed,horizon))
            if prior is None:
                continue
            same=prior['full_months']==changed['full_months']
            if not same:
                yield dict(wave=wave,scenario=scenario,seed=seed,requested_months=horizon,base=base,candidate=group,
                           metric='elapsed_months',status='unequal_horizon',before=prior['full_months'],
                           after=changed['full_months'],absolute_change=None,percent_change=None)
            for key in (*CUMULATIVE,*STOCKS,'food_shortages_per_1000_owned_city_turns','oversized_garrison_final',
                        'army_supply_timely_percent','small_faction_survival_percent','blocked_faction_turns','mean_turn_cpu_seconds'):
                a,b=prior[key],changed[key]
                present=a is not None and b is not None
                yield dict(wave=wave,scenario=scenario,seed=seed,requested_months=horizon,base=base,candidate=group,metric=key,
                    status='paired' if same and present else 'unequal_horizon' if not same else 'not_applicable',
                    before=a,after=b,absolute_change=round(b-a,6) if same and present else None,
                    percent_change=round((b-a)*100/a,4) if same and present and a else None)


def distributions(scores):
    values=defaultdict(list)
    for row in scores:
        for metric in (*CUMULATIVE,'mean_turn_cpu_seconds','army_supply_timely_percent','blocked_faction_turns',
                       'small_faction_survival_percent','food_shortages_per_1000_owned_city_turns','oversized_garrison_final'):
            if row[metric] is not None:
                values[row['wave'],row['group'],metric].append(row[metric])
    return [dict(wave=w,group=g,metric=m,runs=len(data),minimum=min(data),maximum=max(data),
                 mean=round(fmean(data),5),median=median(data)) for (w,g,m),data in sorted(values.items())]


def paired_inputs(cases):
    lookup={(w,r['group'],r['scenario'],r['seed']):(r,d) for w,r,d in cases}
    for (wave,group,scenario,seed),(run,directory) in sorted(lookup.items()):
        if group not in ('H1','H3'):
            continue
        baseline=lookup.get((wave,'H0' if group=='H1' else 'H2',scenario,seed))
        if baseline is not None:
            before,folder=baseline
            opening=[]
            for name in ('monthly','cities','factions'):
                opening.append([row for row in entries(folder/(name+'.csv')) if row['elapsed_turns']=='0']==
                               [row for row in entries(directory/(name+'.csv')) if row['elapsed_turns']=='0'])
            yield dict(wave=wave,scenario=scenario,seed=seed,base=before['group'],candidate=group,
                       metric='opening_state',sample=min(run['requested_months'],before['requested_months']),
                       identical=all(opening) and run['catalog_sha256']==before['catalog_sha256'])
        if group=='H3' and (peer:=lookup.get((wave,'H1',scenario,seed))) is not None:
            before,folder=peer
            count=min(before['completed_turns'],run['completed_turns'])*10
            for name in ('regional-weather-daily','river-ice-daily'):
                if before['completed_turns']==run['completed_turns']:
                    same=sha(folder/(name+'.csv'))==sha(directory/(name+'.csv'))
                else:
                    same=all(a==b for a,b in zip(entries(folder/(name+'.csv')),entries(directory/(name+'.csv'))))
                yield dict(wave=wave,scenario=scenario,seed=seed,base='H1',candidate='H3',
                           metric=name,sample=count,identical=same and before['weather_seed']==run['weather_seed'])


def thresholds(scores):
    for base,candidate in (('H0','H1'),('H2','H3')):
        set_by_group={group:{(r['scenario'],r['seed']):r for r in scores
                            if r['wave']=='matrix' and r['group']==group and r['full_months']==60}
                      for group in (base,candidate)}
        before,after=(set_by_group[g] for g in (base,candidate))
        keys=before.keys()&after.keys()
        n=len(keys)
        for metric,criterion in (('unpaid_city_turns','at_most_130_percent'),
             ('convoy_hunger_losses','under_1000_people'),('battles','at_least_50_percent'),
             ('army_supply_timely_percent','down_at_most_five_points')):
            measured=[key for key in keys if before[key][metric] is not None and after[key][metric] is not None]
            a,b=(fmean(rows[key][metric] for key in measured) if measured else None for rows in (before,after))
            if n!=21 or a is None or b is None:
                status='pending' if n!=21 else 'not_applicable'
            elif metric=='unpaid_city_turns':
                status='within' if b<=a*1.3 else 'exceeds'
            elif metric=='convoy_hunger_losses':
                status='within' if b<1000 else 'exceeds'
            elif metric=='battles':
                status='within' if b>=a*.5 else 'exceeds'
            else:
                status='within' if a-b<=5 else 'exceeds'
            yield dict(base=base,candidate=candidate,metric=metric,complete_pairs=n,measured_pairs=len(measured),before=a,after=b,
                       absolute=None if a is None or b is None else b-a,
                       percent=None if not a or b is None else 100*(b-a)/a,criterion=criterion,status=status)


def archive_refs():
    home=Path.home()
    paths={
        'economy-v2':('yongzhou-commandery','docs/three-kingdoms-economy-v2-validation.zip'),
        **{label:(label,f'build/{label}/three-kingdoms-{label}-validation.zip')
           for label in ('logistics-v2','logistics-v21','logistics-v211','logistics-v212')}}
    result=[]
    for label,(wt,relative) in paths.items():
        path=home/'.codex/worktrees'/wt/'Three-Kingdoms2-King-mainland'/relative
        item=dict(name=path.name,worktree=wt,relative=relative,status='referenced' if path.is_file() else 'unavailable')
        if path.is_file():
            with ZipFile(path) as package:
                item.update(sha256=sha(path),size=path.stat().st_size,entries=len(package.infolist()),
                            inventories=[name for name in package.namelist() if name.endswith('manifest.json')][:10])
        result.append(item)
    return result


def write(directory,name,rows,fields=()):
    rows=list(rows)
    if rows:
        to_csv(directory/(name+'.csv'),rows)
    else:
        (directory/(name+'.csv')).write_text(','.join(fields)+'\n',encoding='utf-8')


def generate(root,*,package=False):
    root.mkdir(parents=True,exist_ok=True)
    out=root/'exports';out.mkdir(exist_ok=True)
    candidates=[]
    all_runs=[]
    for path in sorted((root/'observed').glob('*/*/*/*/*/run.json')):
        run=json.loads(path.read_text())
        wave=path.relative_to(root/'observed').parts[0]
        profile=(W if wave=='stages' else H).get(run['group'])
        if profile!=(run.get('base_observer_group'),run.get('stage')):
            continue
        row=ident(wave,run)
        all_runs.append(dict(row,head=run['head'],tree=run['source_tree_sha256'],catalog=run['catalog_sha256'],
                            weather_seed=run['weather_seed'],rule_versions=run['rule_versions'],stage=run['stage'],
                            base_observer_group=run['base_observer_group'],seconds=run['seconds'],failure=run['failure'],
                            path=path.parent.relative_to(root).as_posix()))
        if (run['outcome'] in ('complete','natural_end')
                and run['requested_months']==HORIZONS.get(wave)):
            candidates.append((wave,run,path.parent))
    climate={row['city_id']:row['climate_region_id'] for row in entries(out/'city-climate-regions.csv')}
    scores=[];yrs=[];season_rows=[]
    for wave,run,folder in candidates:
        summary,months,cities=score(wave,run,folder)
        scores.append(summary)
        season_rows.extend(seasonal(wave,run,folder,cities,climate))
        if wave=='long':
            for start in (0,60,120,180):
                window=[row for row in months if start<=int(row['elapsed_months'])<=start+60]
                if not window:
                    continue
                first,last=window[0],window[-1]
                end=int(last['elapsed_months'])
                yrs.append(dict(ident(wave,run),from_month=start,to_month=end,
                    status='complete' if end==start+60 else 'observed_partial',
                    **{f'{k}_delta':int(last[k])-int(first[k]) for k in CUMULATIVE},
                    **{k:integer(last,k) for k in STOCKS}))
    write(out,'scenario-scores',scores)
    pairs=list(pairwise(scores))
    write(out,'pairwise',pairs)
    write(out,'distributions',distributions(scores))
    write(out,'candidate-thresholds',thresholds(scores))
    write(out,'paired-input-equivalence',paired_inputs(candidates))
    write(out,'seasonal-war-comparison',season_rows)
    logistics_fields=('convoy_departures','convoy_grain_sent','convoy_arrivals','convoy_grain_received',
                      'grain_purchased','purchase_transactions','seasonal_grain_purchase','preparation_dispatches',
                      'extra_meal_grain','weather_delay_units','affected_travel_days','affected_unpaid_grain_numerator',
                      'physical_ice_blocked_days')
    identity_fields=(*ident('stages',{'group':'','scenario':'','seed':0,'requested_months':0,'full_months':0,'outcome':''}),
                     'month','season','geography')
    write(out,'seasonal-logistics-comparison',({k:r[k] for k in (*identity_fields,*logistics_fields)} for r in season_rows))
    winter_fields=('missing_city_turns','city_grain_gap','faction_city_stock_sum','city_stock_samples')
    write(out,'winter-shortage-comparison',({k:r[k] for k in (*identity_fields,*winter_fields)} for r in season_rows if r['season']=='winter'))
    write(out,'winter-convoy-comparison',({k:r[k] for k in (*identity_fields,*logistics_fields[:4],'physical_ice_blocked_days')}
                                         for r in season_rows if r['season']=='winter'))
    keys=list(identity_fields[:-3])
    for filename,subset in {
        'winter-army-supply-comparison':('winter_army_supply_requests','winter_army_supply_required',
                                         'winter_army_supply_timely','winter_army_supply_late',
                                         'winter_army_supply_unmet','winter_army_supply_timely_percent','blocked_days'),
        'troop-sustainability-comparison':('active_troops','reserves','oversized_garrison_final','march_hunger_losses',
                                           'convoy_hunger_losses','battle_troops_lost'),
        'small-faction-survival':('small_factions_opening','small_factions_surviving','small_faction_survival_percent','blocked_faction_turns'),
        'performance-comparison':('mean_turn_cpu_seconds','max_turn_cpu_seconds','mean_turn_wall_seconds','max_turn_wall_seconds',
                                  'elapsed_seconds','peak_rss_bytes','route_queries','rerouted_tasks',
                                  'army_relief_replans','region_updates','ice_updates')
    }.items():
        write(out,filename,({k:r[k] for k in (*keys,*subset)} for r in scores))
    write(out,'long-term-economy-comparison',yrs)
    for name,fields,rows in zip(('snowfall-frequency-summary','snow-duration-summary','snow-accumulation-summary',
                                'river-ice-state-summary','river-freeze-duration-summary'),
                               ((),(),(),(),('reach','days','censored','events')),climate_stats(candidates)):
        write(out,name,rows,fields)
    expected={
        'stages':list(product(W,PRIORITY)),
        'matrix':list(product(H,product((2026,2027,2028),SCENARIOS))),
        'long':list(product(H,((2026,'184-02'),(2026,'208-10')))),
        'holdout':list(product(H,product((2031,),('190-01','208-10')))),
    }
    present={(r['wave'],r['group'],r['seed'],r['scenario']):r for r in all_runs
             if r['requested_months']==HORIZONS.get(r['wave'])}
    missing=[]
    for wave,seats in expected.items():
        for group,(seed,scenario) in seats:
            row=present.get((wave,group,seed,scenario))
            if row is None or row['run_status']=='error':
                missing.append(dict(wave=wave,group=group,seed=seed,scenario=scenario,
                                    status='not_finished' if row is None else 'error'))
    w0w1=[]
    for seed,scenario in PRIORITY:
        a=present.get(('stages','W0',seed,scenario))
        b=present.get(('stages','W1',seed,scenario))
        if a and b and not any(row['run_status']=='error' for row in (a,b)):
            x,y=(root/item['path'] for item in (a,b))
            hashes=[json.loads((folder/'run.json').read_text()).get('without_weather_state_sha256')
                    for folder in (x,y)]
            w0w1.append(dict(seed=seed,scenario=scenario,projected_turn_saves_equal=bool(hashes[0]) and hashes[0]==hashes[1],
                monthly_equal=sha(x/'monthly.csv')==sha(y/'monthly.csv'),
                city_equal=sha(x/'cities.csv')==sha(y/'cities.csv'),faction_equal=sha(x/'factions.csv')==sha(y/'factions.csv')))
    to_json(root/'simulation-manifest.json',dict(schema=SCHEMA,stage_definition=W,cohort_definition=H,
                                               seats={k:len(x) for k,x in expected.items()},uncompleted=missing,runs=all_runs))
    to_json(root/'stage-equivalence.json',w0w1)
    if package:
        pack(root)


def pack(root):
    files={}
    for name in ('exports','checks'):
        files.update({p.relative_to(root).as_posix():p for p in (root/name).glob('*') if p.is_file()})
    simulation=json.loads((root/'simulation-manifest.json').read_text())
    for run in simulation['runs']:
        for file in (root/run['path']).iterdir():
            if file.is_file():
                files[file.relative_to(root).as_posix()]=file
    for path in (*root.glob('*-source-identity.json'),root/'simulation-manifest.json',root/'stage-equivalence.json'):
        files[path.name]=path
    for path in (TOOL_ROOT/'docs/weather-v22').glob('*.md'):
        files['docs/'+path.name]=path
    identities={name:dict(sha256=sha(path),bytes=path.stat().st_size) for name,path in sorted(files.items())}
    manifest=root/'validation-manifest.json'
    to_json(manifest,dict(schema=SCHEMA,source_archives=archive_refs(),files=identities))
    files[manifest.name]=manifest
    target=root/'three-kingdoms-weather-v22-validation.zip'
    temporary=target.with_suffix('.zip.incomplete')
    with ZipFile(temporary,'w',compression=ZIP_DEFLATED,compresslevel=6,allowZip64=True) as zip_out:
        for name,path in sorted(files.items()):
            zip_out.write(path,arcname=name)
    with ZipFile(temporary) as zip_in:
        failure=zip_in.testzip()
        if failure:
            raise ValueError('ZIP CRC check failed: '+failure)
    temporary.replace(target)
    target.with_suffix('.zip.sha256').write_text(f'{sha(target)}  {target.name}\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=TOOL_ROOT/'build/weather-v22')
    parser.add_argument('--package',action='store_true')
    args=parser.parse_args()
    generate(args.root,package=args.package)
