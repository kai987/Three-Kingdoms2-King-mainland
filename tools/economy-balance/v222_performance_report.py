"""Measure the same turns with the real telemetry writer enabled and disabled."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
import cProfile
from math import ceil
from pathlib import Path
import pstats
from time import process_time
import json

from common import Catalog, HeadlessCampaign, ROOT, to_json, to_csv
from v212_experiments import configured
from v222_experiments import Recorder, STRATEGY
from remake import logistics_strategy, transport_emergency, winter_weather


def case(task):
    root, strategy, mode, detailed, turns = task
    entry = root/'performance'/f'{strategy}-{mode}-{detailed}'
    entry.mkdir(parents=True,exist_ok=True)
    catalog=Catalog(ROOT/'game/data/campaigns/207-09.json')
    game=HeadlessCampaign(catalog,record_journal=False)
    profile=logistics_strategy.experiment(4,army=True,recovery=True) if strategy==211 else configured(STRATEGY[strategy])
    samples=[]
    context=Recorder(entry/'telemetry') if detailed else nullcontext(None)
    with context as observe, profile, transport_emergency.experiment(0 if mode=='I3' else 3), winter_weather.experiment(
            5,adjustments=winter_weather.CORRECTIONS,observe=observe,detailed=detailed):
        game.command('new',dict(faction='observer',seed=2028,difficulty='normal'),0)
        for _ in range(turns):
            before=process_time()
            game.command('observe_turn',{},game.revision)
            samples.append(process_time()-before)
        exact=game.export_save(compact=True)['checksum']
    profile_again=logistics_strategy.experiment(4,army=True,recovery=True) if strategy==211 else configured(STRATEGY[strategy])
    if mode=='J3' and not detailed:
        sample=HeadlessCampaign(catalog,record_journal=False)
        with profile_again, transport_emergency.experiment(3), winter_weather.experiment(5,adjustments=winter_weather.CORRECTIONS):
            sample.command('new',dict(faction='observer',seed=2028,difficulty='normal'),0)
            profiler=cProfile.Profile()
            with profiler:
                for _ in range(6):
                    sample.command('observe_turn',{},sample.revision)
            with (root/'checks'/f'cpu-profile-{strategy}.txt').open('w') as stream:
                pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(35)
    order=sorted(samples)
    return dict(strategy=strategy,group=mode,detailed_observer=detailed,turns=len(order),mean_cpu_seconds=sum(order)/len(order),
                median_cpu_seconds=order[ceil(len(order)/2)-1],p95_cpu_seconds=order[ceil(len(order)*0.95)-1],
                rng_draws=game.state.rng.draws,compact_save_sha256=exact,catalog_sha256=catalog.sha256)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--turns',type=int,default=24)
    args=parser.parse_args()
    tasks=[(args.output,strategy,mode,use,args.turns)
           for strategy in (211,212) for mode in ('I3','J3') for use in (False,True)]
    with ProcessPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(case,tasks))
    for a,b in zip(results[::2],results[1::2]):
        if (a['rng_draws'],a['compact_save_sha256'])!=(b['rng_draws'],b['compact_save_sha256']):
            raise ValueError(f'Observer changed saved state under {a["strategy"]}/{a["group"]}')
    to_csv(args.output/'checks/performance-observer-on-off.csv',results)
    print(json.dumps(results,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
