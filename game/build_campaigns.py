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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/officer-placement'))
from remake.city_economy import apply_opening_sizes
from remake.treasures import RULES as TREASURY_RULES
from remake.facilities import RULES as FACILITY_RULES
from remake.equipment import RULES as EQUIPMENT_RULES, build_initials
from route_timing import apply_route_timing
from river_network import build as build_river_network
from route_render_source import validate_geometry_sources
from officer_stat_sources import validate_original_virtue, validate_campaign_stats
from import_campaign_stats import validate_reference as validate_public_reference

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'game/config/campaigns'
OUTPUT = ROOT / 'game/data/campaigns'
SCENARIO_FILE = re.compile(r'scenarios/(?P<date>[0-9]{3}-[0-9]{2})(?:-(?P<variant>[a-z][a-z0-9]*(?:-[a-z0-9]+)*))?\.json\Z')


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

    # Inland reaches have independent flow rules and never enter the sea or
    # unknown-ocean catalogues. Both players and AI read this same link set.
    data['travel_rules'].update(deepcopy(navigation.get('river_rules', {})))
    data['river_routes'] = deepcopy(navigation.get('river_routes', []))
    for river in data['river_routes']:
        river.update(distance_km=1, land_km=0, river_km=1, sea_km=0, days=1)
        data['travel_routes'].append(river)


def load_sources(*, timing=True):
    navigation = read('game/config/navigation-geometry.json')
    if navigation.get('schema') != 'sea-mask-navigation-geometry-v1':
        raise ValueError('Unknown navigation geometry source')
    geometry = read('game/config/route-geometry.json') if timing else None
    geometry_sha256 = sha256((ROOT/'game/config/route-geometry.json').read_bytes()
                            + (ROOT/'game/route_timing.py').read_bytes()).hexdigest() if timing else None
    if timing:
        validate_geometry_sources(ROOT, geometry['sources'])
    river_network = build_river_network()
    if (navigation.get('river_network', {}).get('source_sha256') != river_network['source_sha256']
            or navigation.get('river_routes') != river_network['routes']):
        raise ValueError('Shared river network navigation is stale; rebuild navigation geometry')
    index = json.loads((SOURCE / 'index.json').read_text(encoding='utf-8'))
    people = json.loads((SOURCE / 'people.json').read_text(encoding='utf-8'))
    shared = json.loads((SOURCE / 'shared.json').read_text(encoding='utf-8'))
    original_stats = read('game/config/references/original-officer-stats.json')
    public_stats = read('game/config/references/cnblogs-officer-stats.json')
    san14_abilities = read('game/config/references/san14-abilities.json')
    city_scale_rules = read('game/config/city-scale-rules.json')
    original_identities = read('game/config/portrait-identity-map.json')
    if sha256((ROOT/'game/config/portrait-identity-map.json').read_bytes()).hexdigest() != original_stats['identity_source_sha256']:
        raise ValueError('Original officer identity source differs')
    if index.get('schema') != 'tk2-campaign-sources-v1' or people.get('schema') != 'tk2-campaign-people-v1' or shared.get('schema') != 'tk2-campaign-shared-v1':
        raise ValueError('Unknown canonical campaign source schema')
    order, persons = people['order'], people['people']
    validate_public_reference(public_stats, persons)
    if len(order) < 1023 or len(set(order)) != len(order) or set(order) != set(persons):
        raise ValueError('The canonical pool must retain the released identities and unique additions')
    # The released pool has an intentional runtime hole at1005. New people are
    # appended after1023 rather than renumbering a save-bound historical ID.
    released = [[pid, persons[pid]['runtime_id']] for pid in order[:1023]]
    if sha256(json.dumps(released, separators=(',', ':')).encode()).hexdigest() != '0fb983fdb518092176cd672f32a4c079b6143741b5d6eaee804336b364fdf21d':
        raise ValueError('Released person/runtime identities were renumbered')
    if [persons[pid]['runtime_id'] for pid in order[1023:]] != list(range(1024, len(order) + 1)):
        raise ValueError('New runtime identities must append after the released maximum')
    if any(persons[pid]['person_id'] != pid for pid in order):
        raise ValueError('Person pool identity mismatch')
    if not isinstance(index['scenarios'], list) or not index['scenarios']:
        raise ValueError('Reviewed playable campaigns are required')
    catalogs, seen_ids, seen_files = [], set(), set()
    for entry in index['scenarios']:
        name = entry['file']
        match = SCENARIO_FILE.fullmatch(name) if isinstance(name, str) else None
        if match is None or name in seen_files:
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
        original_people = validate_original_virtue(current_people, original_stats, original_identities)
        stat_counts = validate_campaign_stats(current_people, public_stats, san14_abilities)
        data['coverage'].update(
            virtue=f"SAN14 charisma for{stat_counts['charisma']} people; explicit default60 for{stat_counts['default']} missing sources",
            original_virtue_profiles=0, retained_original_reference_profiles=len(original_people),
            san14_charisma_profiles=stat_counts['charisma'],
            default_virtue_profiles=stat_counts['default'], history_designs_total=0,
            original_initial_health_profiles=stat_counts['original_health'],
            initialization_policy='tk2-officer-initialization-v1')
        old_note = '追加人物的武、知、體力與適性為本作設計值；未具充分德行記錄者沿用用戶指定德60。'
        stat_note = '德採SAN14魅力，缺魅力資料者設60；原表初始體力與勢力語境忠誠分開配置，恢復上限與適性為本作設定。'
        data['design_notes'] = [stat_note if note == old_note else note for note in data['design_notes']]
        data['treasury_rules'] = dict(TREASURY_RULES)
        data['facility_rules'] = deepcopy(FACILITY_RULES)
        data['design_notes'].append('設施包含醫館、學問所、市場與武器屋；費用和成效參考原版說明書及FC公開分析，未證的災害機率與擴展城池配置明列為本作參數。')
        data['design_notes'].append('寶可搜尋、運送、賞賜或每個售100金；初始庫存、搜尋機率與忠誠增幅為本作設定，玩家和AI共用規則。')
        if data.get('main_scenario', {}).get('virtue_default_policy'):
            data['main_scenario']['virtue_default_policy'] = 'campaign-officer-stats-v1'
        data['people'] = [current_people[pid] for pid in order]
        equipment_reference=read('game/config/references/original-equipment-v1.json')
        equipment_appearances=read('game/config/duel-appearances.json')
        data['equipment_rules']=deepcopy(EQUIPMENT_RULES)
        data['equipment_initial']=build_initials(data['people'],equipment_reference['records'],equipment_appearances['profiles'])
        data['design_notes'].append(f"初始裝備按{len(equipment_reference['records'])}名原版對照及名將專屬覆蓋配置；隱藏武具按條件唯一取得，重量會影響單挑命中、回避、先手與退卻。未證的精確倍率為本作規則。")
        apply_navigation_sources(data, navigation)
        if timing:
            apply_route_timing(data, geometry, geometry_sha256)
        date = f'{data["start_year"]}-{data["start_month"]:02d}'
        variant = data.get('scenario_variant')
        if (match['date'] != date or match['variant'] != variant
                or (entry.get('year'), entry.get('month')) != (data['start_year'], data['start_month'])):
            raise ValueError('Campaign date or variant differs from its source entry')
        expected_id = 'mainland' + date + ('-' + variant if variant else '')
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
        name = data['id'].removeprefix('mainland') + '.json'
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
    print(json.dumps(dict(catalogs=len(result['catalogs']), people_per_catalog=result['summary'][0]['library'],
        capacity=99, check=args.check), ensure_ascii=False))
