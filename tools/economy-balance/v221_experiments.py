"""Run weather safety experiments through the real strategic observer."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import gzip
from functools import lru_cache
from itertools import product
import json
from pathlib import Path
import tempfile

from common import ROOT, TOOL_ROOT, git, sha256, to_json
from observe import run_scenario
from observer_telemetry import config
from remake import winter_weather as weather
from v22_experiments import Recorder

GROUPS = {'H0': ('F3',0,0), 'H1': ('F3',5,0), 'H2': ('G4al',0,0), 'H3': ('G4al',5,0)}
GROUPS.update({f'I{change}-{strategy}': (profile,5,change)
               for strategy,profile in ((211,'F3'),(212,'G4al'))
               for change in (weather.TRANSPORT,weather.PREPARATION,weather.CORRECTIONS)})
PANEL=('H0','H1','I3-211','H2','H3','I3-212')
SEVEN=('263-05','221-07','208-10','190-01','184-02','200-01','207-09')
WAVES={
    'matrix': (PANEL,tuple(product((2026,2027,2028),SEVEN)),60),
    'long': (PANEL,((2026,'184-02'),(2026,'208-10')),240),
    'holdout': (('H1','I3-211','H3','I3-212'),((2032,'190-01'),(2032,'208-10')),60),
    'focus': (('I1-211','I2-211','I1-212','I2-212'),
              ((2026,'263-05'),(2026,'221-07'),(2031,'190-01'),(2026,'208-10')),60),
}
ROOT_OUTPUT=TOOL_ROOT/'build/weather-v221'
DAY_FIELDS=('tick date convoy owner phase journey origin source target node last_node next_node '
 'start_work moved end_work rations_before paid base supply missing rations_after cargo_before route_loss '
 'incident_loss cargo_to_bag cargo_after hunger_loss person_days reason original_eta eta ice ice_index ice_state '
 'safe_exit consecutive_no_progress last_progress last_arrival weather_extra_grain')


@lru_cache(maxsize=1)
def source_identity():
    paths=git('ls-files','-co','--exclude-standard','-z','--','source','game/config','game/data/campaigns',
              'crates','tools/economy-balance').decode().strip('\0').split('\0')
    files={name:sha256((ROOT/name).read_bytes()) for name in sorted(set(paths))
           if (ROOT/name).is_file() and not name.endswith('_report.py')}
    return dict(head=git('rev-parse','HEAD').decode().strip(),
                tree_sha256=sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()),files=files)


class TransportRecorder(Recorder):
    def __init__(self,folder):
        super().__init__(folder)
        self.original_eta={}
        self.last_progress={}
        self.last_arrival={}
        self.stalls=Counter()
        self.ice_spells={}
        self.impact={}
        self.activity=Counter()

    def __enter__(self):
        super().__enter__()
        handle=gzip.open(self.path/'transport-progress-daily.csv.gz','wt',compresslevel=1,encoding='utf-8',newline='')
        writer=csv.DictWriter(handle,fieldnames=DAY_FIELDS.split(),lineterminator='\n')
        writer.writeheader()
        self.files['transport-progress-daily']=(handle,writer)
        handle=(self.path/'ice-transport-events.csv').open('w',encoding='utf-8',newline='')
        writer=csv.DictWriter(handle,fieldnames='tick convoy event reach ice_index node remaining_work rations cargo began'.split(),
                              lineterminator='\n')
        writer.writeheader()
        self.files['ice-transport-events']=(handle,writer)
        return self

    def __call__(self,kind,row):
        super().__call__(kind,row)
        if kind=='travel' and row['unit_kind']=='convoy':
            self.impact[row['unit_id']]=(row['tick'],row['extra_grain'])
        if kind=='action':
            self.activity[row['action']]+=1
            if row['action']=='transport_departed':
                self.original_eta[row['details']['unit_id']]=row['details']['arrival']
        if kind!='convoy_day':
            return
        ident,tick=row['convoy'],row['tick']
        reason=row['reason']
        if row['moved']:
            self.last_progress[ident]=tick
            self.stalls[ident]=0
            if row['node'] is not None:
                self.last_arrival[ident]=tick
        elif row['end_work']:
            self.stalls[ident]+=1
        if row['ice'] and ident not in self.ice_spells:
            self.ice_spells[ident]=(tick,row['ice'])
            self.ice_event(row,'blocked',tick,row['ice'])
        elif not row['ice'] and ident in self.ice_spells:
            began,reach=self.ice_spells.pop(ident)
            self.ice_event(row,'resumed' if row['moved'] else 'unblocked_and_still_waiting',began,reach)
        exposure=self.impact.pop(ident,(None,0))
        self.write('transport-progress-daily',dict(row,original_eta=self.original_eta.get(ident,row['original_eta']),
            date='-'.join(map(str,row['date'])),consecutive_no_progress=self.stalls[ident],
            last_progress=self.last_progress.get(ident),last_arrival=self.last_arrival.get(ident),
            weather_extra_grain=exposure[1] if exposure[0]==tick else 0))
        self.metrics.update(escort_person_days=row['person_days'],blocked_by_ice_days=reason=='ice',
                            convoy_unpaid_q=row['missing'])

    def ice_event(self,row,event,began,reach):
        self.write('ice-transport-events',dict(tick=row['tick'],convoy=row['convoy'],event=event,
            reach=reach,ice_index=row['ice_index'],node=row['node'],remaining_work=row['end_work'],
            rations=row['rations_after'],cargo=row['cargo_after'],began=began))


def run_case(output,wave,group,seed,scenario,months,*,hash_turns=False):
    profile,stage,adjustments=GROUPS[group]
    directory=output/'observed'/wave/group/str(seed)/str(months)
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/scenario
    identity=source_identity()
    settings=config(ROOT/'tools/economy-balance/observer-config.json')
    if (target/'run.json').exists():
        row=json.loads((target/'run.json').read_text())
        if (row.get('source_tree_sha256')==identity['tree_sha256'] and row['outcome']=='complete'
                and row.get('adjustments')==adjustments and row['telemetry']['config']==settings
                and (not hash_turns or 'committed_save_sha256' in row)):
            return row
    with tempfile.TemporaryDirectory(prefix='.working-',dir=directory) as partial:
        folder=Path(partial)
        with TransportRecorder(folder/scenario) as record, weather.experiment(
                stage,adjustments=adjustments,detailed=True,observe=record):
            row=run_scenario(scenario,seed,months,folder,profile,settings,hash_turns=hash_turns)
        row.update(group=group,base_observer_group=profile,stage=stage,adjustments=adjustments,
            weather_rules_version=221 if adjustments else 22 if stage else 0,
            weather_seed=weather.seed_for(seed) if stage else None,
            source_tree_sha256=identity['tree_sha256'],weather_totals=dict(record.metrics),
            weather_observations={name:dict(rows=record.counts[name]) for name in record.files},
            seasonal_actions=dict(record.activity),active_ice_spells=record.ice_spells,
            frozen_reach_days=dict(record.ice_days))
        to_json(folder/scenario/'run.json',row)
        if target.exists():
            previous=Path(tempfile.mkdtemp(prefix='.previous-',dir=directory))
            target.rename(previous/scenario)
        (folder/scenario).rename(target)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wave',choices=tuple(WAVES))
    parser.add_argument('--groups',nargs='+',choices=tuple(GROUPS))
    parser.add_argument('--seed',type=int,action='append')
    parser.add_argument('--scenario',action='append',choices=SEVEN)
    parser.add_argument('--months',type=int)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--hash-turns',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT_OUTPUT)
    args=parser.parse_args()
    groups,cases,months=WAVES[args.wave]
    groups=args.groups or groups
    cases=[(seed,scenario) for seed,scenario in cases
           if (not args.seed or seed in args.seed) and (not args.scenario or scenario in args.scenario)]
    months=args.months or months
    if not cases or months<1 or args.workers<1:
        parser.error('empty experiment selection or nonpositive length')
    args.output.mkdir(parents=True,exist_ok=True)
    identity=source_identity()
    to_json(args.output/f"source-{identity['tree_sha256']}.json",identity)
    failures=0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(run_case,args.output,args.wave,group,seed,scenario,months,hash_turns=args.hash_turns):
               (group,seed,scenario) for (seed,scenario),group in product(cases,groups)}
        for task in as_completed(tasks):
            case=tasks[task]
            try:
                run=task.result()
                failures+=run['outcome'] not in ('complete','natural_end')
                print(*case,run['outcome'],run['completed_turns'],run['seconds'],
                       run.get('failure') or '',flush=True)
            except Exception as error:
                failures+=1
                print(*case,'error',repr(error),flush=True)
    return int(bool(failures))


if __name__=='__main__':
    raise SystemExit(main())
