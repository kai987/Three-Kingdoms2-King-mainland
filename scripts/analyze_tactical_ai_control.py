#!/usr/bin/env python3
"""Lift the exact bounded bank8 tactical-AI cooperation graph, read-only ROM."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import OPS,SIZES,instruction
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BRANCHES={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}
TABLES={0xa09e:(0xa0a1,8,'actor_strategy'),0xacab:(0xacae,16,'tactic_predicate')}
FIELDS={'request':0x6f8b,'actor_slot':0x6f8c,'proposal_action_or_destination':0x6f8d,
        'proposal_target_slot':0x6f8e,'proposal_status':0x6f8f,'rng_cursor':0x6f92,
        'scan_slot':0x6f94,'status3_count':0x6f95,'eligible_attempts':0x6f96,
        'battle_main':0x500,'battle_sub':0x501,'active_side':0x504,'action_budget':0x505}
def off(pc):return 0x10010+pc-0xa000
def put(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def walk(nodes,entry):
    todo=[entry];seen=set()
    while todo:
        pc=todo.pop()
        if pc in seen or pc not in nodes:continue
        seen.add(pc);v=nodes[pc]
        if 'targets'in v:todo.extend(v['targets']);continue
        if v['op']=='JMP':
            if 'hook'not in v:todo.append(v['operand'])
        elif v['op']not in ['RTS','RTI','BRK']:
            todo.append(v['next_pc'])
            if v['op']in BRANCHES or v['op']=='JSR'and'hook'not in v:todo.append(v['operand'])
    return sorted(seen)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase7/controller');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA;a.out.mkdir(parents=True,exist_ok=True)
    assert rom[off(0xa000):off(0xa000)+3]==bytes.fromhex('4c2da0')
    pending=[0xa000];nodes={};occupied={};tables=[];hooks={}
    while pending:
        pc=pending.pop()
        if pc in nodes:continue
        assert 0xa000<=pc<0xbab3,('Unclassified tactical destination',hex(pc))
        o=off(pc);op,mode=OPS[rom[o]];size=SIZES[mode];assert op!='?',('dataopcode',hex(pc))
        for q in range(pc,pc+size):assert q not in occupied,('overlap',hex(pc),hex(q));occupied[q]=pc
        value=int.from_bytes(rom[o+1:o+size],'little');nxt=pc+size;_,asm=instruction(rom,o,pc)
        v={'pc':pc,'bank':8,'file':o,'op':op,'mode':{'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}.get(mode,mode),'operand':value,'next_pc':nxt,'raw_hex':rom[o:o+size].hex(' ').upper(),'assembly':asm}
        if pc in TABLES:
            assert op=='JSR'and value==0xb517
            table,count,name=TABLES[pc];assert table==nxt
            targets=[int.from_bytes(rom[off(table)+2*i:off(table)+2*i+2],'little')for i in range(count)]
            assert table+2*count==min(targets),('Exact inline tableend',hex(pc))
            v.update(targets=targets,hook='independent B517 inline dispatch');pending.extend(targets)
            tables.append({'call_pc':pc,'helper':0xb517,'name':name,'bank':8,'table_cpu':table,'table_file':off(table),'count':count,'targets':targets,'raw_hex':rom[off(table):off(table)+2*count].hex(' ').upper(),'boundary_evidence':'table ends exactly at first following handler'})
        elif op=='JSR':
            assert value not in [0xb517,0xeade,0xee07],('Unclassified inline helper',hex(pc))
            if 0xa000<=value<0xbab3:pending.append(value)
            else:
                assert value==0xf266,('Unexpected external helper',hex(pc),hex(value))
                v['hook']='independently recovered RuntimeServices mapper helper';hooks.setdefault(f'{value:04X}',[]).append(pc)
            pending.append(nxt)
        elif op=='JMP':assert mode=='ab';pending.append(value)
        elif op in BRANCHES:v['operand']=(nxt+(value if value<128 else value-256))&65535;pending.extend([v['operand'],nxt])
        elif op not in ['RTS','RTI','BRK']:pending.append(nxt)
        nodes[pc]=v
    for table,count,name in TABLES.values():assert not any(table<=pc<table+2*count for pc in occupied)
    # B517 is independently readable CPU-protocol source, not an opaque ack.
    inline=[];pc=0xb517
    while pc<0xb536:
        o=off(pc);op,mode=OPS[rom[o]];size=SIZES[mode];_,asm=instruction(rom,o,pc)
        inline.append({'pc':pc,'bank':8,'file':o,'raw_hex':rom[o:o+size].hex(' ').upper(),'assembly':asm});pc+=size
    assert pc==0xb536
    groups=[('entry',0xa02d),('secondary_phase',0xb933),('scan',0xa03c),('strategy_dispatch',0xa099)]
    groups += [(f'strategy_{i}',target)for i,target in enumerate(next(t for t in tables if t['name']=='actor_strategy')['targets'])]
    groups += [(f'tactic_predicate_{i}',target)for i,target in enumerate(next(t for t in tables if t['name']=='tactic_predicate')['targets'])]
    entries=[]
    for name,entry in groups:
        reachable=walk(nodes,entry);ns=[nodes[k]for k in reachable]
        entries.append({'name':name,'entry':entry,'bank':8,'file':off(entry),'instruction_count':len(ns),'reachable_instructions':reachable,
          'conditions':[n for n in ns if n['op']in BRANCHES],
          'control_writes':[n for n in ns if n['op']in ['STA','STX','STY','INC','DEC']and n['operand']in FIELDS.values()],
          'external_calls':[n for n in ns if'hook'in n]})
    catalog={'rom_sha256':SHA,'physical_code_bank':8,'original_caller_pair':[8,9],'entry':0xa02d,'trampoline_entry':0xa000,'entry_file':off(0xa02d),'trampoline_raw_hex':'4C 2D A0',
      'control_fields':FIELDS,'request_modes':[{'comparison':255,'entry':0xa034,'meaning':'no request; return'},{'comparison':1,'entry':0xb933,'meaning':'secondary reserve interaction'},{'comparison':'all other rawbytes','entry':0xa03c,'meaning':'scan and choose one proposal'}],
      'inline_tables':sorted(tables,key=lambda t:t['call_pc']),'inline_helper_evidence':inline,'instruction_count':len(nodes),'entries':entries,'shared_helpers':hooks,
      'scope':'Complete reachable tactical cooperation graph from A000/A02D, plus independently recovered B517 CPU protocol and shared F266. No NMI/frame/action-effect controller is executed.',
      'inline_audit':{'reachable_B517_calls':sorted(TABLES),'reachable_EADE_calls':[],'reachable_EE07_calls':[],'table_bytes_are_excluded_from_code':True}}
    program={'rom_sha256':SHA,'entry':0xa02d,'instructions':[nodes[k]for k in sorted(nodes)],'inline_tables':sorted(tables,key=lambda t:t['call_pc'])}
    put(a.out/'program.json',program);put(a.out/'state-catalog.json',catalog)
    lines=['; Complete bounded tactical-AI cooperation graph from physical bank8 A000.','; Inline pointer words are data; B517 and fixed F266 have independent source.']
    for pc,v in sorted(nodes.items()):
        lines.append(f'{v["file"]:06X} b08:${pc:04X} {v["raw_hex"]:<14} {v["assembly"]}')
        if pc in TABLES:
            d=next(t for t in tables if t['call_pc']==pc)
            for i,t in enumerate(d['targets']):lines.append(f'{d["table_file"]+2*i:06X} b08:${d["table_cpu"]+2*i:04X} .word ${t:04X} ; {d["name"]} {i}')
    lines.extend(['; Independent B517 CPU-protocol evidence']+[f'{v["file"]:06X} b08:${v["pc"]:04X} {v["raw_hex"]:<14} {v["assembly"]}'for v in inline])
    (a.out/'control.asm').write_text('\n'.join(lines)+'\n')
    md=['# 战术 AI 入口与全部合法分派','', '入口 branch、8 个策略和 16 个计略 predicate 的完整控制条件和状态写入见下列索引。地址来自原指令，功能名称为现代说明。','']
    for e in entries:
        md += [f'## {e["name"]} — bank8 ${e["entry"]:04X} / file ${e["file"]:06X}', '',
               f'可达 {e["instruction_count"]} 条恢复指令。分支：'+', '.join(f'${n["pc"]:04X} {n["op"]}→${n["operand"]:04X}'for n in e['conditions'])+'。','',
               '控制字段写入：'+', '.join(f'${n["pc"]:04X} {n["op"]} ${n["operand"]:04X}'for n in e['control_writes'])+'。','']
    (a.out/'all-entries.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({'instruction_count':len(nodes),'entry_count':len(entries),'tables':tables,'shared_helpers':hooks},ensure_ascii=False))
if __name__=='__main__':main()
