"""Authoritative original-size tactical positions and shared maneuver points.

The image library supplies the recovered movement classes, never screen pixels.
Path searches, deployments and legal-action views are deterministic and draw no
campaign random numbers. Strategic command books are a separate resource.
"""
from copy import deepcopy
from functools import lru_cache
from heapq import heappop, heappush
import json
from pathlib import Path

from .errors import GameError

SCHEMA = 'tk2-battle-tactical-v1'
VIEW_SCHEMA = 'tk2-battle-tactical-view-v1'
COLUMNS, ROWS, TILE_SIZE = 31, 19, 16
SIDES = ('attackers', 'defenders')
DEFAULT_MAP = 'original-09'  # Explicit fallback for controlled test city IDs.
ATTACK_COST = 2
# A direct challenge is a remake shortcut for original contact/挑発, not a
# separately recovered original tactical command. Exchanges do not charge AP.
DUEL_COST = ATTACK_COST
TACTIC_COSTS = (6, 5, 4, 6, 7, 8, 8, 8, 10, 9, 9, 10, 10, 8, 12, 10)
DAILY_POINTS = (10, 16, 20, 24, 28, 32, 35, 37, 40, 42)
POINT_CAPS = (20, 26, 32, 36, 42, 46, 51, 53, 58, 60)
# Native class order: forest, sand/special ground, plain, water, mountain, camp.
# Each affinity has the <600 and >=600 soldier rows respectively.
MOVEMENT_COSTS = (
    ((2, 3, 1, 3, 3, 4), (3, 4, 2, 5, 5, 6)),
    ((3, 3, 2, 5, 2, 4), (5, 4, 3, 6, 3, 6)),
    ((3, 3, 2, 2, 4, 4), (5, 4, 3, 3, 6, 6)),
)


def _int(value, low, high):
    return type(value) is int and low <= value <= high


@lru_cache(maxsize=1)
def _library():
    root = Path(__file__).resolve().parents[2]
    library = json.loads((root / 'game/assets/battlefields/index.json').read_text())
    bindings = json.loads((root / 'game/config/battlefield-city-bindings.json').read_text())
    if (library.get('schema') != 'tk2-original-battlefields-v1'
            or library.get('grid') != dict(columns=COLUMNS, rows=ROWS, tile_size=TILE_SIZE,
                                           width=COLUMNS*TILE_SIZE, height=ROWS*TILE_SIZE)
            or bindings.get('schema') != 'tk2-battlefield-city-bindings-v1'):
        raise ValueError('Invalid authoritative battlefield library')
    maps = {}
    for index in range(30):
        key = f'original-{index:02d}'
        row = library['maps'][key]
        classes, camps = row['classes'], row['camps']
        if (row['id'] != key or len(classes) != ROWS
                or any(len(line) != COLUMNS or any(not _int(cell, 0, 5) for cell in line) for line in classes)
                or len(camps) != 1 or any(not _int(camps[0][axis], 0, limit)
                    for axis, limit in (('x', COLUMNS-1), ('y', ROWS-1)))):
            raise ValueError('Invalid authoritative battlefield grid')
        maps[key] = dict(classes=tuple(tuple(line) for line in classes),
                         camp=(camps[0]['x'], camps[0]['y']))
    cities = {key: row['map_id'] for key, row in bindings['cities'].items()}
    if any(value not in maps for value in cities.values()):
        raise ValueError('Invalid authoritative battlefield binding')
    return maps, cities


def field_id(city):
    return _library()[1].get(city, DEFAULT_MAP)


def _field(battle):
    return _library()[0][battle['extended']['tactical']['map_id']]


def _unit(battle, ident):
    ident = ident['id'] if isinstance(ident, dict) else ident
    return next(((side, unit) for side in SIDES for unit in battle[side]
                 if unit['id'] == ident), (None, None))


def _live(battle, unit):
    support = battle['extended']['support'].get(str(unit['id']), {})
    return (unit['troops'] > 0 and support.get('health', 1) > 0
            and str(unit['id']) not in battle['extended']['surrenders'])


def _troops(battle, side):
    return sum(unit['troops'] for unit in battle[side] if _live(battle, unit))


def daily_points(troops):
    if not _int(troops, 0, 9990):
        raise ValueError('Invalid tactical soldier total')
    return DAILY_POINTS[min(troops // 1000, 9)]


def point_cap(troops):
    if not _int(troops, 0, 9990):
        raise ValueError('Invalid tactical soldier total')
    return POINT_CAPS[min(troops // 1000, 9)]


def initialize(game, state, battle):
    """Assign both armies distinct real cells; initialization never draws RNG."""
    maps, _ = _library()
    map_id = field_id(battle['target'])
    field = maps[map_id]
    camp_x, camp_y = field['camp']
    anchors = dict(defenders=(camp_x, camp_y),
        attackers=(2 if camp_x >= COLUMNS//2 else COLUMNS-3, max(2, min(ROWS-3, camp_y))))
    occupied, positions = set(), {}
    for side in ('defenders', 'attackers'):
        ax, ay = anchors[side]
        candidates = [(x, y) for y in range(ROWS) for x in range(COLUMNS)
                      if field['classes'][y][x] in (0, 1, 2, 5)]
        candidates.sort(key=lambda p: (abs(p[0]-ax)+abs(p[1]-ay)
            + {2: 0, 1: 2, 0: 4, 5: 0}[field['classes'][p[1]][p[0]]], p[1], p[0]))
        chosen = [p for p in candidates if p not in occupied][:len(battle[side])]
        if len(chosen) != len(battle[side]):
            raise ValueError('Battlefield has insufficient deployment cells')
        # The defending commander keeps the recovered camp cell. Remaining
        # deployment is deterministic regional reuse, not claimed ROM placement.
        for unit, (x, y) in zip(battle[side], chosen):
            positions[str(unit['id'])] = dict(x=x, y=y)
            occupied.add((x, y))
    battle['extended']['tactical'] = dict(schema=SCHEMA, map_id=map_id,
        positions=positions, side='attackers',
        points={side: daily_points(_troops(battle, side)) for side in SIDES},
        passed={side: False for side in SIDES})
    return battle['extended']['tactical']


def validate(game, state, battle):
    row = battle['extended'].get('tactical')
    identities = {str(unit['id']) for side in SIDES for unit in battle[side]}
    if (not isinstance(row, dict) or set(row) != {'schema', 'map_id', 'positions', 'side', 'points', 'passed'}
            or row['schema'] != SCHEMA or row['map_id'] != field_id(battle['target'])
            or row['side'] not in SIDES or not isinstance(row['positions'], dict)
            or set(row['positions']) != identities
            or not isinstance(row['points'], dict) or set(row['points']) != set(SIDES)
            or any(not _int(value, 0, POINT_CAPS[-1]) for value in row['points'].values())
            or not isinstance(row['passed'], dict) or set(row['passed']) != set(SIDES)
            or any(type(value) is not bool for value in row['passed'].values())
            or row['passed'][row['side']]):
        raise ValueError('Invalid tactical battle state')
    for side in SIDES:
        starts = [unit.get('start') for unit in battle[side]]
        if (any(not _int(amount, 1, 999) for amount in starts)
                or row['points'][side] > point_cap(sum(starts))):
            # Casualties may lower tomorrow's cap below today's lawful carried
            # balance. The immutable opening army is still an absolute ceiling.
            raise ValueError('Tactical points exceed the opening army cap')
    seen = set()
    units = {str(unit['id']): unit for side in SIDES for unit in battle[side]}
    for key, point in row['positions'].items():
        if (not isinstance(point, dict) or set(point) != {'x', 'y'}
                or not _int(point['x'], 0, COLUMNS-1) or not _int(point['y'], 0, ROWS-1)):
            raise ValueError('Invalid or overlapping tactical position')
        if _live(battle, units[key]):
            if (point['x'], point['y']) in seen:
                raise ValueError('Invalid or overlapping tactical position')
            seen.add((point['x'], point['y']))


def _action_reason(battle, actor, side=None):
    own, unit = _unit(battle, actor)
    row = battle['extended'].get('tactical')
    if unit is None or not _live(battle, unit):
        return '請選擇仍可作戰的部隊。'
    if row is None:
        return ''
    if side is not None and own != side:
        return '請選擇本方部隊。'
    if battle['outcome'] or battle['extended']['duel']:
        return '請先完成目前的戰鬥操作。'
    if battle['extended'].get('siege'):
        return '請先完成目前的攻城戰。'
    if own != row['side'] or row['passed'][own]:
        return '目前不是本方的戰術行動階段。'
    return ''


def attack_reason(battle, actor, target, side):
    if 'tactical' not in battle['extended']:
        return ''
    reason = _action_reason(battle, actor, side)
    own, acting = _unit(battle, actor)
    other, victim = _unit(battle, target)
    if reason:
        return reason
    if other == own or victim is None or not _live(battle, victim):
        return '請選擇有效的敵方部隊。'
    row = battle['extended']['tactical']
    if row['points'][side] < ATTACK_COST:
        return '本方機動力不足。'
    first, second = row['positions'][str(acting['id'])], row['positions'][str(victim['id'])]
    if abs(first['x']-second['x']) + abs(first['y']-second['y']) != 1:
        return '必須移動至敵軍上下左右相鄰的位置才能攻擊。'
    return ''


def tactic_range_reason(battle, actor, target, tid):
    if 'tactical' not in battle['extended']:
        return ''
    if not _int(tid, 0, len(TACTIC_COSTS)-1):
        return '計略編號無效。'
    side, acting = _unit(battle, actor)
    reason = _action_reason(battle, actor, side)
    if reason:
        return reason
    row = battle['extended']['tactical']
    if row['points'][side] < TACTIC_COSTS[tid]:
        return '本方機動力不足。'
    if tid == 11:  # Ambush is cast on the actor; the old UI target is ignored.
        return ''
    other, victim = _unit(battle, target)
    if other == side or victim is None or not _live(battle, victim):
        return '請選擇有效的敵方部隊。'
    first, second = row['positions'][str(acting['id'])], row['positions'][str(victim['id'])]
    dx, dy = abs(first['x']-second['x']), abs(first['y']-second['y'])
    if tid in (6, 9, 13) and dx+dy != 1:
        return '此計略必須與敵軍上下左右相鄰。'
    if max(dx, dy) > 5:
        return '目標超出計略的五格範圍。'
    return ''


def tile_class(battle, actor):
    """Native movement class of a unit's actual authoritative visible cell."""
    _, unit = _unit(battle, actor)
    if unit is None:
        raise ValueError('Unknown tactical unit')
    point = battle['extended']['tactical']['positions'][str(unit['id'])]
    return _field(battle)['classes'][point['y']][point['x']]


def siege_context(battle, actor, target):
    """Freeze the actual occupied castle cell for this one contact encounter.

    A commander identity or the target city's strategic terrain does not make
    a siege: a combatant must stand on the recovered native class5 cell. The
    receipt is presentation-only and is captured before any later AI movement.
    Old arithmetic-only battles have no grid and keep their existing payload.
    """
    row = battle['extended'].get('tactical')
    if row is None:
        return None
    for value in (target, actor):
        _, unit = _unit(battle, value)
        if unit is not None and tile_class(battle, unit) == 5:
            return dict(fort=unit['id'], map_id=row['map_id'],
                        cell=deepcopy(row['positions'][str(unit['id'])]))
    return None


def tactic_terrain_reason(battle, actor, target, tid):
    """Recovered player target qualifiers; damage and chance stay elsewhere."""
    side, acting = _unit(battle, actor)
    other, victim = _unit(battle, target)
    source_class = tile_class(battle, acting)
    if tid == 11:
        if source_class != 0:
            return '十面埋伏需要本隊位於森林。'
        if acting['troops'] < 100 or battle['extended']['ambush']:
            return '設伏需要至少100兵，且目前沒有伏兵。'
        return ''
    if victim is None:
        return '請選擇有效的敵方部隊。'
    target_class = tile_class(battle, victim)
    positions = battle['extended']['tactical']['positions']
    point = positions[str(victim['id'])]
    neighbors = [unit for unit in battle[other] if unit['id'] != victim['id'] and _live(battle, unit)
        and abs(positions[str(unit['id'])]['x']-point['x'])
            + abs(positions[str(unit['id'])]['y']-point['y']) == 1]
    if tid == 0 and target_class not in (0, 2):
        return '火計的目標必須位於森林或平地。'
    if tid in (1, 2, 3) and target_class not in (0, 4):
        return '此計略的目標必須位於森林或山地。'
    if tid == 4 and target_class != 3:
        return '亂水的目標必須位於河流。'
    if tid == 5 and victim['id'] != battle[other][0]['id']:
        return '火箭只能以敵方主將為目標。'
    if tid == 6 and target_class != 5:
        return '偽擊轉殺的目標必須位於城砦。'
    if tid == 7 and (target_class not in (0, 4) or not neighbors):
        return '共殺的目標須位於森林或山地，且四鄰另有敵隊。'
    if tid == 8 and target_class == 5:
        return '籠絡不能以城砦內的部隊為目標。'
    if tid == 9 and (source_class not in (4, 5) or target_class == 5):
        return '落石須由山地或城砦發動，且目標不能位於城砦。'
    if tid in (10, 12) and (target_class != 3 or not any(tile_class(battle, unit) == 3 for unit in neighbors)):
        return '此計略的目標及其四鄰另一敵隊都必須位於河流。'
    if tid == 13 and source_class != 5:
        return '連弩須由城砦發動。'
    if tid == 14 and (target_class == 5 or not any(tile_class(battle, unit) != 5 for unit in neighbors)):
        return '劫火的目標不能位於城砦，且四鄰須另有非城砦敵隊。'
    if tid == 15 and target_class in (3, 5):
        return '奇門遁甲不能以河流或城砦內的部隊為目標。'
    return ''


def affected_units(battle, target, tid, foe):
    """Spatial victim order only; callers retain all actual damage/RNG rules."""
    _, victim = _unit(battle, target)
    if victim is None or victim not in battle[foe] or not _live(battle, victim):
        return []
    if 'tactical' not in battle['extended'] or tid not in (7, 10, 12, 14):
        return [victim]
    positions = battle['extended']['tactical']['positions']
    occupied = {(positions[str(unit['id'])]['x'], positions[str(unit['id'])]['y']): unit
        for unit in battle[foe] if _live(battle, unit)}
    origin = positions[str(victim['id'])]
    source = (origin['x'], origin['y'])

    def neighbors(point):
        x, y = point
        return ((x-1, y), (x+1, y), (x, y-1), (x, y+1))

    if tid == 7:
        return [victim] + [occupied[point] for point in neighbors(source) if point in occupied]
    queue, seen, result = [source], {source}, []
    for point in queue:
        unit = occupied.get(point)
        if unit is None or tile_class(battle, unit) == 5:
            continue
        if tid == 14 or tile_class(battle, unit) == 3:
            result.append(unit)
        # Non-water enemy units can conduct the connected effect. Only camp
        # cells cut propagation; final water filtering is deliberately later.
        x, y = point
        # Recovered connected-area queue order differs from the cross above.
        for next_point in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if next_point in occupied and next_point not in seen:
                seen.add(next_point)
                queue.append(next_point)
    return result


def movement_cost(state, unit, terrain):
    affinity = state.officers[unit['id']].profile.terrain_affinity
    if not _int(affinity, 0, 2) or not _int(terrain, 0, 5):
        raise ValueError('Invalid movement affinity or terrain')
    return MOVEMENT_COSTS[affinity][int(unit['troops'] >= 600)][terrain]


def _paths(state, battle, actor, budget=None):
    _, unit = _unit(battle, actor)
    if unit is None:
        raise GameError('請選擇有效的部隊。')
    row = battle['extended']['tactical']
    start = row['positions'][str(unit['id'])]
    source = (start['x'], start['y'])
    live = {str(other['id']) for side in SIDES for other in battle[side] if _live(battle, other)}
    occupied = {(point['x'], point['y']) for key, point in row['positions'].items()
                if key != str(unit['id']) and key in live}
    classes = _field(battle)['classes']
    distances, previous = {source: 0}, {}
    queue = [(0, source[1], source[0])]
    while queue:
        cost, y, x = heappop(queue)
        if distances.get((x, y)) != cost:
            continue
        for nx, ny in ((x, y-1), (x-1, y), (x+1, y), (x, y+1)):
            if not (0 <= nx < COLUMNS and 0 <= ny < ROWS) or (nx, ny) in occupied:
                continue
            proposed = cost + movement_cost(state, unit, classes[ny][nx])
            if budget is not None and proposed > budget:
                continue
            if proposed < distances.get((nx, ny), float('inf')):
                distances[(nx, ny)] = proposed
                previous[(nx, ny)] = (x, y)
                heappush(queue, (proposed, ny, nx))
    return source, distances, previous


def move_quote(game, state, battle, actor, x, y):
    if not _int(x, 0, COLUMNS-1) or not _int(y, 0, ROWS-1):
        raise GameError('移動目的地超出戰場邊界。')
    side, unit = _unit(battle, actor)
    reason = _action_reason(battle, actor, side)
    if reason:
        raise GameError(reason)
    source, distances, previous = _paths(state, battle, actor)
    destination = (x, y)
    if destination == source:
        raise GameError('請選擇不同的移動目的地。')
    if destination not in distances:
        raise GameError('目的地已被占據或沒有可通行的路徑。')
    cost = distances[destination]
    if cost > battle['extended']['tactical']['points'][side]:
        raise GameError('本方機動力不足。')
    path = [destination]
    while path[-1] != source:
        path.append(previous[path[-1]])
    path.reverse()
    return dict(path=[dict(x=px, y=py) for px, py in path], cost=cost,
                **{'from': dict(x=source[0], y=source[1]), 'to': dict(x=x, y=y)})


def spend(battle, side, cost):
    row = battle['extended']['tactical']
    if (side not in SIDES or row['side'] != side or row['passed'][side]
            or not _int(cost, 1, POINT_CAPS[-1]) or row['points'][side] < cost):
        raise GameError('本方機動力不足，或目前不是本方的行動階段。')
    row['points'][side] -= cost


def move(game, state, battle, actor, x, y):
    quote = move_quote(game, state, battle, actor, x, y)
    side, unit = _unit(battle, actor)
    spend(battle, side, quote['cost'])
    battle['extended']['tactical']['positions'][str(unit['id'])] = dict(x=x, y=y)
    return quote


def end_side(state, battle):
    row = battle['extended']['tactical']
    side = row['side']
    row['passed'][side] = True
    advanced = all(row['passed'].values())
    if advanced:
        battle['round'] += 1
        for key in SIDES:
            troops = _troops(battle, key)
            row['points'][key] = min(point_cap(troops), row['points'][key] + daily_points(troops))
            row['passed'][key] = False
        row['side'] = 'attackers'
    else:
        row['side'] = 'defenders' if side == 'attackers' else 'attackers'
    return dict(advanced_day=advanced, side=row['side'], round=battle['round'],
                timed_out=battle['round'] > 30)


def view(game, state, battle):
    if not battle or 'tactical' not in battle['extended']:
        return None
    from .campaign_expansion import TACTICS
    from .tactical_ai import tactic_reason
    row = battle['extended']['tactical']
    own = 'attackers' if battle['attacker'] == state.player else 'defenders'
    foe = 'defenders' if own == 'attackers' else 'attackers'
    terrain = game.catalog.map_cities[battle['target']]['terrain']
    actors = {}
    for actor in battle[own]:
        reason = _action_reason(battle, actor, own)
        can_act = not reason and row['points'][own] > 0 and state.phase == 'battle'
        cells = []
        if can_act:
            source, distances, _ = _paths(state, battle, actor, row['points'][own])
            cells = [dict(x=x, y=y, cost=cost) for (x, y), cost in sorted(distances.items(),
                key=lambda item: (item[0][1], item[0][0])) if (x, y) != source]
        attack_reasons = {str(target['id']): attack_reason(battle, actor, target, own) for target in battle[foe]}
        duel_reasons = {key: value or ('受擾亂部隊不能挑戰單挑。'
            if battle['extended']['support'][str(actor['id'])]['stunned'] else '')
            for key, value in attack_reasons.items()}
        tactic_reasons = {str(tid): {str(target['id']): tactic_reason(state, battle, actor,
            target, own, foe, terrain, tactic) for target in battle[foe]}
            for tid, tactic in enumerate(TACTICS)}
        actors[str(actor['id'])] = dict(can_act=bool(can_act), reason=reason,
            reachable=cells,
            attack_targets=[u['id'] for u in battle[foe] if not attack_reasons[str(u['id'])]],
            duel_targets=[u['id'] for u in battle[foe] if not duel_reasons[str(u['id'])]],
            tactic_targets={tid: [u['id'] for u in battle[foe] if not reasons[str(u['id'])]]
                            for tid, reasons in tactic_reasons.items()},
            attack_reasons=attack_reasons, duel_reasons=duel_reasons, tactic_reasons=tactic_reasons)
    return dict(schema=VIEW_SCHEMA, battle_id=battle['id'], round=battle['round'], map_id=row['map_id'],
        grid=dict(columns=COLUMNS, rows=ROWS, tile_size=TILE_SIZE), side=row['side'],
        points=deepcopy(row['points']), caps={side: point_cap(_troops(battle, side)) for side in SIDES},
        can_end=state.phase == 'battle' and row['side'] == own and not battle['extended']['duel'],
        attack_cost=ATTACK_COST, duel_cost=DUEL_COST, tactic_costs=list(TACTIC_COSTS), actors=actors)
