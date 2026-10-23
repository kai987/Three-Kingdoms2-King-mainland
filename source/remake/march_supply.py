"""Saved travelling rations, distinct from city stores and delivered cargo.

Loading a bag moves grain out of its origin; it does not consume that grain.
Consumption uses cumulative integer arithmetic so short final periods and
repeated arrival processing cannot round up or charge the same day twice.
"""

DENOMINATOR = 1000
OFFICER_UNITS = 100
LIMIT = 100000000
_FIELDS = {'troops', 'officers', 'reserves', 'elapsed_days', 'loaded',
           'consumed', 'remaining', 'from_cargo', 'returned_to_cargo'}


def cost(troops, officers, days, reserves=0):
    return ((troops + OFFICER_UNITS * officers + reserves) * days + DENOMINATOR - 1) // DENOMINATOR


def required_grain(total_troops, officer_count, days, reserves=0):
    return cost(total_troops, officer_count, days, reserves)


def quote_supply(quote, total_troops, officer_count, reserves=0):
    return required_grain(total_troops, officer_count, quote['days'], reserves)


def estimate(state, ids, quote, reserves=0):
    """Pure complete-journey loading budget for both player and AI callers."""
    return cost(sum(state.officers[i].troops for i in ids), len(ids), quote['days'], reserves)


def create(state, ids, quote, reserves=0, *, from_cargo=False):
    troops = sum(state.officers[i].troops for i in ids)
    loaded = cost(troops, len(ids), quote['days'], reserves)
    return dict(troops=troops, officers=len(ids), reserves=reserves, elapsed_days=0,
                loaded=loaded, consumed=0, remaining=loaded,
                from_cargo=loaded if from_cargo else 0, returned_to_cargo=0)


def consume(supply, departure_turn, quote, through_turn):
    """Consume only actual route days elapsed, at most the quoted duration."""
    elapsed = min(quote['days'], max(0, through_turn - departure_turn) * 10)
    if elapsed <= supply['elapsed_days']:
        return 0
    used = cost(supply['troops'], supply['officers'], elapsed, supply['reserves'])
    delta = used - supply['consumed']
    if delta < 0 or delta > supply['remaining']:
        raise ValueError('March supply exhausted or inconsistent')
    supply['elapsed_days'] = elapsed
    supply['consumed'] = used
    supply['remaining'] -= delta
    return delta


def process_march_supply(state, through_turn=None):
    """Ten-day service; call before month income with the next turn number.

    Arrival handlers can call with the default current turn as an idempotent
    catch-up. The service changes no RNG, soldiers, route/weather or city grain.
    """
    through_turn = state.turn if through_turn is None else through_turn
    used = 0
    for row in state.extension.get('travel', {}).get('marches', []):
        used += consume(row['supply'], row['departure_turn'], row['quote'], through_turn)
    for row in state.extension.get('logistics', {}).get('convoys', []):
        journey = row['journeys'][-1]
        used += consume(journey['supply'], journey['departure_turn'], journey['quote'], through_turn)
    return used


def validate(supply, quote, departure_turn, state_turn):
    if not isinstance(supply, dict) or set(supply) != _FIELDS:
        raise ValueError('March supply fields')
    if any(type(value) is not int or not 0 <= value <= LIMIT for value in supply.values()):
        raise ValueError('March supply values')
    if not 0 <= supply['officers'] <= 99 or not 0 <= supply['troops'] <= supply['officers'] * 999:
        raise ValueError('March supply manifest')
    expected_elapsed = min(quote['days'], max(0, state_turn - departure_turn) * 10)
    # The ten-day service commits this cursor with the clock. Allowing an
    # internally consistent older cursor would recreate already eaten grain
    # when the saved force is cancelled and its bag is returned to a city.
    if supply['elapsed_days'] != expected_elapsed:
        raise ValueError('March supply elapsed days')
    loaded = cost(supply['troops'], supply['officers'], quote['days'], supply['reserves'])
    consumed = cost(supply['troops'], supply['officers'], supply['elapsed_days'], supply['reserves'])
    if (supply['loaded'] != loaded or supply['consumed'] != consumed
            or supply['from_cargo'] not in (0, loaded)
            or supply['remaining'] + consumed + supply['returned_to_cargo'] != loaded):
        raise ValueError('March supply arithmetic')
