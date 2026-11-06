"""Sequential human placement within audited original deployment rectangles.

The optional receipt is created only at a real new-battle boundary. Positions
remain in the tactical grid; future human units deliberately have no position
until their turn. Reads never initialize a legacy battle or draw random values.
"""
from copy import deepcopy

from .errors import GameError

SCHEMA = 'tk2-battle-placement-v1'
VIEW_SCHEMA = 'tk2-battle-placement-view-v1'
FIELDS = {'schema','side','order','confirmed'}
SIDES = ('attackers','defenders')
REASON = '請先完成本方部隊的布陣。'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _ident(unit):
    value = unit.get('id') if isinstance(unit,dict) else None
    _require(type(value) is int and value >= 0 or type(value) is str and 0 < len(value) <= 128,
             'Invalid placement unit identity')
    return str(value)


def _row(battle):
    return battle.get('extended',{}).get('placement') if isinstance(battle,dict) else None


def pending(battle):
    """Pure status predicate; malformed records are rejected by validation."""
    row = _row(battle)
    return (isinstance(row,dict) and type(row.get('confirmed')) is int
            and isinstance(row.get('order'),list) and row['confirmed'] < len(row['order']))


def _zone(game,battle,side):
    from . import battle_deployment,battle_grid
    return battle_deployment.placement_zone(game.catalog,battle,battle_grid._field(battle),side)


def _initial_ids(battle,side):
    records = battle['extended'].get('defections',{})
    _require(type(records) is dict,'Invalid placement conversion ledger')
    result = []
    for current in SIDES:
        for unit in battle[current]:
            key = _ident(unit)
            record = records.get(key)
            _require(record is None or isinstance(record,dict) and record.get('original_side') in SIDES,
                     'Invalid placement conversion identity')
            if (record['original_side'] if record is not None else current) == side:
                result.append(key)
    return result


def _default(defaults,positions):
    occupied = {(point['x'],point['y']) for point in positions.values()}
    point = next((point for point in defaults if (point['x'],point['y']) not in occupied),None)
    _require(point is not None,'Insufficient original placement candidates')
    return dict(point)


def validate(game,state,battle):
    """Validate optional phase state without repairing positions or old saves.

    After completion, conversions can change roster order and side. The saved
    unique order is retained, and its identity set is checked using the existing
    conversion ledger; it is not claimed to reconstruct original NES slot order.
    """
    if 'placement' not in battle.get('extended',{}):
        return
    from . import battle_grid
    x = battle['extended']; row = x['placement']; tactical = x.get('tactical')
    _require(type(row) is dict and set(row) == FIELDS and row.get('schema') == SCHEMA
        and row.get('side') in SIDES and type(row.get('order')) is list
        and 1 <= len(row['order']) <= 10 and all(type(key) is str for key in row['order'])
        and len(set(row['order'])) == len(row['order'])
        and type(row.get('confirmed')) is int and 0 <= row['confirmed'] <= len(row['order']),
        'Invalid manual placement fields')
    _require(isinstance(tactical,dict) and isinstance(tactical.get('positions'),dict)
        and 'deployment' in x,'Manual placement requires tactical provenance')
    side = row['side']; other = SIDES[1-SIDES.index(side)]
    all_ids = [_ident(unit) for current in SIDES for unit in battle[current]]
    _require(len(all_ids) == len(set(all_ids)),'Duplicate manual placement identity')
    own_ids = _initial_ids(battle,side)
    _require(len(own_ids) == len(set(own_ids)) and set(row['order']) == set(own_ids),
             'Manual placement initial identities differ')
    zone = _zone(game,battle,side)  # Also checks immutable native provenance.
    if row['confirmed'] == len(row['order']):
        return
    _require(state.player == battle['attacker' if side == 'attackers' else 'defender'],
             'Manual placement side is not the player')
    _require(state.phase == 'battle' and type(battle.get('round')) is int and battle['round'] == 1
        and battle.get('outcome') is None and battle.get('used') == []
        and not x.get('defections') and not x.get('siege') and not x.get('duel')
        and not x.get('duel_history') and not x.get('surrenders') and not x.get('occupation')
        and not x.get('ambush') and x.get('withdrawn') is None and 'conditions' not in x,
        'Manual placement is not an untouched first day')
    _require(row['order'] == [_ident(unit) for unit in battle[side]]
        and all(1 <= len(battle[key]) <= 10 for key in SIDES),
        'Manual placement roster changed before confirmation')
    for current in SIDES:
        for unit in battle[current]:
            key = _ident(unit); support = x['support'][key]
            _require(type(unit.get('start')) is int and 1 <= unit['start'] <= 1000
                and type(unit.get('troops')) is int and unit['troops'] == unit['start']
                and type(support.get('health')) is int and support['health'] == state.officers[unit['id']].health
                and type(support.get('energy')) is int and support['energy'] == 18
                and type(support.get('stunned')) is int and support['stunned'] == 0
                and type(support.get('guard')) is int and support['guard'] == 0,
                'Manual placement unit already acted or suffered damage')
    _require(tactical.get('side') == 'attackers'
        and tactical.get('passed') == dict(attackers=False,defenders=False)
        and tactical.get('points') == {key:battle_grid.daily_points(sum(unit['troops'] for unit in battle[key]))
                                       for key in SIDES},'Manual placement changed initial maneuver points')
    if 'supply' in x:
        _require(isinstance(x['supply'],dict) and type(x['supply'].get('days')) is int
            and x['supply']['days'] == 0 and x['supply'].get('settlement') is None,
            'Manual placement has consumed battle days')
    other_ids = [_ident(unit) for unit in battle[other]]
    active_ids = row['order'][:row['confirmed']+1]
    positions = tactical['positions']
    _require(set(positions) == set(other_ids+active_ids),'Invalid partial placement position identities')
    defaults = _zone(game,battle,other)['defaults']
    _require(all(positions[key] == point for key,point in zip(other_ids,defaults)),
             'Manual placement changed the fixed opposing deployment')
    allowed = {(point['x'],point['y']) for point in zone['cells']}
    seen = set()
    for key,point in positions.items():
        _require(type(point) is dict and set(point) == {'x','y'}
            and type(point['x']) is int and 0 <= point['x'] < 31
            and type(point['y']) is int and 0 <= point['y'] < 19,
            'Invalid partial placement coordinate')
        pair = point['x'],point['y']
        _require(pair not in seen,'Overlapping manual placement units')
        _require(key not in active_ids or pair in allowed,'Manual placement outside the original rectangle')
        seen.add(pair)


def initialize(game,state,battle):
    """Create placement once for a real player battle; return None otherwise."""
    x = battle['extended']
    if 'placement' in x:
        validate(game,state,battle)
        return x['placement']
    if ('deployment' not in x or 'tactical' not in x
            or not all(battle[key] and any(unit['troops'] > 0 for unit in battle[key]) for key in SIDES)
            or state.player not in (battle['attacker'],battle['defender'])):
        return None
    candidate = deepcopy(battle); extension = candidate['extended']
    side = 'attackers' if battle['attacker'] == state.player else 'defenders'
    other = SIDES[1-SIDES.index(side)]
    order = [_ident(unit) for unit in candidate[side]]
    extension['placement'] = dict(schema=SCHEMA,side=side,order=order,confirmed=0)
    defaults = _zone(game,candidate,other)['defaults']
    _require(len(defaults) >= len(candidate[other]),'Insufficient opposing deployment candidates')
    positions = {_ident(unit):dict(point) for unit,point in zip(candidate[other],defaults)}
    positions[order[0]] = _default(_zone(game,candidate,side)['defaults'],positions)
    extension['tactical']['positions'] = positions
    _validate_grid(game,state,candidate)
    x['placement'] = extension['placement']
    x['tactical']['positions'] = positions
    return x['placement']


def _validate_grid(game,state,battle):
    # Lazy import avoids a module import cycle; grid validation calls this
    # module's validate, which does not call back into grid validation.
    from . import battle_grid
    battle_grid.validate(game,state,battle)


def confirm(game,state,battle,ident,x,y):
    """Atomically confirm only the current unit, without spending time or AP."""
    try:
        validate(game,state,battle)
        _require(pending(battle),'Manual placement is already complete or absent')
        row = battle['extended']['placement']; key = row['order'][row['confirmed']]
        current = next(unit['id'] for unit in battle[row['side']] if str(unit['id']) == key)
        _require(type(ident) is type(current) and ident == current,'Confirm the current placement unit')
        _require(type(x) is int and type(y) is int,'Invalid manual placement coordinate')
        zone = _zone(game,battle,row['side'])
        _require(dict(x=x,y=y) in zone['cells'],'Manual placement outside the original rectangle')
        positions = battle['extended']['tactical']['positions']
        _require(all(other == key or point != dict(x=x,y=y) for other,point in positions.items()),
                 'Manual placement cell is occupied')
        candidate = deepcopy(battle); saved = candidate['extended']['placement']
        proposed = candidate['extended']['tactical']['positions']
        proposed[key] = dict(x=x,y=y); saved['confirmed'] += 1
        if saved['confirmed'] < len(saved['order']):
            proposed[saved['order'][saved['confirmed']]] = _default(zone['defaults'],proposed)
        _validate_grid(game,state,candidate)
    except (ValueError,KeyError,StopIteration,TypeError) as error:
        raise GameError('布陣位置無效，請依序選擇原陣區內未被占用的位置。') from error
    battle['extended']['placement'] = saved
    battle['extended']['tactical']['positions'] = proposed
    return view(game,state,battle)


def view(game,state,battle):
    """Pure optional projection; future units never enter the tactical view."""
    if 'placement' not in battle.get('extended',{}):
        return None
    validate(game,state,battle)
    row = battle['extended']['placement']; active = pending(battle)
    zone = _zone(game,battle,row['side'])
    actor = None; cells = []
    if active:
        key = row['order'][row['confirmed']]
        actor = next(unit['id'] for unit in battle[row['side']] if str(unit['id']) == key)
        occupied = {(point['x'],point['y']) for ident,point in battle['extended']['tactical']['positions'].items()
                    if ident != key}
        cells = [point for point in zone['cells'] if (point['x'],point['y']) not in occupied]
    return dict(schema=VIEW_SCHEMA,pending=active,side=row['side'],actor=actor,
                confirmed=row['confirmed'],total=len(row['order']),cells=cells,bounds=zone['bounds'])
