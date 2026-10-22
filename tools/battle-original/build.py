#!/usr/bin/env python3
"""Export native NES battle pixels as offline Web assets.

Sources are explicit external Nestopia screenshots and companion states. No ROM,
emulator, save state or research archive is a runtime dependency. The exporter
never changes the source screenshots/states and makes no claim to emulate the
scanline CHR bank switches from a single serialized PPU image.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path
import struct
import zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'game/assets/battle-original'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA = '924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
MAP = 'analysis/runtime/phase3/battle-free-cursor'
ARMY = 'analysis/phase11/runtime/ordinary-attack-return/'
DUEL = 'analysis/phase11/runtime/duel-return/'
PAPER = (255,213,203)


def sha(value): return hashlib.sha256(value).hexdigest()


def chunks(data):
    offset, result = 0, {}
    while offset < len(data):
        if len(data)-offset < 8: raise ValueError('Truncated Nestopia chunk')
        tag = data[offset:offset+4]
        size = struct.unpack_from('<I',data,offset+4)[0]
        if offset+8+size > len(data) or tag in result: raise ValueError('Invalid Nestopia chunk')
        result[tag] = data[offset+8:offset+8+size]
        offset += 8+size
    return result


def unpack(value, size):
    if value[0] == 0: data = value[1:]
    elif value[0] == 1: data = zlib.decompress(value[1:])
    else: raise ValueError('Unknown Nestopia compression')
    if len(data) != size: raise ValueError('Invalid decoded PPU block')
    return data


def state_metadata(path):
    raw = path.read_bytes()
    if raw[:4] != b'NST\x1a': raise ValueError('Expected original Nestopia state')
    top = chunks(raw[8:8+struct.unpack_from('<I',raw,4)[0]])
    ppu = chunks(top[b'PPU\0'])
    mapper = chunks(chunks(top[b'IMG\0'])[b'MPR\0'])
    bank_bytes = chunks(mapper[b'CHR\0'])[b'BNK\0']
    banks = [dict(window=i//3,source=bank_bytes[i],page_1k=bank_bytes[i+1]|bank_bytes[i+2]<<8)
             for i in range(0,len(bank_bytes),3)]
    for item in banks:
        if item['source']==0: item['rom_offset'] = 0x40010+item['page_1k']*1024
    oam = unpack(ppu[b'OAM\0'],256)
    return dict(state_sha256=sha(raw),ppu_register_bytes=list(ppu[b'REG\0']),
                palette_indices=list(unpack(ppu[b'PAL\0'],32)),chr_banks=banks,
                oam_sha256=sha(oam),oam_records=[list(oam[i:i+4])for i in range(0,256,4)],
                nametable_sha256=sha(unpack(ppu[b'NMT\0'],2048)),
                raster_scope='Captured PPU state is provenance only. Original game changes CHR/palette during scanlines; these banks alone do not reproduce the complete visible frame.')


def source(root, stem):
    path = root/(stem+'.png')
    image = Image.open(path).convert('RGB')
    if image.size != (256,240): raise ValueError('Native screenshot must be exactly256x240')
    meta = dict(screenshot=stem+'.png',screenshot_sha256=sha(path.read_bytes()),
                resolution=[256,240],pixel_origin='Original Nestopia video callback, royaltea palette, no resampling')
    capture = root/(stem+'.json')
    if not capture.is_file(): raise ValueError('Missing original capture provenance')
    record=json.loads(capture.read_text())
    if record['rom_sha256'] != ROM_SHA or record['engine']['core_sha256'] != CORE_SHA:
        raise ValueError('Original capture ROM/core provenance mismatch')
    if record['core_options']['nestopia_palette'] != 'royaltea': raise ValueError('Original capture palette mismatch')
    meta.update(capture=stem+'.json',capture_sha256=sha(capture.read_bytes()),captured_frame=record['frames'],engine=record['engine'],pixel_format=record['pixel_format'])
    state = root/(stem+'.state')
    if state.exists(): meta.update(state=stem+'.state',ppu=state_metadata(state))
    return image,meta


def export(image, name, origin, rect=None, operations=None, anchor=None):
    target = OUT/(name+'.png');image.save(target,optimize=False,compress_level=9)
    result = dict(path='/assets/battle-original/'+target.name,width=image.width,height=image.height,
                  sha256=sha(target.read_bytes()),source=deepcopy(origin))
    if rect is not None: result['source']['source_rect']=list(rect)
    if operations: result['source']['operations']=operations
    if anchor: result['anchor']=anchor
    return result


def transparent(image, key):
    result = image.convert('RGBA')
    result.putdata([(*rgb[:3],0 if tuple(rgb[:3])==key else 255)for rgb in result.getdata()])
    return result


def difference(image, background):
    result = image.convert('RGBA')
    result.putdata([(*rgb[:3],0 if tuple(rgb[:3])==base[:3] else 255)
                    for rgb,base in zip(result.getdata(),background.convert('RGBA').getdata())])
    return result


def build(root, rom):
    if sha(rom.read_bytes()) != ROM_SHA: raise ValueError('Pinned user ROM does not match; no output written')
    OUT.mkdir(parents=True,exist_ok=True)
    tactical,tactical_source=source(root,MAP)
    clean_tactical=tactical.crop((0,0,256,160))
    # The native map reference has one fixed 16x16 officer flag. Replace only
    # that square with an exact native ordinary-ground square; no AI inpainting.
    clean_tactical.paste(tactical.crop((0,0,16,16)),(32,96))
    tactical_asset=export(clean_tactical,'tactical',tactical_source,(0,0,256,160),
        operations=[dict(kind='replace_fixed_officer_flag_with_native_ground',destination=[32,96,48,112],source_rect=[0,0,16,16])])
    ground,ground_source=source(root,ARMY+'attack-prelude-1')
    ground=ground.crop((0,0,256,160))
    plain=export(ground,'plain',ground_source,(0,0,256,160))
    # Both illustration choices intentionally retain the original mixed terrain
    # reference rather than pretending to recover a city-specific battle map.
    backgrounds=dict(tactical=tactical_asset,plain=plain,
        mountain=dict(deepcopy(tactical_asset),role='Original mixed mountain/river tactical illustration'),
        water=dict(deepcopy(tactical_asset),role='Original mixed mountain/river tactical illustration'))
    sprites={}
    for kind,rects in [('infantry',[(32,16,48,32),(16,80,32,96)]),
                       ('cavalry',[(208,32,224,48),(224,80,240,96)])]:
        frames=[];digests=set()
        for stem in ('first-attack-main-01','first-attack-main-02','first-attack-main-04'):
            army,meta=source(root,ARMY+stem)
            for rect in rects:
                frame=difference(army.crop(rect),ground.crop(rect))
                if not frame.getbbox(): continue
                key=sha(frame.tobytes())
                if key in digests: continue
                digests.add(key)
                frames.append(export(frame,f'{kind}-{len(frames):02d}',meta,rect,
                    operations=[dict(kind='pixel_exact_native_background_difference',background=ground_source['screenshot'],background_sha256=ground_source['screenshot_sha256'])],
                    anchor=dict(x=8,y=16)))
        sprites[kind]=dict(frames=frames,usage='Original ordinary-attack formation art; presentation only, not an added gameplay troop type')
    for kind,rect in [('duelist',(0,64,128,160)),('duelist_enemy',(128,64,256,160))]:
        frames=[];digests=set()
        for stem in ('first-duel-main-03','first-duel-main-09','first-duel-main-19'):
            if kind == 'duelist_enemy' and stem.endswith('-19'): continue  # Contact frame only retains the defeated horse tail on this side.
            actual_rect=(0,64,88,160) if kind == 'duelist' and stem.endswith('-19') else rect
            screen,meta=source(root,DUEL+stem);image=transparent(screen.crop(actual_rect),(0,0,0))
            bbox=image.getbbox()
            if not bbox: raise ValueError('Missing native horseman')
            frame=Image.new('RGBA',(96,96));shape=image.crop(bbox)
            frame.alpha_composite(shape,((96-shape.width)//2,96-shape.height))
            key=sha(frame.tobytes())
            if key in digests:continue
            digests.add(key)
            frames.append(export(frame,f'{kind}-{len(frames):02d}',meta,actual_rect,
                operations=[dict(kind='transparent_original_black_background',rgba_key=[0,0,0,255]),
                            dict(kind='place_unscaled_native_horseman_on_transparent_canvas',native_bbox=list(bbox),canvas=[96,96])],anchor=dict(x=48,y=96)))
        sprites[kind]=dict(frames=frames,facing='right' if kind=='duelist' else 'left',usage='Original horse and rider; native clothes, armor, pose and colors retained. Generic scene art, not a portrait identity binding.')
    sprites['infantry_enemy']=dict(deepcopy(sprites['cavalry']),facing='left',usage='Opposing original ordinary-attack soldier art; red palette, not a verified cavalry classification. The cavalry key is a compatibility alias for this art and adds no troop type.')
    sprites['cavalry']['usage']=sprites['infantry_enemy']['usage']
    sprites['infantry']['facing']='right'
    sprites['cavalry']['facing']='left'
    # Preserve the actual opposing formations, including the original mixture
    # of spear lines and individual soldiers. Repeating one16x16 cutout loses
    # the native ordinary-attack composition. These full-half transparent
    # layers retain each captured position, pose, palette and relative size;
    # only the Web presentation supplies approach/recoil timing.
    for kind,rect,facing in [('attack_formation',(0,0,128,160),'right'),
                             ('attack_formation_enemy',(128,0,256,160),'left')]:
        frames=[]
        for stem in ('first-attack-main-01','first-attack-main-04'):
            screen,meta=source(root,ARMY+stem)
            frame=difference(screen.crop(rect),ground.crop(rect))
            if not frame.getbbox(): raise ValueError('Missing native attack formation')
            frames.append(export(frame,f'{kind}-{len(frames):02d}',meta,rect,
                operations=[dict(kind='pixel_exact_native_background_difference',background=ground_source['screenshot'],background_sha256=ground_source['screenshot_sha256'])],
                anchor=dict(x=64,y=160)))
        sprites[kind]=dict(frames=frames,facing=facing,
            usage='Complete native ordinary-attack half-screen formation, not a tactical flag or a single repeated soldier. Native capture poses only; Web timing is presentation.')
    # Clean native tactical tiles can be rearranged by the presentation layer.
    terrain={}
    for key,rect in dict(ground=(0,0,16,16),forest=(32,48,64,80),mountain=(96,16,160,80),river=(64,32,96,64)).items():
        terrain[key]=export(tactical.crop(rect),'terrain-'+key,tactical_source,rect)
    witnesses={}
    for key,stem in [('tactical',MAP),('attack',ARMY+'first-attack-main-01'),('attack_advance',ARMY+'first-attack-main-04'),('duel',DUEL+'first-duel-main-03')]:
        image,meta=source(root,stem);witnesses[key]=export(image,'witness-'+key,meta)
    result=dict(schema='tk2-battle-original-v1',rom_sha256=ROM_SHA,core=dict(name='Nestopia libretro',original_capture_core_sha256=CORE_SHA),
        native_resolution=dict(width=256,height=240,main_height=160,panel_height=80,duel_name_height=64,duel_arena_height=96),
        palette=dict(name='royaltea',paper_rgb=list(PAPER),source='Nestopia upstream libretro/palettes.hpp; NES indices are not fixed RGB values'),
        backgrounds=backgrounds,sprites=sprites,terrain=terrain,witnesses=witnesses,
        intentionally_unavailable_effects=['fire','arrow','impact','rock'],
        scope='Pixel-exact native screenshot extraction and transparent sprite cutouts. Background layouts are references, not reconstructed city geography. The web renderer supplies current names/stats and animation timing. No game rule changes.',
        rights='Original game graphics retain their original rights and are not MIT relicensed. Extracted from captures made with the user-provided ROM. Tool code is covered by the repository code license.',
        build=dict(tool='tools/battle-original/build.py',tool_sha256=sha(Path(__file__).read_bytes()),runtime_requires_rom=False,runtime_requires_emulator=False))
    (OUT/'index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


def check():
    manifest=json.loads((OUT/'index.json').read_text())
    assert manifest['schema']=='tk2-battle-original-v1'
    seen=set()
    def visit(value):
        if isinstance(value,dict):
            if 'path' in value and 'sha256' in value:
                path=value['path'];assert re.fullmatch(r'/assets/battle-original/[a-z0-9_-]+\.png',path)
                file=ROOT/'game'/path.lstrip('/');assert file.is_file() and not file.is_symlink()
                assert sha(file.read_bytes())==value['sha256'],path
                image=Image.open(file);assert list(image.size)==[value['width'],value['height']],path
                if '/witness-' not in path and 'duelist' in path:assert image.mode=='RGBA' and image.getchannel('A').getextrema()==(0,255)
                seen.add(path)
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(manifest)
    assert manifest['build']['tool_sha256']==sha(Path(__file__).read_bytes())
    assert all(manifest['sprites'][key]['frames'] for key in ('infantry','cavalry','duelist','duelist_enemy','attack_formation','attack_formation_enemy'))
    for kind in ('attack_formation','attack_formation_enemy'):
        assert len(manifest['sprites'][kind]['frames'])==2
        for frame in manifest['sprites'][kind]['frames']:
            assert (frame['width'],frame['height'])==(128,160)
            image=Image.open(ROOT/'game'/frame['path'].lstrip('/'))
            assert image.mode=='RGBA' and image.getchannel('A').getextrema()==(0,255)
    return dict(images=len(seen),sprites={key:len(row['frames'])for key,row in manifest['sprites'].items()},rom_sha256=manifest['rom_sha256'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path)
    parser.add_argument('--rom',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if not args.check:
        if args.state_root is None or args.rom is None:parser.error('--state-root and --rom are required for extraction')
        build(args.state_root.resolve(),args.rom.resolve())
    print(json.dumps(check(),ensure_ascii=False))
