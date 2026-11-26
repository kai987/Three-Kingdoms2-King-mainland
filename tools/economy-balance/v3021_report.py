"""Build the readable V3.0.2.1 acceptance layer from finished runs and checks."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from hashlib import sha256
import csv
import json
from math import ceil
from pathlib import Path
import re
from shutil import copyfile
from statistics import median

from common import ROOT, TOOL_ROOT, Catalog, to_csv, to_json
from remake import winter_weather
from v3021_experiments import WAVES
from v302_experiments import SETTINGS, case_dir, map_sha
from v302_report import KEYS, csv_file_rows, describe, jsonl, pct

SUCCESS = {'complete','natural_end'}
MACRO = ('unpaid_city_turns','rations_missing','convoy_hunger_losses','winter_timely_percent',
         'strategic_delivered','timely_grain','late_grain','grain_stock','gold_stock','battles',
         'ai_sorties','small_faction_survival_percent','mean_turn_cpu')
CHECKS = ('final-python','final-rust','final-node','final-wasm-build','final-wasm-parity',
          'final-rust-crate','final-pyodide','browser-granary-3021','browser-granary-302',
          'final-backend-state')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def file_sha(path):
    with path.open('rb') as stream:
        return sha256_stream(stream)


def sha256_stream(stream):
    digest = sha256()
    for chunk in iter(lambda: stream.read(1024*1024),b''):
        digest.update(chunk)
    return digest.hexdigest()


def output(path, rows, fields=('status',)):
    if rows:
        to_csv(path,rows)
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w',newline='',encoding='utf-8') as stream:
            csv.writer(stream).writerow(fields)


def matches(run, scene, seed, strategy, weather, months):
    catalog = Catalog(ROOT/f'game/data/campaigns/{scene}.json')
    return ((run['scenario'],run['seed'],run['strategy'],run['weather'],run['requested_months'])
            == (scene,seed,strategy,weather,months)
            and run['completed_turns'] <= months*3
            and (run['completed_turns']==months*3 or run['outcome']=='natural_end')
            and run['map_sha256']==map_sha() and run['catalog_sha256']==catalog.sha256
            and run['weather_seed']==(winter_weather.seed_for(seed) if weather else None)
            and run['emergency']==(222 if weather else 0)
            and run['market_stage']==2 and run['backend']['engine']=='rust'
            and run['parameters']['difficulty']=='normal' and run['parameters']['faction']=='observer'
            and run['parameters']['commands']==['new','observe_turn'])


def select(build, prior, summary):
    published = read(summary/'data/simulation-manifest.json')['simulations']
    historic = {tuple(r[k] for k in KEYS)+(r['group'],):r for r in published}
    exact = build/'final'
    frozen = (build/'final-source.txt').read_text().strip()
    runs, matrix = [], []
    for wave, entries in WAVES.items():
        if wave=='smoke':
            continue
        for seed, scene, strategy, weather, duration in entries:
            planned = ['G1','G4'] if wave=='long' and strategy==212 else ['G0','G1','G4']
            if wave=='winter' and scene=='184-02' and strategy==211:
                planned += ['G3','G3d','G4-no-winter']
            if wave=='relay':
                if scene!='208-10':
                    continue
                planned = ['G4-relay']
            for group in planned:
                tag = dict(wave=wave,scenario=scene,seed=seed,strategy=strategy,weather=weather,
                           requested_months=duration,group=group)
                case = wave,group,seed,scene,strategy,weather,duration
                cohort = {'G0':'S1','G1':'S3'}.get(group)
                folder = case_dir(exact,(wave,'S1',seed,scene,strategy,weather,duration) if group=='G0' else case)
                raw = folder/'run-v302.json'
                archived = False
                old = historic.get(tuple(tag[k] for k in KEYS)+(cohort,))
                if old is None and wave=='winter' and seed==2034 and cohort:
                    old = historic.get(('holdout',scene,seed,strategy,weather,duration,cohort))
                if not raw.exists() and old:
                    folder, archived = prior/old['output'], True
                    raw = folder/'run-v302.json'
                record = None if not raw.exists() else read(raw)
                if record is None:
                    matrix.append(dict(tag,status='pending_or_not_collected',archive=None))
                    continue
                if record.get('outcome') not in SUCCESS:
                    matrix.append(dict(tag,status=record.get('outcome'),archive=archived,
                                       failure=record.get('failure')))
                    continue
                invariant = matches(record,scene,seed,strategy,weather,duration)
                if archived:
                    invariant &= all(record[key]==old[key] for key in (
                        'source','tree_sha256','catalog_sha256','map_sha256','weather_seed','completed_turns',
                        'reserve_options','emergency','strategy'))
                    invariant &= not record['reserve_options'] or not record['reserve_options']['relay']
                elif group != 'G1' or wave != 'long':
                    invariant &= record['source']==frozen
                has_source = sha256(b'').hexdigest()==record['worktree_diff_sha256']
                if not invariant or not has_source:
                    matrix.append(dict(tag,status='ineligible_baseline' if archived else 'metadata_mismatch',
                        archive=archived, source=record['source'], relative_path=record['output'],
                        run_sha256=file_sha(raw), runtime_worktree_diff_sha256=record['worktree_diff_sha256']))
                    continue
                metadata = dict(tag,status=record['outcome'],archive=archived,
                    source=record['source'], tree_sha256=record['tree_sha256'],
                    runtime_worktree_diff_sha256=record['worktree_diff_sha256'],
                    catalog_sha256=record['catalog_sha256'], map_sha256=record['map_sha256'],
                    weather_seed=record['weather_seed'], rules_version=record['rule_versions'],
                    reserve_options=record['reserve_options'], emergency=record['emergency'],
                    start_date=record['start_date'],last_date=record['last_date'],
                    completed_turns=record['completed_turns'],backend=record['backend'],
                    relative_path=record['output'], run_sha256=file_sha(raw),
                    samples_sha256={name:file_sha(folder/name) for name in (
                        'monthly.csv','cities.csv','factions.csv','shortages.csv','strategic-granary-events.jsonl.gz')})
                matrix.append(metadata)
                runs.append((dict(record,group=group,wave=wave),folder))
    return runs,matrix


def pairs(scores):
    by_case = defaultdict(dict)
    for row in scores:
        by_case[tuple(row[k] for k in KEYS)][row['group']] = row
    for case, groups in by_case.items():
        for group,row in groups.items():
            if group in ('G0','G1'):
                continue
            for baseline in ('G0','G1'):
                old = groups.get(baseline)
                if not old or old['completed_turns']!=row['completed_turns']:
                    continue
                for metric in sorted((row.keys() & old.keys())-set(KEYS)):
                    before, after = old[metric], row[metric]
                    if type(before) not in (int,float) or type(after) not in (int,float):
                        continue
                    delta, rel = round(after-before,8), pct(after-before,before)
                    threshold = {'unpaid_city_turns':20,'rations_missing':20,'mean_turn_cpu':30}
                    point_limit = {'winter_timely_percent':-5,'small_faction_survival_percent':-10}
                    guard = baseline=='G0' and metric in (threshold.keys() | point_limit.keys())
                    alert = ((rel > threshold[metric] if rel is not None else after>0)
                             if metric in threshold else delta < point_limit[metric]) if guard else None
                    yield dict(zip(KEYS,case),group=group,baseline=baseline,metric=metric,before=before,
                               after=after,delta=delta,change_pct=rel,alert=alert)


def escort_turn_tables(scope, observed, tables):
    by_city = defaultdict(dict)
    by_turn = defaultdict(Counter)
    for (owner, source, turn), reasons in observed.items():
        unstaffed = reasons == {'no_eligible_escort'}
        by_city[owner, source][turn] = unstaffed
        by_turn[turn]['assessed'] += 1
        by_turn[turn]['blocked'] += None not in reasons
        by_turn[turn]['unstaffed'] += unstaffed
    for turn, marks in sorted(by_turn.items()):
        tables['escort-source-turns'].append(dict(scope,turn=turn,assessed_sources=marks['assessed'],
            blocked_sources=marks['blocked'],sources_without_escort=marks['unstaffed']))
    for (owner, source), turns in sorted(by_city.items()):
        previous, streak, longest = None, 0, 0
        for turn in sorted(turn for turn, missing in turns.items() if missing):
            streak = streak+1 if previous == turn-1 else 1
            longest = max(longest,streak)
            previous = turn
        tables['escort-persistence-by-city'].append(dict(scope,owner=owner,source=source,assessed_turns=len(turns),
            turns_without_escort=sum(turns.values()),longest_consecutive_observed_turns=longest))


def candidate_metrics(run, folder, tables):
    scope = {key:run[key] for key in (*KEYS,'group')}
    reasons, blocks = Counter(), Counter()
    source_marks = defaultdict(set)
    assessments = releases = 0
    residual, relay = defaultdict(list), defaultdict(dict)
    forecasts, requests, receipts = {}, {}, []
    secondary_dispatches = {}
    for row in jsonl(folder/'strategic-granary-events.jsonl.gz'):
        event = row['event']
        if event=='source_eligibility':
            assessments += 1
            blocks[row['reason']] += 1
            source_marks[row['owner'],row['source'],row['turn']].add(row['reason'])
            reasons.update(row['exclusions'])
        elif event=='residual_demand':
            residual['all'].append(row)
            if row['pending_target'] or row['active_target']:
                residual['existing_strategic_order'].append(row)
        elif event=='reserve_released' and row['reason']=='cross_city_urgent':
            releases -= row['delta']
        elif event=='city_forecast':
            forecasts[row['turn'],row['owner'],row['city']] = row['first']
        elif event=='dispatch_requested':
            requests[row['turn'],row['owner'],row['target']] = row['deadline']
        elif event=='order_delivered' and row['priority'] in ('proactive','winter'):
            receipts.append(row)
        elif event=='order_dispatched':
            secondary_dispatches[row['turn'],row['owner'],row['target']] = row
        elif event.startswith('relay_') and 'id' in row:
            relay[row['id']][event] = row
    if assessments:
        for reason, count in blocks.items():
            tables['escort-eligibility-breakdown'].append(dict(scope,unit='source_assessment',
                reason=reason or 'qualifies',count=count,denominator=assessments))
        for reason,count in reasons.items():
            tables['escort-eligibility-breakdown'].append(dict(scope,unit='reported_exclusion',
                reason=reason,count=count,denominator=None))
        tables['source-convoy-limit-analysis'].append(dict(scope,
            source_assessments=assessments,limit_assessments=blocks['source_convoy_limit'],
            unique_source_turns=sum('source_convoy_limit' in reasons for reasons in source_marks.values()),
            lost_timely_grain=None,grain_status='counterfactual_not_measured'))
        escort_turn_tables(scope,source_marks,tables)
    for kind, rows in residual.items():
        tables['residual-demand-comparison'].append(dict(scope,basis=kind,decisions=len(rows),
            with_estimate=sum(r['planned'] is not None for r in rows),
            total_without_receipts=sum(r['baseline'] for r in rows),
            reliable_coverage=sum(r['covered'] for r in rows),
            later_conditional_coverage=sum(r['contingent_coverage'] for r in rows),
            total_uncovered=sum(r['uncovered'] for r in rows),
            quoted_net=sum(r['planned'] or 0 for r in rows)))
        if kind=='existing_strategic_order':
            for demand in rows:
                key = demand['turn'],demand['owner'],demand['target']
                order = secondary_dispatches.get(key)
                if order is not None and demand['uncovered']>0:
                    tables['existing-delivery-follow-up'].append(dict(scope,turn=demand['turn'],
                        owner=demand['owner'],target=demand['target'],reliable_cover=demand['covered'],
                        conditional_cover=demand['contingent_coverage'],uncovered=demand['uncovered'],
                        order_id=order['id'],convoy_id=order['convoy_id'],expected_net=order['expected_grain'],
                        original_receipts=demand['receipts']))
    if assessments:
        tables['reserve-priority-comparison'].append(dict(scope,conditional_release_grain=releases))
    matched = []
    for row in receipts:
        turn = row['dispatch_turn']
        target = (turn,row['owner'],row['target'])
        opens = forecasts.get(target)
        deadline = (turn+opens if opens is not None and row['priority']=='proactive' else requests.get(target))
        if deadline is not None:
            matched.append((row,deadline))
    if run['reserve_options'] and run['reserve_options']['proactive']:
        amount = sum(row['delivered_grain'] for row,_ in matched)
        first = sum(row['delivered_grain'] for row,deadline in matched if row['delivered_turn']<deadline)
        quoted = sum(row['delivered_grain'] for row,_ in matched if row['delivered_turn']<row['deadline'])
        tables['comparable-dispatch-deadlines'].append(dict(scope, matched_receipts=len(matched),
            potential_receipts=len(receipts),delivered_grain=amount,first_forecast_window_grain=first,
            order_window_grain=quoted,first_forecast_window_pct=pct(first,amount),order_window_pct=pct(quoted,amount)))
    if run['reserve_options'] and run['reserve_options'].get('return_safety') and run['emergency']:
        refills = {(r['convoy_id'],int(r['tick'])):int(r['amount'])
                   for r in csv_file_rows(folder/'emergency-local-refills.csv')}
        for artifact in ('emergency-evacuation-plans.csv','emergency-transport-decisions.csv'):
            for row in csv_file_rows(folder/artifact):
                action = row.get('decision')
                if action in ('dock_return_at_node','fund_return_at_node'):
                    tick=int(row['tick'])
                    tables['return-review-interventions'].append(dict(scope,convoy=row['convoy_id'],
                        city=row['actual_position'],tick=tick,action=action,
                        actual_local_grain=refills.get((row['convoy_id'],tick-1)) if action=='fund_return_at_node' else 0))
    for ident, events in relay.items():
        plan = events.get('relay_planned')
        if plan is None:
            continue
        final = events.get('relay_cancelled')
        reason = final.get('reason') if final else next((reason for key,reason in (
            ('relay_second_leg','second_leg_dispatched'),('relay_hub_receipt','hub_received_not_forwarded'))
            if key in events),'first_leg_not_received')
        tables['relay-failure-breakdown'].append(dict(scope,id=ident,source=plan['source'],
            hub=plan['hub'],target=plan['target'],deadline=plan['deadline'],
            received=events.get('relay_hub_receipt',{}).get('received'),outcome=reason))


def weather_parity(runs):
    by_case = defaultdict(dict)
    for record, folder in runs:
        if record['weather']:
            by_case[tuple(record[k] for k in KEYS)][record['group']] = (record,folder)
    for key, cohorts in by_case.items():
        candidate = cohorts.get('G4')
        baseline = cohorts.get('G1')
        if not candidate or not baseline or candidate[0]['completed_turns']!=baseline[0]['completed_turns']:
            continue
        equal_seed = candidate[0]['weather_seed']==baseline[0]['weather_seed']
        for artifact in ('regional-weather-daily.csv','river-ice-daily.csv','snowfall-events.csv'):
            g1,g4=(file_sha(folder/artifact) for _,folder in (baseline,candidate))
            yield dict(zip(KEYS,key),artifact=artifact,seed_match=equal_seed,trace_match=g1==g4,
                       g1=g1,g4=g4)


def severity(run, folder):
    total_bill = total_loss = 0
    amounts, latest, streaks, seen, max_streak = [], {}, Counter(), Counter(), 0
    for row in csv_file_rows(folder/'shortages.csv'):
        key, turn = row['city'], int(row['turn'])
        seen[key] += 1
        streaks[key] = streaks[key]+1 if latest.get(key)==turn-1 else 1
        latest[key] = turn
        max_streak=max(max_streak,streaks[key])
        amounts.append(int(row['missing']))
        total_bill += int(row['required'])
        total_loss += int(row['active_lost'])+int(row['reserve_lost'])
    amounts.sort()
    n, missing = len(amounts), sum(amounts)
    return dict({key:run[key] for key in (*KEYS,'group')},events=n,missing=missing,
        mean=missing/n if n else None,median=median(amounts) if n else None,
        p90=amounts[ceil(.9*n)-1] if n else None,p95=amounts[ceil(.95*n)-1] if n else None,
        percent_of_demand=pct(missing,total_bill),longest_streak=max_streak,
        repeated_cities=sum(count>1 for count in seen.values()),
        actual_person_losses=total_loss)


def perf(build):
    checks = build/'checks'
    for old in sorted(checks.glob('g1-*-r*.json')):
        new = old.with_name(old.name.replace('g1-','g2-',1))
        if not new.exists():
            continue
        before,after = read(old),read(new)
        if before['checkpoint_sha256']!=after['checkpoint_sha256'] or len(before['checks'])!=len(after['checks']):
            raise ValueError(f'Mismatched fixed run {old.name}')
        name = old.stem[3:]
        yield name,before,after


def performance_reports(build, data):
    proof, perf_rows, profile = [], [], []
    for name,before,after in perf(build):
        detail = before['detailed']
        for x,y in zip(before['checks'],after['checks']):
            same_state=x['turn']==y['turn'] and x['checksum']==y['checksum']
            same_rng=x['rng']==y['rng']
            same_decisions=x['decisions']==y['decisions'] if detail else None
            proof.append(dict(sample=name,checkpoint_sha256=before['checkpoint_sha256'],turn=x['turn'],
                 g1=x['checksum'],g2=y['checksum'],same_state=same_state,same_rng=same_rng,
                 same_candidate_order_and_receipts=same_decisions,detailed=detail))
        timings = {}
        for cohort, record in (('G1',before),('G2',after)):
            cpu=sorted(r['cpu'] for r in record['checks'])
            wall=sorted(r['wall'] for r in record['checks'])
            stats = dict(sample=name,group=cohort,turns=len(cpu),detailed=detail,
                mean_cpu=sum(cpu)/len(cpu),cpu_p50=median(cpu),cpu_p95=cpu[ceil(.95*len(cpu))-1],
                cpu_max=max(cpu),wall_p50=median(wall),wall_p95=wall[ceil(.95*len(wall))-1],
                peak_rss_bytes=record['peak_rss_bytes'],rust_calls=record['backend']['calls'],
                route_pairs=record['counters'].get('route_pairs') if detail else None)
            perf_rows.append(stats)
            timings[cohort]=stats
            if detail:
                profile.extend(dict(sample=name,group=cohort,metric=k,value=v)
                               for k,v in record['counters'].items())
        if detail:
            for group,row in timings.items():
                profile.append(dict(sample=name,group=group,metric='peak_rss_bytes',value=row['peak_rss_bytes']))
    output(data/'performance-state-parity.csv',proof,('sample','turn','same_state'))
    output(data/'fixed-state-performance.csv',perf_rows,('sample','group','cpu_p95'))
    output(data/'route-cache-profile.csv',profile,('sample','group','metric','value'))
    return dict(samples=len(perf_rows)//2, turns=len(proof), by_checkpoint=dict(Counter(
        r['sample'].rsplit('-',2)[0] for r in proof)),
        all_exact=bool(proof) and all(r['same_state'] and r['same_rng']
                                     and r['same_candidate_order_and_receipts'] is not False for r in proof))


def checks_report(build):
    gates = []
    for name in CHECKS:
        log, status = build/'logs'/f'{name}.log', build/'checks'/f'{name}.exit'
        result = (int(status.read_text())==0 if status.is_file() else None)
        contents = log.read_text(errors='replace') if log.is_file() else ''
        if name in ('final-python','final-rust') and re.search(r'^OK\s*$',contents,re.M):
            result = True
        if name=='final-node' and re.search(r'^ℹ fail 0$',contents,re.M):
            result = True
        if name=='final-wasm-build' and '"wasm_bytes"' in contents and '"sha256"' in contents:
            result = True
        notes = [line for line in contents.splitlines() if re.search(
            r'^(Ran |OK(?:\s|$)|ℹ tests |test result:|Rust/WASM parity|\{"ok":)| \.\.\. skipped ',line)]
        gates.append(dict(gate=name,passed=result,log_sha256=file_sha(log) if log.is_file() else None,results=notes))
    record=build/'checks/legacy-guandu.json'
    return dict(gates=gates,legacy_guandu=read(record) if record.exists() else None,
                source=(build/'final-source.txt').read_text().strip())


def historical_controls(prior, checks):
    prior = prior/'historical'
    details = read(prior/'historical-convoys.json')
    controls = []
    for row in details['records']:
        relative = row.get('copied')
        path = prior/relative if relative else None
        actual = file_sha(path) if path and path.is_file() else None
        expected = row.get('member_sha256')
        controls.append(dict(convoy=row['convoy'],archived_status=row['status'],
            snapshot=relative or Path(row['archive']).name,
            member=row.get('member'),reported_historical_loss=row.get('return_hunger'),
            verified_archive_sha256=row.get('archive_sha256'),archived_member_sha256=expected,
            local_evidence_sha256=actual,local_evidence_matches=actual==expected if expected is not None else None))
    replay = prior/'convoy-1706/v302-disabled-regression-check.json'
    record = dict(archived_controls=controls, disabled_1706=details['disabled_1706'],
                  disabled_1706_file_sha256=file_sha(replay),source='V3.0.2 acceptance evidence')
    to_json(checks/'historical-transport-controls.json',record)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('prior',type=Path)
    parser.add_argument('prior_summary',type=Path)
    parser.add_argument('summary',type=Path)
    args=parser.parse_args()
    data,checks = args.summary/'data',args.summary/'checks'
    runs,matrix = select(args.build,args.prior,args.prior_summary)
    tables = defaultdict(list)
    # Large details consumed by the existing auditor stay on the raw run.
    published = {'strategic-granary-comparison','proactive-dispatch-comparison',
        'winter-army-supply-comparison','convoy-hunger-comparison','convoy-return-safety',
        'performance-comparison','spatial-grain-imbalance','reserve-release-comparison'}
    scores=[]
    for run, folder in runs:
        sections = defaultdict(list)
        scores.append(describe(run,folder,sections))
        for key in published:
            for row in sections[key]:
                if key=='spatial-grain-imbalance':
                    # The shortage observer initializes timely_new_shipment to zero
                    # without running a deadline-constrained quote at settlement.
                    row.update(observer_timely_shipment_rows=0,timely_legal_coverage=None,
                               timely_coverage_basis='not_collected_placeholder')
                tables[key].append(row)
        candidate_metrics(run,folder,tables)
        tables['shortage-severity-by-scenario'].append(severity(run,folder))
    output(data/'scenario-scores.csv',scores,(*KEYS,'group'))
    comparisons = list(pairs(scores))
    output(data/'pairwise.csv',comparisons,(*KEYS,'group','baseline','metric'))
    alerts=[row for row in comparisons if row['alert']]
    output(data/'balance-alerts.csv',alerts,(*KEYS,'group','baseline','metric'))
    for wave, name in (('long','long-term-economy-comparison'),('holdout','holdout-comparison')):
        output(data/f'{name}.csv',[{key:r[key] for key in (*KEYS,'group','completed_turns',*MACRO)}
               for r in scores if r['wave']==wave],(*KEYS,'group','completed_turns',*MACRO))
    for key, rows in tables.items():
        output(data/f'{key}.csv',rows,(*KEYS,'group','status'))
    for key in ('escort-eligibility-breakdown','residual-demand-comparison','relay-failure-breakdown'):
        if key not in tables:
            output(data/f'{key}.csv',[],(*KEYS,'group','status'))
    for path in (args.build/'historical').glob('*'):
        if path.is_file() and not (data/path.name).exists():
            copyfile(path,data/path.name)
    # Include both old opportunity counts and live source assessments.
    heritage = args.build/'historical/source-convoy-limit-analysis.csv'
    if heritage.exists():
        copyfile(heritage,data/'historical-source-convoy-limit-analysis.csv')
    parity=performance_reports(args.build,data)
    weather=list(weather_parity(runs))
    output(data/'weather-state-parity.csv',weather,(*KEYS,'artifact','seed_match','trace_match'))
    to_json(checks/'technical-gates.json',checks_report(args.build))
    historical_controls(args.prior,checks)
    to_json(data/'simulation-manifest.json',dict(schema='tk2-v3021-observations',simulations=matrix))
    status = dict(expected_runs=len(matrix),completed_runs=len(runs),
        reused_runs=sum(bool(row['archive']) for row in matrix),warning_count=len(alerts),
        outcomes=dict(Counter(row['status'] for row in matrix)),fixed_state_parity=parity,
        weather_traces_compared=len(weather),weather_traces_exact=sum(r['trace_match'] for r in weather),
        city_account_errors=sum(r['city_resource_mismatches'] for r in scores),
        reserve_account_errors=sum(r['reserve_audit_errors'] for r in scores
                                   if type(r['reserve_audit_errors']) is int))
    to_json(data/'report-status.json',status)
    to_json(data/'validation-manifest.json',dict(version=3021,candidate=(args.build/'final-source.txt').read_text().strip(),
        candidate_frozen_at=(args.build/'candidate-frozen-at.txt').read_text().strip(),
        weather_seed_rule='sha256(tk2/winter/22/{campaign_seed})', map_sha256=map_sha(),
        observer_config_sha256=file_sha(SETTINGS), historical_archive_index_sha256=
        file_sha(args.prior_summary/'data/simulation-manifest.json'), **status))
    print(json.dumps(status,ensure_ascii=False))


if __name__=='__main__':
    main()
