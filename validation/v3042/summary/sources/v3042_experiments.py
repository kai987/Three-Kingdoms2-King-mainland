"""Run V3.0.4.2 independently from the frozen 30412 studies."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
import gzip
import json
from math import ceil
from pathlib import Path
import platform
import sys
from statistics import median
from unittest.mock import patch

from common import ROOT, git, sha256, to_csv, to_json
from remake import grain_units, logistics_strategy, transport_coordination, transport_infrastructure as wharf
from remake.campaign import digest
import v30412_replays as replays
import v30412_campaigns as campaigns
from v3041_report import comparisons, emit, read_run

PROTOCOL = ROOT/'docs/transport-infrastructure-v3042/protocol.json'
OLD = {'N0':'K0', 'N1':'K0', 'N2':'L2', 'N3':'L2'}
WITH_WHARVES = {'N1','N3'}
PAIRS = (('N0','N1'), ('N2','N3'), ('N0','N3'))
PERFORMANCE = {'north-snow':10, 'chibi-late':10}


def protocol():
    return json.loads(PROTOCOL.read_bytes())


def options(variant):
    result = replays.settings(OLD[variant])
    if variant in WITH_WHARVES:
        result[wharf.FIELD] = wharf.VERSION
    return result


def provenance():
    base=protocol()['refs']['main']
    return dict(base=base, head_at_run=git('rev-parse','HEAD').decode().strip(),
                runtime_patch_sha256=sha256(git('diff',base,'--binary','--','source','game','crates')),
                protocol_sha256=sha256(PROTOCOL.read_bytes()),
                runner_sha256=sha256(Path(__file__).read_bytes()),
                host=dict(os=platform.system(),arch=platform.machine(),python=sys.version.split()[0]),
                groups={g:options(g) for g in OLD})


def log(logfile, kind, row):
    logfile.write(json.dumps(dict(event=kind, **row),ensure_ascii=False,separators=(',',':'))+'\n')


def open_stream(stack, path):
    path.parent.mkdir(parents=True,exist_ok=True)
    return stack.enter_context(gzip.open(path,'wt',encoding='utf-8',compresslevel=3))


def fixed_side(task):
    phase, raw, variant, output = task
    engine_enable=replays.enable
    variant_dir=output/variant
    marks=[]
    evidence_counts=Counter()
    snapshot=[]
    observer = replays.legacy.winter_replay.HeadlessCampaign
    original_command = observer.command

    def enable(stack, game, group, callback):
        # Convoy 3634 comes from a versioned physical-capacity run with
        # persisted journeys. Preserve that historical capacity background.
        if phase=='historical' and label=='3634' and group=='L2':
            flags=replays.settings(group)
            transport_coordination.initialize(game.state,flags[transport_coordination.FIELD],
                                               flags[transport_coordination.OPTIONS])
        else:
            engine_enable(stack,game,group,callback)
        state=game.to_dict()
        snapshot.append(dict(checkpoint=digest(state),rng=state['rng'],rules=replays.rule_snapshot(game)))
        if variant in WITH_WHARVES:
            with grain_units.using(game.state):
                wharf.initialize(game,game.state,wharf.VERSION)

    def command(game, action, payload, revision):
        reply=original_command(game,action,payload,revision)
        if action=='observe_turn':
            state=game.to_dict()
            ext=state['extension']
            # The off comparison against main below uses the unnormalized
            # engine check. Only the experimental pool is stripped here.
            nodes=ext.pop(wharf.POOL,None)
            ext.pop(wharf.FIELD,None)
            marks.append(dict(turn=state['turn'],domain=digest(state),rng=state['rng'],
                              active_jobs=len(nodes['jobs']) if nodes else 0))
        return reply

    if phase=='fixed':
        label=raw[0].name
    elif phase=='historical':
        label=raw[1]
    else:
        label=raw[0]['label']+f'-{raw[-1]}'
    def callback(kind,row):
        evidence_counts[kind]+=1
        log(events,kind,row)
    with ExitStack() as stack:
        if phase!='performance':
            events=open_stream(stack,variant_dir/'wharf'/f'{label}.jsonl.gz')
            stack.enter_context(wharf.observing(callback))
            stack.enter_context(patch.object(observer,'command',command))
        stack.enter_context(patch.object(replays,'enable',enable))
        result=replays.perform((phase,raw,variant_dir))
    result.update(variant=variant,initial=snapshot[0],normalized_turns=marks,
                  facility_events=dict(evidence_counts))
    if phase=='historical' and label=='3634':
        result['capacity_background']='original_versioned_capacity'
        result['concurrency_only_control']='blocked: original journeys created with physical capacity'
    to_json(variant_dir/'windows'/f'{label}.json',result)
    return result


def fixed_plan(args):
    records=replays.verified_inputs(args.inputs,args.reference)
    pending=[]
    for group, base in OLD.items():
        if args.phase=='fixed':
            slices=replays.audit.fixed_tasks(args.inputs,records,[base])
        elif args.phase=='historical':
            # Retain all eight replayable historical convoys. The archive
            # still describes the cases for which the original save is absent.
            slices=[(args.inputs/item['file'],item['label'],base) for item in records
                    if item['restored'] and item['group']=='historical']
            slices.extend((args.inputs/item['file'],item['name'].split('-')[1].split('.')[0],base)
                          for item in records if item['group']=='fixed' and item['name'] in
                          ('convoy-219.json.gz','convoy-1228.json.gz'))
        else:
            slices=[(item,args.inputs/item['file'],base,repeat) for item in records
                    if item['restored'] and item['group']==('performance' if args.phase=='profile' else args.phase)
                    and (args.phase not in ('performance','profile') or item['label'] in PERFORMANCE)
                    for repeat in range(PERFORMANCE.get(item['label'],1) if args.phase=='performance' else 1)]
        pending.extend((args.phase,raw,group,args.output) for raw in slices)
    if args.phase=='performance':
        pending.sort(key=lambda run:(run[1][-1],run[1][0]['label'],run[2]))
    return pending


def grade_fixed(rows, unmodified):
    base={(r['group'],r['fixture']):r for r in unmodified}
    indexed={(r['variant'],r['fixture']):r for r in rows}
    safety=Counter()
    counts={}
    comparisons=[]
    for variant in OLD:
        own=[r for r in rows if r['variant']==variant]
        counts[variant]=dict(windows=len(own),demands=sum(len(r['physical_targets']) for r in own),
                             return_slots=sum(len(r['returning_sources']) for r in own))
        assert counts[variant]==dict(windows=5,demands=89,return_slots=23)
        for r in own:
            safety.update(r['safety'])
            safety.update(city_resource_mismatches=r['grain_account']['city_resource_mismatches'])
            if variant not in WITH_WHARVES:
                old=base[r['group'],r['fixture']]
                assert all(row['sha256']==previous['sha256'] and row['rng']==previous['rng']
                           for row,previous in zip(r['checks'],old['checks'],strict=True)), r['fixture']
    backgrounds=[]
    for a,b in PAIRS[:2]:
        can_continue=True
        for (variant,key), first in indexed.items():
            if variant!=a:
                continue
            second=indexed[b,key]
            assert first['sha256']==second['sha256']
            lead={(row['owner'],row['city'],row['deadline']):row for row in first['consumption']
                  if row['due_meal_observed']}
            trial={(row['owner'],row['city'],row['deadline']):row for row in second['consumption']
                   if row['due_meal_observed']}
            never_measured=sorted((row['owner'],row['city'],row['deadline'])
                                  for row in first['consumption'] if not row['due_meal_observed']
                                  and (row['owner'],row['city'],row['deadline']) not in trial)
            paired=sorted(lead.keys()&trial.keys())
            assert paired, key
            newly_missing=sum(max(0,trial[k]['actual_missing']-lead[k]['actual_missing']) for k in paired)
            same=first['normalized_turns']==second['normalized_turns']
            comparisons.append(dict(baseline=a,candidate=b,checkpoint=key,input_sha256=first['sha256'],
                                    equal_non_facility_states=same,new_missing_grain=newly_missing,
                                    paired=len(paired),unpaired=len(lead.keys()^trial.keys()),
                                    missing_in_control=sorted(trial.keys()-lead.keys()),
                                    missing_in_candidate=sorted(lead.keys()-trial.keys()),
                                    original_targets_without_observed_bill=never_measured,
                                    control_required=sum(lead[k]['required'] for k in paired),
                                    candidate_required=sum(trial[k]['required'] for k in paired),
                                    control_paid=sum(lead[k]['paid'] for k in paired),
                                    candidate_paid=sum(trial[k]['paid'] for k in paired),
                                    control_missing=sum(lead[k]['actual_missing'] for k in paired),
                                    candidate_missing=sum(trial[k]['actual_missing'] for k in paired)))
            can_continue &= not newly_missing and not (lead.keys()^trial.keys())
        if can_continue:
            backgrounds.append('D0' if a=='N0' else 'D2')
    return dict(stage='fixed',status='pass' if not any(safety.values()) else 'fail',
                admitted_backgrounds=backgrounds if not any(safety.values()) else [],
                baseline_states_and_rng_exact=True,sample_counts=counts,hard_errors=dict(safety),pairs=comparisons,
                **provenance())


def fixed_run(args):
    pending=fixed_plan(args)
    manifest_path=args.output/'manifest.json'
    run=dict(phase=args.phase,**provenance(),
             input_manifest_sha256=sha256(args.reference.read_bytes()),planned=len(pending))
    resumed={}
    if args.resume:
        previous=json.loads(manifest_path.read_bytes())
        for key in ('phase','runtime_patch_sha256','input_manifest_sha256','planned'):
            if run[key]!=previous[key]:
                raise ValueError(f'Cannot resume a different {key}')
        previous_tasks=pending
        pending=[]
        for job in previous_tasks:
            _,raw,variant,_=job
            target=args.output/variant/'windows'/f'{raw[1]}.json'
            if not target.exists() or raw[1]=='3634':
                pending.append(job)
                continue
            row=json.loads(target.read_bytes())
            assert row['variant']==variant and row['convoy']==int(raw[1])
            assert row['checkpoint_sha256']==sha256(raw[0].read_bytes())
            resumed[variant,raw[1]]=row
    run['resumed_windows']=len(resumed)
    to_json(manifest_path,run)
    kwargs={'max_workers':1,'max_tasks_per_child':1} if args.phase=='performance' else {'max_workers':args.workers}
    with ProcessPoolExecutor(**kwargs) as pool:
        rows=[*resumed.values(),*pool.map(fixed_side,pending)]
    to_json(args.output/'results.json',rows)
    if args.phase=='fixed':
        write_fixed_grade(args.output,args.baseline,rows)
    elif args.phase=='performance':
        buckets=defaultdict(list)
        for row in rows:
            buckets[row['label'],row['variant']].append(row)
        output=[]
        for (label,v),items in sorted(buckets.items()):
            values=sorted(cpu for row in items for cpu in row['cpu'])
            output.append(dict(checkpoint=label,variant=v,runs=len(items),samples=len(values),p50=median(values),
                               p95=values[ceil(.95*len(values))-1],p99=values[ceil(.99*len(values))-1],
                               maximum=max(values),peak_memory_bytes=max(r['peak_memory_bytes'] for r in items),
                               route_search_calls=sum(r['route_search_calls'] for r in items)))
        to_csv(args.output/'performance.csv',output)


def write_fixed_grade(output,baseline_path,rows):
    baseline=json.loads(baseline_path.read_bytes())['results']
    result=grade_fixed(rows,baseline)
    to_json(output/'fixed-stage-status.json',result)
    to_csv(output/'fixed-pairs.csv',result['pairs'])


def quick_side(task):
    output,spec=task
    variant=spec['study_group']
    work=output/variant
    case=spec.copy()
    case['variant']=OLD[variant]
    name=f"{spec['scenario']}-{spec['seed']}-{spec['strategy']}"
    audit=work/f'{name}-actual-and-opening.jsonl.gz'
    evidence=work/f'{name}-wharf.jsonl.gz'
    identity=work/f'{name}-identity.json'
    if identity.exists() and evidence.exists() and audit.exists():
        previous=json.loads(identity.read_bytes())
        if previous['case']==spec:
            return previous
        raise ValueError(f'Mismatched evidence {identity}')
    original=campaigns.RecordedCampaign.command
    original_observer=logistics_strategy.observing
    opening=[]
    def command(game, action, payload, revision):
        result=original(game,action,payload,revision)
        if action=='new':
            state=game.to_dict()
            rules=replays.rule_snapshot(game)
            rules[wharf.FIELD]=state['extension'].pop(wharf.FIELD,0)
            state['extension'].pop(wharf.POOL,None)
            opening.append(dict(domain_sha256=digest(state),rng=state['rng'],rules=rules))
        return result
    def observing(callback):
        def paired(kind,row):
            callback(kind,row)
            if kind not in ('unit_meal_settled','city_meal_settled') or (
                    kind=='unit_meal_settled' and row.get('unit_kind')=='march' and row.get('unit_id')==111):
                log(actual,kind,row)
        return original_observer(paired)
    with ExitStack() as stack:
        events=open_stream(stack,evidence)
        actual=open_stream(stack,audit)
        stack.enter_context(wharf.observing(lambda kind,row:log(events,kind,row)))
        stack.enter_context(patch.object(campaigns,'settings',lambda old:options(variant)))
        stack.enter_context(patch.object(campaigns.RecordedCampaign,'command',command))
        stack.enter_context(patch.object(logistics_strategy,'observing',observing))
        result=campaigns.run_pair_side((work,case))
    assert len(opening)==1, (identity,opening)
    row=dict(variant=variant,case=spec,path=str((work/result['output']/'run-v3041.json').relative_to(output)),
             actual_events=str(audit.relative_to(output)), wharf_events=str(evidence.relative_to(output)),
             result=result['result'],terminal_checksum=result['terminal_checksum'],opening=opening[0])
    to_json(identity,row)
    return row


def quick(args):
    gate=json.loads(args.gate.read_bytes())
    if gate['stage']!='fixed' or gate['status']!='pass':
        raise ValueError('Run fixed acceptance before launching the matched campaigns')
    source=provenance()
    if gate['runtime_patch_sha256']!=source['runtime_patch_sha256']:
        raise ValueError('Fixed gate uses a different runtime source')
    tasks=[]
    for background,variants in (('D0',('N0','N1')),('D2',('N2','N3'))):
        if background not in gate['admitted_backgrounds']:
            continue
        for scenario,seed,strategy in protocol()['observations'][background]:
            for variant in variants:
                tasks.append(dict(wave='quick',scenario=scenario,seed=seed,strategy=strategy,months=24,
                                  study_group=variant,source=source['head_at_run'],engine_sha=source['head_at_run'],
                                  source_diff_sha256=sha256(git('diff','HEAD','--binary','--','source','game','crates')),
                                  runtime_patch_sha256=source['runtime_patch_sha256']))
    if not tasks:
        raise ValueError('No background reached the quick gate')
    to_json(args.output/'quick-plan.json',dict(source, cases=tasks))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows=list(pool.map(quick_side,((args.output,case) for case in tasks)))
    to_json(args.output/'quick-completed.json',rows)
    summarize(args.output)


def summarize(output):
    rows=json.loads((output/'quick-completed.json').read_bytes())
    scheduled=json.loads((output/'quick-plan.json').read_bytes())['cases']
    assert len(scheduled)==len(rows)
    scores=[]
    by_case={}
    for row in rows:
        spec=row['case']
        identity=(spec['scenario'],spec['strategy'],spec['seed'])
        siblings=by_case.setdefault(identity,{})
        siblings[row['variant']]=row['opening']
    for groups in by_case.values():
        for first,second in PAIRS[:2]:
            if {first,second} <= groups.keys():
                assert groups[first]['domain_sha256']==groups[second]['domain_sha256']
                assert groups[first]['rng']==groups[second]['rng']
    for row in rows:
        case, score, _=read_run(output/row['path'])
        if score is None:
            continue
        run=row['result']
        relay=Counter()
        spec=row['case']
        path=output/row['variant']/f"{spec['scenario']}-{spec['seed']}-{spec['strategy']}-wharf.jsonl.gz"
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            for line in stream:
                event=json.loads(line)
                if event['event']=='choice':
                    relay['relay_quotes']+=1
                    relay['relay_selected']+=int(event['selected'])
                elif event['event']=='delivery':
                    relay['relay_received']+=event['grain']
                    relay['relay_timely']+=event['grain']*event['timely']
                elif event['event']=='meal':
                    relay['relay_hunger_days']+=int(event['missing']>0)
                    relay['relay_hunger_losses']+=event['troops_lost']
        score.update(run['observed_actual_grain'])
        score.update(security_books=run['whole_grain_security_books']['total'],
                     opening_state_sha256=row['opening']['domain_sha256'],
                     opening_rng=row['opening']['rng'],
                     endpoint_save_checksum=row['terminal_checksum'])
        score.update(variant=row['variant'],completed_turns=run['completed_turns'],
                     p95_turn_cpu=run['performance'].get('p95_turn_cpu_seconds'), **relay)
        scores.append(score)
    # Fill counts with true zero only after the corresponding stream reached EOF.
    relay_keys={'relay_quotes','relay_selected','relay_received','relay_timely','relay_hunger_days','relay_hunger_losses'}
    scores=[dict(row,**{key:row.get(key,0) for key in sorted(relay_keys)}) for row in scores]
    protecting=('city_food_required','city_food_paid','city_food_missing','march_food_required',
                'march_food_paid','march_food_missing','march_hunger_days','march_hunger_losses',
                'final_population','final_active_troops','security_books','p95_turn_cpu')
    pairs,alerts=comparisons(scores,pairs_to_compare=PAIRS,extra=(*sorted(relay_keys),*protecting))
    for row in pairs:
        baseline,delta,relative=row['baseline_value'],row['delta'],row['percent_change']
        metric=row['metric']
        threshold=30 if metric=='p95_turn_cpu' else 20
        if delta is None:
            continue
        if metric in ('march_hunger_days','march_hunger_losses','city_food_missing','march_food_missing',
                      'unresolved_grain','convoy_hunger_losses','p95_turn_cpu') and (
                          (relative is not None and relative>threshold) or (baseline==0 and delta>0)):
            alerts.append(dict(row,threshold=threshold,unit='zero_baseline' if baseline==0 else 'percent'))
    emit(output/'scenario-scores.csv',scores)
    to_csv(output/'pairwise.csv',pairs)
    emit(output/'balance-alerts.csv',alerts)
    score_index={(row['scenario'],row['seed'],row['strategy'],row['variant']):row for row in scores}
    outcomes={}
    retained=[]
    for underlying,before,after in (('D0','N0','N1'),('D2','N2','N3')):
        cohort=[row for k,row in score_index.items() if k[-1]==after]
        needed=sum(spec['study_group']==after for spec in scheduled)
        coverage=sum(row['relay_received'] for row in cohort)
        relevant=[r for r in alerts if r['candidate']==after and r['baseline'] in (before,'N0')]
        complete=len(cohort)==needed and all(row['completed_turns']==72 for row in cohort)
        resource_error=sum(row['resource_mismatches']+row['repeated_origin_dispatches']+
                           row['simultaneous_escort_overlaps']+row['transport_position_overruns'] for row in cohort)
        no_combination_control=any((row['scenario'],row['seed'],row['strategy'],'N0') not in score_index
                                   for row in cohort) if underlying=='D2' else False
        passed=bool(needed and complete and not resource_error and not relevant and coverage and not no_combination_control)
        outcomes[underlying]=dict(status=('pass' if passed else 'fail' if needed else 'not_run'),
                                  completed=len(cohort),planned=needed,full_horizon=complete,
                                  delivery=coverage,hard_errors=resource_error,alerts=len(relevant),
                                  missing_stable_combination_control=no_combination_control)
        if passed:
            retained.append(underlying)
    to_json(output/'economic-stage-status.json',dict(
        quick=dict(status='pass' if retained else 'fail',backgrounds=outcomes,admitted_backgrounds=retained,
                   observed=len(rows),scored=len(scores),alerts=alerts,
                   realized_facility_delivery=sum(row['relay_received'] for row in scores)),
        five=dict(status='not_run',reason='Requires observed closed-loop economic gain and no blocking quick alerts'),
        twenty=dict(status='not_run',reason='Requires five-year admission'),
        holdout=dict(status='not_run',seeds=[2047,2048],reason='No independently frozen candidate')))


def main():
    p=ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('fixed','south','historical','performance','profile','quick','summarize','grade-fixed'))
    p.add_argument('output',type=Path)
    p.add_argument('--inputs',type=Path)
    p.add_argument('--reference',type=Path)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--gate',type=Path)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--resume',action='store_true',help='Continue verified original convoy replays')
    args=p.parse_args()
    if args.resume and args.phase!='historical':
        p.error('--resume is supported for historical replays')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.phase=='quick':
        quick(args)
    elif args.phase=='summarize':
        summarize(args.output)
    elif args.phase=='grade-fixed':
        write_fixed_grade(args.output,args.baseline,json.loads((args.output/'results.json').read_bytes()))
    else:
        fixed_run(args)


if __name__=='__main__':
    main()
