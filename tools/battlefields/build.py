#!/usr/bin/env python3
"""Export all 30 native battle backgrounds; verify shipped output without a ROM.

Rebuilding requires the pinned user ROM and read-only native-capture archive.
Checking requires only this repository and Python's standard library. Nothing in
this module starts an emulator, edits a save state, or invents original pixels.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'game/assets/battlefields'
EVIDENCE = ROOT / 'tools/battlefields/evidence'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA = '924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
GRID = dict(columns=31, rows=19, tile_size=16, width=496, height=304)
CHR_PAGES = (139, 137, 138, 136)
BG_PALETTE = (15, 39, 25, 10, 15, 25, 18, 2, 15, 54, 32, 22, 15, 32, 32, 32)
# These six royaltea colors are independently checked against native screenshots.
# No unobserved RGB palette entries are needed by any of the 30 backgrounds.
COLORS = {15: (0, 0, 0, 255), 39: (247, 162, 71, 255),
          25: (36, 109, 2, 255), 10: (0, 53, 8, 255),
          18: (42, 68, 255, 255), 2: (15, 23, 176, 255)}
WITNESSES = {5: 'city5-map-e4613f07e4f9', 6: 'city6-map-f949847ec5cb',
             9: 'city9-map-0c8a1fd93bb7'}
TABLES = dict(classifier=(0x1175B, 128), tile_pointers=(0x117DB, 240),
              bank_selectors=(0x118CB, 120), graphics_tile_pointers=(0x2E652, 240),
              attribute_pointers=(0x2E742, 240), graphics_bank_selectors=(0x2E832, 120),
              city_descriptor_pointers=(0x31F5A, 60), metatiles=(0x3F487, 512),
              service_coordinates=(0x23BB4, 180))
LABEL_REFERENCE = 'game/config/references/original-facilities-v1.json'


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def png_pixels(raw, size):
    # Reuse the strict, standard-library PNG decoder used for shipped portraits.
    spec = importlib.util.spec_from_file_location('battlefield_png', ROOT / 'game/build_portrait_manifest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.png_pixels(raw, size)[1]


def png_bytes(pixels, width=496, height=304):
    require(len(pixels) == width * height * 4, 'Incorrect RGBA byte count')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + pixels[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def state_blocks(raw):
    def chunks(data):
        result, offset = {}, 0
        while offset < len(data):
            require(offset + 8 <= len(data), 'Truncated native state chunk')
            tag, length = data[offset:offset + 4], struct.unpack_from('<I', data, offset + 4)[0]
            end = offset + 8 + length
            require(end <= len(data) and tag not in result, 'Invalid native state chunk')
            result[tag] = data[offset + 8:end]
            offset = end
        return result
    def unpack(raw, size):
        require(raw and raw[0] in (0, 1), 'Unknown native compression')
        data = raw[1:] if raw[0] == 0 else zlib.decompress(raw[1:])
        require(len(data) == size, 'Native PPU block size mismatch')
        return data
    require(raw[:4] == b'NST\x1a', 'Expected Nestopia state')
    top = chunks(raw[8:8 + struct.unpack_from('<I', raw, 4)[0]])
    ppu = chunks(top[b'PPU\0'])
    return {name: unpack(ppu[tag], size) for name, tag, size in
            (('nametable', b'NMT\0', 2048), ('palette', b'PAL\0', 32), ('oam', b'OAM\0', 256))}


def blob(raw, offset=None):
    record = dict(length=len(raw), hex=raw.hex(), sha256=sha(raw))
    if offset is not None:
        record['rom_file_offset'] = offset
    return record


def unblob(record, size=None):
    raw = bytes.fromhex(record['hex'])
    require(len(raw) == record['length'] and sha(raw) == record['sha256'], 'Extracted source bytes/hash mismatch')
    require(size is None or len(raw) == size, 'Extracted source table size mismatch')
    return raw


def word(raw, offset):
    return raw[offset] | raw[offset + 1] << 8


def cell_source(decoder, city, x, visual_y):
    """Resolve native packed coordinates, skipping metadata row 15."""
    packed_y = visual_y if visual_y < 15 else visual_y + 1
    desc = decoder['descriptors'][city]
    quadrant = int(x >= 16) | 2 * int(packed_y >= 16)
    chunk = decoder['chunks'][desc['chunk_ids'][quadrant]]
    tiles = bytes.fromhex(chunk['tiles']['hex'])
    attrs = bytes.fromhex(chunk['attributes']['hex'])
    local_x, local_y = x % 16, packed_y % 16
    tile = tiles[local_y * 16 + local_x]
    attr = attrs[(local_y // 2) * 8 + local_x // 2]
    palette = attr >> ((local_y % 2) * 4 + (local_x % 2) * 2) & 3
    return tile, palette


def tile_indices(decoder, tile, palette):
    meta = bytes.fromhex(decoder['tables']['metatiles']['hex'])
    quad = meta[tile * 4:tile * 4 + 4]
    pages = [bytes.fromhex(row['hex']) for row in decoder['chr_pages']]
    indices = []
    for y in range(16):
        for x in range(16):
            code = quad[(y // 8) * 2 + x // 8]
            page, offset, bit = pages[code // 64], (code % 64) * 16 + y % 8, 7 - x % 8
            index = (page[offset] >> bit & 1) | (page[offset + 8] >> bit & 1) << 1
            indices.append(0 if index == 0 else palette * 4 + index)
    return indices


def render(decoder, tiles, palettes):
    # Cache at most 128*4 metatiles. The complete map retains original pixels.
    cache = {}
    image = bytearray(GRID['width'] * GRID['height'] * 4)
    colors = {int(k): bytes(v) for k, v in decoder['nes_to_rgba'].items()}
    used_colors = set()
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            palette = palettes[y][x]
            key = tile, palette
            if key not in cache:
                codes = [decoder['bg_palette'][i] for i in tile_indices(decoder, tile, palette)]
                require(set(codes) <= colors.keys(), 'Map needs an RGB color absent from native evidence')
                used_colors.update(codes)
                cache[key] = b''.join(colors[code] for code in codes)
            pixels = cache[key]
            for dy in range(16):
                dest = ((y * 16 + dy) * GRID['width'] + x * 16) * 4
                image[dest:dest + 64] = pixels[dy * 64:(dy + 1) * 64]
    return bytes(image), used_colors


def verify_witness(decoder, maps, witness, screenshot):
    """Compare only unmodified native BG quads; exclude native OAM overlays."""
    require(sha(screenshot) == witness['screenshot_sha256'], 'Native screenshot hash mismatch')
    pixels = png_pixels(screenshot, (256, 240))
    nmt = bytes.fromhex(witness['ppu']['nametable']['hex'])
    pal = bytes.fromhex(witness['ppu']['palette']['hex'])
    oam = bytes.fromhex(witness['ppu']['oam']['hex'])
    require(len(nmt) == 2048 and len(pal) == 32 and len(oam) == 256, 'Malformed native evidence')
    require(list(pal[:16]) == decoder['bg_palette'], 'Native palette disagrees with decoder')
    meta = bytes.fromhex(decoder['tables']['metatiles']['hex'])
    row = maps[f"original-{witness['original_city_index']:02d}"]
    checked, excluded, cells, overridden = 0, 0, 0, 0
    colors = Counter()
    for y in range(10):
        for x in range(16):
            tile, palette = row['tiles'][y][x], row['palettes'][y][x]
            quad = list(meta[tile * 4:tile * 4 + 4])
            offset = y * 64 + x * 2
            if quad != [nmt[offset], nmt[offset + 1], nmt[offset + 32], nmt[offset + 33]]:
                overridden += 1  # Original game writes officer/building overlays.
                continue
            attribute = nmt[960 + y // 2 * 8 + x // 2]
            actual_palette = attribute >> ((y % 2) * 4 + (x % 2) * 2) & 3
            require(actual_palette == palette, 'Native attribute selector mismatch')
            cells += 1
            indices = tile_indices(decoder, tile, palette)
            for dy in range(16):
                for dx in range(16):
                    px, py = x * 16 + dx, y * 16 + dy
                    if any(sy < 240 and sx <= px < sx + 8 and sy + 1 <= py < sy + 9
                           for sy, code, attrs, sx in zip(*[iter(oam)] * 4)):
                        excluded += 1
                        continue
                    code = pal[indices[dy * 16 + dx]]
                    expected = bytes(decoder['nes_to_rgba'][str(code)])
                    start = (py * 256 + px) * 4
                    require(pixels[start:start + 4] == expected, f'Native pixel mismatch in city {witness["original_city_index"]} at {px},{py}')
                    checked += 1
                    colors[str(code)] += 1
    return dict(checked_pixels=checked, excluded_oam_pixels=excluded, checked_cells=cells,
                overridden_cells=overridden, observed_nes_color_pixels=dict(sorted(colors.items())))


def extract_witnesses(archive):
    evidence = []
    for city, stem in WITNESSES.items():
        base = archive / 'analysis/phase5/terrain/core-views'
        meta_raw = (base / (stem + '-evidence.json')).read_bytes()
        meta = json.loads(meta_raw)
        screen = (base / (stem + '.png')).read_bytes()
        state = (base / (stem + '.state')).read_bytes()
        ram = (base / (stem + '-ram.bin')).read_bytes()
        capture_raw = (base / (stem + '.json')).read_bytes()
        capture = json.loads(capture_raw)
        require(meta['city'] == city and not meta['rom_modified'] and not meta['natural_gameplay'], 'Unexpected native fixture provenance')
        require(capture['rom_sha256'] == ROM_SHA and capture['engine']['core_sha256'] == CORE_SHA, 'Native fixture ROM/core mismatch')
        require(capture['core_options']['nestopia_palette'] == 'royaltea', 'Native fixture palette mismatch')
        require(sha(screen) == meta['image_sha256'] and sha(state) == meta['state_sha256']
                and sha(ram) == meta['ram_sha256'], 'Native fixture source hash mismatch')
        require(list(ram[0xB2:0xB6]) == list(CHR_PAGES) == meta['upper_map_bg_chr_pages'], 'Upper map CHR frame mismatch')
        require(meta['camera_pixels'] == [0, 0] and meta['native_map_pixel_translation'] == [0, 0], 'Native fixture is not the origin viewport')
        ppu = state_blocks(state)
        record = dict(original_city_index=city, screenshot=f'tools/battlefields/evidence/city{city:02d}.png',
                      screenshot_sha256=sha(screen), native_resolution=[256, 240], viewport=[0, 0, 256, 160],
                      archive_source=f'analysis/phase5/terrain/core-views/{stem}',
                      capture_metadata_sha256=sha(capture_raw), evidence_metadata_sha256=sha(meta_raw),
                      state_sha256=sha(state), ram_sha256=sha(ram),
                      engine=capture['engine'], palette_name='royaltea',
                      original_rom_unmodified=True, natural_gameplay=False,
                      fixture_ram_changes=meta['ram_changes'], camera_pixels=[0, 0],
                      upper_map_bg_chr_pages=list(CHR_PAGES),
                      ppu={key: blob(value) for key, value in ppu.items()})
        evidence.append((record, screen))
    return evidence


def build(rom_path, archive):
    rom = rom_path.read_bytes()
    require(sha(rom) == ROM_SHA, 'Pinned user ROM does not match; no output written')
    witnesses = extract_witnesses(archive)
    tables = {name: blob(rom[offset:offset + size], offset) for name, (offset, size) in TABLES.items()}
    require(tables['tile_pointers']['hex'] == tables['graphics_tile_pointers']['hex']
            and tables['bank_selectors']['hex'] == tables['graphics_bank_selectors']['hex'], 'Native movement/graphics table mismatch')
    decoder = dict(tables=tables, chr_pages=[], descriptors=[], chunks=[], bg_palette=list(BG_PALETTE),
                   nes_to_rgba={str(k): list(v) for k, v in sorted(COLORS.items())},
                   chr_frame='Fixed upper-map animation frame witnessed in native city5/6/9 captures; scanline animation is not emulated.')
    for page in CHR_PAGES:
        offset = 0x40010 + page * 1024
        decoder['chr_pages'].append(dict(page_1k=page, **blob(rom[offset:offset + 1024], offset)))
    for city in range(30):
        pointer = word(rom, 0x31F5A + city * 2)
        offset = 0x30010 + pointer - 0xC000
        decoder['descriptors'].append(dict(original_city_index=city, pointer_cpu=pointer,
                                           rom_file_offset=offset, chunk_ids=list(rom[offset:offset + 4]),
                                           sha256=sha(rom[offset:offset + 4])))
    for chunk in range(120):
        pointer, attr = word(rom, 0x117DB + chunk * 2), word(rom, 0x2E742 + chunk * 2)
        bank = (rom[0x118CB + chunk] & 63) % 32
        require(attr == pointer - 64, 'Unexpected native attribute layout')
        tile_file, attr_file = 16 + bank * 8192 + pointer - 0x8000, 16 + bank * 8192 + attr - 0x8000
        decoder['chunks'].append(dict(id=chunk, bank_8k=bank, tile_pointer_cpu=pointer,
                                       attribute_pointer_cpu=attr, tiles=blob(rom[tile_file:tile_file + 240], tile_file),
                                       attributes=blob(rom[attr_file:attr_file + 64], attr_file)))
    label_raw = (ROOT / LABEL_REFERENCE).read_bytes()
    labels = json.loads(label_raw)['records']
    classifier = bytes.fromhex(tables['classifier']['hex'])
    maps, rendered = {}, {}
    for city in range(30):
        ident = f'original-{city:02d}'
        tiles, palettes = [], []
        for y in range(19):
            cells = [cell_source(decoder, city, x, y) for x in range(31)]
            tiles.append([value[0] for value in cells]); palettes.append([value[1] for value in cells])
        raw_classes = [[classifier[tile] for tile in row] for row in tiles]
        classes = [[value if value < 6 else 2 for value in row] for row in raw_classes]
        def positions(predicate):
            return [dict(x=x, y=y, packed_y=y if y < 15 else y + 1, raw_tile=tiles[y][x], raw_class=value)
                    for y, row in enumerate(raw_classes) for x, value in enumerate(row) if predicate(value)]
        services = []
        for category, key in enumerate(('rice_shop', 'weapon_shop', 'hospital')):
            offset = 0x23BB4 + city * 6 + category * 2
            x, packed_y = rom[offset:offset + 2]
            present = (x, packed_y) != (255, 255)
            require(not present or 0 <= x < 31 and 0 <= packed_y < 20 and packed_y != 15, 'Invalid native service coordinates')
            services.append(dict(category=category, kind=key, present=present, original_xy=[x, packed_y],
                                 position=dict(x=x, y=packed_y if packed_y < 15 else packed_y - 1) if present else None,
                                 rom_file_offset=offset))
        pixels, _ = render(decoder, tiles, palettes)
        encoded = png_bytes(pixels)
        rendered[ident] = encoded
        label = labels[city]
        require(label['original_city_number'] == city + 1, 'Guide label order mismatch')
        maps[ident] = dict(id=ident, original_city_index=city, source_city_label=label['source_city_label'],
                          path=f'/assets/battlefields/{ident}.png', width=496, height=304,
                          sha256=sha(encoded), rgba_sha256=sha(pixels),
                          tile_grid_sha256=sha(bytes(tile for row in tiles for tile in row)),
                          tiles=tiles, raw_classes=raw_classes, classes=classes, palettes=palettes,
                          camps=positions(lambda c: c == 5), markers=positions(lambda c: c >= 6), services=services,
                          provenance=dict(descriptor_index=city, descriptor_sha256=decoder['descriptors'][city]['sha256'],
                                          chunk_ids=decoder['descriptors'][city]['chunk_ids'],
                                          source_label_row=label['source_row_id'], label_identity='Unverified guide transcription; not a ROM-glyph-certified city identity.'))
    witness_records = []
    for record, screen in witnesses:
        record['verification'] = verify_witness(decoder, maps, record, screen)
        witness_records.append(record)
    result = dict(schema='tk2-original-battlefields-v1', grid=GRID,
                  rom_sha256=ROM_SHA, maps=maps, decoder=decoder,
                  terrain_classes=[dict(id=i, key=key, confidence=confidence) for i, key, confidence in
                                   ((0, 'forest', 'Native pixels and recovered behavior'),
                                    (1, 'special_ground', 'Smooth earth-colored native pixels; official terrain name unresolved'),
                                    (2, 'plain', 'Native pixels and recovered movement classification'),
                                    (3, 'water', 'Native pixels and recovered tactic gates'),
                                    (4, 'mountain', 'Native pixels and recovered affinity costs'),
                                    (5, 'camp', 'Native base/capture behavior; building is a separate overlay'))],
                  movement_class_policy='Raw classes6/7/8 normalize to2 in both original player and AI movement. They are event markers, not additional terrain types. Positive original costs do not attest an impassable-terrain rule.',
                  layer_scope='Original background layer only. Officer flags, village/service and camp buildings are separate original overlays; their coordinates are supplied, not painted onto these backgrounds.',
                  source_labels=dict(reference=LABEL_REFERENCE, sha256=sha(label_raw),
                                     policy='Labels retain the external guide spelling; map IDs are authoritative. No direct join to the remake city identities is claimed.'),
                  native_verification=dict(witnesses=witness_records, checked_pixels=sum(w['verification']['checked_pixels'] for w in witness_records),
                                           policy='Exact origin-viewport BG CHR, attribute selectors and RGBA comparison. Original NMT replacements and OAM-covered pixels are excluded, not repainted.'),
                  coordinate_policy='31 columns ×19 visual rows. Original packed row15 stores attributes and is skipped; visual row15 corresponds to packed row16. Unused lower-chunk data is not playable.',
                  rights='Original game pixels/data retain their original rights; they are not MIT relicensed. Offline extraction is from the user-provided ROM and native captures.',
                  build=dict(tool='tools/battlefields/build.py', tool_sha256=sha(Path(__file__).read_bytes()),
                             runtime_requires_rom=False, runtime_requires_archive=False, runtime_requires_emulator=False,
                             checker_requires_rom=False, enhanced_render='Nearest-neighbor4x in the renderer; no AI redraw or substitute palette.'))
    # Validate every decode and native witness before making any shipped output.
    validate(result, lambda path: rendered[Path(path).stem],
             lambda path: dict((w['screenshot'], screen) for w, screen in witnesses)[path], source_files=False)
    OUT.mkdir(parents=True, exist_ok=True); EVIDENCE.mkdir(parents=True, exist_ok=True)
    for ident, raw in rendered.items():
        (OUT / (ident + '.png')).write_bytes(raw)
    for record, screen in witnesses:
        (ROOT / record['screenshot']).write_bytes(screen)
    (OUT / 'index.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def validate(data, read_image, read_witness, source_files=True):
    require(data['schema'] == 'tk2-original-battlefields-v1' and data['grid'] == GRID, 'Battlefield schema/grid mismatch')
    require(data['rom_sha256'] == ROM_SHA, 'Wrong source ROM identity')
    require(data['build']['tool_sha256'] == sha(Path(__file__).read_bytes()), 'Extractor changed; rebuild original maps and evidence')
    decoder, maps = data['decoder'], data['maps']
    require(list(maps) == [f'original-{i:02d}' for i in range(30)], 'Exactly30 ordered original maps required')
    for name, (offset, length) in TABLES.items():
        require(decoder['tables'][name]['rom_file_offset'] == offset, 'Original source table address changed')
        unblob(decoder['tables'][name], length)
    require(decoder['tables']['tile_pointers']['hex'] == decoder['tables']['graphics_tile_pointers']['hex'], 'Native graphics and movement pointers differ')
    require(decoder['tables']['bank_selectors']['hex'] == decoder['tables']['graphics_bank_selectors']['hex'], 'Native graphics and movement banks differ')
    require(len(decoder['chunks']) == 120 and len(decoder['descriptors']) == 30, 'Native chunk/descriptor count mismatch')
    for i, desc in enumerate(decoder['descriptors']):
        require(desc['original_city_index'] == i and desc['pointer_cpu'] == word(unblob(decoder['tables']['city_descriptor_pointers']), i * 2), 'Descriptor pointer mismatch')
        require(desc['rom_file_offset'] == 0x30010 + desc['pointer_cpu'] - 0xC000, 'Descriptor file address mismatch')
        require(desc['chunk_ids'] == [4 * i, 4 * i + 2, 4 * i + 1, 4 * i + 3] and sha(bytes(desc['chunk_ids'])) == desc['sha256'], 'Original chunk order mismatch')
    for i, chunk in enumerate(decoder['chunks']):
        require(chunk['id'] == i, 'Chunk order mismatch')
        pointer = word(unblob(decoder['tables']['tile_pointers']), 2 * i)
        attr = word(unblob(decoder['tables']['attribute_pointers']), 2 * i)
        bank = (unblob(decoder['tables']['bank_selectors'])[i] & 63) % 32
        require((chunk['bank_8k'], chunk['tile_pointer_cpu'], chunk['attribute_pointer_cpu']) == (bank, pointer, attr) and attr == pointer - 64, 'Chunk source pointer mismatch')
        for key, size, ptr in (('tiles', 240, pointer), ('attributes', 64, attr)):
            unblob(chunk[key], size)
            require(chunk[key]['rom_file_offset'] == 16 + bank * 8192 + ptr - 0x8000, 'Chunk source file mismatch')
    require([row['page_1k'] for row in decoder['chr_pages']] == list(CHR_PAGES), 'Native animation frame changed')
    for row in decoder['chr_pages']:
        unblob(row, 1024)
        require(row['rom_file_offset'] == 0x40010 + row['page_1k'] * 1024, 'Native CHR source mismatch')
    require(decoder['bg_palette'] == list(BG_PALETTE) and decoder['nes_to_rgba'] == {str(k): list(v) for k, v in sorted(COLORS.items())}, 'Unverified native palette')
    classifier, services = unblob(decoder['tables']['classifier']), unblob(decoder['tables']['service_coordinates'])
    grids, rendered_hashes, required_colors = set(), set(), set()
    for city, (ident, row) in enumerate(maps.items()):
        require((row['id'], row['original_city_index'], row['width'], row['height'], row['path']) ==
                (ident, city, 496, 304, f'/assets/battlefields/{ident}.png'), 'Map identity/path mismatch')
        for key in ('tiles', 'palettes', 'raw_classes', 'classes'):
            require(len(row[key]) == 19 and all(len(line) == 31 for line in row[key]), 'Map grid shape mismatch')
        for y in range(19):
            for x in range(31):
                tile, palette = cell_source(decoder, city, x, y)
                require((row['tiles'][y][x], row['palettes'][y][x]) == (tile, palette), 'Map differs from native source chunk')
                raw_class = classifier[tile]
                require(row['raw_classes'][y][x] == raw_class and row['classes'][y][x] == (raw_class if raw_class < 6 else 2), 'Native marker normalization mismatch')
        positions = lambda fn: [dict(x=x, y=y, packed_y=y if y < 15 else y + 1, raw_tile=row['tiles'][y][x], raw_class=value)
                               for y, line in enumerate(row['raw_classes']) for x, value in enumerate(line) if fn(value)]
        require(row['camps'] == positions(lambda c: c == 5) and len(row['camps']) == 1, 'Native camp coordinates mismatch')
        require(row['markers'] == positions(lambda c: c >= 6), 'Native marker coordinates mismatch')
        require(len(row['services']) == 3, 'Native service count mismatch')
        for category, service in enumerate(row['services']):
            x, packed_y = services[city * 6 + category * 2:city * 6 + category * 2 + 2]
            present = (x, packed_y) != (255, 255)
            require(service['original_xy'] == [x, packed_y] and service['category'] == category and service['present'] == present, 'Native service source mismatch')
            require(service['position'] == (dict(x=x, y=packed_y if packed_y < 15 else packed_y - 1) if present else None), 'Native service packed coordinate mismatch')
        pixels, used = render(decoder, row['tiles'], row['palettes']); required_colors.update(used)
        encoded = read_image(row['path'])
        require(sha(encoded) == row['sha256'] and sha(pixels) == row['rgba_sha256'], 'Native map image hash mismatch')
        require(png_pixels(encoded, (496, 304)) == pixels, 'Native map PNG pixels differ from decoded source')
        grid_hash = sha(bytes(tile for line in row['tiles'] for tile in line))
        require(grid_hash == row['tile_grid_sha256'], 'Native map tile hash mismatch')
        grids.add(grid_hash); rendered_hashes.add(row['rgba_sha256'])
    require(len(grids) == len(rendered_hashes) == 30, 'Original30 layouts must remain distinct')
    verified, witnessed_colors = 0, set()
    witnesses = data['native_verification']['witnesses']
    require([w['original_city_index'] for w in witnesses] == [5, 6, 9], 'Required native city5/6/9 witnesses missing')
    for witness in witnesses:
        for key, size in (('nametable', 2048), ('palette', 32), ('oam', 256)):
            unblob(witness['ppu'][key], size)
        require(witness['engine']['core_sha256'] == CORE_SHA and witness['palette_name'] == 'royaltea' and not witness['natural_gameplay'], 'Native witness provenance changed')
        result = verify_witness(decoder, maps, witness, read_witness(witness['screenshot']))
        require(result == witness['verification'], 'Native pixel verification totals changed')
        verified += result['checked_pixels']
        witnessed_colors.update(int(code) for code in result['observed_nes_color_pixels'])
    require(verified == data['native_verification']['checked_pixels'] == 120832, 'Native pixel evidence coverage decreased')
    require(required_colors <= witnessed_colors, 'A rendered color has no exact native pixel witness')
    if source_files:
        label_source = data['source_labels']['reference']
        require(label_source == LABEL_REFERENCE and sha((ROOT / label_source).read_bytes()) == data['source_labels']['sha256'], 'Guide city label evidence changed')
    return dict(maps=len(maps), unique_layouts=len(grids), grid=[31, 19], native_pixels_verified=verified,
                observed_nes_colors=len(witnessed_colors), checker_requires_rom=False)


def check():
    data = json.loads((OUT / 'index.json').read_text(encoding='utf-8'))
    def read_image(path):
        require(re.fullmatch(r'/assets/battlefields/original-[0-2][0-9]\.png', path) is not None, 'Invalid battlefield asset path')
        source = ROOT / 'game' / path.lstrip('/')
        require(source.is_file() and not source.is_symlink(), 'Missing/linked battlefield asset')
        return source.read_bytes()
    def read_witness(path):
        require(path in {f'tools/battlefields/evidence/city{i:02d}.png' for i in WITNESSES}, 'Invalid native witness path')
        source = ROOT / path
        require(source.is_file() and not source.is_symlink(), 'Missing/linked native witness')
        return source.read_bytes()
    return validate(data, read_image, read_witness)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, help='Pinned user-provided ROM; extraction only')
    parser.add_argument('--evidence-root', type=Path, help='Read-only native research archive; extraction only')
    parser.add_argument('--check', action='store_true', help='Verify repository assets without ROM/archive/emulator')
    args = parser.parse_args()
    if not args.check:
        if args.rom is None or args.evidence_root is None:
            parser.error('Extraction requires --rom and --evidence-root; use --check for offline verification')
        build(args.rom.resolve(), args.evidence_root.resolve())
    print(json.dumps(check(), ensure_ascii=False, sort_keys=True))
