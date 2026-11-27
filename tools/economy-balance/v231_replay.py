"""Re-evaluate real shortage checkpoints on the same domain state and RNG."""
from argparse import ArgumentParser
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
import gzip
from io import StringIO
import json
from pathlib import Path
from resource import getrusage, RUSAGE_SELF
from statistics import median
from sys import platform
from time import monotonic, process_time
from unittest.mock import patch

from common import Catalog, HeadlessCampaign, ROOT, git, sha256, to_csv, to_json
from remake import faction_economy, grain_units, granary_planning, logistics, winter_forecast
from remake.campaign import digest, verified_save_content
from v231_observe import CampaignObservation
from v3021_checkpoints import configure
from v302_audit import Audit


def payload(path,group):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        loaded=json.load(stream)
    frame=verified_save_content(loaded.get('save',loaded))
    extension=frame['state']['extension']
    if group in ('F3','F4'):
        extension[winter_forecast.FIELD]=winter_forecast.VERSION
    if group=='F3':
        extension['winter_weather']['options']['agricultural_risk_planning']=False
    return {**frame,'checksum':digest(frame)}


def minimum_quotes(game,state,city):
    owner=state.cities[city].owner
    if owner=='neutral':
        return dict(owner=owner,other_faction_stock=None,legal_sources=0,minimum_eta=None,
                    sources=[],blockers={})
    with grain_units.using(state):
        plan=faction_economy.plan(game,state,owner)
        network=granary_planning.Network(game,state,owner,plan,automatic=True)
        options=network.collect([city]).get(city,())
    return dict(owner=owner,
        other_faction_stock=sum(row.grain for key,row in state.cities.items() if key!=city and row.owner==owner),
        legal_sources=len({row['source'] for row in options}),
        minimum_eta=min((row['days'] for row in options),default=None),
        sources=sorted({row['source'] for row in options}),blockers=dict(network.rejected[city]),
        route_operations=dict(network.stats))


def play(path,scene,strategy,group,turns,*,city=None,observe=True):
    game=HeadlessCampaign(Catalog(ROOT/f'game/data/campaigns/{scene}.json'),record_journal=False)
    data=payload(path,group)
    notes=StringIO()
    record=CampaignObservation(notes,flows=bool(city))
    audit=Audit(record)
    route_searches=0
    candidate_routes=0
    estimate_times=[]
    route=logistics._supply_routes
    unload=logistics._unload
    collect=granary_planning.Network.collect
    estimate=winter_forecast.estimate
    receipts=[]

    def search(*args,**kwargs):
        nonlocal route_searches
        route_searches+=1
        return route(*args,**kwargs)

    def quote_candidates(*args,**kwargs):
        nonlocal candidate_routes
        candidates=collect(*args,**kwargs)
        candidate_routes+=sum(map(len,candidates.values()))
        return candidates

    def timed_prediction(*args,**kwargs):
        start=process_time()
        result=estimate(*args,**kwargs)
        estimate_times.append(process_time()-start)
        return result

    def receive(game,state,row,city,*args,**kwargs):
        opening=city.grain
        result=unload(game,state,row,city,*args,**kwargs)
        if city.grain>opening:
            channel=('regional_market' if 'regional' in row else 'strategic_granary'
                     if 'strategic' in row else 'ordinary')
            receipts.append(dict(turn=state.turn,city=city.id,convoy=row['id'],channel=channel,
                                 grain=city.grain-opening))
        return result

    with ExitStack() as stack:
        configure(stack,strategy,221)
        game.load_save(data,0)
        original=game.to_dict()
        initial={'turn':game.state.turn,'date':[game.state.year,game.state.month,game.state.day],
                 'rng':original['rng'],'domain_sha256':digest(original)}
        if city:
            initial['legal']=minimum_quotes(game,game.state,city)
        stack.enter_context(patch.object(logistics,'_supply_routes',search))
        if not city:
            for cached in (winter_forecast._route,winter_forecast._normal_rates,winter_forecast._conditional_rates):
                cached.cache_clear()
            stack.enter_context(patch.object(granary_planning.Network,'collect',quote_candidates))
            stack.enter_context(patch.object(winter_forecast,'estimate',timed_prediction))
        if observe:
            record.attach(stack)
            stack.enter_context(audit.install())
            stack.enter_context(patch.object(logistics,'_unload',receive))
        cpu,wall=[],[]
        forecast_before=winter_forecast.cache_stats()
        for _ in range(turns):
            old=game.state
            start=process_time()
            real_start=monotonic()
            if observe:
                with audit.command(game,'observe_turn'):
                    game.command('observe_turn',{},game.revision)
                record.after_command(game,old,None)
            else:
                game.command('observe_turn',{},game.revision)
            cpu.append(process_time()-start)
            wall.append(monotonic()-real_start)
            if game.state.phase=='finished':
                break
        forecast_after=winter_forecast.cache_stats()
    assert not audit.errors
    final=game.to_dict()
    result=dict(scene=scene,strategy=strategy,group=group,observation=observe,initial=initial,
        final=dict(turn=game.state.turn,rng=final['rng'],domain_sha256=digest(final)),
        cpu=cpu,wall=wall,route_search_calls=route_searches,candidate_routes=candidate_routes,
        estimate_calls=len(estimate_times),estimate_cpu_seconds=sum(estimate_times),
        market_transport_receipts=receipts,
        peak_rss=getrusage(RUSAGE_SELF).ru_maxrss*(1 if platform=='darwin' else 1024),
        forecast_cache={name:{metric:forecast_after[name][metric]-before[metric] for metric in ('hits','misses')}
                         for name,before in forecast_before.items()})
    if city:
        ledger=[json.loads(line) for line in notes.getvalue().splitlines()]
        bills=[row for row in ledger if row.get('kind')=='city_rations' and row['city']==city]
        result.update(city=city,stock=game.state.cities[city].grain,
            shortages=sum(r['missing']>0 for r in bills),missing=sum(r['missing'] for r in bills),
            observed_postings=[row for row in ledger if row.get('kind')=='warehouse_posting' and row['city']==city])
    return result


def shortage(args):
    paths=sorted(args.checkpoints.glob('*.json.gz'))
    tasks=[(path,group) for path in paths for group in ('F2','F3','F4')]
    def submit(pool,path,group):
        city=path.name.split('-',1)[1].removesuffix('.json.gz')
        return pool.submit(play,path,'208-10',211,group,args.turns,city=city)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs=[(path,submit(pool,path,group)) for path,group in tasks]
        observed=[dict(checkpoint=path.name,checkpoint_sha256=sha256(path.read_bytes()),**result.result())
                  for path,result in jobs]
    to_json(args.output/'shortage-replay-detail.json',{ 'source':git('rev-parse','HEAD').decode().strip(),
                                                      'results':observed})
    detail=[]
    for row in observed:
        info=row['initial']['legal']
        detail.append(dict(checkpoint=row['checkpoint'],source=row['checkpoint_sha256'],group=row['group'],
            city=row['city'],turn=row['initial']['turn'],opening_date=row['initial']['date'],owner=info['owner'],
            other_faction_stock=info['other_faction_stock'],legal_sources=info['legal_sources'],minimum_eta=info['minimum_eta'],
            shortages=row['shortages'],missing=row['missing'],stock=row['stock'],route_blockers=info['blockers']))
    to_csv(args.output/'city-shortage-checkpoint-replay.csv',detail)


def performance(args):
    observed=[]
    for sample in args.samples:
        scene,policy,name=sample.split(',',2)
        path=Path(name)
        for group in ('F2','F4'):
            matched={}
            for observe in (False,True):
                series=[play(path,scene,int(policy),group,args.turns,observe=observe) for _ in range(3)]
                for outcome in series[1:]:
                    assert outcome['final']==series[0]['final']
                if matched:
                    assert series[0]['final']==matched
                matched=series[0]['final']
                times=sorted(n for row in series for n in row['cpu'])
                walls=sorted(n for row in series for n in row['wall'])
                forecasts=Counter()
                for row in series:
                    forecasts.update(row['forecast_cache']['route'])
                calls=sum(row['estimate_calls'] for row in series)
                observed.append(dict(checkpoint=path.name,checkpoint_sha256=sha256(path.read_bytes()),group=group,
                    observation=observe,scene=scene,strategy=policy,samples=len(times),median_cpu=median(times),
                    p95_cpu=times[(95*len(times)-1)//100],
                    median_wall=median(walls),p95_wall=walls[(95*len(walls)-1)//100],
                    forecast_calls=forecasts['hits']+forecasts['misses'],cache_hits=forecasts['hits'],
                    route_search_calls=sum(row['route_search_calls'] for row in series),
                    candidate_routes=sum(row['candidate_routes'] for row in series),
                    estimate_calls=calls,mean_estimate_cpu_s=(sum(row['estimate_cpu_seconds'] for row in series)/calls
                                                              if calls else None),
                    peak_rss=max(row['peak_rss'] for row in series),final=matched,repetitions=series))
    to_json(args.output/'forecast-performance.json',dict(source=git('rev-parse','HEAD').decode().strip(),
                                                         samples=observed))
    keys=('checkpoint','checkpoint_sha256','group','observation','scene','strategy','samples','median_cpu',
          'p95_cpu','median_wall','p95_wall','forecast_calls','cache_hits','route_search_calls',
          'candidate_routes','estimate_calls','mean_estimate_cpu_s','peak_rss')
    to_csv(args.output/'forecast-performance-profile.csv',({key:row[key] for key in keys} for row in observed))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    modes=parser.add_subparsers(dest='mode',required=True)
    a=modes.add_parser('shortage')
    a.add_argument('checkpoints',type=Path)
    a.add_argument('--workers',type=int,default=2)
    b=modes.add_parser('performance')
    b.add_argument('samples',nargs='+')
    for mode in (a,b):
        mode.add_argument('--output',type=Path,required=True)
        mode.add_argument('--turns',type=int,default=3)
    options=parser.parse_args()
    options.output.mkdir(parents=True,exist_ok=True)
    dict(shortage=shortage,performance=performance)[options.mode](options)
