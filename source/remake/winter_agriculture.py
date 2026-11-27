"""Fixed-size observations of the winter and spring before each harvest year."""
from . import winter_climate as climate
from .winter_agriculture_normals import NORMALS

MONTHS = (6, 7, 8, 9)
OBSERVATION_MONTHS = (*climate.WINTER_MONTHS, 4, 5)
DEEP_SNOW = 5
MULTIPLIERS = {'normal': 100, 'moisture': 103, 'mild': 95, 'moderate': 90, 'severe': 85,
               'insufficient': 100, 'observing': 100, 'disabled': 100}
COUNTS = ('winter_snow_days', 'light_snow_days', 'heavy_snow_days', 'blizzard_days',
          'total_snowfall_units', 'max_snow_depth', 'depth_sum', 'winter_snow_cover_days',
          'snow_cover_days', 'deep_snow_days', 'cold_days', 'spring_snow_cover_days',
          'spring_deep_snow_days', 'spring_cold_days', 'final_snow_tick', 'late_snow_days',
          'exceptional_cold_days')
_ROW_FIELDS = {*COUNTS, 'agriculture_status', 'agriculture_multiplier', 'spring_risk_score',
               'moisture_benefit'}


def _row():
    return dict.fromkeys(COUNTS, 0) | dict(agriculture_status='observing', agriculture_multiplier=100,
                                         spring_risk_score=0, moisture_benefit=False)


def begin_day(pool, date, tick, *, complete_start):
    year, month, _ = date
    if month not in OBSERVATION_MONTHS:
        return None
    year += int(month >= 11)
    ledger = pool['agriculture']
    if ledger is None or ledger['year'] != year:
        ledger = dict(year=year, began=tick, complete_start=complete_start, finalized=False,
                      settled=0, regions={key: _row() for key in climate.REGIONS})
        pool['agriculture'] = ledger
    return ledger


def observe(ledger, region, month, tick, weather, *, frost, late, wave):
    """Update one regional row after that day's snow and melt have settled."""
    row = ledger['regions'][region]
    snow, depth, cold = (weather[key] for key in ('severity', 'depth', 'cold'))
    winter = month in climate.WINTER_MONTHS
    risk_window = month in climate.RISK_MONTHS.get(region, ())
    if snow and winter:
        row['winter_snow_days'] += 1
        row[('light_snow_days', 'heavy_snow_days', 'blizzard_days')[snow - 1]] += 1
    row['total_snowfall_units'] += climate.SNOWFALL[snow]
    row['max_snow_depth'] = max(row['max_snow_depth'], depth)
    row['depth_sum'] += depth
    if depth:
        row['snow_cover_days'] += 1
        row['winter_snow_cover_days'] += winter
        row['deep_snow_days'] += depth >= DEEP_SNOW
        row['spring_snow_cover_days'] += risk_window
        row['spring_deep_snow_days'] += risk_window and depth >= DEEP_SNOW
        row['final_snow_tick'] = tick
    row['cold_days'] += cold >= 2
    row['spring_cold_days'] += risk_window and frost
    row['late_snow_days'] += late
    row['exceptional_cold_days'] += wave


def risk_score(row):
    return row['spring_deep_snow_days'] + 2 * row['spring_cold_days']


def _risk_status(score, thresholds):
    for status, boundary in zip(('severe', 'moderate', 'mild'), reversed(thresholds)):
        if score > boundary:
            return status
    return 'normal'


def status(ledger, region):
    if not ledger['complete_start']:
        return 'insufficient'
    if region not in climate.RISK_MONTHS:
        return 'normal'
    row = ledger['regions'][region]
    boundaries, moisture, latest_melt = NORMALS[region]
    classification = _risk_status(risk_score(row), boundaries)
    if (classification == 'normal' and moisture and row['winter_snow_cover_days']
            and moisture[0] <= row['total_snowfall_units'] <= moisture[1]
            and not row['spring_cold_days'] and not row['exceptional_cold_days']
            and row['final_snow_tick'] - ledger['began'] + 1 <= latest_melt):
        return 'moisture'
    return classification


def finalize(ledger, agricultural):
    for region, row in ledger['regions'].items():
        classification = status(ledger, region) if agricultural else 'disabled'
        row.update(spring_risk_score=risk_score(row), agriculture_status=classification,
                   agriculture_multiplier=MULTIPLIERS[classification], moisture_benefit=classification == 'moisture')
    ledger['finalized'] = True


def ledger(state):
    return state.extension.get('winter_weather', {}).get('agriculture')


def mark_income(state):
    current = ledger(state)
    if current is not None and current['year'] == state.year and state.month in MONTHS:
        current['settled'] |= 1 << (state.month - MONTHS[0])


def region_for(game, city_id):
    return climate.CITY_AGRICULTURE.get(city_id) or game.catalog.climate.cities[city_id]['climate_region_id']


def multiplier(state, region, date):
    if date[1] not in MONTHS or not climate.options(state).get('agricultural_climate'):
        return 100
    current = ledger(state)
    if current is None or not current['finalized'] or current['year'] != date[0]:
        return 100
    return current['regions'][region]['agriculture_multiplier']


def planning_enabled(state):
    flags = climate.options(state)
    return flags.get('agricultural_climate') and flags.get('agricultural_risk_planning')


def planning_multiplier(state, region, date):
    """A risk scenario based on already observed spring days and fixed normals."""
    if date[1] not in MONTHS or not planning_enabled(state):
        return 100
    current = ledger(state)
    if (current is None or current['year'] != date[0] or current['finalized']
            or not current['complete_start'] or region not in climate.RISK_MONTHS):
        return 100
    return MULTIPLIERS[_risk_status(risk_score(current['regions'][region]), NORMALS[region][0])]


def summary(state, region):
    current = ledger(state)
    if current is None:
        return dict(year=state.year, status='insufficient', multiplier=100, finalized=False,
                    winter_observed=False, spring_observed=False)
    row = current['regions'][region]
    return dict(year=current['year'], status=(row['agriculture_status'] if current['complete_start'] else 'insufficient'),
                multiplier=row['agriculture_multiplier'], finalized=current['finalized'],
                winter_observed=current['complete_start'] and 4 <= state.month <= 10,
                spring_observed=current['complete_start'] and current['finalized'])


def validate(pool, *, year, began, finalized, complete_start, settled):
    current = pool['agriculture']
    if began is None:
        if current is not None:
            raise ValueError('Unexpected agricultural observation')
        return
    if (not isinstance(current, dict) or set(current) != {'year', 'began', 'complete_start', 'finalized', 'settled', 'regions'}
            or type(current['year']) is not int or current['year'] != year
            or type(current['began']) is not int or current['began'] != began
            or current['complete_start'] is not complete_start or current['finalized'] is not finalized
            or type(current['settled']) is not int or current['settled'] != settled
            or not isinstance(current['regions'], dict) or set(current['regions']) != climate.REGIONS.keys()):
        raise ValueError('Agricultural observation calendar')
    obs_days = min(pool['tick'] - began + 1, 210)
    for region, row in current['regions'].items():
        if (not isinstance(row, dict) or set(row) != _ROW_FIELDS
                or any(type(row[key]) is not int or row[key] < 0 for key in COUNTS)
                or row['winter_snow_days'] != sum(row[key] for key in ('light_snow_days', 'heavy_snow_days', 'blizzard_days'))
                or row['winter_snow_days'] > min(150, obs_days)
                or row['spring_deep_snow_days'] > row['spring_snow_cover_days']
                or row['spring_snow_cover_days'] > row['snow_cover_days']
                or row['winter_snow_cover_days'] > row['snow_cover_days'] or row['deep_snow_days'] > row['snow_cover_days']
                or row['snow_cover_days'] > obs_days or row['cold_days'] > obs_days or row['spring_cold_days'] > obs_days
                or row['late_snow_days'] > obs_days or row['exceptional_cold_days'] > 4
                or row['max_snow_depth'] > 50 or row['depth_sum'] > obs_days * row['max_snow_depth']
                or row['total_snowfall_units'] > 6 * obs_days
                or (not began <= row['final_snow_tick'] <= min(pool['tick'], began + 209) if row['snow_cover_days']
                    else row['final_snow_tick'] != 0)):
            raise ValueError('Regional agricultural observation')
        classification = ('observing' if not finalized else
                          status(current, region) if pool['options']['agricultural_climate'] else 'disabled')
        if (row['agriculture_status'] != classification or type(row['agriculture_multiplier']) is not int
                or row['agriculture_multiplier'] != MULTIPLIERS[classification]
                or type(row['spring_risk_score']) is not int
                or row['spring_risk_score'] != (risk_score(row) if finalized else 0)
                or row['moisture_benefit'] is not (classification == 'moisture')):
            raise ValueError('Agricultural result')
