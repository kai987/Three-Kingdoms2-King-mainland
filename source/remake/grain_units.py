"""Scope grain denominations to a campaign transaction, including validation."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy

FIELD = 'grain_scale'
CURRENT = 10
_scale = ContextVar('campaign_grain_scale', default=CURRENT)


@contextmanager
def using(state=None):
    """An unmarked save keeps the units of its existing provision receipts."""
    if isinstance(state, dict):
        extension = state.get('extension')
    else:
        extension = state.extension if state is not None else None
    scale = (CURRENT if state is None or isinstance(extension, dict)
             and extension.get(FIELD) == CURRENT else 1)
    token = _scale.set(scale)
    try:
        yield
    finally:
        _scale.reset(token)


def amount(authored):
    return authored * _scale.get()


def denominator():
    return 1_000 // _scale.get()


def stocks(values):
    return dict(values, grain=amount(values['grain']))


def policy(defaults):
    return {key: amount(value) if 'grain' in key else value for key, value in deepcopy(defaults).items()}
