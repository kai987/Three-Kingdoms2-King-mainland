"""Versioned regional climate parameters and read-only seasonal outlooks."""
from functools import lru_cache

from .climate_regions import REGIONS, WINTER_MONTHS

VERSION = 23
OPTIONS = 'weather_options'
DEFAULTS = {
    'monthly_snow_probability': True,
    'regional_snow_severity': True,
    'regional_snow_depth': True,
    'revised_cold_profile': True,
    'exceptional_cold_wave': False,
    'spring_cold_exposure': True,
    'agricultural_climate': True,
    'agricultural_risk_planning': True,
}
# Monthly marks are probabilities per ten-day turn, in November–March order.
SNOW_PROBABILITIES = dict(zip(REGIONS, (
    (70, 85, 90, 85, 65), (45, 65, 75, 65, 40), (30, 45, 50, 45, 30),
    (50, 70, 80, 70, 50), (15, 40, 55, 40, 15), (5, 25, 40, 30, 5),
    (0, 15, 25, 15, 0), (0, 0, 0, 0, 0), (0, 10, 20, 10, 0),
    (0, 0, 0, 0, 0), (0, 0, 0, 0, 0),
), strict=True))
LEGACY_SEVERITY = (70, 25, 5)
SEVERITY = {
    'liaodong': (50, 40, 10), 'northern_frontier': (60, 30, 10),
    'northwest': (75, 20, 5), 'qinling_highlands': (50, 40, 10),
    'north_china': (65, 30, 5), 'central_plains': (75, 22, 3),
    'huai_north_jing': (85, 13, 2), 'southern_highlands': (80, 18, 2),
}
DEPTH = {
    'liaodong': 50, 'northern_frontier': 40, 'northwest': 30,
    'qinling_highlands': 45, 'north_china': 30, 'central_plains': 25,
    'huai_north_jing': 15, 'southern_highlands': 20, 'southern_basins': 10,
    'lingnan': 0, 'tropical_islands': 0,
}
# Spring episodes are distinct from ordinary winter snow draws. Values are
# candidate probabilities per turn, in February–May order.
SPRING_COLD = {
    'liaodong': (0, 0, 18, 8), 'northern_frontier': (0, 18, 10, 4),
    'northwest': (0, 14, 8, 3), 'qinling_highlands': (0, 20, 12, 5),
    'north_china': (14, 10, 5, 0), 'central_plains': (12, 9, 4, 0),
    'huai_north_jing': (9, 5, 0, 0), 'southern_highlands': (10, 7, 3, 0),
    'southern_basins': (0, 0, 0, 0),
}
RISK_MONTHS = {
    'liaodong': (4, 5), 'northern_frontier': (3, 4, 5), 'northwest': (3, 4, 5),
    'qinling_highlands': (3, 4, 5), 'north_china': (2, 3, 4),
    'central_plains': (2, 3, 4), 'huai_north_jing': (2, 3),
    'southern_highlands': (2, 3, 4), 'southern_basins': (2, 3, 4),
}
# The two boundary towns use nearby crop-risk normals. Physical roads still
# sample the original regional layer, and both towns share regional events.
CITY_AGRICULTURE = {'shuofang': 'northwest', 'daifang': 'north_china'}
WAVE_REGIONS = {'huai_north_jing': 1, 'southern_basins': 2, 'southern_highlands': 1}
WAVE_PROBABILITY = 5
LATE_SNOW = {'liaodong': 10, 'northern_frontier': 5, 'qinling_highlands': 10}
_MONTH_INDEX = {month: index for index, month in enumerate(WINTER_MONTHS)}
DURATION = ((0, 0), (1, 3), (2, 4), (1, 3))
SNOWFALL = (0, 1, 3, 6)
MELT = (4, 2, 1, 0)
LEGACY_DEPTH = 30


def enabled(state):
    return state.extension.get('weather_rules_version') == VERSION


def options(state):
    return state.extension.get('winter_weather', {}).get('options', {})


def normalize(raw):
    if not isinstance(raw, dict) or set(raw) - DEFAULTS.keys() or any(type(value) is not bool for value in raw.values()):
        raise ValueError('Winter climate options')
    return DEFAULTS | raw


def flags(*enabled_names):
    """Explicit opt-in masks for paired experiments."""
    return normalize(dict.fromkeys(DEFAULTS, False) | dict.fromkeys(enabled_names, True))


def snow_probability(state, region, month):
    if options(state).get('monthly_snow_probability'):
        index = _MONTH_INDEX.get(month)
        return SNOW_PROBABILITIES[region][index] if index is not None else 0
    months, chance, _, _ = REGIONS[region]
    return chance if month in months else 0


def snowfall_months(state, region):
    if options(state).get('monthly_snow_probability'):
        return tuple(month for month, chance in zip(WINTER_MONTHS, SNOW_PROBABILITIES[region]) if chance)
    return REGIONS[region][0]


def severity_distribution(state, region):
    return SEVERITY.get(region, LEGACY_SEVERITY) if options(state).get('regional_snow_severity') else LEGACY_SEVERITY


def snow_depth_limit(state, region):
    flags = options(state)
    if not flags.get('regional_snow_depth'):
        return LEGACY_DEPTH
    if region == 'southern_basins' and not flags.get('exceptional_cold_wave'):
        return 0
    return DEPTH[region]


def cold_normal(state, region, month):
    index = _MONTH_INDEX.get(month)
    if index is None:
        return 0
    if region == 'liaodong' and options(state).get('revised_cold_profile'):
        return (2, 3, 3, 3, 2)[index]
    return REGIONS[region][2][index]


def spring_probability(state, region, month):
    if not options(state).get('spring_cold_exposure') or not 2 <= month <= 5:
        return 0
    return SPRING_COLD.get(region, (0, 0, 0, 0))[month - 2]


@lru_cache(maxsize=512)
def _exposure(chance, weights, cold, depth_limit, late_chance, wave_chance):
    """Expected daily shares in hundredths of a percent, using only public normals."""
    events = [chance * weight * sum(DURATION[severity]) // 20
              for severity, weight in enumerate(weights, 1)]
    events[0] += late_chance * 20
    events[1] += wave_chance
    melt = max(1, MELT[cold])
    tails = [max(0, min(10, min(depth_limit, (sum(DURATION[i]) * SNOWFALL[i]) // 2) // melt))
             for i in (1, 2, 3)]
    event_days = sum(events)
    snowpack = min(10_000 - event_days, chance * sum(w*t for w, t in zip(weights, tails)) // 10)
    return tuple((i, i, share) for i, share in enumerate(events, 1) if share) + (
        ((0, 2 if depth_limit >= 5 and cold >= 2 else 1, snowpack),) if snowpack else ())


def seasonal_exposure(state, region, month, *, pressure=False):
    """Public weather exposure. Draws for specific future days are never used."""
    flags = options(state)
    chance = snow_probability(state, region, month)
    # W1 changes ordinary snowfall chances, with the same outlook policy as 221.
    if not any(flags.get(key) for key in ('regional_snow_depth', 'regional_snow_severity',
                                          'revised_cold_profile', 'spring_cold_exposure', 'exceptional_cold_wave')):
        if not chance:
            return ()
        return ((2, 2, 10_000),) if pressure else ((1, 1, chance * 100),)
    late_chance = (spring_probability(state, region, month) * LATE_SNOW.get(region, 0) // 100
                   if month == 4 else 0)
    # A 5% chance of a three-day wave across 90 days. One regional wave can
    # overlap regular snow, so this small public approximation is not an ETA.
    wave_chance = (WAVE_PROBABILITY * 100 * 3 // 90
                   if flags.get('exceptional_cold_wave') and region in WAVE_REGIONS and month in (12, 1, 2)
                   else 0)
    if pressure and (chance or late_chance or wave_chance):
        return ((2, 2, 10_000),)
    return _exposure(chance, severity_distribution(state, region), cold_normal(state, region, month),
                     snow_depth_limit(state, region), late_chance, wave_chance)
