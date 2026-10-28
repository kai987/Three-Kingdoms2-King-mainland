"""Compile geographic travel times from the same curves drawn on the map.

The map has an artistic, nonuniform projection. Each road or harbour segment
is therefore calibrated to its own geographic endpoints; there is no global
kilometres-per-pixel scale. Existing terrain speeds and hazard rules remain.
"""
from copy import deepcopy
from math import asin, ceil, cos, hypot, isfinite, radians, sin, sqrt


def kilometers(a, b):
    lon1, lat1, lon2, lat2 = map(radians, (*a, *b))
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.009 * 2 * asin(min(1, sqrt(h)))


def metric(part):
    """Validate a compiled curve, including its independently known chord."""
    length, chord = part['length_px'], part['chord_px']
    if (any(type(n) not in (int, float) or not isfinite(n) or n < 0 for n in (length, chord))
            or abs(hypot(part['end'][0]-part['start'][0], part['end'][1]-part['start'][1])-chord) > .002
            or length + .002 < chord or chord == 0 and length > .002):
        raise ValueError('Invalid compiled route curve')
    ratio = max(1, length/chord) if chord else 1
    return dict(mode=part['mode'], length_px=length, chord_px=chord,
                shape_ratio=round(ratio, 9)), ratio


def compile_transit(route, sections, coords, rules):
    """Calibrate each real city section; absent cities can share a bypass.

    All contiguous alternatives have stable identities for in-flight save
    validation, but the runtime exposes only consecutive active city stops.
    The full parent remains the one painted road and is never an extra edge.
    """
    if len(sections) < 2 or route.get('special'):
        return None
    chain = [sections[0]['from']] + [part['to'] for part in sections]
    if len(set(chain)) != len(chain) or chain[0] != route['from'] or chain[-1] != route['to']:
        raise ValueError('Invalid ordered road city sections')
    timed = []
    for index, section in enumerate(sections):
        if section['from'] != chain[index] or len(section['parts']) != 1:
            raise ValueError('Disconnected road city sections')
        entry, ratio = metric(section['parts'][0])
        distance = round(kilometers(coords[section['from']], coords[section['to']])
                         * ratio * rules['detours'][route['terrain']], 1)
        timed.append((distance, entry))
    children = []
    for start in range(len(sections)):
        for end in range(start+1, len(sections)+1):
            distance = round(sum(row[0] for row in timed[start:end]), 1)
            child = {key: deepcopy(value) for key, value in route.items()
                     if key not in ('draw', 'timing_geometry', 'transit_variants')}
            child.update(id=f'{route["id"]}@{start}-{end}',
                         **{'from': chain[start], 'to': chain[end]},
                         parent_route=route['id'], via=chain[start+1:end],
                         distance_km=distance, land_km=distance, sea_km=0,
                         days=max(1, ceil(distance/rules['speeds'][route['terrain']])),
                         timing_geometry=dict(schema='tk2-route-timing-v1',
                                              parts=[deepcopy(row[1]) for row in timed[start:end]]))
            children.append(child)
    route['transit_variants'] = children
    return round(sum(row[0] for row in timed), 1), sum(
        max(1, ceil(row[0]/rules['speeds'][route['terrain']])) for row in timed)


def apply_route_timing(data, geometry, geometry_sha256):
    """Recompute every known/exploration leg; never reuse stored distances."""
    if geometry.get('schema') != 'tk2-route-geometry-v1':
        raise ValueError('Unknown rendered route geometry')
    rules, coords = data['travel_rules'], data['city_coordinates']
    seen = {}
    for field in ('travel_routes', 'sea_routes', 'exploration_routes'):
        for route in data[field]:
            row = geometry['routes'].get(route['id'])
            if row is None or any(row[key] != route[key] for key in ('from', 'to', 'mode')):
                raise ValueError('Missing or mismatched rendered route: ' + route['id'])
            parts = row['parts']
            metrics, ratios = [], []
            for part in parts:
                entry, ratio = metric(part)
                metrics.append(entry)
                ratios.append(ratio)
            a, b = coords[route['from']], coords[route['to']]
            river = 0
            if route['mode'] == 'land':
                if len(parts) != 1 or parts[0]['mode'] != 'land':
                    raise ValueError('Land timing requires one complete road curve')
                land = round(kilometers(a, b) * ratios[0] * rules['detours'][route['terrain']], 1)
                sea = 0
                days = max(1, ceil(land/rules['speeds'][route['terrain']]))
                hazardous_pairs = [{rule.get('from'), rule.get('to')} for key, rule in
                                   data.get('travel_hazards', {}).items()
                                   if key in ('yinping', 'ziwu') and isinstance(rule, dict)]
                if {route['from'], route['to']} not in hazardous_pairs:
                    transit = compile_transit(route, row.get('city_sections', []), coords, rules)
                    if transit:
                        land, days = transit
            elif route['mode'] == 'sea':
                if len(parts) != 3 or [p['mode'] for p in parts] != ['land', 'sea', 'land']:
                    raise ValueError('Sea timing requires both harbour approaches')
                ports = route.get('geo')
                if not ports or len(ports) < 2:
                    raise ValueError('Missing geographic harbour calibration: ' + route['id'])
                land = round((kilometers(a, ports[0])*ratios[0] + kilometers(ports[-1], b)*ratios[2])
                             * rules['detours']['plain'], 1)
                sea = round(kilometers(ports[0], ports[-1])*ratios[1], 1)
                days = max(1, ceil(land/rules['speeds']['plain'])
                           + ceil(sea/rules['speeds']['sea']) + rules['embark_days'])
            elif route['mode'] == 'river':
                segments, ports = route.get('river_segments'), route.get('geo')
                if (not isinstance(segments, list) or not segments or not ports
                        or len(ports) != len(segments)+1
                        or [p['mode'] for p in parts] != ['land']+['river']*len(segments)+['land']):
                    raise ValueError('River timing requires surveyed reaches and both approaches')
                land = round((kilometers(a, ports[0])*ratios[0] + kilometers(ports[-1], b)*ratios[-1])
                             * rules['detours']['plain'], 1)
                water_time = 0
                for i, segment in enumerate(segments):
                    distance = round(kilometers(ports[i], ports[i+1])*ratios[i+1], 1)
                    if distance <= 0 or segment.get('downstream_from') not in (route['from'], route['to']):
                        raise ValueError('Invalid surveyed river reach')
                    flow = 'downstream' if segment['downstream_from'] == route['from'] else 'upstream'
                    speed = rules['river_speeds'][segment['speed_key']][flow]
                    if type(speed) not in (int, float) or not isfinite(speed) or speed <= 0:
                        raise ValueError('Invalid surveyed river speed')
                    segment['distance_km'] = distance
                    river += distance
                    water_time += distance/speed
                sea = 0
                days = max(1, ceil(land/rules['speeds']['plain']) + ceil(water_time) + rules['river_embark_days'])
            else:
                raise ValueError('Unknown travel mode')
            route.update(distance_km=round(land+sea+river, 1), land_km=land, sea_km=sea, days=days,
                         timing_geometry=dict(schema='tk2-route-timing-v1', parts=metrics))
            if route['mode'] == 'river':
                route['river_km'] = round(river, 1)
            values = (land, sea, river, days, metrics)
            if route['id'] in seen and seen[route['id']] != values:
                raise ValueError('One displayed route has inconsistent timing copies')
            seen[route['id']] = values
    data['river_routes'] = [deepcopy(r) for r in data['travel_routes'] if r['mode'] == 'river']
    rules.update(geometry_sha256=geometry_sha256,
                 distance_policy='Geographic endpoint calibration per drawn segment, multiplied by SVG arc/chord ratio and existing land terrain detour; sea legs include both harbour approaches.',
                 resolution='Sum current curve-based edge days, ceil(total/10) ten-day arrivals; hazard multipliers are applied at departure.')
