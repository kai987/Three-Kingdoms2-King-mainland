#!/usr/bin/env python3
"""Original-byte provenance for named postbattle release and known producers.

The seven AND-FC/indirect-store motifs are an exhaustive byte-pattern census,
not a universal proof that no other whole-record or differently coded writer
can produce status0. Native observation and CPU fixtures remain separate.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction
from source.recovered.postbattle_release_services import ROM_SHA256
OUT=ROOT/'analysis/phase22/release';PROD=ROOT/'analysis/phase22/producers';CPU=ROOT/'analysis/phase22/cpu'
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def off(b,p):return 16+b*8192+(p&8191)
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rawrange(rom,bank,start,end,name):
 at=off(bank,start);raw=rom[at:at+end-start]
 return dict(physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=at,byte_count=len(raw),name=name,raw_hex=raw.hex(' ').upper(),sha256=digest(raw))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True);PROD.mkdir(parents=True,exist_ok=True)
 receipt=json.loads((OUT/'validation.json').read_text());assert receipt['status']=='passed'and not receipt['quick']
 pos=[];lines=[];pc=0xD1F9;deps=[]
 while pc<0xD2CD:
  at=off(13,pc);size,asm=instruction(rom,at,pc);b=rom[at:at+size]
  x=dict(physical_bank=13,cpu_address=pc,rom_offset=at,size=size,raw_hex=b.hex(' ').upper(),assembly=asm);pos.append(x)
  lines.append(f'{at:06X} b13:${pc:04X} {x["raw_hex"]:<11} {asm}')
  if b[0]==0x20:
   t=int.from_bytes(b[1:3],'little')
   if not 0xD1F9<=t<0xD2CD:deps.append(dict(call_pc=pc,target=t,kind='fixed_service'if t>=0xE000 and t!=0xE856 else'frozen_direct_local_source',rom_offset=at,raw_hex=x['raw_hex']))
  pc+=size
 assert pc==0xD2CD
 catalog=dict(schema='phase22-named-postbattle-release-byte-catalog-v1',ROM_sha256=ROM_SHA256,new_manual_instruction_positions=len(pos),new_manual_code_bytes=212,instructions=pos,
  original_ranges=[rawrange(rom,13,0xD1F9,0xD2CD,'selected-officer allocation,release and removal'),rawrange(rom,16,0x9D72,0x9E62,'thirty8byte neighbor records')],real_dependencies=deps,
  aliases={'local_d1f9':'settle_selected_officers','local_d20d':'settle_one_selected_officer'},new_local_entry=0xD299,ordinary_parent='Frozen BattleSceneController uses bound-method aliases; no new software frame is added')
 dump(OUT/'static-catalog.json',catalog);(OUT/'original.asm').write_text('; Offsets include16-byte iNES header.\n'+'\n'.join(lines)+'\n')
 vis={(p['physical_bank'],p['cpu_address'])for p in receipt['executed_instruction_positions']};dynamic=sum((13,p['cpu_address'])in vis for p in pos)
 source=ROOT/'source/recovered/postbattle_release_services.py';tree=ast.parse(source.read_text())
 assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('exec','eval','compile')for n in ast.walk(tree))
 paths=('source/recovered/postbattle_release_services.py','source/recovered/wild_recruitment_integration.py','source/recovered/battle_scene_controller.py','source/recovered/city_recruitment_services.py','source/recovered/city_recruitment_integration.py','source/recovered/scene_coordinator.py','source/recovered/nestopia_context.py','source/recovered/service_memory.py','scripts/verify_postbattle_release_services.py','scripts/analyze_postbattle_release_services.py','scripts/trace_wild_recruitment.py')
 counts=receipt['counts'];domains=dict(Counter(x['domain']for x in receipt['cases']))
 evidence=dict(schema='phase22-named-postbattle-release-readable-evidence-v1',ROM_sha256=ROM_SHA256,source_sha256={p:sha(ROOT/p)for p in paths},
  production_original_CPU_callbacks=0,production_IR_interpretation=False,production_runtime_codegen=False,
  validation=dict(path=str((OUT/'validation.json').relative_to(ROOT)),sha256=sha(OUT/'validation.json'),original_CPU_parent_cases=receipt['original_CPU_parent_cases'],counts=counts,domains=domains,source_guard_count=receipt['source_guard_count']),
  coverage=dict(new_manual_positions=len(pos),new_manual_code_bytes=212,dynamically_executed_new_manual_positions=dynamic,not_dynamic=len(pos)-dynamic,all_inputs_or_paths_proven=False),
  exact_scope=dict(RAM_bytes=2048,SRAM_bytes=8192,registers=['A','X','Y','P','SP','PC'],ordered_IO_reads_and_writes=True,all_four_PRG_banks=True,N163_RAM_address_and_autoincrement=True,free_stack_excluded_bytes=0),
  semantics=dict(selection='D1F9 checks20 flags0580..0593; any nonnegative byte selects the corresponding042C row. PHA/PLA preserves row over the callee.',release='D20D destination0540==30; preserve status high6, clear low2; F266 bank16; E856 original random8; location=8neighbors of050E, signed-negative neighbor falls back to050E.',ordinary_destination='BC11 firstFF pointer is reused. Destination city roster gets the ID, commander052B updates052C. Neutral owner&7==7 uses(original&F0)|selected_side_ruler_low4, preserving the exact F0 mask.',cleanup='D299 first match in20 active IDs wins and clears six arrays; otherwise clear first match in40 contiguous captive bytes. No city-roster cleanup, health/troop/loyalty rewrite, or capacity guard is invented.',caller='D20D completes an actual localRTS; D1F9 preserves its own caller and row frames. Existing battle phases invoke these aliases directly.',waiting='Missing F2D7/F266 or any reused dependency retains the real callee frame. No NMI/text acknowledgement is generated.'),
  origin_limits=dict(controlled='1362 numeric/caller CPU cases are explicit fixtures, not natural gameplay.',pure='Native actual saved-PC originalCPU continuation, no new interrupt, no PC/stack/RNG/request/ready preparation.',hardware_fixture='Release callback input needs one explicitly scheduled real6502 NMI plus ordinary A-port data. It is labelled separately and is not an actual internal Native register trace.'),
  artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm')})
 dump(OUT/'evidence.json',evidence)
 # Exhaustive exact-motif byte census; each context below is separately
 # decoded as a real officer-field write, rather than treating every mask as
 # an officer status operation.
 producers=[
  dict(bank=8,mask=0xBD2F,store=0xBD31,start=0xBD28,end=0xBD59,parent='8 A006→BAB3 postbattle side controller→BC46 result dispatch→no destination path',condition='Actual temporary officer list6FA1; nonleader when no return-city destination. Leader takes OR3 instead.',location='Random8 neighbor of050E; negative neighbor falls back to050E.',roster='Does not itself delete a city roster entry; surrounding postbattle parent owns assignment.',native_observed_this_phase=False),
  dict(bank=10,mask=0xAC2F,store=0xAC31,start=0xAC21,end=0xAC67,parent='10 A000→A00F battle-return handling→ABA3 return/redistribution',condition='No same-side neighbor with capacity and no neutral fallback city.',location='Original E89A sampled current/neighbor location; negative neighbor rejected and resampled.',roster='Parent manages departed unit and city roster; this suffix clears status and writes location.',native_observed_this_phase=False),
  dict(bank=11,mask=0xCBE0,store=0xCBE2,start=0xCB81,end=0xCC12,parent='Domestic CA19→CB52 successor→CB81 followers',condition='Recalculated loyalty<31 and original random100<20; firstFF/newleader can terminate the city prefix.',location='Currentcity0045.',roster='ID is retained by this clear path; unlike player release no immediate left-shift.',native_observed_this_phase=False),
  dict(bank=13,mask=0xCDCC,store=0xCDCE,start=0xCD9C,end=0xCDF2,parent='8 A006 player-controlled side→battle main13/sub1 CD52→BB84 return-city candidates',condition='After real A/ready, return-city candidate count is zero; selected nonleader entries become status0, ruler leader becomes status3.',location='Battlecity050E.',roster='Uses D0E1 active/captive postbattle list until FE; subsequent parent leaves battle.',native_observed_this_phase=False),
  dict(bank=13,mask=0xD21F,store=0xD221,start=0xD1F9,end=0xD2CD,parent='Player postbattle main13 or14→destination list special30→officer multi-select→confirmation→D1F9→D20D',condition='RealUI produces destination30 and selected nonleader flags; bare D20D does not repeat that predicate.',location='Random8 neighbor of050E; negative neighbor falls back to050E.',roster='Clears first active/captive match; city names are not separately rewritten byD20D.',native_observed_this_phase=True),
  dict(bank=26,mask=0xC09D,store=0xC09F,start=0xC099,end=0xC0E5,parent='Player city13 succession BE01→family classification→C01E followers→C099',condition='Recalculated loyalty<31, E843 random100<20, officer!=successor040D.',location='Currentcity040E.',roster='Left-shift through26 and fillFF; if all tenFF set entire ownerbyte7; messageD4 waits normally.',native_observed_this_phase=False),
  dict(bank=26,mask=0xC325,store=0xC327,start=0xC318,end=0xC342,parent='Computer city13 succession C132→C289 followers→C318',condition='Compared pointer22 loyalty<31, E843 random100<20, currentID!=successor; family-exemption can leave pointer22 stale.',location='Unchanged.',roster='Remove current roster slot and fillFF; pointer22 may be an earlier valid officer record on family early-return path.',native_observed_this_phase=False),
 ]
 matches=[]
 for bank in range(32):
  b=rom[16+8192*bank:16+8192*(bank+1)]
  for index in range(len(b)-2):
   if b[index:index+3]==bytes.fromhex('29fc91'):matches.append((bank,index))
 assert set(matches)=={(x['bank'],x['mask']&8191)for x in producers}
 producer_lines=[]
 for x in producers:
  x['mask_rom_offset']=off(x['bank'],x['mask']);x['store_rom_offset']=off(x['bank'],x['store']);x['original_range']=rawrange(rom,x['bank'],x['start'],x['end'],x['parent'])
  pc=x['start'];producer_lines.append('\n; '+x['parent'])
  while pc<x['end']:
   at=off(x['bank'],pc);size,asm=instruction(rom,at,pc)
   # Decode inline EE07 pointer bytes as data, never as following opcodes.
   if rom[at:at+3]==bytes.fromhex('2007ee'):
    size=5;asm+=' ; inline target$'+f'{int.from_bytes(rom[at+3:at+5],"little"):04X}'
   producer_lines.append(f'{at:06X} b{x["bank"]:02d}:${pc:04X} {rom[at:at+size].hex(" ").upper():<14} {asm}');pc+=size
  assert pc==x['end']
 (PROD/'original.asm').write_text('; Seven literal status-clear motifs; no universal arbitrary-writer proof.\n'+'\n'.join(producer_lines)+'\n')
 dump(PROD/'catalog.json',dict(schema='phase22-known-status0-producers-v1',ROM_sha256=ROM_SHA256,verified_direct_clear_motif_count=7,producers=producers,all_PRG_exact_AND_FC_indirect_store_motif_matches=len(matches),
  exclusions=['Cold/reset zero-filled SRAM is not an unaffiliated officer population.','Statuslow2==3 is not a release; OR3 death/deletion paths are separate.','Initial record/template copies are whole data initialization, not normal release commands.'],
  limits=['The byte-pattern census covers this exact direct AND-FC/STA-indirect form; arbitrary whole-record writers, aliases or different instruction encodings are not universally excluded.','A code-reachable parent condition is not evidence that every producer was exercised in Native.','No normal city-menu dismissal command is claimed; the zero-write Native route uses ordinary battle retreat and destination30.']))
 dump(PROD/'evidence.json',dict(schema='phase22-status0-producer-provenance-v1',status='bounded_catalog',ROM_sha256=ROM_SHA256,source_CPU_cases=0,verified_direct_clear_motif_count=7,
  source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(PROD/'catalog.json',PROD/'original.asm')}))
 (PROD/'README.md').write_text('''# 在野状态的已证生产者

从全部32个PRG银行逐字节寻找`AND #FC; STA (zp),Y`形式，共7处；每处另核真实code上下文、record指针和Y=11，确认其低2位清0。这个精确模式的穷举**不是**任意whole-record复制、不同编码或非法指针别名的全ROM排除证明。冷启/重置SRAM全0也不当作237个合法在野将；死亡OR3和初始模板复制分别处理。本目录Source CPUcases=0，不重复计算新服务矩阵。

| 实际写PC | 完整父流程条件 | 所在地/名册副作用 | 本轮原机 |
|---|---|---|---|
|8:BD31|A006→BAB3电脑战后分配，无法回城的非君主|本城/随机邻城；君主另OR3|未观察|
|10:AC31|原AI战后回城分配，没有同方可用邻城或中立后备|原随机当前/邻城，负邻城重试|未观察|
|11:CBE2|Domestic CA19继承后CB81，忠诚<31且原抽样<20|byte5=当前城，ID仍留名册|未观察|
|13:CDCE|人类战后主13/sub1，BB84没有任何可回目的城|非君主清0且byte5=战斗城；君主OR3|未观察|
|13:D221|战后主13/14，真实目的地特殊项30、多选非君主、确认|byte5=本城/随机邻城，清首个active或俘虏项|**真实普通退却→原菜单→5/30释放**|
|26:C09F|人类city13继承C01E，忠诚<31、原抽样<20、非新君主|byte5=城，名册左移，空城整个owner=7，消息D4|未观察|
|26:C327|电脑city13继承C289/C318，指针忠诚<31、原抽样<20、非新君主|不改byte5，移除当前名册项；family早返可留旧22指针|未观察|

没有确认一个普通城市菜单的“解雇/放逐”命令。26:C099机械释放曾被早期报告简称“放逐”，但完整父流程实际是继承低忠诚离去，本轮不延用菜单猜名。实际零新增数据写入的可执行路线是：原城11选择131/5/30出征，曹操普通退却，战后目的城列表选末项30，再选择5/30并确认；原机在frame7635写出两条status0。随后按原正常月轮推进，ruler4城2在frame14837把5录用为status2，原忠诚86→90、byte5保持2。

主13/14的正常城市分配和特殊30是同一个D1F9/D20D父结算体；新手写源码212B及精确差分见[新服务](../release/README.md)。此处其他6个父链仅原字节/冻结源码上下文证实，不能改称本轮Native动态执行。所有具体原偏移、字节和SHA见[catalog](catalog.json)与[原汇编](original.asm)。
''')
 (OUT/'README.md').write_text(f'''# 战后释放与分配的具名源码

[PostbattleReleaseController](../../../source/recovered/postbattle_release_services.py) 手写恢复 physical13 `D1F9..D2CC` 的212B/106个原指令位置：选中武将逐一处理、普通城市分配、特殊目的地30释放、六个active数组或俘虏表清除。它继承冻结BattleSceneController，只替换`local_d1f9/local_d20d`绑定；真实主13/14父流程保持原JSR栈。生产没有ROM执行、IR或CPU fallback。

`D1F9`遍历0580的20个标记，所有非负值都表示选中。`D20D`在0540==30时保留status高6位、清低2位，再用原E856和bank16邻城表选择所在地；负邻城则用原战斗城050E。它不检查或改HP、兵数、忠诚。接着`D299`先找20个active ID的首个相等项，清六数组；没有则找连续40个俘虏ID并仅清首项，不删除城市名册。

普通目的城也完整具名编排：复用原BC11的城市指针和首FF，追加ID、必要时更新052C首将目的地；原中立owner使用`(owner&F0)|side_ruler_low4`，保留F0掩码，不能简化成F8。父UI负责真实城市容量、不可释放君主和选中行资格，直接D20D入口不重新伪造这些资格。所有固定服务保留真实调用帧；没有自动text/IRQ/NMI ready。

当前{receipt['original_CPU_parent_cases']}个原CPU父例：{counts.get('actual_caller_RTS',0)} RTS、{counts.get('actual_nonlocal_return',0)}非局部返回、{counts.get('strict_missing_dependency_prefix',0)}严格依赖前缀；另{receipt['source_guard_count']} guards，全部通过。比较完整2048B RAM、8192B SRAM、AXYP/SP/PC、有序IO、四PRG银行与N163状态，无自由栈排除。新106/106位置动态命中，但不代表全部输入或路径。域计数：`{json.dumps(domains,ensure_ascii=False)}`。

1362个数值/软件caller矩阵是明确CPU fixture。正式保存点导出的pure continuation与显式硬件NMI释放夹具按origin分别记录；后者只在CPU模型安排一次真实NMI栈协议和A端口输入，不是Native内部callee寄存器录制。新22矩阵也复验冻结21录用源码在实际成功输入下的完整父返回/双PLA非局部返回，不改21任何文件。

```python
controller = PostbattleReleaseController(memory, rom, services=readable_services)
controller.run_entry(0xD1F9, registers=actual_caller_registers)
# 主A000/A028仍通过原父调用方法绑定进入新具名函数。
```

```sh
.venv-trace/bin/python scripts/verify_postbattle_release_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_postbattle_release_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原字节](original.asm) · [静态目录](static-catalog.json) · [差分](validation.json) · [证据](evidence.json) · [status0生产者目录](../producers/catalog.json) · [原机路线](../runtime/README.md)
''')
 print(json.dumps(dict(status='written',source_sha256=sha(source),static=len(pos),dynamic=dynamic,CPU=receipt['original_CPU_parent_cases'],counts=counts,domains=domains,producer_clear_motifs=len(producers))))
if __name__=='__main__':main()
