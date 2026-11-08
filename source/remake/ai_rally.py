"""Move neighboring troops to an attack front using ordinary transfers."""
from copy import copy

from . import command_books, historical_campaigns


def _project_arrival(ai, front, officers):
    """Reuse the attack planner with the arriving officers in its city roster."""
    projected_front = copy(front)
    projected_front.roster = copy(front.roster)
    projected_front.roster.officer_ids = [*front.roster.officer_ids, *officers]
    projected = copy(ai)
    projected.state = copy(ai.state)
    projected.state.cities = {**ai.state.cities, front.id: projected_front}
    return projected, projected_front


def _strongest(columns, limit):
    return sorted(columns, key=lambda row: (-row['survivors'], row['quote']['days'], row['source']))[:limit]


def reinforce(ai, city, target):
    """Send only the troops needed to make a neighboring attack viable."""
    state, owner = ai.state, city.owner
    if (target.owner == owner or historical_campaigns.allied(state, owner, target.owner)
            or not command_books.can_spend(state, owner, 'transfer')):
        return False
    # One direct attacker must not strip another of a useful column.
    if target in ai.neighbors(city):
        return False
    fronts = [front for front in ai.neighbors(city)
              if front.owner == owner and target in ai.neighbors(front)]
    if not fronts:
        return False
    officers = ai.army(city, transfer=True)
    if not officers:
        return False

    available_columns = [column for source in state.cities.values()
                         if source.owner == owner and target in ai.neighbors(source)
                         and (column := ai.attack_option(source, target)) is not None]
    limit = min(ai.settings['max_attack_sources'], ai.budget)
    required = max(ai.settings['min_attack_troops'],
                   (ai.strength(target) * ai.settings['attack_ratio_percent'] + 99) // 100)
    if not limit or sum(row['survivors'] for row in _strongest(available_columns, limit)) >= required:
        return False

    choices = []
    for front in fronts:
        # A transfer already underway will be reconsidered on arrival.
        if any(row['owner'] == owner and row['target'] == front.id
               for row in state.extension['travel']['marches']):
            continue
        room = ai.game.catalog.rules.city_officer_capacity - ai.game._city_occupancy(state, front)
        other_columns = [row for row in available_columns if row['source'] != front.id]
        for mode in ('land', 'fastest'):
            quote = ai.quote(city, front, mode, adjacent=False)
            # Project only journeys whose troops can arrive intact.
            if not quote or any(leg.get('hazard') for leg in quote['routes']):
                continue
            selected = []
            for officer in officers:
                if len(selected) >= min(3, room):
                    break
                candidate = [*selected, officer]
                if not ai.safe(quote, candidate) or not ai.provisioned(city, candidate, quote):
                    continue
                selected = candidate
                projected, projected_front = _project_arrival(ai, front, selected)
                column = projected.attack_option(projected_front, target)
                if column is None:
                    continue
                columns = _strongest([*other_columns, column], limit)
                if (column not in columns or sum(row['survivors'] for row in columns) < required
                        or not projected.schedule(columns)):
                    continue
                choices.append((quote['days'], len(selected), front.id, mode, selected))
                break
    if not choices:
        return False
    _, _, front_id, mode, selected = min(choices, key=lambda row: row[:4])
    ai.game._queue_march(state, city, state.cities[front_id], selected, 'transfer', mode)
    ai.game._report_ai(state, city, 'transfer', front_id)
    return True
