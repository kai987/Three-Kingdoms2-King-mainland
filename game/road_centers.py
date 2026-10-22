"""Pure presentation builder for reviewed city hubs and local road corridors.

The caller owns source loading, approved-asset verification and output writing.
This module never reads historical files, campaign data, images or saves.
"""
from copy import deepcopy
from math import hypot, isfinite
import re


def _point(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(n) not in (int, float) or not isfinite(n) for n in value)):
        raise ValueError('Road coordinates must be finite number pairs')
    return tuple(value)


def _number(value):
    return '0' if value == 0 else format(value, '.15g')


def _xy(point):
    return ' '.join(_number(n) for n in point)


def _rounded(points, radius):
    """The approved renderer cuts at min(radius, .32 of either adjacent leg)."""
    if len(points) < 2:
        return ''
    result = 'M' + _xy(points[0])
    for a, p, b in zip(points, points[1:], points[2:]):
        before, after = hypot(p[0]-a[0], p[1]-a[1]), hypot(b[0]-p[0], b[1]-p[1])
        cut = min(radius, before * .32, after * .32)
        if not before or not after or not cut:
            result += 'L' + _xy(p)
            continue
        entry = (p[0] + (a[0]-p[0])*cut/before, p[1] + (a[1]-p[1])*cut/before)
        exit_ = (p[0] + (b[0]-p[0])*cut/after, p[1] + (b[1]-p[1])*cut/after)
        result += 'L' + _xy(entry) + 'Q' + _xy(p) + ' ' + _xy(exit_)
    return result + 'L' + _xy(points[-1])


def _path(points, radius, centers):
    # Collapsing an explicit node may produce consecutive copies of its city
    # center. They have no length and must not introduce a corner or loop.
    unique = []
    for point in points:
        if not unique or point != unique[-1]:
            unique.append(point)
    if len(unique) < 2:
        return ''
    # A center is an actual arrival, never an off-curve Q control point.
    start, parts = 0, []
    for index in range(1, len(unique)):
        if index == len(unique)-1 or unique[index] in centers:
            parts.append(_rounded(unique[start:index+1], radius))
            start = index
    return ''.join(parts)


_START = re.compile(r'^\s*M\s*([-+]?\d+(?:\.\d+)?)\s*[, ]\s*([-+]?\d+(?:\.\d+)?)')


def _old_wuwei(path):
    match = _START.match(path)
    return match is not None and tuple(map(float, match.groups())) == (124, 120)


def build(source, positions):
    """Return local erasure/repaint metadata without changing any input.

    Saved ``nodes_to_collapse`` use exact equality, and ``corridor_repairs``
    replace only named source strokes. Display positions supply city centers;
    no nearest-city/radius search can pull an unrelated road into a city.
    """
    if source.get('schema') != 'tk2-road-center-source-v1':
        raise ValueError('Unknown reviewed road-center source')
    centers = {city: _point(value) for city, value in positions.items()}
    registered = set(centers.values())
    original = source['original_paths']
    if not isinstance(original, list) or any(not isinstance(path, str) for path in original):
        raise ValueError('Original road paths must be strings')
    segments = {}
    for row in source['segments']:
        index = row['index']
        if type(index) is not int or not 0 <= index < len(original) or index in segments:
            raise ValueError('Invalid or duplicate source segment index')
        points = [_point(p) for p in row['points']]
        radius = row['radius']
        if len(points) < 2 or type(radius) not in (int, float) or not isfinite(radius) or radius < 0:
            raise ValueError('Invalid source road geometry')
        segments[index] = (points, radius)
    mapping, node_cities, deleted = {}, {}, set()
    hubs = deepcopy(source['hubs'])
    for hub in hubs:
        city = hub['city']
        if city not in centers:
            raise ValueError('Unknown city in road-center source')
        hub['center'] = list(centers[city])
        if any(city not in (row['from'], row['to']) for row in hub['logical_relations']):
            raise ValueError('Hub is used by an unrelated logical road')
        nodes = [_point(p) for p in hub['nodes_to_collapse']]
        if not nodes or _point(hub['old_hub']) not in nodes:
            raise ValueError('City hub is absent from its reviewed nodes')
        for node in nodes:
            if node in mapping and (mapping[node] != centers[city] or node_cities[node] != city):
                raise ValueError('A reviewed node belongs to two city hubs')
            mapping[node], node_cities[node] = centers[city], city
        for index in hub['center_branch_segment_indices']:
            if type(index) is not int or index not in segments:
                raise ValueError('Unknown city-center branch segment')
            deleted.add(index)
    for hub in source['protected_hubs']:
        node = _point(hub.get('old_hub', hub.get('junction')))
        if node in mapping:
            raise ValueError('A protected road hub cannot be collapsed')
    for index in deleted:
        points, _ = segments[index]
        first, last = mapping.get(points[0], points[0]), mapping.get(points[-1], points[-1])
        if first != last or first not in registered:
            raise ValueError('Deleted branch does not collapse to one city center')
    # Local, reviewed corridor repairs also replace old forks/parallel strokes.
    # They describe presentation geometry only; no campaign route is rewritten.
    repairs = deepcopy(source.get('corridor_repairs', []))
    overrides, repair_ids, junctions = {}, set(), set(registered)
    for repair in repairs:
        identity, cities = repair['id'], repair['cities']
        if not identity or identity in repair_ids or not cities or any(c not in centers for c in cities):
            raise ValueError('Invalid reviewed road corridor')
        repair_ids.add(identity)
        for row in repair['strokes']:
            index, radius = row['index'], row['radius']
            points = [_point(p) for p in row['points']]
            if (type(index) is not int or index not in segments or index in overrides
                    or len(points) == 1 or type(radius) not in (int, float)
                    or not isfinite(radius) or radius < 0):
                raise ValueError('Invalid reviewed corridor stroke')
            overrides[index] = (points, radius, cities)
            if points:
                # A joining branch must reach the trunk, rather than its
                # rounded-off control point. Shared sections are drawn once.
                junctions.update((points[0], points[-1]))
    changes, replacements = [], {}
    for index, (points, radius) in sorted(segments.items()):
        updated = [mapping.get(point, point) for point in points]
        affected = {node_cities[p] for p in points if p in node_cities}
        if index in overrides:
            updated, radius, cities = overrides[index]
            affected.update(cities)
        if index not in deleted and index not in overrides and updated == points:
            continue
        new_d = '' if index in deleted else _path(updated, radius, junctions)
        remove = not new_d
        if remove:
            updated = []
        changes.append(dict(index=index, old_d=original[index], new_d=new_d,
            old_points=[list(p) for p in points], new_points=[list(p) for p in updated],
            affected_cities=sorted(affected),
            deleted=remove))
        replacements[index] = new_d
    # Preserve the current city connectors verbatim. The two M124 120 paths
    # (a long segment and a zero-length old connector) were both removed when
    # the approved navigation PNG relocated Wuwei; neither may be repainted.
    paint, obsolete = [], []
    for index, path in enumerate(original):
        if _old_wuwei(path):
            obsolete.append(dict(index=index, old_d=path, reason='obsolete_wuwei_origin'))
            continue
        paint.append(replacements.get(index, path))
    # The approved PNG also contains historical harbour approaches which are
    # absent from original_paths. Erase the reviewed obsolete stroke without
    # inserting it into the replacement road network or the timing graph.
    erased = deepcopy(source.get('erased_access_paths', []))
    erased_ids = set()
    for row in erased:
        if (not row.get('id') or row['id'] in erased_ids
                or row.get('city') not in centers
                or not isinstance(row.get('d'), str) or not _START.match(row['d'])
                or not row.get('reason')):
            raise ValueError('Invalid obsolete harbour approach')
        erased_ids.add(row['id'])
    return dict(schema='tk2-road-center-presentation-v1', ground=deepcopy(source['ground']),
        provenance=deepcopy(source['provenance']), hubs=hubs,
        corridor_repairs=repairs,
        protected_hubs=deepcopy(source['protected_hubs']), changes=changes,
        mask_d=''.join(row['old_d'] + row['new_d'] for row in changes) + ''.join(row['d'] for row in erased),
        paint_d=''.join(paint), crossings=deepcopy(source['crossings']),
        removed_obsolete_paths=obsolete, erased_access_paths=erased)
