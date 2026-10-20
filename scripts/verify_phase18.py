#!/usr/bin/env python3
"""Read-only phase18 byte/pointer/source/Native/browser evidence aggregate.

This audit runs no CPU, control IR, emulator or gameplay source. Historical
phase17 source/artifact hashes must remain current, including its immutableZIP.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,wave
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase18';SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
 assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
 pins={};checked=Counter()
 def pin(name,digest=None):
  path=Path(name);path=path if path.is_absolute()else ROOT/path;key=str(path.relative_to(ROOT))
  assert not any(p.startswith('exploratory')for p in Path(key).parts),key
  actual=sha(path);assert digest is None or actual==digest,(key,actual,digest)
  if key in pins:assert pins[key]==actual
  pins[key]=actual;return actual
 prior_path=ROOT/'analysis/phase17/verification.json';prior=read(prior_path);assert prior['status']=='passed'
 assert sha(prior_path)=='0b54e3a00dec6307fe41ce93ab42f6227f0b6929ce8c0a12658923f4d49d6b8c'
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for name,digest in prior[group].items():pin(name,digest);checked['unchanged_phase17_dependency_pins']+=1
 pin(prior_path)
 oldarchive=ROOT/'build/三国志2超级版-逆向分析-v17.zip'
 assert sha(oldarchive)=='78c7d6476fec1b3cdfb0f54b1ee2e0dea18671fb7a936d310a3f58c54f06f40b'
 control=read(OUT/'control/control-contracts.json');cv=read(OUT/'control/verification.json')
 assert control['corrected_instruction_count']==48754 and control['original_dispatch_table_count']==102
 assert control['prior_inline_dispatch_barriers_resolved']==99 and len(control['removed_table_instruction_positions'])==1
 assert Counter(r['kind']for r in control['remaining_context_barriers'])==Counter(dispatcher_body_requires_actual_returnword_or_far_context=4,fixed_body_requires_actual_mapper_context=54)
 assert cv['status']=='passed'and cv['original_CPU_dispatch_destination_case_count']==775 and len(cv['rows'])==775
 assert all(r['boundary']=='original_computed_dispatch_destination'and not r['actual_caller_RTS']for r in cv['rows'])
 for name,digest in control['source_and_artifact_sha256'].items():pin(name,digest)
 for name,digest in cv['dependencies_sha256'].items():pin(name,digest)
 static=read(OUT/'fields-static/analysis-summary.json');access=read(OUT/'fields-static/access-contracts.json')
 assert static['instruction_count']==48754 and len(access['accesses'])==589
 assert static['finite_refinement_round_count']==8 and not static['fixed_point_proven']
 pin(static['analyzer_path'],static['analyzer_sha256'])
 for name,digest in static['artifact_sha256'].items():pin(name,digest)
 assert Counter(r['classification']for r in access['accesses'])==static['classification_counts']==access['classification_counts']
 for r in access['accesses']:
  if r['classification']=='proved_disjoint_auxiliary_address_domain':assert r['address_contract']['auxiliary_address_intersection_count']==0
 all_access=read(OUT/'fields-static/all-indirect-accesses.json');new_access=read(OUT/'fields-static/new-indirect-accesses.json')
 assert len(all_access['accesses'])==all_access['indirect_access_count']==static['all_indirect_access_count']==1526
 assert len(new_access['accesses'])==new_access['new_indirect_access_count']==static['new_indirect_access_count']==45
 assert new_access['phase17_indirect_access_count']==1481 and new_access['phase18_indirect_access_count']==1526
 assert Counter(r['classification']for r in all_access['accesses'])==all_access['classification_counts']==static['all_indirect_classification_counts']
 assert sum(r['classification']!='proved_disjoint_auxiliary_address_domain'for r in new_access['accesses'])==new_access['new_possible_auxiliary_alias_count']==static['new_possible_auxiliary_alias_count']
 for row in all_access['accesses']:
  blob=bytes.fromhex(row['raw_hex']);assert row['rom_offset']==16+row['physical_bank']*8192+(row['cpu']&8191)
  assert rom[row['rom_offset']:row['rom_offset']+len(blob)]==blob
 source=read(OUT/'services/validation.json');integration=read(OUT/'source-integration.json')
 assert source['status']==integration['status']=='passed'
 assert not source['quick']and source['failed_count']==0 and source['rom_cpu_case_count']==len(source['cases'])
 assert source['rom_cpu_case_count']==source['complete_return_count']+source['strict_prefix_count']
 assert source['source_guard_case_count']==len(source['guards'])and all(g['status']=='passed'for g in source['guards'])
 assert source['source_original_CPU_callbacks']==0 and not source['production_IR_interpretation']
 for row in source['cases']:assert row['all_RAM_byte_count']==2048 and row['all_SRAM_byte_count']==8192
 for name,digest in source['source_sha256'].items():pin(name,digest)
 se=read(OUT/'services/evidence.json');cat=read(OUT/'services/static-catalog.json')
 assert se['rom_sha256']==cat['rom_sha256']==SHA
 assert se['validation']['sha256']==sha(OUT/'services/validation.json')
 assert se['byte_catalog']['sha256']==sha(OUT/'services/static-catalog.json')
 for name,digest in se['source_sha256'].items():pin(name,digest)
 for name,digest in se['artifact_sha256'].items():pin(name,digest)
 for key in('rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count'):assert se['validation'][key]==source[key]
 for row in cat['instructions']:
  raw=bytes.fromhex(row['raw_hex']);assert row['file']==16+row['bank']*8192+(row['pc']&8191)
  assert rom[row['file']:row['file']+len(raw)]==raw;checked['new_source_static_original_instructions']+=1
 for row in cat['original_ranges']:
  raw=bytes.fromhex(row['raw_hex']);assert rom[row['rom_offset']:row['rom_offset']+len(raw)]==raw
  assert hashlib.sha256(raw).hexdigest()==row['sha256']
 static_keys={(r['bank'],r['pc'])for r in cat['instructions']};dynamic_keys={(r['physical_bank'],r['cpu_address'])for r in source['executed_instruction_positions']}
 coverage=dict(static_new_body_instruction_positions=len(static_keys),dynamically_executed_new_body_positions=len(static_keys&dynamic_keys),not_dynamic=len(static_keys-dynamic_keys),static_byte_pin_is_not_dynamic_path_validation=True)
 assert coverage==se['coverage']and (len(static_keys),len(static_keys&dynamic_keys),len(static_keys-dynamic_keys))==(739,267,472)
 assert Counter(c['comparison']for c in source['cases'])==Counter(complete_return=191,strict_prefix=1)
 for row in source['cases']:
  assert row['pure_source_CPU_callbacks']==0
  assert row['source_status']==('returned'if row['comparison']=='complete_return'else'dependency')
 assert integration['rom_cpu_sequence_count']==2 and integration['actual_caller_RTS_count']==0
 assert integration['source_original_CPU_callbacks']==0 and not integration['source_IR_interpretation']and not integration['original_Native_internal_CPU_trace']
 for row in integration['rows']:
  assert row['completion_kind']=='main_E066_and_actual_NMI_IRQ_RTI_sequence'and row['main_updates']==2
  assert row['RAM_bytes']==2048 and row['SRAM_bytes']==8192 and all(e['all_RAM_SRAM_registers_IO_banks_N163_equal']for e in row['events'])
 for name,digest in integration['source_sha256'].items():pin(name,digest)
 for name,digest in integration['artifact_sha256'].items():pin(name,digest)
 runtime=read(OUT/'runtime/validation.json');evidence=read(OUT/'runtime/evidence.json');assert runtime['status']==evidence['status']=='passed'
 assert runtime['rom_sha256']==evidence['rom_sha256']==SHA and runtime['evidence_sha256']==sha(OUT/'runtime/evidence.json')
 assert all(runtime[k]==v for k,v in evidence['summary'].items())
 for p in evidence['dependency_pins']:pin(p['path'],p['sha256'])
 cases={p.name:p for p in(OUT/'runtime').iterdir()if p.is_dir()and(p/'validation.json').is_file()}
 assert set(cases)=={'city-menu-baseline','city-menu-byte1-44','city-menu-tail-markers','ai-reinforce-byte1-0','ai-reinforce-byte1-44'}
 native_cases={c['case']:c for c in evidence['native_cases']};assert set(native_cases)==set(cases)
 total=0;points=0;native_totals=Counter()
 for case_name,folder in sorted(cases.items()):
  r=read(folder/'validation.json');repeat=read(folder/'repeat-validation.json');assert r['status']==repeat['status']=='passed'
  assert r['case']==case_name and r['rom_sha256']==SHA and not r['rom_modified']
  case=native_cases[case_name]
  for key,filename in(('validation','validation.json'),('repeat_validation','repeat-validation.json'),('checkpoints','checkpoints.json'),('frame_services','frame-services.json'),('input_plan','input-plan.json'),('preparation_file','preparation.json')):assert case[key]==case_name+'/'+filename
  assert case['folder']==case_name and case['full_WAV']==case_name+'/full-audio.wav'
  assert case['full_audio']==dict(r['full_audio'],path=case_name+'/full-audio.wav')
  for key in('frames','checkpoint_count','mother_state','mother_sha256','preparation','preparation_groups','verified_effects','final_fields','termination'):assert case[key]==r[key]
  rows=read(folder/'frame-services.json');ps=read(folder/'checkpoints.json');assert len(rows)==r['frames']and len(ps)==r['checkpoint_count'];total+=len(rows);points+=len(ps)
  assert r['fresh_process_per_run']and r['state_imported']and not r['cold_boot']and not r['battery_file_imported']
  assert not r['native_internal_CPU_trace']and not r['source_pipeline_installed']and r['source_CPU_comparisons']==0
  assert r['all_frames_original_RGB_PCM_RAM_SRAM_hashed']and r['all_frames_whole_serialized_buffer_hashed']and not r['serialized_buffer_normalized']
  assert r['additional_core_memory_writes']==len(r['preparation'])and r['additional_core_memory_writes_after_declared_preparation']==0
  assert r['additional_ready_or_result_injections']==0 and not r['controller_pointer_request_RNG_weights_prepared']
  assert r['controlled_fixture']==bool(r['preparation'])and r['natural_gameplay']==(not bool(r['preparation']))
  assert r['inherited_context']['inherited_preparation_byte_writes']==0 and not r['inherited_context']['applied_in_this_run']and r['inherited_context']['natural_parent']
  assert (folder/'initial.state').read_bytes()==(ROOT/r['mother_state']).read_bytes();pin(ROOT/r['mother_state'],r['mother_sha256'])
  assert sha(folder/'initial-ram.bin')==r['initial_RAM_sha256']and sha(folder/'initial-sram.bin')==r['initial_SRAM_sha256']
  assert repeat['all_hashes_equal']and repeat['whole_serialized_buffers_exact']
  assert ROOT/repeat['first_run']==folder
  second=ROOT/repeat['second_run'];second_r=read(second/'validation.json');assert second_r['status']=='passed'
  repeated={a['artifact']:a for a in repeat['artifacts']}
  assert len(repeated)==len(repeat['artifacts'])==repeat['nonempty_artifact_checks']
  assert set(repeated)==set(r['artifact_sha256'])==set(second_r['artifact_sha256'])
  assert r['artifact_sha256']==second_r['artifact_sha256']
  assert repeat['formal_JSON_exact_parity']==r['formal_JSON']==second_r['formal_JSON']
  assert set(r['formal_JSON'])<=set(repeated)and len(r['formal_JSON'])==11
  for key in('excluded_empty_VRAM','excluded_snapshot_metadata_JSON'):
   assert repeat[key]==r[key]==second_r[key]and len(r[key])==len(ps)and not(set(r[key])&set(repeated))
   for filename in r[key]:
    assert (folder/filename).is_file()and(second/filename).is_file()
    if key=='excluded_empty_VRAM':assert (folder/filename).stat().st_size==(second/filename).stat().st_size==0
  for artifact in repeat['artifacts']:
   name=artifact['artifact'];left,right=folder/name,second/name
   assert artifact['equal']and r['artifact_sha256'][name]==dict(bytes=artifact['bytes'],sha256=artifact['sha256'])
   assert left.stat().st_size==right.stat().st_size==artifact['bytes']>0
   assert pin(left,artifact['sha256'])==pin(right,artifact['sha256']);checked['native_double_full_artifacts']+=1
  native_totals['formal_JSON']+=len(r['formal_JSON']);native_totals['writes']+=len(r['preparation'])
  native_totals['empty_VRAM']+=len(r['excluded_empty_VRAM']);native_totals['metadata_JSON']+=len(r['excluded_snapshot_metadata_JSON'])
  assert [w for g in r['preparation_groups']for w in g['writes']]==r['preparation']
  allowed_preparation={
   'city-menu-baseline':{},'city-menu-byte1-44':{0x6161:(0,44)},
   'city-menu-tail-markers':{0x617C:(0,0x12),0x617D:(0,0x34),0x617E:(0,0x56),0x617F:(0,0x78)},
   'ai-reinforce-byte1-0':{0x6082:(32,1),0x6083:(37,1),0x6B9C:(232,132)},
   'ai-reinforce-byte1-44':{0x6082:(32,1),0x6083:(37,1),0x6B9C:(232,132),0x6081:(0,44)}}[case_name]
  assert {w['address']:(w['before'],w['after'])for w in r['preparation']}==allowed_preparation
  assert all(w['frame']==0 and w['kind']=='SRAM'for w in r['preparation'])
  for g in r['preparation_groups']:
   for kind,base,size in(('RAM',0,2048),('SRAM',0x6000,8192)):
    before=bytearray((folder/g['before'][kind]['path']).read_bytes());after=(folder/g['after'][kind]['path']).read_bytes()
    assert len(before)==len(after)==size
    assert g['before'][kind]['bytes']==g['after'][kind]['bytes']==size
    pin(folder/g['before'][kind]['path'],g['before'][kind]['sha256']);pin(folder/g['after'][kind]['path'],g['after'][kind]['sha256'])
    for change in g['writes']:
     if change['kind']==kind:assert before[change['address']-base]==change['before'];before[change['address']-base]=change['after']
    assert bytes(before)==after
   checked['full_preparation_reconstruction']+=1
  pcm_path=folder/'full-audio.wav'
  with wave.open(str(pcm_path),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000);sample_frames=w.getnframes();pcm=w.readframes(sample_frames)
  audio=r['full_audio'];assert audio['path']=='full-audio.wav'and audio['sample_rate']==48000
  assert audio['stereo_sample_frames']==sample_frames and audio['PCM_bytes']==len(pcm)==sample_frames*4
  assert audio['PCM_sha256']==hashlib.sha256(pcm).hexdigest()and audio['WAV_sha256']==sha(pcm_path)
  native_totals['sample_frames']+=sample_frames;native_totals['WAVs']+=1
  callbacks=read(folder/'audio-callbacks.json');assert len(callbacks)==len(rows)
  cursor=0
  for i,row in enumerate(rows):
   assert row['frame']==i+1 and len(row['all30_city_auxiliary_bytes'])==30 and all(len(x)==5 for x in row['all30_city_auxiliary_bytes'])
   assert len(row['all30_city_rosters'])==30 and all(len(x)==10 for x in row['all30_city_rosters'])
   cityraw=bytes.fromhex(row['all30_city_records_raw32']);assert len(cityraw)==960
   assert row['all30_city_auxiliary_bytes']==[[cityraw[32*c+k]for k in(1,28,29,30,31)]for c in range(30)]
   assert row['all30_city_owners']==[cityraw[32*c]&7 for c in range(30)]
   assert row['all30_city_rosters']==[list(cityraw[32*c+17:32*c+27])for c in range(30)]
   for key,offset in(('all30_city_gold',2),('all30_city_reserve',12)):assert row[key]==[int.from_bytes(cityraw[32*c+offset:32*c+offset+2],'little')for c in range(30)]
   for officer_id,officer in row['observed_officers'].items():
    raw=bytes.fromhex(officer['raw']);assert len(raw)==12 and officer['health']==raw[0]and officer['status']==raw[11]&3 and officer['troops_raw16']==int.from_bytes(raw[8:10],'little')
   assert callbacks[i]==dict(emulated_frame_start=i,stereo_sample_frames=row['PCM_stereo_sample_frames'],pcm_sha256=row['PCM_sha256'])
   assert len(row['whole_serialized_state_sha256'])==64 and all(c in'0123456789abcdef'for c in row['whole_serialized_state_sha256'])
   n=row['PCM_stereo_sample_frames']*4;part=pcm[cursor:cursor+n];cursor+=n;assert len(part)==n and row['PCM_stop_byte']==cursor
   assert hashlib.sha256(part).hexdigest()==row['PCM_sha256'];checked['native_frame_PCM_slices']+=1
  assert cursor==len(pcm)
  assert case['images']=={p['label']:case_name+'/'+p['image']for p in ps}
  for p in ps:
   row=rows[p['frame']-1]
   with Image.open(folder/p['image'])as im:assert im.size==(256,240)and hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   assert sha(folder/p['RAM'])==row['RAM_sha256']and(folder/p['RAM']).stat().st_size==2048
   assert sha(folder/p['SRAM'])==row['SRAM_sha256']and(folder/p['SRAM']).stat().st_size==8192
   ram=(folder/p['RAM']).read_bytes();sram=(folder/p['SRAM']).read_bytes()
   assert row['all30_city_records_raw32']==sram[:960].hex()
   for officer_id,officer in row['observed_officers'].items():assert bytes.fromhex(officer['raw'])==sram[0x3C0+12*int(officer_id):0x3C0+12*(int(officer_id)+1)]
   assert row['global_state']==ram[0x7A]and row['nmi_scene']==ram[0x78]and row['calendar_and_turn_6F00_6F06']==list(sram[0xF00:0xF07])
   assert row['domestic_control_6F5B_6F62']==list(sram[0xF5B:0xF63])and row['cooperation_status_6F8B']==sram[0xF8B]
   assert all(p['fields'][key]==row[key]for key in p['fields'])
   assert sha(folder/p['state'])==row['whole_serialized_state_sha256'];checked['checkpoint_full_buffers']+=1
 assert total==6713 and points==113
 assert checked['native_double_full_artifacts']==runtime['nonempty_repeat_artifact_checks']==547
 assert native_totals==Counter(formal_JSON=55,writes=12,empty_VRAM=113,metadata_JSON=113,sample_frames=5361570,WAVs=5)
 for key,value in(('frames_first_run',total),('frames_both_runs',2*total),('checkpoint_count',points),('whole_serialized_hash_frames',total),('formal_JSON_repeat_checks',native_totals['formal_JSON']),('additional_core_memory_writes',native_totals['writes']),('excluded_empty_VRAM',native_totals['empty_VRAM']),('excluded_snapshot_metadata_JSON',native_totals['metadata_JSON']),('PCM_stereo_sample_frames_first_run',native_totals['sample_frames']),('actual_full_WAV_count',native_totals['WAVs'])):assert runtime[key]==value
 browser=read(OUT/'browser-validation.json');bs=read(OUT/'browser-static-check.json')
 assert browser['status']==bs['status']=='passed'and browser['HTML_sha256']==bs['HTML_sha256']==sha(OUT/'index.html')
 assert browser['source_files_checked']==2 and browser['native_cases_checked']==5
 assert len(browser['sources'])==2 and all(row['exact_UTF8']for row in browser['sources'])
 for row in browser['sources']:pin('source/recovered/'+row['filename'],row['SHA256'])
 assert len(browser['native'])==len(browser['audio'])==5 and not browser['console_logs']
 assert all(row['all_field_values_exact']and row['two_checkpoints_full_raw_exact']and row['original_PNG_pair_exact']and row['field_count']==20 for row in browser['native'])
 for row in browser['audio']:
  audio=read(OUT/'runtime'/row['case']/'validation.json')['full_audio']
  assert row['WAV_sha256']==audio['WAV_sha256']and row['original_PCM_duration_exact']
  assert abs(row['after']['duration']-audio['stereo_sample_frames']/48000)<0.00001 and row['after']['currentTime']>0
 screenshot=browser['screenshot'];pin(screenshot['path'],screenshot['sha256'])
 assert screenshot['format']=='JPEG'and screenshot['unaltered_API_bytes']
 with Image.open(ROOT/screenshot['path'])as im:assert im.format=='JPEG'
 assert browser['frame_input'][0]['fractional_input_rejected']and browser['frame_input'][0]['old_table_and_PNG_preserved']
 for name,digest in bs['dependency_pins'].items():pin(name,digest)
 # The whole new formal tree is pinned, rather than guessing every producer's
 # schema-specific alias. Historical provenance locations are data, not pins.
 for p in OUT.rglob('*'):
  if p.is_file()and p.name not in('verification.json','package-receipt.json')and '__pycache__'not in p.parts and not any(x.startswith('exploratory')for x in p.parts):pin(p)
 for p in(ROOT/'scripts').glob('*phase18*.py'):pin(p)
 for n in('analyze_city_control_reachability.py','verify_city_control_reachability.py','analyze_city_auxiliary_accesses.py','analyze_city_auxiliary_services.py','trace_city_auxiliary_fields.py','capture_city_auxiliary_fields.py','verify_city_auxiliary_services.py'):pin('scripts/'+n)
 for n in('city_auxiliary_services.py','city_auxiliary_integration.py'):pin('source/recovered/'+n)
 result=dict(schema='phase18-city-auxiliary-evidence-aggregate-v1',status='passed',ROM_sha256=SHA,rebuilt_byte_identical=True,
  source_and_validator_sha256={n:d for n,d in sorted(pins.items())if n.startswith(('scripts/','source/'))},
  artifact_and_dependency_sha256={n:d for n,d in sorted(pins.items())if not n.startswith(('scripts/','source/'))},
  old_phase17_verification_sha256=sha(prior_path),old_v17_preserved_sha256=sha(oldarchive),checks=dict(checked),
  control=dict(instruction_positions=48754,inline_tables=102,original_CPU_dispatch_destination_cases=775,actual_caller_RTS=0),
  field_access_classification=static['classification_counts'],old_candidate_count=589,
  all_indirect_access_count=1526,new_indirect_access_count=45,new_indirect_possible_auxiliary_alias_count=static['new_possible_auxiliary_alias_count'],
  finite_static_refinement_rounds=8,static_fixed_point_proven=False,
  source_receipt_path='analysis/phase18/services/validation.json',source_counts={k:v for k,v in source.items()if isinstance(v,int)and(k.endswith('count')or k.endswith('cases'))},
  new_source_coverage=coverage,
  integration=dict(rom_cpu_sequences=2,main_updates_per_sequence=2,actual_caller_RTS=0,scope=integration['comparison']),
  native=dict(case_count=5,frames_first_run=total,frames_both_runs=2*total,checkpoints=points),browser_status='passed',
  field_semantics=dict(byte1_official_name=None,tail28_31_official_names=None,actual_AI_word='city[1] | city[2]<<8',actual_AI_gate=300,tail_padding_or_unused_proved=False),
  limitations=['589 original candidates remain individually classified; unresolved pointers are not evidence of unused fields.','City+1 changes real recruitment eligibility; no proven official field label.','Tail markers do not change the bounded menu cycle; other reachability remains open.','Native frame-end memory and media are distinct from the explicitly timed independent CPU software traces.','All phase17 source/evidence dependencies and versioned ZIP remain unchanged.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','field_access_classification','native','browser_status')},ensure_ascii=False))
if __name__=='__main__':main()
