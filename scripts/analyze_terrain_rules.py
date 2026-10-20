#!/usr/bin/env python3
"""All30 battle maps, event-coordinate semantics and native menu glyph evidence."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,argparse,json,csv,hashlib
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from source.recovered import terrain_rules as rules
sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import OPS,SIZES,instruction

def analyze_service(rom,out):
    """Single proven10-entry C0BE inline table; recurse only service-local calls."""
    base=16+9*8192-0xc000;start=0xc0c1;end=0xc0d5
    targets=[int.from_bytes(rom[base+start+2*i:base+start+2*i+2],'little')for i in range(10)]
    assert min(targets)==end and start+20==end
    branches={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'};found={};occupied={};pending=[0xc0bb,*targets];hooks={}
    modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp','rel':'rel'}
    while pending:
        pc=pending.pop()
        while 0xc0bb<=pc<0xc983 and pc not in found:
            off=base+pc;op,mode=OPS[rom[off]];size=SIZES[mode];assert op!='?',hex(pc)
            assert all(k not in occupied for k in range(pc,pc+size)),('instruction overlap',hex(pc))
            for k in range(pc,pc+size):occupied[k]=pc
            operand=int.from_bytes(rom[off+1:off+size],'little');nxt=pc+size
            _,asm=instruction(rom,off,pc)
            if op in branches:operand=(nxt+(operand if operand<128 else operand-256))&65535
            item={'pc':pc,'bank':9,'file':off,'op':op,'mode':modes.get(mode,mode),'operand':operand,'next_pc':nxt,'raw_hex':rom[off:off+size].hex(' ').upper(),'assembly':asm}
            if pc==0xc0be:
                assert op=='JSR'and operand==0xeade;item.update(op='DISPATCH',targets=targets);pending.extend(targets)
            elif op=='JSR'and operand==0xee07:
                item.update(op='FARCALL',inline_target=int.from_bytes(rom[off+3:off+5],'little'),next_pc=pc+5,hook='explicit banked dependency')
                hooks.setdefault('EE07',[]).append({'pc':pc,'inline_target':item['inline_target']})
            elif op in('JSR','JMP'):
                if 0xc0bb<=operand<0xc983:pending.append(operand)
                else:item['hook']=f'cpu_{operand:04X}';hooks.setdefault(f'{operand:04X}',[]).append({'pc':pc,'tail':op=='JMP'})
            elif op in branches:pending.append(operand)
            found[pc]=item
            if item['op']=='DISPATCH'or op in('JMP','RTS','RTI','BRK'):break
            pc=item['next_pc']
    names=['米屋买卖选项与报价','购买粮食数量输入/执行','出售粮食数量输入/执行','病院初始体力检查','50金治疗确认与执行','武器屋装备组选择','绘制4项装备/价格','装备购买限制与写回','消息确认后返回战斗','进入村落确认与服务路由']
    handlers=[]
    for index,entry in enumerate(targets):
        seen=set();todo=[entry]
        while todo:
            pc=todo.pop()
            if pc in seen or pc not in found:continue
            seen.add(pc);v=found[pc]
            if v['op']=='JMP':
                if 'hook'not in v:todo.append(v['operand'])
                continue
            if v['op']in('RTS','RTI','BRK'):continue
            todo.append(v['next_pc'])
            if v['op']in branches or v['op']=='JSR'and'hook'not in v:todo.append(v['operand'])
        nodes=[found[k]for k in sorted(seen)]
        writes=[v for v in nodes if v['op']in('STA','STX','STY','INC','DEC')]
        handlers.append({'substate':index,'entry':entry,'bank':9,'file':base+entry,'name':names[index],'instruction_count':len(nodes),'state_writes':[v for v in writes if v['operand']in(0x500,0x501)],'field_writes':writes,'hooks':sorted(set(v['hook']for v in nodes if'hook'in v)),'reachable':sorted(seen)})
    report={'rom_sha256':rules.ROM_SHA256,'entry':0xc0bb,'physical_pair':[8,9],'parent_battle_state':9,'substate_address':0x501,'substate_count':10,'table_cpu':start,'table_file':base+start,'table_end_exclusive':end,'table_raw_hex':rom[base+start:base+end].hex(' ').upper(),'extent_evidence':'10 words end exactly at first handlerC0D5','handlers':handlers,'instruction_count':len(found),'code_bytes':len(occupied),'hooks':hooks,'scope':'10 true bank9 substates behind the existing bank13 C1FC service bridge; separate from previous pair12/13 local entry counts.'}
    (out/'service-controller.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'service-program.json').write_text(json.dumps({'rom_sha256':rules.ROM_SHA256,'instructions':[found[k]for k in sorted(found)]},ensure_ascii=False,indent=2)+'\n')
    lines=['; Complete reachable village-service control, physicalbank9 C000; inline pointer table excluded from opcodes.',f'; C0BB loads0501; C0BE JSR EADE; table{start:04X}..{end-1:04X}']
    for i,t in enumerate(targets):lines.append(f'{base+start+2*i:06X} b09:${start+2*i:04X} .word ${t:04X} ; sub{i} {names[i]}')
    for k in sorted(found):
        v=found[k];tail=f' ; inline word ${v["inline_target"]:04X}'if v['op']=='FARCALL'else''
        lines.append(f'{v["file"]:06X} b09:${k:04X} {v["raw_hex"]:<12} {v["assembly"]}{tail}')
    (out/'service-controller.asm').write_text('\n'.join(lines)+'\n')
    return report

def state_chunks(blob,start,end):
    found={};p=start
    while p+8<=end:
        tag=blob[p:p+4];size=int.from_bytes(blob[p+4:p+8],'little')
        if p+8+size>end:raise ValueError('Malformed state chunk')
        found[tag]=blob[p+8:p+8+size];p+=8+size
    return found

def native_ppu(path):
    blob=path.read_bytes();assert blob[:4]==b'NST\x1a'
    top=state_chunks(blob,8,8+int.from_bytes(blob[4:8],'little'))
    ppu=state_chunks(top[b'PPU\0'],0,len(top[b'PPU\0']))
    assert ppu[b'NMT\0'][0]==0,'Only uncompressed native-core states are used here'
    img=state_chunks(top[b'IMG\0'],0,len(top[b'IMG\0']))
    mpr=state_chunks(img[b'MPR\0'],0,len(img[b'MPR\0']))
    chr_state=state_chunks(mpr[b'CHR\0'],0,len(mpr[b'CHR\0']))
    banks=chr_state[b'BNK\0'];assert len(banks)==24
    # Source-index0 + little-endian physical1KiB bank index. This interpretation
    # is independently checked below against actual screenshot pixel masks.
    assert all(banks[3*i]==0 for i in range(8))
    pages=[int.from_bytes(banks[3*i+1:3*i+3],'little')for i in range(8)]
    bg=pages[4:8]if ppu[b'REG\0'][0]&16 else pages[:4]
    return ppu[b'NMT\0'][1:],bg,{'state_sha256':hashlib.sha256(blob).hexdigest(),'chr_bank_payload_hex':banks.hex(' ').upper(),'ppu_control':ppu[b'REG\0'][0]}

def chr_tile(rom,page,code):
    raw=rom[0x40010+page*1024+(code&63)*16:0x40010+page*1024+(code&63)*16+16]
    im=Image.new('L',(8,8),255)
    for y in range(8):
        for x in range(8):
            value=((raw[y]>>(7-x))&1)|(((raw[y+8]>>(7-x))&1)<<1)
            # This native menu palette uses pixel-index0 as black ink and
            # nonzero indices as its pink paper. Pixel equality checks below
            # establish the polarity rather than guessing it from the glyph.
            im.putpixel((x,y),0 if value==0 else 255)
    return im,raw

def render_core_labels(rom_path,out):
    """Reproduce explicitly injected original-renderer fixtures, never natural play."""
    import ctypes as C
    from nes_runtime import Runtime
    dest=out/'core-labels';runtime=Runtime(rom_path,dest);completion=[]
    battle=ROOT/'analysis/runtime/phase3/battle-tactics-true.state'
    duel=ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-state-16.state'
    jobs=[(battle,f'message-{msg:02x}',{0x500:0,0x501:3,0x50a:3,0x50b:2,0x540:131,0x541:0,0x310:job,0x311:msg,**{0x42c+i:v for i,v in enumerate([131,47,30,255]+[255]*16)},**{0x550+i:0 for i in range(20)}})for msg,job in[(0xa7,5),(0xa8,2),(0xad,2),(0xb1,2),(0xb2,2),(0xdc,5),(0xd7,2),(0xdd,2),(0xde,2),(0xdf,5),(0xe5,2)]]
    jobs.append((duel,'duel-tactics-submenu',{0x4a8:1,0x4a9:5,0x4bf:4,0x4b5:0,0x4b6:0,0x310:0,0x311:0x2c}))
    try:
        for state,label,changes in jobs:
            runtime.load_state(state);runtime.events=[];runtime.frames=0;ram=bytearray(runtime.memory(2))
            changes.update({0x7c:0,0x7e:0,0x300:0,0x304:255,0x312:255,0x313:255,0x424:0,0x425:0})
            log=[]
            for address,value in changes.items():log.append({'address':address,'old':ram[address],'new':value});ram[address]=value
            C.memmove(runtime.core.retro_get_memory_data(2),bytes(ram),len(ram));runtime.run(240);runtime.snapshot(label)
            final=runtime.memory(2)
            completion.append({'label':label,'frame':runtime.frames,'message_job_0300':final[0x300],'secondary_job_0304':final[0x304],'completed':final[0x300]==255 and final[0x304]==255})
            (dest/(label+'-fixture.json')).write_text(json.dumps({'rom_modified':False,'natural_gameplay':False,'parent_state':str(state.relative_to(ROOT)),'parent_state_sha256':hashlib.sha256(state.read_bytes()).hexdigest(),'runtime_ram_changes':log,'capture_frames':240,'purpose':'Render original menu/message with explicitly initialized control and name-list inputs'},indent=2)+'\n')
    finally:runtime.close()
    (dest/'message-completion-checks.json').write_text(json.dumps({'rom_modified':False,'natural_gameplay':False,'checks':completion},indent=2)+'\n')
    files=[dest/f'message-{m:02x}.png'for m in[0xa7,0xa8,0xad,0xb1,0xb2,0xdc,0xd7,0xdd,0xde,0xdf,0xe5]]
    atlas=Image.new('RGB',(1024,300),(240,240,240));draw=ImageDraw.Draw(atlas)
    for i,path in enumerate(files):
        x=i%4*256;y=i//4*100;draw.text((x,y),path.stem,fill=(0,0,0));atlas.paste(Image.open(path).crop((0,160,256,240)),(x,y+20))
    atlas.save(dest/'message-atlas.png')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase4/terrain');p.add_argument('--render-core-labels',action='store_true');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==rules.ROM_SHA256;a.out.mkdir(parents=True,exist_ok=True)
    if a.render_core_labels:render_core_labels(a.rom,a.out)
    service=analyze_service(rom,a.out)
    def evidence(bank,cpu,length,note):
        base=0xe000 if bank==31 else 0xc000 if bank in[9,13,15,24]else 0xa000 if bank in[8,12,23]else 0x8000
        off=16+bank*8192+cpu-base
        return {'bank':bank,'cpu':cpu,'file':off,'hex':rom[off:off+length].hex(' ').upper(),'note':note}
    rows=[];cities=[];special=[];event_points=[];total=Counter();all_domain=Counter();nonplay=Counter()
    for city in range(30):
        chunks=rules.city_chunks(rom,city);counts=Counter()
        for y in range(32):
            for x in range(32):
                cell=rules.map_cell(rom,chunks,x,y);all_domain[cell['raw_class']]+=1
                if cell['legal_cell']:
                    counts[cell['raw_class']]+=1;total[cell['raw_class']]+=1
                    rows.append({'city':city,**cell})
                    if cell['raw_class']>=6:special.append({'city':city,**cell})
                else:nonplay[cell['raw_class']]+=1
        points=[]
        for index,(x,y)in enumerate(rules.service_coordinates(rom,city)):
            cell=rules.map_cell(rom,chunks,x,y)if(x,y)!=(255,255)else None
            point={'city':city,'service_index':index,'service_name':rules.SERVICE_NAMES[index],'coordinate':[x,y],'active':(x,y)!=(255,255),'coordinate_file':rules.SERVICE_COORDINATES_OFFSET+6*city+2*index,'cell':cell}
            points.append(point);event_points.append(point)
        cities.append({'city':city,'chunks':chunks,'legal_cell_count':sum(counts.values()),'class_counts':dict(counts),'services':points})
    active=[p for p in event_points if p['active']]
    matched=[p for p in active if p['cell']['raw_class']>=6]
    mismatch=[p for p in active if p['cell']['raw_class']<6]
    unlinked=[p for p in special if not any(e['active']and e['city']==p['city']and e['coordinate']==[p['x'],p['y']]for e in event_points)]
    classification=[{'tile':t,'class':rom[0x1175b+t],'metatile_hex':rules.metatile(rom,t).hex(' ').upper(),'metatile_file':rules.METATILE_TABLE_OFFSET+4*t}for t in range(128)]
    glyphs=[];duel_state=ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-state-16.state'
    nmt,bg,state_meta=native_ppu(duel_state);native=Image.open(duel_state.with_suffix('.png')).convert('RGB')
    labels=['けんせい','たいきゃく','こうげき','こうさん','せんじゅつ','データ','すてみのこうげき']
    lengths=[4,5,4,4,5,3,8];atlas=Image.new('RGB',(512,7*72),(255,255,255));draw=ImageDraw.Draw(atlas)
    for i,(name,width)in enumerate(zip(labels,lengths)):
        row=21+2*(i//2);col=18 if i%2==0 else 25
        codes=list(nmt[32*row+col:32*row+col+width]);above=list(nmt[32*(row-1)+col:32*(row-1)+col+width])
        tiles=[]
        for j,code in enumerate(codes):
            im,raw=chr_tile(rom,bg[code//64],code)
            actual=native.crop(((col+j)*8,row*8-2,(col+j+1)*8,row*8+6))
            mask=[pix==(0,0,0)for pix in actual.getdata()]
            assert mask==[pix==0 for pix in im.getdata()],(i,code,bg,'CHR/native pixel mismatch')
            tiles.append({'ppu_code':code,'chr_1k_bank':bg[code//64],'chr_file':0x40010+bg[code//64]*1024+(code&63)*16,'raw_hex':raw.hex(' ').upper()})
        crop=native.crop((col*8,(row-1)*8-2,(col+width)*8,(row+1)*8-2)).resize((width*32,64),Image.Resampling.NEAREST)
        filename=f'duel-menu-{i}.png';crop.save(a.out/filename);draw.text((0,i*72),f'04BF={i}; NMT row{row} col{col}',fill=(0,0,0));atlas.paste(crop,(230,i*72))
        glyphs.append({'menu_index':i,'action_04bf':i,'name':name,'status':'confirmed native rendered glyphs, original CHR/native pixel equality, identity selection table','nmt_row':row,'nmt_column':col,'native_pixel_translation':[0,-2],'codes':codes,'accent_codes_above':above,'tiles':tiles,'image':filename})
    atlas.save(a.out/'duel-menu-atlas.png')
    subglyphs=[];substate=a.out/'core-labels/duel-tactics-submenu.state'
    if substate.exists():
        snmt,sbg,smeta=native_ppu(substate);simage=Image.open(substate.with_suffix('.png')).convert('RGB')
        for index,name,col,width in[(7,'せっとく',18,4),(8,'ばとう',25,3)]:
            row=23;codes=list(snmt[row*32+col:row*32+col+width]);tiles=[]
            for j,code in enumerate(codes):
                im,raw=chr_tile(rom,sbg[code//64],code);actual=simage.crop(((col+j)*8,row*8-2,(col+j+1)*8,row*8+6))
                assert[pix==(0,0,0)for pix in actual.getdata()]==[pix==0 for pix in im.getdata()],(index,'submenuCHR/native mismatch')
                tiles.append({'ppu_code':code,'chr_1k_bank':sbg[code//64],'chr_file':0x40010+sbg[code//64]*1024+(code&63)*16,'raw_hex':raw.hex(' ').upper()})
            filename=f'duel-menu-{index}.png';simage.crop((col*8,(row-1)*8-2,(col+width)*8,(row+1)*8-2)).resize((width*32,64),Image.Resampling.NEAREST).save(a.out/filename)
            subglyphs.append({'menu_index':index-7,'action_04bf':index,'name':name,'status':'confirmed original renderer glyphs, CHR/native pixel equality, B59E selection+7 linkage','nmt_row':row,'nmt_column':col,'codes':codes,'accent_codes_above':list(snmt[(row-1)*32+col:(row-1)*32+col+width]),'native_pixel_translation':[0,-2],'tiles':tiles,'image':filename,'native_state_metadata':smeta})
    if subglyphs:
        expanded=Image.new('RGB',(512,9*72),(255,255,255));expanded.paste(atlas,(0,0));edraw=ImageDraw.Draw(expanded)
        for item in subglyphs:
            index=item['action_04bf'];edraw.text((0,index*72),f'04BF={index}; submenu index={index-7}',fill=(0,0,0));expanded.paste(Image.open(a.out/item['image']),(230,index*72))
        expanded.save(a.out/'duel-menu-atlas.png')
    core_labels=[{'message_id':m,'job':job,'text':text,'source_image':f'core-labels/message-{m:02x}.png','fixture_log':f'core-labels/message-{m:02x}-fixture.json','status':'confirmed original core-rendered Japanese text; fixture is synthetic'}for m,job,text in[(0xa7,5,'ムラにはいりますか'),(0xa8,2,'ここはコメヤです なにをしますか'),(0xad,2,'ここはブキヤです なにをかいますか'),(0xb1,2,'ここはビョウインです'),(0xb2,2,'チリョウにキン50かかります よろしいですか'),(0xdc,5,'どのクニにたいきゃくしますか'),(0xdd,2,'たいきゃくするブショウをえらんでください'),(0xdf,5,'このクニにはいるブショウが10にんをこえました ほかのクニへどうぞ')]]
    payload={'rom_sha256':rules.ROM_SHA256,'city_count':30,'chunk_count':120,'legal_cell_count':len(rows),'legal_class_counts':dict(total),'whole_32x32_lookup_class_counts':dict(all_domain),'attribute_and_outside_class_counts':dict(nonplay),'cities':cities,'classifier':classification,'special_marker_cells':special,'service_points':event_points,'service_point_count':len(active),'service_points_matching_special_markers':len(matched),'service_points_on_other_ground':mismatch,'unlinked_special_marker_cells':unlinked,'metatile_equality':{'ordinary_tile':57,'base_tile':97,'event_marker_tiles':[121,122,123],'shared_bg_quad_hex':rules.metatile(rom,57).hex(' ').upper(),'note':'BG quad equality proven by original F477 data; visible building graphics require separate original renderer sprite overlay.'},'evidence':[evidence(13,0xdb46,88,'Player raw class lookup also maps>=6 to2'),evidence(8,0xb6e5,10,'AI raw class lookup maps>=6 to2'),evidence(31,0xf477+0x79*4,12,'All3 raw marker metatiles share the ordinary-ground BG quad'),evidence(12,0xa4d6,71,'XY service scan;0470 index; literal0500=9 and0501=9 writes; messageA7'),evidence(9,0xc80b,57,'Service index0 trade,1equipment,2healing substate selection'),evidence(9,0xc42c,124,'50gold healing with35..45 amount and initialHP ceiling'),evidence(9,0xc6d5,84,'Equipment ID>=24 updates high3 armor bits; low5 weapon otherwise'),evidence(9,0xc73b,116,'4 rare-equipment predicates and global6FE1 allocation bits'),evidence(23,0xb43c,11,'Menu0012 indexes identity action table and writes04BF'),evidence(23,0xb461,24,'Identity action table and7 original cursor pairs'),evidence(23,0xb59e,9,'Submenu0012 plus7 written to04BF')],'duel_main_menu':glyphs,'duel_tactics_submenu':subglyphs,'native_core_labels':core_labels,'duel_state_metadata':state_meta,'duel_bg_chr_1k_banks':bg,'service_controller':{'json':'service-controller.json','program':'service-program.json','assembly':'service-controller.asm','substates':service['substate_count'],'instructions':service['instruction_count']},'limitations':['Formal terrainclass1 name remains unidentified; exact color/appearance is not promoted to an official name.','Raw marker6/7/8 and city service category0/1/2 are different encodings; explicit coordinate mismatches are retained.','Invalid/attribute/unused map locations are not counted as playable cells.','The native duel state is an explicitly injected complete-core fixture, not natural campaign reachability.']}
    (a.out/'evidence.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    with(a.out/'all-legal-map-cells.csv').open('w',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({'legal_cells':len(rows),'classes':dict(total),'service_points':len(active),'matched_markers':len(matched),'unlinked_markers':len(unlinked),'duel_labels':labels},ensure_ascii=False))

if __name__=='__main__':main()
