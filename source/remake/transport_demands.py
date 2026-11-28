"""Dated demand derived from the faction's published grain forecasts."""
from dataclasses import dataclass

from . import army_relief, convoy_relief, faction_economy, historical_campaigns, winter_strategy, winter_weather


@dataclass(frozen=True)
class Demand:
    owner: str
    kind: str
    target: str | int
    priority: int
    deadline: int
    requested: int
    remaining: int
    reliable: int = 0
    conditional: int = 0
    installments: tuple = ()
    channels: tuple = ()
    created: int = 0
    original: int | None = None
    gold: int = 0
    plan_id: str | None = None

    @property
    def key(self):
        base = f'{self.owner}/{self.kind}/{self.target}'
        return base if self.plan_id is None else f'{base}/{self.plan_id}'

    @property
    def original_deadline(self):
        return self.deadline if self.original is None else self.original

    @property
    def episode(self):
        return f'{self.key}/{self.created}'

    def after(self, tick):
        if self.installments:
            return sum(amount for due, amount in self.installments if tick < due)
        if self.plan_id is not None:
            return self.remaining if tick < self.deadline else 0
        return self.remaining if tick <= self.deadline else 0

    def original_balance(self):
        if not self.installments:
            return self.remaining
        return sum(amount for due, amount in self.installments if due <= self.original_deadline)


def city_shortage(game, state, plan, key):
    from . import granary_demand, strategic_granary
    city, forecast, budget = state.cities[key], plan.cities[key], plan.budgets[key]
    gaps = tuple((ahead, missing) for ahead, missing in forecast.gaps if missing)
    stock = max(0, city.grain - budget['reserved_grain'])
    undispatched = ((income, due, 0) for income, due, _ in forecast.timeline)
    baseline = tuple((t, n) for t, n in faction_economy.balance(stock, undispatched)[0] if n)
    if not baseline:
        return None
    gross = sum(gap for _, gap in baseline)
    remaining = sum(gap for _, gap in gaps)
    now = army_relief._calendar_tick(state)
    ahead = (gaps or baseline)[0][0]
    priority = (0 if not city.grain and forecast.first_missing else
                1 if ahead == 1 else 2 if ahead <= 3 else 4)
    possible = list(forecast.conditional_receipts.items())
    if strategic_granary.enabled(state):
        possible.extend(granary_demand.held_deliveries(game, state, plan, key))
    conditional = remaining - sum(n for _, n in faction_economy.balance(stock, forecast.timeline, possible)[0])
    return Demand(plan.owner, 'city', key, priority, now + ahead * 10, gross, remaining,
                  gross - remaining, conditional,
                  tuple((now + t * 10, amount) for t, amount in gaps),
                  ('local', 'ordinary', 'granary', 'regional'))


def reserves(game, state, plan, supported, *, include_storage, preparations=False):
    """Plans competing for the same closing stock are alternate claims on it."""
    now = army_relief._calendar_tick(state)
    winter = (winter_strategy.seasonal_requirements(game, state, plan.owner, plan)
              if winter_weather.stage(state) >= 5 else {})
    agro = dict((key, (ahead, size)) for key, ahead, size in plan.agricultural_needs())
    for key, forecast in plan.cities.items():
        budget = plan.budgets[key]
        if any(missing for _, missing in forecast.gaps):
            continue  # Cover installments first and refresh readiness from the remainder.
        if preparations:
            for priority, due, ident, kind, goal, gold in supported.get(key, ()):
                if priority == 6 and not include_storage:
                    continue
                if due < 1 or due > len(forecast.balances):
                    continue
                city = state.cities[key]
                # Balances are closing balances after the same-date receipt.
                # A plan must use the preceding balance to load its rations.
                reliable = sum(grain for t, grain in forecast.receipts.items() if t < due)
                need = max(0, goal - city.grain - reliable)
                gold_gap = max(0, gold - city.gold)
                if need or gold_gap:
                    yield Demand(plan.owner, kind, key, priority, now+due*10, need+reliable, need, reliable,
                                 channels=('local', 'ordinary', 'granary', 'regional'), gold=gold_gap, plan_id=ident)
                    break
            else:
                priority = None
            if priority is not None:
                continue
        elif key in supported:
            goal, gold, turns = supported[key]
            ahead = min(len(forecast.balances), max(1, turns))
            # A reserve that can only be restored after a seasonal purchase
            # can't fund a sortie already due. Only dated net supply counts.
            city = state.cities[key]
            reliable = sum(grain for t, grain in forecast.receipts.items() if t < ahead)
            need = max(0, goal - city.grain - reliable)
            gold = max(0, gold - city.gold)
            if need or gold:
                yield Demand(plan.owner, 'mobilization', key, 3, now + ahead * 10, need + reliable,
                             need, reliable, channels=('local', 'ordinary', 'granary', 'regional'), gold=gold)
                continue
        seasonal = []
        if key in winter and winter[key]['extra']:
            row = winter[key]
            seasonal.append((row['deadline'], row['extra'], 'winter'))
        if key in agro:
            due, grain = agro[key]
            seasonal.append((due, grain, 'agriculture'))
        if seasonal:
            # These are incremental forecast gaps in one physical warehouse.
            # Apply an earlier increment before evaluating a later claim.
            dated = {}
            for due, grain, label in sorted(seasonal):
                covered = sum(t for t, _ in dated.values())
                if grain > covered:
                    dated[due] = (dated.get(due, (0, label))[0] + grain - covered, label)
            due = min(dated)
            amount = sum(grain for grain, _ in dated.values())
            yield Demand(plan.owner, dated[due][1], key, 5, now + due * 10, amount, amount,
                         installments=tuple((now + t * 10, grain) for t, (grain, _) in sorted(dated.items())),
                         channels=('local', 'ordinary', 'granary', 'regional'))
            continue
        short = max(0, budget['target'] - state.cities[key].grain - budget['timely_grain'])
        if include_storage and short and (budget['front'] or budget['threatened']):
            yield Demand(plan.owner, 'storage', key, 6, now + 90, short, short,
                         channels=('ordinary', 'granary'))


def military(game, state, army, convoys):
    now = army_relief._calendar_tick(state)
    if army is not None:
        for ident, need in army.demands.items():
            if not need.required:
                continue
            reliable = min(need.required, sum(amount for tick, amount in army.estimates(ident)
                                             if tick <= need.deadline))
            yield Demand(army.owner, 'march', ident, 0 if need.urgent else 1 if need.deadline <= now + 10 else 2,
                         need.deadline, need.required, need.required - reliable, reliable, channels=('army',))
    if convoys is not None:
        for row in convoys.targets.values():
            need = convoy_relief.request(game, state, row)
            if need is None:
                continue
            pending = convoy_relief.outstanding(game, state, row, need, review=convoys.review)
            reliable = min(need.required, sum(amount for _, amount in pending))
            yield Demand(row['owner'], 'convoy', need.ident, 0, need.wait_until, need.required,
                         need.required - reliable, reliable, channels=('convoy',))


def approved_orders(state, owner):
    sources = {}
    now = state.turn
    for order in state.extension['ai_strategy'].get(owner, {}).get('orders', ()):
        city = state.cities[order['source']]
        if city.owner != owner or order['march_id'] is not None or order['departure_turn'] < now:
            continue
        provision = order.get('provision') or 0
        if provision > city.grain:
            sources[city.id] = (provision, 0, max(1, order['departure_turn'] - now))
    return sources


def preparations(state, plan, requests):
    """Keep approved orders, candidate plans and defensive storage distinct."""
    owner, now = plan.owner, state.turn
    result, ordered = {}, set()
    strategy = state.extension['ai_strategy'].get(owner, {})
    for order in strategy.get('orders', ()):
        key = order['source']
        if key not in plan.cities:
            continue
        ordered.add((key, order['target']))
        target = state.cities[order['target']]
        if (order['march_id'] is not None or order['departure_turn'] < now
                or target.owner == owner or historical_campaigns.allied(state, owner, target.owner)):
            continue
        ident = f"{strategy['created_turn']}:{key}:{order['target']}:{order['departure_turn']}"
        result.setdefault(key, []).append((3, max(1, order['departure_turn']-now), ident,
                                          'mobilization', order.get('provision') or 0, 0))
    for key, tasks in requests.items():
        if key not in plan.cities:
            continue
        for ident, task in tasks.items():
            kind, target = task['kind'], task['target']
            if target is not None and ((key, target) in ordered or state.cities[target].owner == owner
                                       or historical_campaigns.allied(state, owner, state.cities[target].owner)):
                continue
            if kind == 'front_defence' and not plan.budgets[key]['threatened']:
                kind = 'front_reserve'
            priority = {'front_defence': 4, 'military_candidate': 5, 'front_reserve': 6}[kind]
            actual_deadline = task['deadline']-now
            # Unapproved stock goals use the forecast horizon, never an expired attack date.
            due = min(len(plan.cities[key].balances), actual_deadline)
            if due > 0:
                result.setdefault(key, []).append((priority, due, f'{now}:{ident}', kind,
                                                   task['grain'], task['gold']))
    return {key: sorted(rows) for key, rows in result.items()}


def source_stock(state, plan):
    return sum(state.cities[key].grain for key in plan.budgets)
