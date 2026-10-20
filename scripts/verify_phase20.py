#!/usr/bin/env python3
"""Read-only phase20 audit; does not replay CPUs, rewrite sources or old audits."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys, wave
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/phase20'
sys.path.insert(0,str(ROOT))
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OLD_AUDIT='2f232a65b1ecfb1322d909c38e5e813f2a3b24cf222fe189561191258eb77359'
OLD_ZIP='2f0fdf6f3755db09715d5f9149ef84ea0a39dbe6531e41361410ce92db703ba2'
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);args=parser.parse_args()
 rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
 pins={};counts=Counter()
 def pin(name,digest=None):
  path=Path(name);path=path if path.is_absolute()else ROOT/path
  key=str(path.relative_to(ROOT));assert not any(part.startswith('exploratory')for part in path.parts),key
  actual=sha(path);assert digest is None or actual==digest,(key,digest,actual)
  if key in pins:assert pins[key]==actual,(key,'Inconsistent duplicate pin')
  pins[key]=actual;return actual
 def receipt_pins(record):
  for group in('source_sha256','source_and_validator_sha256','artifact_sha256','input_sha256'):
   for name,digest in record.get(group,{}).items():pin(name,digest)
  deps=record.get('dependency_pins',{})
  if isinstance(deps,dict):
   for name,digest in deps.items():pin(name,digest)
  else:
   for dep in deps:pin(dep['path'],dep['sha256'])
 def original_bytes(row):
  if 'raw_hex'not in row:return
  raw=bytes.fromhex(row['raw_hex']);off=16+row['physical_bank']*8192+(row['cpu']&8191)
  assert row.get('rom_offset',off)==off and rom[off:off+len(raw)]==raw,row
 prior_path=ROOT/'analysis/phase19/verification.json';assert sha(prior_path)==OLD_AUDIT
 prior=read(prior_path);assert prior['status']=='passed'and prior['rebuilt_byte_identical']
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for name,digest in prior[group].items():pin(name,digest);counts['unchanged_phase19_dependency_pins']+=1
 assert counts['unchanged_phase19_dependency_pins']==20538
 pin(prior_path);assert sha(ROOT/'build/三国志2超级版-逆向分析-v19.zip')==OLD_ZIP
 for name in('README.md','requirements.txt','.gitignore','analysis/index.html','build/三国志2超级版.rebuilt.nes'):pin(name)

 # Static domain validation is not source gameplay or a returned ROM function.
 static=read(OUT/'fields-static/analysis-summary.json');field=read(OUT/'fields-static/verification.json')
 assert static['status']=='analyzed'and field['status']=='passed'and field['failed_count']==0
 assert static['source_CPU_cases']==field['source_CPU_cases']==0
 receipt_pins(field)
 assert field['model_guard_check_count']>=8
 assert field['declared_local_return_structures_checked']==static['universal_return_contract_count']
 assert static['universal_return_contract_count']==static['universal_return_pair_contract_count']+static['universal_numeric_only_return_contract_count']
 counts['static_model_guards']=field['model_guard_check_count']
 counts['original_constructor_prefix_CPU_checks']=field['original_constructor_prefix_CPU_cases']
 counts['original_mapper_prefix_CPU_checks']=field['original_mapper_prefix_CPU_cases']
 counts['original_structured_loop_boundary_CPU_checks']=field['original_structured_loop_boundary_CPU_cases']
 counts['synthetic_compare_branch_model_checks']=field['model_instruction_oracle_cases']
 assert counts['original_structured_loop_boundary_CPU_checks']==12
 assert counts['synthetic_compare_branch_model_checks']==27648
 counts['static_return_structures_checked']=field['declared_local_return_structures_checked']
 for name,n in(('access-contracts.json',589),('all-indirect-accesses.json',1526),('new-indirect-accesses.json',45)):
  access=read(OUT/'fields-static'/name);rows=access['accesses']
  assert len(rows)==access['access_count']==n and len({(x['physical_bank'],x['cpu'])for x in rows})==n
  assert Counter(x['classification']for x in rows)==access['classification_counts']
  expected_classifications=static[{'access-contracts.json':'classification_counts','all-indirect-accesses.json':'all_indirect_classification_counts','new-indirect-accesses.json':'new_indirect_classification_counts'}[name]]
  assert access['classification_counts']==expected_classifications
  assert access['source_CPU_cases']==0
  for row in rows:
   original_bytes(row);contract=row.get('address_contract')or{}
   if row['classification']=='proved_disjoint_auxiliary_address_domain':
    if 'auxiliary_address_intersection_count'in contract:assert contract['auxiliary_address_intersection_count']==0
  counts['classified_original_access_rows']+=n
 remaining=read(OUT/'fields-static/remaining-accesses.json')
 assert remaining['access_count']==len(remaining['accesses'])==static['remaining_access_count']
 assert all(x['classification']!='proved_disjoint_auxiliary_address_domain'for x in remaining['accesses'])
 assert all(v is None for v in static['official_target_field_names'].values())
 counts['remaining_unresolved_auxiliary_candidates']=len(remaining['accesses'])

 # Named source matrix, real exported callers and two kinds of consumer parent.
 service=read(OUT/'services/validation.json');service_ev=read(OUT/'services/evidence.json')
 assert service['status']==service_ev['status']=='passed'and service['failed_count']==0
 assert service['original_CPU_parent_cases']==len(service['cases'])==625
 expected=Counter(actual_fixture_caller_RTS=600,original_loop_wait=24,strict_dependency_prefix=1)
 assert Counter(x['comparison']for x in service['cases'])==service['counts']==expected
 assert service['source_original_CPU_callbacks']==0 and not service['production_IR_interpretation']
 for row in service['cases']:
  assert(row['RAM_bytes'],row['SRAM_bytes'])==(2048,8192)
  assert row['all_registers_IO_banks_N163_equal']and row['source_original_CPU_callbacks']==0
 coverage=service_ev['coverage'];assert coverage['static_original_positions']==coverage['dynamically_executed_positions']==257
 assert coverage['static_original_bytes']==549 and coverage['not_dynamically_executed']==[]
 assert not service_ev['AST_forbidden_imports_or_dynamic_execution']
 for key in('validation','consumer_sequences'):pin(service_ev[key]['path'],service_ev[key]['sha256'])
 catalog=read(OUT/'services/static-catalog.json');assert len(catalog['instructions'])==257
 assert len({(x['physical_bank'],x['cpu'])for x in catalog['instructions']})==257
 for row in catalog['instructions']:original_bytes(row);assert row['dynamically_executed']
 for row in catalog['ranges']:
  raw=bytes.fromhex(row['raw_hex']);assert len(raw)==row['size']and hashlib.sha256(raw).hexdigest()==row['sha256']
  assert rom[row['rom_offset']:row['rom_offset']+len(raw)]==raw
 assert sum(x['size']for x in catalog['ranges'])==549
 counts['controlled_source_CPU_parent_cases']=625;counts['named_original_static_positions']=257
 actual=read(OUT/'cpu/actual-caller-source-validation.json')
 assert actual['status']=='passed'and actual['original_CPU_parent_cases']==len(actual['rows'])==8
 assert(actual['returned_count'],actual['waiting_count'])==(7,1)
 assert Counter(x['completion']for x in actual['rows'])==Counter(returned=7,waiting=1)
 for row in actual['rows']:
  assert row['prepared_bytes']==[]and row['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']
  assert row['source_original_CPU_callbacks']==0 and not row['Native_internal_CPU_trace']
 counts['actual_callee_source_CPU_parent_cases']=8
 for record in(service,service_ev,actual):receipt_pins(record)
 for name,n,kind in(('consumer-sequences.json',4,'controlled'),('native-context-source-sequences.json',2,'actual_saved_Native')):
  rec=read(OUT/'cpu'/name);assert rec['status']=='passed'and rec['failed_count']==0
  assert rec['rom_cpu_sequence_count']==len(rec['rows'])==n and rec['source_original_CPU_callbacks']==0 and not rec['production_IR_interpretation']
  assert rec['comparison']==dict(RAM=2048,SRAM=8192,AXYP_SP_PC=True,ordered_IO_banks_N163=True,inactive_stack_included=True)
  for row in rec['rows']:
   assert row['postentry_memory_injections']==0 and row['all_services_pure_source']
   assert(row['all_RAM_byte_count'],row['all_SRAM_byte_count'])==(2048,8192)
   assert row['ordered_IO_equal']and row['all4banks_equal']and row['N163_state_equal']
   assert all(e['full_scope_equal']for e in row['events'])
   assert row['completion_kind']=='actual_caller_RTS_after_genuine_NMI2_consumer'
   if kind=='actual_saved_Native':
    assert row['prepared_bytes']==[]and row['initial_request_from_original_core']==248
    assert row['original_CPU_prelude_instructions']>0;pin(row['Native_state_path'],row['Native_state_sha256'])
  receipt_pins(rec);counts[kind+'_consumer_parent_sequences']=n
 counts['new_source_CPU_parent_cases']=625+8+4+2
 counts['new_source_actual_caller_RTS_parents']=600+7+4+2
 counts['new_source_wait_parents']=24+1;counts['new_source_strict_dependency_prefixes']=1
 diagnostic=read(OUT/'cpu/evidence.json');assert diagnostic['status']=='passed'and diagnostic['source_comparison_cases']==0
 assert diagnostic['distinct_original_CPU_diagnostic_contexts']==6 and diagnostic['F8_generated_prefixes']==4
 assert diagnostic['parity_RAM_difference_counts']==[37,17,33,32]
 assert diagnostic['existing_real_callee_input_count']==8 and diagnostic['PC_RNG_request_ready_or_caller_frame_injections']==0
 receipt_pins(diagnostic);counts['diagnostic_contexts_not_added_to_source_CPU_cases']=6

 # Full original-core observations and two fresh-process repeats, no prepared data.
 runtime=read(OUT/'runtime/validation.json');native_ev=read(OUT/'runtime/evidence.json');runtime_static=read(OUT/'runtime/static-validation.json')
 assert runtime['status']==native_ev['status']==runtime_static['status']=='passed'
 assert runtime['evidence_sha256']==sha(OUT/'runtime/evidence.json')
 assert all(runtime[k]==v for k,v in native_ev['summary'].items())
 for key in('additional_core_memory_writes','inherited_preparation_byte_writes','state_imports','additional_ready_or_result_injections','source_CPU_comparisons'):
  assert runtime[key]==0,key
 assert runtime['case_count']==runtime['cold_boot_cases']==runtime['actual_full_WAV_count']==2
 assert runtime['original_F8_observed']and runtime['F8_consumer_or_return_verified']
 assert not runtime['native_internal_CPU_trace']and not runtime['source_pipeline_installed']
 receipt_pins(native_ev)
 assert len(native_ev['native_cases'])==2
 for case in native_ev['native_cases']:
  folder=OUT/'runtime'/case.get('folder',case['case']);v=read(folder/'validation.json');repeat=read(folder/'repeat-validation.json')
  assert v['status']==repeat['status']=='passed'and repeat['all_hashes_equal']and repeat['whole_serialized_buffers_exact']
  assert v['cold_boot']and v['natural_gameplay']and not v['state_imported']and not v['battery_file_imported']and not v['controlled_fixture']
  assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
  assert v['preparation']==v['preparation_groups']==[]and not v['controller_pointer_request_RNG_weights_prepared']
  assert v['original_F8_observed']and v['F8_consumer_or_return_verified']and v['core']['core_sha256']==CORE_SHA
  assert len(repeat['artifacts'])==repeat['nonempty_artifact_checks']
  other=ROOT/repeat['second_run']
  for artifact in repeat['artifacts']:
   assert artifact['equal']and artifact['bytes']>0
   for base in(folder,other):
    path=base/artifact['artifact'];assert path.stat().st_size==artifact['bytes'];pin(path,artifact['sha256'])
  for name in repeat['formal_JSON_exact_parity']:
   assert(folder/name).read_bytes()==(other/name).read_bytes();pin(folder/name);pin(other/name)
  counts['native_nonempty_repeat_artifacts']+=len(repeat['artifacts'])
  frames=read(folder/'frame-services.json');points=read(folder/'checkpoints.json')
  assert len(frames)==v['frames']and len(points)==v['checkpoint_count']
  assert all(x['frame']==i+1 and not x['Native_instruction_trace']for i,x in enumerate(frames))
  for point in points:
   row=frames[point['frame']-1]
   with Image.open(folder/point['image'])as image:
    assert image.size==(256,240)and hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   for key,size in(('RAM',2048),('SRAM',8192)):
    path=folder/point[key];assert path.stat().st_size==size and sha(path)==row[key+'_sha256']
   state=folder/point['state'];assert sha(state)==row['whole_serialized_state_sha256']
   captured=NestopiaContext.parse(state.read_bytes())
   assert captured.ram==(folder/point['RAM']).read_bytes()and captured.sram==(folder/point['SRAM']).read_bytes()
   assert captured.registers==row['actual_saved_CPU_registers']and list(captured.prg_banks)==row['actual_saved_PRG_banks']
  with wave.open(str(folder/'full-audio.wav'),'rb')as wav:
   assert(wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000)
   total=0
   for row in frames:
    pcm=wav.readframes(row['PCM_stereo_sample_frames']);total+=len(pcm)
    assert len(pcm)==4*row['PCM_stereo_sample_frames']and hashlib.sha256(pcm).hexdigest()==row['PCM_sha256']
    assert total==row['PCM_stop_byte']
   assert not wav.readframes(1);counts['original_PCM_sample_pairs']+=wav.getnframes()
  effect=v['verified_effects'];assert effect['ordinary_confirmation_delay_frames']==73
  assert effect['AI_continuation_verified']and effect['next_human_ruler']==1
  assert effect['offer']['quote']==[114,0,0]and effect['offer']['leaders_and_messenger']==[222,8,38]
  assert effect['first_observed_reply']['observed_status']==(0 if effect['choice']=='accept'else 1)
  reply=effect['first_observed_reply'];food=reply['city_food'];rulers=reply['rulers']
  if effect['choice']=='accept':
   assert(food[2],food[4])==(9885,10113)
   assert rulers[1]['diplomatic_bytes']==[0,0,10,0]and rulers[4]['diplomatic_bytes']==[160,0,0,0]
   cap=effect['recipient_grain_later_cap_frame'];assert cap>reply['frame']
   # Keep both actual observations; no normalization of the temporary excess.
   assert frames[cap-2]['all30_city_food'][4]==10113 and frames[cap-1]['all30_city_food'][4]==9999
  else:
   assert(food[2],food[4])==(9999,9999)
   assert rulers[1]['diplomatic_bytes']==rulers[4]['diplomatic_bytes']==[0,0,0,0]
  assert effect['original_request_FF_frame']>reply['frame']and effect['final_controller']==[2,2,0,1]
  counts['native_cases']+=1;counts['native_first_run_frames']+=len(frames);counts['native_checkpoints']+=len(points)
  del frames,points
 assert counts['native_cases']==2
 for ck,rk in(('native_first_run_frames','frames_first_run'),('native_checkpoints','checkpoint_count'),('native_nonempty_repeat_artifacts','nonempty_repeat_artifact_checks'),('original_PCM_sample_pairs','PCM_stereo_sample_frames_first_run')):
  assert counts[ck]==runtime[rk],(ck,counts[ck],runtime[rk])
 assert runtime_static['checks']['artifact_rehashes']==counts['native_nonempty_repeat_artifacts']
 assert runtime_static['checks']['PNG_RAM_SRAM_wholeState_same_frame']==counts['native_checkpoints']

 # Browser receipts intentionally share phase19's small, explicit schema.
 browser=read(OUT/'browser-static-check.json');qa=read(OUT/'browser-validation.json')
 assert browser['status']==qa['status']=='passed'
 assert sha(OUT/'index.html')==browser['HTML_sha256']==qa['HTML_sha256']
 assert qa['console']==[]and qa['checks']and all(x['passed']for x in qa['checks'])
 assert len(qa['sources'])>=2 and len(qa['native'])==len(qa['audio'])==2
 for row in qa['sources']:
  assert row['full_UTF8_equal'];pin(ROOT/'source/recovered'/row['file'],row['sha256'])
 for row in qa['native']:
  assert row['frame_values_equal']and row['checkpoint_values_equal']and row['PNG_paths_SHA256_equal']
  assert row['imageStates']and all(x['complete']and x['w']==256 and x['h']==240 for x in row['imageStates'])
 assert all(x['passed']and x['WAV_SHA256_verified']for x in qa['audio'])
 shot=qa['screenshot'];pin(shot['path'],shot['sha256']);assert(ROOT/shot['path']).stat().st_size==shot['bytes']
 assert shot['original_capture_bytes_preserved']
 with Image.open(ROOT/shot['path'])as image:assert image.format in('JPEG','PNG')and image.width==qa['viewport']['DOM_width']
 receipt_pins(browser)
 # Pin all final phase20 files; zero-byte VRAM is preserved but never counted
 # as effective Native content or a rendered/PPU memory verification.
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts)and path.name not in('verification.json','package-receipt.json'):
   pin(path)
 sources={str(p.relative_to(ROOT)):sha(p)for folder in('source','scripts')for p in(ROOT/folder).rglob('*')if p.is_file()and '__pycache__'not in p.parts and not any(x.startswith('exploratory')for x in p.parts)}
 result=dict(schema='phase20-frozen-history-named-F8-source-and-original-core-audit-v1',status='passed',ROM_sha256=ROM_SHA,
  rebuilt_byte_identical=True,old_v19_preserved_sha256=OLD_ZIP,old_phase19_audit_sha256=OLD_AUDIT,checks=dict(counts),
  source_and_validator_sha256=sources,artifact_and_dependency_sha256=pins,
  limits=['639 new source CPU parents remain separate from static constructor prefixes, model checks and six overlapping originalCPU diagnostics.',
   '257/257 instruction positions are not all gameplay inputs, all paths or hardware timing.',
   'Native saved PC/registers/banks and pixels are not an internal per-instruction core trace.',
   'OriginalNative video timing and explicitly scheduled software CPU interrupt sequences have different contracts.',
   'City auxiliary official names/unused status remain unresolved; conditional static domains do not prove full-ROM reachability.'])
 OUT.mkdir(exist_ok=True);(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='passed',checks=dict(counts),source_pins=len(sources),artifact_pins=len(pins)),ensure_ascii=False))
if __name__=='__main__':main()
