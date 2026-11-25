"""Army convoy quotes, node meetings and outstanding physical deliveries."""
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from typing import NamedTuple

from . import command_books, historical_campaigns, logistics, logistics_rules as rules, march_supply
from .grain_units import denominator

WAIT_DAYS = 3
SAFETY_PERCENT = 10
EFFICIENCY_PREFERRED = 70
EFFICIENCY_NORMAL = 50
EFFICIENCY_MINIMUM = 30
# Keep an elective wait within the current route-supply horizon.
MAX_LATE_DAYS = march_supply.RETREAT_DAYS
FIELD = 'relief'
REASONS = ('army_supplied', 'unsafe_return', 'rendezvous_expired', 'rendezvous_replanned')


class Budget(NamedTuple):
    outbound: int
    wait: int
    returning: int
    safety: int

    @property
    def total(self):
        return sum(self)


def ration_budget(units, outward, waiting, backward, *, credit=0, safety=SAFETY_PERCENT):
    """Carry fractional ration credit across the route, wait and return."""
    divisor = denominator()*rules.RATION_SCALE
    weights = (outward, outward+waiting, outward+waiting+backward)
    costs = [max(0, rules.ceil_div(units*weight-credit, divisor)) for weight in weights]
    return Budget(costs[0], costs[1]-costs[0], costs[2]-costs[1],
                  rules.ceil_div(costs[2]*safety, 100))


@dataclass(frozen=True)
class Window:
    city: str
    start: int
    end: int


@dataclass(frozen=True)
class Need:
    army_id: int
    deadline: int
    required: int
    urgent: bool
    stopped: bool = False

    @property
    def key(self):
        return f'{self.army_id}:{self.deadline}'


def boundary(tick):
    return rules.ceil_div(tick, 10)*10


def projected_state(state, tick):
    months = (state.day-1 + max(0, tick-(state.turn-1)*10))//30
    if not months:
        return state
    future = copy(state)
    future.year += (future.month-1+months)//12
    future.month = (future.month-1+months)%12+1
    return future


def windows(state, army, *, stopped=False):
    book, route = army['supply'], army['quote']
    if book['retreat_requested'] or army.get('retreating') or army.get('returning'):
        return ()
    clock, progress = book['clock_tick'], book['route_days']
    places = []
    elapsed = 0
    for index, city in enumerate(route['path']):
        if index:
            elapsed += route['routes'][index-1]['days']
        if elapsed < progress:
            continue
        if index and index < len(route['routes']) and not historical_campaigns.transit_allowed(
                state, army['owner'], state.cities[city].owner):
            break
        if state.cities[city].owner != army['owner']:
            continue
        start = clock + elapsed-progress
        end = boundary(start) if index == len(route['routes']) else start
        if elapsed == progress and (book['waiting'] or stopped):
            end = max(end, clock + (max(0, MAX_LATE_DAYS-book['shortage_streak'])
                                   if book['shortage_streak'] or stopped else WAIT_DAYS))
            places.append(Window(city, start, end))
            # A stopped column has no dependable date for later nodes.
            break
        places.append(Window(city, start, end))
    return tuple(places)


def requirement(game, state, army):
    book, quote = army['supply'], army['quote']
    now, progress = book['clock_tick'], book['route_days']
    left = quote['days']-progress
    urgent = bool(book['shortage_streak'] or book['waiting'] and left)
    days = march_supply.next_supply_days(state, quote, army['owner'], progress)
    if not left and not urgent:
        return Need(army['id'], now, 0, False)
    # Cover the next actual supply point. A stopped column may need food
    # through a bounded node wait before a new move is possible.
    horizon = days if days else MAX_LATE_DAYS if urgent else 0
    units = march_supply.ration_units(state, army['officers'])
    parts = rules.plan(quote, march_supply.travel_rules(game))
    funded = book['remaining']*march_supply.book_denominator(book)+book['credit_units']

    def weight(span):
        travel = min(span, left)
        return rules.weight(parts, progress, travel) + (span-travel)*rules.RATION_SCALE

    required = max(0, rules.ceil_div(units*weight(horizon)-funded, march_supply.book_denominator(book)))
    node=march_supply.current_city(army)
    stopped=(bool(required and node and state.cities[node].owner==army['owner']
                  and state.cities[node].grain<required and left>0))
    urgent |= stopped
    # A waiting column consumes its next ration now and may use a same-day
    # delivery before its next scheduled meal.
    through, lower = horizon, 0
    while lower < through:
        middle = (lower+through)//2
        if units*weight(middle+1) > funded:
            through = middle
        else:
            lower = middle+1
    return Need(army['id'], now if urgent else now+lower, required, urgent, stopped)


def net_requirement(needed, estimates, deadline):
    return max(0, needed-sum(grain for eta, grain in estimates if eta <= deadline))


def _receive_room(game, state, city, owner, ids):
    return (city.owner == owner
            and game._city_occupancy(state,city)+sum(i not in city.roster.officer_ids for i in ids)
                <= game.catalog.rules.city_officer_capacity)


def safe_end(game, state, source, meeting, owner, ids, policy, tick, *, home=None, quotes=None):
    """Prefer the actual home, then an owned node with space and a legal route."""
    home = home or source
    future = projected_state(state, tick)
    origin = copy(state.cities[meeting])
    origin.owner = owner
    original = state.cities[home]
    if _receive_room(game, state, original, owner, ids):
        if meeting == home:
            return 'land', game._quote([meeting], [])
        selected = logistics._safe_quote(game, future, origin, original, policy,
                                         quotes=quotes if future is state else None)
        if selected:
            return selected
    if _receive_room(game, state, state.cities[meeting], owner, ids):
        return 'land', game._quote([meeting], [])
    cities = [city for city in state.cities.values()
              if city.id != home and _receive_room(game,state,city,owner,ids)]
    if state.cities[meeting].owner == owner and cities:
        batch = logistics._supply_routes(game, future, owner, [(meeting, c.id) for c in cities], policy)
    else:
        batch = None
    choices = []
    for city in cities:
        selected = logistics._safe_quote(game, future, origin, city, policy, quotes=batch)
        if selected:
            mode, quote = selected
            choices.append((quote['days'], city.id, mode, quote))
    if choices:
        _, _, mode, quote = min(choices, key=lambda row:row[:3])
        return mode, quote
    return None


def net_cargo(game, quote, grain, *, progress=0, remainder=0, risks=None, parts=None):
    if parts is None:
        parts=rules.plan(quote,march_supply.travel_rules(game))
    net=rules.estimate_cargo(grain,parts,quote['days']-progress,
                             start=progress,remainder=remainder)[0]
    risks=game._march_risks(quote,None) if risks is None else risks
    for risk in risks:
        if risk['applied']:
            continue
        percent=risk['survival_numerator']
        if percent is None:
            hazard=quote['routes'][risk['legs'][0]]['hazard']
            percent=100-hazard['loss_percent_max']
        net=net*percent//risk['survival_denominator']
    return net


def shipment(game,route,need,room,parts,risks):
    def after(amount):
        return net_cargo(game,route,amount,parts=parts,risks=risks)
    high=room
    if after(high)<need:
        return high,after(high)
    low=need
    while low<high:
        middle=(low+high)//2
        if after(middle)>=need:
            high=middle
        else:
            low=middle+1
    return low,after(low)


def escort_band(troops):
    return sum(troops > limit for limit in (500, 1000, 3000, 5000))


def efficiency(net, cargo, bag):
    return 100*net//max(1, cargo+bag)


def escort_rank(state, ident):
    officer = state.officers[ident]
    # A depleted escort remains eligible only under the existing health rule.
    return (escort_band(officer.troops), officer.troops, -officer.health,
            -officer.profile.martial_strength, logistics._key(ident))


def timing(window, now, travel):
    arrives = now+travel
    meeting = max(arrives, window.start)
    if meeting > window.end:
        return None
    # Journeys settle at the normal turn boundary, including after handoff.
    wait_until = boundary(meeting+WAIT_DAYS)
    return meeting, max(0, wait_until-arrives)


def _calendar_tick(state):
    return (state.turn-1)*10


class Planner:
    """Scoped to one domestic transport pass or one read-only preview."""
    def __init__(self, game, state, owner):
        self.game, self.state, self.owner = game, state, owner
        self.armies = {row['id']:row for row in state.extension['travel']['marches']
                       if row['owner']==owner and row['officers']}
        self.demands = {ident:requirement(game,state,row) for ident,row in self.armies.items()}
        self.windows = {ident:windows(state,row,stopped=self.demands[ident].stopped) for ident,row in self.armies.items()
                        if self.demands[ident].required}
        self.convoys = defaultdict(list)
        for row in logistics._pool(state)['convoys']:
            if row['owner']==owner and row['target_march'] is not None:
                self.convoys[row['target_march']].append(row)
        self.busy = {row['source'] for row in logistics._pool(state)['convoys']}
        self.stats = dict(predictions=len(self.demands), route_pairs=0, meeting_quotes=0, return_cache_hits=0)
        self.return_quotes = {}

    def estimates(self, ident, *, exclude=None):
        game, state = self.game, self.state
        slots = {slot.city:slot for slot in self.windows.get(ident, ())}
        for row in self.convoys[ident]:
            if row['id']==exclude or row['delivery_done'] or row['status']=='returning':
                continue
            current = row['journeys'][-1]
            book, route = current['supply'], current['quote']
            slot = slots.get(row['target'])
            if slot is None or book['retreat_requested'] or not row['cargo']['grain']:
                continue
            eta = max(slot.start, book['clock_tick']+route['days']-book['route_days'])
            if eta > slot.end:
                continue
            planned = row.get(FIELD)
            grain = net_cargo(game,route,row['cargo']['grain'],progress=book['route_days'],
                              remainder=row[logistics.LOSS_FIELD],risks=current['risks'])
            if planned:
                bag = ration_budget(march_supply.ration_units(state,row['officers']),
                    march_supply.route_weight(route, route['days']-book['route_days'],
                        offset=book['route_days'],game=game,version=rules.CURRENT),
                    max(0,boundary(eta)-book['clock_tick']-(route['days']-book['route_days']))*rules.RATION_SCALE,
                    planned['return_weight'], credit=book['credit_units']).total
                grain = max(0, grain-max(0,bag-book['remaining']))
            if grain:
                yield eta, grain

    def source_reason(self, source, policy):
        state = self.state
        if state.phase not in {'city','ai'}:
            return 'wrong_phase'
        if source.owner not in self.game.catalog.factions:
            return 'not_owned'
        if not command_books.can_spend(state,source.owner,'dispatch_transport'):
            return 'command_books'
        if (source.id in self.busy
                or logistics._pool(state)['cities'][source.id]['last_dispatch_turn']==state.turn):
            return 'in_transit'
        if not policy['max_officers'] or logistics._present_count(self.game,state,source)<=policy['reserve_officers']:
            return 'no_spare_officer'
        return None

    def candidates(self, source, *, budget=None, selected=None, cargo=None, origin=None, live=None):
        game, state = self.game, self.state
        key = source.id
        policy = logistics._pool(state)['cities'][key]['policy'] if live is None else live['route_policy']
        if live is None:
            reason = self.source_reason(source, policy)
            if reason:
                return (), reason
        ids = sorted(logistics._eligible(game,state,source),key=lambda i:escort_rank(state,i)) if live is None else live['officers']
        if selected is not None:
            ids = selected['officers']
        if not ids:
            return (), 'no_spare_officer'
        floor = policy['reserve_grain'] if live is None else 0
        if selected is not None and len(ids)>policy['max_officers']:
            return (), 'no_spare_officer'
        if budget:
            floor = max(floor,budget['minimum_export_floor'],budget['safety_reserve'])+budget['reserved_grain']
        available = source.grain-floor if live is None else live['journeys'][-1]['supply']['remaining']+live['cargo']['grain']
        home = key if live is None else live['source']
        now = _calendar_tick(state)
        remaining = {}
        for ident,demand in self.demands.items():
            if (selected is not None and ident!=selected['march_id']) or (live and ident!=live['target_march']):
                continue
            if demand.required:
                booked = tuple(self.estimates(ident,exclude=live['id'] if live else None))
                need = net_requirement(demand.required,booked,demand.deadline)
                if need:
                    remaining[ident] = demand, booked
        if not remaining:
            return (), 'army_supplied'
        slot_cities = {slot.city for ident in remaining for slot in self.windows.get(ident,())}
        origin = source if origin is None else origin
        pairs = sorted({(a,b) for city in slot_cities for a,b in ((origin.id,city),(city,home))
                        if a!=b and state.cities[a].owner==source.owner and state.cities[b].owner==source.owner})
        quotes = logistics._supply_routes(game,state,source.owner,pairs,policy) if pairs else {}
        self.stats['route_pairs'] += len(pairs)
        results, blocked = [], 'no_route'
        for ident,(demand, booked) in remaining.items():
            for slot in self.windows.get(ident,()):
                if selected is not None and slot.city!=selected['city']:
                    continue
                # A healthy army already at its friendly final city will be
                # processed by the normal city and transfer services.
                if slot.city==origin.id:
                    options=[('land',game._quote([origin.id],[]))]
                elif selected is not None and selected['mode'] not in ('land','fastest'):
                    quoted=logistics._safe_path(game,state,origin.id,slot.city,source.owner,selected['mode'],policy,
                                                officers=ids,cargo=cargo or 0)
                    options=[(selected['mode'],quoted)] if quoted is not None else []
                else:
                    options=logistics._safe_options(game,state,origin,state.cities[slot.city],policy,
                        quotes=quotes if state.cities[origin.id].owner==source.owner else None)
                for mode,route in options:
                    if logistics._dangerous(route,policy):
                        continue
                    if selected is not None and mode!=selected['mode']:
                        continue
                    dates = timing(slot,now,route['days'])
                    if dates is None:
                        continue
                    eta, wait = dates
                    if eta > demand.deadline+MAX_LATE_DAYS:
                        continue
                    needed = net_requirement(demand.required,booked,max(eta,demand.deadline))
                    if not needed:
                        continue
                    self.stats['meeting_quotes'] += 1
                    maximum = policy['max_grain'] if live is None else live['cargo']['grain']
                    # Return route is stable for these officers until climate,
                    # ownership or actual reception space changes.
                    return_tick = boundary(eta)
                    outward_parts=rules.plan(route,march_supply.travel_rules(game))
                    outward=rules.weight(outward_parts,0,route['days'])
                    risks=game._march_risks(route,None)
                    season = projected_state(state,return_tick)
                    missing_slot = len(ids) if live or selected else 1
                    candidates = [ids] if selected is not None or live is not None else [[i] for i in ids]
                    for team in candidates:
                        troop_count = sum(state.officers[i].troops for i in team)
                        if budget and budget['threatened'] and selected is None and live is None:
                            from .difficulty import get_settings
                            if budget['active']-troop_count < min(budget['active'],get_settings(state)['min_guard_troops']):
                                blocked='defence'
                                continue
                        observed_slot = sum(i not in state.cities[slot.city].roster.officer_ids for i in team)
                        # At normal dispatch with unaltered home ownership, all
                        # eligible officers already have a reserved home slot.
                        return_key = (slot.city,home,season.year,season.month,observed_slot,missing_slot)
                        if return_key in self.return_quotes:
                            back = self.return_quotes[return_key]
                            self.stats['return_cache_hits'] += 1
                        else:
                            back = safe_end(game,state,key,slot.city,source.owner,team,policy,return_tick,
                                            home=home,quotes=quotes)
                            self.return_quotes[return_key] = back
                        if back is None:
                            blocked='unsafe_return'
                            continue
                        backward = march_supply.route_weight(back[1],back[1]['days'],game=game,version=rules.CURRENT)
                        credit = live['journeys'][-1]['supply']['credit_units'] if live else 0
                        bag = ration_budget(troop_count+100*len(team),outward,wait*rules.RATION_SCALE,
                                            backward,credit=credit)
                        room=max(0,min(maximum,available-bag.total))
                        if cargo is not None:
                            room=cargo if cargo<=room else 0
                            net=net_cargo(game,route,room,parts=outward_parts,risks=risks)
                        elif room:
                            room,net=shipment(game,route,needed,room,outward_parts,risks)
                        else:
                            net=0
                        percent=efficiency(net,room,bag.total)
                        urgent=demand.urgent or eta<=demand.deadline<=now+WAIT_DAYS
                        if not net or selected is None and percent<EFFICIENCY_NORMAL and not urgent:
                            blocked='low_efficiency' if net else 'insufficient_grain'
                            continue
                        if selected is None and percent<EFFICIENCY_MINIMUM and (not demand.urgent or net*4<needed):
                            blocked='low_efficiency'
                            continue
                        if selected is None and troop_count>5000 and (not urgent or net*2<needed):
                            blocked='heavy_escort'
                            continue
                        result=dict(march_id=ident,city=slot.city,officers=list(team),quote=route,route_mode=mode,
                            cost_grain=bag.total, max_grain=room, needed_grain=needed, eta_turn=state.turn+route['turns'])
                        result[FIELD]=dict(request_id=demand.key,deadline=demand.deadline,required=needed,
                            eta_tick=eta, wait_until=boundary(eta+WAIT_DAYS),wait_days=wait, cargo=room,
                            estimated_net=min(needed,net), return_city=back[1]['path'][-1],return_days=back[1]['days'],
                            return_weight=backward, outbound=bag.outbound, wait=bag.wait, returning=bag.returning,
                            safety=bag.safety, efficiency=percent, escort_troops=troop_count)
                        rank=(eta>demand.deadline, not demand.urgent, cap_time(eta,demand.deadline),
                              -min(net,needed), percent<EFFICIENCY_PREFERRED, room+bag.total,
                              escort_band(troop_count), troop_count, route['days'], slot.city, mode,
                              tuple(logistics._key(i) for i in team))
                        results.append((rank,result))
                        break
        return tuple(row for _,row in sorted(results,key=lambda item:item[0])), blocked

    def register(self, row):
        self.convoys[row['target_march']].append(row)
        self.busy.add(row['source'])


def cap_time(eta, deadline):
    return max(0,eta-deadline)


def validate(row, state):
    facts=row[FIELD]
    city=facts.get('return_city') if isinstance(facts,dict) else None
    numbers = {'deadline','required','eta_tick','wait_until','wait_days','cargo','estimated_net','return_days',
               'return_weight','outbound','wait','returning','safety','efficiency','escort_troops'}
    if (not row['target_march'] or not isinstance(facts,dict)
            or set(facts)!=numbers|{'request_id','return_city'} or city not in state.cities
            or any(type(facts[field]) is not int or not 0<=facts[field]<=100*logistics.LIMIT for field in numbers)
            or facts['request_id']!=f"{row['target_march']}:{facts['deadline']}"
            or facts['eta_tick']>facts['wait_until'] or facts['efficiency']>100
            or facts['estimated_net']>facts['cargo'] or not facts['required']
            or sum(facts[field] for field in ('outbound','wait','returning','safety'))>logistics.LIMIT):
        raise ValueError('Army relief quote')


def dispatch_error(reason):
    return {
        'army_supplied':'部队已有足够或及时到达的粮食，毋须重复派运。',
        'unsafe_return':'押运队没有可安全抵达的友方返程城池。',
        'insufficient_grain':'扣除往返、等待及备用口粮后，货粮或本城余粮不足。',
    }.get(reason, '部队已移动或会合时限已过，请重新选择实际会合城池。')


def hold_reason(game, state, row, tick):
    """At a real node, stop a mission that must turn around or replan."""
    journey=row['journeys'][-1]
    army=logistics._army(state,row['target_march'],row['owner'])
    if row['delivery_done']:
        return 'delivered'
    if army is None or army['supply']['retreat_requested'] or army.get('retreating'):
        return 'army_missing'
    if state.cities[row['target']].owner!=row['owner']:
        return 'target_changed'
    if row['reason'] in REASONS and row['reason']!='rendezvous_replanned':
        return row['reason']
    actual_tick=journey['supply']['clock_tick']+1 if tick is None else tick
    progress=journey['supply']['route_days']
    if (actual_tick+journey['quote']['days']-progress > row[FIELD]['wait_until']
            or row['reason']=='rendezvous_missed'):
        return 'rendezvous_expired'
    if progress<journey['quote']['days']:
        next_days=march_supply.next_supply_days(state,journey['quote'],row['owner'],progress)
        forward=march_supply.route_weight(journey['quote'],next_days,offset=progress,game=game,
                                           version=rules.CURRENT)
        bag=journey['supply']
        units=march_supply.ration_units(state,row['officers'])
        if units*forward>(bag['remaining']+row['cargo']['grain'])*march_supply.book_denominator(bag)+bag['credit_units']:
            return 'unsafe_return'
    return None


def _return_budget(game,state,row,quote,wait=0):
    supply=row['journeys'][-1]['supply']
    weight=march_supply.route_weight(quote,quote['days'],game=game,version=rules.CURRENT)
    return ration_budget(march_supply.ration_units(state,row['officers']),0,
                         wait*rules.RATION_SCALE,weight,credit=supply['credit_units']).total


def handoff(game,state,row,army,city,tick,maximum):
    from . import logistics_strategy
    if city != row['target'] or state.cities[city].owner!=row['owner'] or row['reason'] in REASONS and row['reason']!='rendezvous_replanned':
        return 0
    need=requirement(game,state,army)
    if not need.required:
        row['reason']='army_supplied'
        return 0
    quote=safe_end(game,state,row['source'],city,row['owner'],row['officers'],row['route_policy'],boundary(tick))
    if quote is None:
        row['reason']='unsafe_return'
        return 0
    protected=_return_budget(game,state,row,quote[1],boundary(tick)-tick)
    bag=row['journeys'][-1]['supply']['remaining']
    net=min(need.required,maximum-max(0,protected-bag))
    if net<=0:
        row['reason']='unsafe_return'
        return 0
    logistics_strategy.observe('relief_handoff',state,convoy=row['id'],army=army['id'],city=city,
                               tick=tick,grain=net,protected=protected,bag=bag,remaining_need=need.required-net)
    return net


def return_home(game,state,row,here,reason):
    book=row['journeys'][-1]['supply']
    selected=safe_end(game,state,row['source'],here,row['owner'],row['officers'],row['route_policy'],
                      _calendar_tick(state))
    if selected is None:
        row.update(status='waiting',reason='no_return_route')
        book['waiting']=True
        return False
    mode,quote=selected
    needed=_return_budget(game,state,row,quote)
    available=book['remaining']+row['cargo']['grain']
    local=state.cities[here]
    if (needed>available and local.owner==row['owner']
            and logistics._receiving_blocker(game,state,row,local,returning=True) is None):
        quote=game._quote([here],[])
        needed=0
    target=quote['path'][-1]
    if not quote['days']:
        row.update(status='returning',reason=reason)
        return logistics._dock(game,state,row,state.cities[target])
    if logistics._begin_journey(game,state,row,here,target,mode,quote,status='returning',
                                reason=reason,prepaid=min(available,needed)):
        logistics._event(game,state,'transport_returned',row,reason=reason)
        return True
    return False


def settle(game,state,row):
    """Apply a route decision once at the shared turn boundary."""
    from . import logistics_strategy
    current=row['journeys'][-1]
    city=march_supply.current_city(current)
    if city is None:
        return True
    now=_calendar_tick(state)
    row['checked_turn']=state.turn
    army=logistics._army(state,row['target_march'],row['owner'])
    if row['delivery_done']:
        return_home(game,state,row,city,'escort_return')
        return True
    if army is None or army['supply']['retreat_requested'] or army.get('returning') or army.get('retreating'):
        return_home(game,state,row,city,'army_missing')
        return True
    planner=Planner(game,state,row['owner'])
    need=planner.demands[army['id']]
    if (not row['cargo']['grain'] or not net_requirement(need.required,planner.estimates(
            army['id'],exclude=row['id']),need.deadline)):
        return_home(game,state,row,city,'army_supplied')
        return True
    rest=current['quote']['days']-current['supply']['route_days']
    window=next((node for node in planner.windows[army['id']] if node.city==row['target']),None)
    if (window and max(now+rest,window.start)<=min(window.end,row[FIELD]['wait_until'])
            and row['reason'] not in REASONS and not current['supply']['retreat_requested']):
        if not rest:
            current['supply']['waiting']=True
            row.update(status='waiting',reason='rendezvous_wait')
        return True
    # At this point the previous agreement can no longer hold. A second
    # journey uses the remaining receipted food, including real cargo refills.
    origin=copy(state.cities[city])
    origin.owner=row['owner']
    options,reason=planner.candidates(origin,live=row)
    if options:
        best=options[0]
        if logistics._begin_journey(game,state,row,city,best['city'],best['route_mode'],best['quote'],
                                   status='outbound',reason='rendezvous_replanned',prepaid=best['cost_grain']):
            row[FIELD]=best[FIELD]
            logistics_strategy.observe('relief_replanned',state,convoy=row['id'],army=army['id'],
                old_city=current['target'],old_days=rest,new_city=best['city'],new_days=best['quote']['days'],
                reason=reason, plan=best[FIELD])
            return True
    logistics_strategy.observe('relief_cancelled',state,convoy=row['id'],army=army['id'],
                               city=city,reason=reason)
    return_home(game,state,row,city,'rendezvous_expired')
    return True
