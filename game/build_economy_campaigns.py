#!/usr/bin/env python3
"""Create v14 dated city economies without rewriting any released save catalog.

History sources support event dates/roles only. Every resource coefficient is
explicit remake balance design; no numbers are exported SAN14 opening stocks.
Only new-game stocks and that catalog's monthly income profile are adapted.
Actual campaign ownership, losses, spending, recruitment and RNG remain live.
"""
from collections import Counter
from copy import deepcopy
import hashlib
from math import prod

from build_campaigns import ROOT, read, write

FOLDER = 'main-scenarios-v14/'
FIELDS = ('gold', 'grain', 'reserves')


def phase_at(phases, date):
    """Use the latest whole [year,month] boundary, never a year-only guess."""
    eligible = [phase for phase in phases if tuple(phase['from_date']) <= tuple(date)]
    return eligible[-1] if eligible else None


def scale(base, percentages, quantum):
    """Exact nonnegative rational scaling, rounded half up to an integer unit."""
    numerator = base * prod(percentages)
    denominator = 100 ** len(percentages) * quantum
    return max(quantum, (2 * numerator + denominator) // (2 * denominator) * quantum)


def validate_spec(spec, city_ids):
    if spec['schema'] != 'dated-scenario-economy-v1':
        raise ValueError('Unknown economy policy')
    regions = {}
    for key, region in spec['regions'].items():
        for city in region['cities']:
            if city in regions:
                raise ValueError('Overlapping economic region: ' + city)
            regions[city] = key
    if set(regions) != set(city_ids) or set(spec['city_production']) != set(city_ids):
        raise ValueError('Missing/unknown city economic configuration')
    sources = {row['id'] for row in spec['sources']}
    for phases in [r['periods'] for r in spec['regions'].values()] + list(spec['city_events'].values()):
        dates = [tuple(row['from_date']) for row in phases]
        if dates != sorted(set(dates)):
            raise ValueError('Economic boundaries must be unique and ordered')
        for phase in phases:
            year, month = phase['from_date']
            if type(year) is not int or type(month) is not int or year < 1 or not 1 <= month <= 12:
                raise ValueError('Invalid economic boundary')
            for kind in ('stock_percent', 'income_percent'):
                if set(phase[kind]) != set(FIELDS) or any(type(v) is not int or not 1 <= v <= 200 for v in phase[kind].values()):
                    raise ValueError('Invalid economic percentage')
            if any(ident not in sources for ident in phase.get('sources', [])):
                raise ValueError('Unknown economic source')
    for profile in spec['production_profiles'].values():
        if set(profile['percent']) != set(FIELDS) or any(type(v) is not int or not 1 <= v <= 200 for v in profile['percent'].values()):
            raise ValueError('Invalid production profile')
    if set(spec['city_events']) - set(city_ids):
        raise ValueError('Unknown city event')
    if any(value not in spec['production_profiles'] for value in spec['city_production'].values()):
        raise ValueError('Unknown city production profile')
    return regions


def city_values(previous, spec, city, date, regions=None):
    """Return deterministic opening/monthly resources and display provenance."""
    regions = regions or validate_spec(spec, [row['id'] for row in previous['cities']])
    region_key = regions[city]
    regional = phase_at(spec['regions'][region_key]['periods'], date)
    if regional is None:
        raise ValueError('Scenario precedes the configured regional baseline')
    production_key = spec['city_production'][city]
    production = spec['production_profiles'][production_key]
    event = phase_at(spec['city_events'].get(city, []), date)
    initial, income = {}, {}
    for field in FIELDS:
        for target, old, kind, quantum in (
            (initial, 'initial_city_resources', 'stock_percent', 'stock_quantum'),
            (income, 'city_income', 'income_percent', 'income_quantum'),
        ):
            factors = [production['percent'][field], regional[kind][field]]
            if event is not None:
                factors.append(event[kind][field])
            target[field] = scale(previous[old][city][field], factors,
                                  spec['arithmetic'][quantum][field])
    label = regional['label'] + ('／' + event['label'] if event else '')
    label_ja = regional['label_ja'] + ('／' + event['label_ja'] if event else '')
    profile = dict(economy_reference_date=list(date), economy_region=region_key,
        economy_production=production_key, economy_period_label_tc=label,
        economy_period_label_ja=label_ja, economy_numeric_basis='authorial_remake_balance_not_historical_measurement',
        economy_source_ids=event.get('sources', []) if event else [],
        economy_date_precision=event['date_precision'] if event else regional['date_precision'])
    return initial, income, profile


def build_catalog(previous, spec, config_sha):
    data = deepcopy(previous)
    data.update(id=previous['id'].replace('-v13', '-v14'), content_generation=14)
    date = (data['start_year'], data['start_month'])
    regions = validate_spec(spec, [row['id'] for row in data['cities']])
    for city in data['cities']:
        key = city['id']
        stocks, income, profile = city_values(previous, spec, key, date, regions)
        data['initial_city_resources'][key] = stocks
        data['city_income'][key] = income
        data['city_profiles'][key].update(profile)
    data['city_economy'] = dict(schema=spec['schema'], source_catalog=previous['id'],
        reference_date=list(date), policy_file='game/config/scenario-economy.json',
        policy_sha256=config_sha, numerical_basis='authorial_remake_balance_not_SAN14_export',
        monthly_policy='opening_date_profile_then_actual_campaign_actions_no_historical_stock_resets',
        garrison_policy='released_officer_troops_unchanged_city_totals_follow_actual_roster',
        sources=deepcopy(spec['sources']),
        fictional_adaptation=bool(data['main_scenario'].get('fictional')))
    data['main_scenario']['city_economy'] = spec['schema']
    data['era_metadata']['main_scenario'] = deepcopy(data['main_scenario'])
    data['design_notes'] = [note for note in data['design_notes']
                            if not note.startswith('新增資料只用於新開v13戰役')]
    data['design_notes'].extend(spec['notes'])
    return data


def build():
    index = read('game/data/main-scenarios-v13/index.json')
    path = ROOT / 'game/config/scenario-economy.json'
    spec = read('game/config/scenario-economy.json')
    config_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    paths, summary = [], []
    for original in index['catalogs']:
        previous = read('game/data/' + original)
        data = build_catalog(previous, spec, config_sha)
        target = FOLDER + original.rsplit('/', 1)[-1]
        write('game/data/' + target, data)
        paths.append(target)
        prior_summary = next(row for row in index['summary'] if row['id'] == previous['id'])
        totals = {field: sum(data['initial_city_resources'][key][field] for key in data['active_cities']) for field in FIELDS}
        summary.append(dict(prior_summary, id=data['id'], economy=spec['schema'],
            initial_resource_totals=totals,
            resource_patterns=len(Counter(tuple(data['initial_city_resources'][key][field] for field in FIELDS)
                                          for key in data['active_cities']))))
    result = dict(schema=index['schema'], catalogs=paths,
                  default=index['default'].replace('-v13', '-v14'), summary=summary)
    write('game/data/' + FOLDER + 'index.json', result)
    return result


if __name__ == '__main__':
    import json
    result = build()
    print(json.dumps(dict(catalogs=len(result['catalogs']), default=result['default'])))
