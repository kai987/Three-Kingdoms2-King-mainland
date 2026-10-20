#!/usr/bin/env python3
"""Emit pinned original-byte provenance for readable tactical8strategy source."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.tactical_strategy_ai import StrategyData,ROM_SHA256,STRATEGY_ENTRIES
from inspect_game_data import disassemble
RANGES={
 'cooperative_scan':(0xA02D,0xA099),'strategy_dispatch':(0xA099,0xA0B1),
 'strategy0':(0xA0B1,0xA105),'strategy1':(0xA105,0xA166),'strategy2':(0xA166,0xA210),
 'strategy3':(0xA210,0xA2AD),'strategy4':(0xA2AD,0xA329),'strategy5_resupply':(0xA329,0xA507),
 'strategy6_heal':(0xA507,0xA606),'strategy7_none':(0xA606,0xA60C),
 'basic_pipeline':(0xA95C,0xA9CF),'basic_chooser':(0xA9CF,0xAAF8),'special_pipeline':(0xAAF8,0xAB68),
 'special_chooser':(0xAB68,0xAC65),'special_whitelist':(0xAC65,0xAC7B),
 'predicate_setup':(0xAC7B,0xACAE),'predicate_table':(0xACAE,0xACCE),'predicate_bodies':(0xACCE,0xAE93),
 'raw16_rank':(0xAE93,0xAF0D),'retreat_and_destination':(0xAF0D,0xB067),
 'army_totals':(0xB067,0xB0B8),'resupply_demand':(0xB0B8,0xB130),
}
STRATEGY_FLOW=[
 '退却→特殊计略；非负side基础计略；负side相邻攻击→基础计略→low2 RNG决定不行动或朝slot0移动',
 '退却→特殊计略→AP>=2且邻接对侧首槽攻击→对侧首槽/城市原base坐标移动',
 '退却→特殊计略→相邻攻击→actor radius2第一最近敌移动；无候选对侧首槽/base坐标移动',
 '退却→特殊计略→相邻攻击→本侧首槽radius2第一最近敌；其邻居存在友军非首槽则基础计略否则靠近；无候选基础计略后本侧首槽移动',
 '退却→特殊计略→相邻攻击→actor radius3第一最近敌移动；无候选基础计略后本侧首槽移动',
 '原service0坐标移动→预测下一原坐标命中后markstrategy7→资源word预算/缺粮/报价分支',
 '原service2坐标移动→预测命中后markstrategy7→资源>=50先扣50→拒绝抽low4<11加35→u8加体力后按初始体封顶',
 '直接status3',
]

def analyze(rom,out):
 data=StrategyData.from_rom(rom);out.mkdir(parents=True,exist_ok=True);ranges=[];listing=[]
 for name,(start,end)in RANGES.items():
  offset=0x10010+start-0xA000;raw=rom[offset:offset+end-start]
  ranges.append(dict(name=name,physical_bank=8,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,raw_hex=raw.hex(' '),byte_count=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
  listing.append(f'; {name}, originalbank8 ${start:04X}..${end-1:04X}\n')
  if name=='strategy_dispatch':
   listing.append(disassemble(rom,8,0xA000,start,0xA0A1))
   for i,target in enumerate(STRATEGY_ENTRIES):
    o=0x100B1+2*i;assert int.from_bytes(rom[o:o+2],'little')==target
    listing.append(f'{o:06X} b08:${0xA0A1+2*i:04X} .word ${target:04X} ; strategy{i}\n')
  elif name=='predicate_table':
   for i in range(16):
    o=offset+2*i;target=int.from_bytes(rom[o:o+2],'little');listing.append(f'{o:06X} b08:${start+2*i:04X} .word ${target:04X} ; tactic{i}\n')
  elif name=='special_whitelist':listing.append(f'{offset:06X} .byte '+', '.join(f'${b:02X}'for b in raw)+'\n')
  else:listing.append(disassemble(rom,8,0xA000,start,end))
 (out/'original-ranges.asm').write_text(''.join(listing))
 source=ROOT/'source/recovered/tactical_strategy_ai.py';pins=[]
 for p in(source,ROOT/'source/recovered/tactical_decisions.py',ROOT/'source/recovered/ai.py',ROOT/'source/recovered/terrain_semantics.py',ROOT/'scripts/verify_tactical_strategy_ai.py',Path(__file__)):
  pins.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 def table(name,offset,size):
  raw=rom[offset:offset+size];return dict(name=name,rom_offset=offset,byte_count=size,raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest())
 tables=[table('city_neighbors_bank16_9D72',0x21D82,240),table('city_base_pointer_bank6_8C52',0xCC62,60),table('serviceXY_bank17_9BA4',0x23BB4,180),table('resource_quotes_bank16_8FC0',0x20FD0,60),table('initial237officer_records_bank17',0x22010,2844)]
 bases=[]
 for city in range(30):
  pointer=int.from_bytes(rom[0xCC62+2*city:0xCC64+2*city],'little');offset=0xC010+pointer-0x8000
  bases.append(dict(city=city,physical_bank=6,cpu_pointer=pointer,rom_offset=offset,raw_y_x=list(rom[offset:offset+2]),source_x_y=data.city_base_xy[city],sha256=hashlib.sha256(rom[offset:offset+2]).hexdigest()))
 model_ast=ast.parse(source.read_text());imports=[node.module for node in ast.walk(model_ast)if isinstance(node,ast.ImportFrom)]
 assert all(module not in('tactical_ai_control','battle_state_machine','py65')for module in imports)
 result=dict(rom_sha256=ROM_SHA256,source_kind='independent high-level gameplay algorithms; not original game source, no IR interpretation/ROM execution',source='source/recovered/tactical_strategy_ai.py',source_ast_imports=imports,dependency_pins=pins,ranges=ranges,tables=tables,city_base_records=bases,
  strategy_flows=[dict(id=i,cpu=entry,rom_offset=0x10010+entry-0xA000,priority=STRATEGY_FLOW[i],scope='complete original strategy body gameplay effects')for i,entry in enumerate(STRATEGY_ENTRIES)],
  APIs=['step(maximum_strategy_calls=256,data_window_bank=None)','run_strategy(id,data_window_bank=None)','retreat()','retreat_destination()','army_totals()','resupply()','heal()','plan_tactic(special=False,data_window_bank=None)'],
  basic_chooser=dict(knowledge_tiers=[dict(minimum=minimum,tier=tier)for minimum,tier in[(0,1),(40,3),(60,5),(75,7),(85,9)]],priority=[dict(action=a,minimum_tier=t,minimum_AP=p,requires_target_raw_troops=troops)for a,t,p,troops in[(6,6,8,True),(5,5,8,False),(8,8,10,False),(9,9,9,True),(7,7,8,True)]],random_branch='predicate1; rejectlow2==0 or low2==3 withtargettroops0;3→action3 tier>=3 AP>=6;1→action2 tier>=2 targetlowcondition0 AP>=4;2→action1 AP>=5;thenbreak even failed',fallback='action4 tier>=4 targettroops AP>=7, thenaction0 targettroops AP>=6; no successstatus3'),
  special_chooser=dict(gate='actor IQ>=92 and level=byte11>>4>=3',whitelist_ids=list(ai_ids()),priority='level3 whitelist21:10 condlow0 AP9 then11 AP10; level4 suffix11 +targettroops:12 AP10 then13 AP8; level5 suffix17+troops:14 AP12; onlyID109 level>=6 condhigh0:15 AP10; all require exact terrain/adjacency predicate'),
  retreat=dict(leader='rawtroops<301 AND hp<51',commander='if ownrawsum<1757 and ownrawsum+3499<enemyrawsum thenforce; else rawtroops<101 AND hp<41',officer='rawtroops<201 AND hp<100 then accepted0..99<70',destination='negative side052A; positive sidefirstsameowner neighbor with anyFF10-slot roster, otherwiselastneutral neighbor; signbyte rejects finaldestination'),
  resupply=dict(arrival='predict raw nextXY before real coordinatecommit; no row15 skip; markstrategy7 first',demand='floor(4*ownraw16sum/1000)*((30-round)&255), low16',budget='floor(gold*7/10), low16',shortage='(demand-currentgrain)&65535',cost='floor(shortage*100/price), low16; zero divisor originalFFFF quotient lowword',unaffordable='spendbudget; gainfloor(budget*price/100), low16',resource_writes='u16 subtract/add wrap; no speculative clamps'),
  heal=dict(arrival='same rawXY precommit guard, mark7 evenifgold<50',cost='50 fromside0526word before draw',random='reject RNGlow4>=11 then add35 (35..45)',health='(oldHP+heal)&255 then min with pinnedinitialHP'),
  context=dict(shared_memory=True,mutable_sram=[0x6000,0x8000],declared_gameplay_ram=[[0x42C,0x42F],[0x4D8,0x4E0],[0x500,0x678]],CPU_registers_flags_stack_mapper_excluded=True,logical_data_window='publicstep/run_strategy/directplan_tactic sync physical banks[0] or explicitdata_window_bank; internalF266-deriveddata reads change logicalbank only; flatRAM must explicitly report externalbank changes',map_descriptor_domain='fourbytesRAM<=07FC/SRAM6000..7FFC/dataROM8000..9FFC; ROMdescriptorneeds known currentbank; selectedchunks0..119',source_guard_domains='strategy0..7, city0..29, selectedruler0..6, actorslot0..19, selectedofficer0..236, physicaldatabank0..31, nonnegativebudget'),
  scope=['All8strategy bodies and A02D gameplay cooperation are independent algorithms; oldIR retained separately as a CPUcontract reference.', 'No proposal effect/AP debit/renderer acknowledgement is manufactured bystrategyAI.', '2F sortinput is maintained; arbitrary internalzero-page scratch is outside equivalence.', 'Complete step can explicitly stopbudget atpendingstrategy with partialactualwrites; budgetprefix countedseparately.', 'Nativeframe snapshots in CPUfixtures do not prove additionalnaturalframes or tactic reachability.'])
 (out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 v=json.loads((out/'validation.json').read_text());assert v['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest();assert v['validator_sha256']==hashlib.sha256((ROOT/'scripts/verify_tactical_strategy_ai.py').read_bytes()).hexdigest()
 readme=f'''# Phase8：完整8项战术策略的独立可读源码\n\n`source/recovered/tactical_strategy_ai.py` 用独立玩法算法恢复策略0..7及A02D合作扫描，完整退却、资源补给、体力治疗、基础/特殊计略选择与目标筛选。没有执行/解释IR、原ROM CPUfallback、图形空hook或自动ack。它不是原始游戏源码，CPU寄存器/stack/flags/mapper协议仍由旧完整IR控制器提供独立参考。\n\n## 接口与输入合同\n\n```python\nai = TacticalStrategyAI(shared_memory, StrategyData.from_rom(rom))\nresult = ai.step()\nresult = ai.run_strategy(4)\n```\n\n构造和调用可传 `data_window_bank`。MappedMemory入口每次读当前`banks[0]`，一次完整update内部独立跟踪原F266引起的数据read窗口；不写真实mapper。Flat64K没有bank元数据，外部host改窗口时必须明确传新的bank，不能依赖旧缓存。ROM地址的A8/A9地图描述必须有已知data bank。四项descriptor限定原RAM/SRAM/8000..9FFF数据窗，chunk0..119；不读取表外代码。真实native snapshots的descriptor在RAM00AA，12项另外的完整策略fixture核对了ROM描述数据及内部银行变化。\n\n`step()`是完整合作更新，`run_strategy(0..7)`是完整单项策略。另公开`retreat()`、`retreat_destination()`、`army_totals()`、`resupply()`、`heal()`及`plan_tactic(special=False)`。`maximum_strategy_calls=0`会停止在真实下一strategy边界，返回budget与已发生写入，不伪造完成。\n\n源码共享RAM/SRAM，声明玩法RAM为042C..042E、04D8..04DF、0500..0677，完整比较8KiB SRAM。2F排序输入及6F93保存X副作用保留；其他CPU临时scratch、寄存器/flags/栈和真实mapper写入不在高层等价合同内。无需静默猜入口X：0..4先经AF0D原LDX0504；治疗draw前固定sideoffset0/2；basicdraw前predicate建立X；其余完整路径按真实次序传播。\n\n## 8项策略次序\n\n| ID | 原bank8入口 | 独立恢复的实际优先次序 |\n|---:|---|---|\n''' + ''.join(f'| {i} | {entry:04X} | {STRATEGY_FLOW[i]} |\n'for i,entry in enumerate(STRATEGY_ENTRIES)) + f'''\n“首槽”为0/10；表有8项，低nibble8..15非法。strategy是现代行为编号，不是正式原菜单名称。普通计略ID和移动方向编码分开。提案status0/1/2/3/4依旧由战场消费者解释；本策略源不会替施放统一扣AP（尤其AIID11的原消费路径另有合同）。\n\n## 精确选择、退却和作用顺序\n\n基础计略按知力分档1/3/5/7/9，radius5候选按raw16兵数降序排序；等值也swap，排序pass使用原2F而不假定无限完整sort。优先6(tier6/AP8/目标有兵)、5(tier5/AP8)、8(tier8/AP10)、9(tier9/AP9/有兵)、7(tier7/AP8/有兵)。随后predicate1通过才抽low2：0拒绝、3且目标无兵也拒绝；3→action3(tier3/AP6)、1→action2(tier2/目标conditionlow4=0/AP4)、2→action1(AP5)。接受抽样但对应门槛失败也结束该随机分支；再尝试4(tier4/有兵/AP7)、0(有兵/AP6)。所有16项地形/邻接/武知忠/预备槽谓词都独立执行实际规则，没有接受值stub。\n\n特殊入口要求知>=92、byte11high4>=3。原21项白名单level3尝试10(condlow4=0/AP9)后11(AP10)；白名单suffix11 level4且目标有兵尝试12(AP10)/13(AP8)；suffix17 level5有兵尝试14(AP12)；仅ID109 level6且目标condhigh4=0尝试15(AP10)。每项仍需真实谓词。成功提案写6F8D/6F8E/6F8F=2；失败门槛和未找到目标保留原先写入次序。\n\n退却使用完整raw16兵数。君主record：兵<301且体<51；非君主首槽：本军总兵<1757且本军+3499<敌军时强制，否则兵<101且体<41；其他武将：兵<201且体<100，再抽0..99<70。负侧目的地052A；正侧扫描8个邻城，第一个同owner且10项名册中有FF的城市优先，否则最后中立城。不假定中立城名册必空，最终负号目的地失败。\n\n补给预测下一原XY到service0，先把策略低nibble改7，再算资源。需求先`floor(4*本军raw16总兵/1000)`，再乘`(30-round)&255`取low16；预算`floor(gold*7/10)`；缺粮为u16回绕减法，不能clamp零。成本按城市实际quote计算；不足预算分支把全部budget换粮。全部资源加减保持u16回绕。\n\n治疗预测到service2亦先mark7，gold<50仍保留该写入；足额先扣50，再拒绝抽low4>=11，得到35..45治疗。HP先u8加法回绕，之后才按原初始体力封顶。两个service预测都没有实际coordinatecommit的row15跳跃；不得因“合理路径”补修原算法。\n\n## 原ROM差分与范围\n\n最终 **{v['rom_cpu_case_count']} 原CPU例、{v['source_guard_case_count']}项source guards，{v['failed_count']}失败**。其中完整原例{v['original_complete_case_count']}，明确budgetprefix {v['original_prefix_case_count']}另列。CPUfixture包含完整策略、退却threshold角色、rawwordwrap、资源不足、治疗、全部requestbyte、basic/special真实pipeline、平局/passcounter和13个nativecheckpoint复用输入。每例完整8KiB SRAM与声明RAM一致；不声称CPU寄存器/mapper等价、自然玩法可达、完整frame执行或所有分支动态覆盖。\n\n`validation.json`固定源码/validatorhash；`evidence.json`固定22段原bytes与immutabletables/共享源码依赖；`original-ranges.asm`明确两张inline表不是指令；`executed-instructions.json`列实际Oracle地址。原ROM保持pinSHA，只在验证脚本由py65执行原instructions。\n\n```sh\n.venv-trace/bin/python scripts/verify_tactical_strategy_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'\n.venv-trace/bin/python scripts/analyze_tactical_strategy_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'\n```\n'''
 (out/'README.md').write_text(readme)
 print(json.dumps(dict(ranges=len(ranges),original_bytes=sum(r['byte_count']for r in ranges),rom_cpu_cases=v['rom_cpu_case_count'],source_guards=v['source_guard_case_count'],source_sha256=v['source_sha256']),indent=2))
 return result

def ai_ids():
 from source.recovered.ai import SPECIAL_OFFICERS
 return SPECIAL_OFFICERS

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase8/strategies');a=p.parse_args();analyze(a.rom.read_bytes(),a.out)
