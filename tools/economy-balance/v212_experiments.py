"""Named, isolated V2.1.2 comparisons using the standard observer."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack, contextmanager
from itertools import product
from json import loads
from pathlib import Path
from unittest.mock import patch

from common import TOOL_ROOT, git, to_json
from observer_telemetry import config
from reproduce_army_relief import PRIORITY

PROFILES={'G1':(55,45), 'G2':(60,55), 'G3m':(55,45), 'G3l':(60,55),
          'G4am':(55,45), 'G4al':(60,55)}


def settings_for(group):
    after_six,no_source=PROFILES[group]
    return dict(after_six=after_six, no_source=no_source,
                staging=group.startswith(('G3','G4')),occupation=group.startswith('G4'),diplomacy=False)


@contextmanager
def configured(group):
    from remake import logistics_strategy, war_recovery
    p=settings_for(group)
    with ExitStack() as hooks:
        hooks.enter_context(patch.object(war_recovery,'LATER',p['after_six']))
        hooks.enter_context(patch.object(war_recovery,'UNFUNDED',p['no_source']))
        options={'army':True,'recovery':True}
        if p['staging']:
            options.update(candidate='occupation' if p['occupation'] else 'logistics')
        hooks.enter_context(logistics_strategy.experiment(4,**options))
        yield


def run():
    from observe import SCENARIOS, run_scenario
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('wave',choices=('priority','matrix','long','holdout','proof'))
    parser.add_argument('--groups',nargs='+',choices=['F3',*PROFILES],required=True)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--months',type=int)
    parser.add_argument('--hash-turns',action='store_true')
    args=parser.parse_args()
    if args.wave=='priority':
        cases=[(seed,60,scenario) for seed,scenario in PRIORITY]
    elif args.wave=='matrix':
        cases=list(product((2026,2027,2028),(60,),SCENARIOS))
    elif args.wave=='long':
        cases=list(product((2026,),(240,),('184-02','208-10')))
    elif args.wave=='proof':
        cases=[(2027,args.months or 12,'207-09')]
    else:
        cases=list(product((2030,),(60,),('190-01','208-10')))
    settings=config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    head=git('rev-parse','HEAD').decode().strip()
    runs=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending=[]
        for group,(seed,months,scenario) in product(args.groups,cases):
            folder=args.output/'observed'/group/str(seed)/str(months)
            saved=folder/scenario/'run.json'
            if saved.exists():
                row=loads(saved.read_text())
                if (row['head']==head and row.get('v212') and row['outcome'] in {'complete','natural_end'}
                        and row.get('telemetry',{}).get('config')==settings
                        and (not args.hash_turns or 'committed_save_sha256' in row)):
                    runs.append(row)
                    continue
            pending.append(pool.submit(run_scenario,scenario,seed,months,folder,group,settings,hash_turns=args.hash_turns))
        runs.extend(job.result() for job in as_completed(pending))
    to_json(args.output/f"{args.wave}-{'-'.join(args.groups)}.json",
            sorted(runs,key=lambda row:(row['scenario'],row['seed'],row['group'])))
    return int(any(row['outcome']=='error' for row in runs))


if __name__=='__main__':
    raise SystemExit(run())
