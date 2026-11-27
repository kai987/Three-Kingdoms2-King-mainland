"""Read-only nine-turn city forecasts and custody-aware route comparisons."""
from collections import Counter, defaultdict
from hashlib import sha256
import json

from . import (city_economy, climate_regions, command_books, domestic, facilities, faction_economy,
               historical_campaigns, logistics, logistics_rules, logistics_strategy, strategic_granary as reserve,
               winter_agriculture, winter_climate, winter_travel, winter_weather)
from .errors import GameError
from . import granary_demand, transport_capacity, winter_climate


def _plan(game, state, owner, *, except_order=None):
    return faction_economy.plan(game, state, owner, granary=True, except_order=except_order)


def profile(game, state, city, budget, forecast):
    """Cap logical storage by existing city/facility and physical warehouse limits."""
    fixed = budget['fixed']
    town = city_economy.town_level(game, state, city.id)
    frontline = budget['front'] or budget['threatened']
    neighbors = game.catalog.granary_neighbors.get(city.id, ())
    contacts = sum(key in state.cities and historical_campaigns.transit_allowed(
        state, city.owner, state.cities[key].owner) for key in neighbors)
    capacity = min(logistics.LIMIT, max(budget['target'], fixed*max(1, town), budget['regular']*town,
                                        forecast.reserve))
    months = reserve.RULES['front_months'] if frontline else reserve.RULES['rear_months']
    winter, winter_due = 0, None
    if reserve.enabled(state,'winter') and winter_weather.stage(state)>=2:
        climate = game.catalog.climate.cities[city.id]['climate_region_id']
        if winter_climate.enabled(state):
            upcoming = [(state.month+offset-1)%12+1 for offset in range(3)]
            chances = [winter_climate.snow_probability(state, climate, month) for month in upcoming]
            starts = [offset for offset, month in enumerate(upcoming)
                      if winter_climate.cold_normal(state, climate, month) >= 2
                      or chances[offset] >= reserve.RULES['cold_reserve_min_chance']]
            chance = max((chances[offset] for offset in starts), default=0)
        else:
            snow_months, chance, cold_levels, _ = climate_regions.REGIONS[climate]
            normal = {month for month,level in zip(climate_regions.WINTER_MONTHS,cold_levels) if level >= 2}
            hazardous = normal | (set(snow_months) if chance >= reserve.RULES['cold_reserve_min_chance'] else set())
            starts = [offset for offset in range(3) if (state.month+offset-1)%12+1 in hazardous]
        if starts:
            winter = fixed * min(100, max(chance,25)*len(starts))//100
            winter = min(fixed*reserve.RULES['winter_max_months'],max(winter,budget.get('winter_reserve_extra',0)))
            winter_due = max(0,3*starts[0]-(state.day-1)//10)
    history = logistics_strategy.pressure(state,'cities',city.id,True,write=False)
    recent = sum(gap for eta,gap in forecast.gaps if eta <= 3)
    target = max(forecast.reserve, fixed*months) + winter
    if forecast.agricultural_risk:
        target += forecast.agricultural_risk[1]
    if (recent and frontline) or history:
        target += min(fixed, recent if recent else fixed//2)
    row = reserve.reserve_row(state, city)
    if row and row['manual_target'] is not None:
        target = row['manual_target']
    target = min(capacity, target)
    roles = dict(agricultural=budget['net']>0, rear=not frontline and budget['net']>0 and contacts>0,
                 frontline=frontline, hub=contacts>=3, winter=bool(winter),
                 emergency=forecast.zero_in is not None and forecast.zero_in <= 1)
    return dict(capacity=capacity, target=target, winter=min(winter,capacity), winter_due=winter_due,
                roles=roles, contacts=contacts)


def _risk(game, state, quote, *, offset=0, seasonal=False):
    if winter_climate.forecast_enabled(state):
        from . import winter_forecast
        outlook=winter_forecast.estimate(game,state,quote,start_in=offset)
        if outlook['bounded'] or not offset and outlook['currently_blocked']:
            return None
        return dict(days=outlook['expected_arrival_days'],risk=outlook['extra_days'],
                    reaches=outlook['reaches'],extra_weight=0,outlook=outlook)
    days = quote['days']
    if winter_weather.movement(state):
        days, _, ice = winter_travel.checkpoint_forecast(game,state,quote)
        if days is None or ice is not None:
            return None
    outlook = (winter_travel.seasonal_forecast(game,state,quote,start_in=offset) if seasonal else
               dict(extra_days=0, extra_weight=0, reaches=()))
    return dict(days=days+outlook['extra_days'], risk=outlook['extra_days'],
                reaches=outlook['reaches'], extra_weight=outlook['extra_weight'])


class Network:
    """One batch per policy. Quotes live for one read or a single AI demand pass."""
    def __init__(self, game, state, owner, plan, *, automatic=False, except_id=None):
        self.game, self.state, self.owner, self.plan = game,state,owner,plan
        self.automatic = automatic
        self.profiles = {key:profile(game,state,state.cities[key],plan.budgets[key],ahead)
                         for key,ahead in plan.cities.items()}
        self.active = transport_capacity.activity(state)
        self.held_sources = {row['source'] for row in reserve.commitments(state,except_id=except_id)}
        self.absent = city_economy.absent_troops(game,state)
        posts = domestic.appointments(state,owner)
        self.restricted = {posts.get('civil'),posts.get('military')}
        if automatic:
            self.restricted.add(state.extension['leaders'].get(owner))
        self.war = {ident for order in state.extension['ai_strategy'].get(owner,{}).get('orders', ())
                    if order['march_id'] is None and order['departure_turn'] >= state.turn
                    for ident in order['officers']}
        self.stats = Counter()
        self.route_cache = {}
        self.rejected = defaultdict(Counter)
        self.temporal = {}
        self.physical = {}
        self.escort_exclusions = {}
        self.max_room = logistics.LIMIT
        self.target_pending = Counter()
        for row in reserve.commitments(state,except_id=except_id):
            self.target_pending[row['target']] += row['load']

    def _donor(self, key, stock_credit, *, may_release=False):
        state, city = self.state, self.state.cities[key]
        ledger = state.extension['logistics']['cities'][key]
        policy=transport_capacity.ai_policy(state,self.owner,ledger['policy'],automatic=self.automatic)
        budget = self.plan.budgets[key]
        if key in self.held_sources:
            return None, 'already_committed'
        if transport_capacity.dispatch_blocker(state,city,self.active):
            return None, 'source_convoy_limit'
        if (not policy['max_grain'] or not policy['max_officers']
                or self.automatic and historical_campaigns.hold_longyou_garrison(self.game,state,city)):
            return None, 'no_transport_capacity'
        present, escorts, exclusions = self._eligible(city, policy)
        if len(present) <= policy['reserve_officers'] or not escorts:
            self.escort_exclusions[key] = exclusions
            return None, 'no_eligible_escort'
        escort = min(escorts, key=lambda ident:(state.officers[ident].troops,logistics._key(ident)))
        if not logistics.escort_defence(self.game,state,city,[escort],threatened=budget['threatened']):
            return None, 'source_defence'
        if self.automatic and budget['threatened'] and not transport_capacity.enabled(state):
            from .difficulty import get_settings
            if budget['active']-state.officers[escort].troops < min(budget['active'],
                                get_settings(state)['min_guard_troops']):
                return None, 'source_defence'
        forecast = self.plan.cities[key]
        spec = self.profiles[key]
        required = max(policy['reserve_grain'], budget['next_installment'], forecast.reserve)
        if budget['threatened']:
            required = max(required, budget['safety_reserve'])
        safe_floor = max(required, spec['target'], reserve.reserve_grain(state,city))
        urgent_floor = max(required, forecast.reserve + spec['winter']) if may_release else safe_floor
        ceiling = city.grain - budget['reserved_grain'] + stock_credit
        if transport_capacity.enabled(state):
            from . import staging_supply
            ceiling=min(ceiling,staging_supply.available(state,city))
        free = ceiling - min(safe_floor, urgent_floor)
        if free <= 0:
            return None, 'source_safety'
        return (city, policy, escort, safe_floor, urgent_floor, ceiling), None

    def _eligible(self, city, policy):
        state = self.state
        roster = [ident for ident in city.roster.officer_ids
                  if state.officers[ident].alive and state.officers[ident].faction_id == self.owner]
        present = [ident for ident in roster if ident not in self.absent]
        if not present:
            return present, [], dict(no_present_officer=1, officer_in_other_mission=len(roster))
        if len(present) <= policy['reserve_officers']:
            return present, [], dict(below_minimum_retained_officers=1)
        counts, eligible = Counter(), []
        ruler = state.extension['leaders'].get(self.owner)
        staff = state.extension.get('civil_staff', {}).get('people', {}) if transport_capacity.enabled(state) else {}
        for ident in present:
            reason = ('restricted_ruler' if self.automatic and ident == ruler else
                      'restricted_appointment' if ident in self.restricted else
                      'assigned_to_war_plan' if ident in self.war else
                      'officer_health_unavailable' if state.officers[ident].health <= 0 else
                      'receipt_cooldown' if state.extension['logistics']['receipts'].get(str(ident),0)>state.turn else
                      'local_clerk_unavailable' if not staff.get(ident,{}).get('working',True) else
                      'officer_already_acted' if state.extension['officer_actions'].get(str(ident)) == state.turn else None)
            if reason is None:
                eligible.append(ident)
            else:
                counts[reason] += 1
        return present, eligible, dict(counts)

    def _measure(self, quote, offset=0):
        key = (tuple(route['id'] for route in quote['routes']),tuple(quote['path']),offset)
        if key in self.temporal:
            self.stats['risk_cache_hits'] += 1
        else:
            self.temporal[key] = _risk(self.game,self.state,quote,offset=offset,
                seasonal=reserve.enabled(self.state,'winter') or self.automatic)
        return self.temporal[key]

    def physical_profile(self, route):
        key=tuple((leg['id'],leg['from']) for leg in route['routes'])
        if key not in self.physical:
            self.physical[key]=transport_capacity.physical(self.game,self.state,route)
        return self.physical[key]

    def collect(self, targets, sources=None, *, stock_credit=None, urgent_targets=()):
        state = self.state
        seasonal = winter_climate.forecast_enabled(state)
        if not command_books.can_spend(state,self.owner,'dispatch_transport'):
            for key in targets:
                self.rejected[key]['no_command_books'] += 1
            return {}
        groups = defaultdict(list)
        urgent_targets = frozenset(urgent_targets)
        observed = reserve.observed() and reserve.candidate(state)
        capacity_observed = transport_capacity.observed()
        physical = transport_capacity.enabled(state,'physical_capacity')
        if observed:
            self.stats['target_passes'] += len(targets)
        for source in sorted(self.plan.budgets if sources is None else sources):
            self.stats['source_evaluations'] += 1
            donor, reason = self._donor(source,(stock_credit or {}).get(source,0),
                may_release=bool(urgent_targets))
            if observed:
                reserve.observe(state, 'source_eligibility', owner=self.owner, source=source,
                    reason=reason, targets=len(targets)-int(source in targets),
                    stock=state.cities[source].grain,
                    exportable=self.plan.budgets[source]['exportable'],
                    fixed=self.plan.budgets[source]['fixed'],
                    exclusions=self.escort_exclusions[source] if reason == 'no_eligible_escort' else {})
            if capacity_observed:
                transport_capacity.observe(state,'source_offer',owner=self.owner,source=source,reason=reason,
                    targets=len(targets)-int(source in targets),active=transport_capacity.active_count(
                        state,state.cities[source],self.active),dispatch_count=transport_capacity.dispatch_count(state,source),
                    exclusions=dict(self.escort_exclusions.get(source,{}) if reason=='no_eligible_escort' else {}))
            if reason:
                for target in targets:
                    if source != target:
                        self.rejected[target][reason] += 1
            else:
                policy = donor[1]
                groups[policy['allow_sea'],policy['allow_special']].append(donor)
        options = defaultdict(list)
        for signature, donors in groups.items():
            pairs = {(city.id,key) for city,policy,*_ in donors for key in targets
                     if city.id!=key and policy['target_city'] in (None,key)}
            if not pairs:
                continue
            self.stats['candidate_pairs'] += len(pairs)
            phrases = pairs | {(target,source) for source,target in pairs}
            cached, visited = self.route_cache.setdefault(signature, ({},set()))
            self.stats['route_cache_hits'] += len(phrases & visited)
            misses = phrases - visited
            if misses:
                self.stats['route_pairs'] += len(misses)
                self.stats['route_batches'] += 1
                cached.update(logistics._supply_routes(self.game,state,self.owner,sorted(misses),donors[0][1]))
                visited.update(misses)
            for city,policy,escort,normal_floor,urgent_floor,ceiling in donors:
                for key in targets:
                    if (city.id,key) not in pairs:
                        continue
                    floor = min(normal_floor, urgent_floor) if key in urgent_targets else normal_floor
                    free = ceiling - floor
                    if free <= 0:
                        self.rejected[key]['source_safety'] += 1
                        continue
                    target = state.cities[key]
                    outward = logistics._safe_options(self.game,state,city,target,policy,quotes=cached)
                    backward = logistics._safe_options(self.game,state,target,city,policy,quotes=cached)
                    if not outward or not backward:
                        self.rejected[key]['no_legal_route' if not outward else 'no_legal_return'] += 1
                        continue
                    if not seasonal and self._measure(backward[0][1]) is None:
                        self.rejected[key]['winter_route_risk'] += 1
                        continue
                    for mode, route in outward:
                        timing = self._measure(route)
                        if timing is None:
                            self.rejected[key]['winter_route_risk'] += 1
                            continue
                        back = self._measure(backward[0][1], timing['days'])
                        if back is None or self.automatic and not seasonal and (timing['reaches'] or back['reaches']):
                            self.rejected[key]['winter_route_risk'] += 1
                            continue
                        if seasonal:
                            from . import winter_transport
                            outward_rations,return_rations,rations=winter_transport.seasonal_meals(
                                state,[escort],timing['outlook'],back['outlook'])
                        else:
                            rations = logistics.escort_rations(self.game,state,[escort],route,backward[0][1])
                            extra_weight = timing['extra_weight']+back['extra_weight']
                            if extra_weight:
                                from . import march_supply
                                rations += logistics_rules.ceil_div(extra_weight*march_supply.ration_units(state,[escort]),
                                    march_supply.denominator()*logistics_rules.RATION_SCALE)
                            outward_rations=logistics._rations(self.game,state,route,[escort],logistics._empty_cargo())
                            return_rations=logistics._rations(self.game,state,backward[0][1],[escort],logistics._empty_cargo())
                        limit = min(policy['max_grain'],free-rations)
                        load_capacity=None
                        if physical:
                            load_capacity=transport_capacity.loading(self.game,state,self.owner,policy,route,rations,
                                free,logistics.LIMIT,automatic=self.automatic,profile=self.physical_profile(route))
                            limit=load_capacity['max_cargo']
                        if limit <= 0:
                            self.rejected[key]['route_capacity' if physical and free>rations else 'no_return_rations'] += 1
                            continue
                        values = dict(source=city.id,target=target.id,escort=escort,
                            mode=mode, route=route, path=route['path'], return_path=backward[0][1]['path'],
                            days=timing['days'], return_days=back['days'], risk=timing['risk']+back['risk'],
                            ice=sorted(set(timing['reaches']) | set(back['reaches'])), limit=limit,
                            rations=rations, outbound_rations=outward_rations, return_rations=return_rations,
                            floor=floor, free=free)
                        if floor < normal_floor:
                            values['release_floor'] = floor
                        if load_capacity is not None:
                            values['capacity']=load_capacity
                        if self.automatic and transport_capacity.enabled(state,'throughput_ranking'):
                            values['rank_turnover']=True
                        if seasonal:
                            values['seasonal_outlook']=timing['outlook']
                        options[key].append(values)
        return options

    def shipment(self, option, needed, deadline, *, exact=None):
        from .regional_procurement import landed_cents
        game, state = self.game,self.state
        city = state.cities[option['target']]
        pending = self.target_pending[city.id]
        # Take already dated cargo into account when checking receiving room.
        first_ahead = max(1,logistics_rules.ceil_div(option['days'],10))
        forecast = self.plan.cities[city.id]
        receipts = sum(amount for ahead,amount in forecast.receipts.items() if ahead<=first_ahead)
        limit = min(option['limit'],self.max_room-city.grain-pending-receipts)
        if not needed or limit <= 0:
            return None
        load = logistics.gross_shipment(game,option['route'],needed,limit,state=state) if exact is None else exact
        if not 0 < load <= limit:
            return None
        net = logistics.projected_grain(game,option['route'],load,state=state)
        if 'seasonal_outlook' in option:
            from . import winter_forecast
            net=min(net,winter_forecast.net_cargo(load,option['seasonal_outlook']))
        if not net:
            return None
        ticks = max(1, logistics_rules.ceil_div(option['days'],10))
        rate = facilities.market_rate(game,facilities._pool(state)['cities'][city.id]['town'],
                                      'buy',state.month,state=state,city=city.id)
        values = {key:value for key,value in option.items() if key not in ('route','seasonal_outlook')}
        values.update(load=load, net=net, arrival_turn=state.turn+ticks,
                      deadline=deadline, reference_price=rate,
                      landed_cents=landed_cents(0,option['rations'],rate,net), eta=ticks,
                      timely=state.turn+ticks<deadline)
        if 'capacity' in values:
            values['capacity']=dict(values['capacity'],max_cargo=limit)
        if values.pop('rank_turnover',False):
            wait=(-values['days'])%10+(-values['return_days'])%10
            values['turnover_priority']=list(transport_capacity.priority(net,values['rations'],
                values['days'],values['return_days'],wait,1,logistics.RULES['receipt_turns'],values['landed_cents']))
        message = [state.turn, self.owner, state.cities[option['source']].grain, city.grain, values]
        values['token'] = sha256(json.dumps(message,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        return values


def _rank(quote):
    if 'turnover_priority' in quote:
        return (not quote['timely'],quote['risk'],*quote['turnover_priority'],quote['source'],quote['mode'])
    return (not quote['timely'], quote['risk'], quote['landed_cents'],
            -quote['net'], quote['days'], quote['return_days'], quote['source'], quote['mode'])


def preview(game,state,owner,target,quantity,source=None,*,except_id=None):
    if (not reserve.enabled(state) or type(target) is not str or target not in state.cities
            or state.cities[target].owner != owner or owner == 'neutral'
            or type(quantity) is not int or not 0 < quantity <= logistics.LIMIT
            or source is not None and (type(source) is not str or source == target or
                                       source not in state.cities or state.cities[source].owner != owner)):
        raise GameError(reserve.INVALID)
    plan = _plan(game,state,owner,except_order=except_id)
    network = Network(game,state,owner,plan,except_id=except_id)
    choices = network.collect([target], [source] if source is not None else None)
    deadline = state.turn+(plan.cities[target].zero_in if plan.cities[target].zero_in is not None
                           else faction_economy.HORIZON+1)
    prior = reserve._order(state,except_id) if except_id is not None else None
    quotes = [quote for option in choices.get(target,())
              if (quote := network.shipment(option,quantity,deadline,exact=prior['load'] if prior else None))]
    return dict(quotes=sorted(quotes,key=_rank), reasons=dict(network.rejected[target]), target=target,
                quantity=quantity, turn=state.turn)


def refresh_reserves(game,state,owner,plan=None):
    """One faction decision after real emergency spending and before trade."""
    plan = plan if plan is not None else _plan(game,state,owner)
    for key, forecast in plan.cities.items():
        city, budget = state.cities[key],plan.budgets[key]
        spec = profile(game,state,city,budget,forecast)
        prior = reserve.reserve_row(state,city)
        if owner != state.player:
            goal = min(spec['target'], max(0,city.grain-budget['reserved_grain']-budget['next_installment']))
            if spec['roles']['emergency']:
                goal = 0
        else:
            goal = min(spec['capacity'], prior['grain']) if prior else 0
        reason = 'scheduled' if not prior or goal >= prior['grain'] else 'policy'
        reserve.change_reserve(state,city,goal,reason)
        if reserve.observed():
            reserve.observe(state,'city_forecast',city=key,owner=owner,total=city.grain,reserve=goal,
                minimum=min(forecast.balances,default=city.grain), first=forecast.zero_in,
                gap=sum(gap for eta,gap in forecast.gaps), risk=sum(forecast.risky_receipts.values()),
                reliable=sum(v for eta,v in forecast.receipts.items() if eta<=faction_economy.HORIZON),
                fixed=budget['fixed'], target=spec['target'], winter=spec['winter'], capacity=spec['capacity'],
                population=state.extension['city_development']['cities'][key]['population'],
                active=budget['active'], reserves=city.reserves, sustainable=budget['sustainable_local'],
                region=game.catalog.climate.cities[key]['climate_region_id'] if game.catalog.climate else None,
                roles=spec['roles'])
    return plan


def dispatch(game,state,owner,plan):
    """Ship only demand still uncovered at the arrival date."""
    if not reserve.enabled(state,'proactive'):
        return []
    from . import granary_relay
    previous = granary_relay.forward(game,state,owner,plan) if reserve.enabled(state,'relay') else []
    if previous:
        plan = _plan(game,state,owner)
    network = Network(game,state,owner,plan,automatic=True)
    keys = plan.shortages(state,within=faction_economy.HORIZON)
    winter_shortages = {}
    for key,spec in network.profiles.items():
        due = spec['winter_due']
        if due is None or due <= 1 or not spec['roles']['frontline']:
            continue
        forecast = plan.cities[key]
        # Stock available at the next cold-season opening, after that
        # installment's already dated deliveries. This is a readiness
        # target, separate from the actual consumption forecast.
        stock = forecast.balances[due-1] + forecast.receipts.get(due,0)
        missing = min(spec['winter'], max(0,spec['target']-stock))
        if missing >= reserve.RULES['minimum_load']:
            winter_shortages[key] = (due,missing)
    readiness = {key: (due, missing, 'winter') for key, (due, missing) in winter_shortages.items()}
    agriculture_needs = plan.agricultural_needs() if winter_agriculture.planning_enabled(state) else ()
    for key, due, needed in agriculture_needs:
        if needed < reserve.RULES['minimum_load']:
            continue
        previous_due, previous_need, _ = readiness.get(key, (due, 0, 'agriculture'))
        readiness[key] = min(due, previous_due), max(needed, previous_need), 'agriculture'
    keys = list(dict.fromkeys([*keys, *sorted(readiness,
                key=lambda key:(readiness[key][0],-readiness[key][1],key))]))
    candidate = reserve.candidate(state)
    commitments = {row['target'] for row in reserve.commitments(state)}
    active = {row['target'] for row in reserve.pool(state)['orders'].values()
              if row['owner']==owner and row['delivered_turn'] is None and row['status'] != 'reserved'}
    active.update(row['target'] for row in granary_relay.entries(state).values() if row['owner']==owner)
    demands = {key: granary_demand.for_city(game, state, plan, key) for key in keys} if candidate else {}
    targets = ([key for key in keys if demands[key].first is not None or key in readiness]
               if candidate else [key for key in keys if key not in commitments | active])
    urgent_targets = set()
    if candidate and reserve.enabled(state, 'coordination'):
        urgent_targets = {key for key in targets if demands[key].first in (2, 3)}
    for key in sorted(set(keys)-set(targets)):
        reserve.observe(state,'dispatch_blocked',owner=owner,target=key,
                        reason='covered' if candidate else 'already_committed')
    if not targets:
        return previous
    choices = network.collect(targets, urgent_targets=urgent_targets)
    used, orders, unfilled = set(), list(previous), []
    for key in targets:
        forecast = plan.cities[key]
        demand = demands.get(key)
        first = forecast.zero_in if demand is None else demand.first
        preparing = first is None and key in readiness
        reason = readiness[key][2] if preparing else 'consumption'
        priority = 'winter' if reason == 'winter' else 'proactive'
        deadline = state.turn+(readiness[key][0] if preparing else first)
        requested = readiness[key][1] if preparing else sum(gap for _,gap in (
            forecast.gaps if demand is None else demand.remaining))
        if candidate and preparing:
            due = readiness[key][0]
            requested = min(requested, max(0, network.profiles[key]['target']-demand.balance_at_end[due-1]))
        options = []
        rejections = network.rejected[key]
        for route in choices.get(key,()):
            if route['source'] in used:
                rejections['already_committed'] += 1
                continue
            eta = logistics_rules.ceil_div(route['days'],10)
            quote_deadline = deadline
            if preparing:
                timely = route['days']+reserve.RULES['timely_buffer_days'] <= 10*(deadline-state.turn-1)
                missing = requested if timely else 0
            elif demand is not None:
                due, missing = demand.after(eta)
                if due is not None:
                    quote_deadline = state.turn + due
            else:
                missing = sum(gap for turn,gap in forecast.gaps if eta<turn)
            if not missing:
                rejections['too_late'] += 1
                continue
            quote = network.shipment(route,max(reserve.RULES['minimum_load'],missing),quote_deadline)
            if (quote is None or quote['net'] < reserve.RULES['minimum_load']
                    or quote['rations']*100 > quote['net']*reserve.RULES['maximum_ration_percent']):
                rejections['below_economic_load'] += 1
                continue
            options.append(quote)
        if candidate and reserve.observed():
            best = min(options, key=_rank) if options else None
            reserve.observe(state,'residual_demand', owner=owner,target=key, deadline=deadline,
                demand_id=f'{owner}/{key}/{deadline}/{reason}',
                priority=priority, **granary_demand.describe(demand),
                planned=None if best is None else best['net'], receipts=forecast.convoy_receipts,
                pending_target=key in commitments, active_target=key in active)
        reserve.observe(state,'dispatch_requested',owner=owner,target=key,deadline=deadline,
            grain=requested, priority=priority, candidates=len(options),
            legal=bool(choices.get(key)), timely_net=max((q['net'] for q in options if q['timely']),default=0),
            delayed_receipts=sum(forecast.risky_receipts.values()), rejections=dict(rejections))
        if not options or not command_books.can_spend(state,owner,'dispatch_transport'):
            if (not preparing and first > 2 and (not candidate or key not in active | commitments)):
                unfilled.append(key)
            continue
        quote = min(options,key=_rank)
        order = reserve.reserve_order(state,owner,quote,priority)
        try:
            reserve.launch(game,state,order,quote)
        except GameError as exc:
            reserve._finish(state,order,'cancelled',str(exc))
            continue
        if reason == 'agriculture':
            winter_weather.report('agricultural_preparation', turn=state.turn, year=state.year, month=state.month,
                                  owner=owner, city=key, method='granary', grain=quote['net'], deadline=deadline)
        used.add(order['source'])
        orders.append(order)
    orders.extend(granary_relay.dispatch(game,state,owner,plan,network,unfilled,used))
    reserve.observe(state,'dispatch_work',owner=owner,**dict(network.stats))
    return orders


def view(game,state):
    from . import economic_regions
    owner = state.player
    plan = _plan(game,state,owner)
    data = reserve.pool(state)
    from . import granary_relay
    relays = [row for row in granary_relay.entries(state).values() if row['owner']==owner]
    entries = {}
    coordinated = reserve.enabled(state,'coordination')
    for key, forecast in plan.cities.items():
        city, budget = state.cities[key],plan.budgets[key]
        spec = profile(game,state,city,budget,forecast)
        prior = reserve.reserve_row(state,city)
        if coordinated:
            protected = reserve.protection(state,city,book=plan.commitments)
            account = dict(available=protected['free'], strategic=protected['strategic'],
                committed=protected['unshipped']+protected['relay'], military=protected['military'])
        else:
            account = dict(available=reserve.available(state,city), strategic=reserve.reserve_grain(state,city),
                committed=reserve.committed(state,key)+granary_relay.credit(state,key), military=budget.get('staging_grain',0))
        entries[key] = dict(spec,**account,total=city.grain,stock_region=economic_regions.region(key),
            inbound=sum(v for t,v in forecast.receipts.items() if t<=faction_economy.HORIZON),
            inbound_risk=sum(v for t,v in forecast.risky_receipts.items() if t<=faction_economy.HORIZON),
            shortfall=sum(missing for eta,missing in forecast.gaps), first=forecast.zero_in,
            turn=state.turn, day=state.day, month=state.month, year=state.year,
            last_update=prior['turn'] if prior else None, reason=prior['reason'] if prior else None,
            manual_target=prior['manual_target'] if prior else None,
            forecast=[dict(ahead=i,harvest=income,due=due,reliable=receipts,
                           risky=forecast.risky_receipts.get(i,0),ending=min(logistics.LIMIT,ending+receipts),
                           missing=gap[1]) for i,((income,due,receipts),ending,gap) in
                           enumerate(zip(forecast.timeline,forecast.balances,forecast.gaps),1)])
        if reserve.candidate(state):
            demand = granary_demand.for_city(game, state, plan, key)
            receipts = [dict(item, expected_date=None if item['status']=='blocked' else
                         winter_weather.date_at(game.catalog.data,(state.turn+item['eta']-1)*10+1))
                        for item in forecast.convoy_receipts]
            entries[key].update(demand=granary_demand.describe(demand), receipts=receipts)
    return dict(version=state.extension[reserve.FIELD],features=data['features'], cities=entries, relays=relays,
                order_costs=dict(set_target=0,hold=0,release=0,reserve=0,cancel=0,
                                 dispatch=command_books.cost('dispatch_transport')),
                orders=[row for row in (*data['orders'].values(),*data['history']) if row['owner']==owner])
