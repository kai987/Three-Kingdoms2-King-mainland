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
             choose_successor=0)


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
        row['used'] += amount
        row['orders'].append(dict(city=city.id, kind=kind, cost=amount))
        # Retained as a historical activity marker, never as an eligibility lock.
        city.action_used = True
    return amount


def view(game, state):
    factions = {}
    if state is not None:
        for owner, row in state.extension['command_books']['factions'].items():
            factions[owner] = {key: row[key] for key in ('city_count', 'total', 'used')}
            factions[owner]['remaining'] = remaining(state, owner)
    return dict(schema=SCHEMA, turn=state.turn if state else None,
                maximum=MAXIMUM, refresh_days=10, costs=dict(COSTS), factions=factions)


def validate(game, state):
    pool = state.extension.get('command_books')
    if (not isinstance(pool, dict) or set(pool) != {'schema', 'turn', 'factions'}
            or pool['schema'] != SCHEMA or type(pool['turn']) is not int
            or pool['turn'] != state.turn or not isinstance(pool['factions'], dict)
            or set(pool['factions']) != set(game.catalog.factions) - {'neutral'}):
        raise ValueError('Invalid faction command-book pool')
    snapshot = set()
    for row in pool['factions'].values():
        if (not isinstance(row, dict) or set(row) != {'city_count', 'city_ids', 'total', 'legacy_used', 'used', 'orders'}
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
        for order in row['orders']:
            if (not isinstance(order, dict) or set(order) != {'city', 'kind', 'cost'}
                    or not isinstance(order['city'], str) or order['city'] not in state.cities
                    or not isinstance(order['kind'], str) or order['kind'] not in COSTS
                    or type(order['cost']) is not int or order['cost'] <= 0
                    or order['cost'] != cost(order['kind'])):
                raise ValueError('Invalid strategic order receipt')
            used += order['cost']
        if used != row['used']:
            raise ValueError('Strategic order ledger does not balance')
