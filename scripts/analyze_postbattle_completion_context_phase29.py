#!/usr/bin/env python3
"""Read original bytes/AST/frozen receipts; write only new29/context.

No CPU/core, recovered gameplay, old producer, or control IR is executed.
The two CC29 name-pointer sites remain frozen candidates, not new exclusions.
"""
from pathlib import Path
import argparse,ast,csv,hashlib,json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/phase29/context'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SOURCES=(
 'source/recovered/postbattle_parent_services.py',
 'source/recovered/postbattle_parent_integration.py',
 'source/recovered/battle_state_machine.py',
 'source/recovered/battle_scene_controller.py',
 'source/recovered/scene_shared_services.py',
 'source/recovered/scene_coordinator.py',
 'source/recovered/postbattle_release_services.py',
)
INPUTS=(
 'analysis/phase28/verification.json',
 'analysis/phase28/context/verification.json',
 'analysis/phase28/context/parent-chain-and-owner.json',
 'analysis/phase28/context/fade-request-and-progress.json',
 'analysis/phase28/context/EE07-stack-and-mapper.json',
 'analysis/phase28/parent-services/validation.json',
 'analysis/phase28/source-integration.json',
 'analysis/phase27/fields-static/analysis-summary.json',
 'analysis/phase27/fields-static/all-indirect-accesses.json',
 'analysis/phase27/fields-static/remaining-accesses.json',
 'analysis/phase18/control/instruction-atlas.json',
 'analysis/phase6/ownership/evidence.json',
 'analysis/battle_fsm/validation.json',
 'scripts/verify_battle_fsm.py',
 'analysis/game_data/name_glyph_records.csv',
 'analysis/game_data/README.md',
)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def off(bank,pc):return 16+bank*8192+(pc&8191)
def save(n,d):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def function(path,name):
 n=next(x for x in ast.walk(ast.parse((ROOT/path).read_text()))if isinstance(x,ast.FunctionDef)and x.name==name)
 return dict(path=path,function=name,line=n.lineno,end_line=n.end_lineno,sha256=sha(ROOT/path))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');a=p.parse_args()
 rom=Path(a.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 baseline=read('analysis/phase28/verification.json');assert baseline['status']=='passed'
 for path in SOURCES:assert sha(ROOT/path)==baseline['source_and_validator_sha256'][path],path
 atlas=read('analysis/phase18/control/instruction-atlas.json')['instructions']
 atlas=sorted(atlas,key=lambda r:(r['physical_bank'],r['cpu']))
 by={(r['physical_bank'],r['cpu']):r for r in atlas}
 windows=((8,0xBAB3,0xBAB9),(8,0xBBA0,0xBC46),(13,0xCC29,0xCCE6),(13,0xD4F0,0xD4FB),(31,0xEBE9,0xEC22),(31,0xF2AF,0xF2D7),(31,0xF368,0xF379))
 raw=[]
 for r in atlas:
  if any(r['physical_bank']==bank and start<=r['cpu']<end for bank,start,end in windows):
   o=off(r['physical_bank'],r['cpu']);b=bytes.fromhex(r['raw_hex']);assert r['rom_offset']==o and rom[o:o+len(b)]==b
   raw.append({k:r[k]for k in('physical_bank','cpu','rom_offset','raw_hex','op','mode','operand')})
 data=[]
 for bank,start,size,label in((8,0xBAB9,8,'fourstage inline table'),(13,0xD4F8,2,'EE07 inline A006'),(16,0x9D72,240,'30x8 city adjacency'),(31,0xF379,32,'raw16 ruler pointer words; only first7 are ruler entries'),(13,0xCCE6,48,'24 sprite Y positions and24 X positions')):
  data.append(dict(physical_bank=bank,cpu=start,rom_offset=off(bank,start),raw_hex=rom[off(bank,start):off(bank,start)+size].hex(' ').upper(),label=label,is_opcode=False))
 assert rom[off(8,0xBBA0):off(8,0xBBB8)]==bytes.fromhex('AD8700101220B8BBA9018D7A00A90D8D0004A9008D010460')
 assert by[8,0xBBDF]['operand']==by[8,0xBBF7]['operand']==0xBC00
 assert by[8,0xBC2B]['operand']==0x1B and by[8,0xBC21]['operand']==0x11
 assert by[8,0xBBC3]['operand']==0x514 and by[8,0xBBC6]['operand']==0x17
 parent=read('analysis/phase28/context/parent-chain-and-owner.json')
 save('completion-chain.json',dict(schema='phase29-postbattle-completion-original-context-v1',ROM_sha256=ROM_SHA,
  phase28_frozen_owner=dict(frontdoor='PostbattleParentGameEngine / PostbattleParentSceneCoordinator',source=function(SOURCES[1],'_resolve_call'),new_public_entries=[0xA006,0xBAB3,0xBB93,0xC027],implemented_parent_stage=2,phase3_dispatch='Original BBA0 is yielded as a strict dispatch dependency; no artificial JSR frame or RTS.',BBA0_BBB8_BC00_direct_owner_not_declared_in_frozen28=True,scope='Concrete frozen28 route/entry AST, not an outdated generic AST model or a global missing-service count.',bounded_old_reader_erratum='The frozen25 generic Registry did not resolve the new28 conditional parent-owner construction in readonly review. Its no-owner result for A006 is a bounded-reader false negative; the concrete28 NEW_ENTRIES and pair route establish the declared owner. No frozen file is changed.'),
  parent_table=parent['dispatch_table_data'],four_states=parent['substates'],
  stage3=dict(entry=0xBBA0,gate=dict(pc=0xBBA0,address=0x87),hold=dict(branch_pc=0xBBA3,target=0xBBB7,normal_RTS=True),completion=dict(call_pc=0xBBA5,target=0xBBB8,return_pc=0xBBA8),post_cleanup_writes=[dict(cpu=0xBBAA,address=0x7A,value=1),dict(cpu=0xBBAF,address=0x400,value=13),dict(cpu=0xBBB4,address=0x401,value=0)],does_not_increment_or_clear_0501=True),
  immediate_vs_async='ECEE already returned in stage2. Stage3 is a fresh caller/gate on87; EC67 normal nonbusy NMI advances fade. Native fade completion does not implement missing Source stage3.',
  CPU_Source_Native_new_cases=0,all_four_states_complete=False))
 adj=rom[off(16,0x9D72):off(16,0x9D72)+240];adjrows=[]
 for city in range(30):
  row=adj[city*8:city*8+8];assert 255 in row;neighbors=list(row[:row.index(255)]);assert all(x<30 for x in neighbors)
  adjrows.append(dict(city=city,table_index=city*8,bytes=list(row),neighbors=neighbors,terminator_index=row.index(255)))
 save('ownership-and-roster-contract.json',dict(schema='phase29-BBB8-BC45-data-contract-v1',
  entries=[0xBBB8,0xBC00],calls=[dict(call_pc=0xBBBA,target=0xF25F,selector=0x30,physical_data_bank=16),dict(call_pc=0xBBC0,target=0xF2AF,input='050E raw byte'),dict(call_pc=0xBBDF,target=0xBC00),dict(call_pc=0xBBF4,target=0xF2AF,input='current non-FF adjacency byte'),dict(call_pc=0xBBF7,target=0xBC00),dict(call_pc=0xBC17,target=0xF368,input='citybyte0 &0F, except7')],
  ownership=dict(condition='0514==0',read_pc=0xBBD6,store_pc=0xBBDD,city_offset=0,preserve_mask=0xF0,new_low_nibble='0507>>4',other_outcomes_do_not_rewrite_owner=True),
  roster=dict(city_pointer_save='00/01 copied to0A/0B atBC00..BC09',owner_read_pc=0xBC0E,owner_mask=15,only_skipped_owner=7,leader_read_pc=0xBC1C,leader_offset=0,scan_read_pc=0xBC23,scan_Y=list(range(17,27)),bounded_by=dict(pc=0xBC2B,CPY=27),termination='Find ruler leader, or exactly10 slots; does not require FF sentinel.',swap_first_read_pc=0xBC34,first_Y=17,stores=[dict(pc=0xBC3C,Y=[17]),dict(pc=0xBC43,Y=list(range(17,27)))],roster_count_or_officer_status_not_written=True),
  adjacency=dict(physical_bank=16,table_cpu=0x9D72,table_rom_offset=off(16,0x9D72),initial_index='u8(050E<<3)',byte_Y_wrap=True,terminator=255,rows=adjrows,normal_city_domain=list(range(30)),longest_neighbors=max(len(x['neighbors'])for x in adjrows),raw_city_at_least30_termination_not_claimed=True),
  bare_suffix_counterexamples=[dict(entry=0xBC00,input_pointer=0x6001,pc=0xBC0E,Y=0,logical_address=0x6001,city_offset=1,scope='Address-formula counterexample only, not a new CPU/Native case.'),dict(entry=0xBC00,input_pointer=0x600B,pc=0xBC23,Y=17,logical_address=0x601C,city_offset=28,scope='Requires a suitable raw owner/leader path; address formula only, not normal full-entry reachability.')],
  limits=['Full BBB8 city-factory contract must not be applied to bareBC00 arbitrary00/01.','Owner0..6 uses7 proper ruler table words; raw8..15 still read following original bytes. Do not silently clamp or use&7.','Logical effective addresses exclude 6502 pagecross/store dummy reads.','No official meaning of city+1/+28..31 is established.']))
 table=rom[off(17,0x8DB4):off(17,0x8DB4)+237*13]
 with (ROOT/'analysis/game_data/name_glyph_records.csv').open()as f:
  names=list(csv.DictReader(f));assert len(names)==237
  for row in names:
   record=bytes.fromhex(row['raw_hex']);i=int(row['id']);assert table[i*13:(i+1)*13]==record
 cc_callees=[r for r in raw if r['physical_bank']==13 and 0xCC29<=r['cpu']<0xCCE6 and r['op']in('JSR','JMP')]
 cc_callers=[{k:r[k]for k in('physical_bank','cpu','rom_offset','raw_hex','op','operand')}for r in atlas if r['physical_bank']==13 and r['op']=='JSR'and r['operand']==0xCC29]
 save('CC29-name-draw-context.json',dict(schema='phase29-CC29-caller-name-pointer-context-v1',
  root=dict(entry=0xD4F0,draw_call=0xD4F0,draw_target=0xCC29,draw_return=0xD4F3,selector_LDY_pc=0xD4F3,selector=0x28,far_call=0xD4F5,inline_target=0xA006,normal_return=0xD4FA),
  frozen_precise_Source=dict(owner='BattleSceneController',strict_entry_adapter='PostbattleReleaseController inherits this body without duplicating it',strict_entry=function(SOURCES[6],'run_entry'),main=function(SOURCES[3],'draw_postbattle_units'),full_caller=function(SOURCES[3],'return_to_city'),locals=[function(SOURCES[3],n)for n in('local_cc45','local_cc5a','local_cc6d','local_ccaa','local_ccdf','multiply_24bit','ruler_pointer')],external_in_draw_closure=[dict(call_pc=0xCC2B,target=0xF25F)],does_not_prove_new29_source_completion=True),
  original_local_call_edges=cc_callees,original_same_physical_pair_callers=cc_callers,
  typed_lifecycle=dict(entry=0xCC29,data_selector=0x31,data_physical_bank=17,order_selector='005E&1 changes which side is drawn first',rulers='high/low nibble0507',first_factory='CC6D F368 then ruler+0 byte',leader_raw_domain=list(range(256)),multiply='EBE9 receives [00,01,02]=[leader,0,0],03=13; output low product06/07',record_pointer='8DB4+13*leader',first_read=dict(pc=0xCC92,Y=0),following_reads=dict(pc=0xCCAC,count=12,Y=0,increment_callee=0xCCDF),logical_address_range_inclusive=[0x8DB4,0x9AB3],normal237_name_range_inclusive=[0x8DB4,0x99BC],known_name_records=237,name_record_size=13,name_table_sha256=hashlib.sha256(table).hexdigest(),source_record_origin='analysis/game_data/name_glyph_records.csv',OAM_writes='For nonFF tile bytes:0200..0203+rawX, update7C=u8(X+4). Frame-end pointers do not substitute for opcode-time pointer.'),
  candidate_only_sites=[dict(physical_bank=13,cpu=x,raw_hex=by[13,x]['raw_hex'],frozen_classification='unresolved_pointer_or_index_contract',contract='Only completeCC29/CC6D established producer lifecycle; no new authoritative exclusion.')for x in(0xCC92,0xCCAC)],
  bare_suffix_counterexample=dict(entry=0xCCAA,input_pointer_06_07=0x6001,read_pc=0xCCAC,Y=0,logical_address=0x6001,scope='Formula only; bareCCAA is not constrained by a previousCC29 invocation.'),
  limits=['Candidate typed full-entry reasoning is not a new static1526 authority or new CPU contract.','No arbitrary call toCCAA or a middle load gets the full-entry pointer domain.','Raw leader237..255 is outside the known237-name table, despite remaining in ROM address space.','No asynchronous NMI/IRQ scratch-interleaving proof is added here.']))
 remaining=read('analysis/phase27/fields-static/remaining-accesses.json')['accesses'];allrows=read('analysis/phase27/fields-static/all-indirect-accesses.json')['accesses']
 connected=[]
 for r in remaining:
  near=r['physical_bank']==13 and 0xCC29<=r['cpu']<0xCCE6
  connected.append(dict(physical_bank=r['physical_bank'],cpu=r['cpu'],rom_offset=r['rom_offset'],raw_hex=r['raw_hex'],frozen_classification=r['classification'],connection='same_CC29_draw_closure'if near else'outside_narrow_completion_context',authority_unchanged=True))
 cleanup=[r for r in allrows if r['physical_bank']==8 and 0xBBB8<=r['cpu']<0xBC46]
 assert len(cleanup)==8 and all(r['classification']=='proved_disjoint_auxiliary_address_domain'for r in cleanup)
 assert len(remaining)==328 and sum(r['connection']=='same_CC29_draw_closure'for r in connected)==2
 save('auxiliary-field-links.json',dict(schema='phase29-completion-auxiliary-field-context-v1',all_frozen_remaining_candidates=connected,remaining_count=328,cleanup_remaining_candidates=0,draw_closure_remaining_candidates=2,all_other_remaining_candidates=326,cleanup_existing_authoritative_accesses=[dict(physical_bank=r['physical_bank'],cpu=r['cpu'],raw_hex=r['raw_hex'],classification=r['classification'],address_contract=r['address_contract'])for r in cleanup],new_authoritative_exclusions=0,newly_named_city_fields=0,official_names={str(i):None for i in(1,28,29,30,31)},address_scope='Logical effective data address, not every CPU bus read including dummy reads.'))
 legacy=read('analysis/battle_fsm/validation.json');owned=read('analysis/phase6/ownership/evidence.json');writer=next(x for x in owned['owner_writers']if x['physical_bank']==8 and x['CPU_store']==0xBBDD)
 assert legacy['semantic_counts']['finalize_city_ownership']==512 and legacy['semantic_counts']['finalization_phase']==256
 save('historical-credit.json',dict(schema='phase29-existing-completion-semantics-credit-v1',existing_named_functions=[function(SOURCES[2],n)for n in('promote_city_leader','finalize_city_ownership','finalization_phase')],old_finalize_city_ownership_cases=512,old_finalize_scope='SRAM comparison through old semantic API; not complete RAM/AXYP/stack/mapper protocol.',old_parent_cases=256,old_parent_ECEE_explicitly_bypassed=True,old_owner_writer=writer,new_exact_protocol_may_be_distinct_scope=True,old_named_CC29_not_new_algorithm=True,old_files_modified=False,new_Source_CPU_cases=0,new_original_CPU_cases=0,new_Native_runs=0))
 (OUT/'original-ranges.asm').write_text('; New29 readonly context; all offsets include16byte NES header\n'+'\n'.join(f"; bank{r['physical_bank']} file${r['rom_offset']:06X}\n${r['cpu']:04X}: {r['raw_hex']:<12}; {r['op']} {r['mode']} ${r['operand']:04X}"for r in raw)+'\n\n; Explicit original data\n'+'\n'.join(f"; bank{r['physical_bank']} CPU${r['cpu']:04X} file${r['rom_offset']:06X} {r['label']}\n.byte {r['raw_hex']}"for r in data)+'\n')
 save('original-positions.json',dict(schema='phase29-postbattle-original-byte-context-v1',ROM_sha256=ROM_SHA,instructions=raw,data=data))
 sourcepins={str(Path(__file__).relative_to(ROOT)):sha(__file__),**{p:sha(ROOT/p)for p in SOURCES}}
 save('analysis-summary.json',dict(schema='phase29-postbattle-completion-context-summary-v1',status='indexed_read_only',ROM_sha256=ROM_SHA,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,all_indirect_positions=1526,frozen_classification_counts={'proved_disjoint_auxiliary_address_domain':1198,'possible_city_auxiliary_alias':81,'unresolved_pointer_or_index_contract':247},remaining_candidates=328,context_new_exclusions=0,cleanup_existing_disjoint_sites=8,CC29_connected_unresolved_sites=2,official_city_auxiliary_names={str(i):None for i in(1,28,29,30,31)},raw345=dict(total=345,operand=104,known_data=13,no_proven_control_entry=228),unknown_unique_services=None,all_four_parent_states_complete=False,source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256={p:sha(ROOT/p)for p in INPUTS}))
 (OUT/'README.md').write_text('''# 战后完成阶段：归属、名单与完整父调用边界

这是阶段29的新只读context，原CPU、Source与Native新增执行均0。只核原字节、冻结源码AST与历史回执，不运行旧producer，不替新Source或原机验证授予完成。

BBA0读取87；非负经BPL到BBB7直接RTS，负值才在BBA5真实JSR BBB8。BBB8返回后写global7A=1、城市0400=13/0401=0；这里不清或递增0501。ECEE早已在阶段2同步请求并返回，状态3不是继续等待中的ECEE服务。冻结28前门只实现阶段2，状态0/1/3保持真实dispatch依赖；同一caller/generator与PC/SP需由新精确服务另证。

归属模型须区分实际源码和有限索引。旧25通用Registry的只读复核没有识别28新增的条件owner构造，曾给A006空owner；这是索引模型的false negative，不代表实际Source未接管。此处以28具体pair路由和NEW_ENTRIES核A006/BAB3/BB93/C027的ParentServices归属，不改旧脚本、旧输出，也不把无owner字样换算成缺失服务总数。

BBB8选择F25F30的数据bank16，F2AF取得本城32B记录。仅outcome0514==0把城市byte0改为(old&F0)|(0507>>4)，保留高四位。随后处理本城及邻城：BC00把城市指针保存到0A/0B，读取owner&0F，只跳过7；其余原值经F368取首将ID，在城市17..26十槽有界寻找，找到才和17互换。它不读FF寻找终止，也不写名册数量或武将status。正常30城的8字节邻接行均含FF，最长7个邻居；raw city≥30的移位/Y回绕与原后续数据不能据此预授终止。

上述8个间接点冻结27均已有条件不交合同，没有本轮新排除，亦未发现+1/+28..31的专用消费者。裸BC00输入仍能使公式读到+1或尾部，完整BBB8的F2AF厂针前提不可移植到裸后缀。

13D4F0先真实调用CC29，D4F3再LDY28，D4F5才是EE07 inlineA006。旧28从D4F5开始的桥未覆盖前置绘制。CC29及其CC45/CC5A/CC6D/CCAA/CCDF早已由BattleSceneController具名实现；闭包仅F25F为外部服务。CC29选择bank17并按ruler首将byte算8DB4+13*ID，读首CHR页和12个tile，写OAM并按5E&1改变两方先后。237条旧姓名记录是独立像素数据来源；raw ID237..255超出该237条表。完整入口下名称指针候选范围8DB4..9AB3在ROM窗，但裸CCAA的06/07没有此限制。

328剩余候选里仅CC92/CCAC直接属于此绘制闭包；本目录把完整入口与裸后缀的区别作为可复查线索，不更新权威分类，不新增原CPU合同。另326项不在这个狭窄上下文，不能据此作未使用结论。

旧finalize_city_ownership已有512个SRAM语义案，旧finalization_phase有256案且两侧显式bypass ECEE；本轮若补精确寄存器、栈、映射或完整父链，是不同验收scope，不是首次恢复归属算法。旧名称绘制同样不重新计入首次恢复。

稳定1526=1198条件不交/81可能/247未知，剩328；raw345=104操作数/13数据/228未证入口。本目录新排除0，城市+1/+28..31正式名称、未知服务总数保持null，全父四态闭合为false。逻辑有效地址合同和6502 dummy总线读须分开。
''')
 print(json.dumps(dict(status='indexed_read_only',cleanup_sites=8,connected_candidates=2,remaining=328,new_exclusions=0,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)))
if __name__=='__main__':main()
