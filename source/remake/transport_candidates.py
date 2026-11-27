"""Compare executable grain offers without spending campaign resources."""
from collections import Counter, defaultdict

from . import army_relief, command_books, facilities, grain_dispatch, granary_planning, logistics
from . import logistics_rules, regional_market, strategic_granary, transport_capacity, transshipment
from . import winter_climate, winter_forecast, winter_transport, winter_travel
from .errors import GameError
from .officers import ref_sort_key
from .transport_allocation import Candidate, order

MAX_OFFERS = 5
SHORTLIST = 8
BOOK = command_books.cost('dispatch_transport')
BUY = command_books.cost('trade_grain')


class Pass:
    """Keep routes within one turn phase; rebuild resource eligibility after a debit."""

    def __init__(self, game, state, owner, *, efficient, features=None):
        self.game, self.state, self.owner = game, state, owner
        self.now = army_relief._calendar_tick(state)
        self.efficient = efficient
        self.routes = {}
        self.trips = {}
        self.failures = defaultdict(Counter)
        self.work = Counter()
        self.features = features or {}
        self.next_plan()

    def next_plan(self):
        self.donors = self.network = self.regional = None
        self.failures.clear()

    def trip(self, quote, back, ids, *, strict):
        game, state = self.game, self.state
        key = (tuple((leg['id'], leg['from']) for leg in quote['routes']),
               tuple((leg['id'], leg['from']) for leg in back['routes']), tuple(ids), strict)
        if key in self.trips:
            self.work['trip_cache_hits'] += 1
            return self.trips[key]
        actual = logistics.escort_rations(game, state, ids, quote, back)
        days, return_days = (winter_travel.quote_days(game, state, leg) for leg in (quote, back))
        facts, conservative = None, None
        protected = actual
        if winter_climate.forecast_enabled(state):
            facts = winter_forecast.estimate(game, state, quote)
            returning = winter_forecast.estimate(game, state, back, start_in=facts['expected_arrival_days'])
            if any(result['bounded'] or result['currently_blocked'] for result in (facts, returning)):
                self.trips[key] = None
                return None
            days, return_days = facts['expected_arrival_days'], returning['expected_arrival_days']
            if strict:
                conservative = winter_forecast.estimate(game, state, quote, conservative=True)
                conservative_days = max(days, conservative['expected_arrival_days'])
                conservative_back = winter_forecast.estimate(game, state, back, start_in=conservative_days,
                                                            conservative=True)
                if conservative['bounded'] or conservative_back['bounded']:
                    self.trips[key] = None
                    return None
                returning = dict(returning, total_ration_weight=max(returning['total_ration_weight'],
                                                    conservative_back['total_ration_weight']))
                return_days = max(return_days, conservative_back['expected_arrival_days'])
            else:
                conservative_days = days
            outbound = facts if conservative is None else dict(facts, total_ration_weight=max(
                facts['total_ration_weight'], conservative['total_ration_weight']))
            _, _, required = winter_transport.seasonal_meals(state, ids, outbound, returning)
            protected = max(actual, required)
        else:
            conservative_days = days
        result = days, return_days, conservative_days, protected, facts, conservative
        self.trips[key] = result
        self.work['measured_trips'] += 1
        return result

    def _arrival(self, days):
        # Warehouse food is settled before deliveries at a turn boundary.
        return self.now + max(1, logistics_rules.ceil_div(days, 10)) * 10

    def _usable(self, candidate):
        demand = candidate.demand
        if candidate.gold and not demand.remaining and demand.gold:
            return True
        at = candidate.conservative_arrival if demand.priority <= 2 else candidate.arrival
        if not demand.after(at) or not candidate.net:
            self.failures[demand.key]['too_late_or_already_covered'] += 1
            return False
        if self.efficient and demand.priority >= 4 and candidate.mode:
            effective = min(candidate.net, demand.after(at))
            if effective <= candidate.rations or (
                    effective < strategic_granary.RULES['minimum_load'] and candidate.period >= 30):
                self.failures[demand.key]['below_economic_load'] += 1
                return False
        if (self.features.get('economics') and demand.kind in ('storage', 'military_candidate', 'front_reserve')
                and candidate.mode and candidate.days >= 20
                and min(candidate.net, demand.after(at)) < 1000):
            self.failures[demand.key]['deferred_small_long_haul'] += 1
            return False
        return True

    def _market(self, demand, plan, buyers):
        game, state = self.game, self.state
        key = demand.target
        city = state.cities[key]
        floor = plan.budgets[key]['wage_gold']
        amount = min(demand.remaining, plan.cities[key].monthly * 2)
        if not amount or not facilities._ready(state, self.owner):
            return None
        offer = facilities.emergency_quote(game, state, city, amount)
        if offer['gold'] > city.gold - floor:
            batch = facilities._rule(game, 'trade_batch_grain')
            amount = min(amount, max(0, city.gold - floor) * batch // offer['rate'])
            offer = facilities.emergency_quote(game, state, city, amount)
        if not offer['grain']:
            self.failures[demand.key][offer['blocked_reason'] or 'market_stock_or_gold'] += 1
            return None
        ids = [ident for ident in city.roster.officer_ids if ident not in buyers
               and state.extension['officer_actions'].get(str(ident)) != state.turn
               and facilities._resident(game, state, city, ident, working=True, healthy=True)]
        if not ids:
            self.failures[demand.key]['no_eligible_buyer'] += 1
            return None
        ident = min(ids, key=lambda i: (-state.officers[i].profile.intellect, ref_sort_key(i)))
        return Candidate(demand, 'local', key, key, (ident,), '', self.now, self.now,
                         offer['grain'], offer['grain'], offer['grain'], 0, 0, 0, BUY, amount, offer['gold'])

    def _ordinary(self, demand, plan, raw, back):
        source, escort, mode, quote, _, gross, _, floor, _ = raw
        game, state = self.game, self.state
        city, target = state.cities[source], state.cities[demand.target]
        ids = (escort,)
        trip = self.trip(quote, back, ids, strict=demand.priority <= 2)
        if trip is None:
            self.failures[demand.key]['unsafe_weather_window'] += 1
            return None
        days, returning, worst, rations, forecast, pressure = trip
        arrival, conservative_arrival = self._arrival(days), self._arrival(worst)
        relevant = conservative_arrival if demand.priority <= 2 else arrival
        needed = demand.after(relevant)
        floor += plan.budgets[source]['reserved_grain']
        available = city.grain - floor
        policy = transport_capacity.ai_policy(state, self.owner,
            logistics._pool(state)['cities'][source]['policy'], automatic=True)
        if demand.priority >= 3 and strategic_granary.enabled(state):
            available = min(available, strategic_granary.available(state, city))
        if available < rations:
            self.failures[demand.key]['insufficient_return_rations'] += 1
            return None
        inbound_stock = sum(value for t, value in plan.cities[target.id].receipts.items()
                            if t * 10 <= arrival - self.now)
        room = logistics.LIMIT - target.grain - inbound_stock
        maximum = min(gross, room, available - rations)
        if transport_capacity.enabled(state, 'physical_capacity'):
            usable_stock = min(available, transport_capacity.current_grain(state, city) - policy['reserve_grain'])
            loading = transport_capacity.loading(game, state, self.owner, policy, quote, rations,
                                                usable_stock, room, automatic=True)
            maximum = min(maximum, loading['max_cargo'])
        cargo = logistics.gross_shipment(game, quote, needed, maximum, state=state) if maximum > 0 and needed else 0
        def deliver(grain):
            net = logistics.projected_grain(game, quote, grain, state=state)
            if forecast is not None:
                net = min(net, winter_forecast.net_cargo(grain, forecast))
            return net
        net = deliver(cargo)
        lower = min(net, winter_forecast.net_cargo(cargo, pressure)) if pressure is not None else net
        gold = min(demand.gold, policy['max_gold'], max(0, city.gold -
                   max(policy['reserve_gold'], plan.budgets[source]['wage_gold'])))
        return Candidate(demand, 'ordinary', source, target.id, ids, mode, arrival,
                         conservative_arrival, net, lower, cargo, rations, days, returning, BOOK,
                         dict(floor=floor, path=quote['path']), gold)

    def _market_route(self, demand, quote, trip, *, channel, mode, cargo, rations, books, officer):
        days, returning, worst, required, forecast, pressure = trip
        if (rations < required
                or not demand.after(self._arrival(worst if demand.priority <= 2 else days))):
            self.failures[demand.key]['insufficient_return_rations_or_time'] += 1
            return None
        net = quote['net'] if forecast is None else min(quote['net'], winter_forecast.net_cargo(cargo, forecast))
        lower = net if pressure is None else min(net, winter_forecast.net_cargo(cargo, pressure))
        return Candidate(demand, channel, quote['source'], quote['target'], (officer,), mode, self._arrival(days),
                         self._arrival(worst), net, lower, cargo, rations, days, returning,
                         books, quote, quote.get('gold', 0))

    def _route_shortlist(self, rows):
        if self.features.get('diversity'):
            self.work['complete_route_checks'] += len(rows)
            return rows
        self.work['pruned_route_quotes'] += max(0, len(rows) - SHORTLIST)
        return rows[:SHORTLIST]

    def _granary_quote(self, network, row, demand, trip):
        deadline = self.state.turn + max(1, (demand.deadline-self.now)//10)
        if trip and self.features.get('requote'):
            arrival = self._arrival(trip[2] if demand.priority <= 2 else trip[0])
            if trip[3] > row['rations']:
                required = trip[3]
                limit = min(row['limit'], row['free']-required)
                updated = dict(row, rations=required, limit=limit)
                physical = row.get('capacity', {}).get('physical_capacity')
                if physical is not None:
                    limit = min(limit, physical-required)
                    updated.update(limit=limit)
                if limit <= 0:
                    self.failures[demand.key]['repriced_source_rations'] += 1
                    return None
                self.work['granary_requotes'] += 1
                row = updated
            return network.shipment(row, demand.after(arrival), deadline)
        return network.shipment(row, demand.after(self._arrival(row['days'])), deadline)

    def _city_routes(self, demands, plan):
        game, state, owner = self.game, self.state, self.owner
        active = [d for d in demands if d.kind not in ('march', 'convoy', 'transshipment')]
        if not active:
            return
        accepted = {d.target: d for d in active}
        returns = {}
        outstanding = [d.target for d in active if d.remaining or d.gold]
        reserve = self.features.get('reserve', False)
        if self.features.get('incremental') and self.donors is None and outstanding:
            self.donors = grain_dispatch._donors(game, state, plan, coordinated=True, reserve=reserve)
        ordinary, blocked = grain_dispatch._options(
            game, state, plan, outstanding, route_cache=self.routes, returns=returns,
            donors=self.donors, reserve=reserve)
        granular = [d.target for d in active if 'granary' in d.channels]
        if granular and strategic_granary.enabled(state, 'proactive'):
            network = self.network or granary_planning.Network(game, state, owner, plan, automatic=True)
            network.route_cache = self.routes
            if self.features.get('incremental'):
                self.network = network
                network.rejected.clear()
            strategic = network.collect(granular, urgent_targets={d.target for d in active if d.priority <= 2},
                                        include_return=True)
        else:
            network, strategic = None, {}
        regional = ((self.regional or regional_market.Planner(game, state, owner, decision=plan, automatic=True,
                                             include_routes=True, coordinated=True))
                    if regional_market.pricing.stage(state) >= regional_market.pricing.PROCUREMENT
                    and command_books.can_spend(state, owner, BUY + BOOK) else None)
        if regional is not None:
            regional.routes = self.routes
            if self.features.get('incremental'):
                self.regional = regional
        assigned = {ident for row in state.extension['ai_strategy'].get(owner, {}).get('orders', ())
                    if row['march_id'] is None and row['departure_turn'] >= state.turn for ident in row['officers']}
        for key, demand in accepted.items():
            if 'local' in demand.channels:
                candidate = self._market(demand, plan, assigned)
                if candidate is not None:
                    yield candidate
            self.failures[demand.key].update(blocked.get(key, {}))
            routes = sorted(ordinary.get(key, ()), key=lambda row: (row[3]['days'], -row[6], row[0], row[2]))
            for raw in self._route_shortlist(routes):
                candidate = self._ordinary(demand, plan, raw, returns[raw[0], key, raw[2]])
                if candidate and self._usable(candidate):
                    yield candidate
            if network is not None:
                self.failures[demand.key].update(network.rejected[key])
                rows = sorted(strategic.get(key, ()), key=lambda row: (row['days'], -row['limit'], row['source'], row['mode']))
                for row in self._route_shortlist(rows) if self.features else rows[:SHORTLIST]:
                    trip = None
                    if self.features.get('requote'):
                        trip = self.trip(row['route'], row['return_quote'], [row['escort']],
                                         strict=demand.priority <= 2)
                        if trip is None:
                            self.failures[demand.key]['unsafe_weather_window'] += 1
                            continue
                    quote = self._granary_quote(network, row, demand, trip)
                    if not quote:
                        continue
                    if trip is None:
                        trip = self.trip(row['route'], row['return_quote'], [quote['escort']], strict=demand.priority <= 2)
                    result = (self._market_route(demand, quote, trip, channel='granary', mode=quote['mode'],
                              cargo=quote['load'], rations=quote['rations'], books=BOOK, officer=quote['escort'])
                              if trip else None)
                    if result and self._usable(result):
                        yield result
            if regional is not None and 'regional' in demand.channels and demand.remaining:
                requested = min(plan.cities[key].monthly * 2, demand.remaining)
                safety = None
                if self.features.get('requote'):
                    def safety(outbound, backward, escort):
                        trip = self.trip(outbound, backward, [escort], strict=demand.priority <= 2)
                        if not trip:
                            return None
                        return trip[3], demand.after(self._arrival(trip[2] if demand.priority <= 2 else trip[0]))
                quotes, rejected = regional.options(state.cities[key], requested, deadline=demand.deadline-self.now,
                                                    coordination_safety=safety, recovery_reserve=reserve)
                self.failures[demand.key].update(rejected)
                for quote in self._route_shortlist(quotes) if self.features else quotes[:SHORTLIST]:
                    if regional_market.conflicts(state, quote):
                        self.failures[demand.key]['active_market_order'] += 1
                        continue
                    a, b = regional.route_details[quote['token']]
                    trip = self.trip(a, b, [quote['actor']], strict=demand.priority <= 2)
                    result = (self._market_route(demand, quote, trip, channel='regional', mode=quote['route_mode'],
                              cargo=quote['cargo'], rations=quote['escort_rations'], books=BOOK+BUY,
                              officer=quote['actor']) if trip else None)
                    if result and self._usable(result):
                        yield result

    def _relief(self, demands, plan, army, convoys):
        game, state = self.game, self.state
        marches = {d.target: d for d in demands if d.kind == 'march'}
        stranded = [d for d in demands if d.kind == 'convoy']
        if not (marches or stranded):
            return
        for key, budget in plan.budgets.items():
            city = state.cities[key]
            if not logistics._pool(state)['cities'][key]['policy']['enabled']:
                continue
            if marches:
                choices, reason = army.candidates(city, budget=budget, targets=marches)
                if not choices and reason:
                    for demand in marches.values():
                        self.failures[demand.key][reason] += 1
                for q in choices:
                    need = marches[q['march_id']]
                    rel = q['relief']
                    # The engine permits recovery after a missed first meal.
                    # Keep that partial recovery separate from on-time relief.
                    yard = q.get('conservative_eta', rel['eta_tick'])
                    if yard > need.deadline + army_relief.MAX_LATE_DAYS:
                        self.failures[need.key]['unsafe_weather_window'] += 1
                        continue
                    yield Candidate(need, 'army', key, q['city'], tuple(q['officers']), q['route_mode'],
                                    rel['eta_tick'], q.get('conservative_eta', rel['eta_tick']),
                                    rel['estimated_net'], q.get('conservative_net', rel['estimated_net']),
                                    q['max_grain'], q['cost_grain'], rel['eta_tick']-self.now,
                                    rel['return_days'], BOOK, (q, army, budget))
            for demand in stranded:
                quote, reason = convoys.quote(city, convoys.targets[demand.target], budget=budget)
                if quote is None:
                    self.failures[demand.key][reason] += 1
                    continue
                rel = quote['relief']
                trip = self.trip(quote['quote'], quote['return_quote'], quote['officers'], strict=True)
                if trip is None or quote['rations'] < trip[3] or self.now + trip[2] > demand.deadline:
                    self.failures[demand.key]['unsafe_weather_window'] += 1
                    continue
                lower = min(rel['net'], winter_forecast.net_cargo(quote['grain'], trip[5])) if trip[5] else rel['net']
                yield Candidate(demand, 'convoy', key, rel['meeting'], tuple(quote['officers']), quote['mode'],
                                rel['eta'], self.now + trip[2], rel['net'], lower, quote['grain'], quote['rations'],
                                trip[0], trip[1], BOOK, quote)

    def _transshipment(self, demands, plan):
        game, state = self.game, self.state
        for demand in demands:
            if demand.kind != 'transshipment':
                continue
            row = transshipment._plans(state)[str(demand.target)]
            for stage, source in enumerate(row['hubs'], 1):
                option = transshipment._quote(game, state, row, stage, source, needed=demand.remaining)
                if option['blocked']:
                    self.failures[demand.key][option['blocked']] += 1
                    continue
                finish = transshipment._deadline(game, state, row, stage, option)
                if finish is None or finish >= min(row['original_deadline'], row['promise']):
                    self.failures[demand.key]['too_late_or_already_covered'] += 1
                    continue
                lots = sum(lot['available'] for lot in option['lots'])
                amount = min(demand.remaining, option['max_cargo'], lots-option['rations'])
                if amount <= 0:
                    self.failures[demand.key]['source_safety'] += 1
                    continue
                net = logistics.projected_grain(game, option['quote'], amount, state=state)
                yield Candidate(demand, 'transshipment', source, option['target'], (option['officer'],), option['mode'],
                                self.now+(finish-state.turn)*10, self.now+(finish-state.turn)*10,
                                net, net, amount, option['rations'], option['days'],
                                winter_travel.quote_days(game, state, option['back']), BOOK,
                                dict(action='dispatch', plan=row['id'], stage=stage, source=source,
                                     officer=option['officer'], grain=amount))

    def build(self, demands, plan, army, convoys, rejected):
        results = defaultdict(list)
        if self.features:
            for demand in demands:
                self.failures.pop(demand.key, None)
        else:
            self.failures.clear()
        from itertools import chain
        possible = chain(self._city_routes(demands, plan), self._relief(demands, plan, army, convoys),
                         self._transshipment(demands, plan))
        for row in possible:
            self.work['candidate_count'] += 1
            if row.key not in rejected:
                results[row.demand.key].append(row)
        selected = []
        for rows in results.values():
            rows.sort(key=lambda row: order(row, efficient=self.efficient))
            self.work['pruned_candidates'] += max(0, len(rows) - MAX_OFFERS)
            selected.extend(_alternatives(rows) if self.features.get('diversity') else rows[:MAX_OFFERS])
        return selected


def _alternatives(ranked):
    if len(ranked) <= MAX_OFFERS:
        return ranked
    chosen, rest = [], []
    sources = set()
    for row in ranked:
        if row.source in sources:
            rest.append(row)
            continue
        chosen.append(row)
        sources.add(row.source)
        if len(chosen) == MAX_OFFERS:
            return chosen
    alternatives = {(row.source, row.mode, row.escorts) for row in chosen}
    remaining = []
    for row in rest:
        identity = row.source, row.mode, row.escorts
        if identity in alternatives:
            remaining.append(row)
        else:
            chosen.append(row)
            alternatives.add(identity)
        if len(chosen) == MAX_OFFERS:
            return chosen
    return chosen + remaining[:MAX_OFFERS-len(chosen)]


def commit(game, state, candidate):
    """Return the actual convoy, immediate receipt or retained market purchase."""
    c, demand = candidate, candidate.demand
    owner = demand.owner
    command_books.require(state, owner, c.command_books)
    source, target = state.cities[c.source], state.cities[c.target]
    if source.owner != owner or target.owner != owner:
        raise GameError('輸送城市已易主。')
    if c.channel == 'local':
        quote = facilities.emergency_quote(game, state, source, c.offer)
        if quote['grain'] != c.load or quote['gold'] != c.gold:
            raise GameError('市場報價已變更。')
        result = facilities.buy_emergency_grain(game, state, c.source, c.escorts[0], owner, c.offer)
        return None, result['grain'], 0
    if c.channel == 'regional':
        item = regional_market.start(game, state, c.offer, automatic=True)
        return item['convoy'], 0, item['purchased'] if item['convoy'] is None else 0
    if c.channel == 'granary':
        priority = 'winter' if demand.kind == 'winter' else 'proactive'
        reserved = strategic_granary.reserve_order(state, owner, c.offer, priority)
        try:
            row = strategic_granary.launch(game, state, reserved, c.offer)
        except GameError as error:
            strategic_granary._finish(state, reserved, 'cancelled', str(error))
            raise
        return row['id'], 0, 0
    if c.channel == 'transshipment':
        ident = logistics._pool(state)['next_id']
        transshipment.execute(game, state, c.offer, owner)
        return ident, 0, 0

    cargo = dict(grain=c.load, gold=c.gold, reserves=0)
    payload = dict(source=c.source, target=c.target, route_mode=c.mode, officers=list(c.escorts), cargo=cargo)
    if c.channel == 'army':
        _, army, budget = c.offer
        payload['target_march'] = demand.target
        row = logistics.dispatch(game, state, payload, owner, relief_planner=army, donor_budget=budget)
    elif c.channel == 'convoy':
        payload['target_convoy'] = demand.target
        row = logistics.dispatch(game, state, payload, owner, convoy_relief_quote=c.offer)
    else:
        if source.grain - c.load - c.rations < c.offer['floor']:
            raise GameError('來源糧倉已低於保護存量。')
        row = logistics.dispatch(game, state, payload, owner, emergency_grain=c.rations,
                                 coordination_offer=c.offer)
    return row['id'], 0, 0
