"""Persistent, deterministic campaign planning using ordinary game orders.

Coordinated columns remain separate legal ten-officer armies. Their departure
dates, rather than edited march receipts, align their existing arrival service.
Planning only reads published state; actual recruitment still owns its RNG roll.
"""
from copy import copy
from itertools import combinations

from .difficulty import attack_budget, get_settings
from .errors import GameError
from .officers import integer, recruitment_loyalty, ref_sort_key
from . import civil_staff
from .route_hazards import allocate_survivors


class StrategicAI:
    def __init__(self, campaign, state):
        self.game, self.state = campaign, state
        self.settings = get_settings(state)
        self.budget = attack_budget(campaign.catalog, state)
        self.quotes = {}

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
        return [self.state.cities[k] for k in self.game._neighbors(city.id, self.state)
                if k in self.state.cities]

    def threat(self, city, exclude=None):
        hostile = [self.strength(c) for c in self.neighbors(city)
                   if c.id != exclude and c.owner not in (city.owner, 'neutral')]
        incoming = [sum(self.state.officers[i].troops for i in m['officers'])
                    for m in self.state.extension['travel']['marches']
                    if m['target'] == city.id and m['owner'] != city.owner and m['kind'] == 'attack']
        return sum(sorted(hostile, reverse=True)[:2]) + sum(incoming)

    def available(self, city):
        marching = self.game._march_ids(self.state)
        return sorted((i for i in city.roster.officer_ids if i not in marching
                       and self.state.officers[i].alive and self.state.officers[i].health > 0
                       and self.state.extension['officer_actions'].get(str(i)) != self.state.turn),
                      key=lambda i: (-self.state.officers[i].troops, ref_sort_key(i)))

    def army(self, city, target=None, *, transfer=False):
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
        month = self.month_at(self.state.turn if departure is None else departure)
        key = source.id, target.id, source.owner, mode, adjacent, month
        if key not in self.quotes:
            snapshot = copy(self.state)
            snapshot.month = month
            self.quotes[key] = self.game._travel_path(snapshot, source.id, target.id,
                                                      source.owner, mode, adjacent=adjacent)
        return self.quotes[key]

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
        if not quote or quote['turns'] > self.settings['max_route_turns']:
            return False
        total = sum(self.state.officers[i].troops for i in ids)
        return bool(total) and self.survivors(quote, ids)*100 >= total*(100-self.settings['max_route_loss_percent'])

    def attack_option(self, city, target):
        ids = self.army(city, target.id)
        total = sum(self.state.officers[i].troops for i in ids)
        if total < self.settings['min_attack_troops'] or city.grain < max(1, total//25):
            return None
        options = []
        for mode in ('land', 'fastest'):
            quote = self.quote(city, target, mode, adjacent=True)
            if self.safe(quote, ids):
                survivors = self.survivors(quote, ids)
                options.append(dict(source=city.id, target=target.id, officers=ids,
                                    mode=mode, quote=quote, survivors=survivors))
        return min(options, key=lambda o: (-o['survivors'], o['quote']['days'],
                                          o['quote']['distance_km'], o['mode'])) if options else None

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
                    if self.safe(quote, member['officers']) and departure+quote['turns'] == arrival:
                        found = dict(source=source.id, target=target.id, mode=member['mode'],
                            departure_turn=departure, arrival_turn=arrival,
                            officers=list(member['officers']), march_id=None)
                        break
                if found is None:
                    break
                orders.append(found)
            if len(orders) == len(members):
                return orders
        return []

    def objective(self, owner, preferred=None):
        cities = [c for c in self.state.cities.values() if c.owner == owner]
        targets = sorted({c.id for city in cities for c in self.neighbors(city) if c.owner != owner})
        if preferred in targets:
            targets = [preferred]
        available_budget = max(0, self.budget-self.state.extension['ai_attacks'])
        winners, potential = [], []
        for key in targets:
            target = self.state.cities[key]
            defend = self.strength(target)
            potential.append((defend, -target.grain, target.id))
            options = [o for city in cities if not city.action_used
                       and (o := self.attack_option(city, target)) is not None]
            options.sort(key=lambda o: (-o['survivors'], o['quote']['days'], o['source']))
            # Limit enumeration to the six strongest approaches, then at most
            # three legal armies. This keeps a large campaign's plan bounded.
            limit = min(self.settings['max_attack_sources'], available_budget)
            for size in range(1, limit+1):
                feasible = []
                for members in combinations(options[:6], size):
                    power = sum(o['survivors'] for o in members)
                    required = max(self.settings['min_attack_troops'],
                                   (defend*self.settings['attack_ratio_percent']+99)//100)
                    if power < required:
                        continue
                    orders = self.schedule(members)
                    if not orders:
                        continue
                    days = sum(o['quote']['days'] for o in members)
                    supply = sum(max(1, sum(self.state.officers[i].troops for i in o['officers'])//25) for o in members)
                    score = min(power-required,required//3)-days*3-supply*2+min(200,target.gold//20+target.grain//200)
                    feasible.append((-score, size, target.id, tuple(o['source'] for o in members), orders))
                if feasible:
                    # Do not send a second column merely to overrun an empty
                    # city that one legal army can already take safely.
                    winners.extend(feasible)
                    break
        if winners:
            best = min(winners, key=lambda row: row[:4])
            return best[2], best[4]
        return (min(potential)[2] if potential else None), []

    def plan(self, owner):
        plans = self.state.extension['ai_strategy']
        old = plans.get(owner)
        turn = self.state.turn
        if old and old['last_turn'] == turn:
            return old
        valid = old and old['target'] in self.state.cities and self.state.cities[old['target']].owner != owner
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
                target, orders = self.objective(owner, old['target'])
                old.update(target=target, orders=orders, last_turn=turn,
                           arrival_turn=orders[0]['arrival_turn'] if orders else None)
                return old
        target, orders = self.objective(owner)
        current = dict(target=target, created_turn=turn, last_turn=turn,
            review_turn=turn+self.settings['plan_horizon_turns'],
            arrival_turn=orders[0]['arrival_turn'] if orders else None, orders=orders)
        plans[owner] = current
        return current

    def depart(self, city, plan):
        for order in list(plan['orders']):
            if order['source'] != city.id or order['march_id'] is not None:
                continue
            if order['departure_turn'] > self.state.turn:
                return True  # Hold this city's column for the agreed arrival.
            target = self.state.cities.get(order['target'])
            ids = order['officers']
            quote = self.quote(city, target, order['mode'], adjacent=True) if target else None
            usable = target and target.owner != city.owner and all(i in self.army(city,target.id) for i in ids)
            if (not usable or not self.safe(quote,ids) or city.grain < max(1,sum(self.state.officers[i].troops for i in ids)//25)
                    or self.state.turn+quote['turns'] > order['arrival_turn']
                    or self.state.extension['ai_attacks'] >= self.budget):
                plan['orders'].remove(order)
                continue
            if self.state.turn+quote['turns'] < order['arrival_turn']:
                order['departure_turn'] = order['arrival_turn']-quote['turns']
                return True
            self.game._queue_march(self.state, city, target, ids, 'attack', order['mode'])
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
        destinations = []
        for target in self.state.cities.values():
            if target.id == city.id or target.owner != city.owner:
                continue
            frontier = [n for n in self.neighbors(target) if n.owner != city.owner]
            if not frontier:
                continue
            if plan['target'] and not any(n.id==plan['target'] for n in frontier):
                continue
            inbound = sum(len(m['officers']) for m in self.state.extension['travel']['marches']
                          if m['target']==target.id and m['owner']==city.owner)
            room = self.game.catalog.rules.city_officer_capacity-self.game._city_occupancy(self.state,target)-inbound
            if room <= 0:
                continue
            for mode in ('land','fastest'):
                quote = self.quote(city,target,mode,adjacent=False)
                chosen = ids[:min(3,room,city.grain//quote['grain_per_officer'])] if quote else []
                if chosen and self.safe(quote,chosen):
                    destinations.append((self.strength(target)-self.threat(target),quote['days'],target.id,mode,chosen))
        if not destinations:
            return False
        _,_,key,mode,chosen = min(destinations,key=lambda row:row[:4])
        self.game._queue_march(self.state,city,self.state.cities[key],chosen,'transfer',mode)
        self.game._report_ai(self.state,city,'transfer',key)
        return True

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
            if amount and city.gold >= 4 and city.grain >= 8:
                officer.troops += amount;city.reserves -= amount;city.gold -= 4;city.grain -= 8

    def personnel_or_recruit(self, city):
        x, r = self.state.extension, self.game.catalog.data['rules']
        ids = self.available(city)
        free = self.game._free_candidates(self.state,city)
        if ids and free and self.game._city_occupancy(self.state,city)<self.game.catalog.rules.city_officer_capacity and city.gold>=r['recruit_officer_gold']:
            actor = min((self.state.officers[i] for i in ids),key=lambda o:(-o.profile.virtue,-o.profile.intellect,ref_sort_key(o.runtime_id)))
            ident = min(free,key=ref_sort_key)
            target = self.state.officers[ident]
            chance = max(15,min(95,35+actor.profile.virtue//2+actor.profile.intellect//5-target.profile.virtue//5))
            city.gold -= r['recruit_officer_gold'];city.action_used = True
            x['officer_actions'][str(actor.runtime_id)] = self.state.turn
            if self.state.rng.next()%100 < chance:
                target.faction_id = city.owner
                leader = self.state.officers[x['leaders'][city.owner]]
                target.loyalty = recruitment_loyalty(leader.profile.virtue,target.loyalty)
                city.roster.officer_ids.append(ident);x['free_locations'].pop(str(ident),None)
                x['officer_actions'][str(ident)] = self.state.turn
            self.game._report_ai(self.state,city,'recruit_officer',str(ident))
            return
        clerks = sorted((p for p in x['civil_staff']['people'].values()
            if p['city'] == city.id and p['owner'] == city.owner and p['working'] and p['health'] > 0
            and p['action_turn'] != self.state.turn),
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
        if (ids or clerks) and city.reserves<200 and city.gold>=r['recruit_gold_per_100'] and city.grain>=r['recruit_grain_per_100']:
            city.reserves += r['recruit_per_action'];self.state.soldiers['recruited'] += r['recruit_per_action']
            city.gold -= r['recruit_gold_per_100'];city.grain -= r['recruit_grain_per_100'];city.action_used = True
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


def run(campaign, state, payload):
    if state.phase != 'ai' or payload.get('turn') != state.turn:
        raise GameError('当前不是待处理的电脑回合。')
    x = state.extension
    ai = StrategicAI(campaign,state)
    if 'domestic' in x:
        from .domestic import prepare_ai
        for owner in sorted(campaign.catalog.factions):
            if owner != state.player:
                prepare_ai(campaign,state,owner)
    if not x['ai_queue']:
        x['ai_queue'] = [c.id for c in sorted(state.cities.values(),key=lambda c:(c.owner,c.id))
                         if c.owner not in (state.player,'neutral')]
        x['ai_cursor'] = 0;x['ai_attacks'] = 0
    while x['ai_cursor'] < len(x['ai_queue']):
        key = x['ai_queue'][x['ai_cursor']];x['ai_cursor'] += 1
        city = state.cities.get(key)
        if city is None or city.owner in (state.player,'neutral') or city.action_used:
            continue
        plan = ai.plan(city.owner)
        ai.prepare(city)
        if not ai.depart(city,plan) and not ai.reinforce(city,plan):
            if 'domestic' not in x:
                ai.personnel_or_recruit(city)
        if 'domestic' not in x:
            city.action_used = True
        if state.phase != 'ai':
            return
    x['ai_queue'] = [];x['ai_cursor'] = 0;x['ai_attacks'] = 0
    if 'domestic' in x:
        from .domestic import finish_faction_turn
        for owner in sorted(campaign.catalog.factions):
            if owner != state.player:
                finish_faction_turn(campaign,state,owner)
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
            if not isinstance(order,dict) or set(order)!=order_fields:
                raise ValueError('AI strategy order fields')
            if (order['source'] not in campaign.catalog.map_cities or order['target']!=plan['target']
                    or order['source']==order['target'] or order['source'] in sources
                    or order['mode'] not in ('fastest','land','sea','special')):
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
                if ident in marches and any(marches[ident][key]!=value for key,value in
                    (('source',order['source']),('target',order['target']),('owner',owner),
                     ('kind','attack'),('departure_turn',order['departure_turn']),('arrival_turn',order['arrival_turn']))):
                    raise ValueError('AI march does not match its plan')
