"""Readonly quotes against a strategic-turn snapshot of physical market stock."""
from contextlib import contextmanager
from contextvars import ContextVar

from . import economic_regions, economy_rules

FIELD = 'regional_market_rules_version'
STAGE = 'regional_market_experiment_stage'
AUTOMATION = 'regional_trade_automation'
POOL = 'regional_market'
VERSION = 301
PRICE_ONLY, PROCUREMENT, TRADE = (1, 2, 3)
BANDS = ('severe', 'tight', 'lean', 'normal', 'ample', 'surplus')
ADJUSTMENTS = (4, 3, 1, 0, -1, -2)
STALE_QUOTE = '糧價或交易條件已更新，請確認新報價。'
_experiment = ContextVar('regional_market_experiment', default=0)
_observer = ContextVar('regional_market_observer', default=None)


@contextmanager
def experiment(level):
    if type(level) is not int or not 0 <= level <= TRADE:
        raise ValueError('Regional market experiment')
    token = _experiment.set(level)
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


def observed():
    return _observer.get() is not None


def report(event, state, **fields):
    callback = _observer.get()
    if callback is not None:
        callback(event, dict(turn=state.turn, year=state.year, month=state.month, day=state.day, **fields))


def stage(state):
    fields = state.extension
    if fields.get(FIELD) != VERSION:
        return 0
    if fields.get(AUTOMATION):
        return TRADE
    return fields.get(STAGE, PROCUREMENT)


def pool(state):
    return state.extension[POOL]


def month_key(state):
    return state.year * 12 + state.month - 1


def initialize(state, level=None):
    level = _experiment.get() if level is None else level
    fields = state.extension
    for key in (FIELD, STAGE, AUTOMATION, POOL):
        fields.pop(key, None)
    if not level:
        return
    fields[FIELD] = VERSION
    if level == PRICE_ONLY:
        fields[STAGE] = PRICE_ONLY
    elif level == TRADE:
        fields[AUTOMATION] = True
    fields[POOL] = dict(map_version=economic_regions.VERSION, turn=0, snapshots={},
                        history={}, orders={}, next_id=1, quota_month=month_key(state), quotas={})
    refresh(state)


def inventory_band(stock, supply):
    if not supply:
        return 5 if stock else 0
    if stock * 4 < supply:
        return 0
    if stock * 2 < supply:
        return 1
    if stock < supply:
        return 2
    if stock < 2 * supply:
        return 3
    return 4 if stock * 2 < 5 * supply else 5


def prices(base_buy, base_sell, season, adjustment):
    sell = max(1, min(99, base_sell + season + adjustment))
    return max(sell + 1, min(100, base_buy + season + adjustment)), sell


def refresh(state):
    if not stage(state):
        return
    ledger = pool(state)
    if ledger['turn'] == state.turn:
        return
    ledger['turn'] = state.turn
    ledger['snapshots'] = {key: [row['stock'], row['monthly_supply']]
                           for key, row in state.extension['grain_market'].items()}
    if ledger['quota_month'] != month_key(state):
        ledger['quota_month'] = month_key(state)
        ledger['quotas'] = {}


def close_month(state, key, prior):
    if not stage(state) or not prior or not (prior['purchased'] or prior['sold']):
        return
    history = pool(state)['history'].setdefault(key, [])
    history.append([prior['last_restock_month'], prior['purchased'], prior['sold']])
    del history[:-2]


def snapshot(game, state, city, town=None):
    if not stage(state):
        return None
    from . import facilities
    town = facilities._pool(state)['cities'][city]['town'] if town is None else town
    stock, supply = pool(state)['snapshots'][city]
    band = inventory_band(stock, supply)
    base_buy, base_sell = (facilities.market_base(game, town, direction, state) for direction in ('buy', 'sell'))
    season = facilities.MARKET_MONTHLY_ADJUSTMENTS[state.month - 1]
    adjust = ADJUSTMENTS[band]
    buy, sell = prices(base_buy, base_sell, season, adjust)
    return dict(turn=state.turn, town=town, snapshot_stock=stock, supply=supply, band=BANDS[band],
                base_buy=base_buy, base_sell=base_sell, season=season, adjustment=adjust, buy=buy, sell=sell,
                token=f'{state.turn}:{city}:{town}:{buy}:{sell}')


def validate(state):
    fields = state.extension
    if FIELD not in fields:
        if {STAGE, AUTOMATION, POOL} & fields.keys():
            raise ValueError('Missing regional market version')
        return
    if (type(fields[FIELD]) is not int or fields[FIELD] != VERSION
            or economy_rules.version(state) != economy_rules.CURRENT
            or STAGE in fields and (type(fields[STAGE]) is not int or fields[STAGE] != PRICE_ONLY)
            or AUTOMATION in fields and (fields[AUTOMATION] is not True or STAGE in fields)):
        raise ValueError('Regional market version')
    ledger = pool(state)
    if (not isinstance(ledger, dict)
            or set(ledger) != {'map_version','turn','snapshots','history','orders','next_id','quota_month','quotas'}
            or ledger['map_version'] != economic_regions.VERSION or ledger['turn'] != state.turn
            or ledger['quota_month'] != month_key(state)):
        raise ValueError('Regional market state')
    markets = state.extension['grain_market']
    snapshots = ledger['snapshots']
    if (not isinstance(snapshots, dict) or set(snapshots) != set(markets)
            or any(not isinstance(values, list) or len(values) != 2
                   or any(type(n) is not int for n in values)
                   or values[1] != markets[key]['monthly_supply']
                   or not 0 <= values[0] <= markets[key]['capacity'] for key, values in snapshots.items())):
        raise ValueError('Regional price snapshot')
    history = ledger['history']
    if not isinstance(history, dict) or not history.keys() <= markets.keys():
        raise ValueError('Regional market history')
    for records in history.values():
        if (not isinstance(records, list) or not 1 <= len(records) <= 2
                or any(not isinstance(row, list) or len(row) != 3 or any(type(n) is not int for n in row)
                       or not 0 < row[0] < month_key(state) or min(row[1:]) < 0 for row in records)
                or [row[0] for row in records] != sorted({row[0] for row in records})):
            raise ValueError('Regional market history entry')
