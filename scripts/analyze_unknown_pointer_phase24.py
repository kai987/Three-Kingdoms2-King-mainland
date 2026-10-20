#!/usr/bin/env python3
"""Phase24 additive unknown-group ranking and typed pointer-return contract.

One selected lifecycle is refined: bank28 D987 preserves an admitted complete
00/01 input word across scratch reuse. All older files stay read-only. Other
unknown groups are ranked, not silently cleared by a whole-program rerun.
"""
from collections import Counter, defaultdict, deque
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase24/fields-static'
SPEC=importlib.util.spec_from_file_location('frozen_phase23_pointer_model',ROOT/'scripts/analyze_city_auxiliary_phase23.py')
old=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=old;SPEC.loader.exec_module(old)
base=old.base
OLD_AUDIT='8e53b4e8c315d49a407c2f120d56fbd3280ed0043fdec36af93e332e70c90f38'
OLD_ZIP='7b141e38fdc88e6c601d10705b255bb48f04e1047cd0ab40ffa588490bf17e51'
ZIP_PATH='build/三国志2超级版-逆向分析-v23增量.zip'
DISJOINT=old.DISJOINT
TARGETS=frozenset((28,pc)for pc in(0xD850,0xD856,0xD859,0xD85D,0xD895,0xD89A,0xD89D,0xD8A1,0xD8B6,0xD8BC))
OFFICER_WORDS=frozenset(0x63C0+12*raw for raw in range(256))
INPUTS=list(dict.fromkeys(old.INPUTS+['scripts/analyze_city_auxiliary_phase23.py','analysis/phase23/verification.json',
 'analysis/phase23/fields-static/all-indirect-accesses.json','analysis/phase23/fields-static/shared-producer-caller-groups.json',
 'analysis/phase23/fields-static/analysis-summary.json','analysis/phase23/fields-static/verification.json',
 'analysis/phase23/fields-static/raw345-executability-ledger.json']))


def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def direct_addresses(row):
 mode,operand=row['mode'],row['operand']
 if mode in('zp','ab'):return frozenset((operand,))
 if mode in('zpx','zpy'):return frozenset((operand+i)&255 for i in range(256))
 if mode in('abx','aby'):return frozenset((operand+i)&65535 for i in range(256))
 return None


class Analysis(old.Analysis):
 def __init__(self,rom):
  super().__init__(rom);self.pointer_postcondition=self.prove_typed_pointer_return();self.pointer_return_applications={}

 def prove_typed_pointer_return(self):
  entry=(28,0xD987);structure=self.function_structure(entry)
  assert not structure['barriers']and structure['calls']=={(31,0xEA7C)}and structure['exits']==[(28,0xDA01)]
  nodes=structure['nodes'];assert len(nodes)==50
  math=self.function_structure((31,0xEA7C));assert not math['barriers']and not math['calls']and len(math['nodes'])==22 and math['exits']==[(31,0xEAA4)]
  assert all(self.known[k]['op']!='JSR' for k in math['nodes'])
  math_writes=[]
  for key in sorted(math['nodes']):
   row=self.known[key]
   if row['op']in base.WRITES and row['mode']!='a':
    values=direct_addresses(row);assert values is not None
    assert not values&{0x10,0x11}
    assert all(base.normalized_ram(a)is not None and base.normalized_ram(a)<256 for a in values)
    math_writes.extend(values)
  assert set(math_writes)=={1,2,5,6,7}
  prefix=bytes.fromhex('AD00008D1000AD01008D1100')
  restore=bytes.fromhex('AD10008D0000AD11008D0100')
  assert self.rom[base.original(28,0xD987):base.original(28,0xD993)]==prefix
  assert self.rom[base.original(28,0xD9E4):base.original(28,0xD9F0)]==restore
  # Complete original local CFG with callee return edges, not guessed linear
  # reachability: the four restore operations dominate the normal RTS.
  successor={}
  for key in nodes:
   row=self.known[key]
   if row['op']=='RTS':targets=[]
   elif row['op']=='JSR':targets=[base.mapped(key,row['cpu']+row['size'])]
   else:targets=self.edges.get(key,[])
   assert all(target in nodes for target in targets)
   successor[key]=targets
  predecessors={key:{p for p in nodes if key in successor[p]}for key in nodes}
  dom={key:{entry}if key==entry else set(nodes)for key in nodes}
  changed=True
  while changed:
   changed=False
   for key in sorted(nodes):
    if key==entry:continue
    assert predecessors[key]
    value={key}|set.intersection(*(dom[p]for p in predecessors[key]))
    if value!=dom[key]:dom[key]=value;changed=True
  restored={(28,pc)for pc in(0xD9E4,0xD9E7,0xD9EA,0xD9ED)}
  assert restored<=dom[28,0xDA01]
  writes=[]
  for key in sorted(nodes):
   row=self.known[key]
   if row['op']not in base.WRITES or row['mode']=='a':continue
   if row['mode']=='iy':
    assert key in((28,0xD9F8),(28,0xD9FF))and row['operand']==0
    offset=8 if key[1]==0xD9F8 else 9
    possible={(pointer+offset)&65535 for pointer in OFFICER_WORDS}
    assert not any(base.normalized_ram(address)is not None for address in possible)
    assert restored<=dom[key]
    writes.append(dict(instruction=self.raw(key),complete_effective_addresses=sorted(possible),input_typed_pointer_offset=offset,may_write_RAM_mirror=False))
   else:
    addresses=direct_addresses(row);assert addresses is not None
    if addresses&{0x10,0x11}:assert key in((28,0xD98A),(28,0xD990))
    if addresses&{0,1}:assert key in((28,0xD996),(28,0xD9E7),(28,0xD9ED))
    writes.append(dict(instruction=self.raw(key),complete_effective_addresses=sorted(addresses)))
  known_callers=[]
  for key,row in self.known.items():
   if row['op']=='JSR'and base.mapped(key,row['operand'])==entry:known_callers.append(self.raw(key))
  assert {(r['physical_bank'],r['cpu'])for r in known_callers}=={(28,0xD837),(28,0xD87E)}
  return dict(schema='phase24-original-typed-pointer-return-contract-v1',entry=self.raw(entry),normal_RTS=self.raw((28,0xDA01)),
    input_pair_base=0,input_whole_pointer_values=sorted(OFFICER_WORDS),output_pairs_equal_input=[0],saved_pair_base=0x10,
    save_instructions=[self.raw((28,pc))for pc in(0xD987,0xD98A,0xD98D,0xD990)],restore_instructions=[self.raw(k)for k in sorted(restored)],
    original_local_instructions=[self.raw(k)for k in sorted(nodes)],known_direct_callers=known_callers,
    helper=dict(entry=self.raw((31,0xEA7C)),original_instructions=[self.raw(k)for k in sorted(math['nodes'])],all_direct_written_RAM_bytes=sorted(set(math_writes)),no_indirect_stores=True,no_nested_calls=True,normal_RTS=self.raw((31,0xEAA4))),
    complete_original_write_inventory=writes,restore_dominates_normal_RTS=True,
    input_contract='Known complete00/01 word is a subset of63C0+12*rawID0..255. All raw IDs, including237..255, remain. No IRQ/NMI/external memory mutation during this ordinary call.',
    proof='D987 atomically copies00/01 into10/11. The00/01 pair is temporarily reused (byte01 explicitly overwritten; EA7C itself writes only01/02/05/06/07). No intermediate direct or callee store writes10/11. All normal-return paths restore00/01 before final stores. For the admitted pointer domain, final indirect+8/+9 stores cannot alias any RAM mirror, saved word, or hardware stack. Therefore normal output pair00 equals the actual input complete word.',
    rejected_domain='Unknown pairs, any domain including a nonadmitted raw address, arbitrary middle entry and bare wrapping/ZP/stack pointer values do not receive this contract. No universal arbitrary-pointer theorem.',
    logical_vs_dummy_scope='The proof concerns logical data stores and pointer state; existing separate IndY dummy bus domains remain explicit.')

 def apply_call(self,state,target,key,far=False):
  result=super().apply_call(state,target,key,far)
  pair=state.pairs.get(0)
  if target==(28,0xD987)and pair is not None and pair.addresses and pair.addresses<=OFFICER_WORDS:
   base.kill(result,{0,1})
   result.pairs[0]=base.Pair(pair.addresses,pair.origins|self.add_origin(key,'typed_complete_pointer_normal_return'))
   self.pointer_return_applications[key]=dict(call=self.raw(key),target=self.raw(target),input_whole_pointer_values=sorted(pair.addresses),restored_pair_base=0,
      scope='Actual complete input word preserved; no independent lo/hi Cartesian reconstruction or call-PC generation identity.')
  return result


def ranking(engine,groups):
 priorities={'G086':(0,'selected_G086_allocation_pointer_save_restore','D805 unconditionally resolves rosterID with F2D7, D987 saves/reuses/restores00/01, then the ten selected record8/9 accesses. Ordinary military Right/Left/commit can distinguish an officer-record lifecycle from a city pointer.'),
  'G107':(1,'already_named_source_static_arithmetic_gap','B1B0/B2AE/B312 deployment-coordinate pointer chain; natural invasion initialization discriminates ROM coordinate tables. Existing battle_setup_ai already contains named behavior; no duplicate Source is requested.'),
  'G033':(2,'already_named_source_multiplication_pointer_gap','C5D2/D471 builds8B1C+20*rawcity and C61F/C624 reads appearance data. Existing recruitment Source and phase22 natural appearing officer are available; arithmetic proof is a later candidate, not expanded in this run.')}
 ranked=[]
 for group in groups:
  g=dict(group);writes=sum(bytes.fromhex(r['raw_hex'])[0]==0x91 for r in g['accesses'])
  if g['group_id']in priorities:priority,category,why=priorities[g['group_id']]
  elif writes:priority,category,why=3,'unresolved_write_lifecycle','At least one real indirect store; prioritize actual producer and complete caller before assigning any auxiliary field meaning.'
  elif g['physical_bank']==31:priority,category,why=4,'generic_fixed_service_context','Generic fixed-bank helper has several callers/input contracts; a bare entry is not equivalent to a natural caller.'
  else:priority,category,why=5,'unresolved_read_lifecycle','Need a complete producer/mapping/caller chain; group size or a negative native observation alone cannot exclude aliases.'
  all_callers=[r for e in g['known_enclosing_procedures']for r in e['all_trusted_incoming_callers']]
  entry_keys={(e['entry']['physical_bank'],e['entry']['cpu'])for e in g['known_enclosing_procedures']}
  nodes=set()
  for entry in entry_keys:nodes|=engine.function_structure(entry)['nodes']
  definitions=[];mapper=[];barriers=[]
  pointer_bytes={g['pointer_zero_page'],(g['pointer_zero_page']+1)&255}
  for key in sorted(nodes):
   row=engine.known[key]
   if row['op']in base.WRITES and row['mode']!='a':
    addresses=direct_addresses(row)
    if addresses is not None:
     normalized={base.normalized_ram(a)for a in addresses};hit=sorted(pointer_bytes&normalized)
     if hit:definitions.append(dict(instruction=engine.raw(key),possibly_written_pointer_bytes=hit,kind='definite_singleton_physical_slot_write'if len(normalized)==1 else'possible_indexed_alias_write',complete_effective_address_count=len(addresses)))
    else:barriers.append(dict(instruction=engine.raw(key),kind='indirect_store_needs_its_own_input_pointer_domain'))
   if row['op']=='JSR':
    if row['operand']in(0xF25F,0xF266):mapper.append(dict(instruction=engine.raw(key),scope='Actual mapper setter in an enclosing known procedure; persistence to each access is NOT inferred from mere membership.'))
    target=base.mapped(key,row['operand']);effect=engine.effects.get(target)
    if effect and pointer_bytes&set(effect['zero_page_may_write']):barriers.append(dict(instruction=engine.raw(key),kind='callee_may_write_pointer_slot',target_physical_bank=target[0],target_cpu=target[1],possibly_written_pointer_bytes=sorted(pointer_bytes&set(effect['zero_page_may_write']))))
  g.update(priority=priority,priority_category=category,route_discrimination=why,indirect_write_access_count=writes,
   selected_for_new_context_contract=g['group_id']=='G086',selected_site_CPUs=[pc for bank,pc in sorted(TARGETS)]if g['group_id']=='G086'else[],
   trusted_enclosing_procedure_count=len(entry_keys),trusted_direct_or_bounded_caller_edge_count=len(all_callers),
   possible_pointer_slot_definitions=definitions,local_explicit_mapper_setters=mapper,pointer_lifetime_barriers=barriers,
   mapper_scope='Physical bank/CPU/file offsets are exact original decoder locations. Listed setters/callers are evidence, not an unstated active8000 data-bank assumption.',
   lifetime_scope='This is the full syntactic may-definition/clobber inventory of known enclosing procedure bodies, not a first-reaching-definition proof. Indexed aliases and indirect/callee barriers are kept, never converted to dedicated producers.')
  ranked.append(g)
 return sorted(ranked,key=lambda g:(g['priority'],-g['indirect_write_access_count'],g['physical_bank'],g['group_id']))


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom');args=parser.parse_args();rom=Path(args.rom).read_bytes()
 assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 assert base.digest(ROOT/'analysis/phase23/verification.json')==OLD_AUDIT and base.digest(ROOT/ZIP_PATH)==OLD_ZIP
 engine=Analysis(rom)
 for n in range(3):
  engine.prove_returns();engine.steps=0;engine.states={};engine.queue=deque();engine.scheduled=set();roots,fallback=engine.run()
  added=engine.refine_write_effects()if n<2 else None
  engine.refinement_rounds.append(dict(round=n+1,original_instruction_transfers=engine.steps,new_non_ZP_store_proofs=added,return_contract_count=len(engine.return_contracts)))
  if not added:break
 previous=base.read('analysis/phase23/fields-static/all-indirect-accesses.json')['accesses'];rows=[]
 for prior in previous:
  key=prior['physical_bank'],prior['cpu'];candidate=engine.contract(key)if key in TARGETS else None
  authority=candidate if key in TARGETS and candidate is not None else prior['address_contract'];inherited=authority is prior['address_contract']
  classification=DISJOINT if authority is not None and not old.old.auxiliary_intersection(authority)else'possible_city_auxiliary_alias'if authority else'unresolved_pointer_or_index_contract'
  row=dict(prior);row.update(classification=classification,address_contract=authority,phase23_classification=prior['classification'],newly_proved_disjoint=classification==DISJOINT and prior['classification']!=DISJOINT,
   authoritative_contract_origin=dict(path='analysis/phase23/fields-static/all-indirect-accesses.json',sha256=base.digest(ROOT/'analysis/phase23/fields-static/all-indirect-accesses.json'),physical_bank=key[0],cpu=key[1],contract_field='address_contract')if inherited and authority else None,
   phase23_authoritative_contract_origin=prior.get('authoritative_contract_origin'),proof_basis='frozen_phase23_authoritative_contract'if inherited else'phase24_typed_complete_pointer_normal_return',
   whole_pointer_values=sorted(old.old.projection_words(authority))if authority else None,Y_values=old.old.projection_Y(authority)if authority else prior['Y_values'],
   candidate_address_contract=candidate if inherited else prior['address_contract'],candidate_whole_pointer_values=sorted(old.old.projection_words(candidate if inherited else prior['address_contract']))if(candidate if inherited else prior['address_contract'])else None,
   candidate_Y_values=old.old.projection_Y(candidate if inherited else prior['address_contract'])if(candidate if inherited else prior['address_contract'])else None,candidate_contract_is_authoritative=False)
  row['authoritative_pointer_representation']='explicit_guarded_pointer_index_cases'if authority and'address_cases'in authority else'complete_joint_address_set'if authority and'whole_pointer_values'in authority else'inherited_independent_low_high_Cartesian_domain'if authority else None
  if not inherited:
   authority['typed_pointer_return_contract_path']='analysis/phase24/fields-static/typed-pointer-return-contract.json'
   authority['required_execution_contract']=dict(original_entry_physical_bank=28,original_entry_cpu=0xD805,normal_no_interrupt_execution=True,raw_roster_ID_bytes='all0..255 retained',pointer_producer='D805 F2AF city→raw roster byte→F2D7 officer domain; normal D987 preserves00/01 before these sites',arbitrary_bare_access_entry_covered=False)
  rows.append(row)
 unknown_groups=[g for g in base.read('analysis/phase23/fields-static/shared-producer-caller-groups.json')['groups']if g['unknown_producer']]
 ranked=ranking(engine,unknown_groups);assert len(ranked)==55 and sum(g['access_count']for g in ranked)==270
 canonical={(r['physical_bank'],r['cpu']):r for r in rows}
 for group in ranked:
  group['phase23_unknown_producer']=group['unknown_producer']
  group['accesses']=[dict(access,phase23_classification=access['classification'],classification=canonical[access['physical_bank'],access['cpu']]['classification'],newly_proved_disjoint=canonical[access['physical_bank'],access['cpu']]['newly_proved_disjoint'])for access in group['accesses']]
  group['newly_proved_disjoint_access_count']=sum(r['newly_proved_disjoint']for r in group['accesses'])
  group['remaining_unknown_access_count']=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in group['accesses'])
 save('unknown-producer-ranking.json',dict(schema='phase24-complete-unknown-group-ranking-v1',input_group_count=55,input_access_count=270,selected_group='G086',groups=ranked))
 save('typed-pointer-return-contract.json',engine.pointer_postcondition)
 save('typed-pointer-return-applications.json',dict(schema='phase24-conditional-whole-pointer-return-applications-v1',application_count=len(engine.pointer_return_applications),applications=[v for k,v in sorted(engine.pointer_return_applications.items())]))
 save('selected-lifecycle.json',dict(schema='phase24-G086-allocation-pointer-lifecycle-v1',group='G086',input_access_count=14,selected_access_count=10,selected_accesses=[r for r in rows if(r['physical_bank'],r['cpu'])in TARGETS],unselected_accesses=[r for r in rows if r['physical_bank']==28 and r['cpu']in(0xC853,0xC87B,0xC8BB,0xDC6F)],entry_original_instructions=[engine.raw(k)for k in sorted(engine.known)if k[0]==28 and 0xD805<=k[1]<=0xD8BC],scope='One selected lifecycle only. Four other G086 accesses belong to different caller/pointer lifetimes and remain unknown.'))
 for name,data in [('all-indirect-accesses.json',rows),('access-contracts.json',[r for r in rows if r['phase17_remaining_candidate']]),('new-indirect-accesses.json',[r for r in rows if not r['phase17_instruction_access']]),('phase23-remaining351-handling.json',[r for r in rows if r['phase23_classification']!=DISJOINT]),('unknown270-handling.json',[r for r in rows if r['phase23_classification']=='unresolved_pointer_or_index_contract']),('remaining-accesses.json',[r for r in rows if r['classification']!=DISJOINT])]:
  save(name,dict(schema='phase24-one-lifecycle-city-auxiliary-access-contracts-v1',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,access_count=len(data),classification_counts=dict(Counter(r['classification']for r in data)),newly_proved_disjoint_count=sum(r['newly_proved_disjoint']for r in data),accesses=data))
 raw=base.read('analysis/phase23/fields-static/raw345-executability-ledger.json');save('raw345-executability-ledger.json',raw)
 dummy=[]
 for row in rows:
  proof=row['address_contract'];hit=old.old.dummy_auxiliary_intersection(proof,row['op'])if proof else None
  dummy.append(dict(physical_bank=row['physical_bank'],cpu=row['cpu'],logical_classification=row['classification'],operation=row['op'],dummy_auxiliary_bus_addresses=hit,dummy_auxiliary_intersection_count=len(hit)if hit is not None else None))
 save('logical-vs-dummy-bus-contracts.json',dict(schema='phase24-logical-and-dummy-bus-domains-v1',access_count=1526,accesses=dummy))
 summary=dict(schema='phase24-one-typed-pointer-lifecycle-summary-v1',status='analyzed',ROM_sha256=base.ROM_SHA256,analyzer_path='scripts/analyze_unknown_pointer_phase24.py',analyzer_sha256=base.digest(__file__),
  artifact_sha256={p:base.digest(ROOT/p)for p in INPUTS},old_phase23_audit_sha256=OLD_AUDIT,old_v23_incremental_preserved_sha256=OLD_ZIP,source_CPU_cases=0,
  selected_group='G086',unknown_input_group_count=55,unknown_input_access_count=270,all_indirect_access_count=1526,previous_candidate_count=351,
  new_disjoint_count=sum(r['newly_proved_disjoint']for r in rows),newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint']for r in rows),remaining_access_count=sum(r['classification']!=DISJOINT for r in rows),all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),
  baseline_candidate_count=589,new_indirect_access_count=45,classification_counts=dict(Counter(r['classification']for r in rows if r['phase17_remaining_candidate'])),new_indirect_classification_counts=dict(Counter(r['classification']for r in rows if not r['phase17_instruction_access'])),remaining_unknown_access_count=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in rows),
  finite_refinement_rounds=engine.refinement_rounds,complete_analysis_fixed_point_proven=False,raw_window_count=345,raw_window_categories=raw['categories'],official_target_field_names=dict(city_plus1=None,city_plus28=None,city_plus29=None,city_plus30=None,city_plus31=None),
  limits=['Only the selected ten G086 allocation sites may acquire new authority; other unknown groups are ranked without new exclusions.',
   'Conditional complete input pointer/ordinary no-interrupt normal-return contract, not arbitrary bare/wrapping/stack aliases or a universal pointer-return theorem.',
   'All raw roster-ID bytes0..255 retained; classification is neither new dynamic coverage nor whole-ROM unreachability.',
   'Actual mapper evidence is not an assumed globally active data window. Logical effective addresses and dummy bus reads remain separate.',
   'No official city auxiliary field meaning, padding/reserved/unused claim from zeros or a finite nonobservation.'])
 save('analysis-summary.json',summary)
 print(json.dumps({k:summary[k]for k in('selected_group','all_indirect_classification_counts','remaining_access_count','new_disjoint_count')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
