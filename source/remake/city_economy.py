"""Shared city-size arithmetic for authored openings and live calendar views.

City tiers are gameplay settings, not historical measurements.  A live size
change affects future production only; this module never touches city stocks,
officers, ownership, the soldier ledger or random-number generators.
"""
from copy import deepcopy


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


def profile_at(data, city_id, year, month):
    """Return an independent current-date profile, keeping dated provenance."""
    profile = deepcopy(data.get('city_profiles', {}).get(city_id, {}))
    tier = tier_at(data, city_id, year, month)
    profile.update(tier=tier, label=TIER_LABELS[tier])
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
