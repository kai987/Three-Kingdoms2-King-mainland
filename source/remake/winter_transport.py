"""Published forecasts used at real transport decision boundaries."""
from . import logistics_rules as rules, march_supply, winter_travel, winter_weather

SAFETY_PERCENT = 110
WAIT_REVIEW_DAYS = 10


def enabled(state):
    return winter_weather.corrected(state,winter_weather.TRANSPORT)


def protected_cost(game,state,quote,units,*,position=0,stop=None,credit=0):
    days,weight,ice=winter_travel.checkpoint_forecast(game,state,quote,position=position,stop=stop)
    if ice is not None:
        region=game.catalog.climate.cities[quote['path'][-1]]['climate_region_id']
        weight+=WAIT_REVIEW_DAYS*winter_travel.wait_rate(state,region)
    divisor=march_supply.denominator()*rules.RATION_SCALE
    amount=rules.ceil_div(max(0,units*weight-credit),divisor)
    return dict(days=days,blocked=ice,meal=amount,safety=rules.ceil_div(amount*(SAFETY_PERCENT-100),100))


def seasonal_meals(state, ids, outward, returning, *, reserves=0):
    """One provision quote per direction and one shared safety allowance."""
    divisor=march_supply.denominator()*rules.RATION_SCALE
    escort=march_supply.ration_units(state,ids)
    out=rules.ceil_div((escort+reserves)*outward['total_ration_weight'],divisor)
    back=rules.ceil_div(escort*returning['total_ration_weight'],divisor)
    return out,back,rules.ceil_div((out+back)*SAFETY_PERCENT,100)


def budget(game,state,row,*,return_quote=None):
    journey=row['journeys'][-1]
    book=journey['supply']
    position=winter_travel.work(book)
    units=march_supply.ration_units(state,row['officers'],row['cargo']['reserves'])
    result=protected_cost(game,state,journey['quote'],units,position=position,credit=book['credit_units'])
    returning=0
    if return_quote is not None and row.get('return_leg')!=len(row['journeys'])-1:
        estimate=protected_cost(game,state,return_quote,march_supply.ration_units(state,row['officers']))
        returning=estimate['meal']+estimate['safety']
    required=result['meal']+result['safety']+returning
    result.update(available=book['remaining'],cargo=row['cargo']['grain'],required=required,
                  returning=returning,shortfall=max(0,required-book['remaining']))
    return result


def city_stock(game,state,city,stock):
    """Only present stock above bookings and the next local ration installment."""
    if not stock:
        return 0
    from . import city_economy, military_budget
    absent=city_economy.absent_troops(game,state)
    active=military_budget.active_garrison(state,city,absent)
    bill=military_budget.fixed_expenses(game,state,city,active)
    installment=(state.day-1)//10+1
    reserve=city_economy.turn_rations(bill['residents']+bill['garrison'],installment)
    if installment==3:
        reserve+=bill['wage_grain']
    return max(0,stock-reserve)


def view(game,state,row):
    journey=row['journeys'][-1]
    book=journey['supply']
    details=budget(game,state,row)
    here=march_supply.current_city(journey)
    tick=book['clock_tick']
    travel_days=sum(item['supply']['elapsed_days'] for item in row['journeys'])
    date=lambda value:winter_weather.date_at(game.catalog.data,value)
    eta=details['days']
    holding=book['waiting'] or book['retreat_requested']
    return dict(details,here=here,remaining_work=journey['quote']['days']*winter_travel.QUANTA-winter_travel.work(book),
                elapsed=travel_days,phase=row['status'],reason=row['reason'],
                original=date((row['original_eta']-1)*10+1) if 'original_eta' in row else None,
                expected=date(tick+eta) if eta is not None and not holding else None,
                forecast_only=True)


def trace_begin(row):
    book=row['journeys'][-1]['supply']
    return (winter_travel.work(book),book['clock_tick'],book['remaining'],book.get('base_consumed',0),
            book['received'],book['lost'],row['cargo']['grain'],len(row['cargo_ledger']))


def trace_day(game,state,row,before):
    start,prior,bag,base,received,lost,cargo,ledger=before
    journey=row['journeys'][-1]
    book=journey['supply']
    now=book['clock_tick']
    if now==prior:
        return
    work=winter_travel.work(book)
    total=journey['quote']['days']*winter_travel.QUANTA
    node=march_supply.current_city(journey)
    meal=book['periods'][-1]['days'][-1]
    ice=book.get('winter',{}).get('blocked')
    frost=state.extension.get(winter_weather.POOL,{}).get('ice',{}).get(ice,{})
    if work>start:
        reason=None
    elif ice:
        reason='ice'
    elif row['reason'] not in ('outbound','escort_return'):
        reason=row['reason']
    elif work>=total:
        reason='arrival_pending'
    else:
        reason='waiting_for_supply'
    charges={}
    for transaction in row['cargo_ledger'][ledger:]:
        key=transaction['kind']
        charges[key]=charges.get(key,0)+transaction['before']['grain']-transaction['after']['grain']
    starvation=book['starvation'][-1] if book['starvation'] and book['starvation'][-1]['tick']==now else None
    reserves_lost=starvation['reserves_before']-starvation['reserves_after'] if starvation else 0
    winter_weather.report('convoy_strength',convoy_id=row['id'],tick=now,
        current_escort=sum(state.officers[ident].troops for ident in row['officers']),
        current_reserves=row['cargo']['reserves'],current_officers=sum(type(i) is int for i in row['officers']),
        current_civil_staff=sum(type(i) is str for i in row['officers']),
        escort_hunger_loss=book['lost']-lost-reserves_lost,reserve_hunger_loss=reserves_lost,
        delivery_done=row['delivery_done'])
    winter_weather.report('convoy_day',tick=now,date=winter_weather.date_at(game.catalog.data,now),
        convoy=row['id'],owner=row['owner'],phase=row['status'],journey=len(row['journeys'])-1,
        origin=row['source'],source=journey['source'],target=journey['target'],
        node=node,last_node=march_supply.last_city(journey),next_node=march_supply.next_city(journey),
        start_work=total-start,moved=work-start,end_work=total-work,
        rations_before=bag,paid=meal[1] if meal else 0,base=book.get('base_consumed',0)-base,
        supply=book['received']-received,missing=meal[3] if meal else 0,
        rations_after=book['remaining'],cargo_before=cargo,route_loss=charges.get('route_loss',0),
        incident_loss=charges.get('weather',0),cargo_to_bag=charges.get('rations',0),
        cargo_after=row['cargo']['grain'],hunger_loss=book['lost']-lost,
        person_days=meal[0] if meal else 0,reason=reason,original_eta=row.get('original_eta'),
        eta=None if ice or reason not in (None,'arrival_pending') else journey['arrival_turn'],
        ice=ice,ice_index=frost.get('index'),ice_state=frost.get('state'),
        safe_exit=node if node is not None and state.cities[node].owner==row['owner'] else None)
