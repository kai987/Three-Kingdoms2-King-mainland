"""Forecast granary shortages and reserve enough grain for donor cities."""
from collections import defaultdict
from dataclasses import dataclass

from . import city_economy, command_books, domestic, facilities, grain_units, historical_campaigns, logistics, military_budget, payroll
from .errors import GameError

WARNING_TURNS = 3
AID_MONTHS = 2
EMERGENCY_MONTHS = 2
RECOVERY_TURNS = 9


@dataclass
class Forecast:
    monthly: int
    zero_in: int | None
    gaps: list[tuple[int, int]]
    reserve: int
    late_gap: int
    balances: list[int]


def forecasts(game, state, owner, *, turns=WARNING_TURNS):
    """Use current development and garrisons, dated production and known shipments.

    Transport cargo is unloaded after the turn's consumption. Keep a second
    balance without shipments to decide how much a donor can safely release.
    """
    if owner == 'neutral' or not game.catalog.data.get('calendar_rules'):
        return {}
    data = game.catalog.data
    cities = [city for city in state.cities.values() if city.owner == owner]
    if not cities:
        return {}
    weighted=military_budget.enabled(state)
    absent = city_economy.absent_troops(game, state)
    development = state.extension.get('city_development', {}).get('cities', {})
    shipments = defaultdict(lambda: defaultdict(int))
    for row in state.extension.get('logistics', {}).get('convoys', ()):
        if (row['owner'] == owner and row['status'] == 'outbound'
                and row['target_march'] is None and not row['delivery_done']):
            arrival = row['journeys'][-1]['arrival_turn'] - state.turn
            if arrival > 0:
                shipments[row['target']][arrival] += (logistics.inbound_grain(game,row) if weighted else row['cargo']['grain'])

    current_date = (state.year, state.month)
    result = {}
    for city in cities:
        active = sum(state.officers[i].troops for i in city.roster.officer_ids
                     if i not in absent and state.officers[i].alive)
        civilian = city_economy.civilian_grain(development.get(city.id, {}).get('population', 0),
                                             city_economy.town_level(game, state, city.id), state=state)
        monthly = civilian + city_economy.garrison_grain_cost(
            data, city.id, *current_date, active, city.reserves)
        wages=payroll.monthly_due(state,city)['grain'] if weighted else 0
        due, reserves = monthly, city.reserves
        stock, unassisted, reserve = city.grain, 0, 0
        arrivals = shipments[city.id]
        gaps, balances = [], []
        for ahead in range(1, turns + 1):
            installments = (state.day - 1) // 10 + ahead
            installment = (installments - 1) % 3 + 1
            if installment == 3:
                year, month = divmod(state.year * 12 + state.month - 1 + installments // 3, 12)
                income = domestic._income(game, city.id, state, date=(year, month + 1))
                bonus = (domestic.earned_grain(state, city.id, income)
                         if installments == 3 and 'domestic' in state.extension else 0)
                harvest = income['grain'] + bonus
                if installments == 3 and state.month == facilities.HARVEST_MONTH:
                    harvest += facilities.harvest_bonus(game, state, city) or 0
                stock += harvest
                unassisted += harvest
                reserves += income.get('reserves', 0)
                due = civilian + city_economy.garrison_grain_cost(
                    data, city.id, year, month + 1, active, reserves)
            ration = city_economy.turn_rations(due, installment)+(wages if installment==3 else 0)
            stock -= ration
            unassisted -= ration
            balances.append(stock)
            if ration:
                gaps.append((ahead, max(0, 1 - stock)))
                reserve = max(reserve, 1 - unassisted)
            stock += arrivals[ahead]
        late_gap = max(0, 1 - stock - sum(amount for ahead, amount in arrivals.items() if ahead > turns))
        zero_in = 0 if city.grain == 0 else next((ahead for ahead, gap in gaps if gap), None)
        if (turns == WARNING_TURNS and zero_in == 0 and not any(gap for _, gap in gaps)
                and not any(arrivals[ahead] for ahead in range(1, turns + 1))):
            # An empty granary needs a buffer even if the next harvest could refill it.
            gaps.append((turns, (monthly + 2) // 3))
        result[city.id] = Forecast(monthly+wages, zero_in, gaps, reserve, late_gap, balances)
    return result


def _shortages(projections):
    return sorted((city_id for city_id, row in projections.items()
                   if row.monthly > 0 and row.zero_in is not None),
                  key=lambda city_id: (projections[city_id].zero_in, city_id))


def _donors(game, state, projections):
    if 'logistics' not in state.extension:
        return []
    pool = state.extension['logistics']
    busy = {row['source'] for row in pool['convoys']}
    donors = []
    owner=state.cities[next(iter(projections))].owner if projections else 'neutral'
    budgets=military_budget.budgets(game,state,owner) if military_budget.enabled(state) and owner!=state.player else {}
    for key, row in projections.items():
        if key in busy or row.zero_in is not None:
            continue
        city = state.cities[key]
        ledger = pool['cities'][key]
        policy = ledger['policy']
        budget=budgets.get(key)
        reserve=min(budget['target'],budget['fixed']*3) if budget else 0
        surplus = city.grain - max(row.reserve,policy['reserve_grain'],reserve)
        if (surplus <= 0 or not policy['max_grain'] or not policy['max_officers']
                or ledger['last_dispatch_turn'] == state.turn
                or historical_campaigns.hold_longyou_garrison(game, state, city)):
            continue
        if logistics._present_count(game, state, city) <= policy['reserve_officers']:
            continue
        ids = logistics._eligible(game, state, city)
        if ids:
            escort = min(ids, key=lambda i: (state.officers[i].troops, logistics._key(i)))
            donors.append((city, policy, surplus, escort))
    return donors


def _deliveries(game, state, owner, projections, targets):
    from .march_supply import cost, estimate, initial_days, quote_supply
    from . import logistics_rules

    weighted=military_budget.enabled(state)
    groups = defaultdict(list)
    for donor in _donors(game, state, projections):
        policy = donor[1]
        groups[policy['allow_sea'], policy['allow_special']].append(donor)
    deliveries = defaultdict(list)
    for donors in groups.values():
        pairs = [pair for city, _, _, _ in donors for key in targets
                 for pair in ((city.id, key), (key, city.id))]
        quotes = logistics._supply_routes(game, state, owner, pairs, donors[0][1])
        for city, policy, surplus, escort in donors:
            for key in targets:
                route = logistics._safe_quote(game, state, city, state.cities[key], policy, quotes=quotes)
                if route is None:
                    continue
                mode, quote = route
                # Prepay the return out of donor stock so the escort does
                # not withdraw the emergency cargo from the receiving city.
                returning = logistics._safe_quote(game, state, state.cities[key], city, policy, quotes=quotes)
                troops = state.officers[escort].troops
                rations=(quote_supply(quote,troops,1,game=game,version=logistics_rules.CURRENT)
                         if weighted else cost(troops,1,quote['days']))
                if returning:
                    rations+=(estimate(state,[escort],returning[1],game=game)
                              if weighted else cost(troops,1,initial_days(state,returning[1])))
                amount = min(policy['max_grain'], surplus - rations)
                if amount > 0:
                    delivered=logistics.projected_grain(game,quote,amount) if weighted else amount
                    if delivered:
                        line=(quote['turns'],quote['days'],-delivered,city.id,escort,mode,rations)
                        deliveries[key].append((*line,quote,amount) if weighted else line)
    return {key:sorted(rows,key=lambda row:row[:7]) for key,rows in deliveries.items()}


def _uncovered(row, planned, arrival=0):
    # Delivery must precede the instalment it is meant to cover.
    return max((max(0, gap - sum(amount for turn, amount in planned if turn < ahead))
                for ahead, gap in row.gaps if arrival < ahead), default=0)


def _schedule(projections, targets, deliveries, slots, *, send=None, game=None):
    """Use the same donor allocation for advice and actual dispatch."""
    assigned = set()
    planned = {key: [] for key in targets}
    for wait in (False, True) if send else (False,):
        for key in targets:
            row = projections[key]
            orders = planned[key]
            for turns, _, capacity, source, escort, mode, rations, *route in deliveries.get(key, ()):
                if not slots:
                    return planned
                if source in assigned:
                    continue
                need = (_uncovered(row, orders, turns) if not wait else
                        max(0, row.late_gap - sum(amount for _, amount in orders)))
                if not need:
                    continue
                amount = min(-capacity, need)
                actual=logistics.gross_shipment(game,route[0],amount,route[1]) if route else amount
                if send and not send(key, source, escort, mode, actual, rations):
                    continue
                assigned.add(source)
                orders.append((turns, amount))
                slots -= 1
    return planned


def dispatch(game, state, owner):
    """Dispatch emergency convoys before ordinary delegated orders."""
    kind = 'dispatch_transport'
    if 'logistics' not in state.extension or not command_books.can_spend(state, owner, kind):
        return
    projections = forecasts(game, state, owner)
    targets = _shortages(projections)
    if not targets or not domestic._present(game, state, state.cities[targets[0]],
                                            domestic.appointments(state, owner)['civil']):
        return

    def send(key, source, escort, mode, amount, rations):
        try:
            logistics.dispatch(game, state, dict(source=source, target=key,
                officers=[escort], cargo=dict(gold=0, grain=amount, reserves=0),
                route_mode=mode), owner, emergency_grain=rations)
        except GameError:
            return False
        return True

    deliveries = _deliveries(game, state, owner, projections, targets)
    _schedule(projections, targets, deliveries, command_books.remaining(state, owner), send=send,game=game)


def aid_cities(game, state, owner):
    projections = forecasts(game, state, owner)
    targets = _shortages(projections)
    if not targets:
        return {}
    allies = any(other != owner and historical_campaigns.allied(state, owner, other)
                 for other in {c.owner for c in state.cities.values()} - {'neutral'})
    slots = command_books.remaining(state, owner)
    deliveries = _deliveries(game, state, owner, projections, targets) if allies and slots else {}
    plans = _schedule(projections,targets,deliveries,slots,game=game)
    return {key: dict(id=key, zero_in=projections[key].zero_in,
                      amount=min(AID_MONTHS * projections[key].monthly,
                                 logistics.LIMIT - state.cities[key].grain)
                      if allies and _uncovered(projections[key], plans[key]) else 0)
            for key in targets}


def allied_stocks(game, state, owner):
    """Only stock above two months' rations and the configured floor is aid."""
    result = []
    policies = state.extension.get('logistics', {}).get('cities', {})
    for key, row in forecasts(game, state, owner).items():
        if row.zero_in is not None:
            continue
        city = state.cities[key]
        floor = policies.get(key, {}).get('policy', {}).get('reserve_grain', 0)
        surplus = city.grain - max(row.reserve, AID_MONTHS * row.monthly, floor)
        if surplus > 0:
            result.append((surplus, city))
    return sorted(result, key=lambda entry: (-entry[0], entry[1].id))


def recovery(game, state, owner):
    """Nine instalments with local harvests, inbound grain and present garrisons."""
    if not grain_units.current_rations():
        return None, {}
    forecasts_by_city = forecasts(game, state, owner, turns=RECOVERY_TURNS)
    if not forecasts_by_city or not any(row.monthly for row in forecasts_by_city.values()):
        return None, {}
    totals = map(sum, zip(*(row.balances for row in forecasts_by_city.values())))
    stock = sum(state.cities[key].grain for key in forecasts_by_city)
    runway = 0 if stock == 0 else next((turn for turn, grain in enumerate(totals, 1) if grain <= 0), None)
    return runway, {key: row for key, row in forecasts_by_city.items()
                    if row.monthly and row.zero_in is not None}


def _emergency_limit(city, forecast):
    turns = EMERGENCY_MONTHS * WARNING_TURNS
    gap = max((gap for ahead, gap in forecast.gaps if ahead <= turns), default=0)
    if not gap and city.grain == 0:
        gap = city_economy.turn_rations(forecast.monthly, 1)
    return min(forecast.monthly * EMERGENCY_MONTHS, gap)


def recovery_view(game, state, owner):
    runway, cities = recovery(game, state, owner)
    result = dict(turns=runway, cities={key: row.zero_in for key, row in cities.items()})
    purchases = {}
    for key in sorted(imminent_shortages(cities)):
        forecast = cities[key]
        city = state.cities[key]
        limit = _emergency_limit(city, forecast)
        if limit:
            offer = facilities.emergency_quote(game, state, city, limit)
            if offer['market_stock'] is not None:
                purchases[key] = dict(offer, demand=limit)
    if purchases:
        result['market_purchases'] = purchases
    return result


def imminent_shortages(shortages):
    return {key for key, row in shortages.items() if row.zero_in <= WARNING_TURNS}


def invest(game, state, owner, outlook):
    """Buy grain for immediate gaps and develop land ahead of later shortages."""
    from . import city_development
    from .officers import ref_sort_key

    _, cities = outlook
    if not cities or not facilities._ready(state, owner) or 'facilities' not in state.extension:
        return
    pool = state.extension['facilities']
    policy = pool['factions'][owner]
    for key in sorted(cities, key=lambda key: (cities[key].zero_in, key)):
        if not command_books.can_spend(state, owner):
            break
        city, forecast = state.cities[key], cities[key]
        actors = [i for i in city.roster.officer_ids
                  if facilities._resident(game, state, city, i, working=True, healthy=True)]
        if not actors:
            continue
        actor = min(actors, key=lambda i: (-state.officers[i].profile.intellect, ref_sort_key(i)))
        if forecast.zero_in <= WARNING_TURNS:
            limit = _emergency_limit(city, forecast)
            if limit:
                facilities.buy_emergency_grain(game, state, key, actor, owner, limit)
            continue

        regular_budget = max(0, city.gold - policy['gold_floor'])
        order = dict(city=key, actor=actor, kind='develop_land')
        land = city_development.quote(game, state, key, actor, order['kind'], owner)
        can_develop = (land['eligible'] and land['gain_max'] and land['gold_max'] <= regular_budget
                       and domestic._income(game, key, state)['grain'] > 0)
        if can_develop:
            city_development.execute(game, state, order, owner)
