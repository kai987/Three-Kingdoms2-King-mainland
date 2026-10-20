#!/usr/bin/env python3
"""Read-only validation of new28 parent/fade/credit documents, zero CPU/core."""
from pathlib import Path
import argparse, ast, hashlib, json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase28/context'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');a=p.parse_args();rom=Path(a.rom).read_bytes();s=read('analysis-summary.json');checks=[]
 def check(name,condition):assert condition,name;checks.append(dict(test=name,status='passed'))
 check('original_ROM_identity',hashlib.sha256(rom).hexdigest()==s['ROM_sha256'])
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for path,value in s[group].items():check('current_pin:'+path,(ROOT/path).is_file()and sha(ROOT/path)==value)
 parent=read('parent-chain-and-owner.json');fade=read('fade-request-and-progress.json');far=read('EE07-stack-and-mapper.json');credit=read('historical-credit-and-erratum.json');budget=read('stable-denominators-and-limits.json')
 for r in parent['original_positions']+[parent['inline_target_data'],parent['dispatch_table_data']]:
  o=16+r['physical_bank']*8192+(r['cpu']&8191);b=bytes.fromhex(r['raw_hex']);assert o==r['rom_offset']and rom[o:o+len(b)]==b
 check('all_original_instructions_and_explicit_data_plus16',True)
 check('data_not_decoded_as_opcode',parent['inline_target_data']['is_opcode']is False and parent['dispatch_table_data']['is_opcode']is False)
 routes={r['target']:r['route']for r in parent['frozen27_route_identities']}
 check('existing_ECEE_EC67_EE07_owners_not_new_missing_services',all(routes[x]['owners']==['IntegratedSceneInitialization']for x in(0xECEE,0xEC67,0xEE07)))
 check('frozen27_resource_owner_and_parent_scope',routes[0xBF0A]['owners']==['PostbattleResourceServices']and all(routes[x]['owners']==[]for x in(0xA006,0xBAB3,0xBB93,0xBBA0,0xC027)))
 check('fourstate_table_not_blanket_completion',[x['entry']for x in parent['substates']]==[0xBAC1,0xBB3D,0xBB93,0xBBA0]and all(parent['substates'][i]['phase28_completion_not_pregranted']for i in(0,1,3)))
 check('D4F5_scope_excludes_prior_CC29',parent['before_D4F5_uncovered_CC29']['call_PC']==0xD4F0 and parent['before_D4F5_uncovered_CC29']['target']==0xCC29)
 request=fade['ECEE'];check('ECEE_immediate_RT_S_no_wait_or_ports',request['normal_RTS']==0xED18 and request['has_polling_wait']is False and request['external_callees']==[]and request['PPU_APU_ports_written']==[])
 check('ECEE_exact_parameters_and_8A_not_reset',request['initial_values']=={'0087':1,'0088':0,'0089':4}and request['does_not_initialize_008A']and request['direct_write_addresses']==[0x87,0x88,0x89,0,1,2,3])
 check('NMI_battle_F90B_progress_and_busy_scope',fade['EC67']['battle_NMI_call_PC']==0xF90B and fade['EC67']['active_scenes']==[2,3,4,5,7,8]and 'nonbusy'in fade['EC67']['eligible_NMI_only'])
 check('actual_parent_wait_and_BBB8_negative_target',fade['sub3']['entry']==0xBBA0 and fade['sub3']['nonnegative_target']==0xBBB7 and fade['sub3']['negative_calls_BBB8_at']==0xBBA5 and fade['sub3']['does_not_call_BBAB'])
 check('EE07_actual_inline_and_stack_frame',far['caller']['inline_target']==0xA006 and far['caller']['normal_return_PC']==0xD4FA and far['callee_frame']['return_PC']==0xEE4D and far['callee_frame']['raw_return_word']==0xEE4C)
 check('EE07_only_code_pair_restore_not_E1',far['mapping']['saved_code_shadow']==0xE2 and far['mapping']['restore_call_PC']==0xEE4F and far['mapping']['not_restored_by_EE07']==[0xE1])
 check('old_effect_and_parent_bypass_scope_kept',credit['old_effects']['loss_SRAM_cases']==512 and credit['old_effects']['supply_return_SRAM_cases']==512 and credit['old_effects']['parent_semantic_cases']==256 and 'bypassed'in credit['old_effects']['scope']and credit['old_files_modified']is False)
 check('old_ECEE_256_not_entire1536_group_or_full2K',credit['old_ECEE_source']['old_complete_ECEE_cases_derived_from_frozen_validator']==256 and credit['old_ECEE_source']['RAM_compared_bytes']==1856 and credit['old_ECEE_source']['free_stack_residue_excluded']is True)
 check('C027_already_named_semantics_new_protocol_separate',credit['C027_credit']['already_named_semantics']and credit['C027_credit']['new_exact_protocol_is_separate_scope'])
 check('stable1526_1198_81_247_328',budget['all_indirect_positions']==1526 and budget['remaining_candidates']==328 and budget['frozen27_classification']=={'proved_disjoint_auxiliary_address_domain':1198,'possible_city_auxiliary_alias':81,'unresolved_pointer_or_index_contract':247})
 check('raw345_and_unknown_names_not_relabelled',budget['raw345']==dict(total=345,operand=104,known_data=13,no_proven_control_entry=228)and all(x is None for x in budget['official_city_auxiliary_names'].values())and budget['unknown_unique_services']is None)
 check('zero_new_execution_no_fourstate_completion',all(s[k]==0 for k in('Source_CPU_cases','original_CPU_cases','Native_runs'))and s['all_four_parent_states_complete_claim']is False and budget['context_new_exclusions']==0)
 for path in('scripts/analyze_postbattle_parent_context_phase28.py','scripts/verify_postbattle_parent_context_phase28.py'):
  tree=ast.parse((ROOT/path).read_text());imports=[n.module or''for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]+[x.name for n in ast.walk(tree)if isinstance(n,ast.Import)for x in n.names]
  assert not any(x.startswith(('py65','source.recovered','nes_runtime'))for x in imports)
  assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('eval','exec')for n in ast.walk(tree))
 check('context_scripts_do_not_execute_Source_CPU_core_or_oldproducer',True)
 sourcepins={**s['source_and_validator_sha256'],'scripts/verify_postbattle_parent_context_phase28.py':sha(__file__)}
 artifacts={**s['artifact_and_dependency_sha256'],**{str(p.relative_to(ROOT)):sha(p)for p in OUT.iterdir()if p.is_file()and p.name not in('verification.json','evidence.json')}}
 result=dict(schema='phase28-postbattle-parent-context-validation-v1',status='passed',ROM_sha256=s['ROM_sha256'],check_count=len(checks),checks=checks,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256=artifacts,limits=['Readonly originalbytes/AST/legacyreceipt audit. No newCPU/core run or producer rerun.','Minimum newly proposed Source phase2 is not blanket closure of state0/1/3, CC29, asyncfade or a wholebattle.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (OUT/'evidence.json').write_text(json.dumps(dict(schema='phase28-postbattle-parent-context-evidence-v1',status='passed',ROM_sha256=s['ROM_sha256'],source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256={**artifacts,'analysis/phase28/context/verification.json':sha(OUT/'verification.json')},Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='passed',checks=len(checks),Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)))
if __name__=='__main__':main()
