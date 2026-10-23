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
        output_sha256=hash_bytes((here / 'assets/map-road-centers.png').read_bytes()),
        water_render_sha256=hash_bytes((here / 'map-source/water-render.json').read_bytes()))
    for field, expected in hashes.items():
        if manifest.get(field) != expected:
            raise ValueError('Road-center render does not match current ' + field)
    if source['ground']['sha256'] != hashes['ground_sha256']:
        raise ValueError('Road ground differs from reviewed source')
    if approved.get('map-navigation.png') != hashes['baseline_sha256'] or approved.get('map-road-centers.png') != hashes['output_sha256']:
        raise ValueError('Road-center raster differs from approved map pins')
    water = json.loads((here / 'map-source/water-render.json').read_bytes())
    water_config = here / 'config/water-corrections.json'
    inputs = {'game/map-source/road-ground.png', 'game/map-source/terrain-under-water.png',
              'game/map-source/historic-water.svg', 'game/map-source/sea-shadow.svg'}
    if (water.get('schema') != 'tk2-water-render-v1'
            or water.get('config_sha256') != hash_bytes(water_config.read_bytes())
            or set(water.get('sources', {})) != inputs):
        raise ValueError('Water render configuration differs from current source')
    for name, expected in water['sources'].items():
        if hash_bytes((root / name).read_bytes()) != expected:
            raise ValueError('Water render source differs: ' + name)
    if (water['output']['path'] != 'game/map-source/hydrology-ground.png'
            or hash_bytes((here / 'map-source/hydrology-ground.png').read_bytes()) != water['output']['sha256']):
        raise ValueError('Water render ground differs from current source')
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
    # Existing terrain repairs remove baked castles for unopened/abolished
    # nodes. The raster itself is kept intact and shared with water rendering.
    ground = json.loads((ROOT / 'game/map-source/water-render.json').read_bytes())['output']
    result['inactive_castle_ground_sha256'] = ground['sha256']
    bridges_path = ROOT / 'game/assets/map-bridges.json'
    if bridges_path.exists():
        bridges = json.loads(bridges_path.read_bytes())
        if bridges.get('schema') != 'tk2-map-bridges-v1':
            raise ValueError('Unknown road bridge presentation schema')
        if hashlib.sha256((ROOT / 'game/build_map_bridges.cjs').read_bytes()).hexdigest() != bridges['sources']['compiler_sha256']:
            raise ValueError('Road bridges do not match current bridge compiler')
        ground = bridges['sources']['ground']
        if ground['path'] != 'game/map-source/hydrology-ground.png' or hashlib.sha256((ROOT / ground['path']).read_bytes()).hexdigest() != ground['sha256']:
            raise ValueError('Road bridges do not match current river ground')
        if hashlib.sha256((ROOT / 'game/config/road-centers.json').read_bytes()).hexdigest() != bridges['sources']['road_geometry_sha256']:
            raise ValueError('Road bridges do not match current road geometry')
        app_source = (ROOT / 'game/app.js').read_text()
        path_source = app_source[app_source.index('function smoothMapPath('):app_source.index('function mapBackgroundHref(')]
        if hashlib.sha256(path_source.encode()).hexdigest() != bridges['sources']['land_path_sha256']:
            raise ValueError('Road bridges do not match rendered land paths')
        for name, expected in bridges['sources']['catalogs'].items():
            if not name.startswith('game/data/campaigns/') or Path(name).name != name.removeprefix('game/data/campaigns/') or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Road bridges do not match campaign paths')
        result['road_bridges'] = bridges
    (ROOT / 'game/assets/map-presentation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    build()
