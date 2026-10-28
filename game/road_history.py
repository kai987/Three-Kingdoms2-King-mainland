"""Attach reviewed historical limits without silently deleting dated routes.

Both opening catalogues and future campaign dates retain the same physical
route inventory. The shared runtime filters explicit availability windows;
uncertain first records and restoration intervals are informational only.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / 'config/road-history.json'


def _date(value):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(n) is not int for n in value)
            or value[0] < 1 or not 1 <= value[1] <= 12):
        raise ValueError('Historical route date must be [year, month]')
    return tuple(value)


def validate_availability(value):
    if not isinstance(value, dict) or not value or set(value) - {'from', 'to'}:
        raise ValueError('Invalid historical route availability')
    start = _date(value['from']) if 'from' in value else None
    end = _date(value['to']) if 'to' in value else None
    if start is not None and end is not None and start >= end:
        raise ValueError('Empty historical route availability interval')


def validate_closures(value):
    if not isinstance(value, list) or not value:
        raise ValueError('Historical road closures require bounded windows')
    intervals = []
    for window in value:
        validate_availability(window)
        if set(window) != {'from', 'to'}:
            raise ValueError('Historical road closures require bounded windows')
        intervals.append((_date(window['from']), _date(window['to'])))
    intervals.sort()
    if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
        raise ValueError('Overlapping historical road closures')


def validate_reference(spec):
    if spec.get('schema') != 'tk2-road-history-v1':
        raise ValueError('Unknown road history reference')
    sources = spec.get('sources')
    if not isinstance(sources, dict) or not sources:
        raise ValueError('Road history requires sources')
    for row in sources.values():
        if (not isinstance(row, dict) or not isinstance(row.get('title'), str)
                or not isinstance(row.get('url'), str) or not row['url'].startswith('https://')):
            raise ValueError('Invalid road history source')
    reviews = spec.get('route_reviews')
    if not isinstance(reviews, dict):
        raise ValueError('Road history requires route reviews')
    for identity, row in reviews.items():
        if (not isinstance(identity, str) or not identity
                or not isinstance(row, dict) or not isinstance(row.get('basis_tc'), str)
                or not isinstance(row.get('basis_ja'), str)
                or not isinstance(row.get('classification'), str)):
            raise ValueError('Invalid road history review')
        if (not isinstance(row.get('source_ids'), list) or not row['source_ids']
                or any(key not in sources for key in row['source_ids'])):
            raise ValueError('Unknown reviewed road source')
        if 'availability' in row:
            validate_availability(row['availability'])
        if 'closures' in row:
            validate_closures(row['closures'])
    for row in spec.get('excluded_military_navigation', []):
        if not row.get('id') or any(key not in sources for key in row.get('source_ids', [])):
            raise ValueError('Invalid excluded military navigation reference')
    return spec


def apply_history(data, spec=None):
    """Enrich matching route copies and validate all authored date windows."""
    raw = SOURCE.read_bytes() if spec is None else None
    spec = validate_reference(json.loads(raw) if spec is None else spec)
    excluded = {row['id'] for row in spec.get('excluded_military_navigation', [])}
    for field in ('travel_routes', 'river_routes', 'sea_routes', 'exploration_routes', 'regional_roads'):
        for route in data.get(field, []):
            if route.get('id') in excluded:
                raise ValueError('Unverified military navigation remains enabled: ' + route['id'])
            row = spec['route_reviews'].get(route.get('id'))
            if row is not None:
                history = route.setdefault('history', {})
                history['review'] = deepcopy(row)
                history['sources'] = list(dict.fromkeys(history.get('sources', [])
                    + [spec['sources'][key]['url'] for key in row['source_ids']]))
                if 'availability' in row:
                    if route.get('availability', row['availability']) != row['availability']:
                        raise ValueError('Conflicting historical route availability')
                    route['availability'] = deepcopy(row['availability'])
                if 'closures' in row:
                    if route.get('closures', row['closures']) != row['closures']:
                        raise ValueError('Conflicting historical road closures')
                    route['closures'] = deepcopy(row['closures'])
            if 'availability' in route:
                validate_availability(route['availability'])
            if 'closures' in route:
                validate_closures(route['closures'])
    data['road_history'] = dict(schema=spec['schema'], review_date=spec['review_date'],
        source_sha256=sha256(raw).hexdigest() if raw is not None else None,
        policy=deepcopy(spec['policy']), sources=deepcopy(spec['sources']),
        excluded_military_navigation=deepcopy(spec.get('excluded_military_navigation', [])),
        deferred_until_surveyed=deepcopy(spec.get('deferred_until_surveyed', [])))
    return data
