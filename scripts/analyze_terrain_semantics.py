#!/usr/bin/env python3
"""Class1 provenance, original BG/OAM evidence and exact AI selector behavior."""
from pathlib import Path
from collections import Counter
import argparse, csv, ctypes as C, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered import terrain_rules as maps
from source.recovered import terrain_semantics as model
from inspect_game_data import instruction

def sha(blob):return hashlib.sha256(blob).hexdigest()
def put(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def origin(bank,cpu):return 16+bank*8192+cpu-(0xe000 if bank==31 else 0xc000 if bank%2 else 0xa000)
def evidence(rom,bank,cpu,length,note):
    off=origin(bank,cpu)
    return {'bank':bank,'cpu':cpu,'file':off,'length':length,'hex':rom[off:off+length].hex(' ').upper(),'note':note}
def assembly(rom,bank,start,end):
    lines=[];pc=start
    while pc<end:
        off=origin(bank,pc);size,text=instruction(rom,off,pc)
        lines.append(f'{off:06X} b{bank:02d}:${pc:04X} {rom[off:off+size].hex(" ").upper():<9} {text}')
        pc+=size
    return lines

def ppu_state(path):
    # Nestopia's serialized end-of-frame mapper banks are the bottom UI banks.
    # Upper map BG banks instead come from the original F21E B2..B5 protocol.
    from analyze_terrain_rules import state_chunks
    blob=path.read_bytes();assert blob[:4]==b'NST\x1a'
    top=state_chunks(blob,8,8+int.from_bytes(blob[4:8],'little'))
    ppu=state_chunks(top[b'PPU\0'],0,len(top[b'PPU\0']))
    for tag in [b'NMT\0',b'OAM\0',b'PAL\0']:assert ppu[tag][0]==0
    return {'nmt':ppu[b'NMT\0'][1:],'oam':ppu[b'OAM\0'][1:],'pal':ppu[b'PAL\0'][1:],
            'reg':ppu[b'REG\0']}

def sprite_overlap(oam,bbox,sprite_height):
    x0,y0,x1,y1=bbox;hits=[]
    for i in range(64):
        sy,tile,attr,sx=oam[4*i:4*i+4];sy+=1
        if sy>=240:continue
        if sx<x1 and sx+8>x0 and sy<y1 and sy+sprite_height>y0:
            hits.append({'sprite':i,'screen_bbox':[sx,sy,sx+8,sy+sprite_height],
                         'tile':tile,'attributes':attr})
    return hits

def chr_indices(rom,pages,code):
    off=0x40010+pages[code//64]*1024+(code&63)*16;raw=rom[off:off+16]
    values=[((raw[y]>>(7-x))&1)|(((raw[y+8]>>(7-x))&1)<<1)for y in range(8)for x in range(8)]
    return values,{'ppu_code':code,'chr_1k_page':pages[code//64],'file':off,'hex':raw.hex(' ').upper(),
                   'pixel_index_counts':dict(Counter(values))}

def quad_indices(rom,pages,quad):
    values=[0]*256;tiles=[]
    for i,code in enumerate(quad):
        pixels,meta=chr_indices(rom,pages,code);tiles.append(meta)
        for y in range(8):
            for x in range(8):values[(y+8*(i//2))*16+x+8*(i%2)]=pixels[8*y+x]
    return values,tiles

def render_maps(rom_path,rom,out,rows):
    from PIL import Image,ImageDraw
    from nes_runtime import Runtime
    dest=out/'core-views';dest.mkdir(parents=True,exist_ok=True)
    parent=ROOT/'analysis/runtime/phase3/attack-intro-7.state'
    rt=Runtime(rom_path,dest);captures=[]
    try:
        for city in [5,6,9]:
            rt.load_state(parent);ram=bytearray(rt.memory(2));changes=[]
            # Global3 restores 8E/90 from saved viewport0512/0510. Include
            # those parameters explicitly instead of assuming the parent's
            # camera is zero. Native map and bottom UI have different scroll.
            for addr,value in [(0x50e,city),(0x7a,3),(0x510,0),(0x511,0),(0x512,0),(0x513,0)]:
                changes.append({'address':addr,'old':ram[addr],'new':value});ram[addr]=value
            C.memmove(rt.core.retro_get_memory_data(2),bytes(ram),len(ram))
            rt.run(300);temp=f'city{city}-capture';rt.snapshot(temp)
            png=dest/(temp+'.png');digest=sha(png.read_bytes());stem=f'city{city}-map-{digest[:12]}'
            for suffix in ['.png','.state','.json','-ram.bin','-sram.bin','-vram.bin']:
                (dest/(temp+suffix)).replace(dest/(stem+suffix))
            screen=Image.open(dest/(stem+'.png')).convert('RGB');fullzoom=screen.resize((768,720),Image.Resampling.NEAREST)
            zoomname=stem+'-fullframe-x3.png';fullzoom.save(dest/zoomname)
            final=(dest/(stem+'-ram.bin')).read_bytes();ppu=ppu_state(dest/(stem+'.state'))
            assert final[0x300]==255 and final[0x304]==255,'Drawing/message jobs still pending'
            assert list(final[0xaa:0xae])==list(maps.city_chunks(rom,city))
            pages=list(final[0xb2:0xb6]);height=16 if ppu['reg'][0]&32 else 8
            meta={'city':city,'parent_state':str(parent.relative_to(ROOT)),'parent_sha256':sha(parent.read_bytes()),
                  'rom_modified':False,'natural_gameplay':False,'ram_changes':changes,'replay_frames':300,
                  'absolute_runtime_frame':rt.frames,'image':stem+'.png','image_sha256':digest,
                  'fullframe_zoom':zoomname,'fullframe_zoom_sha256':sha((dest/zoomname).read_bytes()),
                  'fullframe_zoom_exact':list(fullzoom.getdata())==list(Image.open(dest/zoomname).getdata()),
                  'state':stem+'.state','state_sha256':sha((dest/(stem+'.state')).read_bytes()),
                  'ram_sha256':sha(final),'draw_job_0300':final[0x300],'draw_job_0304':final[0x304],
                  'battle_main_sub':[final[0x500],final[0x501]],'chunks':list(final[0xaa:0xae]),
                  'upper_map_bg_chr_pages':pages,'page_protocol':'fixed31 F21E reads RAM B2..B5 and writes A000/A800/B000/B800',
                  'camera_pixels':[int.from_bytes(final[0x8e:0x90],'little'),int.from_bytes(final[0x90:0x92],'little')],
                  'native_map_pixel_translation':[0,0], 'oam':list(ppu['oam']),'sprite_height':height,
                  'ppu_palette_hex':ppu['pal'].hex(' ').upper(),'glyph_name_claim':None,'visible_cells':[]}
            # Native map uses world pixel minus camera, with no UI -2 shift.
            # Check ROM BG quad
            # against nametable bytes and original CHR masks for every class1
            # cell with a complete 16×16 screen box and no OAM overlap.
            for cell in rows:
                if cell['city']!=city or not(0<=cell['x']<16 and 1<=cell['y']<10):continue
                x,y=cell['x'],cell['y'];cx,cy=meta['camera_pixels'];box=(16*x-cx,16*y-cy,16*x-cx+16,16*y-cy+16)
                overlaps=sprite_overlap(ppu['oam'],box,height)
                if overlaps:continue
                quad=list(maps.metatile(rom,cell['tile']));nmt=ppu['nmt'];at=64*y+2*x
                actual=[nmt[at],nmt[at+1],nmt[at+32],nmt[at+33]]
                if quad!=actual:continue # a UI overlay can replace BG, independent of OAM
                indices,tiles=quad_indices(rom,pages,quad);pixels=list(screen.crop(box).getdata())
                mapping={};matches=True
                for index,pixel in zip(indices,pixels):
                    if index in mapping and mapping[index]!=pixel:matches=False;break
                    mapping[index]=pixel
                if len(set(mapping.values()))!=len(mapping):matches=False
                if not matches:continue
                # Every class1 code uses only original pixel indices1 and2.
                assert set(indices)<=set([1,2])
                attr_off=960+(2*y//4)*8+(2*x//4)
                shift=((2*y%4)//2)*4+((2*x%4)//2)*2
                palette=(nmt[attr_off]>>shift)&3
                native_zoom=screen.crop(box).resize((128,128),Image.Resampling.NEAREST)
                name=f'city{city}-tile{cell["tile"]:02x}-x{x}-y{y}-{digest[:12]}-zoom.png';native_zoom.save(dest/name)
                assert list(Image.open(dest/name).getdata())==list(native_zoom.getdata())
                meta['visible_cells'].append({'x':x,'y':y,'raw_tile':cell['tile'],'raw_class':cell['raw_class'],
                    'raw_file':cell['tile_offset'],'screen_bbox':box,'oam_intersections':overlaps,
                    'original_bg_quad':quad,'nmt_quad':actual,'nmt_offset':at,'attribute_offset':attr_off,
                    'palette_index':palette,'nes_palette_codes':[ppu['pal'][4*palette+i]for i in range(4)],
                    'chr_tiles':tiles,'pixel_index_to_native_rgb':mapping,'chr_native_mask_exact':matches,
                    'zoom':name,'zoom_sha256':sha((dest/name).read_bytes()),'zoom_exact_from_fullframe':True})
            put(dest/(stem+'-evidence.json'),meta);captures.append(meta)
    finally:rt.close()
    found={}
    for cap in captures:
        for cell in cap['visible_cells']:found.setdefault(cell['raw_tile'],(cap,cell))
    assert set(found)==set(model.CLASS1_RAW_TILES),('Not all7 original raw variants are visibly checked',sorted(found))
    atlas=Image.new('RGB',(7*144,190),(240,240,240));draw=ImageDraw.Draw(atlas)
    selected=[]
    for i,tile in enumerate(model.CLASS1_RAW_TILES):
        cap,cell=found[tile];im=Image.open(dest/cell['zoom']);atlas.paste(im,(144*i,42))
        draw.text((144*i,4),f'raw {tile:02X} / class1',fill=(0,0,0));draw.text((144*i,20),f'city{cap["city"]} ({cell["x"]},{cell["y"]})',fill=(0,0,0))
        selected.append({'city':cap['city'],'fullframe':cap['image'],'fullframe_sha256':cap['image_sha256'],**cell})
    # Content hash in the atlas filename protects against stale browser caches.
    rawhash=sha(atlas.tobytes());atlasname=f'class1-seven-raw-tiles-{rawhash[:12]}.png';atlas.save(dest/atlasname)
    result={'captures':captures,'selected_raw_variants':selected,'atlas':atlasname,'atlas_sha256':sha((dest/atlasname).read_bytes()),
            'scope':'Original Nestopia framebuffer, explicit city/global RAM fixtures, no ROM modifications. All zooms are exact nearest-neighbor crops of the paired native full frame. No formal terrain name is printed here.'}
    put(out/'visual-evidence.json',result);return result

def render_attack(rom_path,rom,out):
    """Terrain1 ordinary-attack background; no claim about actor reachability."""
    from PIL import Image
    from nes_runtime import Runtime
    dest=out/'attack-view';dest.mkdir(parents=True,exist_ok=True)
    parent=ROOT/'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu.state'
    rt=Runtime(rom_path,dest)
    try:
        rt.load_state(parent);ram=bytearray(rt.memory(2));changes=[]
        for addr,value in [(0x544,1),(0x7a,5)]:
            changes.append({'address':addr,'old':ram[addr],'new':value});ram[addr]=value
        C.memmove(rt.core.retro_get_memory_data(2),bytes(ram),len(ram));rt.run(180)
        rt.snapshot('capture');digest=sha((dest/'capture.png').read_bytes());stem=f'class1-attack-background-{digest[:12]}'
        for suffix in ['.png','.state','.json','-ram.bin','-sram.bin','-vram.bin']:
            (dest/('capture'+suffix)).replace(dest/(stem+suffix))
        screen=Image.open(dest/(stem+'.png')).convert('RGB');zoom=screen.resize((768,720),Image.Resampling.NEAREST)
        zoomname=stem+'-fullframe-x3.png';zoom.save(dest/zoomname)
        final=(dest/(stem+'-ram.bin')).read_bytes();ppu=ppu_state(dest/(stem+'.state'));pages=list(final[0xb2:0xb6])
        assert final[0x544]==1 and final[0x7a]==6 and final[0x300]==255 and final[0x304]==255
        samples=[];covered=0
        for row in range(20):
            for col in range(32):
                box=(col*8,row*8,col*8+8,row*8+8)
                if sprite_overlap(ppu['oam'],box,16 if ppu['reg'][0]&32 else 8):continue
                code=ppu['nmt'][32*row+col];indices,meta=chr_indices(rom,pages,code);pixels=list(screen.crop(box).getdata());mapping={}
                for index,color in zip(indices,pixels):
                    if index in mapping:assert mapping[index]==color,('attack CHR/native mask mismatch',row,col)
                    mapping[index]=color
                assert len(set(mapping.values()))==len(mapping)
                covered+=1
                if code not in {v['ppu_code']for v in samples}:samples.append({'ppu_code':code,'row':row,'column':col,'pixel_index_to_native_rgb':mapping,**meta})
        result={'rom_modified':False,'natural_gameplay':False,'parent_state':str(parent.relative_to(ROOT)),
                'parent_state_sha256':sha(parent.read_bytes()),'ram_changes':changes,'replay_frames':180,
                'image':stem+'.png','image_sha256':digest,'fullframe_zoom':zoomname,'fullframe_zoom_sha256':sha((dest/zoomname).read_bytes()),
                'state':stem+'.state','state_sha256':sha((dest/(stem+'.state')).read_bytes()),
                'ram_sha256':sha(final),'terrain_0544':final[0x544],'global_007a':final[0x7a],
                'drawing_jobs':[final[0x300],final[0x304]],'bg_chr_pages':pages,'top_bg_tile_count_with_exact_chr_masks':covered,
                'chr_native_mask_samples':samples,'menu_or_actor_behavior_verified':False,
                'setup_chain':'fixed31 E22F reads0544; E237 adds2 for E370 graphic profile; E24A selector37 A024 loads terrain-indexed scene resource',
                'formal_name':None,'scope':'Original ordinary-attack terrain1 background only. State/actors/menu parameters retained from an explicit adjacent-target fixture. All640 top BG tiles (except any OAM intersections) are checked against original CHR/native pixel masks.'}
        put(out/'attack-background-evidence.json',result);return result
    finally:rt.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/terrain');p.add_argument('--render-core',action='store_true');a=p.parse_args()
    rom=a.rom.read_bytes();data=model.TerrainSemanticsData.from_rom(rom);a.out.mkdir(parents=True,exist_ok=True)
    rows=[];tilecounts=Counter();citycounts=Counter()
    for city in range(30):
        chunks=maps.city_chunks(rom,city)
        for y in range(20):
            for x in range(31):
                if not maps.legal_cell(x,y):continue
                cell=maps.map_cell(rom,chunks,x,y)
                if cell['raw_class']!=1:continue
                rows.append({'city':city,**cell});tilecounts[cell['tile']]+=1;citycounts[city]+=1
    assert len(rows)==335 and set(tilecounts)==set(model.CLASS1_RAW_TILES)
    variants=[{'raw_tile':t,'classifier_file':0x1175b+t,'class':rom[0x1175b+t],
               'metatile_file':maps.METATILE_TABLE_OFFSET+4*t,'bg_quad':list(maps.metatile(rom,t)),
               'legal_cell_count':tilecounts[t]}for t in model.CLASS1_RAW_TILES]
    evidence_rows=[
        evidence(rom,8,0xb6e5,10,'AI B6E5 preserves class1; only raw>=6 normalizes to2'),
        evidence(rom,13,0xdb46,10,'Player DB46 preserves class1; only raw>=6 normalizes to2'),
        evidence(rom,8,0xa78c,65,'AI cost computation, including repeated byte8 read A7AA/A7AF'),
        evidence(rom,12,0xa7e7,60,'Player selector063C[slot]>=6, affinity and final AP subtraction'),
        evidence(rom,8,0xa7cd,56,'Exact AI first/second cost tables, identical to player A823/A83F'),
        evidence(rom,31,0xf21e,25,'Top map BG four1KiB page write protocol; end-of-frame mapper banks differ'),
        evidence(rom,12,0xa354,20,'Target normalized terrain from DB46 is written0544 for ordinary attack scene'),
        evidence(rom,12,0xadcc,36,'Player fire targets0/2; trap/virtual/raid targets0/4; water targets3'),
        evidence(rom,12,0xb01d,14,'Player 奇門遁甲 terrain gate excludes3 and5, admits1'),
        evidence(rom,12,0xb3fe,20,'Water-only immobilization effect skips class1'),
        evidence(rom,12,0xb494,20,'Water-only troop damage effect skips class1'),
        evidence(rom,12,0xb538,22,'劫火 damage effect skips only5, so terrain1 passes this gate'),
        evidence(rom,12,0xb91e,19,'Area target discovery skips only castle5; class1 is included'),
        evidence(rom,14,0xb891,41,'Ordinary-attack renderer indexes BB48/BB1E/BB2C by0544'),
        evidence(rom,15,0xcaf9,43,'Attack-scene cell lookup also uses0544 to select map resource'),
        evidence(rom,15,0xd108,32,'Attack command template indexed by affinity*8+terrain; class1 is an index, not a name'),
    ]
    lines=['; Original AI/player target-terrain movement computation. Data tables are not opcodes.']
    lines+=assembly(rom,8,0xa78c,0xa7cd)+['; PLAYER']+assembly(rom,12,0xa7e7,0xa823)
    (a.out/'movement-selector.asm').write_text('\n'.join(lines)+'\n')
    with(a.out/'class1-legal-cells.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    scene_tables={'selector_bank_table_cpu':0xbb48,'selector_bank_table_file':origin(14,0xbb48),
                  'selector_bank_ids':list(rom[origin(14,0xbb48):origin(14,0xbb48)+6]),
                  'first_pointer_cpu':0xbb1e,'first_pointer_file':origin(14,0xbb1e),
                  'first_pointers':[int.from_bytes(rom[origin(14,0xbb1e)+2*i:origin(14,0xbb1e)+2*i+2],'little')for i in range(6)],
                  'second_pointer_cpu':0xbb2c,'second_pointers':[int.from_bytes(rom[origin(14,0xbb2c)+2*i:origin(14,0xbb2c)+2*i+2],'little')for i in range(6)],
                  'scope':'Original indexed resource identity; no readable name association is implied'}
    visual=render_maps(a.rom,rom,a.out,rows)if a.render_core else None
    attack=render_attack(a.rom,rom,a.out)if a.render_core else None
    report={'rom_sha256':model.ROM_SHA256,'formal_name':None,'formal_name_status':'unconfirmed',
            'class1_profile':model.class1_profile(data=data),'legal_cell_count':len(rows),'city_counts':dict(citycounts),
            'raw_variants':variants,'evidence':evidence_rows,'ordinary_attack_scene_tables':scene_tables,
            'ai_selector_formula':'first_table iff officer.raw_byte8>=3; byte9 is ignored because Y is not incremented',
            'player_selector_formula':'first_table iff RAM063C[slot]>=6; cache=(troopword&1023)//100',
            'name_search_scope':'Reviewed original classifier, metatile/CHR, movement, tactical terrain gates, effect gates, attack-scene indexed consumers and existing decoded menu/message corpus. No direct class1 name pointer was found. This does not prove no name exists anywhere in ROM.',
            'formal_name_primary_source_attempt':{'url':'https://endlessfight.org/discuz/forum.php?mod=viewthread&tid=1261','page_title':'FC 三国志II 覇王の大陸 取扱説明書','result':'Public catalog found; scan is behind membership/points access. Contents were not retrieved or treated as evidence.'},
            'visual_evidence':'visual-evidence.json'if visual else None,
            'attack_background_evidence':'attack-background-evidence.json'if attack else None,
            'limitations':['Smooth orange pixels alone do not establish road, desert, plain or another formal terrain name.','Costs for raw affinity3 are zero, but UI/domain evidence marks3 undefined.','Terrain gate acceptance is not complete tactic usability: adjacency, stats, team, resources and targeting still apply.','AI selector discrepancy is preserved from the supplied ROM; no correction or patch is applied.']}
    put(a.out/'evidence.json',report)
    print(json.dumps({'formal_name':None,'class1_cells':len(rows),'raw_tiles':variants,'core_rendered':bool(visual)},ensure_ascii=False))
if __name__=='__main__':main()
