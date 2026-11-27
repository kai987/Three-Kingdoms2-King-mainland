"""Independent regional winter weather on the campaign's 30-day calendar."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from hashlib import sha256

from . import winter_agriculture, winter_climate
from .climate_regions import REGIONS, WINTER_MONTHS
from .winter_climate import DURATION, LEGACY_DEPTH as MAX_DEPTH, MELT, SNOWFALL

FIELD = 'weather_rules_version'
POOL = 'winter_weather'
VERSION = 22
CORRECTED = 221
TRANSPORT = 1
PREPARATION = 2
CORRECTIONS = TRANSPORT | PREPARATION
NAMES = ('clear', 'light_snow', 'heavy_snow', 'blizzard')
ICE_NAMES = ('open', 'floating_ice', 'partial_ice', 'frozen')
BASE_ICE = (-6, -2, 3, 5)
SPEED_PERCENT = (100, 75, 50, 0)
TIME_PERCENT = (100, 115, 140, 200)
WARMTH = (100, 105, 115, 130)
SURCHARGE = (100, 120, 150, 200)
CARGO = (100, 120, 150, 200)
_stage = ContextVar('winter_experiment_stage', default=0)
_adjustments = ContextVar('winter_experiment_adjustments', default=0)
_observer = ContextVar('winter_readonly_observer', default=None)
_detailed = ContextVar('winter_transport_observation', default=False)


@contextmanager
def experiment(stage, *, observe=None, adjustments=0, detailed=False):
    if type(stage) is not int or not 0 <= stage <= 5:
        raise ValueError('Winter experiment stage')
    if type(adjustments) is not int or not 0 <= adjustments <= CORRECTIONS or adjustments and stage != 5:
        raise ValueError('Winter experiment adjustments')
    stage_token, observer_token = _stage.set(stage), _observer.set(observe)
    adjustment_token = _adjustments.set(adjustments)
    detail_token = _detailed.set(bool(detailed and observe is not None))
    try:
        yield
    finally:
        _detailed.reset(detail_token)
        _adjustments.reset(adjustment_token)
        _observer.reset(observer_token)
        _stage.reset(stage_token)


def stage(state):
    return getattr(state, 'extension', {}).get(POOL, {}).get('stage', 0)


def corrected(state, flag):
    return bool(state.extension.get(POOL, {}).get('adjustments', 0) & flag)


def initialize(game, state, requested=None, *, options=None):
    if requested is not None and (type(requested) is not int or requested not in (0, VERSION, CORRECTED, winter_climate.VERSION)):
        raise ValueError('Winter weather rules version')
    climate = requested == winter_climate.VERSION
    if options is not None and not climate:
        raise ValueError('Climate options require weather V2.3')
    selected = _stage.get() if requested is None else (5 if requested else 0)
    adjustments = _adjustments.get() if requested is None else (CORRECTIONS if climate or requested == CORRECTED else 0)
    if selected:
        state.extension[FIELD] = requested if climate else (CORRECTED if adjustments else VERSION)
        state.extension[POOL] = dict(stage=selected, seed=seed_for(state.seed), tick=0,
            regions={key: dict(severity=0, began=0, ends=0, depth=0, cold=0,
                               winter=0, snow_seen=False) for key in REGIONS},
            ice={key: dict(index=0, state=0, changed=0) for key in game.catalog.climate.frozen_reaches})
        pool = state.extension[POOL]
        if adjustments:
            pool['adjustments'] = adjustments
        if climate:
            pool.update(options=winter_climate.normalize({} if options is None else options), agriculture=None)
            for row in pool['regions'].values():
                row.update(snow_cover_run=0, fallback_winter=0)
    else:
        state.extension.pop(FIELD, None)
        state.extension.pop(POOL, None)


def seed_for(seed):
    return sha256(f'tk2/winter/{VERSION}/{seed}'.encode('ascii')).hexdigest()


def ordinal(date):
    year, month, day = date
    return year*360+(month-1)*30+(day-1)


def date_at(data, tick):
    offset = ordinal((data['start_year'], data['start_month'], 1)) + max(0, tick-1)
    year, rest = divmod(offset, 360)
    month, day = divmod(rest, 30)
    return year, month+1, day+1


def winter_year(year, month):
    return year if month >= 11 else year-1


def draw(seed, region, year, month, index, field, limit):
    payload = f'{seed}/{region}/{year}/{month}/{index}/{field}'.encode('ascii')
    return int.from_bytes(sha256(payload).digest()[:8], 'big') % limit


@lru_cache(maxsize=4096)
def snowfall(seed, region, year, month, ten_days, guarantee=False):
    months, chance, _, _ = REGIONS[region]
    if month not in months:
        return 0, 0, 0
    return _snow_event(seed, region, year, month, ten_days, chance, winter_climate.LEGACY_SEVERITY, guarantee)


@lru_cache(maxsize=4096)
def _snow_event(seed, region, year, month, ten_days, chance, weights, guarantee):
    if not chance and not guarantee:
        return 0, 0, 0
    roll = draw(seed, region, year, month, ten_days, 'snow', 100)
    if roll >= chance and not guarantee:
        return 0, 0, 0
    strength = draw(seed, region, year, month, ten_days, 'severity', 100)
    light, heavy, _ = weights
    severity = (1 if strength < light else 2 if strength < light + heavy else 3) if roll < chance else 1
    low, high = DURATION[severity]
    duration = low + draw(seed, region, year, month, ten_days, 'duration', high-low+1)
    first = 1 + ten_days*10 + draw(seed, region, year, month, ten_days, 'begin', 11-duration)
    return severity, first, first+duration-1


def ice_state(index, previous):
    while previous < 3 and index >= (1500, 3500, 6000)[previous]:
        previous += 1
    while previous > 0 and index < (1000, 2500, 5000)[previous-1]:
        previous -= 1
    return previous


def ice_step(index, previous, cold, sensitivity):
    # Index uses hundredths of an abstract point. Only growth uses sensitivity.
    change = BASE_ICE[cold]
    index = min(10_000, max(0, index + change*(sensitivity if change > 0 else 100)))
    return index, ice_state(index, previous)


@lru_cache(maxsize=4096)
def _spring_event(seed, region, year, month, slot, chance):
    if not chance or draw(seed, region, year, month, slot, 'spring-frost', 100) >= chance:
        return 0, 0, False
    duration = 1 + draw(seed, region, year, month, slot, 'spring-duration', 3)
    first = 1 + slot*10 + draw(seed, region, year, month, slot, 'spring-begin', 11-duration)
    late_snow = (month == 4 and draw(seed, region, year, month, slot, 'late-snow', 100)
                 < winter_climate.LATE_SNOW.get(region, 0))
    return first, first + duration - 1, late_snow


@lru_cache(maxsize=1024)
def _exceptional_wave(seed, winter):
    if draw(seed, 'jiangnan', winter, 12, 0, 'cold-wave', 100) >= winter_climate.WAVE_PROBABILITY:
        return 0, 0
    duration = 2 + draw(seed, 'jiangnan', winter, 12, 0, 'wave-duration', 3)
    first = ordinal((winter, 12, 1)) + draw(seed, 'jiangnan', winter, 12, 0, 'wave-begin', 91-duration)
    return first, first + duration - 1


def _advance_climate_region(state, pool, key, row, date, tick, full_winter, wave_span, ledger):
    year, month, day = date
    slot = (day - 1) // 10
    winter = winter_year(year, month)
    ordinary = winter_climate.snow_probability(state, key, month)
    legacy_months, _, _, core = REGIONS[key]
    if ordinary and row['winter'] != winter:
        row.update(winter=winter, snow_seen=False, fallback_winter=0)
    if core and full_winter and month == 3 and day == 21 and not row['snow_seen']:
        row['fallback_winter'] = winter
    fallback = month == 3 and slot == 2 and row['fallback_winter'] == winter
    snow, first, last = _snow_event(pool['seed'], key, year, month, slot, ordinary,
                                    winter_climate.severity_distribution(state, key), fallback)
    event = (snow, tick - day + first, tick - day + last) if snow and first <= day <= last else (0, 0, 0)
    cold = winter_climate.cold_normal(state, key, month)
    # A newly eligible snowy month alone does not add ordinary cold draws.
    if month in legacy_months:
        roll = draw(pool['seed'], key, year, month, day, 'cold', 100)
        cold = min(3, max(0, cold+(roll >= 80)-(roll < 20)))
    first, last, late_snow = _spring_event(pool['seed'], key, year, month, slot,
                                           winter_climate.spring_probability(state, key, month))
    frost = first <= day <= last
    late = frost and late_snow
    if frost:
        cold = max(2, cold)
        if late:
            event = max(event, (1, tick - day + first, tick - day + last))
    serial = ordinal(date)
    wave = key in winter_climate.WAVE_REGIONS and wave_span[0] <= serial <= wave_span[1]
    if wave:
        event = max(event, (winter_climate.WAVE_REGIONS[key],
                            tick - serial + wave_span[0], tick - serial + wave_span[1]))
        cold = max(2, cold)
    severity, began, ends = event
    limit = winter_climate.snow_depth_limit(state, key)
    depth = (min(limit, row['depth'] + SNOWFALL[severity]) if severity else max(0, row['depth'] - MELT[cold]))
    row.update(severity=severity, began=began, ends=ends, depth=depth, cold=cold,
               snow_cover_run=row['snow_cover_run']+1 if depth else 0)
    if severity and month in WINTER_MONTHS:
        row['snow_seen'] = True
    if ledger is not None:
        winter_agriculture.observe(ledger, key, month, tick, row, frost=frost or wave, late=late, wave=wave)


def _observe_agriculture(pool, date, tick):
    year, month, day = date
    winter = winter_year(year, month)
    full = ordinal(date) - tick + 1 <= ordinal((winter, 11, 1))
    ledger = winter_agriculture.begin_day(pool, date, tick, complete_start=full)
    wave = (_exceptional_wave(pool['seed'], winter)
            if full and month in (12, 1, 2) and pool['options']['exceptional_cold_wave'] else (0, 0))
    return full, ledger, wave


def advance(game, state, tick):
    pool = state.extension.get(POOL)
    if pool is None or tick <= pool['tick']:
        return
    if tick != pool['tick']+1:
        raise ValueError('Winter calendar jumped a day')
    data = game.catalog.data
    year, month, day = date_at(data, tick)
    winter = winter_year(year, month)
    obs = _observer.get()
    new_climate = 'options' in pool
    if new_climate:
        date = year, month, day
        full, ledger, wave = _observe_agriculture(pool, date, tick)
    for key, row in pool['regions'].items():
        if new_climate:
            _advance_climate_region(state, pool, key, row, date, tick, full, wave, ledger)
            if obs:
                obs('region', {k:v for k,v in dict(tick=tick, year=year, month=month, day=day, region=key, **row).items()
                               if k not in ('snow_cover_run','fallback_winter')})
            continue
        months, _, cold_months, core = REGIONS[key]
        if month in months and row['winter'] != winter:
            row.update(winter=winter, snow_seen=False)
        guarantee = (core and month == months[-1] and day > 20 and not row['snow_seen']
                     and ordinal((data['start_year'], data['start_month'], 1)) <= ordinal((winter, months[0], 1)))
        severity, first, last = snowfall(pool['seed'], key, year, month, (day-1)//10, guarantee)
        # Retain a guaranteed event for its full duration after marking it seen.
        if row['severity'] and tick <= row['ends']:
            severity, began, ends = row['severity'], row['began'], row['ends']
        elif severity and first <= day <= last:
            began, ends = tick-(day-first), tick+(last-day)
        else:
            severity = began = ends = 0
        cold = cold_months[WINTER_MONTHS.index(month)] if month in WINTER_MONTHS else 0
        if month in months:
            roll = draw(pool['seed'], key, year, month, day, 'cold', 100)
            cold = min(3, max(0, cold+(roll >= 80)-(roll < 20)))
        depth = (min(MAX_DEPTH, row['depth']+SNOWFALL[severity]) if severity
                 else max(0, row['depth']-MELT[cold]))
        row.update(severity=severity, began=began, ends=ends, depth=depth, cold=cold)
        if severity:
            row['snow_seen'] = True
        if obs:
            obs('region', dict(tick=tick, year=year, month=month, day=day, region=key, **row))
    if new_climate and (month, day) == (5, 30):
        winter_agriculture.finalize(ledger, pool['options']['agricultural_climate'])
        if obs:
            for region, row in ledger['regions'].items():
                obs('agriculture_year', dict(year=year, region=region, complete=ledger['complete_start'], **row))
    if pool['stage'] >= 4:
        for key, reach in game.catalog.climate.frozen_reaches.items():
            row = pool['ice'][key]
            cold = pool['regions'][reach['freeze_region_id']]['cold']
            index, status = ice_step(row['index'], row['state'], cold, reach['freeze_sensitivity'])
            previous = row['state']
            if previous != status:
                row['changed'] = tick
            row.update(index=index, state=status)
            if obs:
                obs('ice', dict(tick=tick, year=year, month=month, day=day, reach=key, cold=cold,
                                previous=previous, **row))
    pool['tick'] = tick


def report(kind, **row):
    callback = _observer.get()
    if callback:
        callback(kind, row)


def observing():
    return _observer.get() is not None


def detailed():
    return _detailed.get()


def action(game,state,action,source,*,owner,target=None,**details):
    if observing():
        report('action',tick=(state.turn-1)*10+1, year=state.year,month=state.month,day=state.day,
               owner=owner,action=action,source=source,target=target,
               region=game.catalog.climate.cities.get(source,{}).get('climate_region_id'),
               details=details)


def road_weather(region):
    return max(region['severity'], 2 if region['depth'] >= 5 else int(region['depth'] > 0))


def blocked(state, raw):
    if stage(state) < 4:
        return False
    ice = state.extension[POOL]['ice']
    return any(ice.get(reach['reach_id'], {}).get('state') == 3 for reach in raw.get('river_segments', ()))


def movement(state):
    if stage(state)<2:
        return False
    pool=state.extension[POOL]
    return (any(row['severity'] or row['depth'] for row in pool['regions'].values())
            or any(row['state'] for row in pool['ice'].values()))


def view(game, state):
    if not stage(state):
        return {}
    pool = state.extension[POOL]
    from . import logistics, winter_transport, winter_travel, march_supply, winter_strategy
    forecast_enabled=winter_climate.forecast_enabled(state)
    def journey_info(row,reserves=0,*,show_outlook=True):
        supply,quote=row['supply'],row['quote']
        position=winter_travel.work(supply)
        days,_,_,blocked=winter_travel.forecast(game,state,quote,position=position)
        remaining=winter_travel.QUANTA*quote['days']-position
        expected=(date_at(game.catalog.data,(state.turn-1)*10+days) if days is not None else None)
        here=march_supply.current_city(row)
        alternative=None
        if blocked and here and state.cities[quote['path'][-1]].owner==row['owner']:
            alternative=game._travel_path(state,here,quote['path'][-1],row['owner'],'land')
        result=dict(days=days,expected=expected,remaining_work=remaining,blocked=blocked or supply['winter']['blocked'],
                    shortage=march_supply.remaining_requirement(game,state,row,reserves=reserves),
                    current_city=here,next_city=march_supply.next_city(row),
                    alternative=alternative['path'] if alternative else None)
        if forecast_enabled and show_outlook:
            from . import winter_forecast
            result['outlook']=winter_forecast.trip(game,state,quote,position=position)
        return result
    armies={str(row['id']):journey_info(row) for row in state.extension['travel']['marches']
            if row['owner']==state.player and 'winter' in row['supply']}
    cargo={}
    for convoy in state.extension['logistics']['convoys']:
        trip=convoy['journeys'][-1]
        if convoy['owner']==state.player and 'winter' in trip['supply']:
            row=dict(trip,owner=convoy['owner'],officers=convoy['officers'])
            info=journey_info(row,convoy['cargo']['reserves'],show_outlook=False)
            back=None
            info['expected_grain']=None if info['days'] is None else winter_travel.estimate_cargo(
                game,state,trip['quote'],convoy['cargo']['grain'],position=winter_travel.work(trip['supply']),
                remainder=convoy.get('cargo_loss_remainder',0))
            if corrected(state,TRANSPORT):
                status=winter_transport.view(game,state,convoy)
                home=state.cities[convoy['source']]
                target=state.cities[convoy['target']]
                if home.owner==target.owner==convoy['owner'] and target.id!=home.id:
                    route=logistics._safe_quote(game,state,target,home,convoy['route_policy'])
                    status['return_legal']=route is not None
                    if route:
                        status.update(winter_transport.budget(game,state,convoy,return_quote=route[1]))
                        back=route[1]
                info['safety']=status
            if forecast_enabled:
                from . import winter_forecast
                info['outlook']=winter_forecast.trip(game,state,trip['quote'],back,
                                                    position=winter_travel.work(trip['supply']))
            cargo[str(convoy['id'])]=info
    seasonal={}
    if (corrected(state,PREPARATION) and state.player in game.catalog.factions
            and winter_strategy.season_open(state)
            and any(row['owner']==state.player for rows in (state.extension['logistics']['convoys'],
                                                            state.extension['travel']['marches']) for row in rows)):
        from . import faction_economy,winter_strategy
        seasonal=winter_strategy.seasonal_requirements(game,state,state.player,faction_economy.plan(game,state,state.player))
    def regional_view(key,row):
        visible={**row,'weather':NAMES[row['severity']],'road':NAMES[road_weather(row)],
                 'season_chance':winter_climate.snow_probability(state,key,state.month)}
        if 'options' in pool:
            visible.update(depth_limit=winter_climate.snow_depth_limit(state,key),
                           agriculture=winter_agriculture.summary(state,key))
        if forecast_enabled:
            from . import winter_forecast
            visible['snowpack_risk']=winter_forecast.snowpack_risk(state,key)
            visible['agriculture']['risk_multiplier']=winter_agriculture.planning_multiplier(
                state,key,(visible['agriculture']['year'],6))
        return visible
    return dict(stage=pool['stage'], tick=pool['tick'], as_of=date_at(game.catalog.data, pool['tick']),
        work_per_day=winter_travel.QUANTA, reaches=game.catalog.climate.frozen_reaches, marches=armies,convoys=cargo,
        seasonal=seasonal,
        cities=({key: ({**row, 'agriculture_region_id': winter_climate.CITY_AGRICULTURE[key]}
                       if key in winter_climate.CITY_AGRICULTURE else row)
                 for key, row in game.catalog.climate.cities.items()} if 'options' in pool else game.catalog.climate.cities),
        regions={key:regional_view(key,row) for key,row in pool['regions'].items()},
        ice={key: {**row, 'navigation': ICE_NAMES[row['state']], 'speed_percent': SPEED_PERCENT[row['state']]}
             for key, row in pool['ice'].items()})


def validate(game, state):
    pool = state.extension.get(POOL)
    version = state.extension.get(FIELD, 0)
    if type(version) is not int or version not in (0, VERSION, CORRECTED, winter_climate.VERSION):
        raise ValueError('Winter weather rules version')
    if version == 0:
        if POOL in state.extension:
            raise ValueError('Unexpected winter state')
        return
    fields = {'stage','seed','tick','regions','ice'}
    climate = version == winter_climate.VERSION
    if version == CORRECTED or climate:
        fields.add('adjustments')
    if climate:
        fields.update(('options', 'agriculture'))
    if (not isinstance(pool, dict) or set(pool) != fields
            or type(pool['stage']) is not int or not 1 <= pool['stage'] <= 5
            or (version == CORRECTED or climate) and (pool['stage'] != 5 or type(pool['adjustments']) is not int
                                          or not 1 <= pool['adjustments'] <= CORRECTIONS)
            or pool['seed'] != seed_for(state.seed) or type(pool['tick']) is not int
            or pool['tick'] != (state.turn-1)*10 or not isinstance(pool['regions'], dict)
            or set(pool['regions']) != REGIONS.keys() or not isinstance(pool['ice'], dict)
            or set(pool['ice']) != game.catalog.climate.frozen_reaches.keys()):
        raise ValueError('Winter weather state')
    tick = pool['tick']
    regional_fields = {'severity','began','ends','depth','cold','winter','snow_seen'}
    if climate:
        if winter_climate.normalize(pool['options']) != pool['options'] or pool['adjustments'] != CORRECTIONS:
            raise ValueError('Winter climate configuration')
        regional_fields.update(('snow_cover_run', 'fallback_winter'))
        _validate_agriculture_calendar(game, state, pool)
    for key, row in pool['regions'].items():
        limit = winter_climate.snow_depth_limit(state, key) if climate else MAX_DEPTH
        if (not isinstance(row, dict) or set(row) != regional_fields
                or any(type(row[k]) is not int for k in row.keys()-{'snow_seen'})
                or type(row['snow_seen']) is not bool or not 0 <= row['severity'] <= 3
                or not 0 <= row['cold'] <= 3 or not 0 <= row['depth'] <= limit
                or not 0 <= row['winter'] <= state.year
                or climate and (not 0 <= row['fallback_winter'] <= row['winter']
                                or not 0 <= row['snow_cover_run'] <= tick
                                or bool(row['snow_cover_run']) != bool(row['depth']))
                or (not 1 <= row['began'] <= tick <= row['ends'] <= tick+3 if row['severity']
                    else row['began'] != 0 or row['ends'] != 0)):
            raise ValueError('Regional weather state')
    for row in pool['ice'].values():
        if (not isinstance(row, dict) or set(row) != {'index','state','changed'}
                or any(type(n) is not int for n in row.values())
                or not 0 <= row['index'] <= 10_000 or not 0 <= row['state'] <= 3
                or not 0 <= row['changed'] <= tick
                or ice_state(row['index'], row['state']) != row['state']
                or pool['stage'] < 4 and any(row.values())):
            raise ValueError('River ice state')


def _validate_agriculture_calendar(game, state, pool):
    data = game.catalog.data
    start = ordinal((data['start_year'], data['start_month'], 1))
    year, month, day = date_at(data, pool['tick'])
    cycle = year + int(month >= 11)
    beginning = ordinal((cycle - 1, 11, 1))
    closure = ordinal((cycle, 5, 30))
    began = max(1, beginning - start + 1) if pool['tick'] and start <= closure else None
    finalized = bool(began is not None and ordinal((year, month, day)) >= closure)
    settled = sum(1 << index for index, closing_month in enumerate(winter_agriculture.MONTHS)
                  if finalized and state.year == cycle and closing_month <= state.month)
    winter_agriculture.validate(pool, year=cycle, began=began, finalized=finalized,
                                 complete_start=start <= beginning, settled=settled)
