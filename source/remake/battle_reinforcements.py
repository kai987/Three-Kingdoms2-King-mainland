"""Dispatch local reserves on the tactical clock and return unfinished columns."""

from . import command_books, historical_campaigns, march_supply
from .errors import GameError
from .officers import integer, ref_sort_key
from .route_hazards import evaluate_leg, route_allowed


FIELD = 'reinforcements'
RETURNS = 'battle_reinforcement_returns'
SIDES = ('attackers', 'defenders')
DAYS = 30
ORDER_FIELDS = {'side', 'source', 'owner', 'officers', 'route', 'departed', 'days', 'grain'}


def joined(battle):
    return battle['extended'].get(FIELD, {}).get('joined', {})


def _pending(battle):
    return battle['extended'].get(FIELD, {}).get('pending', [])


def _side_owners(battle):
    attacking = set(battle['extended'].get('coalition', {}).get('provisions', ()))
    return (attacking or {battle['attacker']}), {battle['defender']}


def side_for(state, battle, owner):
    attackers, defenders = _side_owners(battle)
    if owner in attackers:
        return 'attackers'
    if owner in defenders:
        return 'defenders'
    allied_to = [any(historical_campaigns.allied(state, owner, faction) for faction in group)
                 for group in (attackers, defenders)]
    if owner != 'neutral' and allied_to.count(True) == 1:
        return SIDES[allied_to.index(True)]
    return None


def supporting_side(battle):
    return battle['extended'].get(FIELD, {}).get('supporting')


def offer_support(game, state, battle):
    """Pause an otherwise automatic battle for a player who can send aid."""
    side = side_for(state, battle, state.player)
    if (state.phase != 'battle' or side is None
            or any(state.player in group for group in _side_owners(battle))):
        return False
    routes = {source: legs for source, legs in _sources(game, state, battle).items()
              if state.cities[source].owner == state.player}
    if not any(_cost(state, [ident], 2 * leg['days']) <= city.grain
               for city, _, legs, officers in _eligible(game, state, battle, routes)
               for leg in legs for ident in officers):
        return False
    battle['extended'][FIELD] = dict(pending=[], joined={}, supporting=side)
    return True


def _can_decline(state, battle):
    return (supporting_side(battle) is not None
            and not any(row['owner'] == state.player for rows in (_pending(battle), joined(battle).values())
                        for row in rows))


def decline_support(game, state, payload):
    battle = state.battle
    if (state.phase != 'battle' or not battle or payload != {'battle_id': battle['id']}
            or not _can_decline(state, battle) or battle['extended']['duel'] or battle['extended'].get('siege')):
        raise GameError('目前無法取消增援。')
    del battle['extended'][FIELD]['supporting']
    game._resolve_ai_battle(state)


def marching_ids(state):
    battle = getattr(state, 'battle', None)
    pending = _pending(battle) if battle else ()
    returning = state.extension.get(RETURNS, ())
    return {ident for rows in (pending, returning) for row in rows for ident in row['officers']
            if state.officers[ident].alive and state.officers[ident].faction_id == row['owner']}


def _remaining(game, battle, side):
    dispatched = sum(len(row['officers']) for row in _pending(battle) if row['side'] == side)
    entered = sum(row['side'] == side for row in joined(battle).values())
    return game.catalog.rules.battle_officers_per_side - dispatched - entered


def _sources(game, state, battle):
    """Resolve each adjacent directional route once for this quote or AI phase."""
    target = battle['target']
    routes = {}
    for raw in game._known_routes(state):
        if target not in (raw['from'], raw['to']):
            continue
        source = raw['to'] if raw['from'] == target else raw['from']
        if source in state.cities and route_allowed(game.catalog.data, raw, source, target):
            leg = evaluate_leg(game.catalog.data, raw, source, target, state.month)
            if leg['days'] > 0:
                routes.setdefault(source, []).append(leg)
    return routes


def _eligible(game, state, battle, battle_routes):
    unavailable = game._march_ids(state) | {
        unit['id'] for side in SIDES for unit in battle[side]}
    pending = state.extension.get('pending_succession', {})
    for source, legs in sorted(battle_routes.items()):
        city = state.cities[source]
        if (city.owner in pending or not command_books.can_spend(state, city.owner, 'depart')
                or not (side := side_for(state, battle, city.owner))):
            continue
        routes = [leg for leg in legs if battle['round'] + leg['days'] <= DAYS]
        if not routes:
            continue
        officers = [ident for ident in city.roster.officer_ids if ident not in unavailable
                    and state.officers[ident].alive and state.officers[ident].health > 0
                    and state.officers[ident].troops > 0 and state.officers[ident].faction_id == city.owner]
        if officers:
            yield city, side, routes, officers


def _order(state, battle, city, side, leg, officers, *, grain):
    command_books.spend(state, city, 'depart')
    city.grain -= grain
    state.extension['officer_actions'].update({str(ident): state.turn for ident in officers})
    data = battle['extended'].setdefault(FIELD, dict(pending=[], joined={}))
    data['pending'].append(dict(side=side, source=city.id, owner=city.owner, officers=list(officers),
                                route=leg['id'], days=leg['days'], departed=battle['round'], grain=grain))


def _cost(state, officers, days):
    return march_supply.cost(sum(state.officers[ident].troops for ident in officers), len(officers), days)


def dispatch(game, state, payload):
    from . import battle_grid, battle_placement
    from .officers import parse_officer_ref

    battle = state.battle
    if (set(payload) != {'battle_id', 'source', 'route', 'officers'} or state.phase != 'battle'
            or not battle or payload['battle_id'] != battle['id'] or battle_placement.pending(battle)
            or battle['extended']['duel'] or battle['extended'].get('siege')
            or battle_grid.player_side(state, battle) != battle['extended']['tactical']['side']
            or not isinstance(payload['source'], str) or not isinstance(payload['route'], str)
            or not isinstance(payload['officers'], list)):
        raise GameError('目前無法調派戰場援軍。')
    ids = [parse_officer_ref(ident, game.catalog.rules) for ident in payload['officers']]
    for city, side, routes, officers in _eligible(game, state, battle, _sources(game, state, battle)):
        if city.id != payload['source'] or city.owner != state.player:
            continue
        leg = next((leg for leg in routes if leg['id'] == payload['route']), None)
        if (leg is None or not 1 <= len(ids) <= _remaining(game, battle, side)
                or len(set(ids)) != len(ids) or not set(ids) <= set(officers)):
            break
        grain = _cost(state, ids, 2 * leg['days'])
        if grain > city.grain:
            raise GameError('本城糧不足，無法備妥援軍往返口糧。')
        _order(state, battle, city, side, leg, ids, grain=grain)
        return
    raise GameError('援軍路線、武將或名額已失效。')


def auto_dispatch(game, state, battle, side):
    """Give each computer faction one opportunity to reinforce this battle."""
    if not game.catalog.data['rules'].get('ai_max_attacks_per_turn', 1) or _remaining(game, battle, side) <= 0:
        return
    sent = {row['owner'] for row in _pending(battle)} | {row['owner'] for row in joined(battle).values()}
    choices = {}
    leaders = set(state.extension['leaders'].values())
    for city, eligible_side, legs, officers in _eligible(game, state, battle, _sources(game, state, battle)):
        if eligible_side != side or city.owner == state.player or city.owner in sent:
            continue
        leg = min(legs, key=lambda route: (route['days'], route['distance_km'], route['id']))
        officers = sorted((i for i in officers if i not in leaders),
                          key=lambda i: (-state.officers[i].troops, ref_sort_key(i)))
        if officers:
            options = choices.setdefault(city.owner, [])
            options.append((leg['days'], -state.officers[officers[0]].troops, city.id, city, leg, officers))
    for owner in sorted(choices):
        limit = min(2, _remaining(game, battle, side))
        if limit <= 0:
            break
        for _, _, _, city, leg, officers in sorted(choices[owner]):
            ids = []
            for ident in officers:
                if _cost(state, [*ids, ident], 2 * leg['days']) <= city.grain:
                    ids.append(ident)
                    if len(ids) == limit:
                        break
            if ids:
                _order(state, battle, city, side, leg, ids, grain=_cost(state, ids, 2 * leg['days']))
                break


def _entry_cells(game, battle, source):
    from . import battle_grid
    field = battle_grid._field(battle)
    sx, sy = game.catalog.map_cities[source]['position']
    tx, ty = game.catalog.map_cities[battle['target']]['position']
    unit_map = {str(unit['id']): unit for side in SIDES for unit in battle[side]}
    occupied = {(p['x'], p['y']) for ident, p in battle['extended']['tactical']['positions'].items()
                if battle_grid._live(battle, unit_map[ident])}
    if abs(sx - tx) >= abs(sy - ty):
        anchor = (0 if sx < tx else battle_grid.COLUMNS - 1, battle_grid.ROWS // 2)
    else:
        anchor = (battle_grid.COLUMNS // 2, 0 if sy < ty else battle_grid.ROWS - 1)
    return sorted(((x, y) for y, tiles in enumerate(field['classes']) for x, tile in enumerate(tiles)
                   if tile in (0, 1, 2, 5) and (x, y) not in occupied and (x, y) != tuple(field['camp'])),
                  key=lambda cell: (abs(cell[0] - anchor[0]) + abs(cell[1] - anchor[1]), cell[1], cell[0]))


def arrive(game, state, battle):
    """Commit arrivals once, after a full battlefield day and only if still fighting."""
    from . import battle_experience, battle_supply, domestic
    pending = _pending(battle)
    entries = joined(battle)
    for row in pending[:]:
        if battle['round'] < row['departed'] + row['days']:
            continue
        side, source, ids = row['side'], row['source'], row['officers']
        cells = _entry_cells(game, battle, source)
        if len(cells) < len(ids):
            continue
        tactical = battle['extended']['tactical']
        for ident, (x, y) in zip(ids, cells):
            officer = state.officers[ident]
            key = str(ident)
            entries[key] = dict(side=side, home=source, owner=row['owner'])
            battle[side].append(dict(id=ident, troops=officer.troops, start=officer.troops,
                                     martial=officer.profile.martial_strength))
            battle_experience.arrive(battle, side, battle[side][-1])
            tactical['positions'][key] = dict(x=x, y=y)
            battle['extended']['support'][key] = dict(health=officer.health, energy=18, stunned=0, guard=0,
                                                      morale=domestic.unit_morale(game, state, ident))
            order = battle['extended'].get('conditions', {}).get('high_order')
            if order is not None:
                order.append(key)
        provisions = row['grain'] - _cost(state, ids, row['days'])
        battle_supply.receive_reinforcements(state, battle, side, provisions, row['owner'])
        pending.remove(row)
        battle['log'].append(f'{game.catalog.map_cities[source]["name"]}援軍{len(ids)}名武將已抵達戰場。')


def withdraw(state, battle):
    """Reverse the distance actually covered, retaining the original home roster."""
    for row in _pending(battle):
        travelled = min(row['days'], battle['round'] - row['departed'])
        grain = row['grain'] - _cost(state, row['officers'], 2 * travelled)
        if travelled:
            state.extension.setdefault(RETURNS, []).append(dict(
                source=row['source'], target=battle['target'], owner=row['owner'], officers=row['officers'],
                route=row['route'], remaining=travelled, grain=grain))
        else:
            city = state.cities[row['source']]
            city.grain = min(march_supply.LIMIT, city.grain + grain)


def advance_returns(game, state):
    """Returning reinforcements travel on the strategic clock after battle."""
    returning = state.extension.get(RETURNS)
    if not returning:
        return
    for row in returning[:]:
        row['remaining'] -= 10
        if row['remaining'] > 0:
            continue
        city = state.cities[row['source']]
        if city.owner == row['owner']:
            city.grain = min(march_supply.LIMIT, city.grain + row['grain'])
            if city.owner == state.player:
                game._note(state, f'援軍已沿原路返回{game.catalog.map_cities[city.id]["name"]}。')
        returning.remove(row)
    if not returning:
        del state.extension[RETURNS]


def view(game, state, battle):
    from . import battle_grid, battle_placement
    if not battle or state.phase != 'battle' or battle_placement.pending(battle):
        return None
    side = battle_grid.player_side(state, battle)
    if side is None:
        return None
    pending = [dict(row, officers=list(row['officers']), arrival=row['departed'] + row['days']) for row in _pending(battle)
               if row['side'] == side]
    remaining = _remaining(game, battle, side)
    options = []
    if (remaining > 0 and battle['extended']['tactical']['side'] == side
            and not battle['extended']['duel'] and not battle['extended'].get('siege')):
        owners_routes = {key: legs for key, legs in _sources(game, state, battle).items()
                         if state.cities[key].owner == state.player}
        for city, _, legs, officers in _eligible(game, state, battle, owners_routes):
            options.append(dict(city=city.id, grain=city.grain, officers=officers,
                routes=[dict(id=leg['id'], mode=leg['mode'], days=leg['days'],
                             arrival=battle['round'] + leg['days']) for leg in sorted(legs, key=lambda leg: leg['days'])]))
    return dict(pending=pending, remaining=remaining, sources=options, denominator=march_supply.denominator(),
                supporting=supporting_side(battle) is not None, can_decline=_can_decline(state, battle))


def validate(game, state, battle):
    if FIELD not in battle['extended']:
        return
    data = battle['extended'][FIELD]
    if (not isinstance(data, dict) or set(data) - {'supporting'} != {'pending', 'joined'}
            or not isinstance(data['pending'], list) or not isinstance(data['joined'], dict)):
        raise ValueError('Battle reinforcement fields')
    if 'supporting' in data and (data['supporting'] not in SIDES
            or data['supporting'] != side_for(state, battle, state.player)
            or any(state.player in group for group in _side_owners(battle))):
        raise ValueError('Battle reinforcement player side')
    if min(_remaining(game, battle, side) for side in SIDES) < 0:
        raise ValueError('Battle reinforcement capacity')
    deployed = {str(unit['id']): (unit['id'], side) for side in SIDES for unit in battle[side]}
    defections = battle['extended'].get('defections', {})
    for key, row in data['joined'].items():
        if (key not in deployed or set(row) != {'side', 'home', 'owner'} or row['side'] not in SIDES
                or row['home'] not in state.cities or state.cities[row['home']].owner != row['owner']
                or side_for(state, battle, row['owner']) != row['side']
                or defections.get(key, {}).get('original_side', deployed[key][1]) != row['side']):
            raise ValueError('Battle reinforcement identity')
    from .logistics import marching_ids as transport_ids
    occupied = {ident for ident, _ in deployed.values()} | transport_ids(state)
    occupied.update(ident for row in state.extension['travel']['marches'] for ident in row['officers'])
    occupied.update(ident for row in state.extension.get(RETURNS, ()) for ident in row['officers'])
    routes = _sources(game, state, battle) if data['pending'] else {}
    for row in data['pending']:
        ids = row['officers']
        if (set(row) != ORDER_FIELDS or row['side'] not in SIDES or not isinstance(ids, list) or not ids
                or len(set(ids)) != len(ids) or occupied.intersection(ids) or row['source'] not in state.cities):
            raise ValueError('Battle reinforcement participants')
        city = state.cities[row['source']]
        if (city.owner != row['owner'] or side_for(state, battle, city.owner) != row['side']
                or not set(ids) <= set(city.roster.officer_ids)
                or any(not state.officers[i].alive or state.officers[i].faction_id != city.owner
                       or state.officers[i].troops <= 0 for i in ids)
                or not any((leg['id'], leg['days']) == (row['route'], row['days']) for leg in routes.get(city.id, ()))):
            raise ValueError('Battle reinforcement route or roster')
        integer(row['departed'], 1, battle['round'], 'reinforcement departure day')
        integer(row['days'], 1, DAYS - row['departed'], 'reinforcement route days')
        cost = _cost(state, ids, 2 * row['days'])
        integer(row['grain'], cost, cost, 'reinforcement carried grain')
        occupied.update(ids)


def validate_returns(game, state):
    seen = set()
    returning = state.extension.get(RETURNS, [])
    if not isinstance(returning, list) or len(returning) > len(state.officers):
        raise ValueError('Returning battle reinforcements')
    for row in returning:
        if (set(row) != {'source', 'target', 'owner', 'officers', 'route', 'remaining', 'grain'}
                or row['source'] not in state.cities or row['target'] not in game.catalog.map_cities
                or row['source'] == row['target'] or row['owner'] not in game.catalog.factions
                or not isinstance(row['route'], str) or not row['route']
                or not isinstance(row['officers'], list) or not row['officers']
                or not set(row['officers']) <= set(state.officers)
                or len(set(row['officers'])) != len(row['officers']) or seen.intersection(row['officers'])):
            raise ValueError('Returning battle reinforcement identity')
        integer(row['remaining'], 1, DAYS - 1, 'reinforcement return days')
        integer(row['grain'], 0, march_supply.LIMIT, 'reinforcement return grain')
        seen.update(row['officers'])
