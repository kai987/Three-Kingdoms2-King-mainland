"""Evaluate the existing upkeep of newly captured territory."""
from . import facilities, logistics_strategy
from .difficulty import get_settings
from .logistics_rules import ceil_div

FIELD = 'ai_recent_occupation'


def captured(state, city):
    if logistics_strategy.occupancy_budget(state) and city.owner != state.player:
        state.extension.setdefault(FIELD,{})[city.id] = [city.owner,state.turn]


def prune(state):
    if FIELD not in state.extension:
        return
    rows=state.extension[FIELD]
    for key, (owner, _) in list(rows.items()):
        if state.cities[key].owner != owner:
            del rows[key]
    if not rows:
        del state.extension[FIELD]


def validate(game,state):
    if FIELD not in state.extension:
        return
    rows=state.extension[FIELD]
    if not logistics_strategy.occupancy_budget(state) or not isinstance(rows,dict) or not rows:
        raise ValueError('Newly occupied cities')
    for key, value in rows.items():
        if (not isinstance(value,list) or len(value)!=2 or key not in state.cities
                or not isinstance(value[0],str) or value[0] not in game.catalog.factions
                or value[0]!=state.cities[key].owner or value[0]==state.player
                or type(value[1]) is not int or not 1<=value[1]<=state.turn):
            raise ValueError('Occupation record')


def assess(ai, owner, economy):
    state=ai.state
    records=state.extension.get(FIELD,{})
    if not records:
        return []
    output=[]
    for key, budget in economy.budgets.items():
        if key not in records or records[key][0]!=owner:
            continue
        city=state.cities[key]
        forecast=economy.cities[key]
        developed=state.extension['city_development']['cities'][key]
        threat=ai.threat(city)
        defense=min(get_settings(state)['min_guard_troops'],ceil_div(threat,2))
        grain_gap=forecast.first_missing
        guard_gap=max(0,defense-budget['active'])
        supplies=budget['timely_grain']
        status='pending' if grain_gap or guard_gap else 'secured'
        # Only direct local exposure is scored here. No estimate for hiring,
        # replacing losses, or spending resources on a second budget.
        local_risk=max(min(20,ceil_div(guard_gap*20,max(1,defense))),
                       min(20,ceil_div(grain_gap*20,max(1,budget['next_installment']))))
        row=dict(city=key,owner=owner,capture_turn=records[key][1],
                 population=developed['population'],grain=city.grain,gold=city.gold,reserves=city.reserves,
                 regular_grain=budget['regular'],regular_gold=budget['regular_gold'],
                 wage_grain=budget['wage_grain'],wage_gold=budget['wage_gold'],
                 garrison=budget['active'],defense=defense,threat=threat,
                 sustainable=budget['sustainable_combined'],next_grain_gap=grain_gap,
                 zero_in=budget['zero_in'],supplies_on_time=supplies,local_risk=local_risk,
                 status=status)
        row.update(land=developed['land'],industry=developed['industry'],control=developed['governance'])
        row['disaster_damage']=facilities._pool(state)['cities'][key]['damage']
        output.append(row)
    return output


def record(ai,owner,economy):
    rows=assess(ai,owner,economy)
    table=ai.state.extension.get(FIELD,{})
    for row in rows:
        logistics_strategy.observe('occupation',ai.state,**row)
        if row['status']=='secured':
            table.pop(row['city'],None)
    prune(ai.state)
    return [row for row in rows if row['status']=='pending']
