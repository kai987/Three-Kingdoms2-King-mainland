"""Precompute native route answers for the existing save validators."""
from contextlib import contextmanager
from contextvars import ContextVar

from . import march_core, route_hazards
from .route_network import variants


_active = ContextVar('restore_route_checks', default=None)
_MAX_CHECKS = 32768


def _collect(data, state):
    from .logistics import RULES

    marches = state.extension['travel']['marches']
    convoys = state.extension['logistics']['convoys']
    if (not isinstance(marches, list) or len(marches) > 1000
            or not isinstance(convoys, list) or len(convoys) > len(state.cities)):
        return {}
    if not marches and not convoys:
        return {}

    routes = data['travel_routes']
    exploration = data.get('exploration_routes', [])
    current = {route['id']: route for route in variants(routes)}
    current.update((route['id'], route) for route in exploration)
    historical = {route['id']: route for route in variants(routes + exploration)}
    checks = {}

    def collect_journey(journey, lookup):
        quote = journey['quote']
        path, legs = quote['path'], quote['routes']
        month = journey['departure_month']
        if (not isinstance(path, list) or not isinstance(legs, list)
                or len(path) != len(legs) + 1 or len(path) > len(state.cities)
                or type(month) is not int or not 1 <= month <= 12):
            raise ValueError('Invalid route batch input')
        for source, target, saved_leg in zip(path, path[1:], legs):
            if type(source) is not str or type(target) is not str:
                raise ValueError('Invalid route batch endpoint')
            route = lookup[saved_leg['id']]
            checks.setdefault((id(route), source, target, month), route)
            if len(checks) > _MAX_CHECKS:
                raise ValueError('Too many route checks for one batch')

    for march in marches:
        collect_journey(march, current)
        history = march['history']
        if not isinstance(history, list) or len(history) > 16:
            return {}
        for journey in history:
            collect_journey(journey, historical)
    for convoy in convoys:
        journeys = convoy['journeys']
        if not isinstance(journeys, list) or len(journeys) > RULES['max_journeys']:
            return {}
        for journey in journeys:
            collect_journey(journey, historical)
    return checks


class _RouteChecks:
    def __init__(self, data, checks, legs):
        self.data = data
        self.directions = {key[:3]: leg is not None for key, leg in zip(checks, legs)}
        self.legs = dict(zip(checks, legs))

    def allowed(self, data, route, source, target):
        if data is self.data and type(source) is str and type(target) is str:
            result = self.directions.get((id(route), source, target))
            if result is not None:
                return result
        return route_hazards.route_allowed(data, route, source, target)

    def evaluate(self, data, route, source, target, month):
        if (data is self.data and type(source) is str and type(target) is str
                and type(month) is int):
            result = self.legs.get((id(route), source, target, month))
            if result is not None:
                return result
        return route_hazards.evaluate_leg(data, route, source, target, month)


def _prepare(data, state):
    if not march_core.enabled():
        return None
    checks = _collect(data, state)
    if not checks:
        return None

    routes, indices, requests = [], {}, []
    for (identity, source, target, month), route in checks.items():
        if identity not in indices:
            indices[identity] = len(routes)
            routes.append(route)
        requests.append((indices[identity], source, target, month))
    legs = march_core.invoke('restore_route_legs', data=data, routes=routes, checks=requests)
    if (not isinstance(legs, list) or len(legs) != len(checks)
            or any(leg is not None and not isinstance(leg, dict) for leg in legs)):
        raise ValueError('Invalid native route batch reply')
    return _RouteChecks(data, checks, legs)


@contextmanager
def validating_load(data, state):
    try:
        checks = _prepare(data, state)
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError, RecursionError,
            march_core.CoreUnavailable):
        # Malformed saves and older native libraries still go through every
        # original validation and retain the original error behavior.
        checks = None
    token = _active.set(checks)
    try:
        yield
    finally:
        _active.reset(token)


def validators(data):
    checks = _active.get()
    if checks is not None and checks.data is data:
        return checks.allowed, checks.evaluate
    return route_hazards.route_allowed, route_hazards.evaluate_leg
