"""Compare run-scoped receipts and package reproducible V2.1.2 evidence."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from csv import writer
from hashlib import file_digest
from itertools import product
from json import loads
from pathlib import Path
from shutil import copy2
from zipfile import ZIP_DEFLATED, ZipFile

from common import to_csv, to_json
from observe import SCENARIOS
from reproduce_army_relief import PRIORITY
from v211_report import analyze, records, relief_stats
from v21_report import distribution, number, pct, rate, table

COMPLETE = {'complete', 'natural_end'}
CANDIDATE = 'G4al'
SEEDS = (2026, 2027, 2028)
MATRIX = set(product(SEEDS, (60,), SCENARIOS))
LONG = {(2026, 240, scenario) for scenario in ('184-02', '208-10')}
HOLDOUT = {(2030, 60, scenario) for scenario in ('190-01', '208-10')}
PILOTS = {(seed, 60, scenario) for seed, scenario in PRIORITY}
ARCHIVED = ('monthly', 'factions', 'cities', 'capture-recovery', 'shortages', 'supply-requests',
            'convoys', 'troop-flows', 'battles', 'war-quotes', 'war-quote-groups', 'war-plans',
            'route-changes', 'action-capacity', 'army-convoys', 'army-requests', 'war-recovery')
LIMITS = {'shortage_city_turns': (0, 150), 'shortages_per_1000_owned_city_turns': (0, 6),
          'grain_missing': (0, 75000), 'battles': (150, 220), 'convoy_hunger_deaths': (0, 1000),
          'ended_above_local_troops': (0, 300000), 'blocked_9_faction_turns': (0, 5)}
PENDING = 'pending_at_observation_end'
CANCELLED = 'cancelled_no_longer_needed'
EXCLUDED = {PENDING, CANCELLED}
FIELDS = {
    'shortage-comparison': ('shortage_city_turns', 'shortages_per_1000_owned_city_turns', 'grain_missing',
                            'owned_city_turns', 'longest_shortage', 'cities_short_3', 'cities_short_9', 'cities_short_30'),
    'war-frequency-comparison': ('battles', 'war_plans', 'war_plans_dispatched', 'war_plan_conversion',
                                 'wars_per_active_faction_year', 'war_quote_evaluations', 'war_hard_reasons'),
    'troop-sustainability-comparison': ('active_troops', 'stationed_troops', 'reserve_troops', 'natural_monthly_reserves',
                                       'ended_above_local_troops', 'entered_active', 'ai_recruitment', 'delegated_recruitment'),
    'convoy-hunger-comparison': ('convoy_hunger_deaths', 'army_hunger_losses', 'other_hunger_losses',
                                'army_dispatches', 'army_arrived', 'army_delivered', 'other_dispatches', 'other_delivered',
                                'other_closed_success', 'other_closed_net_grain', 'other_closed_sent'),
    'march-hunger-comparison': ('march_hunger_losses', 'march_departure_troops', 'march_hunger_per_10000'),
    'escort-availability-comparison': ('escort_calls', 'resident_officers_mean', 'available_officers_mean',
                                       'light_candidates_mean', 'heavy_candidates_mean', 'army_dispatches',
                                       'army_escort_light', 'escort_reassignments', 'escort_transfers'),
    'army-supply-coverage': ('episode_count', 'effective_episodes', 'fully_timely_episodes', 'partially_timely_episodes',
                             'full_timely_percent', 'partial_timely_percent', 'effective_required', 'timely_grain',
                             'late_grain', 'unmet_grain', 'timely_coverage_percent', 'external_effective_episodes',
                             'external_effective_required', 'external_timely_grain', 'external_timely_percent',
                             'pending_episodes', 'pending_unmet', 'cancelled_episodes', 'immediate_city_episodes'),
    'recovery-parameter-comparison': ('war_recovery_quotes', 'war_no_reliable_surplus', 'war_recovery_deferred',
                                      'war_necessary_exceptions', 'war_avg_reserves_assigned', 'war_avg_grain_budget',
                                      'war_avg_gold_budget', 'war_multiple_front_quotes', 'war_overlapping_front_quotes'),
    'performance-comparison': ('mean_turn_cpu_seconds', 'mean_turn_seconds', 'max_turn_seconds', 'worker_peak_rss_bytes',
                               'quoted_paths', 'quote_cache_hit_rate', 'supply_route_pairs', 'escort_calls',
                               'escort_roster_checks', 'meeting_quotes', 'war_recovery_quotes', 'occupation_assessments'),
}


def digest(path):
    with path.open('rb') as file:
        return file_digest(file, 'sha256').hexdigest()


def archive_digest(archive, name):
    with archive.open(name) as handle:
        return file_digest(handle, 'sha256').hexdigest()


def emit(output, name, rows, empty=('group','seed','months','scenario')):
    file = output / f'{name}.csv'
    if rows:
        to_csv(file, rows)
    else:
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open('w', encoding='utf-8', newline='') as handle:
            writer(handle, lineterminator='\n').writerow(empty)


def grain_needed(episode):
    return number(episode, 'original_required_grain') + number(episode, 'additional_required_grain')


def same_day_city(episode):
    return (episode['terminal_status'] == 'resolved_by_city_supply'
            and episode['first_request_time'] == episode['resolved_time'])


def demand_stats(rows):
    effective = [row for row in rows if row['terminal_status'] not in EXCLUDED]
    external = [row for row in effective if not same_day_city(row)]
    pending = [row for row in rows if row['terminal_status'] == PENDING]

    def measure(episodes):
        required = sum(map(grain_needed, episodes))
        timely = sum(number(row, 'timely_delivered_grain') for row in episodes)
        return required, timely, pct(timely, required)

    required, timely, coverage = measure(effective)
    external_need, external_timely, external_coverage = measure(external)
    full = sum(number(row, 'timely_delivered_grain') == grain_needed(row) for row in effective)
    partial = sum(0 < number(row, 'timely_delivered_grain') < grain_needed(row) for row in effective)
    for row in rows:
        if grain_needed(row) != sum(number(row, key) for key in
                                    ('timely_delivered_grain', 'late_delivered_grain', 'remaining_unmet_grain')):
            raise ValueError(f"Supply episode does not balance: {row['supply_episode_id']}")
    return dict(episode_count=len(rows), effective_episodes=len(effective), fully_timely_episodes=full,
        partially_timely_episodes=partial, full_timely_percent=pct(full, len(effective)),
        partial_timely_percent=pct(partial, len(effective)), effective_required=required,
        timely_grain=timely, timely_coverage_percent=coverage,
        late_grain=sum(number(row, 'late_delivered_grain') for row in effective),
        unmet_grain=sum(number(row, 'remaining_unmet_grain') for row in effective),
        pending_episodes=len(pending), pending_unmet=sum(number(row, 'remaining_unmet_grain') for row in pending),
        cancelled_episodes=sum(row['terminal_status']==CANCELLED for row in rows),
        immediate_city_episodes=len(effective)-len(external), external_effective_episodes=len(external),
        external_effective_required=external_need, external_timely_grain=external_timely,
        external_timely_percent=external_coverage)


def run_sources(places):
    indexed = {}
    errors = []
    for place in places:
        for path in sorted((place / 'observed').glob('*/*/*/*/run.json')):
            run = loads(path.read_text(encoding='utf-8'))
            ident = (run['group'], run['seed'], run['requested_months'], run['scenario'])
            if run['outcome'] not in COMPLETE:
                errors.append(dict(identity=ident, path=str(path), error=run['failure']))
                continue
            indexed[ident] = (path.parent, run)
    return indexed, errors


def verify_history(archive, indexed):
    comparisons = []
    references = {}
    for (group, seed, months, scenario), (folder, run) in indexed.items():
        if group != 'F3' or seed not in SEEDS:
            continue
        prefix = f'data/observed/F3/{seed}/{months}/{scenario}/'
        published = loads(archive.read(prefix+'run.json'))
        if (published['catalog_sha256']!=run['catalog_sha256']
                or published['v211']['opening_sha256']!=run['v211']['opening_sha256']
                or published['parameters']!=run['parameters'] or published['last_date']!=run['last_date']):
            raise ValueError(f'Mismatched archived F3 opening or end condition for {prefix}')
        for name in ARCHIVED:
            filename = name+'.csv'
            member = prefix+filename
            if archive_digest(archive, member) != digest(folder/filename):
                raise ValueError(f'F3 rerun differs from the published raw evidence: {member}')
            references[member] = dict(archive_member=member, sha256=digest(folder/filename))
        comparisons.append(dict(scenario=scenario, seed=seed, months=months, archive_commit=published['head'],
            replay_commit=run['head'], opening_sha256=run['v211']['opening_sha256'],
            exact_streams=len(ARCHIVED), end_date=run['last_date']))
    return comparisons, references


def summary(case, folder, run, products):
    group, seed, months, scenario = case
    identity = dict(group=group, seed=seed, months=months, scenario=scenario)
    score, factions, small = analyze(folder, run)
    score.update(relief_stats(folder, run | {'group':'F3'}))
    episode = list(table(folder, 'supply-episodes'))
    score.update(demand_stats(episode))
    escort = list(table(folder, 'escort-availability'))
    for key, src in (('resident_officers_mean','resident_officers'), ('available_officers_mean','available_officers'),
                     ('light_candidates_mean','light_escort_candidates'), ('heavy_candidates_mean','heavy_escort_candidates')):
        score[key]=distribution([number(row,src) for row in escort])['mean']
    score.update(escort_calls=len(escort), escort_roster_checks=run['v212']['counters'].get('roster_checks',0),
        march_departure_troops=run['v212']['march_departure_troops'],
        march_hunger_per_10000=rate(score['march_hunger_losses'],run['v212']['march_departure_troops'],10000),
        meeting_quotes=score['army_planning_counts'].get('meeting_quotes',0),
        occupation_assessments='not_collected',escort_reassignments='not_collected',escort_transfers='not_collected')
    products['small-faction-survival'].extend(small)
    products['faction-state'].extend(factions)
    reasons = Counter((row['original_reason'],row['rejection_reason']) for row in escort)
    products['escort-rejection-reasons'].extend(dict(identity,original_reason=a,rejection_reason=b,quotes=count)
                                                for (a,b), count in sorted(reasons.items()))
    products['unmet-army-supply'].extend(dict(identity)|row for row in episode if number(row,'remaining_unmet_grain'))
    for logfile in ('escort-assignments', 'pre-expedition-supply-plans', 'occupation-recovery'):
        receipts = records(folder, logfile)
        if receipts is not None:
            products[logfile].extend(dict(identity)|row for row in receipts)
            if logfile == 'occupation-recovery':
                score['occupation_assessments']=len(receipts)
                products['occupation-garrison-budget'].extend(dict(identity,turn=row['turn'])|row['details'] for row in receipts)
            elif logfile == 'escort-assignments':
                score['escort_reassignments']=sum('before' in r['details'] for r in receipts)
                score['escort_transfers']=sum(r['details'].get('result')=='transferred' for r in receipts)
    decisions = [row for row in records(folder,'war-recovery') or []]
    actions={(int(row['turn'])-1,row['owner']):loads(row['actions'])
             for row in table(folder,'action-capacity')}
    by_result=Counter(row['details']['result'] for row in decisions)
    for row in decisions:
        details=row['details']
        budget=details['recovery']
        if budget['other_fronts'] or budget['overlapping_fronts']:
            products['multi-front-commitments'].append(dict(identity,turn=row['turn'],owner=details['owner'],
                plan_id=details['plan_id'],target=details['target'],result=details['result'],
                fronts=budget['other_fronts'], overlapping=budget['overlapping_fronts'],
                reserve=budget.get('reserves_assigned',0), pledged_grain=budget.get('held_grain',0)))
        if details['result']=='deferred':
            products['strategic-decision-comparison'].append(dict(identity,turn=row['turn'],owner=details['owner'],
                plan_id=details['plan_id'],target=details['target'],attack=details['attack_score'],
                prepare=details['prepare_score'],same_turn_actions=actions.get((int(row['turn']),details['owner']),{})))
    score.update(recovery_results=dict(by_result), outcome=run['outcome'], head=run['head'])
    return score


def compare_scores(index):
    pairwise = []
    distributions = []
    selection = [(group, row) for (group,seed,months,scenario), row in index.items()
                 if group in ('F3',CANDIDATE) and (seed,months,scenario) in MATRIX]
    for metric, bounds in LIMITS.items():
        for group in ('F3',CANDIDATE):
            stats=distribution([row[metric] for k,row in selection if k==group])
            mean=stats['mean']
            distributions.append(dict(group=group,metric=metric,**stats,minimum=bounds[0],maximum=bounds[1],
                target_met=bounds[0]<=mean<=bounds[1] if type(mean) in (int,float) else None))
    measurable=set(LIMITS)|{key for keys in FIELDS.values() for key in keys}|{'small_survival_rate','grain_stock','strategic_surplus'}
    for (group,seed,months,scenario), candidate in index.items():
        base=index.get(('F3',seed,months,scenario))
        if group=='F3' or base is None:
            continue
        for key in sorted(measurable):
            a,b=base[key],candidate[key]
            pairwise.append(dict(group=group,seed=seed,months=months,scenario=scenario,metric=key,
                baseline=a,candidate=b,delta=round(b-a,6) if type(a) in (int,float) and type(b) in (int,float) else None))
    return pairwise, distributions


def build(args):
    indexed, errors = run_sources((args.baseline,args.pilots,args.candidate))
    needed = {('F3',*case) for case in MATRIX|LONG|HOLDOUT}
    needed |= {(CANDIDATE,*case) for case in MATRIX|LONG|HOLDOUT}
    needed |= {(group,*case) for group,case in product(('G1','G2','G3l'), PILOTS)}
    missing = sorted(needed-indexed.keys())
    if missing and not args.draft:
        raise ValueError(f'{len(missing)} required runs are missing: {missing}')
    indexed = {key:indexed[key] for key in sorted(needed&indexed.keys())}
    out = args.output/'data'
    products = defaultdict(list)
    scores = {k:summary(k,*entry,products) for k,entry in indexed.items()}
    pairwise, distributions = compare_scores(scores)
    emit(out,'scenario-scores',list(scores.values()))
    emit(out,'pairwise',pairwise)
    emit(out,'distributions',distributions)
    for name, fields in FIELDS.items():
        emit(out,name,[{k:row[k] for k in ('group','scenario','seed','months',*fields)} for row in scores.values()])
    for name, rows in products.items():
        emit(out,name,rows)
    for name, cohort in (('priority-comparison', PILOTS), ('parameter-experiments', PILOTS),
                         ('holdout-comparison', HOLDOUT), ('long-term-economy-comparison', LONG)):
        emit(out,name,[row for key,row in scores.items() if key[1:] in cohort and
                        (name!='parameter-experiments' or key[0] in ('F3','G1','G2'))])
    emit(out,'timely-supply-comparison',[row for row in pairwise if row['metric'] in FIELDS['army-supply-coverage']])
    with ZipFile(args.prior_archive) as archive:
        comparisons, reference = verify_history(archive,indexed)
        previous_reference = loads(archive.read('data/simulation-manifest.json'))['baseline']
        archived_groups = Counter(member.split('/')[2] for member in archive.namelist()
                                 if member.startswith('data/observed/') and member.endswith('/run.json'))
    to_json(out/'baseline-replay-parity.json',comparisons)
    history=dict(archive=args.prior_archive.name, path=str(args.prior_archive.resolve()),
                 sha256=digest(args.prior_archive), run_counts=dict(archived_groups), v21_reference=previous_reference)
    copied = []
    runs = []
    for case,(folder,run) in indexed.items():
        group,seed,months,scenario=case
        prefix=f'data/observed/{group}/{seed}/{months}/{scenario}/'
        members={}
        for file in sorted(folder.iterdir()):
            if not file.is_file():
                continue
            name=prefix+file.name
            if name in reference:
                members[file.name]=reference[name]
            else:
                members[file.name]=dict(member=name,sha256=digest(file))
                copied.append((file,name))
        runs.append(dict(group=group,seed=seed,months=months,scenario=scenario,
            head=run['head'],outcome=run['outcome'],turns=run['completed_turns'],
            rule_versions=run['rule_versions'],catalog_sha256=run['catalog_sha256'],
            observer=run['telemetry']['config'],parameters=run['parameters'],
            policy=run['v212'].get('profile',run['v211']['candidate_config']),files=members))
    to_json(out/'simulation-manifest.json',dict(prior_archive=history,runs=runs,missing=missing,errors=errors))
    checks=loads(args.checks.read_text(encoding='utf-8'))
    evidence=[]
    for key,name in checks['evidence'].items():
        path=args.checks.parent/name
        if not path.is_file():
            raise ValueError(f'Missing validation evidence: {path}')
        dest=args.output/'evidence'/name
        dest.parent.mkdir(exist_ok=True,parents=True)
        copy2(path,dest)
        evidence.append(dict(check=key,member='evidence/'+name,sha256=digest(dest)))
    to_json(out/'validation-manifest.json',dict(checks=checks['checks'],evidence=evidence,
        selected=CANDIDATE,required_run_count=len(needed),actual_run_count=len(runs),archive_reference_count=len(reference),
        status='draft' if missing else 'complete'))
    if args.archive is not None:
        paths = [(file, file.relative_to(args.output).as_posix())
                 for file in sorted(args.output.rglob('*')) if file.is_file() and file.name!='SHA256SUMS'] + copied
        hashes = {name:digest(file) for file,name in paths}
        manifest = args.output/'SHA256SUMS'
        manifest.write_text(''.join(f'{value}  {name}\n' for name,value in sorted(hashes.items())), encoding='utf-8')
        temporary = args.archive.with_suffix('.zip.part')
        with ZipFile(temporary,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
            archive.write(manifest, manifest.name)
            for file,name in paths:
                archive.write(file,name)
        with ZipFile(temporary) as archive:
            for name,value in hashes.items():
                if archive_digest(archive,name)!=value:
                    raise ValueError(f'Validation ZIP checksum failed: {name}')
        temporary.replace(args.archive)
        print(f'{args.archive}: {args.archive.stat().st_size:,} bytes, {len(runs)} observed runs, {len(reference)} referenced streams')


def main():
    parser = ArgumentParser(description=__doc__)
    for name in ('baseline','pilots','candidate','prior-archive','output','checks'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--draft',action='store_true')
    build(parser.parse_args())


if __name__=='__main__':
    main()
