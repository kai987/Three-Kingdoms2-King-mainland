"""Sample public forecast statistics with the unchanged V2.3 weather kernel."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
from pathlib import Path
from pprint import pformat
from types import SimpleNamespace

from common import Catalog, ROOT, git, to_csv, to_json
from remake import winter_climate as climate, winter_travel as travel, winter_weather as weather

SHARES = 10_000
TRAINING = 100_000
HOLDOUT = 200_000
SLOTS = 36


def weather_fixture(rare=False):
    catalog = Catalog(ROOT/'game/data/campaigns/200-01.json')
    return SimpleNamespace(catalog=SimpleNamespace(climate=catalog.climate,
        data={'start_year':184, 'start_month':11})), climate.normalize({'exceptional_cold_wave':rare})


def observe_batch(task):
    rare, seeds = task
    game, options = weather_fixture(rare)
    roads, depths, rivers = (defaultdict(Counter) for _ in range(3))
    for seed in seeds:
        state = SimpleNamespace(seed=seed, extension={})
        weather.initialize(game,state,climate.VERSION,options=options)
        pool = state.extension[weather.POOL]
        for tick in range(1,361):
            weather.advance(game,state,tick)
            slot = (30+(tick-1)//10)%SLOTS
            for region, cell in pool['regions'].items():
                roads[region,slot][cell['severity'],weather.road_weather(cell)] += 1
                depths[region,slot][cell['depth']] += 1
            for reach, cell in pool['ice'].items():
                region = game.catalog.climate.reaches[reach]['climate_region_id']
                rivers[reach,slot][pool['regions'][region]['severity'],cell['state']] += 1
    return rare, roads, depths, rivers


def observe(start,count,workers):
    statistics = {rare:[defaultdict(Counter) for _ in range(3)] for rare in (False,True)}
    tasks = [(rare,range(low,min(low+25,start+count)))
             for rare in statistics for low in range(start,start+count,25)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index, (rare, *datasets) in enumerate(pool.map(observe_batch,tasks),1):
            for totals, batch in zip(statistics[rare],datasets,strict=True):
                for key, values in batch.items():
                    totals[key].update(values)
            if index%10==0 or index==len(tasks):
                print(f'Completed weather batches {index}/{len(tasks)}',flush=True)
    return statistics


def shares(counts):
    samples = sum(counts.values())
    rows = []
    cumulative = previous = 0
    for key,count in sorted(counts.items()):
        cumulative += count
        end = cumulative*SHARES//samples
        if end != previous:
            rows.append((*key,end-previous))
        previous = end
    assert sum(value[-1] for value in rows)==SHARES
    return tuple(rows)


def quantile(counts, percentile):
    threshold = (sum(counts.values())*percentile+99)//100
    for depth, count in sorted(counts.items()):
        threshold -= count
        if threshold<=0:
            return depth
    raise ValueError('No accumulation samples')


def export(output,statistics):
    road_tables, river_tables, rows = {}, {}, []
    for rare, (roads, depths, rivers) in statistics.items():
        road_tables[rare] = {}
        river_tables[rare] = {}
        for region in sorted({key for key,_ in roads}):
            slots = []
            for slot in range(SLOTS):
                counts = roads[region,slot]
                depth = depths[region,slot]
                distribution = shares(counts)
                p90 = quantile(depth,90)
                slots.append((distribution,p90))
                samples = sum(counts.values())
                rate = [sum(travel._medium('plain',snow,road,0,True)[index]*w
                            for snow,road,w in distribution)//SHARES for index in range(3)]
                rows.append(dict(exceptional=rare,kind='land',place=region,month=1+slot//3,slot=1+slot%3,
                    samples=samples,distribution=distribution,
                    light_share=sum(n for (snow,_),n in counts.items() if snow==1)/samples,
                    heavy_share=sum(n for (snow,_),n in counts.items() if snow==2)/samples,
                    blizzard_share=sum(n for (snow,_),n in counts.items() if snow==3)/samples,
                    snow_cover_share=1-depth[0]/samples,
                    deep_cover_share=sum(n for d,n in depth.items() if d>=5)/samples,
                    clear_pack_share=sum(n for (snow,road),n in counts.items() if snow==0 and road)/samples,
                    depth_p50=quantile(depth,50),depth_p90=p90,
                    expected_work_rate=rate[0],expected_ration_weight=rate[1],expected_cargo_weight=rate[2],
                    frozen_share=None))
            road_tables[rare][region] = tuple(slots)
        for reach in sorted({key for key,_ in rivers}):
            slots = []
            for slot in range(SLOTS):
                counts = rivers[reach,slot]
                distribution = shares(counts)
                slots.append(distribution)
                row=dict.fromkeys(rows[0])
                row.update(exceptional=rare,kind='river',place=reach,month=1+slot//3,slot=1+slot%3,
                    samples=sum(counts.values()),distribution=distribution,
                    frozen_share=sum(w for _,ice,w in distribution if ice==3)/SHARES)
                rows.append(row)
            river_tables[rare][reach] = tuple(slots)
    to_csv(output/'monthly-weather-joint-distribution.csv',rows)
    return road_tables, river_tables


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('calibrate','holdout'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--count',type=int,default=1000)
    parser.add_argument('--write-module',type=Path)
    args=parser.parse_args()
    if args.count<1 or args.workers<1 or args.write_module and (args.phase!='calibrate' or args.count!=1000):
        parser.error('Production normals must come from the frozen 1,000-seed calibration set')
    start=TRAINING if args.phase=='calibrate' else HOLDOUT
    args.output.mkdir(parents=True,exist_ok=True)
    roads, rivers=export(args.output,observe(start,args.count,args.workers))
    if args.write_module:
        body='"""Public V2.3 forecast samples from seeds 100000–100999."""\n'
        body+='\nROAD_NORMALS = '+pformat(roads,width=116,compact=True,sort_dicts=True)
        body+='\n\nRIVER_NORMALS = '+pformat(rivers,width=116,compact=True,sort_dicts=True)+'\n'
        args.write_module.write_text(body,encoding='utf-8')
    catalog=Catalog(ROOT/'game/data/campaigns/200-01.json')
    to_json(args.output/'normals-manifest.json', dict(source=git('rev-parse','HEAD').decode().strip(),
        phase=args.phase,seed_start=start,count=args.count,calendar_days=360,profiles=[False,True],
        catalog_sha256=catalog.sha256,map_sha256=sha256((ROOT/'game/assets/map-campaign.png').read_bytes()).hexdigest()))


if __name__=='__main__':
    main()
