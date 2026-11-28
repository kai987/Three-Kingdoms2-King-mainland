"""Versioned AI policy. Experimental stages are scoped to validation runs."""
from contextlib import contextmanager
from contextvars import ContextVar

from . import logistics_rules

FIELD = 'ai_logistics_strategy_version'
PRESSURE = 'ai_logistics_pressure'
POLICY = 'ai_logistics_policy'
V21 = 21
CURRENT = 211
CANDIDATE = 212
VERSIONS_WITH_RELIEF = (CURRENT, CANDIDATE)
DEFAULT_POLICY = None
RELIEF, TRANSPORT, GARRISON, WAR = range(1, 5)
_experiment = ContextVar('logistics_experiment', default=(WAR, True, True, DEFAULT_POLICY))
_observer = ContextVar('logistics_strategy_observer', default=None)


@contextmanager
def experiment(stage, *, army=False, recovery=False, candidate=None):
    token = _experiment.set((stage, army, recovery, candidate))
    try:
        yield
    finally:
        _experiment.reset(token)


def initialize(state):
    stage, army, recovery, candidate = _experiment.get()
    if candidate is not None:
        state.extension.update({FIELD:CANDIDATE, POLICY:dict(candidate)})
    elif stage:
        state.extension[FIELD] = CURRENT if army or recovery else V21


def enabled(state, stage=RELIEF):
    return state.extension.get(FIELD) in (V21, *VERSIONS_WITH_RELIEF) and _experiment.get()[0] >= stage


def army_relief(state):
    return state.extension.get(FIELD) in VERSIONS_WITH_RELIEF and _experiment.get()[1]


def war_recovery(state):
    return state.extension.get(FIELD) in VERSIONS_WITH_RELIEF and _experiment.get()[2]


def staging(state):
    return state.extension.get(FIELD)==CANDIDATE


def occupancy_budget(state):
    return staging(state) and state.extension[POLICY]['occupation']


def validate(game, state):
    fields = state.extension
    if FIELD in fields and (type(fields[FIELD]) is not int or fields[FIELD] not in (V21, *VERSIONS_WITH_RELIEF)
                            or logistics_rules.version(state) != logistics_rules.CURRENT):
        raise ValueError('AI logistics strategy version')
    candidate = fields.get(POLICY)
    if staging(state):
        if (not isinstance(candidate,dict) or set(candidate)!={'occupation','after_six','no_source'}
                or type(candidate['occupation']) is not bool
                or (candidate['after_six'],candidate['no_source']) not in ((55,45),(60,55))):
            raise ValueError('AI logistics candidate settings')
    elif POLICY in fields:
        raise ValueError('Unexpected AI logistics candidate settings')
    from . import war_recovery
    war_recovery.validate(game,state)
    if PRESSURE not in fields:
        return
    rows = fields[PRESSURE]
    if FIELD not in fields or not isinstance(rows, dict) or set(rows) != {'cities', 'factions'}:
        raise ValueError('AI logistics pressure')
    for scope, allowed in (('cities', state.cities), ('factions', game.catalog.factions)):
        table = rows[scope]
        if not isinstance(table, dict) or not set(table) <= set(allowed):
            raise ValueError('AI logistics pressure keys')
        for row in table.values():
            if (not isinstance(row, list) or len(row) != 2
                    or any(type(value) is not int for value in row)
                    or not 1 <= row[1] <= row[0] <= state.turn):
                raise ValueError('AI logistics pressure history')


def pressure(state, scope, key, active, *, write=True):
    """Track consecutive evaluations once per strategic turn, via AI only."""
    table = state.extension.get(PRESSURE, {}).get(scope, {})
    last, streak = table.get(key, (0, 0))
    if write and last == state.turn:
        return streak
    if not active:
        if write:
            table.pop(key, None)
        return 0
    if not write:
        return streak if last >= state.turn - 1 else 0
    if scope not in state.extension.setdefault(PRESSURE, {'cities': {}, 'factions': {}}):
        raise ValueError('Unknown AI logistics pressure scope')
    table = state.extension[PRESSURE][scope]
    count = streak + 1 if last == state.turn - 1 else 1
    table[key] = [state.turn, count]
    return count



@contextmanager
def observing(callback):
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def observed():
    return _observer.get() is not None


def observe(kind, state, **values):
    """Deliver facts at their rule boundary without recording them in the save."""
    callback = _observer.get()
    if callback is not None:
        callback(kind, dict(event_turn=state.turn, event_year=state.year,
                            event_month=state.month, event_day=state.day, **values))
