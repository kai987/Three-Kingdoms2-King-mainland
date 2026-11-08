"""Real, deterministic provisions carried from a march into its battle.

The original game's exhausted provisions cause withdrawal. The exact ration
formula is an author adaptation: reuse the campaign's daily march formula,
including its fractional ration credit, rather than introduce a second rate.
Reading/quoting a battle never loads provisions or advances randomness.
"""
from .errors import GameError
from .march_supply import DENOMINATOR, OFFICER_UNITS, LIMIT, estimate
from .officers import MAX_BATTLE_OFFICERS, OFFICER_TROOP_CAP

SCHEMA = 'tk2-battle-supply-v1'
BUDGET_DAYS = 30
MAX_BATTLE_DAILY_UNITS = MAX_BATTLE_OFFICERS * (OFFICER_TROOP_CAP + OFFICER_UNITS)
SIDES = ('attackers', 'defenders')
_SIDE_FIELDS = {'owner', 'origin', 'loaded', 'initial_credit', 'received', 'consumed',
                'remaining', 'credit_units', 'journal'}


def rules():
    return dict(schema=SCHEMA, budget_days=BUDGET_DAYS, denominator=DENOMINATOR,
                officer_units=OFFICER_UNITS, limit=LIMIT, shortage='withdraw')


def departure_quote(state, ids, route_quote, *, battle_grain=None):
    """Quote attack loading after segment food, without spending or RNG.

    The caller validates the deployment and route. Transfers do not call this
    function and continue to load only the existing segment budget.
    """
    source = state.cities[route_quote['path'][0]]
    march = estimate(state, ids, route_quote)
    units = sum(state.officers[i].troops for i in ids) + OFFICER_UNITS * len(ids)
    maximum = max(0, min(LIMIT - march, source.grain - march))
    default = min((units * BUDGET_DAYS + DENOMINATOR - 1) // DENOMINATOR, maximum)
    selected = default if battle_grain is None else battle_grain
    if type(selected) is not int or not 0 <= selected <= maximum:
        raise GameError('戰鬥備糧超出可用兵糧或上限。')
    return dict(march_grain=march, battle_grain=selected, battle_grain_default=default,
                battle_grain_max=maximum, battle_daily_units=units,
                battle_days_budget=BUDGET_DAYS, total_grain=march + selected,
                available_grain=source.grain)


def daily_units(battle, side):
    active = [unit for unit in battle[side] if unit['troops'] > 0]
    return sum(unit['troops'] for unit in active) + OFFICER_UNITS * len(active)


def _new_side(state, battle, side, march_supply=None):
    origin = battle['source' if side == 'attackers' else 'target']
    owner = battle['attacker' if side == 'attackers' else 'defender']
    city = state.cities[origin]
    if march_supply is not None:
        loaded, credit = march_supply['remaining'], march_supply['credit_units']
    else:
        wanted = (daily_units(battle, side) * BUDGET_DAYS + DENOMINATOR - 1) // DENOMINATOR
        loaded = min(city.grain, wanted) if city.owner == owner else 0
        credit = 0
        city.grain -= loaded
    return dict(owner=owner, origin=origin, loaded=loaded, initial_credit=credit,
                received=0, consumed=0, remaining=loaded,
                credit_units=credit, journal=[])


def initialize(state, battle, *, march_supply=None):
    """Load a new battle once; arrival passes its already paid march balance."""
    if 'supply' in battle['extended']:
        return battle['extended']['supply']
    result = dict(schema=SCHEMA, started_round=battle['round'], days=0, settlement=None,
                  sides={side: _new_side(state, battle, side,
                         march_supply if side == 'attackers' else None) for side in SIDES})
    battle['extended']['supply'] = result
    return result


def ensure(state, battle):
    """Lazy, real-stock bootstrap for a legacy battle's next actual command."""
    return initialize(state, battle)


def _peek(state, battle, side):
    supply = battle['extended'].get('supply')
    if supply is not None:
        return supply['sides'][side]
    # Legacy previews report their present real loading limit, never debit it.
    city = state.cities[battle['source' if side == 'attackers' else 'target']]
    owner = battle['attacker' if side == 'attackers' else 'defender']
    grain = min(city.grain, (daily_units(battle, side) * BUDGET_DAYS + 999) // 1000) if city.owner == owner else 0
    return dict(remaining=grain, credit_units=0, consumed=0, received=0)


def available(state, battle, side):
    return _peek(state, battle, side)['remaining']


def burned(row):
    """Destruction is derived from receipts, never a second saved counter."""
    return sum(receipt['grain'] for receipt in row.get('journal', []) if receipt.get('kind') == 'fire')


def view(state, battle):
    if battle is None:
        return None
    supply = battle['extended'].get('supply')
    result = dict(schema=SCHEMA, initialized=supply is not None,
                  days=supply['days'] if supply else 0, budget_days=BUDGET_DAYS, sides={})
    for side in SIDES:
        row, units = _peek(state, battle, side), daily_units(battle, side)
        result['sides'][side] = dict(initialized=supply is not None,
            grain=row['remaining'] if supply else None,
            available_grain=row['remaining'], daily_units=units,
            daily_grain=max(0, (units-row['credit_units']+999)//1000),
            days_supported=((row['remaining']*1000+row['credit_units'])//units if units else 0),
            consumed=row['consumed'], received=row['received'], burned=burned(row),
            days=supply['days'] if supply else 0)
    return result


def receive(state, battle, side, grain):
    supply = ensure(state, battle)
    row = supply['sides'][side]
    if type(grain) is not int or grain < 0 or row['remaining'] + grain > LIMIT:
        raise ValueError('Invalid battlefield ration delivery')
    if grain:
        row['remaining'] += grain
        row['received'] += grain
        _receipt(row, 'market', supply['days'], grain)


def destroy(state, battle, side, amount):
    """Saturating fire loss against real carried bags; eaten credit survives."""
    if side not in SIDES or type(amount) is not int or not 0 <= amount <= LIMIT:
        raise ValueError('Invalid battlefield ration destruction')
    supply = ensure(state, battle)
    if supply['settlement'] is not None:
        raise ValueError('Battle provisions are already settled')
    row = supply['sides'][side]
    actual = min(row['remaining'], amount)
    if actual:
        row['remaining'] -= actual
        _receipt(row, 'fire', supply['days'], actual)
    return actual


def _receipt(row, kind, day, grain):
    last = row['journal'][-1] if row['journal'] else None
    if last and last['kind'] == kind and last['day'] == day:
        last['grain'] += grain
    else:
        row['journal'].append(dict(kind=kind, day=day, grain=grain))


def end_day(game, state, battle):
    """Charge both armies exactly once after both sides complete a day."""
    supply = ensure(state, battle)
    # The tactical round is advanced first; re-entry cannot double-charge it.
    day = battle['round'] - supply['started_round']
    if day <= supply['days']:
        return None
    if day != supply['days'] + 1 or supply['settlement'] is not None:
        raise ValueError('Battle provision day sequence')
    supply['days'] = day
    shortages = {}
    for side in SIDES:
        row, units = supply['sides'][side], daily_units(battle, side)
        needed = max(0, units-row['credit_units'])
        used = min(row['remaining'], (needed+999)//1000)
        nutrition = row['credit_units']+used*1000
        missing = max(0, units-nutrition)
        row['remaining'] -= used
        row['consumed'] += used
        row['credit_units'] = max(0, nutrition-units)
        row['journal'].append(dict(kind='meal', day=day, units=units, used=used, missing=missing))
        if missing:
            shortages[side] = missing
    battle['log'].append('戰鬥第%d日耗糧：攻方%d，守方%d。' % (
        day, supply['sides']['attackers']['journal'][-1]['used'],
        supply['sides']['defenders']['journal'][-1]['used']))
    if shortages:
        # Simultaneous shortage cannot grant the attacker an unearned city.
        side = 'attackers' if 'attackers' in shortages else 'defenders'
        battle['extended']['withdrawn'] = side
        battle['extended']['duel'] = None
        battle['extended'].pop('siege', None)
        battle['outcome'] = 'retreat' if side == 'attackers' else 'victory'
        state.phase = 'result'
        battle['log'].append('攻方兵糧不足，撤退。' if side == 'attackers' else '守方兵糧不足，撤退。')
        if state.player in (battle['attacker'], battle['defender']):
            game._emit_event(state, 'battle_supply_exhausted',
                city_ids=[battle['source'], battle['target']],
                factions=[battle['attacker'], battle['defender']], details=dict(
                    battle_id=battle['id'], side=side, days=day,
                    grain=supply['sides'][side]['remaining'],
                    daily_grain=(daily_units(battle, side)+999)//1000,
                    missing_units=shortages[side], outcome=battle['outcome']))
    return shortages


def _return_city(state, battle, side):
    """Find a real post-settlement home; never refund a captured origin."""
    owner = battle['attacker' if side == 'attackers' else 'defender']
    origin = state.cities[battle['source' if side == 'attackers' else 'target']]
    living = {unit['id'] for unit in battle[side] if unit['troops'] > 0
              and state.officers[unit['id']].faction_id == owner}
    homes = [city for city in state.cities.values() if city.owner == owner
             and living.intersection(city.roster.officer_ids)]
    if origin in homes:
        return origin
    return sorted(homes, key=lambda city: city.id)[0] if homes else None


def settle(game, state, battle):
    """Move each remaining grain once, after actual officer/city settlement."""
    supply = battle['extended'].get('supply')
    if supply is None:
        return []  # A historical missing ledger is never a refund entitlement.
    if supply['settlement'] is not None:
        return supply['settlement']
    winner = 'attackers' if battle['outcome'] == 'victory' else 'defenders'
    winner_city = state.cities[battle['target']]
    winner_owner = battle['attacker' if winner == 'attackers' else 'defender']
    report = []
    for side in SIDES:
        row = supply['sides'][side]
        city = _return_city(state, battle, side)
        # A routed force without a returning commander leaves its bags behind.
        if city is None and winner_city.owner == winner_owner:
            city = winner_city
        grain = row['remaining']
        stored = min(grain, LIMIT-city.grain) if city is not None else 0
        if city is not None:
            city.grain += stored
        report.append(dict(side=side, city=city.id if city else None,
                           grain=grain, stored=stored, lost=grain-stored,
                           credit_units=row['credit_units']))
        row['remaining'] = row['credit_units'] = 0
    supply['settlement'] = report
    game._note(state, '戰鬥餘糧結算：' + '；'.join(
        ('攻方' if row['side'] == 'attackers' else '守方') + f'{row["stored"]}入城、{row["lost"]}損失'
        for row in report) + '。')
    return report


def validate(state, battle):
    """Replay every receipt; old battles may lack a ledger until commanded."""
    supply = battle['extended'].get('supply')
    if supply is None:
        return
    def integer(value, low, high):
        if type(value) is not int or not low <= value <= high:
            raise ValueError('Battle provision quantity')
    if (not isinstance(supply, dict) or set(supply) != {'schema','started_round','days','sides','settlement'}
            or supply['schema'] != SCHEMA or not isinstance(supply['sides'],dict)
            or set(supply['sides']) != set(SIDES)
            or supply['settlement'] is not None):
        raise ValueError('Battle provision fields')
    integer(supply['started_round'], 1, battle['round'])
    integer(supply['days'], 0, BUDGET_DAYS)
    if supply['days'] != battle['round']-supply['started_round']:
        raise ValueError('Battle provision clock')
    shortages = {}
    for side in SIDES:
        row = supply['sides'][side]
        if not isinstance(row, dict) or set(row) != _SIDE_FIELDS:
            raise ValueError('Battle provision side fields')
        if (row['owner'] != battle['attacker' if side == 'attackers' else 'defender']
                or row['origin'] != battle['source' if side == 'attackers' else 'target']):
            raise ValueError('Battle provision owner')
        for field in ('loaded','remaining'):
            integer(row[field], 0, LIMIT)
        for field in ('received','consumed'):
            integer(row[field], 0, LIMIT*4096)
        for field in ('initial_credit','credit_units'):
            integer(row[field], 0, DENOMINATOR-1)
        if not isinstance(row['journal'], list) or len(row['journal']) > 4096:
            raise ValueError('Battle provision receipts')
        remaining, credit = row['loaded'], row['initial_credit']
        consumed = received = destroyed = days = 0
        for receipt in row['journal']:
            if not isinstance(receipt, dict):
                raise ValueError('Battle provision receipt')
            if receipt.get('kind') == 'meal':
                if set(receipt) != {'kind','day','units','used','missing'} or receipt['day'] != days+1:
                    raise ValueError('Battle provision meal clock')
                integer(receipt['day'],1,supply['days'])
                integer(receipt['units'], 0, MAX_BATTLE_DAILY_UNITS)
                used = min(remaining, (max(0,receipt['units']-credit)+999)//1000)
                nutrition = credit+used*1000
                missing = max(0,receipt['units']-nutrition)
                if type(receipt['used']) is not int or receipt['used'] != used or type(receipt['missing']) is not int or receipt['missing'] != missing:
                    raise ValueError('Battle provision meal replay')
                if missing:
                    if receipt['day'] != supply['days']:
                        raise ValueError('Army remained after provision exhaustion')
                    shortages[side] = missing
                remaining -= used; consumed += used
                credit = max(0,nutrition-receipt['units']); days += 1
            else:
                if set(receipt) != {'kind','day','grain'} or receipt.get('kind') not in ('market', 'fire') or receipt['day'] != days:
                    raise ValueError('Battle provision receipt clock')
                integer(receipt['day'],0,supply['days'])
                integer(receipt['grain'], 1, LIMIT)
                if receipt['kind'] == 'fire':
                    if receipt['grain'] > remaining:
                        raise ValueError('Battle provision destruction exceeds carried grain')
                    remaining -= receipt['grain']; destroyed += receipt['grain']
                else:
                    remaining += receipt['grain']; received += receipt['grain']
                integer(remaining, 0, LIMIT)
        if (days != supply['days'] or (remaining,credit,consumed,received) !=
                (row['remaining'],row['credit_units'],row['consumed'],row['received'])
                or row['loaded']+received != consumed+remaining+destroyed):
            raise ValueError('Battle provision balance')
    if shortages:
        side = 'attackers' if 'attackers' in shortages else 'defenders'
        if (battle['extended']['withdrawn'] != side
                or battle['outcome'] != ('retreat' if side == 'attackers' else 'victory')):
            raise ValueError('Battle provision withdrawal outcome')
