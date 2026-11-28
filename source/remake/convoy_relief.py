"""Physical grain handoffs to stranded ordinary convoys, using army relief quotes."""
from dataclasses import dataclass

from . import army_relief, historical_campaigns, logistics, march_supply
from . import transport_emergency as emergency
from . import transport_capacity, winter_travel


@dataclass(frozen=True)
class Demand:
    ident: int
    city: str
    required: int
    wait_until: int
    meal_per_day: int

    @property
    def root(self):
        return f'convoy:{self.ident}'


def request(game, state, row):
    if (row['target_march'] is not None or 'convoy_relief' in row
            or not row['officers'] and not any(row['cargo'].values())):
        return None
    plan = row.get('emergency', {})
    if plan.get('status') not in ('waiting_for_supply','no_feasible_exit') or plan['route_budget'] is None:
        return None
    book = emergency.book(row)
    here = march_supply.current_city(row['journeys'][-1])
    if here is None or state.cities[here].owner != row['owner'] or not row['officers'] and not row['cargo']['reserves']:
        return None
    live = emergency.available(row) + emergency.stock(game, state, state.cities[here])
    required = max(0, plan['route_budget'] - live)
    if not required:
        return None
    return Demand(row['id'], here, required, book['clock_tick'] + emergency.RELIEF_DAYS, plan['meal_per_day'])


def _need_at_settlement(game,state,target,demand,meeting):
    # Handoffs are daily. The recipient can choose its next journey only once
    # the strategic turn settles, so it also needs meals through that boundary.
    remaining = max(0, army_relief.boundary(meeting)-emergency.book(target)['clock_tick'])
    weight = remaining*emergency.wait_weight(game,state,demand.city)
    waiting = army_relief.ration_budget(emergency.convoy_units(state,target),0,weight,0).wait
    return demand.required+waiting


def missions(state, owner):
    return (row for row in logistics._pool(state)['convoys'] if row['owner']==owner and 'convoy_relief' in row
            and row.get('return_leg')!=len(row['journeys'])-1
            and not emergency.book(row)['retreat_requested'] and not row['delivery_done'])


def outstanding(game, state, target, demand, *, review=None, active=None):
    remaining = []
    planner = review or emergency.Review(game,state)
    for row in missions(state,target['owner']) if active is None else active:
        saved = row['convoy_relief']
        if (saved['root']!=demand.root or row['target']!=demand.city
                or row['owner']!=target['owner'] or not row['cargo']['grain']):
            continue
        journey = row['journeys'][-1]
        book = emergency.book(row)
        progress = book['route_days']
        position = winter_travel.work(book)
        if 'winter' in book:
            days, outward, ice = winter_travel.checkpoint_forecast(game,state,journey['quote'],position=position)
            if ice is not None:
                continue
        else:
            days = journey['quote']['days'] - progress
            outward = march_supply.quoted_weight(game,state,journey['quote'],days,offset=progress)
        arrival = book['clock_tick'] + days
        if arrival > min(saved['wait_until'], demand.wait_until):
            continue
        predicted = army_relief.net_cargo(game,journey['quote'],row['cargo']['grain'],progress=progress,
            remainder=row[logistics.LOSS_FIELD],risks=journey['risks'],state=state,position=position)
        # The additional ration needed to finish, wait and return is held
        # before counting a delivery. A forecast is never added to the bag.
        back = planner.quotes(row['owner'], demand.city, row['route_policy']).get(row['source'], ())
        if not back:
            continue
        budget = army_relief.ration_budget(emergency.convoy_units(state,row), outward,
            (army_relief.boundary(arrival)-arrival)*emergency.wait_weight(game,state,demand.city),
            min(quote.weight for quote in back),credit=book['credit_units']).total
        net = max(0, predicted-max(0,budget-book['remaining']))
        if net:
            remaining.append((arrival,net))
    return tuple(remaining)


def _return_quote(review, owner, source, city, policy):
    back = review.quotes(owner, city, policy).get(source, ())
    return min(back, key=lambda q:(q.risk,q.weight,q.days), default=None)


class Planner:
    """One dispatch pass for a faction. Stock, books and ownership are rechecked."""
    def __init__(self, game, state, owner, *, coordinated=False):
        self.game, self.state, self.owner = game, state, owner
        self.coordinated = coordinated
        self.review = emergency.Review(game, state)
        self.targets = {row['id']:row for row in logistics._pool(state)['convoys']
                        if row['owner']==owner and row.get('emergency',{}).get('status') in
                        ('waiting_for_supply','no_feasible_exit') and 'convoy_relief' not in row}
        self.active = transport_capacity.activity(state)

    def quote(self, source, target, *, budget=None, selected=None, cargo=None):
        game,state = self.game,self.state
        automatic=transport_capacity.automation(state,source.owner)
        policy=transport_capacity.ai_policy(state,source.owner,logistics._pool(state)['cities'][source.id]['policy'],
                                            automatic=automatic)
        if target is None or target['owner'] != source.owner or source.owner != self.owner:
            return None, 'invalid_recipient'
        demand = request(game,state,target)
        if demand is None or source.id==demand.city:
            return None, 'no_vacant_meeting'
        if selected and selected['target'] != demand.city:
            return None, 'invalid_recipient'
        plan = target['emergency']
        if plan['attempts']>=emergency.MAX_RELIEF_ATTEMPTS:
            return None, 'attempt_limit'
        if (plan['last_sent'] is not None and emergency.tick_now(state)-plan['last_sent']<emergency.REVIEW_DAYS):
            return None, 'same_request'
        reason = army_relief.source_blocker(game,state,source,policy,self.active)
        if reason:
            return None, reason
        timely = outstanding(game,state,target,demand,review=self.review)
        if timely or any(row['convoy_relief']['root']==demand.root for row in missions(state,self.owner)):
            # There is at most one in-flight commitment. A late mission is
            # cancelled by settlement; until then it never funds a move.
            return None, 'already_assigned' if timely else 'active_late'
        ids = logistics._eligible(game,state,source,capacity_checks=self.coordinated)
        teams=[selected['ids']] if selected is not None else [[i] for i in sorted(ids,key=lambda i:army_relief.escort_rank(state,i))]
        if not teams or logistics._present_count(game,state,source)-len(teams[0])<policy['reserve_officers']:
            return None, 'no_spare_officer'
        if selected is None:
            from .escort_planning import assigned_to_war
            locked = assigned_to_war(state,source)
            teams = [team for team in teams if team[0] not in locked]
            if not teams:
                return None, 'no_spare_officer'
        stock = emergency.stock(game,state,source)
        if budget and 'minimum_export_floor' in budget:
            stock = min(stock, max(0, source.grain - max(budget['minimum_export_floor'],
                budget['safety_reserve'],policy['reserve_grain'])-budget['reserved_grain']))
        routes = self.review.quotes(self.owner,source.id,policy).get(demand.city,())
        back = _return_quote(self.review,self.owner,source.id,demand.city,policy)
        if not routes or back is None:
            return None, 'no_safe_route'
        result = []
        blocked = 'insufficient_grain'
        physical=transport_capacity.enabled(state,'physical_capacity')
        for out in routes:
            if selected and selected['mode']!=out.mode:
                continue
            eta = emergency.tick_now(state)+out.days
            if eta>demand.wait_until or winter_travel.route_risk(game,state,back.route,out.days):
                blocked = 'outside_window'
                continue
            wait = army_relief.boundary(eta+army_relief.WAIT_DAYS)-eta
            demand_at_eta=demand.required+max(0, out.days*demand.meal_per_day-emergency.available(target))
            needed = _need_at_settlement(game,state,target,demand,eta)
            profile=transport_capacity.physical(game,state,out.route) if physical else None
            for team in teams:
                troops = sum(state.officers[i].troops for i in team)
                if budget and budget['threatened']:
                    from .difficulty import get_settings
                    if budget['active']-troops < min(budget['active'],get_settings(state)['min_guard_troops']):
                        blocked = 'defence'
                        continue
                if not logistics.escort_defence(game,state,source,team):
                    blocked='defence'
                    continue
                bag = army_relief.ration_budget(march_supply.ration_units(state,team),out.weight,
                    wait*emergency.wait_weight(game,state,demand.city),back.weight)
                capacity=max(0,min(policy['max_grain'],stock-bag.total))
                if physical:
                    loading=transport_capacity.loading(game,state,source.owner,policy,out.route,bag.total,
                        stock,logistics.LIMIT,automatic=automatic,profile=profile)
                    capacity=loading['max_cargo']
                parts = logistics.logistics_rules.plan(out.route,march_supply.travel_rules(game))
                risks = game._march_risks(out.route,None)
                if cargo is not None:
                    room = cargo if cargo<=capacity else 0
                    net = army_relief.net_cargo(game,out.route,room,parts=parts,risks=risks,state=state)
                elif capacity:
                    room,net = army_relief.shipment(game,out.route,demand_at_eta,capacity,parts,risks,state=state)
                else:
                    room,net = 0,0
                efficiency = army_relief.efficiency(net,room,bag.total)
                if not net or efficiency<army_relief.EFFICIENCY_MINIMUM and net*4<demand_at_eta:
                    continue
                if cargo is None and net<needed and room<capacity:
                    room,net = army_relief.shipment(game,out.route,needed,capacity,parts,risks,state=state)
                    efficiency = army_relief.efficiency(net,room,bag.total)
                facts = dict(target=demand.ident,root=demand.root,meeting=demand.city,
                    eta=eta,wait_until=min(eta+wait,demand.wait_until),needed=needed,
                    net=net,return_city=source.id,return_weight=back.weight,
                    outbound=bag.outbound,waiting=bag.wait,returning=bag.returning,safety=bag.safety)
                choice=dict(quote=out.route,mode=out.mode,officers=team,grain=room,rations=bag.total,relief=facts)
                if self.coordinated:
                    choice['return_quote']=back.route
                if physical:
                    choice['capacity']=loading
                priority=(eta, -min(net,needed), efficiency<army_relief.EFFICIENCY_PREFERRED,
                    efficiency<army_relief.EFFICIENCY_NORMAL, bag.total+room, troops,
                    tuple(logistics._key(i) for i in team),out.mode)
                if automatic and selected is None and transport_capacity.enabled(state,'throughput_ranking'):
                    priority=(eta,*transport_capacity.priority(min(net,needed),bag.total,out.days,back.days,
                        wait,len(team),logistics.RULES['receipt_turns'],bag.total+room),*priority[5:])
                result.append((priority,choice))
                # Team order prefers light escorts. When selecting manually
                # there is only one expressly chosen set of officers.
                break
        return (min(result,key=lambda item:item[0])[1],None) if result else (None,blocked)

    def dispatch_one(self, cities, budgets):
        game,state = self.game,self.state
        for target in sorted(self.targets.values(),key=lambda row:(row['emergency']['since'],row['id'])):
            demand = request(game,state,target)
            if demand is None:
                continue
            best = None
            rejection = set()
            for source in cities:
                policy = logistics._pool(state)['cities'][source.id]['policy']
                if not policy['enabled'] or historical_campaigns.hold_longyou_garrison(game,state,source):
                    continue
                choice, reason = self.quote(source,target,budget=budgets.get(source.id))
                if choice is None:
                    rejection.add(reason)
                    continue
                rank=(choice['relief']['eta'],-choice['relief']['net'],choice['rations'],source.id)
                if best is None or rank<best[0]:
                    best = (rank,source,choice)
            if best:
                _,source,choice = best
                logistics.dispatch(game,state,dict(source=source.id,target=demand.city,
                    target_convoy=target['id'],officers=choice['officers'],route_mode=choice['mode'],
                    cargo=dict(gold=0,grain=choice['grain'],reserves=0)),self.owner,
                    convoy_relief_quote=choice)
                return True
            emergency.note(game,state,'convoy_relief_request',target,root_relief_request_id=demand.root,
                expected_relief=0,gap=demand.required,decision='rejected',
                rejection_reason='|'.join(sorted(rejection)) if rejection else 'no_eligible_donor')
        return False

    def previews(self, source):
        rows=[]
        for target in self.targets.values():
            choice, _ = self.quote(source,target)
            if choice is not None:
                rows.append(choice)
        return rows


def register(game, state, sender, target):
    plan = target['emergency']
    plan['attempts'] += 1
    plan['last_sent'] = emergency.tick_now(state)
    plan['status'] = 'waiting_for_supply'
    quote = sender['convoy_relief']
    emergency.note(game,state,'convoy_relief_request',target, root_relief_request_id=quote['root'],
        gap=quote['needed'], decision='dispatched', source=sender['source'], sender=sender['id'],
        expected_relief=quote['net'], eta=quote['eta'], rejection_reason=None)


def target_row(state, row, *, indexed=None):
    ident = row['convoy_relief']['target']
    pool = logistics._pool(state)['convoys']
    match = indexed.get(ident) if indexed is not None else next((item for item in pool if item['id']==ident),None)
    if match and row['owner']==match['owner'] and match['target_march'] is None and 'convoy_relief' not in match:
        return match
    return None


def hold(state, row, tick):
    if row.get('return_leg')==len(row['journeys'])-1 or row.get('emergency'):
        return False
    supply = emergency.book(row)
    saved = row['convoy_relief']
    target = target_row(state,row)
    here = march_supply.current_city(target['journeys'][-1]) if target else None
    if (row['delivery_done'] or target is None or here!=saved['meeting']
            or state.cities[here].owner!=row['owner'] or (tick or supply['clock_tick'])>saved['wait_until']):
        supply['retreat_requested']=True
        supply['waiting']=True
        row['reason']='delivered' if row['delivery_done'] else 'rendezvous_expired'
        return True
    return logistics._arrived(row['journeys'][-1])


def settle(game,state,row):
    journey = row['journeys'][-1]
    if march_supply.current_city(journey) is None:
        return True
    row['checked_turn']=state.turn
    target=target_row(state,row)
    if hold(state,row,None) and (emergency.book(row)['retreat_requested'] or row['delivery_done']):
        emergency.note(game,state,'convoy_relief_request',row,root_relief_request_id=row['convoy_relief']['root'],
                       decision='cancelled',rejection_reason=row['reason'])
        logistics._return(game,state,row,'escort_return' if row['delivery_done'] else 'rendezvous_expired')
        return True
    if target is not None and request(game,state,target) is None:
        logistics._return(game,state,row,'army_supplied')
        return True
    return True


def rendezvous(game,state,tick):
    pool = logistics._pool(state)['convoys']
    if not any('convoy_relief' in row for row in pool):
        return
    indexed = {row['id']:row for row in pool}
    review=None
    for row in pool:
        if ('convoy_relief' not in row or row['delivery_done'] or row['status']=='returning'
                or emergency.book(row)['retreat_requested']):
            continue
        sender = emergency.book(row)
        room = row['convoy_relief']
        if sender['clock_tick']!=tick or tick>room['wait_until'] or not row['cargo']['grain']:
            continue
        here = march_supply.current_city(row['journeys'][-1])
        if here!=room['meeting'] or state.cities[here].owner!=row['owner']:
            continue
        recipient = target_row(state,row,indexed=indexed)
        if (recipient is None or emergency.book(recipient)['clock_tick']!=tick
                or march_supply.current_city(recipient['journeys'][-1])!=here):
            continue
        demand = request(game,state,recipient)
        if demand is None:
            continue
        review=review or emergency.Review(game,state)
        back=_return_quote(review,row['owner'],row['source'],here,row['route_policy'])
        if back is None:
            row['reason']='unsafe_return'
            sender['retreat_requested']=True
            continue
        protected=army_relief.ration_budget(emergency.convoy_units(state,row),0,
            (army_relief.boundary(tick)-tick)*emergency.wait_weight(game,state,here),back.weight,
            credit=sender['credit_units']).total
        current=emergency.book(recipient)
        amount=min(_need_at_settlement(game,state,recipient,demand,tick), logistics.LIMIT-current['remaining'],
                   row['cargo']['grain']-max(0,protected-sender['remaining']))
        if transport_capacity.enabled(state,'physical_capacity'):
            amount=min(amount,transport_capacity.refill_room(game,state,recipient,here))
        if amount<=0:
            continue
        march_supply.receive(current,amount,'convoy',row['id'],state.turn)
        logistics._cargo_change(row,'convoy_supply',dict(row['cargo'],grain=row['cargo']['grain']-amount),
                                tick,dict(convoy=recipient['id'],city=here))
        row['delivered']['grain'] += amount
        row.update(delivery_done=True,status='waiting',reason='delivered')
        sender['waiting']=True
        game._supply_event(state,'march_resupplied',unit_kind='convoy',unit_id=recipient['id'],
                           city=here,owner=row['owner'],grain=amount,reason='convoy')
        logistics._event(game,state,'transport_arrived',row,reason='delivered',
                         amounts=dict(gold=0,grain=amount,reserves=0),receipt_tick=tick)
        emergency.note(game,state,'convoy_relief_delivery',recipient,at=here,root_relief_request_id=room['root'],
                       sender=row['id'],actual_relief=amount,protected_return=protected,decision='handed_off')


def validate(state,row,pool):
    relief=row['convoy_relief']
    numeric={'target','eta','wait_until','needed','net','return_weight','outbound','waiting','returning','safety'}
    if (emergency.stage(state)<emergency.EXTERNAL_RELIEF or not isinstance(relief,dict)
            or set(relief)!=numeric|{'root','meeting','return_city'}
            or not all(type(relief[k]) is int and 0<=relief[k]<=100*logistics.LIMIT for k in numeric)
            or not 0<relief['target']<row['id']<pool['next_id'] or relief['root']!=f"convoy:{relief['target']}"
            or relief['meeting']!=row['original_target'] or relief['return_city']!=row['source']
            or not row['initial_cargo']['grain'] or relief['net']>row['initial_cargo']['grain']
            or any(row['initial_cargo'][key] for key in ('gold','reserves','treasure'))
            or relief['eta']>relief['wait_until'] or not relief['net'] or not relief['needed']
            or row['target_march'] is not None or 'relief' in row):
        raise ValueError('Convoy relief mission')
    raw_target=next((item for item in pool['convoys'] if item['id']==relief['target']),None)
    active=not row['delivery_done'] and not emergency.book(row)['retreat_requested'] and row['status']!='returning'
    if active and raw_target is not None and (
            target_row(state,row) is None or not raw_target.get('emergency',{}).get('attempts',0)):
        raise ValueError('Convoy relief commitment missing from its target')
    if active and sum(item.get('convoy_relief',{}).get('root')==relief['root']
                      for item in missions(state,row['owner']))>1:
        raise ValueError('Duplicate in-flight convoy relief')
