#!/usr/bin/env python3
"""Read-only export of original16x16 tactical flags; no fonts or AI redraws.

Optional offline CPU witnesses use py65. The shipped checker/runtime require
only retained declarative bitmap data and PNGs, never a ROM or emulator.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import zlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'game/assets/battle-markers-original'
PREFIX='/assets/battle-markers-original/'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
WITNESS=ROOT/'game/assets/battle-original/witness-tactical.png'
WITNESS_SHA='62a1d06ab0e5dca6cda856b4a7909febfb9b45a031c38e059f9cbf5469566c7d'
PALETTE=((0,0,0),(255,213,203),(255,255,255),(187,45,9))
BOTTOM={0:((0xbd,0xbe),(0xac,0xad),(0xae,0xaf)),2:((0xb8,0xb9),(0x9c,0x9d),(0x9e,0x9f))}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def jb(value):return(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
def png(raw,width,height):
    def chunk(kind,value):return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value)&0xffffffff)
    encoded=b''.join(b'\0'+raw[y*width*4:(y+1)*width*4]for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(encoded,9))+chunk(b'IEND',b'')
def nearest4(raw,width,height):
    return b''.join(b''.join(raw[(y*width+x)*4:(y*width+x+1)*4]*4 for x in range(width))*4 for y in range(height))
def tile_ids(rows,palette,kind,teams,commander):
    style=0 if palette=='friendly'else 2
    left,right=rows[style*2][teams],rows[style*2+1][teams]
    if commander:
        left=(0xba if teams==10 else 0xbb)if style==0 else(0xb5 if teams==10 else 0xb6)
    return [left,right,*BOTTOM[style][kind]]
def render(chr_page,tiles):
    raw=bytearray(16*16*4)
    for tile,(dx,dy)in zip(tiles,((0,0),(8,0),(0,8),(8,8))):
        pattern=chr_page[(tile%64)*16:(tile%64+1)*16]
        for y in range(8):
            for x in range(8):
                index=(pattern[y]>>(7-x)&1)|((pattern[y+8]>>(7-x)&1)<<1)
                at=((y+dy)*16+x+dx)*4;raw[at:at+4]=bytes([*PALETTE[index],255])
    return bytes(raw)
def cpu_tiles(rom,palette,kind,teams,commander):
    from py65.devices.mpu6502 import MPU
    memory=[0]*65536
    for bank,cpu in ((23,0xa000),(31,0xe000)):memory[cpu:cpu+8192]=rom[16+bank*8192:16+(bank+1)*8192]
    slot=(0 if commander else 1)if palette=='friendly'else(10 if commander else 11)
    memory[0]=slot;memory[0x507]=0x10;memory[0x628+slot]=kind|(128 if palette=='enemy'else 0);memory[0x63c+slot]=teams
    memory[0x6f0a]=0;memory[0x6f12]=2
    cpu=MPU(memory=memory,pc=0xa983);cpu.stPushWord(0x7fff)
    for step in range(1000):
        if cpu.pc==0x8000:return memory[0x1b0:0x1b4]
        cpu.step()
    raise ValueError('Original tactical marker routine did not return')
def export(rom_path,out=OUT,verify_cpu=False):
    rom=Path(rom_path).read_bytes();assert sha(rom)==ROM_SHA,'Wrong original ROM'
    assert sha(WITNESS.read_bytes())==WITNESS_SHA,'Retained native witness changed'
    row_raw=rom[0x2eaf4:0x2eb36];rows=[list(row_raw[i*11:(i+1)*11])for i in range(6)]
    chr_offset=0x40010+138*1024;chr_page=rom[chr_offset:chr_offset+1024]
    atlas=bytearray(176*192*4);frames={};cases=[]
    for commander in (False,True):
        for palette,side_index in (('friendly',0),('enemy',1)):
            for kind in range(3):
                row=int(commander)*6+side_index*3+kind
                for teams in range(11):
                    tiles=tile_ids(rows,palette,kind,teams,commander)
                    if verify_cpu:
                        actual=cpu_tiles(rom,palette,kind,teams,commander)
                        assert tiles==actual,(palette,kind,teams,commander,tiles,actual)
                        cases.append([palette,kind,teams,commander,actual])
                    sprite=render(chr_page,tiles)
                    for y in range(16):
                        at=((row*16+y)*176+teams*16)*4;atlas[at:at+64]=sprite[y*64:(y+1)*64]
                    key=f'{palette}:{kind}:{teams}'+(':commander'if commander else'')
                    frames[key]=dict(palette=palette,type=kind,teams=teams,commander=commander,source_rect=[teams*64,row*64,64,64],tiles=tiles)
    if not verify_cpu:
        old=Path(out)/'provenance.json'
        if old.exists():
            previous=json.loads(old.read_text())
            cases=previous.get('cpu_witness_cases',[])
            assert len(cases)==132 and all(row[-1]==tile_ids(rows,*row[:4])for row in cases),'Missing matching retained CPU witnesses'
        else:raise ValueError('First extraction requires --verify-cpu and py65')
    chunk=lambda raw,**where:dict(**where,bytes=len(raw),hex=raw.hex(),sha256=sha(raw))
    proof=dict(schema='tk2-original-battle-markers-provenance-v1',rom_sha256=ROM_SHA,rom_modified=False,
        runtime_requires_rom=False,runtime_requires_core=False,runtime_requires_archive=False,
        pixel_origin='Original CHR page138 plus original23:A983 unitBG table selection; no font rendering, smoothing, invented pixels or AI redraw.',
        source_chunks=dict(marker_chr=chunk(chr_page,chr_page_1k=138,rom_offset=chr_offset),top_tile_rows=chunk(row_raw,physical_bank=23,cpu='AAE4',rom_offset=0x2eaf4)),
        source_routine=dict(physical_bank=23,cpu='A983',end_exclusive='AAE4',rom_offset=0x2e993,sha256=sha(rom[0x2e993:0x2eaf4])),
        palette_rgb=[list(c)for c in PALETTE],bottom_tile_ids={str(k):[list(pair)for pair in pairs]for k,pairs in BOTTOM.items()},
        controller_mapping=dict(friendly=0,enemy=2,note='Original controller0 human white/black; controller>=2 CPU red/pale. These are rendered by current player ownership, not fixed attacker/defender assignment.'),
        army_type=dict(record_byte_index=11,mask=12,shift=2,values={'0':'平','1':'山','2':'水'},unsupported_code=3),
        team_count_note='Native strength cache063C supports0..10. The remake supplies ceil(current troops/100) for requested100-person squads; zero remains the genuine original0 glyph and may receive a separate routed overlay.',
        commander_note='Original slots0 or10 override the top-left glyph; count10 has its own combined numeral/commander glyph.',
        cpu_witness_schema=['palette','type','teams','commander','native_tile_ids'],cpu_witness_cases=cases,
        witness=dict(path='/assets/battle-original/witness-tactical.png',sha256=WITNESS_SHA,width=256,height=240,
            original_capture_sha256='1a7b8d3c1d3b6f6981c013171d9b116a2298f4f9849a8e79be48450dc97c64a3',
            original_capture_id='source:research-archive/analysis/runtime/phase3/battle-free-cursor',
            core_sha256=CORE_SHA,controlled_fixture=True,natural_gameplay=False,
            source_rect=[32,98,16,16],palette='friendly',type=1,teams=10,commander=True,native_tiles=[186,171,172,173],
            raster_note='Map CHR banks change during scanlines; the saved end-of-frame bank registers do not identify the marker bank. Matching native callback pixels independently identifies page138.'))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    blobs={'markers-native.png':png(bytes(atlas),176,192),'markers-4x.png':png(nearest4(bytes(atlas),176,192),704,768),'provenance.json':jb(proof)}
    for name,blob in blobs.items():(out/name).write_bytes(blob)
    meta=lambda name,w,h:dict(path=PREFIX+name,width=w,height=h,sha256=sha(blobs[name]))
    manifest=dict(schema='tk2-battle-markers-original-v1',rom_sha256=ROM_SHA,source='original-chr-and-native-tactical-marker-routine',
        native_size=[16,16],pixel_scale=4,source_rect_format='x,y,width,height',
        native_atlas=meta('markers-native.png',176,192),atlas=meta('markers-4x.png',704,768),
        provenance=dict(path=PREFIX+'provenance.json',sha256=sha(blobs['provenance.json'])),frames=frames)
    (out/'index.json').write_bytes(jb(manifest))
    print(json.dumps(dict(frames=len(frames),cpu_cases=len(cases),native=[176,192],scaled=[704,768],files=4,chr_sha256=sha(chr_page),rows_sha256=sha(row_raw),cpu_cases_sha256=sha(json.dumps(cases,separators=(',',':')).encode()))))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--verify-cpu',action='store_true');a=p.parse_args();export(a.rom,a.out,a.verify_cpu)
