#!/usr/bin/env python3
"""Pin newly named multiply and import two passive appearance caller states."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from source.recovered.city_threshold_services import ROM_SHA256
OUT=ROOT/'analysis/phase25/appearance';CPU=ROOT/'analysis/phase25/cpu-appearance'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def off(b,pc):return 16+b*8192+(pc&8191)
def import_native():
 manifest=ROOT/'analysis/phase25/runtime/evidence.json';receipt=json.loads(manifest.read_text());assert receipt['status']=='passed';pins={str(manifest.relative_to(ROOT)):sha(manifest)};imports=[]
 for path in sorted((ROOT/'analysis/phase25/runtime/natural-appearance-pointer/observer').glob('callee-*.json')):
  x=json.loads(path.read_text())
  if (x['entry'],x['snapshot_sequence'])not in((0xC5D2,4),(0xD471,5)):continue
  assert x['actual_registers']['pc']==x['entry']and x['additional_core_memory_writes']==0 and x['inherited_preparation_byte_writes']==0
  rp=path.parent/x['exported_RAM'];sp=path.parent/x['exported_SRAM'];ram=rp.read_bytes();sram=sp.read_bytes();r=x['actual_registers'];s=r['sp'];word=ram[0x100+((s+1)&255)]|ram[0x100+((s+2)&255)]<<8
  assert len(ram)==2048 and len(sram)==8192 and sha(rp)==x['RAM_sha256']and sha(sp)==x['SRAM_sha256']and word==x['stack_top_word_raw']and tuple(x['actual_PRG_banks'][1:3])==(10,11)
  folder=CPU/'actual-callers'/f'entry-{x["entry"]:04X}-observer-{x["snapshot_sequence"]:04d}';folder.mkdir(parents=True,exist_ok=True)
  (folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram);n163=bytes((11+37*i)&255 for i in range(128));(folder/'input-n163.bin').write_bytes(n163)
  context=dict(schema='phase25-passive-appearance-caller-with-device-fixture-v1',origin='passive_Native_callee_capture_with_explicit_N163_fixture',registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,scope='Common Source/originalCPU fixture; instantaneous device image was not captured'),prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],inherited_Native_preparation=[],controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0])],passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(rp.relative_to(ROOT)),RAM_sha256=sha(rp),SRAM_path=str(sp.relative_to(ROOT)),SRAM_sha256=sha(sp),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=sha(manifest)),actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False,observer_scope='Separate passive core sparse entry capture; same-route five-buffer parity is not a global equivalence theorem')
  dump(folder/'context.json',context);imports.append(str(folder.relative_to(ROOT)))
  for p in(path,rp,sp,*folder.iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
 assert len(imports)==2,imports
 dump(CPU/'evidence.json',dict(schema='phase25-passive-appearance-caller-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,exported_caller_inputs=2,source_CPU_cases=0,original_CPU_prefix_instructions=0,origin='passive_Native_callee_capture_with_explicit_N163_fixture',prepared_numeric_bytes=[],actual_software_state=True,instant_N163_captured=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},limits=['Captured software RAM/SRAM/AXYP/SP/PC/actual MAP and real caller frame are retained.','N163 and model port inputs are common explicit fixtures, not instantaneous Native device captures.','No new IRQ/NMI, caller/PC/RNG/ready preparation or Native internal trace of the fixed original core.']))
 (CPU/'README.md').write_text('''# G033 原调用输入

两份输入直接来自本轮独立被动观察核心在真实 C5D2/D471 指令入口的稀疏捕获：完整2048B RAM、8192B SRAM、AXYP/SP/PC、实际四个PRG页及已有JSR返回帧。母档为冻结第22阶段原核心自然月轮保存点；无新增游戏字节准备、无新增中断、未伪造PC或caller。原固定核心与被动核本路线逐帧五buffer相等另见runtime回执，这不是所有输入下的核心等价定理。

没有捕获瞬时N163/PPU/APU。每份context明确 `N163_origin=explicit_shared_fixture_not_Native_snapshot`，共同给Source/原CPU128B非零模式、address127/autoincrementTrue及显式端口模型；不能称它为原机当时音频图像。Source矩阵与Root整合将分别对照这些软件入口；这里导出不增加Source案例数。

自然实际ID152读取发生在city3、pointer8B58、Y0，physical17。该帧末pointer8B6C属于后续重用，不能倒推为ID152读取地址。前期从14569原REG继续但不插入NMI的CPU探针未复现录用成功，仍只保留为选择分析中的独立probe。
''')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--import-native-callees',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 if a.import_native_callees:import_native()
 from py65.disassembler import Disassembler
 from py65.devices.mpu6502 import MPU
 from source.recovered.nestopia_context import CapturedServiceMemory
 m=CapturedServiceMemory(rom,banks=(17,10,11,31));d=Disassembler(MPU(memory=m));rows=[];pc=0xD471
 while pc<0xD494:
  size,text=d.instruction_at(pc);raw=rom[off(11,pc):off(11,pc)+size];rows.append(dict(physical_bank=11,cpu=pc,rom_offset=off(11,pc),size=size,raw_hex=raw.hex(' ').upper(),assembly=text));pc+=size
 assert len(rows)==19 and sum(x['size']for x in rows)==35 and pc==0xD494
 raw=rom[off(11,0xD471):off(11,0xD494)];catalog=dict(schema='phase25-new-named-multiply-original-byte-catalog-v1',ROM_sha256=ROM_SHA256,newly_named_original_instruction_positions=19,newly_named_original_bytes=35,new_body_range=dict(physical_bank=11,cpu_start=0xD471,cpu_end_exclusive=0xD494,rom_offset=off(11,0xD471),bytes=35,raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest()),original_instructions=rows,already_named_dependency='CityRecruitmentServices.recruit_appearing_officers(C5D2), inherited unchanged; no new recovery credit')
 dump(OUT/'static-catalog.json',catalog);(OUT/'original.asm').write_text('\n'.join(f'11:{r["cpu"]:04X} {r["raw_hex"]:<11} {r["assembly"]}'for r in rows)+'\n')
 source=ROOT/'source/recovered/appearance_pointer_services.py';tree=ast.parse(source.read_text());names={n.name for n in ast.walk(tree)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};assert 'multiply_byte_operands'in names
 validation=json.loads((OUT/'validation.json').read_text());assert validation['status']=='passed'
 for path,digest in validation['source_sha256'].items():assert sha(ROOT/path)==digest,path
 pins={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'validation.json',CPU/'evidence.json',ROOT/'analysis/phase25/fields-static/selection-comparison.json')if p.exists()}
 new_dynamic=[x for x in validation['executed_instruction_positions']if x['physical_bank']==11 and 0xD471<=x['cpu_address']<=0xD493];assert len(new_dynamic)==19
 result=dict(schema='phase25-named-appearance-pointer-services-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,source_path=str(source.relative_to(ROOT)),source_sha256=validation['source_sha256'],analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),validator_path='scripts/verify_appearance_pointer_phase25.py',validator_sha256=sha(ROOT/'scripts/verify_appearance_pointer_phase25.py'),artifact_sha256=pins,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,original_CPU_parent_cases=validation['original_CPU_parent_cases'],counts=validation['counts'],source_guard_count=validation['source_guard_count'],newly_named_original_instruction_positions=19,newly_named_original_bytes=35,new_body_dynamic_instruction_positions=len(new_dynamic),new_body_not_dynamically_covered_positions=0,limits=validation['limits'])
 dump(OUT/'evidence.json',result)
 (OUT/'README.md').write_text(f'''# G033 登场表指针与乘法

新增可读源码只替换physical11 `D471..D493` 的19条/35B八轮无符号8×8乘法；既有 `C5D2` 已具名录用流程不复制、不重复计发现。`AppearancePointerServices(CityThresholdServices)` 的 `PUBLIC_ENTRIES` 在既有入口外增加D471，`run_entry(..., registers=真实caller)`保留原JSR帧、二进制flags与严格依赖；父类调用通过真实别名进入新乘法。无CPU/IR/fallback/假ready。

20/21是破坏式工作字节，2C为移位高字节，2A/2B为完整乘积；X保持，Y最终FF，A/V来自最后真实加法或零乘数路径，不能从数学结果伪造寄存器。所有256城市原始字节×20保留；完整prefix `C5F8..C614` 建立22/23=`8B1C+20*rawcity`。实际读取C61F/C624的Y分别来自偶/奇byte循环，不存在10pair或FF自动终止条件。

合法城市0..29的所有byte索引落在physical17数据ROM；raw255+Y248..255跨到A000..A007、实际映physical10代码。逻辑EA与IndY dummy页分开。只证明这两处读的完整生命周期，不因此排除整个C5D2的status/名册/资源cap写入，更不命名城市+1或tail。

本轮Source原CPU对照 **{validation['original_CPU_parent_cases']}** 个父案例，分类 `{json.dumps(validation['counts'],ensure_ascii=False)}`，另 **{validation['source_guard_count']}** guards；完整2048RAM/8192SRAM、AXYP/SP/PC、端口有序读写、实际四银行及共同N163模型相等。受控乘法/flags/SP边界与完整既有C5D2调用、真实被动callee分列；Root统一工厂层另计，静态原CPU合同也另计。

真实callee只有软件现场；N163是明示共同fixture。无新增中断或caller准备。原Native短路线已独立观察city3/8B58读ID152、原status1→2，详细producer与五buffer对照见 [runtime evidence](../runtime/evidence.json)，输入详见 [CPU来源](../cpu-appearance/README.md)。早期无新增NMI的独立CPUprobe没有复现录用成功，不能当Native成功证据。

复现：

```sh
.venv-trace/bin/python scripts/analyze_appearance_pointer_phase25.py ROM --import-native-callees
.venv-trace/bin/python scripts/verify_appearance_pointer_phase25.py ROM
.venv-trace/bin/python scripts/analyze_appearance_pointer_phase25.py ROM --evidence-only
.venv-trace/bin/python scripts/analyze_unknown_pointer_phase25.py ROM
.venv-trace/bin/python scripts/verify_unknown_pointer_phase25.py ROM
```
''')
 print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','newly_named_original_instruction_positions','source_guard_count')}))
if __name__=='__main__':main()
