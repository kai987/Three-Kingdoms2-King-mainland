"""Resolve starting reserves and historically calibrated active garrisons."""
from collections import defaultdict

from . import capital_openings
from .officers import OFFICER_TROOP_CAP
from .route_hazards import allocate_survivors
from .route_network import available, effective


# Additional percentage points for the named powers at documented mobilizations.
# The figures are game-scale weights. Historical field armies and surrender
# registers describe different parts of a faction's available strength.
_CAMPAIGN_STRENGTH_BONUS = {
    'mainland184-02': {'yellow_turban': 35},  # Hou Han Shu 71, Huangfu Song
    'mainland200-01': {'yuan_shao': 100, 'liu_biao': 8},  # Sanguozhi 6
    'mainland207-09': {'liu_biao': 8},  # Sanguozhi 6
    'mainland208-10': {'wei': 12, 'wu': 10},  # Sanguozhi 54, Red Cliffs
    'mainland211-07-tongguan': {'ma_teng': 25, 'han_sui': 25},  # Sanguozhi 36, Tong Pass
    'mainland212-12': {'liu_zhang': 12},  # Sanguozhi 31, Yi Province
    'mainland215-08': {'wu': 14},  # Sanguozhi 17, Hefei
    'mainland221-07': {'shu': 8, 'wu': 12},  # Sanguozhi 32 and 58, Yiling
    'mainland234-02': {'shu': 16},  # Jin Shu 1, Wuzhang Plains
    'mainland238-01': {'wei': 10, 'gongsun': 18},  # Jin Shu 1, Liaodong
    'mainland263-05': {'wei': 24, 'shu': 18},  # Sanguozhi 28 and 33
}


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


def _uses_dated_economy(data):
    return (data['id'].startswith('mainland')
            and (data.get('main_scenario') or {}).get('city_economy') == 'dated-scenario-economy-v1')


def mobilize_reserves(catalog, *, frontier=None):
    """Transfer a share of existing city reserves to its opening officers."""
    data = catalog.data
    resources, troops = authored(catalog)
    if not _uses_dated_economy(data):
        return resources, troops

    if frontier is None:
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


def resolve(catalog):
    """Return effective opening stocks and officer strengths without drawing RNG."""
    data = catalog.data
    if not _uses_dated_economy(data):
        return authored(catalog)

    frontier = frontier_cities(data)
    resources, troops = mobilize_reserves(catalog, frontier=frontier)
    bonus = _CAMPAIGN_STRENGTH_BONUS.get(data['id'], {})
    for row in data['initial_officers']:
        city, person = row['city'], row['person_id']
        owner = data['initial_owners'][city]
        if owner == 'neutral':
            continue
        increase = (20 if city in frontier else 12) + bonus.get(owner, 0)
        troops[person] = min(OFFICER_TROOP_CAP, troops[person] * (100 + increase) // 100)
    for city in ('henan', 'jingzhao'):
        if city not in resources or not (capital := capital_openings.opening(data, city)):
            continue
        resources[city].update({field: capital[field] for field in resources[city].keys() & capital.keys()})
        roster = [row['person_id'] for row in data['initial_officers'] if row['city'] == city]
        garrison = [troops[person] for person in roster]
        total = sum(garrison)
        target = total * capital['troop_percent'] // 100
        if target < total:
            revised = allocate_survivors(garrison, target, total)
        elif target > total:
            room = [OFFICER_TROOP_CAP - count for count in garrison]
            capacity = sum(room)
            if capacity == 0:
                continue
            additions = allocate_survivors(room, min(target - total, capacity), capacity)
            revised = [count + extra for count, extra in zip(garrison, additions)]
        else:
            continue
        troops.update(zip(roster, revised))
    return resources, troops
