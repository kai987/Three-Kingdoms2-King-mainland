"""Run real campaign observer comparisons with independently seeded winter weather."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from functools import lru_cache
from itertools import product
import json
from pathlib import Path
import shutil
import tempfile

from common import ROOT, TOOL_ROOT, git, sha256, to_json
from observe import SCENARIOS, run_scenario
from observer_telemetry import config
from remake import winter_travel, winter_weather
from remake.logistics_rules import cargo_loss

W = {'W'+str(i): ('F3', i) for i in range(6)}
H = {'H0': ('F3',0), 'H1': ('F3',5), 'H2': ('G4al',0), 'H3': ('G4al',5)}
PRIORITY = ((2027, '190-01'), (2026, '208-10'), (2026, '184-02'))
STREAMS = {
    'regional-weather-daily': 'tick year month day region severity began ends depth cold winter snow_seen',
    'snowfall-events': 'tick year month day region severity began ends depth cold winter snow_seen',
    'snow-accumulation': 'tick year month day region depth previous severity cold',
    'river-ice-daily': 'tick year month day reach cold previous index state changed',
    'river-freeze-events': 'tick year month day reach cold previous index state changed',
    'weather-route-impacts': 'tick unit_kind unit_id owner source target units work grain missing rate normal_rate extra_grain cargo_weight normal_cargo_weight delay blocked previous_blocked',
    'winter-military-actions': 'tick year month day owner action source target region details',
    'winter-cargo-impacts': 'tick unit_id owner grain lost rate previous_credit normal_loss extra_loss',
}


class Recorder:
    def __init__(self, path):
        self.path=path
        self.files={}
        self.snow={}
        self.travel={}
        self.ice_days=Counter()
        self.counts=Counter()
        self.metrics=Counter()

    def __enter__(self):
        self.path.mkdir(parents=True,exist_ok=True)
        for name,fields in STREAMS.items():
            handle=(self.path/(name+'.csv')).open('w',newline='',encoding='utf-8')
            sink=csv.DictWriter(handle,fieldnames=fields.split(),lineterminator='\n')
            sink.writeheader()
            self.files[name]=(handle,sink)
        return self

    def __exit__(self,*_):
        for handle,_ in self.files.values():
            handle.close()

    def write(self,name,row):
        self.files[name][1].writerow(row)
        self.counts[name]+=1

    def __call__(self,kind,row):
        if kind=='region':
            self.write('regional-weather-daily',row)
            if row['began']==row['tick']:
                self.write('snowfall-events',row)
            previous=self.snow.get(row['region'],0)
            if row['depth']!=previous:
                self.snow[row['region']]=row['depth']
                self.write('snow-accumulation',{key:row[key] for key in ('tick','year','month','day','region','depth','severity','cold')}
                           | {'previous':previous})
        elif kind=='ice':
            self.write('river-ice-daily',row)
            if row['state']==3:
                self.ice_days[row['reach']]+=1
            if row['previous']!=row['state']:
                self.write('river-freeze-events',row)
        elif kind=='travel':
            matched=(row['unit_kind'],row['unit_id'])
            if row['unit_kind']=='convoy' and row['cargo_weight']:
                self.travel[matched]=row
            self.metrics.update(people_days=row['units'],extra_grain=row['extra_grain'],
                                delay_work_units=row['delay'],blocked_days=int(row['blocked'] is not None))
            if row['extra_grain'] or row['delay'] or row['blocked'] or row['previous_blocked'] or row['cargo_weight']!=row['normal_cargo_weight']:
                self.write('weather-route-impacts',row)
        elif kind=='action':
            self.write('winter-military-actions',{**row,'details':json.dumps(row['details'],ensure_ascii=False,sort_keys=True)})
        elif kind=='cargo':
            travel=self.travel.get(('convoy',row['unit_id']),{})
            normal_rate=travel.get('normal_cargo_weight',row['rate']) if travel.get('tick')==row['tick'] else row['rate']
            normal=cargo_loss(row['grain'],normal_rate,row['previous_credit'])[0]
            extra=row['lost']-normal
            self.metrics['extra_cargo']+=extra
            if extra:
                self.write('winter-cargo-impacts',dict(row,normal_loss=normal,extra_loss=extra))


@lru_cache(maxsize=1)
def source_identity():
    paths=git('ls-files','-co','--exclude-standard','-z','--','source','game/config','game/data/campaigns',
              'crates','tools/economy-balance').decode().strip('\0').split('\0')
    files={p:sha256((ROOT/p).read_bytes()) for p in sorted(set(paths)) if (ROOT/p).is_file()}
    return dict(head=git('rev-parse','HEAD').decode().strip(), tree_sha256=sha256(
        json.dumps(files,sort_keys=True,separators=(',',':')).encode()),files=files)


def case(output,wave,group,seed,scenario,months,hash_turns):
    rule,stage=(W|H)[group]
    parent=output/'observed'/wave/group/str(seed)/str(months)
    target=parent/scenario
    current=parent/scenario/'run.json'
    parent.mkdir(parents=True,exist_ok=True)
    identity=source_identity()
    settings=config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    if current.exists():
        row=json.loads(current.read_text())
        if (row.get('source_tree_sha256')==identity['tree_sha256'] and row['outcome'] in ('complete','natural_end')
                and row.get('base_observer_group')==rule and row.get('stage')==stage
                and row['telemetry']['config']==settings and (not hash_turns or 'committed_save_sha256' in row)):
            return row
    with tempfile.TemporaryDirectory(prefix='.inflight-',dir=parent) as tmp:
        folder=Path(tmp)
        with Recorder(folder/scenario) as recorder, winter_weather.experiment(stage, observe=recorder):
            row=run_scenario(scenario,seed,months,folder,rule,settings,hash_turns=hash_turns)
        row.update(group=group,base_observer_group=rule,stage=stage,weather_rules_version=22 if stage else 0,
                   weather_seed=winter_weather.seed_for(seed) if stage else None,source_tree_sha256=identity['tree_sha256'],
                   weather_observations={name:dict(rows=recorder.counts[name],status=(
                       'not_applicable' if (name.startswith('river') and stage<4)
                       or (name in ('weather-route-impacts','winter-cargo-impacts') and stage<2)
                       or (name not in ('winter-military-actions',) and stage==0) else 'observed'))
                       for name in STREAMS},
                   weather_totals=dict(recorder.metrics),frozen_reach_days=dict(recorder.ice_days))
        to_json(folder/scenario/'run.json',row)
        if target.exists():
            archived=Path(tempfile.mkdtemp(prefix='.previous-',dir=parent))
            target.rename(archived/scenario)
        (folder/scenario).rename(target)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wave',choices=('stages','matrix','long','holdout'))
    parser.add_argument('--groups',nargs='+',choices=tuple(W|H))
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--months',type=int)
    parser.add_argument('--seed',type=int,action='append',help='Limit independent holdout seeds')
    parser.add_argument('--output',type=Path,default=TOOL_ROOT/'build/weather-v22')
    parser.add_argument('--hash-turns',action='store_true')
    args=parser.parse_args()
    defaults={
        'stages':(W,PRIORITY,12),
        'matrix':(H,tuple(product((2026,2027,2028),SCENARIOS)),60),
        'long':(H,((2026,'184-02'),(2026,'208-10')),240),
        'holdout':(H,tuple(product(args.seed or (2031,),('190-01','208-10'))),60),
    }
    groups,cases,months=defaults[args.wave]
    groups=args.groups or tuple(groups)
    months=args.months or months
    if any(group not in defaults[args.wave][0] for group in groups):
        parser.error('groups do not match the selected wave')
    args.output.mkdir(parents=True,exist_ok=True)
    identity=source_identity()
    to_json(args.output/f'{args.wave}-source-identity.json',identity)
    completed=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(case,args.output,args.wave,group,seed,scenario,months,args.hash_turns):(group,seed,scenario)
              for (seed,scenario),group in product(cases,groups)}
        for job in as_completed(jobs):
            group,seed,scenario=jobs[job]
            try:
                row=job.result()
            except Exception as error:
                print(group,seed,scenario,type(error).__name__,str(error),flush=True)
                row=dict(group=group,seed=seed,scenario=scenario,requested_months=months,outcome='error',failure=repr(error))
            print(group,seed,scenario,row['outcome'],row.get('completed_turns'),row.get('seconds'),
                  row.get('failure') or '',flush=True)
            completed.append(row)
    to_json(args.output/f"{args.wave}-{'-'.join(groups)}.json",
            sorted(completed,key=lambda row:(row['group'],row['scenario'],row['seed'])))
    return int(any(r['outcome']=='error' for r in completed))


if __name__=='__main__':
    raise SystemExit(main())
