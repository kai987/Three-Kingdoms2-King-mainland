#!/usr/bin/env python3
"""Validate new29 readonly context. No CPU/core/Source or old producer run."""
from pathlib import Path
import argparse,ast,csv,hashlib,json

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase29/context'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def off(bank,pc):return 16+8192*bank+(pc&8191)
def normal(address):return(address&2047)if address<8192 else address
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');a=p.parse_args();rom=Path(a.rom).read_bytes()
 summary=read('analysis-summary.json');checks=[]
 def check(name,value):assert value,name;checks.append(dict(test=name,status='passed'))
 check('original_ROM_identity',hashlib.sha256(rom).hexdigest()==summary['ROM_sha256'])
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for path,value in summary[group].items():check('current_pin:'+path,sha(ROOT/path)==value)
 original=read('original-positions.json')
 for row in original['instructions']+original['data']:
  o=off(row['physical_bank'],row['cpu']);b=bytes.fromhex(row['raw_hex'])
  assert row['rom_offset']==o and rom[o:o+len(b)]==b,(row['physical_bank'],row['cpu'])
 check('all_original_instructions_and_explicit_data_plus16',True)
 by={(r['physical_bank'],r['cpu']):r for r in original['instructions']}
 check('inline_A006_is_data_not_an_opcode',next(x for x in original['data']if x['physical_bank']==13 and x['cpu']==0xD4F8)['is_opcode']is False)
 chain=read('completion-chain.json');data=read('ownership-and-roster-contract.json');draw=read('CC29-name-draw-context.json');fields=read('auxiliary-field-links.json');credit=read('historical-credit.json')
 check('BBA0_hold_returns_and_negative_calls_BBB8',chain['stage3']['hold']==dict(branch_pc=0xBBA3,target=0xBBB7,normal_RTS=True)and chain['stage3']['completion']==dict(call_pc=0xBBA5,target=0xBBB8,return_pc=0xBBA8))
 check('stage3_does_not_clear_or_increment_0501',chain['stage3']['does_not_increment_or_clear_0501']and all(x['address']not in(0x500,0x501)for x in chain['stage3']['post_cleanup_writes']))
 check('after_cleanup_global1_city13_phase0_only',chain['stage3']['post_cleanup_writes']==[dict(cpu=0xBBAA,address=0x7A,value=1),dict(cpu=0xBBAF,address=0x400,value=13),dict(cpu=0xBBB4,address=0x401,value=0)])
 # Check the actual frozen28 route, not the old25 generic reader's false negative.
 oldsource=(ROOT/'source/recovered/postbattle_parent_services.py').read_text();tree=ast.parse(oldsource)
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='PostbattleParentServices')
 newentries=next(ast.literal_eval(n.value)for n in cls.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='NEW_ENTRIES'for t in n.targets))
 check('frozen28_real_parent_PUBLIC_and_stage2_only',newentries==(0xA006,0xBAB3,0xBB93,0xC027)and chain['phase28_frozen_owner']['implemented_parent_stage']==2)
 check('BBA0_BBB8_BC00_not_declared_new_parent_entries',all(x not in newentries for x in(0xBBA0,0xBBB8,0xBC00))and 'if index==2:return(yield from self.settle_and_return_supplies())'in oldsource)
 route=(ROOT/'source/recovered/postbattle_parent_integration.py').read_text()
 check('concrete28_pair_route_not_generic_false_negative','pair == (8, 9) and call.target in PostbattleParentServices.NEW_ENTRIES'in route)
 check('original_owner_store_maskF0_notF8',data['ownership']['preserve_mask']==240 and data['ownership']['store_pc']==0xBBDD and by[8,0xBBD8]['operand']==240 and by[8,0xBBDD]['raw_hex']=='91 00')
 check('ownership_only_outcome0_and_citybyte0',data['ownership']['condition']=='0514==0'and data['ownership']['city_offset']==0 and by[8,0xBBC3]['operand']==0x514 and by[8,0xBBC6]['operand']==0x17)
 roster=data['roster']
 check('owner_low4_not_low3_neutral_exact7',roster['owner_mask']==15 and roster['only_skipped_owner']==7 and by[8,0xBC10]['operand']==15 and by[8,0xBC12]['operand']==7)
 check('ten_slot_scan_has_explicit_bound_not_FF',roster['scan_Y']==list(range(17,27))and roster['bounded_by']==dict(pc=0xBC2B,CPY=27)and by[8,0xBC2B]['operand']==27)
 check('roster_swaps_only_first17_and_found17to26',roster['stores']==[dict(pc=0xBC3C,Y=[17]),dict(pc=0xBC43,Y=list(range(17,27)))])
 adjacency=data['adjacency'];check('all30_original_adjacency_rows_have_FF',len(adjacency['rows'])==30 and all(255 in row['bytes']and all(v<30 for v in row['neighbors'])for row in adjacency['rows']))
 check('maximum7_neighbors_rawcity_overflow_not_pregranted',adjacency['longest_neighbors']==7 and adjacency['raw_city_at_least30_termination_not_claimed']and adjacency['byte_Y_wrap'])
 for row in adjacency['rows']:
  start=off(16,0x9D72)+row['city']*8;assert bytes(row['bytes'])==rom[start:start+8]
 check('adjacency_rows_bind_original_bank16_data',True)
 for ex in data['bare_suffix_counterexamples']:
  assert normal((ex['input_pointer']+ex['Y'])&65535)==ex['logical_address']and ex['city_offset']in(1,28)
 check('bare_BC00_address_counterexamples_not_fullentry_domain',len(data['bare_suffix_counterexamples'])==2)
 aux={0x6000+city*32+offset for city in range(30)for offset in(1,28,29,30,31)}
 for row in fields['cleanup_existing_authoritative_accesses']:
  c=row['address_contract'];addresses={normal((ptr+y)&65535)for ptr in c['whole_pointer_values']for y in c['Y_values']}
  assert not(addresses&aux)and c['auxiliary_address_intersection_count']==0,(row['physical_bank'],row['cpu'])
 check('all8_inherited_authoritative_cleanup_domains_recomputed_disjoint',len(fields['cleanup_existing_authoritative_accesses'])==8)
 frozen=json.loads((ROOT/'analysis/phase27/fields-static/remaining-accesses.json').read_text())['accesses']
 expected={(r['physical_bank'],r['cpu']):r for r in frozen};entries=fields['all_frozen_remaining_candidates']
 check('complete328_candidate_ledger_preserved',len(entries)==328 and len({(x['physical_bank'],x['cpu'])for x in entries})==328)
 for row in entries:
  prior=expected[row['physical_bank'],row['cpu']]
  assert all(row[k]==prior[k]for k in('rom_offset','raw_hex'))and row['frozen_classification']==prior['classification']and row['authority_unchanged']
 connected=[r for r in entries if r['connection']=='same_CC29_draw_closure']
 check('only_CC92_CCAC_directly_connected_remaining',[(r['physical_bank'],r['cpu'])for r in connected]==[(13,0xCC92),(13,0xCCAC)])
 check('new_authority_exclusions_and_official_city_names_zero',fields['new_authoritative_exclusions']==fields['newly_named_city_fields']==0 and all(v is None for v in fields['official_names'].values()))
 pointer=draw['typed_lifecycle']
 check('draw_fullentry_maps_bank17_only_F25F_external',pointer['data_selector']==0x31 and pointer['data_physical_bank']==17 and draw['frozen_precise_Source']['external_in_draw_closure']==[dict(call_pc=0xCC2B,target=0xF25F)])
 check('CC29_names_not_city_records',pointer['record_pointer']=='8DB4+13*leader'and pointer['known_name_records']==237 and pointer['name_record_size']==13)
 # Finite arithmetic/address audit only. This does not execute EBE9 or Source.
 domain={0x8DB4+13*i+j for i in range(256)for j in range(13)}
 check('typed_name_address_union_in_ROM_not_aux',min(domain)==0x8DB4 and max(domain)==0x9AB3 and not(domain&aux))
 check('typed_name_projection_matches_recorded_scope',pointer['logical_address_range_inclusive']==[min(domain),max(domain)]and pointer['normal237_name_range_inclusive']==[0x8DB4,0x99BC])
 with(ROOT/'analysis/game_data/name_glyph_records.csv').open()as f:names=list(csv.DictReader(f))
 table=rom[off(17,0x8DB4):off(17,0x8DB4)+237*13]
 assert len(names)==237
 for row in names:
  i=int(row['id']);assert bytes.fromhex(row['raw_hex'])==table[i*13:(i+1)*13]and int(row['rom_offset'],16)==off(17,0x8DB4+i*13)
 check('all237_existing_name_records_exact_original_bytes',hashlib.sha256(table).hexdigest()==pointer['name_table_sha256'])
 ex=draw['bare_suffix_counterexample'];check('bare_CCAA_still_can_read_auxiliary',ex['input_pointer_06_07']+ex['Y']==0x6001 and ex['read_pc']==0xCCAC)
 check('CC29_candidate_sites_still_unresolved',all(r['frozen_classification']=='unresolved_pointer_or_index_contract'for r in draw['candidate_only_sites']))
 old=json.loads((ROOT/'analysis/battle_fsm/validation.json').read_text())
 check('old_finalize512_and_parent256_not_recredited',credit['old_finalize_city_ownership_cases']==old['semantic_counts']['finalize_city_ownership']==512 and credit['old_parent_cases']==old['semantic_counts']['finalization_phase']==256 and credit['old_parent_ECEE_explicitly_bypassed']and 'bypassed'in old['scope'])
 check('frozen_owner_writer_already_present_phase6',credit['old_owner_writer']['CPU_store']==0xBBDD and credit['old_owner_writer']['preserve_mask']==240 and credit['old_owner_writer']['source_service']=='battle_state_machine.finalize_city_ownership')
 check('stable1526_classifications_328_and_raw345',summary['all_indirect_positions']==1526 and summary['remaining_candidates']==328 and summary['frozen_classification_counts']=={'proved_disjoint_auxiliary_address_domain':1198,'possible_city_auxiliary_alias':81,'unresolved_pointer_or_index_contract':247}and summary['raw345']==dict(total=345,operand=104,known_data=13,no_proven_control_entry=228))
 check('context_not_execution_or_fullclosure',all(summary[k]==0 for k in('Source_CPU_cases','original_CPU_cases','Native_runs','context_new_exclusions'))and summary['all_four_parent_states_complete']is False and summary['unknown_unique_services']is None)
 for path in('scripts/analyze_postbattle_completion_context_phase29.py','scripts/verify_postbattle_completion_context_phase29.py'):
  tree=ast.parse((ROOT/path).read_text());imports=[n.module or''for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]+[v.name for n in ast.walk(tree)if isinstance(n,ast.Import)for v in n.names]
  assert not any(x.startswith(('py65','source.recovered','nes_runtime','subprocess','importlib'))for x in imports)
  assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('eval','exec')for n in ast.walk(tree))
 check('readonly_scripts_no_game_CPU_core_or_old_producer_execution',True)
 sources={**summary['source_and_validator_sha256'],'scripts/verify_postbattle_completion_context_phase29.py':sha(__file__)}
 artifacts={**summary['artifact_and_dependency_sha256'],**{str(p.relative_to(ROOT)):sha(p)for p in OUT.iterdir()if p.is_file()and p.name not in('verification.json','evidence.json')}}
 result=dict(schema='phase29-postbattle-completion-context-validation-v1',status='passed',ROM_sha256=summary['ROM_sha256'],check_count=len(checks),checks=checks,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,new_exclusions=0,source_and_validator_sha256=sources,artifact_and_dependency_sha256=artifacts,limits=['Readonly originalbytes/AST/receipt and address-formula audit; no CPU/core/Source or old producer execution.','The fullCC29 name-pointer proposal is not a new authoritative1526 exclusion; bare suffix inputs remain unconstrained.','No wholeparent or wholebattle closure and no official city auxiliary field meaning.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (OUT/'evidence.json').write_text(json.dumps(dict(schema='phase29-postbattle-completion-context-evidence-v1',status='passed',ROM_sha256=summary['ROM_sha256'],source_and_validator_sha256=sources,artifact_and_dependency_sha256={**artifacts,'analysis/phase29/context/verification.json':sha(OUT/'verification.json')},Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,new_exclusions=0),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='passed',checks=len(checks),Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,new_exclusions=0)))
if __name__=='__main__':main()
