"""Integer logistics profiles for the already quoted physical routes."""
from fractions import Fraction
from math import ceil
from types import MappingProxyType

from . import grain_units

FIELD = 'logistics_rules_version'
LEGACY = 1
CURRENT = 2
DAY_TICKS = 1_000
RATION_SCALE = 100 * DAY_TICKS
LOSS_SCALE = 10_000 * DAY_TICKS
MARCH_SUPPLY_PERCENT = MappingProxyType({
    'plain': 125, 'mountain': 150, 'desert': 150,
    'river_downstream': 105, 'river_still': 110, 'river_upstream': 115,
    'sea': 110, 'embark': 110, 'node_wait': 100,
})
CARGO_GRAIN_LOSS_BPS = MappingProxyType({
    'plain': 50, 'mountain': 100, 'desert': 150,
    'river_downstream': 10, 'river_still': 15, 'river_upstream': 20,
    'sea': 20, 'embark': 0, 'node_wait': 0,
})


def version(state):
    return getattr(state, 'extension', {}).get(FIELD, LEGACY)


def validate(state):
    if FIELD in state.extension and (type(state.extension[FIELD]) is not int
            or state.extension[FIELD] != CURRENT or not grain_units.current_rations()):
        raise ValueError('Logistics rules version')


def ceil_div(numerator, divisor):
    return -(-numerator // divisor)


def _share(days, parts):
    """Partition the existing quoted days in the order travelled.

    Quantize cumulative boundaries, never independently round each reach to a
    whole day. The last boundary is exact even for reversed mixed waterways.
    """
    whole = days * DAY_TICKS
    if not whole:
        return []
    total = sum(weight for _, weight in parts)
    edges = []
    accumulated = previous = 0
    for kind, weight in parts:
        accumulated += weight
        boundary = (whole * accumulated) // total
        if boundary > previous:
            edges.append((kind, boundary - previous))
        previous = boundary
    return edges


def _land_access(leg, days, reverse):
    geometry = leg.get('timing_geometry', {}).get('parts', ())
    if not geometry:
        return days * DAY_TICKS, 0
    parts = list(reversed(geometry)) if reverse else geometry
    indexes = [i for i, part in enumerate(parts) if part['mode'] != 'land']
    if not indexes:
        return days * DAY_TICKS, 0
    leading = sum(Fraction(str(part['length_px'])) for part in parts[:indexes[0]])
    trailing = sum(Fraction(str(part['length_px'])) for part in parts[indexes[-1] + 1:])
    total = (leading + trailing)
    start = int(days * DAY_TICKS * leading / total) if total else days * DAY_TICKS
    return start, days * DAY_TICKS - start


def leg_parts(leg, rules=None):
    """Return (mode, fractional-day ticks) for a directional, immutable leg."""
    days = leg['days']
    if leg['mode'] == 'land':
        return [(leg.get('terrain', 'plain'), days * DAY_TICKS)]
    rules = rules or {}
    plain_speed = rules.get('speeds', {}).get('plain', 30)
    authored = leg.get('id', '').rsplit(':', 3)[-3:-1]
    reverse = authored == [leg.get('to'), leg.get('from')]
    land = leg.get('land_access_days', ceil(leg.get('land_km', 0) / plain_speed))
    embark = leg.get('embark_days', rules.get('embark_days', 2))
    if leg['mode'] == 'river':
        water = leg['water_days']
        embark = leg['embark_days']
        reaches = leg['river_segments']
        if reverse:
            reaches = reversed(reaches)
        parts = [('river_' + reach['flow'],
                  Fraction(str(reach['distance_km'])) / Fraction(str(reach['speed_km_per_day'])))
                 for reach in reaches]
    else:
        # Calm sea quotes retain the calibrated days from the catalog.
        # A monsoon changes that total at departure, while access and embark
        # still use their original settings.
        land = min(land, days)
        embark = min(embark, days - land)
        water = days - land - embark
        parts = [('sea', 1)]
    start, end = _land_access(leg, land, reverse)
    return [(kind, ticks) for kind, ticks in [
        ('plain', start), ('embark', embark * DAY_TICKS), *_share(water, parts), ('plain', end)
    ] if ticks]


def plan(quote, rules=None):
    if not quote.get('routes'):
        return [('node_wait', quote['days'] * DAY_TICKS)]
    parts = [part for leg in quote['routes'] for part in leg_parts(leg, rules)]
    if sum(ticks for _, ticks in parts) != quote['days'] * DAY_TICKS:
        raise ValueError('Logistics stages must cover the quoted days')
    return parts


def time_by_mode(parts, start=0, days=None):
    beginning = start * DAY_TICKS
    ending = None if days is None else beginning + days * DAY_TICKS
    offset = 0
    totals = {}
    for mode, ticks in parts:
        overlap = offset + ticks if ending is None else min(offset + ticks, ending)
        covered = overlap - max(offset, beginning)
        if covered > 0:
            totals[mode] = totals.get(mode, 0) + covered
        offset += ticks
        if ending is not None and offset >= ending:
            break
    return totals


def weight(parts, start=0, days=None, *, rates=MARCH_SUPPLY_PERCENT):
    return sum(rates[mode] * ticks for mode, ticks in time_by_mode(parts, start, days).items())


def charge(units, parts, start, days):
    return units * weight(parts, start, days)


def reverse_prefix(parts, travelled_days):
    """Retrace the part already sailed or walked, without opening reverse orders."""
    left = travelled_days * DAY_TICKS
    traversed = []
    reverse = {'river_downstream': 'river_upstream', 'river_upstream': 'river_downstream'}
    for mode, ticks in parts:
        if not left:
            break
        used = min(left, ticks)
        traversed.append([reverse.get(mode, mode), used])
        left -= used
    return list(reversed(traversed))


def estimate_cargo(grain, parts, days, *, start=0, remainder=0, rates=CARGO_GRAIN_LOSS_BPS):
    for day in range(start, start + days):
        lost, remainder = cargo_loss(grain, weight(parts, day, 1, rates=rates), remainder)
        grain -= lost
    return grain, remainder


def cargo_loss(grain, weighted_bps, remainder):
    lost, remainder = divmod(grain * weighted_bps + remainder, LOSS_SCALE)
    return min(grain, lost), remainder
