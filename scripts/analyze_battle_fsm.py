#!/usr/bin/env python3
"""Recover battle dispatch tables and bounded handler control flow.

Known inline pointer tables are data. Calls remain explicit dependencies unless
listed as recovered helpers; no whole-bank executable-code assumption is made.
"""
from pathlib import Path
import argparse,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import instruction,OPS,SIZES
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MAIN=[0xA04E,0xA21B,0xA293,0xA293,0xA44D,0xA87C,0xB94A,0xBC93,
      0xBE7E,0xC1FC,0xC204,0xC691,0xC98C,0xCD16,0xD2CD,0xD4F0]
TABLES={0:(0xA054,5),1:(0xA221,3),2:(0xA29F,4),3:(0xA29F,4),
        4:(0xA462,7),5:(0xA888,11),6:(0xB958,6),7:(0xBCA3,8),
        8:(0xBE84,17),10:(0xC20A,7),11:(0xC697,4),12:(0xC992,6),
        13:(0xCD1C,7),14:(0xD2D3,7),15:(None,4)}
NAMES=['单位选择与行动菜单','单位信息','普通攻击目标选择','普通攻击确认','移动',
       '计略选择与效果','退却','待機','电脑方行动桥接','村落服务跨银行入口',
       '下一方回合准备','单挑后升级提示','战斗结果确认','败方武将转移或转为在野','胜方收容及超额武将转移','归属结算与返回城市']
FIXED_ENTRIES={0xE850,0xE856,0xE862,0xEA7C,0xEAA5,0xEBE9,0xF2AF,0xF368}
FIXED_RANGES=((0xE850,0xE87A),(0xEA7C,0xEADE),(0xEBE9,0xEC2F),(0xF2AF,0xF2D7),(0xF368,0xF379))

def recovered_address(pc):
 return 0xA000<=pc<0xE000 or any(lo<=pc<hi for lo,hi in FIXED_RANGES)

BRANCHES={'BPL','BMI','BVC','BVS','BCC','BCS','BNE','BEQ'}
HOOK_NAMES={0xDF27:'text_jobs_idle',0xDC33:'draw_active_unit',0xDC36:'draw_officer_by_slot',
 0xDC63:'draw_dialog_highlight',0xDC70:'dialog_navigation',0xA1DE:'blink_menu_cursor',
 0xA1F7:'reset_command_cursor',0xD657:'draw_battle_cursor',0xD5EE:'battle_cursor_input',
 0xD4FB:'direction_repeat_input',0xD68A:'find_unit_at_cursor',0xDC4B:'target_side_filter',
 0xA368:'orthogonal_adjacent_target',0xA3D2:'prepare_attack_scene_parameters',0xA433:'save_attack_officer_stats',
 0xB02B:'apply_selected_tactic',0xB5D8:'apply_health_loss',0xB68B:'apply_troop_loss',
 0xBDC0:'finish_side_turn',0xDD72:'check_commander_outcome',0xCAF8:'prepare_postbattle_summary',
 0xCA51:'result_yes_flag',0xC620:'round_resource_update',0xCC29:'draw_postbattle_units',
 0xD0E1:'select_next_postbattle_officer',0xD48D:'postbattle_removal_operation',
 0xD6CC:'enqueue_battle_unit_graphics',0xDA5A:'tile_to_pixel_coordinates',
 0xF283:'queue_message_job_1',0xF293:'queue_message_job_0',0xF28B:'queue_message_job_0_variant',
 0xF26D:'queue_message_job_1_variant',0xE57F:'ppu_reset_or_transition',0xE673:'fade_or_scene_effect',
 0xE68B:'scene_sound_or_effect',0xECEE:'wait_or_job_barrier',0xF2AF:'city_record_pointer',
 0xF2D7:'officer_record_pointer',0xF368:'ruler_record_pointer',0xF387:'initial_officer_pointer',
 0xECBF:'transition_begin',0xF293:'queue_message_job_0'}

def locate(cpu,bank_pair=12):
 if cpu>=0xE000:return 31,0x3E010+cpu-0xE000
 bank=bank_pair+(cpu>=0xC000)
 return bank,16+bank*8192+cpu-(0xC000 if cpu>=0xC000 else 0xA000)

def decode_graph(blob,entry,pair=12):
 nodes={};todo=[entry];issues=[]
 while todo:
  pc=todo.pop()
  if pc in nodes:continue
  if not recovered_address(pc):
   issues.append({'pc':pc,'issue':'tail call outside recovered pair'});continue
  bank,o=locate(pc,pair);op,mode=OPS[blob[o]];size=SIZES[mode]
  raw=blob[o:o+size];value=int.from_bytes(raw[1:],'little');nxt=pc+size
  if op=='?':
   issues.append({'pc':pc,'file':o,'issue':'unofficial opcode or data'});continue
  node={'pc':pc,'bank':bank,'file':o,'op':op,'mode':mode,'operand':value,'raw_hex':raw.hex(' '),'size':size}
  if op in BRANCHES:
   target=(nxt+(value if value<128 else value-256))&65535
   node['taken']=target;node['fallthrough']=nxt;todo.extend([target,nxt])
  elif op=='JSR':
   node['dependency']=HOOK_NAMES.get(value,f'cpu_{value:04X}')
   if value==0xEE07:
    target=int.from_bytes(blob[o+3:o+5],'little');node['far_target']=target
    node['dependency']=f'far_{target:04X}';node['size']=5;nxt=pc+5
   elif value==0xEADE:
    matching=[(table,count) for table,count in [(0xA02E,16),(0xB042,16),(0xADAC,16),*TABLES.values()] if table==nxt]
    if matching:
     table,count=matching[0];targets=[int.from_bytes(blob[locate(table+2*i,pair)[1]:locate(table+2*i,pair)[1]+2],'little') for i in range(count)]
     node['dispatch_targets']=targets;todo.extend(targets);node['fallthrough']=None
     nodes[pc]=node;continue
    issues.append({'pc':pc,'issue':'unclassified inline EADE table'});nodes[pc]=node;continue
   node['fallthrough']=nxt;todo.append(nxt)
  elif op=='JMP':
   if mode=='ab':
    node['taken']=value
    if recovered_address(value):todo.append(value)
    else:node['dependency']=HOOK_NAMES.get(value,f'tail_{value:04X}')
   else:issues.append({'pc':pc,'issue':'indirect jump unresolved'})
  elif op not in ('RTS','RTI','BRK'):
   node['fallthrough']=nxt;todo.append(nxt)
  nodes[pc]=node
 return sorted(nodes.values(),key=lambda x:x['pc']),issues

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
 p.add_argument('--output',type=Path,default=Path('analysis/battle_fsm'));a=p.parse_args()
 blob=a.rom.read_bytes();assert hashlib.sha256(blob).hexdigest()==SHA
 a.output.mkdir(parents=True,exist_ok=True);listings=a.output/'handlers';listings.mkdir(exist_ok=True)
 entries=[];all_nodes={};edges=[]
 for state,main in enumerate(MAIN):
  bank,file=locate(main)
  table,count=TABLES.get(state,(None,1));targets=[]
  if table is None:targets=[main]*count
  else:
   for sub in range(count):
    o=locate(table+sub*2)[1];targets.append(int.from_bytes(blob[o:o+2],'little'))
  substates=[]
  for sub,target in enumerate(targets):
   nodes,issues=decode_graph(blob,target)
   for node in nodes:all_nodes[f"{node['bank']}:{node['pc']}"]=node
   effects=[n for n in nodes if n['op'] in ('STA','STX','STY','INC','DEC') and n['mode'] in ('ab','zp')]
   state_writes=[n for n in effects if n['operand'] in (0x500,0x501,0x7A)]
   deps=[n for n in nodes if 'dependency' in n]
   desc={'state':state,'substate':sub,'entry_cpu':target,'entry_bank':locate(target)[0],
         'entry_file':locate(target)[1],'node_count':len(nodes),'issues':issues,
         'state_writes':state_writes,'dependencies':deps,'nodes':nodes,
         'conditions':[{'cpu':n['pc'],'flag_test':n['op'],'taken':n['taken'],'otherwise':n['fallthrough']} for n in nodes if n['op'] in BRANCHES],
         'delegate_entry_cpu':([0xBAC1,0xBB3D,0xBB93,0xBBA0][sub] if state==15 else None),
         'delegate_entry_bank':(8 if state==15 else None)}
   substates.append(desc)
   lines=[f'; main={state} sub={sub}: {NAMES[state]}',f'; entry bank{locate(target)[0]} ${target:04X}; file ${locate(target)[1]:06X}',
          '; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.']
   for node in nodes:
    _,text=instruction(blob,node['file'],node['pc'])
    lines.append(f"{node['file']:06X} b{node['bank']:02d}:${node['pc']:04X} {node['raw_hex'].upper():<14} {text}"+(' ; '+node['dependency'] if 'dependency' in node else ''))
    if 'far_target' in node:lines.append(f"; inline .word ${node['far_target']:04X}, resumes ${node['pc']+5:04X}")
   (listings/f'state-{state:02d}-sub-{sub:02d}.asm').write_text('\n'.join(lines)+'\n')
  nodes,issues=decode_graph(blob,main)
  for node in nodes:all_nodes[f"{node['bank']}:{node['pc']}"]=node
  entries.append({'state':state,'name':NAMES[state],'entry_cpu':main,'entry_bank':bank,'entry_file':file,
                  'substate_table_cpu':table,'substate_table_file':locate(table)[1] if table else None,
                  'substate_count':count,'substates':substates,'main_issues':issues,
                  'delegate_substate_table':({'bank':8,'cpu':0xBAB9,'file':0x11AC9,'targets':[0xBAC1,0xBB3D,0xBB93,0xBBA0]} if state==15 else None)})
 # Expand all direct calls within the selected pair into executable recovered logic.
 pending=[0xA028];expanded=set();helper_issues=[]
 while pending:
  entry=pending.pop()
  if entry in expanded:continue
  expanded.add(entry)
  nodes,issues=decode_graph(blob,entry)
  helper_issues.extend(issues)
  for node in nodes:
   all_nodes[f"{node['bank']}:{node['pc']}"]=node
   if node['op']=='JSR' and (0xA000<=node['operand']<0xE000 or node['operand'] in FIXED_ENTRIES):pending.append(node['operand'])
 for node in all_nodes.values():
  for kind in ('taken','fallthrough'):
   if node.get(kind) is not None:edges.append({'bank':node['bank'],'cpu':node['pc'],'kind':kind,'target_cpu':node[kind]})
  for target in node.get('dispatch_targets',[]):edges.append({'bank':node['bank'],'cpu':node['pc'],'kind':'inline_dispatch','target_cpu':target})
 payload={'rom_sha256':SHA,'state_variables':{'main':0x500,'sub':0x501,'global':0x7A,'nmi_mode':0x78},
          'main_dispatch':{'cpu':0xA028,'file':0x18038,'table_cpu':0xA02E,'table_file':0x1803E,'count':16},
          'states':entries,'expanded_entry_count':sum(x['substate_count'] for x in entries),
          'control_node_count':len(all_nodes),'control_edges':edges,
          'recovered_fixed_entries':sorted(FIXED_ENTRIES),'scope':'98 local expanded pair12/13 entries plus three additional state15 subdomain aliases, delegated through bank8 BAB3; fixed/far hooks require separate implementations.',
          'not_complete_gameplay':True}
 (a.output/'state-catalog.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp','rel':'rel'}
 lifted=[]
 for node in all_nodes.values():
  item={'pc':node['pc'],'bank':node['bank'],'file':node['file'],'op':node['op'],'mode':modes.get(node['mode'],node['mode']),
        'operand':node['taken'] if node['op'] in BRANCHES else node['operand'],'next_pc':node['pc']+node['size']}
  if node.get('dispatch_targets') is not None:item.update(op='DISPATCH',targets=node['dispatch_targets'])
  elif node.get('far_target') is not None:item.update(op='FARCALL',inline_target=node['far_target'],hook='explicit far dependency')
  elif node['op'] in ('JSR','JMP') and node['operand'] not in {v['pc'] for v in all_nodes.values()}:item['hook']=node.get('dependency','external dependency')
  lifted.append(item)
 (a.output/'program.json').write_text(json.dumps({'rom_sha256':SHA,'instructions':lifted,'helper_issues':helper_issues},ensure_ascii=False,indent=2)+'\n')
 (a.output/'control-program.json').write_text(json.dumps({'rom_sha256':SHA,'nodes':list(all_nodes.values())},ensure_ascii=False,indent=2)+'\n')
 fixed_descriptions={0xE850:'E87A draw AND3 (0..3)',0xE856:'E87A draw AND7 (0..7)',
   0xE862:'Rejection sample below incoming A; bound<15 masks draw to low4 bits; bound0 never terminates',
   0xEA7C:'u16 $01..02 / u16 $03..04; quotient01..02, remainder05..06',
   0xEAA5:'u24 $00..02 / u16 $03..04; quotient00..02, remainder05..07',
   0xEBE9:'u24 $00..02 times u8 $03; full product06..09; inputs/scratch mutated',
   0xF2AF:'City pointer $6000 +32*A -> $00..01; exact registers/flags retained by IR',
   0xF368:'Ruler pointer lookup F379[(A&15)*2] -> $00..01; proven ruler domain0..6'}
 helper_dir=a.output/'helpers';helper_dir.mkdir(exist_ok=True);fixed_index=[]
 for fixed_entry in sorted(FIXED_ENTRIES):
  helper_nodes,helper_errors=decode_graph(blob,fixed_entry)
  fixed_index.append({'entry_cpu':fixed_entry,'bank':31,'file':locate(fixed_entry)[1],
      'description':fixed_descriptions[fixed_entry],'node_count':len(helper_nodes),'issues':helper_errors,
      'source_kind':'independently interpreted recovered IR, no ROM oracle hook'})
  lines=[f'; bank31 ${fixed_entry:04X}, file ${locate(fixed_entry)[1]:06X}', '; '+fixed_descriptions[fixed_entry]]
  for node in helper_nodes:
   _,formatted=instruction(blob,node['file'],node['pc'])
   lines.append(f"{node['file']:06X} b31:${node['pc']:04X} {node['raw_hex'].upper():<14} {formatted}")
  (helper_dir/f'fixed-{fixed_entry:04X}.asm').write_text('\n'.join(lines)+'\n')
 (a.output/'fixed-helper-index.json').write_text(json.dumps({'rom_sha256':SHA,'helpers':fixed_index},ensure_ascii=False,indent=2)+'\n')

 # Durable exact condition/write index for every legal entry.
 md=['# 战场主/子状态逐项索引','',
     '16 个主状态、101 个合法主/子组合：其中 98 个来自 pair12/13 本地表展开；状态15另有3个共享入口的外部子阶段。',
     '每项列出条件分支、状态写入地址、调用依赖和完整原始证据。条件保留6502旗标测试，避免将未知辅助函数的返回值臆译成玩法。','']
 for state in entries:
  md.extend([f"## {state['state']}: {state['name']}",''])
  for sub in state['substates']:
   md.extend([f"### {state['state']}/{sub['substate']} — bank{sub['entry_bank']} ${sub['entry_cpu']:04X} / file ${sub['entry_file']:06X}",''])
   if sub['delegate_entry_cpu'] is not None:md.extend([f"实际委托 bank8 ${sub['delegate_entry_cpu']:04X}。可读语义见 `finalization_phase`；AI武将处理 BC46 仍为显式依赖。",''])
   cond=', '.join(f"${x['cpu']:04X} {x['flag_test']}→${x['taken']:04X} (否则${x['otherwise']:04X})" for x in sub['conditions'])
   writes=', '.join(f"${x['pc']:04X} {x['op']} ${x['operand']:04X}" for x in sub['state_writes'])
   md.extend([f"控制条件：{cond or '无本地条件分支'}。",'',f"控制状态作用：{writes or '此入口不直接修改主/子/global状态'}。",'',
     f"完整流程：[原始指令与调用链](handlers/state-{state['state']:02d}-sub-{sub['substate']:02d}.asm)；可执行逻辑在 program.json。",''])
 (a.output/'all-entries.md').write_text('\n'.join(md)+'\n')
 print(f"Catalogued 16 main states / {payload['expanded_entry_count']} legal expanded entries / {len(all_nodes)} control nodes")
 print('unclassified graph edges',sum(len(s['issues']) for m in entries for s in m['substates']))

if __name__=='__main__':main()
