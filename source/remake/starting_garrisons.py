"""Allocate the dated opening garrison from each city's existing reserves."""
from collections import defaultdict

from .officers import OFFICER_TROOP_CAP
from .route_network import available, effective


def frontier_cities(data):
    active = set(data['active_cities'])
    owners = data['initial_owners']
    year, month = data['start_year'], data['start_month']
    frontier = set()
    for route in effective(data.get('travel_routes', ()), active, year, month):
        a, b = route['from'], route['to']
        if (a in active and b in active and owners[a] != owners[b]
                and 'neutral' not in (owners[a], owners[b])
                and available(route, year, month)):
            frontier.update((a, b))
    return frontier


def authored(catalog):
    data = catalog.data
    resources = {city: dict(data.get('initial_city_resources', {}).get(
        city, data['initial_resources'])) for city in data['active_cities']}
    troops = {row['person_id']: row['troops'] for row in data['initial_officers']}
    return resources, troops


def resolve(catalog):
    """Return effective opening stocks and officer strengths, without drawing RNG."""
    data = catalog.data
    resources, troops = authored(catalog)
    if (not data['id'].startswith('mainland')
            or (data.get('main_scenario') or {}).get('city_economy') != 'dated-scenario-economy-v1'):
        return resources, troops

    frontier = frontier_cities(data)
    garrisons = defaultdict(list)
    for row in data['initial_officers']:
        garrisons[row['city']].append(row['person_id'])

    def command_score(pid):
        profile = catalog.profiles[catalog.ids[pid]]
        return max(profile.martial_strength, profile.intellect * 9 // 10)

    for city, roster in garrisons.items():
        is_front = city in frontier
        military_center = data.get('city_profiles', {}).get(city, {}).get('economy_production') == 'military'
        budget_percent = (60 if military_center else 55) if is_front else 25
        budget = resources[city]['reserves'] * budget_percent // 100
        remaining = budget
        scores = {pid: command_score(pid) for pid in roster}
        ranked = sorted(roster, key=lambda pid: (-scores[pid], catalog.ids[pid]))

        def assign(pid, amount):
            nonlocal remaining
            amount = min(amount, remaining, max(0, OFFICER_TROOP_CAP - troops[pid]))
            troops[pid] += amount
            remaining -= amount

        # A frontline formation gives its main field commanders the larger
        # contingents. Other officers still share the city's mobilization.
        if is_front:
            for pid, share in zip(ranked, (45, 20)):
                if scores[pid] >= 75:
                    assign(pid, budget * share // 100)
        weights = {pid: max(10, scores[pid] - 35) for pid in ranked}
        weight_total = sum(weights.values())
        shared = remaining
        for pid in ranked:
            assign(pid, shared * weights[pid] // weight_total)
        resources[city]['reserves'] -= budget - remaining
    return resources, troops
