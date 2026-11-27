"""Real, saved convoys on the existing geographic routes.

Cargo is removed from the source at departure, counted in transit, and paid
into one friendly destination only after an actual arrival. No ROM inputs.
"""
from collections import Counter
from copy import copy, deepcopy

from . import grain_units
from .errors import GameError
from . import winter_travel, winter_weather
from . import command_books, logistics_rules, historical_campaigns, logistics_strategy, transport_capacity
from .officers import OFFICER_TROOP_CAP, parse_officer_ref
from .route_hazards import allocate_survivors, _python_route_allowed
from .restore_routes import validators as route_validators

SCHEMA = 'tk2-logistics-v3'
LIMIT = 100000000
RULES = dict(max_convoys_per_origin=1, max_journeys=16, receipt_turns=3,
             route_days_per_turn=10, return_on_block=True)
DEFAULT_POLICY = dict(enabled=False, target_city=None,
    reserve_gold=200, reserve_grain=500, reserve_reserves=500, reserve_officers=2,
    target_gold=600, target_grain=1800, target_reserves=2000, target_officers=10,
    allow_sea=False, allow_special=False,
    max_gold=500, max_grain=1500, max_reserves=1000, max_officers=3)
_ROW_FIELDS = {'id', 'owner', 'source', 'target', 'original_target', 'officers',
               'original_officers', 'cargo', 'initial_cargo', 'morale', 'status',
               'journeys', 'checked_turn', 'reason', 'target_march', 'delivered',
               'delivery_done', 'cargo_ledger','route_policy'}
_JOURNEY_FIELDS = {'source', 'target', 'quote', 'mode', 'departure_turn', 'arrival_turn',
                   'departure_year', 'departure_month', 'departure_day', 'risks', 'supply','departure_troops'}
_CITY_FIELDS = {'gold', 'grain', 'reserves'}
_CARGO_FIELDS = _CITY_FIELDS | {'treasure'}
_REASONS = {'outbound', 'arrived', 'returned', 'target_changed', 'route_blocked',
            'origin_changed', 'no_friendly_city', 'no_return_route', 'city_full',
            'resource_full', 'weather', 'waiting', 'journey_limit'}
_REASONS.add('insufficient_grain')
_REASONS.add('route_capacity')
_REASONS.update({'army_missing','army_changed','rendezvous_wait','rendezvous_missed',
                 'delivered','escort_return','retreat','army_supplied','unsafe_return',
                 'rendezvous_expired','rendezvous_replanned'})
_CARGO_KINDS = {'weather','rations','starvation','delivered','army_supply','convoy_supply','bag_return'}
_WAYPOINT_UNLOAD = 'waypoint_unload'
LOSS_FIELD = 'cargo_loss_remainder'
RECEIPT_FIELDS = {'cargo_dispatched','cargo_received','cargo_rations','cargo_route_loss',
                  'cargo_weather_loss','cargo_delivered','cargo_returned','cargo_remaining',
                  'cargo_abandoned','cargo_loss_remainder','escort_base_grain','escort_extra_grain'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def safe_execution(state):
    from . import transport_emergency
    return (logistics_rules.version(state)==logistics_rules.CURRENT and
            (winter_weather.stage(state)<2 or winter_weather.corrected(state,winter_weather.TRANSPORT)
             or transport_emergency.stage(state)))


def _empty_cargo():
    return dict(gold=0, grain=0, reserves=0, treasure=0)


def _treasure_count(state, city):
    if 'treasury' not in state.extension:
        return 0
    from . import treasures
    return treasures.count(state, city)


def _treasure_loss(state, amount):
    if amount:
        from . import treasures
        treasures.record_loss(state, amount)


def _key(ident):
    return (0, ident) if type(ident) is int else (1, str(ident))


def _new_city(city):
    return dict(owner=city.owner, policy=grain_units.policy(DEFAULT_POLICY), last_dispatch_turn=0)


def empty(game, state):
    return dict(schema=SCHEMA, next_id=1,
        cities={key: _new_city(city) for key, city in state.cities.items()},
        convoys=[], receipts={}, reports=[])


def _pool(state):
    return state.extension['logistics']


def marching_ids(state):
    return {i for row in state.extension.get('logistics', {}).get('convoys', []) for i in row['officers']}


def in_transit_reserves(state):
    return sum(row['cargo']['reserves'] for row in state.extension.get('logistics', {}).get('convoys', []))


def due(state):
    return any(_arrived(row['journeys'][-1]) and row['checked_turn'] != state.turn
               for row in state.extension.get('logistics', {}).get('convoys', []))


def _arrived(journey):
    return journey['supply'].get('route_days',journey['supply']['elapsed_days']) >= journey['quote']['days']


def _cargo_change(row, kind, new_cargo, day, reference=None):
    """Every cargo mutation is replayable, including weather/food interleaving."""
    if kind not in (_CARGO_KINDS | {'route_loss', _WAYPOINT_UNLOAD}) or set(new_cargo) != _CARGO_FIELDS:
        raise ValueError('Logistics cargo operation')
    if any(not _int(n,0,99 if key=='treasure' else LIMIT) for key,n in new_cargo.items()):
        raise ValueError('Logistics cargo operation bounds')
    before = deepcopy(row['cargo'])
    if before == new_cargo and kind != 'route_loss':
        return
    row['cargo_ledger'].append(dict(kind=kind,day=day,before=before,
                                    after=deepcopy(new_cargo),reference=reference))
    if 'regional' in row:
        from . import regional_market
        regional_market.track_cargo(row,kind,before['grain'],new_cargo['grain'])
    row['cargo'] = deepcopy(new_cargo)
    if winter_weather.detailed():
        winter_weather.report('convoy_ledger',convoy_id=row['id'],tick=day,owner=row['owner'],
                              kind_of_change=kind,before=before.copy(),after=new_cargo.copy(),reference=reference)


def advance_supply(game, state, row, through_turn=None, *, absolute_tick=None, parts=None, weather_parts=None):
    from .march_supply import advance_unit,current_city
    from . import winter_travel, winter_weather
    if winter_weather.detailed():
        from . import winter_transport
        trace=winter_transport.trace_begin(row)
    else:
        trace=None
    if absolute_tick is not None and row['status'] == 'returning' and row['delivery_done']:
        from . import strategic_granary, transport_emergency
        if (strategic_granary.enabled(state,'return_safety') and transport_emergency.stage(state)
                and transport_emergency.review_return_node(game,state,row,absolute_tick)):
            return 0
    cargo=deepcopy(row['cargo'])
    def changed(kind, new_cargo, day):
        _cargo_change(row,kind,new_cargo,day,dict(journey=len(row['journeys'])-1,tick=day))
        cargo.clear();cargo.update(new_cargo)
    def apply_loss(rate, day):
        if not rate or not cargo['grain']:
            return
        lost, credit = logistics_rules.cargo_loss(cargo['grain'], rate, row[LOSS_FIELD])
        if weather_parts is not None and winter_weather.observing():
            winter_weather.report('cargo',tick=day,unit_id=row['id'],owner=row['owner'],grain=cargo['grain'],
                                  lost=lost,rate=rate,previous_credit=row[LOSS_FIELD])
        changed('route_loss',dict(cargo,grain=cargo['grain']-lost),day)
        row[LOSS_FIELD] = credit
    unit=row
    managed='relief' in row
    if managed and row['status']!='returning' and current_city(row['journeys'][-1]) is not None:
        from . import army_relief
        reason=army_relief.hold_reason(game,state,row,absolute_tick)
        if reason:
            unit=dict(row,hold=True)
            row['reason']=reason
            row['journeys'][-1]['supply']['waiting']=True
    if ('convoy_relief' in row and row['status'] != 'returning'
            and current_city(row['journeys'][-1]) is not None):
        from . import convoy_relief
        if convoy_relief.hold(state,row,absolute_tick):
            unit=dict(row,hold=True)
    if row['journeys'][-1]['supply'].get('retreat_requested') and current_city(row['journeys'][-1]) is not None:
        unit=dict(row,hold=True)
        row['journeys'][-1]['supply']['waiting']=True
    spent=advance_unit(game,state,unit,row['journeys'][-1],through_turn,
                        unit_kind='convoy',cargo=cargo,on_cargo_change=changed,
                        on_cargo_day=apply_loss if LOSS_FIELD in row else None,
                        absolute_tick=absolute_tick,parts=parts,self_funded=managed or 'convoy_relief' in row,weather_parts=weather_parts)
    journey=row['journeys'][-1]
    if 'regional' in row:
        from . import regional_market
        regional_market.track_meals(row,journey['supply']['remaining'])
    remaining=max(0,journey['quote']['days']-journey['supply']['route_days'])
    if 'winter' in journey['supply']:
        remaining=winter_travel.quote_days(game,state,journey['quote'],position=winter_travel.work(journey['supply']))
    journey['arrival_turn']=(journey['supply']['clock_tick']+remaining+9)//10+1
    if _arrived(journey):
        _apply_risks(game,state,row,tick=journey['supply']['clock_tick'])
    if trace is not None:
        winter_transport.trace_day(game,state,row,trace)
    return spent


def _home(state, ident):
    return next((city for city in state.cities.values() if ident in city.roster.officer_ids), None)


def synchronize(game, state):
    pool = _pool(state)
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(city))
        if row['owner'] != city.owner:
            row.update(owner=city.owner, policy=grain_units.policy(DEFAULT_POLICY))
            if not transport_capacity.enabled(state):
                row['last_dispatch_turn']=0
    for row in list(pool['convoys']):
        for ident in row['officers']:
            home=_home(state,ident)
            if (home is not None and home.owner!=row['owner'] and ident in state.officers
                    and state.officers[ident].alive and state.officers[ident].faction_id==row['owner']):
                refuges=[c for c in state.cities.values() if c.owner==row['owner']
                    and game._city_occupancy(state,c)<game.catalog.rules.city_officer_capacity]
                if refuges:
                    refuge=min(refuges,key=lambda c:(len(c.roster.officer_ids),c.id))
                    home.roster.officer_ids.remove(ident);refuge.roster.officer_ids.append(ident)
                else:
                    home.roster.officer_ids.remove(ident)
                    state.officers[ident].faction_id=None;state.officers[ident].loyalty=0
                    state.extension['free_locations'][str(ident)]=home.id
        row['officers'] = [i for i in row['officers'] if i in state.officers and state.officers[i].alive
            and state.officers[i].faction_id == row['owner'] and _home(state, i) is not None]
        if not any(c.owner == row['owner'] for c in state.cities.values()):
            lost = row['cargo']['reserves']
            state.soldiers['lost'] += lost
            _treasure_loss(state,row['cargo']['treasure'])
            _event(game, state, 'transport_returned', row, lost=lost, reason='no_friendly_city')
            _trace_terminal(game, state, row, 'no_friendly_city')
            pool['convoys'].remove(row)
    for ident in list(pool['receipts']):
        if pool['receipts'][ident] <= state.turn:
            pool['receipts'].pop(ident)


def _validate_policy(game, state, policy):
    if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
        raise ValueError('Logistics policy fields')
    for key in ('enabled', 'allow_sea', 'allow_special'):
        if type(policy[key]) is not bool:
            raise ValueError('Logistics policy boolean')
    if policy['target_city'] is not None and (not isinstance(policy['target_city'], str)
            or policy['target_city'] not in game.catalog.map_cities):
        raise ValueError('Logistics destination')
    for key in ('reserve_officers', 'target_officers', 'max_officers'):
        if not _int(policy[key], 1 if key == 'max_officers' else 0, 99):
            raise ValueError('Logistics officer threshold')
    for key in set(DEFAULT_POLICY) - {'enabled', 'allow_sea', 'allow_special', 'target_city',
                                      'reserve_officers', 'target_officers', 'max_officers'}:
        if not _int(policy[key], 0, LIMIT):
            raise ValueError('Logistics resource threshold')


def set_policy(game, state, payload, owner):
    if (not isinstance(payload, dict) or set(payload) - {'city', 'policy'}
            or not isinstance(payload.get('city'), str) or payload['city'] not in state.cities):
        raise GameError('前线运输方针无效。')
    city = state.cities[payload['city']]
    if city.owner != owner or owner == 'neutral' or state.phase not in {'city', 'ai'}:
        raise GameError('请选择战略阶段的本方城池。')
    patch = payload.get('policy', {})
    if not isinstance(patch, dict) or set(patch) - set(DEFAULT_POLICY):
        raise GameError('前线运输方针无效。')
    revised = deepcopy(_pool(state)['cities'][city.id]['policy'])
    revised.update(deepcopy(patch))
    try:
        _validate_policy(game, state, revised)
    except (ValueError, TypeError) as error:
        raise GameError('前线运输方针无效。') from error
    _pool(state)['cities'][city.id]['policy'] = revised


def projected_grain(game, quote, grain, *, progress=0, remainder=0, state=None, position=None):
    if not grain:
        return 0
    from . import winter_travel, winter_weather
    if game is not None and winter_weather.stage(state)>=2:
        return winter_travel.estimate_cargo(game,state,quote,grain,
            position=progress*winter_travel.QUANTA if position is None else position,remainder=remainder)
    rules=game.catalog.data['travel_rules'] if game is not None else None
    parts=logistics_rules.plan(quote,rules)
    return logistics_rules.estimate_cargo(grain,parts,quote['days']-progress,
                                          start=progress,remainder=remainder)[0]


def inbound_grain(game,row,state=None):
    grain=row['cargo']['grain']
    if LOSS_FIELD not in row:
        return grain
    journey=row['journeys'][-1]
    from .winter_travel import work
    if (state is not None and winter_weather.corrected(state,winter_weather.TRANSPORT)
            and (journey['supply'].get('winter',{}).get('blocked') is not None or
                 game is not None and winter_travel.forecast(game,state,journey['quote'],
                                                              position=work(journey['supply']))[0] is None)):
        return 0
    return projected_grain(game,journey['quote'],grain,progress=journey['supply']['route_days'],
                           remainder=row[LOSS_FIELD],state=state,position=work(journey['supply']))


def gross_shipment(game, quote, needed, capacity, *, state=None):
    """Smallest legal load expected to reach the quota, or the full capacity."""
    if not needed or not capacity:
        return 0
    if projected_grain(game,quote,capacity,state=state)<needed:
        return capacity
    low,high=needed,capacity
    while low<high:
        candidate=(low+high)//2
        if projected_grain(game,quote,candidate,state=state)>=needed:
            high=candidate
        else:
            low=candidate+1
    return low


def _inbound(state, key, *, game=None):
    rows = [row for row in _pool(state)['convoys'] if row['target'] == key
            and row['owner'] == state.cities[key].owner and not row['delivery_done']
            and row['target_march'] is None and 'convoy_relief' not in row and row['status'] != 'returning']
    result={field:sum(r['cargo'][field] for r in rows) for field in _CARGO_FIELDS-{'grain'}}
    return dict(result,grain=sum(inbound_grain(game,r,state) for r in rows),officers=0)


def _fronts(game, state, owner):
    found = set()
    for route in game._known_routes(state):
        for a, b in ((route['from'], route['to']), (route['to'], route['from'])):
            if (a in state.cities and b in state.cities and state.cities[a].owner == owner
                    and state.cities[b].owner not in {owner, 'neutral'}
                    and not historical_campaigns.allied(state, owner, state.cities[b].owner)
                    and _python_route_allowed(game.catalog.data, route, a, b)):
                found.add(a)
    return [state.cities[key] for key in sorted(found)]


def _target(game, state, source, policy):
    if policy['target_city'] is not None:
        return state.cities.get(policy['target_city'])
    choices = [city for city in _fronts(game, state, source.owner) if city.id != source.id]
    return min(choices, key=lambda c: (c.reserves + _inbound(state, c.id)['reserves'], c.grain, c.id)) if choices else None


def _dangerous(quote, policy):
    return any((leg['mode'] == 'sea' and not policy['allow_sea'])
               or (leg.get('hazard') and leg['hazard']['kind'] != 'monsoon_storm' and not policy['allow_special'])
               for leg in quote['routes'])


def _permitted_route(game, policy, raw):
    if raw['mode'] == 'sea' and not policy['allow_sea']:
        return False
    if raw['mode'] == 'land' and not policy['allow_special']:
        rules = game.catalog.data['travel_hazards']
        yinping, ziwu = rules.get('yinping', {}), rules.get('ziwu', {})
        pair = {raw['from'], raw['to']}
        if pair == {yinping.get('from', 'yinping'), yinping.get('to', 'shujun')}:
            return False
        if pair == {ziwu.get('from', 'hanzhong'), ziwu.get('to', 'jingzhao')} and raw.get('special', 'ziwu') == 'ziwu':
            return False
    return True


def _safe_engine(game, policy):
    """Share one filtered graph across a batch without editing the catalog.

    Rejecting only its fastest answer would miss a longer safe land detour.
    Copies keep the catalog and all published geometry fingerprints unchanged.
    """
    engine = copy(game)
    engine.catalog = copy(game.catalog)
    engine.catalog.data = dict(game.catalog.data,
        travel_routes=[row for row in game.catalog.data['travel_routes'] if _permitted_route(game, policy, row)],
        exploration_routes=[row for row in game.catalog.data.get('exploration_routes', []) if _permitted_route(game, policy, row)])
    return engine


def _safe_path(game, state, source, target, owner, mode, policy, **load):
    return _safe_engine(game,policy)._travel_path(state,source,target,owner,mode,**load)


def _supply_routes(game, state, owner, pairs, policy):
    from . import ai_core
    direct_water=transport_capacity.enabled(state,'mode_aware_ai_policy')
    if direct_water:
        pairs=tuple(pairs)
    if ai_core.enabled():
        data = game.catalog.data
        excluded = [r['id'] for key in ('travel_routes', 'exploration_routes') for r in data.get(key, ())
                    if not _permitted_route(game, policy, r)]
        result=ai_core.routes(game, state, owner, pairs, excluded=excluded)
    else:
        engine = _safe_engine(game, policy)
        result=engine._python_supply_paths(state, owner, pairs)
    if direct_water:
        # One scan of active direct links per batch. The normal G2 land and
        # fastest searches also remain available, including mixed paths.
        directions=set(pairs)
        routes,_,prepare=game._python_route_graph(state,scoped=({},{}))
        best={}
        for route in routes:
            mode=route['mode']
            if mode=='land' or not _permitted_route(game,policy,route):
                continue
            for a,b in ((route['from'],route['to']),(route['to'],route['from'])):
                if (a,b) not in directions or state.cities[b].owner!=owner:
                    continue
                leg,days=prepare(route,a,b)
                if leg is None:
                    continue
                rank=days,leg['distance_km'],leg['id']
                key=a,b,mode
                if key not in best or rank<best[key][0]:
                    best[key]=rank,leg
        result.update({f'{a}:{b}:{mode}':game._quote([a,b],[entry[1]])
                       for (a,b,mode),entry in best.items()})
    return result


def _safe_options(game, state, source, target, policy, *, quotes=None):
    from .winter_travel import quote_days, route_risk
    # The strategic batch accepts friendly origins. An escort may have to
    # return from a stop that changed hands after it set out.
    if quotes is None and state.phase == 'ai' and state.cities[source.id].owner == source.owner:
        quotes = _supply_routes(game, state, source.owner, [(source.id, target.id)], policy)
    choices = []
    # Ocean permission never disables a safe inland shipping route. Retain
    # the old land-only answer (and its saved mode) when no river is involved.
    modes=('land','fastest','river','sea') if quotes is not None and transport_capacity.enabled(
        state,'mode_aware_ai_policy') else ('land','fastest')
    known=set()
    for mode in modes:
        quote = (_safe_path(game,state,source.id,target.id,source.owner,mode,policy)
                 if quotes is None else quotes.get(f'{source.id}:{target.id}:{mode}'))
        if (quote is not None and mode == 'fastest' and not policy['allow_sea']
                and not any(leg['mode'] == 'river' for leg in quote['routes'])):
            continue
        if quote is not None and not _dangerous(quote, policy) and safe_capacity_route(game,state,quote):
            if len(modes)>2:
                key=tuple(leg['id'] for leg in quote['routes'])
                if key in known:
                    continue
                known.add(key)
            days=quote_days(game,state,quote)
            at_risk=bool(state.phase=='ai' and route_risk(game,state,quote,days*2))
            choices.append((at_risk, days, quote['distance_km'], mode, quote))
    return [(mode, quote) for _, _, _, mode, quote in sorted(choices, key=lambda row: row[:4])]


def _safe_quote(game, state, source, target, policy, *, quotes=None):
    choices = _safe_options(game, state, source, target, policy, quotes=quotes)
    return choices[0] if choices else None


def _eligible(game, state, source, *, absent=None, automatic=None, compound_actor=None, capacity_checks=False):
    busy = game._march_ids(state) if absent is None else absent
    from .domestic import appointments
    offices = appointments(state, source.owner)
    assigned = {offices.get('civil'), offices.get('military')}
    ids = [i for i in source.roster.officer_ids if i not in busy and i not in assigned
            and state.officers[i].alive and state.officers[i].faction_id == source.owner
            and state.officers[i].health > 0
            and _pool(state)['receipts'].get(str(i), 0) <= state.turn]
    if not capacity_checks and not transport_capacity.enabled(state):
        return ids
    from .escort_planning import assigned_to_war
    held = assigned_to_war(state, source)
    if automatic is None:
        automatic = transport_capacity.automation(state,source.owner)
    if automatic:
        held.add(state.extension['leaders'].get(source.owner))
    actions = state.extension['officer_actions']
    staff = state.extension.get('civil_staff', {}).get('people', {})
    return [i for i in ids if i not in held and (i == compound_actor or actions.get(str(i)) != state.turn)
            and staff.get(i, {}).get('working', True)]


def _present_count(game, state, source, *, absent=None):
    busy = game._march_ids(state) if absent is None else absent
    return sum(state.officers[i].alive and state.officers[i].faction_id == source.owner
               and i not in busy for i in source.roster.officer_ids)


def escort_defence(game, state, source, ids, *, allocation=None, threatened=None, absent=None,
                   capacity_checks=False):
    if not capacity_checks and not transport_capacity.enabled(state):
        return True
    if threatened is None:
        threatened = any(row['kind']=='attack' and row['target']==source.id and row['owner']!=source.owner
                         and not historical_campaigns.allied(state,source.owner,row['owner'])
                         for row in state.extension['travel']['marches'])
    if not threatened:
        return True
    from .difficulty import get_settings
    busy = game._march_ids(state) if absent is None else absent
    loads = allocation or {}
    stationed = {i:loads.get(i,state.officers[i].troops) for i in source.roster.officer_ids
                 if state.officers[i].alive and state.officers[i].faction_id==source.owner and i not in busy}
    active = sum(stationed.values())
    return active-sum(stationed.get(i,0) for i in ids) >= min(active,get_settings(state)['min_guard_troops'])


def safe_capacity_route(game, state, quote):
    if transport_capacity.enabled(state):
        ice = state.extension.get(winter_weather.POOL, {}).get('ice', {})
        return not any(ice.get(part['reach_id'], {}).get('state') == 3
                       for leg in quote['routes'] for part in leg.get('river_segments', ()))
    return True


def _rations(game, state, quote, ids, cargo):
    from .march_supply import estimate
    return estimate(state, ids, quote, cargo['reserves'], game=game)


def escort_rations(game, state, ids, outward, backward, *, reserves=0):
    """Quote both complete routes, including different terrain on the return."""
    from .march_supply import quote_supply, ration_units
    from . import transport_emergency, winter_transport
    emergency = transport_emergency.stage(state)
    if winter_transport.enabled(state) or emergency and winter_weather.movement(state):
        out=winter_transport.protected_cost(game,state,outward,ration_units(state,ids,reserves))
        back=winter_transport.protected_cost(game,state,backward,ration_units(state,ids))
        meal=out['meal']+back['meal']
        return logistics_rules.ceil_div(meal*winter_transport.SAFETY_PERCENT,100)
    troops=sum(state.officers[i].troops for i in ids)
    meal = (quote_supply(outward,troops,len(ids),reserves,game=game,version=logistics_rules.CURRENT,state=state) +
            quote_supply(backward,troops,len(ids),game=game,version=logistics_rules.CURRENT,state=state))
    return logistics_rules.ceil_div(meal*winter_transport.SAFETY_PERCENT,100) if emergency else meal


def convoy_return(game, state, source, target, policy):
    return (('land',game._quote([source.id],[])) if source.id==target.id else
            _safe_quote(game,state,target,source,policy))


def capacity_quote(game,state,source,target,ids,quote,cargo,reserves,back):
    policy=_pool(state)['cities'][source.id]['policy']
    physical=transport_capacity.enabled(state,'physical_capacity')
    from . import transport_emergency
    round_trip=physical or winter_weather.corrected(state,winter_weather.TRANSPORT) or transport_emergency.stage(state)
    rations=(_rations(game,state,quote,ids,dict(reserves=reserves)) if not back or not round_trip
        else escort_rations(game,state,ids,quote,back,reserves=reserves))
    available=transport_capacity.current_grain(state,source)-policy['reserve_grain']
    room=max(0,LIMIT-target.grain-_inbound(state,target.id)['grain'])
    profile=transport_capacity.physical(game,state,quote)
    if not physical:
        profile.update(physical_capacity=None,bottleneck=None)
    load=transport_capacity.loading(game,state,source.owner,policy,quote,rations,available,room,profile=profile)
    reason=transport_capacity.dispatch_blocker(state,source)
    if not reason:
        if not command_books.can_spend(state,source.owner,'dispatch_transport'):
            reason='command_books'
        elif (len(ids)>policy['max_officers'] or _present_count(game,state,source)-len(ids)<policy['reserve_officers']
                or not escort_defence(game,state,source,ids)):
            reason='no_spare_officer'
        elif not safe_capacity_route(game,state,quote) or round_trip and (not back or not safe_capacity_route(game,state,back)):
            reason='no_route'
        elif available<rations or source.reserves-reserves<policy['reserve_reserves']:
            reason='insufficient_resources'
        elif reserves>policy['max_reserves']:
            reason='policy_capacity'
        elif load['physical_capacity'] is not None and rations>load['physical_capacity']:
            reason='route_capacity'
    grain=min(cargo,load['max_cargo'])
    out=winter_travel.quote_days(game,state,quote)
    back_days=winter_travel.quote_days(game,state,back) if back else None
    net=projected_grain(game,quote,grain,state=state)
    load.update(net_grain=net, estimated_loss=grain-net, load_grain=grain, blocked_reason=reason,
                outward_days=out,return_days=back_days,turnover=None)
    if back_days is not None:
        load['turnover']=transport_capacity.metrics(net,rations,out,back_days,(-out)%10+(-back_days)%10,
                                                   len(ids),RULES['receipt_turns'])
    return load


def _army(state, ident, owner):
    if type(ident) is not int:
        return None
    return next((row for row in state.extension['travel']['marches']
        if row['id']==ident and row['owner']==owner and row['officers']),None)


def _meeting_quote(game, state, source, army, policy):
    """A supply party walks to an actual future city, never a map coordinate."""
    from . import winter_travel
    dynamic='winter' in army['supply']
    position=winter_travel.work(army['supply'])
    progress=army['supply'].get('route_days',0)
    elapsed=0
    choices=[]
    stops=[]
    for index,key in enumerate(army['quote']['path']):
        if index:
            elapsed+=army['quote']['routes'][index-1]['days']
        if elapsed*winter_travel.QUANTA < position or state.cities[key].owner!=source.owner:
            continue
        stops.append((index,key,elapsed))
    pairs = [(source.id,key) for _,key,_ in stops if key != source.id]
    quotes = _supply_routes(game,state,source.owner,pairs,policy) if pairs and state.phase=='ai' else None
    for index,key,elapsed in stops:
        if key==source.id:
            selected=('land',game._quote([key],[]))
        else:
            selected=_safe_quote(game,state,source,state.cities[key],policy,quotes=quotes)
        if selected:
            mode,quote=selected
            # Prefer a future stop the courier can reach before the column;
            # a late party must subsequently re-plan instead of remote giving.
            deadline=max(0,elapsed-progress)
            if dynamic:
                deadline=winter_travel.forecast(game,state,army['quote'],position=position,
                                                stop=elapsed*winter_travel.QUANTA)[0]
                if deadline is None:
                    continue
            from .march_supply import current_city
            days=winter_travel.quote_days(game,state,quote)
            late=days>deadline
            if army['supply'].get('waiting') and current_city(army)==key:
                late=False
            choices.append((late,index,days,key,mode,quote))
    if not choices:
        return None
    _,_,_,city,mode,quote=min(choices,key=lambda r:r[:4])
    return city,mode,quote


def rescue_targets(game, state, city_id):
    from .march_supply import current_city,next_city,remaining_requirement
    source=state.cities[city_id]
    policy=transport_capacity.ai_policy(state,source.owner,_pool(state)['cities'][city_id]['policy'],
                                       automatic=transport_capacity.automation(state,source.owner))
    if logistics_strategy.army_relief(state):
        from . import army_relief
        planner=army_relief.Planner(game,state,source.owner)
        if not planner.armies:
            return []
        options,blocked=planner.candidates(source)
        best={}
        for option in options:
            best.setdefault(option['march_id'],option)
        result=[]
        for ident,army in planner.armies.items():
            row=dict(march_id=ident,location_city=current_city(army),next_city=next_city(army),
                city=None,target_city=army['target'],quote=None,route_mode='land',officers=[],
                max_grain=0,needed_grain=planner.demands[ident].required,cost_grain=0,
                can_dispatch=ident in best,blocked_reason=None if ident in best else blocked,eta_turn=None)
            row.update(best.get(ident,{}))
            result.append(row)
        return result
    eligible=sorted(_eligible(game,state,source),key=lambda i:(-state.officers[i].profile.martial_strength,_key(i)))
    spare=max(0,_present_count(game,state,source)-policy['reserve_officers'])
    ids=eligible[:min(1,policy['max_officers'],spare)]
    active=transport_capacity.activity(state)
    result=[]
    for army in state.extension['travel']['marches']:
        if army['owner']!=source.owner or source.owner=='neutral':
            continue
        supply=army['supply']
        need=max(0,remaining_requirement(game,state,army,minimum_days=10)-supply['remaining'])
        row=dict(march_id=army['id'],location_city=current_city(army),next_city=next_city(army),
            city=None,target_city=army['target'],quote=None,route_mode='land',officers=list(ids),
            max_grain=0,needed_grain=need,cost_grain=0,can_dispatch=False,
            blocked_reason=None,eta_turn=None)
        reason=None
        if state.phase not in {'city','ai'}:reason='wrong_phase'
        elif source.owner not in game.catalog.factions:reason='not_owned'
        elif _army(state,army['id'],source.owner) is None:reason='army_changed'
        elif not command_books.can_spend(state,source.owner,'dispatch_transport'):reason='command_books'
        elif (transport_capacity.dispatch_blocker(state,source,active) if transport_capacity.enabled(state)
              else active.get(source.id,0)):reason='in_transit'
        elif not ids or not escort_defence(game,state,source,ids):reason='no_spare_officer'
        selected=None if reason else _meeting_quote(game,state,source,army,policy)
        if not reason and selected is None:reason='no_route'
        if selected:
            city,mode,quote=selected
            cost=_rations(game, state,quote,ids,dict(reserves=0))
            maximum=min(policy['max_grain'],max(0,source.grain-policy['reserve_grain']-cost))
            if transport_capacity.enabled(state,'physical_capacity'):
                back=convoy_return(game,state,source,state.cities[city],policy)
                if back is None:
                    reason='no_route'
                    maximum=0
                else:
                    cost=escort_rations(game,state,ids,quote,back[1])
                    capacity=transport_capacity.loading(game,state,source.owner,policy,quote,cost,
                        transport_capacity.current_grain(state,source)-policy['reserve_grain'],LIMIT,
                        automatic=transport_capacity.automation(state,source.owner))
                    maximum=capacity['max_cargo']
                    row['capacity']=capacity
            row.update(city=city,quote=deepcopy(quote),route_mode=mode,cost_grain=cost,
                       max_grain=maximum,eta_turn=state.turn+winter_travel.quote_turns(game,state,quote))
            if maximum<1 and not reason:reason='insufficient_grain'
        row.update(can_dispatch=reason is None,blocked_reason=reason)
        result.append(row)
    return result


def preview(game, state, city_id):
    source, row = state.cities[city_id], _pool(state)['cities'][city_id]
    automatic=transport_capacity.automation(state,source.owner)
    policy=transport_capacity.ai_policy(state,source.owner,row['policy'],automatic=automatic)
    if source.owner == 'neutral' or source.owner not in game.catalog.factions:
        return None, 'not_owned'
    if state.phase not in {'city', 'ai'}:
        return None, 'wrong_phase'
    if not command_books.can_spend(state, source.owner, 'dispatch_transport'):
        return None, 'command_books'
    if reason:=transport_capacity.dispatch_blocker(state,source):
        return None, reason
    if any(getattr(source, field) < policy['reserve_' + field] for field in _CITY_FIELDS):
        return None, 'insufficient_resources'
    target = _target(game, state, source, policy)
    if target is None or target.id == city_id:
        return None, 'no_target'
    if target.owner != source.owner:
        return None, 'no_friendly_target'
    inbound = _inbound(state, target.id)
    eligible = sorted(_eligible(game, state, source), key=lambda i: (
        -state.officers[i].profile.martial_strength, -state.officers[i].profile.intellect, _key(i)))
    from .domestic import appointments
    offices = appointments(state, source.owner)
    retained = max(policy['reserve_officers'], sum(ident is not None and ident in source.roster.officer_ids
        and ident not in game._march_ids(state) for ident in (offices.get('civil'), offices.get('military'))))
    slots = min(policy['max_officers'], max(0, _present_count(game, state, source) - retained))
    ids = [i for i in eligible if escort_defence(game,state,source,[i])][:min(slots, 1)]
    if not ids:
        return None, 'no_spare_officer'
    cargo = {field: min(policy['max_' + field], max(0, getattr(source, field) - policy['reserve_' + field]),
                        max(0, policy['target_' + field] - getattr(target, field) - inbound[field]))
             for field in _CITY_FIELDS}
    cargo['treasure'] = 0
    # A recently received city does not immediately bounce those resources on.
    if _pool(state)['receipts'].get('city:' + city_id, 0) > state.turn:
        cargo = _empty_cargo()
    if not any(cargo.values()):
        return None, 'no_surplus'
    if transport_capacity.enabled(state,'physical_capacity'):
        pairs=[(source.id,target.id),(target.id,source.id)]
        quotes=_supply_routes(game,state,source.owner,pairs,policy)
        choices=_safe_options(game,state,source,target,policy,quotes=quotes)
        back=_safe_quote(game,state,target,source,policy,quotes=quotes)
        if not choices or back is None:
            return None,'no_route'
        available=transport_capacity.current_grain(state,source)-policy['reserve_grain']
        target_room=max(0,policy['target_grain']-target.grain-inbound['grain'])
        returning=winter_travel.quote_days(game,state,back[1])
        result=[]
        for mode,quote in choices:
            grain=escort_rations(game,state,ids,quote,back[1],reserves=cargo['reserves'])
            capacity=transport_capacity.loading(game,state,source.owner,policy,quote,grain,
                                                available,target_room,automatic=automatic)
            amount=capacity['max_cargo']
            if (available<grain or capacity['physical_capacity'] is not None and grain>capacity['physical_capacity']
                    or not (amount or cargo['gold'] or cargo['reserves'])):
                continue
            proposal=dict(target=target.id,officers=ids,cargo=dict(cargo,grain=amount),quote=deepcopy(quote),
                          route_mode=mode,cost_grain=grain,capacity=capacity)
            if not automatic or not transport_capacity.enabled(state,'throughput_ranking'):
                return proposal,None
            outward=winter_travel.quote_days(game,state,quote)
            risk=bool(winter_travel.route_risk(game,state,quote,outward+returning))
            net=projected_grain(game,quote,amount,state=state)
            score=transport_capacity.priority(net,grain,outward,returning,(-outward)%10+(-returning)%10,
                                               len(ids),RULES['receipt_turns'],grain+amount-net)
            result.append(((risk,*score,mode),proposal))
        return (min(result,key=lambda row:row[0])[1],None) if result else (None,'route_capacity')
    selected = _safe_quote(game, state, source, target, policy)
    if selected is None:
        return None, 'no_route'
    mode, quote = selected
    grain = _rations(game, state, quote, ids, cargo)
    from . import transport_emergency
    if source.owner==state.player and (winter_weather.corrected(state,winter_weather.TRANSPORT)
            or transport_emergency.stage(state)):
        back=convoy_return(game,state,source,target,policy)
        if back is None:
            return None,'no_route'
        grain=escort_rations(game,state,ids,quote,back[1],reserves=cargo['reserves'])
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        cargo['grain'] = max(0, source.grain - grain - policy['reserve_grain'])
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        return None, 'insufficient_grain'
    return dict(target=target.id, officers=ids, cargo=cargo, quote=deepcopy(quote),
                route_mode=mode,cost_grain=grain),None


def treasure_transport(game, state, city_id, *, quote_cache=None):
    """Manual cargo uses the same escort, reserve and known-route boundaries.

    A saved automatic support policy never starts moving treasure on its own.
    Routes are calculated only for cities that actually have treasure to send.
    """
    source = state.cities[city_id]
    available = _treasure_count(state, city_id)
    result = dict(available=available, targets=[])
    if not available or source.owner == 'neutral' or source.owner not in game.catalog.factions:
        return result
    policy = _pool(state)['cities'][city_id]['policy']
    eligible = sorted(_eligible(game, state, source), key=lambda i: (
        -state.officers[i].profile.martial_strength, -state.officers[i].profile.intellect, _key(i)))
    spare = max(0, _present_count(game, state, source)-policy['reserve_officers'])
    ids = eligible[:min(1, policy['max_officers'], spare)]
    common = None
    if state.phase not in {'city', 'ai'}: common = 'wrong_phase'
    elif not command_books.can_spend(state,source.owner,'dispatch_transport'): common = 'command_books'
    elif blocked:=transport_capacity.dispatch_blocker(state,source): common = blocked
    elif not ids or not escort_defence(game,state,source,ids): common = 'no_spare_officer'
    elif any(getattr(source, field) < policy['reserve_' + field] for field in _CITY_FIELDS):
        common = 'insufficient_resources'
    quotes = None
    if common is None:
        quote_cache = dict(quotes=None,engines={}) if quote_cache is None else quote_cache
        if quote_cache['quotes'] is None:
            quote_cache['quotes'] = game._travel_view(state)['travel_quotes']
        quotes = quote_cache['quotes']
    for target in sorted(state.cities.values(), key=lambda city: city.id):
        if target.id == city_id or target.owner != source.owner:
            continue
        reason, quote, mode, cost = common, None, 'land', 0
        selected = _safe_quote(game,state,source,target,policy,quotes=quotes) if reason is None else None
        if (selected is None and reason is None
                and any(f'{source.id}:{target.id}:{mode}' in quotes for mode in ('land','fastest'))):
            # The ordinary graph found a route, but its shortest answers may
            # use a forbidden valley/sea. Search that rare detour against one
            # shared filtered graph per permission pair, not one context per
            # city pair. Removing edges cannot reach an otherwise unreachable
            # destination, so absent ordinary quotes need no second search.
            context = (policy['allow_sea'],policy['allow_special'])
            engines = quote_cache['engines']
            if context not in engines: engines[context] = _safe_engine(game,policy)
            engine = engines[context]
            detours = {f'{source.id}:{target.id}:{mode}':
                engine._travel_path(state,source.id,target.id,source.owner,mode)
                for mode in ('land','fastest')}
            selected = _safe_quote(game,state,source,target,policy,quotes=detours)
        if reason is None and selected is None: reason = 'no_route'
        if selected:
            mode, quote = selected
            cost = _rations(game, state, quote, ids, _empty_cargo())
            if winter_weather.corrected(state,winter_weather.TRANSPORT) or transport_capacity.enabled(state,'physical_capacity'):
                back=_safe_quote(game,state,target,source,policy,
                                 quotes=None if transport_capacity.enabled(state,'physical_capacity') else quotes)
                if back is None:
                    reason='no_route'
                else:
                    cost=escort_rations(game,state,ids,quote,back[1])
            if source.grain-cost < policy['reserve_grain']: reason = 'insufficient_grain'
            if transport_capacity.enabled(state,'physical_capacity'):
                physical=transport_capacity.physical(game,state,quote)['physical_capacity']
                if not safe_capacity_route(game,state,quote): reason = 'no_route'
                elif physical is not None and cost>physical: reason = 'route_capacity'
        result['targets'].append(dict(target=target.id, officers=list(ids),
            days=winter_travel.quote_days(game,state,quote) if quote else None,modes=list(quote['modes']) if quote else [],
            route_mode=mode, cost_grain=cost, max_treasure=min(99, available),
            target_treasure=_treasure_count(state, target.id),
            can_dispatch=reason is None, blocked_reason=reason))
    return result


def grain_receipt(row, *, returned=False, abandoned=False):
    cargo = row['cargo']['grain']
    bags = [journey['supply'] for journey in row['journeys']]
    basic = sum(book.get('base_consumed',book['consumed']) for book in bags)
    result=dict(cargo_dispatched=row['initial_cargo']['grain'],cargo_received=0,cargo_rations=0,
        cargo_route_loss=0,cargo_weather_loss=0,cargo_delivered=row['delivered']['grain'],
        cargo_returned=cargo if returned else 0,cargo_abandoned=cargo if abandoned else 0,
        cargo_remaining=0 if returned or abandoned else cargo,cargo_loss_remainder=row[LOSS_FIELD],
        escort_base_grain=basic,escort_extra_grain=sum(book['consumed'] for book in bags)-basic)
    fields={'rations':'cargo_rations','route_loss':'cargo_route_loss','weather':'cargo_weather_loss',
            'bag_return':'cargo_received'}
    for entry in row['cargo_ledger']:
        field=fields.get(entry['kind'])
        if field:
            change=entry['before']['grain']-entry['after']['grain']
            result[field]+=-change if entry['kind']=='bag_return' else change
        if entry['kind']==_WAYPOINT_UNLOAD:
            result['cargo_waypoint_unloaded']=result.get('cargo_waypoint_unloaded',0)+(
                entry['before']['grain']-entry['after']['grain'])
    return result


def valid_grain_receipt(values):
    if not isinstance(values,dict) or set(values)-{'cargo_waypoint_unloaded'}!=RECEIPT_FIELDS or not all(
            _int(value,0,16*LIMIT) for value in values.values()):
        return False
    return (values[LOSS_FIELD]<logistics_rules.LOSS_SCALE and
            values['cargo_dispatched']+values['cargo_received']==values.get('cargo_waypoint_unloaded',0)+sum(values[field] for field in
                ('cargo_rations','cargo_route_loss','cargo_weather_loss','cargo_delivered',
                 'cargo_returned','cargo_abandoned','cargo_remaining')))


def _event(game, state, kind, row, *, lost=0, reason='outbound',amounts=None):
    reports = _pool(state)['reports']
    values=row['cargo'] if amounts is None else amounts
    details = dict(convoy_id=row['id'], gold=values['gold'], grain=values['grain'],
                   reserves=values['reserves'], treasure=values.get('treasure',0), lost=lost, reason=reason)
    if LOSS_FIELD in row:
        details['grain_receipt']=grain_receipt(row,returned=reason=='returned',abandoned=reason=='no_friendly_city')
    if winter_weather.detailed() and (kind in ('transport_departed','transport_arrived','transport_weather')
                                      or kind=='transport_returned' and reason not in ('returned','no_friendly_city')):
        from .transport_emergency import note
        note(game,state,'convoy_event',row,kind_of_event=kind,source=row['source'],target=row['target'],
             initial_reserves=row['initial_cargo']['reserves'],bag_loaded=row['journeys'][0]['supply']['loaded'],
             delivered=row['delivery_done'],lost=lost,report_reason=reason,grain=values['grain'])
    reports.append(dict(turn=state.turn, owner=row['owner'], source=row['source'], target=row['target'],
                        kind=kind, details=details))
    reports[:] = reports[-100:]
    if 'strategic' in row:
        from . import strategic_granary
        strategic_granary.transport_event(state,row,kind,values)
    if kind=='transport_arrived' and transport_capacity.observed():
        transport_capacity.observe(state,'delivery',id=row['id'],owner=row['owner'],
            source=row['source'],target=row['target'],cargo=dict(values))
    if row['owner'] == state.player:
        ids = row['officers'][:1]
        game._emit_event(state, kind, city_ids=list(dict.fromkeys((row['source'], row['target']))),
            person_ids=[state.officers[i].person_id for i in ids], factions=[row['owner']], details=details)


def _journey(game, state, source, target, mode, quote, ids, reserves, *, from_cargo=False,initial_grain=None,previous=None):
    from .march_supply import create
    from .winter_travel import set_eta
    journey=dict(source=source, target=target, mode=mode, quote=deepcopy(quote),
        departure_turn=state.turn, arrival_turn=state.turn + quote['turns'],
        departure_year=state.year, departure_month=state.month, departure_day=state.day,
        risks=game._march_risks(quote, state.rng),
        departure_troops={str(i):state.officers[i].troops for i in ids},
        supply=create(state, ids, quote, reserves, game=game, from_cargo=from_cargo,initial_grain=initial_grain,previous=previous))
    return set_eta(game,state,journey)


def dispatch(game, state, payload, owner, *, emergency_grain=None, relief_planner=None, donor_budget=None, allocation=None,
             convoy_relief_quote=None, regional_order=None, strategic_order=None, strategic_path=None,
             strategic_floor=None, transshipment_quote=None):
    from . import transport_emergency, transshipment
    if (not isinstance(payload, dict) or set(payload) - {'source', 'target', 'officers', 'cargo', 'route_mode','target_march','target_convoy'}
            or not isinstance(payload.get('source'), str) or not isinstance(payload.get('target'), str)
            or payload['source'] not in state.cities or payload['target'] not in state.cities):
        raise GameError('运输队参数无效。')
    source, target = state.cities[payload['source']], state.cities[payload['target']]
    target_march=payload.get('target_march')
    target_convoy=payload.get('target_convoy')
    rescue=None
    if 'target_convoy' in payload:
        if (transport_emergency.stage(state)<transport_emergency.EXTERNAL_RELIEF or target_march is not None
                or type(target_convoy) is not int or emergency_grain is not None or allocation is not None):
            raise GameError('運輸隊接濟參數無效。')
        rescue=next((row for row in _pool(state)['convoys'] if row['id']==target_convoy and row['owner']==owner),None)
        if rescue is None:
            raise GameError('請選擇仍在等待接濟的本方運輸隊。')
    army=_army(state,target_march,owner) if target_march is not None else None
    if target_march is not None and army is None:
        raise GameError('请选择仍在本方行军队列中的部队。')
    if owner == 'neutral' or source.owner != owner or target.owner != owner or source.id == target.id and army is None:
        raise GameError('运输起点与目的地必须是不同的本方城池。')
    if state.phase not in {'city', 'ai'}:
        raise GameError('本城当前不能派出运输队。')
    command_books.require(state, owner, 'dispatch_transport')
    pool = _pool(state)
    automatic=transport_capacity.automation(state,owner)
    policy=transport_capacity.ai_policy(state,owner,pool['cities'][source.id]['policy'],automatic=automatic)
    if transport_capacity.dispatch_blocker(state,source):
        raise GameError('本城已有在途运输队。')
    ids, cargo, mode = payload.get('officers'), payload.get('cargo'), payload.get('route_mode', 'land')
    compound_actor=None
    if regional_order is not None and transport_capacity.enabled(state):
        from . import regional_market
        order=regional_market._orders(state).get(str(regional_order))
        if (order and ids==[order['actor']] and order['status']=='purchased' and order['created']==state.turn
                and (order['owner'],order['source'],order['target'])==(owner,source.id,target.id)):
            compound_actor=order['actor']
    eligible = set(_eligible(game,state,source,compound_actor=compound_actor,
                             capacity_checks=transshipment_quote is not None))
    if (not isinstance(ids, list) or not ids or len(ids) > 99
            or any(type(i) not in (int, str) for i in ids) or len(ids) != len(set(ids))
            or any(i not in eligible for i in ids)):
        raise GameError('请选择本城未出征且未担任内政官的押运武将。')
    try:
        ids = [parse_officer_ref(i, game.catalog.rules) for i in ids]
    except (ValueError, TypeError) as error:
        raise GameError('请选择本城未出征且未担任内政官的押运武将。') from error
    if (not isinstance(cargo, dict) or set(cargo) not in (_CITY_FIELDS,_CARGO_FIELDS)
            or any(not _int(value, 0, 99 if key=='treasure' else LIMIT) for key,value in cargo.items())):
        raise GameError('运输物资数量无效。')
    cargo = dict(cargo,treasure=cargo.get('treasure',0))
    if (army is not None or rescue is not None) and (cargo['gold'] or cargo['reserves'] or cargo['treasure'] or not cargo['grain']):
        raise GameError('行军补给队只能运送兵粮。')
    if not isinstance(mode, str) or mode not in {'land', 'fastest', 'river', 'sea', 'special', 'minimum_grain'}:
        raise GameError('请选择已知的运输路线。')
    relief = None
    special = None
    if rescue is not None:
        from . import convoy_relief
        special = convoy_relief_quote
        if special is None:
            planner = convoy_relief.Planner(game,state,owner)
            special, _ = planner.quote(source,rescue,selected=dict(target=target.id,ids=ids,mode=mode),cargo=cargo['grain'])
        if special is None:
            raise GameError('目前沒有符合路權、存糧和返程預算的接濟方案。')
    if allocation is not None:
        from . import escort_planning
        if (not logistics_strategy.staging(state) or army is None or len(ids)!=1
                or allocation!=escort_planning.can_change(game,state,source,donor_budget,ids[0])):
            raise GameError('押运编兵条件已经变更。')
    if army is not None and logistics_strategy.army_relief(state):
        from . import army_relief
        planner=relief_planner or army_relief.Planner(game,state,owner)
        options,blocked=planner.candidates(source,budget=donor_budget,cargo=cargo['grain'],
            selected=dict(march_id=target_march,city=target.id,officers=ids,mode=mode),loads=allocation)
        if not options:
            raise GameError(army_relief.dispatch_error(blocked))
        relief=options[0]
    if army is not None and relief is None:
        selected=_meeting_quote(game,state,source,army,policy)
        if selected is None or selected[0]!=target.id:
            raise GameError('部队已移动，请重新选择实际会合城池。')
    quote = transshipment_quote['quote'] if transshipment_quote is not None else special['quote'] if special else relief['quote'] if relief else (game._quote([source.id],[]) if source.id==target.id else
             _safe_path(game,state,source.id,target.id,owner,mode,policy,
                        officers=ids,cargo=cargo['grain'],reserves=cargo['reserves']))
    if quote is None or _dangerous(quote, policy) or not safe_capacity_route(game,state,quote):
        raise GameError('没有符合方针的安全运输路线。')
    if strategic_order is not None and quote['path'] != strategic_path:
        from . import strategic_granary
        raise GameError(strategic_granary.STALE)
    if _present_count(game, state, source) - len(ids) < policy['reserve_officers']:
        raise GameError('押运后未达到本城保留武将人数。')
    if not escort_defence(game,state,source,ids,allocation=allocation,capacity_checks=transshipment_quote is not None):
        raise GameError('押運後未達到來源城的必要防禦兵力。')
    physical_enabled=transshipment_quote is not None or transport_capacity.enabled(state,'physical_capacity')
    profile=transport_capacity.physical(game,state,quote) if physical_enabled else None
    policy_grain=transport_capacity.policy_limit(state,owner,policy,profile,automatic=automatic)
    if (cargo['grain']>policy_grain or any(cargo[field]>policy['max_'+field] for field in ('gold','reserves'))
            or len(ids)>policy['max_officers']):
        raise GameError('运输队超过本城的单次运输上限。')
    checked_fields = {'grain'} if army is not None or rescue is not None or emergency_grain is not None else _CITY_FIELDS
    if any(getattr(source, field) - cargo[field] < policy['reserve_' + field] for field in checked_fields):
        raise GameError('运输后未达到本城保留物资数量。')
    grain = (transshipment_quote['rations'] if transshipment_quote is not None else special['rations'] if special else relief['cost_grain'] if relief else _rations(game, state, quote, ids, cargo)
             if emergency_grain is None else emergency_grain)
    if (emergency_grain is None and special is None and relief is None
            and transshipment_quote is None
            and (physical_enabled or army is None and rescue is None and
                 (winter_weather.corrected(state,winter_weather.TRANSPORT) or transport_emergency.stage(state)))):
        back=convoy_return(game,state,source,target,policy)
        if back is None:
            raise GameError('没有符合方针的安全运输路线。')
        grain = escort_rations(game,state,ids,quote,back[1],reserves=cargo['reserves'])
    if physical_enabled and profile['physical_capacity'] is not None and cargo['grain']+grain>profile['physical_capacity']:
        raise GameError('貨糧與獨立口糧超過實際路線的裝載容量。')
    if ((transport_capacity.enabled(state) or transshipment_quote is not None) and army is None and rescue is None
            and cargo['grain']>LIMIT-target.grain-_inbound(state,target.id)['grain']):
        raise GameError('目的城不足以接收本次貨糧。')
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        raise GameError('运输队粮食不足，或低于本城保留量。')
    if cargo['treasure'] > _treasure_count(state,source.id):
        raise GameError('本城的宝数量不足。')
    if pool['next_id'] > 1000000:
        raise GameError('运输队编号已达上限。')
    from . import strategic_granary
    if transport_capacity.enabled(state) or transshipment_quote is not None:
        from . import staging_supply
        if cargo['grain']+grain > staging_supply.available(state,source)-policy['reserve_grain']:
            raise GameError('扣除已承諾的軍糧後，來源城可用糧不足。')
    if (not strategic_granary.enabled(state) and army is None and rescue is None and emergency_grain is None
            and transshipment.credit(state,source.id)
            and cargo['grain']+grain > transport_capacity.current_grain(state,source)-policy['reserve_grain']):
        raise GameError(transshipment.BLOCKED)
    if strategic_granary.enabled(state):
        priority = (army is not None or rescue is not None
                    or emergency_grain is not None and strategic_order is None and regional_order is None)
        if priority:
            strategic_granary.spending(state,source,cargo['grain']+grain,'military_or_urgent')
        elif strategic_floor is not None and strategic_order is not None and strategic_granary.enabled(state,'coordination'):
            strategic_granary.spend_for_dispatch(state,source,cargo['grain']+grain,strategic_order,strategic_floor)
        elif cargo['grain']+grain > strategic_granary.available(state,source,except_id=strategic_order):
            raise GameError(strategic_granary.INSUFFICIENT)
    if allocation is not None:
        from . import domestic
        command_books.spend(state,source,'allocate')
        before={str(i):state.officers[i].troops for i in allocation}
        domestic.apply_allocation(state,source,allocation)
        logistics_strategy.observe('escort_assignment',state,source=source.id,owner=owner,army=target_march,
                                    officer=ids[0],before=before,after=allocation,reserves=source.reserves)
    for field in _CITY_FIELDS:
        setattr(source, field, getattr(source, field) - cargo[field])
    if cargo['treasure']:
        from . import treasures
        treasures.debit(state,source.id,cargo['treasure'])
    command_books.spend(state, source, 'dispatch_transport')
    source.grain -= grain
    state.extension['officer_actions'].update({str(i): state.turn for i in ids})
    from . import domestic
    domestic.on_departure(game, state, ids, source.id)
    row = dict(id=pool['next_id'], owner=owner, source=source.id, target=target.id,
        original_target=target.id, officers=list(ids), original_officers=list(ids), cargo=deepcopy(cargo),
        initial_cargo=deepcopy(cargo), morale=domestic.morale(state, source.id), status='outbound',
        journeys=[_journey(game, state, source.id, target.id, mode, quote, ids, cargo['reserves'],
                           initial_grain=grain)],
        checked_turn=0, reason='outbound',target_march=target_march,
        delivery_done=False,delivered=_empty_cargo(),cargo_ledger=[],
        route_policy={k:policy[k] for k in ('allow_sea','allow_special')})
    if logistics_rules.version(state)==logistics_rules.CURRENT:
        row[LOSS_FIELD]=0
    if strategic_order is not None:
        row['strategic'] = strategic_order
    if regional_order is not None:
        row['regional']=dict(id=regional_order,cargo=cargo['grain'],bag=0,consumed=0)
    if winter_weather.corrected(state,winter_weather.TRANSPORT):
        row['original_eta']=row['journeys'][0]['arrival_turn']
    if relief:
        row['relief']=relief['relief']
        planner.register(row)
    pool['next_id'] += 1
    if physical_enabled:
        row['journeys'][0][transport_capacity.LOAD_FIELD]=dict(total=cargo['grain']+grain,
            limit=profile['physical_capacity'],policy_grain=policy_grain)
    transport_capacity.record_dispatch(state,source.id)
    pool['convoys'].append(row)
    if special:
        row['convoy_relief']=special['relief']
        convoy_relief.register(game,state,row,rescue)
    _event(game, state, 'transport_departed', row)
    if transport_capacity.observed():
        detail=profile if profile is not None else transport_capacity.physical(game,state,quote)
        transport_capacity.observe(state,'departure',id=row['id'],source=source.id,target=target.id,
            owner=owner,officers=list(ids),escort_troops=sum(state.officers[i].troops for i in ids),
            cargo=dict(cargo),rations=grain,profile=detail,policy_grain=policy_grain,
            active=transport_capacity.active_count(state,source),dispatch_count=transport_capacity.dispatch_count(state,source.id),
            route_mode=mode,path=list(quote['path']),route_ids=[leg['id'] for leg in quote['routes']],
            legs=[{key:leg[key] for key in ('id','from','to','mode','terrain','days')} for leg in quote['routes']],
            outbound_days=winter_travel.quote_days(game,state,quote),
            estimated_net=projected_grain(game,quote,cargo['grain'],state=state),
            command_books=command_books.cost('dispatch_transport'),
            purpose='transshipment' if transshipment_quote is not None else 'strategic' if strategic_order is not None else 'regional' if regional_order is not None else
                    'army' if army is not None else 'convoy_relief' if rescue is not None else 'ordinary')
    return row


def auto_dispatch_city(game,state,city_id,*,plans=None,relief_planner=None):
    from . import transport_emergency
    if (not _pool(state)['cities'][city_id]['policy']['enabled']
            or historical_campaigns.hold_longyou_garrison(game, state, state.cities[city_id])):
        return False
    if logistics_strategy.staging(state):
        from . import army_relief, escort_planning
        city=state.cities[city_id]
        planner=relief_planner or army_relief.Planner(game,state,city.owner)
        if escort_planning.send(game,state,city,planner,(plans or {}).get(city_id)):
            return True
    elif logistics_strategy.army_relief(state):
        from . import army_relief
        city=state.cities[city_id]
        planner=relief_planner or army_relief.Planner(game,state,city.owner)
        if planner.windows:
            donor=(plans or {}).get(city_id)
            options,reason=planner.candidates(city,budget=donor)
            logistics_strategy.observe('relief_quote', state, source=city_id, owner=city.owner,
                                    options=options[:1], reason=None if options else reason, counters=planner.stats)
            if options:
                proposed=options[0]
                dispatch(game,state,dict(source=city_id,target=proposed['city'],target_march=proposed['march_id'],
                    officers=proposed['officers'],cargo=dict(gold=0,grain=proposed['max_grain'],reserves=0),
                    route_mode=proposed['route_mode']),city.owner,relief_planner=planner,donor_budget=donor)
                return True
    else:
        from .march_supply import remaining_requirement
        rescues=[]
        for proposed in rescue_targets(game,state,city_id):
            army=_army(state,proposed['march_id'],state.cities[city_id].owner)
            if not proposed['can_dispatch'] or army is None:
                continue
            supply=army['supply']
            need=remaining_requirement(game,state,army)
            if not (supply.get('waiting') or supply.get('shortage_streak') or supply['remaining']<need):
                continue
            rescues.append((-supply.get('shortage_streak',0),proposed['quote']['days'],army['id'],proposed))
        if rescues:
            proposed=min(rescues,key=lambda r:r[:3])[-1]
            grain=min(proposed['max_grain'],max(1,proposed['needed_grain']))
            dispatch(game,state,dict(source=city_id,target=proposed['city'],target_march=proposed['march_id'],
                officers=proposed['officers'],cargo=dict(gold=0,grain=grain,reserves=0),
                route_mode=proposed['route_mode']),state.cities[city_id].owner)
            return True
    proposed, reason = preview(game, state, city_id)
    if reason:
        if reason=='no_surplus':
            return _auto_transfer_city(game,state,city_id)
        return False
    from . import military_budget
    city=state.cities[city_id]
    managed = logistics_strategy.enabled(state) and city.owner!=state.player
    mode=proposed['route_mode']
    cargo=proposed['cargo']
    if military_budget.enabled(state) and city.owner!=state.player and cargo['grain']:
        plans=military_budget.budgets(game,state,city.owner) if plans is None else plans
        donor=plans[city_id]
        recipient=plans[proposed['target']]
        remaining=max(0,recipient['target']-state.cities[proposed['target']].grain-_inbound(state,proposed['target'],game=game)['grain'])
        if remaining<=0:
            cargo=dict(cargo,grain=0)
            if not any(cargo.values()):
                return False
        else:
            floor=min(donor['target'],donor['fixed']*3)
            if 'minimum_export_floor' in donor:
                floor=max(donor['minimum_export_floor'], donor['safety_reserve'])+donor['reserved_grain']
            cargo=dict(cargo,grain=min(cargo['grain'],remaining,
                max(0,city.grain-floor-proposed['cost_grain'])))
            if cargo['grain'] and recipient['stock']>=recipient['fixed']:
                policy=_pool(state)['cities'][city_id]['policy']
                minimum=_safe_path(game,state,city_id,proposed['target'],city.owner,'minimum_grain',policy,
                    officers=proposed['officers'],cargo=cargo['grain'],reserves=cargo['reserves'])
                if minimum is not None:
                    bags=_rations(game,state,minimum,proposed['officers'],cargo)
                    if city.grain-cargo['grain']-bags>=max(floor,policy['reserve_grain']):
                        mode='minimum_grain'
            if not any(cargo.values()):
                return False
    prepaid = None
    physical=transport_capacity.enabled(state,'physical_capacity')
    if managed or transport_emergency.stage(state) or physical:
        target = state.cities[proposed['target']]
        automatic=transport_capacity.automation(state,city.owner)
        policy=transport_capacity.ai_policy(state,city.owner,_pool(state)['cities'][city_id]['policy'],
                                            automatic=automatic)
        quote = _safe_path(game,state,city_id,target.id,city.owner,mode,policy,
                           officers=proposed['officers'],cargo=cargo['grain'],reserves=cargo['reserves'])
        returning = _safe_quote(game,state,target,city,policy)
        if not quote or not returning:
            return False
        prepaid = escort_rations(game,state,proposed['officers'],quote,returning[1],reserves=cargo['reserves'])
        donor = (plans or {}).get(city_id)
        floor = (max(donor['safety_reserve'],donor['minimum_export_floor'],policy['reserve_grain'])
                 + donor['reserved_grain'] if donor and 'minimum_export_floor' in donor else policy['reserve_grain'])
        room = city.grain - floor - prepaid
        if room < 0:
            return False
        if physical:
            available=min(city.grain-floor,transport_capacity.current_grain(state,city)-policy['reserve_grain'])
            cap=transport_capacity.loading(game,state,city.owner,policy,quote,prepaid,available,cargo['grain'],
                                            automatic=automatic)
            if available<prepaid or cap['physical_capacity'] is not None and prepaid>cap['physical_capacity']:
                return False
            room=cap['max_cargo']
        cargo = dict(cargo,grain=min(cargo['grain'],room))
        net = projected_grain(game,quote,cargo['grain'],state=state)
        # An elective shipment ought to move useful cargo, particularly if
        # the only available escort is already carrying a large garrison.
        if not any(cargo.values()) or net*2+cargo['gold']*5+cargo['reserves'] < prepaid:
            return False
    dispatch(game,state,dict(source=city_id,target=proposed['target'],officers=proposed['officers'],
        cargo=cargo,route_mode=mode),city.owner, **({'emergency_grain':prepaid} if prepaid is not None else {}))
    return True


def attack_grain_shortage(state, target, required_grain):
    """Account for convoys already bringing grain to this launch city."""
    inbound = _inbound(state, target.id)['grain'] if 'logistics' in state.extension else 0
    return max(0, required_grain - target.grain - inbound)


def dispatch_attack_grain(game, state, target, required_grain, *, protected_officers=(), max_turns=None):
    """Send grain for a specific AI sortie using the ordinary convoy service."""
    return dispatch_ai_supply(game, state, target, 0, required_grain,
                              protected_officers=protected_officers, max_turns=max_turns)


def supply_shortages(state, target, gold_goal, grain_goal):
    inbound = _inbound(state, target.id)
    return (max(0, gold_goal - target.gold - inbound['gold']),
            max(0, grain_goal - target.grain - inbound['grain']))


def dispatch_ai_supply(game, state, target, gold_goal, grain_goal, *, protected_officers=(),
                       max_turns=None, require_return=False, economy_plan=None, seasonal=False):
    """Choose an eligible rear escort and move real cargo through the shared order."""
    from . import transport_emergency
    owner = target.owner
    if ('logistics' not in state.extension or state.phase != 'ai' or owner == state.player
            or not command_books.can_spend(state, owner, 'dispatch_transport')):
        return False
    gold_need, grain_need = supply_shortages(state, target, gold_goal, grain_goal)
    pool = _pool(state)
    if not (gold_need or grain_need) or pool['next_id'] > 1000000:
        return False

    active_origins = transport_capacity.activity(state)
    physical=transport_capacity.enabled(state,'physical_capacity')
    threatened = {row['target'] for row in state.extension['travel']['marches']
                  if row['kind'] == 'attack' and row['owner'] != owner
                  and not historical_campaigns.allied(state, owner, row['owner'])}
    protected = set(protected_officers)
    grain_room = LIMIT - target.grain - _inbound(state, target.id)['grain']
    groups, candidates = {}, []
    def grain_floor(source, policy):
        row = economy_plan.budgets.get(source.id) if economy_plan is not None else None
        return (max(row['safety_reserve'], row['minimum_export_floor'], policy['reserve_grain'])
                + row['reserved_grain'] if row else policy['reserve_grain'])

    for source in state.cities.values():
        if (source.owner != owner or source.id == target.id
                or transport_capacity.dispatch_blocker(state,source,active_origins)
                or source.id in threatened or pool['receipts'].get('city:' + source.id, 0) > state.turn
                or historical_campaigns.hold_longyou_garrison(game, state, source)):
            continue
        row = pool['cities'][source.id]
        policy=transport_capacity.ai_policy(state,owner,row['policy'],automatic=True)
        if (not policy['enabled'] or policy['target_city'] not in (None, target.id)
                or source.gold < policy['reserve_gold'] or source.reserves < policy['reserve_reserves']
                or source.grain < policy['reserve_grain']
                or _present_count(game, state, source) <= policy['reserve_officers']):
            continue
        gold = min(gold_need, policy['max_gold'], source.gold - policy['reserve_gold'])
        grain = min(policy['max_grain'], grain_room, source.grain - grain_floor(source, policy))
        if not gold and not (grain_need and grain > 0):
            continue
        escorts = [ident for ident in _eligible(game, state, source) if ident not in protected
                   and escort_defence(game,state,source,[ident],threatened=False)]
        if not escorts:
            continue
        # A light escort consumes less of the shipment on the return journey.
        escort = min(escorts, key=lambda ident: (state.officers[ident].troops, _key(ident)))
        permissions = policy['allow_sea'], policy['allow_special']
        groups.setdefault(permissions, []).append((source, escort, gold, grain))

    by_policy = {}
    capacity_candidates=[]
    for permissions, donors in groups.items():
        policy=transport_capacity.ai_policy(state,owner,pool['cities'][donors[0][0].id]['policy'],automatic=True)
        pairs = [(donor.id, target.id) for donor, *_ in donors]
        pairs += [(dest, origin) for origin, dest in pairs]
        quotes = _supply_routes(game, state, owner, pairs, policy)
        by_policy[permissions] = quotes
        for source, escort, gold, grain in donors:
            policy=transport_capacity.ai_policy(state,owner,pool['cities'][source.id]['policy'],automatic=True)
            if physical:
                choices=_safe_options(game,state,source,target,policy,quotes=quotes)
                returning=_safe_options(game,state,target,source,policy,quotes=quotes)
                available=min(source.grain-grain_floor(source,policy),
                              transport_capacity.current_grain(state,source)-policy['reserve_grain'])
                for mode,quote in choices:
                    days=winter_travel.quote_days(game,state,quote)
                    if max_turns is not None and winter_travel.quote_turns(game,state,quote)>max_turns:
                        continue
                    if seasonal and winter_travel.seasonal_forecast(game,state,quote)['reaches']:
                        continue
                    back=next((route for _,route in returning if not seasonal or not
                               winter_travel.seasonal_forecast(game,state,route,start_in=days)['reaches']),None)
                    if back is None or (require_return and not seasonal and max_turns is not None
                                       and winter_travel.quote_turns(game,state,back)>max_turns):
                        continue
                    prepaid=escort_rations(game,state,[escort],quote,back)
                    cap=transport_capacity.loading(game,state,owner,policy,quote,prepaid,available,grain_room,
                                                    automatic=True)
                    if available<prepaid or cap['physical_capacity'] is not None and prepaid>cap['physical_capacity']:
                        continue
                    load=gross_shipment(game,quote,grain_need,cap['max_cargo'],state=state) if grain_need else 0
                    delivered=projected_grain(game,quote,load,state=state)
                    if not (gold or delivered) or delivered*2+gold*5<prepaid:
                        continue
                    coverage=gold*100//max(1,gold_need)+min(delivered,grain_need)*100//max(1,grain_need)
                    rank=(days,-coverage,-delivered,source.id,mode)
                    if transport_capacity.enabled(state,'throughput_ranking'):
                        returning_days=winter_travel.quote_days(game,state,back)
                        metrics=transport_capacity.priority(delivered,prepaid,days,returning_days,
                            (-days)%10+(-returning_days)%10,1,RULES['receipt_turns'],prepaid+load-delivered)
                        rank=(days, -coverage,*metrics,source.id,mode)
                    capacity_candidates.append((rank,source.id,mode,escort,gold,load,prepaid))
                continue
            if seasonal:
                selected=next(((mode,quote) for mode,quote in _safe_options(game,state,source,target,policy,quotes=quotes)
                              if not winter_travel.seasonal_forecast(game,state,quote)['reaches']),None)
            else:
                selected = _safe_quote(game, state, source, target, policy, quotes=quotes)
            if selected is None:
                continue
            mode, quote = selected
            if max_turns is not None and winter_travel.quote_turns(game,state,quote) > max_turns:
                continue
            rations = _rations(game, state, quote, [escort], _empty_cargo())
            floor = grain_floor(source, policy)
            if source.grain - rations < floor:
                continue
            grain = min(grain, source.grain - floor - rations)
            if gold or (grain_need and grain > 0):
                delivered = (projected_grain(game,quote,grain,state=state)
                             if logistics_rules.version(state)==logistics_rules.CURRENT else grain)
                delivered=min(delivered,grain_need)
                coverage = (gold * 100 // max(1, gold_need)
                            + delivered * 100 // max(1, grain_need))
                # A useful shipment next turn can beat a full load many turns away.
                # A sortie with a specific ration requirement still favors a full load.
                priority = (-(coverage * 100 // winter_travel.quote_turns(game,state,quote)) if require_return
                            else int(gold < gold_need or delivered < grain_need))
                candidates.append((priority, winter_travel.quote_days(game,state,quote), -coverage, -delivered,
                                   source.id, mode, escort, gold, grain, quote))
    if physical:
        if not capacity_candidates:
            return False
        _,source,mode,escort,gold,load,prepaid=min(capacity_candidates,key=lambda row:row[0])
        dispatch(game,state,dict(source=source,target=target.id,officers=[escort],
                                 cargo=dict(_empty_cargo(),gold=gold,grain=load),route_mode=mode),owner,
                 emergency_grain=prepaid)
        return True
    if not candidates:
        return False

    for _, _, _, _, source_id, mode, escort, gold, grain, outbound_quote in sorted(candidates,key=lambda row:row[:-1]):
        source = state.cities[source_id]
        policy=transport_capacity.ai_policy(state,owner,pool['cities'][source_id]['policy'],automatic=True)
        routes=by_policy[policy['allow_sea'], policy['allow_special']]
        if seasonal:
            outbound=winter_travel.quote_days(game,state,outbound_quote)
            selected=next(((back_mode,quote) for back_mode,quote in _safe_options(game,state,target,source,policy,quotes=routes)
                           if not winter_travel.seasonal_forecast(game,state,quote,start_in=outbound)['reaches']),None)
        else:
            selected = _safe_quote(game, state, target, source, policy,quotes=routes)
        if require_return and (selected is None or not seasonal and max_turns is not None
                               and winter_travel.quote_turns(game,state,selected[1]) > max_turns):
            continue
        return_rations = _rations(game, state, selected[1], [escort], _empty_cargo()) if selected else 0
        wanted=grain_need+return_rations if grain_need else 0
        weighted=logistics_rules.version(state)==logistics_rules.CURRENT
        load=gross_shipment(game,outbound_quote,wanted,grain,state=state) if weighted else min(grain,wanted)
        cargo=dict(_empty_cargo(),gold=gold,grain=load)
        if require_return and target.grain + (projected_grain(game,outbound_quote,load,state=state)
                                               if weighted else load) < return_rations:
            continue
        prepaid = None
        if economy_plan is not None or transport_emergency.stage(state):
            if selected is None:
                continue
            prepaid = escort_rations(game,state,[escort],outbound_quote,selected[1])
            ceiling = source.grain - grain_floor(source,policy) - prepaid
            if ceiling < 0:
                continue
            cargo['grain'] = min(cargo['grain'], ceiling)
            if (not any(cargo.values()) or
                    projected_grain(game,outbound_quote,cargo['grain'],state=state)*2+cargo['gold']*5 < prepaid):
                continue
        dispatch(game, state, dict(source=source_id, target=target.id, officers=[escort],
                                   cargo=cargo, route_mode=mode), owner,
                 **({'emergency_grain':prepaid} if prepaid is not None else {}))
        return True
    return False


def _auto_transfer_city(game,state,city_id):
    """Permanent front personnel use the ordinary movement service, not cargo."""
    source=state.cities[city_id];policy=_pool(state)['cities'][city_id]['policy']
    if not command_books.can_spend(state, source.owner, 'transfer') or state.phase not in {'city','ai'}:
        return False
    target=_target(game,state,source,policy)
    if target is None or target.owner!=source.owner or target.id==source.id:
        return False
    inbound=sum(len(r['officers']) for r in state.extension['travel']['marches']
        if r['kind']=='transfer' and r['target']==target.id and r['owner']==source.owner)
    wanted=max(0,policy['target_officers']-game._city_occupancy(state,target)-inbound)
    room=game.catalog.rules.city_officer_capacity-game._city_occupancy(state,target)-inbound
    slots=min(3,wanted,room,max(0,_present_count(game,state,source)-policy['reserve_officers']))
    if slots<1:return False
    selected=_safe_quote(game,state,source,target,policy)
    if selected is None:return False
    mode,_=selected
    quote=game._travel_path(state,source.id,target.id,source.owner,mode)
    if quote is None or _dangerous(quote,policy):return False
    chosen=[]
    for ident in sorted(_eligible(game,state,source),key=lambda i:(-state.officers[i].profile.martial_strength,_key(i))):
        if len(chosen)>=slots:break
        if _rations(game, state,quote,[*chosen,ident],dict(reserves=0))<=max(0,source.grain-policy['reserve_grain']):
            chosen.append(ident)
    if not chosen:return False
    game._queue_march(state,source,target,chosen,'transfer',mode)
    return True


def prepare_ai(game, state, owner):
    fronts = {c.id for c in _fronts(game, state, owner)}
    for key, city in state.cities.items():
        if city.owner == owner:
            policy = _pool(state)['cities'][key]['policy']
            policy['enabled'] = key not in fronts
            policy['allow_sea'] = policy['allow_special'] = False
            policy['max_gold'] = max(policy['max_gold'], 2000)
            policy['max_grain'] = max(policy['max_grain'], grain_units.amount(5000))


def auto_dispatch(game, state, owner):
    synchronize(game, state)
    if owner != state.player:
        prepare_ai(game, state, owner)
    for key, city in sorted(state.cities.items()):
        if city.owner == owner:
            auto_dispatch_city(game, state, key)


def _apply_risks(game, state, row, *, tick=None):
    journey = row['journeys'][-1]
    ids = sorted(row['officers'], key=_key)
    for risk_index,risk in enumerate(journey['risks']):
        if risk['applied']:
            continue
        before = [state.officers[i].troops for i in ids] + [row['cargo']['reserves']]
        after = allocate_survivors(before, risk['survival_numerator'], risk['survival_denominator'])
        risk.update(applied=True, before={str(i): n for i, n in zip(ids, before[:-1])},
                    after={str(i): n for i, n in zip(ids, after[:-1])}, lost=sum(before) - sum(after))
        risk['before']['cargo'] = before[-1]
        risk['after']['cargo'] = after[-1]
        for ident, amount in zip(ids, after[:-1]):
            state.officers[ident].troops = amount
        cargo=deepcopy(row['cargo'])
        cargo['reserves'] = after[-1]
        for field in ('gold', 'grain'):
            cargo[field] = cargo[field] * risk['survival_numerator'] // risk['survival_denominator']
        cargo['treasure'] = cargo['treasure'] * risk['survival_numerator'] // risk['survival_denominator']
        _treasure_loss(state,row['cargo']['treasure']-cargo['treasure'])
        _cargo_change(row,'weather',cargo,(state.turn-1)*10 if tick is None else tick,
            dict(journey=len(row['journeys'])-1,risk=risk_index))
        state.soldiers['lost'] += risk['lost']
        if risk['lost']:
            from . import war_recovery
            war_recovery.record(state,row['owner'],row['source'],'convoy',risk['lost'])
        _event(game, state, 'transport_weather', row, lost=risk['lost'], reason='weather')


def _receiving_blocker(game, state, row, target, *, returning):
    """Use the same physical receiving limits for arrival and zero-day docking."""
    if returning:
        additional=sum(i not in target.roster.officer_ids for i in row['officers'])
        if game._city_occupancy(state,target)+additional>game.catalog.rules.city_officer_capacity:
            return 'city_full'
    remaining=row['journeys'][-1]['supply']['remaining'] if returning else 0
    if any(getattr(target,field)+row['cargo'][field]+(remaining if field=='grain' else 0)>LIMIT
           for field in _CITY_FIELDS):
        return 'resource_full'
    if row['cargo']['treasure'] and _treasure_count(state,target.id)+row['cargo']['treasure']>99:
        return 'resource_full'
    return None


def _dock(game, state, row, target, *, surrender=False, terminal_tick=None):
    from . import domestic, march_supply, transport_emergency, transshipment
    if transport_emergency.stage(state) and not surrender and (
            row not in _pool(state)['convoys'] or target.owner!=row['owner']
            or march_supply.current_city(row['journeys'][-1])!=target.id):
        return False
    blocker=_receiving_blocker(game,state,row,target,returning=True)
    if blocker:
        row.update(status='returning',reason=blocker)
        row['journeys'][-1]['supply']['waiting']=True
        row['journeys'][-1]['supply']['retreat_requested']=True
        return False
    row['target']=target.id
    if (winter_weather.observing() or 'regional' in row or 'strategic' in row or transport_capacity.observed()
            or transshipment.enabled(state)):
        outcome='surrender_settlement' if surrender else 'returned_home' if target.id==row['source'] else 'received_elsewhere'
        _trace_terminal(game,state,row,outcome,target.id,terminal_tick=terminal_tick)
    # Once physically received, these people are no longer marching. This must
    # precede cargo morale weighting so their troops count in the new garrison.
    _pool(state)['convoys'].remove(row)
    domestic.on_arrival(game, state, row['officers'], target.id)
    for ident in row['officers']:
        home = _home(state, ident)
        if home is not None and home.id != target.id:
            home.roster.officer_ids.remove(ident)
            target.roster.officer_ids.append(ident)
        state.extension['officer_actions'][str(ident)] = state.turn
        _pool(state)['receipts'][str(ident)] = state.turn + RULES['receipt_turns']
    for field in ('gold', 'grain'):
        setattr(target, field, getattr(target, field) + row['cargo'][field])
    target.grain += row['journeys'][-1]['supply']['remaining']
    domestic.add_reserves(game, state, target, row['cargo']['reserves'], row['morale'])
    if row['cargo']['treasure']:
        from . import treasures
        treasures.credit(state,target.id,row['cargo']['treasure'])
    _pool(state)['receipts']['city:' + target.id] = state.turn + RULES['receipt_turns']
    _event(game,state,'transport_returned',row,reason='returned')
    return True


def _trace_terminal(game, state, row, outcome, city=None, *, terminal_tick=None):
    from . import transshipment
    end = (state.turn-1)*10 if terminal_tick is None else terminal_tick
    if transshipment.enabled(state):
        transshipment.terminated(state,row,outcome,city,end)
    if 'strategic' in row:
        from . import strategic_granary
        strategic_granary.transport_closed(state,row,outcome,city)
    if 'regional' in row:
        from . import regional_market
        regional_market.transport_closed(state,row,outcome,city)
    if transport_capacity.observed():
        books = [leg['supply'] for leg in row['journeys']]
        receipt = grain_receipt(row,returned=city is not None,abandoned=city is None) if LOSS_FIELD in row else None
        transport_capacity.observe(state,'terminal',id=row['id'],outcome=outcome,owner=row['owner'],
            source=row['source'],target=row['original_target'],city=city,end_tick=end,
            reusable_turn=state.turn+RULES['receipt_turns'] if city is not None and row['officers'] else None,
            original_officers=list(row['original_officers']),received_officers=list(row['officers']) if city else [],
            delivered=dict(row['delivered']),cargo_receipt=receipt,
            waiting_days=sum(book['elapsed_days']-book['route_days'] for book in books),
            ration_spent=sum(book['consumed'] for book in books),hunger_losses=sum(book['lost'] for book in books),
            rations=dict(loaded=sum(book['loaded'] for book in books),received=sum(book['received'] for book in books),
                consumed=sum(book['consumed'] for book in books),to_cargo=sum(book['returned_to_cargo'] for book in books),
                remaining=books[-1]['remaining']),
            troops_received=sum(state.officers[i].troops for i in row['officers']) if city else 0)
    from .transport_emergency import note
    note(game,state,'convoy_terminal',row,at=city,terminal_status=outcome,source=row['source'],
         initial_reserves=row['initial_cargo']['reserves'],delivered=row['delivery_done'],
         remaining_gold=row['cargo']['gold'],remaining_treasure=row['cargo']['treasure'],
         event_tick=terminal_tick,actual_terminal_tick=(state.turn-1)*10 if terminal_tick is None else terminal_tick)


def settle_surrender(game, state, owner, holdings):
    """Account for the surrendering faction's cargo and escorts before transfer."""
    for row in list(_pool(state)['convoys']):
        if row['owner'] != owner:
            continue
        candidates = sorted(holdings, key=lambda city: (city.id != row['source'], city.id))
        target = next((city for city in candidates
                       if not _receiving_blocker(game, state, row, city, returning=True)), None)
        if target is None:
            raise GameError('對方城池沒有空間接收在途運輸隊，無法完成受降。')
        _dock(game, state, row, target, surrender=True)


def _unload(game, state, row, target):
    """Cargo arrives; escorts retain their home slots until the real return."""
    from . import domestic, transport_emergency, transshipment
    if (row['target_march'] is None and (winter_weather.corrected(state,winter_weather.TRANSPORT)
            or transport_emergency.stage(state) or 'regional' in row or 'strategic' in row
            or transport_capacity.enforced(state,row))):
        _reserve_before_unload(game,state,row,target)
    cargo=deepcopy(row['cargo'])
    for field in ('gold','grain'):
        setattr(target,field,getattr(target,field)+cargo[field])
    domestic.add_reserves(game,state,target,cargo['reserves'],row['morale'])
    if cargo['treasure']:
        from . import treasures
        treasures.credit(state,target.id,cargo['treasure'])
    _cargo_change(row,'delivered',_empty_cargo(),(state.turn-1)*10,
                  dict(city=target.id))
    for field in _CARGO_FIELDS:row['delivered'][field]+=cargo[field]
    row['delivery_done']=True
    if transshipment.enabled(state):
        transshipment.delivered(state,row,target,cargo['grain'])
    if 'regional' in row:
        from . import regional_market
        regional_market.unloaded(state,row,target,cargo['grain'])
    _pool(state)['receipts']['city:'+target.id]=state.turn+RULES['receipt_turns']
    _event(game,state,'transport_arrived',row,reason='delivered',amounts=cargo)


def _reserve_before_unload(game,state,row,target):
    from . import march_supply, winter_transport
    home=state.cities[row['source']]
    back=_safe_quote(game,state,target,home,row['route_policy']) if home.owner==row['owner'] else None
    if back is None:
        return
    book=row['journeys'][-1]['supply']
    if winter_weather.movement(state):
        cost=winter_transport.protected_cost(game,state,back[1],march_supply.ration_units(state,row['officers']),
                                            credit=book['credit_units'])
        required=cost['meal']+cost['safety']
    else:
        from . import army_relief
        weight=march_supply.quoted_weight(game,state,back[1],back[1]['days'])
        required=army_relief.ration_budget(march_supply.ration_units(state,row['officers']),weight,0,0,
                                           credit=book['credit_units']).total
    moved=min(row['cargo']['grain'],max(0,required-book['remaining']))
    if moved:
        day=book['clock_tick']
        _cargo_change(row,'rations',dict(row['cargo'],grain=row['cargo']['grain']-moved),day,
                      dict(journey=len(row['journeys'])-1,tick=day))
        march_supply.receive(book,moved,'cargo',row['id'],state.turn)
    winter_weather.action(game,state,'convoy_delivery_budget',target.id,owner=row['owner'],target=home.id,
                          convoy=row['id'],required=required,retained=moved,
                          available=book['remaining'],route=back[1]['path'])


def rendezvous(game, state, *, tick=None):
    """Deliver only when both real parties occupy the same node on this day."""
    from .march_supply import current_city,receive
    tick=(state.turn-1)*10 if tick is None else tick
    for row in list(_pool(state)['convoys']):
        if row['target_march'] is None or row['delivery_done'] or row['status']=='returning':
            continue
        journey=row['journeys'][-1]
        supply=journey['supply']
        army=_army(state,row['target_march'],row['owner'])
        if army is None:
            row.update(status='waiting',reason='army_missing')
            supply['waiting']=True
            supply['retreat_requested']=True
            continue
        city=current_city(journey)
        if (city is None or army['supply'].get('clock_tick')!=tick or supply.get('clock_tick')!=tick
                or current_city(army)!=city):
            if _arrived(journey) and ('relief' not in row or row['reason'] in {'outbound','rendezvous_wait'}):
                elapsed=0;future=False
                for index,key in enumerate(army['quote']['path']):
                    if index:elapsed+=army['quote']['routes'][index-1]['days']
                    if key==city and elapsed>=army['supply']['route_days']:future=True
                row.update(status='waiting',reason='rendezvous_wait' if future else 'rendezvous_missed')
                supply['waiting']=True
            continue
        amount=min(row['cargo']['grain'],max(0,LIMIT-army['supply']['remaining']))
        if 'relief' in row:
            from . import army_relief
            amount=army_relief.handoff(game,state,row,army,city,tick,amount)
        if not amount:
            continue
        receive(army['supply'],amount,'convoy',row['id'],state.turn)
        cargo=dict(row['cargo'],grain=row['cargo']['grain']-amount)
        _cargo_change(row,'army_supply',cargo,tick,dict(march=army['id'],city=city))
        row['delivered']['grain']+=amount
        row.update(delivery_done=True,status='waiting',reason='delivered')
        supply['waiting']=True
        game._supply_event(state,'march_resupplied',unit_kind='march',unit_id=army['id'],
            city=city,owner=row['owner'],grain=amount,reason='convoy')
        _event(game,state,'transport_arrived',row,reason='delivered',
               amounts=dict(gold=0,grain=amount,reserves=0))
    from . import transport_emergency
    if transport_emergency.stage(state)>=transport_emergency.EXTERNAL_RELIEF:
        from . import convoy_relief
        convoy_relief.rendezvous(game,state,tick)


def _begin_journey(game,state,row,here,target,mode,quote,*,status,reason,prepaid=None):
    from .march_supply import close,receive
    if len(row['journeys'])>=RULES['max_journeys']:
        row.update(status='waiting',reason='journey_limit')
        row['journeys'][-1]['supply']['waiting']=True
        return False
    previous=row['journeys'][-1]
    remaining=previous['supply']['remaining']
    cap = None
    physical_enabled=transport_capacity.enforced(state,row)
    if physical_enabled:
        cap=transport_capacity.physical(game,state,quote)['physical_capacity']
        if cap is not None and max(row['cargo']['grain']+remaining,prepaid or 0)>cap:
            row.update(status='waiting',reason='route_capacity')
            previous['supply']['waiting']=True
            transport_capacity.observe(state,'reroute_blocked',id=row['id'],city=here,target=target,
                total=row['cargo']['grain']+remaining,required_rations=prepaid,capacity=cap)
            return False
    if row['cargo']['grain']+remaining>LIMIT:
        row.update(status='waiting',reason='resource_full')
        previous['supply']['waiting']=True
        return False
    if remaining:
        previous['supply']['remaining']=0
        previous['supply']['returned_to_cargo']+=remaining
        _cargo_change(row,'bag_return',dict(row['cargo'],grain=row['cargo']['grain']+remaining),
            (state.turn-1)*10,dict(journey=len(row['journeys'])-1))
    close(previous['supply'],state.turn)
    journey=_journey(game,state,here,target,mode,quote,row['officers'],row['cargo']['reserves'],initial_grain=0,previous=previous['supply'])
    row['journeys'].append(journey)
    row.update(status=status,target=target,reason=reason)
    if safe_execution(state) and status=='returning':
        row['return_leg']=len(row['journeys'])-1
    from .march_supply import estimate
    need=(estimate(state,row['officers'],quote,row['cargo']['reserves'],game=game)
          if prepaid is None else max(remaining,prepaid))
    amount=min(need,row['cargo']['grain'])
    if amount:
        _cargo_change(row,'rations',dict(row['cargo'],grain=row['cargo']['grain']-amount),
            (state.turn-1)*10,dict(journey=len(row['journeys'])-1,tick=(state.turn-1)*10))
        receive(journey['supply'],amount,'cargo',row['id'],state.turn)
        need-=amount
    if need and prepaid is None and state.cities[here].owner==row['owner']:
        amount=min(need,state.cities[here].grain)
        if cap is not None:
            amount=min(amount,max(0,cap-row['cargo']['grain']-journey['supply']['remaining']))
        if amount:
            state.cities[here].grain-=amount
            receive(journey['supply'],amount,'city',here,state.turn)
            game._supply_event(state,'march_resupplied',unit_kind='convoy',unit_id=row['id'],
                city=here,owner=row['owner'],grain=amount,reason='city')
    if physical_enabled:
        journey[transport_capacity.LOAD_FIELD]=dict(total=row['cargo']['grain']+journey['supply']['remaining'],
                                                     limit=cap,policy_grain=None)
    if transport_capacity.observed():
        transport_capacity.observe(state,'reroute',id=row['id'],city=here,target=target,reason=reason,
            from_route=[leg['id'] for leg in previous['quote']['routes']],
            route=[leg['id'] for leg in quote['routes']],days=winter_travel.quote_days(game,state,quote),
            total=row['cargo']['grain']+journey['supply']['remaining'],capacity=cap)
    return True


def unload_for_route(game,state,row,city,target,mode,quote,rations):
    """Credit a friendly warehouse and submit the same capacity-checked route."""
    from . import march_supply
    previous = row['journeys'][-1]
    supply = previous['supply']
    cap = transport_capacity.physical(game,state,quote)['physical_capacity']
    load = row['cargo']['grain']+supply['remaining']
    if (row['status']!='waiting' or march_supply.current_city(previous)!=city.id or city.owner!=row['owner']
            or target.owner!=row['owner'] or len(row['journeys'])>=RULES['max_journeys']
            or cap is None or max(supply['remaining'],rations)>cap or not load>cap
            or city.grain+load-cap>LIMIT):
        return None
    turned_back = row['delivery_done'] or 'return_leg' in row
    tick = (state.turn-1)*10
    if not turned_back and target.id!=row['original_target']:
        return None
    unloaded = load-cap
    _cargo_change(row,_WAYPOINT_UNLOAD,dict(row['cargo'],grain=row['cargo']['grain']-unloaded),tick,
                  dict(city=city.id,journey=len(row['journeys'])-1))
    city.grain += unloaded
    if not _begin_journey(game,state,row,city.id,target.id,mode,quote,
                          status='returning' if turned_back else 'outbound',
                          reason='escort_return' if turned_back else 'route_blocked',prepaid=rations):
        raise ValueError('Settled waypoint cargo could not be routed')
    row.pop('emergency',None)
    return unloaded


def _keep_return_journey(row, here, target, quote):
    index=len(row['journeys'])-1
    if row.get('return_leg')!=index or target!=row['target']:
        return False
    journey=row['journeys'][index]
    old=journey['quote']
    offset=old['path'].index(here)
    if (old['path'][offset:]!=quote['path'] or
            [leg['id'] for leg in old['routes'][offset:]]!=[leg['id'] for leg in quote['routes']]):
        return False
    # Preserve elapsed days, fractional food credit and the original hazard rolls.
    row.update(status='returning',reason='escort_return' if row['delivery_done'] else row['reason'])
    journey['supply']['retreat_requested']=False
    return True


def _return(game, state, row, reason):
    from .march_supply import current_city, ration_units
    from . import transport_emergency, winter_transport
    here=current_city(row['journeys'][-1])
    if here is None:
        # A hungry party first reaches its next real road node. It cannot be
        # moved to a city by editing the return route's origin.
        row.update(status='returning',reason=reason)
        row['journeys'][-1]['supply']['retreat_requested']=True
        return
    friendly=[city for city in state.cities.values() if city.owner==row['owner']]
    if not friendly:
        lost=row['cargo']['reserves'];state.soldiers['lost']+=lost
        _treasure_loss(state,row['cargo']['treasure'])
        _event(game,state,'transport_returned',row,lost=lost,reason='no_friendly_city')
        _trace_terminal(game, state, row, 'no_friendly_city')
        _pool(state)['convoys'].remove(row)
        return
    if transport_emergency.stage(state):
        reason = reason if reason in transport_emergency.REASONS else 'retreat'
        if transport_emergency.direct_home(game,state,row,here,reason):
            return True
        return transport_emergency.withdraw(game,state,row,here,reason)
    if 'relief' in row:
        from . import army_relief
        return army_relief.return_home(game,state,row,here,reason)
    choices=[]
    safety=winter_transport.enabled(state)
    book=row['journeys'][-1]['supply']
    available=book['remaining']+row['cargo']['grain']
    local=state.cities[here]
    # Once the convoy can return home no other route can rank above it.
    for city in sorted(friendly, key=lambda city: city.id != row['source']):
        additional=sum(i not in city.roster.officer_ids for i in row['officers'])
        if game._city_occupancy(state,city)+additional>game.catalog.rules.city_officer_capacity:
            continue
        if city.id==here:
            if not safety or not _receiving_blocker(game,state,row,city,returning=True):
                choices.append((False,city.id!=row['source'],0,city.id,'land',game._quote([here],[]),None))
                if city.id == row['source']:
                    break
            continue
        origin=copy(state.cities[here]);origin.owner=row['owner']
        if transport_capacity.enabled(state,'physical_capacity'):
            selected=next(((mode,quote) for mode,quote in _safe_options(game,state,origin,city,row['route_policy'])
                           if transport_capacity.fits(game,state,row,quote)),None)
        else:
            selected=_safe_quote(game,state,origin,city,row['route_policy'])
        if selected:
            mode,quote=selected
            needed=None
            if safety:
                cost=winter_transport.protected_cost(game,state,quote,ration_units(state,row['officers'],row['cargo']['reserves']),
                                                     credit=book['credit_units'])
                needed=cost['meal']+cost['safety']
            unfunded=needed is not None and available<needed
            choices.append((unfunded,city.id!=row['source'],winter_travel.quote_days(game,state,quote),city.id,mode,quote,needed))
            if city.id == row['source'] and not unfunded:
                break
            if city.id == row['source'] and local.owner==row['owner'] and not _receiving_blocker(game,state,row,local,returning=True):
                choices.append((False,True,0,here,'land',game._quote([here],[]),None))
                break
    if not choices:
        row.update(status='waiting',reason='no_return_route')
        row['journeys'][-1]['supply']['waiting']=True
        return
    unfunded,_,_,target,mode,quote,needed=min(choices,key=lambda x:x[:4])
    if not quote['days']:
        row.update(status='returning',reason=reason)
        _dock(game,state,row,state.cities[target])
        return
    if safe_execution(state) and _keep_return_journey(row,here,target,quote):
        winter_weather.action(game,state,'convoy_return_unchanged',here,owner=row['owner'],target=target,
                              convoy=row['id'],route=quote['path'])
        return
    if unfunded:
        row.update(status='waiting',reason='unsafe_return')
        book['waiting']=True
        return
    if _begin_journey(game,state,row,here,target,mode,quote,status='returning',reason=reason,prepaid=needed):
        _event(game,state,'transport_returned',row,reason=reason)


def resolve_supply_retreats(game,state):
    from .march_supply import current_city
    from . import transport_emergency
    emergency = transport_emergency.stage(state)
    review = None
    for row in list(_pool(state)['convoys']):
        journey=row['journeys'][-1]
        book=journey['supply']
        here=current_city(journey)
        waiting=row.get('emergency', {})
        if emergency and here is not None and (
                book['retreat_requested'] or book['waiting'] and not _arrived(journey)
                    and (row['status']=='returning' or book['shortage_streak'] or 'emergency' in row)
                or emergency>=transport_emergency.TERMINAL and row['status']=='waiting'
                    and not any(row['cargo'].values())
                    and transport_emergency.convoy_units(state,row)==100*len(row['officers'])
                    and row['target_march'] is None and 'convoy_relief' not in row):
            review = review or transport_emergency.Review(game,state)
            reason = waiting.get('reason',row['reason'])
            transport_emergency.withdraw(game,state,row,here,
                reason if reason in transport_emergency.REASONS else 'retreat',review=review)
            continue
        winter=(winter_weather.corrected(state,winter_weather.TRANSPORT) and 'relief' not in row)
        if winter and here and not _arrived(journey) and book['waiting'] and not book['retreat_requested']:
            if _winter_replan(game,state,row,here):
                continue
        if book['retreat_requested']:
            if here is not None:
                reason=row['reason'] if safe_execution(state) and row['reason'] in ('route_blocked','target_changed') else 'retreat'
                _return(game,state,row,reason)
            else:
                row.update(status='returning',reason='retreat')


def _winter_replan(game,state,row,here):
    from . import winter_transport, march_supply
    journey=row['journeys'][-1]
    book=journey['supply']
    target=state.cities[row['target']]
    if target.id==here or target.owner!=row['owner']:
        return False
    winter=winter_transport.budget(game,state,row)
    frozen=winter['blocked']
    if not frozen and row.get('return_leg')!=len(row['journeys'])-1:
        return False
    origin=copy(state.cities[here]);origin.owner=row['owner']
    alternate=_safe_quote(game,state,origin,target,row['route_policy'])
    if alternate is not None:
        mode,quote=alternate
        offset=journey['quote']['path'].index(here)
        old=[leg['id'] for leg in journey['quote']['routes'][offset:]]
        needed=winter_transport.protected_cost(game,state,quote,
            march_supply.ration_units(state,row['officers'],row['cargo']['reserves']),credit=book['credit_units'])
        amount=needed['meal']+needed['safety']
        if ([leg['id'] for leg in quote['routes']]!=old and needed['blocked'] is None
                and amount<=book['remaining']+row['cargo']['grain']):
            status='returning' if row.get('return_leg')==len(row['journeys'])-1 else 'outbound'
            if _begin_journey(game,state,row,here,target.id,mode,quote,status=status,reason='route_blocked',prepaid=amount):
                winter_weather.action(game,state,'convoy_detour',here,owner=row['owner'],target=target.id,
                                      convoy=row['id'],blocked=frozen,old_remaining_work=journey['quote']['days']*
                                      winter_travel.QUANTA-winter_travel.work(book),
                                      route=quote['path'],days=needed['days'])
                return True
    if not frozen and row.get('return_leg')==len(row['journeys'])-1 and winter['shortfall']>row['cargo']['grain']:
        _return(game,state,row,'unsafe_return')
        return True
    return False


def process_arrivals(game, state):
    from .march_supply import process_march_supply
    process_march_supply(game,state)
    synchronize(game, state)
    from . import transport_emergency
    review = None
    for row in sorted(list(_pool(state)['convoys']), key=lambda x: (x['journeys'][-1]['arrival_turn'], x['id'])):
        journey = row['journeys'][-1]
        if 'convoy_relief' in row and row.get('return_leg')!=len(row['journeys'])-1:
            from . import convoy_relief
            if convoy_relief.settle(game,state,row):
                continue
        if ('relief' in row and row['status']!='returning'
                and row['checked_turn']!=state.turn):
            from . import army_relief
            if army_relief.settle(game,state,row):
                continue
        if not _arrived(journey) or row['checked_turn'] == state.turn:
            continue
        row['checked_turn'] = state.turn
        _apply_risks(game, state, row)
        target = state.cities[row['target']]
        if row['target_march'] is not None and row['status']!='returning' and not row['delivery_done']:
            rendezvous(game,state)
            if row['delivery_done']:
                _return(game,state,row,'escort_return')
                continue
            army=_army(state,row['target_march'],row['owner'])
            if army is None:
                _return(game,state,row,'army_missing')
                continue
            if row['reason']=='rendezvous_missed':
                origin=copy(target);origin.owner=row['owner']
                selected=_meeting_quote(game,state,origin,army,row['route_policy'])
                if selected and selected[0]!=target.id:
                    city,mode,quote=selected
                    _begin_journey(game,state,row,target.id,city,mode,quote,
                                   status='outbound',reason='rendezvous_missed')
                else:
                    _return(game,state,row,'rendezvous_missed')
                continue
            journey['supply']['waiting']=True
            row.update(status='waiting',reason='rendezvous_wait')
            continue
        if target.owner != row['owner']:
            _return(game, state, row, 'target_changed')
            continue
        if transport_emergency.stage(state) and ('emergency' in row or row.get('return_leg')==len(row['journeys'])-1):
            review = review or transport_emergency.Review(game,state)
            existing = row.get('emergency', {})
            if (row['status']=='returning' and existing.get('status') in (None,'evacuating')
                    and existing.get('final',target.id)==target.id
                    and transport_emergency.can_receive(game,state,row,target)):
                _dock(game,state,row,target)
            else:
                transport_emergency.withdraw(game,state,row,target.id,existing.get('reason','escort_return'),review=review)
            continue
        blocker=_receiving_blocker(game,state,row,target,returning=row['status']=='returning')
        if blocker:
            if transport_emergency.stage(state) and blocker in ('city_full','resource_full'):
                review = review or transport_emergency.Review(game,state)
                transport_emergency.withdraw(game,state,row,target.id,blocker,review=review)
                continue
            if (row['status']=='waiting' and row['reason']=='resource_full' and row['cargo']['treasure']
                    and _treasure_count(state,target.id)+row['cargo']['treasure']>99):
                _return(game,state,row,'resource_full')
                continue
            row.update(status='returning' if row['status']=='returning' else 'waiting', reason=blocker)
            journey['supply']['waiting']=True
            continue
        if row['status']=='returning':
            _dock(game,state,row,target)
        else:
            if not row['delivery_done']:_unload(game,state,row,target)
            _return(game,state,row,'escort_return')


def view(game, state, *, travel_quotes=None):
    result = dict(rules=deepcopy(RULES), cities={}, convoys=[], marching_officers=[], reports=[])
    if state is None or 'logistics' not in state.extension:
        return result
    pool = _pool(state)
    capacity_enabled=transport_capacity.enabled(state)
    active=transport_capacity.activity(state) if capacity_enabled else None
    if capacity_enabled:
        result['rules'].update(max_convoys_per_origin=transport_capacity.active_limit(state),
                               max_dispatches_per_turn=transport_capacity.dispatch_limit(state))
        result['capacity_version']=transport_capacity.VERSION
    result['convoys'] = deepcopy(pool['convoys'])
    result['marching_officers'] = sorted(marching_ids(state), key=_key)
    result['reports'] = deepcopy([row for row in pool['reports'] if row['owner'] == state.player])
    treasure_quote_cache = dict(quotes=travel_quotes,engines={})
    for key, city in state.cities.items():
        policy = pool['cities'][key]['policy']
        proposed, reason = (preview(game, state, key) if city.owner == state.player and policy['enabled']
                            else (None, 'disabled' if city.owner == state.player else 'not_owned'))
        result['cities'][key] = dict(owner=city.owner, policy=deepcopy(pool['cities'][key]['policy']),
            inbound=_inbound(state, key), can_dispatch=reason is None and city.owner == state.player,
            blocked_reason='not_owned' if city.owner != state.player else reason, preview=proposed,
            rescue_targets=rescue_targets(game,state,key) if city.owner==state.player else [],
            treasure_transport=treasure_transport(game,state,key,quote_cache=treasure_quote_cache) if city.owner==state.player
                else dict(available=0,targets=[]))
        if capacity_enabled and city.owner==state.player:
            limit=transport_capacity.dispatch_limit(state)
            sent=transport_capacity.dispatch_count(state,key)
            available=max(0,transport_capacity.current_grain(state,city)-policy['reserve_grain'])
            result['cities'][key]['capacity']=dict(active=transport_capacity.active_count(state,city,active),
                max_active=transport_capacity.active_limit(state),dispatched=sent,dispatch_limit=limit,
                remaining_dispatches=limit-sent,escorts=len(_eligible(game,state,city)),
                available_grain=available,policy_max_grain=policy['max_grain'])
    return result


def _daily_cargo_rates(game,row):
    for index,journey in enumerate(row['journeys']):
        quote=journey['quote']
        parts=logistics_rules.plan(quote,game.catalog.data.get('travel_rules',{}))
        boundaries={0}
        node=0
        for leg in quote['routes']:
            node+=leg['days']
            boundaries.add(node)
        progress=0
        tick=journey['supply']['start_tick']
        for period in journey['supply']['periods']:
            for meal in period['days']:
                tick+=1
                if meal is None:
                    continue
                if 'winter' in journey['supply']:
                    if meal[5]:
                        yield tick,index,meal[5]
                    continue
                _,_,moved,_=meal
                if moved or progress not in boundaries:
                    weight=logistics_rules.weight(parts,progress,1,rates=logistics_rules.CARGO_GRAIN_LOSS_BPS)
                    if weight:
                        yield tick,index,weight
                progress+=moved


def _validate_cargo(row,state,game):
    ledger=row['cargo_ledger']
    if not isinstance(ledger,list) or len(ledger)>100000:
        raise ValueError('Logistics cargo ledger')
    cargo=deepcopy(row['initial_cargo']);delivered=_empty_cargo()
    weighted=LOSS_FIELD in row
    daily=iter(_daily_cargo_rates(game,row)) if weighted else iter(())
    due=next(daily,None)
    credit=0
    kinds=_CARGO_KINDS | {'route_loss'} if weighted else _CARGO_KINDS
    if weighted and 'transshipment' in state.extension:
        kinds = kinds | {_WAYPOINT_UNLOAD}
    rations={};returns={};seen_weather=set();previous_tick=-1
    for entry in ledger:
        if (not isinstance(entry,dict) or set(entry)!={'kind','day','before','after','reference'}
                or entry['kind'] not in kinds or not _int(entry['day'],0,(state.turn-1)*10)
                or entry['day']<previous_tick or entry['before']!=cargo
                or not isinstance(entry['after'],dict) or set(entry['after'])!=_CARGO_FIELDS
                or any(not _int(n,0,99 if key=='treasure' else LIMIT) for key,n in entry['after'].items())):
            raise ValueError('Logistics cargo operation chain')
        previous_tick=entry['day'];after=entry['after'];reference=entry['reference'];kind=entry['kind']
        if not isinstance(reference,dict):raise ValueError('Logistics cargo operation reference')
        # Meals take from the load before its route loss. Weather and unloading
        # are later in that day's sequence. A zero-grain day keeps the fraction.
        while due and (due[0]<previous_tick or due[0]==previous_tick and not (
                kind in {'rations','starvation','route_loss'} and reference.get('journey')==due[1])):
            if cargo['grain']:
                raise ValueError('Logistics missing daily cargo loss')
            due=next(daily,None)
        if kind=='route_loss':
            if (due is None or not cargo['grain'] or previous_tick!=due[0]
                    or reference!={'tick':due[0],'journey':due[1]}):
                raise ValueError('Logistics cargo loss service day')
            lost,credit=logistics_rules.cargo_loss(cargo['grain'],due[2],credit)
            if after!=dict(cargo,grain=cargo['grain']-lost):
                raise ValueError('Logistics daily cargo loss arithmetic')
            due=next(daily,None)
        elif kind=='weather':
            if set(reference)!={'journey','risk'} or not _int(reference['journey'],0,len(row['journeys'])-1):
                raise ValueError('Logistics weather cargo reference')
            j=reference['journey'];n=reference['risk'];journey=row['journeys'][j]
            if not _int(n,0,len(journey['risks'])-1) or (j,n) in seen_weather:
                raise ValueError('Logistics duplicate weather cargo')
            risk=journey['risks'][n];seen_weather.add((j,n))
            expected=dict(cargo,reserves=risk['after'].get('cargo',-1))
            for field in ('gold','grain','treasure'):
                expected[field]=cargo[field]*risk['survival_numerator']//risk['survival_denominator']
            if not risk['applied'] or cargo['reserves']!=risk['before'].get('cargo') or after!=expected:
                raise ValueError('Logistics weather cargo arithmetic')
        elif kind in {'rations','starvation'}:
            if set(reference)!={'journey','tick'} or not _int(reference['journey'],0,len(row['journeys'])-1) or reference['tick']!=entry['day']:
                raise ValueError('Logistics meal cargo reference')
            j=reference['journey'];supply=row['journeys'][j]['supply']
            if kind=='rations':
                amount=cargo['grain']-after['grain']
                if amount<=0 or after!=dict(cargo,grain=cargo['grain']-amount):
                    raise ValueError('Logistics cargo rations arithmetic')
                rations[j]=rations.get(j,0)+amount
            else:
                receipt=next((r for r in supply['starvation'] if r['tick']==entry['day']),None)
                if (receipt is None or receipt['reserves_before']!=cargo['reserves']
                        or after!=dict(cargo,reserves=receipt['reserves_after'])):
                    raise ValueError('Logistics hunger cargo arithmetic')
        elif kind=='bag_return':
            if set(reference)!={'journey'} or not _int(reference['journey'],0,len(row['journeys'])-2):
                raise ValueError('Logistics returned ration reference')
            j=reference['journey'];amount=after['grain']-cargo['grain']
            if amount<=0 or after!=dict(cargo,grain=cargo['grain']+amount):
                raise ValueError('Logistics returned ration arithmetic')
            returns[j]=returns.get(j,0)+amount
        elif kind=='delivered':
            if set(reference)!={'city'} or reference['city'] not in state.cities or any(after.values()):
                raise ValueError('Logistics unloading reference')
            for field in _CARGO_FIELDS:delivered[field]+=cargo[field]
        elif kind==_WAYPOINT_UNLOAD:
            index=reference.get('journey')
            amount=cargo['grain']-after['grain']
            if (set(reference)!={'journey','city'} or not _int(index,0,len(row['journeys'])-2)
                    or reference['city'] not in state.cities or amount<=0
                    or after!=dict(cargo,grain=cargo['grain']-amount)
                    or row['journeys'][index+1]['source']!=reference['city']
                    or (row['journeys'][index+1]['departure_turn']-1)*10!=entry['day']):
                raise ValueError('Logistics waypoint unloading receipt')
        else:
            amount=cargo['grain']-after['grain']
            key='convoy' if kind=='convoy_supply' else 'march'
            recipient=row.get('convoy_relief',{}).get('target') if key=='convoy' else row['target_march']
            if (recipient is None or set(reference)!={key,'city'} or reference[key]!=recipient
                    or reference['city'] not in state.cities or amount<=0
                    or after!=dict(cargo,grain=cargo['grain']-amount)):
                raise ValueError('Logistics field delivery')
            delivered['grain']+=amount
        cargo=deepcopy(after)
    if weighted and (credit!=row[LOSS_FIELD] or due and cargo['grain']):
        raise ValueError('Logistics cargo loss remainder or missing service day')
    if cargo!=row['cargo'] or delivered!=row['delivered'] or not row['delivery_done'] and any(delivered.values()):
        raise ValueError('Logistics cargo delivery balance')
    for index,journey in enumerate(row['journeys']):
        supply=journey['supply']
        if (rations.get(index,0)!=sum(r['grain'] for r in supply['refills'] if r['kind']=='cargo')
                or returns.get(index,0)!=supply['returned_to_cargo']):
            raise ValueError('Logistics ration transfer balance')


def _validate_strength(row,state):
    from .march_supply import validate_strength_manifests
    removed={str(i) for i in row['original_officers'] if not state.officers[i].alive
             or state.officers[i].faction_id!=row['owner']}
    prior_end=None
    for journey in row['journeys']:
        manifest=journey['departure_troops']
        if prior_end is not None and (set(manifest)-set(prior_end)
                or any(prior_end[k]!=n for k,n in manifest.items())
                or not (set(prior_end)-set(manifest))<=removed):
            raise ValueError('Logistics journey strength continuity')
        def reserves_at(tick):
            cargo=row['initial_cargo']
            for entry in row['cargo_ledger']:
                if entry['day']>=tick:break
                cargo=entry['after']
            return cargo['reserves']
        validate_strength_manifests(journey['supply'],manifest,journey['risks'],removed,reserves_at)
        prior=dict(manifest);risk_cursor=0
        def weather(until):
            nonlocal risk_cursor
            while risk_cursor<until:
                risk=journey['risks'][risk_cursor]
                if not risk['applied']:
                    raise ValueError('Logistics strength uses unapplied weather')
                before={k:v for k,v in risk['before'].items() if k!='cargo'}
                if (set(before)-set(prior) or any(prior[k]!=n for k,n in before.items())
                        or not (set(prior)-set(before))<=removed):
                    raise ValueError('Logistics pre-weather troop strength')
                prior.update({k:v for k,v in risk['after'].items() if k!='cargo'})
                risk_cursor+=1
        for receipt in journey['supply']['starvation']:
            weather(receipt['after_risks'])
            before=receipt['before']
            if (set(before)-set(prior) or any(prior[k]!=n for k,n in before.items())
                    or not (set(prior)-set(before))<=removed):
                raise ValueError('Logistics pre-starvation troop strength')
            prior.update(receipt['after'])
        weather(sum(bool(r['applied']) for r in journey['risks']))
        prior_end=prior
    if any(prior_end.get(str(i))!=state.officers[i].troops for i in row['officers']):
        raise ValueError('Logistics final travelling troop strength')


def validate(game, state):
    route_allowed, evaluate_leg = route_validators(game.catalog.data)
    pool = _pool(state)
    if (not isinstance(pool, dict) or set(pool) != {'schema', 'next_id', 'cities', 'convoys', 'receipts', 'reports'}
            or pool['schema'] != SCHEMA or not _int(pool['next_id'], 1, 1000001)):
        raise ValueError('Logistics schema')
    if not isinstance(pool['cities'], dict) or set(pool['cities']) != set(state.cities):
        raise ValueError('Logistics city ledger')
    for key, city in state.cities.items():
        row = pool['cities'][key]
        if (not isinstance(row, dict) or set(row) != {'owner', 'policy', 'last_dispatch_turn'}
                or row['owner'] != city.owner or not _int(row['last_dispatch_turn'], 0, state.turn)):
            raise ValueError('Logistics city receipt')
        _validate_policy(game, state, row['policy'])
    active_limit=transport_capacity.active_limit(state)
    owners=len(game.catalog.factions) if transport_capacity.enabled(state,'concurrency') else 1
    if not isinstance(pool['convoys'], list) or len(pool['convoys']) > len(state.cities)*active_limit*owners:
        raise ValueError('Logistics convoy bounds')
    seen, people, origins = set(), set(), Counter()
    active_departures=Counter()
    weighted=logistics_rules.version(state)==logistics_rules.CURRENT
    row_fields=_ROW_FIELDS | {LOSS_FIELD} if weighted else _ROW_FIELDS
    from . import transport_emergency
    for row in pool['convoys']:
        if (not isinstance(row, dict) or set(row)-{'relief','return_leg','original_eta','emergency','convoy_relief','regional','strategic'} != row_fields
                or not _int(row['id'], 1, pool['next_id'] - 1)
                or weighted and not _int(row[LOSS_FIELD],0,logistics_rules.LOSS_SCALE-1)
                or row['id'] in seen or row['owner'] not in game.catalog.factions
                or any(row[key] not in state.cities for key in ('source', 'target', 'original_target'))
                or row['status'] not in {'outbound', 'returning', 'waiting'} or row['reason'] not in _REASONS
                or not _int(row['morale'], 0, 100) or not _int(row['checked_turn'], 0, state.turn)):
            raise ValueError('Logistics convoy identity')
        if 'relief' in row:
            from . import army_relief
            if state.extension.get(logistics_strategy.FIELD)not in logistics_strategy.VERSIONS_WITH_RELIEF:
                raise ValueError('Army relief version')
            army_relief.validate(row,state)
        if 'emergency' in row:
            transport_emergency.validate_row(state,row)
        if 'convoy_relief' in row:
            from . import convoy_relief
            convoy_relief.validate(state,row,pool)
        origin=transport_capacity.origin_key(state,row['source'],row['owner'])
        origins[origin]+=1
        if origins[origin]>active_limit:
            raise ValueError('Logistics origin capacity')
        seen.add(row['id'])
        for field in ('cargo', 'initial_cargo','delivered'):
            value = row[field]
            if (not isinstance(value, dict) or set(value) != _CARGO_FIELDS
                    or any(not _int(n,0,99 if key=='treasure' else LIMIT) for key,n in value.items())):
                raise ValueError('Logistics cargo bounds')
        if (type(row['delivery_done'])is not bool or row['target_march'] is not None
                and not _int(row['target_march'],1,state.extension['travel']['counter'])
                or not isinstance(row['route_policy'],dict)
                or set(row['route_policy'])!={'allow_sea','allow_special'}
                or any(type(v)is not bool for v in row['route_policy'].values())):
            raise ValueError('Logistics mission')
        if (row['target_march'] is not None and any(row['initial_cargo'][field]
                for field in ('gold','reserves','treasure'))):
            raise ValueError('Logistics army supply cargo')
        for field in ('officers', 'original_officers'):
            ids = row[field]
            if (not isinstance(ids, list) or len(ids) > 99 or any(type(i) not in (int, str) for i in ids)
                    or len(ids) != len(set(ids)) or any(i not in state.officers for i in ids)):
                raise ValueError('Logistics officer references')
        if not row['original_officers'] or not set(row['officers']) <= set(row['original_officers']) or people.intersection(row['officers']):
            raise ValueError('Logistics duplicated officers')
        people.update(row['officers'])
        if any(not state.officers[i].alive or state.officers[i].faction_id != row['owner'] or _home(state, i) is None for i in row['officers']):
            raise ValueError('Logistics officer ownership')
        journeys = row['journeys']
        if not isinstance(journeys, list) or not 1 <= len(journeys) <= RULES['max_journeys'] or journeys[-1]['target'] != row['target']:
            raise ValueError('Logistics journeys')
        if ('return_leg' in row and (not weighted or not _int(row['return_leg'],1,len(journeys)-1))
                or 'original_eta' in row and (not winter_weather.corrected(state,winter_weather.TRANSPORT)
                    or not _int(row['original_eta'],1,state.turn+100000))):
            raise ValueError('Logistics route lifetime')
        if journeys[0]['source'] != row['source'] or journeys[0]['target'] != row['original_target']:
            raise ValueError('Logistics original journey')
        physical_enabled=transport_capacity.enforced(state,row)
        for index, journey in enumerate(journeys):
            weighted_load=physical_enabled and not transport_capacity.historical_journey(row['id'],index)
            journey_fields=_JOURNEY_FIELDS | {transport_capacity.LOAD_FIELD} if weighted_load else _JOURNEY_FIELDS
            if (not isinstance(journey, dict) or set(journey) != journey_fields
                    or any(journey[k] not in state.cities for k in ('source', 'target'))
                    or journey['mode'] not in {'land', 'fastest', 'river', 'sea', 'special', 'minimum_grain'}
                    or not _int(journey['departure_turn'], 1, state.turn)
                    or not _int(journey['departure_year'], 1, state.year)
                    or not _int(journey['departure_month'], 1, 12) or journey['departure_day'] not in {1, 11, 21}
                    or not _int(journey['arrival_turn'], journey['departure_turn'] + 1, journey['departure_turn'] + 100000)
                    or index and (journey['source'] not in journeys[index - 1]['quote']['path']
                        or journeys[index-1]['supply']['closed_tick']!=(journey['departure_turn']-1)*10)):
                raise ValueError('Logistics journey ledger')
            elapsed_days = ((state.year - journey['departure_year']) * 360
                + (state.month - journey['departure_month']) * 30 + state.day - journey['departure_day'])
            if elapsed_days != (state.turn - journey['departure_turn']) * 10:
                raise ValueError('Logistics journey date')
            quote = journey['quote']
            if (not isinstance(quote, dict) or not isinstance(quote.get('path'), list)
                    or not quote['path'] or index == 0 and len(quote['path']) < 2 and row['target_march'] is None
                        and 'convoy_relief' not in row
                    or quote['path'][0] != journey['source'] or quote['path'][-1] != journey['target']
                    or not isinstance(quote.get('routes'), list) or len(quote['path']) != len(quote['routes']) + 1):
                raise ValueError('Logistics route quote')
            if index==len(journeys)-1:
                expected_eta=(journey['supply']['clock_tick']+quote['days']-journey['supply']['route_days']+9)//10+1
                if 'winter' in journey['supply']:
                    from . import winter_travel
                    expected_eta=winter_travel.eta_turn(game,state,journey,state.turn)
                if journey['arrival_turn']!=expected_eta and not (journey['supply']['clock_tick']==journey['supply']['start_tick']
                        and journey['arrival_turn']==journey['departure_turn']+quote['turns']):
                    raise ValueError('Logistics dynamic ETA')
            from .route_network import variants, valid_departure
            routes = {r['id']: r for r in variants(game.catalog.data['travel_routes'] + game.catalog.data.get('exploration_routes', []))}
            legs = []
            for a, b, leg in zip(quote['path'], quote['path'][1:], quote['routes']):
                raw = routes.get(leg.get('id'))
                if raw is None or not route_allowed(game.catalog.data, raw, a, b) or not valid_departure(raw,game.catalog,journey['departure_year'],journey['departure_month']):
                    raise ValueError('Logistics route identity')
                if journey['mode'] == 'land' and raw['mode'] != 'land':
                    raise ValueError('Logistics land route uses water')
                legs.append(evaluate_leg(game.catalog.data, raw, a, b, journey['departure_month']))
            if journey['mode'] in {'river', 'sea'} and (len(legs) != 1 or legs[0]['mode'] != journey['mode']):
                raise ValueError('Logistics direct water route mode')
            if game._quote(quote['path'], legs) != quote:
                raise ValueError('Logistics route arithmetic')
            if weighted_load:
                load=journey[transport_capacity.LOAD_FIELD]
                cap=transport_capacity.physical(game,state,quote)['physical_capacity']
                if (not isinstance(load,dict) or set(load)!={'total','limit','policy_grain'}
                        or load['limit']!=cap or cap is not None and type(load['limit']) is not int
                        or not _int(load['total'],0,2*LIMIT)
                        or cap is not None and load['total']>cap
                        or index==0 and (not _int(load['policy_grain'],0,3*LIMIT)
                            or row['initial_cargo']['grain']>load['policy_grain']
                            or load['total']!=row['initial_cargo']['grain']+journey['supply']['loaded'])
                        or index>0 and load['policy_grain'] is not None):
                    raise ValueError('Logistics physical load')
            from .march_supply import validate as validate_supply,validate_departures
            validate_supply(journey['supply'],quote,journey['departure_turn'],state.turn,game=game,version=logistics_rules.version(state))
            validate_departures(journey['supply'],quote,returning=index>0,game=game)
            supply = journey['supply']
            manifest=journey['departure_troops']
            if (not isinstance(manifest,dict) or not set(manifest)<={str(i) for i in row['original_officers']}
                    or any(not _int(n,0,OFFICER_TROOP_CAP) for n in manifest.values())
                    or supply['troops']!=sum(manifest.values()) or supply['officers']!=len(manifest)):
                raise ValueError('Logistics departure troop snapshot')
            if (supply['officers'] > len(row['original_officers'])
                    or index == 0 and (supply['officers'] != len(row['original_officers'])
                        or supply['reserves'] != row['initial_cargo']['reserves'] or supply['from_cargo']
                        or supply.get('initial_credit',0))
                    or index>0 and 'initial_credit' in supply and
                        supply['initial_credit']!=journeys[index-1]['supply']['credit_units']
                    or index > 0 and supply['loaded']
                    or index < len(journeys)-1 and (supply['remaining'] or supply['closed_tick'] is None)
                    or index == len(journeys)-1 and (supply['returned_to_cargo'] or supply['closed_tick'] is not None)):
                raise ValueError('Logistics supply departure manifest')
            expected = game._march_risks(quote)
            risks = journey['risks']
            if not isinstance(risks, list) or len(risks) != len(expected):
                raise ValueError('Logistics risks')
            for risk, reference in zip(risks, expected):
                if not isinstance(risk, dict) or set(risk) != set(reference):
                    raise ValueError('Logistics risk fields')
                if any(risk[k] != reference[k] for k in ('legs', 'kind', 'survival_denominator')) or type(risk['applied']) is not bool:
                    raise ValueError('Logistics hazard identity')
                if risk['kind'] == 'monsoon_storm':
                    if not _int(risk['survival_numerator'], 10, 20):
                        raise ValueError('Logistics storm roll')
                elif risk['survival_numerator'] != reference['survival_numerator']:
                    raise ValueError('Logistics fixed hazard')
                if not _int(risk['lost'], 0, LIMIT) or not isinstance(risk['before'], dict) or not isinstance(risk['after'], dict):
                    raise ValueError('Logistics weather ledger')
                if not risk['applied']:
                    if risk['before'] or risk['after'] or risk['lost']:
                        raise ValueError('Logistics unapplied hazard')
                else:
                    if set(risk['before']) != set(risk['after']) or 'cargo' not in risk['before']:
                        raise ValueError('Logistics applied hazard identities')
                    keys = sorted(risk['before'], key=lambda k: (k == 'cargo', _key(next((i for i in row['original_officers'] if str(i) == k), k))))
                    if any(k != 'cargo' and k not in {str(i) for i in row['original_officers']} for k in keys):
                        raise ValueError('Logistics hazard officer snapshot')
                    before_values = [risk['before'][key] for key in keys]
                    if any(not _int(n, 0, LIMIT if key == 'cargo' else OFFICER_TROOP_CAP) for key, n in zip(keys, before_values)):
                        raise ValueError('Logistics hazard troop bounds')
                    after_values = allocate_survivors(before_values, risk['survival_numerator'], risk['survival_denominator'])
                    if any(risk['after'][key] != n for key, n in zip(keys, after_values)) or risk['lost'] != sum(before_values) - sum(after_values):
                        raise ValueError('Logistics hazard arithmetic')
        _validate_cargo(row,state,game)
        _validate_strength(row,state)
        if transport_capacity.enabled(state) and journeys[0]['departure_turn']==state.turn:
            active_departures[row['source']]+=1
    if any(n>transport_capacity.dispatch_count(state,source) for source,n in active_departures.items()):
        raise ValueError('Logistics departure count')
    if not isinstance(pool['receipts'], dict) or len(pool['receipts']) > len(state.officers) + len(state.cities):
        raise ValueError('Logistics arrival receipt bounds')
    valid_keys = {str(i) for i in state.officers} | {'city:' + k for k in state.cities}
    if any(key not in valid_keys or not _int(value, 1, state.turn + RULES['receipt_turns']) for key, value in pool['receipts'].items()):
        raise ValueError('Logistics receipt')
    if not isinstance(pool['reports'], list) or len(pool['reports']) > 100:
        raise ValueError('Logistics reports')
    for row in pool['reports']:
        if (not isinstance(row, dict) or set(row) != {'turn', 'owner', 'source', 'target', 'kind', 'details'}
                or not _int(row['turn'], 1, state.turn) or row['owner'] not in game.catalog.factions
                or row['source'] not in state.cities or row['target'] not in state.cities
                or row['kind'] not in {'transport_departed', 'transport_arrived', 'transport_returned', 'transport_weather'}
                or not isinstance(row['details'], dict)
                or set(row['details']) != ({'convoy_id','gold','grain','reserves','treasure','lost','reason'}
                                          | ({'grain_receipt'} if weighted else set()))
                or weighted and not valid_grain_receipt(row['details']['grain_receipt'])
                or not _int(row['details']['convoy_id'], 1, pool['next_id'] - 1)
                or row['details']['reason'] not in _REASONS
                or any(not _int(row['details'][field], 0, LIMIT) for field in ('gold', 'grain', 'reserves', 'lost'))
                or not _int(row['details']['treasure'],0,99)):
            raise ValueError('Logistics report')
