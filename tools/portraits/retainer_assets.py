"""Assign retained authored portraits without redrawing or upscaling native art.

The optional retainer plan keeps new identity bindings separate from approved
portrait studies. Both sizes are extracted from the retained high resolution
source: the small file is a compatibility derivative, never the HD input.
This module only returns proposed output bytes; its caller owns publication.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zlib

from PIL import Image, ImageOps

from supplement_redraw import PALETTE

PLAN = 'art/portraits/retainer-additions-v1/plan.json'
SCHEMA = 'tk2-retainer-portrait-additions-v1'
NATIVE_SIZE = (32, 40)
ENHANCED_SIZE = (128, 160)
METHOD = 'retainer_authored_source_direct128_fixed_palette'
NATIVE_RGB = ((0, 0, 0), (255, 255, 255), (247, 162, 71), (158, 65, 0))
ORIGINS = {
    'reused_unassigned_imagegen_cell': 'retained_unassigned_imagegen_cell',
    'imagegen_new_pixel_art': 'new_retained_imagegen_source',
    'original_portrait_redraw': 'identity_preserving_original_portrait_redraw',
}
REUSE_NOTICE = ('Previously authored, unassigned imagegen artwork; newly bound to this '
                'person ID, not newly generated for this person or a historical likeness.')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def encode_png(pixels, size):
    """Keep encoding deterministic across Pillow versions and metadata changes."""
    width, height = size
    if len(pixels) != width * height * 4:
        raise ValueError('Portrait RGBA byte count differs from its geometry')

    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))

    stride = width * 4
    rows = b''.join(b'\0' + pixels[y * stride:(y + 1) * stride] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def retained(root, relative, expected=None, *, directory='art/portraits'):
    """Reject traversal and symlink aliases before reading an attributed source."""
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or Path(relative).is_absolute() or '..' in Path(relative).parts
            or str(Path(relative)) != relative):
        raise ValueError('Invalid retained retainer source path')
    root = Path(root).resolve()
    path = root / relative
    allowed = root / directory
    if not path.is_relative_to(allowed):
        raise ValueError('Retainer source leaves its retained art directory')
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Retainer source cannot use a symlink')
    if not path.is_file() or not path.resolve().is_relative_to(allowed.resolve()):
        raise ValueError('Missing retained retainer source: ' + relative)
    raw = path.read_bytes()
    if expected is not None and (not isinstance(expected, str)
                                 or not re.fullmatch(r'[0-9a-f]{64}', expected)
                                 or digest(raw) != expected):
        raise ValueError('Retained retainer source hash differs: ' + relative)
    return path, raw


@lru_cache(maxsize=65536)
def native_index(red, green, blue):
    if max(red, green, blue) <= 32:
        return 0
    return min(range(4), key=lambda n: sum((a - b) ** 2
               for a, b in zip((red, green, blue), NATIVE_RGB[n])))


@lru_cache(maxsize=65536)
def fixed_color(color):
    red, green, blue, alpha = color
    if alpha < 128:
        return PALETTE[0]
    if max(red, green, blue) <= 32:
        return PALETTE[1]
    return min(PALETTE[1:], key=lambda candidate:
               sum((candidate[channel] - color[channel]) ** 2 for channel in range(3)))


def detail_blocks(image, phase=(0, 0)):
    """Count non-uniform complete 4px blocks, including transparent pixels."""
    width, height = image.size
    pixels = image.load()
    return sum(any(pixels[x + dx, y + dy] != pixels[x, y]
                   for dy in range(4) for dx in range(4))
               for y in range(phase[1], height - 3, 4)
               for x in range(phase[0], width - 3, 4))


def authored_crop(raw_source, box, matte):
    """Retain the complete original tile and derive a separate display mask."""
    crop = raw_source.crop(box)
    if crop.width < 96 or crop.height < 128:
        raise ValueError('Retainer source must contain authored high resolution pixels')
    # Check every phase: padding a nearest4x file must not disguise an upscale.
    if any(detail_blocks(crop, (x, y)) == 0 for y in range(4) for x in range(4)):
        raise ValueError('Retainer source is an exact nearest4x enlargement')
    mask = bytes(255 if alpha >= 128 and (matte == 'alpha' or max(red, green, blue) > 32)
                 else 0 for red, green, blue, alpha in crop.getdata())
    alpha = Image.frombytes('L', crop.size, mask)
    visible = alpha.getbbox()
    if visible is None:
        raise ValueError('Retainer source contains no visible portrait')
    if visible[0] == 0 or visible[1] == 0 or visible[2] == crop.width or visible[3] == crop.height:
        raise ValueError('Retainer source touches a crop boundary')
    if visible[2] - visible[0] < 60 or visible[3] - visible[1] < 96:
        raise ValueError('Retainer source has insufficient authored portrait detail')
    masked = crop.copy()
    masked.putalpha(alpha)
    return crop, masked, visible


def direct_hd(source, visible, native):
    """Fit authored source pixels to the native silhouette's fourfold envelope."""
    native_image = Image.frombytes('RGBA', NATIVE_SIZE, native['rgba'])
    left, top, right, bottom = [value * 4 for value in native['native_fitted_box']]
    content = ImageOps.contain(source.crop(visible), (right - left, bottom - top),
                               Image.Resampling.NEAREST)
    fitted = Image.new('RGBA', ENHANCED_SIZE, (0, 0, 0, 0))
    fitted.paste(content, (left + (right - left - content.width) // 2,
                          bottom - content.height))
    pixels = bytes(channel for color in fitted.getdata() for channel in fixed_color(color))
    enhanced = Image.frombytes('RGBA', ENHANCED_SIZE, pixels)
    baseline = native_image.resize(ENHANCED_SIZE, Image.Resampling.NEAREST).tobytes()
    changes = sum(pixels[offset:offset + 4] != baseline[offset:offset + 4]
                  for offset in range(0, len(pixels), 4))
    colors = len(set(enhanced.getdata()))
    blocks = detail_blocks(enhanced)
    if changes < 1024 or not 5 <= colors <= 16 or blocks < 20:
        raise ValueError('Retainer portrait adds insufficient high resolution detail')
    return encode_png(pixels, ENHANCED_SIZE), pixels, dict(
        size=list(ENHANCED_SIZE), paletteSize=colors, changedPixels=changes,
        nearest4xExact=False, nonUniformBlocks4x4=blocks)


def append_retainer_assets(root, entries, outputs, atlases, used_hashes, *,
                           prepare_atlas, bake_cell):
    """Preflight optional additions, then append their reproducible output bytes.

    Existing entries, HD records and output files are never modified. An error
    leaves all caller-owned collections untouched. Missing optional plan means
    the approved old build remains byte-for-byte reproducible.
    """
    root = Path(root).resolve()
    if not (root / PLAN).exists():
        return None
    _, plan_raw = retained(root, PLAN)
    plan = json.loads(plan_raw)
    if (plan.get('schema') != SCHEMA or plan.get('native_size') != list(NATIVE_SIZE)
            or plan.get('enhanced_size') != list(ENHANCED_SIZE)
            or not isinstance(plan.get('people'), list) or not plan['people']):
        raise ValueError('Unknown retainer portrait additions plan')
    canonical = json.loads((root / 'game/config/campaigns/people.json').read_bytes())['people']
    planned_ids, planned_cells, occupied = set(), set(), set()
    for row in entries.values():
        if 'source_atlas' in row and 'cell_index' in row:
            occupied.add((row['source_atlas'], row['cell_index']))
    for person in plan['people']:
        if not isinstance(person, dict):
            raise ValueError('Invalid retainer portrait person')
        pid = person.get('person_id')
        if (not isinstance(pid, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', pid)
                or pid in planned_ids or pid in entries or pid not in canonical
                or person.get('name') != canonical[pid]['name']
                or person.get('art_gender_design') not in ('male', 'female')):
            raise ValueError('Retainer portrait stable identity differs')
        planned_ids.add(pid)

    hd_file = root / 'game/config/portrait-enhanced.json'
    hd = json.loads(outputs.get(hd_file, hd_file.read_bytes()))
    previous_hd = hd['people']
    # A repeat build can read its previously published additions. Only bindings
    # owned by this exact plan are replaceable; an unrelated ID is a collision.
    for pid in planned_ids & previous_hd.keys():
        if previous_hd[pid].get('provenance', {}).get('retainer_plan') != PLAN:
            raise ValueError('Retainer enhanced portrait collides with an existing identity')
    old_hd = {pid: row for pid, row in previous_hd.items() if pid not in planned_ids}
    hd_hashes = {row['pixel_sha256'] for row in old_hd.values()}
    new_entries, native_bindings, new_hd, new_outputs, new_hashes, new_atlases = {}, {}, {}, {}, set(), []
    cache, source_paths = {}, set()
    for person in plan['people']:
        pid = person['person_id']
        atlas_path, single_path = person.get('source_atlas'), person.get('source_path')
        if bool(atlas_path) == bool(single_path):
            raise ValueError('Retainer portrait needs exactly one source choice')
        kind = person.get('source_kind')
        if (kind not in ORIGINS or (atlas_path and kind != 'reused_unassigned_imagegen_cell')
                or (single_path and kind not in ('imagegen_new_pixel_art', 'original_portrait_redraw'))):
            raise ValueError('Unknown retainer authored source attribution')
        if kind != 'original_portrait_redraw' and any(key.startswith('native_original_') for key in person):
            raise ValueError('Generated retainer portrait cannot bind an original native')
        relative = atlas_path or single_path
        directory = 'art/portraits/source-atlases' if atlas_path else str(Path(PLAN).parent)
        source_path, source_raw = retained(root, relative, person.get('source_sha256'), directory=directory)
        if not isinstance(person.get('source_sha256'), str):
            raise ValueError('Retainer portrait source needs a pinned SHA256')
        if source_path.suffix != '.png':
            raise ValueError('Retainer source must be a PNG')
        expected_size = person.get('source_size')
        if (not isinstance(expected_size, list) or len(expected_size) != 2
                or any(type(value) is not int or not 128 <= value <= 4096 for value in expected_size)):
            raise ValueError('Invalid retained source geometry')
        if relative not in cache:
            with Image.open(io.BytesIO(source_raw)) as opened:
                if opened.format != 'PNG' or list(opened.size) != expected_size:
                    raise ValueError('Retainer authored source geometry differs')
                image = opened.convert('RGBA')
            cache[relative] = image
        image = cache[relative]
        if list(image.size) != expected_size:
            raise ValueError('Retainer authored source geometry differs')
        matte = person.get('source_matte', 'black' if atlas_path else 'alpha')
        if matte not in ('black', 'alpha') or (atlas_path and matte != 'black'):
            raise ValueError('Invalid retainer source matte')
        source_meta = dict(original_source_path=relative, original_source_sha256=digest(source_raw),
                           source_size=list(image.size), source_matte=matte,
                           source_origin=ORIGINS[kind])
        if atlas_path:
            grid = person.get('grid')
            if (grid != [8, 8] or any(type(value) is not int for value in grid)
                    or type(person.get('cell_index')) is not int):
                raise ValueError('Invalid retainer atlas grid or cell')
            atlas_records = [row for row in atlases if row.get('path') == relative]
            if (len(atlas_records) != 1
                    or atlas_records[0].get('sha256') != person['source_sha256']
                    or atlas_records[0].get('art_gender_design') != person['art_gender_design']):
                raise ValueError('Retainer cell must reuse a retained atlas of the same art direction')
            index = person['cell_index']
            key = (relative, index)
            if key in occupied or key in planned_cells:
                raise ValueError('Retainer source cell is already assigned')
            planned_cells.add(key)
            cache_key = ('indexed', relative)
            if cache_key not in cache:
                cache[cache_key] = prepare_atlas(image, (8, 8))
            indexed, partition = cache[cache_key]
            native = bake_cell(indexed, index, partition, (8, 8),
                               (image.width // 8, image.height // 8))
            source_meta.update(source_atlas=relative, source_atlas_sha256=digest(source_raw),
                               cell_index=index, grid=[8, 8])
        else:
            if 'cell_index' in person or 'grid' in person:
                raise ValueError('Single retainer source cannot declare an atlas cell')
            if relative in source_paths:
                raise ValueError('One retained single portrait cannot represent two people')
            if kind == 'original_portrait_redraw':
                original_id = person.get('native_original_id')
                original_path = person.get('native_original_path')
                original_hash = person.get('native_original_sha256')
                if (type(original_id) is not int or not 0 <= original_id < 237
                        or original_path != f'game/assets/portraits/original/{original_id:03d}.png'):
                    raise ValueError('Retainer redraw native original binding differs')
                originals = json.loads((root / 'game/config/portrait-originals.json').read_bytes())['by_original_id']
                identity_rows = json.loads((root / 'game/config/portrait-identity-map.json').read_bytes())['records']
                identities = {row['original_id']: row['person_id'] for row in identity_rows}
                archived = originals[str(original_id)]
                if (identities.get(original_id) != pid or archived['png_sha256'] != original_hash
                        or archived['path'] != original_path.removeprefix('game')):
                    raise ValueError('Retainer redraw does not match the reviewed original identity')
                original_file, original_png = retained(root, original_path, original_hash,
                                                       directory='game/assets/portraits/original')
                with Image.open(original_file) as opened:
                    original_image = opened.convert('RGBA')
                original_pixels = original_image.tobytes()
                bbox = original_image.getchannel('A').getbbox()
                if (original_image.size != NATIVE_SIZE or digest(original_pixels) != archived['rgba_sha256']
                        or bbox is None):
                    raise ValueError('Retainer original native pixels differ')
                native = dict(rgba=original_pixels, png=original_png,
                              rgba_sha256=digest(original_pixels), png_sha256=digest(original_png),
                              png_bytes=len(original_png), opaque_pixels=archived['opaque_pixels'],
                              source_cell_box=[0, 0, image.width, image.height],
                              declared_grid_cell_box=[0, 0, image.width, image.height],
                              source_visible_box=None, native_fitted_box=list(bbox))
                source_meta.update(native_original_id=original_id, native_original_path=original_path,
                                   native_original_sha256=original_hash)
            else:
                if any(key.startswith('native_original_') for key in person):
                    raise ValueError('Generated retainer portrait cannot bind an original native')
                indices = bytes(0 if alpha < 128 else native_index(red, green, blue)
                                for red, green, blue, alpha in image.getdata())
                indexed = Image.frombytes('L', image.size, indices)
                partition = dict(x_bounds=[0, image.width], y_bounds=[0, image.height])
                native = bake_cell(indexed, 0, partition, (1, 1), image.size)
            source_meta.update(source_path=relative, source_sha256=digest(source_raw))
            new_atlases.append(dict(id=pid, path=relative, sha256=digest(source_raw),
                                   size=list(image.size), art_gender_design=person['art_gender_design'],
                                   source_type='single_authored_portrait', retainer_plan=PLAN))
        source_paths.add(relative)
        if kind != 'original_portrait_redraw':
            if native['rgba_sha256'] in used_hashes | new_hashes:
                raise ValueError('Retainer native pixels duplicate an existing identity')
            new_hashes.add(native['rgba_sha256'])
        crop, masked, visible = authored_crop(image, native['source_cell_box'], matte)
        if kind == 'original_portrait_redraw':
            native['source_visible_box'] = list(visible)
        encoded, pixels, qa = direct_hd(masked, visible, native)
        if digest(pixels) in hd_hashes:
            raise ValueError('Retainer enhanced pixels duplicate an existing identity')
        hd_hashes.add(digest(pixels))
        crop_path = f'art/portraits/retainer-additions-v1/source-crops/{pid}.png'
        crop_png = encode_png(crop.tobytes(), crop.size)
        native_path = (person['native_original_path'].removeprefix('game')
                       if kind == 'original_portrait_redraw' else f'/assets/portraits/generated/{pid}.png')
        native_archive = f'art/portraits/retainer-additions-v1/native-32x40/{pid}.png'
        provenance = dict(base_method=METHOD, retainer_plan=PLAN, retainer_plan_sha256=digest(plan_raw),
                          **source_meta, retained_source_crop=crop_path,
                          retained_source_crop_sha256=digest(crop_png),
                          retained_source_crop_rgba_sha256=digest(crop.tobytes()),
                          source_cell_box=native['source_cell_box'],
                          source_visible_box=[native['source_cell_box'][0] + visible[0],
                                              native['source_cell_box'][1] + visible[1],
                                              native['source_cell_box'][0] + visible[2],
                                              native['source_cell_box'][1] + visible[3]],
                          native_fitted_box=native['native_fitted_box'],
                          native_archive=native_archive, native_archive_sha256=native['png_sha256'],
                          art_direction_basis='authorial_game_art_not_historical_likeness', qa=qa)
        if kind == 'reused_unassigned_imagegen_cell':
            provenance['reuse_notice'] = REUSE_NOTICE
        if 'prompt' in person or 'prompt_sha256' in person:
            retained(root, person.get('prompt'), person.get('prompt_sha256'),
                     directory=str(Path(PLAN).parent))
            if not isinstance(person.get('prompt_sha256'), str):
                raise ValueError('Retainer source prompt needs a pinned SHA256')
            provenance.update(prompt=person['prompt'], prompt_sha256=person['prompt_sha256'])
        native_bindings[pid] = dict(path=native_path, png_sha256=native['png_sha256'],
                                rgba_sha256=native['rgba_sha256'], width=32, height=40,
                                png_bytes=native['png_bytes'],
                                source='pinned_ROM_static_frame0' if kind == 'original_portrait_redraw' else 'imagegen_new_pixel_art',
                                art_direction_basis='authorial_game_art_not_historical_likeness',
                                gender_design=person['art_gender_design'], name=person['name'],
                                retainer_plan=PLAN, retainer_plan_sha256=digest(plan_raw),
                                native_kind='nes_original' if kind == 'original_portrait_redraw' else 'generated',
                                **source_meta, **{key: native[key] for key in (
                                    'opaque_pixels', 'source_cell_box', 'declared_grid_cell_box',
                                    'source_visible_box', 'native_fitted_box')})
        if kind == 'reused_unassigned_imagegen_cell':
            native_bindings[pid]['reuse_notice'] = REUSE_NOTICE
        if kind != 'original_portrait_redraw':
            new_entries[pid] = native_bindings[pid]
        new_hd[pid] = dict(path=f'/assets/portraits/enhanced/{pid}.png', width=128, height=160,
                           source_path=native_path, source_sha256=native['png_sha256'],
                           sha256=digest(encoded), pixel_sha256=digest(pixels),
                           method='identity_preserving_pixel_enhancement', rendering='redrawn128',
                           provenance=provenance)
        if kind != 'original_portrait_redraw':
            new_outputs[root / 'game' / native_path.lstrip('/')] = native['png']
        new_outputs[root / 'game' / new_hd[pid]['path'].lstrip('/')] = encoded
        new_outputs[root / crop_path] = crop_png
        new_outputs[root / native_archive] = native['png']

    hd['people'] = dict(old_hd, **new_hd)
    hd['counts'].update(people=len(hd['people']),
                        source_unique=len({row['pixel_sha256'] for row in hd['people'].values()}),
                        retainer_people=len(new_hd), retainer_source_images=len(source_paths))
    hd['processing']['retainer_mode'] = METHOD
    new_outputs[hd_file] = json_bytes(hd)
    records_dir = root / Path(PLAN).parent
    new_outputs[records_dir / 'native-records.json'] = json_bytes(dict(
        schema='tk2-retainer-portrait-native-records-v1', plan=PLAN, plan_sha256=digest(plan_raw),
        count=len(native_bindings), native_size=list(NATIVE_SIZE), people=native_bindings))
    new_outputs[records_dir / 'enhanced-records.json'] = json_bytes(dict(
        schema='tk2-retainer-portrait-enhanced-records-v1', plan=PLAN, plan_sha256=digest(plan_raw),
        count=len(new_hd), size=list(ENHANCED_SIZE), people=new_hd))
    collision = set(new_outputs) & set(outputs)
    collision.discard(hd_file)
    if collision:
        raise ValueError('Retainer output would replace an existing portrait asset')
    entries.update(new_entries)
    outputs.update(new_outputs)
    atlases.extend(new_atlases)
    used_hashes.update(new_hashes)
    return dict(path=PLAN, sha256=digest(plan_raw), count=len(native_bindings),
                generated_count=len(new_entries), original_count=len(native_bindings) - len(new_entries),
                source_images=len(source_paths), method=METHOD)
