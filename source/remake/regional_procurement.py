"""Legal directed route and landed-cost quotes for existing city markets."""
from collections import Counter, defaultdict
from hashlib import sha256

from . import (army_relief, command_books, domestic, economic_regions, facilities,
               grain_market, historical_campaigns, logistics, logistics_rules, march_supply,
               market_pricing, staging_supply, transport_capacity, winter_travel, winter_weather)

BASE = 1_000
COMMERCIAL_SHARE = 25


def landed_cents(gold, extra_grain, reference_price, net, other_gold=0):
    """Hundredths of gold per 1,000 delivered grain, rounded to nearest."""
    if net <= 0:
        return None
    mills = (gold + other_gold) * BASE + extra_grain * reference_price
    return (mills * 100 + net // 2) // net


def quota_left(state, city, direction):
    ledger = market_pricing.pool(state)
    used = ledger['quotas'].get(city, {}).get(direction, 0)
    return max(0, grain_market.row(state,city)['monthly_supply'] * COMMERCIAL_SHARE // 100 - used)


def role_scores(city, market, budget, *, legal_modes=(), contacts=0):
    """Update overlapping roles from current budgets and already quoted links."""
    def ratio(value, scale):
        return min(100,max(0,value)*100//max(1,scale))

    supply, fixed = market['monthly_supply'], budget.get('fixed',0)
    agriculture = ratio(budget.get('regular',0),2*fixed)
    export = ratio(budget.get('exportable',0),max(fixed,supply))
    purchasing = ratio(city.gold,max(1,supply//50))
    replenishment = ratio(market['stock'],supply)
    return dict(agricultural_output=(agriculture+export+replenishment)//3 if contacts else 0,
        commercial_purchase=(purchasing+replenishment+ratio(budget.get('regular_gold',0),city.gold)
                             + min(100,contacts*25))//4,
        military_consumption=(ratio(budget.get('garrison',0),fixed)
                              + ratio(-budget.get('net',0),fixed))//2,
        transport_connection=min(100,contacts*15+len(legal_modes)*15),
        strategic_stock=ratio(city.grain,budget.get('target',0)) if budget.get('months')==12 else 0)


def _meal(game, state, quote, escort, *, offset=0):
    if winter_weather.movement(state):
        days, weight, ice = winter_travel.checkpoint_forecast(game,state,quote)
        if ice is not None or days is None or winter_travel.route_risk(game,state,quote,days+offset):
            return None
        wait = (-days) % 10
        region = game.catalog.climate.cities[quote['path'][-1]]['climate_region_id']
        wait_weight=wait*winter_travel.wait_rate(state,region)
    else:
        days=quote['days']
        parts=logistics_rules.plan(quote,march_supply.travel_rules(game))
        weight=logistics_rules.weight(parts)
        wait_weight=(-days)%10*logistics_rules.RATION_SCALE
    units=march_supply.ration_units(state,[escort])
    budget=army_relief.ration_budget(units,weight,wait_weight,0)
    return days,budget.outbound+budget.wait


def _entity(game, state, owner, source, active, absent, decision, posts, *, automatic):
    ledger = logistics._pool(state)['cities'][source.id]
    policy=transport_capacity.ai_policy(state,owner,ledger['policy'],automatic=automatic)
    if transport_capacity.dispatch_blocker(state,source,active):
        return None, 'source_transport_busy'
    if not policy['max_grain'] or not policy['max_officers']:
        return None, 'source_policy'
    if automatic and historical_campaigns.hold_longyou_garrison(game,state,source):
        return None, 'source_defence'
    officers=[i for i in source.roster.officer_ids if i not in absent and state.officers[i].alive
              and state.officers[i].faction_id==owner]
    if len(officers)<=policy['reserve_officers']:
        return None, 'no_escorts'
    locked={posts.get('civil'),posts.get('military')}
    if automatic:
        from . import escort_planning
        locked.update(escort_planning.assigned_to_war(state,source))
        locked.add(state.extension['leaders'].get(owner))
    eligible=[i for i in officers if i not in locked and state.officers[i].health>0
              and logistics._pool(state)['receipts'].get(str(i),0)<=state.turn
              and state.extension.get('civil_staff',{}).get('people',{}).get(i,{}).get('working',True)]
    if transport_capacity.enabled(state):
        allowed=set(logistics._eligible(game,state,source,absent=absent,automatic=automatic))
        eligible=[i for i in eligible if i in allowed and logistics.escort_defence(game,state,source,[i])]
    if not eligible:
        return None, 'no_escorts'
    escort=min(eligible,key=lambda i:(state.officers[i].troops,logistics._key(i)))
    budget=decision.budgets.get(source.id,{}) if decision is not None else {}
    if budget.get('threatened') and automatic:
        from .difficulty import get_settings
        if budget['active']-state.officers[escort].troops < min(budget['active'],get_settings(state)['min_guard_troops']):
            return None, 'source_defence'
    # Military budgets already include staging commitments. Subtract each
    # source reservation only once before checking the physical ration budget.
    unreserved = min(staging_supply.available(state,source),source.grain-budget.get('reserved_grain',0))
    from . import strategic_granary
    if strategic_granary.enabled(state):
        unreserved = min(unreserved, strategic_granary.available(state,source))
    floor = max(policy['reserve_grain'], budget.get('minimum_export_floor',0),
                budget.get('next_installment',0),budget.get('safety_reserve',0) if budget.get('threatened') else 0)
    return (source,policy,escort,max(0,unreserved-floor)), None


class Planner:
    """One demand pass. Path books are scoped to the unchanged route state."""

    def __init__(self, game, state, owner, *, decision=None, automatic=False):
        self.game, self.state, self.owner = game,state,owner
        self.decision, self.automatic = decision,automatic
        self.holdings=[c for c in state.cities.values() if c.owner==owner]
        self.active=transport_capacity.activity(state)
        self.absent=game._march_ids(state) | facilities._battle_ids(state)
        self.posts=domestic.appointments(state,owner)
        self.routes={}
        self.work=Counter()

    def _route_book(self, target, candidates):
        groups=defaultdict(list)
        for city,policy,*_ in candidates:
            groups[policy['allow_sea'],policy['allow_special']].append((city.id,policy))
        for preferences, entries in groups.items():
            key=(target.id,preferences)
            pairs={(city,target.id) for city,_ in entries}
            missing=pairs-self.routes.get(key,({},set()))[1]
            if missing:
                pair_list=sorted(missing | {(b,a) for a,b in missing})
                paths=logistics._supply_routes(self.game,self.state,self.owner,pair_list,entries[0][1])
                stored,visited=self.routes.setdefault(key,({},set()))
                stored.update(paths)
                visited.update(missing)
                self.work.update(route_searches=1,quotations=len(pair_list))
            else:
                self.work['cache_hits']+=1
        return {k:self.routes[target.id,k][0] for k in groups}

    def options(self, target, requested, *, source=None, purpose='procurement', deadline=None):
        game,state,owner=self.game,self.state,self.owner
        failures=Counter()
        if (market_pricing.stage(state)<market_pricing.PROCUREMENT or not facilities._ready(state,owner)
                or target.owner!=owner or not command_books.can_spend(state,owner,2)):
            return [], {'city_or_orders':1}
        candidates=[]
        for city in self.holdings:
            if city.id==target.id or source is not None and city.id!=source:
                continue
            prices=market_pricing.snapshot(game,state,city.id)
            data=grain_market.row(state,city.id)
            forecast=self.decision.cities.get(city.id) if self.decision is not None else None
            if self.automatic and forecast is not None and forecast.zero_in is not None:
                failures['source_demand']+=1
                continue
            floor=data['monthly_supply'] if self.automatic and (purpose=='trade' or deadline is None or deadline>30) else 0
            cap=facilities._rule(game,'trade_max_batches') * facilities._rule(game,'trade_batch_grain')
            amount=min(data['stock']-floor,city.gold*BASE//prices['buy'],logistics.LIMIT-city.grain,cap)
            if self.automatic and purpose=='trade':
                amount=min(amount,quota_left(state,city.id,'buy'))
            if amount<=0:
                failures['source_stock' if data['stock']<=floor else
                         'source_gold' if city.gold*BASE<prices['buy'] else 'source_capacity']+=1
                continue
            entity,reason=_entity(game,state,owner,city,self.active,self.absent,self.decision,self.posts,
                                  automatic=self.automatic)
            if reason:
                failures[reason]+=1
                continue
            _,policy,escort,ration_stock=entity
            if policy['target_city'] not in (None,target.id):
                failures['source_policy']+=1
                continue
            candidates.append((city,policy,escort,ration_stock,amount,prices))
        self.work['candidate_sources']+=len(candidates)
        if not candidates:
            return [],dict(failures)
        network=self._route_book(target,candidates)
        destination=market_pricing.snapshot(game,state,target.id)
        results=[]
        roles={}
        for city,policy,escort,ration_stock,amount,prices in candidates:
            quotes=network[policy['allow_sea'],policy['allow_special']]
            outward=logistics._safe_options(game,state,city,target,policy,quotes=quotes)
            backward=logistics._safe_options(game,state,target,city,policy,quotes=quotes)
            if not outward or not backward:
                failures['no_directed_round_trip']+=1
                continue
            if self.decision is not None:
                roles[city.id]=role_scores(city,grain_market.row(state,city.id),self.decision.budgets[city.id],
                    legal_modes={leg['mode'] for _,quote in outward for leg in quote['routes']},contacts=1)
            market=grain_market.row(state,city.id)
            free_space=logistics.LIMIT-target.grain
            for mode,route in outward:
                meal=_meal(game,state,route,escort)
                back=_meal(game,state,backward[0][1],escort,offset=meal[0] if meal else 0)
                if not meal or not back:
                    failures['unsafe_ice']+=1
                    continue
                days, outbound=meal
                protect=logistics_rules.ceil_div((outbound+back[1])*110,100)
                if protect>ration_stock:
                    failures['source_rations']+=1
                    continue
                cap=min(amount,policy['max_grain'],free_space)
                loading=None
                if transport_capacity.enabled(state,'physical_capacity'):
                    loading=transport_capacity.loading(game,state,owner,policy,route,protect,amount+protect,free_space,
                                                        automatic=self.automatic)
                    cap=loading['max_cargo']
                if cap<=0:
                    failures['route_capacity' if loading is not None and free_space>0 else 'destination_capacity']+=1
                    continue
                parts=logistics_rules.plan(route,march_supply.travel_rules(game))
                risks=game._march_risks(route,None)
                project=lambda n:army_relief.net_cargo(game,route,n,parts=parts,risks=risks,state=state)
                if purpose=='trade':
                    batch=facilities._rule(game,'trade_batch_grain')
                    market_room=grain_market.available(state,target.id,'sell')
                    if self.automatic:
                        market_room=min(market_room,quota_left(state,target.id,'sell'))
                    if market_room<batch:
                        failures['destination_market_full']+=1
                        continue
                    wanted=min(cap,requested or cap)
                    cargo=wanted//batch*batch
                    if cargo and project(cargo)>market_room:
                        gross,_=army_relief.shipment(game,route,market_room,cargo,parts,risks,state=state)
                        cargo=gross//batch*batch
                    net=project(cargo) if cargo else 0
                    sold=min(market_room,net)//batch*batch
                    if not sold:
                        failures['too_small_to_sell']+=1
                        continue
                else:
                    cargo,net=army_relief.shipment(game,route,requested,cap,parts,risks,state=state)
                    sold=0
                if not net:
                    failures['no_net_delivery']+=1
                    continue
                gold=logistics_rules.ceil_div(cargo*prices['buy'],BASE)
                ref=destination['buy']
                cost=landed_cents(gold,outbound+back[1],ref,net)
                # The displayed sale projection is current only. Give the
                # automated decision a price buffer for the arrival month.
                sale=destination['sell']
                if self.automatic and purpose=='trade':
                    from .army_relief import projected_state
                    future=projected_state(state,(state.turn-1)*10+days)
                    season=facilities.MARKET_MONTHLY_ADJUSTMENTS[future.month-1]
                    sale=max(1,min(sale,destination['base_sell']+season+destination['adjustment'])-1)
                revenue=sold*sale//BASE
                econ_milli=(revenue-gold)*BASE-(outbound+back[1])*ref
                row=dict(source=city.id,target=target.id,owner=owner,actor=escort,
                         purpose=purpose,requested=requested or 0,cargo=cargo,net=net,
                         gold=gold,rate=prices['buy'],source_quote=prices['token'],reference_price=ref,
                         escort_rations=protect,expected_rations=outbound+back[1],return_rations=back[1],
                         days=days,return_days=back[0],arrival_turn=state.turn+logistics_rules.ceil_div(days,10),
                         deadline=deadline,timely=None if deadline is None else logistics_rules.ceil_div(days,10)*10<deadline,
                         route_mode=mode,route=route['path'],legs=[r['id'] for r in route['routes']],
                         route_types=sorted({r['mode'] for r in route['routes']}),estimated_loss=cargo-net,
                         source_region=economic_regions.region(city.id),target_region=economic_regions.region(target.id),
                         landed_cents=cost,sale_rate=sale,estimate_sale_grain=sold,estimated_revenue=revenue,
                         economic_result_milli=econ_milli)
                row['token']=sha256(repr(tuple(sorted(row.items()))).encode()).hexdigest()[:24]
                # These describe the same executable route and balances. They
                # are independent of the signed terms used by the purchase.
                row.update(source_stock=market['stock'],source_market_capacity=market['capacity'],
                    target_warehouse_room=free_space,transport_capacity=cap,return_route=backward[0][1]['path'],
                    return_route_types=sorted({leg['mode'] for leg in backward[0][1]['routes']}))
                if loading is not None:
                    row['capacity']=loading
                results.append(row)
        self.work['evaluations']+=1
        role='commercial_purchase' if purpose=='trade' else 'agricultural_output'
        if self.automatic and transport_capacity.enabled(state,'throughput_ranking'):
            def rank(row):
                wait=(-row['days'])%10+(-row['return_days'])%10
                return (row['timely'] is False,*transport_capacity.priority(row['net'],row['escort_rations'],
                    row['days'],row['return_days'],wait,1,logistics.RULES['receipt_turns'],row['landed_cents']),
                    -roles.get(row['source'],{}).get(role,0),row['source'],row['route_mode'])
            return sorted(results,key=rank),dict(failures)
        return sorted(results,key=lambda q:(q['timely'] is False,q['landed_cents'],-q['net'],q['days'],
            -roles.get(q['source'],{}).get(role,0),q['source'],q['route_mode'])),dict(failures)
