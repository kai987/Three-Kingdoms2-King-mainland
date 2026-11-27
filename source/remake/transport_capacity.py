"""Optional V3.0.3 transport limits. Stock, cargo and rations retain their own ledgers."""
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar

from . import grain_units, logistics_rules
from .errors import GameError

FIELD = 'transport_capacity_rules_version'
POOL = 'transport_capacity'
OPTIONS = 'transport_capacity_options'
VERSION = 303
FEATURES = ('concurrency', 'physical_capacity', 'mode_aware_ai_policy', 'throughput_ranking',
            'double_dispatch')
DEFAULTS = dict.fromkeys(FEATURES, True) | {'double_dispatch': False}
RATIOS = {'plain': 100, 'mountain': 80, 'desert': 70, 'river_downstream': 200,
          'river_still': 200, 'river_upstream': 200, 'sea': 300}
LOAD_FIELD = 'capacity_load'
INVALID = '運輸容量規則版本或選項無效。'
_observer = ContextVar('transport_capacity_observer', default=None)
_protected_history = ContextVar('transport_capacity_replay_history', default={})


def normalize(raw):
    if (not isinstance(raw, dict) or set(raw) - set(FEATURES)
            or any(type(flag) is not bool for flag in raw.values())):
        raise GameError(INVALID)
    flags = DEFAULTS | raw
    if flags['double_dispatch'] and not flags['concurrency']:
        raise GameError(INVALID)
    if flags['mode_aware_ai_policy'] and not flags['physical_capacity']:
        raise GameError(INVALID)
    return flags


def initialize(state, version, options=None):
    if (type(version) is not int or version not in (0, VERSION) or not version and options
            or version and logistics_rules.version(state) != logistics_rules.CURRENT):
        raise GameError(INVALID)
    if version:
        state.extension[FIELD] = VERSION
        state.extension[POOL] = {'features': normalize({} if options is None else options), 'dispatches': {}}


def enabled(state, feature=None):
    table = state.extension.get(POOL)
    return table is not None and (feature is None or table['features'][feature])


def active_limit(state):
    return 2 if enabled(state, 'concurrency') else 1


def dispatch_limit(state):
    return 2 if enabled(state, 'double_dispatch') else 1


def origin_key(state, source, owner):
    return (source, owner) if enabled(state, 'concurrency') else source


def activity(state):
    return Counter(origin_key(state, row['source'], row['owner'])
                   for row in state.extension['logistics']['convoys'])


def active_count(state, source, active=None):
    key = origin_key(state, source.id, source.owner)
    return (activity(state) if active is None else active).get(key, 0)


def dispatch_count(state, source):
    if enabled(state):
        record = state.extension[POOL]['dispatches'].get(source)
        return record[1] if record is not None and record[0] == state.turn else 0
    return int(state.extension['logistics']['cities'][source]['last_dispatch_turn'] == state.turn)


def record_dispatch(state, source):
    if enabled(state):
        state.extension[POOL]['dispatches'][source] = [state.turn, dispatch_count(state, source) + 1]
    state.extension['logistics']['cities'][source]['last_dispatch_turn'] = state.turn


@contextmanager
def fixed_replay(state, options):
    """Enable a candidate on a private copy of an already validated old checkpoint."""
    if enabled(state):
        raise ValueError('Capacity control must start from an unversioned checkpoint')
    ledger=state.extension['logistics']
    previous={row['id']:len(row['journeys']) for row in ledger['convoys']}
    initialize(state,VERSION,options)
    table=state.extension[POOL]['dispatches']
    for key,city in ledger['cities'].items():
        if city['last_dispatch_turn']:
            table[key]=[city['last_dispatch_turn'],1]
    token=_protected_history.set(previous)
    try:
        yield
    finally:
        _protected_history.reset(token)


def historical_journey(convoy, index):
    return index < _protected_history.get().get(convoy,0)


def dispatch_blocker(state, source, active=None):
    if dispatch_count(state, source.id) >= dispatch_limit(state):
        return 'already_dispatched'
    if active_count(state, source, active) >= active_limit(state):
        return 'in_transit'
    return None


def validate(state):
    version = state.extension.get(FIELD)
    data = state.extension.get(POOL)
    if FIELD not in state.extension and POOL not in state.extension:
        return
    if (type(version) is not int or version != VERSION or logistics_rules.version(state) != logistics_rules.CURRENT
            or not isinstance(data, dict) or set(data) != {'features', 'dispatches'}):
        raise ValueError('Transport capacity version')
    features, dispatches = data['features'], data['dispatches']
    if not isinstance(features, dict) or set(features) != set(FEATURES):
        raise ValueError('Transport capacity features')
    try:
        normalize(features)
    except GameError as error:
        raise ValueError('Transport capacity features') from error
    if not isinstance(dispatches, dict) or not dispatches.keys() <= state.cities.keys():
        raise ValueError('Transport departure counts')
    city_rows = state.extension['logistics']['cities']
    for key, record in dispatches.items():
        if (not isinstance(record, list) or len(record) != 2
                or any(type(value) is not int for value in record)
                or not 1 <= record[0] <= state.turn or not 1 <= record[1] <= dispatch_limit(state)
                or city_rows[key]['last_dispatch_turn'] != record[0]):
            raise ValueError('Transport departure count')
    if any(ledger['last_dispatch_turn'] and key not in dispatches for key, ledger in city_rows.items()):
        raise ValueError('Missing transport departure count')


def automation(state, owner):
    return state.phase == 'ai' and owner != state.player


def ai_policy(state, owner, policy, *, automatic):
    if (automatic and owner != state.player and enabled(state, 'mode_aware_ai_policy')
            and policy['enabled'] and not policy['allow_sea']):
        return dict(policy, allow_sea=True)
    return policy


def base_capacity(state):
    # Shape a physical limit in the save's actual denomination, once.
    return 5_000 * (grain_units.CURRENT if state.extension.get(grain_units.FIELD) == grain_units.CURRENT else 1)


def physical(game, state, quote):
    """Use the actual directional stages, with embark and waiting excluded."""
    rules = game.catalog.data.get('travel_rules', {})
    modes, limiting = set(), None
    for leg in quote['routes']:
        for kind, _, place in logistics_rules.leg_parts(leg, rules, locations=True):
            if kind not in RATIOS:
                continue
            modes.add('river' if kind.startswith('river_') else 'sea' if kind == 'sea' else 'land')
            value = RATIOS[kind]
            if limiting is None or value < limiting['percent']:
                limiting = dict(route=leg['id'], source=leg['from'], target=leg['to'],
                                mode=kind, stage=place, percent=value)
    return dict(mode=next(iter(modes)) if len(modes) == 1 else 'mixed' if modes else 'stationary',
                physical_capacity=(base_capacity(state)*limiting['percent']//100 if limiting else None),
                bottleneck=limiting)


def policy_limit(state, owner, policy, route, *, automatic):
    base = policy['max_grain']
    if automatic and owner != state.player and enabled(state, 'mode_aware_ai_policy'):
        return base * {'river': 2, 'sea': 3}.get(route['mode'], 1)
    return base


def effective_cargo(physical_limit, rations, policy_max, available, other_limit):
    grain = min(policy_max, available-rations, other_limit)
    return max(0, grain if physical_limit is None else min(grain, physical_limit-rations))


def loading(game, state, owner, policy, quote, rations, available, other_limit, *, automatic=False, profile=None):
    if profile is None:
        profile = physical(game,state,quote) if enabled(state, 'physical_capacity') else {
            'mode': 'legacy', 'physical_capacity': None, 'bottleneck': None}
    limit = policy_limit(state, owner, policy, profile, automatic=automatic)
    return dict(profile, policy_max_grain=limit, available_grain=max(0, available), rations=rations,
                max_cargo=effective_cargo(profile['physical_capacity'], rations, limit, available, other_limit))


def current_grain(state, city, *, except_order=None):
    from . import staging_supply, strategic_granary, transshipment
    return min(staging_supply.available(state, city),
               strategic_granary.available(state, city, except_id=except_order)
               if strategic_granary.enabled(state) else max(0,city.grain-transshipment.credit(state,city.id)))


def enforced(state, row):
    if enabled(state,'physical_capacity'):
        return True
    from . import transshipment
    return transshipment.enabled(state) and transshipment.is_batch(state,row['id'])


def fits(game, state, row, quote, *, minimum=0):
    if not enforced(state,row):
        return True
    cap = physical(game, state, quote)['physical_capacity']
    carry = row['cargo']['grain'] + row['journeys'][-1]['supply']['remaining']
    return cap is None or max(carry,minimum) <= cap


def refill_room(game, state, row, city, *, route=None, cargo_grain=None):
    if not enforced(state,row):
        return 100_000_000
    journey=row['journeys'][-1]
    if route is None:
        route=journey['quote']
        index=route['path'].index(city) if city in route['path'] else 0
        routes=route['routes'][index:]
        # A stopped convoy may still need a new route after the handoff.
        route={'routes':routes or route['routes']}
    cap=physical(game,state,route)['physical_capacity']
    carry=(row['cargo']['grain'] if cargo_grain is None else cargo_grain)+journey['supply']['remaining']
    return 100_000_000 if cap is None else max(0,cap-carry)


def metrics(net, rations, outward, backward, waiting, officers, receipt_turns):
    days = outward + backward + waiting
    occupied = days + receipt_turns*10
    return dict(outward_days=outward, return_days=backward, wait_days=waiting,
                cycle_days=days, occupancy_days=occupied, escort_count=officers,
                throughput_milli=net*1000//days if days else None,
                officer_efficiency_milli=net*1000//(officers*occupied) if officers and occupied else None,
                net_grain_gain=net-rations, ration_per_thousand=rations*1000//net if net else None)


def priority(net, rations, outward, backward, waiting, officers, receipt_turns, cost):
    measurements = metrics(net,rations,outward,backward,waiting,officers,receipt_turns)
    return (-net, measurements['cycle_days'], -(measurements['officer_efficiency_milli'] or 0), cost)


@contextmanager
def observing(callback):
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def observed():
    return _observer.get() is not None


def observe(state, event, **values):
    callback = _observer.get()
    if callback is not None:
        callback(event, dict(turn=state.turn, year=state.year, month=state.month, day=state.day, **values))
