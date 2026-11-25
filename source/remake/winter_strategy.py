"""Reserve grain only for a scheduled cold-season operation."""
from . import logistics_rules as rules, march_supply, winter_travel, winter_weather
from .climate_regions import REGIONS


def planned_reserves(game,state,owner):
    if winter_weather.stage(state)<5 or state.month not in (9,10,11,12,1,2,3):
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
