"""Transactional new-battle AI setup with frozen, minimal input receipts.

The original strategy planner is pure. Only a real arrival creates this optional
section. Old pending/default battles keep their exact positions; completed
receipts never constrain moved, wounded or converted units to an opening cell.
"""
from copy import deepcopy

SCHEMA = 'tk2-auto-deployment-v1'
VIEW_SCHEMA = 'tk2-auto-deployment-view-v1'
SIDES = ('defenders','attackers')


def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _units(battle):
    result = {}
    for side in SIDES:
        for unit in battle[side]:
            ident = unit.get('id') if isinstance(unit,dict) else None
            _require(type(ident) is int and ident >= 0 or type(ident) is str and 0 < len(ident) <= 128,
                     'Invalid automatic deployment identity')
            key = str(ident)
            _require(key not in result,'Duplicate automatic deployment identity')
            result[key] = (side,unit)
    return result


def _original_side(battle,key,current):
    records = battle['extended'].get('defections',{})
    _require(isinstance(records,dict),'Invalid automatic deployment conversion ledger')
    record = records.get(key)
    _require(record is None or isinstance(record,dict) and record.get('original_side') in SIDES,
             'Invalid automatic deployment original side')
    return record['original_side'] if record is not None else current


def _receipt(game,battle):
    from . import battle_ai_deployment,battle_deployment,battle_grid
    extension = battle['extended']; record = extension.get('auto_deployment')
    _require(type(record) is dict and set(record) == {'schema','sides'} and record.get('schema') == SCHEMA
        and type(record.get('sides')) is dict and 1 <= len(record['sides']) <= 2
        and set(record['sides']) <= set(SIDES),'Invalid automatic deployment receipt')
    _require('tactical' in extension and 'deployment' in extension,
             'Automatic deployment requires tactical provenance')
    battle_deployment.validate_provenance(game.catalog,battle,battle_grid._field(battle),extension['deployment'])
    units = _units(battle)
    for side,row in record['sides'].items():
        _require(type(row) is dict and set(row) == {'binding','roster'}
            and type(row.get('binding')) is dict and set(row['binding']) == {'family','policy','original_slot'}
            and type(row.get('roster')) is list and 1 <= len(row['roster']) <= 10,
            'Invalid automatic deployment side fields')
        expected = battle_ai_deployment.family_for(battle['attacker' if side=='attackers' else 'defender'])
        _require(row['binding'] == expected
            and type(row['binding'].get('family')) is int
            and type(row['binding'].get('policy')) is str
            and (row['binding'].get('original_slot') is None or type(row['binding']['original_slot']) is int),
            'Invalid automatic deployment family binding')
        keys = []
        for unit in row['roster']:
            _require(type(unit) is dict and set(unit) == {'id','martial'}
                and type(unit.get('id')) is str and unit['id'] in units
                and type(unit.get('martial')) is int and 0 <= unit['martial'] <= 255,
                'Invalid automatic deployment initial roster')
            keys.append(unit['id'])
        initial = {key for key,(current,_) in units.items() if _original_side(battle,key,current) == side}
        _require(len(keys) == len(set(keys)) and set(keys) == initial,
                 'Automatic deployment initial side differs')
    return record,units


def _plans(game,battle):
    """Reproduce immutable initial plans without consulting live positions."""
    from . import battle_ai_deployment,battle_grid
    record,units = _receipt(game,battle)
    frozen = {key:battle[key] for key in ('source','target','attacker','defender')}
    frozen['extended'] = dict(deployment=deepcopy(battle['extended']['deployment']))
    for side in SIDES:
        frozen[side] = [dict(id=units[row['id']][1]['id'],martial=row['martial'])
                       for row in record['sides'].get(side,{}).get('roster',[])]
    occupied = set(); plans = {}
    for side in SIDES:
        if side not in record['sides']:
            continue
        plan = battle_ai_deployment.plan(game.catalog,frozen,battle_grid._field(battle),side,occupied=occupied)
        _require(plan['binding'] == record['sides'][side]['binding'],
                 'Automatic deployment planner binding differs')
        plans[side] = plan
        occupied.update((point['x'],point['y']) for point in plan['positions'].values())
    return plans


def initial_positions(game,battle,side):
    """Fresh saved-input AI cells, for pending manual setup only."""
    _require(side in SIDES,'Invalid automatic deployment side')
    plans = _plans(game,battle)
    _require(side in plans,'Missing automatic deployment side')
    return deepcopy(plans[side]['positions'])


def validate(game,state,battle):
    """Strict optional receipt; completed positions and observer are untouched."""
    if 'auto_deployment' not in battle.get('extended',{}):
        return
    from . import battle_placement
    record,units = _receipt(game,battle)
    _require(('placement' in battle['extended']) == (len(record['sides']) == 1),
             'Automatic deployment has inconsistent manual provenance')
    if not battle_placement.pending(battle):
        return
    placement = battle['extended']['placement']; own = placement['side']
    other = 'defenders' if own=='attackers' else 'attackers'
    _require(set(record['sides']) == {other},'Manual setup has inconsistent automatic sides')
    row = record['sides'][other]
    _require(row['roster'] == [dict(id=str(unit['id']),martial=unit['martial']) for unit in battle[other]],
             'Automatic deployment initial inputs changed before confirmation')
    positions = battle['extended']['tactical']['positions']
    _require(all(positions.get(key) == point for key,point in initial_positions(game,battle,other).items()),
             'Automatic deployment positions changed during manual setup')


def initialize(game,state,battle):
    """Prepare AI sides and then human setup, committing the extension once."""
    from . import battle_ai_deployment,battle_grid,battle_placement
    extension = battle['extended']
    if 'auto_deployment' in extension:
        validate(game,state,battle)
        return extension['auto_deployment']
    if ('placement' in extension or 'tactical' not in extension or 'deployment' not in extension
            or state.phase != 'battle' or battle.get('outcome') is not None
            or type(battle.get('round')) is not int or battle['round'] != 1 or battle.get('used') != []
            or extension['tactical'].get('side') != 'attackers'
            or extension['tactical'].get('passed') != dict(attackers=False,defenders=False)
            or extension['tactical'].get('points') != {side:battle_grid.daily_points(sum(unit['troops'] for unit in battle[side])) for side in SIDES}
            or any(extension.get(key) for key in ('duel','duel_history','siege','ambush','defections','surrenders','occupation','withdrawn'))
            or 'conditions' in extension
            or 'supply' in extension and extension['supply'].get('days') != 0
            or not all(battle[side] and all(unit['troops'] > 0 for unit in battle[side]) for side in SIDES)):
        return None
    candidate = deepcopy(battle); saved = candidate['extended']
    sides = [side for side in SIDES if state.player != battle['attacker' if side=='attackers' else 'defender']]
    if not sides:
        return None
    saved['auto_deployment'] = dict(schema=SCHEMA,sides={side:dict(
        binding=deepcopy(battle_ai_deployment.family_for(candidate['attacker' if side=='attackers' else 'defender'])),
        roster=[dict(id=str(unit['id']),martial=unit['martial']) for unit in candidate[side]]) for side in sides})
    positions = dict(saved['tactical']['positions'])
    for side,plan in _plans(game,candidate).items():
        positions.update(plan['positions'])
    saved['tactical']['positions'] = positions
    # The manual service removes unplaced future humans and chooses the first
    # free safe candidate only after the whole opposing AI army is fixed.
    battle_placement.initialize(game,state,candidate)
    battle_grid.validate(game,state,candidate)
    validate(game,state,candidate)
    battle['extended'] = saved
    return saved['auto_deployment']


def view(game,state,battle):
    """Pure opening strategy explanation, never a request to redeploy."""
    if 'auto_deployment' not in battle.get('extended',{}):
        return None
    validate(game,state,battle)
    plans = _plans(game,battle)
    return dict(schema=VIEW_SCHEMA,sides={side:{key:deepcopy(plan[key]) for key in
        ('binding','profile','order','groups','intended','repairs')} for side,plan in plans.items()})
