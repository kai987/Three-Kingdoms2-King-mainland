#!/usr/bin/env python3
"""Generate compact portraits from the currently indexed white PNGs.

Generation uses the pinned Pillow in tools/portraits/requirements.txt.
The release check uses only the standard library and verifies the exact assets.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
SIZE = (128, 160)
WHITE_SIZE = (512, 640)
SCHEMA = 'tk2-portrait-thumbnails-v1'
MANIFEST = Path('config/portrait-thumbnails.json')
THUMB_DIR = Path('assets/portraits/thumb')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def regular_file(here, relative):
    path = here
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f'Symlinked portrait asset: {relative}')
    return path


def sources(here):
    index = json.loads(regular_file(here, Path('assets/portraits/index.json')).read_bytes())
    if (not isinstance(index, dict) or index.get('schema') != 'tk2-portraits-v1'
            or not isinstance(index.get('people'), dict)):
        raise ValueError('Invalid portrait source index')
    for person_id, row in sorted(index['people'].items()):
        if not isinstance(row, dict):
            raise ValueError(f'Invalid portrait source: {person_id}')
        white = row.get('white')
        if white is None:
            continue
        path = Path(f'assets/portraits/white/{person_id}.png')
        if (re.fullmatch(r'[a-z0-9-]{1,128}', person_id) is None
                or white != {'path': f'/{path.as_posix()}', 'width': WHITE_SIZE[0], 'height': WHITE_SIZE[1]}):
            raise ValueError(f'Invalid white portrait binding: {person_id}')
        yield person_id, regular_file(here, path), regular_file(here, THUMB_DIR / f'{person_id}.webp')


def render(raw):
    from PIL import Image

    with Image.open(BytesIO(raw), formats=['PNG']) as source:
        if source.size != WHITE_SIZE:
            raise ValueError('Invalid white portrait dimensions')
        image = source.convert('RGBA').resize(SIZE, Image.Resampling.BOX)
    # Keep every pixel of the resized image. No subtractive palette or lossy
    # color conversion is needed to save bandwidth compared with the detail art.
    result = BytesIO()
    image.save(result, format='WEBP', lossless=True, method=4)
    return result.getvalue()


def valid_thumbnail(raw):
    # Lossless WebP puts VP8L immediately after the RIFF container header.
    if (len(raw) < 26 or raw[:4] != b'RIFF' or raw[8:16] != b'WEBPVP8L'
            or int.from_bytes(raw[4:8], 'little') + 8 != len(raw) or raw[20] != 0x2f):
        return False
    header = int.from_bytes(raw[21:25], 'little')
    return ((header & 0x3fff) + 1, ((header >> 14) & 0x3fff) + 1) == SIZE and header >> 29 == 0


def build(here=HERE, *, check=False):
    manifest = regular_file(here, MANIFEST)
    people = {}
    source_bytes = thumbnail_bytes = 0
    for person_id, source, target in sources(here):
        raw = source.read_bytes()
        if check:
            thumbnail = target.read_bytes()
        else:
            thumbnail = render(raw)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(thumbnail)
        if not valid_thumbnail(thumbnail) or len(thumbnail) >= len(raw):
            raise ValueError(f'Invalid compact portrait: {person_id}')
        people[person_id] = {'source_sha256': digest(raw), 'thumbnail_sha256': digest(thumbnail)}
        source_bytes += len(raw)
        thumbnail_bytes += len(thumbnail)
    if not people:
        raise ValueError('No white portraits to reduce')
    expected = {'schema': SCHEMA, 'width': SIZE[0], 'height': SIZE[1], 'people': people}
    if check:
        inventory = (here / THUMB_DIR).glob('*.webp')
        if (json.loads(manifest.read_bytes()) != expected
                or {path.name for path in inventory} != {f'{person_id}.webp' for person_id in people}):
            raise ValueError('Portrait thumbnail manifest or inventory is stale')
    else:
        manifest.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return {'portraits': len(people), 'source_bytes': source_bytes, 'thumbnail_bytes': thumbnail_bytes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(build(check=args.check), ensure_ascii=False))
    except (OSError, ValueError) as error:
        raise SystemExit(f'{error}. Rebuild with python3 game/build_portrait_thumbnails.py.') from error


if __name__ == '__main__':
    main()
