"""Persistent, deterministic campaign planning using ordinary game orders.

Coordinated columns use the ordinary roster and travel limits. Allied columns
can share one deployment when they reach their common target.
Planning only reads published state; actual recruitment still owns its RNG roll.
"""
from collections import Counter, defaultdict
from copy import copy
from itertools import combinations

from .difficulty import attack_budget, get_settings
from .errors import GameError
from . import command_books, diplomacy, diplomacy_ai, historical_campaigns, officer_relations
from .officers import integer, recruitment_loyalty, ref_sort_key
from . import civil_staff
from . import grain_relief, grain_units
from .march_supply import denominator, OFFICER_UNITS, estimate as march_grain, next_supply_days, required_grain, travel_rules
from . import city_economy, faction_economy, logistics_rules, logistics_strategy, military_budget, war_recovery
from .route_hazards import allocate_survivors
from . import winter_travel, winter_weather


class StrategicAI:
    def __init__(self, campaign, state):
        self.game, self.state = campaign, state
        self.settings = get_settings(state)
        self.budget = attack_budget(campaign.catalog, state)
        self.quotes = {}
        self.neighbor_ids = {}
        self.support_checked = set()
        self.front_supply_checked = set()
        self.grain_outlooks = {}
        self.military_budget = military_budget.enabled(state)
        self.budget_absent = None
        self.return_quotes = {}
        self.war_quotes = {}
        self.economy_plans = {}
        self.occupation = {}
        self.staging_checked = set()
        self.friendly_recovery = {}
        self.v21 = logistics_strategy.enabled(state)
        self.adaptive = logistics_strategy.enabled(state, logistics_strategy.WAR)
        self.recovery_v211 = logistics_strategy.war_recovery(state)
        self.recovery_wait = {}
        self.winter_checked = set()
        holdings = Counter(city.owner for city in state.cities.values() if city.owner != 'neutral')
        # Let both sides concentrate on the remaining fronts once the map
        # has consolidated. Earlier campaigns retain their wider priorities.
        self.endgame = (1 <= len(holdings) <= 2
                        and max(holdings.values()) * 4 >= len(state.cities) * 3)

    def grain_outlook(self, owner):
        if owner not in self.grain_outlooks:
            self.grain_outlooks[owner] = (self.economy_plan(owner).outlook(self.state) if self.v21
                                         else grain_relief.recovery(self.game, self.state, owner))
        return self.grain_outlooks[owner]

    def economy_plan(self, owner):
        if owner not in self.economy_plans:
            self.economy_plans[owner] = faction_economy.plan(self.game, self.state, owner)
        return self.economy_plans[owner]

    def recovery_support(self, city):
        """Only dated incoming cargo or an executable friendly supplier counts."""
        if city.id in self.friendly_recovery:
            return self.friendly_recovery[city.id]
        from . import logistics

        state, game = self.state, self.game
        plan = self.economy_plan(city.owner)
        local = plan.budgets[city.id]
        grain, gold = local['timely_grain'], 0
        pool = state.extension['logistics']
        for donor in self.neighbors(city):
            if donor.owner != city.owner or donor.id not in plan.budgets:
                continue
            budget = plan.budgets[donor.id]
            stock = max(0, donor.grain-budget['reserved_grain']
                        -max(budget['safety_reserve'], budget['minimum_export_floor']))
            policy = pool['cities'][donor.id]['policy']
            if (not policy['enabled'] or policy['target_city'] not in (None, city.id)
                    or not policy['max_officers'] or not command_books.can_spend(state, city.owner, 'dispatch_transport')
                    or pool['cities'][donor.id]['last_dispatch_turn'] == state.turn
                    or any(row['source'] == donor.id for row in pool['convoys'])
                    or logistics._present_count(game, state, donor) <= policy['reserve_officers']):
                continue
            options = logistics._eligible(game, state, donor)
            if not options:
                continue
            escort = min(options, key=lambda ident: (state.officers[ident].troops, ref_sort_key(ident)))
            outward = logistics._safe_quote(game, state, donor, city, policy)
            backward = logistics._safe_quote(game, state, city, donor, policy)
            if outward is None or backward is None or winter_travel.quote_turns(game,state,outward[1]) > 3:
                continue
            ration = sum(logistics._rations(game,state,route[1],[escort],logistics._empty_cargo())
                         for route in (outward,backward))
            if stock < ration + policy['reserve_grain']:
                continue
            grain += logistics.projected_grain(game, outward[1],
                         min(policy['max_grain'], stock-ration-policy['reserve_grain']),state=state)
            gold += min(policy['max_gold'], max(0, donor.gold-max(budget['wage_gold'],policy['reserve_gold'])))
            break  # One modeled donor is one available order, even when several share its city.
        result = dict(grain=grain, gold=gold)
        self.friendly_recovery[city.id] = result
        return result

    def defenders(self, city):
        """The same healthy, present top ten units the battle can actually use."""
        marching = self.game._march_ids(self.state)
        return sorted((i for i in city.roster.officer_ids if i not in marching
                       and self.state.officers[i].alive and self.state.officers[i].health > 0
                       and self.state.officers[i].troops > 0),
                      key=lambda i: (-self.state.officers[i].troops, ref_sort_key(i)))[:10]

    def strength(self, city):
        return sum(self.state.officers[i].troops for i in self.defenders(city))

    def neighbors(self, city):
        if city.id not in self.neighbor_ids:
            self.neighbor_ids[city.id] = tuple(key for key in self.game._neighbors(city.id, self.state)
                                               if key in self.state.cities)
        return [self.state.cities[key] for key in self.neighbor_ids[city.id]]

    def threat(self, city, exclude=None):
        hostile = [self.strength(c) for c in self.neighbors(city)
                   if c.id != exclude and c.owner not in (city.owner, 'neutral')
                   and not historical_campaigns.allied(self.state, city.owner, c.owner)]
        incoming = [sum(self.state.officers[i].troops for i in m['officers'])
                    for m in self.state.extension['travel']['marches']
                    if m['target'] == city.id and m['owner'] != city.owner and m['kind'] == 'attack'
                    and not historical_campaigns.allied(self.state, city.owner, m['owner'])]
        return sum(sorted(hostile, reverse=True)[:2]) + sum(incoming)

    def available(self, city):
        marching = self.game._march_ids(self.state)
        return sorted((i for i in city.roster.officer_ids if i not in marching
                       and self.state.officers[i].alive and self.state.officers[i].health > 0),
                      key=lambda i: (-self.state.officers[i].troops, ref_sort_key(i)))

    def army(self, city, target=None, *, transfer=False):
        if historical_campaigns.hold_longyou_garrison(self.game, self.state, city):
            return []
        available = self.available(city)
        # The objective itself is removed from the flank estimate. A sole
        # general may sally against its only weak neighbor, but cannot abandon
        # a second enemy front or an already incoming hostile column.
        danger = self.threat(city, exclude=target)
        need = max(self.settings['min_guard_troops'],
                   danger * self.settings['guard_ratio_percent'] // 100) if danger else 0
        guards, kept = set(), 0
        marching = self.game._march_ids(self.state)
        present = sorted((i for i in city.roster.officer_ids if i not in marching
                          and self.state.officers[i].alive and self.state.officers[i].health > 0
                          and self.state.officers[i].troops > 0),
                         key=lambda i: (self.state.officers[i].troops, ref_sort_key(i)))
        if transfer and 'domestic' in self.state.extension:
            from .domestic import appointments
            posts=appointments(self.state,city.owner)
            guards.update(i for i in (posts.get('civil'),posts.get('military'))
                if i in city.roster.officer_ids and i not in marching
                and self.state.officers[i].alive and self.state.officers[i].health > 0)
            kept=sum(sorted((self.state.officers[i].troops for i in guards),reverse=True)[:10])
        for ident in present:
            if kept >= need and (not transfer or guards):
                break
            guards.add(ident)
            kept = sum(sorted((self.state.officers[i].troops for i in guards),reverse=True)[:10])
        # Transfers retain an administrator even in a zero-troop rear city.
        if transfer and not guards and available:
            guards.add(available[-1])
        return [i for i in available if i not in guards and self.state.officers[i].troops > 0][:10]

    def month_at(self, turn):
        ticks = (self.state.day - 1)//10 + turn - self.state.turn
        return (self.state.month - 1 + ticks//3) % 12 + 1

    def quote(self, source, target, mode, *, adjacent, departure=None):
        turn = self.state.turn if departure is None else departure
        elapsed_months = ((self.state.day-1)//10 + turn-self.state.turn)//3
        year = self.state.year + (self.state.month-1+elapsed_months)//12
        month = self.month_at(turn)
        key = source.id, target.id, source.owner, mode, adjacent, year, month
        if key not in self.quotes:
            snapshot = copy(self.state)
            snapshot.year = year
            snapshot.month = month
            self.quotes[key] = self.game._travel_path(snapshot, source.id, target.id,
                                                      source.owner, mode, adjacent=adjacent)
        return self.quotes[key]

    def reinforcement_quotes(self, source, targets):
        from . import ai_core
        if not targets or not ai_core.enabled():
            return
        pairs = [(source.id, dest.id) for dest in targets if any(
            (source.id, dest.id, source.owner, mode, False, self.state.year, self.state.month)
            not in self.quotes for mode in ('land', 'fastest'))]
        if pairs:
            quotes = ai_core.routes(self.game, self.state, source.owner, pairs)
            for origin, dest in pairs:
                for mode in ('land', 'fastest'):
                    key = origin, dest, source.owner, mode, False, self.state.year, self.state.month
                    self.quotes[key] = quotes.get(f'{origin}:{dest}:{mode}')

    def survivors(self, quote, ids):
        troops = [self.state.officers[i].troops for i in sorted(ids,key=ref_sort_key)]
        storm = False
        for leg in quote['routes']:
            hazard = leg.get('hazard')
            if not hazard:
                continue
            if hazard['kind'] == 'monsoon_storm':
                if storm:
                    continue
                storm = True
                n, d = 100-hazard['loss_percent_max'], 100
            else:
                n, d = hazard['survival_numerator'], hazard['survival_denominator']
            troops = allocate_survivors(troops, n, d)
        return sum(troops)

    def safe(self, quote, ids):
        if not quote or winter_travel.quote_turns(self.game,self.state,quote) > self.settings['max_route_turns']:
            return False
        total = sum(self.state.officers[i].troops for i in ids)
        return bool(total) and self.survivors(quote, ids)*100 >= total*(100-self.settings['max_route_loss_percent'])

    def provisioned(self, city, ids, quote):
        """Read-only forecast of the same first loading and friendly stops.

        Neutral cities cannot supply grain. Carry the rounding credit between
        segments, so an intermediate city need not pay a second rounding unit.
        Actual departure rechecks this forecast; later capture or spending is
        still handled by the ordinary daily supply and rescue services.
        """
        if not quote:
            return False
        if logistics_strategy.staging(self.state):
            from . import staging_supply
            if len(quote['routes']) == 1:
                return staging_supply.available(self.state,city) >= march_grain(self.state,ids,quote,game=self.game)
            loaded, stops = staging_supply.assess(self.game,self.state,city,ids,quote,self.economy_plan(city.owner).budgets)
            return staging_supply.available(self.state,city) >= loaded and all(
                row['required']==row['reserved'] for row in stops)
        loaded = march_grain(self.state, ids, quote, game=self.game)
        if city.grain < loaded:
            return False
        units = sum(self.state.officers[i].troops for i in ids) + OFFICER_UNITS * len(ids)
        weighted = logistics_rules.version(self.state) == logistics_rules.CURRENT
        parts = logistics_rules.plan(quote, travel_rules(self.game)) if weighted else None
        divisor = denominator() * (logistics_rules.RATION_SCALE if weighted else 1)
        credit, progress = loaded * divisor, 0
        for index, leg in enumerate(quote['routes']):
            weight = logistics_rules.weight(parts, progress, leg['days']) if weighted else leg['days']
            progress += leg['days']
            credit -= units * weight
            if credit < 0:
                return False
            checkpoint = self.state.cities[quote['path'][index + 1]]
            if index < len(quote['routes']) - 1 and checkpoint.owner == city.owner:
                days = next_supply_days(self.state, quote, city.owner, progress)
                weight = logistics_rules.weight(parts, progress, days) if weighted else days
                needed = max(0, (units * weight - credit + divisor - 1) // divisor)
                if checkpoint.grain < needed:
                    return False
                credit += needed * divisor
        return True

    def war_budget(self, city, target, ids, quote):
        if not self.military_budget:
            return None
        state=self.state
        travel=state.extension['travel']['counter']
        convoys=state.extension.get('logistics',{}).get('next_id',0)
        movements=(travel,convoys)
        if self.budget_absent is None or self.budget_absent[0]!=movements:
            self.budget_absent=(movements,city_economy.absent_troops(self.game,state))
        key=(target.id,city.id,city.owner)
        if key not in self.return_quotes:
            origin=copy(target)
            origin.owner=city.owner
            # Use the current legal directed network. A one-way march is not
            # a licence to quote an illegal return.
            options=[self.quote(origin,city,mode,adjacent=False) for mode in ('land','fastest')]
            self.return_quotes[key]=[option for option in options if option is not None]
        troops=tuple((ident,state.officers[ident].troops) for ident in ids)
        route=tuple((leg['id'],leg['days']) for leg in quote['routes'])
        from . import staging_supply
        held=staging_supply.held(state,city.id) if logistics_strategy.staging(state) else 0
        fingerprint=(key,troops,route,movements,city.grain,city.gold,city.reserves,held,
                     tuple((i,state.officers[i].experience) for i in city.roster.officer_ids))
        # A pending order revalidates its own reservation. Another purpose
        # cannot concurrently spend that stock.
        if fingerprint not in self.war_quotes:
            safe=[option for option in self.return_quotes[key] if self.safe(option,ids)]
            if self.adaptive and not safe and target.owner != 'neutral':
                alternatives = [dest for dest in self.neighbors(target)
                                if dest.owner == city.owner and dest.id != city.id
                                and self.game._city_occupancy(state, dest)+len(ids) <=
                                self.game.catalog.rules.city_officer_capacity]
                origin = copy(target)
                origin.owner = city.owner
                safe = [route for dest in alternatives for mode in ('land', 'fastest')
                        if (route := self.quote(origin,dest,mode,adjacent=False)) and self.safe(route,ids)]
            back=min(safe,key=lambda option:option['days'],default=None)
            incoming = self.adaptive and any(m['kind']=='transfer' and m['owner']==target.owner
                       and m['target']==target.id for m in state.extension['travel']['marches'])
            kwargs = (dict(defenders=self.strength(target), incoming=incoming,
                           recovery=None if self.recovery_v211 else self.recovery_support(city)) if self.adaptive else {})
            self.war_quotes[fingerprint]=military_budget.sortie(self.game,state,city,target,ids,quote,
                back,absent=self.budget_absent[1],held=held, **kwargs)
        return self.war_quotes[fingerprint]

    def affordable_sortie(self,city,target,ids,quote):
        plan=self.war_budget(city,target,ids,quote)
        return plan is None or plan['can_depart']

    def attack_option(self, city, target, *, require_grain=True):
        ids = self.army(city, target.id)
        joint = self.game._allied_attack_info(self.state, target, city.owner)
        if joint:
            ids = ids[:joint['remaining']]
        total = sum(self.state.officers[i].troops for i in ids)
        if not ids or total + (joint['troops'] if joint else 0) < self.settings['min_attack_troops']:
            return None
        options = []
        modes=('land','fastest','river','sea') if self.military_budget else ('land','fastest')
        for mode in modes:
            quote=self.quote(city,target,mode,adjacent=True)
            if not self.safe(quote,ids):
                continue
            choices=range(len(ids),0,-1) if self.military_budget and require_grain else (len(ids),)
            for size in choices:
                selected=ids[:size]
                strength=self.survivors(quote,selected)
                if self.military_budget and strength+(joint['troops'] if joint else 0)<self.settings['min_attack_troops']:
                    break
                if require_grain and (not self.provisioned(city,selected,quote)
                        or not self.affordable_sortie(city,target,selected,quote)):
                    continue
                cost=0
                if self.military_budget:
                    cost=march_grain(self.state,selected,quote,game=self.game)
                options.append(dict(source=city.id,target=target.id,officers=selected,mode=mode,
                                    quote=quote,survivors=strength,provision=cost))
                break
        return min(options,key=lambda o:(-o['survivors'],o['provision'],o['quote']['days'],
                                         o['quote']['distance_km'],o['mode']),default=None)

    def schedule(self, members):
        """Find real departures under their projected calendar weather."""
        turn = self.state.turn
        earliest = turn + max(o['quote']['turns'] for o in members)
        for arrival in range(earliest, earliest+self.settings['plan_horizon_turns']+1):
            orders = []
            for member in members:
                source, target = (self.state.cities[member[k]] for k in ('source', 'target'))
                found = None
                for departure in range(arrival-1, turn-1, -1):
                    quote = self.quote(source, target, member['mode'], adjacent=True, departure=departure)
                    if (self.safe(quote, member['officers']) and departure+winter_travel.quote_turns(self.game,self.state,quote) == arrival
                            and self.provisioned(source, member['officers'], quote)
                            and self.affordable_sortie(source,target,member['officers'],quote)):
                        found = dict(source=source.id, target=target.id, mode=member['mode'],
                            departure_turn=departure, arrival_turn=arrival,
                            officers=list(member['officers']), march_id=None)
                        if self.v21:
                            budget = self.war_budget(source, target, member['officers'], quote)
                            found['provision'] = budget['immediate']
                        break
                if found is None:
                    break
                orders.append(found)
            if len(orders) == len(members):
                return orders
        return []

    def attack_approaches(self, owner):
        approaches = defaultdict(list)
        reserved = historical_campaigns.reserved_sortie_targets(self.game, self.state, owner)
        for source in self.state.cities.values():
            if source.owner != owner:
                continue
            for target in self.neighbors(source):
                if (target.id not in reserved and target.owner != owner
                        and not historical_campaigns.allied(self.state, owner, target.owner)):
                    approaches[target.id].append(source)
        return approaches

    def attack_requirement(self, target):
        return max(self.settings['min_attack_troops'],
                   (self.strength(target)*self.settings['attack_ratio_percent']+99)//100)

    def priority_targets(self, owner, targets):
        requested = diplomacy.requested_target(self.state, owner)
        if requested in targets:
            return {requested}, requested
        if self.state.player != owner and historical_campaigns.allied(self.state, self.state.player, owner):
            support = [key for key in targets
                       if (joint := self.game._allied_attack_info(self.state, self.state.cities[key], owner))
                       and joint['faction'] == self.state.player and joint['remaining']]
            if support:
                return set(support), min(support)
        return historical_campaigns.priority_targets(self.state, owner, targets)

    def objective(self, owner, preferred=None):
        approaches = self.attack_approaches(owner)
        targets = sorted(approaches)
        priority, first = self.priority_targets(owner, targets)
        if priority:
            targets = sorted(priority)
        elif preferred in targets:
            targets = [preferred]
        available_budget = min(max(0, self.budget-self.state.extension['ai_attacks']),
                               command_books.remaining(self.state, owner)//max(1,command_books.cost('depart')))
        winners, potential = [], []
        recovery_quote = None
        deferred = []
        occupied = []
        if logistics_strategy.occupancy_budget(self.state):
            from . import occupation_budget
            if owner not in self.occupation:
                self.occupation[owner]=occupation_budget.record(self,owner,self.economy_plan(owner))
            occupied=self.occupation[owner]
        historical_targets = set()
        hostile_approaches = defaultdict(set)
        if self.recovery_v211:
            # A dated campaign order and an active attack on the staging city
            # each establish a reason to join an existing conflict.
            historical_targets,_=historical_campaigns.priority_targets(self.state,owner,targets)
            for march in self.state.extension['travel']['marches']:
                if (march['kind']=='attack' and march['owner']!=owner
                        and not historical_campaigns.allied(self.state,owner,march['owner'])
                        and not march['supply']['retreat_requested']):
                    hostile_approaches[march['source']].add(march['target'])
        for key in targets:
            target = self.state.cities[key]
            defend = self.strength(target)
            joint = self.game._allied_attack_info(self.state, target, owner)
            potential.append((defend, -target.grain, target.id))
            options = [o for city in approaches[key] if command_books.can_spend(self.state, owner, 'depart')
                       and (o := self.attack_option(city, target)) is not None]
            options.sort(key=lambda o: (-o['survivors'], o['quote']['days'], o['source']))
            # Limit enumeration to the six strongest approaches, then at most
            # three legal armies. This keeps a large campaign's plan bounded.
            limit = min(self.settings['max_attack_sources'], available_budget)
            required = max(self.settings['min_attack_troops'],
                           (defend*self.settings['attack_ratio_percent']+99)//100)
            for size in range(1, limit+1):
                feasible = []
                for members in combinations(options[:6], size):
                    if joint and sum(len(o['officers']) for o in members) > joint['remaining']:
                        continue
                    power = sum(o['survivors'] for o in members) + (joint['troops'] if joint else 0)
                    if power < required:
                        continue
                    orders = self.schedule(members)
                    if not orders:
                        continue
                    # Delayed columns use their actual departure month's
                    # routes, including any changed seasonal travel time.
                    scheduled = [(o, self.quote(self.state.cities[o['source']], target,
                        o['mode'], adjacent=True, departure=o['departure_turn'])) for o in orders]
                    days = sum(winter_travel.quote_days(self.game,self.state,quote) for _, quote in scheduled)
                    supply = sum(march_grain(self.state, order['officers'], quote, game=self.game)
                                 for order, quote in scheduled)
                    score = min(power-required,required//3)-days*3-supply*2//grain_units.amount(1)+min(200,target.gold//20+target.grain//grain_units.amount(200))
                    if self.recovery_v211:
                        if recovery_quote is None:
                            # Use the post-relief resources and the currently valid
                            # campaign-wide commitments at this decision boundary.
                            recovery_quote=war_recovery.Forecast(self.game,self.state,owner)
                        columns=[(order['source'],
                                  sum(self.state.officers[i].troops for i in order['officers']),
                                  self.war_budget(self.state.cities[order['source']],target,order['officers'],route)['immediate'])
                                 for order,route in scheduled]
                        risk=recovery_quote.assess(columns,target=target.id)
                        necessity=('existing_campaign' if target.id in historical_targets
                                   else 'existing_allied_battle' if joint and joint['troops']
                                   else 'countering_incoming_attack' if any(
                                       key in hostile_approaches.get(target.id,()) for key,_,_ in columns)
                                   else None)
                        necessary=necessity is not None
                        attack,prepare=war_recovery.action_score(power-required,required,risk['multiplier'],
                            risk['other_fronts']+risk['overlapping_fronts'],risk.get('source_grain_pressure',0),
                            necessary=necessary)
                        occupation_pressure = max((row['local_risk'] for row in occupied
                            if row['city'] not in {entry['city'] for entry in risk['cities']}),default=0)
                        if occupation_pressure and not necessary:
                            # Compare present exposure with the existing preparation
                            # score. It never becomes a second requisition.
                            prepare=max(prepare,war_recovery.OBJECTIVE_SCALE-25+occupation_pressure)
                        decision=dict(owner=owner,target=target.id,sources=[c[0] for c in columns],
                            plan_id=f'{owner}:{self.state.turn}:{target.id}',necessary=necessary,necessity=necessity,
                            **({'occupation_pressure':occupation_pressure}
                               if logistics_strategy.occupancy_budget(self.state) else {}),
                            attack_score=attack,prepare_score=prepare,recovery=risk)
                        if not necessary and attack<prepare:
                            deferred.append((prepare-attack,target.id,decision))
                            logistics_strategy.observe('war_recovery',self.state,result='prepare',**decision)
                            continue
                        score += (attack-prepare)*3
                        logistics_strategy.observe('war_recovery',self.state,result='eligible',**decision)
                    elif self.adaptive:
                        risk = sum(self.war_budget(self.state.cities[order['source']],target,order['officers'],route)
                                   ['recovery_risk'] for order,route in scheduled)
                        score -= risk // 2
                    feasible.append((-score, size, target.id, tuple(o['source'] for o in members), orders))
                if feasible:
                    # Do not send a second column merely to overrun an empty
                    # city that one legal army can already take safely.
                    winners.extend(feasible)
                    break
        if winners:
            self.recovery_wait.pop(owner,None)
            best = min(winners, key=lambda row: (row[2] != first, *row[:4]))
            return best[2], best[4]
        if deferred:
            _, target, decision = min(deferred,key=lambda row:row[:2])
            self.recovery_wait[owner]=decision['recovery']['cities']
            logistics_strategy.observe('war_recovery',self.state,result='deferred',**decision)
            return target,[]
        self.recovery_wait.pop(owner,None)
        if first:
            return first, []
        return (min(potential)[2] if potential else None), []

    def plan(self, owner):
        plans = self.state.extension['ai_strategy']
        old = plans.get(owner)
        turn = self.state.turn
        if old and old['last_turn'] == turn:
            return old
        target = self.state.cities.get(old['target']) if old else None
        valid = target and target.owner != owner and not historical_campaigns.allied(self.state, owner, target.owner)
        if valid:
            pending = []
            active = {m['id'] for m in self.state.extension['travel']['marches']}
            for order in old['orders']:
                if order['march_id'] is not None:
                    if order['march_id'] in active:
                        pending.append(order)
                    continue
                city = self.state.cities.get(order['source'])
                if city and city.owner == owner and all(i in self.available(city) for i in order['officers']):
                    pending.append(order)
            old['orders'] = pending
            launched = any(o['march_id'] is not None for o in pending)
            if pending and (turn <= old['arrival_turn'] or launched and turn <= old['arrival_turn']+1):
                old['last_turn'] = turn
                return old
            if turn < old['review_turn']:
                target, orders = self.objective(owner, None if self.endgame else old['target'])
                old.update(target=target, orders=orders, last_turn=turn,
                           arrival_turn=orders[0]['arrival_turn'] if orders else None)
                return old
        target, orders = self.objective(owner)
        current = dict(target=target, created_turn=turn, last_turn=turn,
            review_turn=turn+self.settings['plan_horizon_turns'],
            arrival_turn=orders[0]['arrival_turn'] if orders else None, orders=orders)
        plans[owner] = current
        return current

    def support_frontline(self, owner, plan):
        """Provision a threatened border before spending books on routine work."""
        if 'logistics' not in self.state.extension or owner in self.front_supply_checked:
            return
        pending = [order for order in plan['orders'] if order['march_id'] is None]
        due = sum(order['departure_turn'] <= self.state.turn for order in pending)
        if command_books.remaining(self.state, owner) <= due:
            return
        self.front_supply_checked.add(owner)

        from . import logistics
        from .battle_supply import BUDGET_DAYS

        requests = []
        recovery = {row['city']:row for row in self.recovery_wait.get(owner,()) if row['grain_gap'] or row['gold_gap']}
        occupied={row['city']:row for row in self.occupation.get(owner,()) if row['next_grain_gap']}
        sources = {order['source'] for order in pending} | set(recovery) | set(occupied)
        for city in logistics._fronts(self.game, self.state, owner):
            if not self.available(city):
                continue
            ids = self.defenders(city)
            troops = sum(self.state.officers[ident].troops for ident in ids)
            # Stock one full battle plus two turns of movement for a large army.
            grain_goal = max(grain_units.amount(3000), required_grain(troops, len(ids), BUDGET_DAYS + 20))
            gold_goal = 1500
            if city.id in recovery:
                grain_goal=max(grain_goal,city.grain+recovery[city.id]['grain_gap'])
                gold_goal=max(gold_goal,city.gold+recovery[city.id]['gold_gap'])
            if city.id in occupied:
                grain_goal=max(grain_goal,city.grain+occupied[city.id]['next_grain_gap'])
            gold, grain = logistics.supply_shortages(self.state, city, gold_goal, grain_goal)
            if gold >= 100 or grain >= grain_units.amount(300):
                shortage = gold * 100 // gold_goal + grain * 100 // grain_goal
                requests.append((city.id not in sources, -shortage, city.id, gold_goal, grain_goal))

        protected = {ident for order in pending for ident in order['officers']}
        protected.add(self.state.extension['leaders'].get(owner))
        if self.adaptive and logistics_strategy.pressure(self.state,'factions',owner,True,write=False) >= 3:
            requests.sort(key=lambda row: (row[0], not self.economy_plan(owner).budgets[row[2]]['threatened'], *row[1:]))
        else:
            requests.sort()
        for _, _, key, gold, grain in requests:
            if logistics.dispatch_ai_supply(self.game, self.state, self.state.cities[key], gold, grain,
                                            protected_officers=protected, require_return=True,
                                            max_turns=self.settings['max_route_turns'],
                                            **({'economy_plan':self.economy_plan(owner)} if self.v21 else {})):
                return

    def support_endgame(self, owner, plan):
        """Fund or reinforce one viable front while no attack is ready."""
        if (not self.endgame or plan['orders'] or not self.budget or owner in self.support_checked
                or owner in self.recovery_wait):
            return
        self.support_checked.add(owner)
        from . import ai_rally, logistics
        from .battle_supply import BUDGET_DAYS

        approaches = self.attack_approaches(owner)
        priority, first = self.priority_targets(owner, sorted(approaches))
        targets = sorted(priority or approaches)
        requests, fronts = [], []
        max_columns = min(self.settings['max_attack_sources'], self.budget)
        for key in targets:
            target = self.state.cities[key]
            required = self.attack_requirement(target)
            ready = sorted(((option['survivors'], source.id) for source in approaches[key]
                            if (option := self.attack_option(source, target)) is not None), reverse=True)
            power = sum(strength for strength, _ in ready[:max_columns])
            if power < required:
                fronts.append((key != first, (required-power)*100//required, key != plan['target'], key))
            if 'logistics' not in self.state.extension:
                continue
            for source in approaches[key]:
                option = self.attack_option(source, target, require_grain=False)
                if option is None:
                    continue
                grain = march_grain(self.state, option['officers'], option['quote'], game=self.game)
                budget=self.war_budget(source,target,option['officers'],option['quote'])
                if budget is not None and not budget['safe_return']:
                    continue
                goal=budget['required_grain'] if budget is not None else grain
                gold=budget['required_gold'] if budget is not None else 0
                if source.grain>=goal and source.gold>=gold:
                    continue
                supporting = [strength for strength, city_id in ready if city_id != source.id]
                if option['survivors'] + sum(supporting[:max_columns-1]) >= required:
                    ids = option['officers']
                    troops = sum(self.state.officers[ident].troops for ident in ids)
                    total_grain = goal if budget is not None else grain+required_grain(troops,len(ids),BUDGET_DAYS)
                    requests.append((key != first, option['quote']['days'], total_grain-source.grain,
                                     key, source.id, total_grain,gold))

        for _, _, _, key, source_id, grain,gold in sorted(requests):
            source = self.state.cities[source_id]
            if (not any(logistics.supply_shortages(self.state,source,gold,grain))
                    or logistics.dispatch_ai_supply(self.game,self.state,source,gold,grain,
                                                    max_turns=self.settings['max_route_turns'],
                                                    **({'economy_plan':self.economy_plan(owner)} if self.v21 else {}))):
                plan['target'] = key
                return

        for _, _, _, key in sorted(fronts):
            target = self.state.cities[key]
            fronts_for_target = {source.id for source in approaches[key]}
            for donor in sorted(self.state.cities.values(), key=lambda city: city.id):
                if (donor.owner == owner and donor.id not in fronts_for_target
                        and any(city.id in fronts_for_target for city in self.neighbors(donor))
                        and ai_rally.reinforce(self, donor, target)):
                    plan['target'] = key
                    return

    def depart(self, city, plan):
        for order in list(plan['orders']):
            if order['source'] != city.id or order['march_id'] is not None:
                continue
            if order['departure_turn'] > self.state.turn:
                return True  # Hold this city's column for the agreed arrival.
            target = self.state.cities.get(order['target'])
            ids = order['officers']
            joint = self.game._allied_attack_info(self.state, target, city.owner) if target else None
            if joint:
                ids = ids[:joint['remaining']]
            quote = self.quote(city, target, order['mode'], adjacent=True) if target else None
            usable = (ids and target and target.owner != city.owner
                      and not historical_campaigns.allied(self.state, city.owner, target.owner)
                      and all(i in self.army(city,target.id) for i in ids))
            budget=self.war_budget(city,target,ids,quote) if usable and quote is not None else None
            if (not usable or not self.safe(quote,ids) or not self.provisioned(city, ids, quote)
                    or budget is not None and not budget['can_depart']
                    or self.state.turn+winter_travel.quote_turns(self.game,self.state,quote) > order['arrival_turn']
                    or self.state.extension['ai_attacks'] >= self.budget):
                plan['orders'].remove(order)
                continue
            if self.state.turn+winter_travel.quote_turns(self.game,self.state,quote) < order['arrival_turn']:
                order['departure_turn'] = order['arrival_turn']-winter_travel.quote_turns(self.game,self.state,quote)
                return True
            if self.v21 and budget is not None:
                order['provision'] = budget['immediate']
            reserve=budget['immediate']-budget['outbound'] if budget is not None else None
            self.game._queue_march(self.state, city, target, ids, 'attack', order['mode'],battle_grain=reserve)
            order['officers'] = ids
            order['march_id'] = self.state.extension['travel']['counter']
            self.state.extension['ai_attacks'] += 1
            self.game._report_ai(self.state,city,'attack',target.id)
            return True
        return False

    def reinforce(self, city, plan):
        if self.threat(city):
            return False
        ids = self.army(city, transfer=True)
        if not ids:
            return False
        garrison_policy = logistics_strategy.enabled(self.state, logistics_strategy.GARRISON)
        economy = self.economy_plan(city.owner) if garrison_policy else None
        chronic = garrison_policy and logistics_strategy.pressure(self.state, 'cities', city.id, True, write=False) >= 3
        destinations = []
        stage_missing = {}
        eligible = []
        for target in self.state.cities.values():
            if target.id == city.id or target.owner != city.owner:
                continue
            frontier = [n for n in self.neighbors(target) if n.owner != city.owner
                        and not historical_campaigns.allied(self.state, city.owner, n.owner)]
            if not frontier:
                continue
            if plan['target'] and not chronic and not any(n.id==plan['target'] for n in frontier):
                continue
            incoming = [m for m in self.state.extension['travel']['marches']
                        if m['target']==target.id and m['owner']==city.owner]
            inbound = sum(len(m['officers']) for m in incoming)
            if garrison_policy:
                finance = economy.budgets[target.id]
                inbound_troops = sum(self.state.officers[ident].troops for m in incoming for ident in m['officers'])
                support = finance['sustainable_combined'] - self.strength(target) - inbound_troops
                if support<=0 and not finance['threatened']:
                    continue
                if finance['zero_in'] is not None and finance['zero_in'] <= 3:
                    continue
            else:
                support = None
            room = self.game.catalog.rules.city_officer_capacity-self.game._city_occupancy(self.state,target)-inbound
            if room <= 0:
                continue
            eligible.append((target, room, support))
        self.reinforcement_quotes(city, [target for target, _, _ in eligible])
        for target, room, support in eligible:
            for mode in ('land','fastest'):
                quote = self.quote(city,target,mode,adjacent=False)
                chosen = []
                if quote:
                    for ident in ids:
                        if len(chosen) >= min(3, room):
                            break
                        candidate = chosen + [ident]
                        troops = sum(self.state.officers[officer].troops for officer in candidate)
                        threatened = economy is not None and economy.budgets[target.id]['threatened']
                        if support is not None and not threatened and troops>support:
                            continue
                        if self.provisioned(city,candidate,quote):
                            chosen = candidate
                        elif (logistics_strategy.staging(self.state) and not chosen and len(quote['routes'])>1
                              and self.safe(quote,candidate)):
                            from . import staging_supply
                            loaded,stops=staging_supply.assess(self.game,self.state,city,candidate,quote,economy.budgets)
                            if loaded<=staging_supply.available(self.state,city):
                                for stop in stops:
                                    gap=stop['required']-stop['reserved']
                                    if gap:
                                        order=(stop['arrival'],stop['city'],gap)
                                        stage_missing.setdefault(stop['city'],order)
                if chosen and self.safe(quote,chosen):
                    destinations.append((self.strength(target)-self.threat(target),winter_travel.quote_days(self.game,self.state,quote),target.id,mode,chosen))
        if not destinations:
            if stage_missing and self.prepare_checkpoint(city.owner,stage_missing,economy):
                return True
            return False
        _,_,key,mode,chosen = min(destinations,key=lambda row:row[:4])
        kwargs = {'staging_budgets':economy.budgets} if logistics_strategy.staging(self.state) else {}
        try:
            self.game._queue_march(self.state,city,self.state.cities[key],chosen,'transfer',mode,**kwargs)
        except GameError:
            if not kwargs:
                raise
            return False
        if kwargs:
            self.economy_plans.pop(city.owner,None)
        self.game._report_ai(self.state,city,'transfer',key)
        return True

    def prepare_checkpoint(self,owner,missing,economy):
        """Fund one real checkpoint before trying the route again."""
        from . import escort_planning, facilities, logistics
        if owner in self.staging_checked:
            return False
        self.staging_checked.add(owner)
        when,key,grain=min(missing.values())
        city=self.state.cities[key]
        if city.owner!=owner:
            return False
        protected=escort_planning.assigned_to_war(self.state,city)
        gap=grain
        result='deferred'
        # Existing convoys must arrive before the quoted departure plus its
        # first leg. Later deliveries never count as immediate inventory.
        eta=max(1,(when-(self.state.turn-1)*10+9)//10)
        scheduled=sum(x for t,(_,_,x) in enumerate(economy.cities[key].timeline,1) if t<=eta)
        if scheduled>=grain:
            result='awaiting_transport'
        elif facilities._ready(self.state,owner) and command_books.can_spend(self.state,owner,'trade_grain'):
            budget=economy.budgets[key]
            offer=facilities.emergency_quote(self.game,self.state,city,grain)
            actor=next((i for i in self.available(city) if i not in protected and
                facilities._resident(self.game,self.state,city,i,working=True,unused=True,healthy=True)),None)
            if actor is not None and offer['grain'] and city.gold-offer['gold']>=budget['wage_gold']:
                receipt=facilities.buy_emergency_grain(self.game,self.state,key,actor,owner,grain)
                gap-=receipt['grain']
                result='market_purchase'
        if result=='deferred':
            floor=economy.budgets[key]['minimum_export_floor']
            if logistics.dispatch_ai_supply(self.game,self.state,city,0,max(floor,city.grain)+grain,
                    require_return=True,protected_officers=protected,max_turns=eta,economy_plan=economy):
                result='transport_dispatched'
        logistics_strategy.observe('staging_preparation',self.state,owner=owner,city=key,
                                   expected_tick=when,grain_required=grain,gap=gap,result=result)
        if result in {'market_purchase','transport_dispatched'}:
            self.economy_plans.pop(owner,None)
            self.grain_outlooks.pop(owner,None)
            return True
        return False

    def record_pressure(self, owner):
        state = self.state
        _, shortages = self.grain_outlook(owner)
        pressure = bool(grain_relief.imminent_shortages(shortages)) or any(
            row['threatened'] for row in self.economy_plan(owner).budgets.values())
        strategy = state.extension['ai_strategy'].get(owner, {})
        effective = any(order['march_id'] is not None for order in strategy.get('orders', ()))
        effective = effective or any(
            report['owner'] == owner and report['turn'] == state.turn and
            report['kind'] == 'transport_departed' and report['details']['grain'] > 0
            for report in state.extension['logistics']['reports']
            if report['target'] not in shortages)
        return logistics_strategy.pressure(state,'factions',owner,pressure and not effective)

    def prepare(self, city):
        if 'domestic' in self.state.extension:
            # Both sides allocate through the appointed military official at
            # faction-turn end, after reserved frontline cargo has departed.
            # Do not run the older AI-only, fee-charging partial top-up first.
            return
        # Allocation never creates soldiers. Retain a local reserve on an
        # exposed front instead of draining its whole pool into the expedition.
        guard = min(city.reserves,self.settings['min_guard_troops']) if self.threat(city) else 0
        for ident in sorted(self.available(city),key=lambda i:(self.state.officers[i].troops,ref_sort_key(i))):
            officer = self.state.officers[ident]
            amount = min(80,max(0,city.reserves-guard),max(0,600-officer.troops))
            if amount and city.gold >= 4 and city.grain >= grain_units.amount(8):
                officer.troops += amount;city.reserves -= amount;city.gold -= 4;city.grain -= grain_units.amount(8)

    def personnel_or_recruit(self, city):
        x, r = self.state.extension, self.game.catalog.data['rules']
        ids = self.available(city)
        free = self.game._free_candidates(self.state,city)
        if ids and free and self.game._city_occupancy(self.state,city)<self.game.catalog.rules.city_officer_capacity and city.gold>=r['recruit_officer_gold']:
            actor = min((self.state.officers[i] for i in ids),key=lambda o:(-o.profile.virtue,-o.profile.intellect,ref_sort_key(o.runtime_id)))
            ident = min(free,key=ref_sort_key)
            target = self.state.officers[ident]
            chance = max(15,min(95,35+actor.profile.virtue//2+actor.profile.intellect//5-target.profile.virtue//5))
            command_books.spend(self.state,city,'recruit_officer');city.gold -= r['recruit_officer_gold']
            x['officer_actions'][str(actor.runtime_id)] = self.state.turn
            if self.state.rng.next()%100 < chance:
                target.faction_id = city.owner
                leader = self.state.officers[x['leaders'][city.owner]]
                target.loyalty = recruitment_loyalty(leader.profile.virtue,target.loyalty)
                officer_relations.apply(self.game,self.state,ident)
                city.roster.officer_ids.append(ident);x['free_locations'].pop(str(ident),None)
                x['officer_actions'][str(ident)] = self.state.turn
            self.game._report_ai(self.state,city,'recruit_officer',str(ident))
            return
        clerks = sorted((p for p in x['civil_staff']['people'].values()
            if p['city'] == city.id and p['owner'] == city.owner and p['working'] and p['health'] > 0),
            key=lambda p:(-p['profile']['virtue'],-p['profile']['intellect'],p['id']))
        if clerks and free and self.game._city_occupancy(self.state,city)<self.game.catalog.rules.city_officer_capacity and city.gold>=r['recruit_officer_gold']:
            ident = min(free,key=ref_sort_key)
            self.game._staff_recruit_for_owner(self.state,city,clerks[0]['id'],ident,city.owner)
            self.game._report_ai(self.state,city,'staff_recruit',str(ident))
            return
        ledger = x['civil_staff']['cities'].get(city.id)
        if ledger and ledger['candidate'] and city.gold >= civil_staff.RULES['hire_gold']:
            staff_id = ledger['candidate']['id']
            try:
                civil_staff.hire(self.game,self.state,city.id,staff_id,city.owner)
            except GameError:
                pass
            else:
                self.game._report_ai(self.state,city,'hire_staff',staff_id)
                return
        if (ids or clerks) and city.reserves<200 and city.gold>=r['recruit_gold_per_100'] and city.grain>=grain_units.amount(r['recruit_grain_per_100']):
            city.reserves += r['recruit_per_action'];self.state.soldiers['recruited'] += r['recruit_per_action']
            command_books.spend(self.state,city,'recruit');city.gold -= r['recruit_gold_per_100'];city.grain -= grain_units.amount(r['recruit_grain_per_100'])
            self.game._report_ai(self.state,city,'recruit_soldiers')
            return
        candidates = self.game._persuadable(self.state,city)
        if ids and candidates and self.game._city_occupancy(self.state,city)<self.game.catalog.rules.city_officer_capacity and city.gold>=r['persuade_officer_gold'] and not any(report['turn']==self.state.turn and report['action']=='persuade_officer' for report in x['ai_reports']):
            actor = min((self.state.officers[i] for i in ids),key=lambda o:(-o.profile.virtue,ref_sort_key(o.runtime_id)))
            ident = min(candidates,key=lambda i:(self.state.officers[i].loyalty,ref_sort_key(i)))
            self.game._attempt_defection(self.state,city,actor,ident)
            self.game._report_ai(self.state,city,'persuade_officer',str(ident))
            self.game._reconcile_factions(self.state)
            self.quotes.clear()


def _open_ai_queue(campaign, state):
    priority = {owner: rank for rank, owner in enumerate(historical_campaigns.priority_factions(state))}

    def order(owner):
        return priority.get(owner, len(priority)), owner

    owners = {city.owner for city in state.cities.values() if city.owner not in (state.player, 'neutral')}
    planner = StrategicAI(campaign, state)
    for owner in sorted(owners, key=order):
        for payload in diplomacy_ai.orders(planner, owner):
            try:
                diplomacy.execute(campaign, state, payload, owner)
            except GameError:
                continue
            if state.phase != 'ai':
                return
            if planner.v21:
                # A treaty or surrender can change holdings, available
                # officers and transit permissions inside the same AI phase.
                planner = StrategicAI(campaign,state)
            else:
                planner.quotes.clear()
            break

    x = state.extension
    x['ai_queue'] = [city.id for city in sorted(state.cities.values(), key=lambda city: (*order(city.owner), city.id))
                     if city.owner not in (state.player, 'neutral')]
    x['ai_cursor'] = 0
    x['ai_attacks'] = 0


def run(campaign, state, payload):
    if state.phase != 'ai' or payload.get('turn') != state.turn:
        raise GameError('当前不是待处理的电脑回合。')
    # Resuming an interrupted city queue must not repeat this turn's diplomacy.
    if not state.extension['ai_queue']:
        historical_campaigns.dispatch_frontier_sorties(campaign, state)
        _open_ai_queue(campaign, state)
        if state.phase != 'ai':
            return
    x = state.extension
    ai = StrategicAI(campaign,state)
    has_domestic = 'domestic' in x
    escort_checked = set()
    relief_done = {state.cities[key].owner for key in x['ai_queue'][:x['ai_cursor']] if key in state.cities}
    if has_domestic:
        from .domestic import prepare_ai, prioritize_grain
        for owner in sorted(campaign.catalog.factions):
            if owner != state.player:
                prepare_ai(campaign,state,owner)
    while x['ai_cursor'] < len(x['ai_queue']):
        key = x['ai_queue'][x['ai_cursor']];x['ai_cursor'] += 1
        city = state.cities.get(key)
        if city is None or city.owner in (state.player,'neutral') or not command_books.can_spend(state,city.owner):
            continue
        if logistics_strategy.staging(state) and city.owner not in escort_checked:
            from . import escort_planning
            escort_checked.add(city.owner)
            if any(row['owner']==city.owner for row in state.extension['travel']['marches']):
                if escort_planning.prepare(campaign,state,city.owner,ai.economy_plan(city.owner)):
                    ai.economy_plans.pop(city.owner,None)
                    ai.grain_outlooks.pop(city.owner,None)
        outlook = ai.grain_outlook(city.owner)
        if ai.v21 and has_domestic and city.owner not in relief_done:
            outlook = prioritize_grain(campaign, state, city.owner, outlook,
                                        economy_plan=ai.economy_plan(city.owner))
            relief_done.add(city.owner)
            ai.grain_outlooks[city.owner] = outlook
            ai.economy_plans.pop(city.owner, None)
            if winter_weather.stage(state)>=5:
                from . import winter_strategy
                winter_strategy.prepare(ai,city.owner)
        if outlook[0] is not None and not ai.military_budget:
            if has_domestic and city.owner not in relief_done:
                prioritize_grain(campaign, state, city.owner, outlook)
                relief_done.add(city.owner)
            x['ai_strategy'].pop(city.owner, None)
            continue
        for _ in range(command_books.MAXIMUM):
            remaining = command_books.remaining(state, city.owner)
            if not command_books.can_spend(state, city.owner):
                break
            plan = ai.plan(city.owner)
            ai.support_endgame(city.owner, plan)
            # A final offensive may already be provisioning this town.
            # Check its new inbound cargo before spending another convoy.
            if has_domestic and city.owner not in relief_done:
                prioritize_grain(campaign, state, city.owner, outlook)
                relief_done.add(city.owner)
            if not command_books.can_spend(state, city.owner):
                break
            ai.prepare(city)
            if not ai.depart(city,plan):
                ai.support_frontline(city.owner, plan)
                if (command_books.can_spend(state, city.owner) and not ai.reinforce(city,plan)
                        and 'domestic' not in x):
                    ai.personnel_or_recruit(city)
            if state.phase != 'ai':
                return
            if command_books.remaining(state, city.owner) == remaining:
                break
    x['ai_queue'] = [];x['ai_cursor'] = 0;x['ai_attacks'] = 0
    if 'domestic' in x:
        from .domestic import finish_faction_turn
        owners = (sorted({city.owner for city in state.cities.values()} - {state.player,'neutral'})
                  if ai.v21 else sorted(campaign.catalog.factions))
        for owner in owners:
            if owner != state.player:
                finish_faction_turn(campaign, state, owner, outlook=ai.grain_outlook(owner))
                if ai.adaptive:
                    ai.record_pressure(owner)
    campaign._complete_turn(state)
    campaign._reconcile_factions(state)


def validate_strategies(campaign, state):
    """Validate persistent receipts while permitting legitimate mid-march changes."""
    plans = state.extension['ai_strategy']
    if not isinstance(plans,dict) or not set(plans)<=set(campaign.catalog.factions):
        raise ValueError('AI strategy factions')
    marches = {m['id']:m for m in state.extension['travel']['marches']}
    fields = {'target','created_turn','last_turn','review_turn','arrival_turn','orders'}
    order_fields = {'source','target','mode','departure_turn','arrival_turn','officers','march_id'}
    for owner, plan in plans.items():
        if not isinstance(plan,dict) or set(plan)!=fields:
            raise ValueError('AI strategy fields')
        if plan['target'] is not None and plan['target'] not in campaign.catalog.map_cities:
            raise ValueError('AI strategy target')
        integer(plan['created_turn'],1,state.turn,'AI strategy creation')
        integer(plan['last_turn'],plan['created_turn'],state.turn,'AI strategy cursor')
        integer(plan['review_turn'],plan['created_turn'],1000000,'AI strategy review')
        if plan['arrival_turn'] is not None:
            integer(plan['arrival_turn'],plan['created_turn']+1,1000000,'AI strategy arrival')
        if not isinstance(plan['orders'],list) or len(plan['orders'])>3:
            raise ValueError('AI strategy orders')
        sources, scheduled = set(), set()
        for order in plan['orders']:
            if (not isinstance(order,dict) or
                    set(order) not in (order_fields, order_fields | {'provision'})):
                raise ValueError('AI strategy order fields')
            if 'provision' in order:
                if logistics_strategy.FIELD not in state.extension:
                    raise ValueError('AI strategy reservation requires strategy version')
                integer(order['provision'],0,100000000,'AI strategy grain reservation')
            if (order['source'] not in campaign.catalog.map_cities or order['target']!=plan['target']
                    or order['source']==order['target'] or order['source'] in sources
                    or order['mode'] not in ('fastest','land','sea','river','special')):
                raise ValueError('AI strategy route')
            sources.add(order['source'])
            integer(order['departure_turn'],plan['created_turn'],1000000,'AI departure schedule')
            integer(order['arrival_turn'],order['departure_turn']+1,1000000,'AI arrival schedule')
            if order['arrival_turn']!=plan['arrival_turn']:
                raise ValueError('AI coordination arrival')
            ids = order['officers']
            if not isinstance(ids,list) or not 1<=len(ids)<=10 or len(ids)!=len(set(ids)):
                raise ValueError('AI scheduled deployment')
            if scheduled.intersection(ids):
                raise ValueError('AI officer scheduled twice')
            scheduled.update(ids)
            for ident in ids:
                campaign.catalog.rules.officer_id(ident)
                if ident not in state.officers:
                    raise ValueError('AI scheduled officer')
            ident = order['march_id']
            if ident is not None:
                integer(ident,1,state.extension['travel']['counter'],'AI march receipt')
                if ident in marches:
                    march = marches[ident]
                    mission = march.get('mission')
                    # Supply stops can postpone the active arrival, and a
                    # shortage can redirect a real column toward a friendly
                    # city. Travel validates those current journeys; link the
                    # strategy to the unchanged original order instead.
                    if (march['owner'] != owner or not isinstance(mission,dict)
                            or any(mission.get(key) != value for key,value in
                                (('source',order['source']),('target',order['target']),
                                 ('kind','attack'),('mode',order['mode']),
                                 ('departure_turn',order['departure_turn']),
                                 ('arrival_turn',order['arrival_turn'])))):
                        raise ValueError('AI march does not match its plan')
