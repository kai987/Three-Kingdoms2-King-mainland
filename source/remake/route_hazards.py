"""Pure route-time and troop-loss arithmetic for explicit hazard catalogs.

These are the user's game rules, not historical casualty measurements or a
weather forecast.  Quotes never draw random numbers or mutate raw route data.
The campaign runtime owns random storm severity and exactly-once settlement.
"""
from copy import deepcopy
from math import ceil, cos, radians


def _json_numbers(value):
    """Clone JSON data using the same integral-number spelling as browsers.

    Python emits ``50.0`` while JSON.stringify emits ``50``. Keep newly
    quoted hazard data stable across a browser save download without changing
    the checksum format or any released catalog's raw route representation.
    """
    if isinstance(value, dict):
        return {key: _json_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_numbers(item) for item in value]
    if type(value) is float and value.is_integer():
        return int(value)
    return value


def _pair(route, source, target):
    return source != target and {source, target} == {route['from'], route['to']}


def route_allowed(data, route, source, target):
    """Whether this immutable leg can be traversed in the requested direction."""
    if not _pair(route, source, target):
        return False
    policy = data.get('travel_hazards')
    if not policy:
        return True
    yinping = policy.get('yinping', {})
    start, end = yinping.get('from', 'yinping'), yinping.get('to', 'shujun')
    if route.get('mode') == 'land' and {source, target} == {start, end}:
        return source == start and target == end
    return True


def _fixed_hazard(kind, label, numerator, denominator, *, month, season=None):
    percent = _json_numbers(100 * (denominator - numerator) / denominator)
    return dict(kind=kind, label=label, season=season, wind=None,
                month=month, survival_numerator=numerator,
                survival_denominator=denominator, loss_percent=percent,
                loss_percent_min=percent, loss_percent_max=percent)


def _monsoon(policy, month):
    rule = policy.get('monsoon', {})
    if month in rule.get('southwest_months', [5, 6, 7, 8, 9]):
        # Southwest monsoon means wind FROM southwest, travelling northeast.
        return rule, 'southwest_monsoon', (1, 1), '西南季风'
    if month in rule.get('northeast_months', [10, 11, 12, 1, 2, 3]):
        return rule, 'northeast_monsoon', (-1, -1), '东北季风'
    return rule, None, None, None


def evaluate_leg(data, route, source, target, departure_month):
    """Return a directional, deterministic time quote from an immutable leg.

    Hazard catalogs get ``base_days`` (this route's plain-road time) and a
    ``hazard`` description. Legacy catalogs return an unchanged deep copy,
    retaining released quote/save equality. A forbidden directed leg is an
    error rather than a quote that may accidentally be enqueued.

    Land special times multiply the integer plain-road baseline, so a10-day
    plain leg is20 days in the dry Ziwu season and40 in its rainy season.
    Sea wind changes sailing speed only; land access and embark time remain.
    All sea legs of a single march are merged into one storm by the runtime.
    """
    if type(departure_month) is not int or not 1 <= departure_month <= 12:
        raise ValueError('Departure month must be an integer from1 to12')
    if not route_allowed(data, route, source, target):
        raise ValueError('Route does not permit this direction')
    leg = deepcopy(route)
    policy = data.get('travel_hazards')
    if not policy:
        return leg
    leg = _json_numbers(leg)
    leg.update({'from': source, 'to': target})
    plain_speed = data['travel_rules']['speeds']['plain']
    leg['base_days'] = max(1, ceil(route['distance_km'] / plain_speed))
    leg['hazard'] = None
    if route['mode'] == 'land':
        yinping = policy.get('yinping', {})
        if (source, target) == (yinping.get('from', 'yinping'), yinping.get('to', 'shujun')):
            numerator = yinping.get('survival_numerator', 1)
            denominator = yinping.get('survival_denominator', 3)
            # Validate even when the army happens to have zero soldiers.
            allocate_survivors([], numerator, denominator)
            leg['days'] = leg['base_days'] * yinping.get('time_multiplier', 2)
            leg['hazard'] = _fixed_hazard('yinping', '阴平险道：全军最终余三分之一',
                numerator, denominator, month=departure_month)
            return leg
        ziwu = policy.get('ziwu', {})
        endpoints = {ziwu.get('from', 'hanzhong'), ziwu.get('to', 'jingzhao')}
        # The explicit marker disambiguates future alternate Hanzhong-Changan
        # roads; current hazard catalogs contain only the new Ziwu connection.
        if {source, target} == endpoints and route.get('special', 'ziwu') == 'ziwu':
            rainy = departure_month in ziwu.get('rain_months', [7, 8, 9])
            loss = ziwu.get('rain_loss_percent', 50) if rainy else ziwu.get('dry_loss_percent', 20)
            allocate_survivors([], 100 - loss, 100)
            multiplier = ziwu.get('rain_time_multiplier', 4) if rainy else ziwu.get('dry_time_multiplier', 2)
            leg['days'] = leg['base_days'] * multiplier
            leg['hazard'] = _fixed_hazard('ziwu_rain' if rainy else 'ziwu_dry',
                '子午谷暴雨：减员50%' if rainy else '子午谷险道：减员20%',
                100 - loss, 100, month=departure_month,
                season='rainy' if rainy else 'dry')
        return leg
    if route['mode'] != 'sea':
        return leg
    monsoon, season, vector, season_label = _monsoon(policy, departure_month)
    if season is None:
        # April transition preserves the existing calm-sea sailing estimate.
        return leg
    (lon1, lat1), (lon2, lat2) = (data['city_coordinates'][key] for key in (source, target))
    east = (lon2 - lon1) * cos(radians((lat1 + lat2) / 2))
    north = lat2 - lat1
    dot = east * vector[0] + north * vector[1]
    # Perpendicular/zero-length edge goes into the slower case; this is a
    # two-state game rule rather than an unimplemented crosswind forecast.
    following = dot > 0
    speed = (plain_speed * monsoon.get('tailwind_speed_multiplier', 4) if following
             else plain_speed / monsoon.get('headwind_speed_divisor', 4))
    access_days = ceil(route.get('land_km', 0) / plain_speed)
    water_days = ceil(route.get('sea_km', route['distance_km']) / speed)
    embark_days = data['travel_rules'].get('embark_days', 2)
    leg['days'] = max(1, access_days + water_days + embark_days)
    low, high = monsoon.get('storm_loss_percent', [80, 90])
    if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 100:
        raise ValueError('Invalid storm loss range')
    leg['hazard'] = dict(kind='monsoon_storm',
        label=f'{season_label}{"顺风" if following else "逆风"}及暴风雨：全程减员{low}–{high}%',
        season=season, wind='tailwind' if following else 'headwind', month=departure_month,
        loss_percent_min=low, loss_percent_max=high, loss_percent=None,
        survival_numerator=None, survival_denominator=None,
        speed_km_per_day=_json_numbers(speed))
    return leg


def allocate_survivors(troops, numerator, denominator):
    """Distribute floor(total*n/d) survivors proportionally, without new men.

    Remainders use their input order as the stable tie break. This conserves
    the whole army's required integer total rather than losing up to one extra
    man per officer. It does not remove officers or mutate the supplied list.
    """
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0 or not 0 <= numerator <= denominator:
        raise ValueError('Survival ratio must be integers with0<=n<=d andd>0')
    values = list(troops)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError('Troop counts must be nonnegative integers')
    result = [value * numerator // denominator for value in values]
    missing = sum(values) * numerator // denominator - sum(result)
    order = sorted(range(len(values)), key=lambda i: (-(values[i] * numerator % denominator), i))
    for index in order[:missing]:
        result[index] += 1
    return result


# Keep the released reference available for fallback and differential replay.
_python_route_allowed = route_allowed
_python_evaluate_leg = evaluate_leg
_python_allocate_survivors = allocate_survivors


def route_allowed(data, route, source, target):
    from .march_core import enabled, invoke
    if enabled():
        return invoke('allowed', data=data, route=route, source=source, target=target)
    return _python_route_allowed(data, route, source, target)


def evaluate_leg(data, route, source, target, departure_month):
    from .march_core import enabled, invoke
    if enabled():
        return invoke('evaluate_leg', data=data, route=route, source=source,
                      target=target, month=departure_month)
    return _python_evaluate_leg(data, route, source, target, departure_month)


def allocate_survivors(troops, numerator, denominator):
    from .march_core import enabled, invoke
    if enabled():
        return invoke('allocate', troops=list(troops), numerator=numerator,
                      denominator=denominator)
    return _python_allocate_survivors(troops, numerator, denominator)
