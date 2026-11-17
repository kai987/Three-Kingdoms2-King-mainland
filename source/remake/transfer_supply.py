"""Quote the shortest officer transfer that current city stocks can supply."""
from heapq import heappop, heappush
from itertools import count
from math import gcd

from .historical_campaigns import transit_allowed
from .march_supply import denominator, OFFICER_UNITS, estimate
from .route_hazards import evaluate_leg, route_allowed


def _remaining(state, owner, city, balance, units, days):
    """Carry fractional meal credit across our resupply checkpoints."""
    remaining = balance - units * days
    if remaining >= 0 and state.cities[city].owner == owner:
        return state.cities[city].grain * denominator() + remaining % denominator()
    return remaining


def _routes(game, state, owner, mode):
    allowed = {key for key, city in state.cities.items()
               if transit_allowed(state, owner, city.owner)}
    outbound = {key: [] for key in allowed}
    incoming = {key: [] for key in allowed}
    data = game.catalog.data
    for route in game._known_routes(state):
        start, end = route['from'], route['to']
        if start not in allowed or end not in allowed or mode == 'land' and route['mode'] != 'land':
            continue
        for source, target in ((start, end), (end, start)):
            if route_allowed(data, route, source, target):
                leg = evaluate_leg(data, route, source, target, state.month)
                outbound[source].append(leg)
                incoming[target].append(leg)
    return outbound, incoming


def _next_depot_days(state, owner, target, units, incoming):
    """Prune dead ends using the largest possible fractional ration credit."""
    queue = [(0, target)]
    max_credit = denominator() - gcd(denominator(), units)
    distance = {}
    while queue:
        days, here = heappop(queue)
        city = state.cities[here]
        if city.owner == owner:
            if days * units > city.grain * denominator() + max_credit:
                continue
            days = 0
        if here in distance and days >= distance[here]:
            continue
        distance[here] = days
        for leg in incoming[here]:
            heappush(queue, (days + leg['days'], leg['from']))
    return distance


def _distance_to_target(target, incoming, allowed):
    """Lower bound on complete travel days through potentially viable cities."""
    queue = [(0, target)]
    distances = {}
    while queue:
        days, here = heappop(queue)
        if here in distances:
            continue
        distances[here] = days
        for leg in incoming[here]:
            if leg['from'] in allowed and leg['from'] not in distances:
                heappush(queue, (days + leg['days'], leg['from']))
    return distances


def detour(game, state, source, target, ids, mode, primary):
    """Return an ordinary save-compatible quote, with no resource or RNG writes."""
    if not primary or mode not in ('fastest', 'land') or len(primary['routes']) < 2:
        return None
    owner = state.cities[source].owner
    units = sum(state.officers[ident].troops + OFFICER_UNITS for ident in ids)
    # The ordinary forecast starts with exactly the initial leg budget. Only
    # a downstream shortage calls for this alternate route search.
    balance = estimate(state, ids, primary) * denominator()
    for leg in primary['routes']:
        balance = _remaining(state, owner, leg['to'], balance, units, leg['days'])
        if balance < 0:
            break
    else:
        return None

    outbound, incoming = _routes(game, state, owner, mode)
    next_depot = _next_depot_days(state, owner, target, units, incoming)
    if source not in next_depot:
        return None
    lower_bound = _distance_to_target(target, incoming, next_depot)
    serial = count()
    balance = state.cities[source].grain * denominator()
    queue = [(lower_bound[source], 0, 0, next(serial), source, balance, [source], [])]
    labels = {}
    while queue:
        _, days, distance, _, here, balance, path, legs = heappop(queue)
        if here == target:
            return game._quote(path, legs)
        visited = frozenset(path)
        # A shorter prefix with the same food and fewer visited cities can
        # use all the remaining choices of this prefix.
        known = labels.setdefault((here, balance), [])
        if any(previous <= visited for previous in known):
            continue
        known.append(visited)
        for leg in outbound[here]:
            city = leg['to']
            if (city in visited or city not in next_depot
                    or units * (leg['days'] + next_depot[city]) > balance):
                continue
            remaining = _remaining(state, owner, city, balance, units, leg['days'])
            travel_days = days + leg['days']
            heappush(queue, (travel_days + lower_bound[city], travel_days, distance + leg['distance_km'],
                             next(serial), city, remaining, path + [city], legs + [leg]))
    return None
