#!/usr/bin/env python3
"""Pin phase29 stage3 caller protocol and selected passive software captures."""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.battle_setup_ai import ROM_SHA256
OUT=ROOT/'analysis/phase29/completion-services';CPU=ROOT/'analysis/phase29/cpu-completion';NEW=(0xA006,0xBAB3,0xBBA0,0xBBB8,0xBC00);EXTRA=(0xD4F0,0xCC29)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def offset(bank,pc):return 16+bank*8192+(pc&8191)
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def import_native(rom):
 manifest=ROOT/'analysis/phase29/runtime/evidence.json';assert json.loads(manifest.read_text())['status']=='passed';pins={str(manifest.relative_to(ROOT)):sha(manifest)};exports=[];counts=Counter()
 for case in('natural-postbattle-skip','controlled-ancestry-resource-loss'):
  parent=ROOT/'analysis/phase29/runtime'/case/'observer';prep=json.loads((parent/'preparation.json').read_text());events=[json.loads(s)for s in(parent/'events.jsonl').read_text().splitlines()];controlled=prep['controlled_ancestry'];selected=set()
  for path in sorted(parent.glob('callee-*.json')):
   x=json.loads(path.read_text());entry=x['entry']
   if entry not in NEW+EXTRA:continue
   rp=parent/x['exported_RAM'];sp=parent/x['exported_SRAM'];ram=rp.read_bytes();sram=sp.read_bytes();r=x['actual_registers'];stage=ram[0x501];sign=bool(ram[0x87]&128)
   if entry in(0xA006,0xBAB3,0xBBA0)and stage==3:key=entry,sign
   elif entry==0xBBB8 and stage==3 and sign:key=entry,None
   elif entry==0xBC00 and stage==3 and sign:key=entry,x['snapshot_sequence']
   elif entry in EXTRA and x['frame']in(1,21):key=entry,x['frame']
   else:continue
   if key in selected:continue
   selected.add(key);s=r['sp'];word=ram[0x100+((s+1)&255)]|ram[0x100+((s+2)&255)]<<8
   assert len(ram)==2048 and len(sram)==8192 and sha(rp)==x['RAM_sha256']and sha(sp)==x['SRAM_sha256']and word==x['stack_top_word_raw']and r['pc']==entry and x['additional_core_memory_writes']==0
   assert tuple(x['actual_PRG_banks'][1:3])==((12,13)if entry in EXTRA else(8,9))
   i=next(i for i,e in enumerate(events)if e['sequence']==x['event_sequence']);hit=events[i];prior=[e for e in events[:i]if e['kind']=='opcode_boundary'];before=prior[-1]if prior else None
   kind='unknown';transfer=None;proof=dict(callee_opcode_boundary=hit,previous_watched_opcode_boundary=before,not_inferred_from_return_stack=True,scope='Watched boundary provenance, not a global unbroken CPU trace')
   if before:
    pc=before['opcode_PC'];bank=before['actual_PRG_banks'][(pc-0x8000)//8192];raw=rom[offset(bank,pc):offset(bank,pc)+3];ticks=hit['cycle']-before['cycle'];proof.update(previous_ROM_bytes=raw.hex(' ').upper(),cycle_ticks=ticks)
    if raw[0]in(0x20,0x4C)and int.from_bytes(raw[1:],'little')==entry and ticks==(72 if raw[0]==0x20 else 36):
     kind='call'if raw[0]==0x20 else'trampoline'if entry==0xBAB3 else'tail';transfer=pc;assert(before['SP']-s)&255==(2 if kind=='call'else 0)
    elif raw[0]==0x6C and ticks==60:
     p=int.from_bytes(raw[1:],'little');h=(p&0xFF00)|((p+1)&255)
     if p<0x2000 and ram[p&2047]|ram[h&2047]<<8==entry and before['SP']==s:kind='far_indirect_jump'if entry==0xA006 and pc==0xEE4A else'indirect_dispatch_or_tail';transfer=pc;proof['actual_indirect_pointer']=p
   frame_owner=dict(kind='captured_existing_frame_creator_not_fully_observed',existing_stack_word=word,return_PC=(word+1)&65535,SP=s,creation_PC=None,not_inferred_from_return_word_minus3=True)
   if entry in(0xA006,0xBAB3,0xBBA0)and word==0xEE4C:frame_owner.update(kind='EE07_constructed_far_callee_frame'if entry==0xA006 else'inherited_EE07_far_callee_frame',original_protocol_push_PCs=[0xEE46,0xEE49],original_protocol_return_word=0xEE4C)
   elif kind=='call':assert word==(transfer+2)&65535;frame_owner.update(kind='observed_original_JSR_frame',creation_PC=transfer)
   folder=CPU/'actual-callers'/f'entry-{entry:04X}-{case}-stage{stage}-{x["snapshot_sequence"]:04d}';folder.mkdir(parents=True,exist_ok=True);(folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram);n163=bytes((11+37*i)&255 for i in range(128));(folder/'input-n163.bin').write_bytes(n163)
   pointer=ram[0]|ram[1]<<8;aligned_city=(pointer-0x6000)//32 if 0x6000<=pointer<0x63C0 and not(pointer-0x6000)%32 else None
   context=dict(schema='phase29-passive-postbattle-completion-caller-with-device-fixture-v1',origin='passive_Native_callee_capture_with_explicit_N163_fixture',ancestry_origin='controlled_ancestry'if controlled else'natural_ancestry',controlled_ancestry=controlled,natural_ordinary_input_route=prep['natural_ordinary_input_route'],registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,scope='Common Source/originalCPU fixture, not instantaneous Native device capture'),prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],inherited_Native_preparation=prep['known_inherited_preparation'],known_inherited_preparation_byte_writes=prep['known_inherited_preparation_byte_writes'],ancestry_provenance=prep,controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0])],actual_call_kind=kind,immediate_transfer_PC=transfer,immediate_transfer_proof=proof,real_return_frame_owner=frame_owner,stage=stage,fade_sign=sign,input_pointer00=pointer,aligned_real_city_pointer00=aligned_city,owner_scope='Root_frozen_CC29_or_full_D4F0_only'if entry in EXTRA else'PostbattleCompletionServices',passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(rp.relative_to(ROOT)),RAM_sha256=sha(rp),SRAM_path=str(sp.relative_to(ROOT)),SRAM_sha256=sha(sp),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=sha(manifest),events_path=str((parent/'events.jsonl').relative_to(ROOT)),events_sha256=sha(parent/'events.jsonl'),preparation_path=str((parent/'preparation.json').relative_to(ROOT)),preparation_sha256=sha(parent/'preparation.json')),actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False)
   dump(folder/'context.json',context);exports.append(folder);counts['Root'if entry in EXTRA else'Source']+=1
   for p in(path,rp,sp,parent/'preparation.json',parent/'events.jsonl',*folder.iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
 assert counts=={'Source':26,'Root':8},counts
 dump(CPU/'evidence.json',dict(schema='phase29-passive-postbattle-completion-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,exported_caller_inputs=34,Source_NEW5_inputs=26,Root_frozen_CC29_full_D4F0_inputs=8,source_CPU_cases=0,original_CPU_prefix_instructions=0,instant_N163_captured=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},limits=['Two ancestries remain distinct;19 known older preparation writes are not a claim all ancestors only contain19.','Stage3 nonnegative87 returns each invocation, not a suspended ECEE wait.','Unknown immediate transfer is leftnull; actual capturedentry/stack is not inferred from rawret-minus3.','Instantaneous N163/PPU/APU was not captured; explicit common fixture is separate.']))
 (CPU/'README.md').write_text('''# 阶段3真实软件调用输入

两路线各13份NEW5现场：A006/BAB3/BBA0首次hold与87负各一、BBB8一次、BC00实际六次（城4及邻2/12/11/3/1）。后两次无hit仍扫满十槽，不能从仅有store的次数倒推总调用。另各四份冻结CC29/完整D4F0 frame1与21只供Root验证，不记本Source新body。unique34、本体26、Root8，来源本身新增Source CPU例0。

保留真实2K/8K/AXYP-SP-PC/四PRG与原栈。实际call_kind/transfer_PC必须由watched边界/原opcode/周期/SP支持；未知保持null，不用ret−3猜JSR。各context有real_return_frame_owner和完整ancestry_provenance；自然0准备与positive19项已知、更早未知边界分列。N163未瞬时捕获，commonfixture及端口声明明确，固定原核没有内部trace。

两阶段3时点是不同callback，不把它们当同一个跨帧挂起的ECEE。原机自然8次／受控祖先6次同值roster写不能证明非平凡chief swap；非平凡swap、firstmatch、FF洞、rawowner/IO及livealias由受控原CPU/Source独立对照，不能冒称自然观察。
''')
 return exports

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--import-native-callees',action='store_true');p.add_argument('--import-only',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 if a.import_native_callees:import_native(rom)
 if a.import_only:return
 mem=[0]*65536;mem[0xA000:0xC000]=rom[16+8*8192:16+9*8192];d=Disassembler(MPU(memory=mem));code=[];pc=0xBBA0
 while pc<0xBC46:
  n,text=d.instruction_at(pc);code.append(dict(physical_bank=8,cpu=pc,rom_offset=offset(8,pc),bytes=n,raw_hex=bytes(mem[pc:pc+n]).hex(' ').upper(),assembly=text));pc+=n
 assert pc==0xBC46 and len(code)==81 and sum(r['bytes']for r in code)==166
 ranges=[]
 for bank,start,size,name in((8,0xBBA0,166,'stage3 gate plus city and chief closure'),(16,0x9D72,240,'legal30city eightbyte neighbor rows'),(16,0x9E62,16,'raw index30/31 adjacent machine data'),(31,0xF379,32,'seven legitimate ruler words plus adjacent raw selector bytes;7 skipped')):
  raw=rom[offset(bank,start):offset(bank,start)+size];ranges.append(dict(physical_bank=bank,cpu_start=start,rom_offset=offset(bank,start),bytes=size,raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name))
 dump(OUT/'static-catalog.json',dict(schema='phase29-completion-exact-source-byte-catalog-v1',ROM_sha256=ROM_SHA256,new_exact_protocol_positions=81,new_exact_protocol_bytes=166,new_semantic_first_recovery=False,existing_semantics=['source/recovered/battle_state_machine.py:promote_city_leader','source/recovered/battle_state_machine.py:finalize_city_ownership','source/recovered/city_ownership.py:finalize_battle_ownership'],fixed_dependencies=[0xF25F,0xF2AF,0xF368],original_instructions=code,code_and_data_ranges=ranges,formal_auxiliary_field_names_still_unknown=True,phase27_indirect_authority_ledger_unchanged=True))
 (OUT/'original.asm').write_text('\n'.join(f'08:{r["cpu"]:04X} {r["raw_hex"]:<12} {r["assembly"]}'for r in code)+'\n')
 cp=CPU/'evidence.json'
 if cp.exists():
  provenance=json.loads(cp.read_text());provenance['source_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(__file__);dump(cp,provenance)
 v=json.loads((OUT/'validation.json').read_text());assert v['status']=='passed'and not v['quick']and v['passive_software_caller_cases']==26 and v['new_regression_groups']=={'inherited_stage2_ECEE_protocol_in_completion_driver':2}
 for path,digest in v['source_sha256'].items():assert sha(ROOT/path)==digest,path
 source=ROOT/'source/recovered/postbattle_completion_services.py';tree=ast.parse(source.read_text());assert {'complete_after_palette_transition','finalize_current_city_and_neighbor_chiefs','promote_city_ruler_in_roster'}<={n.name for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)}
 dynamic={(r['physical_bank'],r['cpu_address'])for r in v['executed_instruction_positions']};covered={(r['physical_bank'],r['cpu'])for r in code}&dynamic;pins={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'validation.json',CPU/'evidence.json')}
 result=dict(schema='phase29-completion-exact-readable-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,source_path=str(source.relative_to(ROOT)),source_sha256=v['source_sha256'],analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),validator_path='scripts/verify_postbattle_completion_services.py',validator_sha256=sha(ROOT/'scripts/verify_postbattle_completion_services.py'),artifact_sha256=pins,original_CPU_parent_cases=v['original_CPU_parent_cases'],controlled_cases=v['controlled_cases'],passive_software_caller_cases=v['passive_software_caller_cases'],new_regression_groups=v['new_regression_groups'],counts=v['counts'],source_guard_count=v['source_guard_count'],new_exact_protocol_positions=81,new_exact_protocol_bytes=166,new_protocol_dynamic_positions=len(covered),new_protocol_not_dynamically_covered_positions=81-len(covered),new_semantic_first_recovery=False,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False);dump(OUT/'evidence.json',result)
 (OUT/'README.md').write_text(f'''# 精确战后阶段3与城市首将收尾

PostbattleCompletionServices(PostbattleParentServices)的NEW5为A006/BAB3/BBA0/BBB8/BC00。stage2正文继承冻结28；0/1仍停在原dispatch目标。stage3每次独立调用读87：非负即正常RTS，不yield等待、不写ack；负才真JSR BBB8，返回后写7A=1/0400=13/0401=0。0500/0501保留，不能把原机后续淡入与城市控制器重新初始化混成此body写入。

新增精确协议81原位置/166B。旧promote_city_leader/finalize_city_ownership及phase6组合已有玩法语义，本轮不称首次恢复owner/chief算法；新增是完整register/scratch/stack/mapper/read-write顺序与父调用。F25F仅选择E1数据页16，F2AF建城ptr，BC00复制00/01到0A/0B后F368借00/01读leader，保持完整原协议；外层EE07恢复代码pair但不回滚8000页副作用。

BBB8仅outcome0写byte0=(old&F0)|(0507>>4)，高nibble保留。然后当前城及9D72+u8(city<<3)邻接逐项修首将，只精确FF终止，Y bytewrap，不额外加8项limit或signsentinel。合法30城表已有FF不扩成任意rawcity的正常资格；raw30..255单独作为机器数据/实际CPU输入对照。

BC00读owner&0F，仅7跳过。0..6是合法ruler，8..15保留F368合法七项表之后的相邻机器字节，不clamp或改&7；这不是十六个合法ruler。owner8→5F20需要显式硬件输入，缺失即真实PC BC1C/原SP的可恢复ServiceWait；提供共同输入后同generator继续，未改冻结Shared。其他ServiceCall仍必须statusreturned+实际PC/SP。

名册17..26十槽找firstequal，不因FF早停，不查HP/status/地点。匹配时即使同槽/同值仍做两次实际store；保存Y到真实栈，firstslot和foundslot每次重读live0A/B。受控FFF9裸指针例使首store写000A将pointer变FFFF，第二store真实落0011；裸city+1和city+11亦可读写辅助偏移，不能将完整F2AF城基址无aux命中泛化到任意BC00。

本体Source {v['original_CPU_parent_cases']}例（{v['controlled_cases']}受控、{v['passive_software_caller_cases']}被动软件输入），{json.dumps(v['counts'],ensure_ascii=False)}，另{v['source_guard_count']} guards；81位置动态{len(covered)}/81。完整2048RAM含闲置栈、8192SRAM、AXYP-SP-PC、四实际页、交织logicalIO、共同声明N163及逐写EA/value均比较。SourceCPUcallbacks0、IR0，无新NMI/IRQ/ready/ack。原CPU不是dummy总线模拟，Native的STA dummy单列。

新增同generator回归组inherited_stage2_ECEE_protocol_in_completion_driver有2例：new-driver-stage2-ECEE-resume/A006及/BB93。它们均实例化本轮PostbattleCompletionServices，并断言实际使用新的_drive；先与原CPU对齐真实ECEE入口，再验证只返回status=returned但未恢复PC/SP的服务不会推进、不会重复已发生的状态或IO、保留同一个pending ServiceCall与program generator，最后接真实冻结Shared服务恢复完整原caller RTS。两个完整受控父序列各计1个CPU例，不再将内部检查计作独立guard，也不是原机跨帧淡出完成或新增Native输入。

26正式NEW5软件输入与8个Root冻结CC29/完整D4F0入口分开，见../cpu-completion；N163不是现场捕获。自然退却、受控祖先19已知准备/更早未知分别保留。原机同值roster写不是非平凡swap实证；非平凡swap、FF洞、重复firstmatch、rawowner和livealias是受控软件对照，不能冒称自然玩法。

本模块不改城市辅助字段正式名、不改变冻结1526/328账本，不覆盖stage0/1，也不宣称全战后/全ROM完成。复现仅运行新29：analyze_postbattle_completion_services.py ROM --import-native-callees --import-only；verify_postbattle_completion_services.py ROM；analyzer ROM --evidence-only。
''')
 print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','new_protocol_dynamic_positions')}))
if __name__=='__main__':main()
