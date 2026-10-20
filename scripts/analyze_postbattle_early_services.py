#!/usr/bin/env python3
"""Pin phase30 early postbattle raw bytes, Source contracts and passive inputs."""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.battle_setup_ai import ROM_SHA256
from source.recovered.postbattle_early_services import PostbattleEarlyServices
OUT=ROOT/'analysis/phase30/early-services';CPU=ROOT/'analysis/phase30/cpu-early'
CASES=('natural-stage0-human','natural-stage1-mode0','controlled-stage0-human')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def offset(bank,pc):return 16+bank*8192+(pc&8191)
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def import_native(rom):
 manifest=ROOT/'analysis/phase30/runtime/evidence.json';assert json.loads(manifest.read_text())['status']=='passed';pins={str(manifest.relative_to(ROOT)):sha(manifest)};exports=[];counts=Counter();targets=Counter();ancestries=Counter()
 for case in CASES:
  parent=ROOT/'analysis/phase30/runtime'/case/'observer';prep=json.loads((parent/'preparation.json').read_text());events=[json.loads(s)for s in(parent/'events.jsonl').read_text().splitlines()];controlled=prep['controlled_ancestry'];selected=set()
  for path in sorted(parent.glob('callee-*.json')):
   x=json.loads(path.read_text());entry=x['entry']
   if entry not in PostbattleEarlyServices.NEW_ENTRIES:continue
   rp=parent/x['exported_RAM'];sp=parent/x['exported_SRAM'];ram=rp.read_bytes();sram=sp.read_bytes();r=x['actual_registers'];stage=ram[0x501];mode=sram[0xF91];side=ram[0x504]
   if entry in(0xA006,0xBAB3)and stage not in(0,1):continue
   key=entry,stage,mode,side
   if key in selected:continue
   selected.add(key);s=r['sp'];word=ram[0x100+((s+1)&255)]|ram[0x100+((s+2)&255)]<<8
   assert len(ram)==2048 and len(sram)==8192 and sha(rp)==x['RAM_sha256']and sha(sp)==x['SRAM_sha256']and word==x['stack_top_word_raw']and r['pc']==entry and x['additional_core_memory_writes']==0
   assert tuple(x['actual_PRG_banks'][1:3])==(8,9)
   i=next(i for i,e in enumerate(events)if e['sequence']==x['event_sequence']);hit=events[i];prior=[e for e in events[:i]if e['kind']=='opcode_boundary'];before=prior[-1]if prior else None
   kind='unknown';transfer=None;proof=dict(callee_opcode_boundary=hit,previous_watched_opcode_boundary=before,not_inferred_from_return_stack=True,scope='Watched boundary provenance; not a globally unbroken CPU trace')
   if before:
    pc=before['opcode_PC'];bank=before['actual_PRG_banks'][(pc-0x8000)//8192];raw=rom[offset(bank,pc):offset(bank,pc)+3];ticks=hit['cycle']-before['cycle'];proof.update(previous_ROM_bytes=raw.hex(' ').upper(),cycle_ticks=ticks)
    if raw[0]in(0x20,0x4C)and int.from_bytes(raw[1:],'little')==entry and ticks==(72 if raw[0]==0x20 else 36):
     kind='call'if raw[0]==0x20 else'trampoline'if entry==0xBAB3 else'tail';transfer=pc;assert(before['SP']-s)&255==(2 if kind=='call'else 0)
    elif raw[0]==0x6C and ticks==60:
     ptr=int.from_bytes(raw[1:],'little');high=(ptr&0xFF00)|((ptr+1)&255)
     if ptr<0x2000 and ram[ptr&2047]|ram[high&2047]<<8==entry and before['SP']==s:kind='far_indirect_jump'if entry==0xA006 and pc==0xEE4A else'indirect_dispatch_or_tail';transfer=pc;proof['actual_indirect_pointer']=ptr
   frame_owner=dict(kind='captured_existing_frame_creator_not_fully_observed',existing_stack_word=word,return_PC=(word+1)&65535,SP=s,creation_PC=None,not_inferred_from_return_word_minus3=True)
   if entry in(0xA006,0xBAB3,0xBAC1,0xBB3D)and word==0xEE4C:frame_owner.update(kind='EE07_constructed_far_callee_frame'if entry==0xA006 else'inherited_EE07_far_callee_frame',original_protocol_push_PCs=[0xEE46,0xEE49],original_protocol_return_word=0xEE4C)
   elif kind=='call':assert word==(transfer+2)&65535;frame_owner.update(kind='observed_original_JSR_frame',creation_PC=transfer)
   folder=CPU/'actual-callers'/f'entry-{entry:04X}-{case}-stage{stage}-mode{mode}-{x["snapshot_sequence"]:04d}';folder.mkdir(parents=True,exist_ok=True);(folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram);n163=bytes((11+37*j)&255 for j in range(128));(folder/'input-n163.bin').write_bytes(n163)
   context=dict(schema='phase30-passive-postbattle-early-caller-with-device-fixture-v1',origin='passive_Native_callee_capture_with_explicit_N163_fixture',ancestry_origin='controlled_ancestry'if controlled else'natural_ancestry',controlled_ancestry=controlled,natural_ordinary_input_route=prep['natural_ordinary_input_route'],registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,scope='Common Source/originalCPU fixture; not instantaneous Native device capture'),prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],inherited_Native_preparation=prep['known_inherited_preparation'],known_inherited_preparation_byte_writes=prep['known_inherited_preparation_byte_writes'],ancestry_provenance=prep,controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0])],actual_call_kind=kind,immediate_transfer_PC=transfer,immediate_transfer_proof=proof,real_return_frame_owner=frame_owner,stage=stage,mode=mode,side=side,owner_scope='Root_NEW5_and_child'if entry in PostbattleEarlyServices.NEW_ENTRIES else'child_named_allocation_helper_only',passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(rp.relative_to(ROOT)),RAM_sha256=sha(rp),SRAM_path=str(sp.relative_to(ROOT)),SRAM_sha256=sha(sp),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=sha(manifest),events_path=str((parent/'events.jsonl').relative_to(ROOT)),events_sha256=sha(parent/'events.jsonl'),preparation_path=str((parent/'preparation.json').relative_to(ROOT)),preparation_sha256=sha(parent/'preparation.json')),actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False)
   dump(folder/'context.json',context);exports.append(folder);counts['Root_NEW5'if entry in PostbattleEarlyServices.NEW_ENTRIES else'child_helpers']+=1;targets[f'{entry:04X}']+=1;ancestries[context['ancestry_origin']]+=1
   for p in(path,rp,sp,parent/'preparation.json',parent/'events.jsonl',*folder.iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
 assert exports and set(PostbattleEarlyServices.NEW_ENTRIES)<=set(int(k,16)for k in targets),targets
 dump(CPU/'evidence.json',dict(schema='phase30-passive-postbattle-early-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,exported_caller_inputs=len(exports),counts=dict(counts),targets=dict(targets),ancestries=dict(ancestries),source_CPU_cases=0,original_CPU_prefix_instructions=0,instant_N163_captured=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},limits=['Three imported snapshot windows retain natural versus controlled ancestry;19 known older writes do not bound all earlier preparation.','No immediate transfer or caller JSR is inferred from raw return-minus3.','Instantaneous N163/PPU/APU is not captured; common explicit fixture remains separate.','Actual observed modes and call sites must be read from captures; controlled Source mode2 or BB36 coverage is not Native proof.']))
 (CPU/'README.md').write_text('''# 阶段30真实软件调用输入

三个原存档短窗分自然stage0human、自然stage1mode0及受控祖先stage0human/后续mode1。每个导出保留实际2K/8K/AXYP-SP-PC/四PRG/原栈；同一entry/stage/mode/side只选首现场，导出范围只含NEW5。其它helper与inline目标的原capture保留在Native目录，不把它们伪造为新增JSRcaller；完整父case已经执行其真实正文。immediate_transfer_PC未知即null，不用ret−3造JSR。祖先0或19已知写及更早unknown完整保留，不称本轮冷启或新准备。

N163未瞬时捕获，input-n163.bin与端口值是共同显式软件夹具。原CPU/Source比较不是fixedcore逐指令trace；被动核只在此路径与固定核逐帧五buffer相同。Source内部不注入NMI/IRQ、PC、ready或ack。
''')
 print(json.dumps(dict(exported=len(exports),counts=dict(counts),targets=dict(targets))))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--import-native-callees',action='store_true');p.add_argument('--import-only',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 if a.import_native_callees:import_native(rom)
 if a.import_only:return
 m=[0]*65536;m[0xA000:0xC000]=rom[16+8*8192:16+9*8192];d=Disassembler(MPU(memory=m));code=[]
 for lo,hi in((0xBAC1,0xBB93),(0xBC46,0xBC4C),(0xBC52,0xBF0A)):
  pc=lo
  while pc<hi:
   size,text=d.instruction_at(pc);code.append(dict(physical_bank=8,cpu=pc,rom_offset=offset(8,pc),bytes=size,raw_hex=bytes(m[pc:pc+size]).hex(' ').upper(),assembly=text));pc+=size
  assert pc==hi
 assert len(code)==410 and sum(r['bytes']for r in code)==912
 ranges=[]
 for bank,start,size,name in((8,0xBAC1,210,'stage0 and stage1 routing bodies'),(8,0xBC46,708,'three-mode allocator including sixbyte inline table'),(16,0x9D72,256,'byte-indexed adjacency data plus adjacent raw data'),(31,0xF379,32,'seven legitimate ruler words plus following raw selectors; no16ruler claim')):
  raw=rom[offset(bank,start):offset(bank,start)+size];ranges.append(dict(physical_bank=bank,cpu_start=start,rom_offset=offset(bank,start),bytes=size,raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name))
 callees=Counter()
 for r in code:
  raw=bytes.fromhex(r['raw_hex'])
  if raw[0]==0x20:callees[f'{int.from_bytes(raw[1:],"little"):04X}']+=1
 dump(OUT/'static-catalog.json',dict(schema='phase30-early-exact-source-byte-catalog-v1',ROM_sha256=ROM_SHA256,new_exact_protocol_positions=410,new_exact_protocol_code_bytes=912,inline_table_bytes=6,new_semantic_first_recovery=False,existing_semantics=['source/recovered/postbattle.py:process_ai_officers','source/recovered/battle_state_machine.py:finalization_phase'],new_public=list(PostbattleEarlyServices.NEW_ENTRIES),named_local_helpers=list(PostbattleEarlyServices.ALLOCATION_HELPERS),original_instructions=code,code_and_data_ranges=ranges,JSR_callee_counts=dict(callees),dispatch_table=dict(cpu=0xBC4C,targets=[0xBC52,0xBD59,0xBD67],raw_hex=rom[offset(8,0xBC4C):offset(8,0xBC52)].hex(' ').upper()),fixed_dependencies=[0xF368,0xF2AF,0xF2D7,0xF266,0xF25F,0xE856],formal_auxiliary_field_names_still_unknown=True,frozen_pointer_authority_ledger_unchanged=True))
 (OUT/'original.asm').write_text('\n'.join(f'08:{r["cpu"]:04X} {r["raw_hex"]:<12} {r["assembly"]}'for r in code)+'\n')
 cp=CPU/'evidence.json'
 if cp.exists():
  x=json.loads(cp.read_text());x['source_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(__file__);dump(cp,x)
 v=json.loads((OUT/'validation.json').read_text());assert v['status']=='passed'and not v['quick']
 for path,h in v['source_sha256'].items():assert sha(ROOT/path)==h,path
 passive_groups={phase:sum(r['case'].startswith(f'passive-p{phase}/')for r in v['cases'])for phase in(29,30)};assert passive_groups=={29:26,30:14},passive_groups
 source=ROOT/'source/recovered/postbattle_early_services.py';tree=ast.parse(source.read_text());assert {'route_attacking_side_disposition','route_defending_side_disposition','allocate_AI_officers','fill_pointed_city_roster'}<={n.name for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)}
 dynamic={(r['physical_bank'],r['cpu_address'])for r in v['executed_instruction_positions']};covered={(r['physical_bank'],r['cpu'])for r in code}&dynamic;pins={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'validation.json')}
 if cp.exists():pins[str(cp.relative_to(ROOT))]=sha(cp)
 result=dict(schema='phase30-early-exact-readable-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,source_path=str(source.relative_to(ROOT)),source_sha256=v['source_sha256'],analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),validator_path='scripts/verify_postbattle_early_services.py',validator_sha256=sha(ROOT/'scripts/verify_postbattle_early_services.py'),artifact_sha256=pins,original_CPU_parent_cases=v['original_CPU_parent_cases'],controlled_cases=v['controlled_cases'],passive_software_caller_cases=v['passive_software_caller_cases'],inherited_phase29_passive_cases=passive_groups[29],new_phase30_passive_cases=passive_groups[30],counts=v['counts'],nonlocal_return_count=v['nonlocal_return_count'],original_BB36_parent_call_cases=v['original_BB36_parent_call_cases'],original_BB8C_parent_call_cases=v['original_BB8C_parent_call_cases'],source_guard_count=v['source_guard_count'],new_exact_protocol_positions=410,new_exact_protocol_code_bytes=912,inline_table_bytes=6,new_protocol_dynamic_positions=len(covered),new_protocol_not_dynamically_covered_positions=410-len(covered),new_semantic_first_recovery=False,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False);dump(OUT/'evidence.json',result)
 (OUT/'README.md').write_text(f'''# 阶段30战后前两态与AI安置精确协议

PostbattleEarlyServices继承冻结29Completion，新增A006/BAB3/BAC1/BB3D/BC46精确owner。原四阶段0/1现在真实执行，2/3继承既有正文；BC46三表为BC52/BD59/BD67，非法mode不执行表外字节。Source无CPU/IRfallback，无新ready/request/RNG/PC/栈伪造或自动完成未知服务。

手工具名协议覆盖410原指令位置/912codeB+6B inline表。process_ai_officers与finalization_phase已经有独立玩法语义，本轮不称首次恢复。新增信用是完整caller、register/flags、scratch、原栈、mapper、交织logicalIO协议。旧高层依赖标签BB37/BB8D不等于实际JSR；原BB36→BC46→BB39及BB8C→BC46→BB8F已由bytes和CPU对照核实，历史文件不改。原CPU完整父病例BB36计{v["original_BB36_parent_call_cases"]}、BB8C计{v["original_BB8C_parent_call_cases"]}，逐row保留连续PC/实际REG/SP/栈顶4B；这是软件oracle证据，不等于Native到达数。

stage0先写五组CHR cache8/9，F368取0507高nibble；stage1取低nibble。controller整byte恰3才AI，不能&3。human分别按outcome零/非零交接0500=13/14、sub0、050B=17/2；不替人类选择或完成下一态。AI side80/0，mode为stage0 outcome0→0、非零→2，stage1 outcome0→1、非零→0。真实BC46返回后才INC0501，守住samecaller真实栈。

mode0先当前城17起填，mode1只邻城，mode2先源城052A第一FF；满城时原04可保EADE目标高字节BD，不重置为0。收军只排active sidebyteFF，不排active officerIDFF；首将扫描20槽，遇FF继续。临时表填终止符是至少一次的do-while，可超过21。邻城收集9D72+X负值终止/Xbyte递增，不能写固定8for；随后两个消费循环才真CPY8。既有名单/城市资格与裸helper的rawbyte域分列。

BD96每次live00/01读写；raw offset>=27仍先写一笔后比较，caller有效容量不泛化到裸输入。逃走将匹配时真实PHA/PLA先写052C再名册。空邻城分配后整个ownerbyte替换为ruler，不虚构status2/recordlocation同步。overflow首轮比较rulerleader，释放后02被u8(city<<3)覆盖，后续ID可能按rowbyte变status3；其余status低2清0并按E856/真实bank16邻表写byte5。F25F更新E1数据窗，F266更新DE主数据窗，两者原副作用各自保留，不全四页还原。

本体Source {v['original_CPU_parent_cases']}例（{v['controlled_cases']}受控，{v['passive_software_caller_cases']}被动软件输入）：{json.dumps(v['counts'],ensure_ascii=False)}；另{v['source_guard_count']}guards。410位置动态{len(covered)}/410；未命中{410-len(covered)}不叫全路径证明。对照完整2048RAM含闲置栈、8192SRAM、AXYP-SP-PC、四页、交织logicalIO及共同声明N163。py65不是硬件dummy总线模拟；原机观察独立列示。

新30owner实际动态跑stage2 ECEE缺服务→假returned未改PC/SP不推进/同pending与generator→真实Shared完整恢复；stage3每次新callback非负87真RTS、负才结算，以及缺5F20的真实设备wait/共同输入续跑。它们是独立软件CPU回归，不是新Native帧、跨帧挂起ECEE或借锁29hash代替测试。

继承setup_fields是旧setup调试键，不能将其中side_base等名字当战后字段定义；这里6F91是mode。入口API为run_entry(actualregisters)或真实ServiceCall，不能用默认构造值替caller。

14份新30实际输入和26份冻结29 NEW5回归分列，正式来源见../cpu-early。独立受控初值覆盖overflow RNG低3位八种选择及cursor255回卷、裸早态phase255的INC0501回零；不称合法UI入口或原机准备。祖先自然与19项已知受控/更早unknown分开；本轮无新增准备。瞬时N163未捕获，共同fixture另列。Native未走到的mode2/BB36不能因受控CPU命中而声称实机到达。字段+1与+28..31正式名称仍未知，冻结访问账本不因此改变；不宣称全ROM完成。

复现仅运行新30：analyze_postbattle_early_services.py ROM --import-native-callees --import-only；verify_postbattle_early_services.py ROM；analyze_postbattle_early_services.py ROM --evidence-only。本轮完成后停止，不自动启动31。
''')
 print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','new_protocol_dynamic_positions')}))
if __name__=='__main__':main()
