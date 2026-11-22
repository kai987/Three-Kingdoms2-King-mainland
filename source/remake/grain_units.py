"""Scope grain denominations to a campaign transaction, including validation."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy

FIELD = 'grain_scale'
CURRENT = 10
RATION_FIELD = 'grain_rations'
RATION_VERSION = 2
_scale = ContextVar('campaign_grain_scale', default=CURRENT)
_rations = ContextVar('campaign_grain_rations', default=RATION_VERSION)


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
    ration_version = extension.get(RATION_FIELD, 1) if isinstance(extension, dict) else 1
    ration_token = _rations.set(RATION_VERSION if state is None else ration_version)
    try:
        yield
    finally:
        _rations.reset(ration_token)
        _scale.reset(token)


def amount(authored):
    return authored * _scale.get()


def scale():
    return _scale.get()


def current_rations():
    return _rations.get() == RATION_VERSION


def denominator():
    return 50 if current_rations() else 1_000 // scale()


def stocks(values):
    return dict(values, grain=amount(values['grain']))


def policy(defaults):
    return {key: amount(value) if 'grain' in key else value for key, value in deepcopy(defaults).items()}
