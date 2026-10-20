#!/usr/bin/env python3
"""Read-only strict phase17 audit: fields/extinction, two root parents, Native.

This gate runs noCPU, controlIR or emulator. ActualRTS, E000/E066 reset boundaries
and explicitprefix comparisons are counted separately. Missing browser files
alone may produce a pending preview; existing stale or failed evidence cannot.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit,parse_qs,unquote
import argparse,hashlib,json,sys,wave
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from verify_phase12 import source_AST,objects,path_for,relative,sha,read
from verify_phase15 import passed
from verify_phase16 import Audit as PreviousAudit,audit_preparation
OUT=ROOT/'analysis/phase17';SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MODULES={'fields':'city_field_contracts','extinction':'player_extinction'}
INTEGRATION=OUT/'source-integration.json'
NATIVE_CASES={'single-player-empty-rosters-reset','two-player-empty-rosters-continue','former-leader-only-candidate'}
class Audit(PreviousAudit):
 def common_pins(self,data,area=None,relative_base=None):
  super().common_pins(data,area,relative_base)
  if not isinstance(data,dict):return
  for stem in('source','analyzer','validator','source_baseline'):
   path=data.get(stem+'_path');digest=data.get(stem+'_sha256')
   if isinstance(path,str)and isinstance(digest,str):self.pin(path,digest)

def counts(receipt):
 total=receipt['rom_cpu_case_count'];rows=receipt['rows'];assert len(rows)==total
 actual=Counter(row['comparison']for row in rows);assert set(actual)<={'complete_return','reset_boundary','strict_prefix'}
 caller=receipt.get('complete_return_count',receipt.get('total_complete_return_CPU_cases',actual['complete_return']))
 reset=receipt.get('reset_boundary_count',0)
 prefix=receipt.get('strict_prefix_count',receipt.get('total_strict_prefix_CPU_cases',actual['strict_prefix']))
 assert(caller,reset,prefix)==(actual['complete_return'],actual['reset_boundary'],actual['strict_prefix'])and caller+reset+prefix==total
 guards=receipt['source_guard_case_count'];assert len(receipt['guards'])==guards
 assert all((isinstance(g,dict)and g['status']=='passed')or(isinstance(g,str)and bool(g))for g in receipt['guards'])
 return dict(rom_cpu_case_count=total,source_guard_case_count=guards,complete_return_CPU_cases=caller,
   actual_caller_RTS_CPU_cases=sum(row['completion_kind']=='actual_caller_RTS'for row in rows),reset_boundary_CPU_cases=reset,completed_boundary_CPU_cases=caller+reset,strict_prefix_CPU_cases=prefix)

def fields_contracts(audit,r):
 c=counts(r);assert(c['rom_cpu_case_count'],c['complete_return_CPU_cases'],c['strict_prefix_CPU_cases'],c['source_guard_case_count'])==(6548,4890,1658,7)
 assert all(row['all_RAM_byte_count']==2048 and row['all_SRAM_byte_count']==8192 for row in r['rows'])
 assert r['scope']['ordered_SRAM_reads_and_writes']and r['scope']['inactive_caller_stack_included']
 assert all(row['completion_kind']=='actual_caller_RTS'and row['source_status']=='returned'for row in r['rows']if row['comparison']=='complete_return')
 boundary=Counter(row['completion_kind']for row in r['rows']if row['comparison']=='strict_prefix')
 assert boundary==Counter(explicit_prefix_boundary=1657,real_scan_cycle_without_terminator=1)
 waiting=next(row for row in r['rows']if row['completion_kind']=='real_scan_cycle_without_terminator')
 assert waiting['source_status']=='waiting'and waiting['final_registers']['pc']==0xA444 and waiting['continuation']['source_status']=='bounded_prefix'
 review=read(OUT/'fields/alias-refinement.json');inventory=read(OUT/'fields/dispatch-bank-inventory.json');schema=read(OUT/'fields/schema.json')
 assert review['prior_candidate_count']==647 and review['excluded_prior_candidate_count']==58 and review['remaining_prior_candidate_count']==589
 assert len(review['excluded_candidates'])==58 and len(review['remaining_candidates'])==589
 assert review['new_indirect_access_count']==18 and review['new_possible_auxiliary_alias_count']==0 and review['expanded_total_possible_alias_count']==589
 assert len(review['new_indirect_accesses'])==18 and not review['new_possible_auxiliary_aliases']
 for item in review['excluded_candidates']:
  if item.get('exact_address_proof'):
   proof=item['exact_address_proof'];assert proof['city_intersections']==0 and proof['low_high_byte_join_correlations_not_assumed']
   assert not any(0x6000<=address<0x63C0 for address in proof['possible_effective_addresses'])
 assert(inventory['raw_PRG_bank_count'],inventory['raw_PRG_byte_count'],inventory['prior_known_positions'],inventory['new_known_positions'])==(32,262144,46518,47968)
 assert inventory['new_positions_added']==1450 and len(inventory['contiguous_export_vectors'])==87
 assert inventory['trusted_control_entries_found_in_nonseeded_banks']==0 and not inventory['known_direct_control_targets_below_A000']
 assert len(inventory['computed_or_mapper_context_barriers'])==161
 assert len(inventory['mapping_calls'])==207 and len(inventory['raw_allbank_far_call_patterns'])==155
 assert sum(not q['trusted_instruction_position']for q in inventory['raw_allbank_far_call_patterns'])==4
 assert schema['city_byte1']['official_name']is None and schema['city_bytes28_31']['official_name']is None
 assert schema['city_bytes28_31']['padding_or_unassigned_not_proved']
 producer=read(OUT/'fields/legal-full-roster-origin.json')
 assert producer['counted_as_two_rows_in_main_receipt']and producer['destination_before_count']==9 and producer['destination_after_count']==10
 assert producer['full_roster']==list(range(9))+[196]and producer['nomination_city_read_offsets']==list(range(17,27))and producer['nomination_tail_reads']==0
 assert not producer['native_internal_CPU_trace']and not producer['natural_campaign_reachability_claim']
 manifest_path=ROOT/'analysis/phase16/fields/provenance/manifest.json';manifest=read(manifest_path);audit.pin(manifest_path,sha(manifest_path))
 assert manifest['copy_count']==4 and manifest['copied_bytes']==364407
 for item in manifest['copies']:
  audit.pin(item['portable_path'],item['sha256'],item['bytes'])
  assert not any(p.startswith('exploratory')for p in Path(item['portable_path']).parts)
 return dict(old647_excluded=58,old647_remaining=589,new18_indirect_accesses_all_disjoint_or_other_record=True,
   full10_without_FF_is_legal_capacity_output=True,normal_player_and_valid_mean_AI_capacity_guards_separate_from_raw_unbounded_scan=True,
   official_city_byte1_and_tail_names_unresolved=True,no_unused_padding_theorem=True,fixture_domains=r['fixture_domains'])

def extinction_contracts(audit,r):
 c=counts(r);assert(c['rom_cpu_case_count'],c['complete_return_CPU_cases'],c['reset_boundary_CPU_cases'],c['strict_prefix_CPU_cases'],c['source_guard_case_count'])==(423,416,4,3,16)
 assert r['comparison']['RAM_bytes']==2048 and r['comparison']['SRAM_bytes']==8192
 for row in r['rows']:
  assert row['RAM_bytes']==2048 and row['SRAM_bytes']==8192
  if row['comparison']=='complete_return':assert row['completion_kind']=='actual_caller_RTS'and row['source_status']=='returned'
  elif row['comparison']=='reset_boundary':assert row['completion_kind']=='E000_nonlocal_E066_boundary'and row['final_registers']['pc']==0xE066
 assert r['native_input_actual_caller_count']==28 and len(r['actual_caller_inputs'])==28
 return dict(actual_caller_RTS=416,E000_to_E066_nonlocal_reset_boundaries=4,strict_prefix=3,
  native_callee_inputs_already_in423=28,first_slot_FF_predicate_does_not_filter_health_or_status=True,scope=r['comparison'],limits=r['limits'])

def integration_contracts(audit,r):
 passed(r);audit.common_pins(r);c=counts(r)
 assert(c['rom_cpu_case_count'],c['complete_return_CPU_cases'],c['reset_boundary_CPU_cases'],c['strict_prefix_CPU_cases'],c['source_guard_case_count'])==(2,1,1,0,3)
 assert r['comparison']['RAM_bytes']==2048 and r['comparison']['SRAM_bytes']==8192
 assert r['source_original_CPU_callbacks']==0 and not r['source_IR_interpretation']
 for row in r['rows']:
  assert row['RAM_bytes']==2048 and row['SRAM_bytes']==8192 and row['all_event_comparisons_equal']
  if row['comparison']=='reset_boundary':assert row['final_registers']['pc']==0xE066 and row['reset_epoch']==1
 return dict(**{**c,'actual_caller_RTS_CPU_cases':0,'main_NMI_IRQ_RTI_boundary_CPU_cases':1},scope=r['comparison'],parent_cases_not_sum_of_main_NMI_IRQ_arrivals=True,
   completion_kinds=dict(Counter(row['completion_kind']for row in r['rows'])))

def audit_native(audit):
 from PIL import Image
 folder=OUT/'runtime';e=read(folder/'evidence.json');v=read(folder/'validation.json');passed(e);passed(v)
 assert e['schema']=='phase17-native-player-extinction-flows-v1'and v['evidence_sha256']==sha(folder/'evidence.json')
 assert{m['case']for m in e['native_cases']}==NATIVE_CASES
 assert not v['native_internal_CPU_trace']and not v['source_pipeline_installed']and v['source_CPU_comparisons']==0
 audit.common_pins({key:value for key,value in e.items()if key!='native_cases'});audit.common_pins(v);audit.raw(e,'native')
 static_path=folder/'static-validation.json';static=read(static_path)
 assert static['status']=='passed'and not static['failed_count']and static['source_CPU_comparisons']==0
 audit.pin(static_path,sha(static_path));audit.pin(folder/'README.md',sha(folder/'README.md'))
 totals=Counter();details=[]
 for manifest in e['native_cases']:
  p=folder/manifest['case'];r=read(p/'validation.json');rep=read(p/'repeat-validation.json');passed(r)
  assert r['schema']=='phase17-native-player-extinction-flow-v1'and rep['status']=='passed'and rep['all_hashes_equal']and rep['whole_serialized_buffers_exact']
  assert r['controlled_fixture']and not r['natural_gameplay']and not r['rom_modified']and not r['battery_file_imported']and r['fresh_process_per_run']
  assert not r['source_pipeline_installed']and not r['native_internal_CPU_trace']and r['source_CPU_comparisons_in_this_receipt']==0
  assert r['additional_core_memory_writes']==11 and r['additional_core_memory_writes_after_declared_preparation']==0 and r['additional_ready_or_result_injections']==0
  assert not r['death_or_status_bit_preparation']and not r['selected_tactic_result_request_cache_animation_ack_injection']and r['frontend_reset_calls']==0
  audit.common_pins(manifest,relative_base=p);audit.common_pins(r,relative_base=p)
  for script,key in [('scripts/capture_player_extinction.py','script_sha256'),('scripts/capture_succession_flows.py','capture_base_sha256'),
     ('scripts/capture_campaign_flows.py','campaign_capture_base_sha256'),('scripts/nes_runtime.py','original_runtime_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256')]:audit.pin(script,r[key])
  audit.pin('.toolchain/nestopia/nestopia_libretro.dylib',r['core']['core_sha256'])
  prep=audit_preparation(audit,p,r);assert prep['exact_preparation_groups']==1
  assert all(item['address']not in(0x6F43,0x4C8,0x6F8B,0x500,0x501,0x540,0x541)for item in r['preparation'])
  inherited=r['inherited_context'];assert inherited['applied_in_this_run']is False and inherited['inherited_preparation_byte_writes']==0
  if r['state_imported']:
   assert not r['cold_boot'];audit.pin(r['mother_state'],r['mother_sha256'])
   assert(p/'initial.state').read_bytes()==path_for(r['mother_state']).read_bytes()
   assert inherited['whole_mother_equal_to_natural_ancestor'];audit.pin(inherited['ancestor_state'],inherited['ancestor_state_sha256'])
   assert path_for(r['mother_state']).read_bytes()==path_for(inherited['ancestor_state']).read_bytes()
   audit.pin(inherited['documented_parent_validation'],inherited['documented_parent_validation_sha256'])
  else:assert r['cold_boot']and r['mother_state']is None
  for name,item in r['artifact_sha256'].items():assert item['bytes']>0;audit.pin(p/name,item['sha256'],item['bytes'])
  assert path_for(rep['first_run']).resolve()==p.resolve();second=path_for(rep['second_run'])
  assert len(rep['artifacts'])==rep['nonempty_artifact_checks']
  for item in rep['artifacts']:
   assert item['equal']and item['bytes']>0
   audit.pin(p/item['artifact'],item['sha256'],item['bytes']);audit.pin(second/item['artifact'],item['sha256'],item['bytes'])
  assert len(rep['formal_JSON_exact_parity'])==10 and set(rep['formal_JSON_exact_parity'])==set(r['formal_JSON'])
  for name in rep['formal_JSON_exact_parity']:assert(p/name).read_bytes()==(second/name).read_bytes()
  for name in r['excluded_empty_VRAM']:assert(p/name).stat().st_size==0
  points=read(p/'checkpoints.json');frames=read(p/'frame-services.json');callbacks=read(p/'audio-callbacks.json');audio=r['full_audio']
  assert len(points)==r['checkpoint_count']and len(frames)==r['frames']and len(callbacks)==r['frames']
  with wave.open(str(p/'full-flow.wav'),'rb')as stream:
   assert(stream.getnchannels(),stream.getsampwidth(),stream.getframerate(),stream.getnframes())==(2,2,48000,audio['stereo_sample_frames'])
   pcm=stream.readframes(stream.getnframes())
  assert len(pcm)==audio['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==audio['PCM_sha256']and any(pcm)
  assert sha(p/'full-flow.wav')==audio['WAV_sha256']
  cursor=0
  for index,row in enumerate(frames,1):
   assert row['frame']==index
   count=row['PCM_stereo_sample_frames'];chunk=pcm[cursor:cursor+4*count];cursor+=len(chunk)
   assert len(chunk)==4*count and hashlib.sha256(chunk).hexdigest()==row['PCM_sha256']and cursor==row['PCM_stop_byte']and any(chunk)==row['PCM_nonzero']
  assert cursor==len(pcm);cursor=0
  for row in callbacks:
   count=row['stereo_sample_frames'];chunk=pcm[cursor:cursor+4*count];cursor+=len(chunk)
   assert len(chunk)==4*count and hashlib.sha256(chunk).hexdigest()==row['pcm_sha256']and 0<=row['emulated_frame_start']<r['frames']
  assert cursor==len(pcm)
  assert sha(p/'initial-ram.bin')==r['initial_RAM_sha256']and sha(p/'initial-sram.bin')==r['initial_SRAM_sha256']
  for point in points:
   row=frames[point['frame']-1]
   assert sha(p/point['RAM'])==row['RAM_sha256']and sha(p/point['SRAM'])==row['SRAM_sha256']
   assert(p/point['RAM']).stat().st_size==2048 and(p/point['SRAM']).stat().st_size==8192 and(p/point['state']).stat().st_size>0
   with Image.open(p/point['image'])as image:
    assert list(image.size)==row['native_dimensions']==[256,240]
    assert hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
  effects=r['verified_effects'];assert effects==manifest['verified_effects']and r['campaign_events']==read(p/'campaign-events.json')
  assert effects['actual_original_ordinary_attack']and effects['health_FF_preserved_not_normalized']
  assert effects['original_defeat_record']['health']==255 and effects['original_defeat_record']['status']==3
  final=r['final_fields'];assert effects['final_controller']==[final['global_state'],final['nmi_scene'],final['active_main'],final['active_phase']]
  if manifest['case']=='single-player-empty-rosters-reset':
   assert effects['ending_observed']and effects['original_owned_empty_rosters_no_candidate']and effects['leader_before_ending']==255
   assert effects['ending_mode']==0 and effects['original_ready_marker_FE']and effects['ending_continue_flag_before_A']==0
   assert effects['original_B_does_not_exit']and effects['original_A_software_reset']and effects['actual_title_return']and effects['actual_new_game_reactivated']
   assert not effects['reset_via_frontend']and effects['reactivated_player_ruler']==2 and effects['reactivated_leader']==131
  elif manifest['case']=='two-player-empty-rosters-continue':
   assert r['cold_boot']and not r['state_imported']and effects['ending_observed']and effects['leader_before_ending']==255
   assert effects['actual_cold_title_two_player_selection']and effects['two_player_flag_generated_by_original_title']and effects['flag_not_prepared']
   assert effects['ending_continue_flag_before_A']==1 and effects['original_A_parent_restore']and effects['original_A_clears_continue_flag']
   assert effects['remaining_player_original_prompt_acknowledged']and effects['remaining_player_world_ready']and not effects['software_reset_after_loss']
   assert effects['second_player_ruler']==4 and effects['controller2_button_pulses']>0
   assert any(item.get('controller_port',0)==1 and item['buttons']for item in read(p/'input-plan.json'))
  else:
   assert not effects['ending_observed']and effects['original_candidate_city11_accepted']and effects['original_candidate_officer131_accepted']and effects['candidate_health_status_not_filtered']
   assert effects['leader_after']==131 and effects['leader_record_after']['health']==255 and effects['leader_record_after']['status']==3
  totals.update(frames_first_run=r['frames'],checkpoint_count=r['checkpoint_count'],nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],
   formal_JSON_repeat_checks=len(rep['formal_JSON_exact_parity']),PCM_stereo_sample_frames_first_run=audio['stereo_sample_frames'],
   excluded_empty_VRAM=len(r['excluded_empty_VRAM']),excluded_snapshot_metadata_JSON=len(r['excluded_snapshot_metadata_JSON']),
   additional_core_memory_writes=r['additional_core_memory_writes'],state_import_count=int(r['state_imported']),cold_boot_count=int(r['cold_boot']),inherited_preparation_byte_writes=0)
  for filename in('validation.json','repeat-validation.json'):audit.pin(p/filename,sha(p/filename))
  details.append(dict(case=manifest['case'],status='passed',frames=r['frames'],checkpoint_count=r['checkpoint_count'],controlled_fixture=True,
   cold_boot=r['cold_boot'],state_imported=r['state_imported'],preparation=prep,verified_effects=effects,inherited_context=inherited,
   receipt_path=relative(p/'validation.json'),repeat_receipt_path=relative(p/'repeat-validation.json')))
 mapping={'frames_first_run':'original_core_frames_first_run','checkpoint_count':'checkpoint_count','nonempty_repeat_artifact_checks':'nonempty_artifacts_double_run_hash_checks',
  'formal_JSON_repeat_checks':'formal_JSON_exact_parity','PCM_stereo_sample_frames_first_run':'PCM_stereo_sample_frames_first_run','excluded_empty_VRAM':'excluded_empty_VRAM',
  'excluded_snapshot_metadata_JSON':'excluded_snapshot_metadata_JSON','additional_core_memory_writes':'additional_core_memory_writes','state_import_count':'state_imports','cold_boot_count':'cold_boot_cases','inherited_preparation_byte_writes':'inherited_preparation_byte_writes'}
 for key,value in totals.items():assert v[mapping[key]]==value
 assert dict(e['summary'])=={key:v[key]for key in e['summary']}
 assert(totals['frames_first_run'],totals['checkpoint_count'],totals['nonempty_repeat_artifact_checks'],totals['formal_JSON_repeat_checks'])==(34062,594,2429,30)
 assert(totals['additional_core_memory_writes'],totals['inherited_preparation_byte_writes'],totals['state_import_count'],totals['cold_boot_count'])==(33,0,2,1)
 assert v['original_core_frames_both_runs']==68124 and v['case_count']==3
 assert(static['nonempty_artifact_rehash_checks'],static['decoded_same_frame_PNG_RGB_RAM_SRAM'],static['decoded_48k_stereo_WAV'],static['preparation_full_dump_reconstruction_checks'])==(2429,594,3,3)
 return {**v,**totals,'frames_both_runs':68124,'native_case_count':3,'cases':details,'no_global_natural_or_zero_write_claim':True,
  'nested_native_frames_are_not_source_CPU_comparisons':True,'PCM_stereo_sample_frames_both_runs_derived':2*totals['PCM_stereo_sample_frames_first_run']}

def browser_checks(audit,areas,runtime,allow_pending):
 missing=[]
 def required(path):
  if path.is_file():return read(path)
  assert allow_pending,f'Missing required browser artifact {relative(path)}'
  missing.append(relative(path));return None
 static_path=OUT/'browser-static-validation.json';static=required(static_path)
 if static is not None:
  assert static['status']=='passed'and static['JS_syntax']=='passed'and not static['native_files_modified']
  assert static['HTML_sha256']==sha(OUT/'index.html')and static['native_evidence_sha256']==sha(OUT/'runtime/evidence.json')
  assert static['final_required']and static['integration']['status']=='passed'and static['integration']['current_pins_match']
  assert{row['key']for row in static['modules']}==set(MODULES)|{'adapter'}
  assert static['standalone_CPU_domains']==2 and static['module_count']==3
  for row in static['modules']:
   if row['key']=='adapter':
    assert row['standalone_counted']is False and all(row[key]is None for key in('CPU','complete','reset','prefix','guards'))
    audit.pin('source/recovered/extinction_scene_services.py',row['source_sha256'])
    assert row['verification_CPU_callbacks']==row['production_CPU_callbacks']==0
    continue
   assert row['standalone_counted']is True
   c=areas[row['key']]['primary_receipt_counts']
   assert row['CPU']==c['rom_cpu_case_count']and row['guards']==c['source_guard_case_count']and row['prefix']==c['strict_prefix_CPU_cases']
   assert row['complete']==c['complete_return_CPU_cases']
   if c['reset_boundary_CPU_cases']:assert row.get('reset',row.get('reset_boundaries',row.get('reset_boundary_count')))==c['reset_boundary_CPU_cases']
   assert row['verification_CPU_callbacks']==row['production_CPU_callbacks']==0
  qa=static['native_static_QA']
  assert qa['nonempty_double_run_artifacts']==2429 and qa['formal_JSON_exact_parity']==30
  assert qa['same_frame_PNG_RAM_SRAM_state']==594 and qa['frame_PCM_segments']==34062 and qa['audio_callback_segments']==34062
  assert qa['WAV_header_PCM_hash']==3 and qa['preparation_group_checks']==3
  audit.pin('scripts/build_phase17_browser.py',static['generator_sha256'])
  if'template_generator_sha256'in static:audit.pin('scripts/build_phase14_browser.py',static['template_generator_sha256'])
  audit.pin(static_path,sha(static_path))
 browser_path=OUT/'browser-validation.json';browser=required(browser_path)
 if browser is not None:
  assert browser['status']=='passed'and browser.get('html_sha256',browser.get('HTML_sha256'))==sha(OUT/'index.html')
  assert browser.get('checks')and all(browser['checks'].values())and not browser.get('console_errors',[])
  audit.pin(OUT/'browser-proof.png',browser['screenshot_sha256'])
  audit.common_pins(browser)
  from PIL import Image
  proof=path_for(browser['screenshot_media_path'])
  assert proof.read_bytes()==(OUT/'browser-proof.png').read_bytes()
  with Image.open(proof)as image:
   assert image.format==browser['screenshot_format']=='JPEG'
   assert image.size==(browser['screenshot_dimensions']['width'],browser['screenshot_dimensions']['height'])
  assert{item['file']for item in browser['source_modules']}=={'city_field_contracts.py','player_extinction.py','extinction_scene_services.py'}
  for item in browser.get('source_modules',[]):
   assert item['full_source_equal'];audit.pin('source/recovered/'+item['file'],item['sha256'],item['bytes'])
  for item in objects(browser):
   if isinstance(item.get('src'),str)and'?'in item['src']:
    url=urlsplit(item['src']);expected=parse_qs(url.query).get('sha')
    if expected:
     file=ROOT/unquote(url.path.lstrip('/'))if url.path.startswith('/analysis/')else OUT/unquote(url.path)
     audit.pin(file,expected[0])
  audit.pin(browser_path,sha(browser_path))
 if(OUT/'index.html').exists():audit.pin(OUT/'index.html',sha(OUT/'index.html'))
 return static_path,static,browser_path,browser,missing

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
 p.add_argument('--allow-pending-browser',action='store_true',help='Only missing browser acceptance may be pending; allotherfiles and existingpins remain strict')
 args=p.parse_args();rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
 assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
 audit=Audit(rom)
 for name in('scripts/verify_phase17.py','scripts/verify_phase16.py','scripts/verify_phase15.py','scripts/verify_phase13.py','scripts/verify_phase12.py',
   'scripts/package_results.py','scripts/validate_phase17_package.py','scripts/write_phase17_report.py','scripts/build_phase17_browser.py'):
  path=ROOT/name;assert path.is_file(),name;audit.pin(path,sha(path))
 regressions={}
 for phase in range(5,17):
  path=ROOT/f'analysis/phase{phase}/verification.json';old=read(path);passed(old,production_contract=False)
  for key in('source_and_validator_sha256','artifact_and_dependency_sha256'):
   for name,digest in old.get(key,{}).items():audit.pin(name,digest)
  audit.pin(path,sha(path));regressions[str(phase)]=dict(status='passed',verification_sha256=sha(path),current_pins=True)
 parent_path=OUT/'regression/parent-regression.json';parents=read(parent_path);audit.pin(parent_path,sha(parent_path));audit.common_pins(parents)
 # The /tmp producer log is only an historical location. Its exact portable
 # copy is mandatory evidence; neverpin /tmp as a requiredarchive dependency.
 log=OUT/'regression/parent-regression.log';audit.pin(log,parents['log_sha256'])
 readonly_path=OUT/'regression/readonly-audits.json';readonly=read(readonly_path)
 assert readonly['status']=='passed'and len(readonly['rows'])==12 and all(row['exit_code']==0 for row in readonly['rows'])
 audit.pin(readonly_path,sha(readonly_path))
 areas={};receipts={};evidences={};total=Counter()
 for area,module in MODULES.items():
  folder=OUT/area;r=read(folder/'validation.json');e=read(folder/'evidence.json');passed(r)
  assert e.get('rom_sha256',e.get('ROM_sha256'))==SHA
  audit.common_pins(r,area);audit.common_pins(e,area);audit.raw(e,area)
  for path in folder.glob('*.json'):
   if path.name in('validation.json','evidence.json'):continue
   data=read(path);audit.common_pins(data,area);audit.raw(data,f'{area}/{path.name}');audit.pin(path,sha(path))
  for path in folder.glob('*.asm'):audit.pin(path,sha(path))
  audit.pin(folder/'README.md',sha(folder/'README.md'))
  c=counts(r);total.update(c)
  semantic=fields_contracts(audit,r)if area=='fields'else extinction_contracts(audit,r)
  receipts[area]=sha(folder/'validation.json');evidences[area]=sha(folder/'evidence.json')
  audit.pin(folder/'validation.json',receipts[area]);audit.pin(folder/'evidence.json',evidences[area])
  areas[area]=dict(receipt_path=relative(folder/'validation.json'),evidence_path=relative(folder/'evidence.json'),primary_receipt_counts=c,
   actual_scope=r.get('scope',r.get('comparison')),semantics=semantic)
 r=read(INTEGRATION);integration=integration_contracts(audit,r)
 receipts['source-integration']=sha(INTEGRATION);audit.pin(INTEGRATION,receipts['source-integration'])
 ast_paths=[ROOT/f'source/recovered/{module}.py'for module in list(MODULES.values())+['extinction_scene_services','scene_coordinator','campaign_session']]
 ast_checks=source_AST(ast_paths)
 for path in ast_paths:audit.pin(path,sha(path))
 runtime=audit_native(audit);receipts['native']=sha(OUT/'runtime/validation.json');evidences['native']=sha(OUT/'runtime/evidence.json')
 audit.pin(OUT/'runtime/validation.json',receipts['native']);audit.pin(OUT/'runtime/evidence.json',evidences['native'])
 static_path,static,browser_path,browser,missing=browser_checks(audit,areas,runtime,args.allow_pending_browser)
 for path in(OUT/'README.md',ROOT/'source/README.md'):assert path.is_file();audit.pin(path,sha(path))
 assert not any(any(part.startswith('exploratory')for part in Path(name).parts)for name in audit.pins),'Excluded exploratory path cannot be a requiredportabledependency'
 sourcepins={name:digest for name,digest in sorted(audit.pins.items())if name.startswith(('source/','scripts/'))}
 artifactpins={name:digest for name,digest in sorted(audit.pins.items())if name not in sourcepins}
 # Integrationcomplete_return is a parentmain/NMI/IRQsequence, not anRTS.
 assert integration['complete_return_CPU_cases']==1
 source_actual_RTS=total['actual_caller_RTS_CPU_cases']
 all_declared_complete=total['complete_return_CPU_cases']+integration['complete_return_CPU_cases']
 all_reset=total['reset_boundary_CPU_cases']+integration['reset_boundary_CPU_cases']
 result=dict(schema='phase17-source-campaign-evidence-aggregate-v1',status='pending'if missing else'passed',rom_sha256=SHA,
  missing_required_artifacts=missing,areas=areas,receipt_sha256=receipts,evidence_sha256=evidences,
  source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256=artifactpins,
  rom_cpu_case_count=total['rom_cpu_case_count'],source_guard_case_count=total['source_guard_case_count'],
  total_complete_return_CPU_cases=total['complete_return_CPU_cases'],total_actual_caller_RTS_CPU_cases=source_actual_RTS,
  total_reset_boundary_CPU_cases=total['reset_boundary_CPU_cases'],total_strict_prefix_CPU_cases=total['strict_prefix_CPU_cases'],
  source_integration_receipt_path=relative(INTEGRATION),source_integration=integration,
  integration_rom_cpu_case_count=integration['rom_cpu_case_count'],integration_source_guard_case_count=integration['source_guard_case_count'],
  source_integration_reset_boundary_CPU_cases=1,source_integration_main_NMI_IRQ_RTI_boundary_CPU_cases=1,source_integration_actual_caller_RTS_CPU_cases=0,
  all_CPU_cases_including_integration=total['rom_cpu_case_count']+2,all_source_guards_including_integration=total['source_guard_case_count']+3,
  all_complete_return_CPU_cases_including_integration=all_declared_complete,
  all_actual_caller_RTS_CPU_cases_including_integration=source_actual_RTS,all_reset_boundary_CPU_cases_including_integration=all_reset,
  all_main_NMI_IRQ_RTI_boundary_CPU_cases_including_integration=1,
  all_completed_boundary_CPU_cases_including_integration=all_declared_complete,
  all_complete_or_reset_boundary_CPU_cases_including_integration=all_declared_complete+all_reset,
  all_strict_prefix_CPU_cases_including_integration=total['strict_prefix_CPU_cases'],
  completed_comparison_label_scope='complete_return is the receiptcomparison classification; integrationone is a realmain_E066/NMI/IRQsequenceboundary. ActualRTS5306 and reset5 and mainsequence1 are distinct.',
  source_AST=ast_checks,metadata_range_corrections=audit.metadata_range_corrections,rebuilt_byte_identical=True,regressions=regressions,
  parent_regression_receipt_path=relative(parent_path),readonly_regression_receipt_path=relative(readonly_path),
  native_evidence_path=relative(OUT/'runtime/evidence.json'),native=runtime,
  browser_static_receipt_path=relative(static_path),browser_static_receipt_sha256=sha(static_path)if static is not None else None,
  browser_receipt_sha256=sha(browser_path)if browser is not None else None,browser_status=browser['status']if browser else'pending',
  limitations=['Citybyte1 andtail28..31 remain withoutprovedofficialnames. 589potentialaliases are notconfirmedconsumers orproof ofunused/padding.',
   'Fourunboundedcapacity/scannerprefixes andonecyclicwait are explicit originalboundaries, notcompletecitycommands orfakeRTS.',
   'Normalplayer/valid-occupancy AIcapacitychecks andboundedten-slotnomination are distinctfromrawprefixoverflow.',
   'Extinction4reset boundaries finishatE066 ratherthanRTS; integrationreset1 andactualmain/NMI/IRQparent1 are distinctcompletionkinds.',
   'Native3controlledpre-fightcases have33newwrites,2naturalmotherimports and1coldstart; titlegenerates6F43 withrealport1inputs. Noall-natural/zero-writecampaignclaim.',
   'NativehasnointernalCPUtrace andnosourcepipeline; RGB/PCMtiming are suppliedbyimmutable originalNestopiacore.',
   'OriginalROM/oldNative/oldversionZIPs remainimmutable; currentold5..16 producers/audits were actually rerun. This aggregate runsnoCPU/core/IR.'])
 assert(result['all_CPU_cases_including_integration'],result['all_source_guards_including_integration'],source_actual_RTS,all_reset,result['all_strict_prefix_CPU_cases_including_integration'])==(6973,26,5306,5,1661)
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','all_CPU_cases_including_integration','browser_status','missing_required_artifacts')},ensure_ascii=False))
if __name__=='__main__':main()
