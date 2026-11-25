"""Independent regional winter weather on the campaign's 30-day calendar."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from hashlib import sha256

from .climate_regions import REGIONS, WINTER_MONTHS

FIELD = 'weather_rules_version'
POOL = 'winter_weather'
VERSION = 22
NAMES = ('clear', 'light_snow', 'heavy_snow', 'blizzard')
ICE_NAMES = ('open', 'floating_ice', 'partial_ice', 'frozen')
DURATION = ((0, 0), (1, 3), (2, 4), (1, 3))
SNOWFALL = (0, 1, 3, 6)
MELT = (4, 2, 1, 0)
MAX_DEPTH = 30
BASE_ICE = (-6, -2, 3, 5)
SPEED_PERCENT = (100, 75, 50, 0)
TIME_PERCENT = (100, 115, 140, 200)
WARMTH = (100, 105, 115, 130)
SURCHARGE = (100, 120, 150, 200)
CARGO = (100, 120, 150, 200)
_stage = ContextVar('winter_experiment_stage', default=0)
_observer = ContextVar('winter_readonly_observer', default=None)


@contextmanager
def experiment(stage, *, observe=None):
    if type(stage) is not int or not 0 <= stage <= 5:
        raise ValueError('Winter experiment stage')
    stage_token, observer_token = _stage.set(stage), _observer.set(observe)
    try:
        yield
    finally:
        _observer.reset(observer_token)
        _stage.reset(stage_token)


def stage(state):
    return getattr(state, 'extension', {}).get(POOL, {}).get('stage', 0)


def initialize(game, state, requested=None):
    if requested is not None and (type(requested) is not int or requested not in (0, VERSION)):
        raise ValueError('Winter weather rules version')
    selected = _stage.get() if requested is None else (5 if requested == VERSION else 0)
    if selected:
        state.extension[FIELD] = VERSION
        state.extension[POOL] = dict(stage=selected, seed=seed_for(state.seed), tick=0,
            regions={key: dict(severity=0, began=0, ends=0, depth=0, cold=0,
                               winter=0, snow_seen=False) for key in REGIONS},
            ice={key: dict(index=0, state=0, changed=0) for key in game.catalog.climate.frozen_reaches})
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
    roll = draw(seed, region, year, month, ten_days, 'snow', 100)
    if roll >= chance and not guarantee:
        return 0, 0, 0
    strength = draw(seed, region, year, month, ten_days, 'severity', 100)
    severity = (1 if strength < 70 else 2 if strength < 95 else 3) if roll < chance else 1
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
    for key, row in pool['regions'].items():
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
    from . import winter_travel, march_supply
    def journey_info(row,reserves=0):
        supply,quote=row['supply'],row['quote']
        position=winter_travel.work(supply)
        days,_,_,blocked=winter_travel.forecast(game,state,quote,position=position)
        remaining=winter_travel.QUANTA*quote['days']-position
        expected=(date_at(game.catalog.data,(state.turn-1)*10+days) if days is not None else None)
        here=march_supply.current_city(row)
        alternative=None
        if blocked and here and state.cities[quote['path'][-1]].owner==row['owner']:
            alternative=game._travel_path(state,here,quote['path'][-1],row['owner'],'land')
        return dict(days=days,expected=expected,remaining_work=remaining,blocked=blocked or supply['winter']['blocked'],
                    shortage=march_supply.remaining_requirement(game,state,row,reserves=reserves),
                    current_city=here,next_city=march_supply.next_city(row),
                    alternative=alternative['path'] if alternative else None)
    armies={str(row['id']):journey_info(row) for row in state.extension['travel']['marches']
            if row['owner']==state.player and 'winter' in row['supply']}
    cargo={}
    for convoy in state.extension['logistics']['convoys']:
        trip=convoy['journeys'][-1]
        if convoy['owner']==state.player and 'winter' in trip['supply']:
            row=dict(trip,owner=convoy['owner'],officers=convoy['officers'])
            info=journey_info(row,convoy['cargo']['reserves'])
            info['expected_grain']=None if info['days'] is None else winter_travel.estimate_cargo(
                game,state,trip['quote'],convoy['cargo']['grain'],position=winter_travel.work(trip['supply']),
                remainder=convoy.get('cargo_loss_remainder',0))
            cargo[str(convoy['id'])]=info
    return dict(stage=pool['stage'], tick=pool['tick'], as_of=date_at(game.catalog.data, pool['tick']),
        work_per_day=winter_travel.QUANTA, reaches=game.catalog.climate.frozen_reaches, marches=armies,convoys=cargo,
        cities=game.catalog.climate.cities,
        regions={key: {**row, 'weather': NAMES[row['severity']], 'road': NAMES[road_weather(row)],
                       'season_chance': REGIONS[key][1] if state.month in REGIONS[key][0] else 0}
                 for key, row in pool['regions'].items()},
        ice={key: {**row, 'navigation': ICE_NAMES[row['state']], 'speed_percent': SPEED_PERCENT[row['state']]}
             for key, row in pool['ice'].items()})


def validate(game, state):
    pool = state.extension.get(POOL)
    version = state.extension.get(FIELD, 0)
    if type(version) is not int or version not in (0, VERSION):
        raise ValueError('Winter weather rules version')
    if version == 0:
        if POOL in state.extension:
            raise ValueError('Unexpected winter state')
        return
    if (not isinstance(pool, dict) or set(pool) != {'stage','seed','tick','regions','ice'}
            or type(pool['stage']) is not int or not 1 <= pool['stage'] <= 5
            or pool['seed'] != seed_for(state.seed) or type(pool['tick']) is not int
            or pool['tick'] != (state.turn-1)*10 or not isinstance(pool['regions'], dict)
            or set(pool['regions']) != REGIONS.keys() or not isinstance(pool['ice'], dict)
            or set(pool['ice']) != game.catalog.climate.frozen_reaches.keys()):
        raise ValueError('Winter weather state')
    tick = pool['tick']
    for row in pool['regions'].values():
        if (not isinstance(row, dict) or set(row) != {'severity','began','ends','depth','cold','winter','snow_seen'}
                or any(type(row[k]) is not int for k in row.keys()-{'snow_seen'})
                or type(row['snow_seen']) is not bool or not 0 <= row['severity'] <= 3
                or not 0 <= row['cold'] <= 3 or not 0 <= row['depth'] <= MAX_DEPTH
                or not 0 <= row['winter'] <= state.year
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
