"""Compare the shipped route timings and both logistics rates in all catalogs."""
from argparse import ArgumentParser
from collections import Counter
import csv
from pathlib import Path

from common import catalogs, to_csv, to_json
from route_inventory import FORMATIONS, _instances, _static_route
from remake import grain_units, logistics_rules as rules, march_supply, route_hazards as hazards
from remake.march_core import backend_status


def export(output, previous=None):
    scenarios = catalogs()
    grouped = _instances(scenarios, 'mainland208-10')
    scenario_totals = {catalog.data['id']: Counter() for catalog in scenarios}
    links, comparisons, reaches = [], [], []
    with grain_units.using():
        for route_key, info in sorted(grouped.items()):
            raw, data = info['raw'], info['data']
            a, b = raw['from'], raw['to']
            directions = ((a, b), (b, a))
            quotes = {}
            for source, target in directions:
                permitted = hazards.route_allowed(data, raw, source, target)
                assert permitted == hazards._python_route_allowed(data, raw, source, target)
                if permitted:
                    for month in range(1, 13):
                        leg = hazards.evaluate_leg(data, raw, source, target, month)
                        assert leg == hazards._python_evaluate_leg(data, raw, source, target, month)
                        quotes[source, month] = leg
            links.append(_static_route(route_key, info, quotes))
            for source, target in directions:
                for month in range(1, 13):
                    leg = quotes.get((source, month))
                    active = info['eligible'][month] if leg else []
                    quote = dict(routes=[leg], days=leg['days']) if leg else None
                    parts = rules.plan(quote, data['travel_rules']) if quote else []
                    ticks = rules.time_by_mode(parts)
                    cargo, remainder = rules.estimate_cargo(100_000, parts, quote['days']) if leg else (None, None)
                    orientation = 'catalog' if source == a else 'reverse'
                    row = dict(route_key=route_key, route_id=raw['id'], orientation=orientation,
                               from_city=source, to_city=target, month=month, mode=raw['mode'],
                               allowed_direction=leg is not None, scenarios_with_open_window=active,
                               declared_scenarios=info['scenarios'], discovery_required=info['kind']=='exploration',
                               days_v1=leg['days'] if leg else None, days_v2=leg['days'] if leg else None,
                               stages=ticks, risk=leg['hazard'] if leg else None,
                               cargo_sent=100_000 if leg else None, cargo_delivered=cargo,
                               cargo_loss_remainder=remainder)
                    for mode in rules.MARCH_SUPPLY_PERCENT:
                        row[f'days_{mode}'] = ticks.get(mode,0)/rules.DAY_TICKS if leg else None
                    for soldiers, officers in FORMATIONS:
                        key = f'{soldiers}_{officers}'
                        v1 = march_supply.cost(soldiers, officers, leg['days']) if leg else None
                        v2 = rules.ceil_div((soldiers+100*officers)*rules.weight(parts),
                                march_supply.denominator()*rules.RATION_SCALE) if leg else None
                        row[f'grain_v1_{key}'] = v1
                        row[f'grain_base_v2_{key}'] = v1
                        row[f'grain_v2_{key}'] = v2
                        row[f'grain_extra_{key}'] = v2-v1 if leg else None
                        row[f'grain_change_percent_{key}'] = round(100*(v2-v1)/v1,3) if v1 else None
                    for ident in active:
                        if info['kind'] == 'configured':
                            scenario_totals[ident].update(open_configured_directions_seasons=1,
                                grain_v1_10000_1=row['grain_v1_10000_1'], grain_v2_10000_1=row['grain_v2_10000_1'])
                        else:
                            scenario_totals[ident].update(discoverable_directions_seasons=1)
                    comparisons.append(row)
                    if leg and raw['mode'] == 'river':
                        for position, (mode, duration) in enumerate(parts, 1):
                            reaches.append(dict(route_key=route_key, route_id=raw['id'], from_city=source,
                                to_city=target, month=month, stage_number=position, stage_mode=mode,
                                day_ticks=duration, days=duration/rules.DAY_TICKS,
                                multiplier_percent=rules.MARCH_SUPPLY_PERCENT[mode],
                                cargo_loss_bps=rules.CARGO_GRAIN_LOSS_BPS[mode],
                                reach_quotes=leg['river_segments'], order_is_travel_direction=True))
    keys = {(row['route_key'], row['orientation'], str(row['month'])) for row in comparisons}
    assert len(keys) == len(comparisons)
    prior_count = None
    if previous:
        with previous.open(encoding='utf-8', newline='') as handle:
            prior = {(row['route_key'],row['orientation'],row['month']):row for row in csv.DictReader(handle)}
        assert prior.keys() <= keys, sorted(prior.keys()-keys)[:10]
        for row in comparisons:
            older=prior.get((row['route_key'],row['orientation'],str(row['month'])))
            if older is None:
                continue
            assert older['allowed_direction'] == str(row['allowed_direction']).lower()
            days=older['travel_days_demo_applies_only_when_available']
            assert (int(days) if days!='null' else None)==row['days_v2'],row['route_key']
        prior_count = len(prior)
    to_csv(output/'travel-routes-v1-v2.csv', links)
    to_csv(output/'route-seasonal-costs-v1-v2.csv', comparisons)
    to_csv(output/'river-segment-supply-v2.csv', reaches)
    to_csv(output/'scenario-logistics-summary.csv', (
        dict(scenario_id=c.data['id'], scenario_sha256=c.sha256, reference_year=c.data['start_year'],
             **scenario_totals[c.data['id']]) for c in scenarios))
    result = dict(scenarios=len(scenarios), routes=len(links), old_keys_matched=prior_count,
                  directional_seasonal_cases=len(comparisons), formation_columns=len(FORMATIONS),
                  blocked_directions_seasonal=sum(not row['allowed_direction'] for row in comparisons),
                  mixed_segment_rows=len(reaches), backend=backend_status())
    to_json(output/'route-validation.json', result)
    print(result)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    arguments = parser.parse_args()
    export(arguments.output, arguments.previous)
