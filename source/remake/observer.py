"""Identify the observer seat and derive its result from the strategic map."""

SEAT = 'observer'


def winner(state):
    owners = {city.owner for city in state.cities.values()}
    if len(owners) == 1 and 'neutral' not in owners:
        return next(iter(owners))
    return None


def outcome(state):
    if winner(state) is not None:
        return 'victory'
    if all(city.owner == 'neutral' for city in state.cities.values()):
        return 'defeat'
    return None
