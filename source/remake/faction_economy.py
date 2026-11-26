"""Read-only budgets, dated city forecasts and command-local resource commitments."""
from collections import defaultdict
from dataclasses import dataclass, field

from . import city_economy, domestic, facilities, historical_campaigns
from . import logistics, logistics_rules, logistics_strategy, military_budget

HORIZON = 9


@dataclass(frozen=True)
class Commitment:
    plan_id: str
    faction_id: str
    source_city_id: str
    target_city_id: str
    amount: int
    priority: int
    created_turn: int
    expiration_turn: int
    resource_type: str = 'grain'

    @property
    def commitment_id(self):
        return (self.plan_id, self.source_city_id, self.resource_type)


@dataclass
class Commitments:
    """Only unspent grain/gold is reserved here. Live convoys own debited cargo."""
    held: dict = field(default_factory=dict)

    def amount(self, source, resource='grain'):
        return sum(row.amount for row in self.held.values()
                   if row.source_city_id == source and row.resource_type == resource)

    def reserve(self, item, stock):
        if (item.amount <= 0 or item.commitment_id in self.held
                or item.amount > stock - self.amount(item.source_city_id, item.resource_type)):
            return False
        self.held[item.commitment_id] = item
        return True

    def release(self, item):
        self.held.pop(item.commitment_id, None)


def pending(state, owner, *, granary=False, except_id=None):
    book = Commitments()
    from . import staging_supply
    for row in staging_supply.active(state):
        if row['owner'] == owner:
            item = Commitment(f"march:{row['army']}:{row['route_day']}", owner,
                              row['city'], row['path'][-1], row['reserved'], 3,
                              row['turn'], row['expires']//10+1)
            book.reserve(item, state.cities[row['city']].grain)
    plan = state.extension['ai_strategy'].get(owner, {})
    for order in plan.get('orders', ()):
        source = state.cities.get(order['source'])
        target = state.cities.get(order['target'])
        if (order['march_id'] is not None or not order.get('provision')
                or not source or source.owner != owner or not target or target.owner == owner
                or historical_campaigns.allied(state, owner, target.owner)
                or order['departure_turn'] < state.turn):
            continue
        item = Commitment(f"{owner}:{plan['created_turn']}:{target.id}", owner,
                          source.id, target.id, order['provision'], 4,
                          plan['created_turn'], order['departure_turn'])
        book.reserve(item, source.grain)
    if granary:
        from . import strategic_granary
        for row in strategic_granary.commitments(state, except_id=except_id):
            if row['owner'] != owner:
                continue
            item = Commitment(f"granary:{row['id']}", owner, row['source'], row['target'],
                              row['load']+row['rations'], 4, row['reserved_turn'],
                              row['reserved_turn']+strategic_granary.RULES['hold_turns'])
            book.reserve(item, state.cities[row['source']].grain)
        if strategic_granary.enabled(state,'relay'):
            from . import granary_relay
            for row in granary_relay.ready(state):
                if row['owner'] != owner:
                    continue
                item = Commitment(f"relay:{row['id']}",owner,row['hub'],row['target'],row['received'],
                                  4,row['received_turn'],row['deadline'])
                book.reserve(item,state.cities[row['hub']].grain)
    return book


@dataclass
class Forecast:
    monthly: int
    zero_in: int | None
    gaps: list
    reserve: int
    late_gap: int
    balances: list
    receipts: dict
    timeline: tuple
    room: int
    first_missing: int
    risky_receipts: dict = field(default_factory=dict)


def balance(stock, timeline, deliveries=()):
    """Deliveries arrive after the ration installment at the same turn."""
    extra = defaultdict(int)
    for eta, amount in deliveries:
        extra[eta] += amount
    gaps, balances, settled = [], [], []
    for ahead, (harvest, due, inbound) in enumerate(timeline, 1):
        available = min(logistics.LIMIT, stock + harvest)
        gaps.append((ahead, max(0, due - available)))
        remaining = max(0, available - due)
        settled.append(remaining)
        stock = min(logistics.LIMIT, remaining + inbound + extra[ahead])
        balances.append(stock)
    return gaps, balances, settled


def _forecast(game, state, city, row, inbound, booked, turns, next_income):
    data = game.catalog.data
    reserve_troops = city.reserves
    rations = row['residents'] + row['garrison']
    timeline, receipts = [], {}
    installment_at_open = (state.day - 1) // 10
    daily_reserve, running = 0, 0
    for ahead in range(1, turns + 1):
        date_offset = installment_at_open + ahead
        installment = (date_offset - 1) % 3 + 1
        harvest = wages = 0
        if installment == 3:
            year, month = divmod(state.year * 12 + state.month - 1 + date_offset // 3, 12)
            income = (next_income if date_offset == 3 else
                      city_economy.monthly_income(game, city.id, state, date=(year, month + 1)))
            harvest = income['grain']
            if date_offset == 3:
                harvest += domestic.earned_grain(state, city.id, income)
                if state.month == facilities.HARVEST_MONTH:
                    harvest += facilities.harvest_bonus(game, state, city) or 0
            reserve_troops += income['reserves']
            rations = row['residents'] + city_economy.garrison_grain_cost(
                data, city.id, year, month + 1, row['active'], reserve_troops)
            wages = row['wage_grain']
        due = city_economy.turn_rations(rations, installment) + wages
        receipt = inbound.get(ahead, 0)
        receipts[ahead] = receipt
        timeline.append((harvest, due, receipt))
        # A donor cannot depend on another convoy to restore what it ships.
        running += due - harvest
        daily_reserve = max(daily_reserve, running)
    stock = max(0, city.grain - booked)
    gaps, balances, settled = balance(stock, timeline)
    zero = (0 if not city.grain and row['fixed'] else
            next((ahead for ahead, amount in gaps if amount), None))
    due_now = gaps[0][1] if gaps else 0
    safety = row['safety_reserve']
    tail = max(0, safety - balances[-1]) if balances else 0
    # Cargo that will arrive beyond the horizon can fill long-term storage,
    # but cannot hide a gap/payroll charge before its actual arrival.
    tail = max(0, tail - sum(amount for ago, amount in inbound.items() if ago > turns))
    return Forecast(row['fixed'], zero, gaps, daily_reserve, tail, settled,
                    receipts, tuple(timeline), max(0, logistics.LIMIT - stock), due_now)


def sustainable(regular, civilians, wages, reserves, active_rate, reserve_rate, *, added=0):
    """Integer version of floor((income - civil costs - r*R) / a)."""
    return max(0, ((regular + added - civilians - wages) * 100 - reserves * reserve_rate) // active_rate)


def capacity(game, state, city, row):
    frontier = city_economy.frontier_outpost_at(game.catalog.data, city.id, state.year, state.month)
    active_rate, reserve_rate = (30, 30) if frontier else (18, 9)
    base = sustainable(row['regular'], row['residents'], row['wage_grain'], city.reserves,
                       active_rate, reserve_rate)
    # A spot-market quote or an individual convoy is finite. There is no
    # verified standing monthly supply contract in the current engine.
    combined = base
    wartime = sustainable(row['regular'], row['residents'], row['wage_grain'], city.reserves,
                          active_rate, reserve_rate, added=max(0, city.grain - row['minimum_reserve']))
    # Reassigning a reserve changes its existing maintenance rate rather than
    # adding a second soldier. At an outpost the two rates are identical.
    spare = (row['regular'] - row['residents'] - row['wage_grain']) * 100
    spare -= city.reserves * reserve_rate + row['active'] * active_rate
    fill = max(0, spare // (active_rate - reserve_rate)) if active_rate > reserve_rate else city.reserves
    return dict(sustainable_local=base, sustainable_combined=combined, sustainable_wartime=wartime,
                excess_troops=max(0, row['active'] - combined), sustainable_allocation=fill,
                active_rate=active_rate, reserve_rate=reserve_rate)


@dataclass
class FactionEconomyPlan:
    owner: str
    budgets: dict
    cities: dict
    commitments: Commitments
    active_away: int

    def shortages(self, state, *, within=3):
        keys = (key for key, forecast in self.cities.items()
                if forecast.monthly and forecast.zero_in is not None and forecast.zero_in <= within)
        return sorted(keys, key=lambda key: (self.cities[key].zero_in,
            -self.cities[key].first_missing, -sum(gap for t, gap in self.cities[key].gaps if t <= 3),
            not self.budgets[key]['threatened'], key))

    def outlook(self, state):
        stock = sum(row['stock'] for row in self.budgets.values())
        runway = 0 if self.budgets and not stock else next((ahead for ahead, total in enumerate(
            map(sum, zip(*(row.balances for row in self.cities.values()))), 1) if total <= 0), None)
        return runway, {key: self.cities[key] for key in self.shortages(state, within=HORIZON)}

    def summary(self, state):
        rows = list(self.budgets.values())
        return dict(grain=sum(row['stock'] for row in rows), gold=sum(row['gold'] for row in rows),
                    regular=sum(row['regular'] for row in rows), fixed=sum(row['fixed'] for row in rows),
                    net=sum(row['net'] for row in rows), stationed=sum(row['active'] for row in rows),
                    deployed=self.active_away, reserves=sum(row['reserves'] for row in rows),
                    needs=self.shortages(state), donors=[k for k, row in self.budgets.items() if row['exportable']],
                    granaries=[k for k, row in self.budgets.items() if row['months'] == 12],
                    exportable=sum(row['exportable'] for row in rows), inbound=sum(row['inbound'] for row in rows),
                    timely=sum(row['timely_grain'] for row in rows),
                    committed=sum(row['march_grain'] + row['reserved_grain'] for row in rows))


def plan(game, state, owner, *, stationed=None, incomes=None, base=None, turns=HORIZON,
         granary=False, except_order=None):
    projected_convoys = {} if granary else None
    budgets = (military_budget.budgets(game,state,owner,stationed=stationed,incomes=incomes,
                                      inbound_cache=projected_convoys) if base is None else base)
    if not budgets:
        return FactionEconomyPlan(owner, {}, {}, Commitments(), 0)
    from . import winter_strategy
    winter_reserves=winter_strategy.planned_reserves(game,state,owner)
    shipments, due = defaultdict(lambda: defaultdict(int)), defaultdict(int)
    uncertain = defaultdict(lambda: defaultdict(int)) if granary else None
    book = pending(state, owner, granary=granary, except_id=except_order)
    away = set()
    for row in state.extension.get('logistics', {}).get('convoys', ()):
        if row['owner'] == owner:
            away.update(row['officers'])
        if (row['owner'] == owner and row['status'] == 'outbound' and not row['delivery_done']
                and row['target_march'] is None and row['target'] in budgets):
            journey = row['journeys'][-1]
            eta = max(1, journey['arrival_turn'] - state.turn)
            projected = projected_convoys.get(row['id']) if granary else None
            if projected is None:
                projected = logistics.inbound_grain(game,row,state)
            if granary:
                from . import winter_travel, winter_weather
                supply = journey['supply']
                if ('convoy_relief' in row or row['target'] != journey['target'] or
                        journey['supply']['retreat_requested'] or supply['waiting'] or
                        any(not historical_campaigns.transit_allowed(state,owner,state.cities[key].owner)
                            for key in journey['quote']['path'][1:]) or
                        winter_weather.movement(state) and
                        winter_travel.route_risk(game,state,journey['quote'],eta*10)):
                    uncertain[row['target']][eta] += projected or row['cargo']['grain']
                    continue
            shipments[row['target']][eta] += projected
            due[row['target']] += projected
    for march in state.extension.get('travel', {}).get('marches', ()):
        if march['owner'] == owner:
            away.update(march['officers'])
    away.update(ident for ident in city_economy.absent_troops(game, state)
                if state.officers[ident].faction_id == owner and state.officers[ident].alive)
    staged = defaultdict(int)
    for item in book.held.values():
        if item.plan_id.startswith('march:'):
            staged[item.source_city_id] += item.amount
    forecast = {}
    next_date = (state.year + (state.month == 12), state.month % 12 + 1)
    for key, row in budgets.items():
        city = state.cities[key]
        minimum = row['fixed']
        safety = minimum * (3 if row['front'] else 2)
        next_income = city_economy.monthly_income(game, key, state, date=next_date)
        natural = next_income['reserves']
        held = book.amount(key)
        if key in winter_reserves:
            premium=winter_reserves[key][1]
            row.update(target=row['target']+premium,winter_reserve_extra=premium)
        row.update(gold=city.gold, reserves=city.reserves, minimum_reserve=minimum,
                   safety_reserve=safety, reserved_grain=held, next_natural_reserves=natural)
        if staged:
            row['staging_grain'] = staged[key]
        projected = _forecast(game, state, city, row, shipments[key], held, turns, next_income)
        if granary:
            projected.risky_receipts = dict(uncertain[key])
        forecast[key] = projected
        reserve = max(minimum, projected.reserve)
        first = projected.zero_in
        timely = sum(amount for eta, amount in shipments[key].items()
                     if (first is None and eta <= turns) or first is not None and eta < first)
        row.update(current_shortfall=projected.first_missing, zero_in=first, inbound=due[key],
                   timely_grain=timely, minimum_export_floor=reserve,
                   above_minimum=max(0, city.grain-held-minimum),
                   above_safety=max(0, city.grain-held-safety),
                   above_strategy=max(0, city.grain-held-row['target']),
                   exportable=max(0, city.grain-held-reserve))
        row.update(capacity(game, state, city, row))
    return FactionEconomyPlan(owner, budgets, forecast, book,
                             sum(state.officers[ident].troops for ident in away))


def allocation_limit(game, state, city, row):
    if row['threatened']:
        # Current support must still cover the next ration payment.
        spare = max(0, city.grain - row['reserved_grain'] - row['next_installment'])
        spread = (row['active_rate'] - row['reserve_rate']) or 1
        return max(row['sustainable_allocation'], spare * 100 // spread)
    return row['sustainable_allocation'] if row['zero_in'] is None or row['zero_in'] > 3 else 0


def recruitment_limit(state, city, budget, requested):
    if budget['threatened']:
        return requested
    reserve_target = domestic.appointments(state, city.owner)['policy']['reserve_target']
    unmet = reserve_target - city.reserves - budget['next_natural_reserves']
    return min(requested, max(0, unmet), max(0, budget['sustainable_combined']-budget['active']))
