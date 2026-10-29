"""Real, saved convoys on the existing geographic routes.

Cargo is removed from the source at departure, counted in transit, and paid
into one friendly destination only after an actual arrival. No ROM inputs.
"""
from copy import copy, deepcopy

from .errors import GameError
from . import command_books
from .officers import parse_officer_ref
from .route_hazards import allocate_survivors, evaluate_leg, route_allowed, _python_route_allowed

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
_REASONS.update({'army_missing','army_changed','rendezvous_wait','rendezvous_missed',
                 'delivered','escort_return','retreat'})
_CARGO_KINDS = {'weather','rations','starvation','delivered','army_supply','bag_return'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


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
    return dict(owner=city.owner, policy=deepcopy(DEFAULT_POLICY), last_dispatch_turn=0)


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
    if kind not in _CARGO_KINDS or set(new_cargo) != _CARGO_FIELDS:
        raise ValueError('Logistics cargo operation')
    if any(not _int(n,0,99 if key=='treasure' else LIMIT) for key,n in new_cargo.items()):
        raise ValueError('Logistics cargo operation bounds')
    before = deepcopy(row['cargo'])
    if before == new_cargo:
        return
    row['cargo_ledger'].append(dict(kind=kind,day=day,before=before,
                                    after=deepcopy(new_cargo),reference=reference))
    row['cargo'] = deepcopy(new_cargo)


def advance_supply(game, state, row, through_turn=None, *, absolute_tick=None):
    from .march_supply import advance_unit,current_city
    cargo=deepcopy(row['cargo'])
    def changed(kind, new_cargo, day):
        _cargo_change(row,kind,new_cargo,day,dict(journey=len(row['journeys'])-1,tick=day))
        cargo.clear();cargo.update(new_cargo)
    unit=row
    if row['journeys'][-1]['supply'].get('retreat_requested') and current_city(row['journeys'][-1]) is not None:
        unit=dict(row,hold=True)
        row['journeys'][-1]['supply']['waiting']=True
    spent=advance_unit(game,state,unit,row['journeys'][-1],through_turn,
                        unit_kind='convoy',cargo=cargo,on_cargo_change=changed,
                        absolute_tick=absolute_tick)
    journey=row['journeys'][-1]
    remaining=max(0,journey['quote']['days']-journey['supply']['route_days'])
    journey['arrival_turn']=(journey['supply']['clock_tick']+remaining+9)//10+1
    if _arrived(journey):
        _apply_risks(game,state,row,tick=journey['supply']['clock_tick'])
    return spent


def _home(state, ident):
    return next((city for city in state.cities.values() if ident in city.roster.officer_ids), None)


def synchronize(game, state):
    pool = _pool(state)
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(city))
        if row['owner'] != city.owner:
            row.update(owner=city.owner, policy=deepcopy(DEFAULT_POLICY), last_dispatch_turn=0)
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


def _inbound(state, key):
    rows = [row for row in _pool(state)['convoys'] if row['target'] == key
            and row['owner'] == state.cities[key].owner and not row['delivery_done']
            and row['target_march'] is None and row['status'] != 'returning']
    return dict(**{field: sum(r['cargo'][field] for r in rows) for field in _CARGO_FIELDS},
                officers=0)


def _fronts(game, state, owner):
    found = set()
    for route in game._known_routes(state):
        for a, b in ((route['from'], route['to']), (route['to'], route['from'])):
            if (a in state.cities and b in state.cities and state.cities[a].owner == owner
                    and state.cities[b].owner not in {owner, 'neutral'}
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


def _safe_engine(game, policy):
    """Share one filtered graph across a batch without editing the catalog.

    Rejecting only its fastest answer would miss a longer safe land detour.
    Copies keep the catalog and all published geometry fingerprints unchanged.
    """
    def allowed(raw):
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
    engine = copy(game)
    engine.catalog = copy(game.catalog)
    engine.catalog.data = dict(game.catalog.data,
        travel_routes=[row for row in game.catalog.data['travel_routes'] if allowed(row)],
        exploration_routes=[row for row in game.catalog.data.get('exploration_routes', []) if allowed(row)])
    return engine


def _safe_path(game, state, source, target, owner, mode, policy):
    return _safe_engine(game,policy)._travel_path(state,source,target,owner,mode)


def _safe_quote(game, state, source, target, policy, *, quotes=None):
    choices = []
    # Ocean permission never disables a safe inland shipping route. Retain
    # the old land-only answer (and its saved mode) when no river is involved.
    for mode in ('land', 'fastest'):
        quote = (_safe_path(game,state,source.id,target.id,source.owner,mode,policy)
                 if quotes is None else quotes.get(f'{source.id}:{target.id}:{mode}'))
        if (quote is not None and mode == 'fastest' and not policy['allow_sea']
                and not any(leg['mode'] == 'river' for leg in quote['routes'])):
            continue
        if quote is not None and not _dangerous(quote, policy):
            choices.append((quote['days'], quote['distance_km'], mode, quote))
    if not choices:
        return None
    _, _, mode, quote = min(choices, key=lambda row: row[:3])
    return mode, quote


def _eligible(game, state, source):
    busy = game._march_ids(state)
    from .domestic import appointments
    offices = appointments(state, source.owner)
    assigned = {offices.get('civil'), offices.get('military')}
    return [i for i in source.roster.officer_ids if i not in busy and i not in assigned
            and state.officers[i].alive and state.officers[i].faction_id == source.owner
            and state.officers[i].health > 0
            and _pool(state)['receipts'].get(str(i), 0) <= state.turn]


def _present_count(game, state, source):
    busy = game._march_ids(state)
    return sum(state.officers[i].alive and state.officers[i].faction_id == source.owner
               and i not in busy for i in source.roster.officer_ids)


def _rations(state, quote, ids, cargo):
    from .march_supply import estimate
    return estimate(state, ids, quote, cargo['reserves'])


def _army(state, ident, owner):
    if type(ident) is not int:
        return None
    return next((row for row in state.extension['travel']['marches']
        if row['id']==ident and row['owner']==owner and row['officers']),None)


def _meeting_quote(game, state, source, army, policy):
    """A supply party walks to an actual future city, never a map coordinate."""
    progress=army['supply'].get('route_days',0)
    elapsed=0
    choices=[]
    for index,key in enumerate(army['quote']['path']):
        if index:
            elapsed+=army['quote']['routes'][index-1]['days']
        if elapsed < progress or state.cities[key].owner!=source.owner:
            continue
        if key==source.id:
            selected=('land',game._quote([key],[]))
        else:
            selected=_safe_quote(game,state,source,state.cities[key],policy)
        if selected:
            mode,quote=selected
            # Prefer a future stop the courier can reach before the column;
            # a late party must subsequently re-plan instead of remote giving.
            deadline=max(0,elapsed-progress)
            from .march_supply import current_city
            late=quote['days']>deadline
            if army['supply'].get('waiting') and current_city(army)==key:
                late=False
            choices.append((late,index,quote['days'],key,mode,quote))
    if not choices:
        return None
    _,_,_,city,mode,quote=min(choices,key=lambda r:r[:4])
    return city,mode,quote


def rescue_targets(game, state, city_id):
    from .march_supply import current_city,next_city,next_supply_days,required_grain
    source=state.cities[city_id]
    policy=_pool(state)['cities'][city_id]['policy']
    eligible=sorted(_eligible(game,state,source),key=lambda i:(-state.officers[i].profile.martial_strength,_key(i)))
    spare=max(0,_present_count(game,state,source)-policy['reserve_officers'])
    ids=eligible[:min(1,policy['max_officers'],spare)]
    result=[]
    for army in state.extension['travel']['marches']:
        if army['owner']!=source.owner or source.owner=='neutral':
            continue
        supply=army['supply']
        remaining_days=next_supply_days(state,army['quote'],army['owner'],supply.get('route_days',0))
        troops=sum(state.officers[i].troops for i in army['officers'])
        need=max(0,required_grain(troops,len(army['officers']),max(10,remaining_days))-supply['remaining'])
        row=dict(march_id=army['id'],location_city=current_city(army),next_city=next_city(army),
            city=None,target_city=army['target'],quote=None,route_mode='land',officers=list(ids),
            max_grain=0,needed_grain=need,cost_grain=0,can_dispatch=False,
            blocked_reason=None,eta_turn=None)
        reason=None
        if state.phase not in {'city','ai'}:reason='wrong_phase'
        elif source.owner not in game.catalog.factions:reason='not_owned'
        elif _army(state,army['id'],source.owner) is None:reason='army_changed'
        elif not command_books.can_spend(state,source.owner,'dispatch_transport'):reason='command_books'
        elif any(r['source']==source.id for r in _pool(state)['convoys']):reason='in_transit'
        elif not ids:reason='no_spare_officer'
        selected=None if reason else _meeting_quote(game,state,source,army,policy)
        if not reason and selected is None:reason='no_route'
        if selected:
            city,mode,quote=selected
            cost=_rations(state,quote,ids,dict(reserves=0))
            maximum=min(policy['max_grain'],max(0,source.grain-policy['reserve_grain']-cost))
            row.update(city=city,quote=deepcopy(quote),route_mode=mode,cost_grain=cost,
                       max_grain=maximum,eta_turn=state.turn+quote['turns'])
            if maximum<1:reason='insufficient_grain'
        row.update(can_dispatch=reason is None,blocked_reason=reason)
        result.append(row)
    return result


def preview(game, state, city_id):
    source, row = state.cities[city_id], _pool(state)['cities'][city_id]
    policy = row['policy']
    if source.owner == 'neutral' or source.owner not in game.catalog.factions:
        return None, 'not_owned'
    if state.phase not in {'city', 'ai'}:
        return None, 'wrong_phase'
    if not command_books.can_spend(state, source.owner, 'dispatch_transport'):
        return None, 'command_books'
    if row['last_dispatch_turn'] == state.turn:
        return None, 'already_dispatched'
    if any(c['source'] == city_id for c in _pool(state)['convoys']):
        return None, 'in_transit'
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
    ids = eligible[:min(slots, 1)]
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
    selected = _safe_quote(game, state, source, target, policy)
    if selected is None:
        return None, 'no_route'
    mode, quote = selected
    grain = _rations(state, quote, ids, cargo)
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        cargo['grain'] = max(0, source.grain - grain - policy['reserve_grain'])
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        return None, 'insufficient_grain'
    return dict(target=target.id, officers=ids, cargo=cargo, quote=deepcopy(quote),
                route_mode=mode, cost_grain=grain), None


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
    elif _pool(state)['cities'][city_id]['last_dispatch_turn'] == state.turn: common = 'already_dispatched'
    elif any(row['source'] == city_id for row in _pool(state)['convoys']): common = 'in_transit'
    elif not ids: common = 'no_spare_officer'
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
            cost = _rations(state, quote, ids, _empty_cargo())
            if source.grain-cost < policy['reserve_grain']: reason = 'insufficient_grain'
        result['targets'].append(dict(target=target.id, officers=list(ids),
            days=quote['days'] if quote else None,modes=list(quote['modes']) if quote else [],
            route_mode=mode, cost_grain=cost, max_treasure=min(99, available),
            target_treasure=_treasure_count(state, target.id),
            can_dispatch=reason is None, blocked_reason=reason))
    return result


def _event(game, state, kind, row, *, lost=0, reason='outbound',amounts=None):
    reports = _pool(state)['reports']
    values=row['cargo'] if amounts is None else amounts
    details = dict(convoy_id=row['id'], gold=values['gold'], grain=values['grain'],
                   reserves=values['reserves'], treasure=values.get('treasure',0), lost=lost, reason=reason)
    reports.append(dict(turn=state.turn, owner=row['owner'], source=row['source'], target=row['target'],
                        kind=kind, details=details))
    reports[:] = reports[-100:]
    if row['owner'] == state.player:
        ids = row['officers'][:1]
        game._emit_event(state, kind, city_ids=list(dict.fromkeys((row['source'], row['target']))),
            person_ids=[state.officers[i].person_id for i in ids], factions=[row['owner']], details=details)


def _journey(game, state, source, target, mode, quote, ids, reserves, *, from_cargo=False,initial_grain=None):
    from .march_supply import create
    return dict(source=source, target=target, mode=mode, quote=deepcopy(quote),
        departure_turn=state.turn, arrival_turn=state.turn + quote['turns'],
        departure_year=state.year, departure_month=state.month, departure_day=state.day,
        risks=game._march_risks(quote, state.rng),
        departure_troops={str(i):state.officers[i].troops for i in ids},
        supply=create(state, ids, quote, reserves, from_cargo=from_cargo,initial_grain=initial_grain))


def dispatch(game, state, payload, owner):
    if (not isinstance(payload, dict) or set(payload) - {'source', 'target', 'officers', 'cargo', 'route_mode','target_march'}
            or not isinstance(payload.get('source'), str) or not isinstance(payload.get('target'), str)
            or payload['source'] not in state.cities or payload['target'] not in state.cities):
        raise GameError('运输队参数无效。')
    source, target = state.cities[payload['source']], state.cities[payload['target']]
    target_march=payload.get('target_march')
    army=_army(state,target_march,owner) if target_march is not None else None
    if target_march is not None and army is None:
        raise GameError('请选择仍在本方行军队列中的部队。')
    if owner == 'neutral' or source.owner != owner or target.owner != owner or source.id == target.id and army is None:
        raise GameError('运输起点与目的地必须是不同的本方城池。')
    if state.phase not in {'city', 'ai'}:
        raise GameError('本城当前不能派出运输队。')
    command_books.require(state, owner, 'dispatch_transport')
    pool = _pool(state)
    policy = pool['cities'][source.id]['policy']
    if pool['cities'][source.id]['last_dispatch_turn'] == state.turn or any(r['source'] == source.id for r in pool['convoys']):
        raise GameError('本城已有在途运输队。')
    ids, cargo, mode = payload.get('officers'), payload.get('cargo'), payload.get('route_mode', 'land')
    if (not isinstance(ids, list) or not ids or len(ids) > 99
            or any(type(i) not in (int, str) for i in ids) or len(ids) != len(set(ids))
            or any(i not in _eligible(game, state, source) for i in ids)):
        raise GameError('请选择本城未出征且未担任内政官的押运武将。')
    try:
        ids = [parse_officer_ref(i, game.catalog.rules) for i in ids]
    except (ValueError, TypeError) as error:
        raise GameError('请选择本城未出征且未担任内政官的押运武将。') from error
    if (not isinstance(cargo, dict) or set(cargo) not in (_CITY_FIELDS,_CARGO_FIELDS)
            or any(not _int(value, 0, 99 if key=='treasure' else LIMIT) for key,value in cargo.items())):
        raise GameError('运输物资数量无效。')
    cargo = dict(cargo,treasure=cargo.get('treasure',0))
    if army is not None and (cargo['gold'] or cargo['reserves'] or cargo['treasure'] or not cargo['grain']):
        raise GameError('行军补给队只能运送兵粮。')
    if not isinstance(mode, str) or mode not in {'land', 'fastest', 'river', 'sea', 'special'}:
        raise GameError('请选择已知的运输路线。')
    if army is not None:
        selected=_meeting_quote(game,state,source,army,policy)
        if selected is None or selected[0]!=target.id:
            raise GameError('部队已移动，请重新选择实际会合城池。')
    quote = (game._quote([source.id],[]) if source.id==target.id else
             _safe_path(game, state, source.id, target.id, owner, mode, policy))
    if quote is None or _dangerous(quote, policy):
        raise GameError('没有符合方针的安全运输路线。')
    if _present_count(game, state, source) - len(ids) < policy['reserve_officers']:
        raise GameError('押运后未达到本城保留武将人数。')
    if any(cargo[field] > policy['max_' + field] for field in _CITY_FIELDS) or len(ids) > policy['max_officers']:
        raise GameError('运输队超过本城的单次运输上限。')
    checked_fields={'grain'} if army is not None else _CITY_FIELDS
    if any(getattr(source, field) - cargo[field] < policy['reserve_' + field] for field in checked_fields):
        raise GameError('运输后未达到本城保留物资数量。')
    grain = _rations(state, quote, ids, cargo)
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        raise GameError('运输队粮食不足，或低于本城保留量。')
    if cargo['treasure'] > _treasure_count(state,source.id):
        raise GameError('本城的宝数量不足。')
    if pool['next_id'] > 1000000:
        raise GameError('运输队编号已达上限。')
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
        journeys=[_journey(game, state, source.id, target.id, mode, quote, ids, cargo['reserves'])],
        checked_turn=0, reason='outbound',target_march=target_march,
        delivery_done=False,delivered=_empty_cargo(),cargo_ledger=[],
        route_policy={k:policy[k] for k in ('allow_sea','allow_special')})
    pool['next_id'] += 1
    pool['cities'][source.id]['last_dispatch_turn'] = state.turn
    pool['convoys'].append(row)
    _event(game, state, 'transport_departed', row)
    return row


def auto_dispatch_city(game, state, city_id):
    if not _pool(state)['cities'][city_id]['policy']['enabled']:
        return False
    from .march_supply import next_supply_days,required_grain
    rescues=[]
    for proposed in rescue_targets(game,state,city_id):
        army=_army(state,proposed['march_id'],state.cities[city_id].owner)
        if not proposed['can_dispatch'] or army is None:
            continue
        supply=army['supply']
        days=next_supply_days(state,army['quote'],army['owner'],supply.get('route_days',0))
        need=required_grain(sum(state.officers[i].troops for i in army['officers']),len(army['officers']),days)
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
    dispatch(game, state, dict(source=city_id, target=proposed['target'], officers=proposed['officers'],
        cargo=proposed['cargo'], route_mode=proposed['route_mode']), state.cities[city_id].owner)
    return True


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
        if _rations(state,quote,[*chosen,ident],dict(reserves=0))<=max(0,source.grain-policy['reserve_grain']):
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


def _dock(game, state, row, target):
    from . import domestic
    blocker=_receiving_blocker(game,state,row,target,returning=True)
    if blocker:
        row.update(status='returning',reason=blocker)
        row['journeys'][-1]['supply']['waiting']=True
        row['journeys'][-1]['supply']['retreat_requested']=True
        return False
    row['target']=target.id
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


def _unload(game, state, row, target):
    """Cargo arrives; escorts retain their home slots until the real return."""
    from . import domestic
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
    _pool(state)['receipts']['city:'+target.id]=state.turn+RULES['receipt_turns']
    _event(game,state,'transport_arrived',row,reason='delivered',amounts=cargo)


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
            if _arrived(journey):
                elapsed=0;future=False
                for index,key in enumerate(army['quote']['path']):
                    if index:elapsed+=army['quote']['routes'][index-1]['days']
                    if key==city and elapsed>=army['supply']['route_days']:future=True
                row.update(status='waiting',reason='rendezvous_wait' if future else 'rendezvous_missed')
                supply['waiting']=True
            continue
        amount=min(row['cargo']['grain'],max(0,LIMIT-army['supply']['remaining']))
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


def _begin_journey(game,state,row,here,target,mode,quote,*,status,reason):
    from .march_supply import close,receive
    if len(row['journeys'])>=RULES['max_journeys']:
        row.update(status='waiting',reason='journey_limit')
        row['journeys'][-1]['supply']['waiting']=True
        return False
    previous=row['journeys'][-1]
    remaining=previous['supply']['remaining']
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
    journey=_journey(game,state,here,target,mode,quote,row['officers'],row['cargo']['reserves'],initial_grain=0)
    row['journeys'].append(journey)
    row.update(status=status,target=target,reason=reason)
    from .march_supply import initial_days,required_grain
    need=required_grain(sum(state.officers[i].troops for i in row['officers']),len(row['officers']),
                        initial_days(state,quote,row['owner']),row['cargo']['reserves'])
    amount=min(need,row['cargo']['grain'])
    if amount:
        _cargo_change(row,'rations',dict(row['cargo'],grain=row['cargo']['grain']-amount),
            (state.turn-1)*10,dict(journey=len(row['journeys'])-1,tick=(state.turn-1)*10))
        receive(journey['supply'],amount,'cargo',row['id'],state.turn)
        need-=amount
    if need and state.cities[here].owner==row['owner']:
        amount=min(need,state.cities[here].grain)
        if amount:
            state.cities[here].grain-=amount
            receive(journey['supply'],amount,'city',here,state.turn)
            game._supply_event(state,'march_resupplied',unit_kind='convoy',unit_id=row['id'],
                city=here,owner=row['owner'],grain=amount,reason='city')
    return True


def _return(game, state, row, reason):
    from .march_supply import current_city
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
        _pool(state)['convoys'].remove(row)
        return
    choices=[]
    for city in friendly:
        additional=sum(i not in city.roster.officer_ids for i in row['officers'])
        if game._city_occupancy(state,city)+additional>game.catalog.rules.city_officer_capacity:
            continue
        if city.id==here:
            choices.append((city.id!=row['source'],0,city.id,'land',game._quote([here],[])))
            continue
        origin=copy(state.cities[here]);origin.owner=row['owner']
        selected=_safe_quote(game,state,origin,city,row['route_policy'])
        if selected:
            mode,quote=selected
            choices.append((city.id!=row['source'],quote['days'],city.id,mode,quote))
    if not choices:
        row.update(status='waiting',reason='no_return_route')
        row['journeys'][-1]['supply']['waiting']=True
        return
    _,_,target,mode,quote=min(choices,key=lambda x:x[:3])
    if not quote['days']:
        row.update(status='returning',reason=reason)
        _dock(game,state,row,state.cities[target])
        return
    if _begin_journey(game,state,row,here,target,mode,quote,status='returning',reason=reason):
        _event(game,state,'transport_returned',row,reason=reason)


def resolve_supply_retreats(game,state):
    from .march_supply import current_city
    for row in list(_pool(state)['convoys']):
        if row['journeys'][-1]['supply']['retreat_requested']:
            if current_city(row['journeys'][-1]) is not None:
                _return(game,state,row,'retreat')
            else:
                row.update(status='returning',reason='retreat')


def process_arrivals(game, state):
    from .march_supply import process_march_supply
    process_march_supply(game,state)
    synchronize(game, state)
    for row in sorted(list(_pool(state)['convoys']), key=lambda x: (x['journeys'][-1]['arrival_turn'], x['id'])):
        journey = row['journeys'][-1]
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
        blocker=_receiving_blocker(game,state,row,target,returning=row['status']=='returning')
        if blocker:
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
    return result


def _validate_cargo(row,state):
    ledger=row['cargo_ledger']
    if not isinstance(ledger,list) or len(ledger)>100000:
        raise ValueError('Logistics cargo ledger')
    cargo=deepcopy(row['initial_cargo']);delivered=_empty_cargo()
    rations={};returns={};seen_weather=set();previous_tick=-1
    for entry in ledger:
        if (not isinstance(entry,dict) or set(entry)!={'kind','day','before','after','reference'}
                or entry['kind'] not in _CARGO_KINDS or not _int(entry['day'],0,(state.turn-1)*10)
                or entry['day']<previous_tick or entry['before']!=cargo
                or not isinstance(entry['after'],dict) or set(entry['after'])!=_CARGO_FIELDS
                or any(not _int(n,0,99 if key=='treasure' else LIMIT) for key,n in entry['after'].items())):
            raise ValueError('Logistics cargo operation chain')
        previous_tick=entry['day'];after=entry['after'];reference=entry['reference'];kind=entry['kind']
        if not isinstance(reference,dict):raise ValueError('Logistics cargo operation reference')
        if kind=='weather':
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
        else:
            amount=cargo['grain']-after['grain']
            if (set(reference)!={'march','city'} or reference['march']!=row['target_march']
                    or reference['city'] not in state.cities or amount<=0
                    or after!=dict(cargo,grain=cargo['grain']-amount)):
                raise ValueError('Logistics marching army delivery')
            delivered['grain']+=amount
        cargo=deepcopy(after)
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
    if not isinstance(pool['convoys'], list) or len(pool['convoys']) > len(state.cities):
        raise ValueError('Logistics convoy bounds')
    seen, people, origins = set(), set(), set()
    for row in pool['convoys']:
        if (not isinstance(row, dict) or set(row) != _ROW_FIELDS or not _int(row['id'], 1, pool['next_id'] - 1)
                or row['id'] in seen or row['source'] in origins or row['owner'] not in game.catalog.factions
                or any(row[key] not in state.cities for key in ('source', 'target', 'original_target'))
                or row['status'] not in {'outbound', 'returning', 'waiting'} or row['reason'] not in _REASONS
                or not _int(row['morale'], 0, 100) or not _int(row['checked_turn'], 0, state.turn)):
            raise ValueError('Logistics convoy identity')
        seen.add(row['id']); origins.add(row['source'])
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
        if journeys[0]['source'] != row['source'] or journeys[0]['target'] != row['original_target']:
            raise ValueError('Logistics original journey')
        for index, journey in enumerate(journeys):
            if (not isinstance(journey, dict) or set(journey) != _JOURNEY_FIELDS
                    or any(journey[k] not in state.cities for k in ('source', 'target'))
                    or journey['mode'] not in {'land', 'fastest', 'river', 'sea', 'special'}
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
                    or quote['path'][0] != journey['source'] or quote['path'][-1] != journey['target']
                    or not isinstance(quote.get('routes'), list) or len(quote['path']) != len(quote['routes']) + 1):
                raise ValueError('Logistics route quote')
            if index==len(journeys)-1:
                expected_eta=(journey['supply']['clock_tick']+quote['days']-journey['supply']['route_days']+9)//10+1
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
            from .march_supply import validate as validate_supply,validate_departures
            validate_supply(journey['supply'],quote,journey['departure_turn'],state.turn)
            validate_departures(journey['supply'],quote,returning=index>0)
            supply = journey['supply']
            manifest=journey['departure_troops']
            if (not isinstance(manifest,dict) or not set(manifest)<={str(i) for i in row['original_officers']}
                    or any(not _int(n,0,1000) for n in manifest.values())
                    or supply['troops']!=sum(manifest.values()) or supply['officers']!=len(manifest)):
                raise ValueError('Logistics departure troop snapshot')
            if (supply['officers'] > len(row['original_officers'])
                    or index == 0 and (supply['officers'] != len(row['original_officers'])
                        or supply['reserves'] != row['initial_cargo']['reserves'] or supply['from_cargo'])
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
                    if any(not _int(n, 0, LIMIT if key == 'cargo' else 1000) for key, n in zip(keys, before_values)):
                        raise ValueError('Logistics hazard troop bounds')
                    after_values = allocate_survivors(before_values, risk['survival_numerator'], risk['survival_denominator'])
                    if any(risk['after'][key] != n for key, n in zip(keys, after_values)) or risk['lost'] != sum(before_values) - sum(after_values):
                        raise ValueError('Logistics hazard arithmetic')
        _validate_cargo(row,state)
        _validate_strength(row,state)
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
                or set(row['details']) != {'convoy_id', 'gold', 'grain', 'reserves', 'treasure', 'lost', 'reason'}
                or not _int(row['details']['convoy_id'], 1, pool['next_id'] - 1)
                or row['details']['reason'] not in _REASONS
                or any(not _int(row['details'][field], 0, LIMIT) for field in ('gold', 'grain', 'reserves', 'lost'))
                or not _int(row['details']['treasure'],0,99)):
            raise ValueError('Logistics report')
