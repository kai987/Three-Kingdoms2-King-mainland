"""Build V2.1.1 comparisons from measured runs and a checksum-verified E4 archive."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from hashlib import sha256
from json import loads
from pathlib import Path
from statistics import mean, median
from zipfile import ZipFile

from common import to_csv, to_json
from observe import SCENARIOS
from reproduce_army_relief import PRIORITY, audit
from v21_report import analyze, number, pct, rate, table

NA, UNKNOWN = 'not_applicable', 'not_collected'
SEEDS=(2026,2027,2028)
BASELINE_STREAMS=('monthly','cities','factions','convoys','troop-flows','battles','war-plans',
                  'war-quotes','war-quote-groups','shortages','action-capacity','route-changes',
                  'supply-requests','capture-recovery')
TARGETS={'shortage_city_turns':(None,150), 'shortages_per_1000_owned_city_turns':(None,6),
         'grain_missing':(None,75000), 'battles':(150,220), 'convoy_hunger_deaths':(None,5000),
         'small_survival_rate':(30,None)}
LOWER_IS_BETTER={
    'shortage_city_turns','shortages_per_1000_owned_city_turns','grain_missing','convoy_hunger_deaths',
    'army_hunger_losses','other_hunger_losses','army_hunger_per_10000_escorts','army_hunger_per_1000_delivered',
    'ended_above_local_troops','blocked_9_faction_turns','delivery_during_shortage',
    'mean_turn_cpu_seconds','mean_turn_seconds','max_turn_seconds'}
HIGHER_IS_BETTER={'small_survival_rate','army_window_success','army_closed_success','army_efficiency'}


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def archive_prefix(group, seed, months, scenario):
    return f'data/observed/{group}/{seed}/{months}/{scenario}/'


def omit_na_mean(values):
    valid=[value for value in values if isinstance(value,(float,int)) and type(value) is not bool]
    return round(mean(valid),6) if valid else NA


def records(folder,name):
    path=folder/(name+'.csv')
    if path.is_file():
        return [row | {'details':loads(row['details'])} for row in table(folder,name)]


def relief_stats(folder,run):
    hist=records(folder,'army-convoys')
    q=records(folder,'army-requests')
    recovery=records(folder,'war-recovery')
    convoys=defaultdict(list)
    for row in table(folder,'convoys'):
        convoys[row['convoy_id']].append(row)
    classes={name:[] for name in ('army','other')}
    terminal={str(row['id']) for row in run.get('terminal',{}).get('convoy_loads',())}
    for ident,rows in convoys.items():
        dep=next((r for r in rows if r['stage']=='departed'),None)
        if dep:
            kind='other' if dep['target_march'] in ('','null') else 'army'
            classes[kind].append((ident,dep,rows))
    deaths=Counter()
    march_loss=defaultdict(list)
    for row in table(folder,'troop-flows'):
        if row['kind']=='convoy_hunger_deaths':
            deaths[row['reference']]+=int(row['count'])
        if row['kind']=='march_hunger_deaths':
            march_loss[row['reference']].append(int(row['turn']))
    data={}
    for kind,shipments in classes.items():
        estimates=Counter()
        for ident,departure,rows in shipments:
            landed=[r for r in rows if r['stage']=='delivered' and number(r,'actual_grain')>0]
            estimates['arrived']+=bool(landed)
            estimates['sent']+=number(departure,'grain_loaded')
            estimates['delivered']+=sum(number(r,'actual_grain') for r in landed)
            estimates['hunger_losses']+=deaths[ident]
            if ident in terminal:
                estimates['pending']+=1
            else:
                estimates['closed']+=1
                estimates['closed_delivered']+=bool(landed)
                estimates['closed_sent']+=number(departure,'grain_loaded')
                estimates['closed_net_grain']+=sum(number(r,'actual_grain') for r in landed)
            if kind=='army' and landed:
                when=int(landed[0]['turn'])
                estimates['followup_hunger']+=any(when<=t<=when+3 for t in march_loss[departure['target_march']])
        data.update({kind+'_dispatches':len(shipments),**{kind+'_'+name:estimates[name] for name in
                     ('arrived','sent','delivered','hunger_losses','pending','closed','closed_delivered',
                      'closed_sent','closed_net_grain','followup_hunger')},
                     kind+'_window_success':pct(estimates['arrived'],len(shipments)),
                     kind+'_closed_success':pct(estimates['closed_delivered'],estimates['closed']),
                     kind+'_hunger_per_1000_delivered':rate(estimates['hunger_losses'],estimates['delivered'],1000)})
    if hist is None:
        for key in ('escort_troops','escort_mean','escort_light','escort_heavy','efficiency','bags',
                    'wait_days','return_rations','safety_rations','hunger_per_10000_escorts'):
            data['army_'+key]=UNKNOWN
    else:
        observed=[r['details'] for r in hist if r['details']['stage']=='transport_departed']
        if len(observed)!=data['army_dispatches']:
            raise ValueError(f'Army departures do not reconcile {folder}')
        troops=[r['escort_strength'] for r in observed]
        bags=sum(r['initial_bag'] for r in observed)
        final={}
        for r in hist:
            d=r['details']
            final[d['convoy']]=d
        wait_rows=[value['actual_wait_days'] for ident,value in final.items() if str(ident) not in terminal]
        real_new=run['group'] in {'F1','F3'}
        data.update(army_escort_troops=sum(troops),army_escort_mean=omit_na_mean(troops),
                    army_escort_light=sum(n<=500 for n in troops),army_escort_heavy=sum(n>5000 for n in troops),
                    army_efficiency=pct(data['army_delivered'],data['army_sent']+bags),
                    army_bags=bags,army_wait_days=sum(wait_rows),
                    army_return_rations=sum(r['plan']['returning'] for r in observed) if real_new else NA,
                    army_safety_rations=sum(r['plan']['safety'] for r in observed) if real_new else NA,
                    army_hunger_per_10000_escorts=rate(data['army_hunger_losses'],sum(troops),10000))
    new=run['group'] in {'F1','F3'}
    planning=(q or [])
    requests=[r['details'] for r in planning if r['kind']=='relief_quote']
    fulfilled=[r['details'] for r in planning if r['kind']=='relief_handoff']
    counters=Counter()
    # Each source observation carries accumulated counters for its planning
    # pass; take the latest state of that pass before summing the deltas.
    passes={}
    for r in planning:
        if r['kind']=='relief_quote':
            d=r['details']
            passes[r['turn'],d['owner']]=d.get('counters',{})
    for value in passes.values():
        counters.update(value)
    data.update(army_quote_calls=len(requests) if new and q is not None else NA,
                army_quotes_blocked=sum(not r['options'] for r in requests) if new and q is not None else NA,
                army_covered_or_no_need=sum(r['reason']=='army_supplied' for r in requests) if new and q is not None else NA,
                army_quotes_by_reason=dict(Counter(r['reason'] for r in requests if r['reason'])) if new else NA,
                army_actual_handoffs=len(fulfilled) if new else NA,
                army_actual_handoff_shortfall=sum(r['remaining_need'] for r in fulfilled) if new else NA,
                army_reroutes=sum(r['kind']=='relief_replanned' for r in planning) if new else NA,
                army_cancelled=sum(r['kind']=='relief_cancelled' for r in planning) if new else NA,
                army_planning_counts=dict(counters) if new else NA)
    if new and sum(r['grain'] for r in fulfilled)!=data['army_delivered']:
        raise ValueError(f'Army handoff totals mismatch in {folder}')
    war=run['group'] in {'F2','F3'}
    wars=[row['details'] for row in recovery or []]
    assessments=[r['recovery'] for r in wars if r['result']!='deferred']
    chosen={r['plan_id'] for r in wars if r['result']=='deferred'}
    data.update(war_recovery_quotes=len(assessments) if war else NA,
                war_recovery_plans=len({r['plan_id'] for r in wars}) if war else NA,
                war_recovery_deferred=len(chosen) if war else NA,
                war_recovery_mean_months=omit_na_mean(r['months'] for r in assessments) if war else NA,
                war_no_reliable_surplus=sum(r['no_reliable_surplus'] for r in assessments) if war else NA,
                war_necessary_exceptions=sum(r['necessary'] for r in wars if r['result']=='eligible') if war else NA,
                war_multiple_front_quotes=sum(r['other_fronts']>0 for r in assessments) if war else NA,
                war_overlapping_front_quotes=sum(r['overlapping_fronts']>0 for r in assessments) if war else NA,
                war_avg_reserves_assigned=omit_na_mean(r.get('reserves_assigned',0) for r in assessments) if war else NA,
                war_avg_gold_budget=omit_na_mean(r.get('gold_need',0) for r in assessments) if war else NA,
                war_avg_grain_budget=omit_na_mean(r.get('grain_need',0) for r in assessments) if war else NA)
    data['mean_turn_cpu_seconds']=run['performance'].get('mean_turn_cpu_seconds',UNKNOWN)
    return data


def compare_history(original, replay, stream):
    """Exact cell-by-cell comparison after the independently verified identity."""
    left,right=original/(stream+'.csv'),replay/(stream+'.csv')
    if left.read_bytes()==right.read_bytes():
        with left.open(encoding='utf-8') as handle:
            return {'sha256':checksum(left),'rows':sum(1 for _ in handle)-1,'differences':0}
    records_a,records_b=list(table(original,stream)),list(table(replay,stream))
    keys=set(records_a[0])&set(records_b[0]) if records_a and records_b else set()
    diffs=abs(len(records_a)-len(records_b))
    examples=[]
    for i,(a,b) in enumerate(zip(records_a,records_b),1):
        changed=[key for key in keys if a[key]!=b[key]]
        if changed and len(examples)<3:
            examples.append(dict(row=i,keys=sorted(changed)))
        diffs+=len(changed)
    return dict(rows=min(len(records_a),len(records_b)),differences=diffs,examples=examples)


def collect(data,base_tree,archive):
    result,small,manifest,history=[],[],[],[]
    with ZipFile(archive) as bundle:
        hashes={path:checksum for line in bundle.read('sha256.txt').decode().splitlines()
                if line and '  ' in line for checksum,path in [line.split('  ',1)]}

        def record(group, seed, months, scenario):
            base=base_tree/group/str(seed)/str(months)/scenario
            new=data/'observed'/group/str(seed)/str(months)/scenario
            reused=group=='E4' and not (new/'run.json').exists()
            folder=base if reused else new
            run=loads((folder/'run.json').read_text())
            for key,expected in dict(group=group,seed=seed,requested_months=months,scenario=scenario).items():
                if run[key]!=expected:
                    raise ValueError(f'Incorrect {key} in {folder}')
            if run['outcome'] not in ('complete','natural_end'):
                raise ValueError(f'Incomplete selected run at {folder}')
            if run['completed_turns']!=months*3 and run['outcome']!='natural_end':
                raise ValueError(f'Unexpected duration at {folder}')
            if run['parameters']['difficulty']!='normal' or run['parameters']['lifespan']!='historical':
                raise ValueError(f'Different opening configuration at {folder}')
            if group=='E4':
                prefix=archive_prefix(group,seed,months,scenario)
                for path in sorted(base.glob('*')):
                    if path.is_file() and hashes.get(prefix+path.name)!=checksum(path):
                        raise ValueError(f'Historical SHA-256 differs: {path}')
                original=loads((base/'run.json').read_text())
                for key in ('catalog_sha256','start_date','last_date','rule_versions','parameters','completed_turns'):
                    if original[key]!=run[key]:
                        raise ValueError(f'E4 replay changed {key} in {folder}')
                if not reused:
                    files={name:compare_history(base,folder,name) for name in BASELINE_STREAMS}
                    history.append(dict(scenario=scenario,seed=seed,months=months,files=files))
            row,_,small_rows=analyze(folder,run)
            row.update(relief_stats(folder,run))
            result.append(row)
            small.extend(small_rows)
            manifest.append(dict(group=group,scenario=scenario,seed=seed,months=months,
                reused_historical_archive=reused,archive_prefix=archive_prefix(group,seed,months,scenario) if reused else None,
                catalog_sha256=run['catalog_sha256'],head=run['head'],worktree_diff_sha256=run['worktree_diff_sha256'],
                rule_versions=run['rule_versions'],configuration=run.get('v211',UNKNOWN),completed_turns=run['completed_turns'],
                results={path.name:checksum(path) for path in sorted(folder.glob('*')) if path.is_file()}))
            return run

        for months,events in ((60,((seed,scenario) for seed in SEEDS for scenario in SCENARIOS)),
                              (240,((2026,s) for s in ('184-02','208-10')))):
            for seed,scenario in events:
                e4=record('E4',seed,months,scenario)
                candidate=record('F3',seed,months,scenario)
                if e4['catalog_sha256']!=candidate['catalog_sha256'] or e4['start_date']!=candidate['start_date']:
                    raise ValueError(f'Pair opening differs: {scenario}, {seed}')
                if e4.get('v211') and e4['v211']['opening_sha256']!=candidate['v211']['opening_sha256']:
                    raise ValueError(f'Pair opening state differs: {scenario}, {seed}')
                if (seed,scenario) in PRIORITY and months==60:
                    for group in ('F1','F2'):
                        run=record(group,seed,months,scenario)
                        if run['v211']['opening_sha256']!=candidate['v211']['opening_sha256']:
                            raise ValueError(f'Priority opening differs: {group}, {scenario}, {seed}')
    return result,small,manifest,history


def distributions(rows):
    pairs={(r['scenario'],r['seed'],r['group']):r for r in rows if r['months']==60}
    groups={'all':lambda r:True}
    groups.update({scenario:(lambda r,key=scenario:r['scenario']==key) for scenario in SCENARIOS})
    groups.update({str(seed):(lambda r,key=seed:r['seed']==key) for seed in SEEDS})
    summaries=[]
    for scope,choose in groups.items():
        for group in ('E4','F1','F2','F3'):
            subset=[r for r in rows if r['group']==group and r['months']==60 and choose(r)]
            if not subset:
                continue
            for key in subset[0]:
                if key in ('seed','months','completed_turns'):
                    continue
                values=[r[key] for r in subset if type(r[key]) in (int,float)]
                if not values:
                    continue
                samples=[(pairs[r['scenario'],r['seed'],'E4'].get(key),r[key]) for r in subset]
                factor=1 if key in LOWER_IS_BETTER else -1 if key in HIGHER_IS_BETTER else 0
                changes=[(test-control)*factor for control,test in samples
                         if type(control) in (int,float) and type(test) in (int,float)]
                summaries.append(dict(scope=scope,group=group,metric=key,samples=len(values),
                  mean=round(mean(values),6),median=round(median(values),6),minimum=min(values),maximum=max(values),
                  improved=sum(n<0 for n in changes) if factor else NA,
                  clearly_worse=sum(n>0 and n>=max(1,abs(control)*0.1) for (control,test),n in
                     ((p,(p[1]-p[0])*factor) for p in samples if type(p[0]) in (int,float)
                      and type(p[1]) in (int,float))) if factor else NA))
    return summaries


def write(data,baseline_tree,baseline,output):
    rows,small,manifest,history=collect(data,baseline_tree,baseline)
    rows.sort(key=lambda r:(r['months'],r['scenario'],r['seed'],r['group']))
    to_csv(output/'scenario-scores.csv',rows)
    to_csv(output/'small-faction-survival.csv',small)
    to_csv(output/'distributions.csv',distributions(rows))
    selected={r['group']:r for r in rows if r['scenario']=='207-09' and r['seed']==2027 and r['months']==60}
    to_csv(output/'parameter-experiments.csv',[
        dict(group=g,rule_versions=m['rule_versions'],config=m['configuration']['candidate_config'],
             scenario=m['scenario'],seed=m['seed'],months=m['months'],commit=m['head'])
        for m in manifest for g in [m['group']] if not m['reused_historical_archive']
        and (m['seed'],m['scenario']) in PRIORITY and m['months']==60])
    matrices={
        'army-relief-comparison':('army_dispatches','army_arrived','army_window_success','army_closed_success',
                                 'army_followup_hunger','army_hunger_losses','army_delivered','army_sent','army_pending'),
        'escort-strength-comparison':('army_escort_mean','army_escort_troops','army_escort_light','army_escort_heavy'),
        'convoy-hunger-comparison':('army_hunger_losses','other_hunger_losses','army_hunger_per_10000_escorts',
                                   'army_hunger_per_1000_delivered','convoy_hunger_deaths'),
        'convoy-efficiency-comparison':('army_efficiency','army_bags','army_wait_days','army_delivered',
            'closed_delivery_rate','convoy_weather_grain_loss','convoy_route_grain_loss','delivery_during_shortage'),
        'rendezvous-comparison':('army_quote_calls','army_quotes_blocked','army_reroutes','army_actual_handoffs',
                                'army_actual_handoff_shortfall','army_cancelled','army_return_rations','army_safety_rations'),
        'duplicate-supply-requests':('army_covered_or_no_need','army_quotes_by_reason','army_actual_handoffs'),
        'war-recovery-comparison':('war_recovery_quotes','war_recovery_plans','war_recovery_deferred',
            'war_recovery_mean_months','war_no_reliable_surplus','war_necessary_exceptions',
            'war_avg_reserves_assigned','war_avg_gold_budget','war_avg_grain_budget'),
        'multi-front-budget-comparison':('war_multiple_front_quotes','war_overlapping_front_quotes',
                                         'war_recovery_deferred','war_plan_conversion'),
        'war-frequency-comparison':('battles','wars_per_active_faction_year','war_plans','war_plans_dispatched',
                                     'war_plan_conversion','war_necessary_exceptions'),
        'faction-action-capacity-comparison':('blocked_faction_turns','blocked_9_faction_turns','blocked_reasons'),
        'shortage-comparison':('shortage_city_turns','shortages_per_1000_owned_city_turns','grain_missing',
                               'longest_shortage','delivery_during_shortage'),
        'troop-sustainability-comparison':('active_troops','reserve_troops','ended_above_local_troops',
                                          'ended_garrison_grain','battle_troops_lost'),
        'performance-comparison':('simulation_seconds','mean_turn_seconds','max_turn_seconds','mean_turn_cpu_seconds',
                                  'worker_peak_rss_bytes','quote_cache_hit_rate','supply_route_pairs','army_planning_counts'),
    }
    identity=('scenario','seed','months','group')
    for name,fields in matrices.items():
        to_csv(output/(name+'.csv'),[{key:r.get(key,UNKNOWN) for key in (*identity,*fields)} for r in rows])
    to_csv(output/'long-term-economy-comparison.csv',[r for r in rows if r['months']==240])
    keys=(*TARGETS,'army_hunger_losses','other_hunger_losses','army_dispatches','army_arrived','army_delivered',
          'active_troops','reserve_troops','ended_above_local_troops','blocked_9_faction_turns','delivery_during_shortage')
    pairs=[]
    for first in [s for s in rows if s['group']=='E4']:
        last=next(r for r in rows if (r['group'],r['scenario'],r['seed'],r['months'])==
                                  ('F3',first['scenario'],first['seed'],first['months']))
        row={key:first[key] for key in identity[:-1]}
        for key in keys:
            a,b=first[key],last[key]
            row.update({f'{key}_E4':a,f'{key}_F3':b,f'{key}_delta':round(b-a,6)
                        if type(a) in (int,float) and type(b) in (int,float) else NA})
        pairs.append(row)
    to_csv(output/'pairwise.csv',pairs)
    agg={}
    for group in ('E4','F3'):
        group_rows=[r for r in rows if r['months']==60 and r['group']==group]
        if len(group_rows)!=21:
            raise ValueError('Incomplete final matrix')
        subset=[r for r in small if r['months']==60 and r['group']==group]
        agg[group]={k:omit_na_mean(r[k] for r in group_rows) for k in keys}
        agg[group]['small_survival_rate']=pct(sum(r['survived'] for r in subset),len(subset))
        agg[group]['small_survived']=sum(r['survived'] for r in subset)
        agg[group]['small_started']=len(subset)
        agg[group]['army_success_total']=sum(r['army_arrived'] for r in group_rows)
        agg[group]['army_dispatch_total']=sum(r['army_dispatches'] for r in group_rows)
        agg[group]['army_grain_total']=sum(r['army_delivered'] for r in group_rows)
    acceptance={key:(minimum is None or agg['F3'][key]>=minimum)
                    and (maximum is None or agg['F3'][key]<=maximum)
                for key,(minimum,maximum) in TARGETS.items()}
    archive=dict(name=baseline.name,sha256=checksum(baseline),path=str(baseline.resolve()))
    to_json(output/'simulation-manifest.json',dict(baseline=archive,runs=manifest))
    to_json(output/'baseline-replay-parity.json',history)
    to_json(output/'summary.json',dict(aggregates=agg,targets=TARGETS,met=acceptance,
                                      priority_case=selected))
    priority=[r for r in rows if (r['seed'],r['scenario']) in PRIORITY and r['months']==60]
    to_csv(output/'priority-comparison.csv',priority)
    print(agg)
    if any(item['differences'] for replay in history for item in replay['files'].values()):
        raise ValueError('Historical observation rows differ; see baseline-replay-parity.json')


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--baseline-tree',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    write(args.data,args.baseline_tree,args.baseline,args.output)
