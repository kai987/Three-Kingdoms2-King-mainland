#!/usr/bin/env python3
"""Document exact stage2 closure and import selected passive phase28 callers."""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.battle_setup_ai import ROM_SHA256
OUT=ROOT/'analysis/phase28/parent-services';CPU=ROOT/'analysis/phase28/cpu-parent'
NEW=(0xA006,0xBAB3,0xBB93,0xC027)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def offset(bank,pc):return 16+bank*8192+(pc&8191)
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def import_native(rom):
 manifest=ROOT/'analysis/phase28/runtime/evidence.json';assert json.loads(manifest.read_text())['status']=='passed';pins={str(manifest.relative_to(ROOT)):sha(manifest)};imports=[];case_counts={}
 for case in('natural-postbattle-skip','controlled-ancestry-resource-loss'):
  parent=ROOT/'analysis/phase28/runtime'/case/'observer';prep=json.loads((parent/'preparation.json').read_text());events=[json.loads(s)for s in(parent/'events.jsonl').read_text().splitlines()];controlled=prep['controlled_ancestry'];selected=set()
  for path in sorted(parent.glob('callee-*.json')):
   x=json.loads(path.read_text());entry=x['entry']
   if entry not in NEW+(0xD4F5,):continue
   rp=parent/x['exported_RAM'];sp=parent/x['exported_SRAM'];ram=rp.read_bytes();sram=sp.read_bytes();r=x['actual_registers'];stage=ram[0x501];sign=bool(ram[0x87]&128)
   if stage==2:key=entry,stage,None
   elif stage==3 and entry==0xA006:key=entry,stage,sign
   else:continue
   if key in selected:continue
   selected.add(key);s=r['sp'];word=ram[0x100+((s+1)&255)]|ram[0x100+((s+2)&255)]<<8
   assert len(ram)==2048 and len(sram)==8192 and sha(rp)==x['RAM_sha256']and sha(sp)==x['SRAM_sha256']and word==x['stack_top_word_raw']and r['pc']==entry and x['additional_core_memory_writes']==0
   assert tuple(x['actual_PRG_banks'][1:3])==((12,13)if entry==0xD4F5 else(8,9))
   i=next(i for i,e in enumerate(events)if e['sequence']==x['event_sequence']);hit=events[i];previous=[e for e in events[:i]if e['kind']=='opcode_boundary'];before=previous[-1]if previous else None
   kind='unknown';transfer_pc=None;proof=dict(callee_opcode_boundary=hit,previous_watched_opcode_boundary=before,not_inferred_from_return_stack=True,scope='Watched boundary provenance; not an unbroken global CPU trace')
   if before:
    bank=before['actual_PRG_banks'][(before['opcode_PC']-0x8000)//8192];pc=before['opcode_PC'];raw=rom[offset(bank,pc):offset(bank,pc)+3];proof.update(previous_ROM_bytes=raw.hex(' ').upper())
    ticks=hit['cycle']-before['cycle'];proof['cycle_ticks']=ticks
    if raw[0]in(0x20,0x4C)and int.from_bytes(raw[1:],'little')==entry and ticks==(72 if raw[0]==0x20 else 36):
     kind='call'if raw[0]==0x20 else'trampoline'if entry==0xBAB3 and pc==0xA006 else'tail'
     proof['SP_delta']=((before['SP']-r['sp'])&255);assert proof['SP_delta']==(2 if kind=='call'else 0);transfer_pc=pc
    elif raw[0]==0x6C and ticks==60:
     pointer=int.from_bytes(raw[1:],'little');low=pointer&2047;high=((pointer&0xFF00)|((pointer+1)&255))&2047
     if pointer<0x2000 and ram[low]|ram[high]<<8==entry and before['SP']==r['sp']:
      kind='far_indirect_jump'if entry==0xA006 and pc==0xEE4A else'state_inline_dispatch'if entry==0xBB93 else'indirect_dispatch_or_tail';transfer_pc=pc;proof['actual_indirect_pointer']=pointer
    elif entry==0xD4F5 and pc==0xD4F3 and ticks==24 and raw[:2]==bytes.fromhex('A028'):
     kind='midpoint';transfer_pc=pc;assert before['SP']==r['sp']
   frame_owner=dict(kind='captured_existing_return_frame_owner_not_fully_observed',existing_stack_word=word,return_PC=(word+1)&65535,SP=s,creation_PC=None,not_inferred_from_return_word_minus3=True)
   if entry in(0xA006,0xBAB3,0xBB93)and word==0xEE4C:
    frame_owner.update(kind='EE07_constructed_far_callee_frame'if entry==0xA006 else'inherited_EE07_far_callee_frame',original_protocol_push_PCs=[0xEE46,0xEE49],original_protocol_return_word=0xEE4C,basis='Captured actual stack; original EE07 constructs this frame before its indirect jump. No new frame is added at trampoline/dispatch.')
   elif entry==0xC027 and kind=='call':
    assert word==(transfer_pc+2)&65535;frame_owner.update(kind='observed_original_JSR_frame',creation_PC=transfer_pc)
   elif entry==0xD4F5:
    frame_owner.update(kind='existing_outer_battle_frame_at_actual_midpoint',midpoint_adds_frame=False,basis='Captured original stack; D4F3 LDY28 falls through without a JSR. Frame creator is not guessed.')
   folder=CPU/'actual-callers'/f'entry-{entry:04X}-{case}-stage{stage}-{x["snapshot_sequence"]:04d}';folder.mkdir(parents=True,exist_ok=True);(folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram);n163=bytes((11+37*i)&255 for i in range(128));(folder/'input-n163.bin').write_bytes(n163)
   context=dict(schema='phase28-passive-postbattle-parent-caller-with-device-fixture-v1',origin='passive_Native_callee_capture_with_explicit_N163_fixture',ancestry_origin='controlled_ancestry'if controlled else'natural_ancestry',controlled_ancestry=controlled,natural_ordinary_input_route=prep['natural_ordinary_input_route'],registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,scope='Common Source/originalCPU fixture, not instantaneous Native capture'),prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],inherited_Native_preparation=prep['known_inherited_preparation'],known_inherited_preparation_byte_writes=prep['known_inherited_preparation_byte_writes'],ancestry_provenance=prep,controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0])],actual_call_kind=kind,immediate_transfer_PC=transfer_pc,immediate_transfer_proof=proof,real_return_frame_owner=frame_owner,stage=stage,fade_sign=sign,scope='stage2_complete_caller'if stage==2 else'stage3_unimplemented_dispatch_prefix_only',owner_scope=('Root_midpoint_bridge_only'if entry==0xD4F5 else'PostbattleParentServices'),passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(rp.relative_to(ROOT)),RAM_sha256=sha(rp),SRAM_path=str(sp.relative_to(ROOT)),SRAM_sha256=sha(sp),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=sha(manifest),events_path=str((parent/'events.jsonl').relative_to(ROOT)),events_sha256=sha(parent/'events.jsonl'),preparation_path=str((parent/'preparation.json').relative_to(ROOT)),preparation_sha256=sha(parent/'preparation.json')),actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False)
   dump(folder/'context.json',context);imports.append(str(folder.relative_to(ROOT)))
   for p in(path,rp,sp,parent/'preparation.json',parent/'events.jsonl',*folder.iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
  case_counts[case]=len(selected)
 assert case_counts=={'natural-postbattle-skip':7,'controlled-ancestry-resource-loss':7},case_counts
 dump(CPU/'evidence.json',dict(schema='phase28-passive-postbattle-parent-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,exported_caller_inputs=14,Source_NEW4_inputs=12,Root_midpoint_bridge_inputs=2,stage2_NEW4_inputs=8,stage3_NEW4_strict_prefix_inputs=4,source_CPU_cases=0,original_CPU_prefix_instructions=0,instant_N163_captured=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},limits=['ECEE returns in the same frame; later stage3 calls are independent invocations, not one suspended fade JSR.','Controlled ancestor19 known writes and earlier unknown preparation remain explicit.','Sparse software capture is from the independent observer, not fixed-core internal trace.','Instantaneous N163/PPU/APU is not captured; explicit common fixture is separate.']))
 (CPU/'README.md').write_text('''# 战后阶段2原机软件调用上下文

正式独立被动核心两路线各取7份真实2K/8K/AXYP-SP-PC/实际四PRG/原栈现场，共14份：stage2 A006/BAB3/BB93/C027各一、stage3 A006首hold与87负各一、D4F5 stage2中段。NEW4本体只有12份（8完整阶段2、4阶段3严格调度前缀），D4F5两份只供Root中段桥。导出来源本身不计Source CPU案例，不从保存点强跳PC或补caller。

A006 EE4A far_indirect_jump实际沿EE07构造的EE4C返回帧；BAB3原A006 JMP沿用同帧；C027真实BB99 JSR。BB93前EADE最终JMP未hook，immediate_transfer_PC明确null，不由栈伪造JSR。D4F5为真实捕获的中段PC，静态前序D4F3 LDY28未单独hook，immediate_transfer_PC也null；frameowner明确旧外层帧和midpoint不造帧。unknown表示未观察的直接transfer，不是否认真实入口软件现场。

每份context保留real_return_frame_owner、immediate_transfer_proof、原metadata/事件/2K8K哈希及完整ancestry_provenance。自然路线旧准备0；positive保留19项已知数值准备和更早phase3准备未完全建立的边界。两条都不是本轮冷启，本轮新增游戏字节/PC/栈准备0，不替换实际母档身份。

N163_origin=explicit_shared_fixture_not_Native_snapshot。瞬时N163/PPU/APU未捕；128B模式、address127/autoincrementTrue、端口输入和controller0/0只是Source与原CPU共同夹具。固定原核心不含内部trace；独立被动核同路线完整五buffer一致不是全局硬件等价定理。

ECEE在本帧立即返回；stage3后续是各次独立调用，不能将21帧淡出说成同一挂起ECEE的resume。stage3四份Source输入只到BBA0调度目标，不执行等待/完成正文。完整软件对照见../parent-services/validation.json，原机palette逐时点见../runtime/palette-lifecycle-observations.json。
''')
 return imports

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--import-native-callees',action='store_true');p.add_argument('--import-only',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 if a.import_native_callees:import_native(rom)
 if a.import_only:return
 mem=[0]*65536
 for bank,st in((8,0xA000),(9,0xC000),(31,0xE000)):mem[st:st+8192]=rom[16+bank*8192:16+(bank+1)*8192]
 d=Disassembler(MPU(memory=mem));ranges=[];code=[]
 for bank,start,end,name,iscode in((8,0xA006,0xA009,'original parent trampoline',True),(8,0xBAB3,0xBAB9,'phase load and inline dispatch call',True),(8,0xBAB9,0xBAC1,'four original inline target words',False),(8,0xBB93,0xBBA0,'implemented stage2 body',True),(9,0xC027,0xC0BB,'supply return and cap closure',True),(31,0xECEE,0xED19,'inherited immediate fade initialization; not new algorithm',False)):
  raw=rom[offset(bank,start):offset(bank,start)+end-start];ranges.append(dict(physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset(bank,start),bytes=len(raw),raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name,new_exact_protocol=iscode))
  if iscode:
   pc=start
   while pc<end:
    size,text=d.instruction_at(pc);code.append(dict(physical_bank=bank,cpu=pc,rom_offset=offset(bank,pc),bytes=size,raw_hex=bytes(mem[pc:pc+size]).hex(' ').upper(),assembly=text));pc+=size
   assert pc==end
 assert bytes(mem[0xBAB9:0xBAC1])==bytes.fromhex('C1BA3DBB93BBA0BB')
 dump(OUT/'static-catalog.json',dict(schema='phase28-stage2-Source-original-byte-catalog-v1',ROM_sha256=ROM_SHA256,new_exact_protocol_positions=len(code),new_exact_protocol_bytes=sum(r['bytes']for r in code),inline_dispatch_table_bytes=8,implemented_stage=2,unimplemented_stage_targets={'0':0xBAC1,'1':0xBB3D,'3':0xBBA0},code_and_reference_ranges=ranges,original_instructions=code,new_semantic_first_recovery=False,existing_semantics=['source/recovered/battle_state_machine.py:finalization_phase','source/recovered/battle_state_machine.py:return_campaign_supplies'],fixed_dependencies=[0xECEE,0xF25F,0xF2AF,0xF2D7],inherited_resource_BF0A_exact_source='source/recovered/postbattle_resource_services.py'))
 (OUT/'original.asm').write_text('\n'.join(f'{r["physical_bank"]:02X}:{r["cpu"]:04X} {r["raw_hex"]:<12} {r["assembly"]}'for r in code)+'\n')
 validation=json.loads((OUT/'validation.json').read_text());assert validation['status']=='passed'and not validation['quick']
 assert validation['passive_software_caller_cases']==12 and validation['controlled_cases']==1228
 for path,digest in validation['source_sha256'].items():assert sha(ROOT/path)==digest,path
 source=ROOT/'source/recovered/postbattle_parent_services.py';tree=ast.parse(source.read_text());assert {'postbattle_stage_dispatch','settle_and_return_supplies','return_campaign_supply_words','add_supply_pair_and_cap','cap_supply_field'}<={n.name for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)}
 static={(r['physical_bank'],r['cpu'])for r in code};dynamic={(r['physical_bank'],r['cpu_address'])for r in validation['executed_instruction_positions']}&static
 pins={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'validation.json',CPU/'evidence.json')if p.exists()};result=dict(schema='phase28-stage2-readable-exact-parent-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,source_path=str(source.relative_to(ROOT)),source_sha256=validation['source_sha256'],analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),validator_path='scripts/verify_postbattle_parent_services.py',validator_sha256=sha(ROOT/'scripts/verify_postbattle_parent_services.py'),artifact_sha256=pins,original_CPU_parent_cases=validation['original_CPU_parent_cases'],counts=validation['counts'],source_guard_count=validation['source_guard_count'],new_exact_protocol_positions=len(code),new_exact_protocol_bytes=sum(r['bytes']for r in code),new_protocol_dynamic_positions=len(dynamic),new_protocol_not_dynamically_covered_positions=len(static-dynamic),new_semantic_first_recovery=False,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False);dump(OUT/'evidence.json',result)
 print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','new_exact_protocol_positions','new_protocol_dynamic_positions','source_guard_count')}))
 (OUT/'README.md').write_text(f'''# 精确战后阶段2父服务

PostbattleParentServices(PostbattleResourceServices)只新增A006/BAB3/BB93/C027四个入口。真实输入必须已在相应PC、code physical8/9、有原caller栈；拒绝seed_return、错误返回、错误银行及表外phase。A006是JMP BAB3，无新增帧；BAB3原EADE四项表仍为BAC1/BB3D/BB93/BBA0，但只实现phase2。0/1/3保留实际dispatch目标、栈和暂存为strict dependency，不能称整个四态控制器恢复。

本轮精确协议{len(code)}个原位置/{sum(r['bytes']for r in code)}B，另8B inline表。既有finalization_phase/return_campaign_supplies已恢复玩法，既有Shared已恢复ECEE、既有phase27已恢复BF0A。本轮不把这些再次记首次算法发现，也不把依赖的43B ECEE计入新增协议正文。

## ECEE等待措辞纠正

ECEE原文立即写87=1、88=0、89=4，设置00/01=0100、02/03=0120，复制32B palette后ED18 RTS到BB96。它不写8A，不轮询87，也不等待帧或硬件ack。冻结旧语义接口render_barrier及旧bypass只是旧测试合同，不能推论原ECEE是同步等待或软件未恢复。本轮通过已有exact Shared、原JSR帧执行它，没有fakeRTS。

真正的fade完成检查在后续phase3 BBA0读87符号；NMI EC67推进并最终写87FF。每帧阶段3是新的原调用，不是一个跨帧挂起的ECEE JSR。本Source只停到BBA0入口；Native可见完成仍不是本Source已执行阶段3正文的证据。

## 阶段2与补给

BB93真实顺序为JSR ECEE、BB96 JSR BF0A、BB99 JSR C027、BB9C INC0501、BB9F RTS。BF0A复用既有pure源码及真实localcall；BF9B tail不造帧。C027第一次以((0514<<1)&FF)^2索引0526/0522，加到050E城+2/+4；然后F25F选择17并检查052B。非FF selector经原F2D7，packed low2只有1/2时选择052C，否则回050E。第二次索引(0514<<1)&FF。所有raw8域保留，但与合法outcome0/1、city0..29、officer0..236分列。

每项先低/高带carry相加并实际写回，再以10000比较，达到上限时高先写27、低后写0F。先wrap16再cap9999，不能用无限整数先cap替代。同城会依次收到两份补给。C08E第一项cap是真实JSR；第二项cap是C0A5的fallthrough；C067第二份是tail JMP C07A，均不造新帧。每个byte读写重取live00/01。

F25F改变E1与实际8000数据页，F2AF/F2D7是已有exact服务；本体不保存/还原整个四页。返回Root外层EE07只恢复原代码窗口，数据页副作用必须保留。D4F5中段桥及其CC29之前绘制不在本四入口owner内，由Root独立声明。

## 对照范围

Source父case {validation['original_CPU_parent_cases']}，分类{json.dumps(validation['counts'],ensure_ascii=False)}；另{validation['source_guard_count']} guards。每案比较完整2048RAM（包括闲置栈）、8192SRAM、AXYP/SP/PC、四PRG、mixed logicalIO读写次序和明示共同N163。Source原CPUcallback0，无IR/CPU执行、无新NMI/IRQ、无ack/ready写入。裸raw/数值/原caller夹具与被动Native输入逐case分列。SP矩阵是明确子集，未声明所有堆栈与palette backup重叠的任意输入都正常返回。

两个same-generator序列先真实停在ECEE caller，再提供已恢复Shared服务后resume；原CPU从同callee继续，缺少PC/SP的“returned”不得推进。这是依赖可用性重试，不是跨帧淡出完成等待。stage0/1/3、missingfixed与越界guard分别计数，不以它们增加正常玩法成功数。

被动callee输入见../cpu-parent；瞬间N163/PPU/APU未捕，所有软件比较使用共同设备fixture。自然退却和受控祖先分别保留，positive继承19项已知准备及更早未知边界；本轮不替换母档身份。原CPU对照不是原机内部CPUtrace，Root frontdoor复用同一软件输入不增加独立Native输入数。

静态新增正文动态覆盖{len(dynamic)}/{len(static)}原位置，仍不等于全部分支、四态完整父链或整ROM完成。城市辅助字段正式名和既有1526账本本轮不改。

复现：.venv-trace/bin/python scripts/analyze_postbattle_parent_services.py ROM --import-native-callees --import-only；.venv-trace/bin/python scripts/verify_postbattle_parent_services.py ROM；.venv-trace/bin/python scripts/analyze_postbattle_parent_services.py ROM --evidence-only。仅写新phase28目录，旧1..27不重跑或覆盖。
''')
if __name__=='__main__':main()
