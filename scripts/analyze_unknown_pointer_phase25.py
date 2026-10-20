#!/usr/bin/env python3
"""One additive full-word appearance-table constructor, with must entry proof."""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase25/fields-static'
spec=importlib.util.spec_from_file_location('frozen24_pointer_model',ROOT/'scripts/analyze_unknown_pointer_phase24.py');old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
base=old.base;DISJOINT=old.DISJOINT;TARGETS=frozenset(((11,0xC61F),(11,0xC624)))
WORDS=frozenset(0x8B1C+20*raw for raw in range(256))
PREFIX=(0xC5F8,0xC5FB,0xC5FD,0xC5FF,0xC601,0xC604,0xC606,0xC609,0xC60B,0xC60C,0xC60E,0xC610,0xC612,0xC614)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
class Analysis(old.Analysis):
 def __init__(self,rom):
  super().__init__(rom)
  raw=bytes.fromhex('AD36008520A91485212071D4A9008D3700A52A18691C8522A52B698B8523')
  assert rom[base.original(11,0xC5F8):base.original(11,0xC616)]==raw
  multiply=bytes.fromhex('A007A900852C852A852B4621900DA52018652A852AA52C652B852B0620262C8810E860')
  assert rom[base.original(11,0xD471):base.original(11,0xD494)]==multiply
  ident=max(self.factory_ids)+1
  self.appearance_descriptor=dict(id=ident,entry=(11,0xC5F8),marker=(11,0xC614),end=0xC614,base=0x22,kind='appearance_complete_raw8_times20_plus8B1C',addresses=WORDS,prologue=frozenset((11,pc)for pc in PREFIX),marker_half=1)
  d=self.appearance_descriptor;self.templates.setdefault(d['entry'],[]).append(d);self.factory_ids[ident]=d;self.markers[d['marker']]=d
 def transfer(self,key,state):
  result=super().transfer(key,state)
  # The inherited scalar-cell layer conservatively invalidates pointer facts
  # at the final STA. Install this exact new constructor's postcondition
  # after that store, using its input must-builder, never a matching PC alone.
  d=self.appearance_descriptor
  if key==d['marker']and d['id']in state.builders:
   base.atomic_pair(result,0x22,self.fact(d,d['entry']))
   result.registers=(frozenset(((0x22,1),)),)+result.registers[1:]
  return result
 def apply_call(self,state,target,key,far=False):
  result=super().apply_call(state,target,key,far)
  # Only this validated constructor's pending capability passes its one
  # exact multiply call. This does not restore any pointer, scalar, half or
  # generic builder that the real helper/clobber summary killed.
  ident=self.appearance_descriptor['id']if hasattr(self,'appearance_descriptor')else None
  if key==(11,0xC601)and target==(11,0xD471)and ident in state.builders:
   result.builders|=frozenset((ident,))
  return result
def prove_mapping_lifetime(e):
 """Finite original call closure and typed stores before the selected reads.

 This is a persistence theorem under this entry, not bank17 inferred from
 a frame-end shadow. The final unbounded append scan returns afterwards;
 it is deliberately not granted a universal no-alias/store theorem.
 """
 root=(11,0xC5D2);queue=[root];seen=set();nodes=set();functions=[]
 while queue:
  entry=queue.pop()
  if entry in seen:continue
  seen.add(entry);f=e.function_structure(entry);assert not f['barriers'];nodes|=f['nodes'];queue.extend(f['calls'])
  functions.append(dict(entry=e.raw(entry),original_instruction_count=len(f['nodes']),callees=[e.raw(k)for k in sorted(f['calls'])],normal_RTS=[e.raw(k)for k in f['exits']]))
 expected={(11,0xC5D2),(11,0xC66F),(11,0xD105),(11,0xD283),(11,0xD304),(11,0xD471),(11,0xD4BB),(11,0xD69D),(31,0xE88A),(31,0xE89A),(31,0xF266)}
 assert seen==expected
 direct=[];indirect=[];ports=[]
 for key in sorted(nodes):
  row=e.known[key]
  if row['op']not in base.WRITES or row['mode']=='a':continue
  if row['mode']=='iy':indirect.append(e.raw(key));continue
  addresses=old.direct_addresses(row);assert addresses is not None
  direct.append(dict(instruction=e.raw(key),effective_addresses=sorted(addresses)))
  if any(a>=0x8000 for a in addresses):ports.append(key)
 assert ports==[(31,0xF269)]
 pointer_writes=[x['instruction']['cpu']for x in direct if any(base.normalized_ram(a)in(0x22,0x23)for a in x['effective_addresses'])]
 assert pointer_writes==[0xC60E,0xC614]
 assert {r['cpu']for r in indirect}=={0xC659,0xC66C,0xD6AF,0xD6B4,0xD6C8,0xD6CD}
 # C66C is the only potentially unbounded rawcity/Y store. It is followed
 # immediately by RTS, and cannot loop back to either selected ROM read.
 assert e.edges[11,0xC66C]==[(11,0xC66E)]and e.known[11,0xC66E]['op']=='RTS'
 body=e.function_structure(root)['nodes'];pred={key:set()for key in body};success={}
 for key in body:
  row=e.known[key]
  targets=[]if row['op']=='RTS'else[base.mapped(key,row['cpu']+row['size'])]if row['op']=='JSR'else e.edges.get(key,[])
  assert all(k in body for k in targets);success[key]=targets
  for target in targets:pred[target].add(key)
 dom={key:{root}if key==root else set(body)for key in body};changed=True
 while changed:
  changed=False
  for key in sorted(body):
   if key==root:continue
   assert pred[key];value={key}|set.intersection(*(dom[p]for p in pred[key]))
   if value!=dom[key]:dom[key]=value;changed=True
 assert all((11,0xC5D2)in dom[k]and(11,0xC5D4)in dom[k]and(11,0xC614)in dom[k]for k in TARGETS)
 return dict(schema='phase25-typed-appearance-mapping-lifetime-contract-v1',functions=functions,original_closure_instruction_positions=len(nodes),direct_write_inventory=direct,indirect_store_inventory=indirect,
  selected_mapper_call=e.raw((11,0xC5D4)),raw_selector=49,physical_data_bank=17,mapper_body=[e.raw((31,pc))for pc in(0xF266,0xF269,0xF26C)],
  mapper_and_constructor_dominate_selected_reads=True,pointer22_direct_writes=pointer_writes,only_explicit_PRG_mapper_write=e.raw((31,0xF269)),
  typed_indirect_write_domains=[dict(CPU=[0xD6AF,0xD6B4,0xD6C8,0xD6CD],base='6000+32*rawcity0..255',offsets=[2,3,4,5],addresses_min=0x6002,addresses_max=0x7FE5,may_alias_ZP_stack_or_mapper=False),dict(CPU=[0xC659],base='63C0+12*rawID0..255',offsets=[11],addresses_min=0x63CB,addresses_max=0x6FBF,may_alias_ZP_stack_or_mapper=False),dict(CPU=[0xC66C],scope='Unbounded append in a bare/raw suffix is not classified by this proof. It exits throughC66E without any later selected table read; normal caller capacity proof is separate.')],
  ordinary_contract='Enter C5D2 with original pair10/11 code windows and binary arithmetic; no IRQ/NMI or external mutation. Initial data window arbitrary: original LDY49/F266 selects17. Before each selected read, all other callees preserve22/23 and data mapping; direct constructor stores dominate; typed indirect stores cannot hit ZP/stack/mapper. A000..A007 still belongs to physical10 code window.',
  exclusions=['No all-C5D2-write disjointness or fullroster/raw append safety theorem.','No arbitrary middle-entry, malformed call-frame or interrupt atomicity theorem.','Logical read and dummy uncorrected page remain separately enumerated.'])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 e=Analysis(rom)
 lifetime=prove_mapping_lifetime(e);save('mapping-lifetime-contract.json',lifetime)
 for n in range(3):
  e.prove_returns();e.steps=0;e.states={};e.queue=deque();e.scheduled=set();roots,fallback=e.run();added=e.refine_write_effects()if n<2 else None
  e.refinement_rounds.append(dict(round=n+1,original_instruction_transfers=e.steps,new_non_ZP_store_proofs=added,return_contract_count=len(e.return_contracts)))
  if not added:break
 prior=json.loads((ROOT/'analysis/phase24/fields-static/all-indirect-accesses.json').read_text())['accesses'];rows=[]
 for oldrow in prior:
  key=oldrow['physical_bank'],oldrow['cpu'];proof=e.contract(key)if key in TARGETS else oldrow['address_contract'];row=dict(oldrow)
  row.update(phase24_classification=oldrow['classification'],newly_proved_disjoint=False)
  if key in TARGETS and proof:
   proof['required_execution_contract']=dict(constructor_entry_physical_bank=11,constructor_entry_cpu=0xC5F8,constructor_complete_after_cpu=0xC614,must_enter_full_constructor=True,raw_city_bytes='all0..255 retained',binary_arithmetic=True,normal_no_interrupt_execution=True,bare_middle_entry_covered=False,mapping_scope='Logical ROM address theorem does not assume a universally active data bank. C5D2 separately selects physical17 before its typed prefix; A000..A007 map physical10.')
   row.update(address_contract=proof,whole_pointer_values=sorted(WORDS),Y_values=proof['Y_values'],classification=DISJOINT if not old.old.old.auxiliary_intersection(proof)else'possible_city_auxiliary_alias',proof_basis='phase25_complete_original_multiply_prefix_must_builder',candidate_address_contract=None,candidate_whole_pointer_values=None,candidate_Y_values=None,candidate_contract_is_authoritative=False,authoritative_contract_origin=None,authoritative_pointer_representation='complete_joint_address_set')
   row['newly_proved_disjoint']=row['classification']==DISJOINT and oldrow['classification']!=DISJOINT
  rows.append(row)
 canonical={(r['physical_bank'],r['cpu']):r for r in rows};assert all(canonical[k]['address_contract']is not None for k in TARGETS)
 constructor=dict(schema='phase25-appearance-whole-pointer-constructor-v1',entry=e.raw((11,0xC5F8)),complete_after=e.raw((11,0xC614)),original_prefix_instructions=[e.raw((11,pc))for pc in PREFIX],multiply_entry=e.raw((11,0xD471)),multiply_original_instructions=[e.raw((11,pc))for pc in sorted(pc for b,pc in e.known if b==11 and 0xD471<=pc<=0xD493)],pointer_base=0x22,whole_pointer_values=sorted(WORDS),raw_city_values=list(range(256)),formula='8B1C+20*rawcity',normal_city_values=list(range(30)),real_pair_index_first_read=list(range(0,256,2)),real_pair_index_second_read=list(range(1,256,2)),no_ten_pair_or_FF_terminator=True,code_window_crossing=dict(raw_city=255,first_A000_Y=248,last_A007_Y=255,physical_bank=10),source_CPU_cases=0,limits=['Must-entry constructor and no-interrupt ordinary call contract; arbitrary middle entries, caller mutation and IRQ/NMI mutation are outside the proof.','Logical and dummy bus domains are separate. Both remain ROM for the admitted whole-word/raw-Y domain.','The two selected logical reads are disjoint from cityaux; this is not an all-C5D2-store or all-caller nonalias theorem.'])
 save('appearance-pointer-contract.json',constructor)
 for name,data in(('all-indirect-accesses.json',rows),('remaining-accesses.json',[r for r in rows if r['classification']!=DISJOINT]),('selected-accesses.json',[canonical[k]for k in sorted(TARGETS)])):
  save(name,dict(schema='phase25-one-appearance-pointer-contracts-v1',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,access_count=len(data),classification_counts=dict(Counter(r['classification']for r in data)),newly_proved_disjoint_count=sum(r['newly_proved_disjoint']for r in data),accesses=data))
 groups=json.loads((ROOT/'analysis/phase24/fields-static/unknown-producer-ranking.json').read_text())
 for g in groups['groups']:
  g['selected_for_new_context_contract']=g['group_id']=='G033'
  for r in g['accesses']:
   key=r['physical_bank'],r['cpu'];r['phase24_classification']=r['classification'];r['classification']=canonical[key]['classification'];r['newly_proved_disjoint']=canonical[key]['newly_proved_disjoint']
  g['newly_proved_disjoint_access_count']=sum(r['newly_proved_disjoint']for r in g['accesses']);g['remaining_unknown_access_count']=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in g['accesses'])
 groups.update(schema='phase25-unknown-producer-ranking-v1',selected_group='G033');save('unknown-producer-ranking.json',groups)
 dummy=[]
 for r in rows:
  proof=r['address_contract'];hits=old.old.old.dummy_auxiliary_intersection(proof,r['op'])if proof else None
  dummy.append(dict(physical_bank=r['physical_bank'],cpu=r['cpu'],logical_classification=r['classification'],operation=r['op'],dummy_auxiliary_bus_addresses=hits,dummy_auxiliary_intersection_count=len(hits)if hits is not None else None))
 save('logical-vs-dummy-bus-contracts.json',dict(access_count=1526,accesses=dummy))
 inputs=['scripts/analyze_unknown_pointer_phase24.py','analysis/phase24/fields-static/all-indirect-accesses.json','analysis/phase24/fields-static/unknown-producer-ranking.json','analysis/phase24/fields-static/verification.json']
 summary=dict(schema='phase25-one-appearance-pointer-summary-v1',status='analyzed',ROM_sha256=base.ROM_SHA256,analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),artifact_sha256={path:sha(ROOT/path)for path in inputs},source_CPU_cases=0,selected_group='G033',all_indirect_access_count=1526,all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),previous_candidate_count=341,remaining_access_count=sum(r['classification']!=DISJOINT for r in rows),newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint']for r in rows),new_disjoint_count=sum(r['newly_proved_disjoint']for r in rows),unknown_input_group_count=55,unknown_input_access_count=270,retained_original_ranking_scope=dict(source='phase23 unknown-producer groups retained by phase24 ranking',group_count=55,access_count=270,current_phase24_unknown_access_count=260,meaning='Historical group membership, not this phase25 input unknown count'),pre_phase25_unknown_access_count=260,remaining_unknown_access_count=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in rows),finite_refinement_rounds=e.refinement_rounds,complete_analysis_fixed_point_proven=False,official_target_field_names=dict(city_plus1=None,city_plus28=None,city_plus29=None,city_plus30=None,city_plus31=None),limits=constructor['limits'])
 save('analysis-summary.json',summary)
 (OUT/'README.md').write_text('''# G033完整指针与映射合同

仅将physical11 C61F/C624两处逻辑读从未知排除：本轮前unknown260→258；全1526条分类为1187不交、81可能、258未知，候选341→339。55组/270访问是第23阶段原unknown分组经第24阶段保留的历史成员，不是本轮前unknown总数。本轮只比较G107与G033并选择G033，不宣称重新恢复全部55组。

完整14条前序C5F8..C614包含真实D471乘法JSR，must-builder要求完整进入、同一前序所有边都通过；bypass join或裸高字节store不制造完整指针。19条D471用原bytes+全部rawcity×20原CPU合同核对。循环侧域保留所有Y byte；没有凭FF或10pair假设终止。所有256原city字节含30..255都保留，后者只是机器域，不称合法城市。

22/23=8B1C+20*rawcity。合法城市0..29即使所有Y0..255，逻辑读仍在银行17 ROM；raw255+Y248..255逻辑A000..A007由银行10代码窗提供，而同次IndY未进位dummy页为9F00..9F07、银行17。逻辑EA与dummy bus分别重算。该结论仅两条读，不替整个C5D2所有写排除城市辅助字段。

mapping-lifetime-contract.json从C5D2闭包252个原位置列完整callee/写入。入口真实LDY49/F266选择17，setter与指针高byte完成均支配两读；仅F269直接写PRG端口。中间typed city cap和officer status写不碰ZP/stack/mapper。C66C裸/raw无界append仍保留：它后面直接RTS而不再访问两表读，不能用此证明append安全。普通无中断、二进制算术、完整caller合同之外的任意裸输入/IRQ/NMI/外部内存写不被接纳。

verification.json中的33280个原CPU合同与Source差分另计：256个D471真实软件帧RTS、256个完整构造prefix、32768个偶/奇pair读取prefix。后两类不是完整C5D2返回，更不是Native帧。自然被动caller及实际映射见../cpu-appearance，Source helper与统一factory对照见../appearance及../source-integration.json。

城市+1/+28..31正式名称仍未知；ROM表读取并不赋予城市字段语义。零值、有限路径未写或裸alias不构成unused/padding/bug的结论。
''')
 print(json.dumps({k:summary[k]for k in('all_indirect_classification_counts','remaining_access_count','new_disjoint_count')},ensure_ascii=False))
if __name__=='__main__':main()
