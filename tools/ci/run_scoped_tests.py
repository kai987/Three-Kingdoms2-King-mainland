#!/usr/bin/env python3
"""Execute a closed Python CI plan without weakening full-release test coverage.

List mode reads inventories only. Scoped mode validates every current catalog's
identity/references, then runs registered related modules and selected real
three-turn campaigns. Full mode delegates unchanged discovery to the existing
three-shard runner for both arithmetic backends, with no test-name filtering.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.ci import run_campaign_tests as runner

SCENARIO_ID=re.compile(r'mainland[0-9]{3}-[0-9]{2}(?:-[a-z][a-z0-9]*(?:-[a-z0-9]+)*)?\Z')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def require(condition,message):
    if not condition:raise ValueError(message)

def inventory(root=ROOT):
    source=read(root/'game/config/campaigns/index.json')
    compiled=read(root/'game/data/campaigns/index.json')
    require(source.get('schema')=='tk2-campaign-sources-v1','Unknown canonical campaign index')
    require(compiled.get('schema')=='tk2-campaign-index-v1','Unknown current campaign index')
    entries=source.get('scenarios');require(isinstance(entries,list)and bool(entries),'Current scenario inventory is empty')
    identities={};paths={}
    for row in entries:
        identity=row.get('id');name=row.get('file')
        require(isinstance(identity,str)and SCENARIO_ID.fullmatch(identity),'Invalid current scenario ID')
        require(isinstance(name,str)and name.startswith('scenarios/')and '..' not in Path(name).parts and Path(name).suffix=='.json','Invalid canonical scenario path')
        require(Path(name).name==identity.removeprefix('mainland')+'.json','Scenario ID and canonical filename disagree')
        require(type(row.get('year'))is int and type(row.get('month'))is int and 1<=row['month']<=12,'Invalid canonical scenario date')
        require('-'.join(identity.removeprefix('mainland').split('-')[:2])==f"{row['year']}-{row['month']:02d}",'Scenario ID and canonical date disagree')
        require(identity not in identities,'Duplicate source scenario ID')
        output='campaigns/'+Path(name).name
        require(output not in paths.values(),'Duplicate compiled scenario path')
        identities[identity]=row;paths[identity]=output
    require(set(compiled.get('catalogs',[]))==set(paths.values())and len(compiled['catalogs'])==len(paths),'Compiled/source catalog inventory differs')
    require(source['default']==compiled.get('default')and source['default']in identities,'Current default scenario identity differs')
    require({p.relative_to(root/'game/config/campaigns').as_posix()for p in(root/'game/config/campaigns/scenarios').glob('*.json')}=={row['file']for row in entries},'Unindexed/stale canonical scenario file')
    summaries=compiled.get('summary',[])
    require(isinstance(summaries,list)and len(summaries)==len(identities)and {row.get('id')for row in summaries}==set(identities),'Compiled menu summary identity differs')
    require({p.name for p in (root/'game/data/campaigns').glob('*.json')}=={Path(p).name for p in paths.values()}|{'index.json'},'Unindexed/stale compiled campaign file')
    return identities,paths

PYTHON_GROUPS=runner.GROUPS|{'global','compat','all'}

def python_groups(plan):
    if 'python_groups' in plan:return plan['python_groups']
    if plan['mode']=='docs':return []
    if plan['full']:return ['all']
    return ['global',*plan['groups'],*(['compat']if plan['native']else[])]

def validate_plan(value,current_ids):
    require(isinstance(value,dict),'Plan must be an object')
    mode=value.get('mode');require(mode in('docs','scoped','full'),'Unknown CI plan mode')
    require(type(value.get('full'))is bool and value['full']==(mode=='full'),'CI full flag/mode disagree')
    require(type(value.get('native'))is bool,'CI native flag must be boolean')
    groups=value.get('groups');ids=value.get('scenario_ids')
    require(isinstance(groups,list)and all(isinstance(group,str)for group in groups)and len(groups)==len(set(groups))and set(groups)<=runner.GROUPS,'Unknown or duplicate CI group')
    require(isinstance(ids,list)and all(isinstance(i,str)and SCENARIO_ID.fullmatch(i)for i in ids)and len(ids)==len(set(ids)),'Invalid or duplicate planned scenario IDs')
    require(not set(ids)-set(current_ids),'Unknown current scenario ID in CI plan')
    require(mode!='full'or not ids,'Full plans use an empty scenario_ids list to select every current catalog')
    pgroups=python_groups(value)
    require(isinstance(pgroups,list)and all(isinstance(g,str)for g in pgroups)and len(pgroups)==len(set(pgroups))and set(pgroups)<=PYTHON_GROUPS,'Invalid Python group selection')
    require(not {'scenarios','compat'}&set(pgroups)or value['native'],'Selected real-catalog parity requires the native artifact')
    require(mode!='scoped'or 'scenarios'not in pgroups or bool(ids),'Scenario-local Python checks require selected scenario IDs')
    require(mode!='scoped'or bool(groups),'Scoped CI plan has no test groups')
    removed=value.get('removed_scenario_ids',[])
    require(isinstance(removed,list)and all(isinstance(i,str)and SCENARIO_ID.fullmatch(i)for i in removed),'Invalid removed scenario provenance')
    require(not set(removed)&set(current_ids),'Removed scenario ID is still in the current inventory')
    require(not removed or mode=='full','Removing a scenario requires full discovery')
    return value

def selected_modules(plan,registry):
    if plan['mode']=='docs':return []
    if plan['mode']=='full':return sorted(registry['modules'])
    groups=set(python_groups(plan));identities=set(plan['scenario_ids']);selected=[]
    for name,row in registry['modules'].items():
        tier=row['tier']
        choose=tier=='global'or tier=='related'and bool(groups&set(row.get('groups',[])))
        if choose and row.get('scenario_ids'):choose=bool(identities&set(row['scenario_ids']))
        if tier=='compatibility':choose='compat'in groups
        if choose:selected.append(name)
    return sorted(selected)

def resolve_backends(plan,choice=None):
    if choice is None:
        configured=os.environ.get('MARCH_CORE_BACKEND')
        choice=(configured if configured in('python','rust')else'both')if plan['full']or plan['native']else'python'
    return ['python','rust']if choice=='both'else[choice]

def execution_plan(plan,registry,*,backend=None,shard=None,shards=None,root=ROOT):
    identities,_=inventory(root);validate_plan(plan,identities)
    require((shard is None)==(shards is None),'--shard and --shards must be provided together')
    require(shard is None or plan['full'],'Shard arguments are only accepted for full discovery')
    if shard is not None:
        require(shards==3,'Full CI uses the existing three-shard contract')
        runner.select_shard([],shard,shards)
    backends=resolve_backends(plan,backend)
    modules=selected_modules(plan,registry)
    if plan['full']and shard is not None:modules=runner.select_shard(modules,shard,shards)
    if plan['full']:
        shard_ids=[shard]if shard is not None else[1,2,3]
        count=shards if shards is not None else 3
        invocations=[dict(backend=b,argv=[sys.executable,'-B',str(root/'tools/ci/run_campaign_tests.py'),'--shard',str(i),'--shards',str(count)])for b in backends for i in shard_ids]
    else:invocations=[]
    return dict(schema='tk2-ci-python-execution-v1',mode=plan['mode'],status='planned',groups=plan['groups'],python_groups=python_groups(plan),
        backends=[]if plan['mode']=='docs'else backends,files=modules,file_count=len(modules),
        global_catalog_count=len(identities),scenario_ids=sorted(identities)if plan['full']else plan['scenario_ids']if 'scenarios'in python_groups(plan)else[],
        full_invocations=invocations,shard=shard,shards=3 if plan['full']else None,native_required=bool(plan['full']or plan['native']),
        removed_scenario_ids=plan.get('removed_scenario_ids',[]))

def global_catalog_checks(root=ROOT):
    """Raw JSON only: all current IDs, references and stable runtime identities."""
    identities,paths=inventory(root);person_identity=None;checked=[]
    for identity in identities:
        row=identities[identity];data=read(root/'game/data'/paths[identity]);source=read(root/'game/config/campaigns'/row['file'])
        require(source.get('schema')=='tk2-campaign-override-v1'and source.get('id')==identity,f'{identity}: canonical identity differs')
        require(data.get('schema')=='tk2-campaign-v1'and data.get('id')==identity,f'{identity}: current catalog identity differs')
        require((data.get('start_year'),data.get('start_month'))==(row['year'],row['month']),f'{identity}: current date differs')
        require(type(row['year'])is int and type(row['month'])is int and 1<=row['month']<=12,f'{identity}: invalid scenario date')
        cities=[c['id']for c in data['cities']];city_ids=set(cities);active=set(data['active_cities']);factions={f['id']for f in data['factions']}
        people=data['people'];mapping={p['person_id']:p['runtime_id']for p in people};runtime_ids=set(mapping.values())
        require(len(cities)==len(city_ids)==data['city_count'],f'{identity}: duplicate/count city identity')
        require(active<=city_ids and set(data['initial_owners'])==active,f'{identity}: invalid active/owner city reference')
        require(set(data['initial_owners'].values())<=factions|{'neutral'},f'{identity}: unknown initial owner')
        require(len(factions)==len(data['factions'])and all(f['city']in active for f in data['factions']),f'{identity}: duplicate/invalid faction reference')
        require(len(mapping)==len(runtime_ids)==len(people)==data['officer_count'],f'{identity}: duplicate/count person identity')
        require(all(type(i)is int and 0<=i<data['rules']['runtime_capacity']for i in runtime_ids),f'{identity}: invalid runtime person ID')
        require(person_identity is None or mapping==person_identity,f'{identity}: shared runtime/person mapping differs');person_identity=mapping
        require(set(data['era_assignments'])==set(mapping),f'{identity}: missing/extra person placement plan')
        require(set(data['faction_rulers'])==factions and all(type(i)is int and i in runtime_ids for i in data['faction_rulers'].values()),f'{identity}: invalid faction ruler reference')
        require(all(pid in mapping and city in city_ids for pid,city in data['appearance_locations'].items()),f'{identity}: invalid appearance location reference')
        require(data['rules']['city_officer_capacity']==99 and data['rules']['battle_officers_per_side']==10,f'{identity}: current 99/10 rule differs')
        require(data['calendar_rules']==dict(turn_days=10,month_days=30,turn_start_days=[1,11,21],monthly_settlement='month_rollover'),f'{identity}: invalid ten-day calendar format')
        assigned=[]
        for initial in data['initial_officers']+data['initial_free_officers']:
            require(initial['person_id']in mapping and initial['city']in active,f'{identity}: invalid initial officer reference')
            assigned.append(initial['person_id'])
        require(len(assigned)==len(set(assigned)),f'{identity}: duplicate initial officer assignment')
        rosters=Counter(row['city']for row in data['initial_officers'])
        require(all(size<=data['rules']['city_officer_capacity']for size in rosters.values()),f'{identity}: initial city officer capacity exceeded')
        for initial in data['initial_officers']:
            posting=data['era_assignments'][initial['person_id']];owner=data['initial_owners'][initial['city']]
            require(posting.get('faction')in factions and posting.get('city')==initial['city']and posting['faction']==owner,f'{identity}: initial owned posting and city owner disagree')
            for field in('faction','faction_id','initial_faction'):
                if field in initial:require(initial[field]in factions and initial[field]==owner,f'{identity}: invalid explicit initial faction reference')
        for initial in data['initial_free_officers']:
            posting=data['era_assignments'][initial['person_id']]
            # Free officers occupy a location, not a faction's 99-place roster.
            require(posting.get('faction')is None and posting.get('city')==initial['city'],f'{identity}: invalid initial free-officer posting')
        for field in('initial_city_resources','city_income'):
            require(set(data[field])==city_ids,f'{identity}: missing/extra city resource reference')
            require(all(type(value)is int and value>=0 for item in data[field].values()for value in item.values()),f'{identity}: negative/noninteger {field}')
        require(all(len(edge)==2 and set(edge)<=city_ids for edge in data['links']),f'{identity}: invalid road endpoint')
        for route in data.get('travel_routes',[])+data.get('exploration_routes',[]):
            require(route['from']in city_ids and route['to']in city_ids,f'{identity}: invalid route endpoint')
        for pid,windows in data['appearance_windows'].items():
            require(pid in mapping and all(w['city']in city_ids for w in windows),f'{identity}: invalid dated appearance reference')
        checked.append(dict(id=identity,path=paths[identity],initial_serving=len(data['initial_officers']),initial_free=len(data['initial_free_officers']),max_owned_city_roster=max(rosters.values(),default=0),sha256=hashlib.sha256((root/'game/data'/paths[identity]).read_bytes()).hexdigest()))
    return dict(status='passed',catalog_count=len(checked),catalogs=checked)

def module_at(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def check_selected_sources(identities,root=ROOT):
    """Use the actual builder on a read-only subset of current canonical inputs."""
    source_index,_=inventory(root);builder=module_at('ci_selected_campaign_builder',root/'game/build_campaigns.py')
    original_source=builder.SOURCE
    try:
        with tempfile.TemporaryDirectory(prefix='tk-ci-canonical-')as folder:
            current=Path(folder);(current/'scenarios').mkdir()
            for name in('people.json','shared.json'):shutil.copyfile(original_source/name,current/name)
            entries=[source_index[identity]for identity in identities]
            (current/'index.json').write_text(json.dumps(dict(schema='tk2-campaign-sources-v1',default=identities[0],scenarios=entries)))
            for row in entries:shutil.copyfile(original_source/row['file'],current/row['file'])
            builder.SOURCE=current
            _,catalogs=builder.load_sources()
            for data in catalogs:
                row=source_index[data['id']];raw=(root/'game/data/campaigns'/Path(row['file']).name).read_bytes()
                require(raw==builder.encoded(data),f'{data["id"]}: current catalog is stale; rebuild it from canonical sources')
    finally:builder.SOURCE=original_source
    return dict(status='passed',scenario_ids=list(identities))

def scenario_smoke(identities,backends=('python','rust'),*,root=ROOT,turns=3):
    """Actual new/AI/arrival/combat/month/save services, with exact backend parity."""
    if not identities:return []
    sys.path.insert(0,str(root/'source'))
    from remake.campaign import Catalog,canonical,digest
    from remake.march_core import using_backend
    soak=module_at('ci_selected_campaign_soak',root/'tools/campaign-soak/run.py')
    _,paths=inventory(root);results=[]
    for identity in identities:
        require(identity in paths,f'Unknown smoke catalog: {identity}')
        catalog=Catalog(root/'game/data'/paths[identity]);faction='wei'if'wei'in catalog.factions else next(iter(catalog.factions))
        outputs=[];saves=[]
        for backend in backends:
            with using_backend(backend):
                replay=soak.Replay(catalog,faction,2026,backend)
                state=replay.game.state
                require((state.year,state.month,state.day,state.turn)==(catalog.data['start_year'],catalog.data['start_month'],1,1),f'{identity}: opening date differs')
                require(set(state.cities)==set(catalog.data['active_cities']),f'{identity}: opening active cities differ')
                for city in state.cities.values():
                    require(city.owner==catalog.data['initial_owners'][city.id],f'{identity}: initial owner differs for {city.id}')
                    stock=catalog.data['initial_city_resources'][city.id]
                    require(all(getattr(city,key)==stock[key]for key in('gold','grain','reserves')),f'{identity}: initial stock differs for {city.id}')
                    require(len(city.roster.officer_ids)<=99,f'{identity}: opening officer capacity exceeded')
                result=replay.run(turns);saved=replay.game.export_save();replay.game.validate(replay.game.state)
                require(result['completed_turns']==turns,f'{identity}: three-turn smoke ended before its coverage target')
                outputs.append({k:v for k,v in result.items()if k!='backend'});saves.append(saved)
        require(all(result==outputs[0]for result in outputs),f'{identity}: Python/Rust state/save/RNG/transcript differs')
        for saved in saves:
            for backend in backends:
                with using_backend(backend):
                    clone=soak.HeadlessCampaign(catalog);clone.load_save(deepcopy(saved),0)
                    require(canonical(clone.export_save())==canonical(saved),f'{identity}: cross-backend save load changed canonical checksum/state/RNG')
        results.append(dict(id=identity,backends=list(backends),turns=outputs[0]['completed_turns'],commands=outputs[0]['commands'],
            state_sha256=digest(saves[0]['state']),save_sha256=outputs[0]['final_save_sha256'],
            command_sha256=outputs[0]['command_sha256'],rng=outputs[0]['final']['rng'],cross_backend_save_checks=len(saves)*len(backends)))
    return results

@contextmanager
def backend_environment(backend):
    before=os.environ.get('MARCH_CORE_BACKEND');os.environ['MARCH_CORE_BACKEND']=backend
    try:yield
    finally:
        if before is None:os.environ.pop('MARCH_CORE_BACKEND',None)
        else:os.environ['MARCH_CORE_BACKEND']=before

def validate_required_result(outcome,backend):
    require(outcome.testsRun>0,'Required Python suite was empty for '+backend)
    require(not outcome.skipped,'Required Python tests skipped for '+backend+': '+repr(outcome.skipped))
    require(outcome.wasSuccessful(),'Related Python tests failed for '+backend)

def run(plan,execution,*,root=ROOT):
    result=deepcopy(execution);started=time.monotonic();result['status']='running'
    if plan['mode']=='docs':result.update(status='skipped',elapsed_seconds=0);return result
    result['global_catalog_checks']=global_catalog_checks(root)
    if execution['native_required']or'rust'in execution['backends']:
        sys.path.insert(0,str(root/'source'))
        from remake.march_core import invoke,using_backend
        with using_backend('rust'):invoke('allocate',troops=[1],numerator=1,denominator=1)
    if plan['full']:
        require((root/'tools/web-runtime/node_modules/pyodide/package.json').is_file(),'Install the pinned tools/web-runtime before full discovery; release artifact tests must not skip')
        require(shutil.which('node')is not None,'Node.js is required for full save-boundary discovery')
        for invocation in execution['full_invocations']:
            environment=dict(os.environ,MARCH_CORE_BACKEND=invocation['backend'])
            subprocess.run(invocation['argv'],cwd=root,env=environment,check=True)
    else:
        files=[root/name for name in execution['files']]
        for backend in execution['backends']:
            with backend_environment(backend):
                suite=runner.load_suite(files,root/'tests',root/'source')
                outcome=unittest.TextTestRunner(verbosity=2,stream=sys.stdout).run(suite)
                result.setdefault('module_runs',[]).append(dict(backend=backend,cases=outcome.testsRun,failures=len(outcome.failures),errors=len(outcome.errors),skipped=len(outcome.skipped)))
                validate_required_result(outcome,backend)
        if 'scenarios'in python_groups(plan):
            result['selected_source_checks']=check_selected_sources(plan['scenario_ids'],root)
            # A scenario-local run always checks both actual arithmetic adapters,
            # even when a caller restricted related-module execution to one backend.
            result['scenario_smoke']=scenario_smoke(plan['scenario_ids'],('python','rust'),root=root)
    result.update(status='passed',elapsed_seconds=round(time.monotonic()-started,3));return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--list-only',action='store_true');parser.add_argument('--report',type=Path)
    parser.add_argument('--backend',choices=['python','rust','both']);parser.add_argument('--shard',type=int);parser.add_argument('--shards',type=int)
    args=parser.parse_args(argv)
    try:
        registry,registry_sha=runner.load_registry();plan=read(args.plan)
        execution=execution_plan(plan,registry,backend=args.backend,shard=args.shard,shards=args.shards)
        execution.update(registry_sha256=registry_sha,all_file_count=len(registry['modules']))
        print(json.dumps(execution,ensure_ascii=False,sort_keys=True),flush=True)
        result=execution if args.list_only else run(plan,execution)
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        return 0
    except (ValueError,OSError,RuntimeError,AssertionError,subprocess.CalledProcessError)as error:
        if args.report:
            failure=dict(execution if 'execution'in locals()else {},status='failed',error=str(error))
            args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(failure,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        print(str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
