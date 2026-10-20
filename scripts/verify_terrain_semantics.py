#!/usr/bin/env python3
"""Original ROM oracles for class1 lookup, movement selector and terrain gates."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered import terrain_semantics as model
from source.recovered import terrain_rules as maps

def verify_images(rom,out):
    """Run under system Python with Pillow, without modifying the trace venv."""
    from PIL import Image
    from analyze_terrain_semantics import ppu_state,quad_indices,chr_indices,sprite_overlap
    visual=json.loads((out/'visual-evidence.json').read_text());counts=Counter()
    for cap in visual['captures']:
        dest=out/'core-views';screen=Image.open(dest/cap['image']).convert('RGB')
        zoom=Image.open(dest/cap['fullframe_zoom']).convert('RGB')
        assert list(screen.resize((768,720),Image.Resampling.NEAREST).getdata())==list(zoom.getdata())
        counts['independent_fullframe_zoom_pixels']+=1
        ram=(dest/(Path(cap['state']).stem+'-ram.bin')).read_bytes();ppu=ppu_state(dest/cap['state'])
        for cell in cap['visible_cells']:
            x,y=cell['x'],cell['y'];box=tuple(cell['screen_bbox']);quad=list(maps.metatile(rom,cell['raw_tile']))
            assert quad==cell['nmt_quad'];at=64*y+2*x;nmt=ppu['nmt'];assert [nmt[at],nmt[at+1],nmt[at+32],nmt[at+33]]==quad
            assert not sprite_overlap(ppu['oam'],box,cap['sprite_height'])
            indices,_=quad_indices(rom,list(ram[0xb2:0xb6]),quad);mapping={int(k):tuple(v)for k,v in cell['pixel_index_to_native_rgb'].items()}
            crop=screen.crop(box);assert list(crop.getdata())==[mapping[i]for i in indices]
            assert list(Image.open(dest/cell['zoom']).convert('RGB').getdata())==list(crop.resize((128,128),Image.Resampling.NEAREST).getdata())
            counts['independent_class1_original_chr_and_native_crop_pixels']+=1
    attack=json.loads((out/'attack-background-evidence.json').read_text());dest=out/'attack-view'
    screen=Image.open(dest/attack['image']).convert('RGB');zoom=Image.open(dest/attack['fullframe_zoom']).convert('RGB')
    assert list(screen.resize((768,720),Image.Resampling.NEAREST).getdata())==list(zoom.getdata());counts['independent_fullframe_zoom_pixels']+=1
    ram=(dest/(Path(attack['state']).stem+'-ram.bin')).read_bytes();ppu=ppu_state(dest/attack['state']);pages=list(ram[0xb2:0xb6])
    mapping={}
    for sample in attack['chr_native_mask_samples']:
        for k,v in sample['pixel_index_to_native_rgb'].items():
            key=int(k);value=tuple(v)
            assert key not in mapping or mapping[key]==value
            mapping[key]=value
    for row in range(20):
        for col in range(32):
            box=(col*8,row*8,col*8+8,row*8+8)
            if sprite_overlap(ppu['oam'],box,16 if ppu['reg'][0]&32 else 8):continue
            code=ppu['nmt'][32*row+col];indices,_=chr_indices(rom,pages,code)
            assert list(screen.crop(box).getdata())==[mapping[i]for i in indices]
            counts['independent_attack_background_chr_and_native_pixels']+=1
    return dict(counts)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/terrain');p.add_argument('--images-only',action='store_true',help='Internal system-Python/Pillow pixel verifier');a=p.parse_args()
    rom=a.rom.read_bytes();data=model.TerrainSemanticsData.from_rom(rom);counts=Counter();failures=[];examples=[]
    if a.images_only:
        print(json.dumps(verify_images(rom,a.out)));return
    from verify_terrain_rules import fresh,run
    def check(name,condition,details):
        counts[name]+=1
        if not condition:failures.append({'group':name,'details':details})
    def flags(q):return int(q['carry'])|int(q['zero'])*2|int(q['overflow'])*64|int(q['negative'])*128
    b=fresh(rom,8);b[0x6f8c]=0;b[0x664]=0
    def ai_case(terrain,officer_flags,low,high,ap,group):
        b[0x63c8]=low;b[0x63c9]=high;b[0x63cb]=officer_flags;b[0x505]=ap
        cpu,steps=run(b,0xa78c,reg={'a':terrain});q=model.ai_movement_quote(terrain,officer_flags,low,ap,data=data)
        got=(cpu.a,cpu.x,cpu.y,cpu.p&0xc3);expected=(q['remaining_ap'],q['return_x'],q['return_y'],flags(q))
        check(group,got==expected,{'terrain':terrain,'flags':officer_flags,'byte8':low,'byte9':high,'ap':ap,'got':got,'expected':expected})
    # Every low byte, byte9 boundary values, all four affinity encodings and
    # insufficient/exact/overflowing AP cases, for the requested class1.
    for low in range(256):
        for high in [0,1,2,3,255]:
            for affinity in range(4):
                for ap in [0,2,3,4,255]:ai_case(1,affinity<<2,low,high,ap,'ai_class1_exhaustive_low_byte')
    # Also exercise every packed flag byte and every possible ignored byte9.
    for packed in range(256):
        for low in [2,3]:
            for ap in [0,3,4,255]:ai_case(1,packed,low,packed,ap,'ai_class1_all_packed_flags_and_high_bytes')
    for terrain in [0,2,3,4,5]:
        for low in [0,1,2,3,88,89,90,255]:
            for high in [0,255]:
                for affinity in range(4):
                    for ap in [0,1,3,6,255]:ai_case(terrain,affinity<<2,low,high,ap,'ai_other_terrain_selector_boundaries')
    bp=fresh(rom,12);bp[0x509]=0;bp[0x664]=0
    def player_case(terrain,affinity,cache,ap,group):
        bp[0x63cb]=affinity<<2;bp[0x63c]=cache;bp[0x505]=ap
        cpu,steps=run(bp,0xa7e7,reg={'a':terrain});q=model.player_movement_quote(terrain,affinity<<2,cache,ap,data=data)
        got=(cpu.a,cpu.x,cpu.p&0xc3);expected=(q['remaining_ap'],q['return_x'],flags(q))
        check(group,got==expected,{'terrain':terrain,'affinity':affinity,'cache':cache,'ap':ap,'got':got,'expected':expected})
    for cache in range(256):
        for affinity in range(4):
            for ap in [0,2,3,4,255]:player_case(1,affinity,cache,ap,'player_class1_full_cache_domain')
    for terrain in [0,2,3,4,5]:
        for cache in [0,1,5,6,7,255]:
            for affinity in range(4):
                for ap in [0,2,3,4,255]:player_case(terrain,affinity,cache,ap,'player_other_terrain_cache_boundaries')
    cells=json.loads((a.out/'evidence.json').read_text())['legal_cell_count'];assert cells==335
    class1=[]
    for city in range(30):
        chunks=maps.city_chunks(rom,city)
        for y in range(20):
            for x in range(31):
                if not maps.legal_cell(x,y):continue
                cell=maps.map_cell(rom,chunks,x,y)
                if cell['raw_class']!=1:continue
                class1.append((city,chunks,x,y))
                for pair,entry,zpx,zpy in [(8,0xb6e5,0x20,0x21),(12,0xdb46,0x10,0x11)]:
                    lookup=fresh(rom,pair);lookup[0xa8]=0xaa;lookup[0xa9]=0
                    for i,chunk in enumerate(chunks):lookup[0xaa+i]=chunk
                    lookup[zpx]=x;lookup[zpy]=y;cpu,steps=run(lookup,entry)
                    check('all335_class1_player_and_ai_lookups',cpu.a==1,{'city':city,'xy':[x,y],'entry':entry,'got':cpu.a})
    # Four self-contained terrain predicates can be compared as full routines.
    for terrain in range(6):
        for entry,expected in [(0xadcc,terrain in[0,2]),(0xadd8,terrain in[0,4]),(0xade4,terrain==3),(0xb01d,terrain not in[3,5])]:
            gate=fresh(rom);gate[0x0a]=terrain;cpu,steps=run(gate,entry)
            check('complete_player_terrain_gate_routines',bool(cpu.p&1)==expected,{'terrain':terrain,'entry':entry,'carry':bool(cpu.p&1),'expected':expected})
    # Full no-effect water branches, and the original inferno prefix before
    # B55C does damage. No RNG or damage helper is replaced with fake success.
    for city,chunks,x,y in class1:
        for entry,stop in [(0xb3fe,0x0200),(0xb494,0x0200),(0xb538,0xb55c)]:
            effect=fresh(rom);effect[0xa8]=0xaa;effect[0xa9]=0
            for i,chunk in enumerate(chunks):effect[0xaa+i]=chunk
            effect[0x12]=0;effect[0x600]=x;effect[0x614]=y;effect[0x650]=7;effect[0x509]=2
            before=bytes(effect.sram);cpu,steps=run(effect,entry,stop=stop)
            check('all335_class1_water_skip_and_inferno_prefix',effect[0x650]==7 and bytes(effect.sram)==before,
                  {'city':city,'xy':[x,y],'entry':entry,'stop_pc':cpu.pc,'halt_before_damage':entry==0xb538})
    # File hashes, completion flags, seven variants and no-OAM checks provide
    # independent artifact integrity. Pixel-crop equality is performed during
    # actual core capture by the analyzer and retained for all122 cells.
    visual=json.loads((a.out/'visual-evidence.json').read_text());dest=a.out/'core-views'
    for cap in visual['captures']:
        exact=True
        for key,hkey in [('image','image_sha256'),('fullframe_zoom','fullframe_zoom_sha256'),('state','state_sha256')]:
            exact &= hashlib.sha256((dest/cap[key]).read_bytes()).hexdigest()==cap[hkey]
        exact &= cap['draw_job_0300']==255 and cap['draw_job_0304']==255 and cap['camera_pixels']==[0,0]
        check('complete_core_capture_hashes_and_drawing_readiness',exact,{'city':cap['city']})
        for cell in cap['visible_cells']:
            exact=cell['original_bg_quad']==cell['nmt_quad'] and not cell['oam_intersections'] and cell['chr_native_mask_exact'] and cell['zoom_exact_from_fullframe']
            exact &= hashlib.sha256((dest/cell['zoom']).read_bytes()).hexdigest()==cell['zoom_sha256']
            check('native_bg_chr_mask_and_no_sprite_overlay',exact,{'city':cap['city'],'raw_tile':cell['raw_tile'],'xy':[cell['x'],cell['y']]})
    attack=json.loads((a.out/'attack-background-evidence.json').read_text());dest=a.out/'attack-view';exact=True
    for key,hkey in [('image','image_sha256'),('fullframe_zoom','fullframe_zoom_sha256'),('state','state_sha256')]:
        exact &= hashlib.sha256((dest/attack[key]).read_bytes()).hexdigest()==attack[hkey]
    exact &= attack['drawing_jobs']==[255,255] and attack['terrain_0544']==1 and attack['top_bg_tile_count_with_exact_chr_masks']==640
    check('attack_background_original_core_and_hashes',exact,{'terrain':attack['terrain_0544']})
    pixels=subprocess.run(['python3',str(Path(__file__).resolve()),str(a.rom),'--out',str(a.out),'--images-only'],text=True,capture_output=True)
    if pixels.returncode:failures.append({'group':'independent_image_pixel_verifier','details':pixels.stderr[-3000:]})
    else:counts.update(json.loads(pixels.stdout))
    for low,high in [(2,3),(3,0),(88,3),(255,0)]:
        troops=low|((high&3)<<8);cache=troops//100
        ai=model.ai_movement_quote(1,0,low,20,data=data);player=model.player_movement_quote(1,0,cache,20,data=data)
        examples.append({'byte8':low,'byte9':high,'troops_low10':troops,'player_cache':cache,'ai_cost':ai['cost'],'player_cost':player['cost']})
    oracle_groups=['ai_class1_exhaustive_low_byte','ai_class1_all_packed_flags_and_high_bytes','ai_other_terrain_selector_boundaries','player_class1_full_cache_domain','player_other_terrain_cache_boundaries','all335_class1_player_and_ai_lookups','complete_player_terrain_gate_routines','all335_class1_water_skip_and_inferno_prefix']
    oracle_count=sum(counts[k]for k in oracle_groups)
    result={'rom_sha256':model.ROM_SHA256,'status':'passed'if not failures else'failed','case_count':sum(counts.values()),'failed_count':len(failures),
            'rom_oracle_case_count':oracle_count,'artifact_case_count':sum(counts.values())-oracle_count,
            'complete_core_fixture_count':4,'formal_name_confirmed':False,
            'counts':dict(counts),'failures':failures,'selector_disagreement_examples':examples,'formal_name':None,
            'scope':'Independent readable quote functions versus original6502 A78C/A7E7; all335 original class1 lookups; four complete terrain gates; water effect no-op and inferno effect prefix; real core BG/CHR/OAM artifact integrity.',
            'limitations':['Quotes compare A/X/Y and NZVC; pointer scratch, other CPU flags and bank side effects are outside the quote model.','Does not reproduce full tactical effects or ordinary attack renderer.','Inferno oracle stops at B55C before damage and verifies only terrain acceptance.','Core screenshots are controlled RAM fixtures, not natural campaign reachability.','No formal class1 name is inferred from colors or mechanics.']}
    (a.out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'case_count':result['case_count'],'failed_count':len(failures),'counts':dict(counts)},ensure_ascii=False))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
