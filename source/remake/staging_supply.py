"""Reserve real grain at reachable checkpoints for approved AI columns."""
from collections import defaultdict

from . import logistics_rules as rules, logistics_strategy, march_supply

FIELD = 'ai_supply_nodes'
EXPIRY_DAYS = 10


def assess(game, state, city, ids, quote, budgets):
    """Return the original first-leg load and the unfunded part at each owned stop."""
    loaded = march_supply.estimate(state, ids, quote, game=game)
    units = march_supply.ration_units(state, ids)
    divisor = march_supply.denominator() * rules.RATION_SCALE
    parts = rules.plan(quote, march_supply.travel_rules(game))
    stock = loaded * divisor
    progress = 0
    rows = []
    provisional = defaultdict(int)
    started = (state.turn - 1) * 10
    for index, leg in enumerate(quote['routes'][:-1]):
        stock -= units * rules.weight(parts, progress, leg['days'])
        progress += leg['days']
        key = quote['path'][index + 1]
        budget = budgets.get(key)
        if budget is None or state.cities[key].owner != city.owner:
            continue
        onward = march_supply.next_supply_days(state, quote, city.owner, progress)
        missing = max(0, rules.ceil_div(units * rules.weight(parts, progress, onward) - stock, divisor))
        if missing:
            space = max(0, exportable(state, state.cities[key], budget) - provisional[key])
            covered = min(missing, space)
            rows.append(dict(city=key, route_day=progress, arrival=started + progress,
                             required=missing, reserved=covered, expires=started + progress + EXPIRY_DAYS))
            provisional[key] += covered
            stock += missing * divisor
    return loaded, rows


def route_key(quote):
    return tuple(quote['path'])


def active(state):
    rows = state.extension.get(FIELD)
    if not rows:
        return
    marches = {row['id']: row for row in state.extension['travel']['marches']}
    for item in rows:
        row = marches.get(item['army'])
        if (row and row['owner'] == item['owner'] == state.cities[item['city']].owner
                and row['status'] == 'outbound' and not row['supply']['retreat_requested']
                and row['departure_turn'] == item['turn'] and route_key(row['quote']) == tuple(item['path'])
                and row['supply']['route_days'] <= item['route_day']
                and row['supply']['clock_tick'] < item['expires']):
            yield item


def held(state, city, except_army=None):
    return sum(row['reserved'] for row in active(state) if row['city'] == city and row['army'] != except_army)


def exportable(state, city, budget):
    floor = max(budget['minimum_export_floor'], budget['safety_reserve'], budget['next_installment'])
    other = budget['reserved_grain'] - budget.get('staging_grain',0)
    return max(0, city.grain - other - floor - held(state,city.id))


def available(state, city, *, army=None):
    return max(0, city.grain - held(state, city.id, army))


def reserve(state, row, proposals):
    if not proposals:
        return
    assert all(item['required'] == item['reserved'] for item in proposals)
    plan = f"{row['owner']}:{state.turn}:{row['target']}"
    entries = state.extension.setdefault(FIELD, [])
    for item in proposals:
        booking = dict(item, army=row['id'], plan=plan, owner=row['owner'], turn=state.turn,
                       path=list(row['quote']['path']))
        entries.append(booking)
        logistics_strategy.observe('staging_node', state, status='reserved', **booking)


def settle(state, unit, city_id, grain, tick):
    for item in active(state):
        if item['army'] != unit['id'] or item['city'] != city_id or item['route_day'] != unit['supply']['route_days']:
            continue
        state.extension[FIELD].remove(item)
        logistics_strategy.observe('staging_node', state, status='settled', actual_grain=grain,
                                   actual_tick=tick, **item)
        return


def synchronize(state):
    if FIELD not in state.extension:
        return
    live = {id(row) for row in active(state)}
    available = {key: state.cities[key].grain for key in {row['city'] for row in state.extension[FIELD]}}
    keep = []
    for row in state.extension[FIELD]:
        if id(row) not in live:
            logistics_strategy.observe('staging_node', state, status='released', **row)
            continue
        stock = min(row['reserved'], available[row['city']])
        if stock != row['reserved']:
            logistics_strategy.observe('staging_node', state, status='reduced', remaining=stock, **row)
        if stock:
            keep.append(dict(row, reserved=stock))
            available[row['city']] -= stock
    if keep:
        state.extension[FIELD] = keep
    else:
        del state.extension[FIELD]


def validate(state):
    if FIELD not in state.extension:
        return
    rows = state.extension[FIELD]
    keys = {'army','plan','owner','turn','path','city','route_day','arrival','required','reserved','expires'}
    if not logistics_strategy.staging(state) or not isinstance(rows,list) or not rows:
        raise ValueError('Military supply-node reservations')
    positions = set()
    for row in rows:
        if (not isinstance(row,dict) or set(row)!=keys or not isinstance(row['path'],list)
                or any(not isinstance(i,str) or i not in state.cities for i in row['path'])
                or type(row['city']) is not str or row['city'] not in row['path'][1:-1]
                or not isinstance(row['owner'],str) or not isinstance(row['plan'],str)
                or any(type(row[key]) is not int or row[key]<=0 for key in
                       ('army','turn','route_day','arrival','required','reserved','expires'))
                or row['plan']!=f"{row['owner']}:{row['turn']}:{row['path'][-1]}"
                or row['reserved']>row['required'] or row['turn']>state.turn
                or row['arrival']!=(row['turn']-1)*10+row['route_day']
                or row['expires']!=row['arrival']+EXPIRY_DAYS
                or (row['army'],row['route_day']) in positions):
            raise ValueError('Military supply-node reservation')
        positions.add((row['army'],row['route_day']))
    troops = {row['id']:row for row in state.extension['travel']['marches']}
    stock = defaultdict(int)
    for row in active(state):
        march = troops[row['army']]
        stock[row['city']] += row['reserved']
        position = 0
        for key, leg in zip(march['quote']['path'][1:], march['quote']['routes']):
            position += leg['days']
            if position==row['route_day'] and key==row['city']:
                break
        else:
            raise ValueError('Military supply node is outside the approved route')
    if len(list(active(state)))!=len(rows) or any(qty>state.cities[key].grain for key,qty in stock.items()):
        raise ValueError('Unbacked military supply-node reservation')
