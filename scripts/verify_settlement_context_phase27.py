#!/usr/bin/env python3
"""Verify new G106 context documents only; no CPU, Source or core execution."""
from pathlib import Path
import argparse, ast, hashlib, json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase27/context'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');a=p.parse_args();rom=Path(a.rom).read_bytes()
 summary=read('analysis-summary.json');assert hashlib.sha256(rom).hexdigest()==summary['ROM_sha256']
 checks=[]
 def check(name,condition):assert condition,name;checks.append(dict(test=name,status='passed'))
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for path,value in summary[group].items():check('current_pin:'+path,sha(ROOT/path)==value)
 chain=read('owner-and-caller-chain.json');pointer=read('pointer-and-field-context.json');credit=read('semantic-deduplication.json');budget=read('stable-denominators-and-acceptance.json');current=read('current27-owner-scope.json')
 for row in chain['original_positions']:
  off=16+8192*row['physical_bank']+(row['cpu']&8191);raw=bytes.fromhex(row['raw_hex'])
  assert off==row['rom_offset']and rom[off:off+len(raw)]==raw,(row['physical_bank'],row['cpu'])
 check('all_trusted_original_positions_plus16',True)
 for row in pointer['immutable_data_tables']:
  off=16+8192*row['physical_bank']+(row['cpu']&8191);raw=bytes.fromhex(row['raw_hex']);assert off==row['rom_offset']and rom[off:off+len(raw)]==raw
 check('immutable_rate_threshold_data_plus16',True)
 check('no_declared_exact_owner_in_frozen26_bounded_model',len(chain['owner_routes'])==7 and all(r['route']['owners']==[]and r['route']['status']=='no_declared_owner_in_bounded_route_model'for r in chain['owner_routes']))
 new=set(current['NEW_ENTRIES']);check('new27_exact_four_callees_only',new=={0xBF0A,0xBF9E,0xBFB3,0xBFEC}and all(r['route']['owners']==(['PostbattleResourceServices']if r['target']in new else[])for r in current['routes']))
 check('parent_not_closed_and_deployment_five_retained',current['parent_completion_claim']is False and current['parent_A006_BAB3_BB93_unowned_in_bounded_model']is True and len(current['frozen_deployment_owner_retained'])==5 and all(r['route']['owners']==['DeploymentPointerServices']for r in current['frozen_deployment_owner_retained']))
 check('A006_BAB3_dispatch_complete_bounded_table',chain['dispatcher']['targets']==[0xBAC1,0xBB3D,0xBB93,0xBBA0]and chain['dispatcher']['count']==4)
 edge={r['call_PC']:r for r in chain['local_calls']}
 check('actual_BB96_caller',edge[0xBB96]['callee']==0xBF0A and edge[0xBB96]['normal_return_PC']==0xBB99)
 check('four_BF9E_JSRs_and_one_tail_JMP',[(x,edge[x]['Y_at_complete_BF0A_call'])for x in(0xBF34,0xBF5E,0xBF69,0xBF8E)]==[(0xBF34,6),(0xBF5E,8),(0xBF69,14),(0xBF8E,2)]and edge[0xBF9B]['kind']=='tail_JMP'and edge[0xBF9B]['raw_return_word']is None)
 check('separate_byte11_entry_and_word_threshold_read_callers',edge[0xBF81]['callee']==0xBFB3 and edge[0xBF81]['Y_at_complete_BF0A_call']==11 and [edge[x]['Y_at_complete_BF0A_call']for x in(0xBF86,0xBF93)]==[2,4])
 copy=pointer['pointer_factory']['original_copy'];off=16+8192*copy['physical_bank']+(copy['cpu']&8191);raw=bytes.fromhex(copy['raw_hex']);check('F2AF_output_copied_to1A_1B_rawbytes',off==copy['rom_offset']and rom[off:off+len(raw)]==raw)
 check('F25F_not_F266_save_contract',pointer['mapper']['target']==0xF25F and pointer['mapper']['fixed_save_byte']==0xE1 and pointer['mapper']['raw_selector_decimal']==48 and pointer['mapper']['physical_data_bank']==16)
 aux={0x6000+32*i+o for i in range(30)for o in(1,28,29,30,31)}
 expected={0xBF74:[11],0xBFA0:[2,4,6,8,14],0xBFA6:[3,5,7,9,15],0xBFDF:[2,4,6,8,11,14],0xBFE9:[3,5,7,9,15],0xBFEC:[2,4],0xBFF2:[3,5]}
 for row in pointer['complete_caller_candidate_contracts']:
  assert row['candidate_only_not_new_static_authority']is True
  assert row['complete_caller_Y_values']==expected[row['cpu']]
  assert row['complete_caller_whole_pointer_values']==[0x6000+32*i for i in range(256)]
  intersection=sorted({(p+y)&65535 for p in row['complete_caller_whole_pointer_values']for y in row['complete_caller_Y_values']}&aux)
  assert intersection==row['calculated_logical_address_intersection']==[]
 check('seven_candidate_contracts_intersection_recomputed_and_non_authority',len(pointer['complete_caller_candidate_contracts'])==7)
 check('old512_SRAM_semantics_not_new_CPU_equivalence',credit['old_SRAM_effect_case_count']==512 and credit['old_finalization_case_count']==256 and credit['first_recovery_of_old_algorithm_claim']is False and 'ECEE' in credit['old_scope'])
 check('six_old_named_fields_not_target_aux_names',[r['city_offset']for r in pointer['semantics']]==[6,8,14,11,2,4]and all(v is None for v in budget['official_city_auxiliary_names'].values()))
 check('frozen1526_baseline_and_selected_seven_unchanged',budget['all_indirect_positions']==1526 and budget['frozen26_remaining']==335 and budget['frozen26_classification']=={'proved_disjoint_auxiliary_address_domain':1191,'possible_city_auxiliary_alias':81,'unresolved_pointer_or_index_contract':254}and len(budget['selected_prior_records'])==7 and all(r['classification']=='unresolved_pointer_or_index_contract'for r in budget['selected_prior_records']))
 check('raw345_partition_kept',budget['raw_window_ledger']==dict(total=345,operand=104,known_data=13,no_proven_control_entry=228))
 check('all_ten_statuses_are_explicit_frozen26_not_phase27_pass',len(budget['dimensions'])==10 and all(r['frozen26_status_is_not_phase27_summary']and r['new_phase27_acceptance_status']is None for r in budget['dimensions']))
 check('context_has_no_new_execution_or_coverage',all(summary[k]==0 for k in('Source_CPU_cases','original_CPU_cases','Native_runs','context_new_static_exclusions'))and summary['natural_capture_claim']is False and summary['unknown_unique_services']is None)
 for path in('scripts/analyze_settlement_context_phase27.py','scripts/verify_settlement_context_phase27.py'):
  tree=ast.parse((ROOT/path).read_text());imports=[n.module or''for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(tree)if isinstance(n,ast.Import)for a in n.names]
  assert not any(s.startswith(('py65','source.recovered','nes_runtime'))for s in imports)
  assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('eval','exec')for n in ast.walk(tree))
 check('no_CPU_recovered_Source_or_core_execution_in_context_scripts',True)
 sourcepins={**summary['source_and_validator_sha256'],'scripts/verify_settlement_context_phase27.py':sha(__file__)}
 artifacts={**summary['artifact_and_dependency_sha256'],**{str(p.relative_to(ROOT)):sha(p)for p in OUT.iterdir()if p.is_file()and p.name not in('verification.json','evidence.json')}}
 result=dict(schema='phase27-G106-context-validation-v1',status='passed',ROM_sha256=summary['ROM_sha256'],checks=checks,check_count=len(checks),Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256=artifacts,limits=['Finite AST/rawbyte/candidate contract audit, not dynamic reachability or whole-game closure.','New27 production/source/Native facts are independently owned, not pregranted here.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 evidence=dict(schema='phase27-G106-context-evidence-v1',status='passed',ROM_sha256=summary['ROM_sha256'],source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256={**artifacts,'analysis/phase27/context/verification.json':sha(OUT/'verification.json')},Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)
 (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='passed',checks=len(checks),Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)))
if __name__=='__main__':main()
