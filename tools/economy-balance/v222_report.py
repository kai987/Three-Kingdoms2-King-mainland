"""Recalculate matched observations and package the V2.2.2 validation evidence."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from statistics import mean
import csv
import gzip
import hashlib
import json

from common import ROOT, git, to_csv, to_json
from v221_report import supply
from v222_experiments import STREAMS, cases, personnel_safe_terminal, source_identity
from remake import winter_weather as weather

METRICS = ('unpaid_city_turns','rations_missing','battles','ai_sorties','march_hunger_losses',
    'convoy_hunger_losses','convoy_grain_arrived','grain_stock','gold_stock','recruited','active_troops',
    'reserves','population','safe_pct_all','safe_pct_ended','unresolved_pct','dangerous_stalled',
    'long_stalled','safe_personnel_percent','winter_timely_percent','annual_timely_percent','mean_cpu_seconds',
    'historical_safe_return_pct')
RECEIVED = {'returned_home', 'received_elsewhere'}
PERIODS = ('regional-weather-daily.csv', 'snowfall-events.csv','snow-accumulation.csv',
           'river-ice-daily.csv','river-freeze-events.csv')
PRIOR_PREFIX = 'observed'
PREVIOUS_SHA = 'cc606fd31eeb120ac578caea2be085ee099ba32341b7ae44ac113a46f97b19b5'
EXPECTED = set().union(*(set(cases(wave)) for wave in ('focus','paired','long')))
ACCEPTANCE_CHECKS = {
    'environment.json','matrix.log','holdout.log','march-build.log','cargo.log','wasm.log',
    'transport-locales.log','fixture-relief-proof.json',
    'js-final.log','web-build.log','browser-emergency.log','convoy-emergency-zh.png','convoy-emergency-ja-mobile.png',
    'emergency-fixtures-final.log','full-suite-final.log','ci-registry.log','baseline-replay.log',
    'checkpoint-replay.log','guandu-candidate.log','guandu-baseline.log',
    'performance-observer-on-off.csv','cpu-profile-211.txt','cpu-profile-212.txt',
    'performance-stranded-77.json','cpu-stranded-77-I3.txt','cpu-stranded-77-J3.txt',
} | {f'{backend}-final-shard-{shard}.log' for backend in ('python','rust') for shard in range(1,7)}
RAW_ARTIFACTS = set(PERIODS) | {
    'run.json','monthly.csv','factions.csv','cities.csv','shortages.csv','battles.csv','troop-flows.csv','convoys.csv',
    'army-convoys.csv','army-requests.csv','supply-episodes.csv','supply-episodes-weather-aware.csv',
    'convoy-survival.csv','unresolved-convoy-cases.csv','transport-progress-daily.csv.gz',
    'convoy-resolution-daily.csv.gz','convoy-ledger.csv.gz','ice-transport-events.csv',
} | {f'{stream}.csv' for name,stream in STREAMS.items() if name!='convoy_ledger'}



def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rows(path):
    with (gzip.open(path,'rt',encoding='utf-8',newline='') if path.suffix=='.gz'
          else path.open(encoding='utf-8',newline='')) as stream:
        yield from csv.DictReader(stream)


def integer(row,key):
    value=row.get(key)
    return int(value) if value not in ('',None,'null','not_applicable') else 0


def percentage(part,total):
    return round(part*100/total,6) if total else None


def base(run):
    return dict(group=run['group'], strategy=run['strategy'], scenario=run['scenario'], seed=run['seed'],
                months=run['requested_months'])


def compare_archived(previous, path, run):
    band='long' if run['requested_months']==240 else 'holdout' if run['seed'] not in (2026,2027,2028) else 'matrix'
    prefix=f'{PRIOR_PREFIX}/{band}/I3-{run["strategy"]}/{run["seed"]}/{run["requested_months"]}/{run["scenario"]}/'
    filenames=('monthly.csv','factions.csv','cities.csv','convoys.csv','regional-weather-daily.csv',
               'river-ice-daily.csv','supply-episodes.csv','supply-episodes-weather-aware.csv')
    names=set(previous.namelist())
    result={'archive_member':prefix,'availability':'matched_archived_case' if prefix+'run.json' in names else 'no_matching_archived_case'}
    for name in filenames:
        key=name.split('.')[0].replace('-','_')
        if prefix+name in names:
            result[key]=hashlib.sha256(previous.read(prefix+name)).hexdigest()==sha(path/name)
        else:
            result[key]='not_available'
    return result


def ledger_check(path):
    initial={}
    exits={}
    moved=defaultdict(Counter)
    file_totals=Counter()
    transferred=Counter()
    reserves_at_cutoff={}
    ready={r['convoy_id']:r for r in rows(path/'convoy-survival.csv')}
    for event in rows(path/'convoy-events.csv'):
        if event['kind_of_event']=='transport_departed':
            ident=event['convoy_id']
            initial[ident]=integer(event,'current_grain_cargo')
            reserves_at_cutoff[ident]=integer(event,'initial_reserves')
    for entry in rows(path/'convoy-ledger.csv.gz'):
        ident=entry['convoy_id']
        before,after=(json.loads(entry[key]) for key in ('before','after'))
        if not all(n>=0 for n in (*before.values(),*after.values())):
            raise ValueError(f'Negative cargo in {path.name} convoy {ident}')
        if ident in exits and exits[ident]!=before or ident not in exits and before['grain']!=initial[ident]:
            raise ValueError(f'Discontinuous cargo ledger at {path.name} convoy {ident}')
        exits[ident]=after
        reserves_at_cutoff[ident]=after['reserves']
        kind=entry['kind_of_change']
        grain=before['grain']-after['grain']
        moved[ident][kind]+=grain
        file_totals[kind]+=grain
        if kind=='delivered':
            transfer=before['reserves']-after['reserves']
            transferred[ident]+=transfer
            file_totals['delivered_reserves']+=transfer
        if kind=='weather':
            file_totals['incident_reserves']+=before['reserves']-after['reserves']
    deliveries=Counter()
    for delivery in rows(path/'convoy-relief-deliveries.csv'):
        deliveries[delivery['sender']]+=integer(delivery,'actual_relief')
    if any(changes['convoy_supply']!=deliveries[ident] for ident,changes in moved.items()):
        raise ValueError(f'Field relief cargo/receipts differ under {path}')
    for ident,start in initial.items():
        final=integer(ready[ident],'remaining_cargo')
        if start-sum(moved[ident].values())!=final:
            raise ValueError(f'Cargo grain conservation failure in {path} convoy {ident}')
    return dict(file_totals),transferred,reserves_at_cutoff


def reconcile_cutoff(path,run,transferred,reserves_at_cutoff):
    """Apply settlement-boundary receipts issued after the last travel day."""
    survival=run['transport_survival']
    active={str(entry['id']):entry for entry in run['terminal']['convoy_loads']}
    cutoff=run['completed_turns']*10
    all_convoys=list(rows(path/'convoy-survival.csv'))
    era=dict(start_year=run['start_date'][0],start_month=run['start_date'][1])
    dormant=[]
    safe=0
    corrections=[]
    for item in all_convoys:
        ident=item['convoy_id']
        if item['actual_terminal_tick'] in ('','null'):
            final=active.pop(ident)
            held=integer(item,'current_reserves')
            remaining=reserves_at_cutoff[ident]
            if held!=remaining:
                corrections.append(dict(convoy_id=ident,cutoff_tick=cutoff,
                    last_daily_reserves=held,final_ledger_reserves=remaining,legally_transferred=transferred[ident]))
            idle=cutoff-integer(item,'last_effective_tick')
            item.update(current_phase=final['status'],current_reserves=remaining,
                        consecutive_unresolved_days=idle,days_since_last_effective_action=idle,
                        remaining_cargo=final['cargo_grain'],remaining_rations=final['escort_bag'])
            if item['delivered_tick'] not in ('','null'):
                item['days_since_delivery']=cutoff-integer(item,'delivered_tick')
            item['personnel_safe_end']=None
            dormant.append(item)
            continue
        if integer(item,'current_reserves')!=reserves_at_cutoff[ident]:
            raise ValueError(f'Terminal reserve receipt differs from the cargo ledger: {path} convoy {ident}')
        day=weather.date_at(era,integer(item,'actual_terminal_tick')+1)
        item['actual_terminal_date']='-'.join(map(str,day))
        item['personnel_safe_end']=personnel_safe_terminal(item,transferred[ident])
        safe+=item['personnel_safe_end']
    if active:
        raise ValueError(f'Missing final active convoys: {path}: {sorted(active)}')
    for name,records in (('convoy-survival',all_convoys),('unresolved-convoy-cases',dormant)):
        normalized=path/f'normalized-{name}.csv'
        if records:
            to_csv(normalized,records)
        else:
            header=(path/f'{name}.csv').read_text().strip()
            normalized.write_text(header+',personnel_safe_end\n',encoding='utf-8')
    totals={k:sum(integer(item,k) for item in all_convoys) for k in survival['totals']}
    safe_personnel=sum(integer(item,'current_escort')+integer(item,'current_reserves')
                       for item in all_convoys if item['terminal_status'] in RECEIVED)
    in_transit_personnel=sum(integer(item,'current_escort')+integer(item,'current_reserves') for item in dormant)
    survival=dict(survival,totals=totals,safe_ended=safe,safe_personnel=safe_personnel,
                  in_transit_personnel=in_transit_personnel)
    to_json(path/'normalized-run.json',dict(run,transport_survival=survival))
    return all_convoys,dormant,survival,corrections


def collect(path,run):
    key=base(run)
    final=list(rows(path/'monthly.csv'))[-1]
    year, winter=supply(run,path,'supply-episodes-weather-aware.csv')
    legacy, legacy_winter=supply(run,path,'supply-episodes.csv')
    ledger,transferred,reserve_cargo=ledger_check(path)
    all_convoys,dormant,survival,corrections=reconcile_cutoff(path,run,transferred,reserve_cargo)
    survivors=survival['totals']
    terminal=survival['states']
    departed,ended,unresolved,safe=(survival[n] for n in ('dispatched','ended','unresolved','safe_ended'))
    long_cases=[record for record in all_convoys if (integer(record,'max_consecutive_blocked_days')>=30
                 or record['terminal_status']=='dangerous_stalled')]
    observed_alive=sum(integer(record,'current_escort')+integer(record,'current_reserves')
                       for record in all_convoys if record['terminal_status']!='no_friendly_city')
    personnel=survivors['initial_escort']+survivors['initial_reserves']
    terminal_reserve_losses=sum(integer(record,'current_reserves') for record in all_convoys
                                if record['terminal_status']=='no_friendly_city')
    disbanded=terminal.get('no_friendly_city',0)
    max_convoy=max(all_convoys,key=lambda r:integer(r,'escort_hunger_loss')+integer(r,'reserve_hunger_loss'),default={})
    outgoing=sum(integer(record,'grain') for record in rows(path/'convoy-events.csv')
                 if record['kind_of_event']=='transport_departed')
    incoming=sum(integer(record,'grain') for record in rows(path/'convoy-events.csv')
                 if record['kind_of_event']=='transport_arrived')
    checks=(integer(final,'convoy_hunger_losses')==survivors['escort_hunger_loss']+survivors['reserve_hunger_loss'],
            departed==len(all_convoys),unresolved==len(dormant),outgoing==integer(final,'convoy_grain_sent'),
            incoming==integer(final,'convoy_grain_arrived'))
    if not all(checks):
        raise ValueError((path, checks))
    stats={k:integer(final,k) for k in METRICS if k in final}
    stats.update(recruited=integer(final,'raised_troops'), published_winter_required=winter.get('required',0),
        published_winter_timely=winter.get('timely',0),published_annual_required=year.get('required',0),
        published_annual_timely=year.get('timely',0),legacy_winter_required=legacy_winter.get('required',0),
        legacy_winter_timely=legacy_winter.get('timely',0),legacy_annual_required=legacy.get('required',0),
        legacy_annual_timely=legacy.get('timely',0), winter_timely_percent=percentage(winter.get('timely',0),winter.get('required',0)),
        annual_timely_percent=percentage(year.get('timely',0),year.get('required',0)),
        legacy_annual_timely_percent=percentage(legacy.get('timely',0),legacy.get('required',0)),
        mean_cpu_seconds=run['performance']['mean_turn_cpu_seconds'], ended=ended,dispatched=departed,
        unresolved=unresolved,safe_ended=safe, safe_pct_all=percentage(safe,departed),safe_pct_ended=percentage(safe,ended),
        unresolved_pct=percentage(unresolved,departed),dangerous_stalled=terminal.get('dangerous_stalled',0),
        long_stalled=len(long_cases), returned_home=terminal.get('returned_home',0),
        received_elsewhere=terminal.get('received_elsewhere',0),surrender_settlement=terminal.get('surrender_settlement',0),
        no_friendly_city=disbanded,not_delivered_in_transit=terminal.get('not_delivered_in_transit',0),
        delivered_returning=terminal.get('delivered_returning',0),initial_personnel=personnel,**survivors,
        legally_transferred_reserves=ledger.get('delivered_reserves',0),
        safely_received_escort_and_cargo_at_end=survival['safe_personnel'],still_in_transit_personnel=survival['in_transit_personnel'],
        surviving_personnel_observed=observed_alive+ledger.get('delivered_reserves',0),
        terminal_reserve_losses=terminal_reserve_losses,
        personnel_unreconciled=personnel-observed_alive-ledger.get('delivered_reserves',0)-terminal_reserve_losses
            -survivors['escort_hunger_loss']-survivors['reserve_hunger_loss']-survivors['other_troop_loss'],
        safe_personnel_percent=percentage(survival['safe_personnel']+ledger.get('delivered_reserves',0),personnel),
        all_escorts_exhausted=sum(bool(integer(record,'initial_escort') and not integer(record,'current_escort'))
                                 for record in all_convoys),
        max_convoy_hunger_loss=integer(max_convoy,'escort_hunger_loss')+integer(max_convoy,'reserve_hunger_loss'),
        max_hunger_convoy=max_convoy.get('convoy_id'),
        convoy_relief_requests=run['streams']['convoy-relief-requests'],convoy_relief_deliveries=run['streams']['convoy-relief-deliveries'],
        evacuation_orders=run['streams']['emergency-evacuation-plans'])
    stats['convoy_relief_dispatches']=sum(r['decision']=='dispatched' for r in rows(path/'convoy-relief-requests.csv'))
    stats['convoy_relief_grain_delivered']=sum(integer(r,'actual_relief') for r in rows(path/'convoy-relief-deliveries.csv'))
    stats['staged_orders']=sum(r['decision']=='staged' for r in rows(path/'emergency-evacuation-plans.csv'))
    army_relief={r['convoy_id'] for r in rows(path/'convoys.csv') if r.get('target_march') not in ('',None,'null')}
    for day in rows(path/'transport-progress-daily.csv.gz'):
        def n(field):
            return integer(day,field)
        if (n('start_work')-n('moved')!=n('end_work')
                or n('rations_before')+n('supply')-n('paid')!=n('rations_after')
                or n('cargo_before')-n('route_loss')-n('incident_loss')-n('cargo_to_bag')!=n('cargo_after')):
            raise ValueError(f'Physical work or ration ledger does not balance under {path} day {day}')
        ledger['daily_receipts']=ledger.get('daily_receipts',0)+1
        if day['convoy'] in army_relief:
            ledger['army_hunger']=ledger.get('army_hunger',0)+n('hunger_loss')
    stats['army_relief_hunger_losses']=ledger.get('army_hunger',0)
    docked=sum(terminal.get(k,0) for k in ('returned_home','received_elsewhere','surrender_settlement'))
    stats['historical_safe_return_pct']=percentage(docked,ended)
    return (dict(key,run_status=run['outcome'],completed_turns=run['completed_turns'], **stats),
            [dict(key,**r) for r in dormant], [dict(key,**r) for r in long_cases],ledger,
            [dict(key,**r) for r in corrections])


def validate_weather(games):
    checks=[]
    for (seed,scene,strategy,group,months),(folder,run) in sorted(games.items()):
        other=games.get((seed,scene,strategy,'I3',months))
        if group=='I3' or other is None:
            continue
        path,old=other
        if (old['catalog_sha256'],old['weather_seed'])!=(run['catalog_sha256'],run['weather_seed']):
            raise ValueError('Paired scenario or weather seed changed')
        def equal(name):
            if run['completed_turns']==old['completed_turns']:
                return sha(path/name)==sha(folder/name)
            # A naturally ended campaign only covers the common time window.
            tick=min(run['completed_turns'],old['completed_turns'])*10
            return ([r for r in rows(path/name) if integer(r,'tick')<=tick] ==
                    [r for r in rows(folder/name) if integer(r,'tick')<=tick])
        checks.append(dict(base(run),through_tick=min(run['completed_turns'],old['completed_turns'])*10,
                           **{name.removesuffix('.csv').replace('-','_'):equal(name) for name in PERIODS}))
    if any(not val for r in checks for key,val in r.items() if key not in
           {'group','scenario','seed','months','strategy','through_tick'}):
        raise ValueError('Paired weather drift')
    return checks


def write(folder,name,records,*,header='scenario,seed,strategy,group,months'):
    target=folder/f'{name}.csv'
    if records:
        to_csv(target,records)
    else:
        target.write_text(header+'\n',encoding='utf-8')


def exports(root,older):
    actual={}
    failed=[]
    sources=set()
    for f in (root/'observed').glob('*/*/*/*/run.json'):
        run=json.loads(f.read_text())
        key=(run['seed'],run['scenario'],run['strategy'],run['group'],run['requested_months'])
        if run['outcome'] in ('complete','natural_end'):
            actual[key]=(f.parent,run)
            sources.add(run['source_tree_sha256'])
        else:
            failed.append(dict(base(run),failure=run['failure']))
    if len(sources)>1:
        raise ValueError(f'Mixed experiment sources {sources}')
    current=source_identity()
    changes=[]
    if sources and sources!={current['tree_sha256']}:
        before=json.loads((root/'sources'/f'{next(iter(sources))}.json').read_text())['files']
        after=current['files']
        changes=sorted(name for name in before.keys()|after.keys() if before.get(name)!=after.get(name))
        if changes!=['tools/economy-balance/v222_experiments.py']:
            raise ValueError(f'Observation runtime inputs changed: {changes}')
    to_json(root/'sources'/f"{current['tree_sha256']}.json",current)
    observation=root/'exports'
    observation.mkdir(parents=True,exist_ok=True)
    metrics=[]; unresolved=[]; long=[]; ledgers=[]; historical=[]; boundary_fixes=[]
    if sha(older)!=PREVIOUS_SHA:
        raise ValueError('Historical evidence hash changed')
    with ZipFile(older) as prior:
        for _,(path,run) in sorted(actual.items()):
            score,stranded,long_cases,ledger,corrections=collect(path,run)
            metrics.append(score)
            unresolved.extend(stranded)
            long.extend(long_cases)
            boundary_fixes.extend(corrections)
            ledgers.append(dict(base(run),**{k:ledger.get(k,0) for k in (
                'rations','bag_return','route_loss','weather','army_supply','convoy_supply','delivered',
                'delivered_reserves','incident_reserves','daily_receipts')}))
            if run['group']=='I3':
                historical.append(dict(base(run),**compare_archived(prior,path,run)))
    write(observation,'archived-I3-identity',historical)
    write(observation,'weather-sequence-checks',validate_weather(actual))
    write(observation,'cargo-ledger-checks',ledgers)
    write(observation,'settlement-boundary-reconciliation',boundary_fixes)
    write(observation,'scenario-scores',metrics)
    index={(r['seed'],r['scenario'],r['strategy'],r['group'],r['months']):r for r in metrics}
    paired=[]
    for key,r in index.items():
        seed,scene,strategy,group,months=key
        base_row=index.get((seed,scene,strategy,'I3',months))
        if base_row and group!='I3':
            for field in METRICS:
                a,b=base_row[field],r[field]
                paired.append(dict(seed=seed,scenario=scene,strategy=strategy,group=group,months=months,
                    metric=field,i3=a,candidate=b,delta=round(b-a,6) if a is not None and b is not None else None))
    write(observation,'pairwise',paired)
    write(observation,'unresolved-convoy-cases',unresolved)
    write(observation,'long-convoy-cases',long)
    datekeys=('group','strategy','scenario','seed','months')
    comparison={
        'emergency-transport-comparison':('evacuation_orders','staged_orders','long_stalled','dangerous_stalled'),
        'emergency-evacuation-comparison':('evacuation_orders','staged_orders','received_elsewhere'),
        'convoy-relief-comparison':('convoy_relief_requests','convoy_relief_dispatches','convoy_relief_deliveries','convoy_relief_grain_delivered'),
        'convoy-survival-comparison':('initial_escort','initial_reserves','current_escort','current_reserves','initial_officers',
            'current_officers','initial_civil_staff','current_civil_staff','escort_hunger_loss','reserve_hunger_loss','other_troop_loss',
            'safe_personnel_percent','safely_received_escort_and_cargo_at_end','legally_transferred_reserves','still_in_transit_personnel',
            'surviving_personnel_observed','terminal_reserve_losses','personnel_unreconciled',
            'all_escorts_exhausted'),
        'convoy-terminal-comparison':('dispatched','returned_home','received_elsewhere','no_friendly_city','surrender_settlement',
            'delivered_returning','not_delivered_in_transit','dangerous_stalled','unresolved'),
        'safe-return-comparison':('dispatched','ended','safe_ended','unresolved','safe_pct_all','safe_pct_ended','unresolved_pct','historical_safe_return_pct'),
        'convoy-hunger-comparison':('convoy_hunger_losses','escort_hunger_loss','reserve_hunger_loss',
            'max_convoy_hunger_loss','max_hunger_convoy','army_relief_hunger_losses'),
        'winter-army-supply-comparison':('published_winter_required','published_winter_timely','winter_timely_percent',
            'legacy_winter_required','legacy_winter_timely'),
        'winter-shortage-comparison':('unpaid_city_turns','rations_missing','published_winter_required','published_winter_timely'),
        'performance-comparison':('mean_cpu_seconds',),
        'long-term-economy-comparison':('grain_stock','gold_stock','active_troops','reserves','population',
            'unpaid_city_turns','rations_missing','battles','march_hunger_losses','convoy_hunger_losses','winter_timely_percent'),
    }
    for name,fields in comparison.items():
        write(observation,name,[{k:r[k] for k in (*datekeys,*fields)}
              for r in metrics if r['months']==240 or name!='long-term-economy-comparison'])
    magnitude=[]
    for wave in ('focus','paired','long','holdout'):
        design=set(cases(wave))
        selected=[r for key,r in index.items() if key in design]
        for strategy,group,months in sorted({(r['strategy'],r['group'],r['months']) for r in selected}):
            found=[r for r in selected if (r['strategy'],r['group'],r['months'])==(strategy,group,months)]
            means={k:round(mean(r[k] for r in found if r[k] is not None),5)
                   if any(r[k] is not None for r in found) else None for k in METRICS}
            magnitude.append(dict(wave=wave,strategy=strategy,group=group,months=months,runs=len(found),**means))
    write(observation,'sample-means',magnitude)
    return dict(schema='weather-v222-validation-r1',baseline_commit='1e521fa67fc54c7ae16f4195f8adafbfe2891e6d',
        current_git_head=git('rev-parse','HEAD').decode().strip(),source_tree_sha256=next(iter(sources),None),
        delivered_source_tree_sha256=current['tree_sha256'], postprocessing_adjusted_sources=changes,
        normalization=('strategic terminal date = start + terminal tick; personnel-safe endings use actual surviving groups; '
                       'right-censored cargo uses the latest physical receipt, including last-boundary settlements'),
        expected=len(EXPECTED),completed=len(EXPECTED&actual.keys()),
        additional_controls=len(actual.keys()-EXPECTED),failed=failed,
        missing=[dict(seed=s,scenario=c,strategy=a,group=g,months=m) for s,c,a,g,m in sorted(EXPECTED-actual.keys())],
        runs=[dict(base(run),head=run['head'],path=str(path.relative_to(root)),catalog_sha256=run['catalog_sha256'],
                   weather_seed=run['weather_seed'],backend=run['backend']['engine'],rules=run['rule_versions'])
              for _,(path,run) in sorted(actual.items())])


def archive_references(sources, older):
    """Pin byte-identical I3 inputs to the existing V2.2.1 validation archive."""
    references={}
    with ZipFile(older) as previous:
        inventory=json.loads(previous.read('validation-manifest.json'))['files']
        for rel,file in list(sources.items()):
            parts=Path(rel).parts
            if len(parts)!=6 or parts[0]!='observed' or not parts[1].startswith('I3-'):
                continue
            group,seed,months,scene,name=parts[1:]
            wave='long' if months=='240' else 'matrix' if seed in ('2026','2027','2028') else 'holdout'
            member=f'observed/{wave}/{group}/{seed}/{months}/{scene}/{name}'
            original=inventory.get(member)
            if original and file.stat().st_size==original['bytes'] and sha(file)==original['sha256']:
                references[rel]=dict(member=member,**original)
                del sources[rel]
    return references


def check_package(archive, older, manifest):
    """Check the published bytes as well as the referenced archive members."""
    def check(bundle, name, entry):
        if bundle.getinfo(name).file_size!=entry['bytes']:
            raise ValueError(f'Archive member size mismatch: {name}')
        with bundle.open(name) as file:
            if hashlib.file_digest(file,'sha256').hexdigest()!=entry['sha256']:
                raise ValueError(f'Archive member SHA-256 mismatch: {name}')

    files=manifest['files']
    references=manifest['referenced_files']
    with ZipFile(archive) as bundle, ZipFile(older) as prior:
        names=bundle.namelist()
        if len(names)!=len(files)+1 or set(names)!=set(files)|{'validation-manifest.json'}:
            raise ValueError('Acceptance archive inventory differs from its manifest')
        for name,entry in files.items():
            check(bundle,name,entry)
        for entry in references.values():
            check(prior,entry['member'],entry)
        if json.loads(bundle.read('validation-manifest.json'))!=manifest:
            raise ValueError('Archive manifest differs from the verified inventory')


def package(root,older,report):
    prior_reference=dict(path=str(older.resolve()),sha256=sha(older),bytes=older.stat().st_size)
    docs=ROOT/'docs/weather-v222'
    tools=ROOT/'tools/economy-balance'
    sources={
        'simulation-manifest.json':root/'simulation-manifest.json',
        **{f'docs/{p.name}':p for p in docs.glob('*.md')},
        **{f'reproduction-tools/{p.name}':p for p in tools.glob('v222_*.py')},
    }
    for section in ('exports','checks','sources','observed','reproduction'):
        for file in (root/section).rglob('*'):
            if not file.is_file() or any(part.startswith('.') for part in file.relative_to(root).parts):
                continue
            rel=file.relative_to(root)
            if section=='checks' and file.name not in ACCEPTANCE_CHECKS:
                continue
            if section=='observed' and file.name not in RAW_ARTIFACTS:
                continue
            if section=='reproduction' and not (
                    file.name in ('node-decisions.json','historical-replay-checks.json','prior-two-cases.json')
                    or rel.parts[1]=='checkpoints'):
                continue
            if section=='observed' and file.name in ('convoy-survival.csv','unresolved-convoy-cases.csv','run.json'):
                sources[rel.as_posix()]=file.with_name('normalized-'+file.name)
            else:
                sources[rel.as_posix()]=file
    references=archive_references(sources,older)
    files={rel:dict(bytes=p.stat().st_size,sha256=sha(p)) for rel,p in sorted(sources.items())}
    manifest=dict(schema='weather-v222-delivery-r1',previous_package=prior_reference,
                  source_commit=report['current_git_head'],files=files,referenced_files=references)
    to_json(root/'validation-manifest.json',manifest)
    archive=root/'three-kingdoms-weather-v222-validation.zip'
    intermediate=archive.with_suffix('.partial')
    with ZipFile(intermediate,'w',compression=ZIP_DEFLATED,compresslevel=5) as bundle:
        for rel,p in sorted(sources.items()):
            bundle.write(p,rel)
        bundle.write(root/'validation-manifest.json','validation-manifest.json')
    check_package(intermediate,older,manifest)
    intermediate.replace(archive)
    checksum=sha(archive)
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n')
    print(archive,archive.stat().st_size,checksum,len(files),'files',len(references),'prior references',flush=True)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--package',action='store_true')
    args=parser.parse_args()
    report=exports(args.output,args.previous)
    to_json(args.output/'simulation-manifest.json',report)
    print(report['completed'],'/',report['expected'],'completed',len(report['failed']),'failed',
          report['additional_controls'],'optional controls',flush=True)
    if args.package:
        if report['missing'] or report['failed']:
            parser.error('A final validation archive requires the complete primary observation matrix')
        package(args.output,args.previous,report)


if __name__=='__main__':
    main()
