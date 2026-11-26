"""Node-based safety decisions for convoys already physically in transit."""
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
from heapq import heappop, heappush
from itertools import count

from . import army_relief, historical_campaigns, logistics, logistics_rules as rules
from . import march_supply, staging_supply, winter_transport, winter_travel, winter_weather
from .route_hazards import evaluate_leg, route_allowed

FIELD = 'transport_emergency_rules_version'
EXPERIMENT = 'transport_emergency_experiment_stage'
VERSION = 222
EVACUATION, EXTERNAL_RELIEF, TERMINAL = range(1, 4)
REVIEW_DAYS = 10
RELIEF_DAYS = 30
MAX_RELIEF_ATTEMPTS = 2
STATUSES = {'evacuating', 'waiting_for_supply', 'waiting_for_thaw', 'waiting_for_access',
            'no_feasible_exit', 'awaiting_terminal_resolution'}
REASONS = {'escort_return', 'unsafe_return', 'route_blocked', 'target_changed',
           'resource_full', 'city_full', 'retreat', 'rendezvous_expired', 'army_missing',
           'army_supplied', 'rendezvous_missed', 'no_return_route', 'delivered'}
_stage = ContextVar('transport_emergency_experiment', default=0)


@contextmanager
def experiment(level):
    if type(level) is not int or not 0 <= level <= TERMINAL:
        raise ValueError('Transport emergency experiment stage')
    token = _stage.set(level)
    try:
        yield
    finally:
        _stage.reset(token)


def initialize(state, requested=None):
    level = _stage.get() if requested is None else (TERMINAL if requested else 0)
    state.extension.pop(FIELD, None)
    state.extension.pop(EXPERIMENT, None)
    if level:
        state.extension[FIELD] = VERSION
        if level < TERMINAL:
            state.extension[EXPERIMENT] = level


def stage(state):
    if FIELD not in state.extension:
        return 0
    return state.extension.get(EXPERIMENT, TERMINAL)


def validate_version(state):
    fields = state.extension
    if (FIELD in fields and (type(fields[FIELD]) is not int or fields[FIELD] != VERSION
            or rules.version(state) != rules.CURRENT)
            or EXPERIMENT in fields and (FIELD not in fields
                or type(fields[EXPERIMENT]) is not int or fields[EXPERIMENT] not in (EVACUATION, EXTERNAL_RELIEF))):
        raise ValueError('Transport emergency rules version')


def book(row):
    return row['journeys'][-1]['supply']


def convoy_units(state, row):
    return march_supply.ration_units(state, row['officers'], row['cargo']['reserves'])


def available(row):
    return book(row)['remaining'] + row['cargo']['grain']


def tick_now(state):
    return (state.turn - 1) * 10


def stock(game, state, city):
    policy = logistics._pool(state)['cities'][city.id]['policy']
    granted = staging_supply.available(state, city)
    from . import strategic_granary
    if strategic_granary.enabled(state):
        # Return custody outranks future city dispatch, after present army
        # bookings, the local ration installment and the explicit donor floor.
        from . import granary_relay
        granted = max(0, granted - strategic_granary.committed(state,city.id) - granary_relay.credit(state,city.id))
    return min(winter_transport.city_stock(game, state, city, granted),
               max(0, granted - policy['reserve_grain']))


def can_receive(game, state, row, city):
    return city.owner == row['owner'] and not logistics._receiving_blocker(game, state, row, city, returning=True)


def wait_weight(game, state, here):
    if not winter_weather.movement(state):
        return rules.RATION_SCALE
    region = game.catalog.climate.cities[here]['climate_region_id']
    return winter_travel.wait_rate(state, region)


@dataclass(frozen=True)
class Quote:
    route: dict
    days: int
    weight: int
    risk: int

    @property
    def mode(self):
        return 'land' if all(leg['mode'] == 'land' for leg in self.route['routes']) else 'fastest'


@dataclass(frozen=True)
class Option:
    quote: Quote
    budget: army_relief.Budget
    final: str
    staged: bool = False

    @property
    def target(self):
        return self.quote.route['path'][-1]


class Review:
    """Cache quote inputs within one settlement phase, never resource availability."""

    def __init__(self, game, state):
        self.game, self.state = game, state
        self.graphs = {}
        self.paths = {}
        self.legs = {}
        self.weather = winter_weather.movement(state)
        pool = state.extension.get(winter_weather.POOL, {})
        self.conditions = (
            state.month,
            tuple((key, val['severity'], val['depth'], val['cold']) for key, val in pool.get('regions', {}).items()),
            tuple((key, val['state']) for key, val in pool.get('ice', {}).items()),
        )
        self.ownership = tuple(sorted((key, city.owner) for key, city in state.cities.items()))
        self.rights = {}

    def allowed(self, owner):
        if owner not in self.rights:
            self.rights[owner] = frozenset(key for key, city in self.state.cities.items()
                                         if historical_campaigns.transit_allowed(self.state, owner, city.owner))
        return self.rights[owner]

    def access_signature(self, owner):
        pool = self.state.extension.get(winter_weather.POOL, {})
        ice = tuple(key for key, val in pool.get('ice', {}).items() if val['state'] == 3)
        inputs = (self.ownership, sorted(self.allowed(owner)), ice)
        return sha256(repr(inputs).encode()).hexdigest()[:20]

    def graph(self, owner, policy):
        key = (owner, policy['allow_sea'], policy['allow_special'])
        if key in self.graphs:
            return key, self.graphs[key]
        game, state = self.game, self.state
        allowed = self.allowed(owner)
        edges = defaultdict(list)
        frozen = set()
        for raw in game._known_routes(state):
            if not logistics._permitted_route(game, policy, raw):
                continue
            for a, b in ((raw['from'], raw['to']), (raw['to'], raw['from'])):
                # A party can leave the foreign node where it is physically
                # stranded. The graph never admits it to a forbidden node.
                if a not in state.cities or b not in allowed:
                    continue
                ident = (raw['id'], a, b)
                if ident not in self.legs:
                    leg = evaluate_leg(game.catalog.data, raw, a, b, state.month) if route_allowed(
                        game.catalog.data, raw, a, b) else None
                    if leg is None:
                        self.legs[ident] = None
                    else:
                        if self.weather:
                            days, weight, ice = winter_travel.checkpoint_forecast(
                                game, state, game._quote([a, b], [leg]))
                        else:
                            days, ice = leg['days'], None
                            weight = rules.weight(rules.leg_parts(leg, march_supply.travel_rules(game)))
                        hazard = leg.get('hazard') or {}
                        risk = hazard.get('loss_percent_max', 100 - 100 * hazard.get('survival_numerator', 1)
                                          // hazard.get('survival_denominator', 1))
                        self.legs[ident] = (leg, days, weight, risk, ice)
                choice = self.legs[ident]
                if choice is None:
                    continue
                leg, days, weight, risk, ice = choice
                if ice is not None:
                    frozen.add(a)
                else:
                    edges[a].append((b, leg, days, weight, risk))
        self.graphs[key] = (edges, frozen)
        return key, self.graphs[key]

    def quotes(self, owner, origin, policy):
        key, (edges, _) = self.graph(owner, policy)
        lookup = (key, origin)
        if lookup in self.paths:
            return self.paths[lookup]
        results = defaultdict(list)
        # A fast route and a less expensive route can both be relevant,
        # especially when the last few bags of grain determine feasibility.
        for primary in ('time', 'grain', 'safe'):
            serial = count()

            def rank(days, weight, risk):
                return {'time': (days, risk, weight), 'grain': (weight, risk, days),
                        'safe': (risk, days, weight)}[primary]

            queue = [(rank(0, 0, 0), next(serial), origin, (origin,), (), 0, 0, 0)]
            seen = set()
            while queue:
                _, _, here, path, legs, days, weight, risk = heappop(queue)
                if here in seen:
                    continue
                seen.add(here)
                if not any(item.route['routes'] == list(legs) for item in results[here]):
                    results[here].append(Quote(self.game._quote(list(path), list(legs)), days, weight, risk))
                for dest, leg, leg_days, cost, hazard in edges.get(here, ()):
                    if dest not in seen:
                        score = rank(days + leg_days, weight + cost, risk + hazard)
                        heappush(queue, (score, next(serial), dest, (*path, dest), (*legs, leg),
                                         days + leg_days, weight + cost, risk + hazard))
        self.paths[lookup] = results
        return results

    def measure(self, route):
        game, state = self.game, self.state
        if self.weather:
            days, weight, ice = winter_travel.checkpoint_forecast(game, state, route)
            if ice is not None:
                return None
        else:
            days = route['days']
            weight = rules.weight(rules.plan(route, march_supply.travel_rules(game)))
        risk = 0
        for leg in route['routes']:
            hazard = leg.get('hazard') or {}
            risk += hazard.get('loss_percent_max', 100 - 100 * hazard.get('survival_numerator', 1)
                               // hazard.get('survival_denominator', 1))
        return Quote(route, days, weight, risk)

    def options(self, row, here, receiving):
        units = convoy_units(self.state, row)
        credit = book(row)['credit_units']
        routes = self.quotes(row['owner'], here, row['route_policy'])
        return [Option(quote, army_relief.ration_budget(units, quote.weight, 0, 0, credit=credit), city)
                for city in receiving for quote in routes.get(city, ())]

    def staged(self, row, here, options, allotment, access):
        game, state = self.game, self.state
        already = {city: quantity for city, quantity, conditions in row.get('emergency', {}).get('stops', ())
                   if conditions == access}
        units = convoy_units(state, row)
        credit = book(row)['credit_units']
        choices = []
        estimated = {}
        checked = set()
        for option in options:
            route = option.quote.route
            for idx, city in enumerate(route['path'][1:-1], start=1):
                point = state.cities[city]
                if point.owner != row['owner']:
                    continue
                if city not in estimated:
                    estimated[city] = stock(game, state, point)
                offered = estimated[city]
                prefix = route['routes'][:idx]
                suffix = route['routes'][idx:]
                key = (tuple(leg['id'] for leg in prefix), tuple(leg['id'] for leg in suffix))
                if not offered or offered <= already.get(city, -1) or key in checked:
                    continue
                checked.add(key)
                outward = self.measure(game._quote(route['path'][:idx+1], prefix))
                backward = self.measure(game._quote(route['path'][idx:], suffix))
                if outward is None or backward is None:
                    continue
                wait = (-(book(row)['clock_tick'] + outward.days)) % 10
                short = army_relief.ration_budget(units, outward.weight, wait * wait_weight(game, state, city),
                                                 0, credit=credit)
                follow = army_relief.ration_budget(units, backward.weight, 0, 0)
                if short.total <= allotment and follow.total <= allotment - short.total + offered:
                    choices.append((Option(outward, short, option.final, staged=True), offered))
        return min(choices, key=lambda x: option_rank(x[0]), default=(None, 0))


def option_rank(option):
    return (option.quote.risk, option.quote.days, option.budget.total, option.target,
            tuple(leg['id'] for leg in option.quote.route['routes']))


def note(game, state, event, row, *, at=None, **values):
    if not winter_weather.observing():
        return
    supply = book(row)
    phase = row.get('emergency', {})
    winter_weather.report(event, tick=supply['clock_tick'], convoy_id=row['id'], owner=row['owner'],
        actual_position=at if at is not None else march_supply.current_city(row['journeys'][-1]),
        current_phase=row['status'], initial_escort_troops=sum(row['journeys'][0]['departure_troops'].values()),
        current_escort_troops=sum(state.officers[i].troops for i in row['officers']),
        current_officers=sum(type(i) is int for i in row['officers']),
        current_civil_staff=sum(type(i) is str for i in row['officers']),
        current_reserve_cargo=row['cargo']['reserves'], current_rations=supply['remaining'],
        current_grain_cargo=row['cargo']['grain'], full_return_budget=phase.get('full_budget'),
        emergency_route_budget=phase.get('route_budget'), emergency_target=phase.get('target'),
        emergency_reason=phase.get('reason'), **values)


def _take_local(game, state, row, city, amount):
    if city.owner != row['owner']:
        return 0
    supply = book(row)
    taken = min(amount, stock(game, state, city), logistics.LIMIT - supply['remaining'])
    if taken:
        from . import strategic_granary
        strategic_granary.spending(state,city,taken,'military_or_urgent')
        city.grain -= taken
        march_supply.receive(supply, taken, 'city', city.id, state.turn)
        strategic_granary.observe(state,'emergency_refill',city=city.id,owner=city.owner,
                                   convoy_id=row['id'],grain=taken)
        game._supply_event(state, 'march_resupplied', unit_kind='convoy', unit_id=row['id'],
            city=city.id, owner=row['owner'], grain=taken, reason='city')
        note(game, state, 'emergency_refill', row, at=city.id, amount=taken)
    return taken


def _signature(review, row, here, local_stock, receiving, reason):
    supply = book(row)
    return sha256(repr((reason, here, len(row['journeys']), available(row), supply['credit_units'],
        convoy_units(review.state, row), local_stock, tuple(receiving), review.conditions,
        review.ownership, sorted(review.allowed(row['owner'])))).encode()).hexdigest()


def direct_home(game,state,row,here,reason):
    """Normal funded returns do not need the emergency all-destination search."""
    if 'emergency' in row or len(row['journeys']) >= logistics.RULES['max_journeys']:
        return False
    home = state.cities[row['source']]
    if not can_receive(game,state,row,home):
        return False
    if here == home.id:
        return logistics._dock(game,state,row,home)
    from copy import copy
    origin = copy(state.cities[here])
    origin.owner = row['owner']
    review = Review(game,state)
    for mode,route in logistics._safe_options(game,state,origin,home,row['route_policy']):
        quote = review.measure(route)
        if quote is None:
            continue
        needed = army_relief.ration_budget(convoy_units(state,row),quote.weight,0,0,
                                          credit=book(row)['credit_units']).total
        from . import strategic_granary
        if strategic_granary.enabled(state):
            local = state.cities[here]
            approach = {march['target'] for march in state.extension['travel']['marches']
                        if march['kind'] == 'attack' and not historical_campaigns.allied(
                            state,row['owner'],march['owner']) and march['owner'] != row['owner']
                        and march['arrival_turn'] <= state.turn+max(1,(quote.days+9)//10)}
            weather = winter_travel.seasonal_forecast(game,state,route)
            if (row['delivery_done'] and can_receive(game,state,row,local)
                    and (approach.intersection(route['path'][1:]) or weather['reaches'])):
                strategic_granary.observe(state,'return_shelter',convoy_id=row['id'],owner=row['owner'],
                    city=local.id,home=home.id,reason='route_threat' if approach.intersection(route['path'][1:]) else 'ice_risk',
                    return_days=quote.days,required=needed,grain=available(row))
                return logistics._dock(game,state,row,local)
            missing = max(0,needed-available(row))
            if missing and local.owner == row['owner'] and stock(game,state,local) >= missing:
                _take_local(game,state,row,local,missing)
        if needed > available(row):
            continue
        if logistics._keep_return_journey(row,here,home.id,route):
            return True
        if logistics._begin_journey(game,state,row,here,home.id,mode,route,
                                    status='returning',reason=reason,prepaid=needed):
            logistics._event(game,state,'transport_returned',row,reason=reason)
            return True
    return False


def withdraw(game, state, row, here, reason, *, review=None):
    """At a real node, retain the same journey or move only what can be paid."""
    review = review or Review(game, state)
    local = state.cities[here]
    supply = book(row)
    previous = row.get('emergency', {})
    carry = available(row)
    local_supply = stock(game, state, local) if local.owner == row['owner'] else 0
    receiving = sorted(city.id for city in state.cities.values() if can_receive(game, state, row, city))
    signature = _signature(review, row, here, local_supply, receiving, reason)
    if previous.get('signature') == signature and previous['status'] != 'evacuating':
        return False
    access = review.access_signature(row['owner'])
    options = review.options(row, here, receiving)
    home = min((o for o in options if o.final == row['source']), key=lambda o: (o.budget.total, option_rank(o)),
               default=None)
    choice = min((o for o in options if o.final == row['source'] and o.budget.total <= carry),
                 key=option_rank, default=None)
    staged_stock = 0
    protected = carry + local_supply
    stranded = previous.get('status') != 'evacuating' and ('emergency' in row or supply['waiting'])
    empty_delivery = not any(row['cargo'].values()) and not (convoy_units(state, row) - 100*len(row['officers']))
    if stage(state) >= TERMINAL and empty_delivery and here in receiving and (stranded or row['delivery_done']):
        choice = next(o for o in options if o.target == here)
    if choice is None:
        if home and carry < home.budget.total and previous.get('status') == 'evacuating' and home.budget.total <= protected:
            choice = home
        elif here in receiving:
            choice = next(o for o in options if o.target == here)
        else:
            choice = min((o for o in options if o.budget.total <= protected), key=option_rank, default=None)
    if choice is None and options:
        choice, staged_stock = review.staged(row, here, options, protected, access)
    risky = False
    day_cost = army_relief.ration_budget(convoy_units(state, row), wait_weight(game,state,here), 0, 0,
                                        credit=supply['credit_units']).outbound
    confirmed = ()
    if (choice is None and stage(state)>=EXTERNAL_RELIEF and previous.get('status')=='waiting_for_supply'
            and 'convoy_relief' not in row):
        from . import convoy_relief
        demand=convoy_relief.request(game,state,row)
        if demand is not None:
            confirmed=convoy_relief.outstanding(game,state,row,demand,review=review)
    funded_wait=any(grain >= max(0,previous['route_budget']-protected+day_cost*(eta-supply['clock_tick']))
                    and day_cost*(eta-supply['clock_tick'])<=protected for eta,grain in confirmed)
    if choice is None and not funded_wait and (
            supply['shortage_streak'] or supply['waiting'] and protected <= day_cost*REVIEW_DAYS):
        choice = min((o for o in options if o.budget.outbound + o.budget.wait <= protected),
                     key=option_rank, default=None)
        risky = choice is not None
    nearest = choice or min(options, key=lambda o:(o.budget.total, option_rank(o)), default=None)
    stops = previous.get('stops', [])
    if choice is not None and choice.staged:
        stops = [*stops, [choice.target, staged_stock, access]][-logistics.RULES['max_journeys']:]
    pool = row['emergency'] = dict(status='no_feasible_exit',
        since=previous.get('since', supply['clock_tick']), reason=reason, signature=signature,
        full_budget=home.budget.total if home else None,
        route_budget=nearest.budget.total if nearest else None, target=nearest.target if nearest else None,
        final=nearest.final if nearest else None, stops=stops, local_supply=local_supply,
        meal_per_day=day_cost, risk_margin_waived=risky,
        attempts=previous.get('attempts', 0), last_sent=previous.get('last_sent'))
    if choice:
        path = choice.quote.route
        if not path['days']:
            pool['status'] = 'awaiting_terminal_resolution'
            note(game,state,'emergency_decision',row,at=here,decision='dock',rejection_reason=None)
            return logistics._dock(game, state, row, local)
        if logistics._keep_return_journey(row, here, choice.target, path):
            pool['status'] = 'evacuating'
            note(game,state,'emergency_decision',row,at=here,decision='keep_route',rejection_reason=None)
            return True
        if len(row['journeys']) < logistics.RULES['max_journeys']:
            needed = choice.budget.total - (choice.budget.safety if risky else 0)
            missing = max(0, needed - carry)
            provided = _take_local(game, state, row, local, missing) if missing else 0
            if provided == missing and logistics._begin_journey(game,state,row,here,choice.target,
                    choice.quote.mode,path,status='returning',reason=reason,prepaid=needed):
                pool['status'] = 'evacuating'
                note(game,state,'emergency_plan',row,at=here,decision='staged' if choice.staged else 'withdraw',
                     route=path['path'], days=choice.quote.days, safety=choice.budget.safety,
                     available_local_supply=local_supply,
                     rejection_reason='insufficient_safety_margin_waiting_risk' if risky else None)
                logistics._event(game,state,'transport_returned',row,reason=reason)
                return True
        row['reason'] = 'journey_limit' if len(row['journeys']) >= logistics.RULES['max_journeys'] else row['reason']

    _, (_, frozen) = review.graph(row['owner'], row['route_policy']) if not options else (None, (None, set()))
    physical_ice = supply.get('winter', {}).get('blocked') or here in frozen
    supply['waiting'] = True
    supply['retreat_requested'] = True
    row['status'] = 'waiting'
    if not options and physical_ice:
        pool['status'] = 'waiting_for_thaw'
    elif not options and (local.owner != row['owner'] or reason in ('route_blocked', 'target_changed')):
        pool['status'] = 'waiting_for_access'
    elif confirmed:
        pool['status'] = 'waiting_for_supply'
    if row['reason'] != 'journey_limit':
        row['reason'] = 'unsafe_return' if options else 'no_return_route'
    if 'convoy_relief' in row:
        pool['status'] = 'no_feasible_exit' if pool['status'] == 'waiting_for_supply' else pool['status']
    note(game,state,'emergency_decision',row,at=here,decision=pool['status'],
         available_local_supply=local_supply,rejection_reason=row['reason'])
    return False


def validate_row(state, row):
    plan = row['emergency']
    numbers = {'since','full_budget','route_budget','local_supply','meal_per_day','attempts','last_sent'}
    if (not stage(state) or not isinstance(plan,dict) or
            set(plan) != numbers | {'status','reason','signature','target','final','stops','risk_margin_waived'}
            or plan['status'] not in STATUSES or plan['reason'] not in REASONS
            or type(plan['risk_margin_waived']) is not bool
            or not isinstance(plan['signature'],str) or len(plan['signature']) != 64
            or any(plan[key] is not None and plan[key] not in state.cities for key in ('target','final'))
            or type(plan['attempts']) is not int or not 0 <= plan['attempts'] <= MAX_RELIEF_ATTEMPTS
            or any(plan[k] is not None and (type(plan[k]) is not int or not 0 <= plan[k] <= 20*logistics.LIMIT)
                   for k in numbers)
            or any(plan[k] is None for k in ('since','local_supply','meal_per_day'))
            or plan['since'] > tick_now(state) or plan['last_sent'] is not None and plan['last_sent'] > tick_now(state)
            or not isinstance(plan['stops'],list) or len(plan['stops']) > logistics.RULES['max_journeys']
            or any(not isinstance(stop,list) or len(stop) != 3 or stop[0] not in state.cities
                   or type(stop[1]) is not int or stop[1] < 1
                   or not isinstance(stop[2],str) or len(stop[2]) != 20 for stop in plan['stops'])):
        raise ValueError('Convoy emergency plan')
