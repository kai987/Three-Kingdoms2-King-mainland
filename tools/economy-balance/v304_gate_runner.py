"""Run the closed Python/Rust test inventory and retain reproducible evidence."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from time import monotonic

from common import TOOL_ROOT, to_json


def execution(output, frozen, name, command, **environment):
    start = monotonic()
    log = output/'logs'/f'{name}.log'
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w',encoding='utf-8') as stream:
        print(json.dumps(dict(command=command,environment=environment,source=frozen)),file=stream,flush=True)
        result = subprocess.run(command,cwd=TOOL_ROOT,env=dict(os.environ,**environment),
                                stdout=stream,stderr=subprocess.STDOUT)
        print(json.dumps(dict(exit_code=result.returncode)),file=stream)
    raw = log.read_bytes()
    value = dict(source=frozen,command=command,environment=environment,exit_code=result.returncode,
                 seconds=round(monotonic()-start,3),log=f'logs/{log.name}',
                 log_sha256=sha256(raw).hexdigest(),log_bytes=len(raw))
    to_json(output/'checks'/f'{name}.json',value)
    return value


def python_inventory(output,frozen,workers):
    def shard(pair):
        backend,index=pair
        name=f'{backend}-shard-{index}'
        inventory=f'checks/{name}-inventory.json'
        argv=[sys.executable,'-Bu','tools/ci/run_campaign_tests.py',
              '--shard',str(index),'--shards','6','--timings',str(output/inventory)]
        result=execution(output,frozen,name,argv,MARCH_CORE_BACKEND=backend)
        log=(output/result['log']).read_text()
        count=re.search(r'Ran (\d+) tests? in',log)
        skipped=re.search(r'skipped=(\d+)',log)
        result.update(tests=int(count[1]) if count else None,skips=int(skipped[1]) if skipped else 0,
                      inventory=inventory,failures=re.findall(r'^(?:FAIL|ERROR): (.*)$',log,re.M))
        to_json(output/'checks'/f'{name}.json',result)
        print(name,result['exit_code'],result['tests'],flush=True)
        return backend,result
    cases=[(backend,index) for index in range(1,7) for backend in ('python','rust')]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows=list(pool.map(shard,cases))
    expected={str(path.relative_to(TOOL_ROOT)) for path in (TOOL_ROOT/'tests').rglob('test_remake_*.py')}
    proof={}
    for backend in ('python','rust'):
        items=[row for kind,row in rows if kind==backend]
        files=[]
        for row in items:
            source=output/row['inventory']
            if source.is_file():
                files.extend(json.loads(source.read_text())['files'])
        valid=set(files)==expected and len(files)==len(expected)
        proof[backend]=dict(shards=items,files=len(files),full_inventory=valid,
            tests=sum(x['tests'] or 0 for x in items),skips=sum(x['skips'] for x in items),
            pass_=valid and all(row['exit_code']==0 and row['tests'] for row in items))
    to_json(output/'checks/backend-suite-proof.json',proof)
    return int(any(not val['pass_'] for val in proof.values()))


def disabled_inventory(output,frozen,legacy_root,checkpoint):
    variants={'old-rust':(legacy_root,'rust'),'new-python':(TOOL_ROOT,'python'),'new-rust':(TOOL_ROOT,'rust')}

    def run(item):
        name,(work,backend)=item
        source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=work,text=True).strip()
        result=output/'checks'/f'disabled-replay-{name}.json'
        command=[sys.executable,'-Bu','tools/economy-balance/v303_replay_checks.py','backend',
                 str(checkpoint),str(result),'--turns','9']
        executed=execution(output,source,f'disabled-run-{name}',command,
            MARCH_CORE_BACKEND=backend,TK2_OBSERVER_RUNTIME_ROOT=str(work))
        if executed['exit_code']:
            raise ValueError(f'{name} parity replay failed')
        found=json.loads(result.read_text(encoding='utf-8'))
        return name,dict(state=found,execution=executed)

    with ThreadPoolExecutor(max_workers=3) as pool:
        found=dict(pool.map(run,variants.items()))
    baseline=found['old-rust']['state']
    trace=baseline['states']
    proof=dict(compared=sum(len(v) for v in trace.values()),matching=0,groups=list(trace),runs=found,
               final_engine_source=frozen)
    if all(x['state']['states']==trace and x['state']['checkpoint_sha256']==baseline['checkpoint_sha256']
           for x in found.values()):
        proof['matching']=proof['compared']
    to_json(output/'checks/disabled-source-parity-rerun.json',proof)
    print(json.dumps({k:proof[k] for k in ('compared','matching','groups')},ensure_ascii=False))
    return int(not proof['matching'])


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--disabled-parity',type=Path,nargs=2,metavar=('LEGACY_ROOT','CHECKPOINT'))
    args=parser.parse_args()
    frozen=(args.output/'frozen-source.txt').read_text().strip()
    status=disabled_inventory(args.output,frozen,*args.disabled_parity) if args.disabled_parity else (
        python_inventory(args.output,frozen,args.workers))
    raise SystemExit(status)
