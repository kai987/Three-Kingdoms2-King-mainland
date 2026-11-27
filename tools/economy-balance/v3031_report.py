"""Reconcile V3.0.3.1 cohorts with exact archived C0/C4 controls."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from shutil import copyfile

from common import to_csv, to_json
from v302_report import KEYS, csv_file_rows, jsonl, pct
from v3021_report import file_sha, output, read
from v303_report import GUARDS, composition, labels, route_modes, transport
from v3031_experiments import matrix, options

IDENTITY = (*KEYS, 'economy_background', 'group')
REPORTS = ('transport-mode-throughput','officer-turnover-comparison','origin-concurrency-usage',
           'convoy-hunger-comparison','convoy-return-safety','comparable-dispatch-deadlines',
           'winter-army-supply-comparison','performance-comparison','transport-capacity-blockers')
FIXED_KEYS = {
    'capacity-counterfactual.csv': ('scenario','strategy','start_turn','checkpoint_sha256',
                                   'owner','source','original_convoy','replay_end_turn'),
    'transport-capability-funnel.csv': ('scenario','strategy','turn','checkpoint_sha256','owner',
                                       'target','seed','weather','deadline_turn','first_uncovered_grain',
                                       'first_uncovered_in','l5_replay_end_turn'),
}


def catalog_runs(args):
    selected = {}
    archived = read(args.prior/'data/simulation-manifest.json')['simulations']
    planned = [(*case, 'G1') for case in matrix(('five','long','holdout'),('D1','D2'),'G1')]
    planned += [(*case,'G4') for case in matrix(('five',),('D1','D2'),'G4')]
    required = {(w,scene,seed,p,weather,m,b,g) for w,g,seed,scene,p,weather,m,b in planned}
    roots = {'historical':args.historical, 'reviewed':[args.predecessor/'reviewed'],
             'final':[args.predecessor/'final']}
    metadata, missing = [], []
    frozen = (args.build/'frozen-source.txt').read_text().strip()
    for path in args.build.glob('G*/observed/*/*/*/*/*/*/*/run-v302.json'):
        run = read(path)
        key = tuple(run[field] for field in IDENTITY)
        if key not in required:
            continue
        if (run['outcome'] not in ('complete','natural_end') or run['source']!=frozen
                or run['head']!=frozen or run['transport_capacity_options']!=options(run['group'])
                or run['worktree_diff_sha256']!='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'):
            raise ValueError(f'Invalid current cohort: {key}')
        selected[key] = run,path.parent
        metadata.append(dict(labels(run),input='current',relative_path=path.relative_to(args.build).as_posix(),
            run_sha256=file_sha(path),source=run['source'],tree_sha256=run['tree_sha256'],map_sha256=run['map_sha256'],
            scenario_sha256=run['catalog_sha256'],weather_seed=run['weather_seed'],
            options=run['transport_capacity_options'],rules=run['rule_versions'],parameters=run['parameters'],
            completed_turns=run['completed_turns'],status=run['outcome']))
    keys = {key[:-1] for key in required}
    for entry in archived:
        group = {'C0':'D0','C4':'D3'}.get(entry['group'])
        key = tuple(entry[field] for field in IDENTITY[:-1])
        if group is None or key not in keys:
            continue
        relative = entry['relative_path']
        candidates = [root/relative/'run-v302.json' for root in roots[entry['input']]]
        path = next((p for p in candidates if p.is_file() and file_sha(p)==entry['run_sha256']),None)
        if path is None:
            missing.append(dict(key=key,group=group,detail='archived_file_missing',expected=entry['run_sha256']))
            continue
        old = read(path)
        control = selected.get((*key,'D1'))
        identity = ('scenario','seed','strategy','weather','weather_seed','map_sha256','catalog_sha256',
                    'rule_versions','reserve_options')
        def rules(run):
            return {k:v for k,v in run['rule_versions'].items() if k!='transport_capacity_rules_version'}
        if control and (any(old[k]!=control[0][k] for k in identity if k!='rule_versions')
                        or rules(old)!=rules(control[0])):
            raise ValueError(f'Mismatched archived control: {key} {group}')
        run = dict(old,group=group,wave=entry['wave'],economy_background=entry['economy_background'])
        run.setdefault('transport_capacity_options',entry['transport_capacity_options'])
        selected[(*key,group)] = run,path.parent
        metadata.append(dict(entry,group=group,input='historical',original_group=entry['group'],
                             status=old['outcome']))
    manifest = read(args.prior/'sources/historical-economic-references.json')
    for old in manifest:
        if old['group']!='G0' or old['comparison_status']!='verified_historical_reference':
            continue
        wave = 'long' if old['wave']=='long' else 'five'
        key = (wave, old['scenario'], old['seed'], old['strategy'], old['weather'], old['requested_months'])
        for root in args.historical:
            path = root/old['relative_path']/'run-v302.json'
            if path.is_file() and file_sha(path)==old['run_sha256']:
                run = dict(read(path),group='historical-G0',wave=wave,economy_background='G0')
                selected[(*key,'G0','historical-G0')] = run,path.parent
                metadata.append(dict(old,input='historical-G0',group='historical-G0',
                                     original_group='G0',status=run['outcome']))
                break
    missing.extend(dict(key=key,detail='current_not_completed') for key in sorted(required-selected.keys()))
    return selected,metadata,missing,required


def read_slots(run,folder,targets):
    stream = folder/'transport-capacity-events.jsonl.gz'
    if not stream.is_file():
        return
    departure,terminal,delivery={},{},{}
    for row in jsonl(stream):
        ident=row.get('id')
        if row['event']=='departure':
            departure[ident]=row
        elif row['event']=='terminal':
            terminal[ident]=row
        elif row['event']=='delivery':
            delivery[ident]=row
    urgent = folder/'urgent-slot-observations.jsonl.gz'
    needs = list(jsonl(urgent)) if urgent.is_file() else []
    military = {row['convoy'] for row in needs if row['convoy'] is not None
                and (row['seasonal'] or row['deadline_turns'] is not None or row['protected_officers'])}
    def purpose(ident):
        if ident in military:
            return 'military_city'
        return departure.get(ident,{}).get('purpose','not_observed')
    people = defaultdict(Counter)
    for row in csv_file_rows(folder/'convoy-resolution-daily.csv.gz'):
        person = people[int(row['convoy_id'])]
        person.update(officer_days=int(row['current_officers']),clerk_days=int(row['current_civil_staff']),
                      escort_troop_days=int(row['current_escort']))
    scope = labels(run)
    totals = defaultdict(Counter)
    if run['group'] in ('D1','D2'):
        limit=2 if run['group']=='D2' else 1
        targets['observed-origin-account'].append(dict(scope,departures=len(departure),activity_limit=limit,
            over_activity_limit=sum(row['active']>limit for row in departure.values()),
            over_turn_limit=sum(row['dispatch_count']>1 for row in departure.values())))
    for ident,row in departure.items():
        name = purpose(ident)
        person = people[ident]
        end = terminal.get(ident)
        closed = end['end_tick'] if end else run['completed_turns']*10
        start = (row['turn']-1)*10
        committed_days = max(0,closed-start)
        hold = 0 if not end or end['reusable_turn'] is None else max(0,(end['reusable_turn']-1)*10-closed)
        current=totals[name]
        net=delivery.get(ident,{}).get('cargo',{}).get('grain',0)
        crew={type(officer) for officer in row['officers']}
        cooldown=hold*len(end['received_officers']) if end else 0
        current.update(departures=1, second_departures=row['active']==2, origin_slot_days=committed_days,
            officer_days=person['officer_days'],clerk_days=person['clerk_days'],escort_troop_days=person['escort_troop_days'],
            officer_cooldown_days=0 if not end else hold*sum(type(i) is int for i in end['received_officers']),
            clerk_cooldown_days=0 if not end else hold*sum(type(i) is str for i in end['received_officers']),
            command_books=row['command_books'],actual_delivered=net,
            military_only_grain=net if crew=={int} else 0,
            clerk_only_grain=net if crew=={str} else 0,mixed_crew_grain=net if len(crew)>1 else 0,
            military_only_days=person['officer_days']+cooldown if crew=={int} else 0,
            clerk_only_days=person['clerk_days']+cooldown if crew=={str} else 0,
            closed=int(bool(end)),complete_cycle_days=committed_days if end else 0)
        if row['active']==2:
            targets['origin-slot-occupation'].append(dict(scope,convoy=ident,source=row['source'],target=row['target'],
                purpose=name,dispatch_turn=row['turn'],arrival_turn=delivery.get(ident,{}).get('turn'),
                occupancy_days=committed_days,right_censored=end is None))
    for name,counts in totals.items():
        targets['origin-slot-purpose'].append(dict(scope,purpose=name,**counts))
    for request in needs:
        if not (request['seasonal'] or request['deadline_turns'] is not None or request['protected_officers']):
            continue
        for row in request['blocked']:
            occupants=row['convoys']
            occupied_purposes=[purpose(item['id']) for item in occupants]
            lower=any(mark in ('ordinary','regional','strategic') for mark in occupied_purposes)
            horizon=request['deadline_turns']
            same_demand=any(departure.get(piece['id'],{}).get('target')==request['target'] for piece in occupants)
            evidence=dict(scope,turn=request['turn'],source=row['source'],target=request['target'],
                deadline=None if horizon is None else request['turn']+horizon,seasonal=request['seasonal'],
                shared_limit=row['reason'],convoy_ids=[item['id'] for item in occupants],
                occupied_purposes=occupied_purposes,source_stock=row['stock'],actual_request_success=request['sent'],
                other_eligibility_checked=False,demand_destination_overlap=same_demand)
            targets['urgent-dispatch-blockers'].append(evidence)
            if lower and not request['sent']:
                targets['dispatch-priority-conflicts'].append(evidence)
    totals_row = Counter()
    for tally in totals.values():
        totals_row.update(tally)
    targets['officer-occupation-comparison'].append(dict(scope,**totals_row))


def compare(scores):
    identities = {tuple(row[k] for k in IDENTITY):row for row in scores}
    for key,after in sorted(identities.items()):
        group=key[-1]
        controls={'D1':('D0','historical-G0'), 'D2':('D0','D1','historical-G0'),
                  'D3':('D0','D2','historical-G0')}.get(group,())
        for control in controls:
            base = identities.get((*key[:-1],control))
            if control=='historical-G0':
                base=identities.get((*key[:-2],'G0',control))
            if base is None or base['completed_turns']!=after['completed_turns']:
                continue
            for name in sorted(after.keys() & base.keys() - set(IDENTITY)):
                a,b=base[name],after[name]
                if type(a) not in (int,float) or type(b) not in (int,float):
                    continue
                shift=round(b-a,8)
                percent=pct(shift,a)
                alert=False
                if name in GUARDS:
                    limit,kind=GUARDS[name]
                    alert=(percent>limit if percent is not None else b>0) if kind=='percent_up' else shift < -limit
                yield dict(zip(IDENTITY,key),baseline=control,metric=name,before=a,after=b,
                           change=shift,change_percent=percent,warning=alert)


def fixed_results(args,out):
    results=defaultdict(Counter)
    for filename,identity in FIXED_KEYS.items():
        current=args.build/'fixed'/filename
        rows=list(csv_file_rows(current))
        for old in csv_file_rows(args.prior/'data'/filename):
            if old['group'] in ('C0','C4'):
                rows.append(dict(old,group={'C0':'D0','C4':'D3'}[old['group']]))
        by_group=defaultdict(Counter)
        for row in rows:
            by_group[row['group']][tuple(row[key] for key in identity)]+=1
        expected=23 if filename.startswith('capacity') else 89
        base=by_group['D1']
        if (set(by_group)!={'D0','D1','D2','D3'} or len(base)!=expected
                or sum(base.values())!=expected or any(keys!=base for keys in by_group.values())):
            raise ValueError(f'Expected {expected} independently matched observations per group in {filename}')
        output(out/filename,rows)
        for row in rows:
            stats=results[row['group']]
            if filename.startswith('capacity'):
                stats.update(returning=1,qualified=row['donor_qualified']=='true',
                    timely=bool(json.loads(row['timely_quotes'])),actual_source=bool(json.loads(row['actual_shipments'])))
            else:
                if row['l5_actual_reception']=='null':
                    stats['censored']+=1
                    continue
                grain=int(row['l5_actual_reception'])
                stats.update(targets=1,positive=grain>0,full=grain>=int(row['first_uncovered_grain']),
                             actual=grain,strategic=int(row['l5_strategic_reception']))
    return results


def build(args):
    summary=args.summary
    out=summary/'data'
    for name in ('data','checks','sources'):
        (summary/name).mkdir(parents=True,exist_ok=True)
    runs,manifest,missing,required=catalog_runs(args)
    fixed=fixed_results(args,out)
    census=route_modes(list(csv_file_rows(args.prior/'data/transport-capacity-by-route.csv')))
    tables=defaultdict(list)
    scores=[]
    for key,(run,folder) in sorted(runs.items()):
        score=composition(run,folder,tables)
        score.update(transport(run,folder,census,tables))
        scores.append(score)
        read_slots(run,folder,tables)
        print(*key,flush=True)
    for name in (*REPORTS,'origin-slot-purpose','origin-slot-occupation','officer-occupation-comparison',
                 'observed-origin-account','urgent-dispatch-blockers','dispatch-priority-conflicts'):
        if tables[name]:
            output(out/f'{name}.csv',tables[name])
    fields=list(dict.fromkeys(key for row in scores for key in row))
    scores=[{field:row.get(field) for field in fields} for row in scores]
    output(out/'scenario-scores.csv',scores,IDENTITY)
    pairs=list(compare(scores))
    for name,subset in (
            ('pairwise',pairs),('balance-alerts',[r for r in pairs if r['warning']]),
            ('common-safety-ablation',[r for r in pairs if r['group']=='D1' and r['baseline']=='D0']),
            ('concurrent-transport-comparison',[r for r in pairs if r['group']=='D2' and r['baseline']=='D1']),
            ('long-term-economy-comparison',[r for r in pairs if r['wave']=='long']),
            ('holdout-comparison',[r for r in pairs if r['wave']=='holdout'])):
        if subset:
            output(out/f'{name}.csv',subset)
    historical=Counter()
    for row in csv_file_rows(args.prior/'data/transport-dispatch-receipts.csv'):
        if row['group']=='C4' and row['active_after_dispatch']=='2':
            historical[row['purpose']]+=1
    notices=dict(current_runs=len(required & runs.keys()),planned_current=len(required),missing=missing,
                reused_controls=sum(row['input']=='historical' for row in manifest),fixed=fixed,
                reused_economic_references=sum(row['input']=='historical-G0' for row in manifest),
                prior_c4_second_dispatch_purposes=historical,
                actual_urgent_slot_screens=len(tables['urgent-dispatch-blockers']),
                actual_unsatisfied_requests_with_low_priority_slot=len(tables['dispatch-priority-conflicts']),
                ledger_issues=sum(s.get('portable_transport_ledger_issues') or 0 for s in scores),
                warehouse_issues=sum(s.get('city_resource_mismatches') or 0 for s in scores))
    to_json(out/'simulation-manifest.json',manifest)
    to_json(out/'report-status.json',notices)
    for source,dest in ((args.build/'checks','checks'),(args.build/'fixed','checks')):
        for path in sorted(source.glob('*.json')):
            copyfile(path,summary/dest/path.name)
    print(json.dumps(notices,ensure_ascii=False))


if __name__=='__main__':
    p=ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('summary',type=Path)
    p.add_argument('--prior',type=Path,required=True)
    p.add_argument('--predecessor',type=Path,required=True)
    p.add_argument('--historical',type=Path,action='append',default=[])
    build(p.parse_args())
