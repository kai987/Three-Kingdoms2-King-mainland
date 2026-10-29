"""Faction-wide strategic orders; views never grant or consume an order.

The owned-city table is read from the user-provided original ROM, bank25
$A0E4 (file0x320F4). The expanded map retains its maximum of13. The remake's
already established ten-day turn is the refresh boundary instead of a month.
"""
from .errors import GameError

SCHEMA = 'tk2-command-books-v1'
TOTAL_BY_CITIES = (0, 3, 3, 3, 4, 5, 7, 7, 7, 8, 8, 8, 8, 9, 9, 9,
                   9, 10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13)
MAXIMUM = 13
COSTS = dict(recruit=1, recruit_officer=1, persuade_officer=1, staff_recruit=1,
             hire_staff=1, depart=1, transfer=1, dispatch_transport=1,
             search_treasure=1, reward_officer=1, sell_treasure=1,
             develop_town=1, treat_officer=1, study_officer=1, trade_grain=1,
             buy_equipment=1, improve_prevention=1, equip_owned=1,
             allocate=1, resupply_march=1, transport_treasure=1,
             set_domestic=0, set_logistics=0, set_governor=0,
             set_treasury_policy=0, set_facility_policy=0, reject_staff=0,
             choose_successor=0, allocation_close=0)


def total(cities):
    if type(cities) is not int or not 0 <= cities <= 512:
        raise ValueError('Invalid command-book city count')
    return TOTAL_BY_CITIES[min(cities, 30)]


def cost(kind):
    if type(kind) is int and 0 <= kind <= MAXIMUM:
        return kind
    if type(kind) is str and kind in COSTS:
        return COSTS[kind]
    raise ValueError('Unknown strategic order cost')


def initialize(game, state, *, legacy=False):
    """Opening/turn reset only; one conservative import for current old saves."""
    factions = {}
    for owner in sorted(game.catalog.factions):
        if owner == 'neutral':
            continue
        holdings = [c for c in state.cities.values() if c.owner == owner]
        grant = total(len(holdings))
        used = min(grant, sum(c.action_used for c in holdings)) if legacy else 0
        factions[owner] = dict(city_count=len(holdings), city_ids=sorted(c.id for c in holdings), total=grant,
                               legacy_used=used, used=used, orders=[])
    state.extension['command_books'] = dict(schema=SCHEMA, turn=state.turn, factions=factions)


def remaining(state, owner):
    row = state.extension.get('command_books', {}).get('factions', {}).get(owner)
    if row is None or owner in state.extension.get('ended_factions', []):
        return 0
    return max(0, row['total'] - row['used'])


def can_spend(state, owner, kind=1):
    amount = cost(kind)
    return bool(owner != 'neutral' and owner in state.extension.get('command_books', {}).get('factions', {})
                and owner not in state.extension.get('ended_factions', [])
                and remaining(state, owner) >= amount)


def require(state, owner, kind=1):
    if not can_spend(state, owner, kind):
        raise GameError('本勢力命令書不足。')


def spend(state, city, kind):
    """Shared service commit point, called once per accepted strategic order."""
    if type(kind) is not str or kind not in COSTS:
        raise ValueError('Unknown strategic order receipt kind')
    amount = cost(kind)
    require(state, city.owner, amount)
    if amount:
        row = state.extension['command_books']['factions'][city.owner]
        close_allocation(state, city.owner)
        row['used'] += amount
        row['orders'].append(dict(city=city.id, kind=kind, cost=amount))
        # Retained as a historical activity marker, never as an eligibility lock.
        city.action_used = True
    return amount


def active_allocation(state, owner, city=None):
    """The current paid city-wide distribution, never a client-created credit."""
    row = state.extension['command_books']['factions'].get(owner, {})
    active = row.get('allocation', {}).get('active')
    if active is None or city is not None and active['city'] != city:
        return None
    receipt = row['orders'][active['receipt']]
    return dict(id=active['id'], city=active['city'], source=receipt['kind'])


def open_allocation(state, city):
    """Attach a flow only to the just-paid recruit/allocation receipt.

    Optional ledger metadata preserves the exact representation of existing
    current-format saves that have never used the city-wide interface.
    """
    row = state.extension['command_books']['factions'][city.owner]
    receipt = row['orders'][-1]
    if receipt['city'] != city.id or receipt['kind'] not in ('allocate', 'recruit'):
        raise ValueError('Allocation flow requires a paid city recruitment/allocation receipt')
    allocation = row.setdefault('allocation', dict(serial=0, active=None))
    serial = allocation['serial'] + 1
    identity = f'{state.turn}:{city.owner}:{city.id}:{serial}'
    receipt['allocation_flow'] = identity
    allocation.update(serial=serial, active=dict(id=identity, city=city.id, receipt=len(row['orders']) - 1))
    return identity


def require_allocation(state, city, identity):
    active = active_allocation(state, city.owner, city.id)
    if not isinstance(identity, str) or active is None or identity != active['id']:
        raise GameError('配兵流程已結束，請重新開啟編兵。')


def close_allocation(state, owner, *, city=None, identity=None):
    """An old dialog's close callback cannot close a newer distribution."""
    row = state.extension['command_books']['factions'].get(owner, {})
    allocation = row.get('allocation')
    active = allocation.get('active') if allocation else None
    if active is None or city is not None and active['city'] != city or identity is not None and active['id'] != identity:
        return False
    allocation['active'] = None
    return True


def view(game, state):
    factions = {}
    if state is not None:
        for owner, row in state.extension['command_books']['factions'].items():
            factions[owner] = {key: row[key] for key in ('city_count', 'total', 'used')}
            factions[owner]['remaining'] = remaining(state, owner)
            active = active_allocation(state, owner)
            if active is not None:
                factions[owner]['allocation_flow'] = active
    return dict(schema=SCHEMA, turn=state.turn if state else None,
                maximum=MAXIMUM, refresh_days=10, allocation_batch='confirm-v1',
                costs=dict(COSTS), factions=factions)


def validate(game, state):
    pool = state.extension.get('command_books')
    if (not isinstance(pool, dict) or set(pool) != {'schema', 'turn', 'factions'}
            or pool['schema'] != SCHEMA or type(pool['turn']) is not int
            or pool['turn'] != state.turn or not isinstance(pool['factions'], dict)
            or set(pool['factions']) != set(game.catalog.factions) - {'neutral'}):
        raise ValueError('Invalid faction command-book pool')
    snapshot = set()
    for owner, row in pool['factions'].items():
        fields = {'city_count', 'city_ids', 'total', 'legacy_used', 'used', 'orders'}
        if (not isinstance(row, dict) or set(row) not in (fields, fields | {'allocation'})
                or type(row['city_count']) is not int or not 0 <= row['city_count'] <= len(game.catalog.map_cities)
                or not isinstance(row['city_ids'], list) or len(row['city_ids']) != row['city_count']
                or any(type(key) is not str or key not in state.cities for key in row['city_ids'])
                or row['city_ids'] != sorted(set(row['city_ids']))
                or snapshot.intersection(row['city_ids'])
                or type(row['total']) is not int or row['total'] != total(row['city_count'])
                or type(row['legacy_used']) is not int or not 0 <= row['legacy_used'] <= min(row['total'], row['city_count'])
                or type(row['used']) is not int or not row['legacy_used'] <= row['used'] <= row['total']
                or not isinstance(row['orders'], list) or len(row['orders']) > MAXIMUM):
            raise ValueError('Invalid faction command-book balance')
        snapshot.update(row['city_ids'])
        used = row['legacy_used']
        tagged = []
        for order in row['orders']:
            order_fields = {'city', 'kind', 'cost'}
            if (not isinstance(order, dict) or set(order) not in (order_fields, order_fields | {'allocation_flow'})
                    or not isinstance(order['city'], str) or order['city'] not in state.cities
                    or not isinstance(order['kind'], str) or order['kind'] not in COSTS
                    or type(order['cost']) is not int or order['cost'] <= 0
                    or order['cost'] != cost(order['kind'])):
                raise ValueError('Invalid strategic order receipt')
            used += order['cost']
            if 'allocation_flow' in order:
                if order['kind'] not in ('allocate', 'recruit'):
                    raise ValueError('Invalid allocation receipt kind')
                tagged.append(order)
        if used != row['used']:
            raise ValueError('Strategic order ledger does not balance')
        if 'allocation' not in row:
            if tagged:
                raise ValueError('Allocation receipt has no flow ledger')
            continue
        allocation = row['allocation']
        if (not isinstance(allocation, dict) or set(allocation) != {'serial', 'active'}
                or type(allocation['serial']) is not int or not 1 <= allocation['serial'] <= MAXIMUM
                or allocation['serial'] != len(tagged)):
            raise ValueError('Invalid allocation flow ledger')
        for serial, order in enumerate(tagged, 1):
            expected = f'{state.turn}:{owner}:{order["city"]}:{serial}'
            if order['allocation_flow'] != expected:
                raise ValueError('Invalid allocation flow identity')
        active = allocation['active']
        if active is not None:
            if (not isinstance(active, dict) or set(active) != {'id', 'city', 'receipt'}
                    or type(active['receipt']) is not int or active['receipt'] != len(row['orders']) - 1
                    or not row['orders'] or row['orders'][-1] is not tagged[-1]
                    or active['id'] != tagged[-1]['allocation_flow'] or active['city'] != tagged[-1]['city']
                    or state.cities[active['city']].owner != owner):
                raise ValueError('Invalid active allocation flow')
