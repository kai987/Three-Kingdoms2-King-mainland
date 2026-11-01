"""Lossless opening-preview packing; never changes catalog or save identities."""
from collections import Counter
from copy import deepcopy
import json

SCHEMA = 'tk2-scenario-previews-v1'
MAX_EXPANDED_BYTES = 16 * 1024 * 1024
SHARED_FIELDS = frozenset(('world', 'road_additions', 'added_city_ids',
    'regional_roads', 'river_routes', 'city_label_offsets', 'city_history',
    'sea_routes', 'travel_hazards', 'map_cities', 'city_profiles'))


def _key(field, value):
    return field, json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':'))


def pack(rows):
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError('Opening preview rows are required')
    counts = Counter(_key(field, value) for row in rows for field, value in row.items()
                     if field in SHARED_FIELDS)
    pool, slots, result = [], {}, []
    for row in rows:
        values, refs = {}, {}
        for field, value in row.items():
            key = _key(field, value) if field in SHARED_FIELDS else None
            if key and counts[key] > 1 and len(key[1].encode('utf-8')) >= 2048:
                if key not in slots:
                    slots[key] = len(pool)
                    pool.append(dict(field=field, value=value))
                refs[field] = slots[key]
            else:
                values[field] = value
        result.append(dict(values=values, refs=refs))
    return dict(schema=SCHEMA, shared=pool, rows=result)


def unpack(value, *, expected_ids=None):
    def identities(rows):
        if expected_ids is not None:
            ids = [row.get('id') if isinstance(row, dict) else None for row in rows]
            if (any(not isinstance(key, str) for key in ids)
                    or len(ids) != len(set(ids)) or set(ids) != set(expected_ids)):
                raise ValueError('Opening previews must match known scenarios')
    def size(item):
        return len(json.dumps(item, ensure_ascii=False, allow_nan=False,
                              separators=(',', ':')).encode('utf-8'))
    # Local sessions and deliberately small test fixtures still supply rows.
    if isinstance(value, list):
        identities(value)
        if len(value) > 256 or size(value) > MAX_EXPANDED_BYTES:
            raise ValueError('Opening previews exceed expansion budget')
        return deepcopy(value)
    if (not isinstance(value, dict) or set(value) != {'schema', 'shared', 'rows'}
            or value['schema'] != SCHEMA or not isinstance(value['shared'], list)
            or len(value['shared']) > 1024 or not isinstance(value['rows'], list)
            or not 1 <= len(value['rows']) <= 256):
        raise ValueError('Invalid packed opening previews')
    pool = value['shared']
    for item in pool:
        if (not isinstance(item, dict) or set(item) != {'field', 'value'}
                or not isinstance(item['field'], str) or item['field'] not in SHARED_FIELDS):
            raise ValueError('Invalid shared opening-preview field')
    identities([row.get('values') if isinstance(row, dict) else None for row in value['rows']])
    sizes = [size(item['value']) for item in pool]
    planned, expanded = [], 0
    for row in value['rows']:
        if (not isinstance(row, dict) or set(row) != {'values', 'refs'}
                or not isinstance(row['values'], dict) or not isinstance(row['refs'], dict)
                or set(row['values']) & set(row['refs'])):
            raise ValueError('Invalid opening-preview row')
        expanded += size(row['values'])
        for field, index in row['refs'].items():
            if (field not in SHARED_FIELDS or type(index) is not int
                    or not 0 <= index < len(pool) or pool[index]['field'] != field):
                raise ValueError('Invalid opening-preview reference')
            expanded += sizes[index] + len(field.encode('utf-8')) + 8
        if expanded > MAX_EXPANDED_BYTES:
            raise ValueError('Opening previews exceed expansion budget')
        planned.append(row)
    result = []
    for row in planned:
        decoded = deepcopy(row['values'])
        for field, index in row['refs'].items():
            # Preserve independent mutable view containers across scenarios.
            decoded[field] = deepcopy(pool[index]['value'])
        result.append(decoded)
    return result
