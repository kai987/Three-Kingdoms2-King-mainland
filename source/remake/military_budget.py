"""Read-only city and sortie budgets for AI using the versioned logistics rules."""
from collections import defaultdict

from . import city_economy, grain_units, logistics_rules, payroll
from . import historical_campaigns, march_supply

REAR_MONTHS = 3
FRONT_MONTHS = 6
GRANARY_MONTHS = 12
REPLACEMENT_PERCENT = 20
CONTINGENCY_PERCENT = 10
LOW_PRICE_MONTHS = (10, 11)


def enabled(state):
    return logistics_rules.version(state) == logistics_rules.CURRENT


def active_garrison(state, city, absent):
    return sum(state.officers[ident].troops for ident in city.roster.officer_ids
               if ident not in absent and state.officers[ident].alive
               and state.officers[ident].faction_id == city.owner)


def garrison(game, state, city, active, reserves):
    return city_economy.garrison_grain_cost(game.catalog.data,city.id,state.year,state.month,active,reserves)


def fixed_expenses(game,state,city,active):
    development=state.extension.get('city_development',{}).get('cities',{}).get(city.id,{})
    town=city_economy.town_level(game,state,city.id)
    civilian=city_economy.civilian_grain(development.get('population',0),town,state=state)
    wages=payroll.monthly_due(state,city)
    return dict(active=active,residents=civilian,wage_grain=wages['grain'],wage_gold=wages['gold'],
                garrison=garrison(game,state,city,active,city.reserves))


def budgets(game,state,owner,*,stationed=None,incomes=None):
    """Only one absent-person, front and shipment scan for this faction quote."""
    from . import domestic, facilities, grain_market, logistics

    if not enabled(state) or owner=='neutral':
        return {}
    cities={city.id:city for city in state.cities.values() if city.owner==owner}
    if not cities:
        return {}
    absent=city_economy.absent_troops(game,state)
    stationed=city_economy.stationed_troops(game,state,absent) if stationed is None else stationed
    front={city.id for city in logistics._fronts(game,state,owner)}
    data=game.catalog.data
    granaries=set(data.get('logistics_granary_cities',()))
    in_transit=defaultdict(int)
    within_three_months=defaultdict(int)
    committed_convoys=defaultdict(int)
    committed_marches=defaultdict(int)
    for row in state.extension.get('logistics',{}).get('convoys',()):
        if row['owner']!=owner:
            continue
        journey=row['journeys'][-1]
        committed_convoys[row['source']]+=row['cargo']['grain']+journey['supply']['remaining']
        if row['status']=='outbound' and row['target_march'] is None and not row['delivery_done']:
            arrival=journey['arrival_turn']-state.turn
            projected=logistics.inbound_grain(game,row)
            in_transit[row['target']]+=projected
            if 0<=arrival<=9:
                within_three_months[row['target']]+=projected
    for row in state.extension['travel']['marches']:
        if row['owner']==owner:
            committed_marches[row['source']]+=row['supply']['remaining']
    threat={row['target'] for row in state.extension['travel']['marches'] if row['kind']=='attack'
            and row['target'] in cities and row['owner']!=owner
            and not historical_campaigns.allied(state,owner,row['owner'])}
    result={}
    for key,city in cities.items():
        income=incomes[key] if incomes is not None else city_economy.monthly_income(game,key,state)
        bonus=domestic.earned_grain(state,key,income)
        bill=fixed_expenses(game,state,city,stationed.get(key,0))
        fixed=bill['residents']+bill['wage_grain']+bill['garrison']
        net=income['grain']+bonus-fixed
        frontier=city_economy.frontier_outpost_at(data,key,state.year,state.month)
        months=GRANARY_MONTHS if key in granaries else FRONT_MONTHS if key in front or frontier else REAR_MONTHS
        stock_target=fixed*months
        market=grain_market.row(state,key)
        has_buyer=any(ident not in absent and state.officers[ident].alive and state.officers[ident].health>0
                      and state.officers[ident].faction_id==owner
                      and state.extension.get('civil_staff',{}).get('people',{}).get(ident,{}).get('working',True)
                      for ident in city.roster.officer_ids)
        extra=garrison(game,state,city,bill['active'],city.reserves+100)-bill['garrison']
        result[key]=dict(bill,stock=city.grain,regular=income['grain'],earned=bonus,
            fixed=fixed,net=net,months=months,target=stock_target,deficit=max(0,stock_target-city.grain-in_transit[key]),
            stock_months=round(city.grain/fixed,2) if fixed else None,
            depletion_months=round(city.grain/-net,2) if net<0 else None,
            convoy_grain=committed_convoys[key],march_grain=committed_marches[key],
            inbound=in_transit[key],timely=within_three_months[key],
            market_stock=market['stock'] if market else 0,
            market_affordable=facilities.emergency_quote(game,state,city,fixed)['grain']
                if market and fixed and has_buyer and facilities._ready(state,owner) else 0,
            additional_reserve_rations_100=extra,
            threatened=key in threat,
            next_installment=city_economy.turn_rations(fixed,(state.day-1)//10+1))
    return result


def recruitment(game,state,city,requested,budget):
    """Cap the delegated order without reserving or debiting any forecast income."""
    if not requested or not budget:
        return requested
    emergency=budget['threatened']
    active=budget['active']
    old_garrison=garrison(game,state,city,active,city.reserves)
    fixed=budget['wage_grain']+budget['residents']+old_garrison
    months=1 if emergency else REAR_MONTHS
    installment=(state.day-1)//10+1
    projected=city.grain+months*budget['regular']+budget['earned']+(0 if emergency else budget['timely'])
    floor=fixed if emergency else min(budget['target'],REAR_MONTHS*fixed)
    cost_per_hundred=grain_units.amount(30)
    low,high=0,requested
    while low<high:
        count=(low+high+1)//2
        immediate=logistics_rules.ceil_div(count*cost_per_hundred,100)
        reserve=garrison(game,state,city,active,city.reserves+count)
        future_active=garrison(game,state,city,active+count,city.reserves)
        next_installment=city_economy.turn_rations(fixed+reserve-old_garrison,installment)
        fixed_future=fixed+max(reserve,future_active)-old_garrison
        if city.grain>=immediate+next_installment and projected>=immediate+months*fixed_future+floor:
            low=count
        else:
            high=count-1
    return low


def sortie(game,state,city,target,ids,quote,back,*,absent=None):
    """One consistent outbound, home defence and replacement calculation."""
    from . import battle_supply

    soldiers=sum(state.officers[ident].troops for ident in ids)
    travel=march_supply.quote_supply(quote,soldiers,len(ids),game=game,version=logistics_rules.CURRENT)
    battle=battle_supply.BUDGET_DAYS
    battle_stock=march_supply.cost(soldiers,len(ids),battle)
    back_stock=(march_supply.quote_supply(back,soldiers,len(ids),game=game,version=logistics_rules.CURRENT)
                if back is not None else None)
    absent=city_economy.absent_troops(game,state) if absent is None else absent
    left=max(0,active_garrison(state,city,absent)-soldiers)
    bill=fixed_expenses(game,state,city,left)
    home=bill['residents']+bill['wage_grain']+bill['garrison']
    expected_days=1 if target.owner=='neutral' else min(8,3+soldiers//3000)
    expected_battle=march_supply.cost(soldiers,len(ids),expected_days)
    safety=logistics_rules.ceil_div((travel+(back_stock or 0)+expected_battle)*CONTINGENCY_PERCENT,100)
    losses=logistics_rules.ceil_div(soldiers*REPLACEMENT_PERCENT,100)
    replacement=losses*3
    replacement_gold=logistics_rules.ceil_div(losses,5)
    # The real carry reserves 30 battle days. Replacement is a planning
    # reserve and may be supported by future city income or other friendly cities.
    immediate=travel+battle_stock+(back_stock or 0)+safety
    total=immediate+home+replacement
    city_income=city_economy.monthly_income(game,city.id,state)
    immediate_home=city_economy.turn_rations(home,(state.day-1)//10+1)
    safe_return=back is not None or target.owner=='neutral'
    required_grain=max(immediate+immediate_home,total-city_income['grain'])
    required_gold=max(0,bill['wage_gold']+replacement_gold-city_income['gold'])
    can_depart=safe_return and city.grain>=required_grain and city.gold>=required_gold
    return dict(outbound=travel,battle=battle_stock,expected_battle=expected_battle,returning=back_stock,
                home=home,replacement_grain=replacement,replacement_gold=replacement_gold,
                safety=safety,total=total,immediate=immediate,required_grain=required_grain,
                required_gold=required_gold,safe_return=safe_return,can_depart=can_depart)


def buy_reserves(game,state,owner):
    """Buy at most a month's fixed expenses per eligible city and actual stock."""
    from . import command_books, facilities
    from .officers import ref_sort_key

    if owner==state.player or not enabled(state) or not facilities._ready(state,owner):
        return 0
    if not command_books.can_spend(state,owner,'trade_grain'):
        return 0
    outlook=budgets(game,state,owner)
    priority=sorted(outlook,key=lambda key:(outlook[key]['net']>=0,
        -outlook[key]['deficit'],key))
    purchased=0
    for key in priority:
        if not command_books.can_spend(state,owner,'trade_grain'):
            break
        city,plan=state.cities[key],outlook[key]
        if not plan['deficit'] or not plan['market_stock'] or state.month not in LOW_PRICE_MONTHS and plan['net']>=0:
            continue
        if plan['stock']<plan['next_installment']:
            continue  # The existing emergency path has priority.
        town=city_economy.town_level(game,state,key)
        quote=facilities._trade_quote(game,state,city,town,'buy')
        reserved_gold=plan['wage_gold']+facilities._pool(state)['factions'][owner]['gold_floor']
        ceiling=min(plan['fixed'],plan['deficit'])
        batches=min(quote['max_batches'],ceiling//quote['batch_grain'],
                    max(0,city.gold-reserved_gold)//quote['rate'])
        if batches<=0:
            continue
        actors=[ident for ident in city.roster.officer_ids if
                facilities._resident(game,state,city,ident,working=True,healthy=True)]
        if not actors:
            continue
        actor=min(actors,key=lambda ident:(-state.officers[ident].profile.intellect,ref_sort_key(ident)))
        facilities.trade(game,state,dict(city=key,actor=actor,direction='buy',batches=batches),owner)
        purchased+=batches*quote['batch_grain']
    return purchased
