"""Provide batched native leg results only during the original save validator."""
from collections import Counter
from contextvars import ContextVar
from functools import wraps
from unittest.mock import patch


def collect_checks(data, state):
    from remake import logistics
    from remake.route_network import variants

    travel = state.extension['travel']['marches']
    convoys = state.extension['logistics']['convoys']
    if (not isinstance(travel, list) or len(travel) > 1000
            or not isinstance(convoys, list) or len(convoys) > len(state.cities)):
        raise ValueError('Unexpected travel bounds')
    if not travel and not convoys:
        return []

    routes = data['travel_routes']
    exploration = data.get('exploration_routes', [])
    current = {route['id']: route for route in variants(routes)}
    current.update((route['id'], route) for route in exploration)
    historical = {route['id']: route for route in variants(routes + exploration)}
    checks = {}

    def add(journey, lookup):
        quote = journey['quote']
        path, legs = quote['path'], quote['routes']
        month = journey['departure_month']
        if (not isinstance(path, list) or not isinstance(legs, list)
                or len(path) != len(legs) + 1 or len(path) > len(state.cities)
                or type(month) is not int or not 1 <= month <= 12):
            raise ValueError('Unexpected saved route shape')
        for source, target, leg in zip(path, path[1:], legs):
            if type(source) is not str or type(target) is not str:
                raise ValueError('Unexpected saved route endpoint')
            route = lookup[leg['id']]
            checks.setdefault((id(route), source, target, month), route)
            if len(checks) > 32768:
                raise ValueError('Too many restore checks for one batch')

    for row in travel:
        add(row, current)
        history = row['history']
        if not isinstance(history, list) or len(history) > 16:
            raise ValueError('Unexpected march history')
        for old in history:
            add(old, historical)
    for convoy in convoys:
        journeys = convoy['journeys']
        if not isinstance(journeys, list) or len(journeys) > logistics.RULES['max_journeys']:
            raise ValueError('Unexpected convoy history')
        for journey in journeys:
            add(journey, historical)
    return list(checks.items())


class RestoreBatch:
    def __init__(self):
        self.restoring = ContextVar('restore_route_game', default=None)
        self.results = ContextVar('restore_route_results', default=None)
        self.stats = Counter()

    def prepare(self, game, state):
        from remake import march_core

        data = game.catalog.data
        entries = collect_checks(data, state)
        if not entries:
            return None
        routes, route_indices, requests = [], {}, []
        for (identity, source, target, month), route in entries:
            if identity not in route_indices:
                route_indices[identity] = len(routes)
                routes.append(route)
            requests.append((route_indices[identity], source, target, month))
        config = {key: data[key] for key in ('travel_rules', 'travel_hazards', 'city_coordinates') if key in data}
        request = dict(op='restore_route_legs', data=config, routes=routes, checks=requests)
        with march_core._lock:
            legs = march_core._call(march_core._load(), request)
        if (not isinstance(legs, list) or len(legs) != len(entries)
                or any(leg is not None and not isinstance(leg, dict) for leg in legs)):
            raise ValueError('Invalid native restore batch reply')
        allowed, evaluated = {}, {}
        for (key, _route), leg in zip(entries, legs):
            allowed[key[:3]] = leg is not None
            evaluated[key] = leg
        self.stats.update(batches=1, checks=len(entries))
        return data, allowed, evaluated

    def install(self, patches, campaign):
        from remake import logistics, march_core, route_hazards

        original_load = campaign.load_save
        original_validate = campaign.validate
        original_allowed = route_hazards.route_allowed
        original_evaluate = route_hazards.evaluate_leg

        @wraps(original_load)
        def load(game, *args, **kwargs):
            token = self.restoring.set(game)
            try:
                return original_load(game, *args, **kwargs)
            finally:
                self.restoring.reset(token)

        @wraps(original_validate)
        def validate(game, state):
            if self.restoring.get() is not game or not march_core.enabled():
                return original_validate(game, state)
            try:
                results = self.prepare(game, state)
            except (ValueError, KeyError, TypeError, AttributeError, RecursionError, march_core.CoreUnavailable):
                # The unmodified validator still owns malformed input and errors.
                self.stats['fallbacks'] += 1
                return original_validate(game, state)
            token = self.results.set(results)
            try:
                return original_validate(game, state)
            finally:
                self.results.reset(token)

        def allowed(data, route, source, target):
            results = self.results.get()
            if results is not None and results[0] is data and type(source) is str and type(target) is str:
                value = results[1].get((id(route), source, target))
                if value is not None:
                    self.stats['direction_results'] += 1
                    return value
            return original_allowed(data, route, source, target)

        def evaluate(data, route, source, target, month):
            results = self.results.get()
            if (results is not None and results[0] is data and type(source) is str
                    and type(target) is str and type(month) is int):
                value = results[2].get((id(route), source, target, month))
                if value is not None:
                    self.stats['leg_results'] += 1
                    return value
            return original_evaluate(data, route, source, target, month)

        patches.enter_context(patch.object(campaign, 'load_save', load))
        patches.enter_context(patch.object(campaign, 'validate', validate))
        for module in (route_hazards, logistics):
            patches.enter_context(patch.object(module, 'route_allowed', allowed))
            patches.enter_context(patch.object(module, 'evaluate_leg', evaluate))
