#!/usr/bin/env python3
"""Build playable campaigns from canonical offline sources.

Shared board/person definitions are stored once. Scenarios contain recursive
object differences; lists keep their source order. No earlier generated catalog,
network service, ROM or player save is an input.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import re
import sys
from math import asin, ceil, cos, radians, sin, sqrt
from hashlib import sha256

# Support both the CLI and callers loading this builder by absolute file path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from remake.city_economy import apply_opening_sizes
from route_timing import apply_route_timing
from route_render_source import validate_geometry_sources
from officer_stat_sources import validate_original_virtue

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'game/config/campaigns'
OUTPUT = ROOT / 'game/data/campaigns'
SCENARIO_FILE = re.compile(r'scenarios/[0-9]{3}-[0-9]{2}\.json\Z')


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def write(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def apply_patch(base, patch):
    """Apply explicit set/update/delete operations without changing sources."""
    if not isinstance(base, dict) or not isinstance(patch, dict):
        raise ValueError('Campaign dictionary patch requires objects')
    if set(patch) - {'set', 'update', 'delete'}:
        raise ValueError('Unknown campaign patch operation')
    replacements = patch.get('set', {})
    children = patch.get('update', {})
    removals = patch.get('delete', [])
    if not isinstance(replacements, dict) or not isinstance(children, dict) or not isinstance(removals, list):
        raise ValueError('Invalid campaign patch shape')
    if len(set(removals)) != len(removals) or set(replacements) & set(children) or set(removals) & (set(replacements) | set(children)):
        raise ValueError('Overlapping campaign patch operations')
    result = deepcopy(base)
    for key in removals:
        if key not in result:
            raise ValueError('Deleting unknown campaign field: ' + str(key))
        del result[key]
    for key, value in replacements.items():
        result[key] = deepcopy(value)
    for key, child in children.items():
        if key not in result or not isinstance(result[key], dict):
            raise ValueError('Updating unknown campaign dictionary: ' + str(key))
        result[key] = apply_patch(result[key], child)
    return result


def apply_navigation_sources(data, navigation):
    """One vector road source feeds movement, previews and discovered sea lanes."""
    by_pair = {frozenset((r['from'], r['to'])): r for r in navigation['routes']}
    for field in ('travel_routes', 'sea_routes', 'exploration_routes'):
        for row in data[field]:
            if row['mode'] != 'sea':
                continue
            route = by_pair[frozenset((row['from'], row['to']))]
            draw = deepcopy(route['draw'])
            if route['from'] != row['from']:
                draw = [dict(part, points=list(reversed(part['points']))) for part in reversed(draw)]
            row['draw'] = draw
    for corridor in navigation['land_roads']:
        a, b = corridor['from'], corridor['to']
        if frozenset((a, b)) in {frozenset(e) for e in data['links']}:
            raise ValueError('Duplicate added land corridor')
        first, second = data['city_coordinates'][a], data['city_coordinates'][b]
        lon1, lat1, lon2, lat2 = map(radians, (*first, *second))
        haversine = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
        distance = round(6371.009 * 2 * asin(min(1, sqrt(haversine))) *
                         data['travel_rules']['detours'][corridor['terrain']], 1)
        data['links'].append([a, b])
        data['travel_routes'].append(dict(id=f'{a}:{b}:land', **{'from': a, 'to': b},
            mode='land', terrain=corridor['terrain'], distance_km=distance,
            land_km=distance, sea_km=0,
            days=max(1, ceil(distance / data['travel_rules']['speeds'][corridor['terrain']])),
            draw=deepcopy(corridor['draw']), history=deepcopy(corridor['history'])))
        data['regional_roads'].append(deepcopy(corridor))


def load_sources(*, timing=True):
    navigation = read('game/config/navigation-geometry.json')
    if navigation.get('schema') != 'sea-mask-navigation-geometry-v1':
        raise ValueError('Unknown navigation geometry source')
    geometry = read('game/config/route-geometry.json') if timing else None
    geometry_sha256 = sha256((ROOT/'game/config/route-geometry.json').read_bytes()
                            + (ROOT/'game/route_timing.py').read_bytes()).hexdigest() if timing else None
    if timing:
        validate_geometry_sources(ROOT, geometry['sources'])
    index = json.loads((SOURCE / 'index.json').read_text(encoding='utf-8'))
    people = json.loads((SOURCE / 'people.json').read_text(encoding='utf-8'))
    shared = json.loads((SOURCE / 'shared.json').read_text(encoding='utf-8'))
    original_stats = read('game/config/references/original-officer-stats.json')
    city_scale_rules = read('game/config/city-scale-rules.json')
    original_identities = read('game/config/portrait-identity-map.json')
    if sha256((ROOT/'game/config/portrait-identity-map.json').read_bytes()).hexdigest() != original_stats['identity_source_sha256']:
        raise ValueError('Original officer identity source differs')
    if index.get('schema') != 'tk2-campaign-sources-v1' or people.get('schema') != 'tk2-campaign-people-v1' or shared.get('schema') != 'tk2-campaign-shared-v1':
        raise ValueError('Unknown canonical campaign source schema')
    order, persons = people['order'], people['people']
    if len(order) != 1023 or len(set(order)) != len(order) or set(order) != set(persons):
        raise ValueError('The canonical pool must contain 1023 unique identities')
    if any(persons[pid]['person_id'] != pid for pid in order):
        raise ValueError('Person pool identity mismatch')
    if len(index['scenarios']) != 25:
        raise ValueError('Expected the 25 reviewed playable campaigns')
    catalogs, seen_ids, seen_files = [], set(), set()
    for entry in index['scenarios']:
        name = entry['file']
        if not isinstance(name, str) or SCENARIO_FILE.fullmatch(name) is None or name in seen_files:
            raise ValueError('Invalid or duplicate campaign source file')
        seen_files.add(name)
        source = json.loads((SOURCE / name).read_text(encoding='utf-8'))
        if source.get('schema') != 'tk2-campaign-override-v1' or source.get('id') != entry['id']:
            raise ValueError('Campaign source identity mismatch')
        data = apply_patch(shared['catalog'], source.get('overrides', {}))
        apply_opening_sizes(data, city_scale_rules)
        current_people = apply_patch(persons, source.get('people_overrides', {}))
        if set(current_people) != set(order):
            raise ValueError('A campaign may not add or remove canonical person identities')
        validate_original_virtue(current_people, original_stats, original_identities)
        data['people'] = [current_people[pid] for pid in order]
        apply_navigation_sources(data, navigation)
        if timing:
            apply_route_timing(data, geometry, geometry_sha256)
        expected_id = f'mainland{data["start_year"]}-{data["start_month"]:02d}'
        if data.get('schema') != 'tk2-campaign-v1' or data.get('id') != expected_id or data['id'] != entry['id'] or data['id'] in seen_ids:
            raise ValueError('Invalid or duplicate playable campaign identity')
        if data.get('calendar_rules') != dict(turn_days=10, month_days=30, turn_start_days=[1, 11, 21], monthly_settlement='month_rollover'):
            raise ValueError('Current campaigns require fixed ten-day turns')
        if 'content_generation' in data or data['rules']['city_officer_capacity'] != 99 or data['rules']['battle_officers_per_side'] != 10:
            raise ValueError('Campaign rules do not match the current 99/10 contract')
        if len({p['runtime_id'] for p in data['people']}) != len(order):
            raise ValueError('Duplicate runtime person identity')
        if any(p['person_id'] != pid for pid, p in zip(order, data['people'])):
            raise ValueError('Campaign person override changes an identity')
        if set(data['era_assignments']) != set(order):
            raise ValueError('Every person requires a scenario placement plan')
        seen_ids.add(data['id'])
        catalogs.append(data)
    if index['default'] not in seen_ids:
        raise ValueError('Default campaign is not present')
    return index, catalogs


def build(check=False, output=OUTPUT):
    output = Path(output)
    source_index, catalogs = load_sources()
    paths, summary, files = [], [], {}
    for data in catalogs:
        name = f'{data["start_year"]}-{data["start_month"]:02d}.json'
        files[name] = encoded(data)
        paths.append('campaigns/' + name)
        summary.append(dict(id=data['id'], year=data['start_year'], month=data['start_month'],
            library=len(data['people']), serving=len(data['initial_officers']),
            free=len(data['initial_free_officers']), future=data['coverage']['future_plans'],
            pending=0, capacity=99, reference_classes=data['placement_completion']['reference_classes']))
    index = dict(schema='tk2-campaign-index-v1', catalogs=paths, default=source_index['default'], summary=summary)
    files['index.json'] = encoded(index)
    if check:
        if {p.name for p in output.glob('*.json')} != set(files):
            raise ValueError('Generated campaign files differ from the canonical list')
        for name, raw in files.items():
            if (output / name).read_bytes() != raw:
                raise ValueError('Generated campaign differs: ' + name)
    else:
        output.mkdir(parents=True, exist_ok=True)
        for name, raw in files.items():
            (output / name).write_bytes(raw)
    return index


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=OUTPUT,
        help='Output folder; alternate folders support isolated verification')
    args = parser.parse_args()
    result = build(args.check, args.output)
    print(json.dumps(dict(catalogs=len(result['catalogs']), people_per_catalog=1023,
        capacity=99, check=args.check), ensure_ascii=False))
