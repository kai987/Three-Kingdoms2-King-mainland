"""Evaluate three forecasts against the same physical route and weather sequence."""
from argparse import ArgumentParser
from collections import defaultdict
from copy import copy
from pathlib import Path
from random import Random
from statistics import fmean
from types import SimpleNamespace
from unittest.mock import patch

from common import Catalog, ROOT, git, to_csv, to_json
from remake import logistics_rules as rules, route_hazards, route_network, winter_climate
from remake import winter_forecast as forecast, winter_travel as travel, winter_weather as weather
from remake.travel import TravelCampaign

DATE_CASES=((3,21,'liaodong'),(11,21,'northern_frontier'),(12,20,'liaodong'),
            (11,11,'freeze'),(3,11,'freeze'),(12,21,'qinling_highlands'))
ADVERSE_CASES=((12,21,'northern-river-freeze'),(1,11,'northern-river-freeze'),
               (1,21,'northern-river-freeze'),(2,11,'northern-river-freeze'),
               (2,21,'northern-river-freeze'),(3,1,'northern-river-freeze'),
               (3,21,'liaodong'),(4,1,'liaodong'))


def graph(catalog,month):
    directions={}
    nodes=defaultdict(list)
    active=catalog.active_city_ids(200,month)
    for raw in route_network.effective(catalog.data['travel_routes'],active,200,month):
        for start,end in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
            if start in active and end in active and route_hazards.route_allowed(catalog.data,raw,start,end):
                leg = route_hazards.evaluate_leg(catalog.data,raw,start,end,month)
                directions[raw['id'],start,end]=leg
                nodes[start].append(leg)
    return directions,nodes


def route_for(game,region,mapping,seed):
    directions,nodes=mapping
    rows=sorted(directions.values(),key=lambda row:(row['id'],row['from'],row['to']))
    frozen=game.catalog.climate.frozen_reaches
    if region=='northern-river-freeze':
        reach='yellow:jincheng:shuofang'
        leg=next(row for row in rows if row['mode']=='river' and
                 any(part.reach==reach for part in travel._parts_for_leg(game,row)))
        return TravelCampaign._quote([leg['from'],leg['to']],[leg]),None
    if region=='freeze':
        candidates=[r for r in rows if any(p.reach in frozen for p in travel._parts_for_leg(game,r))
                    and (r['id'],r['to'],r['from']) in directions]
    else:
        candidates=[r for r in rows if any(p.region==region and p.mode in forecast.LAND for p in travel._parts_for_leg(game,r))]
    rand=Random(seed)
    first=rand.choice(candidates)
    legs=[first]
    visited={first['from'],first['to']}
    for _ in range(rand.randrange(3)):
        choices=[r for r in nodes[legs[-1]['to']] if r['to'] not in visited
                 and (r['id'],r['to'],r['from']) in directions]
        if not choices:
            break
        leg=rand.choice(choices)
        legs.append(leg)
        visited.add(leg['to'])
    path=[first['from'],*(r['to'] for r in legs)]
    quote=TravelCampaign._quote(path,legs)
    reverse=[directions.get((r['id'],r['to'],r['from'])) for r in reversed(legs)]
    backing=TravelCampaign._quote(list(reversed(path)),reverse) if all(reverse) else None
    return quote,backing


def calendar(game,state,tick):
    state.year,state.month,state.day=weather.date_at(game.catalog.data,tick)


def follow(game,state,quote,cargo=30_000):
    begin=state.extension[weather.POOL]['tick']
    parts=travel.plan(game,quote)
    complete=quote['days']*travel.QUANTA
    boundary=position=food=credit=ice_days=0
    nodes=[(leg['days']*travel.QUANTA,leg['to']) for leg in quote['routes']]
    city=quote['path'][0]
    for span in range(1,721):
        clock=begin+span
        calendar(game,state,clock)
        weather.advance(game,state,clock)
        width, next_node = nodes[0]
        closed=travel.closed_at_node(state,quote,position)
        region=game.catalog.climate.cities[city if closed else next_node]['climate_region_id']
        day=travel.day(state,parts,position,rest_region=region,moving=not closed,
                       on_leg=position>boundary,stop=boundary+width)
        food+=day.ration
        lost,credit=rules.cargo_loss(cargo,day.cargo,credit)
        cargo-=lost
        ice_days+=bool(closed or day.blocked)
        position+=day.moved
        if position==complete:
            calendar(game,state,clock+1)
            return dict(actual_days=span,actual_rations=food,actual_net=cargo,actual_ice_wait_days=ice_days)
        if position==boundary+width:
            boundary=position
            city=next_node
            nodes.pop(0)
    raise ValueError('Fixed route did not finish after two full weather cycles')


def classic(game,state,quote,back=None,*,old=False):
    frame=state
    if old:
        frame=copy(state)
        pool=state.extension[weather.POOL]
        frame.extension={weather.FIELD:weather.CORRECTED,
                         weather.POOL:{key:val for key,val in pool.items() if key!='options'}}
    stationary, food, blocked=travel.checkpoint_forecast(game,frame,quote)
    estimate=travel.seasonal_forecast(game,frame,quote)
    delay=(stationary if stationary is not None else quote['days']+10)+estimate['extra_days']
    if blocked:
        food=max(food,(quote['days']+10)*rules.RATION_SCALE)
    net=travel.estimate_cargo(game,frame,quote,30_000)
    # The old return cost holds current conditions from the departure snapshot.
    returning=travel.checkpoint_forecast(game,frame,back)[1] if back else None
    return dict(days=delay,food=food+estimate['extra_weight'],net=net,back=returning)


def trial(catalog,mappings,seed,index,date_cases=DATE_CASES):
    month,day,region=date_cases[index%len(date_cases)]
    year=200+(month<11)
    game=SimpleNamespace(catalog=SimpleNamespace(climate=catalog.climate,
        data=dict(catalog.data,start_month=11,start_year=200)))
    state=SimpleNamespace(seed=seed,extension={})
    weather.initialize(game,state,winter_climate.VERSION,options=winter_climate.normalize({}))
    offset=weather.ordinal((year,month,day))-weather.ordinal((200,11,1))
    for tick in range(1,offset+1):
        weather.advance(game,state,tick)
    calendar(game,state,offset+1)
    quote,back=route_for(game,region,mappings[month],seed)
    visible={key:dict(state.extension[weather.POOL]['regions'][key]) for key in
             {part.region for part in travel.plan(game,quote)}}
    def forbidden(*args,**kwargs):
        raise AssertionError('A forecast attempted to read an actual weather draw')
    with patch.object(weather,'draw',forbidden):
        newer=forecast.trip(game,state,quote,back)
        older=classic(game,state,quote,back)
        earliest=classic(game,state,quote,back,old=True)
    actual=follow(game,state,quote)
    returned=follow(game,state,back) if back else None
    return dict(seed=seed,region=region,year=year,month=month,day=day,path=quote['path'],
        route_ids=[r['id'] for r in quote['routes']],visible=visible,**actual,
        actual_return_days=returned['actual_days'] if returned else None,
        actual_return_rations=returned['actual_rations'] if returned else None,
        actual_return_ice_wait_days=returned['actual_ice_wait_days'] if returned else None,
        old221_days=earliest['days'],old221_rations=earliest['food'],old221_net=earliest['net'],
        old23_days=older['days'],old23_rations=older['food'],old23_net=older['net'],old23_return=older['back'],
        new_days=newer['expected_arrival_days'],new_rations=newer['total_ration_weight'],
        new_net=forecast.net_cargo(30_000,newer),new_return=newer.get('return_ration_weight'),
        conservative_days=newer['conservative_arrival_days'],currently_blocked=newer['currently_blocked'],
        predicted_ice_wait_days=newer['predicted_ice_wait_days'],freeze_risk=newer['seasonal_freeze_risk'],
        return_freeze_risk=newer.get('return_freeze_risk'),base_days=newer['base_days'],
        visible_extra=newer['visible_weather_extra_days'],seasonal_extra=newer['seasonal_extra_days'],
        base_rations=newer['base_ration_weight'],visible_rations=newer['visible_weather_extra_weight'],
        seasonal_rations=newer['seasonal_extra_weight'],waiting_rations=newer['waiting_ration_weight'])


def summary(rows):
    metrics=[]
    for model in ('old221','old23','new'):
        for key in ('days','rations','net','return'):
            if model=='old221' and key=='return':
                continue
            actual='actual_return_rations' if key=='return' else 'actual_'+key
            differences=[row[model+'_'+key]-row[actual] for row in rows
                         if row[actual] is not None and row[model+'_'+key] is not None]
            absolute=sorted(map(abs,differences))
            count=len(absolute)
            metrics.append(dict(model=model,metric=key,samples=count,
                signed_error=fmean(differences),absolute_error=fmean(absolute),
                p50_error=absolute[(count-1)//2],p90_error=absolute[(9*count-1)//10],
                underestimates=sum(d<0 for d in differences)/count))
    return metrics


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('calibrate','holdout','adverse'))
    parser.add_argument('output',type=Path)
    parser.add_argument('--count',type=int,default=120)
    args=parser.parse_args()
    catalog=Catalog(ROOT/'game/data/campaigns/200-01.json')
    dates=ADVERSE_CASES if args.phase=='adverse' else DATE_CASES
    mappings={month:graph(catalog,month) for month,_,_ in dates}
    start={'calibrate':300_000,'holdout':400_000,'adverse':500_000}[args.phase]
    results=[trial(catalog,mappings,start+index,index,dates) for index in range(args.count)]
    args.output.mkdir(parents=True,exist_ok=True)
    to_csv(args.output/'cross-month-route-prediction.csv',results)
    to_csv(args.output/'route-forecast-errors.csv',summary(results))
    to_json(args.output/'fixed-route-manifest.json',dict(
        phase=args.phase,seed_start=start,count=len(results),source=git('rev-parse','HEAD').decode().strip(),
        catalog_sha256=catalog.sha256,conservative_eta_covered=sum(
            r['new_days']<=r['actual_days']<=r['conservative_days'] for r in results),whole_route_engine='winter_travel.day'))


if __name__=='__main__':
    main()
