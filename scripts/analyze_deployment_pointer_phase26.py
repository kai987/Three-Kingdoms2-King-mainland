#!/usr/bin/env python3
"""Pin readable formation refactoring and passive actual deployment callers."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from source.recovered.battle_setup_ai import ROM_SHA256
OUT=ROOT/'analysis/phase26/deployment';CPU=ROOT/'analysis/phase26/cpu-deployment'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def offset(bank,pc):return 16+bank*8192+(pc&8191)
def import_native():
 manifest=ROOT/'analysis/phase26/runtime/evidence.json';x=json.loads(manifest.read_text());assert x['status']=='passed';pins={str(manifest.relative_to(ROOT)):sha(manifest)};imports=[]
 for path in sorted((ROOT/'analysis/phase26/runtime/observer').glob('callee-*.json')):
  x=json.loads(path.read_text())
  if x['entry']not in(0xB130,0xB1B0,0xB2AE):continue
  assert x['actual_registers']['pc']==x['entry']and x['additional_core_memory_writes']==0 and x['inherited_preparation_byte_writes']==0
  rp=path.parent/x['exported_RAM'];sp=path.parent/x['exported_SRAM'];ram=rp.read_bytes();sram=sp.read_bytes();r=x['actual_registers'];s=r['sp'];word=ram[0x100+((s+1)&255)]|ram[0x100+((s+2)&255)]<<8
  assert len(ram)==2048 and len(sram)==8192 and sha(rp)==x['RAM_sha256']and sha(sp)==x['SRAM_sha256']and word==x['stack_top_word_raw']and tuple(x['actual_PRG_banks'][1:3])==(8,9)
  folder=CPU/'actual-callers'/f'entry-{x["entry"]:04X}-observer-{x["snapshot_sequence"]:04d}';folder.mkdir(parents=True,exist_ok=True)
  (folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram);n163=bytes((11+37*i)&255 for i in range(128));(folder/'input-n163.bin').write_bytes(n163)
  context=dict(schema='phase26-passive-deployment-caller-with-device-fixture-v1',origin='passive_Native_callee_capture_with_explicit_N163_fixture',registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,scope='Common Source/originalCPU fixture; instantaneous device image was not captured'),prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],inherited_Native_preparation=[],controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0])],passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(rp.relative_to(ROOT)),RAM_sha256=sha(rp),SRAM_path=str(sp.relative_to(ROOT)),SRAM_sha256=sha(sp),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=sha(manifest)),actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False,observer_scope='Separate passive core sparse entry capture; this one-route five-buffer parity is not a global equivalence theorem')
  dump(folder/'context.json',context);imports.append(str(folder.relative_to(ROOT)))
  for p in(path,rp,sp,*folder.iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
 assert len(imports)==3,imports
 dump(CPU/'evidence.json',dict(schema='phase26-passive-deployment-caller-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,exported_caller_inputs=3,source_CPU_cases=0,original_CPU_prefix_instructions=0,origin='passive_Native_callee_capture_with_explicit_N163_fixture',prepared_numeric_bytes=[],actual_software_state=True,instant_N163_captured=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},limits=['Actual opcode-entry software states preserve2048RAM/8192SRAM/AXYP-SP-PC/4PRG and existing real JSR frame.','N163 and model ports are explicitly shared fixtures, not instantaneous Native device captures.','B312 is not observed by the Native route; only software CPU contracts cover that side.']))
 (CPU/'README.md').write_text('''# G107真实部署caller

本轮独立被动核心在B130/B1B0/B2AE实际指令入口直接保存2K RAM、8K SRAM、AXYP/SP/PC、四实际PRG页与已有返回栈。无游戏字节准备、无合成PC/caller、无新CPU中断；固定原核心与被动核沿相同普通按键路线的逐帧五buffer一致另见runtime回执，不扩称全局等价。

每个context的N163_origin明确为explicit_shared_fixture_not_Native_snapshot。瞬时N163/PPU/APU未捕获，共同128B非零N163模式、address127/autoincrementTrue及端口输入只是独立Source/原CPU比较夹具。B312没有本路线Native观察；不得以其原CPU对照替代原机侧实测。

原机8次坐标读取实际pointer20=8D4E、data physical6，commander Y0/1，随后strategy组索引8/9、12/13、14/15。指针在B1B0里先作profile/work再由formation重建，帧末值不能替代内部生命周期捕获。这里导出来源本身不增加Source CPU案例。
''')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--import-native-callees',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 if a.import_native_callees:import_native()
 oldpath=ROOT/'analysis/phase11/setup-ai/evidence.json';frozen=json.loads(oldpath.read_text());rows=[r for r in frozen['original_instructions']if r['bank']==8 and(0xB2AE<=r['pc']<0xB30E or 0xB312<=r['pc']<0xB36D)]
 for r in rows:
  raw=bytes.fromhex(r['raw_hex']);assert r['rom_offset']==offset(8,r['pc'])and rom[r['rom_offset']:r['rom_offset']+len(raw)]==raw
 assert len(rows)==92 and sum(len(bytes.fromhex(r['raw_hex']))for r in rows)==187
 ranges=[]
 for start,end,name in((0xB2AE,0xB30E,'first formation constructor'),(0xB312,0xB36D,'second formation constructor')):
  raw=rom[offset(8,start):offset(8,end)];ranges.append(dict(physical_bank=8,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset(8,start),bytes=len(raw),raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name))
 data=[]
 for bank,start,size,name in((8,0xB30E,4,'first group offsets'),(8,0xB36D,4,'second group offsets'),(16,0x9D72,256,'byteindexed neighbor window'),(17,0x9AB4,256,'first template byte window'),(16,0x9E62,256,'second template byte window'),(6,0x8C52,256,'first complete128 pointer words'),(6,0x8000,256,'second complete128 pointer words')):
  raw=rom[offset(bank,start):offset(bank,start)+size];data.append(dict(physical_bank=bank,cpu_start=start,rom_offset=offset(bank,start),bytes=size,raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name))
 dump(OUT/'static-catalog.json',dict(schema='phase26-formation-readable-refactoring-byte-catalog-v1',ROM_sha256=ROM_SHA256,refactored_prior_generated_positions=92,refactored_prior_generated_bytes=187,new_semantic_first_recovery=False,inherited_B1B0_unchanged=True,code_ranges=ranges,data_ranges=data,original_instructions=rows,baseline_source_path='source/recovered/battle_setup_ai.py',baseline_source_sha256=sha(ROOT/'source/recovered/battle_setup_ai.py')))
 (OUT/'original.asm').write_text('\n'.join(f'08:{r["pc"]:04X} {r["raw_hex"]:<12} {r["op"]} {r["mode"]} ${r["operand"]:04X}'for r in rows)+'\n')
 source=ROOT/'source/recovered/deployment_pointer_services.py';tree=ast.parse(source.read_text());names={n.name for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)};assert {'first_side_formation','second_side_formation'}<=names
 validation=json.loads((OUT/'validation.json').read_text());assert validation['status']=='passed'
 for path,digest in validation['source_sha256'].items():assert sha(ROOT/path)==digest,path
 dynamic=[x for x in validation['executed_instruction_positions']if x['physical_bank']==8 and(0xB2AE<=x['cpu_address']<0xB30E or 0xB312<=x['cpu_address']<0xB36D)];assert len(dynamic)==92
 pins={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'validation.json',CPU/'evidence.json')if p.exists()}
 result=dict(schema='phase26-formation-readable-refactoring-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,source_path=str(source.relative_to(ROOT)),source_sha256=validation['source_sha256'],analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),validator_path='scripts/verify_deployment_pointer_phase26.py',validator_sha256=sha(ROOT/'scripts/verify_deployment_pointer_phase26.py'),artifact_sha256=pins,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,original_CPU_parent_cases=validation['original_CPU_parent_cases'],counts=validation['counts'],source_guard_count=validation['source_guard_count'],refactored_prior_generated_instruction_positions=92,refactored_prior_generated_bytes=187,new_semantic_first_recovery=False,inherited_B1B0_unchanged=True,refactored_body_dynamic_positions=92,refactored_body_not_dynamically_covered_positions=0,limits=validation['limits'])
 dump(OUT/'evidence.json',result)
 (OUT/'README.md').write_text(f'''# G107部署坐标指针

新增DeploymentPointerServices(BattleSetupAI)，仅把既有直接源码中仍是通用控制形态的B2AE/B312两体重构为可读流程：92个原位置/187B。B1B0的profile/strategy分组与四坐标读取继承不变；不重复称首次恢复部署算法。新增证据是完整caller/栈/mapper合同与四个完整指针读地址合同。旧phase11只有1972RAM排除free-stack的2326例，本轮不同scope单列。

PUBLIC五入口A003/B130/B1B0/B2AE/B312要求真实registers.pc、physical8/9窗口及已有返回帧；拒绝seed_return和错误PC/SP返回。缺F266保留真实pending。Source不执行CPU、IR、opcode字典或动态代码生成。

first：F266 raw30→physical16查邻城；match时raw31→17查template，negative sentinel则0；byte offset=32×template mod256；raw26→physical6，以(2×city)&FF完整取8C52表word加offset。second：raw30→16查9E62，offset是原ASL4+ADC原值+ASL，即34×template mod256，最后raw26→6取8000表word。先前口头36不是原ROM算术；冻结旧报告不改。

20/21先是profile/work，再完整重建为坐标指针；22..25为独立组游标。B272/B278读commanderY0/1，B290/B296按strategy组offset读成对坐标并推进该组2。正常city0..29读bank6 ROM；raw0..255完整保留，30..127/158..255可能指内部RAM镜像。保守second raw域极端Y触及2000..200E，这些只有地址合同，未给硬件输入不能称读取成功/无副作用或正常玩法。裸四读不获得完整构造合同。LDA的额外dummy只在跨页时存在，py65只加周期不模拟该读；和STA无条件dummy分开。

Source完整对照{validation['original_CPU_parent_cases']}个父case，分类{json.dumps(validation['counts'],ensure_ascii=False)}，另{validation['source_guard_count']}guards。完整2048RAM含闲置栈、8192SRAM、AXYP/SP/PC、真实四银行、读写交织的combined logical IO及N163共同fixture均比较。无新增IRQ/NMI或fakeack。原CPU静态/地址合同、Root统一工厂和Native帧分别计数，不能相加称全ROM完成。

本轮Native只实捕first formation；B312仅Source/原CPU合同覆盖，不能声称原机两侧都走过。三份被动软件现场见../cpu-deployment；N163未现场捕获，明示共同fixture。runtime原/新核心同路线五buffer相同不构成全局等价定理。

复现：.venv-trace/bin/python scripts/analyze_deployment_pointer_phase26.py ROM --import-native-callees；verify_deployment_pointer_phase26.py ROM；analyze_deployment_pointer_phase26.py ROM --evidence-only；analyze_unknown_pointer_phase26.py ROM；verify_unknown_pointer_phase26.py ROM。
''')
 print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','refactored_prior_generated_instruction_positions','source_guard_count')}))
if __name__=='__main__':main()
