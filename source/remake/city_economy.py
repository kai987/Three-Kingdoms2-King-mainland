"""City production and frontier upkeep for authored openings and live turns.

City sizes and production are gameplay settings. Only committed frontier
maintenance debits city stocks.
"""
from copy import deepcopy
from heapq import heappop, heappush

from .route_hazards import route_allowed
from .route_network import effective


FIELDS = ('gold', 'grain', 'reserves')
TIER_MULTIPLIERS = {'normal': 1, 'large': 2, 'giant': 3}
TIER_LABELS = {'normal': '普通城', 'large': '大城', 'giant': '巨城'}


def _scaled(value, numerator, denominator, quantum=1):
    """Integer half-up rounding, matching the dated stock quantum contract."""
    if value == 0:
        return 0
    return max(1, ((2 * value * numerator + denominator * quantum) //
                   (2 * denominator * quantum)) * quantum)


def tier_at(data, city_id, year, month):
    """Resolve an authored date without modifying the opening catalog."""
    rule = data.get('city_scale_rules', {}).get('cities', {}).get(city_id)
    if rule is None:
        return data.get('city_profiles', {}).get(city_id, {}).get('tier', 'normal')
    tier = rule['tier']
    for change in rule.get('changes', []):
        if (year, month) >= tuple(change['from_date']):
            tier = change['tier']
    return tier


def frontier_outpost_at(data, city_id, year, month):
    rule = data.get('frontier_outposts', {}).get(city_id)
    if rule is None or (year, month) < tuple(rule['from_date']):
        return None
    end = rule.get('to_date')
    return rule if end is None or (year, month) < tuple(end) else None


def profile_at(data, city_id, year, month):
    """Return an independent current-date profile, keeping dated provenance."""
    profile = deepcopy(data.get('city_profiles', {}).get(city_id, {}))
    tier = tier_at(data, city_id, year, month)
    profile.update(tier=tier, label=TIER_LABELS[tier])
    if frontier_outpost_at(data, city_id, year, month) is not None:
        profile.update(kind='frontier_outpost', label='边塞据点')
    return profile


def profiles_at(data, year, month):
    return {city_id: profile_at(data, city_id, year, month)
            for city_id in data.get('city_profiles', {})}


def income_at(data, city_id, year, month):
    """Scale opening production directly, never repeatedly compound rounds."""
    income = data.get('city_income', {}).get(city_id)
    if income is None:
        return None
    opening_tier = data.get('city_profiles', {}).get(city_id, {}).get('tier', 'normal')
    tier = tier_at(data, city_id, year, month)
    if tier == opening_tier:
        return dict(income)
    return {field: _scaled(value, TIER_MULTIPLIERS[tier], TIER_MULTIPLIERS[opening_tier])
            for field, value in income.items()}


def incomes_at(data, year, month):
    return {city_id: income_at(data, city_id, year, month)
            for city_id in data.get('city_income', {})}


def _frontier_sponsor(data, city_id, rule, owners, routes, outposts):
    owner = owners[city_id]
    if owner == 'neutral':
        return None
    preferences = [key for key in rule['supply_cities']
                   if owners.get(key) == owner and key not in outposts]
    adjacent = {}
    for route in routes:
        source, target = route['from'], route['to']
        if owners.get(source) != owner or owners.get(target) != owner:
            continue
        adjacent.setdefault(source, []).append((target, route))
        adjacent.setdefault(target, []).append((source, route))

    # Search backward from the outpost to find routes that a rear city can
    # actually use to reach it. The search also supplies a nearest fallback.
    queue, visited = [(0, city_id)], set()
    nearest = None
    while queue:
        days, here = heappop(queue)
        if here in visited:
            continue
        visited.add(here)
        if here not in outposts:
            if not preferences or here == preferences[0]:
                return here
            nearest = nearest or here
        for previous, route in adjacent.get(here, ()):
            if previous not in visited and route_allowed(data, route, previous, here):
                heappush(queue, (days + route['days'], previous))
    return next((key for key in preferences if key in visited), nearest)


def _frontier_upkeep(base, development):
    if development is None:
        return base
    opening = development['baseline']['population']
    return (base * development['population'] + opening - 1) // opening


def frontier_outposts_view(data, state=None):
    """Resolve current or opening maintenance without changing city stocks."""
    ids = data.get('frontier_outposts', {})
    if not ids:
        return {}
    if state is None:
        year, month = data['start_year'], data['start_month']
        owners = {key: data['initial_owners'][key] for key in data['active_cities']}
        development = {}
    else:
        year, month = state.year, state.month
        owners = {key: city.owner for key, city in state.cities.items()}
        development = state.extension.get('city_development', {}).get('cities', {})
    outposts = {key: rule for key in sorted(ids) if key in owners
                if (rule := frontier_outpost_at(data, key, year, month)) is not None}
    if not outposts:
        return {}
    roads = [route for route in effective(data['travel_routes'], owners, year, month)
             if route['mode'] == 'land']
    return {key: dict(monthly_maintenance=_frontier_upkeep(rule['upkeep_gold'], development.get(key)),
                      sponsor_city=_frontier_sponsor(
                          data, key, rule, owners, roads, outposts))
            for key, rule in outposts.items()}


def frontier_maintenance(game, state):
    """Settle facilities from rear-city gold and rations from local stock."""
    outposts = frontier_outposts_view(game.catalog.data, state)
    if not outposts:
        return
    from .domestic import _garrison_troops
    from .map_presentation import city_names
    from .march_supply import cost as ration_cost

    names = city_names(game.catalog, state.year, state.month)
    battling = {unit['id'] for side in ('attackers', 'defenders')
                for unit in state.battle[side]} if state.battle else set()
    days = game.catalog.data['calendar_rules']['month_days']
    for key, row in outposts.items():
        outpost = state.cities[key]
        if outpost.owner == 'neutral':
            continue
        troops = _garrison_troops(game, state, outpost, exclude=battling)
        ration = ration_cost(troops, 0, days)
        fed = min(ration, outpost.grain)
        outpost.grain -= fed
        cost = row['monthly_maintenance']
        sponsor = state.cities.get(row['sponsor_city'])
        if sponsor is not None:
            paid = min(cost, sponsor.gold)
            sponsor.gold -= paid
        if outpost.owner != state.player:
            continue
        if sponsor is None:
            note = f'{names[key]}未连通己方郡城，{cost}金维护费未支付。'
        else:
            unpaid = f'，尚缺{cost - paid}金' if paid < cost else ''
            note = f'{names[sponsor.id]}为{names[key]}支付维护费{paid}金{unpaid}。'
        if ration:
            shortfall = f'，粮草尚缺{ration - fed}' if fed < ration else ''
            note += f'驻军消耗{fed}粮{shortfall}。'
        game._note(state, note)


def opening_development(data, city_id, tier):
    """Use the existing dated economy to set remake development baselines."""
    profile = data.get('city_profiles', {}).get(city_id, {})
    if profile.get('economy_numeric_basis') != 'authorial_remake_balance_not_historical_measurement':
        return {}
    income = data.get('city_income', {}).get(city_id)
    if income is None:
        return {}
    size = TIER_MULTIPLIERS[tier]
    gold, grain = income['gold'], income['grain']
    controlled = data['initial_owners'].get(city_id, 'neutral') != 'neutral'
    # Grain and gold already account for regional geography, war and recovery.
    # Use per-tier production for governance so a capital is not automatically
    # more stable than a prosperous small city.
    stability = (gold + grain // 4) // (4 * size)
    return dict(land=min(850, 40 * size + grain),
                industry=min(850, 36 * size + 2 * gold),
                population=min(8500, 200 * size + 2 * grain + 3 * gold) * 100,
                governance=min(92, (58 if controlled else 47) + stability))


def apply_opening_sizes(data, rules):
    """Apply reviewed settings once to an untransformed canonical source.

    Canonical shared/scenario values retain their authored date/region/history
    effects. Only the changed size multiplier is applied, with the existing
    stock quantums. Generated catalogs record their resolved opening tiers,
    allowing the same helpers to calculate later production without inflation.
    """
    if 'city_scale_rules' in data:
        raise ValueError('City-size opening transformation already applied')
    if rules.get('schema') != 'tk2-city-scale-rules-v1':
        raise ValueError('Unknown city-size rules schema')
    if rules.get('tier_multipliers') != TIER_MULTIPLIERS:
        raise ValueError('Unexpected city-size multipliers')
    profiles = data['city_profiles']
    for city_id, rule in rules['cities'].items():
        if city_id not in profiles or rule['tier'] not in TIER_MULTIPLIERS:
            raise ValueError('Invalid city-size opening rule: ' + city_id)
        if profiles[city_id]['tier'] != rule['source_tier']:
            raise ValueError('Canonical source tier changed: ' + city_id)
        previous = (0, 0)
        for change in rule.get('changes', []):
            date = change['from_date']
            if (not isinstance(date, list) or len(date) != 2 or
                    type(date[0]) is not int or type(date[1]) is not int or
                    not 1 <= date[0] <= 9999 or not 1 <= date[1] <= 12 or
                    tuple(date) <= previous or change['tier'] not in TIER_MULTIPLIERS):
                raise ValueError('Invalid city-size change: ' + city_id)
            previous = tuple(date)
    data['city_scale_rules'] = deepcopy(rules)
    year, month = data['start_year'], data['start_month']
    for city_id, rule in rules['cities'].items():
        profile = profiles[city_id]
        source_tier, tier = profile['tier'], tier_at(data, city_id, year, month)
        numerator, denominator = TIER_MULTIPLIERS[tier], TIER_MULTIPLIERS[source_tier]
        if source_tier != tier:
            for section, quantums in (('initial_city_resources', rules['stock_quantum']),
                                      ('city_income', dict.fromkeys(FIELDS, 1))):
                for field, value in data[section][city_id].items():
                    data[section][city_id][field] = _scaled(value, numerator, denominator, quantums[field])
        profile.update(tier=tier, label=TIER_LABELS[tier],
                       basis='user_authored_remake_city_scale_setting',
                       tier_basis='user_authored_remake_city_scale_setting',
                       tier_date_precision='game_year_boundary_not_historical_city_classification')
