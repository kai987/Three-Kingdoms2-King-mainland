"""Real, saved convoys on the existing geographic routes.

Cargo is removed from the source at departure, counted in transit, and paid
into one friendly destination only after an actual arrival. No ROM inputs.
"""
from copy import copy, deepcopy

from .errors import GameError
from .officers import parse_officer_ref
from .route_hazards import allocate_survivors, evaluate_leg, route_allowed, _python_route_allowed

SCHEMA = 'tk2-logistics-v1'
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
               'journeys', 'checked_turn', 'reason'}
_JOURNEY_FIELDS = {'source', 'target', 'quote', 'mode', 'departure_turn', 'arrival_turn',
                   'departure_year', 'departure_month', 'departure_day', 'risks'}
_CARGO_FIELDS = {'gold', 'grain', 'reserves'}
_REASONS = {'outbound', 'arrived', 'returned', 'target_changed', 'route_blocked',
            'origin_changed', 'no_friendly_city', 'no_return_route', 'city_full',
            'resource_full', 'weather', 'waiting', 'journey_limit'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


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
    return any(row['journeys'][-1]['arrival_turn'] <= state.turn and row['checked_turn'] != state.turn
               for row in state.extension.get('logistics', {}).get('convoys', []))


def _home(state, ident):
    return next((city for city in state.cities.values() if ident in city.roster.officer_ids), None)


def synchronize(game, state):
    pool = _pool(state)
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(city))
        if row['owner'] != city.owner:
            row.update(owner=city.owner, policy=deepcopy(DEFAULT_POLICY), last_dispatch_turn=0)
    for row in list(pool['convoys']):
        row['officers'] = [i for i in row['officers'] if i in state.officers and state.officers[i].alive
            and state.officers[i].faction_id == row['owner'] and _home(state, i) is not None]
        if not any(c.owner == row['owner'] for c in state.cities.values()):
            lost = row['cargo']['reserves']
            state.soldiers['lost'] += lost
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
            and row['owner'] == state.cities[key].owner]
    return dict(**{field: sum(r['cargo'][field] for r in rows) for field in _CARGO_FIELDS},
                officers=sum(len(r['officers']) for r in rows))


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


def _safe_path(game, state, source, target, owner, mode, policy):
    """Reuse the existing path engine after removing disallowed known edges.

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
    return engine._travel_path(state, source, target, owner, mode)


def _safe_quote(game, state, source, target, policy):
    choices = []
    for mode in (('land', 'fastest') if policy['allow_sea'] else ('land',)):
        quote = _safe_path(game, state, source.id, target.id, source.owner, mode, policy)
        if quote is not None and not _dangerous(quote, policy):
            choices.append((quote['days'], quote['distance_km'], mode, quote))
    if not choices:
        return None
    _, _, mode, quote = min(choices, key=lambda row: row[:3])
    return mode, quote


def _eligible(game, state, source):
    busy = game._march_ids(state)
    domestic = state.extension.get('domestic', {}).get('cities', {}).get(source.id, {})
    assigned = {domestic.get('civil'), domestic.get('military')}
    return [i for i in source.roster.officer_ids if i not in busy and i not in assigned
            and state.officers[i].alive and state.officers[i].faction_id == source.owner
            and state.officers[i].health > 0
            and state.extension['officer_actions'].get(str(i)) != state.turn
            and _pool(state)['receipts'].get(str(i), 0) <= state.turn]


def _present_count(game, state, source):
    busy = game._march_ids(state)
    return sum(state.officers[i].alive and state.officers[i].faction_id == source.owner
               and i not in busy for i in source.roster.officer_ids)


def _rations(quote, ids, cargo):
    return len(ids) * quote['grain_per_officer'] + (cargo['reserves'] * quote['days'] + 999) // 1000


def preview(game, state, city_id):
    source, row = state.cities[city_id], _pool(state)['cities'][city_id]
    policy = row['policy']
    if source.owner == 'neutral' or source.owner not in game.catalog.factions:
        return None, 'not_owned'
    if state.phase not in {'city', 'ai'}:
        return None, 'wrong_phase'
    if source.action_used:
        return None, 'action_used'
    if row['last_dispatch_turn'] == state.turn:
        return None, 'already_dispatched'
    if any(c['source'] == city_id for c in _pool(state)['convoys']):
        return None, 'in_transit'
    if any(getattr(source, field) < policy['reserve_' + field] for field in _CARGO_FIELDS):
        return None, 'insufficient_resources'
    target = _target(game, state, source, policy)
    if target is None or target.id == city_id:
        return None, 'no_target'
    if target.owner != source.owner:
        return None, 'no_friendly_target'
    inbound = _inbound(state, target.id)
    room = game.catalog.rules.city_officer_capacity - game._city_occupancy(state, target) - inbound['officers']
    if room < 1:
        return None, 'target_full'
    eligible = sorted(_eligible(game, state, source), key=lambda i: (
        -state.officers[i].profile.martial_strength, -state.officers[i].profile.intellect, _key(i)))
    retained = max(policy['reserve_officers'], sum(x is not None for x in (
        state.extension.get('domestic', {}).get('cities', {}).get(city_id, {}).get('civil'),
        state.extension.get('domestic', {}).get('cities', {}).get(city_id, {}).get('military'))))
    slots = min(room, policy['max_officers'], max(0, _present_count(game, state, source) - retained))
    wanted = max(1, policy['target_officers'] - game._city_occupancy(state, target) - inbound['officers'])
    ids = eligible[:min(slots, wanted)]
    if not ids:
        return None, 'no_spare_officer'
    cargo = {field: min(policy['max_' + field], max(0, getattr(source, field) - policy['reserve_' + field]),
                        max(0, policy['target_' + field] - getattr(target, field) - inbound[field]))
             for field in _CARGO_FIELDS}
    # A recently received city does not immediately bounce those resources on.
    if _pool(state)['receipts'].get('city:' + city_id, 0) > state.turn:
        cargo = dict(gold=0, grain=0, reserves=0)
    need_people = game._city_occupancy(state, target) + inbound['officers'] < policy['target_officers']
    if not any(cargo.values()) and not need_people:
        return None, 'no_surplus'
    selected = _safe_quote(game, state, source, target, policy)
    if selected is None:
        return None, 'no_route'
    mode, quote = selected
    grain = _rations(quote, ids, cargo)
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        cargo['grain'] = max(0, source.grain - grain - policy['reserve_grain'])
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        return None, 'insufficient_grain'
    return dict(target=target.id, officers=ids, cargo=cargo, quote=deepcopy(quote),
                route_mode=mode, cost_grain=grain), None


def _event(game, state, kind, row, *, lost=0, reason='outbound'):
    reports = _pool(state)['reports']
    details = dict(convoy_id=row['id'], gold=row['cargo']['gold'], grain=row['cargo']['grain'],
                   reserves=row['cargo']['reserves'], lost=lost, reason=reason)
    reports.append(dict(turn=state.turn, owner=row['owner'], source=row['source'], target=row['target'],
                        kind=kind, details=details))
    reports[:] = reports[-100:]
    if row['owner'] == state.player:
        ids = row['officers'][:1]
        game._emit_event(state, kind, city_ids=list(dict.fromkeys((row['source'], row['target']))),
            person_ids=[state.officers[i].person_id for i in ids], factions=[row['owner']], details=details)


def _journey(game, state, source, target, mode, quote):
    return dict(source=source, target=target, mode=mode, quote=deepcopy(quote),
        departure_turn=state.turn, arrival_turn=state.turn + quote['turns'],
        departure_year=state.year, departure_month=state.month, departure_day=state.day,
        risks=game._march_risks(quote, state.rng))


def dispatch(game, state, payload, owner):
    if (not isinstance(payload, dict) or set(payload) - {'source', 'target', 'officers', 'cargo', 'route_mode'}
            or not isinstance(payload.get('source'), str) or not isinstance(payload.get('target'), str)
            or payload['source'] not in state.cities or payload['target'] not in state.cities):
        raise GameError('运输队参数无效。')
    source, target = state.cities[payload['source']], state.cities[payload['target']]
    if owner == 'neutral' or source.owner != owner or target.owner != owner or source.id == target.id:
        raise GameError('运输起点与目的地必须是不同的本方城池。')
    if state.phase not in {'city', 'ai'} or source.action_used:
        raise GameError('本城当前不能派出运输队。')
    pool = _pool(state)
    policy = pool['cities'][source.id]['policy']
    if pool['cities'][source.id]['last_dispatch_turn'] == state.turn or any(r['source'] == source.id for r in pool['convoys']):
        raise GameError('本城已有在途运输队。')
    ids, cargo, mode = payload.get('officers'), payload.get('cargo'), payload.get('route_mode', 'land')
    if (not isinstance(ids, list) or not ids or len(ids) > 99
            or any(type(i) not in (int, str) for i in ids) or len(ids) != len(set(ids))
            or any(i not in _eligible(game, state, source) for i in ids)):
        raise GameError('请选择本城未行动、未出征且未担任内政官的押运武将。')
    try:
        ids = [parse_officer_ref(i, game.catalog.rules) for i in ids]
    except (ValueError, TypeError) as error:
        raise GameError('请选择本城未行动、未出征且未担任内政官的押运武将。') from error
    if (not isinstance(cargo, dict) or set(cargo) != _CARGO_FIELDS
            or any(not _int(value, 0, LIMIT) for value in cargo.values())):
        raise GameError('运输物资数量无效。')
    if not isinstance(mode, str) or mode not in {'land', 'fastest', 'sea', 'special'}:
        raise GameError('请选择已知的运输路线。')
    quote = _safe_path(game, state, source.id, target.id, owner, mode, policy)
    if quote is None or _dangerous(quote, policy):
        raise GameError('没有符合方针的安全运输路线。')
    inbound = _inbound(state, target.id)
    if game._city_occupancy(state, target) + inbound['officers'] + len(ids) > game.catalog.rules.city_officer_capacity:
        raise GameError('目的城没有足够的武将名额。')
    if _present_count(game, state, source) - len(ids) < policy['reserve_officers']:
        raise GameError('押运后未达到本城保留武将人数。')
    if any(cargo[field] > policy['max_' + field] for field in _CARGO_FIELDS) or len(ids) > policy['max_officers']:
        raise GameError('运输队超过本城的单次运输上限。')
    if any(getattr(source, field) - cargo[field] < policy['reserve_' + field] for field in _CARGO_FIELDS):
        raise GameError('运输后未达到本城保留物资数量。')
    grain = _rations(quote, ids, cargo)
    if source.grain - cargo['grain'] - grain < policy['reserve_grain']:
        raise GameError('运输队粮食不足，或低于本城保留量。')
    if pool['next_id'] > 1000000:
        raise GameError('运输队编号已达上限。')
    for field in _CARGO_FIELDS:
        setattr(source, field, getattr(source, field) - cargo[field])
    source.grain -= grain
    source.action_used = True
    state.extension['officer_actions'].update({str(i): state.turn for i in ids})
    from . import domestic
    domestic.on_departure(game, state, ids, source.id)
    row = dict(id=pool['next_id'], owner=owner, source=source.id, target=target.id,
        original_target=target.id, officers=list(ids), original_officers=list(ids), cargo=deepcopy(cargo),
        initial_cargo=deepcopy(cargo), morale=domestic.morale(state, source.id), status='outbound',
        journeys=[_journey(game, state, source.id, target.id, mode, quote)], checked_turn=0, reason='outbound')
    pool['next_id'] += 1
    pool['cities'][source.id]['last_dispatch_turn'] = state.turn
    pool['convoys'].append(row)
    _event(game, state, 'transport_departed', row)
    return row


def auto_dispatch_city(game, state, city_id):
    if not _pool(state)['cities'][city_id]['policy']['enabled']:
        return False
    proposed, reason = preview(game, state, city_id)
    if reason:
        return False
    dispatch(game, state, dict(source=city_id, target=proposed['target'], officers=proposed['officers'],
        cargo=proposed['cargo'], route_mode=proposed['route_mode']), state.cities[city_id].owner)
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


def _apply_risks(game, state, row):
    journey = row['journeys'][-1]
    ids = sorted(row['officers'], key=_key)
    for risk in journey['risks']:
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
        row['cargo']['reserves'] = after[-1]
        for field in ('gold', 'grain'):
            row['cargo'][field] = row['cargo'][field] * risk['survival_numerator'] // risk['survival_denominator']
        state.soldiers['lost'] += risk['lost']
        _event(game, state, 'transport_weather', row, lost=risk['lost'], reason='weather')


def _finish(game, state, row, target):
    from . import domestic
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
    domestic.add_reserves(game, state, target, row['cargo']['reserves'], row['morale'])
    _pool(state)['receipts']['city:' + target.id] = state.turn + RULES['receipt_turns']
    kind = 'transport_returned' if row['status'] == 'returning' else 'transport_arrived'
    _event(game, state, kind, row, reason='returned' if kind == 'transport_returned' else 'arrived')


def _return(game, state, row, reason):
    current = row['journeys'][-1]
    here = current['target']
    if reason == 'route_blocked':
        path = current['quote']['path']
        blocked = next((index for index, key in enumerate(path[1:-1], 1)
                        if state.cities[key].owner not in {row['owner'], 'neutral'}), None)
        if blocked is not None:
            here = path[blocked - 1]
    friendly = [city for city in state.cities.values() if city.owner == row['owner']]
    if not friendly:
        lost = row['cargo']['reserves']
        state.soldiers['lost'] += lost
        _event(game, state, 'transport_returned', row, lost=lost, reason='no_friendly_city')
        _pool(state)['convoys'].remove(row)
        return
    choices = []
    # Return to the original city when possible, then the nearest safe reserve.
    for city in friendly:
        if city.id == here:
            choices.append((city.id != row['source'], 0, city.id, 'land', game._quote([here], [])))
            continue
        quote = _safe_path(game, state, here, city.id, row['owner'], 'land',
                           dict(allow_sea=False, allow_special=False))
        if quote is not None and not any(leg.get('hazard') for leg in quote['routes']):
            choices.append((city.id != row['source'], quote['days'], city.id, 'land', quote))
    if not choices or len(row['journeys']) >= RULES['max_journeys']:
        row.update(status='waiting', reason='no_return_route' if not choices else 'journey_limit')
        return
    _, _, target, mode, quote = min(choices, key=lambda x: x[:3])
    row.update(status='returning', target=target, reason=reason)
    row['journeys'].append(_journey(game, state, here, target, mode, quote))
    _event(game, state, 'transport_returned', row, reason=reason)


def process_arrivals(game, state):
    synchronize(game, state)
    for row in sorted(list(_pool(state)['convoys']), key=lambda x: (x['journeys'][-1]['arrival_turn'], x['id'])):
        journey = row['journeys'][-1]
        if journey['arrival_turn'] > state.turn or row['checked_turn'] == state.turn:
            continue
        row['checked_turn'] = state.turn
        _apply_risks(game, state, row)
        target = state.cities[row['target']]
        if target.owner != row['owner']:
            _return(game, state, row, 'target_changed')
            continue
        if any(state.cities[key].owner not in {row['owner'], 'neutral'} for key in journey['quote']['path'][1:-1]):
            _return(game, state, row, 'route_blocked')
            continue
        additional = sum(i not in target.roster.officer_ids for i in row['officers'])
        if game._city_occupancy(state, target) + additional > game.catalog.rules.city_officer_capacity:
            row.update(status='waiting', reason='city_full')
            continue
        if any(getattr(target, field) + row['cargo'][field] > LIMIT for field in _CARGO_FIELDS):
            row.update(status='waiting', reason='resource_full')
            continue
        _finish(game, state, row, target)


def view(game, state):
    result = dict(rules=deepcopy(RULES), cities={}, convoys=[], marching_officers=[], reports=[])
    if state is None or 'logistics' not in state.extension:
        return result
    pool = _pool(state)
    result['convoys'] = deepcopy(pool['convoys'])
    result['marching_officers'] = sorted(marching_ids(state), key=_key)
    result['reports'] = deepcopy([row for row in pool['reports'] if row['owner'] == state.player])
    for key, city in state.cities.items():
        policy = pool['cities'][key]['policy']
        proposed, reason = (preview(game, state, key) if city.owner == state.player and policy['enabled']
                            else (None, 'disabled' if city.owner == state.player else 'not_owned'))
        result['cities'][key] = dict(owner=city.owner, policy=deepcopy(pool['cities'][key]['policy']),
            inbound=_inbound(state, key), can_dispatch=reason is None and city.owner == state.player,
            blocked_reason='not_owned' if city.owner != state.player else reason, preview=proposed)
    return result


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
        for field in ('cargo', 'initial_cargo'):
            value = row[field]
            if not isinstance(value, dict) or set(value) != _CARGO_FIELDS or any(not _int(n, 0, LIMIT) for n in value.values()):
                raise ValueError('Logistics cargo bounds')
        if any(row['cargo'][field] > row['initial_cargo'][field] for field in _CARGO_FIELDS):
            raise ValueError('Logistics cargo creation')
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
                    or journey['mode'] not in {'land', 'fastest', 'sea', 'special'}
                    or not _int(journey['departure_turn'], 1, state.turn)
                    or not _int(journey['departure_year'], 1, state.year)
                    or not _int(journey['departure_month'], 1, 12) or journey['departure_day'] not in {1, 11, 21}
                    or not _int(journey['arrival_turn'], journey['departure_turn'] + 1, journey['departure_turn'] + 100000)
                    or index and (journey['source'] not in journeys[index - 1]['quote']['path']
                        or journey['departure_turn'] < journeys[index - 1]['arrival_turn'])):
                raise ValueError('Logistics journey ledger')
            elapsed_days = ((state.year - journey['departure_year']) * 360
                + (state.month - journey['departure_month']) * 30 + state.day - journey['departure_day'])
            if elapsed_days != (state.turn - journey['departure_turn']) * 10:
                raise ValueError('Logistics journey date')
            quote = journey['quote']
            if (not isinstance(quote, dict) or not isinstance(quote.get('path'), list)
                    or not quote['path'] or index == 0 and len(quote['path']) < 2
                    or quote['path'][0] != journey['source'] or quote['path'][-1] != journey['target']
                    or not isinstance(quote.get('routes'), list) or len(quote['path']) != len(quote['routes']) + 1
                    or journey['arrival_turn'] != journey['departure_turn'] + quote['turns']):
                raise ValueError('Logistics route quote')
            routes = {r['id']: r for r in game.catalog.data['travel_routes'] + game.catalog.data.get('exploration_routes', [])}
            legs = []
            for a, b, leg in zip(quote['path'], quote['path'][1:], quote['routes']):
                raw = routes.get(leg.get('id'))
                if raw is None or not route_allowed(game.catalog.data, raw, a, b):
                    raise ValueError('Logistics route identity')
                legs.append(evaluate_leg(game.catalog.data, raw, a, b, journey['departure_month']))
            if game._quote(quote['path'], legs) != quote:
                raise ValueError('Logistics route arithmetic')
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
                    if risk['before'] or risk['after'] or risk['lost'] or index < len(journeys) - 1:
                        raise ValueError('Logistics unapplied hazard')
                else:
                    if set(risk['before']) != set(risk['after']) or 'cargo' not in risk['before']:
                        raise ValueError('Logistics applied hazard identities')
                    keys = sorted(risk['before'], key=lambda k: (k == 'cargo', _key(next((i for i in row['original_officers'] if str(i) == k), k))))
                    if any(k != 'cargo' and k not in {str(i) for i in row['original_officers']} for k in keys):
                        raise ValueError('Logistics hazard officer snapshot')
                    before_values = [risk['before'][key] for key in keys]
                    if any(not _int(n, 0, LIMIT if key == 'cargo' else 999) for key, n in zip(keys, before_values)):
                        raise ValueError('Logistics hazard troop bounds')
                    after_values = allocate_survivors(before_values, risk['survival_numerator'], risk['survival_denominator'])
                    if any(risk['after'][key] != n for key, n in zip(keys, after_values)) or risk['lost'] != sum(before_values) - sum(after_values):
                        raise ValueError('Logistics hazard arithmetic')
        cargo = deepcopy(row['initial_cargo'])
        for journey in journeys:
            for risk in journey['risks']:
                if risk['applied']:
                    if risk['before']['cargo'] != cargo['reserves']:
                        raise ValueError('Logistics cargo hazard chain')
                    cargo['reserves'] = risk['after']['cargo']
                    for field in ('gold', 'grain'):
                        cargo[field] = cargo[field] * risk['survival_numerator'] // risk['survival_denominator']
        if row['cargo'] != cargo:
            raise ValueError('Logistics cargo hazard balance')
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
                or set(row['details']) != {'convoy_id', 'gold', 'grain', 'reserves', 'lost', 'reason'}
                or not _int(row['details']['convoy_id'], 1, pool['next_id'] - 1)
                or row['details']['reason'] not in _REASONS
                or any(not _int(row['details'][field], 0, LIMIT) for field in ('gold', 'grain', 'reserves', 'lost'))):
            raise ValueError('Logistics report')
