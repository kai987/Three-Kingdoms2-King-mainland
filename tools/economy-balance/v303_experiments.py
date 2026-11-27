"""Run reproducible V3.0.3 observer cohorts without changing historical defaults."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from common import TOOL_ROOT, to_json
from v302_experiments import run
from v3021_experiments import WAVES as PRIOR

ROOT=TOOL_ROOT/'build/transport-capacity-v303/final'
WAVES = {
    'pilot': [(2026,'184-02',211,0,2),(2026,'208-10',211,221,2)],
    'quick': [(2026,'184-02',211,0,12),(2026,'208-10',211,0,12),
              (2026,'184-02',212,221,12),(2026,'263-05',211,221,12)],
    'five': PRIOR['winter']+PRIOR['dry'],
    'long': PRIOR['long'],
    'holdout': [(2037,'184-02',211,221,60),(2038,'208-10',212,221,60)],
}
GROUPS = {
    'C0': None,
    'C1': (True,False,False,False,False),
    'C1b': (True,False,False,False,True),
    'C2': (False,True,False,False,False),
    'C2p': (False,True,True,False,False),
    'C3': (True,True,True,False,False),
    'C4': (True,True,True,True,False),
}
FLAGS = ('concurrency','physical_capacity','mode_aware_ai_policy','throughput_ranking','double_dispatch')


def options(group):
    return dict(zip(FLAGS,GROUPS[group])) if GROUPS[group] is not None else None


def simulate(output, case, background):
    wave, cohort, _, _, _, weather, _ = case
    granary = None
    if background in ('G1','G4'):
        granary = dict(version=3021 if background=='G4' else 302,proactive=True,winter=bool(weather),relay=False)
        if background=='G4':
            granary.update(coordination=True,return_safety=True)
    return run(output/background,case,granary_options=granary,capacity_options=options(cohort),
               economy_background=background,progress=True)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('wave',choices=WAVES)
    parser.add_argument('--groups',nargs='+',choices=GROUPS,required=True)
    parser.add_argument('--background',choices=('G0','G1','G4'),default='G1')
    parser.add_argument('--scenario',action='append')
    parser.add_argument('--strategy',type=int,choices=(211,212))
    parser.add_argument('--weather',type=int,choices=(0,221))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=Path,default=ROOT)
    args=parser.parse_args()
    matrix=[(args.wave,group,seed,scene,policy,weather,months)
            for group in args.groups for seed,scene,policy,weather,months in WAVES[args.wave]
            if (not args.scenario or scene in args.scenario) and (args.strategy is None or policy==args.strategy)
            and (args.weather is None or weather==args.weather)]
    label='-'.join([args.wave,args.background,*args.groups,*(args.scenario or []),
                    str(args.strategy or 'any'),str(args.weather)])
    to_json(args.output/f'planned-{label}.json',matrix)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(simulate,args.output,case,args.background) for case in matrix]
        finished=[]
        for job in as_completed(futures):
            result=job.result()
            finished.append(result)
            print(json.dumps({key:result.get(key) for key in (
                'wave','group','economy_background','scenario','seed','strategy','weather','outcome',
                'completed_turns','source','seconds','failure')},ensure_ascii=False),flush=True)
    to_json(args.output/f'completed-{label}.json',sorted(finished,key=lambda row:row['output']))
    return int(any(row['outcome'] not in ('complete','natural_end') for row in finished))


if __name__ == '__main__':
    raise SystemExit(main())
