"""Shared fixed-point travel and provisions over the existing physical routes.

Normal work remains the quoted integer day, split into the existing route stages.
The actual day uses fractions internally and retains progress at 1/644,000 normal
day. All unchanged speeds, snowy straight days and ice speeds divide that unit.
"""
from fractions import Fraction
from functools import lru_cache
from typing import NamedTuple

from . import climate_regions, logistics_rules as rules, winter_weather as weather

QUANTA = 644 * rules.DAY_TICKS
SPEED_UNIT = 644
MAX_RATION_WEIGHT = 260_000
MAX_CARGO_WEIGHT = 300_000


class Part(NamedTuple):
    mode: str
    work: int
    region: str
    reach: str | None


class Daily(NamedTuple):
    moved: int
    ration: int
    cargo: int
    blocked: str | None
    normal_ration: int
    normal_cargo: int
    delay: int


def _on_land(mode, ticks, runs):
    work = ticks*SPEED_UNIT
    previous = elapsed = 0
    for region, count in runs:
        elapsed += count
        end = work*elapsed//climate_regions.SAMPLES
        if end > previous:
            yield Part(mode, end-previous, region, None)
        previous = end


def _parts_for_leg(game, leg):
    climate = game.catalog.climate
    source, target = leg['from'], leg['to']
    ruleset = game.catalog.data['travel_rules']
    key = (leg['id'], source, target, leg['days'], leg.get('water_days'), leg.get('embark_days'))
    if key not in climate.parts:
        stages = rules.leg_parts(leg, ruleset, locations=True)
        first_water = next((place for mode, _, place in stages if mode.startswith('river_')), None)
        parts = []
        for mode, ticks, location in stages:
            if location == 'road':
                parts.extend(_on_land(mode, ticks, climate.land(leg['id'], source, target, mode)))
            elif mode.startswith('river_'):
                row = climate.reaches.get(location)
                region = row['climate_region_id'] if row else climate.cities[source]['climate_region_id']
                parts.append(Part(mode, ticks*SPEED_UNIT, region, location))
            elif mode == 'sea':
                # Land and snow speed are excluded at sea. The geographic bands
                # are only used for exposure to cold and snowfall.
                split = climate.land(leg['id'], source, target, 'sea')
                if all(point in climate_regions.ISLANDS for point in (source, target)):
                    split = (('tropical_islands', climate_regions.SAMPLES),)
                parts.extend(_on_land(mode, ticks, split))
            else:
                node = target if location == 'trailing' else source
                parts.append(Part(mode, ticks*SPEED_UNIT,
                                  climate.cities[node]['climate_region_id'],
                                  first_water if mode == 'embark' else None))
        climate.parts[key] = tuple(parts)
    return climate.parts[key]


def plan(game, quote):
    return tuple(part for leg in quote.get('routes', ()) for part in _parts_for_leg(game, leg))


def reverse_parts(parts,limit=None):
    modes={'river_downstream':'river_upstream','river_upstream':'river_downstream'}
    return tuple(Part(modes.get(part.mode,part.mode),amount,part.region,part.reach)
                 for part,amount in reversed(tuple(_segments(parts,0,limit))))


def return_weight(state,parts,region):
    days,rations,_,frozen=_forecast(tuple(p.work for p in parts),
        tuple(medium(state,p) for p in parts),wait_rate(state,region))
    return rations if frozen is None else max(rations,(10+rules.ceil_div(
        sum(p.work for p in parts),QUANTA))*rules.RATION_SCALE)


def work(supply):
    return supply['winter']['work'] if 'winter' in supply else supply['route_days']*QUANTA


def medium(state, part):
    pool = state.extension[weather.POOL]
    row = pool['regions'][part.region]
    snow = row['severity']
    road = weather.road_weather(row) if part.mode in ('plain','mountain','desert') else snow
    ice = pool['ice'].get(part.reach)
    ice_status = ice['state'] if pool['stage'] >= 4 and ice else 0
    speed, ration, cargo = _medium(part.mode,snow,road,ice_status,pool['stage']>=3)
    return speed, ration, cargo, part.reach if not speed else None


@lru_cache(maxsize=256)
def _medium(mode, snow, road, ice_status, weather_cargo):
    if mode.startswith('river_') or mode == 'embark':
        speed = (weather.SPEED_PERCENT[ice_status]*SPEED_UNIT//100 if mode != 'embark'
                 else 0 if ice_status == 3 else SPEED_UNIT)
    elif mode in ('plain','mountain','desert'):
        speed = SPEED_UNIT*100//weather.TIME_PERCENT[road]
    else:
        speed = SPEED_UNIT
    surcharge = weather.SURCHARGE[road]
    ration = (weather.WARMTH[snow]*(10_000+(rules.MARCH_SUPPLY_PERCENT[mode]-100)*surcharge)
              * rules.RATION_SCALE // 1_000_000)
    cargo = rules.CARGO_GRAIN_LOSS_BPS[mode]*rules.DAY_TICKS
    return speed, ration, cargo*weather.CARGO[road]//100 if weather_cargo else cargo


def _segments(parts, position, stop=None):
    end = 0
    for part in parts:
        start, end = end, end+part.work
        remaining = (end if stop is None else min(end, stop)) - max(start, position)
        if remaining > 0:
            yield part, remaining
        if stop is not None and end >= stop:
            break


def wait_rate(state, region):
    snow = state.extension[weather.POOL]['regions'][region]['severity']
    return weather.WARMTH[snow]*rules.RATION_SCALE//100


def day(state, parts, position, *, rest_region, moving=True, on_leg=False, stop=None, clear=False):
    """Take one actual day. Time left after a checkpoint pays a full meal."""
    remaining_day = Fraction(1)
    advanced = exposure = ration = cargo = normal_ration = normal_cargo = 0
    blocked = None
    if moving or on_leg:
        for part, available in _segments(parts, position, stop):
            speed, weight, loss, ice = ((*_medium(part.mode,0,0,0,False),None)
                                        if clear else medium(state,part))
            movement = moving and speed
            duration = min(remaining_day, Fraction(available, speed*rules.DAY_TICKS)) if movement else remaining_day
            if movement:
                amount = duration*speed*rules.DAY_TICKS
                advanced += amount
            if movement or ice:
                exposure += duration
            blocked = ice
            ration += duration*weight
            cargo += duration*loss if movement or on_leg else 0
            normal_ration += duration*rules.MARCH_SUPPLY_PERCENT[part.mode]*rules.DAY_TICKS
            if movement or on_leg:
                normal_cargo += duration*rules.CARGO_GRAIN_LOSS_BPS[part.mode]*rules.DAY_TICKS
            remaining_day -= duration
            if not remaining_day:
                break
    # The original engine charges a meal on the last march day. When a
    # journey reaches a node before nightfall, the remaining meal time uses
    # the node rate and there is no additional physical cargo exposure.
    ration += remaining_day*(rules.RATION_SCALE if clear else wait_rate(state,rest_region))
    normal_ration += remaining_day*rules.RATION_SCALE
    return Daily(int(advanced), int(ration), int(cargo), blocked, int(normal_ration),
                 int(normal_cargo), int(exposure*QUANTA-advanced))


@lru_cache(maxsize=8192)
def _forecast(workloads, rates, waiting):
    duration = Fraction(0)
    ration = Fraction(0)
    cargo = Fraction(0)
    for amount, (speed, weight, loss, ice) in zip(workloads, rates):
        if ice:
            return None, int(ration), int(cargo), ice
        time = Fraction(amount, speed*rules.DAY_TICKS)
        duration += time
        ration += time*weight
        cargo += time*loss
    days = rules.ceil_div(duration.numerator, duration.denominator)
    ration += (days-duration)*waiting
    return days, int(ration), int(cargo), None


def forecast(game, state, quote, *, position=0, stop=None):
    """Today’s published road and ice conditions held for an estimate."""
    segments = tuple(_segments(plan(game, quote), position, stop))
    if not segments:
        return 0, 0, 0, None
    # The rounded day ends at the route's next real stopping point.
    node = quote['path'][-1]
    if stop is not None:
        offset = 0
        for leg in quote['routes']:
            offset += leg['days']*QUANTA
            if offset == stop:
                node = leg['to']
                break
    waiting = wait_rate(state, game.catalog.climate.cities[node]['climate_region_id'])
    return _forecast(tuple(amount for _,amount in segments),
                     tuple(medium(state, part) for part,_ in segments), waiting)


def checkpoint_forecast(game,state,quote,*,position=0,stop=None):
    """Published conditions, rounding the day at the same nodes as movement."""
    days = weight = end = 0
    for leg in quote['routes']:
        beginning,end=end,end+leg['days']*QUANTA
        if end<=position:
            continue
        if stop is not None and beginning>=stop:
            break
        parts=_parts_for_leg(game,leg)
        segments=tuple(_segments(parts,max(0,position-beginning),None if stop is None else stop-beginning))
        waiting=wait_rate(state,game.catalog.climate.cities[leg['to']]['climate_region_id'])
        duration,rations,_,blocked=_forecast(tuple(work for _,work in segments),
                    tuple(medium(state,part) for part,_ in segments),waiting)
        weight+=rations
        if blocked:
            return None,weight,blocked
        days+=duration
    return days,weight,None


def seasonal_forecast(game,state,quote,*,start_in=0,position=0,pressure=False):
    """Risk based on public monthly normals and currently visible ice."""
    pool=state.extension.get(weather.POOL)
    if pool is None:
        return dict(extra_days=0,extra_weight=0,reaches=())
    from . import winter_climate
    if winter_climate.forecast_enabled(state):
        from . import winter_forecast
        result=winter_forecast.estimate(game,state,quote,start_in=start_in,position=position,
                                        conservative=pressure)
        # The risk is represented by the ETA and budget. Only an exhausted
        # forecast horizon makes this planning quote unusable.
        return dict(result,risk_reaches=result['reaches'],
                    reaches=result['reaches'] if result['bounded'] else ())
    new_climate = winter_climate.enabled(state)
    elapsed=start_in*QUANTA
    delay=extra=0
    risks=set()
    for part,work in _segments(plan(game,quote),position):
        month=((state.month-1)+(state.day-1+elapsed//QUANTA)//30)%12+1
        if part.mode in ('plain','mountain','desert'):
            if new_climate:
                exposures = winter_climate.seasonal_exposure(state, part.region, month, pressure=pressure)
            else:
                months,chance,_,_=climate_regions.REGIONS[part.region]
                severity = 2 if pressure else 1
                exposures = ((severity, severity, (100 if pressure else chance)*100),) if month in months else ()
            if exposures:
                clear = _medium(part.mode,0,0,0,False)[1]
            for snow, road, exposure in exposures:
                duration = weather.TIME_PERCENT[road]
                rate = _medium(part.mode,snow,road,0,True)[1]
                delay += work*(duration-100)*exposure
                extra += work*(duration*rate-100*clear)*exposure
        if part.reach in pool['ice'] and pool['stage']>=4:
            reach=game.catalog.climate.frozen_reaches[part.reach]
            typical=winter_climate.cold_normal(state, reach['freeze_region_id'], month)
            ice=pool['ice'][part.reach]
            trend=max(weather.BASE_ICE[typical],weather.BASE_ICE[pool['regions'][reach['freeze_region_id']]['cold']]
                      if elapsed//QUANTA<=10 else 0)
            if ice['state']==3 or trend>0 and ice['index']+trend*reach['freeze_sensitivity']*min(
                    30,elapsed//QUANTA+rules.ceil_div(work,QUANTA))>=6000:
                risks.add(part.reach)
        elapsed+=work
    return dict(extra_days=rules.ceil_div(delay,1_000_000*QUANTA),
                extra_weight=rules.ceil_div(extra,1_000_000*QUANTA),reaches=tuple(sorted(risks)))


def leg_time(game, state, leg):
    return leg_forecast(game, state, leg)[0]


def time_rank(game, state, leg):
    # These are normal-work units multiplied by the exact reciprocal speed.
    # Distinct segments must not each add a whole rounding day in the search.
    parts=_parts_for_leg(game,leg)
    return sum(p.work*(300*SPEED_UNIT//medium(state,p)[0]) for p in parts)


def leg_forecast(game, state, leg):
    parts = _parts_for_leg(game, leg)
    rates = tuple(medium(state, part) for part in parts)
    if all(row[0] == SPEED_UNIT and row[1] == rules.MARCH_SUPPLY_PERCENT[p.mode]*rules.DAY_TICKS
           for p,row in zip(parts,rates)):
        # The exact original weight in neutral conditions, including fractions.
        return leg['days'], sum(p.work//SPEED_UNIT*rules.MARCH_SUPPLY_PERCENT[p.mode] for p in parts
                                ) if all(p.work%SPEED_UNIT==0 for p in parts) else sum(
            p.work*rules.MARCH_SUPPLY_PERCENT[p.mode] for p in parts)//SPEED_UNIT
    waiting = wait_rate(state, game.catalog.climate.cities[leg['to']]['climate_region_id'])
    return _forecast(tuple(p.work for p in parts), rates, waiting)[:2]


def quote_days(game, state, quote, *, position=0, wait=None):
    normal = rules.ceil_div(quote['days']*QUANTA-position, QUANTA)
    if not weather.movement(state):
        return normal
    estimate = forecast(game, state, quote, position=position)[0]
    if estimate is None:
        return normal + (10 if wait is None else wait)
    return estimate


def quote_turns(game,state,quote):
    if not weather.movement(state):
        return quote['turns']
    return max(1,rules.ceil_div(quote_days(game,state,quote),10))


def route_risk(game,state,quote,days):
    """A public cold/ice trend for protecting a pending winter return."""
    if weather.stage(state)<5:
        return ()
    pool=state.extension[weather.POOL]
    result=set()
    for part in plan(game,quote):
        if part.reach not in pool['ice']:
            continue
        row=pool['ice'][part.reach]
        reach=game.catalog.climate.frozen_reaches[part.reach]
        cold=pool['regions'][reach['freeze_region_id']]['cold']
        rise=max(0,weather.BASE_ICE[cold])*reach['freeze_sensitivity']
        if row['state']==3 or (row['state']>=1 and row['index']+rise*min(days,10)>=6_000):
            result.add(part.reach)
    return tuple(sorted(result))


def ration_weight(game, state, quote, *, position=0, stop=None, minimum=0):
    if not weather.movement(state) and position%QUANTA==0:
        count=(quote['days']*QUANTA if stop is None else stop)-position
        if count%QUANTA==0:
            days=count//QUANTA
            parts=rules.plan(quote,game.catalog.data['travel_rules'])
            return rules.weight(parts,position//QUANTA,days)+max(0,minimum-days)*rules.RATION_SCALE
    days, ration, _, blocked = forecast(game, state, quote, position=position, stop=stop)
    # An already travelling column may have to wait for an unknown thaw.
    # Budget at least a ten-day retry instead of treating the frozen tail as free.
    if blocked:
        days = rules.ceil_div((quote['days']*QUANTA if stop is None else stop)-position, QUANTA)+10
        ration = max(ration, days*rules.RATION_SCALE)
    return ration+max(0, minimum-days)*rules.RATION_SCALE


def horizon_weight(game,state,quote,days,*,position,stop):
    time=Fraction(days)
    weight=0
    region=game.catalog.climate.cities[quote['path'][-1]]['climate_region_id']
    for part,amount in _segments(plan(game,quote),position,stop):
        speed,rate,_,_=medium(state,part)
        duration=min(time,Fraction(amount,speed*rules.DAY_TICKS)) if speed else time
        weight+=duration*rate
        time-=duration
        if not time:
            break
    return int(weight+time*wait_rate(state,region))


def checkpoint_horizon_weight(game,state,quote,days,*,position,stop):
    """Ration weight through published physical days, with actual stop rounding."""
    end=weight=0
    region=game.catalog.climate.cities[quote['path'][0]]['climate_region_id']
    for leg in quote['routes']:
        beginning,end=end,end+leg['days']*QUANTA
        if end<=position:
            region=game.catalog.climate.cities[leg['to']]['climate_region_id']
            continue
        if beginning>=stop or days<=0:
            break
        segments=tuple(_segments(_parts_for_leg(game,leg),max(0,position-beginning),stop-beginning))
        rates=tuple(medium(state,part) for part,_ in segments)
        arrival=game.catalog.climate.cities[leg['to']]['climate_region_id']
        through,rations,_,frozen=_forecast(tuple(work for _,work in segments),rates,wait_rate(state,arrival))
        if through is not None and days>=through:
            days-=through
            weight+=rations
            region=arrival
            continue
        if frozen and beginning>=position:
            return weight+days*wait_rate(state,region)
        remaining=Fraction(days)
        partial=0
        for (part,work),(speed,rate,_,ice) in zip(segments,rates):
            duration=remaining if not speed else min(remaining,Fraction(work,speed*rules.DAY_TICKS))
            partial+=duration*(wait_rate(state,part.region) if ice else rate)
            remaining-=duration
            if not remaining:
                break
        return weight+int(partial+remaining*wait_rate(state,arrival))
    return weight+max(0,days)*wait_rate(state,region)


def next_checkpoint(quote, position):
    work_done=0
    for leg in quote['routes']:
        work_done+=leg['days']*QUANTA
        if work_done>position:
            break
    return work_done


def closed_at_node(state, quote, position):
    if weather.stage(state) < 4:
        return None
    beginning=0
    for leg in quote['routes']:
        if beginning==position:
            ice=state.extension[weather.POOL]['ice']
            return next((r['reach_id'] for r in leg.get('river_segments',())
                         if ice.get(r['reach_id'],{}).get('state')==3),None)
        beginning+=leg['days']*QUANTA
    return None


def preview(game, state, quote, *, units=0, cargo=0, back=None):
    if weather.stage(state) < 2:
        return {}
    days, ration, _, blocked = forecast(game,state,quote)
    normal_parts = rules.plan(quote, game.catalog.data['travel_rules'])
    normal_weight = rules.weight(normal_parts)
    from .grain_units import denominator
    divisor = denominator()*rules.RATION_SCALE
    charged=lambda weight:rules.ceil_div(units*weight,divisor)
    parts=plan(game,quote)
    pool=state.extension[weather.POOL]
    result=dict(normal_days=quote['days'], days=days, extra_days=None if days is None else days-quote['days'],
                base_grain=charged(quote['days']*rules.RATION_SCALE),
                normal_grain=charged(normal_weight),grain=None if blocked else charged(ration),
                extra_grain=None if blocked else charged(ration)-charged(normal_weight),
                cargo_loss_estimate=cargo-estimate_cargo(game,state,quote,cargo) if not blocked else None,
                normal_cargo_loss_estimate=cargo-rules.estimate_cargo(cargo,normal_parts,quote['days'])[0] if cargo else 0,
                region_snow={p.region:weather.NAMES[pool['regions'][p.region]['severity']] for p in parts},
                ice={p.reach:weather.ICE_NAMES[pool['ice'][p.reach]['state']] for p in parts if p.reach in pool['ice']},
                blocked_reach=blocked, forecast='current_conditions')
    if units and not blocked and parts:
        weights=([],[])
        for part in parts:
            speed,rate,loss,_=medium(state,part)
            warmth=weather.WARMTH[pool['regions'][part.region]['severity']]
            weights[0].append((speed,rate*100//warmth,loss,None))
            weights[1].append((speed,rules.MARCH_SUPPLY_PERCENT[part.mode]*rules.DAY_TICKS,loss,None))
        workloads=tuple(p.work for p in parts)
        without_warmth=charged(_forecast(workloads,tuple(weights[0]),rules.RATION_SCALE)[1])
        base_for_delay=charged(_forecast(workloads,tuple(weights[1]),rules.RATION_SCALE)[1])
        result.update(winter_warmth=charged(ration)-without_warmth,
                      winter_route_overhead=without_warmth-base_for_delay,
                      winter_delay_grain=base_for_delay-result['normal_grain'])
    from . import winter_climate
    if winter_climate.forecast_enabled(state):
        from . import winter_forecast
        outlook=winter_forecast.trip(game,state,quote,back)
        result['outlook']=dict(outlook,grain=charged(outlook['total_ration_weight']),
            extra_grain=charged(outlook['total_ration_weight'])-charged(outlook['base_ration_weight']),
            return_grain=charged(outlook['return_ration_weight']) if 'return_ration_weight' in outlook else None,
            expected_net_grain=winter_forecast.net_cargo(cargo,outlook),
            conservative_net_grain=winter_forecast.net_cargo(cargo,dict(outlook,
                cargo_loss_weight=outlook['conservative_cargo_loss_weight'],
                expected_arrival_days=outlook['conservative_arrival_days'])))
    return result


@lru_cache(maxsize=4096)
def _cargo_rates(workloads,rates):
    result=[]
    left=Fraction(1)
    weight=0
    for amount,(speed,_,loss,ice) in zip(workloads,rates):
        if ice:
            return None
        duration=Fraction(amount,speed*rules.DAY_TICKS)
        while duration>=left:
            result.append(int(weight+left*loss))
            duration-=left
            left=Fraction(1)
            weight=0
        left-=duration
        weight+=duration*loss
    if left<1:
        result.append(int(weight))
    return tuple(result)


def estimate_cargo(game,state,quote,grain,*,position=0,remainder=0):
    if not grain:
        return 0
    if weather.stage(state)<2 or not weather.movement(state) and position%QUANTA==0:
        parts=rules.plan(quote,game.catalog.data['travel_rules'])
        offset=position//QUANTA
        return rules.estimate_cargo(grain,parts,quote['days']-offset,start=offset,remainder=remainder)[0]
    segments=tuple(_segments(plan(game,quote),position))
    rates=_cargo_rates(tuple(n for _,n in segments),tuple(medium(state,p) for p,_ in segments))
    if rates is None:
        return 0
    return _apply_cargo(grain,remainder,rates)[0]


def leg_cargo(game,state,leg,grain,remainder):
    parts=_parts_for_leg(game,leg)
    rates=_cargo_rates(tuple(p.work for p in parts),tuple(medium(state,p) for p in parts))
    return _apply_cargo(grain,remainder,rates)


def _apply_cargo(grain,remainder,rates):
    for weight in rates:
        lost,remainder=rules.cargo_loss(grain,weight,remainder)
        grain-=lost
    return grain,remainder


def eta_turn(game,state,journey,through_turn):
    supply = journey['supply']
    if 'winter' not in supply:
        return None
    days = quote_days(game,state,journey['quote'],position=work(supply))
    return through_turn + rules.ceil_div(days,10)


def set_eta(game,state,journey):
    eta=eta_turn(game,state,journey,state.turn)
    if eta is not None:
        journey['arrival_turn']=max(state.turn+1,eta)
    return journey
