"""Run the preselected V2.1.1 experiments against an identified worktree."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from json import loads
from pathlib import Path

from common import TOOL_ROOT, git, to_json
from observe import SCENARIOS, run_scenario
from observer_telemetry import config
from reproduce_army_relief import PRIORITY

GROUPS=('E4','F1','F2','F3')


def scheduled(wave,groups):
    if wave=='priority':
        return [(group,seed,60,scenario) for group,(seed,scenario) in product(groups,PRIORITY)]
    if wave=='paired':
        return [(group,seed,60,scenario)
                for group,seed,scenario in product(groups,(2026,2027,2028),SCENARIOS)]
    return [(group,2026,240,scenario) for group,scenario in product(groups,('184-02','208-10'))]


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('wave',choices=('priority','paired','long'))
    parser.add_argument('--groups',choices=GROUPS,nargs='+',default=GROUPS)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--reuse',action='store_true')
    args=parser.parse_args()
    if args.workers<1:
        parser.error('Workers must be positive')
    head=git('rev-parse','HEAD').decode().strip()
    settings=config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    reused=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks=[]
        for group,seed,months,scenario in scheduled(args.wave,args.groups):
            folder=args.output/'observed'/group/str(seed)/str(months)
            marker=folder/scenario/'run.json'
            if args.reuse and marker.exists():
                row=loads(marker.read_text())
                if (row['head']==head and row['group']==group and row['seed']==seed
                        and row['scenario']==scenario and row['requested_months']==months
                        and row['outcome'] in ('complete','natural_end')
                        and row['telemetry']['config']==settings and 'v211' in row):
                    reused.append(row)
                    continue
            tasks.append(pool.submit(run_scenario,scenario,seed,months,folder,group,settings))
        runs=[*reused,*(item.result() for item in as_completed(tasks))]
    ordered=sorted(runs,key=lambda row:(row['requested_months'],row['scenario'],row['seed'],row['group']))
    to_json(args.output/f"{args.wave}-{'-'.join(args.groups)}.json",ordered)
    return int(any(row['outcome']=='error' for row in runs))


if __name__=='__main__':
    raise SystemExit(main())
