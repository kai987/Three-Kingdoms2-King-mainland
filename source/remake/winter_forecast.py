"""Public seasonal estimates for V2.3.1. Actual travel uses winter_travel.day."""
from functools import lru_cache
from types import SimpleNamespace
from typing import NamedTuple

from . import logistics_rules as rules, winter_climate as climate, winter_travel as travel
from . import winter_weather as weather
from .winter_forecast_normals import RIVER_NORMALS, ROAD_NORMALS

FIELD = climate.FORECAST_FIELD
VERSION = climate.FORECAST_VERSION
SHARES = 10_000
DAY = 1_000
VISIBLE_DAYS = 20
MAX_DAYS = 720
LAND = ('plain','mountain','desert')
PROFILE_KEYS = ('monthly_snow_probability','regional_snow_severity','regional_snow_depth',
                'revised_cold_profile','spring_cold_exposure')


class Rates(NamedTuple):
    work: int
    food: int
    cargo: int
    frozen: int


class Projection(NamedTuple):
    days: int
    food: int
    cargo: int
    waiting: int
    waiting_food: int
    visible_delay: int
    visible_food: int
    freeze: int
    reaches: tuple
    bounded: bool


def enabled(state):
    return state.extension.get(FIELD) == VERSION


def _published(flags):
    return SimpleNamespace(extension={weather.POOL:{'options':dict(flags)}})


@lru_cache(maxsize=6_144)
def _normal_rows(flags,mode,region,reach,slot):
    options = dict(flags)
    rare = options.get('exceptional_cold_wave',False)
    full = all(options.get(key) for key in PROFILE_KEYS)
    if full:
        if reach in RIVER_NORMALS[rare] and mode not in LAND and mode!='sea':
            return RIVER_NORMALS[rare][reach][slot]
        if mode in LAND:
            return ROAD_NORMALS[rare][region][slot][0]
        counts = [0,0,0,0]
        for snow,_,weight in ROAD_NORMALS[rare][region][slot][0]:
            counts[snow]+=weight
        return tuple((snow,0,weight) for snow,weight in enumerate(counts) if weight)
    exposed = climate.seasonal_exposure(_published(flags),region,slot//3+1)
    clear = SHARES-sum(row[-1] for row in exposed)
    return ((0,0,clear),)+tuple((snow,road if mode in LAND else 0,w) for snow,road,w in exposed)


def _rates(mode,distribution,conservative):
    outcomes=[]
    for snow,condition,share in distribution:
        road, ice = (condition,0) if mode in LAND else (snow,condition)
        speed, food, cargo = travel._medium(mode,snow,road,ice,True)
        if not speed:
            food = weather.WARMTH[snow]*rules.RATION_SCALE//100
            cargo = 0
        outcomes.append((speed*rules.DAY_TICKS,food,cargo,share))
    issue = sum(share for work,_,_,share in outcomes if not work)
    counts = [sum(row[index]*row[3] for row in outcomes)//SHARES for index in range(3)]
    if conservative and len(outcomes)>1:
        # Weight the slowest quarter once, including slow water and standing ice.
        tail = [0,0,0]
        left = SHARES//4
        for row in sorted(outcomes,key=lambda rate:(rate[0],-rate[1],-rate[2])):
            share = min(left,row[3])
            for index in range(3):
                tail[index] += row[index]*share
            left -= share
            if not left:
                break
        counts = [(2*mean+total*4//SHARES)//3 for mean,total in zip(counts,tail,strict=True)]
        issue = (2*issue+min(SHARES,4*issue))//3
    return Rates(*counts,issue)


@lru_cache(maxsize=6_144)
def _normal_rates(flags,mode,region,reach,slot,conservative):
    return _rates(mode,_normal_rows(flags,mode,region,reach,slot),conservative)


@lru_cache(maxsize=4_096)
def _depth_profile(flags,region,ordinal,depth,cold):
    public = _published(flags)
    carry = []
    for ahead in range(VISIBLE_DAYS):
        if ahead:
            month = (ordinal+ahead)%360//30+1
            level = cold if ahead<3 else climate.cold_normal(public,region,month)
            depth = max(0,depth-weather.MELT[level])
        carry.append(2 if depth>=5 else int(depth>0))
    return tuple(carry)


@lru_cache(maxsize=4_096)
def _ice_profile(flags,region,ordinal,index,status,sensitivity,cold):
    public = _published(flags)
    states = [status]
    for ahead in range(1,VISIBLE_DAYS):
        month = (ordinal+ahead)%360//30+1
        level = cold if ahead<3 else climate.cold_normal(public,region,month)
        index,status = weather.ice_step(index,status,level,sensitivity)
        states.append(status)
    return tuple(states)


@lru_cache(maxsize=8_192)
def _conditional_rates(flags,mode,region,reach,slot,grade,visible_ice,snow,confidence,conservative):
    normal = _normal_rows(flags,mode,region,reach,slot)
    if mode in LAND:
        updated=tuple((max(observed,snow),max(road,grade,snow),w) for observed,road,w in normal)
    else:
        updated=tuple((max(observed,snow),visible_ice if visible_ice is not None else condition,w)
                      for observed,condition,w in normal)
    baseline = _rates(mode,normal,conservative)
    visible = _rates(mode,updated,conservative)
    return Rates(*((a*(VISIBLE_DAYS-confidence)+b*confidence)//VISIBLE_DAYS
                   for a,b in zip(baseline,visible,strict=True)))


@lru_cache(maxsize=4_096)
def _base(legs):
    days = weight = 0
    for parts,_ in legs:
        work = sum(amount for _,amount in parts)
        section = rules.ceil_div(work,travel.QUANTA)
        numerator = sum(amount*rules.MARCH_SUPPLY_PERCENT[part.mode]*rules.DAY_TICKS for part,amount in parts)
        numerator += (section*travel.QUANTA-work)*rules.RATION_SCALE
        days += section
        weight += numerator//travel.QUANTA
    return days,weight


def _project(legs,ordinal,start,flags,visible,ice,conservative):
    elapsed = rations = loss = waiting = waiting_food = visible_delay = visible_food = freeze = 0
    exposed = set()
    for parts, rest in legs:
        for part, remain in parts:
            mode, _, region, reach = part
            while remain and elapsed < MAX_DAYS*DAY:
                ahead = start+elapsed//DAY
                slot = (ordinal+ahead)%360//10
                normal = _normal_rates(flags,mode,region,reach,slot,conservative)
                rate = normal
                known_ice = None
                if ahead < VISIBLE_DAYS:
                    pack, public_snow = visible[region]
                    known_ice = ice[reach][ahead] if reach in ice else None
                    snow = public_snow if ahead<2 else 0
                    if pack[ahead] or known_ice is not None or snow:
                        rate = _conditional_rates(flags,mode,region,reach,slot,pack[ahead],
                                                  known_ice,snow,VISIBLE_DAYS-ahead,conservative)
                    block = DAY-elapsed%DAY
                else:
                    block = (10-(ordinal+ahead)%10)*DAY-elapsed%DAY
                time = min(block, rules.ceil_div(remain*DAY,rate.work) if rate.work else block)
                remain = max(0,remain-time*rate.work//DAY)
                rations += time*rate.food
                loss += time*rate.cargo
                waiting += time*rate.frozen
                waiting_food += time*rate.food*rate.frozen//SHARES
                visible_delay += time*max(0,normal.work-rate.work)//travel.QUANTA
                visible_food += time*max(0,rate.food-normal.food)*(SHARES-rate.frozen)//SHARES
                freeze = max(freeze,rate.frozen)
                if reach is not None and rate.frozen>=SHARES//5:
                    exposed.add(reach)
                elapsed += time
            if remain:
                return Projection(MAX_DAYS,rations//DAY,loss//DAY,waiting//(DAY*SHARES),
                                  waiting_food//DAY,visible_delay//DAY,visible_food//DAY,
                                  freeze,tuple(sorted(exposed)),True)
        night = -elapsed%DAY
        ahead = start+elapsed//DAY
        slot = (ordinal+ahead)%360//10
        warmth = sum(weather.WARMTH[snow]*w for snow,_,w in _normal_rows(flags,'plain',rest,None,slot))
        rations += night*warmth*rules.RATION_SCALE//(100*SHARES)
        elapsed += night
    return Projection(elapsed//DAY,rations//DAY,loss//DAY,waiting//(DAY*SHARES),
                      waiting_food//DAY,visible_delay//DAY,visible_food//DAY,
                      freeze,tuple(sorted(exposed)),False)


@lru_cache(maxsize=4_096)
def _route(legs,ordinal,start,options,marks,ice_marks,conservative):
    seen = {region:(_depth_profile(options,region,ordinal,depth,cold),snow)
            for region,depth,snow,cold in marks}
    ice = {reach:_ice_profile(options,region,ordinal,index,status,sensitivity,cold)
           for reach,region,index,status,sensitivity,cold in ice_marks}
    return _project(legs,ordinal,start,options,seen,ice,conservative)


def _legs(game,quote,position,stop):
    legs=[]
    end=0
    for leg in quote['routes']:
        start,end=end,end+leg['days']*travel.QUANTA
        if end<=position:
            continue
        if stop is not None and stop<=start:
            break
        parts=travel._parts_for_leg(game,leg)
        sections=tuple(travel._segments(parts,max(0,position-start),None if stop is None else stop-start))
        if sections:
            legs.append((sections,game.catalog.climate.cities[leg['to']]['climate_region_id']))
    return tuple(legs)


def estimate(game,state,quote,*,position=0,stop=None,start_in=0,conservative=False):
    pool=state.extension[weather.POOL]
    legs=_legs(game,quote,position,stop)
    parts={part for sections,_ in legs for part,_ in sections}
    regions={part.region for part in parts}
    reaches={part.reach for part in parts if part.reach in pool['ice']}
    marks=tuple((key,cell['depth'],cell['severity'],cell['cold']) for key in sorted(regions)
                for cell in (pool['regions'][key],))
    ice_marks=[]
    for key in sorted(reaches):
        reach=game.catalog.climate.reaches[key]
        cell=pool['ice'][key]
        region=reach['freeze_region_id']
        ice_marks.append((key,region,cell['index'],cell['state'],reach['freeze_sensitivity'],
                          pool['regions'][region]['cold']))
    ordinal=weather.ordinal((state.year,state.month,state.day))%360
    result=_route(legs,ordinal,start_in,tuple(sorted(pool['options'].items())),marks,tuple(ice_marks),conservative)
    base, base_food=_base(legs)
    blocked=travel.closed_at_node(state,quote,position)
    if blocked is None and legs:
        blocked=travel.medium(state,legs[0][0][0][0])[3]
    delay=max(0,result.days-base)
    wait=min(delay,result.waiting)
    visible=min(delay-wait,result.visible_delay)
    extra=result.food-base_food
    wait_food=min(max(0,extra),result.waiting_food)
    visible_food=min(max(0,extra-wait_food),result.visible_food)
    return dict(base_days=base,expected_arrival_days=result.days,
                visible_weather_extra_days=visible,seasonal_extra_days=delay-wait-visible,
                predicted_ice_wait_days=wait,currently_blocked=blocked,seasonal_freeze_risk=result.freeze,
                base_ration_weight=base_food,total_ration_weight=result.food,
                visible_weather_extra_weight=visible_food,seasonal_extra_weight=extra-wait_food-visible_food,
                waiting_ration_weight=wait_food,cargo_loss_weight=result.cargo,extra_days=delay,
                extra_weight=max(0,extra),reaches=result.reaches,bounded=result.bounded)


def net_cargo(grain,estimate,remainder=0):
    """Approximate the rolling cargo debit with the mean per-day exposure."""
    days=max(1,estimate['expected_arrival_days'])
    return _net_cargo(grain,estimate['cargo_loss_weight'],days,remainder)


@lru_cache(maxsize=8_192)
def _net_cargo(grain,total_weight,days,remainder):
    weight,extra=divmod(total_weight,days)
    if not grain or not (weight or extra):
        return grain
    for index in range(days):
        lost,remainder=rules.cargo_loss(grain,weight+(index<extra),remainder)
        grain-=lost
        if not grain:
            break
    return grain


def snowpack_risk(state, region, *, days=10):
    pool=state.extension[weather.POOL]
    row=pool['regions'][region]
    options=tuple(sorted(pool['options'].items()))
    ordinal=weather.ordinal((state.year,state.month,state.day))%360
    slot=(ordinal+days)%360//10
    public=sum(share for _,road,share in _normal_rows(options,'plain',region,None,slot) if road)
    if days>=VISIBLE_DAYS:
        return public
    observed=bool(_depth_profile(options,region,ordinal,row['depth'],row['cold'])[days])
    return (public*days+(SHARES if observed else 0)*(VISIBLE_DAYS-days))//VISIBLE_DAYS


def trip(game,state,outbound,back=None,*,position=0):
    normal=estimate(game,state,outbound,position=position)
    conservative=estimate(game,state,outbound,position=position,conservative=True)
    result=dict(normal,conservative_arrival_days=max(normal['expected_arrival_days'],
                                                    conservative['expected_arrival_days']),
        conservative_ration_weight=max(normal['total_ration_weight'],conservative['total_ration_weight']),
        conservative_cargo_loss_weight=max(normal['cargo_loss_weight'],conservative['cargo_loss_weight']))
    if back is not None:
        returning=estimate(game,state,back,start_in=normal['expected_arrival_days'])
        result.update(return_ration_weight=returning['total_ration_weight'],
                      return_freeze_risk=returning['seasonal_freeze_risk'],
                      return_departure_days=normal['expected_arrival_days'],
                      return_arrival_days=normal['expected_arrival_days']+returning['expected_arrival_days'])
    return result


def cache_stats():
    return dict(route=_route.cache_info()._asdict(),normal=_normal_rates.cache_info()._asdict(),
                visible=_conditional_rates.cache_info()._asdict())
