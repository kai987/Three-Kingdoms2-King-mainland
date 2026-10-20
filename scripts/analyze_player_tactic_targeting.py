#!/usr/bin/env python3
"""Emit pinned all16 player qualifiers, original inline tables and scope."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.player_tactic_targeting import TargetingData,ROM_SHA256,PLAYER_ENTRIES
from inspect_game_data import disassemble
RULES=[
 '目标class0或2','目标class0或4','目标class0或4','目标class0或4','目标class3','目标槽0或10',
 '目标class5且施放者与目标正交相邻','目标class0/4且有任一对施放侧的敌方正交邻格单位',
 '目标class≠5（没有AI忠诚判定）','施放者class4/5且正交相邻，目标class≠5（与AI相反）',
 '目标class3且有敌方正交邻格单位class3','施放者class0、完整raw16兵>=100、本侧缓存slot==FF',
 '目标class3且有敌方正交邻格单位class3','施放者class5且正交相邻',
 '目标class≠5且有敌方正交邻格单位class≠5','目标class≠3且≠5（没有AI武知/兵判定）']
NAMES=['火計','陥穽','虚兵','要撃','乱水','火箭','偽撃転殺','共殺','籠絡','落石','連環','十面埋伏','水攻','連弩','劫火','奇門遁甲']
RANGES=[('cursor_enemy_and_range_prefix',12,0xA000,0xA9FC,0xAA1D),('full_16_qualification',12,0xA000,0xAD80,0xB02B),
 ('coordinate_distance',12,0xA000,0xB860,0xB8A1),('highest_coordinate_match',13,0xC000,0xD6B6,0xD6CC),
 ('player_terrain_lookup',13,0xC000,0xDB46,0xDB9E),('terrain_class_table',13,0xC000,0xDB9E,0xDC1E),
 ('opposite_side_lookup',13,0xC000,0xDC4B,0xDC63)]
DATA={12:[(0xADAC,32,'EADE16 entry words')],13:[(0xDB70,2,'EE07 inline entry A012')],}
def analyze(rom,out):
 data=TargetingData.from_rom(rom);out.mkdir(parents=True,exist_ok=True);ranges=[];listing=[]
 for name,bank,base,start,end in RANGES:
  offset=16+bank*8192+start-base;raw=rom[offset:offset+end-start]
  ranges.append(dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,raw_hex=raw.hex(' '),byte_count=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
  listing.append(f'; {name} originalbank{bank} ${start:04X}..${end-1:04X}\n')
  if name=='terrain_class_table':listing.append(f'{offset:06X} .byte '+', '.join(f'${b:02X}'for b in raw)+'\n');continue
  cursor=start
  for address,size,label in DATA.get(bank,[]):
   if not start<=address<end:continue
   listing.append(disassemble(rom,bank,base,cursor,address));o=16+bank*8192+address-base
   if size==32:
    for i,target in enumerate(PLAYER_ENTRIES):listing.append(f'{o+2*i:06X} b12:${address+2*i:04X} .word ${target:04X} ; ID{i} {NAMES[i]}\n')
   else:listing.append(f'{o:06X} .word ${int.from_bytes(rom[o:o+size],"little"):04X} ; {label}\n')
   cursor=address+size
  listing.append(disassemble(rom,bank,base,cursor,end))
 (out/'original-ranges.asm').write_text(''.join(listing))
 source=ROOT/'source/recovered/player_tactic_targeting.py';v=json.loads((out/'validation.json').read_text())
 assert v['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
 assert v['validator_sha256']==hashlib.sha256((ROOT/'scripts/verify_player_tactic_targeting.py').read_bytes()).hexdigest()
 pins=[]
 for p in(source,ROOT/'source/recovered/tactical_decisions.py',ROOT/'source/recovered/terrain_semantics.py',ROOT/'source/recovered/battle.py',ROOT/'source/recovered/game_enums.py',ROOT/'scripts/verify_player_tactic_targeting.py',Path(__file__)):
  pins.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 for entry in v['native_snapshot_inputs']:
  for prefix in('header','RAM','SRAM'):
   assert hashlib.sha256((ROOT/entry[prefix+'_path']).read_bytes()).hexdigest()==entry[prefix+'_sha256']
 imports=[n.module for n in ast.walk(ast.parse(source.read_text()))if isinstance(n,ast.ImportFrom)]
 assert all(not any(term in(module or'')for term in('py65','state_machine','control','trace'))for module in imports)
 tables=[]
 for name,o,n in [('player_AP_cost_ABC9',0x18BD9,16),('map_chunk_pointers_bank8_B7CB',0x117DB,240),('map_chunk_selectors_bank8_B8BB',0x118CB,120)]:
  raw=rom[o:o+n];tables.append(dict(name=name,rom_offset=o,byte_count=n,raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
 chunk_tables=[]
 for i,pointer in enumerate(data.tactical.chunk_pointers):
  bank=data.chunk_banks[i];o=16+bank*8192+pointer-0x8000
  chunk_tables.append(dict(chunk=i,physical_bank=bank,cpu=pointer,rom_offset=o,byte_count=256,sha256=hashlib.sha256(rom[o:o+256]).hexdigest()))
 e=dict(rom_sha256=ROM_SHA256,source_kind='independent readable all16 player qualifiers; not original source, no IR/CPU executor',dependency_pins=pins,source_ast_imports=imports,ranges=ranges,tables=tables,map_chunks=chunk_tables,
  APIs=['PlayerTacticTargeting(shared_memory, TargetingData.from_rom(rom), data_window_bank=None)','eligible(tactic_id, data_window_bank=None)','eligibility_suffix(tactic_id,target_terrain,actor_terrain)','can_target(tactic_id,actor_slot,target_slot,data_window_bank=None)'],
  rules=[dict(id=i,name=NAMES[i],physical_bank=12,cpu=target,rom_offset=0x18010+target-0xA000,rule=RULES[i],returned_carry_when_eligible=True,player_AP_cost=data.player_costs[i])for i,target in enumerate(PLAYER_ENTRIES)],
  boundaries=dict(eligible='FullAD80 prelude and selectedpredicateRTS. Caller supplies actualselectedslots; no generalenemy/range filter isinsideAD80.',suffix='ADA4 after0A/0B actualterrainprelude; classesareexplicitbyteinputs.',
   can_target='Cursor game checks: enemy byDC4B, write0509onlyafterenemycheck, normalizedmaxaxisdistance<6, thenAD80. ID11forces selftarget and bypassesenemyfilter. Ends beforeUI messagepreparation.',
   AP='16byte ABC9costtablequoted. Availability/menu selection AP checks and actualAA96 debit are outside, no AP mutation.',probability='B7BE/B739 outcomechance is distinct and not invoked here.',
   map='DB46classlookup, raw6/7/8 foldedto2; RAM/SRAM/ROMdescriptor guards; logicaldatawindowfollowsF266 but CPUmapperwrites excluded.'),
  quirks=['AE2D y>=16 is reduced1; neighborqueries y15 is convertedto16.', 'D6B6 highest matching slot wins; no officerFF filter added, and duplicatefriendly can hide lowerenemy.', 'ID11 reads complete raw16 officer bytes8/9, not low10; anynonzerohighbyte passes100 condition.', '04D8/04DC cache occupancy checks onlyslot==FF, notTTL.', 'Player9 target!=5 contrasts withAI9 target==5; Player8 and15 do notcopy AIstat requirements.'],
  native_snapshot_inputs=v['native_snapshot_inputs'],validation={k:v[k]for k in('status','rom_cpu_case_count','original_complete_case_count','original_prefix_case_count','source_guard_case_count','failed_count','compared_SRAM_bytes','declared_RAM_ranges','original_instruction_locations')})
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 (out/'README.md').write_text(f'''# Phase9：玩家16项计略目标资格

`PlayerTacticTargeting` 独立恢复 bank12 AD80 完整地形前序、16项分派和所有实际资格分支到RTS，没有解释IR、原ROM fallback或自动确认。资格和施放成功概率分开；它是重构源码，不是原作者源码。

| ID | 正式名称 | 原入口 | 原玩家资格，C=1成立 | 玩家AP表报价 |
|---:|---|---|---|---:|
'''+''.join(f'| {i} | {NAMES[i]} | {p:04X} | {RULES[i]} | {data.player_costs[i]} |\n'for i,p in enumerate(PLAYER_ENTRIES))+f'''
`eligible(id)` 对当前050A/0509执行完整AD80资格；`eligibility_suffix(id,target_terrain,actor_terrain)` 适用于真实地形前序已执行的ADA4后缀。`can_target(id,actor,target)` 增加cursor敌方和距离<6前缀，ID11实际以自己为目标且绕过敌方筛选。该便利API明确选择050A/0543，敌方检查失败保留原0509；不输入按键、不排消息、不扣AP、不执行effect。菜单学会/可选条件是另一个前序。

玩家落石要求施放者class4/5、正交相邻、目标class≠5；AI落石恰好要求目标class5。玩家籠絡只有class≠5，没有AI忠诚条件；玩家奇門遁甲只有class≠3/5，没有AI武知/兵门槛。不能用 `ai.action_predicate`替代本表。B7BE的概率阈值有signed8回绕与夹5..95，强知力差可能回绕成5；选中合法目标不保证成功。本模块不会抽RNG或改变结果。

邻接先把raw y>=16减1；格子查询把normalized y15转raw16。原D6B6从19倒序找第一个坐标匹配，未检查0664是否FF；重叠的高slot友军会遮住低slot敌军。ID11的兵>=100读取完整raw16，byte9非零即通过，不把兵高6清掉；缓存只检查slotFF，不检查TTL。AP表只报价，真正扣费位于后续AA96；AI11绕过该消费表的差异由effects模块负责。

地图数据来自pinROM静态chunk/terrain表。ROM descriptor需明确当前data_window_bank或mappedmemory.banks[0]；一次资格内部按实际F266改变逻辑数据窗口，不写真实mapper。RAM/SRAM四字节descriptor和chunk0..119有guard。共享memory可与统一GameEngine直接复用。

最终 **{v['rom_cpu_case_count']}原CPU、{v['source_guard_case_count']} source guards、{v['failed_count']}失败**，分为{v['original_complete_case_count']}完整资格RTS和{v['original_prefix_case_count']}明确cursor前缀。完整8KiB SRAM、声明RAM0A/0B、10/11、0509/050A、0543及原返回carry一致；其他flags/registers/stack/mapper/CPU工作字节不在高层合同。覆盖全部16项、有效和极值classes、同坐标/正交/间隔、最高槽优先、双方side、raw16兵临界与缓存、ROMdescriptor上下文。实验表外ID不运行原ROM表外代码。

另复用正式native10case（8个计略以及陥穽death/落石levelup）的target-cursor/cast-confirmation RAM/SRAM作为20次CPU输入，全部通过；每个headerJSON、RAM和SRAM SHA固定。cursor样本只把已经正式confirmed的目标作为原AA03选择输入，未称它是快照当时已经选中的0509。独立原core回放/图形成功证据由runtime报告提供，这20次不新增nativeframes或自然可达主张。未引用exploratory文件。

`evidence.json`固定7段原bytes、inline16项地址表、AP报价、mapchunk和依赖hash；`original-ranges.asm`把EADE表和EE07内联word标为数据。`executed-instructions.json`列{v['original_instruction_locations']}个实际地址，不代表每个分支的动态覆盖。

```python
targeting = PlayerTacticTargeting(shared_memory, TargetingData.from_rom(rom))
result = targeting.eligible(9)  # completeAD80资格
result = targeting.can_target(9, 10, 1)  # cursor玩法检查，无UI或施放
```

```sh
.venv-trace/bin/python scripts/verify_player_tactic_targeting.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_player_tactic_targeting.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 print(json.dumps(dict(original_ranges=len(ranges),ROM_bytes=sum(r['byte_count']for r in ranges),source_sha256=v['source_sha256'],rom_cpu_cases=v['rom_cpu_case_count'],source_guards=v['source_guard_case_count'],formal_native_cases=len(set(r['case']for r in v['native_snapshot_inputs']))),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/targeting');a=p.parse_args();analyze(a.rom.read_bytes(),a.out)
