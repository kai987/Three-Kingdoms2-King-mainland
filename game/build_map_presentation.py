#!/usr/bin/env python3
"""Rebuild approved city labels and native castle masks without repainting."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
from road_centers import build as build_road_centers

ROOT = Path(__file__).resolve().parents[1]


def road_center_corrections(root, approved):
    """Validate the native raster against its current source and geometry.

    Only compact audit metadata enters the runtime response; rebuilding the
    full SVG remains possible from canonical inputs without historical files.
    """
    here = root / 'game'
    source_bytes = (here / 'config/road-centers.json').read_bytes()
    source = json.loads(source_bytes)
    if source['ground']['asset'] != '/map-source/road-ground.png':
        raise ValueError('Unexpected canonical road ground asset')
    manifest = json.loads((here / 'map-source/road-centers-render.json').read_bytes())
    if manifest.get('schema') != 'tk2-road-center-render-v1':
        raise ValueError('Unknown road-center render manifest')
    shared = json.loads((here / 'config/campaigns/shared.json').read_bytes())
    positions = {city['id']: city['position'] for city in shared['catalog']['cities']}
    position_bytes = json.dumps(positions, ensure_ascii=False, sort_keys=True,
                                separators=(',', ':')).encode('utf-8')
    hash_bytes = lambda content: hashlib.sha256(content).hexdigest()
    hashes = dict(source_sha256=hash_bytes(source_bytes), positions_sha256=hash_bytes(position_bytes),
        baseline_sha256=hash_bytes((here / 'assets/map-navigation.png').read_bytes()),
        ground_sha256=hash_bytes((here / 'map-source/road-ground.png').read_bytes()),
        output_sha256=hash_bytes((here / 'assets/map-road-centers.png').read_bytes()))
    for field, expected in hashes.items():
        if manifest.get(field) != expected:
            raise ValueError('Road-center render does not match current ' + field)
    if source['ground']['sha256'] != hashes['ground_sha256']:
        raise ValueError('Road ground differs from reviewed source')
    if approved.get('map-navigation.png') != hashes['baseline_sha256'] or approved.get('map-road-centers.png') != hashes['output_sha256']:
        raise ValueError('Road-center raster differs from approved map pins')
    geometry = build_road_centers(source, positions)
    return dict(schema='tk2-road-center-corrections-v1',
        backgrounds={'/assets/map-navigation.png': '/assets/map-road-centers.png'},
        render=deepcopy(manifest),
        summary=dict(reviewed_hubs=len(geometry['hubs']),
                     visible_hubs=sum(bool(hub.get('visible_current_png')) for hub in geometry['hubs']),
                     changed_segments=len(geometry['changes']),
                     deleted_spokes=sum(row['deleted'] for row in geometry['changes']),
                     protected_hubs=len(geometry['protected_hubs'])),
        hubs=[{key: hub[key] for key in ('city', 'center', 'old_hub')} for hub in geometry['hubs']])


def build():
    source = json.loads((ROOT / 'game/config/map-source.json').read_text(encoding='utf-8'))
    if source.get('schema') != 'tk2-map-source-v1':
        raise ValueError('Unknown approved map source')
    for name, expected in source['approved_asset_sha256'].items():
        if Path(name).name != name or Path(name).suffix != '.png':
            raise ValueError('Invalid approved map asset name')
        if hashlib.sha256((ROOT / 'game/assets' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Approved map pixels changed: ' + name)
    result = deepcopy(source['presentation'])
    rows = source['native_castle_sprite']['rows']
    for field, color in (('castle_fill_pixels', 6), ('castle_outline_pixels', 2)):
        expected = [[x*4-16, y*4-16] for y, row in enumerate(rows) for x, value in enumerate(row) if value == color]
        if result[field] != expected:
            raise ValueError('Approved castle mask differs from native source rows')
    if result['background_sha256'] != source['approved_asset_sha256']['map-basin.png'] or result['campaign_background_sha256'] != source['approved_asset_sha256']['map-campaign.png']:
        raise ValueError('Presentation refers to different map pixels')
    result['road_center_corrections'] = road_center_corrections(ROOT, source['approved_asset_sha256'])
    (ROOT / 'game/assets/map-presentation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    build()
