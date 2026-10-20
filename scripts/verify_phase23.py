#!/usr/bin/env python3
"""Read-only phase23 audit; writes only the new verification.json.

No original core, CPU runner, analyzer, producer or old audit main is invoked.
Source comparisons, static contracts, model checks and Native observations
retain separate domains. Missing not-yet-final artifacts require --allow-pending.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys,wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase23'
SPEC=importlib.util.spec_from_file_location('readonly_phase22_audit_helpers',ROOT/'scripts/verify_phase22.py')
old=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=old;SPEC.loader.exec_module(old)
ROM_SHA=old.ROM_SHA;sha=old.sha;read=old.read;original=old.original;DISJOINT=old.DISJOINT
OLD_AUDIT='ca94229cff060e16b25f8f3e92eb752a94121af730ae70d114ce4ddf3a6d8eb8'
OLD_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
FIVE=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
CONFIGS={
 'natural-money8888-aux0':(8888,0,8,8850,True,0),
 'diagnostic-money257-aux0':(257,0,7,218,False,2),
 'diagnostic-money258-aux0':(258,0,8,220,True,2),
 'diagnostic-money512-aux0':(512,0,7,473,False,2),
 'diagnostic-money257-aux43':(257,43,7,218,False,3),
 'diagnostic-money257-aux44':(257,44,8,219,True,3),
}
def digest(raw):return hashlib.sha256(raw).hexdigest()
class Pending(Exception):pass

class Audit(old.Audit):
 def need(self,path):
  path=Path(path)
  if not path.is_file():raise Pending('Missing '+str(path.relative_to(ROOT)))
  return read(path)
 def record(self,path,final=True):
  value=self.need(path)
  if final and value.get('status')not in('passed','analyzed'):raise Pending('Not final '+str(Path(path).relative_to(ROOT)))
  self.pin(path)
  try:self.record_pins(value,Path(path).parent)
  except AssertionError as exc:
   if getattr(self,'allow_pending',False)and exc.args and isinstance(exc.args[0],tuple)and len(exc.args[0])>1 and exc.args[0][1]=='stale pin'and exc.args[0][0]not in self.frozen_names:
    raise Pending('Not-yet-current new-domain pin: '+exc.args[0][0])from exc
   raise
  self.nested_raw(value)
  return value
 def frozen_history(self):
  self.pin('analysis/phase22/verification.json',OLD_AUDIT)
  value=read(ROOT/'analysis/phase22/verification.json')
  self.frozen_names=set(value['source_and_validator_sha256'])|set(value['artifact_and_dependency_sha256'])
  assert value['status']=='passed'and value['ROM_sha256']==ROM_SHA and value['rebuilt_byte_identical']
  assert len(value['source_and_validator_sha256'])==473 and len(value['artifact_and_dependency_sha256'])==35354
  for name,pin in value['source_and_validator_sha256'].items():self.pin(name,pin);self.sources[name]=pin
  for name,pin in value['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  assert sha(ROOT/'build/三国志2超级版-逆向分析-v22.zip')==OLD_ZIP
  assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.counts.update(unchanged_phase22_source_script_pins=473,unchanged_phase22_artifact_dependency_pins=35354)

 def runtime(self):
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json')
  assert e['summary']=={k:v[k]for k in e['summary']}
  self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_city_threshold.py',v['script_sha256'])
  assert(v['native_configurations'],v['natural_configurations'],v['controlled_diagnostic_configurations'])==(6,1,5)
  assert(v['original_core_first_run_frames'],v['total_control_frames_all_runs'],v['fresh_process_runs'])==(45,180,24)
  assert(v['nonempty_artifact_checks'],v['decoded_PNG_checks'],v['full_WAV_checks'])==(838,138,12)
  assert(v['preparation_byte_writes_across_six_configurations'],v['physical_preparation_byte_writes_all_runs'])==(12,48)
  assert v['all_five_complete_buffers_match_each_frame']and v['all_nonempty_artifacts_repeat_exact']and v['failed_count']==0
  assert v['inherited_preparation_byte_writes']==v['additional_request_result_ready_RNG_PC_writes']==v['original_auxiliary_writes_observed']==0
  assert v['source_CPU_cases']==0 and v['state_imports_all_runs']==24 and v['cold_boot_runs']==0
  assert len(e['native_cases'])==len(e['observer_runs'])==6 and {c['case']for c in e['native_cases']}==set(CONFIGS)
  assert e['ROM_sha256']==ROM_SHA
  core_pins={'original-control':('924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a','.toolchain/nestopia/nestopia_libretro.dylib'),
   'observer':('45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d','.toolchain/phase21-observer/observed/nestopia_libretro.dylib')}
  for pin,path in core_pins.values():self.pin(path,pin)
  assert e['original_core_sha256']==core_pins['original-control'][0]and e['observer_core_sha256']==core_pins['observer'][0]
  mother=ROOT/e['mother_state'];self.pin(mother,e['mother_sha256']);m=old.prior.NestopiaContext.parse(mother.read_bytes())
  assert m.sram[0x41:0x44]==bytes((0,184,34))and int.from_bytes(m.sram[0x42:0x44],'little')==8888
  artifacts=pngs=wavs=points=frames=prep_count=raw_count=dedicated=0
  for case,(gold,aux,n,last_gold,accepted,writes)in CONFIGS.items():
   streams={};stream_frames={}
   for variant in('original-control','observer'):
    first=folder/case/variant;a=self.record(first/'validation.json');repeat=self.record(first/'repeat-validation.json')
    second=ROOT/repeat['second_run'];b=read(second/'validation.json');assert a==b
    assert a['status']==repeat['status']=='passed'and a['frames']==n
    assert a['core']['core_sha256']==core_pins[variant][0]and a['AV']['sample_rate']==48000 and a['AV']['native_dimensions']==[256,240]
    assert a['state_imported']and not a['cold_boot']and a['inherited_context']['inherited_preparation_byte_writes']==0
    assert a['natural_gameplay']==(writes==0)and a['controlled_diagnostic']==(writes!=0)
    assert a['additional_core_memory_writes']==len(a['preparation'])==writes
    assert not a['status_location_roster_troops_RNG_PC_request_result_ready_prepared']and not a['Native_internal_CPU_trace']
    assert a['source_CPU_comparisons']==0 and a['observer_core_sparse_CPU_events']==(variant=='observer')
    assert a['official_city_plus1_name']is None and a['fresh_process_per_run']and a['full_serialized_buffers_not_normalized']
    assert a['additional_core_memory_writes_after_declared_preparation']==0
    assert repeat['all_nonempty_artifact_bytes_exact']and repeat['validation_bytes_exact']
    assert repeat['artifact_checks']==len(a['artifact_sha256'])
    assert(first/'initial-ram.bin').read_bytes()==m.ram and(first/'initial-sram.bin').read_bytes()==m.sram
    assert(first/'mother-input.state').read_bytes()==mother.read_bytes()
    before=read(first/'initial-fields.json');assert before['all30_city_records_raw32'][2]==m.sram[64:96].hex()
    # initial-* is the common unprepared mother, not the diagnostic start.
    expected=bytearray(m.sram);declared=[]
    for change in a['preparation']:
     assert change['kind']=='SRAM'and change['address']in(0x6041,0x6042,0x6043)and change['frame']==0
     assert expected[change['address']-0x6000]==change['before']
     expected[change['address']-0x6000]=change['after'];declared.append((change['address'],change['before'],change['after']))
    assert expected[0x41:0x44]==bytes((aux,gold&255,gold>>8))
    assert len(a['preparation_groups'])==int(writes>0)
    for group in a['preparation_groups']:
     for key in('before','after'):
      for kind,size in(('RAM',2048),('SRAM',8192)):
       item=group[key][kind];p=first/item['path'];assert p.stat().st_size==item['bytes']==size;self.pin(p,item['sha256'])
     assert(first/group['before']['RAM']['path']).read_bytes()==(first/group['after']['RAM']['path']).read_bytes()==m.ram
     assert(first/group['before']['SRAM']['path']).read_bytes()==m.sram
     assert(first/group['after']['SRAM']['path']).read_bytes()==expected
     actual=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(m.sram,expected))if x!=y]
     assert actual==sorted(declared)and group['writes']==a['preparation']
    start=old.prior.NestopiaContext.parse((first/'prepared-initial.state').read_bytes());assert start.ram==m.ram and start.sram==expected
    assert a['initial_fields']['all30_city_records_raw32'][2]==expected[64:96].hex()
    for name,pin in a['artifact_sha256'].items():
     assert pin['bytes']>0
     for root in(first,second):
      path=root/name;assert path.stat().st_size==pin['bytes'];self.pin(path,pin['sha256'])
     artifacts+=1
    hashes=read(first/'buffer-hashes.json');rows=read(first/'frame-services.json');callbacks=read(first/'audio-callbacks.json')
    plan=read(first/'input-plan.json');assert len(plan)==n and all(p['frames']==1 and p['buttons']==[] and p['start_frame']==i for i,p in enumerate(plan))
    assert hashes==read(second/'buffer-hashes.json')and len(hashes)==len(rows)==len(callbacks)==n
    stream_frames[variant]=hashes
    with wave.open(str(first/'full-audio.wav'),'rb')as wav:
     assert(wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000)
     pcm_digest=hashlib.sha256();stops=[]
     for i,(row,h,cb)in enumerate(zip(rows,hashes,callbacks),1):
      assert row['frame']==h['frame']==i and cb['emulated_frame_start']==i-1
      pcm=wav.readframes(cb['stereo_sample_frames']);assert len(pcm)==cb['stereo_sample_frames']*4
      assert digest(pcm)==cb['pcm_sha256']==h['PCM_sha256']==row['PCM_sha256'];pcm_digest.update(pcm);stops.append(wav.tell()*4)
      assert all(row[key]==h[key]for key in FIVE)
      stem=first/('actual-frame-%03d'%i);ram=Path(str(stem)+'-ram.bin').read_bytes();sram=Path(str(stem)+'-sram.bin').read_bytes();state=Path(str(stem)+'.state').read_bytes()
      assert len(ram)==2048 and len(sram)==8192 and digest(ram)==h['RAM_sha256']and digest(sram)==h['SRAM_sha256']
      assert len(state)==h['whole_serialized_state_bytes']and digest(state)==h['whole_serialized_state_sha256']
      context=old.prior.NestopiaContext.parse(state)
      assert context.ram==ram and context.sram==sram and context.registers==row['actual_saved_CPU_registers']and list(context.prg_banks)==row['actual_saved_PRG_banks']
      for city in range(30):
       b=city*32;assert row['all30_city_records_raw32'][city]==sram[b:b+32].hex()
       assert row['all30_city_auxiliary_bytes'][city]==[sram[b+k]for k in(1,28,29,30,31)]
       assert row['all30_city_word_plus1_plus2'][city]==int.from_bytes(sram[b+1:b+3],'little')
       assert row['all30_city_gold'][city]==int.from_bytes(sram[b+2:b+4],'little')
       assert row['all30_city_reserve'][city]==int.from_bytes(sram[b+12:b+14],'little')
      assert sram[0x3FC:0x408].hex()==row['numeric_officer5']['raw12']
      assert row['numeric_officer5']['troops_raw16']==int.from_bytes(sram[0x404:0x406],'little')
      if i<=4:assert sram[0x41:0x44]==expected[0x41:0x44]
     assert not wav.readframes(1)and wav.tell()*4==a['full_audio']['PCM_bytes']and wav.getnframes()==a['full_audio']['stereo_sample_frames']
     assert pcm_digest.hexdigest()==a['full_audio']['PCM_sha256'];wavs+=1
    checks=read(first/'checkpoints.json');assert len(checks)==a['checkpoint_count']
    for point in checks:
     h=hashes[point['frame']-1];assert point['PCM_stop_byte']==stops[point['frame']-1]
     with Image.open(first/point['image'])as im:im.load();assert im.size==(256,240)and im.mode=='RGB'and digest(im.tobytes())==h['RGB_sha256']
     for key,size in(('RAM',2048),('SRAM',8192)):
      raw=(first/point[key]).read_bytes();assert len(raw)==size and digest(raw)==h[key+'_sha256']
     assert digest((first/point['state']).read_bytes())==h['whole_serialized_state_sha256'];pngs+=1
    for name in a['excluded_empty_VRAM']:assert(first/name).stat().st_size==(second/name).stat().st_size==0
    assert read(first/'auxiliary-events.json')==[]
    f=a['final_fields'];assert f['cooperation_status_6F8B']==255 and f['ruler_6F03']==4
    assert(f['all30_city_gold'][2],f['all30_city_reserve'][2],f['numeric_officer5']['troops_raw16'])==(last_gold,7799 if accepted else 8099,1000 if accepted else 700)
    if accepted:assert rows[4]['all30_city_gold'][2]==gold and rows[4]['domestic_budget_6F5D']==28
    effect=a['verified_effects'];assert(effect['initial_true_gold'],effect['initial_aux1'],effect['initial_overlapping_word'])==(gold,aux,aux|((gold&255)<<8))
    assert effect['gate_acceptance_effect_observed']==accepted and effect['original_request_FF']and effect['original_city_auxiliary_writes_observed']==0
    if variant=='observer':
     raw=(first/'bus-events.bin').read_bytes();ev=[json.loads(x)for x in(first/'events.jsonl').read_text().splitlines()]
     assert len(raw)==72*len(ev)==72*a['observer_events']['count'];raw_count+=len(ev)
     for j,event in enumerate(ev):assert old.prior.decode_event(raw[72*j:72*j+72])==event and event['sequence']==j+1
     assert not any(x['target_type']=='city_auxiliary'and x['kind']=='write_attempt'for x in ev)
     hits=[x for x in ev if x['target_type']=='city_auxiliary'];assert len(hits)==(2 if accepted else 1);dedicated+=len(hits)
     notes=read(first/'consumer-observations.json');assert len(notes)==len(hits)
     for note,event in zip(notes,hits):
      assert note['raw_event']==event and(event['physical_bank'],event['opcode_PC'],event['address'],event['Y'],event['value'])==(10,0xBD97,0x6041,1,aux)
      assert self.rom[original(10,0xBD97):original(10,0xBD97)+2]==b'\xB1\x20'
      pre=a['initial_fields']if event['frame']==1 else rows[event['frame']-2];post=rows[event['frame']-1]
      assert note['frame_start_city2_raw32']==pre['all30_city_records_raw32'][2]and note['frame_end_city2_raw32']==post['all30_city_records_raw32'][2]
      assert note['frame_start_gold']==pre['all30_city_gold'][2]and note['frame_end_gold']==post['all30_city_gold'][2]
      assert 'not a claimed opcode-instant'in note['scope']
    streams[variant]=a
   assert stream_frames['original-control']==stream_frames['observer']
   one,two=folder/case/'original-control',folder/case/'observer'
   for name in('initial.state','initial-ram.bin','initial-sram.bin','prepared-initial.state','mother-input.state','input-plan.json','full-audio.wav'):assert sha(one/name)==sha(two/name)
   frames+=n;points+=streams['original-control']['checkpoint_count'];prep_count+=writes
  assert(frames,points,artifacts,pngs,wavs,prep_count,raw_count,dedicated)==(45,69,838,138,12,12,114,9)
  self.counts.update(native_configurations=6,native_natural_configurations=1,native_diagnostic_configurations=5,native_fresh_process_runs=24,
   native_first_original_frames=45,native_all_control_frames=180,native_original_first_checkpoints=69,native_nonempty_repeat_artifacts=838,native_PNG_checks=138,native_full_WAV_checks=12,
   native_logical_preparation_bytes=12,native_physical_preparation_bytes_all_runs=48,native_state_imports=24,native_cold_boots=0,
   observer_raw_records=114,observer_dedicated_BD97_reads=9,observer_auxiliary_writes=0)

 def static_fields(self):
  folder=OUT/'fields-static';validation=self.record(folder/'verification.json');summary=self.record(folder/'analysis-summary.json');self.record(folder/'evidence.json')
  assert validation['failed_count']==0 and validation['source_CPU_cases']==summary['source_CPU_cases']==0
  previous={(r['physical_bank'],r['cpu']):r for r in read(ROOT/'analysis/phase22/fields-static/all-indirect-accesses.json')['accesses']}
  data=self.record(folder/'all-indirect-accesses.json',False);rows=data['accesses'];canonical={(r['physical_bank'],r['cpu']):r for r in rows}
  assert len(rows)==len(canonical)==1526 and set(canonical)==set(previous)
  for key,row in canonical.items():
   self.raw(row);proof=row['address_contract'];assert row['phase22_classification']==previous[key]['classification']
   if proof:
    hit=old.intersection(proof);assert hit==proof['possible_auxiliary_effective_addresses']and len(hit)==proof['auxiliary_address_intersection_count']
    assert row['whole_pointer_values']==sorted(old.words(proof))and row['Y_values']==old.indices(proof)
    if row['classification']==DISJOINT:assert not hit
   else:assert row['classification']=='unresolved_pointer_or_index_contract'
   assert row['candidate_contract_is_authoritative']is False
   origin=row['phase23_authoritative_contract_origin']
   if origin:
    self.pin(origin['path'],origin['sha256']);assert proof==previous[key][origin['contract_field']]
   assert row['newly_proved_disjoint']==(row['classification']==DISJOINT and previous[key]['classification']!=DISJOINT)
  assert Counter(r['classification']for r in rows)==summary['all_indirect_classification_counts']
  assert summary['all_indirect_classification_counts']==dict(proved_disjoint_auxiliary_address_domain=1175,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=270)
  remaining=self.record(folder/'phase22-remaining368-handling.json',False);assert len(remaining['accesses'])==remaining['access_count']==368
  assert all(r==canonical[r['physical_bank'],r['cpu']]for r in remaining['accesses'])
  assert sum(r['newly_proved_disjoint']for r in remaining['accesses'])==summary['newly_proved_disjoint_all_count']
  assert summary['newly_proved_disjoint_all_count']==17 and summary['remaining_access_count']==351
  assert len(self.record(folder/'remaining-accesses.json',False)['accesses'])==summary['remaining_access_count']
  assert not summary['complete_analysis_fixed_point_proven']and all(v is None for v in summary['official_target_field_names'].values())
  groups=self.record(folder/'shared-producer-caller-groups.json',False);assert groups['previous_candidate_count']==368
  assert groups['group_count']==len(groups['groups'])==summary['grouping_count']
  assert groups['group_count']==110 and sum(g['unknown_producer']for g in groups['groups'])==55
  assert sum(g['access_count']for g in groups['groups']if g['unknown_producer'])==270
  assert len(summary['finite_refinement_rounds'])==2
  access_keys=[]
  for group in groups['groups']:
   assert group['access_count']==len(group['accesses'])and isinstance(group['unknown_producer'],bool)
   for row in group['accesses']:assert row['physical_bank']==group['physical_bank'];access_keys.append((row['physical_bank'],row['cpu']))
   for producer in group['shared_pointer_producers']:self.nested_raw(producer)
   for proc in group['known_enclosing_procedures']:
    self.raw(proc['entry'])
    for caller in proc['all_trusted_incoming_callers']:self.nested_raw(caller)
  assert len(access_keys)==len(set(access_keys))==368 and set(access_keys)=={(r['physical_bank'],r['cpu'])for r in remaining['accesses']}
  raw=self.record(folder/'raw345-executability-ledger.json',False);assert raw['window_count']==len(raw['windows'])==345
  categories=Counter(r['phase22_executability_category']for r in raw['windows']);assert categories==raw['categories']==summary['raw_window_categories']
  assert categories==dict(unresolved_raw_window_no_proved_control_entry=228,
   trusted_instruction_operand_no_proved_alternate_entry=104,declared_ROM_data_no_proved_instruction_entry=13)
  for row in raw['windows']:
   offset=16+row['physical_bank']*8192+row['bank_offset'];assert offset==row['rom_offset']and self.rom[offset:offset+len(bytes.fromhex(row['raw_hex']))]==bytes.fromhex(row['raw_hex'])
   assert not row['promoted_to_executable_code']and not row['trusted_instruction_entry_at_start']
  dummy=self.record(folder/'logical-vs-dummy-bus-contracts.json',False)
  assert dummy['access_count']==len(dummy['accesses'])==1526
  for row in dummy['accesses']:
   authority=canonical[row['physical_bank'],row['cpu']];proof=authority['address_contract']
   actual=old.dummy_intersection(proof,authority['op'])if proof else None
   assert row['logical_classification']==authority['classification']and row['operation']==authority['op']
   assert row['dummy_auxiliary_bus_addresses']==actual and row['dummy_auxiliary_intersection_count']==(None if actual is None else len(actual))
   assert row['logical_contract_changed']is False
  self.record(folder/'scalar-cell-site-proofs.json',False)
  assert validation['original_contract_CPU_cases']==5643
  assert validation['actual_caller_RTS_contract_cases']==4107 and validation['original_follower_scan_prefix_contract_CPU_cases']==1024 and validation['original_flag_prefix_contract_CPU_cases']==512
  assert validation['model_guard_check_count']==len(validation['model_checks'])==19 and all(r['passed']for r in validation['model_checks'])
  self.counts.update(static_all_accesses=1526,static_previous_candidates=368,static_remaining_candidates=summary['remaining_access_count'],
   static_newly_disjoint=summary['newly_proved_disjoint_all_count'],static_complete_producer_caller_groups=groups['group_count'],
   static_raw_hypotheses_not_code=345,raw_operand_windows=104,raw_declared_data_windows=13,raw_unresolved_windows=228,
   static_unknown_producer_groups=55,static_unknown_producer_accesses=270,
   static_actual_caller_RTS_contract_cases_not_Source=4107,static_finite_refinement_rounds_not_fixed_point=2)
  # All original CPU contract and model checks remain outside Source totals.
  for key,value in validation.items():
   if isinstance(value,int)and('CPU_cases'in key or'guard_check_count'in key):self.counts['static_'+key+'_not_Source']=value

 def source_cases(self):
  folder=OUT/'threshold';body=self.need(folder/'validation.json')
  if body.get('quick'):raise Pending('Threshold Source validation is still quick')
  body=self.record(folder/'validation.json');evidence=self.record(folder/'evidence.json',False);catalog=self.record(folder/'static-catalog.json',False)
  assert body['failed_count']==0 and body['failures']==[] and body['status']=='passed'
  assert body['original_CPU_parent_cases']==len(body['cases'])and Counter(r['comparison']for r in body['cases'])==body['counts']
  assert body['source_guard_count']==len(body['guards'])and all(g['status']=='passed'for g in body['guards'])
  assert len(body['model_checks'])==1 and body['model_checks'][0]['passed']and body['model_checks'][0]['original_CPU_cases']==0
  assert body['model_checks'][0]['finite_formula_inputs']==65536
  assert body['source_original_CPU_callbacks']==0 and not body['production_IR_interpretation']and not body['Native_internal_CPU_trace']
  assert evidence['production_original_CPU_callbacks']==0 and not evidence['production_IR_interpretation']and not evidence['production_runtime_codegen']
  assert evidence['coverage']==dict(new_manual_instruction_positions=85,new_manual_code_bytes=149,dynamic_new_positions=85,not_dynamic=0,all_paths_or_inputs_proven=False)
  for row in body['cases']:
   assert(row['RAM_bytes'],row['SRAM_bytes'])==(2048,8192)and row['AXYP_SP_PC_ordered_IO_four_banks_N163_equal']and row['source_original_CPU_callbacks']==0
  # Only three newly named helpers occupy149 original bytes. Parent BD7A is reused.
  assert catalog['new_manual_code_bytes']==149 and catalog['new_manual_instruction_positions']==len(catalog['instructions'])==85
  assert sum(len(bytes.fromhex(r['raw_hex']))for r in catalog['original_ranges'])==149
  assert catalog['full_consumer_reused_frozen_source']=='source/recovered/city_auxiliary_services.py:recruitment_then_development'
  visited={(r['physical_bank'],r['cpu_address'])for r in body['executed_instruction_positions']}
  for row in catalog['instructions']:self.raw(row);assert(row['physical_bank'],row['cpu_address'])in visited
  self.nested_raw(catalog);self.nested_raw(evidence)
  integration=self.record(OUT/'source-integration.json')
  assert integration['original_CPU_parent_cases']==len(integration['rows'])==38
  assert integration['counts']==Counter(r['completion']for r in integration['rows'])==dict(returned=37,nonlocal_return=1)
  assert integration['guard_count']==len(integration['guards'])==3 and integration['source_original_CPU_callbacks']==0
  for row in integration['rows']:assert row['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and row['source_original_CPU_callbacks']==0
  for name in('city_threshold_services.py','city_threshold_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
     values=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module or'']
     assert not any(any(bad in value for bad in('py65','state_machine','importlib'))for value in values)
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.counts.update(new_manual_original_code_bytes=149,new_manual_instruction_positions=85,source_child_CPU_cases=len(body['cases']),source_child_guards=len(body['guards']),source_integration_CPU_cases=38,source_integration_guards=3,
   new_Source_CPU_cases=len(body['cases'])+38,new_Source_guard_cases=len(body['guards'])+3,
   new_Source_actual_caller_RTS=body['counts'].get('actual_caller_RTS',0)+37,
   new_Source_nonlocal_return=body['counts'].get('actual_nonlocal_return',0)+1,
   new_Source_strict_dependency_prefix=body['counts'].get('strict_missing_dependency_prefix',0),
   source_readonly_model_checks_not_CPU_cases=1,source_readonly_model_formula_inputs_not_CPU_cases=65536)
  assert self.counts['new_Source_CPU_cases']==self.counts['new_Source_actual_caller_RTS']+self.counts['new_Source_nonlocal_return']+self.counts['new_Source_strict_dependency_prefix']
  for key,value in body['counts'].items():self.counts['source_child_'+key]=value

 def cpu_contexts(self):
  folder=OUT/'cpu-threshold';trace=self.record(folder/'trace.json',False);evidence=self.record(folder/'evidence.json',False)
  assert trace['status']==evidence['status']=='bounded_original_CPU_observation'
  assert trace['source_CPU_cases']==evidence['source_CPU_cases']==0 and trace['contexts']==len(trace['cases'])==6 and trace['exported_caller_inputs']==24
  captured=set()
  for row in trace['cases']:
   case=row['case'];gold,aux,_,_,accepted,writes=CONFIGS[case]
   self.pin(row['native_state']);context=old.prior.NestopiaContext.parse((ROOT/row['native_state']).read_bytes())
   assert context.registers==row['saved_registers']and list(context.prg_banks)==row['actual_banks']
   assert row['new_NMI_IRQ_arrivals']==0 and row['additional_CPU_prepared_numeric_bytes']==[]and row['source_CPU_cases']==0 and not row['Native_internal_CPU_trace']
   native=read(OUT/'runtime'/case/'original-control/validation.json')
   assert row['prepared_numeric_bytes']==native['preparation']and len(row['captured'])==4
   captured.update(row['captured'])
   assert row['origin']==('actual_Native_snapshot_originalCPU_reached_caller'if writes==0 else'diagnostic_Native_snapshot_originalCPU_reached_caller')
   assert len(row['gates'])==(2 if accepted else 1)and len(row['branches'])==len(row['gates'])
   for gate,branch in zip(row['gates'],row['branches']):
    assert(gate['city'],gate['pointer20'],gate['Y'],gate['opaque_byte1'],gate['true_gold'],gate['overlap_word'])==(2,0x6040,1,aux,gold,aux|((gold&255)<<8))
    assert gate['registers']['pc']==0xBD97 and gate['unsigned_predicate']==accepted and branch['carry']==accepted and branch['registers']['pc']==0xBDA1
   if accepted:assert row['before_officer5_commit']['true_gold']==gold and row['before_officer5_commit']['reserve']==7799
   assert row['final_fields']['officer5_troops']==(1000 if accepted else 700)and row['final_fields']['city2_reserve']==(7799 if accepted else 8099)
  contexts=sorted((folder/'actual-callers').glob('entry-*/context.json'))
  assert len(contexts)==len(captured)==24 and captured=={p.parent.name for p in contexts}
  domains=Counter()
  for path in contexts:
   row=self.record(path,False);domains[row['origin']]+=1
   assert row['additional_CPU_prepared_numeric_bytes']==[]
   assert not row['synthetic_caller_or_PC_or_RNG_or_request_preparation']and row['injected_new_NMI']==row['injected_new_IRQ']==0 and not row['Native_internal_CPU_trace']
   parent=Path(row['original_Native_state']).parts;case=parent[parent.index('runtime')+1]
   native=read(OUT/'runtime'/case/'original-control/validation.json')
   assert row['inherited_Native_preparation']==row['prepared_numeric_bytes']==native['preparation']
   self.pin(row['original_Native_state'],row['original_Native_state_sha256'])
   ram=(path.parent/'input-ram.bin').read_bytes();sram=(path.parent/'input-sram.bin').read_bytes();assert len(ram)==2048 and len(sram)==8192
   sp=row['registers']['sp'];assert row['existing_return_PC']==((ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8)+1)&65535
  assert domains==dict(actual_Native_snapshot_originalCPU_reached_caller=4,diagnostic_Native_snapshot_originalCPU_reached_caller=20)
  self.counts.update(original_CPU_actual_context_callee_exports_not_Source_cases=24,original_CPU_actual_contexts_not_Source_cases=6,
   original_CPU_context_new_NMI_IRQ_arrivals=0,original_CPU_context_additional_prepared_bytes=0,
   original_CPU_context_instructions_not_Source_cases=sum(r['original_instructions']for r in trace['cases']))

 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing analysis/phase23/README.md')
  self.pin(OUT/'README.md')
  qa=self.record(OUT/'browser-validation.json');page_path=OUT/'index.html';self.pin(page_path,qa['HTML_sha256'])
  assert qa['status']=='passed'and qa.get('console_errors',[])==[]and qa['check_count']==len(qa['checks'])
  assert all(row['status']=='passed'for row in qa['checks'])
  page=old.prior.Page();page.feed(page_path.read_text())
  names=('city_threshold_services.py','city_threshold_integration.py','city_auxiliary_services.py')
  assert len(page.sources)==len(names)==3
  for text,name in zip(page.sources,names):assert text.encode('utf8')==(ROOT/'source/recovered'/name).read_bytes()
  payload=json.loads(page.evidence);native=read(OUT/'runtime/evidence.json');groups=read(OUT/'fields-static/shared-producer-caller-groups.json');static=read(OUT/'fields-static/analysis-summary.json')
  assert payload['groups']==groups['groups']and payload['group_count']==groups['group_count']and payload['previous_candidate_count']==368
  assert payload['remaining_count']==static['remaining_access_count']and payload['runtime_summary']==native['summary']
  assert len(payload['cases'])==6
  for actual,item in zip(payload['cases'],native['native_cases']):
   folder=OUT/'runtime'/item['folder'];prep=read(folder/'preparation.json');points=read(folder/'checkpoints.json')
   expected=[]
   for point in points:
    if point['label'].startswith('actual-frame-'):
     f=point['fields'];expected.append(dict(frame=point['frame'],label=point['label'],image=point['image'],state=point['state'],SRAM=point['SRAM'],RAM=point['RAM'],
      city2_raw32=f['all30_city_records_raw32'][2],officer5_raw12=f['all237_officer_records_raw12'][5],budget=f['domestic_budget_6F5D'],request=f['cooperation_status_6F8B']))
   start=prep['groups'][0]['after']['SRAM']if prep['groups']else'initial-sram.bin'
   assert actual==dict(case=item['case'],frames=item['frames'],points=expected,natural=item['natural_gameplay'],preparation=prep['writes'],
    start_SRAM=start,start_city2_raw32=(folder/start).read_bytes()[0x40:0x60].hex(),effects=item['verified_effects'])
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path==OUT/'verification.json'or path.suffix=='.zip':continue
   assert path.is_file(),('Broken portal link',link)
  screenshot=qa['screenshot'];self.pin(screenshot['path'],screenshot['sha256'])
  self.counts.update(browser_source_modules=len(page.sources),browser_checks=len(qa['checks']))
  return dict(status='passed',HTML_sha256=qa['HTML_sha256'],receipt_path=relative(OUT/'browser-validation.json'))

def relative(path):return str(Path(path).relative_to(ROOT))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA;audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[]
 audit.frozen_history();audit.runtime()
 for name,method in(('fields-static',audit.static_fields),('Source',audit.source_cases),('exact-CPU-contexts',audit.cpu_contexts),('Root-browser-and-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','canonical_v22_archive_replaced'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in old.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 included_roots=tuple(x+'/'for x in manifest['include_roots']);included_files=set(manifest['include_files'])
 included={k:v for k,v in audit.pins.items()if k in included_files or k.startswith(included_roots)}
 external={k:v for k,v in audit.pins.items()if k not in included}
 value=dict(schema='phase23-frozen-history-threshold-discrimination-audit-v1',status='pending_final_artifacts'if pending else'passed',
  ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v22_preserved_sha256=OLD_ZIP,old_phase22_audit_sha256=OLD_AUDIT,
  source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,
  included_dependency_sha256=included,external_dependency_sha256=external,checks=dict(audit.counts),pending=pending,
  source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guard_cases',0),
  source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),
  source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),
  limits=['Read-only validation of frozen records, not a rerun of any core, CPU or producer.',
   'One natural and five diagnostic configurations are distinct from Source comparisons and static original-CPU contracts.',
   'Native BD97 bus events capture+1 only; full-frame +2/gold envelopes and independent CPU exact gates remain separately attributed.',
   'A conditional overlapping-word predicate is not an official name or a natural writer for city+1.',
   'External historical dependencies remain pinned to the separate v22 base; the incremental archive excludes ROM, byte-source, toolchain and large old history.'])
 (OUT/'verification.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status=value['status'],checks=value['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))
if __name__=='__main__':main()
