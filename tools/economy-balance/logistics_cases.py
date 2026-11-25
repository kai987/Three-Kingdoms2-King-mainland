"""Export engine-based scenarios and explicitly marked arithmetic cases."""
from argparse import ArgumentParser
from copy import deepcopy
from itertools import product
from pathlib import Path

from common import catalogs, open_game, to_csv, to_json
from remake import grain_units, logistics, logistics_rules as rules, march_preview, march_supply
from remake import military_budget as budget, route_hazards
from remake.officers import OFFICER_TROOP_CAP

LOADS=(1,100,10_000,50_000,100_000,200_000)
DURATIONS=(10,30,60,90)
MODES=tuple(rules.MARCH_SUPPLY_PERCENT)


def _same_owner_examples(game):
    state = game.state
    examples = {}
    for raw in game._known_routes(state):
        mode = raw['mode']
        if mode in examples:
            continue
        for source, target in ((raw['from'],raw['to']), (raw['to'],raw['from'])):
            if source not in state.cities or target not in state.cities:
                continue
            home, destination = state.cities[source], state.cities[target]
            if home.owner == 'neutral' or destination.owner != home.owner or not logistics._eligible(game,state,home):
                continue
            if not route_hazards.route_allowed(game.catalog.data, raw, source, target):
                continue
            leg = route_hazards.evaluate_leg(game.catalog.data,raw,source,target,state.month)
            if mode=='land' and leg['hazard']:
                continue
            examples[mode] = (source, target, raw)
            break
    return examples


def _configure(game, state, source, target, amount):
    home = state.cities[source]
    target_city = state.cities[target]
    policy = state.extension['logistics']['cities'][source]['policy']
    policy.update(max_grain=max(amount, policy['max_grain']), reserve_grain=0, reserve_gold=0,
                  reserve_reserves=0, reserve_officers=0, allow_sea=True)
    logistics._validate_policy(game,state,policy)
    home.grain = amount+500_000
    target_city.grain = 500_000
    actor = logistics._eligible(game,state,home)[0]
    state.soldiers['initial'] += 1000-state.officers[actor].troops
    state.officers[actor].troops = 1000
    return home, target_city, actor, policy


def _contract(game, state, source, target, raw, *, amount=50_000):
    """One real order, real route search, out-and-back arrival and stock checks."""
    home, destination, actor, policy = _configure(game,state,source,target,amount)
    initial_grain = sum(c.grain for c in state.cities.values())
    expected = logistics._safe_path(game,state,source,target,home.owner,raw['mode'],policy)
    if not expected or raw['mode'] not in expected['modes']:
        raise ValueError(f'No {raw["mode"]} transport fixture {source}/{target}')
    convoy = logistics.dispatch(game,state,dict(source=source,target=target,officers=[actor],
                             cargo=dict(gold=0,grain=amount,reserves=0),route_mode=raw['mode']),home.owner)
    journey = convoy['journeys'][0]
    assert journey['quote'] == expected
    assert journey['supply']['loaded'] == march_supply.estimate(state,[actor],expected,game=game)
    logistics.validate(game,state)
    # Isolate the convoy services from ordinary city production or salary.
    # Day-of-month advances as usual so any return route uses its real month.
    for _ in range(200):
        if convoy not in state.extension['logistics']['convoys']:
            break
        state.turn += 1
        state.day += 10
        if state.day > 30:
            state.day = 1
            state.month += 1
            if state.month > 12:
                state.month = 1
                state.year += 1
        logistics.process_arrivals(game,state)
    assert convoy not in state.extension['logistics']['convoys'] and convoy['delivery_done']
    expected_first = march_supply.quote_supply(expected,1000,1,game=game,version=rules.CURRENT)
    outbound_paid = journey['supply']['consumed']
    assert outbound_paid <= expected_first
    if len(expected['routes'])==1 and not journey['supply']['starvation']:
        assert outbound_paid == expected_first
    receipt=logistics.grain_receipt(convoy,returned=True)
    assert logistics.valid_grain_receipt(receipt),receipt
    meals=sum(j['supply']['consumed'] for j in convoy['journeys'])
    loss=receipt['cargo_route_loss']+receipt['cargo_weather_loss']
    assert initial_grain - sum(c.grain for c in state.cities.values()) == loss+meals
    return dict(case='engine_dispatch_and_return',from_city=source,to_city=target,requested_mode=raw['mode'],
                route_ids=[l['id'] for l in expected['routes']],departure_month=journey['departure_month'],
                outbound_days=expected['days'],return_days=sum(j['quote']['days'] for j in convoy['journeys'][1:]),
                outbound_grain=outbound_paid,return_grain=meals-outbound_paid,**receipt,grain_conserved=True)


def rations():
    for mode,days,strength,officers,reserves in product(MODES, (1,7,10,20,22,30),
                    (0,1000,10_000,50_000,100_000), (1,5,10), (0,1000)):
        ticks=days*rules.DAY_TICKS
        units=strength+100*officers+reserves
        basic=march_supply.cost(strength,officers,days,reserves)
        total=rules.ceil_div(rules.charge(units,[(mode,ticks)],0,days),50*rules.RATION_SCALE)
        assert total>=basic
        yield dict(case='arithmetic',route_mode=mode,troops=strength,officers=officers,reserve_cargo=reserves,
                   days=days,percent=rules.MARCH_SUPPLY_PERCENT[mode],base_grain=basic,
                   extra_grain=total-basic,total_grain=total,stages={mode:ticks})
    stages=[('plain',2000),('embark',1000),('river_downstream',3000),('river_upstream',4000)]
    total=rules.ceil_div(rules.charge(10100,stages,0,10),50*rules.RATION_SCALE)
    assert total==2293
    yield dict(case='specified_mixed_profile',route_mode='mixed',troops=10_000,officers=1,reserve_cargo=0,
               days=10,percent=None,base_grain=2020,extra_grain=total-2020,total_grain=total,stages=stages)


def cargo_cases():
    for mode,days,quantity in product(MODES,DURATIONS,LOADS):
        net,remainder=rules.estimate_cargo(quantity,[(mode,days*rules.DAY_TICKS)],days)
        yield dict(case='no_weather_no_cargo_meals',route_mode=mode,days=days,sent=quantity,received=net,
                   lost=quantity-net,remainder=remainder,bps=rules.CARGO_GRAIN_LOSS_BPS[mode])


def real_transports(game, state):
    examples=_same_owner_examples(game)
    assert set(examples)=={'land','river','sea'}
    for mode,quantity in product(examples, (100,10_000,50_000,100_000,200_000,100_000_001)):
        source,target,raw=examples[mode]
        # Overrides are confined to the sample, and the normal command still checks
        # configured permission, maximum feasible stock and the actual transit.
        status='dispatched'
        result={}
        if quantity<=logistics.LIMIT:
            result=_contract(game,deepcopy(state),source,target,raw,amount=quantity)
        else:
            status='blocked_by_cargo_limit'
        fields=['case','from_city','to_city','requested_mode','route_ids','departure_month','outbound_days',
                'return_days','outbound_grain','return_grain',*sorted(logistics.RECEIPT_FIELDS),'grain_conserved']
        yield dict(scenario=game.catalog.data['id'],requested_cargo=quantity,status=status,
                   **{key:result.get(key) for key in fields})


def real_minimum(catalogs, seed):
    cases=(('188-06','jincheng','shuofang','attack'),('235-01','shuofang','jincheng','transfer'),
           ('217-07','shujun','bajun','transfer'),('208-10','jiangxia','nanjun','attack'))
    for key,source,target,purpose in cases:
        game=open_game(catalogs[key],seed)
        state=game.state
        ids=state.cities[source].roster.officer_ids[:1]
        roster_active=bool(ids)
        if not ids:
            owner=state.cities[source].owner
            ids=[ident for ident,person in state.officers.items() if person.alive and person.faction_id==owner][:1]
        assert ids,(key,source,target)
        with grain_units.using(state):
            for cargo in (0,1000,10_000):
                row=march_preview.preview_logistics(game,state,source,target,ids,'minimum_grain',purpose,cargo,0,0)
                fastest,minimum=row['fastest'],row['minimum']
                def columns(quote):
                    if not quote:
                        return dict(days=None,path=None,grain=None,cargo_loss=None,returning=None)
                    estimate=quote['logistics']
                    return dict(days=quote['days'],path=quote['path'],grain=estimate['total_grain'],
                                cargo_loss=estimate['cargo_loss'],returning=estimate['return_grain'])
                yield dict(scenario=key,source=source,target=target,purpose=purpose,cargo=cargo,
                           opening_roster_can_dispatch=roster_active,
                           sample_officer='opening_origin' if roster_active else 'hypothetical_friendly_officer',
                           can_use_minimum=bool(minimum),reason=row['blocked_reason'],
                           **{f'{name}_{measure}':value for name,route in (('fastest',fastest),('minimum',minimum))
                              for measure,value in columns(route).items()})


def real_budgets(rows, seed):
    for game in (open_game(catalog,seed) for catalog in rows):
        state=game.state
        with grain_units.using(state):
            for owner in sorted({city.owner for city in state.cities.values()}-{'neutral'}):
                for city, result in budget.budgets(game,state,owner).items():
                    yield dict(scenario=game.catalog.data['id'],city=city,owner=owner,**result)


def real_recruit(game, state):
    city=state.cities['jiangxia']
    initial=city.grain
    for stock,requested,threat in product((0,100,1000,5000,initial,100_000),(100,500,1000),(False,True)):
        city.grain=stock
        plan=budget.budgets(game,state,city.owner)[city.id]
        plan['threatened']=threat
        accepted=budget.recruitment(game,state,city,requested,plan)
        assert 0<=accepted<=requested and (accepted==0 or stock>0)
        yield dict(scenario=game.catalog.data['id'],city=city.id,
                   case='scenario_opening' if stock==initial and not threat else 'controlled_stock_and_threat',
                   requested=requested,accepted=accepted,stock=city.grain,threatened=threat,
                   residents=plan['residents'],wages=plan['wage_grain'],garrison=plan['garrison'],
                   before_reserves=city.reserves,nominal_income=plan['regular'],known_inbound=plan['timely'],
                   reserve_months=plan['months'],strategic_grain_target=plan['target'])
    city.grain=initial


def real_sorties(game, state):
    from remake.strategic_ai import StrategicAI

    original=state.cities['jiangxia']
    target=state.cities['nanjun']
    for strength,scenario_stock in product((1000,10_000,30_000,50_000,100_000), (0,2000,20_000,100_000)):
        fresh=deepcopy(state)
        source=fresh.cities[original.id]
        source.grain=scenario_stock
        count=rules.ceil_div(strength,OFFICER_TROOP_CAP)
        ids=source.roster.officer_ids[:count]
        weight,remainder=divmod(strength,count)
        for n,ident in enumerate(ids):
            fresh.officers[ident].troops=weight+(n<remainder)
        assert len(ids)==count
        planner=StrategicAI(game,fresh)
        for mode in ('fastest','land','river'):
            quote=planner.quote(source,target,mode,adjacent=True)
            if not quote:
                continue
            plan=planner.war_budget(source,target,ids,quote)
            yield dict(scenario=game.catalog.data['id'],from_city=source.id,to_city=target.id,
                       case='controlled_roster_actual_route_and_budget',troops=strength,officers=count,
                       stock=source.grain,gold=source.gold,route_mode=mode,route_ids=[r['id'] for r in quote['routes']],
                       outbound_days=quote['days'],**plan)


def export(output, seed):
    scenarios=catalogs()
    indexed={cat.path.stem:cat for cat in scenarios}
    game=open_game(indexed['208-10'],seed)
    state=game.state
    with grain_units.using(state):
        march=list(rations())
        cargo=list(cargo_cases())
        transport=list(real_transports(game,state))
        recruiting=list(real_recruit(game,state))
        sorties=list(real_sorties(game,state))
    selections=list(real_minimum(indexed,seed))
    strategic=list(real_budgets(scenarios,seed))
    datasets={'march-supply-cases-v2':march,'cargo-attrition-cases-v2':cargo,'transport-conservation-v2':transport,
              'minimum-grain-route-cases':selections,'war-budget-v2':sorties,
              'ai-recruitment-budget-cases':recruiting,'ai-expedition-budget-cases':sorties,
              'strategic-grain-reserves':strategic}
    for name, data in datasets.items():
        to_csv(output/(name+'.csv'),data)
    result={name:len(data) for name,data in datasets.items()}
    to_json(output/'case-validation.json',result)
    to_json(output/'experiments'/'high-pressure-rates.json',
        dict(kind='optional_stress_profile',applied_to_observer_runs=False,
             march_percent=dict(plain=150,mountain=200,desert=200,river_downstream=110,
                 river_still=115,river_upstream=125,sea=120,embark=110,node_wait=100),
             cargo_loss_bps=dict(plain=100,mountain=200,desert=200,river_downstream=20,
                 river_still=30,river_upstream=40,sea=40,embark=0,node_wait=0)))
    print(result)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seed',type=int,default=2026)
    args=parser.parse_args()
    export(args.output,args.seed)
