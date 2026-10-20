#!/usr/bin/env python3
"""Pin one G086 pointer lifetime and the new hand-written UI helper bodies.

This analyzer reads frozen original-byte catalogs. It never runs a frozen
generator, writes production source, or counts an address ledger as execution.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from source.recovered.city_ui_controller import ROM_SHA256
OUT=ROOT/'analysis/phase24/lifecycle';CPU=ROOT/'analysis/phase24/cpu-lifecycle'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def off(pc):return 16+28*8192+(pc&8191)
def import_native_callees():
 """Import sparse passive-observer software state, with honest device scope."""
 native=ROOT/'analysis/phase24/runtime';manifest=native/'evidence.json';receipt=json.loads(manifest.read_text());assert receipt['status']=='passed'
 imported=[];pins={str(manifest.relative_to(ROOT)):sha(manifest)}
 for path in sorted((native/'observer').glob('callee-*.json')):
  x=json.loads(path.read_text());assert x['entry']in(0xD64A,0xD987)and x['actual_registers']['pc']==x['entry']
  ram_path=path.parent/x['exported_RAM'];sram_path=path.parent/x['exported_SRAM'];ram=ram_path.read_bytes();sram=sram_path.read_bytes()
  assert len(ram)==2048 and len(sram)==8192 and sha(ram_path)==x['RAM_sha256']and sha(sram_path)==x['SRAM_sha256']
  r=x['actual_registers'];sp=r['sp'];word=ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8
  assert word==x['stack_top_word_raw']and tuple(x['actual_PRG_banks'][1:3])==(27,28)
  folder=CPU/'actual-callers'/f'entry-{x["entry"]:04X}-observer-{x["snapshot_sequence"]:04d}'
  folder.mkdir(parents=True,exist_ok=True);(folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram)
  n163=bytes((11+37*i)&255 for i in range(128));(folder/'input-n163.bin').write_bytes(n163)
  context=dict(schema='phase24-passive-Native-callee-with-device-fixture-v1',origin='passive_Native_callee_capture_with_explicit_N163_fixture',registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,
   N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,scope='Common Source/originalCPU model input, not the instantaneous Native device image'),
   prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],inherited_Native_preparation=[],controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,
   hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0],scope='Independent callee CPU comparison; captured81 retains the actual Native input')],
   passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(ram_path.relative_to(ROOT)),RAM_sha256=sha(ram_path),SRAM_path=str(sram_path.relative_to(ROOT)),SRAM_sha256=sha(sram_path),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=sha(manifest)),
   actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False,observer_scope='Sparse original-CPU entry/watch capture in a separate passive core; one-route five-buffer parity, not a global equivalence theorem')
  dump(folder/'context.json',context);imported.append(str(folder.relative_to(ROOT)))
  for p in(path,ram_path,sram_path):pins[str(p.relative_to(ROOT))]=sha(p)
 assert len(imported)==4,imported
 for folder in imported:
  for path in(ROOT/folder).iterdir():pins[str(path.relative_to(ROOT))]=sha(path)
 dump(CPU/'evidence.json',dict(schema='phase24-passive-callee-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,exported_caller_inputs=len(imported),source_CPU_cases=0,original_CPU_prefix_instructions=0,origin='passive_Native_callee_capture_with_explicit_N163_fixture',prepared_numeric_bytes=[],actual_software_state=True,instant_N163_captured=False,artifact_sha256=pins,
  source_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},limits=['Four actual software caller states come from the passive observer, not a synthesized saved-state CPU prelude.','N163 is a common explicit Source/CPU fixture and is not represented as an instantaneous Native snapshot.','Actual sparse observer events and five-buffer route parity do not prove global observer equivalence.']))
 (CPU/'README.md').write_text('''# 配兵原调用输入

四个D64A/D987入口输入由新被动观察核心在真实JSR入口直接复制2048B物理RAM、8192B物理SRAM，并记录AXYP/SP/PC、实际四个PRG页和已有返回栈；原游戏内存、寄存器、PC和返回帧未准备。该观察版另与固定原核心走同一路径逐帧五buffer严格相等，不能扩称全部运行下等价。

没有瞬时N163/PPU/APU副本。每个 `context.json` 明确 `N163_origin=explicit_shared_fixture_not_Native_snapshot`，Source/原CPU共同使用128B非零模型图、address127/autoincrementTrue，并验证完整不变。它是明示设备输入，不是原核心当时音频状态。模型端口输入及双手柄0另列；捕获RAM81保留真实左右按键。无新NMI/IRQ、无伪caller和数据ready。

这里只导出来源，不增加Source CPU案例。独立源码矩阵与Root调用层整合各自引用这些输入和声明scope；观察events是稀疏原机边界，而不是完整原核心逐指令录制。
''')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--import-native-callees',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 if a.import_native_callees:import_native_callees()
 oldpath=ROOT/'analysis/phase13/city/static-control.json';old=json.loads(oldpath.read_text());rows=[r for r in old['original_instructions']if 0xD64A<=r['pc']<0xDA02]
 for r in rows:assert r['physical_bank']==28 and r['rom_offset']==off(r['pc'])and rom[r['rom_offset']:r['rom_offset']+len(bytes.fromhex(r['raw_hex']))]==bytes.fromhex(r['raw_hex'])
 assert len(rows)==379 and sum(len(bytes.fromhex(r['raw_hex']))for r in rows)==913
 ranges=[]
 for start,end,name in((0xD64A,0xD74C,'selection navigation and multiple/city selection'),(0xD773,0xD7A8,'selected-row marker packet'),(0xD7A8,0xD7C5,'list window restore request'),(0xD7C5,0xD94E,'allocation/end-row and numeric packet'),(0xD94E,0xD96F,'BCD nibble packet loop'),(0xD96F,0xD987,'single BCD digit and leading blank'),(0xD987,0xDA02,'selected record pointer save/divide/restore/normalize')):
  raw=rom[off(start):off(end)];ranges.append(dict(physical_bank=28,cpu_start=start,cpu_end_exclusive=end,rom_offset=off(start),bytes=len(raw),raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name))
 table=rom[off(0xD74C):off(0xD773)]
 selected_sites=(0xD850,0xD856,0xD859,0xD85D,0xD895,0xD89A,0xD89D,0xD8A1,0xD8B6,0xD8BC)
 catalog=dict(schema='phase24-one-G086-lifecycle-byte-catalog-v1',ROM_sha256=ROM_SHA256,selected_group='G086',selected_unknown_group_sites=14,targeted_G086_sites=list(selected_sites),other_G086_sites_outside_new_body=[0xC853,0xC87B,0xC8BB,0xDC6F],new_manual_positions=379,new_manual_code_bytes=913,immutable_table_bytes=39,
  new_manual_ranges=ranges,instructions=rows,immutable_tables=[dict(physical_bank=28,cpu_start=0xD74C,cpu_end_exclusive=0xD773,rom_offset=off(0xD74C),raw_hex=table.hex(' ').upper(),sha256=hashlib.sha256(table).hexdigest(),meaning='list values/cursor/sprite descriptors; not executable instructions')],
  inherited_original_catalog=dict(path=str(oldpath.relative_to(ROOT)),sha256=sha(oldpath)),
  newly_replaced_generated_helpers=['city_helper_d64a','city_helper_d773','city_helper_d7a8','city_helper_d94e','city_helper_d96f','city_helper_d987'],
  already_recovered_arithmetic='source/recovered/troop_fields.py:garrison_allocation/normalize_reserve, phase5 field-only contract; not counted as newly discovered arithmetic',
  external_services=[dict(physical_bank=31,cpu=entry)for entry in(0xED19,0xEDF5,0xF2AF,0xF2D7,0xEA7C,0xE9BA,0xEBE9)],
  reused_local_helpers=[dict(physical_bank=28,cpu=0xDDAD,name='real text readiness'),dict(physical_bank=28,cpu=0xDD4F,name='current city owner')])
 dump(OUT/'static-catalog.json',catalog)
 listing=['; New direct-source G086 UI bodies only; original ROM offsets include 16-byte header.']
 for r in rows:listing.append(f'{r["rom_offset"]:06X} b28:${r["pc"]:04X} {r["raw_hex"].upper():<11} {r["op"]} {r["mode"]} {r["operand"]:04X}')
 (OUT/'original.asm').write_text('\n'.join(listing)+'\n')
 stages=[
  dict(cpu=0xD805,kind='input',effect='A=current city rawbyte; original caller requires a non-end selected row and new C0 directional input.'),
  dict(cpu=0xD808,kind='city_pointer_generation',effect='F2AF creates00/01=6000+32*rawcity. Fixed helper is actually called, not replaced by a guessed field pointer.'),
  dict(cpu=0xD80B,kind='roster_index',effect='Y=(selected0012+17)&255. Legal list row0..9 addresses city+17..26. Bare row values are not automatically bounded.'),
  dict(cpu=0xD812,kind='roster_read',effect='Reads the raw roster ID from the city pointer, then passes exactly that byte to F2D7.'),
  dict(cpu=0xD814,kind='officer_pointer_generation',effect='F2D7 creates00/01=63C0+12*raw_officer. Raw237..255 retains machine behavior; normal Native record IDs remain0..236.'),
  dict(cpu=0xD819,kind='officer_read',effect='Loads the full16bit +8/+9 troop word into02/03. It is not masked to battlefield low10.'),
  dict(cpu=0xD987,kind='save',effect='Before divide,00/01 is copied bytewise to10/11. The accepted record domain is disjoint from zero-page and the stack.'),
  dict(cpu=0xD996,kind='borrow',effect='The wrapper writes raw troop low/high into01/02, breaking the whole00/01 officer-pointer value. EA7C itself does not write00.'),
  dict(cpu=0xD9A9,kind='dependency',effect='Actual JSR EA7C computes raw/100 quotient/remainder, with its real caller frame. Missing owner remains a strict dependency.'),
  dict(cpu=0xD9E4,kind='restore',effect='10/11 are restored to00/01 before the next officer access. Conditional whole-pointer postcondition needs an intact input and no intervening IRQ/NMI/external mutation.'),
  dict(cpu=0xD9F2,kind='ordered_record_update',effect='Subtracts the actual adjusted remainder from full +8/+9 in original low/high order, including cap/byte-overage quirks.'),
  dict(cpu=0xD850,kind='allocation',effect='Right path adds min(working reserve,100) after the original <=999 precheck and normalization. Left path restores100 only under original remainder/reserve checks.'),
  dict(cpu=0xD8B3,kind='final_record_read',effect='Re-reads full +8/+9 for the displayed number. D8C2 then overwrites01 with numeric data: the officer-pointer lifetime has ended.'),
  dict(cpu=0xD8CC,kind='packet',effect='BCD plus row-address multiplication constructs031C.. packet and007E|1. Producing a packet is not PPU/text completion.'),
  dict(cpu=0xB441,physical_bank=27,kind='parent_commit',effect='After actual end-row confirmation, parent reacquires a fresh city pointer and writes working042C/D to city+12/+13. Ordinary edits already changed officer storage.'),
 ]
 dump(OUT/'pointer-lifetime.json',dict(schema='phase24-one-G086-pointer-lifetime-v1',ROM_sha256=ROM_SHA256,physical_bank=28,stages=stages,field_names=dict(city_byte1=None,city_tail28=None,city_tail29=None,city_tail30=None,city_tail31=None),
  limits=['This is an officer-roster/allocation path, not a dedicated city auxiliary-field producer.','The pointer return theorem is conditional; explicit bare ZP/stack/wrap inputs retain original alias effects and are not legal UI cases.','No interrupt-atomicity is inferred.','A transient value in00/01 need not be a pointer; frame-end contents do not prove the internal lifetime.']))
 source=ROOT/'source/recovered/pointer_lifecycle_services.py';tree=ast.parse(source.read_text())
 forbidden=('exec','eval','compile','MPU','TacticalAIControl','CPU6502')
 assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in forbidden for n in ast.walk(tree))
 if not(OUT/'validation.json').exists():print(json.dumps(dict(status='catalog_only',positions=379,code_bytes=913)));return
 validation=json.loads((OUT/'validation.json').read_text());assert validation['status']=='passed'
 visited={(r['physical_bank'],r['cpu_address'])for r in validation['executed_instruction_positions']};dynamic=sum((28,r['pc'])in visited for r in rows)
 actual=list((CPU/'actual-callers').glob('entry-*/context.json'))
 evidence=dict(schema='phase24-one-G086-independent-source-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,selected_unknown_producer_group='G086',new_manual_positions=379,new_manual_code_bytes=913,immutable_data_bytes=39,dynamic_new_positions=dynamic,not_dynamic_positions=379-dynamic,all_paths_or_inputs_proven=False,
  recovered_scope='Named selection/input/pointer save/borrow/restore/record update/numeric packet protocol. Frozen arithmetic and other group bodies are not counted as new semantic discoveries.',
  validation=dict(path=str((OUT/'validation.json').relative_to(ROOT)),sha256=sha(OUT/'validation.json'),original_CPU_parent_cases=validation['original_CPU_parent_cases'],counts=validation['counts'],source_guard_count=validation['source_guard_count']),
  production_original_CPU_callbacks=0,production_IR_interpretation=False,production_runtime_codegen=False,original_Native_internal_CPU_trace=False,
  source_sha256={str(p.relative_to(ROOT)):sha(p)for p in(source,ROOT/'source/recovered/pointer_lifecycle_integration.py',ROOT/'source/recovered/city_ui_controller.py',ROOT/'source/recovered/troop_fields.py',Path(__file__),ROOT/'scripts/verify_pointer_lifecycle_services.py')},
  artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'pointer-lifetime.json')},exported_caller_inputs=len(actual))
 dump(OUT/'evidence.json',evidence)
 (OUT/'README.md').write_text(f'''# G086 配兵指针的完整生命周期

仅选择阶段23的一个 unknown-producer 组 G086 的配兵子链，针对其中10个D850..D8BC读写点；另3个装备包点及DC6F计数点不在本轮新body内，不声称整个14点组已闭合。新增 [PointerLifecycleServices](../../../source/recovered/pointer_lifecycle_services.py) 继承冻结 CityUIController，具名替换六个原生成helper：D64A、D773、D7A8、D94E、D96F、D987。原选择/配兵/数字packet正文共379指令位置、913原代码字节，39字节列表/光标数据独立记账。阶段5已证明的 `garrison_allocation`／`normalize_reserve` 算术不重新计为首次发现。

玩家在真实行游标上输入后，D805调F2AF建立城市指针，按`(0012+17)&255`读取名册ID，再由F2D7建立完整武将指针。D987保存00/01到10/11；D996..D99C把01/02当数值临时区，EA7C自身不写00；除法后恢复00/01，随后才读写+8/+9。显示前再次读取兵word，之后01转作数字临时区，该指针世代结束。父B431在结束行确认后重新取得城市指针，将工作库存042C/D写到city+12/+13。详见 [原字节与偏移](static-catalog.json)、[逐步生存期](pointer-lifetime.json)。

完整原16位兵数、999检查在归一前、10000库存边界及低字节超额修正、左右输入次序、选择取消/带洞压紧、真实调用栈、BCD/行地址packet均保留。031C..与007E|1是请求，不自动完成文本/PPU。裸raw ID、ZP/栈/16位回绕别名单列机械CPU输入，不推为正常UI可达性；完整指针保持合同只对不别名的真实武将记录和无额外中断模型有效。

[validation.json](validation.json) 当前 {validation['original_CPU_parent_cases']} 原CPU父案通过，分类 {json.dumps(validation['counts'],ensure_ascii=False)}，另{validation['source_guard_count']}个源码guard。比较全部2048 RAM、8192 SRAM、AXYP/SP/PC、有序IO、四实际PRG页与N163，未排除闲置栈；Source原CPU callback=0。379新位置动态命中{dynamic}个，位置覆盖不等于所有路径/输入已证明。受控数值/软件caller与真实Native调用输入分别标明。

API `PointerLifecycleServices(memory,rom,services).run_entry(entry,registers=actual)`／`__call__(ServiceCall)`，保留真实返回帧。要求物理27/28与实际入口PC，不允许seed_return；pending必须由同caller继续，缺少菜单/除法owner严格停留。其他冻结父菜单与真实固定服务继续复用。本轮并未给城市+1/+28..31新正式名称，也未恢复其他unknown-producer组。

```sh
.venv-trace/bin/python scripts/verify_pointer_lifecycle_services.py ROM.nes
.venv-trace/bin/python scripts/analyze_pointer_lifecycle_services.py ROM.nes
```
''')
 print(json.dumps(dict(status='written',new_positions=379,dynamic=dynamic,original_CPU_parent_cases=validation['original_CPU_parent_cases'],counts=validation['counts'],actual_caller_inputs=len(actual))))
if __name__=='__main__':main()
