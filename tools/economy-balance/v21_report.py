"""Derive V2.1 comparisons from committed observer ledgers and package evidence."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from zipfile import ZipFile, ZIP_DEFLATED

from common import to_csv, to_json
from run_v21_experiments import schedule, STAGES

UNKNOWN = 'not_collected'
NA = 'not_applicable'
MAIN = {
    'shortage_city_turns': ('缺糧城旬','down',350),
    'shortages_per_1000_all_city_turns': ('每千城旬缺糧','down',15),
    'shortages_per_1000_owned_city_turns': ('每千已歸屬城旬缺糧','down',None),
    'grain_missing': ('口糧總缺口','down',200000),
    'battles': ('交戰','range',(150,220)),
    'convoy_hunger_deaths': ('運輸缺糧減員','down',None),
    'delivery_during_shortage': ('仍缺糧時的交付','down',None),
    'longest_shortage': ('最長連續缺糧','down',None),
    'active_troops': ('期末現役兵','down',None),
    'ended_above_local_troops': ('期末超出本地供養的兵力','down',None),
    'blocked_9_faction_turns': ('連續阻塞達九旬的勢力旬','down',None),
    'largest_two_stock_share': ('全圖前兩城庫存佔比 %','context',None),
}
FILES = {
    'shortage-comparison': ('shortage_city_turns','shortages_per_1000_all_city_turns',
        'shortages_per_1000_owned_city_turns','grain_missing','all_city_turns','owned_city_turns',
        'longest_shortage','cities_short_3','cities_short_9','cities_short_30'),
    'grain-distribution-comparison': ('grain_stock','largest_stock_share','largest_two_stock_share',
        'shortage_with_surplus_rate','shortage_with_legal_surplus_rate','shortage_timely_coverage_rate',
        'relief_arrival_spell_count','relief_arrival_spell_resolved_after_three_turns','relief_arrival_spell_resolution_rate',
        'strategic_surplus','known_timely_requests'),
    'strategic-reserve-comparison': ('strategic_surplus','strategic_reserve_met','strategic_reserve_observed',
        'emergency_released_reserve','emergency_reserve_release_count'),
    'convoy-efficiency-comparison': ('supply_requests','supply_requests_dispatched','supply_requests_failed',
        'convoy_dispatched','convoy_arrived','convoy_grain_sent','convoy_grain_arrived','window_delivery_rate',
        'closed_convoys','closed_convoy_dispatched_grain','closed_convoy_delivered_grain','closed_delivery_rate',
        'pending_convoys','pending_convoy_grain','convoy_rations','convoy_extra_rations','convoy_route_grain_loss',
        'convoy_cargo_rations','convoy_weather_grain_loss','convoy_hunger_deaths',
        'convoy_route_hazard_deaths','delivery_during_shortage','net_delivery_deviation','convoy_reroutes',
        'aborted_for_supply','return_interrupted_for_supply','supply_failure_reasons'),
    'troop-sustainability-comparison': ('active_troops','stationed_troops','away_troops','reserve_troops',
        'ended_above_local_troops','ended_above_local_cities','ended_garrison_grain',
        'battle_troops_lost','march_hunger_losses','convoy_hunger_deaths','city_shortage_troops',
        'route_hazard_deaths','active_transferred'),
    'recruitment-comparison': ('manual_recruitment','delegated_recruitment','ai_recruitment',
        'natural_monthly_reserves','entered_active','postbattle_recruitment','raised_troops'),
    'war-budget-comparison': ('battles','wars_per_active_faction_year','active_faction_turns','war_quote_evaluations',
        'war_quotes_blocked','war_plans','war_plans_dispatched','war_plan_conversion','war_hard_reasons',
        'dynamic_days_mean','battle_days','battle_grain_rations','battle_grain_burned',
        'march_rations','postbattle_recruit_gold','postbattle_recruit_grain'),
    'faction-action-capacity-comparison': ('blocked_faction_turns','blocked_3_faction_turns','blocked_9_faction_turns',
        'longest_faction_block','peaceful_faction_turns','blocked_reasons'),
    'performance-comparison': ('simulation_seconds','mean_turn_seconds','max_turn_seconds','worker_peak_rss_bytes',
        'quoted_paths','quote_cache_hit_rate','supply_route_pairs','war_quote_evaluations'),
    'long-term-economy-comparison': tuple(MAIN) + ('grain_stock','reserve_troops','emergency_grain_bought',
        'ended_above_local_cities','small_opened','small_survived','small_survival_rate'),
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def table(root, name):
    path = root / f'{name}.csv'
    if not path.is_file():
        raise ValueError(f'Missing observed table {path}')
    with path.open(encoding='utf-8', newline='') as file:
        yield from csv.DictReader(file)


def number(row, key):
    value = row.get(key, UNKNOWN)
    return int(value) if str(value).lstrip('-').isdigit() else value


def optional(value):
    return None if value in ('null', '', UNKNOWN, NA) else json.loads(value)


def pct(num, den):
    return round(100*num/den, 4) if den else NA


def rate(num, den, unit):
    return round(unit*num/den, 4) if type(den) is int and den else UNKNOWN


def latest_snapshots(folder, name, at, key):
    return {row[key]: row for row in table(folder, name) if int(row['elapsed_turns']) == at}


def group_identity(run):
    return dict(group=run['group'], seed=run['seed'], scenario=run['scenario'], months=run['requested_months'],
                completed_turns=run['completed_turns'], outcome=run['outcome'])


def analyze(folder, run):
    """Summarize actual settlements. Empty streams with a header are valid zeros."""
    identity = group_identity(run)
    snapshots = list(table(folder,'monthly'))
    last = snapshots[-1]
    elapsed = identity['completed_turns']
    cities = latest_snapshots(folder,'cities',elapsed,'city')
    sampled_streak = [number(r,'max_food_shortage_streak') for r in cities.values()]
    warehouse = sorted((number(r,'grain_stock') for r in cities.values()), reverse=True)
    grain_stock = sum(warehouse)
    factions = list(table(folder, 'factions'))
    initial = {r['faction']:r for r in factions if number(r,'elapsed_turns') == 0 and r['faction']!='neutral'}
    ending = {r['faction']:r for r in factions if number(r,'elapsed_turns') == elapsed and r['faction']!='neutral'}
    city_groups = defaultdict(list)
    for city in cities.values():
        if city['owner']!='neutral':
            city_groups[city['owner']].append(city)

    def row_surplus(city):
        target = number(city,'strategic_reserve_target')
        return max(0,number(city,'grain_stock')-target) if type(target) is int else 0

    faction_rows, small_rows = [], []
    for owner in sorted(set(initial)|set(ending)):
        a,b = initial.get(owner,{}),ending.get(owner,{})
        squad = city_groups[owner]
        stock = number(b,'grain_stock') if b else 0
        largest = sorted((number(city,'grain_stock') for city in squad),reverse=True)
        faction_rows.append(dict(identity,faction=owner,opening_cities=number(a,'cities') if a else 0,
            ending_cities=number(b,'cities') if b else 0,grain_stock=stock,gold_stock=number(b,'gold_stock') if b else 0,
            monthly_regular_grain=number(b,'monthly_regular_grain') if b else 0,
            fixed_grain=number(b,'monthly_fixed_grain') if b else 0,
            active_troops=number(b,'active_troops') if b else 0,reserves=number(b,'reserves') if b else 0,
            stationed_troops=sum(number(city,'stationed_active_troops') for city in squad),
            strategic_surplus=sum(map(row_surplus,squad)),top_stock_share=pct(sum(largest[:1]),stock),
            top_two_stock_share=pct(sum(largest[:2]),stock)))
        if a and 1<=number(a,'cities')<=3:
            small_rows.append(dict(identity,faction=owner,opening_cities=number(a,'cities'),
                                   final_cities=number(b,'cities') if b else 0,
                                   survived=bool(b and number(b,'cities')>0)))

    shortage_rows = list(table(folder,'shortages'))
    if sum(number(r,'missing') for r in shortage_rows) != number(last,'rations_missing'):
        raise ValueError(f'Shortage grain does not reconcile in {folder}')
    if len(shortage_rows) != number(last,'unpaid_city_turns'):
        raise ValueError(f'Shortage count does not reconcile in {folder}')
    shortage_by_city = defaultdict(set)
    def by_turn(row, shift=0):
        return int(row['turn']) + shift
    for row in shortage_rows:
        shortage_by_city[row['city']].add(by_turn(row,1))
    requests = list(table(folder,'supply-requests'))
    emergency = [r for r in requests if r['channel']=='city_emergency']
    routed = [r for r in emergency if str(r['can_arrive_before_zero_grain']).isdigit()]
    all_timed = sum(number(row,'requested_grain') for row in routed
                    if type(number(row,'requested_grain')) is int)
    can_supply = sum(min(number(row,'requested_grain'),number(row,'can_arrive_before_zero_grain'))
                     for row in routed if type(number(row,'requested_grain')) is int)
    failures = Counter()
    for r in emergency:
        reason=optional(r['reason']) if r['reason'].startswith(('{','[','"')) else r['reason']
        if isinstance(reason,dict):
            if reason.get('primary'):
                failures[reason['primary']]+=1
            failures.update(reason.get('blockers',{}))
        elif isinstance(reason,list):
            failures.update(reason)
        elif r['result']=='failed':
            failures[reason]+=1
    allocations=[a for row in emergency for a in (optional(row['delivery_allocations']) or [])]
    v21 = run.get('rule_versions',{}).get('ai_strategy') in (21,211)
    rescue_ids={str(i) for r in emergency for i in (optional(r['convoy_ids']) or [])}
    voyages=defaultdict(list)
    for row in table(folder,'convoys'):
        voyages[row['convoy_id']].append(row)
    closed=departed=delivered=pending=closed_gross=closed_net=0
    deviations, relief = [], []
    for ident, events in voyages.items():
        out=[r for r in events if r['stage']=='departed']
        if not out:
            continue
        if len(out)!=1:
            raise ValueError(f'Duplicate {ident} dispatch in {folder}')
        arrival=[r for r in events if r['stage']=='delivered']
        if len(arrival)>1:
            raise ValueError(f'Duplicate {ident} delivery in {folder}')
        sent=number(out[0],'grain_loaded')
        landed=number(arrival[0],'actual_grain') if arrival else 0
        departed+=sent
        delivered+=landed
        finished=bool(arrival or any(r['stage'] in ('docked','abandoned') for r in events))
        if finished:
            closed+=1
            closed_gross+=sent
            closed_net+=landed
        else:
            pending+=1
        if arrival:
            a=arrival[0]
            deviations.append(landed-number(out[0],'expected_grain'))
            cast=shortage_by_city[a['target']]
            arrival_turn=by_turn(a)
            if ident in rescue_ids and arrival_turn in cast and arrival_turn+3<=elapsed+1:
                relief.append(not any(n in cast for n in range(arrival_turn+1,arrival_turn+4)))
    if departed != number(last,'convoy_grain_sent') or delivered != number(last,'convoy_grain_arrived'):
        raise ValueError(f'Observed voyage totals do not match settled totals in {folder}: {(departed,delivered)}')

    flow=Counter()
    for entry in table(folder,'troop-flows'):
        flow[entry['kind']]+=number(entry,'count')
    routes=Counter(row['status'] for row in table(folder,'route-changes') if row['unit_kind']=='convoy')
    war=Counter()
    quote_count=blocked=0
    battle_stock=[]
    for row in table(folder,'war-quotes'):
        quote_count+=1
        if row['outcome']=='blocked':
            blocked+=1
            war.update(optional(row['reasons']) or [])
        budget=optional(row['budget'])
        if budget and 'battle_days' in budget and row['outcome']=='passed':
            battle_stock.append(budget['battle_days'])
    war_plans=defaultdict(set)
    for row in table(folder,'war-plans'):
        war_plans[row['stage']].add(row['plan_id'])
    actions=Counter()
    action_reasons=Counter()
    max_block=0
    for row in table(folder,'action-capacity'):
        length=number(row,'no_action_streak')
        max_block=max(max_block,length)
        actions[row['status']]+=1
        if length>=3:
            actions['three']+=1
        if length>=9:
            actions['nine']+=1
        if row['status']=='blocked':
            action_reasons.update(optional(row['reasons']) or [])
    q=run.get('performance',{})
    paths=q.get('route_queries',{})
    query_count=paths.get('ai_quote_queries',UNKNOWN)
    convoy_base=number(last,'convoy_base_rations')
    terminal=run.get('terminal',{})
    staged=sum(number(city,'stationed_active_troops') for city in cities.values())
    over=[number(city,'stationed_troops_above_sustainable') for city in cities.values()
          if city['owner']!='neutral']
    survives=sum(row['survived'] for row in small_rows)
    data=dict(identity,
        shortage_city_turns=len(shortage_rows), grain_missing=number(last,'rations_missing'),
        all_city_turns=number(last,'all_city_turns'), owned_city_turns=number(last,'owned_city_turns'),
        shortages_per_1000_all_city_turns=rate(len(shortage_rows),number(last,'all_city_turns'),1000),
        shortages_per_1000_owned_city_turns=rate(len(shortage_rows),number(last,'owned_city_turns'),1000),
        longest_shortage=max(sampled_streak,default=0),
        **{f'cities_short_{n}':sum(x>n for x in sampled_streak) for n in (3,9,30)},
        grain_stock=grain_stock, largest_stock_share=pct(sum(warehouse[:1]),grain_stock),
        largest_two_stock_share=pct(sum(warehouse[:2]),grain_stock),
        shortage_with_surplus_rate=pct(sum(bool((optional(r['reserve_surplus']) or {}).get('1'))
                                           for r in shortage_rows),len(shortage_rows)),
        shortage_with_legal_surplus_rate=pct(sum(bool((optional(r['legal_route_surplus']) or {}).get('1'))
                                           for r in shortage_rows),len(shortage_rows)),
        shortage_timely_coverage_rate=pct(can_supply,all_timed),
        known_timely_requests=len(routed), relief_arrival_spell_count=len(relief),
        relief_arrival_spell_resolved_after_three_turns=sum(relief),relief_arrival_spell_resolution_rate=pct(sum(relief),len(relief)),
        strategic_surplus=sum(map(row_surplus,cities.values())),
        strategic_reserve_met=number(last,'strategic_reserve_met'),
        strategic_reserve_observed=number(last,'strategic_reserve_observed'),
        emergency_released_reserve=sum(a.get('released_reserve',0) for a in allocations) if v21 else NA,
        emergency_reserve_release_count=sum(a.get('released_reserve',0)>0 for a in allocations) if v21 else NA,
        supply_requests=len(emergency),supply_requests_dispatched=sum(r['result']=='dispatched' for r in emergency),
        supply_requests_failed=sum(r['result']=='failed' for r in emergency),
        window_delivery_rate=pct(delivered,departed),closed_convoys=closed,
        closed_convoy_dispatched_grain=closed_gross, closed_convoy_delivered_grain=closed_net,
        closed_delivery_rate=pct(closed_net,closed_gross),pending_convoys=pending,
        pending_convoy_grain=sum(row['cargo_grain'] for row in terminal['convoy_loads'])
            if 'convoy_loads' in terminal else UNKNOWN,
        convoy_extra_rations=max(0,number(last,'convoy_rations')-convoy_base) if type(convoy_base) is int else UNKNOWN,
        convoy_hunger_deaths=flow['convoy_hunger_deaths'],
        convoy_route_hazard_deaths=flow['convoy_route_hazard_deaths'],
        delivery_during_shortage=number(last,'convoy_late_arrivals'),
        net_delivery_deviation=round(mean(deviations),3) if deviations else NA,
        convoy_reroutes=routes['rerouted'],aborted_for_supply=routes['aborted_for_supply'],
        return_interrupted_for_supply=routes['return_interrupted_for_supply'],supply_failure_reasons=dict(failures),
        active_troops=number(last,'active_troops'),stationed_troops=staged,
        away_troops=number(last,'active_troops')-staged,reserve_troops=number(last,'reserves'),
        ended_above_local_troops=sum(over),ended_above_local_cities=sum(x>0 for x in over),
        ended_garrison_grain=terminal.get('monthly_garrison_grain',UNKNOWN),
        city_shortage_troops=flow['city_shortage_deaths'],route_hazard_deaths=sum(n for k,n in flow.items() if 'hazard_deaths' in k),
        active_transferred=sum(number(r,'active') for r in table(folder,'troop-flows') if r['kind']=='transfer_departed'),
        manual_recruitment=flow['manual_recruitment'],delegated_recruitment=flow['delegated_recruitment'],
        ai_recruitment=flow['ai_direct_recruitment'],natural_monthly_reserves=flow['natural_monthly_reserves'],
        entered_active=flow['reserve_allocation'] if terminal else UNKNOWN,postbattle_recruitment=flow['postbattle_recruitment'],
        wars_per_active_faction_year=rate(number(last,'battles'),number(last,'active_faction_turns'),36),
        war_quote_evaluations=quote_count,war_quotes_blocked=blocked,war_plans=len(war_plans['assembled']),
        war_plans_dispatched=len(war_plans['dispatched']),war_plan_conversion=pct(len(war_plans['dispatched']),len(war_plans['assembled'])),
        war_hard_reasons=dict(war),dynamic_days_mean=round(mean(battle_stock),4) if battle_stock else (UNKNOWN if run['group']=='E4' else NA),
        blocked_faction_turns=actions['blocked'],blocked_3_faction_turns=actions['three'],
        blocked_9_faction_turns=actions['nine'],longest_faction_block=max_block,
        peaceful_faction_turns=actions['peace_or_no_unmet_need']+actions['resting_or_building_reserves'],
        blocked_reasons=dict(action_reasons),small_opened=len(small_rows),small_survived=survives,
        small_survival_rate=pct(survives,len(small_rows)),simulation_seconds=run['seconds'],
        mean_turn_seconds=q.get('mean_turn_seconds',UNKNOWN),max_turn_seconds=q.get('max_turn_seconds',UNKNOWN),
        worker_peak_rss_bytes=q.get('worker_peak_rss_bytes',UNKNOWN),quoted_paths=query_count,
        quote_cache_hit_rate=pct(paths.get('ai_quote_cache_hits',0),query_count) if type(query_count) is int else UNKNOWN,
        supply_route_pairs=paths.get('supply_route_pairs',UNKNOWN))
    for metrics in FILES.values():
        for metric in metrics:
            if metric not in data:
                data[metric]=number(last,metric)
    return data, faction_rows, small_rows


def distribution(values):
    items=[x for x in values if type(x) in (int,float)]
    if not items:
        return dict(n=0,mean=NA,median=NA,min=NA,max=NA)
    return dict(n=len(items),mean=round(mean(items),4),median=median(items),min=min(items),max=max(items))


def write(file, rows):
    if rows:
        to_csv(file, rows)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--tables-only',action='store_true',help='Validate and export tables before writing documentation')
    parser.add_argument('--docs',type=Path,required=True)
    parser.add_argument('--preflight',type=Path,required=True)
    parser.add_argument('--references',type=Path,required=True)
    parser.add_argument('--candidate-root',type=Path,
        help='Use this observation root for E runs and retain the original D control')
    args=parser.parse_args()
    source=args.root/'observed'
    comparisons=args.root/'comparisons'
    comparisons.mkdir(parents=True,exist_ok=True)
    required=set(schedule('paired',STAGES)+schedule('pilot',STAGES)+schedule('long',STAGES))
    groups,factions,small=[],[],[]
    found={}
    files={}
    data_files={}
    candidate=args.candidate_root/'observed' if args.candidate_root else source
    controls=list(source.glob('D/*/*/*/run.json'))
    candidates=list(candidate.glob('E*/*/*/*/run.json'))
    for path in sorted(controls+candidates):
        run=json.loads(path.read_text())
        key=(run['group'],run['seed'],run['requested_months'],run['scenario'])
        if key not in required or run['outcome'] not in ('complete','natural_end'):
            continue
        row, by_faction, seats=analyze(path.parent,run)
        groups.append(row)
        factions.extend(by_faction)
        small.extend(seats)
        found[key]=run
        files[key]=path
        relative=Path(run['group'])/str(run['seed'])/str(run['requested_months'])/run['scenario']
        for child in sorted(path.parent.glob('*')):
            if child.is_file() and child.suffix in ('.csv','.json'):
                data_files['data/observed/'+str(relative/child.name)]=child
    if not groups:
        raise ValueError('There are no completed observations to report')
    metrics_index={(r['group'],r['seed'],r['months'],r['scenario']):r for r in groups}
    keys=('group','seed','scenario','months','completed_turns','outcome')
    write(comparisons/'faction-economy-comparison.csv',factions)
    write(comparisons/'small-faction-survival.csv',small)
    for file, metrics in FILES.items():
        rows=[{k:r[k] for k in (*keys,*metrics)} for r in groups
              if file != 'long-term-economy-comparison' or r['months']==240]
        write(comparisons/(file+'.csv'),rows)
    pairs=[]
    for (group,seed,months,scenario),e in sorted(metrics_index.items()):
        d=metrics_index.get(('D',seed,months,scenario))
        if group=='D' or d is None:
            continue
        dr,er=found['D',seed,months,scenario],found[group,seed,months,scenario]
        for field in ('catalog_sha256','parameters','telemetry','rule_versions'):
            a,b=dr[field],er[field]
            if field=='telemetry':
                a,b=a['config'],b['config']
            if field=='rule_versions':
                a={key:value for key,value in a.items() if key!='ai_strategy'}
                b={key:value for key,value in b.items() if key!='ai_strategy'}
            if a!=b:
                raise ValueError(f'{field} differs in comparison {scenario}/{seed}/{group}')
        record={k:e[k] for k in keys}
        for metric in MAIN:
            bv,cv=d[metric],e[metric]
            record.update({metric+'_d':bv,metric+'_e':cv,
                           metric+'_delta':round(cv-bv,6) if type(bv) in (int,float) and type(cv) in (int,float) else NA})
        pairs.append(record)
    write(comparisons/'pairwise.csv',pairs)

    bins=defaultdict(list)
    for r in groups:
        if r['months']==60:
            for bucket,name in (('all','all'),('scenario',r['scenario']),('seed',str(r['seed']))):
                bins[r['group'],bucket,name].append(r)
    aggregates=[]
    for (group,bucket,name), rows in sorted(bins.items()):
        for metric in MAIN:
            aggregates.append(dict(group=group,dimension=bucket,value=name,metric=metric,
                **distribution(r[metric] for r in rows)))
    write(comparisons/'distributions.csv',aggregates)
    write(comparisons/'scenario-scores.csv',[{k:r[k] for k in (*keys,*MAIN,'small_opened','small_survived','small_survival_rate')}
                                           for r in groups])
    wave_counts=Counter((r['group'],r['months']) for r in groups)
    valid_pairs=[r for r in pairs if r['group']=='E4' and r['months']==60]
    summary=[dict(metric=key,label=label,target=target,
        d=distribution(r[key+'_d'] for r in valid_pairs), e=distribution(r[key+'_e'] for r in valid_pairs),
        improved=sum(r[key+'_delta']<0 for r in valid_pairs if type(r[key+'_delta']) in (int,float))
                 if direction=='down' else NA) for key,(label,direction,target) in MAIN.items()]
    seats={(g,m):dict(opened=sum(row['small_opened'] for row in groups if (row['group'],row['months'])==(g,m)),
           survived=sum(row['small_survived'] for row in groups if (row['group'],row['months'])==(g,m)))
           for g,m in wave_counts}
    to_json(comparisons/'simulation-manifest.json',dict(schema='tk2-logistics-v21-simulation-v1',
        completed=[dict(run,run_json_sha256=digest(files[g,seed,months,scenario]))
            for (g,seed,months,scenario),run in sorted(found.items())],
        missing=[dict(group=g,seed=s,months=m,scenario=c) for g,s,m,c in sorted(required-found.keys())],
        prior_evidence=json.loads(args.references.read_text())))
    to_json(comparisons/'summary.json',dict(paired_runs=len(valid_pairs),main=summary,
        counts=[dict(group=g,months=m,runs=wave_counts[g,m],small=seats[g,m]) for g,m in sorted(wave_counts)],
        long_pairs=[r for r in pairs if r['months']==240]))
    to_json(comparisons/'validation-manifest.json',dict(schema='tk2-logistics-v21-validation-v1',
        runs=len(found),expected=len(required),reference_count=len(json.loads(args.references.read_text())),
        test_evidence=sorted(p.name for p in args.preflight.iterdir() if p.is_file()),
        comparisons=sorted(p.name for p in comparisons.glob('*.csv'))))
    data_files.update({'data/'+p.name:p for p in comparisons.iterdir() if p.is_file()})
    if args.tables_only:
        print(json.dumps(dict(tables=str(comparisons),completed=len(found),expected=len(required),pairs=len(valid_pairs))))
        return
    supplemental=args.root/'supplemental'
    data_files.update({'data/supplemental/'+str(p.relative_to(supplemental)):p
                       for p in supplemental.rglob('*') if p.is_file() and p.suffix in ('.csv','.json')})
    data_files.update({'docs/'+p.name:p for p in args.docs.glob('*.md')})
    data_files.update({'checks/'+p.name:p for p in args.preflight.iterdir() if p.is_file()})
    args.archive.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(args.archive,'w',ZIP_DEFLATED,compresslevel=6) as archive:
        checks=[]
        for relative,p in sorted(data_files.items()):
            archive.write(p,relative)
            checks.append(f'{digest(p)}  {relative}\n')
        archive.writestr('sha256.txt',''.join(checks))
    print(json.dumps(dict(archive=str(args.archive),sha256=digest(args.archive),
                          completed=len(found),expected=len(required),pairs=len(valid_pairs))))


if __name__=='__main__':
    main()
