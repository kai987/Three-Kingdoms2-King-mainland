#!/usr/bin/env python3
"""Rebuild site icons from the approved8x8 native castle mask, using stdlib only.

Native palette indices2(outline) and6(fill) form the silhouette. Terrain pixels
are omitted. Each source pixel remains an integer rectangle; no resampling or
antialiasing changes the original outline. Source art is never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'game/config/map-source.json'
GOLD = (248, 216, 120, 255)
BLACK = (0, 0, 0, 255)
ICO_SIZES = (16, 32, 48, 64)


def castle_source(root):
    data = json.loads((root / SOURCE).read_text(encoding='utf-8'))
    sprite = data['native_castle_sprite']
    rows = sprite['rows']
    if (sprite.get('width'), sprite.get('height')) != (8, 8) or len(rows) != 8:
        raise ValueError('Expected the approved8x8 native castle')
    if any(len(row) != 8 or any(type(value) is not int for value in row) for row in rows):
        raise ValueError('Invalid native castle rows')
    points = [(x, y) for y, row in enumerate(rows) for x, value in enumerate(row)
              if value in (2, 6)]
    if not points:
        raise ValueError('The native castle silhouette is empty')
    left, top = min(x for x, y in points), min(y for x, y in points)
    width = max(x for x, y in points) - left + 1
    height = max(y for x, y in points) - top + 1
    mask = {(x - left, y - top) for x, y in points}
    digest = hashlib.sha256(json.dumps(sprite, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return mask, width, height, digest


def pixels(mask, width, height, size):
    scale = size // 8
    if scale < 1:
        raise ValueError('Site icon size must be at least8')
    left, top = (size - width * scale) // 2, (size - height * scale) // 2
    return bytes(channel for y in range(size) for x in range(size)
                 for channel in (GOLD if (x - left) // scale >= 0 and (y - top) // scale >= 0
                                 and ((x - left) // scale, (y - top) // scale) in mask else BLACK))


def png(size, rgba):
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value) & 0xffffffff)

    stride = size * 4
    rows = b''.join(b'\0' + rgba[y * stride:(y + 1) * stride] for y in range(size))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def ico(images):
    """Classic32-bit BGRA DIB frames plus opaque AND masks for broad ICO support."""
    entries, frames = [], []
    offset = 6 + 16 * len(images)
    for size, rgba in images:
        bitmap = bytearray()
        for y in reversed(range(size)):
            for x in range(size):
                r, g, b, a = rgba[(y * size + x) * 4:(y * size + x + 1) * 4]
                bitmap.extend((b, g, r, a))
        mask = bytes(((size + 31) // 32) * 4 * size)
        frame = (struct.pack('<IiiHHIIiiII', 40, size, size * 2, 1, 32, 0,
                             len(bitmap), 0, 0, 0, 0) + bitmap + mask)
        entries.append(struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32, len(frame), offset))
        frames.append(frame)
        offset += len(frame)
    return struct.pack('<HHH', 0, 1, len(images)) + b''.join(entries) + b''.join(frames)


def outputs(root=ROOT):
    mask, width, height, digest = castle_source(Path(root))
    left, top = (8 - width) // 2, (8 - height) // 2
    rectangles = ''.join(f'<rect x="{x + left}" y="{y + top}" width="1" height="1"/>'
                         for x, y in sorted(mask, key=lambda point: (point[1], point[0])))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">'
           '<title>三國・大陸戰役</title>'
           f'<metadata>Native castle: {SOURCE}#native_castle_sprite; sha256={digest}</metadata>'
           '<rect width="8" height="8" fill="#000000"/>'
           f'<g fill="#f8d878">{rectangles}</g></svg>\n').encode('utf-8')
    return {
        'game/favicon.ico': ico([(size, pixels(mask, width, height, size)) for size in ICO_SIZES]),
        'game/favicon.svg': svg,
        'game/assets/site-icon-32.png': png(32, pixels(mask, width, height, 32)),
        'game/assets/site-icon-180.png': png(180, pixels(mask, width, height, 180)),
    }


def build(check=False, root=ROOT):
    root = Path(root)
    artifacts = outputs(root)
    for name, raw in artifacts.items():
        target = root / name
        if target.is_symlink():
            raise ValueError('Site icon output may not be a symlink: ' + name)
        if check:
            if not target.is_file() or target.read_bytes() != raw:
                raise ValueError('Site icon is stale: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    return {name: dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            for name, raw in artifacts.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(dict(check=args.check, ico_sizes=ICO_SIZES, files=build(args.check)), ensure_ascii=False))
