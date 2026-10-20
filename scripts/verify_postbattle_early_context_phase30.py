#!/usr/bin/env python3
"""Check new30 readonly context; zero CPU/core/Source/gameplay execution."""
from pathlib import Path
import argparse,ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase30/context'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();s=read('analysis-summary.json');checks=[]
 def check(name,value):assert value,name;checks.append(dict(test=name,status='passed'))
 check('original_ROM_identity',hashlib.sha256(rom).hexdigest()==s['ROM_sha256'])
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for path,value in s[group].items():check('current_pin:'+path,sha(ROOT/path)==value)
 original=read('original-positions.json');by={(r['physical_bank'],r['cpu']):r for r in original['instructions']}
 for r in original['instructions']+original['data']:
  offset=16+8192*r['physical_bank']+(r['cpu']&8191);bs=bytes.fromhex(r['raw_hex']);assert offset==r['rom_offset']and rom[offset:offset+len(bs)]==bs
 check('all_original_instruction_and_data_bytes_plus16',True)
 branches=read('early-stage-branches-and-callers.json');stages=branches['stages'];erratum=read('historical-credit-and-return-erratum.json');name=read('ruler-and-name-pointer-boundaries.json')
 check('stage0_real_call_BB36_rawreturnBB38_resumeBB39',stages[0]['callee']==dict(call_pc=0xBB36,target=0xBC46,raw_return_word=0xBB38,return_pc=0xBB39)and by[8,0xBB36]['raw_hex']=='20 46 BC')
 check('stage1_real_call_BB8C_rawreturnBB8E_resumeBB8F',stages[1]['callee']==dict(call_pc=0xBB8C,target=0xBC46,raw_return_word=0xBB8E,return_pc=0xBB8F)and by[8,0xBB8C]['raw_hex']=='20 46 BC')
 check('normal_return_increment_only_after_truecallee_return',by[8,0xBB39]['operand']==by[8,0xBB8F]['operand']==0x501 and stages[0]['normal_RTS']==0xBB3C and stages[1]['normal_RTS']==0xBB92)
 check('stage0_highruler_human_outcome_routes13or14',stages[0]['ruler']=='0507 high nibble'and stages[0]['human_branches']==[dict(outcome='nonzero',state=13,phase=0,field050B=17,RTS=0xBB0E),dict(outcome='zero',state=14,phase=0,field050B=17,RTS=0xBB1E)])
 check('stage1_lowruler_human_outcome_routes13or14',stages[1]['ruler']=='0507 low nibble'and stages[1]['human_branches']==[dict(outcome='zero',state=13,phase=0,field050B=2,RTS=0xBB64),dict(outcome='nonzero',state=14,phase=0,field050B=2,RTS=0xBB74)])
 check('controller_field3_and_AIcode3',all(x['controller_field_offset']==x['AI_controller_value']==3 for x in stages)and by[8,0xBAEF]['raw_hex']==by[8,0xBB47]['raw_hex']=='B1 00')
 check('AI_side_and_mode_domains_differ_by_stage',[x['AI_side0504']for x in stages]==[128,0]and stages[0]['AI_mode6F91']==[dict(outcome='nonzero',mode=2),dict(outcome='zero',mode=0)]and stages[1]['AI_mode6F91']==[dict(outcome='zero',mode=1),dict(outcome='nonzero',mode=0)])
 check('original_redundant_LDA0A_then0D_is_not_new_branch',branches['redundant_original_load']==dict(cpu=0xBAFD,value=10,immediately_overwritten_at=0xBAFF,value_after=13,do_not_invent_branch=True)and by[8,0xBAFD]['raw_hex']=='A9 0A'and by[8,0xBAFF]['raw_hex']=='A9 0D')
 check('stage0_shadow_five_codepairs8_9',branches['stage0_fixed_shadow_initialization']==dict(low_addresses=[0xB2,0xC2,0xCA,0xD2,0xDA],low_value=8,high_addresses=[0xB3,0xC3,0xCB,0xD3,0xDB],high_value=9))
 check('old_BB37_BB8D_markers_superseded_only_new_context',[(x['semantic_code_marker'],x['actual_JSR_PC'],x['actual_return_PC'])for x in erratum['old_dependency_markers']]==[(0xBB37,0xBB36,0xBB39),(0xBB8D,0xBB8C,0xBB8F)])
 legacy=(ROOT/'source/recovered/battle_state_machine.py').read_text()
 check('frozen_old_semantic_marker_not_rewritten',"0xBB37 if stage==0 else 0xBB8D"in legacy)
 check('old_AIthree_modes512_not_first_recovery',erratum['old_AI_modes']=={'ai_mode0':512,'ai_mode1':512,'ai_mode2':512}and erratum['new_precise_protocol_not_first_algorithm_recovery'])
 check('old_parent256_bypass_separate',erratum['old_parent_semantic_cases']==256 and erratum['old_parent_ECEE_bypassed'])
 check('seven_normal_ruler_words_original',name['normal_table_words']==[0x6F07+8*i for i in range(7)]and len(name['raw16_table_words'])==16)
 check('raw8_needs5F20_input_not_fake',name['raw16_table_words'][8]==0x5F20 and all(x['read_performed_by_context']is False for x in name['raw_boundaries']))
 check('raw11_live_scratch_raw14_stack_raw15_RAMmirror',name['raw16_table_words'][11]==1 and name['raw16_table_words'][14]==0x12E and name['raw16_table_words'][15]==0x1800)
 check('CC6D_real_JSRs_CC54_CC67',name['CC6D_exact_JSR_callers']==[dict(physical_bank=13,cpu=0xCC54,target=0xCC6D,return_pc=0xCC57),dict(physical_bank=13,cpu=0xCC67,target=0xCC6D,return_pc=0xCC6A)])
 check('D4F0_draw_precedes_D4F5_farcall',name['D4F0_chain']==dict(draw_call_pc=0xD4F0,draw_entry=0xCC29,draw_return=0xD4F3,selector=0x28,farcall_pc=0xD4F5,inline_target=0xA006))
 check('typed_name_proposal_not_context_authority',name['typed_name_proposal']['context_promotes_no_authority']and name['typed_name_proposal']['normal_leader_domain']==list(range(256))and name['typed_name_proposal']['raw237_255_not_official_names'])
 check('bare_CCAA_aux_plus1_counterexample_retained',name['bare_CCAA']['pointer06']==name['bare_CCAA']['logical_address']==0x6001 and name['bare_CCAA']['Y']==0)
 check('frozen29_baseline_328_and_raw345_unchanged',s['frozen29_baseline']==dict(all_indirect=1526,conditional_disjoint=1198,possible=81,unknown=247,remaining=328,raw345=dict(operand=104,known_data=13,no_control_entry=228)))
 check('no_new_context_execution_or_names_or_wholeclosure',all(s[k]==0 for k in('Source_CPU_cases','original_CPU_cases','Native_runs','context_new_exclusions'))and all(x is None for x in s['official_city_auxiliary_names'].values())and s['unknown_unique_services']is None and s['full_game_closure']is False)
 for path in('scripts/analyze_postbattle_early_context_phase30.py','scripts/verify_postbattle_early_context_phase30.py'):
  t=ast.parse((ROOT/path).read_text());imports=[n.module or''for n in ast.walk(t)if isinstance(n,ast.ImportFrom)]+[v.name for n in ast.walk(t)if isinstance(n,ast.Import)for v in n.names]
  assert not any(x.startswith(('py65','source.recovered','nes_runtime','subprocess','importlib'))for x in imports)
  assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('exec','eval')for n in ast.walk(t))
 check('context_no_CPU_Source_core_or_oldproducer_importexecution',True)
 pins={**s['source_and_validator_sha256'],str(Path(__file__).relative_to(ROOT)):sha(__file__)};artifacts={**s['artifact_and_dependency_sha256'],**{str(p.relative_to(ROOT)):sha(p)for p in OUT.iterdir()if p.is_file()and p.name not in('verification.json','evidence.json')}}
 result=dict(schema='phase30-early-parent-context-validation-v1',status='passed',ROM_sha256=s['ROM_sha256'],check_count=len(checks),checks=checks,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,new_exclusions=0,source_and_validator_sha256=pins,artifact_and_dependency_sha256=artifacts,limits=['Readonly originalbytes/AST/frozen receipt comparison. No Source/CPU/core or old producer execution.','New fields-static CPU contracts and new Source/Native coverage are independent; no automatic nextphase31.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(OUT/'evidence.json').write_text(json.dumps(dict(schema='phase30-early-parent-context-evidence-v1',status='passed',source_and_validator_sha256=pins,artifact_and_dependency_sha256={**artifacts,'analysis/phase30/context/verification.json':sha(OUT/'verification.json')},Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='passed',checks=len(checks),Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)))
if __name__=='__main__':main()
