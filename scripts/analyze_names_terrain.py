#!/usr/bin/env python3
"""ROM-backed tactic menu names, terrain grids and remaining-field evidence."""
from pathlib import Path
import sys,json,argparse,hashlib,csv
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source/recovered'))
import game_enums as enums

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/names_terrain');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==enums.ROM_SHA256
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    def ev(bank,cpu,size,description):
        base=0xe000 if bank==31 else (0xa000 if bank in[8,10,12,14,23,25,27,29]else 0xc000)
        off=16+bank*8192+cpu-base
        return dict(bank=bank,cpu_address=f'0x{cpu:04X}',rom_offset=f'0x{off:06X}',raw_hex=rom[off:off+size].hex(' ').upper(),description=description)
    def tile(code):
        bank=enums.TACTIC_NAME_BG_CHR_PAGES[code//64];off=0x40010+bank*1024+(code&63)*16;raw=rom[off:off+16]
        im=Image.new('L',(8,8));pix=im.load();palette=[255,170,85,0]
        for y in range(8):
            for x in range(8):pix[x,y]=palette[((raw[y]>>(7-x))&1)|(((raw[y+8]>>(7-x))&1)<<1)]
        return im
    tactics=[];atlas=Image.new('L',(640,800),240);draw=ImageDraw.Draw(atlas)
    for i,name in enumerate(enums.TACTIC_NAMES):
        po=0x18ca1+2*i;cpu=int.from_bytes(rom[po:po+2],'little');off=0x18010+cpu-0xa000
        topn=rom[off];top=list(rom[off+1:off+1+topn]);second=off+1+topn;bottomn=rom[second];bottom=list(rom[second+1:second+1+bottomn])
        im=Image.new('L',(max(topn,bottomn)*8,16),255)
        for y,row in enumerate([top,bottom]):
            for x,t in enumerate(row):im.paste(tile(t),(x*8,y*8))
        file=f'tactic-{i:02d}.png';im.resize((im.width*4,64),Image.Resampling.NEAREST).save(out/file)
        x=(i//8)*320;y=(i%8)*100;draw.text((x,y),f'ID{i:02d} ${cpu:04X}',fill=0);atlas.paste(Image.open(out/file),(x,y+22))
        disp=int.from_bytes(rom[0x19052+2*i:0x19054+2*i],'little')
        tactics.append({'action_id':i,'name':name,'name_status':'confirmed original ROM glyphs and selector linkage','action_cost':rom[0x18bd9+i],'name_pointer_rom_offset':f'0x{po:06X}','name_cpu_address':f'0x{cpu:04X}','name_rom_offset':f'0x{off:06X}','raw_hex':rom[off:second+1+bottomn].hex(' ').upper(),'top_tiles':top,'bottom_tiles':bottom,'image':file,'dispatch_cpu_address':f'0x{disp:04X}'})
    atlas.save(out/'tactics16.png')
    for start in [0,8]:atlas.crop((start//8*320,0,start//8*320+320,800)).save(out/f'tactics-{start:02d}-{start+7:02d}.png')
    menu_states=list(rom[0x181bc:0x181c1]);menu_names=['移動','攻撃','計略','待機','退却']
    menu=[]
    for i,(name,state) in enumerate(zip(menu_names,menu_states)):
        y,x=rom[0x181ab+2*i:0x181ad+2*i]
        menu.append({'selection_index':i,'name':name,'state_0500':state,'cursor_pixel_y':y,'cursor_pixel_x':x,'status':'confirmed cursor coordinates linked to native unit-menu screenshot','state_rom_offset':f'0x{0x181bc+i:06X}','cursor_rom_offset':f'0x{0x181ab+2*i:06X}'})
    # Original core-rendered pixel crops; no assumed metatile graphic dictionary.
    scenes=[('attack-intro-4',ROOT/'analysis/runtime/phase3/attack-intro-4',False),('battle-camera-right2',ROOT/'analysis/runtime/phase3/battle-camera-right2',False),('synthetic-city5-upper',ROOT/'analysis/runtime/phase3/synthetic-city5/upper-map',True)]
    grids=[];paired=[];scene_metadata=[]
    for label,prefix,synthetic in scenes:
        ramfile=Path(str(prefix)+'-ram.bin');png=Path(str(prefix)+'.png')
        if not ramfile.exists() or not png.exists():continue
        ram=ramfile.read_bytes();chunks=list(ram[0xaa:0xae]);camx=int.from_bytes(ram[0x8e:0x90],'little');camy=int.from_bytes(ram[0x90:0x92],'little')
        cells=[enums.map_terrain(rom,chunks,x,y) for y in range(32) for x in range(32)]
        gridfile=f'{label}-terrain-grid.json';(out/gridfile).write_text(json.dumps({'label':label,'synthetic_ram_fixture':synthetic,'chunks':chunks,'camera_pixels':[camx,camy],'cells':cells},ensure_ascii=False,indent=2)+'\n')
        grids.append({'label':label,'json':gridfile,'chunks':chunks,'synthetic_ram_fixture':synthetic,'camera_pixels':[camx,camy]})
        image=Image.open(png).convert('RGB');overlay=image.copy();odraw=ImageDraw.Draw(overlay)
        local=[]
        for cell in cells:
            if not cell['valid_battle_cell']:continue
            sx=cell['physical_pixel_x']-camx;sy=cell['physical_pixel_y']-camy
            if not(0<=sx<=240 and 0<=sy<=144):continue
            c=cell['raw_class'];color={0:'#FFFFFF',1:'#FF00FF',2:'#111111',3:'#FFFFFF',4:'#FFFFFF',5:'#FFFF00'}.get(c,'#FF00FF')
            odraw.rectangle((sx,sy,sx+15,sy+15),outline=color);odraw.text((sx+3,sy+3),str(c),fill=color)
            local.append((cell,sx,sy))
        overlay.resize((768,720),Image.Resampling.NEAREST).save(out/f'{label}-class-overlay.png')
        # Retain a few labelled native cell patches of every observed class.
        count={}
        for cell,sx,sy in local:
            cl=cell['raw_class']
            if count.get(cl,0)>=3:continue
            count[cl]=count.get(cl,0)+1
            imgname=f'{label}-class{cl}-{count[cl]}.png'
            image.crop((sx,sy,sx+16,sy+16)).resize((128,128),Image.Resampling.NEAREST).save(out/imgname)
            paired.append({'scene':label,'synthetic_ram_fixture':synthetic,'image':imgname,'source_image':str(png.relative_to(ROOT)),'screen_pixel_xy':[sx,sy],'logical_xy':[cell['x'],cell['y']],'tile_id':cell['tile_id'],'raw_class':cl,'tile_rom_offset':f'0x{cell["tile_rom_offset"]:06X}'})
        scene_metadata.append({'scene':label,'source_image':str(png.relative_to(ROOT)),'ram_file':str(ramfile.relative_to(ROOT)),'synthetic_ram_fixture':synthetic,'overlay':f'{label}-class-overlay.png','native_class_counts':count})
    with (out/'native-terrain-patches.csv').open('w',newline='') as f:
        keys=['scene','synthetic_ram_fixture','image','source_image','screen_pixel_xy','logical_xy','tile_id','raw_class','tile_rom_offset'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(paired)
    classification=list(rom[0x1175b:0x117db]);first=list(rom[0x18833:0x1884f]);second=list(rom[0x1884f:0x1886b])
    initial=rom[0x22010:0x22b2c]
    counts={str(i):sum(((initial[j+11]>>2)&3)==i for j in range(0,len(initial),12)) for i in range(4)}
    remaining=[
      {'field':'byte5','status':'strong inference city-location semantics; exact assignment verified','notes':['Set when state low2 is cleared to0 by city-roster removal/wandering routines.','Do not treat it as permanent owner; city roster, not byte5, represents normal affiliation.'],'evidence':[ev(26,0xc099,15,'Clear low2 and write city $040E into byte5'),ev(25,0xba14,65,'Status0 search rejects city and adjacent-city locations')]},
      {'field':'byte9 bits2..7','status':'unresolved semantic name; mechanical treatment confirmed','initial_nonzero_record_count':sum(bool(initial[j+9]&0xfc) for j in range(0,len(initial),12)),'notes':['UI and primary battle troop count mask the high6 bits out.','The troop-loss writer replaces byte9 with the remaining high2 bits, clearing them even if requested loss is0.','AI candidate sorting compares byte9 before byte8 without masking; action11 treats any nonzero byte9 as its troop predicate. These consumers observe the raw bits without proving a separate flag meaning.','No confirmed normal initialization uses nonzero high6 bits.'],'evidence':[ev(29,0xbbf4,31,'Troop UI uses high byte AND03'),ev(12,0xb68b,54,'Troop loss reads high byte AND03 and overwrites byte9 with remaining high byte'),ev(8,0xaec6,42,'Candidate sorting compares unmasked high/low bytes'),ev(8,0xaddd,15,'Tactic11 troop gate accepts any nonzero raw byte9')]},
      {'field':'byte11 bits0..1','status':'confirmed state encoding; path-dependent permanence unresolved','values':{str(k):{'label':enums.OfficerStatus(k).name,'confidence':v[0],'note':v[1]} for k,v in enums.OFFICER_STATUS_CONFIDENCE.items()},'notes':['Single-duel zero HP results0515/0517=2 are battle result codes, not officer low2 status codes. Duel bank24 D060 only copies temporary HP into record byte0.','Postbattle main13/sub1 clears low2 to0 and writes byte5 city050E for its selected roster; its ruler-leader branch instead sets3. The selector builds IDs from battlefield slots/captive lists without directly checking officer low2.','Existence of the postbattle clear operation does not prove that status3 is revivable; earlier active-slot removal and captive-list membership must be distinguished.','Complete Nestopia injected duel fixture also retained low2 while HP reached0; it is explicitly synthetic and does not establish every campaign death path.','Do not globally equate removal3 with permanent death; battle post-result and city roster paths must be distinguished.'],'evidence':[ev(25,0xaf00,83,'Status1 year gate, roster insertion and status2 transition'),ev(26,0xc099,15,'Roster removal to0 with location'),ev(12,0xb5d8,59,'Health0 sets low2=3; following helpers remove active battlefield unit'),ev(25,0xbdc6,41,'Set removal3, erase city roster entry, then compact roster'),ev(24,0xd060,20,'Duel HP writeback; no packed status write in this helper'),ev(13,0xcdc5,40,'Postbattle selected nonleader: ANDFC status, store city050E; leader alternate OR03'),ev(13,0xd101,105,'Construct postbattle list from side-bit battlefield slots plus captive arrays; appendFE sentinel')]},
      {'field':'byte11 bits2..3','status':'confirmed terrain-dependent movement affinity','glyphs':enums.TERRAIN_AFFINITY_GLYPHS,'initial_record_counts':counts,'code3':{'name':None,'status':'undefined/unverified encoding','observed_behavior':'Fourth column is0 in every validated movement row0..6 of both tables; UI top-glyph selector overruns its3-entry data table and reads A0 0B (following LDY opcode).','oracle_cases_zero_cost':2043,'oracle_cases_top_glyph_overrun':64},'evidence':[ev(12,0xa7e7,60,'Index terrain*4|affinity, choose table using cached hundred-troop selector_byte RAM063C[slot]>=6, subtract action-point cost'),ev(13,0xdb03,67,'Refresh063C[slot] from officer troops_low10 divided by100; empty officerIDFF writesFF'),ev(25,0xb630,31,'Three original glyph selectors平山水, followed by next function LDY opcode')]},
    ]
    payload={'rom_sha256':enums.ROM_SHA256,'tactics':tactics,'tactic_link_evidence':[ev(12,0xabd9,119,'0580[row] selects original16-name pointer table and builds VRAM packet'),ev(12,0xa951,8,'Same0580[row] written to0543'),ev(12,0xb03a,40,'0543&0F chooses16 effect entries'),ev(12,0xa8e8,16,'Original menu CHR page setup')],'unit_menu':menu,'terrain_classifier':{'raw_classification_table_cpu':'0xB74B','raw_classification_table_rom_offset':'0x01175B','values':classification,'labels':{str(k):{'name':v[0],'status':v[1]} for k,v in enums.TERRAIN_LABELS.items()},'lookup_evidence':ev(8,0xb6e5,102,'Quadrant/chunk pointer/bank/tile/class lookup; raw>=6 folds to2')},'terrain_movement':{'first_table':first,'second_table':second,'first_selector':'RAM063C[slot]>=6; refreshed from troops_low10//100 (empty slotFF)','class_row_count':7,'affinity_column_count':4,'original_first_rom_offset':'0x018833','original_second_rom_offset':'0x01884F'},'terrain_grids':grids,'native_patches':paired,'runtime_scenes':scene_metadata,'remaining_fields':remaining,'limitations':['Original-pixel terrain descriptions are distinguished from official-language labels; class1 has no verified formal name.','No inferred metatile graphic dictionary is used as confirmation evidence.','Full32x32 grid records raw lookup provenance, but attribute/unused rows are explicitly not playable.','Synthetic city5 fixture uses original ROM renderer with explicitly changed runtime RAM; it is not a natural campaign screenshot.']}
    (out/'evidence.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f'Wrote16 linked tactic names, terrain provenance grids and {len(paired)} native-pixel patches to {out}')

if __name__=='__main__':main()
