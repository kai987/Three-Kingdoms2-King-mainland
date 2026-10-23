"""Shared JSON byte parsing; transport layers own body size and error replies.

Keep HTTP and browser-worker requests consistent without importing either
transport, campaign state, or save handling into this module.
"""
import json
import math


MAX_JSON_DEPTH = 64


class DepthLimitError(ValueError):
    """Let each transport retain its existing depth-limit error response."""


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key] = item
    return value


def _finite_number(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('Non-finite JSON number')
    return value


def _reject_constant(unused):
    raise ValueError('Non-finite JSON constant')


def loads(raw):
    """Decode UTF-8 bytes, rejecting deep, ambiguous or non-finite JSON."""
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise DepthLimitError('JSON nesting limit')
        elif char in (93, 125):
            depth -= 1
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
                      parse_float=_finite_number, parse_constant=_reject_constant)
