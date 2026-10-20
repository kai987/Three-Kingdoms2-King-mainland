#!/usr/bin/env python3
"""Pin original city-recruitment bytes and the independently written source.

This offline analyzer disassembles the original ROM for review. It never
generates production source, runs original code as a source dependency, or
changes any phase1..20 artifact.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction,OPS
from source.recovered.city_recruitment_services import CityRecruitmentServices,ROM_SHA256
OUT=ROOT/'analysis/phase21/recruitment'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def offset(bank,pc):return 16+bank*8192+(pc&8191)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 receipt=json.loads((OUT/'validation.json').read_text());assert receipt['status']=='passed'and not receipt['quick']
 positions=[];listing=[];dependencies=[];pc=0xC5B9
 while pc<0xC795:
  at=offset(11,pc);size,asm=instruction(rom,at,pc);raw=rom[at:at+size]
  assert asm.split()[0]!='.byte'
  x=dict(physical_bank=11,cpu_address=pc,rom_offset=at,size=size,raw_hex=raw.hex(' ').upper(),assembly=asm)
  positions.append(x);listing.append(f'{at:06X} b11:${pc:04X} {x["raw_hex"]:<11} {asm}')
  if raw[0]in(0x20,0x4C):
   target=int.from_bytes(raw[1:3],'little')
   if not 0xC5B9<=target<0xC795:dependencies.append(dict(call_pc=pc,target=target,kind='tail'if raw[0]==0x4C else'call',raw_hex=x['raw_hex'],rom_offset=at))
  pc+=size
 assert pc==0xC795
 ranges=[]
 for bank,start,length,name in((11,0xC5B9,476,'named recruitment code'),(11,0xC795,5,'difficulty chance bytes'),(31,0xE89A,16,'RNG callee that saves and restores X through0053'),(17,0x8B1C,600,'thirty20byte city appearance year/ID records'),(16,0x9D72,240,'thirty8byte city neighbor records')):
  at=offset(bank,start);raw=rom[at:at+length];ranges.append(dict(physical_bank=bank,cpu_start=start,rom_offset=at,byte_count=length,name=name,raw_hex=raw.hex(' ').upper(),sha256=digest(raw)))
 catalog=dict(schema='phase21-city-recruitment-original-byte-catalog-v1',ROM_sha256=ROM_SHA256,new_manual_instruction_positions=len(positions),new_manual_code_bytes=476,
  pair=[10,11],new_public_entries=[0xC5B9,0xC5D2,0xC66F,0xC6CC],local_only_entries=[0xC71A,0xC765],instructions=positions,original_ranges=ranges,real_dependencies=dependencies,
  reused_dependencies_not_new_manual_code=sorted({x['target']for x in dependencies}),runtime_IR_or_original_CPU=False)
 dump(OUT/'static-catalog.json',catalog);(OUT/'original.asm').write_text('; Original code only; offsets include the16-byte iNES header.\n'+'\n'.join(listing)+'\n')
 vis={(x['physical_bank'],x['cpu_address'])for x in receipt['executed_instruction_positions']};dynamic=sum((11,x['cpu_address'])in vis for x in positions)
 source=ROOT/'source/recovered/city_recruitment_services.py';tree=ast.parse(source.read_text())
 forbidden=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):forbidden.extend(x.name for x in node.names if any(s in x.name.lower()for s in('py65','executor','tactical_ai_control')))
  if isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id in('exec','eval','compile'):forbidden.append(node.func.id)
 assert not forbidden
 counts=receipt['counts'];full=[x for x in receipt['cases']if x['case'].startswith('full-scan/')]
 actual=[x for x in receipt['cases']if x['domain']=='actual_saved_Native_context_original_CPU_callee']
 source_paths=('source/recovered/city_recruitment_services.py','source/recovered/city_recruitment_integration.py','source/recovered/negotiation_services.py','source/recovered/domestic_secondary_services.py','source/recovered/domestic_cooperation_controller.py','source/recovered/scene_shared_services.py','source/recovered/global_ui_controller.py','source/recovered/nestopia_context.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py','scripts/analyze_city_recruitment_services.py','scripts/verify_city_recruitment_services.py','scripts/trace_city_auxiliary_runtime.py')
 evidence=dict(schema='phase21-named-city-recruitment-readable-evidence-v1',ROM_sha256=ROM_SHA256,source_file=str(source.relative_to(ROOT)),source_sha256={p:sha(ROOT/p)for p in source_paths},
  production_original_CPU_callbacks=0,production_IR_interpretation=False,production_runtime_codegen=False,
  validation=dict(path=str((OUT/'validation.json').relative_to(ROOT)),sha256=sha(OUT/'validation.json'),status=receipt['status'],original_CPU_parent_cases=receipt['original_CPU_parent_cases'],counts=counts,source_guard_count=receipt['source_guard_count'],actual_saved_context_callee_cases=len(actual)),
  coverage=dict(static_new_manual_instruction_positions=len(positions),new_manual_code_bytes=476,dynamically_executed_new_manual_positions=dynamic,not_dynamically_executed=len(positions)-dynamic,all_paths_or_all_inputs_proven=False),
  source_equivalence_contract=dict(RAM_bytes=2048,SRAM_bytes=8192,registers=['A','X','Y','P','SP','PC'],ordered_IO_reads_and_writes=True,all_four_PRG_banks=True,N163_RAM_address_and_autoincrement=True,free_stack_exclusions=0,Native_internal_CPU_trace=False),
  domains=dict(controlled_numeric_and_caller_fixtures='Explicit per-case data and real software frame shapes. They do not establish natural gameplay reachability.',actual_saved_context_callees='OriginalCPU continuation from a saved Native actualREG/MAP/N163 context, with no new PC/caller/RNG/request/ready preparation. No new interrupts are scheduled.',raw_suffix='FirstFF offsets1/27..31 and full-Y failure deliberately bypass the parent capacity guard; demonstrate raw alias mechanics, not valid natural UI reachability.'),
  semantics=dict(driver='C5B9 visits all30cities, appearance before unaffiliated. A successful C6CC discards its own caller frame and exits the city scan through the true outer caller.',appearance='C5D2 owned city, random<10, prefix roster count<10, original rawyear subtraction gate, status1,90/10 probability, status2 and firstFF append. No guessed ten-pair or FF terminator replaces the original year gate.',unaffiliated='C6CC owner, difficulty chance bytes, prefix count<10; neighboring city list; C71A scans statuslow2==0 and tests90/10 then residence=currentcity or one of8neighbors. No HP filter.',preference='Ruler4 IDs109/112/55/183/144; ruler2 IDs86/99/57/165/156; ruler3 IDs107/234/235/213/47 receive90, all others10.',commit='Status low2=2 retaining high6; append at firstFF; recalculate loyalty; residencebyte5 and HP unchanged; no invented gold fee or recruitment UI acknowledgement.',firstFF='Raw byteY increments and wraps. If noFF exists in all256 reachable positions the source yields a real loop-wait boundary and resumes the same original loop. It neither supplies a terminator nor fabricates a return.',raw_year='C616 retains its raw8bit index and rawyear-100 wrap. YEAR>=155 can pass FF/yearFF; the source does not add a fictitious sentinel or ten-pair bound.'),
  superseding_phase20_erratum=dict(prior_incomplete_claim='An internal E89A write to X was treated as a net X clobber and prevented a237-record bound.',original_E89A_bytes=ranges[2]['raw_hex'],corrected_no_interrupt_contract='E89A saves X at0053, uses cursor0054, then restores X before actualRTS. With C66F X passthrough, C71A scans IDs0..236 exactly if no success.',ordinary_scan_addresses=dict(first_status=0x63CB,last_status=0x6EDB,record_count=237,final_pointer22=0x6EDC),interrupt_limit='No claim is made that a midcallee Native NMI modifies0053. That requires actual passive observation; the normal-return proof does not supply a timing model.',full_scan_cases=[dict(case=x['case'],records=x['scanned_record_count'],E89A_calls=x['uninterrupted_E89A_calls'])for x in full],phase20_frozen_files_unchanged=True),
  artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm')})
 dump(OUT/'evidence.json',evidence)
 (OUT/'README.md').write_text(f'''# 城市登场与在野录用

[CityRecruitmentServices](../../../source/recovered/city_recruitment_services.py) 独立手写 physical11 `C5B9..C794`，通过具名函数实现城市登场、偏好概率、在野录用、首FF写入与实际双PLA返回。新手工范围是225个原指令位置/476B；`C690..C6CB` 是偏好分支的一部分，包含在此范围。城市指针/资源限制、名册前缀计数、君主定位、忠诚和固定RNG/mapper服务复用冻结的独立源码。生产侧不执行ROM/CPU、不解释IR、不读取程序JSON或运行时生成代码。

`C5B9` 对30城依次先做登场，再做在野录用。`C5D2` 要求owner低3位等于当前君主、原随机门槛小于10、首FF前人数少于10，然后按原城市ID/年表判断。年字节先减100再与原年度比较；不存在额外添加的十项上限或FF终止规则。普通年度的FF/yearFF会被年份门槛挡住；raw年度155及以后可能进入其后机器字节，保留原条件和明确执行预算。

`C6CC` 在owner、原难度概率及名册容量通过后准备8个邻城，进入`C71A`。只对status低2位为0的记录作概率和所在地检查；所在地是本城或邻城时提交。它没有HP检查。君主4的109/112/55/183/144、君主2的86/99/57/165/156、君主3的107/234/235/213/47得到90阈值，其余为10。成功保留status高6位、将低2位置2、写入首FF、重新计算忠诚；不改体力或所在地，不附加金币费用。

成功路径`C792/C793`的两次PLA丢弃C6CC返回层，再RTS到外层。正常`C5B9`父驱动拥有这个真实caller；单独调用C6CC/C71A/C765可能返回`nonlocal_return`，绝不冒充本层RTS。容量由父流程首FF前人数判断；直接绕过这个门槛的裸suffix仍按8位Y扫描，可访问城市tail/下一记录。全256个位置无FF时是原无限循环；源码报告`waiting`并保留栈/循环，不写假FF、ready或ack。

## 237项边界与阶段20勘误

固定`E89A`完整字节为`{ranges[2]['raw_hex']}`。它保存X到0053，使用0054随机游标，最后恢复X再RTS。阶段20只看到内部写X而未完整纳入返回恢复，因而对237项循环界限的保留判断不完整；本轮补充覆盖它，旧阶段20文件保持原字节。

在无新增中断的普通callee合同下，`C66F`和`E89A`均保持X，所以未成功的`C71A`恰扫237个记录：ID0..236、status有效地址63CB..6EDB，结束pointer22为6EDC。四个完整扫描例都验证这一点；status0且所在地不合格的例实际调用E89A {full[0]['uninterrupted_E89A_calls']}次，其他status例不调用该内部随机服务。这里不声称已经观察到Native中断覆盖0053，也不将这段扫描误称HP维护。后续首FF扫描是另一个未定界的raw循环。

## 原CPU差分范围

当前{receipt['original_CPU_parent_cases']}个独立原CPU父用例：{counts.get('actual_caller_RTS',0)}个真实caller RTS、{counts.get('actual_nonlocal_return',0)}个真实非局部返回、{counts.get('original_loop_wait',0)}个原循环等待、{counts.get('strict_missing_dependency_prefix',0)}个缺服务严格前缀；另{receipt['source_guard_count']}个源码guard。其中{len(actual)}个从保存的Native actualREG/MAP/N163上下文通过原CPU真实前序产生callee输入，其余数值/帧fixture逐例明示。它们不冒充原Nestopia内部CPU录制。比较完整2048B RAM（含全部栈残余）、8192B SRAM、AXYP/SP/PC、有序IO读写、四个PRG银行及N163 RAM/地址/自增，无闲置栈排除，source CPUcallbacks为0。

新body动态命中{dynamic}/{len(positions)}个原指令位置；这是位置覆盖，不是所有路径或全部输入证明。HP0/1/99/FF、记录0/109/236、所在地本城/邻城/不合格、偏好全256byte、年份门槛、名册空洞/满额/裸tail别名、无FF循环和缺固定服务分别列明。正式阶段20自然母档没有status0在野将；该原机路线的237次空扫不能作为成功录用实证，原机成功证据由runtime域单列。

```python
rules = CityRecruitmentServices(memory, rom, services=readable_services)
rules.run_entry(0xC5B9, registers=actual_caller_registers)
rules(service_call)  # 原physical10/11与真实caller帧
rules.resume()       # 同一pending服务/循环，无自动确认
```

PUBLIC继承Negotiation既有入口并加C5B9/C5D2/C66F/C6CC；C71A/C765仅定向LOCAL。新组合入口`CityRecruitmentGameEngine`保留旧1..20源码不变，真正A000调用通过具名方法别名进入本轮实现；裸C6CC非局部终点保持terminal，重复同call不再pop。

```sh
.venv-trace/bin/python scripts/verify_city_recruitment_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_recruitment_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原字节](original.asm) · [静态目录](static-catalog.json) · [差分回执](validation.json) · [证据](evidence.json) · [有效地址CPU轨迹](../cpu/runtime-trace.json)
''')
 print(json.dumps(dict(status='written',source_sha256=sha(source),static=len(positions),dynamic=dynamic,CPU=receipt['original_CPU_parent_cases'],counts=counts,guards=receipt['source_guard_count'])))
if __name__=='__main__':main()
