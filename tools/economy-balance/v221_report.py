"""Recompute V2.2.1 validation exports from committed engine receipts."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
from functools import lru_cache
from hashlib import file_digest
from itertools import product, zip_longest
import json
from pathlib import Path
from statistics import fmean, median
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from common import HeadlessCampaign, TOOL_ROOT, catalogs, to_json
from v221_experiments import GROUPS, ROOT_OUTPUT, WAVES
from remake import city_economy, route_hazards, winter_travel
from v22_report import CUMULATIVE, STOCKS, entries, ident, integer, season, seasonal, sha, tick_month, write, score

SCHEMA='tk2-weather-v221-validation-v1'
SNAPSHOT=Path.home()/'.codex/worktrees/weather-v22/Three-Kingdoms2-King-mainland'
BASELINE_RELATIVE=Path('build/weather-v22/three-kingdoms-weather-v22-validation.zip')
CANDIDATE={'I3-211':('H1','H0'),'I3-212':('H3','H2'),'I1-211':('H1',),'I2-211':('H1',),
           'I1-212':('H3',),'I2-212':('H3',)}
MEASURES=('unpaid_city_turns','rations_missing','battles','march_hunger_losses','convoy_hunger_losses',
          'oversized_garrison_final','blocked_faction_turns','army_supply_timely_percent',
          'winter_army_supply_timely_percent','published_timely_percent','published_winter_timely_percent',
          'convoy_dispatched','net_grain_delivered','delivery_rate','safe_return_rate','overdue_90',
          'restarted_returns','active_at_end','army_relief_hunger_losses','shortfall_grain','sorties_per_1000_faction_turns',
          'published_pending','convoy_hunger_per_10000_people_days','convoy_hunger_per_10000_grain',
          'mean_turn_cpu_seconds','max_turn_wall_seconds','seasonal_purchase','seasonal_transfer')


def compressed_rows(path):
    with gzip.open(path,'rt',encoding='utf-8',newline='') as handle:
        yield from csv.DictReader(handle)


def tick_from_date(run,text):
    if text in (None,'','null'):
        return None
    y,m,d=json.loads(text)
    y0,m0,d0=run['start_date']
    return (y-y0)*360+(m-m0)*30+d-d0+1


def ratio(value,maximum):
    return round(100*value/maximum,6) if maximum else None


def supply(run,directory,name,*,interval=None):
    totals=Counter()
    winter=Counter()
    for row in entries(directory/name):
        opened=integer(row,'first_request_time')
        if interval and not interval[0]<opened<=interval[1]:
            continue
        values=dict(episodes=1,required=integer(row,'original_required_grain')+integer(row,'additional_required_grain'),
                    timely=integer(row,'timely_delivered_grain'),late=integer(row,'late_delivered_grain'),
                    unmet=integer(row,'remaining_unmet_grain'),
                    pending=row['terminal_status']=='pending_at_observation_end',
                    actual_shortages=integer(row,'actual_shortage_tick') is not None)
        totals.update(values)
        if season(tick_month(run,opened))=='winter':
            winter.update(values)
    return dict(totals),dict(winter)


def convoy_data(wave,run,directory):
    seed=ident(wave,run)
    loads=defaultdict(dict)
    active={str(c['id']) for c in run['terminal']['convoy_loads']}
    transitions=[]
    for row in entries(directory/'convoys.csv'):
        ident_key=row['convoy_id']; history=loads[ident_key]
        phase=row['stage']; date=[int(row[name]) for name in ('year','month','day')]
        transitions.append(dict(seed,convoy=ident_key,date=date,phase=phase,source=row['source'],
            target=row['target'],reason=row['reason'],expected=row['expected_arrival_date'],
            delivered=integer(row,'actual_grain'),route_date=row['actual_route_date'],route=row['route']))
        if phase=='departed':
            history.update(source=row['source'],target=row['target'],owner=row['owner'],
                ordinary=row['target_march']=='null',departure=tick_from_date(run,row['dispatched_date']),
                eta=tick_from_date(run,row['expected_arrival_date']),cargo=integer(row,'grain_loaded'))
        elif phase=='delivered':
            history.update(delivery=tick_from_date(run,row['actual_route_date'])
                or tick_from_date(run,row['actual_arrival_date']), receipt=tick_from_date(run,row['actual_arrival_date']),
                net=integer(row,'actual_grain'))
        elif phase=='docked':
            history.update(docked=tick_from_date(run,row['actual_route_date'])
                or tick_from_date(run,json.dumps(date)))
        elif phase=='abandoned':
            history['abandoned']=True
        elif phase=='return_ordered':
            history['return_orders']=history.get('return_orders',0)+1
    reasons=defaultdict(Counter)
    stalled=Counter()
    missing=defaultdict(Counter)
    ice_day={}; previous={}
    ice_cases=[]
    frozen={}
    for row in compressed_rows(directory/'transport-progress-daily.csv.gz'):
        convoy=row['convoy']; day=int(row['tick']); moved=int(row['moved'])
        assert int(row['start_work'])-moved==int(row['end_work']), (directory,convoy,day)
        assert int(row['rations_before'])+int(row['supply'])-int(row['paid'])==int(row['rations_after']), (directory,convoy,day)
        assert (int(row['cargo_before'])-int(row['route_loss'])-int(row['incident_loss'])
                -int(row['cargo_to_bag'])==int(row['cargo_after'])), (directory,convoy,day)
        if convoy in previous and previous[convoy][0]==row['journey'] and previous[convoy][1]+1==day:
            assert previous[convoy][2]==int(row['start_work']), (directory,convoy,day)
        previous[convoy]=(row['journey'],day,int(row['end_work']))
        if row['reason'] and row['reason']!='arrival_pending':
            block=reasons[row['reason']]
            block[convoy]+=1
        stalled[convoy]=max(stalled[convoy],int(row['consecutive_no_progress']))
        if row['ice']:
            ice_day[convoy]=ice_day.get(convoy,0)+1
            episode=frozen.get(convoy)
            if not episode or episode['reach']!=row['ice'] or episode['ice_released_tick'] is not None:
                episode=dict(seed,convoy=convoy,reach=row['ice'],journey=row['journey'],first_tick=day,last_tick=day,
                    ice_days=0,ice_index_at_start=integer(row,'ice_index'),initial_rations=int(row['rations_before']),
                    initial_cargo=int(row['cargo_before']),initial_work=int(row['start_work']),last_rations=0,
                    last_cargo=0,ice_released_tick=None,resumed_tick=None,resumed_work=None,mode_at_resume=None)
                frozen[convoy]=episode
                ice_cases.append(episode)
            episode.update(last_tick=day,ice_days=episode['ice_days']+1,last_rations=int(row['rations_after']),
                           last_cargo=int(row['cargo_after']))
        elif convoy in frozen:
            episode=frozen[convoy]
            if episode['ice_released_tick'] is None:
                episode['ice_released_tick']=day
            if moved:
                frozen.pop(convoy).update(resumed_tick=day,resumed_work=moved,
                    mode_at_resume='replanned' if row['journey']!=episode['journey'] else 'continued')
        facts=loads[convoy]
        for period in ('annual','winter') if season(tick_month(run,day))=='winter' else ('annual',):
            counts=facts.setdefault(period,Counter())
            counts.update(escort_days=int(row['person_days']), hunger_loss=int(row['hunger_loss']),
                          paid=int(row['paid']), shortage_days=bool(int(row['missing'])),
                          ice_days=bool(row['ice']))
        if int(row['missing']):
            shortage=missing[convoy]
            if not shortage:
                shortage['first_tick']=day
            shortage.update(days=1,unpaid_q=int(row['missing']),lost=int(row['hunger_loss']))
    summary=Counter()
    details=[]
    for convoy,record in loads.items():
        if 'departure' not in record:
            continue
        delivered='delivery' in record
        docked='docked' in record
        pending=convoy in active
        last=record.get('docked') or (run['completed_turns']*10 if pending else
                                     previous.get(convoy,(None,run['completed_turns']*10,None))[1])
        comparison=record.get('delivery',last)
        excess=max(0,comparison-record['eta']) if record['eta'] is not None else None
        summary.update(departed=1,ordered_returns=record.get('return_orders',0),delivered=delivered,
                       encounters_ice=convoy in ice_day,docked=docked,terminal=not pending,pending=pending,
                       net_grain_delivered=record.get('net') or 0,
                       overdue_30=bool(excess is not None and excess>30),
                       overdue_90=bool(excess is not None and excess>90),
                       stalled_3=stalled[convoy]>=3,stalled_10=stalled[convoy]>=10,stalled_30=stalled[convoy]>=30,
                       convoys_with_shortage=convoy in missing,
                       hunger_losses=missing[convoy].get('lost',0) if convoy in missing else 0)
        details.append(dict(seed,convoy=convoy,source=record['source'],target=record['target'],owner=record['owner'],
                ordinary=record['ordinary'],departure=record['departure'],original_eta=record['eta'],
                delivered=record.get('delivery'),receipt=record.get('receipt'),docked=record.get('docked'),cargo=record['cargo'],
                net=record.get('net'),observed_elapsed=last-record['departure'],overdue_days=excess,
                order_count=record.get('return_orders',0),longest_stall=stalled[convoy],ice_days=ice_day.get(convoy,0),
                hunger_loss=missing[convoy].get('lost',0) if convoy in missing else 0,
                annual=record.get('annual',{}),winter=record.get('winter',{}),
                outcome='docked' if docked else 'active_at_end' if pending else
                        'abandoned' if record.get('abandoned') else 'ended_elsewhere'))
    repeat=[]
    for row in entries(directory/'route-changes.csv'):
        if row['unit_kind']!='convoy' or row['status']!='rerouted' or row['old_target']!=row['new_target']:
            continue
        old=json.loads(row['old_path']); new=json.loads(row['new_path'])
        if old and new and new[0] in old and old[old.index(new[0]):]==new:
            repeat.append(dict(seed,convoy=row['unit_id'],date=[row['year'],row['month'],row['day']],
                               reason=row['reason'],old_path=old,new_path=new,disposition='same_observed_path_restarted'))
    return (summary,details,transitions,
            [dict(seed,reason=reason,days=sum(branch.values()),convoys=len(branch)) for reason,branch in sorted(reasons.items())],
            [dict(seed,convoy=key,**row) for key,row in missing.items()],repeat,ice_cases)


def pairs(scores):
    lookup={(r['wave'],r['group'],r['scenario'],r['seed']):r for r in scores}
    for row in scores:
        bases=CANDIDATE.get(row['group'],())
        for base in bases:
            wave=row['wave']
            # The four controlled focus cases share matching matrix or holdout weather baselines where available.
            previous=lookup.get((wave,base,row['scenario'],row['seed']))
            if previous is None and wave=='focus':
                previous=lookup.get(('matrix',base,row['scenario'],row['seed']))
            if previous is None:
                continue
            same=previous['full_months']==row['full_months']==row['requested_months']
            for metric in MEASURES:
                a,b=previous[metric],row[metric]
                valid=same and a is not None and b is not None
                yield dict(wave=wave,baseline_wave=previous['wave'],base=base,candidate=row['group'],
                           scenario=row['scenario'],seed=row['seed'],metric=metric,
                           status='matched' if valid else 'duration_short_or_unequal' if not same else 'not_applicable',
                           before=a,after=b,absolute=b-a if valid else None,percent=100*(b-a)/a if valid and a else None)


def weather_equivalence(cases):
    paths={(w,r['group'],r['scenario'],r['seed']):(r,d) for w,r,d in cases}
    for (wave,group,scenario,seed),(run,directory) in sorted(paths.items()):
        reference=('H1',) if group=='I3-211' else ('H3','I3-211') if group=='I3-212' else ()
        for older in reference:
            previous=paths.get((wave,older,scenario,seed))
            if previous is None:
                continue
            for name in ('regional-weather-daily','river-ice-daily'):
                other,folder=previous
                same=run['completed_turns']==other['completed_turns']
                a=directory/(name+'.csv'); b=folder/(name+'.csv')
                days=min(run['completed_turns'],other['completed_turns'])*10
                match=sha(a)==sha(b) if same else all(
                    x==y for x,y in zip_longest(
                        (r for r in entries(a) if int(r['tick'])<=days),
                        (r for r in entries(b) if int(r['tick'])<=days)))
                yield dict(wave=wave,group=group,base=older,scenario=scenario,seed=seed,
                           stream=name,matched=match and run['weather_seed']==other['weather_seed'],
                           matched_days=min(run['completed_turns'],other['completed_turns'])*10)


def phase_rows(run,months,cities,directory,details):
    faction_activity=list(entries(directory/'action-capacity.csv'))
    catalog=next(item for item in catalogs_once() if item.data['id'].endswith(run['scenario']))
    for beginning in (0,60,120,180):
        window=[m for m in months if beginning<=int(m['elapsed_months'])<=beginning+60]
        if len(window)<2:
            continue
        start,end=window[0],window[-1]
        first,last=(int(r['elapsed_turns']) for r in (start,end))
        end_month=int(end['elapsed_months'])
        stock=cities[last]
        convoy=[r for r in details if r['receipt'] is not None and first*10<r['receipt']<=last*10]
        def large_origin(row):
            month=(run['start_date'][1]-1)+(row['departure']-1)//30
            return city_economy.tier_at(catalog.data,row['source'],run['start_date'][0]+month//12,month%12+1) in ('large','giant')
        ranges=(first*10,last*10)
        _,legacy=supply(run,directory,'supply-episodes.csv',interval=ranges)
        _,published=supply(run,directory,'supply-episodes-weather-aware.csv',interval=ranges)
        yield dict(ident('long',run),from_month=beginning,to_month=end_month,
            status='complete' if end_month==beginning+60 else 'observed_partial',
            **{metric:int(end[metric])-int(start[metric]) for metric in CUMULATIVE},
            **{metric:integer(end,metric) for metric in STOCKS},
            docked_convoys=sum(r['docked'] is not None and first*10<r['docked']<=last*10 for r in details),
            grain_delivered=sum(r['net'] or 0 for r in convoy),
            registered_large_source_grain=sum(r['net'] or 0 for r in convoy if large_origin(r)),
            oversized_garrison=sum(integer(r,'stationed_troops_above_sustainable') or 0 for r in stock),
            inactive_faction_turns=sum(first<int(r['turn'])<=last and r['qualifies']=='true' and
                (integer(r,'no_action_streak') or 0)>=3 for r in faction_activity),
            winter_legacy_needed=legacy.get('required',0),winter_legacy_timely=legacy.get('timely',0),
            winter_published_needed=published.get('required',0),winter_published_timely=published.get('timely',0))


@lru_cache(maxsize=1)
def catalogs_once():
    return catalogs()


def climate_review():
    games=[HeadlessCampaign(item,record_journal=False) for item in catalogs_once()]
    cities={}
    rivers={}
    route_parts={}
    pairs={frozenset(a) for a in (('jincheng','shuofang'),('dongjun','qinghe'),('hongnong','hedong'),
        ('qinghe','pingyuan'),('wudu','yinping'))}
    centers={'liaodong','qinling_highlands','southern_highlands'}
    def row(kind,identity,region,*,mapping=None,source=None,target=None,mode=None,reach=None,work=None,sensitivity=None):
        return dict(kind=kind,identity=identity,source=source,target=target,mode=mode,region=region,
                    reach=reach,work=work,freeze_sensitivity=sensitivity,mapping=mapping,
                    result='existing mapping retained')
    for game in games:
        cities.update(game.catalog.climate.cities)
        rivers.update(game.catalog.climate.reaches)
        for raw in game.catalog.climate.routes.values():
            for source,target in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                if (frozenset((source,target)) not in pairs and not
                        any(game.catalog.climate.cities[city]['climate_region_id'] in centers for city in (source,target))):
                    continue
                if not route_hazards.route_allowed(game.catalog.data,raw,source,target):
                    continue
                route=route_hazards.evaluate_leg(game.catalog.data,raw,source,target,1)
                quote=game._quote([source,target],[route])
                for index,part in enumerate(winter_travel.plan(game,quote),1):
                    identity,mode,region,reach,work=raw['id'],part.mode,part.region,part.reach,part.work
                    key=(identity,source,target,index,mode,region,reach,work)
                    route_parts[key]=row('route_part',f'{identity}/{index}',region,
                        mapping='physical reach' if reach else 'terrain segmentation',
                        source=source,target=target,mode=mode,reach=reach,work=work,
                        sensitivity=rivers[reach]['freeze_sensitivity'] if reach in rivers else None)
    all_rows=[row('city',key,value['climate_region_id'],mapping=value['elevation_class'])
              for key,value in sorted(cities.items())]
    all_rows.extend(row('river_reach',key,value['freeze_region_id'],reach=key,
                       mapping=value['mapping'],sensitivity=value['freeze_sensitivity'])
                    for key,value in sorted(rivers.items()))
    all_rows.extend(route_parts.values())
    return all_rows,{key:value['climate_region_id'] for key,value in cities.items()}


def convoy_seasons(key,run,details):
    for period in ('annual','winter'):
        for category in ('ordinary','army_relief'):
            ordinary=category=='ordinary'
            matching=[r for r in details if r['ordinary']==ordinary]
            counts=Counter()
            for row in matching:
                counts.update(row[period])
                if period=='annual' or season(tick_month(run,row['departure']))=='winter':
                    counts['departures']+=1
                if row['receipt'] is not None and (period=='annual' or season(tick_month(run,row['receipt']))=='winter'):
                    counts['deliveries']+=1
                    counts['delivered_grain']+=row['net'] or 0
                if row['docked'] is not None and (period=='annual' or season(tick_month(run,row['docked']))=='winter'):
                    counts['returns']+=1
            yield dict(key,season=period,category=category,
                **{k:counts[k] for k in ('departures','deliveries','returns','delivered_grain','escort_days',
                                          'hunger_loss','paid','shortage_days','ice_days')},
                loss_per_10000_escort_days=ratio(counts['hunger_loss']*100,counts['escort_days']),
                loss_per_10000_delivered_grain=ratio(counts['hunger_loss']*100,counts['delivered_grain']))


# Threshold rows disclose genuinely comparable observations, including empty denominators.
def readiness(scores,comparisons):
    for candidate,(same_weather,off) in (('I3-211',('H1','H0')),('I3-212',('H3','H2'))):
        for metric,baseline,criterion,limit in (
          ('convoy_hunger_losses',same_weather,'candidate_max',200),
          ('army_supply_timely_percent',same_weather,'minimum_difference',0),
          ('published_timely_percent',same_weather,'minimum_difference',0),
          ('winter_army_supply_timely_percent',off,'minimum_difference',-5),
          ('published_winter_timely_percent',off,'minimum_difference',-5),
          ('seasonal_purchase',same_weather,'positive_total',0),
          ('seasonal_transfer',same_weather,'positive_total',0),
          ('mean_turn_cpu_seconds',same_weather,'relative_max',-20),
        ):
            trials=[r for r in comparisons if r['wave']=='matrix' and r['candidate']==candidate and
                    r['base']==baseline and r['metric']==metric and r['status']=='matched']
            base=fmean(r['before'] for r in trials) if trials else None
            revised=fmean(r['after'] for r in trials) if trials else None
            effect=revised-base if trials else None
            actual={'candidate_max':revised,'minimum_difference':effect,
                    'positive_total':sum(r['after'] for r in trials) if trials else None,
                    'relative_max':100*effect/base if trials and base else None}[criterion]
            all_pairs=sum(r['wave']=='matrix' and r['candidate']==candidate and r['base']==baseline and
                       r['metric']==metric for r in comparisons)
            result='incomplete'
            if all_pairs==21 and actual is not None:
                passed=actual<=limit if criterion in ('candidate_max','relative_max') else (
                    actual>limit if criterion=='positive_total' else actual>=limit)
                result='met' if passed else 'missed'
            yield dict(candidate=candidate,reference=baseline,metric=metric,comparison=criterion,limit=limit,
                pair_seats=all_pairs,comparable_cases=len(trials),baseline_mean=base,candidate_mean=revised,
                actual=actual,result=result)
        for row in scores:
            if row['wave']!='long' or row['group']!=candidate:
                continue
            prior=next((s for s in scores if s['wave']=='long' and s['group']==same_weather and
                        s['scenario']==row['scenario'] and s['seed']==row['seed']),None)
            if prior is None:
                continue
            before=prior['convoy_hunger_losses']
            comparable=prior['full_months']==row['full_months']==240
            actual=100*(row['convoy_hunger_losses']-before)/before if before and comparable else None
            yield dict(candidate=candidate,reference=same_weather,metric='long_convoy_hunger_'+row['scenario'],
                comparison='relative_max',limit=-50,pair_seats=1,comparable_cases=int(comparable),
                baseline_mean=before,candidate_mean=row['convoy_hunger_losses'],actual=actual,
                result='incomplete' if actual is None else 'met' if actual<=-50 else 'missed')


def generate(root):
    export=root/'exports'; export.mkdir(parents=True,exist_ok=True)
    out=defaultdict(list)
    accepted=[]
    identity={}
    for path in sorted((root/'observed').glob('*/*/*/*/*/run.json')):
        run=json.loads(path.read_text())
        wave=path.relative_to(root/'observed').parts[0]
        if wave not in WAVES or run['requested_months']!=WAVES[wave][2]:
            continue
        summary=dict(ident(wave,run),path=path.parent.relative_to(root).as_posix(),head=run['head'],
            source_tree_sha256=run['source_tree_sha256'],catalog_sha256=run['catalog_sha256'],
            weather_seed=run['weather_seed'],weather=run['weather_rules_version'],
            rule_versions=run['rule_versions'],profile=run['base_observer_group'],adjustments=run['adjustments'],
            worktree_diff_sha256=run['worktree_diff_sha256'], observation_config=run['telemetry']['config'],
            backend=run['backend'],failure=run['failure'])
        identity[wave,run['group'],run['scenario'],run['seed']]=summary
        if run['outcome'] in ('complete','natural_end'):
            accepted.append((wave,run,path.parent))
    expected={(wave,group,scenario,seed) for wave,(groups,seats,_) in WAVES.items()
              for group,(seed,scenario) in product(groups,seats)}
    runnable={key for key,row in identity.items() if row['run_status'] in ('complete','natural_end')}
    outstanding=[dict(wave=w,group=g,scenario=s,seed=k,status=identity.get((w,g,s,k),{}).get('run_status','not_completed'))
                 for w,g,s,k in sorted(expected-runnable)]
    engine_digests={r['source_tree_sha256'] for r in identity.values() if r['run_status'] in ('complete','natural_end')}
    assert len(engine_digests)<=1, f'Mixed experiment engine identities: {engine_digests}'
    to_json(root/'simulation-manifest.json',dict(schema=SCHEMA,groups=GROUPS,runs=list(identity.values()),
            uncompleted=outstanding,expected=len(expected),additional_controls=len(runnable-expected),
            engine_source_sha256=next(iter(engine_digests),None)))
    out['climate-mapping-review'],climate=climate_review()
    for wave,run,directory in accepted:
        sample,months,cities=score(wave,run,directory)
        key=ident(wave,run)
        summary,details,transitions,reasons,shortages,repeated,ice_cases=convoy_data(wave,run,directory)
        totals,win=supply(run,directory,'supply-episodes-weather-aware.csv')
        legacy,legacy_win=supply(run,directory,'supply-episodes.csv')
        season_actions=run['seasonal_actions']
        people=run['weather_totals'].get('escort_person_days',0)
        sanctioned=integer(months[-1],'active_faction_turns')
        sample.update(net_grain_delivered=summary['net_grain_delivered'],
                      shortfall_grain=totals.get('unmet',0),active_at_end=summary['pending'],
                      restarted_returns=len(repeated),army_relief_hunger_losses=sum(r['hunger_loss'] for r in details if not r['ordinary']),
                      sorties_per_1000_faction_turns=ratio(sample['ai_sorties']*10,sanctioned),
                      delivery_rate=ratio(sum(r['delivered'] is not None for r in details if r['outcome']!='active_at_end'),
                                          summary['terminal']),
                      safe_return_rate=ratio(summary['docked'],summary['terminal']),
                      overdue_90=summary['overdue_90'],published_pending=totals.get('pending',0),
                      published_timely_percent=ratio(totals.get('timely',0),totals.get('required',0)),
                      published_winter_timely_percent=ratio(win.get('timely',0),win.get('required',0)),
                      seasonal_purchase=season_actions.get('winter_purchase',0),
                      seasonal_transfer=season_actions.get('winter_stock_transport',0),
                      convoy_hunger_per_10000_people_days=ratio(sample['convoy_hunger_losses']*100,people),
                      convoy_hunger_per_10000_grain=ratio(sample['convoy_hunger_losses']*100,summary['net_grain_delivered']))
        out['scenario-scores'].append(sample)
        out['transport-progress-comparison'].append(dict(key,**{field:summary[field] for field in (
            'departed','delivered','docked','terminal','pending','overdue_30','overdue_90','stalled_3','stalled_10',
            'stalled_30','ordered_returns','net_grain_delivered','convoys_with_shortage','hunger_losses','encounters_ice')},
            observed_escort_person_days=people))
        out['safe-return-comparison'].append(dict(key,departed=summary['departed'],docked=summary['docked'],
            delivered=summary['delivered'],terminal=summary['terminal'],pending=summary['pending'],
            delivery_rate=sample['delivery_rate'],safe_return_rate=sample['safe_return_rate'],
            grain=summary['net_grain_delivered'],hunger_losses=sample['convoy_hunger_losses'],
            hunger_per_10000_escort_days=sample['convoy_hunger_per_10000_people_days'],
            hunger_per_10000_delivered_grain=sample['convoy_hunger_per_10000_grain']))
        out['transport-lifecycle'].extend(transitions)
        out['ice-blocked-spells'].extend(ice_cases)
        out['convoy-block-reasons'].extend(reasons)
        out['dynamic-ration-shortfalls'].extend(shortages)
        out['repeated-return-orders'].extend(repeated)
        out['overdue-convoys'].extend(row for row in details if (row['overdue_days'] or 0)>0)
        out['long-convoy-cases'].extend(row for row in details if row['observed_elapsed']>90 or row['longest_stall']>=30)
        out['winter-convoy-comparison'].extend(convoy_seasons(key,run,details))
        for name,year,win0 in (('legacy',legacy,legacy_win),('weather-aware',totals,win)):
            for label,t in (('annual',year),('winter',win0)):
                out[f'winter-army-supply-{name}-comparison'].append(dict(key,season=label,
                    **{k:t.get(k,0) for k in ('episodes','required','timely','late','unmet','pending')},
                    actual_shortages=t.get('actual_shortages',0) if name=='weather-aware' else None,
                    timely_percent=ratio(t.get('timely',0),t.get('required',0))))
        out['winter-preparation-comparison'].append(dict(key,
            evaluations=season_actions.get('winter_preparation_evaluation',0),
            purchases=sample['seasonal_purchase'],transfers=sample['seasonal_transfer'],
            rejections=season_actions.get('winter_preparation_rejection',0),
            node_date_updates=season_actions.get('winter_supply_node_updated',0),
            node_releases=season_actions.get('winter_supply_node_released',0)))
        by_convoy={str(r['convoy']):r for r in details}
        for record in entries(directory/'winter-military-actions.csv'):
            action=record['action']
            target={'winter_preparation_evaluation':'winter-preparation-evaluations',
                    'winter_preparation_rejection':'winter-preparation-rejections',
                    'winter_purchase':'winter-procurement-comparison',
                    'winter_stock_transport':'winter-transfer-comparison',
                    'winter_supply_node_updated':'winter-supply-node-comparison',
                    'winter_supply_node_released':'winter-supply-node-comparison'}.get(action)
            if action=='winter_stock_transport':
                facts=json.loads(record['details'])
                convoy=by_convoy.get(str(facts['convoy']))
                evidence=dict(key,**record,convoy_id=facts['convoy'],estimated_gap=facts['extra'],
                              expected_deadline_turns=facts['deadline'])
                evidence.update(donor=convoy['source'],recipient=convoy['target'],sent_grain=convoy['cargo'],
                    delivered_grain=convoy['net'],actual_received_tick=convoy['receipt'],
                    actual_docked_tick=convoy['docked'],terminal_status=convoy['outcome'])
                out[target].append(evidence)
            elif action=='winter_purchase':
                facts=json.loads(record['details'])
                out[target].append(dict(key,**record,purchased_grain=facts['grain'],estimated_gap=facts['extra']))
            elif target:
                out[target].append(dict(key,**record))
            if action=='convoy_return_unchanged':
                return_order=json.loads(record['details'])
                out['repeated-return-orders'].append(dict(key,convoy=return_order['convoy'],
                    date=[record['year'],record['month'],record['day']],reason='existing_route',
                    old_path=return_order['route'],new_path=return_order['route'],
                    disposition='unchanged_request_ignored'))
        season_rows=list(seasonal(wave,run,directory,cities,climate))
        active_turns=Counter(tick_month(run,(int(r['turn'])-1)*10) for r in entries(directory/'action-capacity.csv'))
        for row in season_rows:
            sample_size=active_turns[row['month']]
            row.update(active_faction_turns=sample_size,
                       sorties_per_1000_faction_turns=ratio(row['sorties']*10,sample_size),
                       engagements_per_1000_faction_turns=ratio(row['engagements']*10,sample_size))
        out['seasonal-war-comparison'].extend(season_rows)
        out['winter-shortage-comparison'].extend({k:r[k] for k in (*key,'month','geography','missing_city_turns','city_grain_gap')}
                                                 for r in season_rows if r['season']=='winter')
        out['performance-comparison'].append(dict(key,**run['performance'],
            region_updates=run['weather_observations']['regional-weather-daily']['rows'],
            ice_updates=run['weather_observations']['river-ice-daily']['rows'],
            observed_convoy_days=run['weather_observations']['transport-progress-daily']['rows'],
            actual_return_replans=sum(r['disposition']=='same_observed_path_restarted' for r in repeated),
            branch=run['source_tree_sha256']))
        if wave=='long':
            out['long-term-economy-comparison'].extend(phase_rows(run,months,cities,directory,details))
    out['pairwise']=list(pairs(out['scenario-scores']))
    out['balance-readiness']=list(readiness(out['scenario-scores'],out['pairwise']))
    buckets=defaultdict(list)
    for row in out['scenario-scores']:
        for metric in MEASURES:
            if row[metric] is not None:
                buckets[row['wave'],row['group'],metric].append(row[metric])
    out['distributions']=[dict(wave=wave,group=group,metric=metric,samples=len(series),mean=fmean(series),
                               median=median(series),min=min(series),max=max(series))
                          for (wave,group,metric),series in sorted(buckets.items())]
    directions={'army_supply_timely_percent','winter_army_supply_timely_percent','published_timely_percent',
                'published_winter_timely_percent','net_grain_delivered','delivery_rate','safe_return_rate'}
    delta=defaultdict(list)
    for row in out['pairwise']:
        if row['status']=='matched':
            delta[row['wave'],row['base'],row['candidate'],row['metric']].append(row['absolute'])
    out['paired-delta-distributions']=[dict(wave=wave,base=base,candidate=candidate,metric=metric,samples=len(values),
                mean_delta=fmean(values),median_delta=median(values),minimum=min(values),maximum=max(values),
                increases=sum(v>0 for v in values),decreases=sum(v<0 for v in values),equal=sum(v==0 for v in values),
                better_when='increasing' if metric in directions else 'decreasing' if
                    metric in {'unpaid_city_turns','rations_missing','march_hunger_losses','convoy_hunger_losses',
                               'oversized_garrison_final','blocked_faction_turns','shortfall_grain','overdue_90'} else None)
                for (wave,base,candidate,metric),values in sorted(delta.items())]
    out['paired-weather-equivalence']=list(weather_equivalence(accepted))
    for name in ('winter-procurement-comparison','winter-transfer-comparison','winter-supply-node-comparison',
                 'winter-preparation-evaluations','winter-preparation-rejections','repeated-return-orders',
                 'long-term-economy-comparison','overdue-convoys','long-convoy-cases','pairwise',
                 'paired-weather-equivalence','dynamic-ration-shortfalls','ice-blocked-spells'):
        out.setdefault(name,[])
    for name,rows in out.items():
        write(export,name,rows,fields=('wave','group','scenario','seed'))
    return identity


def pack(root):
    result={}
    for label in ('checks','exports'):
        result.update({p.relative_to(root).as_posix():p for p in (root/label).glob('*') if p.is_file()})
    result.update({p.name:p for p in root.glob('source-*.json')})
    manifest=root/'simulation-manifest.json'
    result[manifest.name]=manifest
    for run in json.loads(manifest.read_text())['runs']:
        for path in (root/run['path']).iterdir():
            if path.is_file():
                result[path.relative_to(root).as_posix()]=path
    for p in (root/'reproduction').rglob('*'):
        if p.is_file() and p.name in ('diagnostic.jsonl','probe-result.json','comparison.json'):
            result[p.relative_to(root).as_posix()]=p
    for path in (TOOL_ROOT/'docs/weather-v221').glob('*.md'):
        result[f'docs/{path.name}']=path
    previous=SNAPSHOT/BASELINE_RELATIVE
    source=dict(path=str(previous),sha256=sha(previous),bytes=previous.stat().st_size) if previous.is_file() else None
    identity=root/'validation-manifest.json'
    to_json(identity,dict(schema=SCHEMA,previous_package=source,
        files={name:dict(sha256=sha(path),bytes=path.stat().st_size) for name,path in sorted(result.items())}))
    result[identity.name]=identity
    target=root/'three-kingdoms-weather-v221-validation.zip'
    temp=target.with_suffix('.zip.incomplete')
    with ZipFile(temp,'w',compression=ZIP_DEFLATED,compresslevel=5,allowZip64=True) as archive:
        for name,path in sorted(result.items()):
            archive.write(path,name,compress_type=ZIP_STORED if path.suffix in ('.gz','.png') else ZIP_DEFLATED)
    with ZipFile(temp) as archive:
        assert archive.testzip() is None
        for name,meta in json.loads(archive.read(identity.name))['files'].items():
            with archive.open(name) as file:
                assert file_digest(file,'sha256').hexdigest()==meta['sha256'],name
    temp.replace(target)
    target.with_suffix('.zip.sha256').write_text(f'{sha(target)}  {target.name}\n',encoding='utf-8')
    print(target.name,target.stat().st_size,len(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT_OUTPUT)
    parser.add_argument('--package',action='store_true')
    args=parser.parse_args()
    generate(args.root)
    if args.package:
        pack(args.root)
