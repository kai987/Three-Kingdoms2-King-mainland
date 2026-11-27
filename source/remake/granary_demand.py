"""Dated net receipts and the outstanding part of a strategic grain request."""
from dataclasses import dataclass

from . import faction_economy, historical_campaigns, logistics, logistics_rules
from . import march_supply, strategic_granary as reserve, winter_climate, winter_travel, winter_weather


def inbound(game, state, row, projected):
    journey = row['journeys'][-1]
    book = journey['supply']
    eta = max(1, journey['arrival_turn'] - state.turn)
    path = journey['quote']['path']
    last = march_supply.last_city(journey)
    remaining = path[path.index(last) + 1:] if last in path else path[1:]
    blocked = (row['status'] != 'outbound' or row['target'] != journey['target']
               or book['waiting'] or book['retreat_requested']
               or not projected or any(not historical_campaigns.transit_allowed(state, row['owner'],
                   state.cities[key].owner) for key in remaining))
    status, conditional_eta = ('blocked' if blocked else 'reliable'), None
    if not blocked and winter_weather.movement(state):
        outlook = winter_travel.seasonal_forecast(game, state, journey['quote'], position=winter_travel.work(book))
        if winter_climate.forecast_enabled(state):
            from . import winter_forecast
            if outlook['bounded']:
                status='blocked'
            else:
                eta=max(eta,logistics_rules.ceil_div(outlook['expected_arrival_days'],10))
                projected=min(projected,winter_forecast.net_cargo(
                    row['cargo']['grain'],outlook,row[logistics.LOSS_FIELD]))
                if outlook['seasonal_freeze_risk']>=2_000:
                    status='seasonal'
                    conditional_eta=eta
        elif outlook['reaches']:
            status = 'seasonal'
            # Widen uncertain ETAs using published information. No date is
            # promised for a stopped convoy or a route that has lost access.
            conditional_eta = eta + max(1, logistics_rules.ceil_div(outlook['extra_days'], 10))
    return dict(convoy=row['id'], order=row.get('strategic'), source=row['source'], eta=eta,
                conditional_eta=conditional_eta, net=projected, cargo=row['cargo']['grain'], status=status)


def held_deliveries(game, state, plan, target):
    """An unlaunched order can cover a later window only if still backed."""
    for row in reserve.commitments(state):
        if row['target'] != target or row['owner'] != plan.owner:
            continue
        key = (f"granary:{row['id']}", row['source'], 'grain')
        source = state.cities[row['source']]
        if (key not in plan.commitments.held
                or plan.commitments.amount(source.id) > source.grain):
            continue
        if any(not historical_campaigns.transit_allowed(state, row['owner'], state.cities[city].owner)
               for city in row['path'][1:]):
            continue
        officer = state.officers[row['escort']]
        if (not officer.alive or officer.health <= 0 or officer.faction_id != row['owner']
                or row['escort'] not in source.roster.officer_ids):
            continue
        policy = logistics._pool(state)['cities'][source.id]['policy']
        quote = logistics._safe_path(game,state,source.id,target,row['owner'],row['mode'],policy)
        if quote is None or quote['path'] != row['path'] or logistics._dangerous(quote,policy):
            continue
        days, _, ice = winter_travel.checkpoint_forecast(game,state,quote) if winter_weather.movement(state) else (
            quote['days'], None, None)
        if ice is not None:
            continue
        latest_launch = row['reserved_turn'] + reserve.RULES['hold_turns']
        ahead = latest_launch - state.turn + max(1, logistics_rules.ceil_div(days,10))
        if 0 < ahead < row['deadline'] - state.turn:
            net = logistics.projected_grain(game,quote,row['load'],state=state)
            yield ahead, min(net, row['expected_grain'])


@dataclass(frozen=True)
class Demand:
    baseline: list
    reliable: list
    remaining: list
    balance_at_end: list
    held: int

    @property
    def first(self):
        return next((ahead for ahead, missing in self.remaining if missing), None)

    def after(self, eta):
        eligible = [(ahead, amount) for ahead, amount in self.remaining if ahead > eta and amount]
        return (eligible[0][0], sum(amount for _, amount in eligible)) if eligible else (None, 0)


def calculate(stock, forecast, *, holds=()):
    holds = tuple(holds)
    baseline = tuple((income, due, 0) for income, due, _ in forecast.timeline)
    baseline_gaps, _, _ = faction_economy.balance(stock, baseline)
    possible = (*forecast.conditional_receipts.items(), *holds)
    gaps, closing, _ = faction_economy.balance(stock, forecast.timeline, possible)
    return Demand(baseline_gaps, forecast.gaps, gaps, closing, sum(amount for _, amount in holds))


def for_city(game, state, plan, target):
    row = plan.budgets[target]
    stock = max(0, state.cities[target].grain - row['reserved_grain'])
    return calculate(stock, plan.cities[target], holds=held_deliveries(game, state, plan, target))


def describe(demand):
    baseline, reliable, remaining = (sum(missing for _, missing in gaps)
                                     for gaps in (demand.baseline, demand.reliable, demand.remaining))
    return dict(baseline=baseline, covered=baseline-reliable, reliable_shortfall=reliable,
                contingent_coverage=reliable-remaining, uncovered=remaining, committed_inbound=demand.held,
                first_uncovered=demand.first)
