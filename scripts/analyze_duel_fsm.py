#!/usr/bin/env python3
"""Recover every bounded duel dispatch table and reachable handler as an IR.

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
NAMES={0:"load_records_and_initialize_scene",1:"alternate_actor_and_control",2:"computer_action_selection",3:"apply_regular_strike",4:"retreat_and_pursuit",5:"inspect_officer",6:"surrender_result",7:"persuasion_result_selection",8:"verbal_abuse_status_effect",9:"paired_dialogue",10:"initialize_alias",11:"initialize_alias",12:"initialize_alias",13:"zero_hp_animation",14:"resolve_result_and_return_to_battle",15:"fade_and_restart_attack_scene",16:"action0_motion",17:"action2_motion",18:"action6_motion",19:"motion_return_to_saved_state",20:"motion_outward",21:"motion_inward"}
STATE_LABELS=[
 "读取记录及初始化场景", "轮换行动者与玩家/电脑入口", "电脑动作选择", "普通扣体及确认写回",
 "退却、追击与永久体力扣减", "显示双方武将资料", "投降结果动画", "説得候选结果", "罵倒及04B5持续状态",
 "双方对白及控制回调", "初始化别名0", "初始化别名0", "初始化别名0", "零体力表现",
 "结果与装备奖励、回战斗", "结果淡出、回普通攻击场景", "动作类别0移动表现", "动作类别2移动表现",
 "动作类别6移动表现", "移动归位与恢复保存状态", "向外移动及恢复状态", "向内移动及恢复状态",
]
HANDLER_NOTES={
0:["等待0087 bit7；从两条永久记录读取体力到04B1/B2，按武器ID分动画类；请求左侧精灵", "等待007E&4清零；请求第一组背景精灵", "等待007E&4清零；请求右侧武器精灵", "等待007E&4清零；请求第二组背景精灵，暂置actor=1", "排队双方名称，标记显示更新待处理", "D060写回双方体力并排队显示；设置007E bit2", "由体力、武力及武器/防具修正生成04B3/B4，随机比较选择actor；清04C0", "按双方武器动画类读9项表设置04C5/C6，准备双边对白后去state9"],
1:["处理04C0，轮换actor；更新04B5持续状态与04C3；依04AB/AC决定玩家或电脑", "等待名称/对白队列完成，画主菜单", "读取方向/确认键；动作4「せんじゅつ」进入戦術子菜单或退回", "按04BF分派到4/5/6/7/8或16/17/18；动作3受D262君主条件限制", "等待对白后画戦術菜单", "戦術菜单「せっとく」「ばとう」确认写04BF=选项+7回sub3；取消回sub1"],
2:["以当前体力、原始体力一半、对手体力及君主条件尝试动作3；跳过或前进", "以双方体力差及B7DD随机门槛尝试动作6", "低体力条件及B816随机门槛尝试动作2（保留原字节/寄存器行为）", "比较双方知/武与04B5状态，分别尝试动作7、动作8", "按双方体力三个区间和R(8)查B760动作表；回state1/sub3"],
3:["调用BA15伤害参数，应用类别与04B5效果、判定命中/反伤/零伤；修改临时HP，排队结果对白", "等待双对白队列完成及A/B确认；D060将双方临时HP写入永久记录，等待显示更新", "等待007E bit2清零；优先检查当前actor体力，其次另一方；继续state1或结果2进入state13"],
4:["等待对白；请求当前武将肖像及消息29", "等待确认；排队消息0", "等待对白；保存返回4/sub3，去state20", "轮换actor，请求另一方肖像及消息2A", "确认后以另一方04B3*2与R100比较，去sub9或sub5", "等待对白；保存返回4/sub6，去state21", "对另一方永久记录体力扣R(10)+5，按SBC/BPL裁剪，排队消息3D", "确认后读受击永久体力；非零转BC16；零则排队消息26去sub8", "确认后写另一方结果2，当前方0；去state14，04C0=FF", "等待确认；BC16轮换actor并据控制条件回state1或state2"],
5:["清040C/040D，选定0410武将ID并推进", "显示面板、farcall武将资料；040D=FF才推进并更新窗口参数", "040D负时，按钮位4/5切换双方并回sub0；B按钮回state1/sub2，恢复原actor及窗口参数"],
6:["等待对白，请求武将肖像及消息27", "等待对白确认，设置声音/调色并排队消息0", "等待对白，推进并请求行动方起始精灵", "设04B8计时及04BB位置、调色并请求投降表现精灵", "按04B8>>5的帧索引绘制；帧5排队消息28并推进", "等待对白和确认；actor结果3、另一方0；04C0=80，去state14"],
7:["用对手忠/体及actor知+徳三档索引BFB2表，写04BF和双方对白编号，去state9", "另一方结果1、当前方0；去state15", "双方结果0，04C0=FF；去state14", "等待对白确认；另一方结果4、当前方0，04C0=FF；去state14"],
8:["一次性处理：actor04B5=80；知+徳与对手知差的u8运算、R10和110门槛决定对手04B5持续值，准备双边对白，去state9"],
9:["等待双队列完成；请求第一武将肖像", "请求第二肖像并按04BD排队双方对白", "绘制双方动作参数；等待对白和确认，轮换actor并用04BE排队对方回应", "等待回应及确认，轮换actor；04BF>=2回state7/sub(04BF-1)，否则回state1并清04C3/C4"],
13:["准备零体力姿势/调色与当前方精灵", "设置表现计时及双方位置", "04B8循环到指定帧后排队消息26", "继续绘制；对白完成及确认后去state14，清04C0"],
14:["将双方ID保存到0514/0516；任一结果2去sub2，否则请求淡出并到sub1", "等待0087 bit7；battle0500=11/sub0，global7A=3，恢复050F控制代码并调用ECBF", "结果2对应武将的特殊ID/事件标志奖励分支，可改变胜方武器/防具并排队对白，或直接请求淡出", "等待奖励对白及确认；请求淡出回sub1"],
15:["保存双方ID到0514/0516，推进并请求淡出", "等待0087 bit7；global7A=5，恢复050F控制代码并调用ECBF（回普通攻击场景）"],
16:["请求行动方起始精灵并推进", "初始化04B8/04BB位置并请求武器精灵", "更新横坐标直到接触阈值；等待精灵工作后推进", "设置接触姿势/调色及计时后推进", "设置对侧姿势/调色并推进", "按04B8计时演示攻击帧及音效；指定帧后请求精灵并写03B7..03BC", "去state19/sub0归位，请求归位精灵"],
17:["请求行动方起始精灵并推进", "初始化位置及计时", "按方向移动到接触阈值", "设置类别2动作参数/计时并请求精灵", "持续帧计时和精灵/音效请求", "初始化后半段计时/调色并请求精灵", "设置对侧姿势后推进", "计时完成后去state19/sub0归位；否则演示后半段精灵/音效"],
18:["请求行动方起始精灵并推进", "初始化位置及计时", "按方向移动到接触阈值", "类别6接触动画和帧计时", "类别6连续动画及声音/精灵请求", "动作计时继续并推进", "完成动作表现并推进", "准备归位state19及精灵位置"],
19:["设置归位精灵/调色，初始化04B8并推进", "朝本方起点移动，04BB达18或A8才推进", "从04BD/04BE恢复主/子state，请求对侧武器精灵"],
20:["请求行动方精灵并推进", "初始化04B8及04BB，画外移精灵", "位置向外移动；达08或B8恢复04BD/04BE；按OAM字节计数隐藏越界精灵"],
21:["请求行动方精灵并推进", "初始化04B8及04BB，画内移精灵", "位置向内移动；达B8或08恢复04BD/04BE；按OAM字节计数隐藏越界精灵"],
}
HOOK_NAMES={0xD060:"commit_duel_hp_and_draw_health",0xD166:"draw_active_officer_panel",0xD299:"dialogue_queues_finished",0xD13D:"draw_continue_prompt",0xCDFD:"prepare_character_sprite",0xCEA5:"draw_character_sprite",0xF2D7:"officer_record_pointer",0xF28B:"enqueue_dialogue",0xF26D:"enqueue_dialogue_with_arguments",0xECEE:"begin_palette_fade",0xECBF:"finish_scene_transition",0xE87A:"rng_next",0xE843:"rng_below_100",0xE862:"bounded_rng",0xED1E:"menu_navigation",0xEDF5:"menu_cursor",0xD17C:"draw_action_menu",0xD283:"enqueue_paired_dialogue",0xD262:"officer_is_ruler"}

def analyze(path,out):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 m=bytearray(65536);m[0xa000:0xc000]=raw[16+23*8192:16+24*8192];m[0xc000:0xe000]=raw[16+24*8192:16+25*8192];m[0xe000:]=raw[16+31*8192:16+32*8192]
 cpu=MPU(memory=m);d=Disassembler(cpu)
 tables={}
 for pc in range(0xb100,0xcdfd):
  if m[pc:pc+3]!=bytes.fromhex('20deea'):continue
  start=pc+3;targets=[];bound=0xe000;p=start
  while p<bound and len(targets)<64:
   target=m[p]|m[p+1]<<8
   if not 0xa000<=target<0xe000:break
   targets.append(target)
   if target>=p+2:bound=min(bound,target)
   p+=2
  if p!=bound:raise ValueError(f'Unproved pointer table boundary at {pc:04x}')
  tables[pc]={"call_pc":pc,"table_start":start,"table_end_exclusive":p,"targets":targets,"count":len(targets),"extent_evidence":"Last pointer ends exactly where the earliest forward handler starts"}
 primary=tables[0xb115]['targets'];assert len(primary)==22
 found={};occupied={};edges=[];conflicts=[];hooks={};pending=deque([0xb100]+primary+[x for t in tables.values() for x in t['targets']])
 branches={'BCC','BCS','BEQ','BMI','BNE','BPL','BVC','BVS'}
 while pending:
  pc=pending.popleft()
  while 0xb100<=pc<0xcdfd and pc not in found:
   if pc in occupied:conflicts.append([pc,occupied[pc]]);break
   n,asm=d.instruction_at(pc);op,mode=cpu.disassemble[m[pc]]
   if op=='???':raise ValueError(f'Unsupported opcode at {pc:04x}')
   raw_instruction=bytes(m[pc:pc+n]);operand=int.from_bytes(raw_instruction[1:],'little');next_pc=pc+n
   if op in branches:operand=(pc+2+int.from_bytes(raw_instruction[1:2],'little',signed=True))&65535
   if any(a in occupied for a in range(pc,pc+n)):conflicts.append([pc,'overlap']);break
   for a in range(pc,pc+n):occupied[a]=pc
   item={'pc':pc,'op':op,'mode':mode,'operand':operand,'next_pc':next_pc,'assembly':asm,'bytes_hex':raw_instruction.hex()}
   if pc in tables:
    item['op']='DISPATCH';item['targets']=tables[pc]['targets'];item['next_pc']=None
    for i,target in enumerate(item['targets']):edges.append({'from':pc,'to':target,'kind':'dispatch','index':i});pending.append(target)
   elif op=='JSR' and operand==0xee07:
    item['op']='FARCALL';item['target']=m[pc+3]|m[pc+4]<<8;item['next_pc']=pc+5
    hooks.setdefault('EE07',{'kind':'far_call','call_sites':[]})['call_sites'].append({'pc':pc,'inline_target':item['target'],'bank_selector_register':'Y at call'})
    edges.append({'from':pc,'to':item['next_pc'],'kind':'far_call_returns'})
   elif op in {'JSR','JMP'} and mode=='abs':
    if 0xb100<=operand<0xcdfd:
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
  driver=next((v for v in tables.values() if entry<=v['call_pc']<entry+24),None)
  targets=driver['targets'] if driver else [entry]
  handlers=[]
  for sub,target in enumerate(targets):
   locations=reachable(target);ops=[found[p] for p in locations]
   writes=[v for v in ops if v['op'] in {'STA','STX','STY','INC','DEC'} and v['mode'] in {'abs','abx','aby'}]
   note_state=0 if state in (10,11,12) else state
   handlers.append({'substate':sub,'entry':target,'behavior_note':HANDLER_NOTES[note_state][sub],'instruction_count':len(locations),'conditions':[{'pc':v['pc'],'branch':v['op'],'target':v['operand']} for v in ops if v['op'] in branches],
     'writes':[{'pc':v['pc'],'operation':v['op'],'address':v['operand'],'mode':v['mode']} for v in writes],
     'hooks':sorted({v['hook'] for v in ops if 'hook' in v}), 'far_calls':[{'pc':v['pc'],'target':v['target']} for v in ops if v['op']=='FARCALL'],
     'reachable_locations':locations})
  states.append({'state':state,'entry':entry,'name':NAMES[state],'label_cn':STATE_LABELS[state],'category':'initialization_alias' if state in (10,11,12) else 'animation' if state>=16 or state==13 else 'result_return' if state in (14,15) else 'control', 'label_confidence':'structural/machine behavior; exact menu wording needs UI matching','dispatch_pc':driver['call_pc'] if driver else None,'substate_count':len(targets),'handlers':handlers})
 # Direct predecessor loads identify state writes without inventing path reachability.
 # Full conditions and source PCs remain in each handler's instruction CFG.
 predecessors={}
 for v in found.values():
  if v['next_pc'] is not None:predecessors.setdefault(v['next_pc'],[]).append(v)
 transition_writes=[]
 for state in states:
  for handler in state['handlers']:
   for pc in handler['reachable_locations']:
    v=found[pc]
    if v['op']!='STA' or v['mode']!='abs' or v['operand'] not in (0x04a8,0x04a9,0x007a):continue
    prior=predecessors.get(pc,[])
    load=prior[0] if len(prior)==1 and prior[0]['op']=='LDA' else None
    transition_writes.append({'from_state':state['state'],'from_substate':handler['substate'],'pc':pc,'address':v['operand'],
      'value':load['operand'] if load and load['mode']=='imm' else None,
      'dynamic_source_address':load['operand'] if load and load['mode']=='abs' else None,
      'qualification':'Potential write on a reachable conditional path, not an unconditional edge'})
 report={'rom_sha256':SHA,'main_state_address':0x04a8,'substate_address':0x04a9,'current_actor_address':0x04aa,'entry':0xb100,
   'main_state_count':22,'dispatch_table_count':len(tables),'distinct_subhandler_entries':len(set(x['entry'] for s in states for x in s['handlers'])),'states':states,'dispatch_tables':list(tables.values()),'instruction_count':len(found),'code_bytes':len(occupied),'conflicts':conflicts,'hooks':hooks,'edges':edges,
   'state_transition_writes':transition_writes,
   'completion_scope':'All bounded main/substate control handlers recovered as instruction-level IR; named host helpers and rendering remain explicit dependencies, not silent stubs.'}
 (out/'state_machine.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (out/'program.json').write_text(json.dumps({'rom_sha256':SHA,'instructions':[found[p] for p in sorted(found)]},indent=2)+'\n')
 lines=['; Reachable duel handlers, physical bank23 A000/bank24 C000. Pointer tables excluded.']
 for pc in sorted(found):
  v=found[pc];bank=23 if pc<0xc000 else 24;off=16+bank*8192+(pc-(0xa000 if bank==23 else 0xc000))
  tail=' ; inline targets: '+','.join(f'${x:04X}' for x in v.get('targets',[])) if v['op']=='DISPATCH' else ' ; inline far target $'+format(v['target'],'04X') if v['op']=='FARCALL' else ''
  lines.append(f'${pc:04X} | b{bank} file ${off:06X} | {v["assembly"]}{tail}')
 (out/'handlers.asm').write_text('\n'.join(lines)+'\n')
 (out/'opcodes.json').write_text(json.dumps(dict(Counter(v['op'] for v in found.values())),indent=2)+'\n')
 (out/'state_transitions.json').write_text(json.dumps(transition_writes,ensure_ascii=False,indent=2)+'\n')
 doc=['# 单挑主/子状态逐项目录','', '功能名称结合实际字节读写；退却/投降/説得/罵倒对应已验证的原菜单字形，见phase4/terrain及phase4/duel报告。条件的精确分支目标与全部作用见同条的CFG地址、写入及外部依赖；`handlers.asm`和`program.json`保留每条可执行操作。','', '| 主状态 | 类别 | 入口 | 有效子状态 | 行为 |','|---:|---|---|---|---|']
 for s in states:doc.append(f'| {s["state"]} | {s["category"]} | `${s["entry"]:04X}` | '+('忽略子状态，一次性函数' if s['dispatch_pc'] is None else f'0..{s["substate_count"]-1}')+f' | {s["label_cn"]} |')
 for s in states:
  doc.extend(['',f'## 主状态 {s["state"]}：{s["label_cn"]}',''])
  for h in s['handlers']:
   transitions=[v for v in transition_writes if v['from_state']==s['state'] and v['from_substate']==h['substate']]
   control=[]
   for v in transitions:
    rhs=str(v['value']) if v['value'] is not None else f'读取${v["dynamic_source_address"]:04X}' if v['dynamic_source_address'] is not None else '动态A寄存器'
    control.append(f'`${v["pc"]:04X}`写`${v["address"]:04X}`={rhs}')
   doc.extend([f'### 子状态 {h["substate"]} / `${h["entry"]:04X}`','',h['behavior_note'],'',
     '可能控制转移：'+('；'.join(control) if control else '没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。'),'',
     '条件分支：'+('，'.join(f'`${v["pc"]:04X}` {v["branch"]}→`${v["target"]:04X}`' for v in h['conditions']) or '无'),'',
     '绝对地址写入：'+('，'.join(f'`${v["pc"]:04X}` {v["operation"]} `${v["address"]:04X}`({v["mode"]})' for v in h['writes']) or '无；间接/零页写入见IR'),'',
     '外部依赖：'+(', '.join('$'+v for v in h['hooks']) or '无')+('；farcall '+', '.join(f'`${v["pc"]:04X}`→`${v["target"]:04X}`（Y指定银行）' for v in h['far_calls']) if h['far_calls'] else ''),''])
 (out/'handlers.md').write_text('\n'.join(doc)+'\n')
 attack_table=raw[16+14*8192+0x6f:16+14*8192+0x85]
 attack_targets=[int.from_bytes(attack_table[i:i+2],'little') for i in range(0,len(attack_table),2)]
 assert attack_targets==[0xA085,0xA15F,0xA4F7,0xAA23,0xA3BC,0xCD43,0xCE25,0xCF67,0xACC5,0xB1EC,0xD6BA]
 catalog={'rom_sha256':SHA,'attack_scene_to_duel':{
    'dispatch_bank':14,'dispatch_cpu':0xA06C,'state_address':0x0540,'bounded_table_count':11,
    'table_targets':attack_targets,'duel_index':5,'target_bank':15,'target_cpu':0xCD43,
    'substate_address':0x0541,'substate_targets':[0xCD4F,0xCD59,0xCDCF],
    'handoff_cpu':0xCD59,'prerequisites':['0087 bit7 set','E768 cleanup'],
    'header_cpu_start':0xCD61,'header_cpu_end_exclusive':0xCDCF,
    'effects':'7A=7; clear04A8/04A9/04AA; copy/swap0560/0561 and0562/0563 to04AD/AE and04AB/AC; control3 becomes80'},
    'global_scene_setup':{'bank':31,'cpu':0xE2E8,'incoming_global_state':7,'nmi_mode_address':0x0078,'nmi_mode':5,'outgoing_global_state':8,
      'dependencies':['pair23 A003 background setup','pair29 portrait/dialogue/display setup','fixed-bank scene and palette helpers']},
    'nmi_update':{'bank':31,'nmi_cpu':0xF9A0,'call_cpu':0xF9CD,'pair_selector':0x37,
      'target_bank':23,'public_cpu':0xA01B,'controller_cpu':0xB100,'precondition':'F9A9/F9AB resets007C OAM byte count before callback'},
    'hp_writeback':{'bank':24,'cpu_start':0xD060,'cpu_end_exclusive':0xD074,
      'writes':'side0 then side1 to63C0+12*officerID byte0; same-ID side1 wins; subsequent drawing atD074 external'},
    'return_to_battle':{'bank':24,'cpu':0xC33B,'main_state':14,'substate':1,'global_state':3,'battle_state':11,'battle_substate':0,'dependency':0xECBF},
    'return_to_attack_scene':{'bank':24,'cpu':0xC480,'main_state':15,'substate':1,'global_state':5,'dependency':0xECBF},
    'scope':'Entry/header/control/writeback/return catalog; external scene setup and display work is not claimed independently recovered here.'}
 (out/'entry_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['main_state_count','dispatch_table_count','distinct_subhandler_entries','instruction_count','code_bytes','conflicts']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/duel_fsm');a=p.parse_args();analyze(a.rom,a.out)
