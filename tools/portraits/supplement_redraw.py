"""Bake retained imagegen edits directly to 128x160, never through 32x40.

This module only fits and quantizes authored pixels. It does not draw faces or
invent shading. The native assets and the old fourfold files remain archived.
"""
from hashlib import sha256
import json
from pathlib import Path
import struct
import zlib

from PIL import Image, ImageOps

PLAN = 'art/portraits/supplement-hd-v2/plan.json'
PALETTE = (
    (0, 0, 0, 0), (0, 0, 0, 255),
    (108, 46, 7, 255), (142, 56, 0, 255), (158, 65, 0, 255),
    (185, 85, 10, 255), (198, 99, 18, 255), (223, 121, 34, 255),
    (247, 162, 71, 255), (255, 187, 89, 255), (255, 218, 128, 255),
    (255, 214, 162, 255), (255, 235, 204, 255),
    (188, 189, 185, 255), (226, 226, 222, 255), (255, 255, 255, 255),
)


def digest(raw):
    return sha256(raw).hexdigest()


def retained(root, path, expected):
    if not isinstance(path, str) or Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('Invalid retained redraw source path')
    file = root / path
    if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()) or not file.is_file():
        raise ValueError('Missing retained redraw source: ' + path)
    raw = file.read_bytes()
    if digest(raw) != expected:
        raise ValueError('Retained redraw source hash differs: ' + path)
    return raw


def png(pixels):
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data)&0xffffffff)
    stride = 128*4
    rows = b''.join(b'\0'+pixels[y*stride:(y+1)*stride] for y in range(160))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB',128,160,8,6,0,0,0))
            +chunk(b'IDAT', zlib.compress(rows,9))+chunk(b'IEND',b''))


def bake(root, person_id, native_path, native_png, previous_png):
    root = Path(root)
    plan_raw = (root/PLAN).read_bytes()
    plan = json.loads(plan_raw)
    if plan.get('schema') != 'tk2-portrait-redraw-v2' or plan.get('size') != [128,160]:
        raise ValueError('Unknown 128x160 redraw plan')
    person = plan['people'][person_id]
    if person['native']['path'] != 'game'+native_path or person['native']['sha256'] != digest(native_png):
        raise ValueError('Redrawn portrait native identity differs')
    retained(root,person['native']['path'],person['native']['sha256'])
    old = person['original_enhanced']
    if retained(root,old['path'],old['sha256']) != previous_png:
        raise ValueError('Redrawn portrait lost its previous nearest4x file')
    source_raw = retained(root,person['generated_source'],person['generated_source_sha256'])
    retained(root,person['prompt'],person['prompt_sha256'])
    source = Image.open(root/person['generated_source']).convert('RGBA')
    if min(source.size) < 128 or max(source.size) > 4096:
        raise ValueError('Redraw must contain authored high resolution pixels')
    native = Image.open(root/person['native']['path']).convert('RGBA')
    if native.size != (32,40) or digest(native.tobytes()) != person['native']['rgba_sha256']:
        raise ValueError('Native portrait geometry or pixels changed')
    old_image = Image.open(root/old['path']).convert('RGBA')
    if old_image.size != (128,160) or digest(old_image.tobytes()) != old['rgba_sha256']:
        raise ValueError('Archived nearest4x portrait changed')
    source_alpha = source.getchannel('A').point(lambda value: 255 if value >= 128 else 0)
    source_box = source_alpha.getbbox()
    native_box = native.getchannel('A').getbbox()
    if source_box is None or native_box is None:
        raise ValueError('Empty redrawn portrait')
    # Preserve the original bust's envelope while recovering finer source pixels.
    left,top,right,bottom = [n*4 for n in native_box]
    content = ImageOps.contain(source.crop(source_box),(right-left,bottom-top),Image.Resampling.NEAREST)
    fitted = Image.new('RGBA',(128,160),(0,0,0,0))
    fitted.paste(content,(left+(right-left-content.width)//2,bottom-content.height))
    cache = {}
    pixels = bytearray()
    for color in fitted.getdata():
        if color not in cache:
            red,green,blue,alpha = color
            if alpha < 128:
                cache[color] = PALETTE[0]
            elif max(red,green,blue) <= 32:
                cache[color] = PALETTE[1]
            else:
                cache[color] = min(PALETTE[1:], key=lambda c: sum((c[k]-color[k])**2 for k in range(3)))
        pixels.extend(cache[color])
    pixels = bytes(pixels)
    baseline = native.resize((128,160),Image.Resampling.NEAREST).tobytes()
    changes = sum(pixels[i:i+4] != baseline[i:i+4] for i in range(0,len(pixels),4))
    colors = len({pixels[i:i+4] for i in range(0,len(pixels),4)})
    blocks = sum(len({pixels[((y+dy)*128+x+dx)*4:((y+dy)*128+x+dx)*4+4]
                         for dy in range(4) for dx in range(4)}) > 1
                 for y in range(0,160,4) for x in range(0,128,4))
    if changes < 1024 or not 5 <= colors <= 16 or blocks < 20:
        raise ValueError('Redraw adds insufficient high resolution detail')
    encoded = png(pixels)
    provenance = dict(
        base_method='identity_preserving_redrawn128',redraw_plan=PLAN,redraw_plan_sha256=digest(plan_raw),
        generated_source=person['generated_source'],generated_source_sha256=digest(source_raw),
        prompt=person['prompt'],prompt_sha256=person['prompt_sha256'],
        original_enhanced=old['path'],original_enhanced_sha256=old['sha256'],
        qa=dict(size=[128,160],paletteSize=colors,changedPixels=changes,nearest4xExact=False,
                source_size=list(source.size),nonUniformBlocks4x4=blocks))
    return encoded, dict(path=f'/assets/portraits/enhanced/{person_id}.png',width=128,height=160,
        source_path=native_path,source_sha256=digest(native_png),sha256=digest(encoded),
        pixel_sha256=digest(pixels),method='identity_preserving_pixel_enhancement',
        rendering='redrawn128',provenance=provenance)
