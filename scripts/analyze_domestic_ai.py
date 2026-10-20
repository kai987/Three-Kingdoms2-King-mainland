#!/usr/bin/env python3
"""Recover bounded ruler-AI control and city UI field references, read-only ROM."""
from pathlib import Path
import argparse,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import OPS,SIZES,instruction
from source.recovered.domestic_ai import ROM_SHA256

BRANCHES={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}
MODES={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}
DOMESTIC_DISPATCH={0xA039:(0xA03C,3),0xA1BC:(0xA1BF,3)}
ROOTS={0xA00F:'君主AI入口',0xA042:'负标记/phase2提前返回',0xA043:'phase0战略权重初始化',0xA19C:'三路战略抽样',0xA240:'敌邻接城市目标扫描',
 0xA2D3:'外交计时禁止攻击条件',0xA3D6:'跨城武将补充选择',0xA481:'攻击将补兵到1000',
 0xA55C:'城际金调拨',0xA60C:'城际米调拨',0xA6C9:'出征人数需求',0xA74A:'出征金米费用',
 0xA79C:'出征队列与资源准备',0xB49C:'战略分支1',0xBEC7:'城市发展/武将装备选择',
 0xBEE6:'循环自方城市',0xC1A7:'城市byte11发展副作用',0xC1C0:'城市byte11人口副作用',
 0xC248:'最低忠且未处理武将',0xC2EB:'最低知且未处理武将',0xC3FF:'武器购买将选择',
 0xC451:'可购买下一装备查询',0xC50E:'君主所在城位置调整',0xC5B9:'登用/搜索预处理',
 0xC66F:'特定君主武将登用概率',0xC79A:'自方城市体力处理',0xC9A5:'首将选择',
 0xCC12:'金不足时卖米',0xD0E1:'敌邻接数',0xD105:'城市地址/资源cap',0xD12D:'扣预算继续循环',
 0xD152:'扣任务预算',0xD165:'嵌套预算1',0xD178:'嵌套预算2',0xD18D:'嵌套预算3',
 0xD1A4:'城市敌邻接列表',0xD249:'君主所在城查找',0xD304:'城市首FF武将数',
 0xD36F:'城金付款',0xD3A9:'城米付款',0xD4CB:'同方城市连通工作位图',0xD583:'工作位图共同覆盖查询'}

def locate(pc,pair=10):
    bank=pair+int(pc>=0xC000);base=0xC000 if pc>=0xC000 else 0xA000
    return bank,16+bank*8192+pc-base

def in_scope(pc):
    return 0xA000<=pc<0xD717 and not(0xCA19<=pc<0xCC12 or 0xCF3F<=pc<0xD03A)

def graph(rom):
    pending=list(ROOTS);found={};occupied={};hooks={};dispatch=[]
    while pending:
        pc=pending.pop()
        while in_scope(pc)and pc not in found:
            bank,off=locate(pc);op,mode=OPS[rom[off]];size=SIZES[mode]
            if op=='?':raise ValueError(f'Unrecognized/data opcode at{pc:04X}')
            if any(q in occupied for q in range(pc,pc+size)):raise ValueError(f'Instruction overlap at{pc:04X}')
            for q in range(pc,pc+size):occupied[q]=pc
            operand=int.from_bytes(rom[off+1:off+size],'little');nxt=pc+size
            if op in BRANCHES:operand=(nxt+(operand if operand<128 else operand-256))&65535
            _,asm=instruction(rom,off,pc)
            node={'pc':pc,'bank':bank,'file':off,'op':op,'mode':MODES.get(mode,mode),'operand':operand,'next_pc':nxt,'raw_hex':rom[off:off+size].hex(' ').upper(),'assembly':asm}
            if pc in DOMESTIC_DISPATCH:
                assert op=='JSR'and operand==0xD494
                table,count=DOMESTIC_DISPATCH[pc];toff=locate(table)[1]
                targets=[int.from_bytes(rom[toff+2*i:toff+2*i+2],'little')for i in range(count)]
                node.update(hook='independently recovered D494 inline dispatch',targets=targets)
                pending.extend(targets);dispatch.append({'call_pc':pc,'table':table,'file':toff,'count':count,'targets':targets,'raw_hex':rom[toff:toff+2*count].hex(' ').upper(),'boundary':'3words end at first following code instruction'})
            elif op=='JSR'and operand==0xEE07:
                node.update(op='FARCALL',inline_target=int.from_bytes(rom[off+3:off+5],'little'),next_pc=pc+5,hook='explicit banked dependency')
            elif op in('JSR','JMP'):
                if mode=='ind':raise ValueError(f'Unresolved indirect jump{pc:04X}')
                if in_scope(operand):pending.append(operand)
                else:node['hook']=f'explicit_cpu_{operand:04X}'
            elif op in BRANCHES:pending.append(operand)
            if 'hook'in node:hooks.setdefault(f'{operand:04X}',[]).append(pc)
            found[pc]=node
            if pc in DOMESTIC_DISPATCH or op in('JMP','RTS','RTI','BRK'):break
            pc=node['next_pc']
    return found,dispatch,hooks

def ui_fields(rom):
    records=[]
    for start,end,mode in[(0xb3e5,0xb4c1,2),(0xb4c1,0xb59c,3),(0xb59c,0xb67b,4),(0xb305,0xb3e5,1)]:
        position=0;pc=start
        while pc<end:
            off=16+29*8192+pc-0xa000;code=rom[off]
            if code>=240:
                digits,field=rom[off+1:off+3]
                records.append({'template_cpu':start,'bank':29,'ui_mode':mode,'cpu':pc,'file':off,'raw_hex':rom[off:off+3].hex(' ').upper(),'format':code,'digits':digits,'city_byte_offset':field,'row':position//14,'column':position%14})
                pc+=3;position+=digits
            else:pc+=1;position+=1
        assert position==224
    return records

def resource16_glyphs(rom,out):
    from PIL import Image
    from analyze_terrain_rules import native_ppu,chr_tile
    result=[]
    for label,path,coords,pages in[
        ('resource16_original_icon',ROOT/'analysis/phase5/runtime/city-info/menu-2.state',[(11,3),(11,4),(12,3),(12,4)],[5,5,5,5]),
        ('message34_takara_wo',out/'resource16-fixtures/message-34.state',[(22,10),(22,11),(22,12),(22,13)],[8,8,8,9])]:
        if not path.exists():continue
        nmt,bg,meta=native_ppu(path);native=Image.open(path.with_suffix('.png')).convert('RGB');tiles=[]
        for(row,col),page in zip(coords,pages):
            code=nmt[32*row+col];im,raw=chr_tile(rom,page,code)
            actual=native.crop((col*8,row*8,col*8+8,row*8+8))
            assert[pix==(0,0,0)for pix in actual.getdata()]==[pix==0 for pix in im.getdata()],('glyphpixel',label,row,col)
            tiles.append({'nmt_row':row,'nmt_column':col,'ppu_code':code,'chr_1k_bank':page,'chr_file':0x40010+1024*page+16*(code&63),'raw_hex':raw.hex(' ').upper(),'native_pixel_equality':True,'screen_translation':[0,0]})
        result.append({'label':label,'snapshot':str(path.relative_to(ROOT)),'native_state':meta,'final_bg_bank_registers':bg,'tiles':tiles,'note':'City topoverlay uses midframe mapper banking; final-state banks alone are not the rendered scanline banks.'})
    return result

def clock_graph(rom,out):
    """Pair25/26 calendar/events/AI scene; exact primarytable bounds."""
    primary={0xa036:(0xa039,4),0xa299:(0xa29c,16),0xc776:(0xc779,17)}
    scopes={'calendar':0xa033,'turn_events':0xa296,'ruler_ai_scene':0xc773}
    pending=list(scopes.values());found={};occupied={};tables={};hooks={}
    while pending:
        pc=pending.pop()
        while 0xa000<=pc<0xe000 and pc not in found:
            bank,off=locate(pc,25);op,mode=OPS[rom[off]];size=SIZES[mode]
            assert op!='?',('clockunknown',hex(pc))
            assert all(q not in occupied for q in range(pc,pc+size)),('clockoverlap',hex(pc))
            for q in range(pc,pc+size):occupied[q]=pc
            operand=int.from_bytes(rom[off+1:off+size],'little');nxt=pc+size
            if op in BRANCHES:operand=(nxt+(operand if operand<128 else operand-256))&65535
            _,asm=instruction(rom,off,pc);node={'pc':pc,'bank':bank,'file':off,'op':op,'mode':MODES.get(mode,mode),'operand':operand,'next_pc':nxt,'raw_hex':rom[off:off+size].hex(' ').upper(),'assembly':asm}
            if op=='JSR'and operand==0xeade:
                table=nxt;toff=locate(table,25)[1]
                if pc in primary:table,count=primary[pc]
                else:
                    count=0;minimum=0xe000
                    while count<32:
                        pointer=int.from_bytes(rom[toff+2*count:toff+2*count+2],'little');assert 0xa000<=pointer<0xe000
                        count+=1;minimum=min(minimum,pointer)
                        if table+2*count==minimum:break
                        assert table+2*count<minimum,('clocktablealiasboundary',hex(pc),hex(pointer))
                    else:raise ValueError(f'No proven EADE tableend at{pc:04X}')
                targets=[int.from_bytes(rom[toff+2*i:toff+2*i+2],'little')for i in range(count)]
                assert table+2*count==min(targets)
                desc={'call_pc':pc,'bank':bank,'table_cpu':table,'table_file':toff,'count':count,'targets':targets,'raw_hex':rom[toff:toff+2*count].hex(' ').upper(),'boundary_evidence':'Pointer table ends exactly at first following handler; callgraph excludeswords fromopcodes.'}
                tables[pc]=desc;node.update(op='DISPATCH',targets=targets);pending.extend(targets)
            elif op=='JSR'and operand==0xee07:node.update(op='FARCALL',inline_target=int.from_bytes(rom[off+3:off+5],'little'),next_pc=pc+5,hook='explicit banked dependency')
            elif op in('JSR','JMP'):
                assert mode!='ind',('clockindirect',hex(pc))
                if 0xa000<=operand<0xe000:pending.append(operand)
                else:node['hook']=f'explicit_cpu_{operand:04X}'
            elif op in BRANCHES:pending.append(operand)
            found[pc]=node
            if 'hook'in node:hooks.setdefault(f'{operand:04X}',[]).append(pc)
            if node['op']=='DISPATCH'or op in('JMP','RTS','RTI','BRK'):break
            pc=node['next_pc']
    program={'rom_sha256':ROM_SHA256,'instructions':[found[k]for k in sorted(found)]}
    (out/'turn-program.json').write_text(json.dumps(program,ensure_ascii=False,indent=2)+'\n')
    catalog={'rom_sha256':ROM_SHA256,'physical_pair':[25,26],'controllers':[{'name':name,'entry':entry,**tables[entry+3]}for name,entry in scopes.items()],'all_tables':[tables[k]for k in sorted(tables)],'instruction_count':len(found),'hooks':hooks,'scope':'Three bounded pair25/26 controllers; doesnot includeNMI, PPU timing orpair10/11 decision body.'}
    (out/'turn-controllers.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    lines=['; Pair25/26 calendar, turnevents and rulerAI bridge. External fixed/far helpers remain explicit.']
    for pc in sorted(found):
        n=found[pc];lines.append(f'{n["file"]:06X} b{n["bank"]:02d}:${pc:04X} {n["raw_hex"]:<14} {n["assembly"]}')
        if pc in tables:
            d=tables[pc]
            for i,target in enumerate(d['targets']):lines.append(f'{d["table_file"]+2*i:06X} b{d["bank"]:02d}:${d["table_cpu"]+2*i:04X} .word ${target:04X}')
    (out/'turn-control.asm').write_text('\n'.join(lines)+'\n')
    return catalog

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/domestic-ai');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;a.out.mkdir(parents=True,exist_ok=True)
    turn=clock_graph(rom,a.out)
    found,dispatch,hooks=graph(rom);program={'rom_sha256':ROM_SHA256,'instructions':[found[k]for k in sorted(found)]}
    (a.out/'program.json').write_text(json.dumps(program,ensure_ascii=False,indent=2)+'\n')
    lines=['; Bounded ruler/domesticAI pair10/11. Inline pointers are data, not instructions.','; Political/succession, fixed services and banked calls are explicit dependencies.']
    for pc in sorted(found):
        node=found[pc];lines.append(f'{node["file"]:06X} b{node["bank"]:02d}:${pc:04X} {node["raw_hex"]:<14} {node["assembly"]}'+(' ; '+node['hook']if'hook'in node else''))
        if pc in DOMESTIC_DISPATCH:
            d=next(d for d in dispatch if d['call_pc']==pc)
            for i,target in enumerate(d['targets']):lines.append(f'{d["file"]+2*i:06X} b10:${d["table"]+2*i:04X} .word ${target:04X} ; index{i}')
    (a.out/'control.asm').write_text('\n'.join(lines)+'\n')
    schema={'rom_sha256':ROM_SHA256,'record_size':32,'count':30,'ram_base':0x6000,'initial_file':0x20c10,'ui_numeric_interpreter':{'bank':29,'cpu':0xaf77,'file':0x3af87},'fields':[
        {'offset':0,'size':1,'name':'ruler_low3_and_flags','confidence':'confirmed low3 ruler index; high5 path-specific flags'},
        {'offset':1,'size':1,'name':'unresolved_byte1','confidence':'unresolved'},
        {'offset':2,'size':2,'name':'gold','label':'金','confidence':'confirmed UI template+payment+scene transfer'},
        {'offset':4,'size':2,'name':'grain','label':'米','confidence':'confirmed UI template+payment+scene transfer'},
        {'offset':6,'size':2,'name':'population_hundreds','label':'人口','display_multiplier':100,'confidence':'confirmed numeric template+two literal zero digits+native UI'},
        {'offset':8,'size':2,'name':'land','label':'土地','confidence':'confirmed native UI position+numeric offset'},
        {'offset':10,'size':1,'name':'disaster_prevention','label':'防災','confidence':'confirmed native UI position+numeric offset'},
        {'offset':11,'size':1,'name':'governance','label':'統治度','confidence':'confirmed city commander panel+numeric offset'},
        {'offset':12,'size':2,'name':'reserve_troops','label':'ヒカエ','confidence':'confirmed military menu+reserve consumption'},
        {'offset':14,'size':2,'name':'industry','label':'産業','confidence':'confirmed native UI position+numeric offset'},
        {'offset':16,'size':1,'name':'treasures','label':'タカラ','confidence':'confirmed message34 original-rendered noun+quantity; A954..A962 byte16 producer; C4E1..C4FB sale consumer','glyph_image':'city-field16-label.png','icon_is_not_transcribed_as_a_letter':True},
        {'offset':17,'size':10,'name':'officer_roster','confidence':'confirmed fixed10slots; FF empty'},
        {'offset':27,'size':5,'name':'auxiliary_bytes27_to31','confidence':'unresolved full semantics'}
    ],'numeric_templates':ui_fields(rom),'display_semantics':{'population':'RawLE16 read by F1, five digits, then two literal zeros: rawvalue*100 in normal domain. Annual income independently masksraw&7FFF.','land_industry':'F1 renders lowest3decimaldigits of rawLE16. Annual income independently masksraw&03FF; initial9999 therefore displays999 but incomeinput783.','officer_troop_sum':'F3 adds rawLE16 officerwords withoutlow10mask, wrapping16bits before five-digit display.'},'resource16_glyphs':resource16_glyphs(rom,a.out),'ui_scope':'Natural original-core screenshots supplied by root, analysis/phase5/runtime/city-info; no RAM injection. Message34 fixture is explicitly synthetic, unchangedROM. All-equal initial resource values alone are not used to infer field offsets.'}
    (a.out/'city-schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
    evidence={'rom_sha256':ROM_SHA256,'physical_pair':[10,11],'entry':0xa00f,'entry_file':0x1401f,'roots':[{'cpu':cpu,'file':locate(cpu)[1],'bank':locate(cpu)[0],'name':name}for cpu,name in ROOTS.items()],'instruction_count':len(found),'dispatches':dispatch,'hooks':hooks,'political_external_ranges':[[0xca19,0xcc12],[0xcf3f,0xd03a]],'legal_domain':{'cities':30,'rulers':7,'officers':237,'roster_slots':10,'difficulty_table_rows':3},'not_complete_global_scheduler':True}
    (a.out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'instruction_count':len(found),'roots':len(ROOTS),'dispatches':dispatch,'hooks':list(hooks),'turn_instruction_count':turn['instruction_count'],'turn_tables':len(turn['all_tables'])},ensure_ascii=False))

if __name__=='__main__':main()
