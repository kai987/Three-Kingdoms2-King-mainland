"""Export and verify every physical direction/month against both arithmetic backends."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

from common import TOOL_ROOT, catalogs, to_csv, to_json
from route_inventory import FORMATIONS, _instances
from remake import grain_units, logistics_rules as rules, route_hazards as hazards
from remake import winter_travel as travel, winter_weather as weather
from remake.campaign import Campaign
from remake.climate_regions import REGIONS

MODES={'off':(0,0,0), 'neutral':(0,0,0), 'light_snow':(1,2,0), 'heavy_snow':(2,8,0),
       'blizzard':(3,25,0), 'floating_ice':(0,0,1), 'partial_ice':(0,0,2), 'frozen':(0,0,3)}
ICE_INDEX=(0,1800,4000,6500)
SAMPLE_CARGO=1500


def env(game,month,kind,state=None):
    strength,depth,ice=MODES[kind]
    if state is None:
        state=SimpleNamespace(seed=2026,month=month,year=game.catalog.data['start_year'],extension={})
    state.month=month
    weather.initialize(game,state,22 if kind!='off' else 0)
    if kind!='off':
        pool=state.extension[weather.POOL]
        for zone,row in pool['regions'].items():
            if month in REGIONS[zone][0]:
                row.update(severity=strength,depth=depth)
        for value in pool['ice'].values():
            value.update(index=ICE_INDEX[ice],state=ice)
    return state


def samples():
    for label,mode,strength,depth in (
            ('plain_clear','plain',0,0),('plain_light','plain',1,1),
            ('plain_heavy','plain',2,5),('mountain_heavy','mountain',2,5),
            ('mountain_blizzard','mountain',3,20),('after_snow','plain',0,8)):
        book=SimpleNamespace(extension={weather.POOL:dict(stage=5,regions=dict(
                    liaodong=dict(severity=strength,depth=depth)),ice={})})
        parts=(travel.Part(mode,10*travel.QUANTA,'liaodong',None),)
        elapsed=position=weight=0
        cargo=SAMPLE_CARGO
        remainder=0
        while position<10*travel.QUANTA:
            day=travel.day(book,parts,position,rest_region='liaodong')
            position+=day.moved
            weight+=day.ration
            elapsed+=1
            loss,remainder=rules.cargo_loss(cargo,day.cargo,remainder)
            cargo-=loss
        yield dict(case=label,mode=mode,normal_days=10,actual_days=elapsed,work=position,
                   ration_weight=weight,grain=rules.ceil_div(weight*10100,rules.RATION_SCALE*50),
                   cargo_loaded=SAMPLE_CARGO,cargo_delivered=cargo,cargo_loss=SAMPLE_CARGO-cargo,carry=remainder)


def generate(destination):
    registered=catalogs()
    games={c.data['id']:Campaign(c,record_journal=False) for c in registered}
    grouped=_instances(registered,'208-10')
    summary=Counter()
    samples_by_city={}
    river_mapping={}
    for game in games.values():
        for key,row in game.catalog.climate.cities.items():
            assert key not in samples_by_city or row==samples_by_city[key]
            samples_by_city[key]=row
        for reach,row in game.catalog.climate.reaches.items():
            river_mapping.setdefault(reach,row)
    to_csv(destination/'city-climate-regions.csv',(dict(city_id=key,**row) for key,row in sorted(samples_by_city.items())))
    to_csv(destination/'river-freeze-segments.csv',(dict(reach=key,**row) for key,row in sorted(river_mapping.items())))
    climate_rows=[]
    disallowed=[]
    alternate_cache={}
    exports={}
    route_keys=set()
    def alternatives(info,month,source,target):
        available=info['eligible'][month]
        if not available:
            return None
        ident=available[0]
        key=ident,month,source,target
        if key not in alternate_cache:
            game=games[ident]
            data=game.catalog.data
            state=env(game,month,'frozen')
            state.cities={city:SimpleNamespace(owner=data['initial_owners'].get(city,'neutral'))
                          for city in game.catalog.active_city_ids(state.year,month)}
            state.extension['travel']=dict(discovered=[])
            state.extension['diplomacy']={'alliances':[]}
            owner=state.cities[source].owner
            quote=game._travel_path(state,source,target,owner,'land',adjacent=state.cities[target].owner!=owner)
            alternate_cache[key]=quote['path'] if quote else None
        return alternate_cache[key]

    def all_quotes():
        for key,info in sorted(grouped.items()):
            raw,data=info['raw'],info['data']
            game=games[data['id']]
            for source,target in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                enabled=hazards.route_allowed(data,raw,source,target)
                assert enabled==hazards._python_route_allowed(data,raw,source,target)
                for month in range(1,13):
                    identity=(key,source,target,month)
                    assert identity not in route_keys
                    route_keys.add(identity)
                    if not enabled:
                        summary['one_way_disallowed']+=1
                        disallowed.append(dict(route_key=key,route_id=raw['id'],source=source,target=target,
                                               month=month,reason='one_way',declared_scenarios=info['scenarios']))
                        continue
                    leg=hazards.evaluate_leg(data,raw,source,target,month)
                    assert leg==hazards._python_evaluate_leg(data,raw,source,target,month)
                    quote=game._quote([source,target],[leg])
                    parts=travel.plan(game,quote)
                    normal=rules.plan(quote,data['travel_rules'])
                    assert sum(p.work for p in parts)==leg['days']*travel.QUANTA
                    assert all(p.region in REGIONS for p in parts)
                    if month==1:
                        for index,part in enumerate(parts,1):
                            climate_rows.append(dict(route_key=key,route_id=raw['id'],source=source,target=target,
                                order=index,mode=part.mode,work=part.work,region=part.region,reach=part.reach,
                                snow_exposure=bool(REGIONS[part.region][0]),
                                elevation_class='highland' if part.mode=='mountain' else 'lowland_or_water',
                                mapping='endpoint_interpolation' if part.mode in ('mountain','plain','desert','sea') else 'surveyed_route_stage'))
                    base_weight=rules.weight(normal)
                    for condition in MODES:
                        frame=(data['id'],month,condition)
                        if frame not in exports:
                            exports[frame]=env(game,month,condition)
                        state=exports[frame]
                        if condition=='off':
                            days,weight,blocked=quote['days'],base_weight,None
                        else:
                            days,weight,_,blocked=travel.forecast(game,state,quote)
                        net=travel.estimate_cargo(game,state,quote,SAMPLE_CARGO) if not blocked else None
                        alternative=alternatives(info,month,source,target) if blocked else None
                        if condition=='neutral':
                            assert days==quote['days'] and weight==base_weight
                            assert net==rules.estimate_cargo(SAMPLE_CARGO,normal,quote['days'])[0]
                        if blocked:
                            summary['frozen_quotes']+=1
                        summary['rows']+=1
                        pool=state.extension.get(weather.POOL,{})
                        row=dict(route_key=key,route_id=raw['id'],source=source,target=target,month=month,
                            mode=raw['mode'],status='frozen' if blocked else 'passable',control=condition,
                            season_eligible_scenarios=info['eligible'][month],discovery_required=info['kind']=='exploration',
                            normal_days=quote['days'],forecast_days=days,extra_days=None if days is None else days-quote['days'],
                            normal_weight=base_weight,forecast_weight=None if blocked else weight,
                            snow_depth=max((pool['regions'][p.region]['depth'] for p in parts),default=0) if pool else 0,
                            ice_state=max((pool['ice'].get(p.reach,{}).get('state',0) for p in parts),default=0) if pool else 0,
                            blocked_reach=blocked,alternative_path=alternative,risk=leg['hazard'],
                            cargo_dispatched=SAMPLE_CARGO,cargo_delivered=net,cargo_lost=None if net is None else SAMPLE_CARGO-net)
                        for soldiers,officers in FORMATIONS:
                            units=soldiers+100*officers
                            name=f'{soldiers}_{officers}'
                            prior=rules.ceil_div(units*base_weight,50*rules.RATION_SCALE)
                            estimate=None if blocked else rules.ceil_div(units*weight,50*rules.RATION_SCALE)
                            row.update({f'normal_grain_{name}':prior,f'forecast_grain_{name}':estimate,
                                        f'extra_grain_{name}':None if estimate is None else estimate-prior})
                        yield row
    with grain_units.using():
        to_csv(destination/'route-weather-comparison.csv',all_quotes())
    to_csv(destination/'route-climate-segments.csv',climate_rows)
    to_csv(destination/'route-blocked-directions.csv',disallowed)
    records=list(samples())
    for unit in ('dynamic-march-cases','winter-ration-cases','winter-cargo-loss-cases'):
        to_csv(destination/(unit+'.csv'),records)
    frozen=[]
    index=status=0
    for tick,cold in enumerate([3]*18+[0]*18,1):
        before=status
        index,status=weather.ice_step(index,status,cold,150)
        frozen.append(dict(tick=tick,cold=cold,index=index,before=before,after=status,
                           navigation=weather.ICE_NAMES[status],speed_percent=weather.SPEED_PERCENT[status]))
    to_csv(destination/'frozen-route-cases.csv',frozen)
    to_csv(destination/'climate-config-validation.csv',(
        dict(region=key,months=row[0],declared_probability=row[1],cold=row[2],guaranteed=row[3],
             cities=sum(info['climate_region_id']==key for info in samples_by_city.values()),
             reach_count=sum(info['freeze_region_id']==key and bool(info['freeze_sensitivity']) for info in river_mapping.values()))
        for key,row in REGIONS.items()))
    to_json(destination/'routes-manifest.json',dict(scenarios=len(registered),business_keys=len(route_keys),
        cities=len(samples_by_city),reaches=len(river_mapping),conditions=MODES,formations=FORMATIONS,
        sample_cargo=SAMPLE_CARGO,**summary))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=TOOL_ROOT/'build/weather-v22/exports')
    generate(parser.parse_args().output)
