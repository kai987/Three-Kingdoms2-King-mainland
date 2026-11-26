"""Logical city reserves and orders backed by the campaign's real convoys."""
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar

from . import economy_rules, logistics, logistics_rules, staging_supply
from .errors import GameError

VERSION = 302
FIELD = 'strategic_granary_rules_version'
OPTIONS = 'strategic_granary_options'
POOL = 'strategic_granary'
COMMAND = 'strategic_granary_order'

# Experimental parameters with independent switches. These adjust allocation
# and custody only. Production, consumption, prices and restocking stay shared.
RULES = dict(rear_months=1, front_months=2, history=96, hold_turns=3,
             minimum_load=150, maximum_ration_percent=45, timely_buffer_days=5,
             winter_max_months=1, cold_reserve_min_chance=20, relay_hubs=3, relay_targets=3)
FEATURES = frozenset({'proactive', 'winter', 'relay'})
ACTIVE = {'reserved', 'dispatched', 'in_transit', 'delayed', 'diverted',
          'partially_delivered', 'delivered'}
TERMINAL = {'cancelled', 'returned', 'failed'}
REASONS = {'civilian_and_garrison', 'military_or_urgent', 'manual', 'policy', 'ownership',
           'expired', 'source_safety', 'warehouse', 'scheduled'}
INVALID = '戰略糧倉操作無效。'
STALE = '戰略調糧條件已變更，請重新取得報價。'
INSUFFICIENT = '官倉可動用糧食不足。'

_experiment = ContextVar(POOL + '_experiment', default=None)
_observer = ContextVar(POOL + '_observer', default=None)


@contextmanager
def experiment(**options):
    flags = _options(options)
    token = _experiment.set(flags)
    try:
        yield
    finally:
        _experiment.reset(token)


@contextmanager
def observing(callback):
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def observe(state, event, **fields):
    callback = _observer.get()
    if callback is not None:
        callback(event, dict(turn=state.turn, year=state.year, month=state.month, day=state.day, **fields))


def observed():
    return _observer.get() is not None


def _options(raw):
    if not isinstance(raw, dict) or not raw.keys() <= FEATURES or any(type(v) is not bool for v in raw.values()):
        raise GameError(INVALID)
    return {key: raw.get(key, False) for key in sorted(FEATURES)}


def enabled(state, feature=None):
    if state is None or state.extension.get(FIELD) != VERSION:
        return False
    return feature is None or state.extension[POOL]['features'][feature]


def initialize(state, version=None, options=None):
    if version is None and options is None:
        flags = _experiment.get()
        if flags is None:
            return
    else:
        if type(version) is not int or version not in (0, VERSION) or not version and options:
            raise GameError(INVALID)
        state.extension.pop(FIELD, None)
        state.extension.pop(POOL, None)
        if not version:
            return
        flags = _options({} if options is None else options)
    if (economy_rules.version(state) != economy_rules.CURRENT or
            logistics_rules.version(state) != logistics_rules.CURRENT):
        raise GameError(INVALID)
    state.extension[FIELD] = VERSION
    state.extension[POOL] = dict(features=dict(flags), cities={}, orders={}, history=[], relays={}, next_id=1)


def pool(state):
    return state.extension[POOL]


def reserve_row(state, city):
    if enabled(state):
        row = pool(state)['cities'].get(city.id)
        if row and row['owner'] == city.owner:
            return row
    return None


def reserve_grain(state, city):
    entry = reserve_row(state, city)
    return min(city.grain, entry['grain']) if entry else 0


def commitments(state, source=None, *, except_id=None):
    if not enabled(state):
        return ()
    return (row for row in pool(state)['orders'].values()
            if row['status'] == 'reserved' and row['id'] != except_id
            and (source is None or row['source'] == source)
            and state.cities[row['source']].owner == state.cities[row['target']].owner == row['owner'])


def committed(state, source, *, except_id=None):
    return sum(row['load'] + row['rations'] for row in commitments(state, source, except_id=except_id))


def available(state, city, *, except_id=None, military=True):
    held = staging_supply.held(state, city.id) if military else 0
    relay = 0
    if enabled(state,'relay'):
        from . import granary_relay
        relay = granary_relay.credit(state,city.id)
    return max(0, city.grain - reserve_grain(state, city) - committed(state, city.id, except_id=except_id) - held - relay)


def change_reserve(state, city, grain, reason, *, target=None, set_target=False):
    """Reclassify existing stock, preserving its current ownership."""
    cities = pool(state)['cities']
    previous = reserve_row(state, city)
    current = previous['grain'] if previous else 0
    chosen = target if set_target else previous['manual_target'] if previous else None
    if current == grain and (not set_target or previous and chosen == previous['manual_target']):
        return
    cities[city.id] = dict(owner=city.owner, grain=grain, manual_target=chosen,
                           turn=state.turn, reason=reason)
    if current != grain:
        observe(state, 'reserve_added' if grain > current else 'reserve_released',
                city=city.id, owner=city.owner, delta=grain-current, grain=grain, reason=reason)


def spending(state, city, amount, reason):
    """A real priority debit spends ordinary stock first, then frees reserve."""
    grain = reserve_grain(state, city)
    remainder = max(0, city.grain - amount)
    if grain > remainder:
        change_reserve(state, city, remainder, reason)


def _order(state, ident):
    return pool(state)['orders'].get(str(ident))


def _note_order(state, order, event):
    if observed():
        observe(state, event, **order)


def _finish(state, order, status, reason):
    ledger = pool(state)
    order.update(status=status, reason=reason, completed_turn=state.turn)
    del ledger['orders'][str(order['id'])]
    ledger['history'].append(order)
    del ledger['history'][:-RULES['history']]
    _note_order(state, order, 'order_closed')


def synchronize(state):
    """Settle ownership, higher priority preemption and expired unshipped locks."""
    if not enabled(state):
        return
    ledger = pool(state)
    if not ledger['cities'] and not ledger['orders'] and not ledger['relays']:
        return
    for key, row in list(ledger['cities'].items()):
        city = state.cities.get(key)
        if city is None or city.owner != row['owner']:
            observe(state, 'reserve_released', city=key, owner=row['owner'],
                    delta=-row['grain'], grain=0, reason='ownership')
            del ledger['cities'][key]
        elif row['grain'] > city.grain:
            change_reserve(state, city, city.grain, 'military_or_urgent')
    held = defaultdict(int)
    for row in staging_supply.active(state):
        held[row['city']] += row['reserved']
    # Staged army grain takes priority if the labels overlap.
    for key, amount in held.items():
        city = state.cities[key]
        stock = reserve_grain(state, city)
        if stock > city.grain - amount:
            change_reserve(state, city, max(0, city.grain-amount), 'military_or_urgent')

    live = {row['id']: row for row in state.extension['logistics']['convoys'] if 'strategic' in row}
    for order in list(ledger['orders'].values()):
        if order['status'] == 'reserved':
            source, target = (state.cities[key] for key in (order['source'], order['target']))
            amount = order['load'] + order['rations']
            reason = ('ownership' if source.owner != order['owner'] or target.owner != order['owner'] else
                      'expired' if state.turn > order['reserved_turn'] + RULES['hold_turns'] else
                      'source_safety' if amount > source.grain - reserve_grain(state, source) - held[source.id] else None)
            if reason:
                _finish(state, order, 'cancelled', reason)
            else:
                held[source.id] += amount
            continue
        convoy = live.get(order['convoy_id'])
        if convoy is None:
            raise ValueError('Strategic dispatch without a terminal receipt')
        if order['delivered_turn'] is not None:
            continue
        journey = convoy['journeys'][-1]
        delayed = convoy['status'] in {'waiting', 'blocked'} or journey['supply']['waiting']
        diverted = convoy['target'] != order['target'] or len(convoy['journeys']) > 1
        status = ('diverted' if diverted else 'delayed'
                  if delayed or journey['arrival_turn'] > order['expected_turn'] else 'in_transit')
        reason = convoy['reason'] if delayed or diverted else None
        if (order['status'], order['reason']) != (status, reason):
            order.update(status=status, reason=reason)
            _note_order(state, order, 'order_progress')
    if enabled(state,'relay'):
        from . import granary_relay
        granary_relay.synchronize(state)


def reserve_order(state, owner, quote, priority):
    ledger = pool(state)
    if any(commitments(state, quote['source'])):
        raise GameError(STALE)
    order_id = ledger['next_id']
    if order_id > 1_000_000:
        raise GameError(INVALID)
    ledger['next_id'] += 1
    order = dict(id=order_id, owner=owner, source=quote['source'], target=quote['target'],
        status='reserved', priority=priority, reserved_turn=state.turn, dispatch_turn=None,
        load=quote['load'], rations=quote['rations'], expected_grain=quote['net'],
        expected_turn=quote['arrival_turn'], deadline=quote['deadline'], escort=quote['escort'],
        mode=quote['mode'], path=list(quote['path']), convoy_id=None, delivered_grain=0,
        delivered_turn=None, completed_turn=None, reason=None, reception=None, actual_cost=None,
        reference_price=quote['reference_price'])
    ledger['orders'][str(order_id)] = order
    _note_order(state, order, 'order_reserved')
    return order


def launch(game, state, order, quote):
    if order['status'] != 'reserved':
        raise GameError(STALE)
    return logistics.dispatch(game, state, dict(source=order['source'], target=order['target'],
        officers=[quote['escort']], cargo=dict(grain=quote['load'], gold=0, reserves=0),
        route_mode=quote['mode']), order['owner'], emergency_grain=quote['rations'],
        strategic_order=order['id'], strategic_path=quote['path'])


def transport_event(state, convoy, kind, amounts):
    order = _order(state, convoy['strategic'])
    if kind == 'transport_departed':
        order.update(status='dispatched', dispatch_turn=state.turn, convoy_id=convoy['id'])
        _note_order(state, order, 'order_dispatched')
    elif kind == 'transport_arrived':
        if order['delivered_turn'] is not None:
            raise ValueError('Duplicate strategic delivery')
        delivered = amounts['grain']
        order.update(status='delivered' if delivered >= order['expected_grain'] else 'partially_delivered',
                     delivered_grain=delivered, delivered_turn=state.turn, reason=None)
        _note_order(state, order, 'order_delivered')
        if enabled(state,'relay'):
            from . import granary_relay
            granary_relay.accept(state,order)


def transport_closed(state, convoy, outcome, city):
    from .regional_procurement import landed_cents
    order = _order(state, convoy['strategic'])
    receipt = logistics.grain_receipt(convoy, returned=city is not None, abandoned=city is None)
    spent = max(0, sum(j['supply']['consumed'] for j in convoy['journeys']))
    casualty = sum(sum(s.get('lost', 0) for s in j['supply']['starvation']) for j in convoy['journeys'])
    observe(state, 'escort_receipt', order_id=order['id'], convoy_id=convoy['id'], owner=order['owner'],
            city=city, outcome=outcome, original_escorts=convoy['original_officers'],
            retained_escorts=convoy['officers'],
            original_troops=sum(convoy['journeys'][0]['departure_troops'].values()),
            remaining_troops=sum(state.officers[ident].troops for ident in convoy['officers']),
            hunger_losses=casualty, escort_food=spent, **receipt)
    order.update(reception=city, actual_cost=landed_cents(0, spent, order['reference_price'], order['delivered_grain']))
    _finish(state, order, 'returned' if city else 'failed', outcome)
    if enabled(state,'relay'):
        from . import granary_relay
        granary_relay.terminal(state,order)


def execute(game, state, payload, owner):
    from . import granary_planning
    action = payload.get('action') if isinstance(payload, dict) else None
    if not enabled(state) or state.phase != 'city' or owner != state.player or type(action) is not str:
        raise GameError(INVALID)
    if action in {'set_target', 'hold', 'release'}:
        if set(payload) != {'action','city','amount'} or type(payload.get('amount')) is not int:
            raise GameError(INVALID)
        city = game._owned_city(state, payload['city'])
        prior, amount = reserve_grain(state, city), payload['amount']
        if not 0 <= amount <= logistics.LIMIT or action != 'set_target' and not amount:
            raise GameError(INVALID)
        if action in {'hold','set_target'}:
            plan = granary_planning._plan(game,state,owner)
            capacity = granary_planning.profile(game,state,city,plan.budgets[city.id],plan.cities[city.id])['capacity']
            if amount+(prior if action=='hold' else 0) > capacity:
                raise GameError(INSUFFICIENT)
        if action == 'hold':
            if amount > available(state, city):
                raise GameError(INSUFFICIENT)
            change_reserve(state, city, prior+amount, 'manual')
        elif action == 'release':
            if amount > prior:
                raise GameError(INSUFFICIENT)
            change_reserve(state, city, prior-amount, 'manual')
        else:
            change_reserve(state, city, prior, 'manual', target=amount or None, set_target=True)
        return
    if action == 'reserve':
        if set(payload) != {'action','target','source','quantity','token'} or type(payload.get('token')) is not str:
            raise GameError(INVALID)
        quotes = granary_planning.preview(game,state,owner,payload['target'],payload['quantity'],payload['source'])
        quote = next((row for row in quotes['quotes'] if row['token'] == payload['token']), None)
        if quote is None:
            raise GameError(STALE)
        reserve_order(state, owner, quote, 'manual')
        return
    if action in {'cancel', 'dispatch'} and set(payload) == {'action','order'} and type(payload['order']) is int:
        order = _order(state, payload['order'])
        if not order or order['owner'] != owner or order['status'] != 'reserved':
            raise GameError(STALE)
        if action == 'cancel':
            _finish(state, order, 'cancelled', 'manual')
        else:
            quotes = granary_planning.preview(game,state,owner,order['target'],order['expected_grain'],
                                              order['source'], except_id=order['id'])
            quote = next((q for q in quotes['quotes'] if q['escort'] == order['escort'] and q['mode'] == order['mode']
                          and q['load'] == order['load'] and q['rations'] == order['rations']
                          and q['path'] == order['path']), None)
            if quote is None:
                raise GameError(STALE)
            order.update(expected_grain=quote['net'], expected_turn=quote['arrival_turn'])
            launch(game, state, order, quote)
        return
    raise GameError(INVALID)


def validate(state):
    if FIELD not in state.extension:
        if POOL in state.extension or any('strategic' in row for row in state.extension['logistics']['convoys']):
            raise ValueError('Missing granary version')
        return
    if (type(state.extension[FIELD]) is not int or not enabled(state)
            or economy_rules.version(state) != economy_rules.CURRENT
            or logistics_rules.version(state) != logistics_rules.CURRENT):
        raise ValueError('Granary version')
    data = pool(state)
    if (not isinstance(data, dict) or set(data) != {'features','cities','orders','history','relays','next_id'}
            or set(data['features']) != FEATURES or any(type(v) is not bool for v in data['features'].values())
            or type(data['next_id']) is not int or not 1 <= data['next_id'] <= 1_000_001
            or not isinstance(data['cities'], dict) or not isinstance(data['orders'], dict)
            or not isinstance(data['history'], list) or len(data['history']) > RULES['history']):
        raise ValueError('Granary ledger')
    def quantity(x, upper=logistics.LIMIT):
        return type(x) is int and 0 <= x <= upper
    held = defaultdict(int)
    for stage in staging_supply.active(state):
        held[stage['city']] += stage['reserved']
    for key, row in data['cities'].items():
        if (key not in state.cities or not isinstance(row, dict)
                or set(row) != {'owner','grain','manual_target','turn','reason'}
                or row['owner'] != state.cities[key].owner or row['owner'] == 'neutral'
                or not quantity(row['grain'], state.cities[key].grain - held[key])
                or row['manual_target'] is not None and not quantity(row['manual_target'])
                or not quantity(row['turn'],state.turn) or row['reason'] not in REASONS):
            raise ValueError('City reserve')
        held[key] += row['grain']
    convoys = {row['id']:row for row in state.extension['logistics']['convoys'] if 'strategic' in row}
    seen, linked, sources = set(), set(), set()
    fields = {'id','owner','source','target','status','priority','reserved_turn','dispatch_turn','load','rations',
        'expected_grain','expected_turn','deadline','escort','mode','path','convoy_id','delivered_grain','delivered_turn',
        'completed_turn','reason','reception','actual_cost','reference_price'}
    entries = [(key,row,True) for key,row in data['orders'].items()]
    entries.extend((None,row,False) for row in data['history'])
    for key, row, active in entries:
        if (not isinstance(row, dict) or set(row) != fields or not quantity(row['id'],data['next_id']-1)
                or not row['id'] or row['id'] in seen or active and key != str(row['id'])
                or row['status'] not in (ACTIVE if active else TERMINAL)
                or row['priority'] not in {'manual','proactive','winter','relay'}
                or row['source'] == row['target'] or row['source'] not in state.cities or row['target'] not in state.cities
                or row['owner'] == 'neutral' or row['mode'] not in {'land','fastest'}
                or row['escort'] not in state.officers or not isinstance(row['path'],list)
                or len(row['path']) < 2 or row['path'][0] != row['source'] or row['path'][-1] != row['target']
                or any(city not in state.cities for city in row['path'])
                or any(not quantity(row[field]) for field in ('load','rations','expected_grain','delivered_grain','reference_price'))
                or not 0 < row['expected_grain'] <= row['load'] or row['delivered_grain'] > row['load']
                or not quantity(row['reserved_turn'], state.turn) or not row['reserved_turn']
                or not quantity(row['expected_turn']) or row['expected_turn'] <= row['reserved_turn']
                or not quantity(row['deadline']) or row['deadline'] < row['reserved_turn']
                or any(row[field] is not None and not quantity(row[field], state.turn)
                       for field in ('dispatch_turn','delivered_turn','completed_turn'))
                or row['reason'] is not None and type(row['reason']) is not str
                or row['reception'] is not None and row['reception'] not in state.cities
                or row['actual_cost'] is not None and not quantity(row['actual_cost'])):
            raise ValueError('Strategic order')
        seen.add(row['id'])
        if row['status'] == 'reserved':
            source = state.cities[row['source']]
            held[source.id] += row['load'] + row['rations']
            if (source.id in sources or source.owner != row['owner'] or state.cities[row['target']].owner != row['owner']
                    or held[source.id] > source.grain or any(row[k] is not None for k in
                    ('convoy_id','dispatch_turn','delivered_turn','completed_turn')) or row['delivered_grain']):
                raise ValueError('Strategic commitment')
            sources.add(source.id)
        elif active:
            convoy = convoys.get(row['convoy_id'])
            if (convoy is None or convoy['owner'] != row['owner'] or convoy['strategic'] != row['id']
                    or row['convoy_id'] in linked or row['completed_turn'] is not None
                    or convoy['source'] != row['source'] or convoy['original_target'] != row['target']
                    or convoy['initial_cargo']['grain'] != row['load']
                    or convoy['journeys'][0]['supply']['loaded'] != row['rations']
                    or convoy['journeys'][0]['departure_turn'] != row['dispatch_turn']
                    or (row['delivered_turn'] is not None) != convoy['delivery_done']
                    or row['delivered_grain'] != convoy['delivered']['grain']):
                raise ValueError('Strategic convoy link')
            linked.add(row['convoy_id'])
        elif row['completed_turn'] is None:
            raise ValueError('Strategic order without completion')
    if linked != convoys.keys():
        raise ValueError('Untracked strategic convoy')
    from . import granary_relay
    granary_relay.validate(state)
