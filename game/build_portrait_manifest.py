#!/usr/bin/env python3
"""Bind extracted/new portraits to stable identities without changing any save catalog.

All canonical bindings must have genuine, checked PNG assets. Missing images are an
error: this builder never manufactures a generic head or silently reuses art.
Only the standard library is needed to verify native PNG pixels and provenance.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
NATIVE = (32, 40)
ENHANCED = (128, 160)
ENHANCED_CONFIG = 'game/config/portrait-enhanced.json'
ENHANCED_REFERENCE = 'art/portraits/hd-samples/zhuge-liang-preserved-v8/portrait-128x160.png'
HEX = re.compile(r'^[0-9a-f]{64}$')
ASSET = re.compile(r'^/assets/portraits/(?:original/[0-9]{3}|generated/[a-z0-9-]+)\.png$')
ENHANCED_ASSET = re.compile(r'^/assets/portraits/enhanced/[a-z0-9-]+\.png$')
RETAINER_PLAN = 'art/portraits/retainer-additions-v1/plan.json'
RETAINER_METHOD = 'retainer_authored_source_direct128_fixed_palette'
RETAINER_PALETTE = {
    (0, 0, 0, 0), (0, 0, 0, 255), (108, 46, 7, 255), (142, 56, 0, 255),
    (158, 65, 0, 255), (185, 85, 10, 255), (198, 99, 18, 255), (223, 121, 34, 255),
    (247, 162, 71, 255), (255, 187, 89, 255), (255, 218, 128, 255),
    (255, 214, 162, 255), (255, 235, 204, 255), (188, 189, 185, 255),
    (226, 226, 222, 255), (255, 255, 255, 255),
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png_pixels(raw, expected_size=NATIVE):
    """Decode strict 8-bit RGB/RGBA PNGs; return dimensions and RGBA bytes."""
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Portrait is not a PNG')
    position, image_data, header, ended = 8, bytearray(), None, False
    while position < len(raw):
        if position + 12 > len(raw):
            raise ValueError('Truncated PNG chunk')
        length = struct.unpack('>I', raw[position:position + 4])[0]
        kind = raw[position + 4:position + 8]
        end = position + 12 + length
        if end > len(raw):
            raise ValueError('Truncated PNG data')
        data = raw[position + 8:position + 8 + length]
        checksum = struct.unpack('>I', raw[position + 8 + length:end])[0]
        if zlib.crc32(kind + data) & 0xffffffff != checksum:
            raise ValueError('Portrait PNG CRC mismatch')
        if kind == b'IHDR':
            if header is not None or length != 13:
                raise ValueError('Invalid portrait PNG header')
            header = struct.unpack('>IIBBBBB', data)
        elif kind == b'IDAT':
            image_data.extend(data)
        elif kind == b'IEND':
            ended = True
            if length or end != len(raw):
                raise ValueError('Trailing portrait PNG data')
        position = end
    if not ended or header is None:
        raise ValueError('Incomplete PNG')
    width, height, depth, color, compression, filtering, interlace = header
    if (width, height) != expected_size or depth != 8 or color not in (2, 6) or any((compression, filtering, interlace)):
        label = 'native32x40' if expected_size == NATIVE else f'{expected_size[0]}x{expected_size[1]}'
        raise ValueError(f'Portrait must be a {label}, noninterlaced8bit RGB/RGBA PNG')
    channels = 4 if color == 6 else 3
    stride = width * channels
    scanlines = zlib.decompress(image_data)
    if len(scanlines) != (stride + 1) * height:
        raise ValueError('Portrait PNG decoded size mismatch')
    previous = bytearray(stride)
    output = bytearray()
    for y in range(height):
        offset = y * (stride + 1)
        kind = scanlines[offset]
        if kind > 4:
            raise ValueError('Unknown PNG row filter')
        row = bytearray(scanlines[offset + 1:offset + 1 + stride])
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            up = previous[x]
            corner = previous[x - channels] if x >= channels else 0
            if kind == 1:
                row[x] = (row[x] + left) & 255
            elif kind == 2:
                row[x] = (row[x] + up) & 255
            elif kind == 3:
                row[x] = (row[x] + (left + up) // 2) & 255
            elif kind == 4:
                prediction = left + up - corner
                distances = abs(prediction - left), abs(prediction - up), abs(prediction - corner)
                nearest = left if distances[0] <= distances[1] and distances[0] <= distances[2] else up if distances[1] <= distances[2] else corner
                row[x] = (row[x] + nearest) & 255
        previous = row
        if channels == 4:
            output.extend(row)
        else:
            for x in range(0, stride, 3):
                output.extend(row[x:x + 3])
                output.append(255)
    return (width, height), bytes(output)


def image_record(row):
    path = row.get('path', '')
    if not isinstance(path, str) or ASSET.fullmatch(path) is None:
        raise ValueError('Invalid portrait asset path')
    if not all(HEX.fullmatch(row.get(key, '')) for key in ('png_sha256', 'rgba_sha256')):
        raise ValueError('Missing portrait hashes: ' + path)
    raw = (ROOT / 'game' / path.lstrip('/')).read_bytes()
    size, pixels = png_pixels(raw)
    if sha(raw) != row['png_sha256'] or sha(pixels) != row['rgba_sha256']:
        raise ValueError('Portrait source hash mismatch: ' + path)
    if tuple(row.get(key) for key in ('width', 'height')) != size:
        raise ValueError('Portrait source dimensions mismatch: ' + path)
    return dict(path=path, width=size[0], height=size[1], png_sha256=sha(raw), rgba_sha256=sha(pixels)), pixels


def enhanced_records(data, primary):
    """Validate optional derivatives without replacing original identity records."""
    if not isinstance(data, dict) or data.get('schema') != 'tk2-enhanced-portraits-v1' or (data.get('width'), data.get('height')) != ENHANCED:
        raise ValueError('Invalid enhanced portrait manifest schema/dimensions')
    rows = data.get('people')
    if not isinstance(rows, dict):
        raise ValueError('Enhanced portrait people must be an object')
    reference = data.get('approved_reference')
    if not isinstance(reference, dict) or reference.get('path') != ENHANCED_REFERENCE:
        raise ValueError('Invalid enhanced portrait approved reference path')
    reference_hash = reference.get('sha256')
    if not isinstance(reference_hash, str) or HEX.fullmatch(reference_hash) is None:
        raise ValueError('Invalid enhanced portrait approved reference hash')
    reference_file = ROOT / ENHANCED_REFERENCE
    if not reference_file.is_file() or sha(reference_file.read_bytes()) != reference_hash:
        raise ValueError('Enhanced portrait approved reference hash mismatch')
    png_pixels(reference_file.read_bytes(), ENHANCED)
    enhanced, retainer_cache, retainer_hashes = {}, {}, set()
    previous_hashes = {row.get('pixel_sha256') for row in rows.values()
                       if isinstance(row, dict) and isinstance(row.get('provenance'), dict)
                       and row['provenance'].get('retainer_plan') != RETAINER_PLAN}
    for person_id, row in rows.items():
        if person_id not in primary:
            raise ValueError('Unknown enhanced portrait person')
        if not isinstance(row, dict):
            raise ValueError('Invalid enhanced portrait record')
        path = row.get('path')
        if not isinstance(path, str) or ENHANCED_ASSET.fullmatch(path) is None:
            raise ValueError('Invalid enhanced portrait asset path')
        if path != f'/assets/portraits/enhanced/{person_id}.png':
            raise ValueError('Enhanced portrait path belongs to a different person')
        if (row.get('width'), row.get('height')) != ENHANCED:
            raise ValueError('Enhanced portrait dimensions mismatch')
        for key in ('source_sha256', 'sha256', 'pixel_sha256'):
            value = row.get(key)
            if not isinstance(value, str) or HEX.fullmatch(value) is None:
                raise ValueError('Missing enhanced portrait hashes: ' + path)
        source = primary[person_id]
        if row.get('source_path') != source['path'] or row['source_sha256'] != source['png_sha256']:
            raise ValueError('Enhanced portrait source/person binding mismatch: ' + person_id)
        if row.get('method') != 'identity_preserving_pixel_enhancement' or not isinstance(row.get('provenance'), dict):
            raise ValueError('Enhanced portrait must state its enhancement provenance')
        if (source.get('retainer_plan') == RETAINER_PLAN
                and (row.get('rendering') != 'redrawn128'
                     or row['provenance'].get('base_method') != RETAINER_METHOD)):
            raise ValueError('Retainer enhanced portrait must retain its direct128 source method')
        if 'rendering' in row and row['rendering'] not in ('nearest4x','redrawn128'):
            raise ValueError('Unknown enhanced portrait rendering')
        if (row.get('rendering') == 'nearest4x'
                and row['provenance'].get('base_method') != 'native32x40_exact_nearest4x'):
            raise ValueError('Nearest4x portrait rendering lacks its source method')
        asset = ROOT / 'game' / path.lstrip('/')
        asset_root = ROOT / 'game/assets/portraits/enhanced'
        if not asset.resolve().is_relative_to(asset_root.resolve()) or not asset.is_file():
            raise ValueError('Enhanced portrait asset is missing or outside its asset directory')
        raw = asset.read_bytes()
        if sha(raw) != row['sha256']:
            raise ValueError('Enhanced portrait PNG hash mismatch: ' + path)
        size, pixels = png_pixels(raw, ENHANCED)
        if sha(pixels) != row['pixel_sha256']:
            raise ValueError('Enhanced portrait pixel hash mismatch: ' + path)
        if any(pixels[i] not in (0, 255) for i in range(3, len(pixels), 4)):
            raise ValueError('Enhanced portrait contains partial transparency')
        if row.get('rendering') == 'nearest4x':
            native_file = ROOT / 'game' / source['path'].lstrip('/')
            native = png_pixels(native_file.read_bytes(), NATIVE)[1]
            expected = b''.join(native[((y // 4) * 32 + x // 4) * 4:((y // 4) * 32 + x // 4) * 4 + 4]
                                for y in range(160) for x in range(128))
            if pixels != expected:
                raise ValueError('Nearest4x portrait pixels do not preserve the native source')
        if row.get('rendering') == 'redrawn128':
            if row['provenance'].get('base_method') == RETAINER_METHOD:
                validate_retainer_redrawn(person_id, row, source, pixels, retainer_cache)
                if row['pixel_sha256'] in previous_hashes | retainer_hashes:
                    raise ValueError('Retainer enhanced pixels duplicate another identity')
                retainer_hashes.add(row['pixel_sha256'])
            else:
                validate_redrawn(person_id,row,source,pixels)
        enhanced[person_id] = dict(path=path, width=size[0], height=size[1])
        if 'rendering' in row:
            enhanced[person_id]['rendering'] = row['rendering']
    return enhanced


def validate_redrawn(person_id, row, source, pixels):
    """A larger file is insufficient: retain its sources and verify real detail."""
    p = row['provenance']
    if p.get('base_method') != 'identity_preserving_redrawn128':
        raise ValueError('Redrawn portrait source method differs')
    directory = 'art/portraits/supplement-hd-v2/'
    def retained(path, expected):
        if (not isinstance(path,str) or Path(path).is_absolute() or '..' in Path(path).parts
                or not path.startswith(directory) or not isinstance(expected,str) or not HEX.fullmatch(expected)):
            raise ValueError('Invalid retained redraw path or hash')
        file = ROOT/path
        if (file.is_symlink() or not file.resolve().is_relative_to((ROOT/directory).resolve())
                or not file.is_file() or sha(file.read_bytes()) != expected):
            raise ValueError('Retained redraw source is missing or changed')
        return file.read_bytes()
    if p.get('redraw_plan') != directory+'plan.json':
        raise ValueError('Redrawn portrait plan path differs')
    plan = json.loads(retained(p['redraw_plan'],p.get('redraw_plan_sha256')))
    if plan.get('schema') != 'tk2-portrait-redraw-v2' or plan.get('size') != [128,160]:
        raise ValueError('Invalid redrawn portrait plan')
    person = plan.get('people',{}).get(person_id)
    if not isinstance(person,dict):
        raise ValueError('Redrawn portrait plan belongs to another person')
    native = person.get('native',{})
    if native.get('path') != 'game'+source['path'] or native.get('sha256') != source['png_sha256']:
        raise ValueError('Redrawn portrait native source differs')
    native_pixels = png_pixels((ROOT/'game'/source['path'].lstrip('/')).read_bytes(),NATIVE)[1]
    if native.get('rgba_sha256') != sha(native_pixels):
        raise ValueError('Redrawn portrait native pixels differ')
    old = person.get('original_enhanced',{})
    if (old.get('path') != directory+'original-enhanced/'+person_id+'.png'
            or p.get('original_enhanced') != old.get('path')
            or p.get('original_enhanced_sha256') != old.get('sha256')):
        raise ValueError('Redrawn portrait previous file binding differs')
    old_pixels = png_pixels(retained(old['path'],old.get('sha256')),ENHANCED)[1]
    if sha(old_pixels) != old.get('rgba_sha256'):
        raise ValueError('Redrawn portrait archived pixels differ')
    for key, suffix in (('generated_source','sources/'+person_id+'.png'),('prompt','prompts/'+person_id+'.txt')):
        if (person.get(key) != directory+suffix or p.get(key) != person.get(key)
                or p.get(key+'_sha256') != person.get(key+'_sha256')):
            raise ValueError('Redrawn portrait authored source binding differs')
        retained(person[key],person.get(key+'_sha256'))
    authored = retained(person['generated_source'],person['generated_source_sha256'])
    if len(authored)<33 or authored[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Redrawn portrait authored source is not a PNG')
    source_size = list(struct.unpack('>II',authored[16:24]))
    if min(source_size)<128 or max(source_size)>4096:
        raise ValueError('Redrawn portrait authored source resolution is insufficient')
    baseline = b''.join(native_pixels[((y//4)*32+x//4)*4:((y//4)*32+x//4)*4+4]
                        for y in range(160) for x in range(128))
    if old_pixels != baseline:
        raise ValueError('Redrawn portrait archived fourfold source differs from native')
    changed = sum(pixels[i:i+4] != baseline[i:i+4] for i in range(0,len(pixels),4))
    colors = len({pixels[i:i+4] for i in range(0,len(pixels),4)})
    blocks = sum(len({pixels[((y+dy)*128+x+dx)*4:((y+dy)*128+x+dx)*4+4]
                         for dy in range(4) for dx in range(4)}) > 1
                 for y in range(0,160,4) for x in range(0,128,4))
    qa = p.get('qa',{})
    if (not isinstance(qa,dict) or qa.get('size') != [128,160] or qa.get('nearest4xExact') is not False
            or qa.get('source_size') != source_size
            or type(qa.get('changedPixels')) is not int or qa['changedPixels'] != changed or changed < 1024
            or type(qa.get('paletteSize')) is not int or qa['paletteSize'] != colors or not 5 <= colors <= 16
            or type(qa.get('nonUniformBlocks4x4')) is not int
            or qa['nonUniformBlocks4x4'] != blocks or blocks < 20):
        raise ValueError('Redrawn portrait has insufficient or misreported high resolution detail')


def retainer_retained(path, expected=None, *, directory='art/portraits/retainer-additions-v1', cache=None):
    """The new plan has its own strict source boundary; old redraw rules stay intact."""
    if (not isinstance(path, str) or not path or '\\' in path or Path(path).is_absolute()
            or '..' in Path(path).parts or str(Path(path)) != path
            or not (ROOT / path).is_relative_to(ROOT / directory)
            or (expected is not None and (not isinstance(expected, str) or not HEX.fullmatch(expected)))):
        raise ValueError('Invalid retained retainer path or hash')
    current = ROOT
    for part in Path(path).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Retainer source cannot use a symlink')
    file = ROOT / path
    if not file.is_file() or not file.resolve().is_relative_to((ROOT / directory).resolve()):
        raise ValueError('Retained retainer source is missing or outside its directory')
    key = ('raw', path)
    raw = cache.get(key) if cache is not None else None
    if raw is None:
        raw = file.read_bytes()
        if cache is not None:
            cache[key] = raw
    if expected is not None and sha(raw) != expected:
        raise ValueError('Retained retainer source hash differs')
    return raw


def retainer_plan(cache):
    if 'plan' not in cache:
        raw = retainer_retained(RETAINER_PLAN, cache=cache)
        plan = json.loads(raw)
        if (plan.get('schema') != 'tk2-retainer-portrait-additions-v1'
                or plan.get('native_size') != [32, 40] or plan.get('enhanced_size') != [128, 160]
                or not isinstance(plan.get('people'), list) or not plan['people']):
            raise ValueError('Invalid retainer portrait plan')
        people = {}
        for person in plan['people']:
            if (not isinstance(person, dict) or not isinstance(person.get('person_id'), str)
                    or not re.fullmatch(r'[a-z0-9-]+', person['person_id'])
                    or person['person_id'] in people):
                raise ValueError('Invalid or repeated retainer portrait identity')
            people[person['person_id']] = person
        cache.update(plan=(plan, sha(raw), people))
    return cache['plan']


def retainer_records(kind, cache):
    key = ('records', kind)
    if key not in cache:
        _, plan_hash, people = retainer_plan(cache)
        path = str(Path(RETAINER_PLAN).parent / (kind + '-records.json'))
        data = json.loads(retainer_retained(path, cache=cache))
        if (data.get('schema') != f'tk2-retainer-portrait-{kind}-records-v1'
                or data.get('plan') != RETAINER_PLAN or data.get('plan_sha256') != plan_hash
                or not isinstance(data.get('people'), dict) or set(data['people']) != set(people)
                or type(data.get('count')) is not int or data['count'] != len(people)):
            raise ValueError('Retainer portrait archive records differ from its plan')
        cache[key] = data['people']
    return cache[key]


def retainer_binding(person_id, binding, cache):
    """Check native attribution, geometry, plan identity and retained compatibility file."""
    _, plan_hash, planned = retainer_plan(cache)
    person = planned.get(person_id)
    if (not isinstance(person, dict) or binding.get('retainer_plan') != RETAINER_PLAN
            or binding.get('retainer_plan_sha256') != plan_hash
            or binding.get('name') != person.get('name')
            or binding.get('gender_design') != person.get('art_gender_design')
            or binding != retainer_records('native', cache).get(person_id)):
        raise ValueError('Retainer native identity or archive binding differs')
    atlas, single = person.get('source_atlas'), person.get('source_path')
    if bool(atlas) == bool(single):
        raise ValueError('Retainer plan needs exactly one authored source')
    relative = atlas or single
    expected_hash = person.get('source_sha256')
    if not isinstance(expected_hash, str) or not HEX.fullmatch(expected_hash):
        raise ValueError('Retainer authored source needs a pinned hash')
    raw = retainer_retained(relative, expected_hash,
                            directory='art/portraits/source-atlases' if atlas else str(Path(RETAINER_PLAN).parent),
                            cache=cache)
    if len(raw) < 33 or raw[:8] != b'\x89PNG\r\n\x1a\n' or not relative.endswith('.png'):
        raise ValueError('Retainer authored source is not a PNG')
    dimensions = list(struct.unpack('>II', raw[16:24]))
    if (person.get('source_size') != dimensions or min(dimensions) < 128 or max(dimensions) > 4096
            or binding.get('source_size') != dimensions
            or binding.get('original_source_path') != relative
            or binding.get('original_source_sha256') != expected_hash):
        raise ValueError('Retainer authored source geometry or attribution differs')
    matte = person.get('source_matte', 'black' if atlas else 'alpha')
    if matte not in ('black', 'alpha') or binding.get('source_matte') != matte:
        raise ValueError('Retainer source matte differs')
    if atlas:
        grid, index = person.get('grid'), person.get('cell_index')
        if (person.get('source_kind') != 'reused_unassigned_imagegen_cell' or matte != 'black'
                or grid != [8, 8] or any(type(value) is not int for value in grid)
                or type(index) is not int or not 0 <= index < 64
                or binding.get('native_kind') != 'generated'
                or any(key.startswith('native_original_') for key in person)
                or binding.get('source_atlas') != relative
                or binding.get('source_atlas_sha256') != expected_hash
                or binding.get('cell_index') != index or type(binding.get('cell_index')) is not int
                or binding.get('source_origin') != 'retained_unassigned_imagegen_cell'
                or 'Previously authored, unassigned' not in binding.get('reuse_notice', '')
                or 'not newly generated' not in binding.get('reuse_notice', '')):
            raise ValueError('Retainer reused source cell attribution differs')
        if 'generated' not in cache:
            cache['generated'] = read('game/config/portrait-generated.json')
        rows = [row for row in cache['generated']['source_atlases'] if row.get('path') == relative]
        if (len(rows) != 1 or rows[0].get('sha256') != expected_hash
                or rows[0].get('art_gender_design') != person.get('art_gender_design')):
            raise ValueError('Retainer source atlas art direction differs')
        partition = rows[0].get('actual_grid_partition', {})
        xs, ys = partition.get('x_bounds'), partition.get('y_bounds')
        if any(not isinstance(axis, list) or len(axis) != 9 or axis[0] != 0
               or axis[-1] != extent or any(type(v) is not int for v in axis)
               or any(a >= b for a, b in zip(axis, axis[1:]))
               for axis, extent in ((xs, dimensions[0]), (ys, dimensions[1]))):
            raise ValueError('Retainer source atlas partition differs')
        col, row = index % 8, index // 8
        box = [xs[col], ys[row], xs[col + 1], ys[row + 1]]
    else:
        if (person.get('source_kind') not in ('imagegen_new_pixel_art', 'original_portrait_redraw')
                or any(key in person or key in binding for key in ('source_atlas', 'cell_index', 'grid'))
                or binding.get('source_path') != relative or binding.get('source_sha256') != expected_hash):
            raise ValueError('Retainer single authored source attribution differs')
        original = person['source_kind'] == 'original_portrait_redraw'
        expected_origin = ('identity_preserving_original_portrait_redraw' if original
                           else 'new_retained_imagegen_source')
        if binding.get('source_origin') != expected_origin:
            raise ValueError('Retainer single authored source origin differs')
        if original:
            original_id = person.get('native_original_id')
            original_path = person.get('native_original_path')
            original_hash = person.get('native_original_sha256')
            if (type(original_id) is not int or not 0 <= original_id < 237
                    or original_path != f'game/assets/portraits/original/{original_id:03d}.png'
                    or binding.get('native_kind') != 'nes_original'
                    or binding.get('source') != 'pinned_ROM_static_frame0'
                    or binding.get('path') != original_path.removeprefix('game')
                    or binding.get('png_sha256') != original_hash
                    or any(binding.get(key) != person.get(key) for key in (
                        'native_original_id', 'native_original_path', 'native_original_sha256'))):
                raise ValueError('Retainer original portrait identity differs')
            originals = read('game/config/portrait-originals.json')['by_original_id']
            identities = {row['original_id']: row['person_id']
                          for row in read('game/config/portrait-identity-map.json')['records']}
            archived = originals.get(str(original_id), {})
            if (identities.get(original_id) != person_id or archived.get('png_sha256') != original_hash
                    or archived.get('rgba_sha256') != binding.get('rgba_sha256')):
                raise ValueError('Retainer redraw native is not the independently reviewed original')
            retainer_retained(original_path, original_hash,
                              directory='game/assets/portraits/original', cache=cache)
        elif (binding.get('native_kind') != 'generated'
              or any(key.startswith('native_original_') for key in person)
              or any(key.startswith('native_original_') for key in binding)):
            raise ValueError('Generated retainer cannot claim an original portrait')
        box = [0, 0, dimensions[0], dimensions[1]]
    if binding.get('source_cell_box') != box:
        raise ValueError('Retainer source crop box differs from its authored cell')
    visible, fitted = binding.get('source_visible_box'), binding.get('native_fitted_box')
    if (not isinstance(visible, list) or len(visible) != 4 or any(type(v) is not int for v in visible)
            or not box[0] < visible[0] < visible[2] < box[2]
            or not box[1] < visible[1] < visible[3] < box[3]
            or not isinstance(fitted, list) or len(fitted) != 4 or any(type(v) is not int for v in fitted)
            or not 0 < fitted[0] < fitted[2] < 32 or not 0 < fitted[1] < fitted[3] < 40):
        raise ValueError('Retainer source or native envelope is clipped')
    archive = str(Path(RETAINER_PLAN).parent / 'native-32x40' / (person_id + '.png'))
    archive_raw = retainer_retained(archive, binding['png_sha256'], cache=cache)
    if sha(png_pixels(archive_raw, NATIVE)[1]) != binding['rgba_sha256']:
        raise ValueError('Retainer native compatibility archive pixels differ')
    if 'prompt' in person or 'prompt_sha256' in person:
        prompt_hash = person.get('prompt_sha256')
        if not isinstance(prompt_hash, str) or not HEX.fullmatch(prompt_hash):
            raise ValueError('Retainer prompt needs a pinned hash')
        retainer_retained(person.get('prompt'), prompt_hash, cache=cache)
    return person, raw, dimensions, box


def validate_retainer_redrawn(person_id, row, source, pixels, cache=None):
    """Validate direct authored detail independently of the immutable HD-v2 study."""
    cache = {} if cache is None else cache
    if source.get('retainer_plan') != RETAINER_PLAN:
        raise ValueError('Retainer HD portrait lacks a native retainer identity')
    binding = retainer_records('native', cache).get(person_id)
    if (not isinstance(binding, dict) or binding.get('path') != source.get('path')
            or binding.get('png_sha256') != source.get('png_sha256')):
        raise ValueError('Retainer HD portrait native source differs')
    person, authored, dimensions, box = retainer_binding(person_id, binding, cache)
    proof = row['provenance']
    if (row != retainer_records('enhanced', cache).get(person_id)
            or proof.get('base_method') != RETAINER_METHOD
            or proof.get('retainer_plan') != RETAINER_PLAN
            or proof.get('retainer_plan_sha256') != binding['retainer_plan_sha256']
            or proof.get('source_cell_box') != box
            or proof.get('native_fitted_box') != binding['native_fitted_box']):
        raise ValueError('Retainer enhanced archive or source geometry differs')
    for key in ('original_source_path', 'original_source_sha256', 'source_size', 'source_matte', 'source_origin'):
        if proof.get(key) != binding.get(key):
            raise ValueError('Retainer enhanced authored source binding differs')
    for key in ('source_atlas', 'source_atlas_sha256', 'cell_index', 'grid', 'source_path', 'source_sha256',
                'reuse_notice', 'native_original_id', 'native_original_path', 'native_original_sha256'):
        if key in binding and proof.get(key) != binding[key]:
            raise ValueError('Retainer enhanced source attribution differs')
    if 'prompt' in person and any(proof.get(key) != person.get(key) for key in ('prompt', 'prompt_sha256')):
        raise ValueError('Retainer enhanced prompt binding differs')
    directory = str(Path(RETAINER_PLAN).parent) + '/'
    crop_path = directory + 'source-crops/' + person_id + '.png'
    archive_path = directory + 'native-32x40/' + person_id + '.png'
    if (proof.get('retained_source_crop') != crop_path or proof.get('native_archive') != archive_path
            or proof.get('native_archive_sha256') != binding['png_sha256']):
        raise ValueError('Retainer enhanced retained archive path differs')
    crop_hash = proof.get('retained_source_crop_sha256')
    if not isinstance(crop_hash, str) or not HEX.fullmatch(crop_hash):
        raise ValueError('Retainer source crop needs a pinned hash')
    crop_raw = retainer_retained(crop_path, crop_hash, cache=cache)
    width, height = box[2] - box[0], box[3] - box[1]
    crop_pixels = png_pixels(crop_raw, (width, height))[1]
    if width < 96 or height < 128 or sha(crop_pixels) != proof.get('retained_source_crop_rgba_sha256'):
        raise ValueError('Retainer source crop has insufficient or changed pixels')
    authored_key = ('decoded-source', proof['original_source_path'])
    if authored_key not in cache:
        cache[authored_key] = png_pixels(authored, tuple(dimensions))[1]
    full = cache[authored_key]
    expected_crop = b''.join(full[(y * dimensions[0] + box[0]) * 4:(y * dimensions[0] + box[2]) * 4]
                             for y in range(box[1], box[3]))
    if crop_pixels != expected_crop:
        raise ValueError('Retainer source crop does not preserve its authored original')
    visible = [width, height, 0, 0]
    for y in range(height):
        for x in range(width):
            color = crop_pixels[(y * width + x) * 4:(y * width + x) * 4 + 4]
            if color[3] >= 128 and (proof['source_matte'] == 'alpha' or max(color[:3]) > 32):
                visible = [min(visible[0], x), min(visible[1], y), max(visible[2], x + 1), max(visible[3], y + 1)]
    if (visible[0] <= 0 or visible[1] <= 0 or visible[2] >= width or visible[3] >= height
            or visible[2] - visible[0] < 60 or visible[3] - visible[1] < 96
            or proof.get('source_visible_box') != [box[0] + visible[0], box[1] + visible[1],
                                                  box[0] + visible[2], box[1] + visible[3]]):
        raise ValueError('Retainer authored visible portrait is clipped or misreported')
    for oy in range(4):
        for ox in range(4):
            fine = any(any(crop_pixels[((y + dy) * width + x + dx) * 4:((y + dy) * width + x + dx) * 4 + 4]
                           != crop_pixels[(y * width + x) * 4:(y * width + x) * 4 + 4]
                           for dy in range(4) for dx in range(4))
                       for y in range(oy, height - 3, 4) for x in range(ox, width - 3, 4))
            if not fine:
                raise ValueError('Retainer authored source is only a nearest4x enlargement')
    native_pixels = png_pixels((ROOT / 'game' / source['path'].lstrip('/')).read_bytes(), NATIVE)[1]
    baseline = b''.join(native_pixels[((y // 4) * 32 + x // 4) * 4:((y // 4) * 32 + x // 4) * 4 + 4]
                        for y in range(160) for x in range(128))
    changed = sum(pixels[i:i + 4] != baseline[i:i + 4] for i in range(0, len(pixels), 4))
    colors = {tuple(pixels[i:i + 4]) for i in range(0, len(pixels), 4)}
    blocks = sum(len({pixels[((y + dy) * 128 + x + dx) * 4:((y + dy) * 128 + x + dx) * 4 + 4]
                      for dy in range(4) for dx in range(4)}) > 1
                 for y in range(0, 160, 4) for x in range(0, 128, 4))
    qa = proof.get('qa', {})
    if (not isinstance(qa, dict) or qa.get('size') != [128, 160] or qa.get('nearest4xExact') is not False
            or type(qa.get('changedPixels')) is not int or qa['changedPixels'] != changed or changed < 1024
            or type(qa.get('paletteSize')) is not int or qa['paletteSize'] != len(colors)
            or not 5 <= len(colors) <= 16 or not colors <= RETAINER_PALETTE
            or type(qa.get('nonUniformBlocks4x4')) is not int
            or qa['nonUniformBlocks4x4'] != blocks or blocks < 20):
        raise ValueError('Retainer HD portrait has insufficient or misreported authored detail')


def identities():
    canonical = read('game/config/campaigns/people.json')
    expected = {pid: (row['name'], row['runtime_id']) for pid, row in canonical['people'].items()}
    if (set(canonical['order']) != set(expected)
            or len(canonical['order']) != len(expected)):
        raise ValueError('Canonical portrait identity order differs')
    index = read('game/data/campaigns/index.json')
    people, stable = None, None
    for path in index['catalogs']:
        rows = read('game/data/' + path)['people']
        current = {p['person_id']: (p['name'], p['runtime_id']) for p in rows}
        if len(current) != len(rows) or len({p['runtime_id'] for p in rows}) != len(rows):
            raise ValueError('Duplicate portrait person/runtime identity')
        if stable is not None and current != stable:
            raise ValueError('Scenario portrait identities diverge')
        people, stable = rows, current
    if people is None or stable != expected:
        raise ValueError('Campaign portrait identities differ from the canonical pool')
    return {p['person_id']: p for p in people}


def build():
    people = identities()
    mapping = read('game/config/portrait-identity-map.json')
    originals = read('game/config/portrait-originals.json')
    generated = read('game/config/portrait-generated.json')
    if mapping.get('schema') != 'tk2-portrait-identities-v1' or originals.get('schema') != 'tk2-original-portraits-v1' or generated.get('schema') != 'tk2-generated-portraits-v1':
        raise ValueError('Unknown portrait manifest schema')
    if mapping['rom_sha256'] != originals['rom_sha256'] or tuple(originals['native_size']) != NATIVE:
        raise ValueError('Original portrait source mismatch')
    if set(originals['by_original_id']) != {str(i) for i in range(237)}:
        raise ValueError('Original237 portrait archive incomplete')
    evidence = mapping['evidence']
    if evidence['path'] != '/assets/portraits/evidence/original-name-glyphs.png' or sha((ROOT / 'game' / evidence['path'].lstrip('/')).read_bytes()) != evidence['sha256']:
        raise ValueError('Original name glyph evidence mismatch')
    validated_originals = {}
    for key, row in originals['by_original_id'].items():
        if row['original_id'] != int(key) or row['frame'] != 0:
            raise ValueError('Wrong original portrait identity/frame')
        if row['path'] != f'/assets/portraits/original/{int(key):03d}.png':
            raise ValueError('Original portrait file is bound to a different numeric ID')
        validated_originals[int(key)] = image_record(row)[0]
    records = mapping['records']
    if len(records) != 237 or {r['original_id'] for r in records} != set(range(237)):
        raise ValueError('Original name identity mapping incomplete')
    bound, bound_ids = {}, set()
    for row in records:
        proof = row['evidence']
        name_bytes = bytes.fromhex(proof['name_glyph_record_hex'])
        if len(name_bytes) != 13 or sha(name_bytes) != proof['rom_name_record_sha256']:
            raise ValueError('Original name record evidence mismatch')
        cell = [row['original_id'] % 16 * 64, row['original_id'] // 16 * 32, 64, 32]
        if proof['name_glyph_atlas'] != evidence['path'] or proof['name_glyph_atlas_cell'] != cell:
            raise ValueError('Original name glyph cell mismatch')
        person = row.get('person_id')
        if person is None:
            continue
        if person not in people or person in bound:
            raise ValueError('Unknown/duplicate original person binding')
        bound[person] = row
        bound_ids.add(row['original_id'])
    if len(bound) != mapping['bound_original_people'] or len(bound_ids) != len(bound):
        raise ValueError('Original portrait binding count mismatch')
    new = generated['by_person_id']
    if set(new) != set(people) - set(bound):
        raise ValueError('New portrait coverage must exactly match unbound stable identities')
    output, source_atlases, used_cells, retainer_cache = {}, {}, set(), {}
    retainer_originals = set()
    if (ROOT / RETAINER_PLAN).exists():
        _, _, planned = retainer_plan(retainer_cache)
        retainer_originals = {pid for pid, person in planned.items()
                             if person.get('source_kind') == 'original_portrait_redraw'}
        if not retainer_originals <= set(bound):
            raise ValueError('Retainer original redraw has no reviewed original identity')
    visible_colors = {tuple(value[:3]) for value in originals['palette']['rgba']}
    for person_id, person in people.items():
        if person_id in bound:
            identity = bound[person_id]
            original_id = identity['original_id']
            item = dict(validated_originals[original_id], kind='nes_original', original_id=original_id,
                        source='pinned_ROM_static_frame0', original_transcribed_name=identity['transcribed_name'])
            if person_id in retainer_originals:
                binding = retainer_records('native', retainer_cache)[person_id]
                if binding.get('native_original_id') != original_id:
                    raise ValueError('Retainer original redraw binds another original identity')
                retainer_binding(person_id, binding, retainer_cache)
                item.update(**{key: binding[key] for key in ('retainer_plan', 'retainer_plan_sha256',
                                'original_source_path', 'original_source_sha256', 'source_origin')})
        else:
            source = new[person_id]
            if source.get('source') != 'imagegen_new_pixel_art' or source.get('art_direction_basis') != 'authorial_game_art_not_historical_likeness':
                raise ValueError('New art must state its actual generation provenance')
            item, pixels = image_record(source)
            if item['path'] != f'/assets/portraits/generated/{person_id}.png':
                raise ValueError('New portrait is bound to a different person file')
            colors = {tuple(pixels[i:i + 3]) for i in range(0, len(pixels), 4) if pixels[i + 3]}
            if not colors <= visible_colors:
                raise ValueError('New portrait departs from the original visible palette')
            if any(pixels[i] not in (0, 255) for i in range(3, len(pixels), 4)):
                raise ValueError('New portrait contains non-native partial transparency')
            if source.get('retainer_plan') == RETAINER_PLAN:
                retainer_binding(person_id, source, retainer_cache)
                cell = (source['original_source_path'], source.get('cell_index', 'single'))
                if cell in used_cells:
                    raise ValueError('Generated source cell is assigned to more than one person')
                used_cells.add(cell)
                item.update(kind='generated', original_id=None, source=source['source'],
                            art_direction_basis=source['art_direction_basis'],
                            **{key: source[key] for key in ('retainer_plan', 'retainer_plan_sha256',
                               'original_source_path', 'original_source_sha256', 'source_origin')})
                for key in ('source_atlas', 'source_atlas_sha256', 'cell_index', 'source_path', 'source_sha256'):
                    if key in source:
                        item[key] = source[key]
            else:
                atlas = source['source_atlas']
                if not isinstance(atlas, str) or not atlas.startswith('art/portraits/') or '..' in Path(atlas).parts or Path(atlas).suffix.lower() != '.png':
                    raise ValueError('Invalid art source atlas')
                if atlas not in source_atlases:
                    source_atlases[atlas] = sha((ROOT / atlas).read_bytes())
                if source_atlases[atlas] != source['source_atlas_sha256']:
                    raise ValueError('Generated source atlas hash mismatch')
                if type(source.get('cell_index')) is not int or not 0 <= source['cell_index'] < 64:
                    raise ValueError('Generated atlas cell index invalid')
                cell = (atlas, source['cell_index'])
                if cell in used_cells:
                    raise ValueError('Generated source cell is assigned to more than one person')
                used_cells.add(cell)
                item.update(kind='generated', original_id=None, source=source['source'],
                            art_direction_basis=source['art_direction_basis'], source_atlas=atlas,
                            source_atlas_sha256=source_atlases[atlas], cell_index=source['cell_index'])
        output[person_id] = dict(item, name=person['name'])
    counts = Counter(item['kind'] for item in output.values())
    generated_unique = len({r['rgba_sha256'] for r in output.values() if r['kind'] == 'generated'})
    if generated_unique != counts['generated']:
        raise ValueError('Generated portraits contain duplicate pixel images; review the source cells')
    sources = {name: sha((ROOT / 'game/config' / name).read_bytes()) for name in
               ('portrait-identity-map.json', 'portrait-originals.json', 'portrait-generated.json')}
    if (ROOT / ENHANCED_CONFIG).is_file():
        for person_id, variant in enhanced_records(read(ENHANCED_CONFIG), output).items():
            output[person_id]['enhanced'] = variant
        sources['portrait-enhanced.json'] = sha((ROOT / ENHANCED_CONFIG).read_bytes())
    result = dict(schema='tk2-portraits-v1', width=32, height=40, display_background='#000000',
        identity_policy='stable_person_id; no ordinal or similarity matching; saves and released catalogs unchanged',
        generated_likeness_policy='new game art, not claimed historical likeness or an original NES portrait',
        counts=dict(people=len(output), nes_original=counts['nes_original'], generated=counts['generated'],
                    original_archive=237, original_unique_pixels=len({r['rgba_sha256'] for r in validated_originals.values()}),
                    bound_original_unique_pixels=len({r['rgba_sha256'] for r in output.values() if r['kind'] == 'nes_original'}),
                    generated_unique_pixels=generated_unique, original_identity_pending=237 - len(bound)),
        sources=sources,
        by_runtime_id={str(p['runtime_id']): p['person_id'] for p in people.values()}, people=output)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    raw = (json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    path = ROOT / 'game/assets/portraits/index.json'
    if args.check:
        if path.read_bytes() != raw:
            raise SystemExit('Portrait index differs from the checked sources')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
