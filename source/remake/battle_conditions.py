"""Original phantom movement restriction, separate from legacy support flags.

Original B155 writes3 for an attacking caster and2 for a defending caster.
Only the completed defender-to-attacker day boundary decrements this clock.
The caller must settle food and battle termination before advancing it, and
must call apply only after an actual successful cast. Nothing here spends AP,
draws RNG, changes troops, or guesses the origin of old stunned/guard values.
"""
from copy import deepcopy

SCHEMA = 'tk2-battle-conditions-v1'
SIDES = ('attackers', 'defenders')
MAX_DAY = 30


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
    if (not isinstance(row, dict) or set(row) != {'schema', 'day', 'units'}
            or row['schema'] != SCHEMA or type(current) is not int or current < 1
            or not _integer(row['day'], 1, min(current, MAX_DAY))
            or not isinstance(row['units'], dict) or len(row['units']) > 20):
        raise ValueError('Invalid battle condition fields')
    if battle.get('outcome') is None:
        allowed = (current-1, current) if pending_day else (current,)
        if row['day'] not in allowed:
            raise ValueError('Invalid battle condition day')
    units = _units(battle)
    for key, condition in row['units'].items():
        if (type(key) is not str or not key or key.strip() != key
                or not isinstance(condition, dict)
                or set(condition) != {'kind', 'remaining'}
                or condition['kind'] != 'phantom'
                or not _integer(condition['remaining'], 1, 3)):
            raise ValueError('Invalid battle condition unit fields')
        if not allow_removed and not _live(extension, units, key):
            raise ValueError('Battle condition references a removed unit')
    return row


def duration(side):
    """Original side128 attacker writes3; side0 defender writes2."""
    if side not in SIDES:
        raise ValueError('Invalid phantom caster side')
    return 3 if side == 'attackers' else 2


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


def movement_blocked(battle, ident):
    """This gate belongs only on tactical movement, never all actions."""
    return remaining(battle, ident) > 0


def apply(battle, ident, side):
    """Apply a successful phantom cast; overwrite rather than stack it.

    Success qualification and AP debit belong to the shared tactic command.
    An old battle receives its optional extension only at this mutation.
    """
    count = duration(side)
    key = _key(ident)
    extension = _extension(battle)
    row = _checked(battle)
    current = battle.get('round')
    units = _units(battle)
    if (not _integer(current, 1, MAX_DAY) or battle.get('outcome') is not None
            or not _live(extension, units, key) or units[key][0] == side):
        raise ValueError('Invalid phantom target or battle phase')
    if row is None:
        row = dict(schema=SCHEMA, day=current, units={})
        extension['conditions'] = row
    row['units'][key] = dict(kind='phantom', remaining=count)
    return count


def clear(battle, ident):
    """Clear the selected target, including a just-removed transaction unit."""
    key = _key(ident)
    row = _checked(battle, pending_day=True, allow_removed=True)
    if row is None or key not in row['units']:
        return False
    del row['units'][key]
    return True


def drop_removed(battle):
    """Remove dead, surrendered and absent units; keep an empty ledger."""
    row = _checked(battle, pending_day=True, allow_removed=True)
    if row is None:
        return []
    extension, units = _extension(battle), _units(battle)
    removed = sorted(key for key in row['units'] if not _live(extension, units, key))
    for key in removed:
        del row['units'][key]
    return removed


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
    units, changes = {}, []
    for key in sorted(row['units']):
        before = row['units'][key]['remaining']
        after = before-1
        if after:
            units[key] = dict(kind='phantom', remaining=after)
        changes.append(dict(id=key, kind='phantom', before=before, remaining=after))
    row.update(day=current, units=units)
    return changes
