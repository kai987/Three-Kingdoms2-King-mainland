#!/usr/bin/env python3
"""G106 typed resource-copy and saved-index lifetime, additive phase27 only."""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase27/fields-static'
spec=importlib.util.spec_from_file_location('frozen26_pointer_model',ROOT/'scripts/analyze_unknown_pointer_phase26.py');old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
base=old.base;DISJOINT=old.DISJOINT;TARGETS=frozenset((8,pc)for pc in(0xBF74,0xBFA0,0xBFA6,0xBFDF,0xBFE9,0xBFEC,0xBFF2));CITY_WORDS=frozenset(0x6000+32*i for i in range(256))
HELPERS=frozenset(((8,0xBF9E),(8,0xBFB3),(8,0xBFEC)))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def typed(pair):return pair is not None and pair.addresses and pair.addresses<=CITY_WORDS
class Analysis(old.Analysis):
 def __init__(self,rom):
  super().__init__(rom)
  assert rom[base.original(8,0xBF1B):base.original(8,0xBF27)]==bytes.fromhex('AD00008D1A00AD01008D1B00')
  ident=max(self.factory_ids)+1;self.resource_copy=dict(id=ident,entry=(8,0xBF1B),marker=(8,0xBF24),base=0x1A,kind='typed_complete_city_word_copy',addresses=CITY_WORDS,prologue=frozenset((8,pc)for pc in(0xBF1B,0xBF1E,0xBF21,0xBF24)))
  self.factory_ids[ident]=self.resource_copy
 def transfer(self,key,state):
  result=super().transfer(key,state);d=self.resource_copy
  if key==d['entry']and typed(state.pairs.get(0)):result.builders|=frozenset((d['id'],))
  if key==d['marker']and d['id']in state.builders and typed(state.pairs.get(0)):
   base.atomic_pair(result,0x1A,base.Pair(state.pairs[0].addresses,state.pairs[0].origins|self.add_origin(d['entry'],'typed_complete_city_word_copy')))
   result.registers=(frozenset(((0x1A,1),)),)+result.registers[1:];result.builders-=frozenset((d['id'],))
  return result
 def apply_call(self,state,target,key,far=False):
  result=super().apply_call(state,target,key,far)
  if target in HELPERS and typed(state.pairs.get(0x1A)):
   pair=state.pairs[0x1A];result.pairs[0x1A]=base.Pair(pair.addresses,pair.origins|self.add_origin(key,'typed_resource_pointer_normal_return'))
   y=state.numbers[2]
   if y is not None:
    values=frozenset((v+1)&255 if target==(8,0xBFEC)or v!=11 else 11 for v in y)
    result.numbers=(result.numbers[0],state.numbers[1]if target!=(8,0xBFEC)else result.numbers[1],values)
   result.registers=(result.registers[0],result.registers[1],frozenset())
  return result
def prove_helpers(e):
 nodes=set();queue=[(8,0xBF0A)];functions=[];seen=set()
 while queue:
  entry=queue.pop()
  if entry in seen:continue
  seen.add(entry);f=e.function_structure(entry);assert not f['barriers'];nodes|=f['nodes'];queue.extend(f['calls']);functions.append(dict(entry=e.raw(entry),original_instruction_count=len(f['nodes']),calls=[e.raw(k)for k in sorted(f['calls'])],RTS=[e.raw(k)for k in f['exits']]))
 expected={(8,0xBF0A),(8,0xBF9E),(8,0xBFB3),(8,0xBFEC),(31,0xF25F),(31,0xF2AF),(31,0xE87A),(31,0xEBE9),(31,0xEA7C)};assert seen==expected
 helpers=[]
 for entry in sorted(HELPERS):
  f=e.function_structure(entry);writes=[]
  for key in sorted(f['nodes']):
   row=e.known[key]
   if row['op']not in base.WRITES or row['mode']=='a':continue
   if row['mode']=='iy':
    assert row['operand']==0x1A and key in((8,0xBFDF),(8,0xBFE9));domain={(p+y)&65535 for p in CITY_WORDS for y in range(256)}
    assert all(base.normalized_ram(a)is None for a in domain);writes.append(dict(instruction=e.raw(key),typed_input='6000+32*allrawcity0..255',Y_domain=list(range(256)),non_RAM_mirror_addresses=True,possible_mapper_addresses=sorted(a for a in domain if a>=0x8000)))
   else:
    addresses=old.old.old.direct_addresses(row);assert addresses is not None and not addresses&{0x1A,0x1B};writes.append(dict(instruction=e.raw(key),complete_effective_addresses=sorted(addresses)))
  for callee in f['calls']:
   assert callee in((31,0xEBE9),(31,0xEA7C));cf=e.function_structure(callee);assert not cf['calls']and not cf['barriers']
   for key in cf['nodes']:
    row=e.known[key]
    if row['op']in base.WRITES and row['mode']!='a':
     assert row['mode']not in('ix','iy');addresses=old.old.old.direct_addresses(row);assert addresses is not None and all(base.normalized_ram(a)is not None and base.normalized_ram(a)<0x1A for a in addresses)
  helpers.append(dict(entry=e.raw(entry),normal_returns=[e.raw(k)for k in f['exits']],complete_write_inventory=writes,typed_pointer1A_preserved=True,raw_input_Y=list(range(256)),output_Y='(inputY+1)&255'if entry==(8,0xBFEC)else'inputY==11 ?11:(inputY+1)&255',no_interrupt_normal_return_only=True,bare_or_non_city_pointer_domain_covered=False))
 # SavedY has its own original PHA/PLA across the two fixed arithmetic
 # routines; neither routine pushes, pops or stores to stack memory.
 for entry in((31,0xEBE9),(31,0xEA7C)):
  f=e.function_structure(entry);assert all(e.known[k]['op']not in('PHA','PLA','PHP','PLP','TXS','LDX','TAX','TSX','INX','DEX')for k in f['nodes'])
 assert e.known[8,0xBF9B]['op']=='JMP'and e.known[8,0xBF9B]['operand']==0xBF9E
 code=sorted(k for k in nodes if k[0]in(8,9));assert len(code)==118
 return dict(schema='phase27-G106-resource-pointer-and-index-lifetime-v1',functions=functions,resource_code_instruction_positions=118,resource_code_bytes=267,original_code=[e.raw(k)for k in code],typed_helper_return_contracts=helpers,copy_entry=e.raw((8,0xBF1B)),copy_complete_after=e.raw((8,0xBF24)),input_pair0=CITY_WORDS and sorted(CITY_WORDS),output_pair1A_equals_current_complete_pair0=True,actual_JSR_callers_to_BF9E=[e.raw((8,pc))for pc in(0xBF34,0xBF5E,0xBF69,0xBF8E)],tail_caller_to_BF9E=e.raw((8,0xBF9B)),tail_adds_new_caller_frame=False,
  existing_semantics_path='source/recovered/battle_state_machine.py:postbattle_city_losses',new_semantic_first_recovery=False,
  limits=['Whole typed pointercopy plus normal binary no-interrupt return. Bare helper pointers outside6000+32*rawbyte are not preserved by this contract.','Raw helperY permits6000..80DF including mapper addresses; this is a pointer/address invariant, not successful hardware-side execution or a menu eligibility theorem.','A006/BAB3 exact parent and its ECEE barrier remain separate missing owners.'])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 e=Analysis(rom);proof=prove_helpers(e);save('resource-pointer-lifetime-contract.json',proof)
 for n in range(3):
  e.prove_returns();e.steps=0;e.states={};e.queue=deque();e.scheduled=set();roots,fallback=e.run();added=e.refine_write_effects()if n<2 else None
  e.refinement_rounds.append(dict(round=n+1,original_instruction_transfers=e.steps,new_non_ZP_store_proofs=added,return_contract_count=len(e.return_contracts)))
  if not added:break
 previous_path=ROOT/'analysis/phase26/fields-static/all-indirect-accesses.json';prior=json.loads(previous_path.read_text())['accesses'];rows=[]
 for oldrow in prior:
  key=oldrow['physical_bank'],oldrow['cpu'];authority=e.contract(key)if key in TARGETS else oldrow['address_contract'];row=dict(oldrow);row.update(phase26_classification=oldrow['classification'],newly_proved_disjoint=False)
  if key in TARGETS and authority is not None:
   hit=old.old.old.old.old.auxiliary_intersection(authority)
   authority['required_execution_contract']=dict(complete_BF0A_pointer_producer=True,original_outcome_zero_path=True,binary_no_interrupt_normal_execution=True,pointer1A_current_city_copy=True,bare_helper_entry_covered=False,rawcity0_255_retained=True)
   row.update(classification=DISJOINT if not hit else'possible_city_auxiliary_alias',address_contract=authority,whole_pointer_values=sorted(old.old.old.old.old.projection_words(authority)),Y_values=authority['Y_values'],newly_proved_disjoint=not hit and oldrow['classification']!=DISJOINT,proof_basis='phase27_typed_city_pointer_copy_saved_Y_and_real_helper_returns',authoritative_contract_origin=None,candidate_contract_is_authoritative=False,authoritative_pointer_representation='complete_joint_address_set')
  rows.append(row)
 for name,data in(('all-indirect-accesses.json',rows),('remaining-accesses.json',[r for r in rows if r['classification']!=DISJOINT]),('selected-accesses.json',[r for r in rows if(r['physical_bank'],r['cpu'])in TARGETS])):
  save(name,dict(schema='phase27-one-G106-resource-contracts-v1',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,access_count=len(data),classification_counts=dict(Counter(r['classification']for r in data)),newly_proved_disjoint_count=sum(r['newly_proved_disjoint']for r in data),accesses=data))
 dummy=[]
 for r in rows:
  p=r['address_contract'];hits=old.old.old.old.old.dummy_auxiliary_intersection(p,r['op'])if p else None
  dummy.append(dict(physical_bank=r['physical_bank'],cpu=r['cpu'],operation=r['op'],logical_classification=r['classification'],conditional_dummy_auxiliary_bus_addresses=hits,scope='IndY reads extra only on crossing; STA has a separate unconditional uncorrected-page read. Domain theorem, not py65-observed bus cycles.'))
 save('logical-vs-dummy-bus-contracts.json',dict(access_count=1526,accesses=dummy))
 inputs=['scripts/analyze_unknown_pointer_phase26.py','analysis/phase26/fields-static/all-indirect-accesses.json','analysis/phase26/fields-static/verification.json','source/recovered/battle_state_machine.py']
 summary=dict(schema='phase27-G106-resource-pointer-summary-v1',status='analyzed',ROM_sha256=base.ROM_SHA256,analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),artifact_sha256={p:sha(ROOT/p)for p in inputs},source_CPU_cases=0,selected_group='G106',all_indirect_access_count=1526,all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),previous_candidate_count=335,remaining_access_count=sum(r['classification']!=DISJOINT for r in rows),pre_phase27_unknown_access_count=254,remaining_unknown_access_count=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in rows),newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint']for r in rows),finite_refinement_rounds=e.refinement_rounds,complete_analysis_fixed_point_proven=False,official_target_field_names=dict(city_plus1=None,city_plus28=None,city_plus29=None,city_plus30=None,city_plus31=None),limits=proof['limits'])
 save('analysis-summary.json',summary);print(json.dumps({k:summary[k]for k in('all_indirect_classification_counts','remaining_access_count','newly_proved_disjoint_all_count')},ensure_ascii=False))
if __name__=='__main__':main()
