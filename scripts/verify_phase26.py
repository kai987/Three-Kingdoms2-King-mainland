#!/usr/bin/env python3
"""Read-only phase26 evidence audit. Only the new verification.json is written.

No CPU, emulator, capture, analyzer or historical producer is executed.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys,wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase26';sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('readonly_phase25_audit',ROOT/'scripts/verify_phase25.py')
base=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=base;SPEC.loader.exec_module(base)
from capture_native_deployment_pointer import decode_event,fields,PLAN,MOTHER,CORE_SHA,OBSERVER_SHA
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=base.ROM_SHA;sha=base.sha;read=base.read;original=base.original;DISJOINT=base.DISJOINT;Pending=base.Pending
OLD_AUDIT='0d86bd6ac30879bb2fd03bc0135aec70fcac3c05a99b98e494f98c0de4ec78af'
OLD_ZIP='aeb015ef87f34c4ca6db6921cbec717e287881ff0e995aa7aa07e81cb7c9c565'
OLD_POSTZIP='2ccdfcc76edb145a888c3689650110ccf347f640c3b3d61582d4f1606b533f20'
V22_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(path):return str(Path(path).resolve().relative_to(ROOT))

class Audit(base.Audit):
 def frozen_history(self):
  self.pin('analysis/phase25/verification.json',OLD_AUDIT);v=read(ROOT/'analysis/phase25/verification.json')
  assert v['status']=='passed'and v['pending']==[]and v['ROM_sha256']==ROM_SHA and v['rebuilt_byte_identical']
  assert(len(v['source_and_validator_sha256']),len(v['artifact_and_dependency_sha256']))==(511,42522)
  self.frozen_names=set(v['source_and_validator_sha256'])|set(v['artifact_and_dependency_sha256'])
  for name,pin in v['source_and_validator_sha256'].items():self.pin(name,pin);self.sources[name]=pin
  for name,pin in v['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  self.pin('analysis/phase25/package-receipt.json',OLD_POSTZIP);p=read(ROOT/'analysis/phase25/package-receipt.json')
  assert p['status']=='passed'and p['phase25_audit_sha256']==OLD_AUDIT and p['sha256']==OLD_ZIP and p['file_count']==2690
  self.pin('build/三国志2超级版-逆向分析-v25增量.zip',OLD_ZIP)
  assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.pin('build/三国志2超级版-逆向分析.zip',V22_ZIP)
  self.counts.update(unchanged_phase25_source_script_pins=511,unchanged_phase25_artifact_dependency_pins=42522,unchanged_phase25_postZIP_receipts=1)

 def ancestry(self,ancestor):
  for value in ancestor.values():
   if isinstance(value,dict)and 'path'in value and 'sha256'in value:self.pin(value['path'],value['sha256'])
  parent=read(ROOT/ancestor['parent_validation']['path']);point=ancestor['parent_checkpoint']
  assert parent['natural_gameplay']and not parent['controlled_fixture']and parent['initial_state']is None
  assert parent['inherited_preparation']=={}and parent['preparation_reference']is None and parent['additional_core_memory_writes']==parent['additional_ready_or_result_injections']==0
  assert parent['artifact_sha256'][MOTHER.name]['sha256']==sha(MOTHER)and parent['script_sha256']==ancestor['parent_producer']['sha256']
  assert point in read(ROOT/ancestor['parent_checkpoints']['path'])and point['frame']==5626 and point['state']==MOTHER.name
  assert ancestor['ancestor_cold_boot']and not ancestor['ancestor_state_imported']and ancestor['ancestor_numeric_preparation_bytes']==0
  assert ancestor['new_case_state_imported']and not ancestor['new_case_cold_boot']

 def runtime(self):
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json')
  assert e['summary']=={k:v[k]for k in e['summary']};self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_deployment_pointer.py',v['script_sha256'])
  expected=dict(natural_routes=1,core_variants=2,fresh_process_runs=4,original_first_frames=160,all_control_frames=640,original_checkpoints=160,nonempty_artifact_repeat_checks=1316,PNG_checks=320,WAV_checks=2,observer_events=25114,full_software_snapshots=3,logical_coordinate_reads=8,city_auxiliary_bus_events=0,additional_core_memory_writes=0,ancestor_preparation_bytes=0,cold_boots=0,state_imports=4,Source_CPU_cases=0,failed_count=0)
  assert all(v[k]==value for k,value in expected.items())
  assert v['all_five_complete_buffers_equal_each_frame']and v['all_complete_initial_API_buffers_equal']and v['all_artifacts_repeat_exact']and v['full_serialized_buffers_not_normalized']
  self.ancestry(e['ancestry']);self.pin(MOTHER,e['mother']['sha256']);m=NestopiaContext.parse(MOTHER.read_bytes());original_rows=None;artifacts=images=wavs=0
  for variant,core_sha in(('original-control',CORE_SHA),('observer',OBSERVER_SHA)):
   first=folder/variant;second=OUT/'runtime-repeat'/variant;a=self.record(first/'validation.json');b=self.record(second/'validation.json');repeat=self.record(first/'repeat-validation.json');assert a==b
   assert a['core']['core_sha256']==core_sha and a['frames']==a['checkpoint_count']==160 and a['state_imported']and not a['cold_boot']and a['natural_ordinary_input_route']
   assert a['additional_core_memory_writes']==a['inherited_preparation_byte_writes']==a['Source_CPU_cases']==0 and not a['original_core_internal_CPU_trace']
   self.ancestry(a['ancestry']);prep=self.record(first/'preparation.json',False);assert prep['preparation']==[]and prep['additional_core_memory_writes']==prep['inherited_preparation_byte_writes']==0 and prep['ancestry']==e['ancestry']
   assert repeat['all_bytes_exact']and repeat['artifact_checks']==len(a['artifact_sha256'])
   n=NestopiaContext.parse((first/'initial.state').read_bytes());assert(n.ram,n.sram,n.registers,n.prg_banks)==(m.ram,m.sram,m.registers,m.prg_banks)
   assert(first/'initial-ram.bin').read_bytes()==m.ram and(first/'initial-sram.bin').read_bytes()==m.sram
   for name,pin in a['artifact_sha256'].items():
    assert pin['bytes']>0
    for path in(first/name,second/name):assert path.stat().st_size==pin['bytes'];self.pin(path,pin['sha256'])
    artifacts+=1
   rows=read(first/'frame-services.json');points=read(first/'checkpoints.json');callbacks=read(first/'audio-callbacks.json');plan=read(first/'input-plan.json')
   assert len(rows)==len(points)==len(callbacks)==160 and[(p['frames'],tuple(p['buttons']),p['label'])for p in plan]==PLAN
   if original_rows is None:original_rows=rows
   assert rows==original_rows
   with wave.open(str(first/'full-audio.wav'))as wav:
    assert(wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
    for row,point,cb in zip(rows,points,callbacks):
     i=row['frame'];assert i==point['frame']==cb['emulated_frame_start']+1
     pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']and wav.tell()*4==row['PCM_stop_byte']
     r=(first/point['RAM']).read_bytes();s=(first/point['SRAM']).read_bytes();state=(first/point['state']).read_bytes();n=NestopiaContext.parse(state)
     assert len(r)==2048 and len(s)==8192 and digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']
     assert(n.ram,n.sram,n.registers,list(n.prg_banks))==(r,s,row['actual_saved_CPU_registers'],row['actual_saved_PRG_banks'])
     assert all(row[k]==value for k,value in fields(r,s).items())and all(row[k]==value for k,value in point['fields'].items())
     for key in('RAM','SRAM','state','image'):assert(first/point[key]).read_bytes()==(folder/'original-control'/point[key]).read_bytes()
     with Image.open(first/point['image'])as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
     images+=1
    assert not wav.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and wav.tell()*4==a['full_audio']['PCM_bytes'];wavs+=1
   for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):assert(first/name).read_bytes()==(folder/'original-control'/name).read_bytes()
   assert a['final_fields']['global_007A']==4 and a['final_fields']['NMI_0078']==3 and a['final_fields']['battle_0500_0501']==[10,4]
  assert(artifacts,images,wavs)==(1316,320,2);self.observer(folder/'observer');self.core_provenance()
  self.counts.update({f'Native_{k}':value for k,value in expected.items()})

 def observer(self,folder):
  events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()));raw=(folder/'bus-events.bin').read_bytes();assert len(events)==25114 and len(raw)==len(events)*176
  for i,e in enumerate(events,1):
   assert decode_event(raw[(i-1)*176:i*176],sequence=i)==e
   if e['opcode_PC']is not None and e['opcode_PC']>=0x8000:assert e['physical_bank']==e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]and e['rom_offset']==original(e['physical_bank'],e['opcode_PC'])
   if e['data_ROM_offset']is not None:assert e['value']==self.rom[e['data_ROM_offset']]and e['data_physical_bank']==e['actual_PRG_banks'][(e['address']-0x8000)//8192]
   if e['target_type']=='pointer_scratch_RAM_write':assert e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
  assert not any(e['target_type']=='city_auxiliary_bus'for e in events)
  words=[e for e in events if e['kind']in('word_read_low','word_read_high')];assert len(words)==8 and all(e['data_physical_bank']==8 for e in words)
  schema=self.record(folder/'event-schema.json',False);assert len(schema['raw_layout'])==schema['words']==44 and schema['bytes_per_record']==176
  snapshots=(folder/'snapshots.bin').read_bytes();index=list(map(json.loads,(folder/'snapshot-index.jsonl').read_text().splitlines()));by_sequence={e['sequence']:e for e in events}
  assert len(index)==3 and len(snapshots)==30720 and[e['entry']for e in index]==[0xB130,0xB1B0,0xB2AE]
  for i,item in enumerate(index,1):
   e=by_sequence[item['event_sequence']];payload=snapshots[(i-1)*10240:i*10240];r,s=payload[:2048],payload[2048:]
   assert item['snapshot_sequence']==e['full_snapshot_sequence']==i and item['frame']==e['frame']==139 and item['physical_bank']==e['physical_bank']==8
   assert digest(payload)==item['sha256']and digest(r)==item['RAM_sha256']and digest(s)==item['SRAM_sha256']and list(r[:0x30])==e['ZP_0000_002F']
   assert e['scratch_0053_0054']==list(r[0x53:0x55])and e['battle_setup_0506_0507_050E_052A']==[r[x]for x in(0x506,0x507,0x50E,0x52A)]
   assert(e['raw_bank_selector_DE'],e['raw_bank_selector_DF'],e['strategy_side_6F91'],e['noncommander_count_6F94'])==(r[0xDE],r[0xDF],s[0xF91],s[0xF94])and e['profile_counts_6F99_6FA0']==list(s[0xF99:0xFA1])
   assert item['actual_registers']==dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC'])and item['actual_PRG_banks']==e['actual_PRG_banks']==[1,8,9,31]
   assert not item['instantaneous_N163_PPU_APU_captured']and item['capture_core_sha256']==OBSERVER_SHA and item['additional_core_memory_writes']==item['inherited_preparation_byte_writes']==0
   assert(folder/item['exported_RAM']).read_bytes()==r and(folder/item['exported_SRAM']).read_bytes()==s
  observation=self.record(OUT/'runtime/deployment-observations.json',False);logical=[e for e in events if e['logical_coordinate_read']]
  assert logical==observation['logical_coordinate_reads']and len(logical)==8 and observation['untaken_formation_entries']==[0xB312]
  assert all(e['frame']==139 and e['data_physical_bank']==6 and e['pointer_0020_0021']==0x8D4E and e['address']==0x8D4E+e['Y']for e in logical)
  assert[(e['Y'],e['value'])for e in logical]==[(0,14),(1,20),(8,17),(9,17),(12,14),(13,19),(14,13),(15,20)]
  assert len(observation['logical_read_to_unit_store_pairs'])==8
  for pair in observation['logical_read_to_unit_store_pairs']:
   r,w=pair['logical_read'],pair['following_original_store'];assert r==by_sequence[r['sequence']]and w==by_sequence[w['sequence']]and w['sequence']>r['sequence']and w['value']==r['value']
   assert w['address']==(0x614 if r['opcode_PC']in(0xB272,0xB290)else 0x600)+r['X']and w['kind']=='write_attempt'
  self.counts.update(Native_raw_word_events_mapped=8,Native_logical_coordinate_read_to_real_store_pairs=8,Native_instantaneous_N163_captures=0)

 def core_provenance(self):
  folder=OUT/'runtime/core-provenance';v=self.record(folder/'build.json',False);assert v['commit']=='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
  assert v['first_build_clean_new_tree']and v['final_source_clean_build']and v['dependency_rebuild_byte_identical']and not v['modified_emulator_object_layout']and v['extra_emulated_bus_reads']==v['extra_emulated_bus_writes']==0
  for item in[v['original_core'],v['passive_observer'],v['parent_frozen_patch']]+v['unchanged_old_observers']:self.pin(item['path'],item['sha256'])
  assert v['original_core']['sha256']==CORE_SHA and v['passive_observer']['sha256']==OBSERVER_SHA
  patch=(folder/'observer.patch').read_bytes();assert digest(patch)==v['patch_sha256'];originals={x['path']:(folder/'upstream'/x['path']).read_bytes()for x in v['source_files']};generated=base.prior.apply_patch_readonly(patch,originals)
  for item in v['source_files']:assert digest(originals[item['path']])==item['original_sha256']and digest(generated[item['path']])==item['patched_sha256']
  for path in(folder/'patched').rglob('*'):
   if path.is_file():assert path.read_bytes()==generated[str(path.relative_to(folder/'patched'))]
  watch=generated['source/core/NstWatch.cpp.inc'].decode();board=generated['source/core/board/NstBoard.cpp'].decode();make=generated['libretro/Makefile'].decode()
  assert 'map.Peek'not in watch and 'map.Poke'not in watch and 'out[i]=b.wrk[0][i]'in board and 'e[17]=source[5];'in watch
  assert 'memory[0xDE]'in watch and 'memory[0xDF]'in watch and '++watch_overflow'in watch and '++watch_snapshot_overflow'in watch and v['include_dependency_declared']in make
  assert generated['source/core/NstCpu.hpp']==originals['source/core/NstCpu.hpp']
  self.counts['observer_upstream_source_files_patch_reconstructed_readonly']=len(originals)

 def source_cases(self):
  v=self.record(OUT/'deployment/validation.json');e=self.record(OUT/'deployment/evidence.json');c=self.record(OUT/'deployment/static-catalog.json',False)
  if v['quick']:raise Pending('Child Source still quick')
  assert v['failed_count']==0 and v['failures']==[]and v['original_CPU_parent_cases']==len(v['cases'])==2009 and Counter(x['comparison']for x in v['cases'])==v['counts']==dict(actual_caller_RTS=2007,strict_missing_dependency_prefix=2)
  assert v['source_guard_count']==len(v['guards'])==7 and all(x['status']=='passed'for x in v['guards'])and v['source_original_CPU_callbacks']==0 and not v['production_IR_interpretation']and not v['Native_internal_CPU_trace']
  assert not e['new_semantic_first_recovery']and e['inherited_B1B0_unchanged']and e['refactored_prior_generated_instruction_positions']==c['refactored_prior_generated_positions']==92 and e['refactored_prior_generated_bytes']==c['refactored_prior_generated_bytes']==187
  visited={(x['physical_bank'],x['cpu_address'])for x in v['executed_instruction_positions']}
  for row in c['original_instructions']:
   bank=row.get('physical_bank',row.get('bank'));pc=row.get('cpu',row.get('pc'));self.raw(dict(row,physical_bank=bank,cpu=pc));assert(bank,pc)in visited
  for row in v['cases']:assert(row['RAM_bytes'],row['SRAM_bytes'])==(2048,8192)and row['AXYP_SP_PC_ordered_IO_four_banks_N163_equal']and row['combined_logical_IO_read_write_interleaving_equal']and row['source_original_CPU_callbacks']==0
  integration=self.record(OUT/'source-integration.json');assert integration['original_CPU_parent_cases']==len(integration['rows'])==48 and integration['inherited_regression_cases']==45 and integration['new_deployment_caller_cases']==3
  assert Counter(x['completion']for x in integration['rows'])==integration['counts']==dict(returned=47,nonlocal_return=1)and integration['guard_count']==len(integration['guards'])==3 and integration['source_original_CPU_callbacks']==0
  assert all(x['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and x['combined_logical_IO_order_equal']and x['source_original_CPU_callbacks']==0 for x in integration['rows'])
  self.actual_contexts()
  for name in('deployment_pointer_services.py','deployment_pointer_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
     names=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module or''];assert not any(any(b in name for b in('py65','state_machine','importlib'))for name in names)
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.counts.update(source_child_CPU_cases=2009,source_child_guards=7,source_integration_CPU_cases=48,source_integration_guards=3,new_Source_CPU_cases=2057,new_Source_guards=10,new_Source_actual_caller_RTS=2054,new_Source_nonlocal_return=1,new_Source_strict_dependency_prefix=2,refactored_previously_named_positions=92,refactored_previously_named_bytes=187,new_semantic_first_recovery=0)

 def actual_contexts(self):
  paths=sorted((OUT/'cpu-deployment/actual-callers').glob('entry-*/context.json'));assert len(paths)==3
  for path in paths:
   row=self.record(path,False);assert row['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and row['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   assert row['prepared_numeric_bytes']==row['additional_CPU_prepared_numeric_bytes']==row['inherited_Native_preparation']==[]and row['injected_new_NMI']==row['injected_new_IRQ']==0 and not row['synthetic_caller_PC_or_stack']
   c=row['passive_capture'];self.pin(c['metadata'],c['metadata_sha256']);meta=read(ROOT/c['metadata']);self.pin(c['manifest'],c['manifest_sha256']);r=(ROOT/c['RAM_path']).read_bytes();s=(ROOT/c['SRAM_path']).read_bytes()
   self.pin(c['RAM_path'],c['RAM_sha256']);self.pin(c['SRAM_path'],c['SRAM_sha256']);assert r==(path.parent/'input-ram.bin').read_bytes()and s==(path.parent/'input-sram.bin').read_bytes()
   assert row['registers']==meta['actual_registers']and row['physical_banks']==meta['actual_PRG_banks']and row['actual_software_state_captured']and not row['unmodified_core_internal_trace']
   sp=row['registers']['sp'];assert row['existing_return_PC']==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535
   fixture=(path.parent/'input-n163.bin').read_bytes();assert len(fixture)==128 and digest(fixture)==row['explicit_N163_fixture']['sha256']and row['N163_address']==127 and row['N163_autoincrement']
  self.counts['actual_passive_software_callee_exports']=3

 def static_fields(self):
  folder=OUT/'fields-static';v=self.record(folder/'verification.json');s=self.record(folder/'analysis-summary.json');self.record(folder/'evidence.json')
  assert v['source_CPU_cases']==s['source_CPU_cases']==0 and v['failed_count']==0 and v['original_contract_CPU_cases']==36443 and(v['actual_caller_RTS_CPU_cases'],v['constructor_prefix_CPU_cases'],v['bare_access_counterexample_prefix_CPU_cases'])==(1624,34816,3)
  old={(x['physical_bank'],x['cpu']):x for x in read(ROOT/'analysis/phase25/fields-static/all-indirect-accesses.json')['accesses']};rows=self.record(folder/'all-indirect-accesses.json',False)['accesses'];assert len(rows)==1526 and{(x['physical_bank'],x['cpu'])for x in rows}==set(old)
  changed=[]
  for row in rows:
   self.raw(row);key=(row['physical_bank'],row['cpu']);p=row['address_contract']
   if p:
    hit=base.prior.prior.old.intersection(p);assert hit==p['possible_auxiliary_effective_addresses']and len(hit)==p['auxiliary_address_intersection_count']
    if row['classification']==DISJOINT:assert not hit
   if row['classification']!=old[key]['classification']:
    changed.append(key);assert row['classification']==DISJOINT
    c=p['required_execution_contract'];assert c['normal_no_interrupt_binary_execution']and c['complete_formation_return_required']and not c['bare_selected_access_entry_covered']and c['all_raw_city_bytes_retained']and c['all_raw_Y_bytes_retained']and c['physical_data_bank_after_complete_formation']==6
   else:assert p==old[key]['address_contract']
  assert set(changed)=={(8,pc)for pc in(0xB272,0xB278,0xB290,0xB296)}and s['previous_candidate_count']==339 and s['remaining_access_count']==335 and s['newly_proved_disjoint_all_count']==4
  assert Counter(x['classification']for x in rows)==s['all_indirect_classification_counts']==dict(proved_disjoint_auxiliary_address_domain=1191,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=254)
  assert len(v['formation_helper_checks'])==1024 and len(v['B1B0_caller_checks'])==600 and sum(x['case_count']for x in v['constructor_prefix_check_groups'])==34816 and len(v['bare_counterexamples'])==3
  for row in v['B1B0_caller_checks']:
   for access in row['observed_accesses']:
    p,y=access['pointer20'],access['Y'];candidate=(p&0xFF00)|((p+y)&255);cross=(p&255)+y>255
    assert access['logical_address']==(p+y)&65535 and access['candidate_not_actual_dummy_address']==candidate and access['page_cross_dummy_read_required']==cross and access['required_dummy_address']==(candidate if cross else None)
  assert all(x is None for x in s['official_target_field_names'].values())and not s['complete_analysis_fixed_point_proven']and v['model_guard_check_count']==len(v['model_checks'])==13 and all(x['passed']for x in v['model_checks'])
  self.counts.update(static_Source_CPU_cases=0,static_original_CPU_contract_cases=36443,static_actual_caller_RTS_contract_cases=1624,static_constructor_prefix_contract_cases=34816,static_bare_prefix_contract_cases=3,static_model_guards=13,static_remaining_candidates=335,static_new_conditional_exclusions=4)

 def context(self):
  folder=OUT/'context';v=self.record(folder/'verification.json');s=self.record(folder/'analysis-summary.json',False);self.record(folder/'evidence.json')
  assert v['Source_CPU_cases']==v['original_CPU_cases']==v['Native_runs']==s['Source_CPU_cases']==s['original_CPU_cases']==s['Native_runs']==0 and v['check_count']==len(v['checks'])==15 and all(x['status']=='passed'for x in v['checks'])
  assert s['focused_group']=='G107'and s['target_access_count']==4 and s['baseline_remaining_candidates']==339 and s['new_exclusions_from_this_context_audit']==0 and s['unknown_unique_services']is None
  for name in('owner-and-caller-chain.json','completion-contracts.json','stable-denominators.json','owner-priority-checks.json','historical-wording-erratum.json','acceptance-delta-framework.json'):self.record(folder/name,False)
  denominator=read(folder/'stable-denominators.json');assert denominator['existing_old_setup_validation']['declared_RAM_bytes']==1972 and denominator['existing_old_setup_validation']['old_CPU_cases']==2326
  self.counts.update(context_reference_checks=15,context_Source_CPU_cases=0,context_original_CPU_cases=0,context_Native_runs=0)

 def acceptance(self):
  folder=OUT/'acceptance';v=self.record(folder/'verification.json');r=self.record(folder/'requirements.json',False);p=self.record(folder/'request-provenance.json',False)
  assert v['source_CPU_cases']==v['original_CPU_cases']==v['Native_frames']==0 and not r['overall_reverse_engineering_complete']and r['completion_percentage']is None
  assert v['direct_user_message_locator_checks']==11 and v['dimension_status_and_receipt_checks']==10 and v['coordinator_report_separately_labelled']
  assert v['evidence_reference_checks']==79 and v['source_syntax_checks']==98 and v['current_summary_cross_receipt_checks']==10
  messages={x['message_id']:x for x in p['source_messages']};locators={x['request_id']:x for x in p['request_locators']};assert len(locators)==11 and len(r['dimensions'])==10
  for user in r['user_request_register']:
   locator=locators[user['id']];message=messages[locator['message_id']];assert user['quote']in message['text']and locator['turn_id']==message['turn_id']and message['source_kind']=='read_thread_userMessage'
   source=user['source'];assert source['source_kind']=='direct_human_userMessage'and source['message_id']==locator['message_id']and source['turn_id']==locator['turn_id']
  assert p['coordination_report']['source_kind']=='coordinator_delegation_report'and p['coordination_report']['not_verbatim_user_quote']
  for row in r['dimensions']:
   assert row['acceptance_status']and row['verified_results']and row['pending_results']and row['phase26_change']['result']and row['phase26_change']['remaining_gap']
   for item in row['verified_results']:assert item['claim']and item['evidence']in row['evidence'];self.pin(item['evidence'])
  self.counts.update(acceptance_dimensions=10,acceptance_exact_user_message_locators=11,acceptance_reference_checks_not_gameplay=v['evidence_reference_checks'],acceptance_Source_syntax_checks_not_CPU=v['source_syntax_checks'],acceptance_Source_CPU_cases=0,acceptance_Native_frames=0)

 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing final Root report')
  self.pin(OUT/'README.md');qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'index.html',qa['final_html_sha256'])
  assert qa['status']=='passed'and qa['failed_count']==0 and qa['console_errors']==qa['console_warnings']==[]and qa['check_count']==len(qa['checks'])==242 and all(x['status']=='passed'for x in qa['checks'])
  assert qa['Native_frames_added']==qa['Source_CPU_cases_added']==0 and qa['acceptance_only_rebuild_preserves_prior_160_frame_checks']and qa['CSS_only_rebuild_preserves_prior_data_and_behavior_checks']
  page=base.PortalPage();page.feed((OUT/'index.html').read_text());payload=json.loads(page.evidence)
  for name in('deployment_pointer_services.py','deployment_pointer_integration.py'):assert(ROOT/'source/recovered'/name).read_text()in page.sources
  assert len(page.sources)==2 and payload['native']==read(OUT/'runtime/evidence.json')['summary']and payload['points']==read(OUT/'runtime/original-control/checkpoints.json')==read(OUT/'runtime/observer/checkpoints.json')
  assert payload['static']==read(OUT/'fields-static/analysis-summary.json')and payload['acceptance']==read(OUT/'acceptance/requirements.json')and payload['observations']==read(OUT/'runtime/deployment-observations.json')
  for key,name in(('ownership','owner-and-caller-chain'),('completion','completion-contracts'),('denominators','stable-denominators'),('erratum','historical-wording-erratum')):assert payload[key]==read(OUT/'context'/(name+'.json'))
  for key,keys,name in(('source',('original_CPU_parent_cases','counts','source_guard_count'),'deployment/validation.json'),('integration',('original_CPU_parent_cases','counts','guard_count'),'source-integration.json'),('contracts',('original_contract_CPU_cases','actual_caller_RTS_CPU_cases','constructor_prefix_CPU_cases','bare_access_counterexample_prefix_CPU_cases','model_guard_check_count'),'fields-static/verification.json')):
   value=read(OUT/name);assert payload[key]=={k:value[k]for k in keys}
  observations=payload['observations'];expected=observations['full_software_entries']+observations['logical_coordinate_reads']+[x['following_original_store']for x in observations['logical_read_to_unit_store_pairs']]
  assert payload['events']==sorted({e['sequence']:e for e in expected}.values(),key=lambda e:e['sequence'])and len(payload['events'])==19
  assert len(payload['audio'])==2
  for variant,audio in zip(('original-control','observer'),payload['audio']):
   path=OUT/audio['path'];assert path==OUT/'runtime'/variant/'full-audio.wav';self.pin(path,audio['sha256'])
   with wave.open(str(path))as wav:assert(audio['channels'],audio['sample_rate'],audio['sample_frames'],audio['duration_seconds'])==(wav.getnchannels(),wav.getframerate(),wav.getnframes(),wav.getnframes()/wav.getframerate())
  selected={x['cpu']:x for x in read(OUT/'fields-static/selected-accesses.json')['accesses']};assert len(payload['accesses'])==len(selected)==4
  for item in payload['accesses']:
   row=selected[item['cpu']];contract=row['address_contract'];assert item['physical_bank']==row['physical_bank']and item['raw_hex']==row['raw_hex']and item['classification']==row['classification']
   assert item['pointer_count']==len(contract['whole_pointer_values'])and item['Y_count']==len(contract['Y_values'])and item['requirements']==contract['required_execution_contract']and item['auxiliary_intersection']==0
   assert item['logical_address_count']==len({(p+y)&65535 for p in contract['whole_pointer_values']for y in contract['Y_values']})
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path in(OUT/'verification.json',OUT/'package-receipt.json')or path.suffix=='.zip':continue
   assert path.is_file(),('Broken portal link',link)
  for name in('browser-native-proof.jpg','browser-deployment-proof.jpg'):
   path=OUT/name;self.pin(path,qa['artifact_and_dependency_sha256'][relative(path)])
   with Image.open(path)as image:image.load();assert image.format=='JPEG'and min(image.size)>=600
  self.counts.update(browser_checks=qa['check_count'],browser_Source_modules=len(page.sources),browser_Native_points=160,browser_actual_events=19,browser_screenshots=2)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA
 audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[];audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('context',audit.context),('acceptance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');audit.pin(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP and manifest['foundational_archive']['sha256']==V22_ZIP
 assert manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase26']
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in base.prior.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots']);names=set(manifest['include_files']);included={k:v for k,v in audit.pins.items()if k in names or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase26-one-deployment-pointer-readonly-audit-v1',status='pending_final_artifacts'if pending else'passed',ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,
  old_v25_incremental_preserved_sha256=OLD_ZIP,old_phase25_audit_sha256=OLD_AUDIT,old_phase25_postZIP_receipt_sha256=OLD_POSTZIP,old_v22_preserved_sha256=V22_ZIP,
  source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,
  checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guards',0),
  source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),
  limits=['Only new evidence is read; no original CPU/core, producer, historical audit main or analyzer is executed.',
   'One natural imported route, not a new cold boot; ancestor cold/no-preparation provenance is separately pinned.',
   'Only the separate26 observer has internal events. Full five-buffer equivalence is bounded to160 route frames.',
   'Actual software captures do not include instantaneous N163/PPU/APU. Source device fixtures remain explicit and separate.',
   'Formation body refactors, inherited B1B0, Source cases, static CPU contracts, syntax/reference checks and Native runs are separate counts.',
   'Auxiliary field names, whole-ROM completion and standalone playable source remain unproven.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))
if __name__=='__main__':main()
