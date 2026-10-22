#!/usr/bin/env python3
"""Bind extracted/new portraits to stable identities without changing any save catalog.

All 1023 bindings must have genuine, checked PNG assets. Missing images are an
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
HEX = re.compile(r'^[0-9a-f]{64}$')
ASSET = re.compile(r'^/assets/portraits/(?:original/[0-9]{3}|generated/[a-z0-9-]+)\.png$')


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png_pixels(raw):
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
    if (width, height) != NATIVE or depth != 8 or color not in (2, 6) or any((compression, filtering, interlace)):
        raise ValueError('Portrait must be a native32x40, noninterlaced8bit RGB/RGBA PNG')
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
    return NATIVE, bytes(output)


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


def identities():
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
    if people is None or len(people) != 1023:
        raise ValueError('Expected the released1023-person pool')
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
    output, source_atlases, used_cells = {}, {}, set()
    visible_colors = {tuple(value[:3]) for value in originals['palette']['rgba']}
    for person_id, person in people.items():
        if person_id in bound:
            identity = bound[person_id]
            original_id = identity['original_id']
            item = dict(validated_originals[original_id], kind='nes_original', original_id=original_id,
                        source='pinned_ROM_static_frame0', original_transcribed_name=identity['transcribed_name'])
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
    result = dict(schema='tk2-portraits-v1', width=32, height=40, display_background='#000000',
        identity_policy='stable_person_id; no ordinal or similarity matching; saves and released catalogs unchanged',
        generated_likeness_policy='new game art, not claimed historical likeness or an original NES portrait',
        counts=dict(people=len(output), nes_original=counts['nes_original'], generated=counts['generated'],
                    original_archive=237, original_unique_pixels=len({r['rgba_sha256'] for r in validated_originals.values()}),
                    bound_original_unique_pixels=len({r['rgba_sha256'] for r in output.values() if r['kind'] == 'nes_original'}),
                    generated_unique_pixels=generated_unique, original_identity_pending=237 - len(bound)),
        sources={name: sha((ROOT / 'game/config' / name).read_bytes()) for name in
                 ('portrait-identity-map.json', 'portrait-originals.json', 'portrait-generated.json')},
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
