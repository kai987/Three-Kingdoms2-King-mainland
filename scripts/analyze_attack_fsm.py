#!/usr/bin/env python3
"""Recover every bounded normal-attack dispatch table and reachable handler as an IR.

IR preserves the actual 6502 conditions. External helpers become explicit hooks.
No guessed state indices are seeded and no original ROM bytes are changed.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
SHA="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
NAMES={0:'攻击场景控制初始化与双方信息显示',1:'战阵行动循环与结果检查',
 2:'阵列对象动作与结果推进',3:'当前参与武将的菜单交互',
 4:'结果确认、体力处理与返回战场',5:'单挑准备与结果回读',
 6:'参与方0阵形选择',7:'参与方1阵形选择',
 8:'智力派生参数显示与分支',9:'战阵对象动画与处理',
 10:'交互确认及单挑转移选择'}
HOOK_NAMES={0xF2D7:"officer_record_pointer",0xF28B:"enqueue_dialogue",0xF283:"enqueue_dialogue_1",0xF293:"enqueue_dialogue_0",0xECEE:"begin_palette_fade",0xECBF:"finish_scene_transition",0xE87A:"rng_next",0xE843:"rng_below_100",0xE862:"bounded_rng",0xEE07:"banked_call",0xE57F:"ppu_reset_or_transition"}

def analyze(path,out):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 m=bytearray(65536);m[0xa000:0xc000]=raw[16+14*8192:16+15*8192];m[0xc000:0xe000]=raw[16+15*8192:16+16*8192];m[0xe000:]=raw[16+31*8192:16+32*8192]
 cpu=MPU(memory=m);d=Disassembler(cpu)
 tables={}
 for pc in range(0xa069,0xe000):
  if m[pc:pc+3]!=bytes.fromhex('20deea'):continue
  start=pc+3;targets=[];bound=0xe000;p=start
  while p<bound and len(targets)<64:
   target=m[p]|m[p+1]<<8
   if not 0xa000<=target<0xe000:break
   targets.append(target)
   if target>=p+2:bound=min(bound,target)
   p+=2
  if p!=bound:raise ValueError(f'Unproved pointer table boundary at {pc:04x}')
  bank=14 if start<0xc000 else 15;file=16+bank*8192+start-(0xa000 if start<0xc000 else 0xc000)
  tables[pc]={"call_pc":pc,"table_start":start,"table_bank":bank,"table_file":file,"table_end_exclusive":p,"raw_hex":bytes(m[start:p]).hex(' ').upper(),"targets":targets,"count":len(targets),"extent_evidence":"Last pointer ends exactly where the earliest forward handler starts"}
 primary=tables[0xa06c]['targets'];assert len(primary)==11
 found={};occupied={};edges=[];conflicts=[];hooks={};pending=deque([0xa069]+primary+[x for t in tables.values() for x in t['targets']])
 branches={'BCC','BCS','BEQ','BMI','BNE','BPL','BVC','BVS'}
 while pending:
  pc=pending.popleft()
  while 0xa000<=pc<0xe000 and pc not in found:
   if pc in occupied:conflicts.append([pc,occupied[pc]]);break
   n,asm=d.instruction_at(pc);op,mode=cpu.disassemble[m[pc]]
   if op=='???':raise ValueError(f'Unsupported opcode at {pc:04x}')
   raw_instruction=bytes(m[pc:pc+n]);operand=int.from_bytes(raw_instruction[1:],'little');next_pc=pc+n
   if op in branches:operand=(pc+2+int.from_bytes(raw_instruction[1:2],'little',signed=True))&65535
   if any(a in occupied for a in range(pc,pc+n)):conflicts.append([pc,'overlap']);break
   for a in range(pc,pc+n):occupied[a]=pc
   bank=14 if pc<0xc000 else 15;file=16+bank*8192+pc-(0xa000 if pc<0xc000 else 0xc000)
   item={'pc':pc,'bank':bank,'file':file,'op':op,'mode':mode,'operand':operand,'next_pc':next_pc,'assembly':asm,'bytes_hex':raw_instruction.hex()}
   if pc in tables:
    item['op']='DISPATCH';item['targets']=tables[pc]['targets'];item['next_pc']=None
    for i,target in enumerate(item['targets']):edges.append({'from':pc,'to':target,'kind':'dispatch','index':i});pending.append(target)
   elif op=='JSR' and operand==0xee07:
    item['op']='FARCALL';item['inline_target']=m[pc+3]|m[pc+4]<<8;item['next_pc']=pc+5
    hooks.setdefault('EE07',{'kind':'far_call','call_sites':[]})['call_sites'].append({'pc':pc,'inline_target':item['inline_target'],'bank_selector_register':'Y at call'})
    edges.append({'from':pc,'to':item['next_pc'],'kind':'far_call_returns'})
   elif op in {'JSR','JMP'} and mode=='abs':
    if 0xa000<=operand<0xe000:
     pending.append(operand);edges.append({'from':pc,'to':operand,'kind':op})
    else:
     key=f'{operand:04X}'
     hooks.setdefault(key,{'target':operand,'name':HOOK_NAMES.get(operand,'helper_'+key.lower()),'kind':'external_helper','call_sites':[]})['call_sites'].append({'pc':pc,'tail':op=='JMP'})
     item['hook']=key
   elif op in branches:
    pending.append(operand);edges.append({'from':pc,'to':operand,'kind':op})
   found[pc]=item
   if op in branches:edges.append({'from':pc,'to':next_pc,'kind':'branch_not_taken'})
   if item['op']=='DISPATCH' or op in {'JMP','RTS','RTI','BRK'}:break
   pc=item['next_pc']
 out.mkdir(parents=True,exist_ok=True)
 def reachable(entry):
  seen=set();q=[entry]
  while q:
   pc=q.pop()
   if pc in seen or pc not in found:continue
   seen.add(pc);v=found[pc]
   if v['op']=='DISPATCH':q+=v['targets'];continue
   if v['op']=='JMP':
    if 'hook' not in v:q.append(v['operand'])
    continue
   if v['op'] in {'RTS','RTI','BRK'}:continue
   q.append(v['next_pc'])
   if v['op'] in branches or v['op']=='JSR' and 'hook' not in v:q.append(v['operand'])
  return sorted(seen)
 states=[]
 for state,entry in enumerate(primary):
  driver=next((v for v in tables.values() if entry<=v['call_pc']<entry+32),None)
  targets=driver['targets'] if driver else [entry]
  handlers=[]
  for sub,target in enumerate(targets):
   locations=reachable(target);ops=[found[p] for p in locations]
   writes=[v for v in ops if v['op'] in {'STA','STX','STY','INC','DEC'} and v['mode'] in {'abs','abx','aby'}]
   handlers.append({'substate':sub,'entry':target,'instruction_count':len(locations),'conditions':[{'pc':v['pc'],'branch':v['op'],'target':v['operand']} for v in ops if v['op'] in branches],
     'writes':[{'pc':v['pc'],'operation':v['op'],'address':v['operand'],'mode':v['mode']} for v in writes],
     'hooks':sorted({v['hook'] for v in ops if 'hook' in v}), 'far_calls':[{'pc':v['pc'],'target':v['inline_target']} for v in ops if v['op']=='FARCALL'],
     'reachable_locations':locations})
  entry_bank=14 if entry<0xc000 else 15;entry_file=16+entry_bank*8192+entry-(0xa000 if entry<0xc000 else 0xc000)
  states.append({'state':state,'entry':entry,'entry_bank':entry_bank,'entry_file':entry_file,'name':NAMES[state],'label_confidence':'descriptive machine behavior; state6 formation selection has original-renderer fixture evidence, state7 has symmetric instruction evidence','dispatch_pc':driver['call_pc'] if driver else None,'substate_count':len(targets),'handlers':handlers})
 report={'rom_sha256':SHA,'main_state_address':0x0540,'substate_address':0x0541,'third_control_byte_address':0x0542,'entry':0xa069,
   'state_variables':{'main':0x0540,'sub':0x0541,'global':0x7a,'nmi_mode':0x78},'main_dispatch':{'cpu':0xa069,'file':0x1c079,'table_cpu':0xa06f,'table_file':0x1c07f,'count':11},
   'main_state_count':11,'dispatch_table_count':len(tables),'expanded_entry_count':sum(s['substate_count'] for s in states),'distinct_subhandler_entries':len(set(x['entry'] for s in states for x in s['handlers'])),'states':states,'dispatch_tables':list(tables.values()),'instruction_count':len(found),'code_bytes':len(occupied),'conflicts':conflicts,'hooks':hooks,'edges':edges,
   'completion_scope':'All bounded main/substate control handlers recovered as instruction-level IR; named host helpers and rendering remain explicit dependencies, not silent stubs.'}
 (out/'state-catalog.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (out/'program.json').write_text(json.dumps({'rom_sha256':SHA,'instructions':[found[p] for p in sorted(found)]},indent=2)+'\n')
 lines=['; Reachable normal-attack handlers, physical bank14 A000/bank15 C000. Pointer tables excluded.']
 for pc in sorted(found):
  v=found[pc];bank=14 if pc<0xc000 else 15;off=16+bank*8192+(pc-(0xa000 if bank==23 else 0xc000))
  tail=' ; inline targets: '+','.join(f'${x:04X}' for x in v.get('targets',[])) if v['op']=='DISPATCH' else ' ; inline far target $'+format(v['inline_target'],'04X') if v['op']=='FARCALL' else ''
  lines.append(f'${pc:04X} | b{bank} file ${off:06X} | {v["assembly"]}{tail}')
 (out/'handlers.asm').write_text('\n'.join(lines)+'\n')
 (out/'opcodes.json').write_text(json.dumps(dict(Counter(v['op'] for v in found.values())),indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['main_state_count','dispatch_table_count','distinct_subhandler_entries','instruction_count','code_bytes','conflicts']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/attack_fsm');a=p.parse_args();analyze(a.rom,a.out)
