#!/usr/bin/env python3
"""Reproduce capture-derived runtime PNGs without claiming native PPU exports.

Run from any directory. Pillow is required. --check verifies every output without
writing. Full source screenshots and emulator states never enter game/assets/.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys

from PIL import Image, ImageChops, ImageDraw

STUDY = Path(__file__).resolve().parent
ROOT = STUDY.parents[2]
OUTPUT = ROOT / 'game/assets/original-ui'
WINDOW_PIXEL_STEP = 6
DISPLAY_SCALE = 4
PROVENANCE = 'original-capture-derived'


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', compress_level=9)
    return buffer.getvalue()


def local_source(name: str) -> Path:
    path = (STUDY / name).resolve()
    path.relative_to(STUDY)
    return path


def reference(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def export_plan() -> dict[Path, bytes]:
    candidates_path = STUDY / 'asset-candidates.json'
    candidate_bytes = candidates_path.read_bytes()
    candidates = json.loads(candidate_bytes)['candidates']
    if len(candidates) != 14 or len({row['id'] for row in candidates}) != 14:
        raise ValueError('Expected the accepted fourteen distinct candidates')
    outputs: dict[Path, bytes] = {}
    assets, files, display_images = [], [], []
    for row in candidates:
        ident = row['id']
        if not re.fullmatch(r'[a-z][a-z0-9-]{1,79}', ident):
            raise ValueError(f'Invalid asset ID: {ident!r}')
        screenshot_path, crop_path = local_source(row['source_file']), local_source(row['preview_file'])
        screenshot_bytes, crop_bytes = screenshot_path.read_bytes(), crop_path.read_bytes()
        if sha256(screenshot_bytes) != row['source_sha256'] or sha256(crop_bytes) != row['preview_sha256']:
            raise ValueError(f'Accepted source hash changed: {ident}')
        screenshot, crop = Image.open(io.BytesIO(screenshot_bytes)).convert('RGBA'), Image.open(io.BytesIO(crop_bytes)).convert('RGBA')
        rect = row['rect_xyxy_window_pixels']
        if len(rect) != 4 or any(type(value) is not int for value in rect) or not (0 <= rect[0] < rect[2] <= screenshot.width and 0 <= rect[1] < rect[3] <= screenshot.height):
            raise ValueError(f'Invalid source rectangle: {ident}')
        expected_crop = screenshot.crop(rect)
        if crop.size != expected_crop.size or ImageChops.difference(crop.convert('RGB'), expected_crop.convert('RGB')).getbbox():
            raise ValueError(f'Accepted reference does not match its full source crop: {ident}')
        # The measured screenshot grid is approximately 6 window pixels per
        # displayed game pixel. This sampling base is not a recovered PPU size.
        base_dimensions = tuple(max(1, round(value / WINDOW_PIXEL_STEP)) for value in crop.size)
        base = crop.convert('RGB').resize(base_dimensions, Image.Resampling.NEAREST)
        display = base.resize(tuple(value * DISPLAY_SCALE for value in base.size), Image.Resampling.NEAREST)
        variants = [
            ('source_crop', f'source/{ident}.png', crop_bytes, crop.size),
            ('pixel_base', f'pixel-base/{ident}.png', png(base), base.size),
            ('display_4x', f'{ident}-4x.png', png(display), display.size),
        ]
        asset = dict(id=ident, title=row['title'], provenance=PROVENANCE,
                     native_dimensions_confirmed=False,
                     source_capture=row['source_capture'], source_file=reference(screenshot_path),
                     source_sha256=sha256(screenshot_bytes), source_dimensions=list(screenshot.size),
                     rect_xyxy_window_pixels=rect,
                     reference_crop_file=reference(crop_path), reference_crop_sha256=sha256(crop_bytes),
                     processing=dict(window_pixel_step=WINDOW_PIXEL_STEP,
                                     pixel_base_dimensions_rule='round(crop dimension / 6)',
                                     sampling='Pillow NEAREST, center-of-output-pixel sampling',
                                     pixel_base_is_approximation=True,
                                     palette_quantization='none; sampled capture colors preserved',
                                     source_filtering_preserved=True,
                                     display_scale=DISPLAY_SCALE,
                                     display_resampling='Pillow NEAREST'))
        for kind, relative, raw, dimensions in variants:
            target = OUTPUT / relative
            outputs[target] = raw
            entry = dict(path='/assets/original-ui/' + relative, sha256=sha256(raw),
                         bytes=len(raw), width=dimensions[0], height=dimensions[1])
            asset[kind] = entry
            files.append(dict(entry, id=ident, variant=kind, provenance=PROVENANCE))
        asset.update(path=asset['display_4x']['path'], sha256=asset['display_4x']['sha256'],
                     width=display.width, height=display.height)
        assets.append(asset)
        display_images.append((ident, display))
    manifest = dict(schema='tk2-original-ui-v1', provenance=PROVENANCE,
                    native_dimensions_confirmed=False,
                    note='Extracted from accepted OpenEmu window screenshots. Pixel-base sizes approximate the measured 6x display grid; they are not direct PPU or native exports. No AI redraw or palette quantization.',
                    candidate_manifest=reference(candidates_path), candidate_manifest_sha256=sha256(candidate_bytes),
                    generator=reference(Path(__file__).resolve()), generator_sha256=sha256(Path(__file__).read_bytes()),
                    assets=assets, files=files)
    outputs[OUTPUT / 'index.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    for name, entries, columns, cell_width, cell_height in [
        ('icons', display_images[:10], 5, 210, 190),
        ('scenes', display_images[10:], 2, 540, 490),
    ]:
        sheet = Image.new('RGB', (columns * cell_width, ((len(entries) + columns - 1) // columns) * cell_height), '#ffd4c8')
        draw = ImageDraw.Draw(sheet)
        for index, (ident, image) in enumerate(entries):
            x = (index % columns) * cell_width + (cell_width - image.width) // 2
            y = (index // columns) * cell_height + 30
            sheet.paste(image, (x, y))
            draw.text(((index % columns) * cell_width + 6, (index // columns) * cell_height + 6), ident, fill='black')
        outputs[STUDY / f'runtime-assets-{name}.png'] = png(sheet)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify deterministic outputs without writing')
    args = parser.parse_args()
    outputs = export_plan()
    differences = []
    for path, raw in outputs.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != raw:
                differences.append(reference(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    if differences:
        print('Capture-derived asset differences:\n' + '\n'.join(differences), file=sys.stderr)
        return 1
    print(f'{"Verified" if args.check else "Exported"} 14 capture-derived assets, 42 PNG variants and index.json; native_dimensions_confirmed=false')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
