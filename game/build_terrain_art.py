#!/usr/bin/env python3
"""Composite approved local mountain pixels over the current map, using stdlib only.

The retained transparent crop contains art changes, never an older full-map
background. Current water, banks, road corridors and city boxes take priority.
Run after water/road/route geometry generation; --check never writes files.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import ceil, floor, hypot
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'game/config/terrain-art.json'
COMMAND = 'python3 -B game/build_terrain_art.py'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_portrait_manifest import png_pixels
from road_centers import build as road_geometry
from route_render_source import validate_geometry_sources


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return sha256(value).hexdigest()


def png_encode(size, rgba):
    """Encode a deterministic noninterlaced RGBA PNG without timestamps."""
    width, height = size
    if len(rgba) != width * height * 4:
        raise ValueError('RGBA length does not match terrain dimensions')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    stride = width * 4
    rows = b''.join(b'\0' + rgba[y*stride:(y+1)*stride] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def local(root, name):
    name = Path(name)
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('Terrain paths must be repository-relative')
    return Path(root) / name


def runs_mask(runs, size):
    width, height = size
    mask = bytearray(width * height)
    for row in runs:
        if (not isinstance(row, list) or len(row) != 3
                or any(type(n) is not int for n in row)):
            raise ValueError('Invalid terrain pixel run')
        y, x, length = row
        if not 0 <= y < height or not 0 <= x < width or length <= 0 or x + length > width:
            raise ValueError('Terrain pixel run is outside the map')
        mask[y*width+x:y*width+x+length] = b'\1' * length
    return mask


def dilate(mask, size, radius):
    """Chebyshev pixel margin: exactly radius native pixels on every bank."""
    width, height = size
    if type(radius) is not int or not 0 <= radius <= 16:
        raise ValueError('Invalid terrain protection margin')
    horizontal = bytearray(len(mask))
    for y in range(height):
        start = y * width
        for x in range(width):
            if mask[start+x]:
                left, right = max(0, x-radius), min(width, x+radius+1)
                horizontal[start+left:start+right] = b'\1' * (right-left)
    result = bytearray(len(mask))
    for dy in range(-radius, radius+1):
        for y in range(max(0, -dy), min(height, height-dy)):
            source, target = y*width, (y+dy)*width
            for x in range(width):
                if horizontal[source+x]:
                    result[target+x] = 1
    return result


TOKEN = re.compile(r'[MLQ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')


def svg_polylines(d):
    """Sample the renderer's M/L/Q curves at <=0.5 native-pixel intervals."""
    tokens = TOKEN.findall(d)
    if ''.join(tokens).replace('+', '') != re.sub(r'[\s,]', '', d).replace('+', ''):
        raise ValueError('Unsupported terrain road SVG command')
    at, current, line, result = 0, None, [], []
    def point():
        nonlocal at
        value = (float(tokens[at]), float(tokens[at+1]))
        at += 2
        return value
    while at < len(tokens):
        command = tokens[at]
        at += 1
        if command == 'M':
            if line:
                result.append(line)
            current = point()
            line = [current]
            continue
        if current is None or command not in ('L', 'Q'):
            raise ValueError('Disconnected terrain road SVG')
        if command == 'L':
            end = point()
            steps = max(1, ceil(hypot(end[0]-current[0], end[1]-current[1])*2))
            line.extend((current[0]+(end[0]-current[0])*i/steps,
                         current[1]+(end[1]-current[1])*i/steps) for i in range(1, steps+1))
        else:
            control, end = point(), point()
            steps = max(1, ceil((hypot(control[0]-current[0], control[1]-current[1])
                                 + hypot(end[0]-control[0], end[1]-control[1]))*2))
            for i in range(1, steps+1):
                t = i/steps
                line.append(((1-t)**2*current[0]+2*(1-t)*t*control[0]+t*t*end[0],
                             (1-t)**2*current[1]+2*(1-t)*t*control[1]+t*t*end[1]))
        current = end
    if line:
        result.append(line)
    return result


def protect_paths(mask, size, paths, radius, crop):
    width, height = size
    left, top = crop['x'], crop['y']
    right, bottom = left+crop['width'], top+crop['height']
    for d in set(paths):
        for line in svg_polylines(d):
            for x, y in line:
                if not left-radius <= x < right+radius or not top-radius <= y < bottom+radius:
                    continue
                for yy in range(max(0, floor(y-radius)), min(height, ceil(y+radius)+1)):
                    for xx in range(max(0, floor(x-radius)), min(width, ceil(x+radius)+1)):
                        # Half a pixel guards antialias coverage around the
                        # underlying 4.1px road and 5.4px bridge strokes.
                        if hypot(xx+.5-x, yy+.5-y) <= radius+.5:
                            mask[yy*width+xx] = 1


def render(root=ROOT, config_path=CONFIG):
    root = Path(root)
    config_raw = local(root, config_path).read_bytes()
    config = json.loads(config_raw)
    if config.get('schema') != 'tk2-current-map-terrain-art-v1':
        raise ValueError('Unknown terrain art configuration')
    size = tuple(config['size'])
    if size != (1352, 1024):
        raise ValueError('Terrain art must preserve the native map dimensions')
    art = config['art_source']
    art_raw = local(root, art['path']).read_bytes()
    # Fail before reading any other file if the retained art was changed.
    if digest(art_raw) != art['sha256']:
        raise ValueError('Approved terrain art source hash differs: ' + art['path'])
    crop = art['crop']
    if crop != dict(x=0, y=280, width=288, height=432):
        raise ValueError('Approved mountain crop must retain its native placement')
    _, source_pixels = png_pixels(art_raw, (crop['width'], crop['height']))
    sources = {str(config_path): digest(config_raw), art['path']: digest(art_raw)}
    def read(name):
        raw = local(root, name).read_bytes()
        sources[name] = digest(raw)
        return raw
    for name, expected in config['approval']['source_hashes'].items():
        if digest(read(name)) != expected:
            raise ValueError('Retained mountain approval source hash differs: ' + name)
    _, original_ground = png_pixels(read(config['approval']['immutable_baseline']), size)
    reconstructed_approval = bytearray(original_ground)
    base_raw = read(config['base'])
    _, base_pixels = png_pixels(base_raw, size)
    _, hydrology = png_pixels(read(config['hydrology']), size)
    water = json.loads(read(config['water_render']))
    if (water.get('schema') != 'tk2-water-render-v1'
            or water['output']['path'] != config['hydrology']
            or water['output']['sha256'] != sources[config['hydrology']]):
        raise ValueError('Current hydrology render is stale; rebuild water and roads before terrain art')
    if digest(read('game/config/water-corrections.json')) != water['config_sha256']:
        raise ValueError('Water configuration changed; rebuild water and roads before terrain art')
    for name, expected in water['sources'].items():
        if digest(read(name)) != expected:
            raise ValueError('Water render source changed: ' + name)
    road_render = json.loads(read(config['road_render']))
    if (road_render.get('schema') != 'tk2-road-center-render-v1'
            or road_render['output_sha256'] != sources[config['base']]
            or road_render['water_render_sha256'] != sources[config['water_render']]):
        raise ValueError('Current road render is stale; rebuild roads before terrain art')
    shared = json.loads(read(config['cities']))['catalog']
    positions = {city['id']: city['position'] for city in shared['cities']}
    if len(positions) != 115 or digest(canonical(positions)) != road_render['positions_sha256']:
        raise ValueError('Road render city positions differ from the current 115 cities')
    roads = json.loads(read(config['road_source']))
    if sources[config['road_source']] != road_render['source_sha256']:
        raise ValueError('Road corridor source changed; rebuild roads before terrain art')
    geometry = road_geometry(roads, positions)
    compiled = json.loads(read(config['route_geometry']))
    if compiled.get('schema') != 'tk2-route-geometry-v1':
        raise ValueError('Unknown current route geometry')
    validate_geometry_sources(root, compiled['sources'])
    for name in ('game/build_terrain_art.py', 'game/road_centers.py',
                 'game/build_portrait_manifest.py', 'game/route_render_source.py'):
        read(name)
    width, height = size
    water_mask = runs_mask(water['mask_runs'], size)
    # Corrections mask alone omits unchanged historic water and coastlines.
    for index in range(width*height):
        r, g, b = hydrology[index*4:index*4+3]
        if b >= 120 and b > r+40 and b > g+40:
            water_mask[index] = 1
    protected = dilate(water_mask, size, config['protection']['water_bank_px'])
    # The repair mask also contains erased former spokes. Retain the current
    # restored ground there, rather than letting an old art edge refill it.
    paths = [geometry['paint_d'], geometry['mask_d']]
    paths.extend(crossing['d'] for crossing in geometry['crossings'])
    for route in compiled['routes'].values():
        paths.extend(part['d'] for part in route['parts'] if part['mode'] == 'land')
    protect_paths(protected, size, paths, config['protection']['road_radius_px'], crop)
    half = config['protection']['castle_half_size']
    if half != 16:
        raise ValueError('Current native castle protection must remain 32px')
    for cx, cy in positions.values():
        for y in range(max(0, cy-half), min(height, cy+half)):
            left, right = max(0, cx-half), min(width, cx+half)
            protected[y*width+left:y*width+right] = b'\1' * (right-left)
    allowed = runs_mask(config['approval']['allowed_mask_runs'], size)
    art_mask, applied = bytearray(width*height), bytearray(width*height)
    output = bytearray(base_pixels)
    for y in range(crop['height']):
        for x in range(crop['width']):
            source = (y*crop['width']+x)*4
            pixel = source_pixels[source:source+4]
            if pixel[3] not in (0, 255) or pixel[3] == 0 and pixel[:3] != b'\0\0\0':
                raise ValueError('Mountain source must use hard opacity and zeroed transparent RGB')
            if not pixel[3]:
                continue
            index = (y+crop['y'])*width+x+crop['x']
            if not allowed[index]:
                raise ValueError('Mountain source is outside the approved v1/v2/v3 art mask')
            reconstructed_approval[index*4:index*4+4] = pixel
            art_mask[index] = 1
            if not protected[index]:
                output[index*4:index*4+4] = pixel
                applied[index] = 1
    if sum(art_mask) != config['approval']['art_pixels']:
        raise ValueError('Approved mountain source pixel inventory differs')
    if digest(reconstructed_approval) != config['approval']['original_asset_rgba_sha256']:
        raise ValueError('Transparent crop does not reconstruct the retained approved mountain pixels')
    output = bytes(output)
    png = png_encode(size, output)
    manifest = dict(schema='tk2-current-map-terrain-art-render-v1',
        policy='Current road/water background wins; apply only retained opaque art pixels outside protected corridors.',
        rebuild_command=COMMAND, sources=dict(sorted(sources.items())),
        positions_sha256=digest(canonical(positions)), city_count=len(positions),
        approved_asset_rgba_sha256=config['approval']['original_asset_rgba_sha256'],
        output=dict(path=config['output'], sha256=digest(png), rgba_sha256=digest(output)),
        stats=dict(art_pixels=sum(art_mask), applied_pixels=sum(applied),
                   protected_art_pixels=sum(art_mask)-sum(applied), protected_pixels=sum(protected),
                   outside_art_pixels_unchanged=width*height-sum(art_mask)))
    details = dict(size=size, crop=crop, base_pixels=base_pixels, output_pixels=output,
                   source_pixels=source_pixels, art_mask=art_mask,
                   protected_mask=protected, applied_mask=applied)
    return png, manifest, details


def build(check=False, root=ROOT, config_path=CONFIG):
    root = Path(root)
    config = json.loads(local(root, config_path).read_bytes())
    png, manifest, _ = render(root, config_path)
    rendered = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    output, receipt = local(root, config['output']), local(root, config['manifest'])
    if check:
        if not output.exists() or output.read_bytes() != png or not receipt.exists() or receipt.read_bytes() != rendered:
            raise ValueError('Terrain art is stale; rebuild with ' + COMMAND)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(png)
        receipt.write_bytes(rendered)
    return manifest


def check(root=ROOT, config_path=CONFIG):
    return build(check=True, root=root, config_path=config_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only byte comparison of output and source receipt')
    args = parser.parse_args(argv)
    try:
        manifest = build(check=args.check)
    except (ValueError, KeyError, TypeError, OSError, zlib.error) as error:
        print(f'Terrain art failed: {error}. Rebuild command: {COMMAND}', file=sys.stderr)
        return 1
    print(json.dumps(dict(check=args.check, output=manifest['output'], **manifest['stats']), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
