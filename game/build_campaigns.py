#!/usr/bin/env python3
"""Build playable campaigns from canonical offline sources.

Shared board/person definitions are stored once. Scenarios contain recursive
object differences; lists keep their source order. No earlier generated catalog,
network service, ROM or player save is an input.
"""
from copy import deepcopy
from collections import Counter
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
from remake.city_economy import TIER_LABELS, TIER_MULTIPLIERS, apply_opening_sizes
from remake.treasures import RULES as TREASURY_RULES
from remake.facilities import RULES as FACILITY_RULES
from remake.equipment import RULES as EQUIPMENT_RULES, build_initials
from route_timing import apply_route_timing
from river_network import build as build_river_network
from road_history import apply_history
from route_render_source import validate_geometry_sources
from officer_stat_sources import validate_original_virtue, validate_campaign_stats
from import_campaign_stats import validate_reference as validate_public_reference

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'game/config/campaigns'
OUTPUT = ROOT / 'game/data/campaigns'
SCENARIO_FILE = re.compile(r'scenarios/(?P<date>[0-9]{3}-[0-9]{2})(?:-(?P<variant>[a-z][a-z0-9]*(?:-[a-z0-9]+)*))?\.json\Z')
# The original raster still uses the 115 centers in shared.json. These cities
# are drawn by the same live sprite renderer at separately reviewed centers.
EXPANSION_CITIES = {
    'hefei': ('合肥', 'jiujiang'),
    'guangling': ('广陵', 'xiapi'),
    'chaisang': ('柴桑', 'yuzhang'),
    'xicheng': ('西城', 'hanzhong'),
    'shangyong': ('上庸', 'xincheng'),
    'yiling': ('夷陵', 'nanjun'),
    'changli': ('昌黎', 'liaodong'),
    'pingyang': ('平阳', 'hedong'),
    'hengyang': ('衡阳', 'changsha'),
    'xiangdong': ('湘东', 'changsha'),
    'jianping': ('建平', 'yidu'),
}
HAN_ANNALS = 'https://zh.wikisource.org/wiki/三國志/卷04'
WU_ANNALS = 'https://www.shidianguji.com/zh/book/LS0004/chapter/1j7fnux22fnsn_304'
EXPANSION_FOUNDINGS = {
    'changli': (244, 9, 'attested_annal_month', '曹魏於244年九月立昌黎縣。', HAN_ANNALS),
    'pingyang': (247, 5, 'attested_annal_month', '平陽為舊縣，247年五月曹魏分河東設郡，本作按立郡開放。', HAN_ANNALS),
    'hengyang': (257, 2, 'attested_annal_month', '孫吳於257年二月分長沙西部置衡陽郡，治湘南。', WU_ANNALS),
    'xiangdong': (257, 2, 'attested_annal_month', '孫吳於257年二月分長沙東部置湘東郡，治酃縣。', WU_ANNALS),
    'jianping': (260, 1, 'attested_year_game_month', '孫吳260年分宜都置郡；史料未載確月，本作以1月為年界。', 'https://zh.wikisource.org/wiki/宋書/卷37'),
}


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


def relocate_opening_officer(data, officer, city_id, owner, basis):
    person_id = officer['person_id']
    officer['city'] = city_id
    era = data['era_assignments'][person_id]
    era.update(city=city_id, faction=owner, placement_basis=basis)
    if isinstance(era.get('posting_reference'), dict):
        era['posting_reference'].update(city=city_id, faction=owner, basis=basis)
    era['appearance_plan']['city'] = city_id
    data['appearance_locations'][person_id] = city_id


def summarize_placement(data):
    """Count effective placements after the shared and scenario sources are merged."""
    people = len(data['people'])
    officers = data['initial_officers']
    serving = len(officers)
    eras = data['era_assignments']
    reviews = [era['placement_review'] for era in eras.values()]
    future = sum(era['appearance_plan']['status'] in ('future_free', 'future')
                 for era in eras.values())
    by_city = Counter(row['city'] for row in officers)
    by_faction = Counter(data['initial_owners'][row['city']] for row in officers)
    for faction in data['factions']:
        faction['initial_officers'] = by_faction[faction['id']]
    data['officer_count'] = people
    data['coverage'].update(
        library=people, configured_profiles=people, health_configured=people,
        affinity_configured=people, placement_plans=len(eras), future_plans=future,
        initial_serving=serving, planned_serving=serving, planned_max_city_roster=max(by_city.values(), default=0),
        initial_free=len(data['initial_free_officers']))
    data['placement_completion'].update(
        people=people, future_plans=future,
        reference_classes=dict(Counter(review['historical_certainty'] for review in reviews)),
        bases=dict(Counter(review['basis'] for review in reviews)))


def apply_city_chronology(data, review, people_by_id):
    """Resolve established sites and reviewed opening posts before expanding the board."""
    scenario = data['id']
    date = (data['start_year'], data['start_month'])
    factions = {row['id'] for row in data['factions']} | {'neutral'}
    for city, owner in review['owners'][scenario].items():
        founding = data['city_foundings'].get(city)
        active = founding is None or date >= (founding['year'], founding['month'])
        if active != (owner is not None) or (active and owner not in factions):
            raise ValueError(f'{scenario}: invalid reviewed opening for {city}')
        if active:
            if city not in data['active_cities']:
                data['active_cities'].append(city)
            data['initial_owners'][city] = owner
        history = data['city_history'][city]
        history['opening'] = dict(
            owner=owner, sources=history['sources'],
            basis=('fictional_scenario_adaptation' if data['main_scenario']['group'] == 'if'
                   else 'reviewed_regional_opening') if active else 'not_yet_open',
            note=('按本開局的區域控制與已知任職配置。' if active else founding['date_note']))

    serving = {row['person_id']: row for row in data['initial_officers']}
    posted = review['garrisons'].get(scenario, {})
    seen = set()
    for city, people in posted.items():
        owner = data['initial_owners'][city]
        for person in people:
            officer = serving.get(person)
            if (person in seen or not officer or officer.get('ruler') or owner == 'neutral'
                    or data['initial_owners'][officer['city']] != owner):
                raise ValueError(f'{scenario}: invalid reviewed post {person} at {city}')
            seen.add(person)
            relocate_opening_officer(data, officer, city, owner, 'attested_expansion_post')

    free = {row['person_id']: row for row in data.get('initial_free_officers', [])}
    for person, city in review['free_locations'].get(scenario, {}).items():
        if person not in free or city not in data['initial_owners']:
            raise ValueError(f'{scenario}: invalid local free officer {person} at {city}')
        relocate_opening_officer(data, free[person], city, None, 'reviewed_local_presence')
        for window in data.get('appearance_windows', {}).get(person, []):
            if tuple(window['start']) <= date <= tuple(window['end']):
                window['city'] = city

    for city in ('wuchang', 'jianan', 'xiping', 'gaoliang'):
        if city not in data['initial_owners']:
            continue
        data['city_history'][city]['garrisons'] = [
            dict(person_id=person, name=people_by_id[person]['name'],
                 basis=('attested_expansion_post' if person in seen else
                        'retained_faction_ruler_seat' if row.get('ruler') else 'expansion_regional_defence'))
            for person, row in serving.items() if row['city'] == city]


def apply_city_expansion(data, locations, opening, notes, people_by_id):
    """Append reviewed cities without editing the inherited map or IF overrides."""
    date = data['start_year'], data['start_month']
    for city_id, (name, parent) in EXPANSION_CITIES.items():
        loc = locations[city_id]
        data['cities'].append(dict(id=city_id, name=name, position=loc['position'], terrain=loc['terrain']))
        data['city_coordinates'][city_id] = loc['coordinates']
        history = data['city_history'].setdefault(city_id, {})
        history.setdefault('detail', notes[city_id]['basis'])
        history['sources'] = list(dict.fromkeys([*history.get('sources', []), *notes[city_id]['sources']]))
        data['added_city_ids'].append(city_id)
        profile = deepcopy(data['city_profiles'][parent])
        parent_scale = TIER_MULTIPLIERS[profile['tier']]
        profile.update(tier='normal', label=TIER_LABELS['normal'], reference_income=None,
                       basis='historical_city_expansion_regional_balance',
                       is_SAN14_starting_resources=False, economy_source_ids=[])
        for key in ('tier_basis', 'tier_date_precision'):
            profile.pop(key, None)
        data['city_profiles'][city_id] = profile
        data['initial_city_resources'][city_id] = {
            field: value // (2 * parent_scale)
            for field, value in data['initial_city_resources'][parent].items()}
        data['city_income'][city_id] = {
            field: value // parent_scale for field, value in data['city_income'][parent].items()}
        if city_id in EXPANSION_FOUNDINGS:
            year, month, precision, note, source = EXPANSION_FOUNDINGS[city_id]
            data['city_foundings'][city_id] = dict(
                year=year, month=month, parent=parent, resource_divisor=4, precision=precision,
                date_note=note, source=source)
            if date < (year, month):
                continue
        data['active_cities'].append(city_id)

    new_active = set(EXPANSION_CITIES) & set(data['active_cities'])
    owners, garrisons = opening['owners'], opening['garrisons']
    factions = {row['id']: row for row in data['factions']}
    if set(owners) != new_active or set(garrisons) != new_active or set(owners.values()) - (set(factions) | {'neutral'}):
        raise ValueError(f'{data["id"]}: expansion opening does not match active cities/factions')
    data['initial_owners'].update(owners)
    data['city_count'] = len(data['cities'])
    officers = {row['person_id']: row for row in data['initial_officers']}
    moves = opening.get('transfers', {})
    attested = opening.get('attested_garrisons', {})
    if set(attested) - new_active:
        raise ValueError(f'{data["id"]}: garrison evidence for inactive city')
    seen, transfers = set(), set()
    for city_id, people in garrisons.items():
        named_posts = set(attested.get(city_id, []))
        if named_posts - set(people):
            raise ValueError(f'{data["id"]}: unassigned attested garrison at {city_id}')
        history = data['city_history'][city_id]
        fictional = data['main_scenario']['group'] == 'if'
        history['opening'] = dict(
            owner=owners[city_id], basis='fictional_scenario_adaptation' if fictional else 'reviewed_regional_opening',
            note=('按假想劇本的既有勢力格局配置。' if fictional
                  else '有任職史料的駐將單列。其餘按當年勢力範圍及可用人物配置。'),
            sources=history['sources'])
        history['garrisons'] = []
        for person_id in people:
            officer = officers.get(person_id)
            if not officer or officer.get('ruler') or person_id in seen or owners[city_id] == 'neutral':
                raise ValueError(f'{data["id"]}: invalid garrison officer {person_id} at {city_id}')
            previous = data['initial_owners'][officer['city']]
            if previous != owners[city_id]:
                if moves.get(person_id) != previous:
                    raise ValueError(f'{data["id"]}: unreviewed garrison transfer of {person_id}')
                transfers.add(person_id)
            seen.add(person_id)
            basis = 'attested_expansion_post' if person_id in named_posts else 'expansion_regional_defence'
            relocate_opening_officer(data, officer, city_id, owners[city_id], basis)
            history['garrisons'].append(dict(
                person_id=person_id, name=people_by_id[person_id]['name'], basis=basis))
    if transfers != set(moves):
        raise ValueError(f'{data["id"]}: unused expansion transfers')


def apply_early_shu_openings(data, opening, people):
    """Assign later reviewed retinue openings and move their men from local reserves."""
    date = data['start_year'], data['start_month']
    if date <= tuple(opening['after']):
        return
    scenario = data['id']
    shu = next((faction for faction in data['factions'] if faction['id'] == 'shu'), None)
    fictional = data['main_scenario']['group'] == 'if'
    active = set(data['active_cities'])
    serving = {row['person_id'] for row in data['initial_officers']}
    free = {row['person_id'] for row in data['initial_free_officers']}
    for person_id, review in opening['people'].items():
        last = tuple(review['last_opening'])
        if date > last:
            continue
        if shu is None:
            raise ValueError(f'{scenario}: reviewed early Shu retainer has no faction')
        city = review.get('stations', {}).get(scenario, shu['city'])
        if (city not in active or data['initial_owners'][city] != 'shu'
                or person_id in serving or person_id in free):
            raise ValueError(f'{scenario}: invalid opening post for {person_id} at {city}')
        resources = data['initial_city_resources'][city]
        troops = 300
        if resources['reserves'] < troops:
            raise ValueError(f'{scenario}: {city} has insufficient reserves for {person_id}')
        resources['reserves'] -= troops
        person = people[person_id]
        resolve = date[0] == person['death_year']
        if not person['service_year'] <= date[0] <= person['death_year']:
            raise ValueError(f'{scenario}: opening post is outside the lifespan of {person_id}')
        data['initial_officers'].append(dict(
            person_id=person_id, city=city, troops=troops, ruler=False, resolve_death_year=resolve))
        note = review['note']
        basis = 'reviewed_early_shu_retainer_opening'
        certainty = 'historical_career_with_opening_station_inference'
        if fictional:
            note += '本篇為假想劇本，按劇本內劉備或蜀漢勢力的城池配置。'
            certainty = 'fictional_scenario_adaptation'
        sources = review['sources']
        data['era_assignments'][person_id] = dict(
            source_status='historical_named_supplement', source_ruler=None, source_city=None,
            status='serving', year_state='available', faction='shu', city=city,
            reason=note, death_year_resolved=resolve, planning_complete=True,
            placement_basis=basis, scenario_membership_basis=basis,
            posting_reference=dict(person_id=person_id, faction='shu', city=city,
                                   basis=basis, source_urls=sources, historical_certainty=certainty),
            membership_revision=dict(basis=basis, note=note, source_urls=sources),
            placement_review=dict(basis=basis, source_urls=sources, note=note,
                                  reference_date=list(date), reference_scenario=scenario,
                                  historical_certainty=certainty),
            appearance_plan=dict(start=list(date), end=list(last), city=city,
                                 status='serving', basis=basis))
        data['appearance_locations'][person_id] = city


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
    san14_dlc_abilities = read('game/config/references/san14-dlc-abilities.json')
    city_scale_rules = read('game/config/city-scale-rules.json')
    city_name_rules = read('game/config/city-name-rules.json')
    city_chronology = read('game/config/campaigns/city-chronology-openings.json')
    expansion_map = read('game/config/campaigns/city-expansion-map.json')['cities']
    expansion_openings = read('game/config/campaigns/city-expansion-openings.json')
    early_shu_openings = read('game/config/campaigns/early-shu-openings.json')
    canonical_index = read('game/config/campaigns/index.json')
    scenario_dates = {row['id']: (row['year'], row['month']) for row in canonical_index['scenarios']}
    scenario_ids = set(scenario_dates)
    if (city_chronology.get('schema') != 'tk2-city-chronology-openings-v1'
            or set(city_chronology['owners']) != scenario_ids
            or any(set(row) != {'wuchang', 'jianan'} for row in city_chronology['owners'].values())
            or (set(city_chronology['garrisons']) | set(city_chronology['free_locations'])) - scenario_ids):
        raise ValueError('Incomplete reviewed city chronology')
    if (expansion_openings.get('schema') != 'tk2-city-expansion-openings-v1'
            or set(expansion_map) != set(EXPANSION_CITIES)
            or set(expansion_openings['scenarios']) != scenario_ids
            or set(expansion_openings['notes']) != set(EXPANSION_CITIES)):
        raise ValueError('Incomplete reviewed historical city expansion')
    original_identities = read('game/config/portrait-identity-map.json')
    if sha256((ROOT/'game/config/portrait-identity-map.json').read_bytes()).hexdigest() != original_stats['identity_source_sha256']:
        raise ValueError('Original officer identity source differs')
    if index.get('schema') != 'tk2-campaign-sources-v1' or people.get('schema') != 'tk2-campaign-people-v1' or shared.get('schema') != 'tk2-campaign-shared-v1':
        raise ValueError('Unknown canonical campaign source schema')
    order, persons = people['order'], people['people']
    validate_public_reference(public_stats, persons)
    dlc_people = {row['person_id'] for row in san14_dlc_abilities['abilities']}
    last_early_opening = tuple(early_shu_openings['after'])
    if (early_shu_openings.get('schema') != 'tk2-early-shu-openings-v1'
            or last_early_opening not in scenario_dates.values()
            or set(early_shu_openings['people']) != dlc_people
            or dlc_people - set(persons)
            or any(tuple(review['last_opening']) not in scenario_dates.values()
                   or any(scenario not in scenario_dates
                          or not last_early_opening < scenario_dates[scenario] <= tuple(review['last_opening'])
                          for scenario in review.get('stations', {}))
                   for review in early_shu_openings['people'].values())):
        raise ValueError('Incomplete reviewed early Shu retainer openings')
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
        for city, rule in city_name_rules.items():
            history = data['city_history'].setdefault(city, {})
            history.update(deepcopy(rule), sources=[*rule['sources'], *history.get('sources', [])])
        current_people = apply_patch(persons, source.get('people_overrides', {}))
        if set(current_people) != set(order):
            raise ValueError('A campaign may not add or remove canonical person identities')
        apply_city_chronology(data, city_chronology, current_people)
        apply_opening_sizes(data, city_scale_rules)
        apply_city_expansion(data, expansion_map, expansion_openings['scenarios'][entry['id']],
                             expansion_openings['notes'], current_people)
        apply_early_shu_openings(data, early_shu_openings, current_people)
        original_people = validate_original_virtue(current_people, original_stats, original_identities)
        stat_counts = validate_campaign_stats(current_people, public_stats, san14_abilities, san14_dlc_abilities)
        data['coverage'].update(
            virtue=f"SAN14 charisma for{stat_counts['charisma']} people; explicit default60 for{stat_counts['default']} missing sources",
            original_virtue_profiles=0, retained_original_reference_profiles=len(original_people),
            san14_charisma_profiles=stat_counts['charisma'], san14_abilities=stat_counts['charisma'],
            default_virtue_profiles=stat_counts['default'], new_historical_people=stat_counts['default'],
            history_designs_total=0,
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
        apply_history(data)
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
        summarize_placement(data)
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
