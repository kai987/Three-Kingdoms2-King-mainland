"""Export physical links, directional runtime quotations and dated availability."""
import json

from common import sha256
from remake import route_hazards as hazards, route_network
from remake.map_presentation import city_names

FORMATIONS = ((1000, 1), (10000, 1), (50000, 5), (100000, 10))
MODES = ('land', 'river', 'sea')
RULE_FIELDS = ('from', 'to', 'mode', 'terrain', 'distance_km', 'land_km', 'river_km',
               'sea_km', 'days', 'river_segments', 'one_way', 'special', 'parent_route',
               'via', 'availability', 'closures', 'discovery_candidate')


def _identity(data, raw, kind):
    endpoints = (raw['from'], raw['to'])
    configuration = {key: raw[key] for key in RULE_FIELDS if key in raw}
    for code in ('travel_hazards', 'travel_rules'):
        configuration[code] = data[code]
    configuration['city_coordinates'] = [data['city_coordinates'].get(key) for key in endpoints]
    configuration['kind'] = kind
    raw_hash = sha256(json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode())
    return f'{raw["id"]}@{raw_hash[:12]}'


def _instances(catalogs, selected):
    result = {}
    for catalog in sorted(catalogs, key=lambda c: (c.data['id'] != selected, c.data['id'])):
        data, scenario = catalog.data, catalog.data['id']
        year = data['start_year']
        names = city_names(catalog, year, data['start_month'])
        for kind, routes in (('configured', data['travel_routes']), ('exploration', data.get('exploration_routes', []))):
            eligible = {}
            for month in range(1, 13):
                active = set(catalog.active_city_ids(year, month))
                eligible[month] = {row['id'] for row in route_network.effective(routes, active, year, month)
                                   if {row['from'], row['to']} <= active}
            for raw in route_network.variants(routes):
                assert raw['from'] in catalog.map_cities and raw['to'] in catalog.map_cities
                assert raw['from'] != raw['to'] and raw['mode'] in MODES and raw['distance_km'] > 0
                key = _identity(data, raw, kind)
                record = result.setdefault(key, dict(raw=raw, data=data, names=names, kind=kind,
                                                    scenarios=[], eligible={m: [] for m in range(1, 13)}))
                record['scenarios'].append(scenario)
                for month, active_routes in eligible.items():
                    if raw['id'] in active_routes:
                        record['eligible'][month].append(scenario)
    return result


def _static_route(route_key, instance, quotes):
    raw, data, names = (instance[k] for k in ('raw', 'data', 'names'))
    source, target = raw['from'], raw['to']
    from_lon, from_lat = data['city_coordinates'].get(source, (None, None))
    to_lon, to_lat = data['city_coordinates'].get(target, (None, None))
    speed = data['travel_rules']['speeds']
    mode = raw['mode']
    april = quotes.get((source, 4))
    river_names = list(dict.fromkeys(seg.get('name_tc', seg.get('river_id')) for seg in raw.get('river_segments', [])))
    effects = [(m, q['hazard']) for (_, m), q in quotes.items() if q['hazard'] is not None]
    return dict(
        route_key=route_key, route_id=raw['id'], from_city_id=source, from_city_name=names[source],
        to_city_id=target, to_city_name=names[target], route_mode=mode, terrain_type=raw['terrain'],
        record_kind=instance['kind'], requires_exploration_or_discovery=instance['kind']=='exploration',
        transit_parent_route=raw.get('parent_route'), transit_substitution=bool(raw.get('transit_variants')),
        bypassed_city_ids=raw.get('via', []), distance_km=raw['distance_km'],
        land_distance_km=raw.get('land_km', 0), river_distance_km=raw.get('river_km', 0),
        sea_distance_km=raw.get('sea_km', 0), river_name='／'.join(river_names) if river_names else None,
        river_flow_direction=april.get('flow') if mode=='river' and april else None,
        base_speed_km_per_day=(april.get('speed_km_per_day') if mode=='river' and april
                               else speed.get(raw['terrain'])),
        base_travel_days=april['days'] if april else None, catalog_static_days=raw['days'],
        embark_days=(data['travel_rules']['river_embark_days'] if mode=='river' else
                     data['travel_rules']['embark_days'] if mode=='sea' else 0),
        disembark_days=None, one_way=not hazards.route_allowed(data, raw, target, source),
        special_route_type=raw.get('special'), seasonal_hazard=sorted({effect['kind'] for _, effect in effects}),
        hazard_months=sorted({m for m, _ in effects}),
        minimum_troop_loss_rate=min([effect['loss_percent_min']/100 for _, effect in effects] + ([0] if len(effects)<len(quotes) else []))
            if effects else 0,
        maximum_troop_loss_rate=max((effect['loss_percent_max']/100 for _, effect in effects), default=0),
        from_longitude=from_lon, from_latitude=from_lat, to_longitude=to_lon, to_latitude=to_lat,
        catalog_scenario_ids=instance['scenarios'], example_scenario_id=data['id'],
        dates_available=raw.get('availability'), closures=raw.get('closures', []),
        configured_history=raw.get('history'), configured_geo_waypoints=raw.get('geo'), river_segments=raw.get('river_segments', []),
    )
