"""Reserve grain only for a scheduled cold-season operation."""
from collections import defaultdict

from . import logistics_rules as rules, march_supply, winter_travel, winter_weather
from .climate_regions import REGIONS


def planned_reserves(game,state,owner,*,seasonal=False):
    if winter_weather.stage(state)<5 or state.month not in (9,10,11,12,1,2,3):
        return {}
    if not seasonal and winter_weather.corrected(state,winter_weather.PREPARATION):
        return {}
    result={}
    for order in state.extension['ai_strategy'].get(owner,{}).get('orders',()):
        source,target=order['source'],order['target']
        if order['march_id'] is not None or source not in state.cities or target not in state.cities:
            continue
        if state.cities[source].owner!=owner or not order['officers']:
            continue
        days=max(0,(order['departure_turn']-state.turn)*10)
        departure=(state.month-1+(state.day-1+days)//30)%12+1
        quote=game._travel_path(state,source,target,owner,order['mode'],adjacent=True)
        if not quote:
            continue
        normal=march_supply.route_weight(quote,quote['days'],game=game,version=rules.CURRENT)
        current=winter_travel.ration_weight(game,state,quote)
        # This uses monthly eligibility and published conditions, never the
        # future event draw. Reserve the expected premium of light snow.
        allowance=sum(part.work*REGIONS[part.region][1] for part in winter_travel.plan(game,quote)
                      if departure in REGIONS[part.region][0] and part.mode in ('plain','mountain','desert'))
        margin=max(0,current-normal,allowance*15*rules.RATION_SCALE//(winter_travel.QUANTA*10_000))
        people=march_supply.ration_units(state,order['officers'])
        extra=rules.ceil_div(people*margin,march_supply.denominator()*rules.RATION_SCALE)
        if extra:
            result[source]=(target,extra)
    return result


def prepare(ai,owner):
    game,state=ai.game,ai.state
    if owner in ai.winter_checked:
        return
    ai.winter_checked.add(owner)
    if winter_weather.stage(state)<5:
        return
    if winter_weather.corrected(state,winter_weather.PREPARATION):
        prepare_seasonally(ai,owner)
        return
    requested=planned_reserves(game,state,owner)
    if not requested:
        return
    from . import command_books, escort_planning, facilities, logistics
    plans=ai.economy_plan(owner)
    for key,(target,extra) in sorted(requested.items()):
        city=state.cities[key]
        budget=plans.budgets[key]
        available=city.grain+budget['timely_grain']
        base=budget['safety_reserve']+budget['reserved_grain']
        shortage=min(extra,base+extra-available)
        if available<base or shortage<=0:
            continue  # Urgent city and ordinary military needs use their original pipeline.
        protected=escort_planning.assigned_to_war(state,city)
        if state.month in (10,11) and facilities._ready(state,owner) and command_books.can_spend(state,owner,'trade_grain'):
            worker=next((i for i in ai.available(city) if i not in protected and
                facilities._resident(game,state,city,i,working=True,unused=True,healthy=True)),None)
            offer=facilities.emergency_quote(game,state,city,shortage)
            if worker is not None and offer['grain'] and city.gold-offer['gold']>=budget['wage_gold']:
                receipt=facilities.buy_emergency_grain(game,state,key,worker,owner,shortage)
                winter_weather.action(game,state,'winter_purchase',key,owner=owner,target=target,
                                      grain=receipt['grain'],extra=extra)
                break
        if logistics.dispatch_ai_supply(game,state,city,0,base+extra,require_return=True,
                protected_officers=protected,max_turns=3,economy_plan=plans):
            winter_weather.action(game,state,'winter_stock_transport',key,owner=owner,target=target,
                                  grain_needed=shortage,extra=extra)
            break
    else:
        return
    ai.economy_plans.pop(owner,None)
    ai.grain_outlooks.pop(owner,None)


def seasonal_requirements(game,state,owner,plans):
    """Apply published route risk to the same city timeline used by ordinary relief."""
    from . import faction_economy, logistics
    if state.month not in (9,10,11,12,1,2,3):
        return {}
    ordinary=defaultdict(lambda: defaultdict(int))
    winter=defaultdict(lambda: defaultdict(int))
    remove=defaultdict(lambda: defaultdict(int))
    extra=defaultdict(lambda: defaultdict(int))
    risk=defaultdict(set)
    exposed=set()
    for city,(_,amount) in planned_reserves(game,state,owner,seasonal=True).items():
        if city in plans.cities:
            extra[city][1]+=amount
            exposed.add(city)
    for row in state.extension['logistics']['convoys']:
        target=row['target']
        if (row['owner']!=owner or target not in plans.cities or row['status']!='outbound'
                or row['delivery_done'] or row['target_march'] is not None or not row['cargo']['grain']):
            continue
        journey=row['journeys'][-1]
        supply=journey['supply']
        quote=journey['quote']
        position=winter_travel.work(supply)
        outlook=winter_travel.seasonal_forecast(game,state,quote,position=position)
        days,_,ice=winter_travel.checkpoint_forecast(game,state,quote,position=position)
        normal=max(0,quote['days']-supply['route_days'])
        if not (outlook['extra_days'] or outlook['reaches'] or ice or days!=normal):
            continue
        exposed.add(target)
        risk[target].update(outlook['reaches'])
        if ice is not None:
            risk[target].add(ice)
        expected=logistics.inbound_grain(game,row,state)
        remove[target][max(1,journey['arrival_turn']-state.turn)]+=expected
        normal_net=logistics.projected_grain(game,quote,row['cargo']['grain'],progress=supply['route_days'],
                                             remainder=row[logistics.LOSS_FIELD])
        ordinary[target][max(1,rules.ceil_div(normal,10))]+=normal_net
        if days is not None and not outlook['reaches']:
            delay=outlook['extra_days']
            reduced=expected-min(expected,rules.ceil_div(expected*delay,100))
            winter[target][max(1,rules.ceil_div(max(days,normal+delay),10))]+=reduced

    for march in state.extension['travel']['marches']:
        here=march['source']
        if (march['owner']!=owner or here not in plans.cities or march['status']=='returning'
                or march['supply']['retreat_requested']):
            continue
        book=march['supply']; quote=march['quote']
        progress=book['route_days']; position=winter_travel.work(book)
        outlook=winter_travel.seasonal_forecast(game,state,quote,position=position)
        if not outlook['extra_weight']:
            continue
        # Extra provision is associated with the next existing owned supply node.
        offset=0
        for index,leg in enumerate(quote['routes']):
            offset+=leg['days']
            node=quote['path'][index+1]
            if offset>progress and node in plans.cities:
                break
        else:
            continue
        expected,weight,_=winter_travel.checkpoint_forecast(game,state,quote,position=position,
                                                          stop=offset*winter_travel.QUANTA)
        if expected is None:
            continue
        normal=march_supply.route_weight(quote,offset-progress,offset=progress,game=game,version=rules.CURRENT)
        people=march_supply.ration_units(state,march['officers'])
        divisor=march_supply.book_denominator(book)
        amount=rules.ceil_div(people*max(0,weight-normal,outlook['extra_weight']),divisor)
        ordinary_need=rules.ceil_div(people*normal,divisor)
        uncovered=max(0,amount-max(0,book['remaining']-ordinary_need))
        if uncovered:
            extra[node][max(1,rules.ceil_div(expected,10))]+=uncovered
            exposed.add(node)

    result={}
    for key in sorted(exposed):
        city=state.cities[key]; row=plans.budgets[key]; forecast=plans.cities[key]
        stock=max(0,city.grain-row['reserved_grain'])
        normal_terms=[]; winter_terms=[]
        for turn,(harvest,charge,receipt) in enumerate(forecast.timeline,1):
            shared=max(0,receipt-remove[key][turn])
            normal_terms.append((harvest,charge,shared+ordinary[key][turn]))
            winter_terms.append((harvest,charge+extra[key][turn],shared+winter[key][turn]))
        normal_gaps,normal_stock,_=faction_economy.balance(stock,normal_terms)
        winter_gaps,winter_stock,_=faction_economy.balance(stock,winter_terms)
        floor=row['minimum_reserve'] if row['front'] else row['next_installment']
        def deficit(gaps,balances):
            return max([amount for _,amount in gaps]+[floor-amount for amount in balances]+[0])
        baseline=deficit(normal_gaps,normal_stock)
        projected=deficit(winter_gaps,winter_stock)
        crossings=[i for (i,n),(_,w),normal,winter_stock in
                   zip(normal_gaps,winter_gaps,normal_stock,winter_stock)
                   if w>n or winter_stock<min(floor,normal)]
        result[key]=dict(baseline=baseline,winter=projected,extra=max(0,projected-baseline),
                         deadline=min(crossings,default=len(winter_terms)),reaches=tuple(sorted(risk[key])),
                         covered=stock,committed=row['reserved_grain'],
                         projected_delivery=sum(winter[key].values()))
    return result


def prepare_seasonally(ai,owner):
    from . import command_books, escort_planning, facilities, logistics
    game,state=ai.game,ai.state
    if state.month not in (9,10,11,12,1,2,3):
        return
    plans=ai.economy_plan(owner)
    proposals=seasonal_requirements(game,state,owner,plans)
    for key,estimate in sorted(proposals.items(),key=lambda item:(item[1]['deadline'],-item[1]['extra'],item[0])):
        winter_weather.action(game,state,'winter_preparation_evaluation',key,owner=owner,**estimate)
        if not estimate['extra']:
            winter_weather.action(game,state,'winter_preparation_rejection',key,owner=owner,reason='covered')
            continue
        city=state.cities[key]; budget=plans.budgets[key]
        protected=escort_planning.assigned_to_war(state,city)
        worker=None
        offer=facilities.emergency_quote(game,state,city,estimate['extra'])
        can_buy=facilities._ready(state,owner) and command_books.can_spend(state,owner,'trade_grain')
        if can_buy:
            worker=next((i for i in ai.available(city) if i not in protected and
                         facilities._resident(game,state,city,i,working=True,unused=True,healthy=True)),None)
        if worker is not None and offer['grain'] and city.gold-offer['gold']>=budget['wage_gold']:
            receipt=facilities.buy_emergency_grain(game,state,key,worker,owner,estimate['extra'])
            winter_weather.action(game,state,'winter_purchase',key,owner=owner,grain=receipt['grain'],**estimate)
            break
        pending=logistics._inbound(state,key)['grain']
        if logistics.dispatch_ai_supply(game,state,city,0,city.grain+pending+estimate['extra'],
                    protected_officers=protected,max_turns=estimate['deadline'],require_return=True,
                    economy_plan=plans,seasonal=True):
            winter_weather.action(game,state,'winter_stock_transport',key,owner=owner,
                                  convoy=logistics._pool(state)['next_id']-1,**estimate)
            break
        reason=('command_or_market_unavailable' if not can_buy else 'no_buyer' if worker is None else
                'market_stock_or_gold' if not offer['grain'] or city.gold-offer['gold']<budget['wage_gold']
                else 'no_viable_transfer')
        winter_weather.action(game,state,'winter_preparation_rejection',key,owner=owner,reason=reason,**estimate)
    else:
        return
    ai.economy_plans.pop(owner,None)
    ai.grain_outlooks.pop(owner,None)
