"""Quote the shortest officer transfer that current city stocks can supply."""
from heapq import heappop, heappush
from itertools import count
from math import gcd

from .historical_campaigns import transit_allowed
from . import logistics_rules as rules
from .march_supply import denominator, OFFICER_UNITS, estimate, travel_rules
from .route_hazards import evaluate_leg, route_allowed


def _remaining(state, owner, city, balance, units, weight, divisor):
    """Carry fractional meal credit across our resupply checkpoints."""
    remaining = balance - units * weight
    if remaining >= 0 and state.cities[city].owner == owner:
        return state.cities[city].grain * divisor + remaining % divisor
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


def _next_depot_weight(state, owner, target, units, incoming, weight, divisor, weighted):
    """Prune dead ends using the largest possible fractional ration credit."""
    queue = [(0, target)]
    max_credit = divisor - (1 if weighted else gcd(divisor, units))
    distance = {}
    while queue:
        days, here = heappop(queue)
        city = state.cities[here]
        if city.owner == owner:
            if days * units > city.grain * divisor + max_credit:
                continue
            days = 0
        if here in distance and days >= distance[here]:
            continue
        distance[here] = days
        for leg in incoming[here]:
            heappush(queue, (days + weight(leg), leg['from']))
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
    weighted = rules.version(state) == rules.CURRENT
    divisor = denominator() * (rules.RATION_SCALE if weighted else 1)
    weights = {}
    def weight(leg):
        if not weighted:
            return leg['days']
        key = leg['id'], leg['from']
        if key not in weights:
            weights[key] = rules.weight(rules.leg_parts(leg, travel_rules(game)))
        return weights[key]
    balance = estimate(state, ids, primary, game=game) * divisor
    for leg in primary['routes']:
        balance = _remaining(state, owner, leg['to'], balance, units, weight(leg), divisor)
        if balance < 0:
            break
    else:
        return None

    outbound, incoming = _routes(game, state, owner, mode)
    next_depot = _next_depot_weight(state, owner, target, units, incoming, weight, divisor, weighted)
    if source not in next_depot:
        return None
    lower_bound = _distance_to_target(target, incoming, next_depot)
    serial = count()
    balance = state.cities[source].grain * divisor
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
                    or units * (weight(leg) + next_depot[city]) > balance):
                continue
            remaining = _remaining(state, owner, city, balance, units, weight(leg), divisor)
            travel_days = days + leg['days']
            heappush(queue, (travel_days + lower_bound[city], travel_days, distance + leg['distance_km'],
                             next(serial), city, remaining, path + [city], legs + [leg]))
    return None


MINIMUM_GRAIN = 'minimum_grain'
SEARCH_LIMIT = 2048


def minimum_grain(game, state, source, target, owner, ids, *, adjacent=False, cargo=0, reserves=0):
    """Search physical, provisionable paths in increasing lower-bound grain cost.

    The original engine freezes all leg conditions at departure. We preserve
    that quote contract, track the granaries and both fractional balances, and
    exclude loops. The visit limit applies to exploratory player/AI quotes.
    """
    if (rules.version(state) != rules.CURRENT or source == target or not ids
            or source not in state.cities or target not in state.cities
            or not adjacent and state.cities[target].owner != owner
            or cargo > state.cities[source].grain):
        return None
    data = game.catalog.data
    policy = travel_rules(game)
    if adjacent:
        routes = [row for row in game._known_routes(state)
                  if {row['from'],row['to']} == {source,target}]
        valid = {source,target}
    else:
        routes = game._known_routes(state)
        valid = {key for key,city in state.cities.items() if transit_allowed(state,owner,city.owner)}
        valid.add(source)
    outgoing = {key: [] for key in valid}
    incoming = {key: [] for key in valid}
    for raw in routes:
        a,b = raw['from'],raw['to']
        if a not in valid or b not in valid:
            continue
        for origin,dest in ((a,b),(b,a)):
            if not route_allowed(data,raw,origin,dest):
                continue
            leg = evaluate_leg(data,raw,origin,dest,state.month)
            parts = rules.leg_parts(leg,policy)
            weight = rules.weight(parts)
            hazard = (leg.get('hazard') or {}).get('loss_percent_max',0)
            outgoing[origin].append((dest,leg,parts,weight,hazard))
            incoming[dest].append((origin,weight))

    distance = {}
    reverse = [(0,target)]
    while reverse:
        weight, here = heappop(reverse)
        if here in distance:
            continue
        distance[here] = weight
        for previous,fee in incoming[here]:
            if previous not in distance:
                heappush(reverse,(weight+fee,previous))
    if source not in distance:
        return None

    divisor = denominator() * rules.RATION_SCALE
    units = sum(state.officers[i].troops for i in ids) + OFFICER_UNITS * len(ids) + reserves
    stock = (state.cities[source].grain-cargo)*divisor
    serial = count()
    queue = [(rules.ceil_div(units*distance[source],divisor),0,0,0,(),next(serial),
              source,stock,cargo,0,0,[source],[])]
    seen = {}
    attempts = 0
    while queue and attempts<SEARCH_LIMIT:
        _,days,risk,_,keys,_,here,credit,load,remainder,paid,path,legs=heappop(queue)
        if here == target:
            return game._quote(path,legs)
        signature = here,credit,load,remainder
        visited = frozenset(path)
        visited_paths = seen.setdefault(signature,[])
        if any(previous<=visited for previous in visited_paths):
            continue
        visited_paths.append(visited)
        attempts += 1
        for dest,leg,parts,weight,extra_risk in outgoing[here]:
            if dest in visited or dest not in distance:
                continue
            due = units * weight
            balance = credit - due
            if balance < 0:
                continue
            if dest != target and state.cities[dest].owner == owner:
                balance = state.cities[dest].grain*divisor + balance % divisor
            grain,carry = (rules.estimate_cargo(load,parts,leg['days'],remainder=remainder)
                           if load else (0,remainder))
            projected = rules.ceil_div(paid + due + units*distance[dest],divisor) + cargo-grain
            heappush(queue,(projected,days+leg['days'],risk+extra_risk,len(legs)+1,
                           keys+(leg['id'],),next(serial),dest,balance,grain,carry,paid+due,
                           path+[dest],legs+[leg]))
    return None
