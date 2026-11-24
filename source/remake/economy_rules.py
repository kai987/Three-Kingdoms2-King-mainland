"""Versioned agricultural parameters and deterministic production arithmetic."""
from typing import NamedTuple

FIELD = 'economy_rules_version'
LEGACY = 1
CURRENT = 2
POPULATION_REFERENCE = 100_000
POPULATION_POWER = (7, 10)
POPULATION_REFERENCE_MULTIPLIER = 2
LAND_SCALE = 20
LAND_SEGMENTS = ((0, 300, 15), (300, 600, 12), (600, 999, 10))


class TownAgriculture(NamedTuple):
    population_cap: int
    grain_bonus_percent: int
    resident_rate_percent: int


TOWN_AGRICULTURE = {
    1: TownAgriculture(50_000, 3, 3),
    2: TownAgriculture(90_000, 4, 4),
    3: TownAgriculture(150_000, 5, 5),
}


def version(state=None):
    """Unmarked saves retain the economy that shipped before this marker."""
    return CURRENT if state is None else state.extension.get(FIELD, LEGACY)


def validate(state):
    if FIELD in state.extension:
        value = state.extension[FIELD]
        if type(value) is not int or value not in (LEGACY, CURRENT):
            raise ValueError('Economic rules version')
        if value == CURRENT:
            from . import grain_units
            if grain_units.scale() != grain_units.CURRENT or not grain_units.current_rations():
                raise ValueError('Economy V2 grain units')


def effective_population(population, town):
    return min(max(0, population), TOWN_AGRICULTURE[town].population_cap)


def population_multiplier(population):
    exponent, root = POPULATION_POWER
    return POPULATION_REFERENCE_MULTIPLIER * (population / POPULATION_REFERENCE) ** (exponent / root)


def land_yield_units(land):
    land = min(LAND_SEGMENTS[-1][1], max(0, land))
    return sum(max(0, min(land, end) - start) * rate for start, end, rate in LAND_SEGMENTS)


def land_factors(land, opening):
    reference = LAND_SCALE * (60 + opening)
    return max(0, reference + land_yield_units(land) - land_yield_units(opening)), reference


def land_stage(land):
    return next(index for index, (_, end, _) in enumerate(LAND_SEGMENTS, 1)
                if land < end or end == LAND_SEGMENTS[-1][1])


def adjusted_grain(base, population, town, land, opening_land, tax, opening_tax):
    """Floor the combined multiplier exactly, including integral edge cases.

    The floating-point result is only a starting guess. For a nonnegative
    candidate k, compare k^10 with the rational tenth power of the yield.
    """
    effective = effective_population(population, town)
    if not base or not effective:
        return 0
    land_factor, land_reference = land_factors(land, opening_land)
    numerator = base * (100 + TOWN_AGRICULTURE[town].grain_bonus_percent) * land_factor * tax
    denominator = 100 * land_reference * opening_tax
    guess = int(numerator * population_multiplier(effective) / denominator)
    exponent, root = POPULATION_POWER
    powered = (numerator * POPULATION_REFERENCE_MULTIPLIER) ** root * effective ** exponent
    divisor = denominator ** root * POPULATION_REFERENCE ** exponent
    while (guess + 1) ** root * divisor <= powered:
        guess += 1
    while guess ** root * divisor > powered:
        guess -= 1
    return guess
