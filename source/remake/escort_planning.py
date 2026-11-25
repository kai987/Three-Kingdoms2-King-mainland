"""Use ordinary personnel and allocation orders to staff actual relief work."""
from . import army_relief, command_books, domestic, historical_campaigns, logistics, logistics_strategy
from .difficulty import get_settings
from .errors import GameError
from .officers import OFFICER_TROOP_CAP

LIGHT = 500
MOVE_LIMIT = 20


def assigned_to_war(state,city):
    rows=state.extension['ai_strategy'].get(city.owner,{}).get('orders',())
    return {ident for row in rows if row['source']==city.id and row['march_id'] is None
            and row['departure_turn']>=state.turn
            and state.cities[row['target']].owner!=city.owner
            and not historical_campaigns.allied(state,city.owner,state.cities[row['target']].owner)
            for ident in row['officers']}


def eligible(game,state,city):
    locked=assigned_to_war(state,city)
    return [i for i in logistics._eligible(game,state,city) if i not in locked]


def arrange(current, stocks, receivers, *, capacity=logistics.LIMIT, light=LIGHT):
    """Quote a reduction using real local places for every displaced soldier."""
    if current<=light:
        return None
    need=current-light
    changes={}
    for ident,troops in receivers:
        added=min(need,OFFICER_TROOP_CAP-troops)
        if added:
            changes[ident]=troops+added
            need-=added
        if not need:
            break
    if need>max(0,capacity-stocks):
        return None
    return changes


def can_change(game,state,city,donor,ident):
    need=command_books.cost('allocate')+command_books.cost('dispatch_transport')
    if not command_books.can_spend(state,city.owner,need):
        return None
    available=eligible(game,state,city)
    if ident not in available:
        return None
    slots=[i for i in available if i!=ident and state.officers[i].troops<OFFICER_TROOP_CAP]
    slots.sort(key=lambda i:(-state.officers[i].profile.martial_strength,logistics._key(i)))
    strength=state.officers[ident].troops
    receivers=[(i,state.officers[i].troops) for i in slots] if donor and donor['threatened'] else ()
    changes=arrange(strength,city.reserves,receivers)
    if changes is None and not receivers:
        changes=arrange(strength,city.reserves,[(i,state.officers[i].troops) for i in slots])
    if changes is None:
        return None
    freed=strength-LIGHT-sum(troops-state.officers[i].troops for i,troops in changes.items())
    if donor and donor['threatened']:
        troops=donor['active']
        if troops-freed-LIGHT < min(troops,get_settings(state)['min_guard_troops']):
            return None
    return changes | {ident:LIGHT}


def preserves_escort(game,state,city,outlook,budget,relief_needed):
    if (not logistics_strategy.staging(state) or city.owner==state.player or not budget
            or budget['threatened'] or not logistics._pool(state)['cities'][city.id]['policy']['enabled']):
        return None
    profile=logistics._pool(state)['cities'][city.id]['policy']
    if (not (relief_needed or outlook) or city.grain<=max(profile['reserve_grain'],budget['safety_reserve'])
            or logistics._present_count(game,state,city)<=profile['reserve_officers']):
        return None
    options=[i for i in eligible(game,state,city) if state.officers[i].troops<=LIGHT]
    return min(options,key=lambda i:army_relief.escort_rank(state,i),default=None)


def send(game,state,city,planner,donor,*,urgent_only=False):
    policy=logistics._pool(state)['cities'][city.id]['policy']
    if (not policy['enabled'] or historical_campaigns.hold_longyou_garrison(game,state,city)
            or not planner.windows):
        return False
    options,reason=planner.candidates(city,budget=donor,urgent_only=urgent_only)
    if reason=='no_spare_officer' and logistics._eligible(game,state,city) and not eligible(game,state,city):
        reason='officer_reserved_for_war'
    logistics_strategy.observe('relief_quote',state,source=city.id,owner=city.owner,options=options[:1],
        reason=None if options else reason,counters=planner.stats)
    change=None
    legal_adjustment=False
    if not options and reason in {'low_efficiency','heavy_escort','insufficient_grain','defence'}:
        candidates=[i for i in eligible(game,state,city) if state.officers[i].troops>LIGHT]
        for ident in sorted(candidates,key=lambda i:army_relief.escort_rank(state,i)):
            changes=can_change(game,state,city,donor,ident)
            if changes is None:
                continue
            legal_adjustment=True
            projected,_=planner.candidates(city,budget=donor,loads=({ident:LIGHT}),urgent_only=True)
            if projected:
                options,change=projected,changes
                break
        if candidates and not legal_adjustment:
            logistics_strategy.observe('escort_assignment',state,source=city.id,owner=city.owner,
                                       result='no_legal_troop_reassignment',candidates=candidates)
    if not options:
        return False
    proposed=options[0]
    try:
        logistics.dispatch(game,state,dict(source=city.id,target=proposed['city'],target_march=proposed['march_id'],
            officers=proposed['officers'],cargo=dict(gold=0,grain=proposed['max_grain'],reserves=0),
            route_mode=proposed['route_mode']),city.owner,relief_planner=planner,donor_budget=donor,allocation=change)
    except GameError:
        logistics_strategy.observe('escort_assignment',state,source=city.id,owner=city.owner,
                                   result='requirements_changed',army=proposed['march_id'])
        return False
    return True


def prepare(game,state,owner,plan):
    """Screen surplus nearby donors once before voluntary strategic spending."""
    if not command_books.can_spend(state,owner,'dispatch_transport'):
        return False
    planner=army_relief.Planner(game,state,owner)
    meetings={slot.city for ident,slots in planner.windows.items() if planner.demands[ident].urgent
              for slot in slots}
    if not meetings:
        return False
    nearby=set(meetings)
    for node in sorted(meetings):
        for city in game._neighbors(node,state):
            nearby.add(city)
    cities=[key for key in nearby if key in plan.budgets and plan.budgets[key]['exportable']
            and not plan.budgets[key]['threatened']]
    cities.sort(key=lambda key:(key not in meetings,-plan.budgets[key]['exportable'],key))
    for key in cities:
        if send(game,state,state.cities[key],planner,plan.budgets[key],urgent_only=True):
            return True
    return move_neighbor(game,state,owner,plan,planner,meetings,nearby)


def move_neighbor(game,state,owner,plan,planner,meetings,nearby):
    """Make a staffed depot possible via a real, short personnel transfer."""
    from . import march_supply
    if not command_books.can_spend(state,owner,'transfer') or not any(
            row['supply']['shortage_streak'] for row in planner.armies.values()):
        return False
    travel=state.extension['travel']['marches']
    for key in sorted(meetings):
        budget = plan.budgets.get(key)
        if not budget or budget['threatened'] or budget['exportable'] < budget['fixed']:
            continue
        target=state.cities[key]
        policy=logistics._pool(state)['cities'][key]['policy']
        if not policy['enabled'] or eligible(game,state,target):
            continue
        if any(row['kind']=='transfer' and row['target']==key for row in travel):
            continue
        for donor_id in game._neighbors(key,state):
            if donor_id==key or donor_id not in nearby or donor_id not in plan.budgets:
                continue
            source=state.cities[donor_id]
            budget=plan.budgets[donor_id]
            policy=logistics._pool(state)['cities'][donor_id]['policy']
            options=eligible(game,state,source)
            if budget['threatened'] or len(options)<2:
                continue
            ident=min(options,key=lambda i:army_relief.escort_rank(state,i))
            if state.officers[ident].troops>LIGHT:
                continue
            route=logistics._safe_path(game,state,donor_id,key,owner,'land',policy)
            if not route or route['days']>MOVE_LIMIT:
                continue
            grain,stops=march_supply.estimate(state,[ident],route,game=game),route['routes']
            if len(stops)!=1 or grain>budget['exportable']:
                continue
            try:
                game._queue_march(state,source,target,[ident],'transfer','land',staging_budgets=plan.budgets)
            except GameError:
                continue
            logistics_strategy.observe('escort_assignment',state,source=donor_id,owner=owner,target=key,
                                       result='transferred',officer=ident,grain=grain)
            return True
    return False
