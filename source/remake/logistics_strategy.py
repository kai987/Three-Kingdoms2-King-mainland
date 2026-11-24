"""Versioned AI policy. Experimental stages are scoped to validation runs."""
from contextlib import contextmanager
from contextvars import ContextVar

from . import logistics_rules

FIELD = 'ai_logistics_strategy_version'
PRESSURE = 'ai_logistics_pressure'
CURRENT = 21
RELIEF, TRANSPORT, GARRISON, WAR = range(1, 5)
_experiment = ContextVar('logistics_experiment', default=WAR)


@contextmanager
def experiment(stage):
    token = _experiment.set(stage)
    try:
        yield
    finally:
        _experiment.reset(token)


def initialize(state):
    if _experiment.get():
        state.extension[FIELD] = CURRENT


def enabled(state, stage=RELIEF):
    return state.extension.get(FIELD) == CURRENT and _experiment.get() >= stage


def validate(game, state):
    fields = state.extension
    if FIELD in fields and (type(fields[FIELD]) is not int or fields[FIELD] != CURRENT
                            or logistics_rules.version(state) != logistics_rules.CURRENT):
        raise ValueError('AI logistics strategy version')
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
