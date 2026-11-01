#!/usr/bin/env python3
"""Register generated gait frames; nearest-neighbour packing only, no repainting.

python3 art/loading-cover-v2/build.py
The unchanged generated source has a blank row between y=513 and y=526.
Both subjects use the same scale and anchor across their four gait frames.
"""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'game/assets/loading'
CELL, SCALE, INSET = 128, 4, 8


def main():
    source = Image.open(HERE / 'march-source.png').convert('RGBA')
    assert source.size == (1774, 887), 'Recheck crop registration for new artwork'
    for subject, top, bottom in [('rider', 0, 520), ('infantry', 520, 887)]:
        frames = [source.crop((i * source.width // 4, top,
                               (i + 1) * source.width // 4, bottom))
                  for i in range(4)]
        bounds = [frame.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
                  for frame in frames]
        assert all(bounds), 'Empty animation frame'
        box = (min(b[0] for b in bounds), min(b[1] for b in bounds),
               max(b[2] for b in bounds), max(b[3] for b in bounds))
        ratio = min((CELL - 2 * INSET) / (box[2] - box[0]),
                    (CELL - 2 * INSET) / (box[3] - box[1]))
        size = (round((box[2] - box[0]) * ratio), round((box[3] - box[1]) * ratio))
        atlas = Image.new('RGBA', (CELL * 4, CELL))
        for i, frame in enumerate(frames):
            sprite = frame.crop(box).resize(size, Image.Resampling.NEAREST)
            atlas.paste(sprite, (i * CELL + (CELL - size[0]) // 2,
                                CELL - INSET - size[1]))
        atlas.resize((CELL * 4 * SCALE, CELL * SCALE), Image.Resampling.NEAREST).save(
            OUT / f'march-{subject}-v2.png', optimize=True)
    (OUT / 'cover-map-v2.png').write_bytes((HERE / 'cover-map-source.png').read_bytes())


if __name__ == '__main__':
    main()
