#!/usr/bin/env python3
"""Add only complete-CC29 name-pointer contracts to the frozen1526 ledger.

No Source/CPU/core or old producer executes here. The independent verifier
executes original6502 as a contract oracle, never a gameplay implementation.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase30/fields-static'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BASE_AUDIT='177c7d2d27dc3f5fd9840f90802be752befa3dd7ae885e867e9c110432f68a15'
DISJOINT='proved_disjoint_auxiliary_address_domain'
TARGETS=((13,0xCC92),(13,0xCCAC))
INPUTS=('analysis/phase29/verification.json','analysis/phase27/fields-static/verification.json','analysis/phase27/fields-static/all-indirect-accesses.json','analysis/phase27/fields-static/logical-vs-dummy-bus-contracts.json','analysis/phase23/fields-static/raw345-executability-ledger.json','analysis/phase18/control/instruction-atlas.json','analysis/phase29/context/CC29-name-draw-context.json','analysis/phase29/source-integration.json','analysis/game_data/name_glyph_records.csv')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def off(bank,pc):return 16+bank*8192+(pc&8191)
def normal(a):return a&2047 if a<8192 else a
AUX=frozenset(0x6000+32*c+f for c in range(30)for f in(1,28,29,30,31))
def save(n,d):OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def pointer_values(pc):
 return sorted({0x8DB4+13*leader+delta for leader in range(256)for delta in([0]if pc==0xCC92 else range(1,13))})
def address_contract(pc):
 words=pointer_values(pc)
 return dict(whole_pointer_values=words,whole_pointer_count=len(words),Y_values=[0],Y_was_unknown=False,low_high_relationship='Original completed multiply/add/increment word at each selected read; no independent low/high product or call-PC generation association.',possible_auxiliary_effective_addresses=[],auxiliary_address_intersection_count=0,logical_effective_address_count=len(words),logical_range_inclusive=[min(words),max(words)],required_execution_contract=dict(root_entry_PC=[0xCC29,0xD4F0],complete_current_CC29_lifecycle=True,actual_code_pair=[12,13],full_entry_F25F_selector=0x31,data_physical_bank=17,packed_ruler_nibbles_domain=list(range(7)),raw_leader_bytes=list(range(256)),binary_no_NMI_IRQ_execution=True,bare_CCAA_or_midinstruction_entry_covered=False),contract_scope='Conditional complete-entry logical effective address, not every caller to bareCCAA and not every6502 bus read.')
def admissible_context(d):
 return(d.get('root')in(0xCC29,0xD4F0)and tuple(d.get('pair',()))==(12,13)and d.get('complete_CC29')is True and d.get('F25F31_executed')is True and d.get('data_bank')==17 and all(v in range(7)for v in d.get('rulers',(-1,-1)))and len(d.get('rulers',()))==2 and d.get('interrupted')is False and d.get('binary')is True and not d.get('middle_entry',True))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 assert sha(ROOT/'analysis/phase29/verification.json')==BASE_AUDIT
 atlas=read('analysis/phase18/control/instruction-atlas.json')['instructions'];by={(r['physical_bank'],r['cpu']):r for r in atlas}
 ranges=((13,0xCC29,0xCCE6),(13,0xD4F0,0xD4FB),(31,0xEBE9,0xEC22),(31,0xF25F,0xF266),(31,0xF368,0xF379))
 raw=[]
 for r in sorted(atlas,key=lambda r:(r['physical_bank'],r['cpu'])):
  if any(r['physical_bank']==b and lo<=r['cpu']<hi for b,lo,hi in ranges):
   row={k:r[k]for k in('physical_bank','cpu','rom_offset','raw_hex','op','mode','operand')};o=off(row['physical_bank'],row['cpu']);bs=bytes.fromhex(row['raw_hex']);assert row['rom_offset']==o and rom[o:o+len(bs)]==bs;raw.append(row)
 exact={0xCC29:'A0 31',0xCC2B:'20 5F F2',0xCC54:'20 6D CC',0xCC67:'20 6D CC',0xCC6D:'20 68 F3',0xCC72:'B1 00',0xCC80:'20 E9 EB',0xCC92:'B1 06',0xCC95:'20 DF CC',0xCC9B:'20 AA CC',0xCCAA:'A0 00',0xCCAC:'B1 06',0xCCAE:'20 DF CC',0xCCA4:'C9 0C',0xCCDF:'E6 06',0xCCE3:'E6 07',0xD4F0:'20 29 CC'}
 for pc,bs in exact.items():assert by[13,pc]['raw_hex']==bs
 # Prove that code after the completed constructor changes06/07 only in
 # CCDF; variable stores are bounded OAM0200..0302, never pointer scratch.
 post=[r for r in raw if r['physical_bank']==13 and 0xCC90<=r['cpu']<0xCCE6];writes=[r for r in post if r['op']in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and r['mode']!='a']
 assert {r['operand']for r in post if r['op']=='JSR'}=={0xCCDF,0xCCAA}and not any(r['op']=='JMP'for r in post)
 direct=[];indexed=[]
 for r in writes:
  if r['mode']in('zp','ab'):
   assert r['operand']not in(6,7)or r['cpu']in(0xCCDF,0xCCE3);direct.append(r)
  else:
   assert r['mode']=='abx'and 0x200<=r['operand']<=0x203
   addresses=range(r['operand'],r['operand']+256);assert all(normal(v)not in(6,7)for v in addresses);indexed.append(dict(instruction=r,complete_effective_address_range=[min(addresses),max(addresses)]))
 names=rom[off(17,0x8DB4):off(17,0x8DB4)+237*13];ptrwords=[int.from_bytes(rom[off(31,0xF379)+2*i:off(31,0xF379)+2*i+2],'little')for i in range(16)]
 proof=dict(schema='phase30-complete-CC29-name-pointer-contract-v1',status='original_structure_proof_with_separate_CPU_receipt',ROM_sha256=ROM_SHA,root_entries=[0xCC29,0xD4F0],selected_targets=[dict(physical_bank=b,cpu=pc,raw_hex=by[b,pc]['raw_hex'],rom_offset=off(b,pc))for b,pc in TARGETS],original_instructions=raw,explicit_data=[dict(physical_bank=31,cpu=0xF379,rom_offset=off(31,0xF379),raw_hex=rom[off(31,0xF379):off(31,0xF379)+32].hex(' ').upper(),is_opcode=False,label='raw16 ruler words; only0..6 are proper ruler entries'),dict(physical_bank=13,cpu=0xD4F8,rom_offset=off(13,0xD4F8),raw_hex='06 A0',is_opcode=False,label='EE07 inline target')],normal_ruler_words=ptrwords[:7],raw16_ruler_words=ptrwords,normal_ruler_domain=list(range(7)),known237_name_table=dict(physical_bank=17,cpu=0x8DB4,rom_offset=off(17,0x8DB4),record_size=13,record_count=237,sha256=hashlib.sha256(names).hexdigest(),raw_leader_237_255_outside_known_names=True),lifecycle=['D4F0 first JSRCC29, or direct completeCC29 entry with actual caller frame.','CC29 LDY31/JSRF25F selects physical17 data. No later mapper call in this draw closure.','CC54/CC67 JSRCC6D passes high/low0507 ruler index; normal0..6 F368 points to6F07..6F37.','CC72 reads raw leaderbyte; operands00/01/02=[leader,0,0],03=13 to originalEBE9.','CC83..CC8E adds8DB4 with carry to complete06/07; product≤3315 and resultingword≤9AA7.','CC92 Y0 reads first byte. CCDF completes INC06 and conditionalINC07 before the next selected read.','CCAA resetsY0, CCAC reads nextbyte; original12-iteration counter and CCDF cover offsets1..12.','Stack/OAM operations do not write pointer06/07; no interrupt observes a transient partial increment in this contract.'],post_constructor_direct_writes=direct,post_constructor_complete_indexed_write_domains=indexed,caller_scope=dict(CC6D_JSR_callers=[0xCC54,0xCC67],CCAA_JSR_caller=0xCC9B,normal_execution_no_extra_middle_entry=True),factorization='Each packet constructor resets00..03 and originalmultiply resets04..09; packet writes affect OAM/7C/0A and stack, not rulerSRAM or the next leader input. Thus the pointer theorem factors by the current single leaderbyte, not exhaustive pairs of twoleader identities.',bare_counterexample_addresses=[0x6001,0x601C,0x601F],raw8_hardware_read_boundary=dict(ruler=8,ruler_pointer=ptrwords[8],read_PC=0xCC72,provided_hardware_value=False),new_semantic_first_recovery=False,source_CPU_cases=0,Native_frames=0,limits=['Conditional full-entry proof, not a universal reachability/unreachability claim.','Normal ruler0..6 premise; raw7..15 original table words and their hardware/alias behavior remain outside this theorem.','All256 raw leaderbytes retained; known237 names must not truncate the original arithmetic.','BareCCAA arbitrary06/07 still can read city+1 and tails; no authority from a prior dynamic invocation is reused.','Logical effective data addresses exclude addressing-mode dummy cycles; selected IndY Y0 requires no page-cross dummy read.','No NMI/IRQ interference or decimal-mode CPU proof; production Source and Native validations are separate.'])
 save('name-pointer-lifecycle-contract.json',proof)
 prior=read('analysis/phase27/fields-static/all-indirect-accesses.json')['accesses'];rows=[]
 for old in prior:
  row=dict(old);key=row['physical_bank'],row['cpu'];row.update(phase29_classification=old['classification'],newly_proved_disjoint=False)
  if key in TARGETS:
   c=address_contract(key[1]);assert not({normal((p+y)&65535)for p in c['whole_pointer_values']for y in c['Y_values']}&AUX)
   row.update(classification=DISJOINT,address_contract=c,whole_pointer_values=c['whole_pointer_values'],Y_values=c['Y_values'],newly_proved_disjoint=True,proof_basis='phase30_complete_CC29_name_constructor_and_original_bounded_increment_lifecycle',authoritative_contract_origin='analysis/phase30/fields-static/name-pointer-lifecycle-contract.json',authoritative_pointer_representation='complete_joint_address_set',candidate_contract_is_authoritative=False,candidate_address_contract=None,candidate_whole_pointer_values=None,candidate_Y_values=None)
  rows.append(row)
 for n,rs in(('all-indirect-accesses.json',rows),('remaining-accesses.json',[r for r in rows if r['classification']!=DISJOINT]),('selected-accesses.json',[r for r in rows if(r['physical_bank'],r['cpu'])in TARGETS])):
  save(n,dict(schema='phase30-conditional-name-pointer-access-ledger-v1',ROM_sha256=ROM_SHA,source_CPU_cases=0,access_count=len(rs),classification_counts=dict(Counter(r['classification']for r in rs)),newly_proved_disjoint_count=sum(r['newly_proved_disjoint']for r in rs),accesses=rs))
 dummy=read('analysis/phase27/fields-static/logical-vs-dummy-bus-contracts.json')
 for row in dummy['accesses']:
  if(row['physical_bank'],row['cpu'])in TARGETS:row.update(logical_classification=DISJOINT,conditional_dummy_auxiliary_bus_addresses=[],extra_dummy_read_required=False,scope='CompleteCC29 selected Y0 loads; IndY read has no additional page-cross read. Logical-domain theorem, not py65 dummy-cycle capture.')
 save('logical-vs-dummy-bus-contracts.json',dummy)
 save('raw345-executability-ledger.json',read('analysis/phase23/fields-static/raw345-executability-ledger.json'))
 save('analysis-summary.json',dict(schema='phase30-name-pointer-conditional-field-summary-v1',status='analyzed',independent_original_CPU_receipt_required=True,ROM_sha256=ROM_SHA,analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),source_CPU_cases=0,all_indirect_access_count=1526,all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),previous_candidate_count=328,remaining_access_count=sum(r['classification']!=DISJOINT for r in rows),remaining_unknown_access_count=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in rows),newly_proved_disjoint_all_count=2,complete_analysis_fixed_point_proven=False,raw345=dict(total=345,operand=104,known_data=13,no_control_entry=228),official_target_field_names=dict(city_plus1=None,city_plus28=None,city_plus29=None,city_plus30=None,city_plus31=None),source_and_validator_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},artifact_sha256={p:sha(ROOT/p)for p in INPUTS},limits=proof['limits']))
 (OUT/'original-ranges.asm').write_text('; New30 original name-pointer proof; offsets include16-byte header\n'+'\n'.join(f"; bank{r['physical_bank']} file${r['rom_offset']:06X}\n${r['cpu']:04X}: {r['raw_hex']:<12}; {r['op']} {r['mode']} ${r['operand']:04X}"for r in raw)+'\n')
 print(json.dumps(dict(status='analyzed',independent_CPU_receipt_required=True,all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),remaining=326,new_conditional_exclusions=2,source_CPU_cases=0)))
if __name__=='__main__':main()
