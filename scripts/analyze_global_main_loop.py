#!/usr/bin/env python3
"""Lift fixed-bank global dispatch, setup prefixes and bounded NMI control."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import OPS,SIZES,instruction
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BRANCHES={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}
# Recurse only these fixed control/helper regions. Display synthesis, input
# polling, PPU jobs, banked audio playback and scene bodies remain dependencies.
REGIONS=[(0xe05e,0xe567),(0xe57f,0xe667),(0xe66b,0xe6a6),
         (0xe749,0xe774),(0xe7b5,0xe843),(0xf237,0xf26d),
         (0xf800,0xf87b),(0xf88d,0xfaa9),(0xfad5,0xfb2d)]
def local(pc):return any(a<=pc<b for a,b in REGIONS)
def offset(pc):return 0x3e010+pc-0xe000
def put(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def walk(found,start,stop_at=()):
    seen=set();todo=[start]
    while todo:
        pc=todo.pop()
        if pc in seen or pc in stop_at or pc not in found:continue
        seen.add(pc);v=found[pc];op=v['op']
        if op in ['GLOBAL_DISPATCH','NMI_DISPATCH']:todo.extend(v['targets']);continue
        if op=='JMP':
            if 'hook'not in v:todo.append(v['operand'])
            continue
        if op in ['RTS','RTI','BRK']:continue
        todo.append(v['next_pc'])
        if op in BRANCHES or op=='JSR'and'hook'not in v:todo.append(v['operand'])
    return sorted(seen)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase6/global');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA;a.out.mkdir(parents=True,exist_ok=True)
    targets=[int.from_bytes(rom[offset(0xe07c)+2*i:offset(0xe07c)+2*i+2],'little')for i in range(15)]
    nmi=[int.from_bytes(rom[offset(0xf87b)+2*i:offset(0xf87b)+2*i+2],'little')for i in range(9)]
    assert min(targets)==0xe09a and 0xe07c+30==0xe09a
    assert 0xf87b+18==0xf88d and nmi[:2]==[0xfa97,0xfa97]
    pending=[0xe05e,0xe066,0xf800,0xf862,0xf88d,0xe4e9,0xe823,0xe830,0xf237,0xf24b,0xf25f,0xf266,*targets,*nmi]
    found={};occupied={};hooks={}
    while pending:
        pc=pending.pop()
        if pc in found or not local(pc):continue
        off=offset(pc);op,mode=OPS[rom[off]];size=SIZES[mode];assert op!='?',hex(pc)
        for k in range(pc,pc+size):assert k not in occupied or occupied[k]==pc,('instruction overlap',hex(pc),hex(k));occupied[k]=pc
        value=int.from_bytes(rom[off+1:off+size],'little');nxt=pc+size;_,asm=instruction(rom,off,pc)
        v={'pc':pc,'bank':31,'file':off,'op':op,'mode':{'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}.get(mode,mode),
           'operand':value,'next_pc':nxt,'raw_hex':rom[off:off+size].hex(' ').upper(),'assembly':asm}
        if pc in [0xe079,0xf878]:
            assert op=='JMP'and mode=='ind'
            v.update(op='GLOBAL_DISPATCH'if pc==0xe079 else'NMI_DISPATCH',targets=targets if pc==0xe079 else nmi)
            pending.extend(v['targets'])
        elif op in BRANCHES:
            v['operand']=(nxt+(value if value<128 else value-256))&65535;pending.extend([v['operand'],nxt])
        elif op=='JSR':
            assert value not in [0xeade,0xee07,0xb517],('Unexpected inline payload',hex(pc))
            if local(value):pending.append(value)
            else:
                v['hook']='explicit external CPU helper';hooks.setdefault(f'{value:04X}',[]).append({'call_pc':pc,'kind':'call'})
            pending.append(nxt)
        elif op=='JMP':
            assert mode=='ab',('Unknown indirect destination',hex(pc))
            if local(value):pending.append(value)
            else:v['hook']='explicit external CPU tail';hooks.setdefault(f'{value:04X}',[]).append({'call_pc':pc,'kind':'tail'})
        elif op not in ['RTS','RTI','BRK']:pending.append(nxt)
        found[pc]=v
    # No table/data bytes may masquerade as instructions.
    for lo,hi in [(0xe07c,0xe09a),(0xe2c2,0xe2e2),(0xe567,0xe57f),(0xe667,0xe66b),(0xe6a6,0xe6c6),(0xf87b,0xf88d)]:
        assert not any(lo<=k<hi for k in occupied),('data lifted as code',hex(lo))
    names=['冷启动后硬件/音序初始化并进入scene6设置','城市场景初始化','内政AI一次主线程合作更新',
           '战场恢复/初始化','战术AI一次主线程合作更新','普通攻击场景初始化','普通攻击期间主线程RNG更新',
           '单挑场景初始化','单挑期间主线程RNG更新','标题/开局菜单场景初始化','等待别名（标题/开局菜单回调推进）',
           '新局/君主选择场景初始化','等待别名（新局/君主选择回调推进）','结局场景初始化','等待别名（结局回调推进）']
    callback_names=['通用回调','通用回调别名','城市UI回调','战场回调','普通攻击回调','单挑回调','标题/开局菜单回调','新局/君主选择回调','结局回调']
    states=[]
    for index,entry in enumerate(targets):
        reachable=walk(found,entry,[0xe066]);nodes=[found[k]for k in reachable]
        states.append({'state':index,'entry':entry,'bank':31,'file':offset(entry),'name':names[index],
           'reachable_instructions':reachable,'instruction_count':len(reachable),
           'direct_global_writes':[v for v in nodes if v['op']in['STA','STX','STY','INC','DEC']and v['operand']in[0x78,0x7a]],
           'external_calls':[v for v in nodes if 'hook'in v],
           'declared_terminal':'next E066 boundary; dependencies can interrupt setup before completion'})
    edges=[]
    for state in states:
        index=state['state']
        for write in state['direct_global_writes']:
            if write['operand']!=0x7a:continue
            if write['op']=='INC':edges.append({'from':index,'to':(index+1)&31,'pc':write['pc'],'condition':'setup reaches original INC007A; dependencies may block earlier'})
            elif write['op']=='STA':
                preceding=found.get(write['pc']-2)
                if preceding and preceding['op']=='LDA'and preceding['mode']=='imm':edges.append({'from':index,'to':preceding['operand']&31,'pc':write['pc'],'condition':'original literal store'})
        if index in [2,4]:edges.append({'from':index,'to':None,'condition':'banked cooperation update may modify007A; no new global state invented','call_pc':0xe185 if index==2 else 0xe229})
        if index in [6,8,10,12,14]:edges.append({'from':index,'to':index,'condition':'bounded main body returnsE066; a real NMI can separately alter007A'})
    callbacks=[]
    for index,entry in enumerate(nmi):
        reachable=walk(found,entry,[0xf88d]);nodes=[found[k]for k in reachable]
        callbacks.append({'scene':index,'entry':entry,'bank':31,'file':offset(entry),'name':callback_names[index],
           'reachable_instructions':reachable,'instruction_count':len(reachable),'external_calls':[v for v in nodes if'hook'in v]})
    handoffs=[
      {'domain':'global-main','state':2,'call_pc':0xe185,'cpu_target':0xa000,'selector_call':0xf24b,'selector':0x2a,'physical_pair':[10,11],'entry_stub_hex':rom[16+10*8192:16+10*8192+3].hex(' ').upper(),'actual_local_entry':0xa00f,'role':'one domestic-AI cooperation update; not city NMI UI'},
      {'domain':'global-main','state':4,'call_pc':0xe229,'cpu_target':0xa000,'selector_call':0xf24b,'selector':0x28,'physical_pair':[8,9],'actual_local_entry':0xa02d,'role':'one battlefield-AI cooperation update; not battle NMI controller'},
      {'domain':'nmi-scene','scene':2,'call_pc':0xf8ef,'cpu_target':0xa000,'selector':0x3b,'physical_pair':[27,28],'role':'city UI controller'},
      {'domain':'nmi-scene','scene':3,'call_pc':0xf94d,'cpu_target':0xa000,'selector':0x2c,'physical_pair':[12,13],'role':'BattleStateMachine callback'},
      {'domain':'nmi-scene','scene':4,'call_pc':0xf994,'cpu_target':0xa000,'selector':0x2e,'physical_pair':[14,15],'role':'AttackStateMachine callback'},
      {'domain':'nmi-scene','scene':5,'call_pc':0xf9cd,'cpu_target':0xa01b,'selector':0x37,'physical_pair':[23,24],'role':'DuelStateMachine callback'},
      {'domain':'nmi-scene','scene':6,'call_pc':0xfa04,'cpu_target':0xa003,'selector':0x2a,'physical_pair':[10,11],'role':'title/start/scenario menu, distinct from main-thread domestic A000'},
      {'domain':'nmi-scene','scene':7,'call_pc':0xfa44,'cpu_target':0xa024,'selector':0x28,'physical_pair':[8,9],'actual_local_entry':0xd70f,'role':'new-game/ruler-selection controller, distinct from battlefield-AI A000'},
      {'domain':'nmi-scene','scene':8,'call_pc':0xfa85,'cpu_target':0xa01e,'selector':0x37,'physical_pair':[23,24],'actual_local_entry':0xd693,'role':'ending controller, not an attack callback'},
    ]
    program={'rom_sha256':SHA,'instructions':[found[k]for k in sorted(found)],'main_targets':targets,'nmi_targets':nmi}
    report={'rom_sha256':SHA,'cold_post_reset_entry':0xe05e,'main_dispatch_entry':0xe066,'main_state_address':0x7a,'main_mask':31,'main_state_count':15,
        'main_table_cpu':0xe07c,'main_table_file':offset(0xe07c),'main_table_raw_hex':rom[offset(0xe07c):offset(0xe09a)].hex(' ').upper(),
        'nmi_entry':0xf800,'nmi_window_entry':0xf862,'nmi_window_boundary':0xf88d,'nmi_scene_address':0x78,'nmi_mask':15,'nmi_scene_count':9,
        'nmi_table_cpu':0xf87b,'nmi_table_file':offset(0xf87b),'nmi_table_raw_hex':rom[offset(0xf87b):offset(0xf88d)].hex(' ').upper(),
        'states':states,'main_edges':edges,'nmi_callbacks':callbacks,'handoffs':handoffs,'instruction_count':len(found),'byte_count':len(occupied),'external_targets':hooks,
        'bank_cache_protocol':{'F237':{'logical_shadow':[0xe2,0xe3],'role':'NMI callback code banks'},'F24B':{'logical_shadow':[0xdf,0xe0],'role':'main-thread interrupted code banks'},'F25F':{'logical_shadow':[0xe1],'role':'NMI callback data bank'},'F266':{'logical_shadow':[0xde],'role':'main-thread interrupted data bank'},'F83E':'NMI starts by activating E1/E2/E3','F88D':'NMI normal exit restores DE/DF/E0'},
        'ending_state13':{'scene':8,'0541_0':'no-successor/defeat route','0541_1_to_3':'scored ending categories, detailed semantics belong to faction_lifecycle','audio_request_branch':'0541==0 usesE673 with98; nonzero usesE67B withAA'},
        'dependency_notes':{'EE53':'PPU pending-update transaction dispatcher, not an audio player','pair14_A003':'bank15 D8D4 original per-callback audio engine; changes bank2 data/bank3 code and channel RAM; unresolved playback dependency','F3BD':'post-reset initialization/controller protection probe outside the bounded loop source','FB28':'IRQ flag0062 polling; CPU-only updates cannot invent its completion'},
        'scope':'All15 main indices and all9 NMI callback indices, fixed-bank control only. Hardware, banked scene bodies and per-frame audio are explicit dependencies. This is not a complete NES frame or cold reset emulation.'}
    put(a.out/'program.json',program);put(a.out/'state-catalog.json',report)
    lines=['; Fixed31 global/NMI control. Proven pointer tables excluded from code.']
    for pc,table in [(0xe07c,targets),(0xf87b,nmi)]:
        for i,target in enumerate(table):lines.append(f'{offset(pc+2*i):06X} b31:${pc+2*i:04X} .word ${target:04X} ; index{i}')
    for k in sorted(found):
        v=found[k];extra=' ; external dependency'if'hook'in v else'';lines.append(f'{v["file"]:06X} b31:${k:04X} {v["raw_hex"]:<9} {v["assembly"]}{extra}')
    (a.out/'global-control.asm').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'main_states':15,'nmi_scenes':9,'instructions':len(found),'external_targets':len(hooks)}))
if __name__=='__main__':main()
