#!/usr/bin/env python3
"""Decode pinned ROM portrait data to static, native-size RGBA PNGs.

This is an offline asset decoder, not an emulator or game runtime dependency.
It retains frame 0, ordinary mouth, exact 2bpp pixels/OAM priority, and the
32x40 descriptor extent. Transparent color 0 is displayed on black in-game.
The RGB conversion explicitly matches the previously recorded Nestopia
royaltea palette, rather than claiming that NES color indices are fixed RGB.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
WIDTH, HEIGHT, COUNT = 32, 40, 237
PALETTE_OFFSET = 0x3DBFB
PALETTE_MODE0 = bytes.fromhex('0f 12 1a 2a 0f 27 16 2a 0f 36 30 16 0f 36 30 16 0f 0f 20 16 0f 0f 2b 28 0f 36 30 16 0f 20 27 17')
RGBA = ((0, 0, 0, 0), (255, 255, 255, 255), (247, 162, 71, 255), (158, 65, 0, 255))
WITNESS = ROOT / 'art/portraits/reference/officer-info-native-witness.png'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png(rgba):
    """Write deterministic, dependency-free 8-bit RGBA PNG (no resampling)."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    rows = b''.join(b'\0' + rgba[y * WIDTH * 4:(y + 1) * WIDTH * 4] for y in range(HEIGHT))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', WIDTH, HEIGHT, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def decode(rom):
    if sha(rom) != ROM_SHA256:
        raise ValueError('Portrait extraction requires the pinned original ROM; no files written')
    if rom[PALETTE_OFFSET:PALETTE_OFFSET + 32] != PALETTE_MODE0:
        raise ValueError('Pinned mode-0 palette bytes changed')
    def byte(address):
        return rom[0x2010 + address - 0x8000]
    def word(address):
        return byte(address) | byte(address + 1) << 8
    def sprites(pointer):
        result = []
        for i in range(64):
            address = pointer + 4 * i
            if byte(address) == 0x80:
                return result
            result.append(tuple(byte(address + j) for j in range(4)))
        raise ValueError('Unterminated sprite descriptor')
    def tile(page, index):
        offset = 0x40010 + 1024 * page + 16 * (index & 63)
        raw = rom[offset:offset + 16]
        return [[((raw[y] >> (7 - x)) & 1) | (((raw[y + 8] >> (7 - x)) & 1) << 1)
                 for x in range(8)] for y in range(8)]
    result = []
    for original_id in range(COUNT):
        page = rom[0x34EE6 + original_id]
        base = byte(0x99A0 + original_id)
        body = word(0x9AA0 + 2 * base)
        mouth = word(0x9BAC + 2 * base)
        pixels = {}
        records = sprites(body) + sprites(mouth)
        if len(records) != 20:
            raise ValueError('Expected fourteen body and six ordinary-mouth sprites')
        for dy, index, attributes, dx in records:
            if attributes & 3 != 3:
                raise ValueError('Portrait is not using the proven sprite palette 3')
            if not (0 <= dx <= WIDTH - 8 and 0 <= dy <= HEIGHT - 8):
                raise ValueError('Descriptor exceeds the native portrait extent')
            grid = tile(page, index)
            for y in range(8):
                for x in range(8):
                    value = grid[7 - y if attributes & 0x80 else y][7 - x if attributes & 0x40 else x]
                    if value:
                        # Lower OAM index wins for opaque sprite pixels.
                        pixels.setdefault((dx + x, dy + y), value)
        rgba = bytes(channel for y in range(HEIGHT) for x in range(WIDTH)
                     for channel in RGBA[pixels.get((x, y), 0)])
        image = png(rgba)
        result.append(dict(original_id=original_id, path=f'/assets/portraits/original/{original_id:03d}.png',
                           width=WIDTH, height=HEIGHT, chr_page=page, chr_rom_offset=0x40010 + 1024 * page,
                           chr_sha256=sha(rom[0x40010 + 1024 * page:0x40010 + 1024 * (page + 1)]),
                           frame=0, base_frame_index=base, body_pointer=body, ordinary_mouth_pointer=mouth,
                           sprite_records=len(records), opaque_pixels=len(pixels), rgba_sha256=sha(rgba),
                           png_sha256=sha(image), png_bytes=len(image), _rgba=rgba, _png=image))
    return result


def build(rom_path, check=False):
    rom = Path(rom_path).read_bytes()
    rows = decode(rom)
    out = ROOT / 'game/assets/portraits/original'
    if not check:
        out.mkdir(parents=True, exist_ok=True)
    witnesses = dict(path='art/portraits/reference/officer-info-native-witness.png',
                     sha256='d31153e8770601acd65bc5367b67f679300e86c570cde6564d23bf1e4ec7571e',
                     original_id=131, crop=[16, 175, 48, 215], opaque_pixels_compared=734,
                     opaque_pixel_mismatches=0, transparent_pixels_compare_on_black=546,
                     pixel_profile='Nestopia 2.0.0 135dfa6 / royaltea / NTSC / filter disabled')
    # This optional check consumes an existing reference, never makes a mock frame.
    if WITNESS.exists():
        from PIL import Image
        if sha(WITNESS.read_bytes()) != witnesses['sha256']:
            raise ValueError('Pinned native screenshot witness changed')
        reference = Image.open(WITNESS).convert('RGB').crop(tuple(witnesses['crop']))
        sample = rows[131]['_rgba']
        actual = bytes(sample[i + j] if sample[i + 3] else 0
                       for i in range(0, len(sample), 4) for j in range(3))
        if reference.tobytes() != actual:
            raise ValueError('Native screenshot does not match decoded portrait pixels')
        witnesses['sha256'] = sha(WITNESS.read_bytes())
    for row in rows:
        path = out / f'{row["original_id"]:03d}.png'
        if check:
            if path.read_bytes() != row['_png']:
                raise ValueError('Original portrait changed: ' + str(path))
        else:
            path.write_bytes(row['_png'])
    pixels = Counter(row['rgba_sha256'] for row in rows)
    manifest = dict(schema='tk2-original-portraits-v1', source='pinned_user_ROM_CHR_and_OAM_descriptors',
                    rom_sha256=ROM_SHA256, original_id_count=COUNT, unique_pixel_images=len(pixels),
                    native_size=[WIDTH, HEIGHT], display_background='#000000', alpha_zero='NES sprite color 0',
                    resampling='none; native 2bpp pixels', source_frame='frame0 ordinary mouth',
                    palette=dict(mode=0, routine='physical29 A015 -> physical30 DBB1; mode0 pointer DBEB',
                                 rom_offset=PALETTE_OFFSET, mode0_bytes=list(PALETTE_MODE0),
                                 sprite_palette_index=3, nes_color_indices=list(PALETTE_MODE0[28:32]),
                                 rgba=[list(r) for r in RGBA], rgb_basis='recorded original-core royaltea conversion',
                                 native_witness=witnesses),
                    identity_note='Original numeric IDs only; stable remake person binding is a separate reviewed identity mapping.',
                    by_original_id={str(row['original_id']): {k:v for k,v in row.items() if not k.startswith('_')} for row in rows})
    target = ROOT / 'game/config/portrait-originals.json'
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    if check:
        if target.read_text() != text:
            raise ValueError('Original portrait manifest changed')
    else:
        target.write_text(text)
    return rows, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--contact-sheet', type=Path, help='Optional preview only (requires Pillow)')
    args = parser.parse_args()
    rows, manifest = build(args.rom, args.check)
    if args.contact_sheet:
        from PIL import Image, ImageDraw
        scale, columns, width, height = 4, 16, 40, 52
        sheet = Image.new('RGB', (columns * width, ((COUNT + columns - 1) // columns) * height), '#16110c')
        draw = ImageDraw.Draw(sheet)
        for row in rows:
            x, y = (row['original_id'] % columns) * width + 4, (row['original_id'] // columns) * height
            portrait = Image.frombytes('RGBA', (WIDTH, HEIGHT), row['_rgba'])
            sheet.paste(portrait, (x, y), portrait)
            draw.text((x + 6, y + HEIGHT), f'{row["original_id"]:03d}', fill='#ffd5cb')
        args.contact_sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(args.contact_sheet)
    print(json.dumps(dict(original_ids=COUNT, unique_pixel_images=manifest['unique_pixel_images'],
                          native_size=manifest['native_size'], checked=args.check,
                          assets='game/assets/portraits/original/', manifest='game/config/portrait-originals.json')))


if __name__ == '__main__':
    main()
