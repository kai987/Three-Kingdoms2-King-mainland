"""Finite, city-owned-by-ID grain inventories separate from public warehouses."""

from . import economy_rules, market_pricing
from .city_economy import monthly_income, town_level

FIELD = 'grain_market'
_FIELDS = {'stock', 'capacity', 'monthly_supply', 'last_restock_month', 'opening_stock',
           'restocked', 'purchased', 'sold', 'overflow'}


def _month(state):
    return state.year * 12 + state.month - 1


def supply(town, regular_grain):
    base, percent = economy_rules.TOWN_MARKET_SUPPLY[town]
    return base + regular_grain * percent // 100


def row(state, city_id):
    return state.extension.get(FIELD, {}).get(city_id)


def _restock(remaining, monthly, month):
    capacity = monthly * economy_rules.MARKET_CAPACITY_MONTHS
    overflow = max(0, remaining - capacity)
    restocked = min(monthly, capacity - remaining + overflow)
    return dict(stock=remaining - overflow + restocked, capacity=capacity, monthly_supply=monthly,
                last_restock_month=month, opening_stock=remaining, restocked=restocked,
                purchased=0, sold=0, overflow=overflow)


def initialize(game, state):
    if economy_rules.version(state) == economy_rules.CURRENT:
        state.extension.setdefault(FIELD, {})
        restock(game, state)


def restock(game, state, regular_incomes=None):
    """Post at most one issuance per city per calendar month."""
    pool = state.extension.get(FIELD)
    if pool is None:
        return
    month = _month(state)
    for key, city in state.cities.items():
        previous = pool.get(key)
        if previous is not None and previous['last_restock_month'] >= month:
            continue
        grain = 0
        if city.owner != 'neutral':
            income = monthly_income(game, key, state) if regular_incomes is None else regular_incomes[key]
            grain = income['grain']
        monthly = supply(town_level(game, state, key), grain)
        market_pricing.close_month(state, key, previous)
        pool[key] = _restock(0 if previous is None else previous['stock'], monthly, month)
        if market_pricing.observed():
            market_pricing.report('stock_flow', state, city=key, owner=city.owner, kind='restock',
                                  **pool[key])


def available(state, city_id, direction):
    market = row(state, city_id)
    if market is None:
        return None
    return market['stock'] if direction == 'buy' else market['capacity'] - market['stock']


def transfer(state, city_id, direction, grain, *, gold=None, rate=None, channel=None, payer=None):
    """Move an already-quoted amount between the market and its buyer/seller."""
    market = row(state, city_id)
    if market is None:
        return
    if type(grain) is not int or not 0 < grain <= available(state, city_id, direction):
        raise ValueError('Market stock transfer')
    before = market['stock']
    if direction == 'buy':
        market['purchased'] += grain
        market['stock'] -= grain
    else:
        market['sold'] += grain
        market['stock'] += grain
    if market_pricing.observed():
        market_pricing.report('stock_flow', state, city=city_id, owner=state.cities[city_id].owner,
                              kind=direction, grain=grain, gold=gold, rate=rate, channel=channel, payer=payer,
                              opening_stock=before, stock=market['stock'], capacity=market['capacity'],
                              monthly_supply=market['monthly_supply'])


def purchase_limit(buyer_gold, warehouse, trade_limit, market):
    limits = [(buyer_gold, 'insufficient_gold'), (warehouse, 'warehouse_full'), (trade_limit, 'trade_limit')]
    if market is not None:
        limits.insert(0, (market, 'market_empty'))
    return min(limits, key=lambda limit: limit[0])


def validate(state):
    pool = state.extension.get(FIELD)
    if economy_rules.version(state) != economy_rules.CURRENT:
        if FIELD in state.extension:
            raise ValueError('Market inventory requires economy V2')
        return
    if not isinstance(pool, dict) or set(pool) != set(state.cities):
        raise ValueError('Missing city market inventory')
    for market in pool.values():
        if (not isinstance(market, dict) or set(market) != _FIELDS
                or any(type(value) is not int or value < 0 for value in market.values())
                or not 0 < market['last_restock_month'] <= _month(state)):
            raise ValueError('Market inventory fields')
        receipt = _restock(market['opening_stock'], market['monthly_supply'], market['last_restock_month'])
        if (market['monthly_supply'] < min(base for base, _ in economy_rules.TOWN_MARKET_SUPPLY.values())
                or market['capacity'] != receipt['capacity'] or market['restocked'] != receipt['restocked']
                or market['overflow'] != receipt['overflow'] or market['stock'] > market['capacity']
                or market['stock'] != receipt['stock'] - market['purchased'] + market['sold']):
            raise ValueError('Market stock conservation')
