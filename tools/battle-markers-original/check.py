#!/usr/bin/env python3
"""Verify exact native tactical flag pixels without ROM, core or fonts."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'game/assets/battle-markers-original'
PREFIX='/assets/battle-markers-original/'
FILES={'index.json','provenance.json','markers-native.png','markers-4x.png'}
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CHR_SHA='ccdb9c9b9a7eee020dac687088f8ed91dafd80d9980efef5834dc9fba26087da'
ROWS_SHA='5a5400d9d2035d2a30e7c63224714373589d69558c42d1d10e92c468af1ff33e'
CASES_SHA='f67747b8c5e6761335efd57397b49618ac884ef03f72da6960400d690a6016d5'
WITNESS='/assets/battle-original/witness-tactical.png'
WITNESS_SHA='62a1d06ab0e5dca6cda856b4a7909febfb9b45a031c38e059f9cbf5469566c7d'
PALETTE=((0,0,0),(255,213,203),(255,255,255),(187,45,9))
for _name,_path in [('native_marker_builder',Path(__file__).with_name('build.py')),('native_marker_png',ROOT/'game/build_portrait_manifest.py')]:
    _spec=importlib.util.spec_from_file_location(_name,_path);_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_module)
    if _name=='native_marker_builder':builder=_module
    else:png=_module

def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def pixels(raw,size):return png.png_pixels(raw,size)[1]
def crop(raw,width,rect):
    x,y,w,h=rect
    return b''.join(raw[((y+dy)*width+x)*4:((y+dy)*width+x+w)*4]for dy in range(h))
def public(value):
    require(type(value)is str and value in {PREFIX+n for n in FILES},'Unlisted original marker path')
    return value

def validate(data,read):
    require(data.get('schema')=='tk2-battle-markers-original-v1'and data.get('rom_sha256')==ROM_SHA,'Invalid original marker identity')
    require(data.get('native_size')==[16,16]and data.get('pixel_scale')==4 and data.get('source_rect_format')=='x,y,width,height','Invalid original marker geometry')
    require('/Users/'not in json.dumps(data)and '/tmp/'not in json.dumps(data),'Private paths in original marker manifest')
    record=data.get('provenance',{});raw=read(public(record.get('path')))
    require(sha(raw)==record.get('sha256'),'Marker provenance hash mismatch');proof=json.loads(raw)
    require(proof.get('schema')=='tk2-original-battle-markers-provenance-v1'and proof.get('rom_sha256')==ROM_SHA and proof.get('rom_modified')is False,'Invalid marker origin')
    require(all(proof.get('runtime_requires_'+name)is False for name in ('rom','core','archive')),'Marker runtime requires original inputs')
    require('/Users/'not in raw.decode()and '/tmp/'not in raw.decode(),'Private paths in marker provenance')
    require(proof.get('palette_rgb')==[list(c)for c in PALETTE],'Unverified original marker palette')
    require(proof.get('army_type')==dict(record_byte_index=11,mask=12,shift=2,values={'0':'平','1':'山','2':'水'},unsupported_code=3),'Original army type offset must be byte11 bits2..3')
    source=proof.get('source_chunks',{});chunks={}
    for key,expected,size,offset in [('marker_chr',CHR_SHA,1024,0x40010+138*1024),('top_tile_rows',ROWS_SHA,66,0x2eaf4)]:
        row=source.get(key,{});blob=bytes.fromhex(row.get('hex',''))
        require(len(blob)==row.get('bytes')==size and sha(blob)==row.get('sha256')==expected,'Original marker source changed: '+key)
        require(row.get('rom_offset')==offset,'Wrong marker source offset')
        chunks[key]=blob
    cases=proof.get('cpu_witness_cases',[])
    require(isinstance(cases,list)and len(cases)==132 and sha(json.dumps(cases,separators=(',',':')).encode())==CASES_SHA,'Original marker CPU witnesses changed')
    rows=[list(chunks['top_tile_rows'][i*11:(i+1)*11])for i in range(6)]
    frames=data.get('frames',{});expected_keys={}
    for palette,kind,teams,commander,tiles in cases:
        key=f'{palette}:{kind}:{teams}'+(':commander'if commander else'')
        require(tiles==builder.tile_ids(rows,palette,kind,teams,commander),'Marker tile selection differs from original CPU')
        row=int(commander)*6+(0 if palette=='friendly'else 3)+kind
        expected_keys[key]=dict(palette=palette,type=kind,teams=teams,commander=commander,source_rect=[teams*64,row*64,64,64],tiles=tiles)
    require(isinstance(frames,dict)and all(isinstance(frame,dict)and set(frame)=={'palette','type','teams','commander','source_rect','tiles'}
        and type(frame['palette'])is str and type(frame['type'])is int and type(frame['teams'])is int and type(frame['commander'])is bool
        and isinstance(frame['source_rect'],list)and len(frame['source_rect'])==4 and all(type(v)is int for v in frame['source_rect'])
        and isinstance(frame['tiles'],list)and len(frame['tiles'])==4 and all(type(v)is int for v in frame['tiles'])for frame in frames.values()),'Invalid marker frame types')
    require(frames==expected_keys,'Marker frame mapping differs from original')
    decoded={}
    for key,size,name in [('native_atlas',(176,192),'markers-native.png'),('atlas',(704,768),'markers-4x.png')]:
        row=data.get(key,{})
        require(row.get('path')==PREFIX+name and (row.get('width'),row.get('height'))==size,'Invalid marker atlas metadata')
        blob=read(public(row['path']));require(sha(blob)==row.get('sha256'),'Marker atlas hash mismatch')
        decoded[key]=pixels(blob,size)
    require(decoded['atlas']==builder.nearest4(decoded['native_atlas'],176,192),'Marker4x pixels differ from native atlas')
    for key,row in frames.items():
        native_rect=[v//4 for v in row['source_rect']]
        require(crop(decoded['native_atlas'],176,native_rect)==builder.render(chunks['marker_chr'],row['tiles']),'Marker sprite differs from original CHR: '+key)
    witness=proof.get('witness',{})
    require(witness.get('path')==WITNESS and witness.get('sha256')==WITNESS_SHA and witness.get('source_rect')==[32,98,16,16],'Unverified original marker witness')
    blob=read(WITNESS);require(sha(blob)==WITNESS_SHA,'Retained original callback pixels changed')
    witness_pixels=crop(pixels(blob,(256,240)),256,[32,98,16,16])
    frame=frames['friendly:1:10:commander'];native_rect=[v//4 for v in frame['source_rect']]
    require(witness_pixels==crop(decoded['native_atlas'],176,native_rect),'Marker atlas differs from original native callback')
    return dict(schema=data['schema'],frames=132,cpu_cases=132,native_size=[16,16],atlas=[704,768],exact4x=True,native_callback_pixels=256,checker_requires_rom=False,checker_requires_emulator=False)

def safe_read(root,path):
    root=Path(root)
    if path==WITNESS:
        file=ROOT/'game/assets/battle-original/witness-tactical.png'
    else:file=root/public(path).removeprefix(PREFIX)
    require(not root.is_symlink()and not file.is_symlink(),'Symlink marker path')
    return file.read_bytes()
def check(root=OUT):
    root=Path(root);require(not root.is_symlink(),'Symlink marker directory')
    require({p.name for p in root.iterdir()}==FILES,'Unexpected original marker source file')
    data=json.loads(safe_read(root,PREFIX+'index.json'))
    return validate(data,lambda path:safe_read(root,path))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=OUT);a=p.parse_args();print(json.dumps(check(a.root),sort_keys=True))
