#!/usr/bin/env python3
"""Bake imagegen-authored portrait atlases into native 32x40 game assets.

Only image cropping, nearest-neighbor fitting and fixed palette quantization
occur here. No faces, clothing, distinguishing marks or variations are drawn
by code. An original atlas cell is assigned to at most one person. Duplicate
native results may use a documented unused cell of the same art-direction
gender; a failure is reported rather than inventing procedural variations.

Pillow is an offline development dependency, never a game runtime dependency.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'art/portraits/plan.json'
SOURCE = ROOT / 'art/portraits/source-atlases'
DESTINATION = ROOT / 'game/assets/portraits/generated'
MANIFEST = ROOT / 'game/config/portrait-generated.json'
SUPPLEMENT = ROOT / 'art/portraits/historical-additions-v1/plan.json'
SIZE, GRID, CELL = (32, 40), (8, 8), (128, 192)
RGB = ((0, 0, 0), (255, 255, 255), (247, 162, 71), (158, 65, 0))
RGBA = ((0, 0, 0, 0), (255, 255, 255, 255), (247, 162, 71, 255), (158, 65, 0, 255))
POLICY = dict(
    source='imagegen raster art only; no procedurally drawn faces',
    cell_partition='logical8x8 order; actual boundaries are midpoints of full-atlas black separator bands, minimum3px vertical or8px horizontal; exactly9 bands per axis including outer margins required',
    visible_box='all nonzero palette pixels in the actual partition; visible pixels must not touch any partition edge; no component removed',
    black_threshold='alpha below128 or maximum RGB channel at most32 -> transparent',
    quantization='nearest squared RGB distance to black/white/orange/brown; ties choose lower index; no dithering',
    fit='contain in30x38, aspect preserved; bottom aligned with1px black margin and horizontally centered',
    resampling='Pillow NEAREST; no interpolation, sharpening, or geometry edits',
    palette_rgba=[list(color) for color in RGBA],
    display_background='#000000',
    uniqueness='native RGBA SHA256 must be unique; same-gender unused-cell fallback only',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=65536)
def palette_pixel(red, green, blue):
    if max(red, green, blue) <= 32:
        return 0
    return min(range(4), key=lambda n: sum((a - b) ** 2 for a, b in zip((red, green, blue), RGB[n])))


def png(rgba, size=SIZE):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    width, height = size
    rows = b''.join(b'\0' + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def prepare_atlas(atlas, grid=GRID):
    """Recover the authored grid without cutting hats at nominal 192px rows.

    Imagegen preserves black inter-person gaps but does not promise exact cell
    geometry. Full-atlas projections identify only bands blank across every
    row/column, so an internal facial/hat gap cannot split one portrait. Both
    nominal geometry and these actual partition boundaries are recorded.
    """
    width, height = atlas.size
    indices = bytes(0 if alpha < 128 else palette_pixel(red, green, blue)
                    for red, green, blue, alpha in atlas.convert('RGBA').getdata())
    columns, rows = [0] * width, [0] * height
    for offset, value in enumerate(indices):
        if value:
            columns[offset % width] += 1
            rows[offset // width] += 1

    def partition(counts, minimum, axis, cells):
        bands, start = [], None
        for position, value in enumerate(counts + [1]):
            if not value and start is None:
                start = position
            elif value and start is not None:
                if position - start >= minimum:
                    bands.append([start, position])
                start = None
        if len(bands) != cells + 1 or bands[0][0] != 0 or bands[-1][1] != len(counts):
            raise ValueError(f'Cannot identify {cells} complete portrait {axis} from black separator bands: {bands}')
        return [0] + [(start + end) // 2 for start, end in bands[1:-1]] + [len(counts)], bands

    x_bounds, x_bands = partition(columns, 3, 'columns', grid[0])
    y_bounds, y_bands = partition(rows, 8, 'rows', grid[1])
    return Image.frombytes('L', atlas.size, indices), dict(
        x_bounds=x_bounds, y_bounds=y_bounds,
        vertical_black_bands=x_bands, horizontal_black_bands=y_bands)


def bake_cell(atlas, index, partition, grid=GRID, cell=CELL):
    """Keep the complete visible head/shoulders from one assigned source cell."""
    if not 0 <= index < grid[0] * grid[1]:
        raise ValueError('Atlas cell outside declared grid')
    column, row = index % grid[0], index // grid[0]
    cx, cy = partition['x_bounds'][column], partition['y_bounds'][row]
    box = (cx, cy, partition['x_bounds'][column + 1], partition['y_bounds'][row + 1])
    nominal = (column * cell[0], row * cell[1], (column + 1) * cell[0], (row + 1) * cell[1])
    indexed = atlas.crop(box)
    visible = indexed.point(lambda value: 255 if value else 0)
    bbox = visible.getbbox()
    if bbox is None:
        raise ValueError(f'Atlas cell {index} contains no visible portrait')
    if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == indexed.width or bbox[3] == indexed.height:
        raise ValueError(f'Atlas cell {index} touches a crop boundary; refusing a clipped portrait')
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if width < 32 or height < 64:
        raise ValueError(f'Atlas cell {index} has an implausibly small visible portrait: {bbox}')
    if width * 38 >= height * 30:
        fitted = (30, min(38, max(1, (height * 30 + width // 2) // width)))
    else:
        fitted = (min(30, max(1, (width * 38 + height // 2) // height)), 38)
    left, top = (SIZE[0] - fitted[0]) // 2, SIZE[1] - 1 - fitted[1]
    native = Image.new('L', SIZE, 0)
    native.paste(indexed.crop(bbox).resize(fitted, Image.Resampling.NEAREST), (left, top))
    values = bytes(native.getdata())
    opaque = sum(value != 0 for value in values)
    if opaque < 150 or len(set(values) - {0}) < 2:
        raise ValueError(f'Atlas cell {index} loses its portrait at native size')
    rgba = bytes(channel for value in values for channel in RGBA[value])
    image = png(rgba)
    return dict(rgba=rgba, png=image, rgba_sha256=sha(rgba), png_sha256=sha(image),
                png_bytes=len(image), opaque_pixels=opaque, source_cell_box=list(box),
                declared_grid_cell_box=list(nominal),
                source_visible_box=[cx + bbox[0], cy + bbox[1], cx + bbox[2], cy + bbox[3]],
                native_fitted_box=[left, top, left + fitted[0], top + fitted[1]])


def read_plan():
    raw = PLAN.read_bytes()
    plan = json.loads(raw)
    if plan.get('schema') != 'tk2-portrait-art-plan-v1' or tuple(plan.get('native_size', [])) != SIZE:
        raise ValueError('Unknown portrait art plan or native size')
    if tuple(plan.get('grid', [])) != GRID or tuple(plan.get('cell_size', [])) != CELL:
        raise ValueError('Unknown atlas geometry')
    identities, atlas_ids, groups = set(), set(), []
    for group in plan['groups']:
        atlas_id, gender, people = group['id'], group['art_gender_design'], group['people']
        if not re.fullmatch(r'new-\d{2}', atlas_id) or atlas_id in atlas_ids or gender not in ('male', 'female'):
            raise ValueError('Invalid or repeated portrait art group')
        if not 1 <= len(people) <= 64:
            raise ValueError('Too many people assigned to one atlas')
        atlas_ids.add(atlas_id)
        for person in people:
            identity = person['person_id']
            if not re.fullmatch(r'[A-Za-z0-9_-]+', identity) or identity in identities:
                raise ValueError('Invalid or repeated stable person ID')
            identities.add(identity)
        groups.append(group)
    if len(identities) != plan['new_count']:
        raise ValueError('Portrait art plan count does not match unique identities')
    return plan, groups, sha(raw)


def append_supplement(entries, outputs, atlases, used_hashes):
    """Append separately authored art without rebuilding the approved old HD art."""
    raw = SUPPLEMENT.read_bytes()
    plan = json.loads(raw)
    if (plan.get('schema') != 'tk2-portrait-supplement-v1'
            or plan.get('native_size') != list(SIZE) or plan.get('grid') != [2, 2]
            or len(plan.get('people', [])) != 4):
        raise ValueError('Unknown supplemental portrait plan')
    source = ROOT / plan['source_atlas']
    if not source.resolve().is_relative_to(SUPPLEMENT.parent.resolve()):
        raise ValueError('Supplemental art source leaves its retained source directory')
    source_bytes = source.read_bytes()
    if sha(source_bytes) != plan['source_sha256']:
        raise ValueError('Supplemental imagegen source changed')
    image = Image.open(source).convert('RGBA')
    if list(image.size) != plan['source_size']:
        raise ValueError('Supplemental source geometry changed')
    indexed, partition = prepare_atlas(image, (2, 2))
    atlases.append(dict(id='historical-additions-v1', path=plan['source_atlas'],
                        sha256=plan['source_sha256'], size=list(image.size),
                        art_gender_design='male', grid=[2, 2], actual_grid_partition=partition))
    canonical = json.loads((ROOT / 'game/config/campaigns/people.json').read_bytes())['people']
    enhanced = {}
    seen = set()
    for person in plan['people']:
        pid, index = person['person_id'], person['cell_index']
        if (pid in entries or pid not in canonical or person['name'] != canonical[pid]['name']
                or type(index) is not int or index in seen):
            raise ValueError('Supplemental portrait identity/cell binding differs')
        seen.add(index)
        value = bake_cell(indexed, index, partition, (2, 2), (image.width // 2, image.height // 2))
        if value['rgba_sha256'] in used_hashes:
            raise ValueError('New historical portrait duplicates an existing identity')
        used_hashes.add(value['rgba_sha256'])
        path = f'/assets/portraits/generated/{pid}.png'
        entries[pid] = dict(path=path, png_sha256=value['png_sha256'],
                            rgba_sha256=value['rgba_sha256'], width=32, height=40,
                            png_bytes=value['png_bytes'], source_atlas=plan['source_atlas'],
                            source_atlas_sha256=plan['source_sha256'], cell_index=index,
                            source='imagegen_new_pixel_art',
                            art_direction_basis='authorial_game_art_not_historical_likeness',
                            gender_design=person['art_gender_design'], name=person['name'],
                            **{k: value[k] for k in ('opaque_pixels', 'source_cell_box',
                               'declared_grid_cell_box', 'source_visible_box', 'native_fitted_box')})
        outputs[DESTINATION / (pid + '.png')] = value['png']
        enlarged = Image.frombytes('RGBA', SIZE, value['rgba']).resize((128, 160), Image.Resampling.NEAREST)
        pixels = enlarged.tobytes()
        encoded = png(pixels, (128, 160))
        hd_path = f'/assets/portraits/enhanced/{pid}.png'
        outputs[ROOT / 'game' / hd_path.lstrip('/')] = encoded
        enhanced[pid] = dict(path=hd_path, width=128, height=160, source_path=path,
                             source_sha256=value['png_sha256'], sha256=sha(encoded),
                             pixel_sha256=sha(pixels), method='identity_preserving_pixel_enhancement',
                             rendering='nearest4x',
                             provenance=dict(supplement_plan=str(SUPPLEMENT.relative_to(ROOT)),
                                             supplement_plan_sha256=sha(raw),
                                             atlas=plan['source_atlas'], source_atlas_sha256=plan['source_sha256'],
                                             cell_index=index, base_method='native32x40_exact_nearest4x',
                                             prompt=plan['prompt'],
                                             art_direction_basis='authorial_game_art_not_historical_likeness',
                                             qa=dict(size=[128, 160], paletteSize=len(set(enlarged.getdata())),
                                                     alphaChanges=0, nearest4xExact=True)))
    records = SUPPLEMENT.parent / 'enhanced-records.json'
    outputs[records] = (json.dumps(dict(schema='tk2-portrait-supplement-enhanced-v1',
                                       people=enhanced), ensure_ascii=False, indent=2) + '\n').encode()
    hd_file = ROOT / 'game/config/portrait-enhanced.json'
    hd = json.loads(hd_file.read_bytes())
    hd['people'].update(enhanced)
    hd['counts'].update(people=len(hd['people']),
                        source_unique=len({row['pixel_sha256'] for row in hd['people'].values()}),
                        atlas_count=len(json.loads((ROOT / 'art/portraits/enhancement-v1/plan.json').read_bytes())['atlases']) + 1)
    hd['processing']['supplement_mode'] = 'authorial_pixel_art_native_nearest4x_preserving_identity'
    outputs[hd_file] = (json.dumps(hd, ensure_ascii=False, indent=2) + '\n').encode()
    return dict(path=str(SUPPLEMENT.relative_to(ROOT)), sha256=sha(raw), count=len(enhanced))


def build(check=False):
    plan, groups, plan_sha = read_plan()
    missing = [str(SOURCE / (group['id'] + '.png')) for group in groups
               if not (SOURCE / (group['id'] + '.png')).is_file()]
    if missing:
        raise ValueError('Missing source atlases; no assets written: ' + ', '.join(missing))
    # Preflight all cells and all assignments before touching published outputs.
    cells, atlases, reserved = {}, [], set()
    for group in groups:
        path = SOURCE / (group['id'] + '.png')
        raw = path.read_bytes()
        atlas = Image.open(path).convert('RGBA')
        if atlas.size != (GRID[0] * CELL[0], GRID[1] * CELL[1]):
            raise ValueError('Atlas dimensions differ from declared geometry: ' + str(path))
        indexed, partition = prepare_atlas(atlas)
        data = dict(id=group['id'], path=str(path.relative_to(ROOT)), sha256=sha(raw),
                    size=list(atlas.size), art_gender_design=group['art_gender_design'],
                    actual_grid_partition=partition)
        atlases.append(data)
        for index in range(64):
            cells[group['id'], index] = dict(bake_cell(indexed, index, partition), atlas=data, cell_index=index)
        reserved.update((group['id'], index) for index in range(len(group['people'])))
    spare = {'male': [], 'female': []}
    for group in groups:
        spare[group['art_gender_design']].extend((group['id'], index) for index in range(len(group['people']), 64))
    used_cells, used_hashes, entries, outputs = set(), set(), {}, {}
    for group in groups:
        for index, person in enumerate(group['people']):
            preferred = group['id'], index
            key = preferred
            if cells[key]['rgba_sha256'] in used_hashes:
                key = next((candidate for candidate in spare[group['art_gender_design']]
                            if candidate not in used_cells and candidate not in reserved
                            and cells[candidate]['rgba_sha256'] not in used_hashes), None)
                if key is None:
                    raise ValueError(f'No unique unused same-gender cell remains for {person["person_id"]}; no assets written')
            if key in used_cells:
                raise ValueError('One source cell cannot represent multiple people')
            value = cells[key]
            used_cells.add(key)
            used_hashes.add(value['rgba_sha256'])
            identity = person['person_id']
            entry = dict(path=f'/assets/portraits/generated/{identity}.png',
                         png_sha256=value['png_sha256'], rgba_sha256=value['rgba_sha256'],
                         width=SIZE[0], height=SIZE[1], png_bytes=value['png_bytes'],
                         source_atlas=value['atlas']['path'], source_atlas_sha256=value['atlas']['sha256'],
                         cell_index=value['cell_index'], source='imagegen_new_pixel_art',
                         art_direction_basis='authorial_game_art_not_historical_likeness',
                         gender_design=group['art_gender_design'], name=person['name'],
                         opaque_pixels=value['opaque_pixels'], source_cell_box=value['source_cell_box'],
                         declared_grid_cell_box=value['declared_grid_cell_box'],
                         source_visible_box=value['source_visible_box'], native_fitted_box=value['native_fitted_box'])
            if key != preferred:
                entry['duplicate_fallback'] = dict(planned_source_atlas=f'art/portraits/source-atlases/{preferred[0]}.png',
                                                   planned_cell_index=preferred[1], reason='native_pixel_duplicate_used_unique_unassigned_same_gender_cell')
            entries[identity] = entry
            outputs[DESTINATION / (identity + '.png')] = value['png']
    if len(entries) != plan['new_count'] or len(used_hashes) != plan['new_count']:
        raise ValueError('New portrait identity/pixel count mismatch')
    supplement = append_supplement(entries, outputs, atlases, used_hashes)
    manifest = dict(schema='tk2-generated-portraits-v1', count=len(entries), unique_pixel_images=len(used_hashes),
                    native_size=list(SIZE), source='imagegen_new_pixel_art',
                    art_direction_basis='authorial_game_art_not_historical_likeness',
                    plan='art/portraits/plan.json', plan_sha256=plan_sha,
                    supplement_plans=[supplement],
                    processing=POLICY, source_atlases=atlases,
                    assigned_by_gender=dict(Counter(entry['gender_design'] for entry in entries.values())),
                    duplicate_fallback_count=sum('duplicate_fallback' in entry for entry in entries.values()),
                    by_person_id=entries)
    outputs[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    if DESTINATION.exists():
        extra = set(DESTINATION.glob('*.png')) - set(outputs)
        if extra:
            raise ValueError('Unexpected existing portrait files; no assets overwritten: ' + ', '.join(str(path) for path in sorted(extra)))
    if check:
        for path, data in outputs.items():
            if not path.is_file() or path.read_bytes() != data:
                raise ValueError('Generated portrait output differs: ' + str(path))
    else:
        DESTINATION.mkdir(parents=True, exist_ok=True)
        for path, data in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return manifest


def inspect_atlas(path, preview=None):
    path = Path(path)
    image = Image.open(path).convert('RGBA')
    if image.size != (GRID[0] * CELL[0], GRID[1] * CELL[1]):
        raise ValueError('Inspection requires the declared 1024x1536 atlas')
    indexed, partition = prepare_atlas(image)
    cells = [bake_cell(indexed, index, partition) for index in range(64)]
    if preview:
        sheet = Image.new('RGB', (8 * 40, 8 * 52), 'black')
        draw = ImageDraw.Draw(sheet)
        for index, item in enumerate(cells):
            portrait = Image.frombytes('RGBA', SIZE, item['rgba'])
            x, y = (index % 8) * 40 + 4, (index // 8) * 52
            sheet.paste(portrait, (x, y), portrait)
            draw.text((x + 8, y + 40), str(index), fill='white')
        output = Path(preview)
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.resize((sheet.width * 3, sheet.height * 3), Image.Resampling.NEAREST).save(output)
    return dict(atlas=str(path), cells=64, unique_native_images=len({cell['rgba_sha256'] for cell in cells}),
                opaque_range=[min(cell['opaque_pixels'] for cell in cells), max(cell['opaque_pixels'] for cell in cells)],
                actual_grid_partition=partition,
                visible_boxes=[cell['source_visible_box'] for cell in cells], output_preview=str(preview) if preview else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--inspect-atlas', type=Path)
    parser.add_argument('--preview', type=Path, help='Optional inspection sheet outside published assets')
    args = parser.parse_args()
    if args.inspect_atlas:
        print(json.dumps(inspect_atlas(args.inspect_atlas, args.preview)))
    else:
        manifest = build(args.check)
        print(json.dumps(dict(count=manifest['count'], unique_pixel_images=manifest['unique_pixel_images'],
                              native_size=manifest['native_size'], assigned_by_gender=manifest['assigned_by_gender'],
                              duplicate_fallbacks=manifest['duplicate_fallback_count'], check=args.check)))


if __name__ == '__main__':
    main()
