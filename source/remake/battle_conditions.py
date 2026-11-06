"""Original movement conditions, separate from legacy support flags.

Original B155 writes3 for an attacking caster and2 for a defending caster.
Chain B3FE writes4/5 for an attacking caster and3/4 for a defending caster;
its accepted0/1 sample is supplied by the caller for each actual water target.
Qimen's high clock/damage only runs with original109 still present. Its saved
order starts with defenders then attackers and survives subsequent conversion.
Only the completed defender-to-attacker day boundary decrements these clocks.
The caller must settle food and battle termination before advancing it, and
must call apply only after an actual successful cast. Nothing here spends AP
or infers a condition from old stunned/guard values. Only committed Qimen days
draw damage samples and change battle troops; profile stats remain immutable.
"""
from copy import deepcopy

SCHEMA = 'tk2-battle-conditions-v1'
SIDES = ('attackers', 'defenders')
MAX_DAY = 30
QIMEN_PERSON = 'san14-candidate-0440'


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _key(ident):
    if type(ident) is int and ident >= 0:
        return str(ident)
    if type(ident) is str and ident and ident.strip() == ident:
        return ident
    raise ValueError('Invalid battle condition officer')


def _extension(battle):
    if not isinstance(battle, dict) or not isinstance(battle.get('extended'), dict):
        raise ValueError('Invalid battle condition context')
    return battle['extended']


def _units(battle):
    result = {}
    for side in SIDES:
        if not isinstance(battle.get(side), list):
            raise ValueError('Invalid battle condition armies')
        for unit in battle[side]:
            if not isinstance(unit, dict) or 'id' not in unit:
                raise ValueError('Invalid battle condition unit')
            key = _key(unit['id'])
            if key in result:
                raise ValueError('Duplicate battle condition officer')
            result[key] = (side, unit)
    return result


def _live(extension, units, key):
    entry = units.get(key)
    if entry is None:
        return False
    unit = entry[1]
    support = extension.get('support', {}).get(key, {})
    return (type(unit.get('troops')) is int and unit['troops'] > 0
            and support.get('health', 1) > 0
            and key not in extension.get('surrenders', {}))


def _present(extension, units, key):
    """CF60/high-clock retention is not a troop-count or HP qualification."""
    return key in units and key not in extension.get('surrenders', {})


def _checked(battle, *, pending_day=False, allow_removed=False):
    """Check only this optional extension; never initialize old battles.

    Mutations may be called between roster removal and final validation, or
    immediately after the round increment. Those narrow transitions are not
    accepted by the public save validator.
    """
    extension = _extension(battle)
    if 'conditions' not in extension:
        return None
    row = extension['conditions']
    current = battle.get('round')
    if (not isinstance(row, dict) or not {'schema', 'day', 'units'} <= set(row)
            or set(row)-{'schema', 'day', 'units', 'high_order'}
            or row['schema'] != SCHEMA or type(current) is not int or current < 1
            or not _integer(row['day'], 1, min(current, MAX_DAY))
            or not isinstance(row['units'], dict) or len(row['units']) > 20):
        raise ValueError('Invalid battle condition fields')
    if battle.get('outcome') is None:
        allowed = (current-1, current) if pending_day else (current,)
        if row['day'] not in allowed:
            raise ValueError('Invalid battle condition day')
    units = _units(battle)
    if 'high_order' in row:
        order = row['high_order']
        if (not isinstance(order, list) or len(order) > 20
                or any(type(key) is not str or not key or key.strip() != key for key in order)
                or len(set(order)) != len(order)
                or not allow_removed and set(order) != set(units)):
            raise ValueError('Invalid high battle condition order')
    for key, condition in row['units'].items():
        if (type(key) is not str or not key or key.strip() != key
                or not isinstance(condition, dict)
                or set(condition) != {'kind', 'remaining'}
                or condition['kind'] not in ('phantom', 'chain', 'qimen')
                or not _integer(condition['remaining'], 1,
                                {'phantom':3, 'chain':5, 'qimen':9}[condition['kind']])):
            raise ValueError('Invalid battle condition unit fields')
        if condition['kind'] == 'qimen' and 'high_order' not in row:
            raise ValueError('Qimen condition is missing its saved order')
        present = _present if condition['kind'] == 'qimen' else _live
        if not allow_removed and not present(extension, units, key):
            raise ValueError('Battle condition references a removed unit')
    return row


def duration(side):
    """Original side128 attacker writes3; side0 defender writes2."""
    if side not in SIDES:
        raise ValueError('Invalid phantom caster side')
    return 3 if side == 'attackers' else 2


def chain_duration(side, roll):
    """B3FE's accepted0/1 sample; no RNG or target traversal lives here."""
    if side not in SIDES:
        raise ValueError('Invalid chain caster side')
    if not _integer(roll, 0, 1):
        raise ValueError('Invalid chain duration sample')
    return (4 if side == 'attackers' else 3)+roll


def qimen_duration(side, roll):
    """B5A6's accepted low2 bits, expressed as high-clock counts."""
    if side not in SIDES:
        raise ValueError('Invalid Qimen caster side')
    if not _integer(roll, 0, 3):
        raise ValueError('Invalid Qimen duration sample')
    return (6 if side == 'attackers' else 5)+roll


def qimen_source(state, battle):
    """CF60's fixed person, on either side, without inventing an HP/men gate.

    The owning campaign validates officer profiles. A routed zero-men slot is
    still present until an actual removal/surrender or the battle's ending.
    """
    extension, units = _extension(battle), _units(battle)
    officers = getattr(state, 'officers', {})
    for side in ('defenders', 'attackers'):
        for unit in battle[side]:
            ident = unit['id']
            officer = officers.get(ident)
            martial = getattr(getattr(officer, 'profile', None), 'martial_strength', 0)
            if (getattr(officer, 'person_id', None) == QIMEN_PERSON
                    and type(martial) is int and martial > 0
                    and _present(extension, units, str(ident))):
                return ident
    return None


def validate(battle):
    """Pure strict save check; a missing legacy extension remains missing."""
    _checked(battle)


def view(battle):
    """Return an independent optional snapshot without creating any state."""
    row = _checked(battle)
    return deepcopy(row) if row is not None else None


def remaining(battle, ident):
    key = _key(ident)
    row = _checked(battle)
    return row['units'].get(key, {}).get('remaining', 0) if row else 0


def kind(battle, ident):
    """Pure optional condition tag; old stunned/guard never imply a kind."""
    key = _key(ident)
    row = _checked(battle)
    return row['units'].get(key, {}).get('kind') if row else None


def movement_blocked(battle, ident):
    """This gate belongs only on tactical movement, never all actions."""
    return remaining(battle, ident) > 0


def apply(battle, ident, side):
    """Apply a successful phantom cast; overwrite rather than stack it.

    Success qualification and AP debit belong to the shared tactic command.
    An old battle receives its optional extension only at this mutation.
    """
    return _apply(battle, ident, side, 'phantom', duration(side))


def apply_chain(battle, ident, side, roll):
    """Apply one successful water victim; overwrite either existing kind."""
    return _apply(battle, ident, side, 'chain', chain_duration(side, roll))


def apply_qimen(battle, ident, side, roll):
    """Apply a successful cast to a live target, capturing high order once."""
    return _apply(battle, ident, side, 'qimen', qimen_duration(side, roll))


def _apply(battle, ident, side, condition_kind, count):
    key = _key(ident)
    extension = _extension(battle)
    row = _checked(battle)
    current = battle.get('round')
    units = _units(battle)
    if (not _integer(current, 1, MAX_DAY) or battle.get('outcome') is not None
            or not _live(extension, units, key) or units[key][0] == side
            or condition_kind == 'qimen' and len(units) > 20):
        raise ValueError('Invalid battle condition target or phase')
    if row is None:
        row = dict(schema=SCHEMA, day=current, units={})
        extension['conditions'] = row
    if condition_kind == 'qimen' and 'high_order' not in row:
        row['high_order'] = [str(unit['id']) for army in ('defenders', 'attackers')
                             for unit in battle[army]]
    row['units'][key] = dict(kind=condition_kind, remaining=count)
    return count


def clear(battle, ident):
    """Clear the selected target, including a just-removed transaction unit."""
    key = _key(ident)
    row = _checked(battle, pending_day=True, allow_removed=True)
    if row is None:
        return False
    _prune_order(battle, row)
    if key not in row['units']:
        return False
    del row['units'][key]
    return True


def drop_removed(battle):
    """Remove dead, surrendered and absent units; keep an empty ledger."""
    row = _checked(battle, pending_day=True, allow_removed=True)
    if row is None:
        return []
    extension, units = _extension(battle), _units(battle)
    removed = sorted(key for key, condition in row['units'].items()
                     if not (_present if condition['kind'] == 'qimen' else _live)(extension, units, key))
    for key in removed:
        del row['units'][key]
    _prune_order(battle, row)
    return removed


def _prune_order(battle, row):
    if 'high_order' in row:
        present = set(_units(battle))
        row['high_order'] = [key for key in row['high_order'] if key in present]


def advance_daily(state, battle):
    """Decrement once, after food/30-day termination has been resolved.

    Zero bags do not mean starvation when fractional meal credit survives.
    The food service owns that decision; its terminal phase/outcome stops this
    hook. Replaying one boundary is harmless; skipping multiple days is an
    error rather than retroactively consuming a condition.
    """
    row = _checked(battle, pending_day=True)
    if row is None:
        return []
    current = battle['round']
    if (getattr(state, 'phase', None) != 'battle'
            or battle.get('outcome') is not None or current > MAX_DAY):
        return []
    if current == row['day']:
        return []
    if current != row['day']+1:
        raise ValueError('Invalid battle condition day sequence')
    source = qimen_source(state, battle) if 'high_order' in row else None
    if source is not None and not _integer(state.officers[source].experience, 0, 49999):
        raise ValueError('Invalid Qimen source experience')
    units, changes = {}, []
    for key in sorted(row['units']):
        condition_kind = row['units'][key]['kind']
        if condition_kind == 'qimen':
            units[key] = dict(row['units'][key])
            continue
        before = row['units'][key]['remaining']
        after = before-1
        if after:
            units[key] = dict(kind=condition_kind, remaining=after)
        changes.append(dict(id=key, kind=condition_kind, before=before, remaining=after))
    if source is not None:
        by_id, counter = _units(battle), 0
        for key in row['high_order']:
            condition = units.get(key)
            if condition is None or condition['kind'] != 'qimen':
                continue
            unit = by_id[key][1]
            before, troops = condition['remaining'], unit['troops']
            after = before-1
            requested = 80+state.rng.next()%71
            remaining_troops = max(0, troops-requested)
            unit['troops'] = remaining_troops
            counter += remaining_troops%256
            if after:
                units[key] = dict(kind='qimen', remaining=after)
            else:
                del units[key]
            changes.append(dict(id=key, kind='qimen', before=before, remaining=after,
                troops_before=troops, troops_after=remaining_troops, loss=troops-remaining_troops))
        # Explicit remake growth contract: normal capped experience and the
        # current tier function, without mutating immutable profile/battle war.
        from .officers import experience_tier
        officer = state.officers[source]
        officer.experience = min(49999, officer.experience+counter//2)
        officer.tier = experience_tier(officer.experience)
    row.update(day=current, units=units)
    return changes
