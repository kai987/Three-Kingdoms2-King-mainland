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


def load_sources():
    index = json.loads((SOURCE / 'index.json').read_text(encoding='utf-8'))
    people = json.loads((SOURCE / 'people.json').read_text(encoding='utf-8'))
    shared = json.loads((SOURCE / 'shared.json').read_text(encoding='utf-8'))
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
        current_people = apply_patch(persons, source.get('people_overrides', {}))
        if set(current_people) != set(order):
            raise ValueError('A campaign may not add or remove canonical person identities')
        data['people'] = [current_people[pid] for pid in order]
        expected_id = f'mainland{data["start_year"]}-{data["start_month"]:02d}'
        if data.get('schema') != 'tk2-campaign-v1' or data.get('id') != expected_id or data['id'] != entry['id'] or data['id'] in seen_ids:
            raise ValueError('Invalid or duplicate playable campaign identity')
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
