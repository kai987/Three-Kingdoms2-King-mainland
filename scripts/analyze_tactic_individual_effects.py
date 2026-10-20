#!/usr/bin/env python3
"""Pin original byte provenance for the three independent individual effects."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.tactic_individual_effects import IndividualData,ROM_SHA256,EFFECT_ENTRIES
from inspect_game_data import disassemble
RANGES=[('effect_dispatch',12,0xA000,0xB02B,0xB062),('trap',12,0xA000,0xB0DD,0xB155),
 ('troop_damage',12,0xA000,0xB188,0xB1D5),('fire_arrow',12,0xA000,0xB243,0xB2CD),
 ('rockfall',12,0xA000,0xB3B6,0xB3D0),('HP_and_death',12,0xA000,0xB5D8,0xB643),
 ('troop_settlement',12,0xA000,0xB68B,0xB6F0),('grain_loss',12,0xA000,0xB6F0,0xB72B),
 ('probability_gate',12,0xA000,0xB7BE,0xB860),('death_map_refresh',13,0xC000,0xD6CC,0xD751),
 ('XP_trampoline',14,0xA000,0xA009,0xA00C),('XP_arithmetic',15,0xC000,0xD7FB,0xD8D4),
 ('remove_trampoline',8,0xA000,0xA02A,0xA02D),('remove_slot_cache',9,0xC000,0xD6CD,0xD70F),
 ('raw_officer_pointer',31,0xE000,0xF2D7,0xF308)]
DATA={12:[(0xB042,32,'effect entry pointer table'),(0xB62D,2,'EE07 inline entry A009'),(0xB640,2,'EE07 inline entry A02A'),(0xB6ED,2,'EE07 inline entry A006'),(0xB85A,6,'distance correction bytes')],13:[(0xD731,2,'EE07 inline entry A012; graphics service prefix only')],15:[(0xD85B,14,'seven XP threshold words')]}
def analyze(rom,out):
 IndividualData.from_rom(rom);out.mkdir(parents=True,exist_ok=True);ranges=[];listing=[]
 for name,bank,base,start,end in RANGES:
  offset=16+bank*8192+start-base;raw=rom[offset:offset+end-start]
  ranges.append(dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
  listing.append(f'; {name} bank{bank} ${start:04X}..${end-1:04X}\n');cursor=start
  for address,size,label in sorted(DATA.get(bank,[])):
   if not start<=address<end:continue
   listing.append(disassemble(rom,bank,base,cursor,address));o=16+bank*8192+address-base
   listing.append(f'{o:06X} b{bank:02}: ${address:04X} .byte '+', '.join(f'${v:02X}'for v in rom[o:o+size])+f' ; {label}\n');cursor=address+size
  listing.append(disassemble(rom,bank,base,cursor,end))
 (out/'original-ranges.asm').write_text(''.join(listing))
 source=ROOT/'source/recovered/tactic_individual_effects.py';v=json.loads((out/'validation.json').read_text())
 assert v['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
 pins=[]
 for p in(source,ROOT/'source/recovered/battle.py',ROOT/'source/recovered/game_algorithms.py',ROOT/'scripts/verify_tactic_individual_effects.py',Path(__file__)):
  pins.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 rea=[]
 for p in(ROOT/'analysis/rea/pairs/pair-12/procedure-index.json',ROOT/'analysis/rea/pairs/pair-12/functions/0xb02b.asm',ROOT/'analysis/rea/pairs/pair-12/functions/0xb02b.c'):
  if p.exists():rea.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 imports=[n.module for n in ast.walk(ast.parse(source.read_text()))if isinstance(n,ast.ImportFrom)]
 assert all(not any(term in(module or'')for term in('py65','state_machine','control','trace'))for module in imports)
 e=dict(rom_sha256=ROM_SHA256,source_kind='independent readable game algorithms, not original source; no ROM/IR executor',dependency_pins=pins,source_ast_imports=imports,ranges=ranges,REA_archive=rea,
  REA_limit='Existing mapped pair12 analysis discovers B02B dispatcher but does not resolve the 16 inline entry pointers. Original effect bytes and farcall inline words were separately decoded.',
  APIs=['IndividualTactics(shared_memory, IndividualData.from_rom(rom))','apply(1|5|9)','health_loss(byte)','grain_loss(word,side_offset=0|2)','after_death_graphics(map_refresh_returned=True)'],
  entries={str(k):v for k,v in EFFECT_ENTRIES.items()},
  death=dict(prefix_stop_pc=0xB615,real_dependency='bank13 D6CC CALL, no source stub',resume_pc=0xB618,caller_signal_required=True,asynchronous_ack=False,
   XP='full16 dead martial+intelligence then floor/2, u16 XP wrap/cap49999/single-level advancement',removal='six unit arrays and6FA1 FF, first matching entire4B cache row FF',
   no_city_or_ruler_transfer=True,no_army_count_or_total_accounting=True,graphics_service_test_count=len(v['graphics_services']),
   tested_service_SRAM_writes=sum(len(r['host_SRAM_written'])for r in v['graphics_services'])),
  distinctions=dict(effect_probability_not_target_eligibility=True,cast_AP_outside=True,grain='raw16 opposite-side 0522/0524',troop_damage='masked10 target troops then clear byte9 high6; u16 report accumulation',
   HP='u8 saturated HP, zero includingzero/zero marks record11|3',HP_formula='u8 martial+IQ wraps before quotient; level+quotient u8; multiply5..7 then /10',
   rockfall='HP first, real death service if required, live troop phase next, final substate7',
   internal_FF='legitimate removal clears0664; next F2D7(FF) maps6FB4, preserved with full SRAM parity. Initial FF selected officer is rejected.',
   aliases='same record and same slot retain live read/write order; killXP may change martial before troop phase'),
  validation={k:v[k]for k in('rom_cpu_case_count','source_guard_case_count','failed_count','original_complete_case_count','original_death_prefix_case_count','original_post_graphics_suffix_case_count','compared_SRAM_bytes','declared_RAM_ranges','original_instruction_locations')})
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 (out/'README.md').write_text(f'''# Phase9：陥穽、火箭、落石独立效果源码

三项实际 effect handler 的玩法逻辑已还原为 `IndividualTactics`，不解释 IR、不执行 ROM、不用图形空函数。它是重构源码，不是原作者源码。入口前提是 B02B 的真实结果区清零已经完成；目标资格、玩家/AI扣AP、消息与图形流程另有边界。玩家落石资格排除 terrain5，AI资格要求 terrain5，两者不影响共用 B3B6 的概率及效果体。

| ID | 原 bank12 入口 | 成功效果 |
|---:|---|---|
| 1 陥穽 | B0DD | B7BE概率；B0EB计算HP损失；存报告；sub++ |
| 5 火箭 | B243 | 对侧raw16军粮乘10..14%取整，加知力/5；饱和扣粮与报告；sub++ |
| 9 落石 | B3B6 | 先完整HP阶段，后以实时record计算兵损；最终sub=7 |

HP伤害的武力+知力先发生8bit回绕；死亡XP使用两者完整16bit和，不能混用。HP=0（包括0扣0）设record11|3；活分支完整RTS。死亡在 B615 调用真实 D6CC 前停止，返回 dependency。只有该 CALL 实际返回后显式调用 `after_death_graphics(map_refresh_returned=True)`，才计算杀将XP、报告死者ID、清槽和首个匹配缓存，并继续原handler。False/漏传不会推进；这不是异步任务确认。原D6CC仍未恢复为高层图形源码。

死亡路径没有 C91E 的阵营人数/总兵记账，也没有城市/君主/名册转属；尸体record兵字节不被HP阶段清除。落石的后续兵损在死亡清掉0664后按真实 F2D7(FF) 指向6FB4的AI工作SRAM，保留该原quirk；不把旧死者ID补回。同槽/同record与杀将升级后武力变化按原顺序保留。兵损读取low10并清byte9高6；火箭读取完整16bit军粮，不读取目标兵数。

最终 {v['rom_cpu_case_count']} 次原CPU比较、{v['source_guard_case_count']} guards，{v['failed_count']}失败：{v['original_complete_case_count']}完整RTS例，{v['original_death_prefix_case_count']}死亡前缀与{v['original_post_graphics_suffix_case_count']}真实图形CALL后续分别计数。每例完整8KiB SRAM和validation声明RAM一致；不声明寄存器、flags、stack、mapper、arithmetic scratch或完整NMI等价。141次实际D6CC在这些输入中均未写SRAM或声明玩法RAM，仍由验证器真实执行并记录host字节差异，绝不假完成。自然核心施放证据在本阶段独立runtime报告，不由这组CPU fixture推导。

`original-ranges.asm`明确EE07后inline entry word和XP阈值表不是指令；`evidence.json`逐段固定ROM偏移/bytes/SHA与已读REA存档。`validation.json`固定本源码及validatorhash，`executed-instructions.json`列949个实际原指令位置，不表示所有分支动态覆盖。

```python
effects = IndividualTactics(shared_memory, IndividualData.from_rom(rom))
result = effects.apply(9)
# 如果result为dependency，host实际执行D6CC后：
result = effects.after_death_graphics(map_refresh_returned=True)
```

```sh
.venv-trace/bin/python scripts/verify_tactic_individual_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactic_individual_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 print(json.dumps(dict(ranges=len(ranges),ROM_bytes=sum(r['byte_count']for r in ranges),source_sha256=v['source_sha256'],rom_cpu_cases=v['rom_cpu_case_count'],guards=v['source_guard_case_count']),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/individual');a=p.parse_args();analyze(a.rom.read_bytes(),a.out)
