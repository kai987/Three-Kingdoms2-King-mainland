#!/usr/bin/env python3
"""Read-only phase30 audit. Only new analysis/phase30/verification.json is written.

No CPU/core, producer, analyzer, historical audit main or generator is executed.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys,wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase30';sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('readonly_phase27_audit',ROOT/'scripts/verify_phase27.py');base=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=base;SPEC.loader.exec_module(base)
from capture_native_postbattle_early import decode_event,fields,CASES,CORE_SHA,OBSERVER_SHA,RECORD_BYTES
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=base.ROM_SHA;sha=base.sha;read=base.read;original=base.original;DISJOINT=base.DISJOINT;Pending=base.Pending
OLD_AUDIT='177c7d2d27dc3f5fd9840f90802be752befa3dd7ae885e867e9c110432f68a15'
OLD_ZIP='fb068a084d9b65038a49f7914d24e437ea4151a90f84af08ac87e19656a0cbc2'
OLD_POSTZIP='d481a1efd41c77e4447bfab0887de27ffbce547fdbc4a875d41e1604ee307f7e'
V22_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(p):return str(Path(p).resolve().relative_to(ROOT))

class Audit(base.Audit):
 def frozen_history(self):
  self.pin('analysis/phase29/verification.json',OLD_AUDIT);v=read(ROOT/'analysis/phase29/verification.json');assert v['status']=='passed'and not v['pending']and v['ROM_sha256']==ROM_SHA and v['rebuilt_byte_identical']
  assert(len(v['source_and_validator_sha256']),len(v['artifact_and_dependency_sha256']))==(563,52043)
  self.frozen_names=set(v['source_and_validator_sha256'])|set(v['artifact_and_dependency_sha256'])
  for name,p in v['source_and_validator_sha256'].items():self.pin(name,p);self.sources[name]=p
  for name,p in v['artifact_and_dependency_sha256'].items():self.pin(name,p)
  self.pin('analysis/phase29/package-receipt.json',OLD_POSTZIP);p=read(ROOT/'analysis/phase29/package-receipt.json');assert p['status']=='passed'and p['phase29_audit_sha256']==OLD_AUDIT and p['sha256']==OLD_ZIP and p['file_count']==3040
  self.pin('build/三国志2超级版-逆向分析-v29增量.zip',OLD_ZIP);self.pin('build/三国志2超级版-逆向分析.zip',V22_ZIP);assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.counts.update(unchanged_phase29_source_script_pins=563,unchanged_phase29_artifact_dependency_pins=52043,unchanged_phase29_postZIP_receipts=1)

 def ancestry30(self,c,ancestor):
  for value in ancestor.values():
   if isinstance(value,dict)and 'path'in value and 'sha256'in value:self.pin(value['path'],value['sha256'])
   elif isinstance(value,list):
    for x in value:
     if isinstance(x,dict)and 'path'in x and 'sha256'in x:self.pin(x['path'],x['sha256'])
  assert ancestor['additional_core_memory_writes']==0 and ancestor['additional_preparation']==[]and ancestor['new_case_state_imported']and not ancestor['new_case_cold_boot']
  parent=read(ROOT/ancestor['parent_validation']['path']);assert parent['status']=='passed'and ancestor['parent_checkpoint']in read(ROOT/ancestor['parent_checkpoints']['path'])and ancestor['parent_checkpoint']['frame']==c['parent_frame']
  assert sha(ROOT/c['mother'])==ancestor['mother']['sha256']==c['mother_sha256']
  if c['natural']:
   assert ancestor['natural_ordinary_input_route']and not ancestor['controlled_ancestry']and ancestor['known_inherited_preparation_byte_writes']==0 and not ancestor['known_inherited_preparation']and ancestor['earlier_ancestor_cold_boot']
   p=read(ROOT/ancestor['earlier_parent']['path']);assert p['cold_boot']and not p['state_imported']and p['additional_core_memory_writes']==0 and not parent['preparation']and parent['additional_core_memory_writes']==0
  else:
   assert not ancestor['natural_ordinary_input_route']and ancestor['controlled_ancestry']and ancestor['known_inherited_preparation']==parent['preparation']and len(parent['preparation'])==ancestor['known_inherited_preparation_byte_writes']==19
   assert 'not fully established'in ancestor['earlier_than_phase15_numeric_preparation_status']
   folder=ROOT/ancestor['historical_preparation_base']
   for g in ancestor['historical_preparation_groups']:
    before={k:bytearray((folder/g['before'][k]['path']).read_bytes())for k in('RAM','SRAM')};after={k:(folder/g['after'][k]['path']).read_bytes()for k in before}
    for row in g['writes']:
     index=row['address']-(0x6000 if row['kind']=='SRAM'else 0);assert before[row['kind']][index]==row['before'];before[row['kind']][index]=row['after']
    assert all(bytes(before[k])==after[k]for k in before)

 def runtime(self):
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json');assert e['summary']=={k:v[k]for k in e['summary']};self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_postbattle_early.py',v['script_sha256'])
  expected=dict(routes=3,natural_routes=2,controlled_ancestry_routes=1,core_variants=2,fresh_process_runs=12,original_first_frames=48,all_control_frames=192,original_checkpoints=48,nonempty_artifact_repeat_checks=879,PNG_checks=96,WAV_checks=6,observer_events=179547,full_software_snapshots=138,early_public_software_inputs=14,actual_BC46_calls=2,actual_BB8C_calls=2,actual_BB36_calls=0,actual_BC46_mode0_calls=1,actual_BC46_mode1_calls=1,actual_BC46_mode2_calls=0,early_city_roster_writes=4,changed_early_city_roster_bytes=4,ECEE_immediate_returns=2,phase3_fresh_hold_callbacks=23,phase3_completion_callbacks=1,city_auxiliary_bus_events=0,additional_core_memory_writes=0,cold_boots=0,state_imports=12,Source_CPU_cases=0,failed_count=0)
  assert all(v[k]==x for k,x in expected.items())and all(v[k]for k in('all_five_complete_buffers_equal_each_frame','all_complete_initial_API_buffers_equal','all_artifacts_repeat_exact','full_serialized_buffers_not_normalized'))
  artifacts=images=wavs=0
  for case,c in CASES.items():
   self.ancestry30(c,e['case_ancestry'][case]);mother=ROOT/c['mother'];m=NestopiaContext.parse(mother.read_bytes());original_rows=None
   for variant,core in(('original-control',CORE_SHA),('observer',OBSERVER_SHA)):
    first=folder/case/variant;second=OUT/'runtime-repeat'/case/variant;a=self.record(first/'validation.json');b=self.record(second/'validation.json');repeat=self.record(first/'repeat-validation.json');assert a==b and a['core']['core_sha256']==core
    assert a['frames']==a['checkpoint_count']==c['frames']and a['state_imported']and not a['cold_boot']and a['additional_core_memory_writes']==a['Source_CPU_cases']==0 and not a['original_core_internal_CPU_trace']
    assert a['natural_ordinary_input_route']==c['natural']and a['controlled_ancestry']==(not c['natural'])and a['known_inherited_preparation_byte_writes']==(0 if c['natural']else 19)
    self.ancestry30(c,a['ancestry']);prep=self.record(first/'preparation.json',False);assert prep==e['case_ancestry'][case]==a['ancestry']and repeat['all_bytes_exact']and repeat['artifact_checks']==len(a['artifact_sha256'])
    n=NestopiaContext.parse((first/'initial.state').read_bytes());assert(n.ram,n.sram,n.registers,n.prg_banks)==(m.ram,m.sram,m.registers,m.prg_banks)
    assert(first/'initial-ram.bin').read_bytes()==m.ram and(first/'initial-sram.bin').read_bytes()==m.sram
    for name,p in a['artifact_sha256'].items():
     assert p['bytes']>0
     for path in(first/name,second/name):assert path.stat().st_size==p['bytes'];self.pin(path,p['sha256'])
     artifacts+=1
    rows=read(first/'frame-services.json');points=read(first/'checkpoints.json');callbacks=read(first/'audio-callbacks.json');plan=read(first/'input-plan.json');assert len(rows)==len(points)==len(callbacks)==c['frames']and len(plan)==1 and plan[0]['buttons']==[]and plan[0]['frames']==c['frames']
    if original_rows is None:original_rows=rows
    assert rows==original_rows
    with wave.open(str(first/'full-audio.wav'))as wav:
     assert(wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
     for i,(row,point,cb)in enumerate(zip(rows,points,callbacks),1):
      assert row['frame']==point['frame']==cb['emulated_frame_start']+1==i and row['parent_route_frame']==c['parent_frame']+i
      pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']and wav.tell()*4==row['PCM_stop_byte']
      r=(first/point['RAM']).read_bytes();s=(first/point['SRAM']).read_bytes();state=(first/point['state']).read_bytes();n=NestopiaContext.parse(state)
      assert len(r)==2048 and len(s)==8192 and digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']
      assert(n.ram,n.sram,n.registers,list(n.prg_banks))==(r,s,row['actual_saved_CPU_registers'],row['actual_saved_PRG_banks'])and all(row[k]==x for k,x in fields(r,s).items())and all(row[k]==x for k,x in point['fields'].items())
      for key in('RAM','SRAM','state','image'):assert(first/point[key]).read_bytes()==(folder/case/'original-control'/point[key]).read_bytes()
      with Image.open(first/point['image'])as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
      images+=1
     assert not wav.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and wav.tell()*4==a['full_audio']['PCM_bytes'];wavs+=1
    for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):assert(first/name).read_bytes()==(folder/case/'original-control'/name).read_bytes()
    assert a['initial_fields']['outcome_0514']==c['outcome']and a['initial_fields']['battle_0500_0501']==[15,c['start_stage']]and rows[0]['battle_0500_0501']==c['first_stage']
   self.observer30(folder/case/'observer',case)
  assert(artifacts,images,wavs)==(879,96,6);self.core_provenance();self.record(folder/'media-static-validation.json')
  self.counts.update({f'Native_{k}':x for k,x in expected.items()})

 def observer30(self,folder,case):
  events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()));raw=(folder/'bus-events.bin').read_bytes();assert len(raw)==len(events)*RECORD_BYTES
  schema=self.record(folder/'event-schema.json',False);assert len(schema['raw_layout'])==schema['words']==68 and schema['bytes_per_record']==272
  for i,e in enumerate(events,1):
   assert decode_event(raw[(i-1)*RECORD_BYTES:i*RECORD_BYTES],sequence=i)==e
   if e['opcode_PC']is not None and e['opcode_PC']>=0x8000:assert e['physical_bank']==e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]and e['rom_offset']==original(e['physical_bank'],e['opcode_PC'])
   if e['data_ROM_offset']is not None:assert e['value']==self.rom[e['data_ROM_offset']]and e['data_physical_bank']==e['actual_PRG_banks'][(e['address']-0x8000)//8192]
   if e['target_type']=='pointer_001A_001B_RAM_write':assert e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
  shadow=bytearray((folder/'initial-sram.bin').read_bytes());frame=1
  for e in events:
   while frame<e['frame']:
    assert shadow==(folder/f'frame-{frame:03d}-sram.bin').read_bytes();frame+=1
   if e['kind']=='write_attempt'and 0x6000<=e['address']<0x8000:
    address=e['address']-0x6000;assert shadow[address]==e['storage_byte_before_write'];shadow[address]=e['physical_storage_byte_after_event']
  while frame<=CASES[case]['frames']:
   assert shadow==(folder/f'frame-{frame:03d}-sram.bin').read_bytes();frame+=1
  snapshots=(folder/'snapshots.bin').read_bytes();index=list(map(json.loads,(folder/'snapshot-index.jsonl').read_text().splitlines()));by_seq={e['sequence']:e for e in events};assert len(snapshots)==len(index)*10240
  for i,item in enumerate(index,1):
   e=by_seq[item['event_sequence']];payload=snapshots[(i-1)*10240:i*10240];r,s=payload[:2048],payload[2048:];assert item['snapshot_sequence']==e['full_snapshot_sequence']==i and item['frame']==e['frame']
   assert digest(payload)==item['sha256']and digest(r)==item['RAM_sha256']and digest(s)==item['SRAM_sha256']and list(r[:0x30])==e['ZP_0000_002F']
   assert e['battle_0506_0507_050E_0514']==[r[x]for x in(0x506,0x507,0x50E,0x514)]and e['RAM0500_0503']==list(r[0x500:0x504])and e['RAM0514_0517']==list(r[0x514:0x518])and e['RAM0518_051B']==list(r[0x518:0x51C])
   assert e['fade_0087_008A']==list(r[0x87:0x8B])and e['ppu_flags_007D_0080']==list(r[0x7D:0x81])and e['palette_active_0100_011F']==list(r[0x100:0x120])and e['palette_backup_0120_013F']==list(r[0x120:0x140])and e['shadow_bank_bytes_00DE_00E5']==list(r[0xDE:0xE6])
   assert item['actual_registers']==dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC'])and item['actual_PRG_banks']==e['actual_PRG_banks']
   assert not item['instantaneous_N163_PPU_APU_captured']and item['capture_core_sha256']==OBSERVER_SHA and item['additional_core_memory_writes']==0
   assert(folder/item['exported_RAM']).read_bytes()==r and(folder/item['exported_SRAM']).read_bytes()==s
   sp=e['SP'];word=r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8;assert word==e['stack_top_word_raw']&65535
  ob=next(x for x in self.record(OUT/'runtime/early-lifecycle-observations.json',False)['routes']if x['case']==case);by_seq={e['sequence']:e for e in events}
  def original_event_tree(x):
   if isinstance(x,dict):
    if x.get('kind')in('opcode_boundary','read','word_read_low','word_read_high','write_attempt')and'sequence'in x:assert x==by_seq[x['sequence']]
    else:
     for value in x.values():original_event_tree(value)
   elif isinstance(x,list):
    for value in x:original_event_tree(value)
  original_event_tree(ob);ops=[e for e in events if e['kind']=='opcode_boundary'];early=[e for e in ops if e['physical_bank']==8 and e['opcode_PC']in(0xBAC1,0xBB3D,0xBC46,0xBC52,0xBD59,0xBD67,0xBB36,0xBB8C,0xBB39,0xBB8F)];assert early==ob['early_original_entries']
  controller=[e for e in events if e['early_controller_byte_read']];assert controller==ob['controller_byte_reads']
  writes=[e for e in events if e['early_SRAM_write']];city=[e for e in writes if e['address']<0x63C0];assert writes==ob['early_SRAM_writes']and city==ob['early_city_roster_writes']
  assert all(e['kind']=='write_attempt'and 0xBC46<=e['opcode_PC']<0xBF0A and e['physical_storage_byte_after_event']==e['value']for e in writes)
  assert not any(e['opcode_PC']in(0xBB36,0xBD67)for e in early)and not ob['city_auxiliary_bus_events']and not any(e['target_type']=='city_auxiliary_bus'for e in events)
  if case=='natural-stage0-human':assert not city and not ob['actual_BC46_calls']and[x['value']for x in controller]==[0]and[x['opcode_PC']for x in early]==[0xBAC1]
  else:
   call=ob['actual_BC46_calls'][0];entry=call['entry'];previous=next(p for p in reversed(ops)if p['sequence']<entry['sequence']);assert previous==call['actual_JSR_boundary']and(previous['physical_bank'],previous['opcode_PC'])==(8,0xBB8C)and previous['SP']==entry['SP']+2
   assert entry['stack_top_word_raw']&65535==0xBB8E and call['return_PC']==0xBB8F and call['not_inferred_from_return_word_minus3']
   assert self.rom[previous['rom_offset']:previous['rom_offset']+3]==bytes.fromhex('20 46 BC')
   target=ob['mode_targets'][0];assert target['postbattle_mode_6F91']==(0 if CASES[case]['natural']else 1)and target['opcode_PC']==(0xBC52 if CASES[case]['natural']else 0xBD59)
   if CASES[case]['natural']:
    assert len(writes)==25 and len(city)==4 and[e['value']for e in controller]==[3]
    assert[(e['opcode_PC'],e['address'],e['storage_byte_before_write'],e['physical_storage_byte_after_event'])for e in city]==[(0xBDB8,0x6091+i,255,ID)for i,ID in enumerate((8,191,51,167))]
   else:assert len(writes)==21 and not city and[e['value']for e in controller]==[0,3]
  public=[e for e in events if e['full_snapshot_sequence']and e['physical_bank']==8 and e['opcode_PC']in(0xA006,0xBAB3,0xBAC1,0xBB3D,0xBC46)and e['RAM0500_0503'][1]<2];assert public==ob['public_early_software_inputs']and len(public)=={'natural-stage0-human':3,'natural-stage1-mode0':4,'controlled-stage0-human':7}[case]
  for call in ob['phase2_ECEE_immediate_returns']:
   entry,ret,resume=[call[k]for k in('entry','before_RTS','resumed_parent')];assert(entry['opcode_PC'],ret['opcode_PC'],resume['opcode_PC'])==(0xECEE,0xED18,0xBB96)and entry['SP']==ret['SP']and resume['SP']==ret['SP']+2 and entry['frame']==ret['frame']==resume['frame']
  holds=ob['phase3_fresh_hold_callbacks'];release=ob['phase3_completion_callbacks'];assert all(not e['fade_0087_008A'][0]&128 for e in holds)and all(e['fade_0087_008A'][0]&128 for e in release)
  assert(len(holds),len(release),len(index))=={'natural-stage0-human':(0,0,9),'natural-stage1-mode0':(19,1,70),'controlled-stage0-human':(4,0,59)}[case]

 def core_provenance(self):
  folder=OUT/'runtime/core-provenance';v=self.record(folder/'build.json',False);assert v['commit']=='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
  assert v['first_build_clean_new_tree']and v['final_source_clean_build']and v['dependency_rebuild_byte_identical']and not v['modified_emulator_object_layout']and v['extra_emulated_bus_reads']==v['extra_emulated_bus_writes']==0
  for item in[v['original_core'],v['passive_observer'],v['parent_frozen_patch']]+v['unchanged_old_observers']:self.pin(item['path'],item['sha256'])
  assert v['original_core']['sha256']==CORE_SHA and v['passive_observer']['sha256']==OBSERVER_SHA
  patch=(folder/'observer.patch').read_bytes();assert digest(patch)==v['patch_sha256'];originals={x['path']:(folder/'upstream'/x['path']).read_bytes()for x in v['source_files']};generated=base.base.base.prior.apply_patch_readonly(patch,originals)
  for item in v['source_files']:assert digest(originals[item['path']])==item['original_sha256']and digest(generated[item['path']])==item['patched_sha256']
  for path in(folder/'patched').rglob('*'):
   if path.is_file():assert path.read_bytes()==generated[str(path.relative_to(folder/'patched'))]
  watch=generated['source/core/NstWatch.cpp.inc'].decode();board=generated['source/core/board/NstBoard.cpp'].decode();make=generated['libretro/Makefile'].decode()
  assert 'map.Peek'not in watch and 'map.Poke'not in watch and 'out[i]=b.wrk[0][i]'in board and 'e[17]=source[5];'in watch
  assert 'memory[0xDE]'in watch and 'memory[0xDF]'in watch and '++watch_overflow'in watch and '++watch_snapshot_overflow'in watch and v['include_dependency_declared']in make
  assert generated['source/core/NstCpu.hpp']==originals['source/core/NstCpu.hpp']
  self.counts['observer_upstream_source_files_patch_reconstructed_readonly']=len(originals)


 def static_fields(self):
  f=OUT/'fields-static';v=self.record(f/'verification.json');s=self.record(f/'analysis-summary.json');self.record(f/'evidence.json')
  assert v['source_CPU_cases']==v['Native_frames']==v['source_original_CPU_callbacks']==0 and v['failed_count']==0
  assert(v['original_contract_CPU_cases'],v['actual_caller_RTS_CPU_cases'],v['explicit_prefix_CPU_cases'],v['model_guard_check_count'])==(7188,7172,16,21)and len(v['model_checks'])==21 and v['actual_frozen29_input_count']==8 and v['new_Native_captures']==0
  expected=dict(proved_disjoint_auxiliary_address_domain=1200,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=245)
  assert s['all_indirect_classification_counts']==v['all_indirect_classification_counts']==expected and s['remaining_access_count']==v['remaining_access_count']==326 and s['previous_candidate_count']==328 and s['newly_proved_disjoint_all_count']==2 and not s['complete_analysis_fixed_point_proven']and all(x is None for x in s['official_target_field_names'].values())
  previous=read(ROOT/'analysis/phase27/fields-static/all-indirect-accesses.json');current=self.record(f/'all-indirect-accesses.json',False);selected=self.record(f/'selected-accesses.json',False);contract=self.record(f/'name-pointer-lifecycle-contract.json',False)
  assert len(previous['accesses'])==len(current['accesses'])==1526 and len(selected['accesses'])==2 and{(r['physical_bank'],r['cpu'])for r in selected['accesses']}=={(13,0xCC92),(13,0xCCAC)}
  oldrows={(r['physical_bank'],r['cpu']):r for r in previous['accesses']};newrows={(r['physical_bank'],r['cpu']):r for r in current['accesses']};assert set(oldrows)==set(newrows)
  selectedkeys={(r['physical_bank'],r['cpu'])for r in selected['accesses']};unchanged=0;aux={0x6000+32*city+offset for city in range(30)for offset in(1,28,29,30,31)}
  for key,row in newrows.items():
   before=oldrows[key];self.raw(row)
   if key not in selectedkeys:
    for field in('classification','address_contract','raw_hex','rom_offset','Y_values','whole_pointer_values'):
     assert row.get(field)==before.get(field),(key,field)
    unchanged+=1
   else:
    assert before['classification']=='unresolved_pointer_or_index_contract'and row['classification']==DISJOINT and row['address_contract']and row['candidate_contract_is_authoritative']is False
    c=row['address_contract'];assert c['required_execution_contract']and c['contract_scope']and c['auxiliary_address_intersection_count']==0 and c['possible_auxiliary_effective_addresses']==[]
    effective={(pointer+y)&65535 for pointer in c['whole_pointer_values']for y in c['Y_values']};assert not effective&aux and len(effective)==c['logical_effective_address_count']
  assert unchanged==1524 and Counter(r['classification']for r in newrows.values())==expected
  assert(f/'raw345-executability-ledger.json').read_bytes()==(ROOT/'analysis/phase24/fields-static/raw345-executability-ledger.json').read_bytes()
  assert len(contract['selected_targets'])==2 and contract['source_CPU_cases']==contract['Native_frames']==0 and len(contract['bare_counterexample_addresses'])==3
  for row in contract['original_instructions']:self.raw(row)
  self.counts.update(new_static_Source_CPU_cases=0,new_static_Native_frames=0,new_static_original_CPU_contract_cases=7188,new_static_contract_RTS=7172,new_static_contract_prefixes=16,new_static_model_premise_checks=21,new_static_exclusions=2,current_static_remaining_candidates=326,unchanged1524_static_contract_classifications=unchanged,raw345_bytes_unchanged=True)

 def context(self):
  f=OUT/'context';v=self.record(f/'verification.json');s=self.record(f/'analysis-summary.json',False);self.record(f/'evidence.json')
  assert v['Source_CPU_cases']==v['original_CPU_cases']==v['Native_runs']==0 and v['check_count']==len(v['checks'])==41 and all(x['status']=='passed'for x in v['checks'])and v['new_exclusions']==0
  assert not s['full_game_closure']and all(x is None for x in s['official_city_auxiliary_names'].values())and s['frozen29_baseline']['remaining']==328
  self.counts.update(context_reference_checks=41,context_Source_CPU_cases=0,context_original_CPU_cases=0,context_Native_runs=0)

 def source_cases(self):
  v=self.record(OUT/'early-services/validation.json');self.record(OUT/'early-services/evidence.json');c=self.record(OUT/'early-services/static-catalog.json',False)
  if v['quick']:raise Pending('Child Source still quick')
  assert v['failed_count']==0 and v['failures']==[]and v['original_CPU_parent_cases']==len(v['cases'])and Counter(x['comparison']for x in v['cases'])==v['counts']
  assert v['original_CPU_parent_cases']==1546 and v['controlled_cases']==1506 and v['passive_software_caller_cases']==40 and v['controlled_cases']+40==len(v['cases'])and v['counts']==dict(actual_caller_RTS=1540,strict_dependency_prefix=6)
  assert v['source_guard_count']==len(v['guards'])==11 and all(x['status']=='passed'for x in v['guards'])and v['source_original_CPU_callbacks']==0 and not v['production_IR_interpretation']and not v['Native_internal_CPU_trace']
  assert all(x['all2048_RAM_8192_SRAM_AXYP_SP_PC_combined_IO_four_banks_shared_N163_equal']and x['source_original_CPU_callbacks']==0 for x in v['cases'])
  assert(c['new_exact_protocol_positions'],c['new_exact_protocol_code_bytes'],c['inline_table_bytes'])==(410,912,6)and not c['new_semantic_first_recovery']
  visited={(x['physical_bank'],x['cpu_address'])for x in v['executed_instruction_positions']}
  for row in c['original_instructions']:
   bank=row.get('physical_bank',row.get('bank'));pc=row.get('cpu',row.get('pc'));self.raw(dict(row,physical_bank=bank,cpu=pc));assert(bank,pc)in visited
  assert v['original_BB36_parent_call_cases']>0 and v['original_BB8C_parent_call_cases']>0
  i=self.record(OUT/'source-integration.json');assert i['original_CPU_parent_cases']==len(i['rows'])and Counter(x['completion']for x in i['rows'])==i['counts']and i['guard_count']==len(i['guards'])and i['source_original_CPU_callbacks']==0
  assert all(x['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and x['combined_logical_IO_order_equal']and x['source_original_CPU_callbacks']==0 for x in i['rows'])and Counter(x['comparison']for x in i['rows'])==i['comparison_counts']
  assert i['inherited_regression_cases']==115 and i['new_controlled_AI_stage0_cases']==2 and i['new_early_caller_cases']==14 and i['original_CPU_parent_cases']==131 and i['counts']==dict(returned=130,nonlocal_return=1)and i['guard_count']==4
  assert not i['production_IR_interpretation']and not i['Native_internal_CPU_trace']and i['inherited_ECEE_regression_dynamically_rerun_on_new_owner']==1
  regressions=[x for x in i['rows']if x.get('ECEE_regression')];assert len(regressions)==1;reg=regressions[0]['ECEE_regression'];assert reg['initial_missing']and reg['fake_return_checks']==2 and reg['same_original_call']and reg['same_owner_and_generator']and reg['unchanged_RAM_SRAM_registers_banks_IO_on_fake']and reg['real_Shared_continuation']and reg['real_Shared_ECEE_resolutions']==reg['parent_ECEE_call_records']==1 and reg['no_restart_or_repeated_partial_effects_compared_to_originalCPU']
  for name in('postbattle_early_services.py','postbattle_early_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,ast.Import):assert all(not x.name.startswith(('py65','capture_','nes_runtime'))for x in node.names)
    if isinstance(node,ast.ImportFrom):assert not(node.module or'').startswith(('py65','capture_','nes_runtime'))
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.actual_contexts30()
  self.counts.update(source_child_CPU_cases=len(v['cases']),source_child_guards=v['source_guard_count'],source_integration_CPU_cases=len(i['rows']),source_integration_guards=i['guard_count'],new_Source_CPU_cases=len(v['cases'])+len(i['rows']),new_Source_guards=v['source_guard_count']+i['guard_count'],new_Source_actual_caller_RTS=v['counts'].get('actual_caller_RTS',0)+i['counts'].get('returned',0),new_Source_nonlocal_return=i['counts'].get('nonlocal_return',0),new_Source_strict_dependency_prefix=v['counts'].get('strict_dependency_prefix',0)+i['counts'].get('dependency',0),new_semantic_first_recovery=0)

 def actual_contexts30(self):
  paths=sorted((OUT/'cpu-early/actual-callers').glob('entry-*/context.json'))
  if len(paths)!=14:raise Pending('Final14 actual early software caller exports not all present')
  controlled=natural=0;integration=read(OUT/'source-integration.json');rootrows={x['case'].split('/',1)[1]:x for x in integration['rows']if x['case'].startswith('postbattle-early/')};assert set(rootrows)=={x.parent.name for x in paths}
  ancestry=read(OUT/'runtime/evidence.json')['case_ancestry'];event_cache={}
  for path in paths:
   row=self.record(path,False);assert row['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and row['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'and row['prepared_numeric_bytes']==row['additional_CPU_prepared_numeric_bytes']==[]and row['injected_new_NMI']==row['injected_new_IRQ']==0 and not row['synthetic_caller_PC_or_stack']
   capture=row['passive_capture'];self.pin(capture['metadata'],capture['metadata_sha256']);meta=read(ROOT/capture['metadata']);self.pin(capture['manifest'],capture['manifest_sha256']);r=(ROOT/capture['RAM_path']).read_bytes();s=(ROOT/capture['SRAM_path']).read_bytes();self.pin(capture['RAM_path'],capture['RAM_sha256']);self.pin(capture['SRAM_path'],capture['SRAM_sha256'])
   assert r==(path.parent/'input-ram.bin').read_bytes()and s==(path.parent/'input-sram.bin').read_bytes()and row['registers']==meta['actual_registers']and row['physical_banks']==meta['actual_PRG_banks']and row['actual_software_state_captured']and not row['unmodified_core_internal_trace']
   case=next(x for x in CASES if '/'+x+'/'in capture['metadata']);assert row['ancestry_provenance']==ancestry[case]and row['controlled_ancestry']==(not CASES[case]['natural'])and row['natural_ordinary_input_route']==CASES[case]['natural']
   assert row['inherited_Native_preparation']==ancestry[case]['known_inherited_preparation']and row['known_inherited_preparation_byte_writes']==ancestry[case]['known_inherited_preparation_byte_writes']
   self.pin(capture['events_path'],capture['events_sha256']);self.pin(capture['preparation_path'],capture['preparation_sha256'])
   if case not in event_cache:event_cache[case]={e['sequence']:e for e in map(json.loads,(ROOT/capture['events_path']).read_text().splitlines())}
   events=event_cache[case];event=events[capture['event_sequence']];assert event['full_snapshot_sequence']==meta['snapshot_sequence']==capture['snapshot_sequence']and event['frame']==meta['frame']==capture['frame']and event['opcode_PC']==row['registers']['pc']
   assert event['actual_PRG_banks']==row['physical_banks']and meta['capture_core_sha256']==OBSERVER_SHA and not meta['instantaneous_N163_PPU_APU_captured']
   parent=rootrows[path.parent.name];assert parent['origin']==row['origin']and parent['prepared_new_bytes']is False and parent['initial_registers']==row['registers']and parent['inherited_Native_preparation']==row['inherited_Native_preparation']and parent['N163_context_origin']==row['N163_origin']and parent['caller_kind']==row['actual_call_kind']
   assert parent['ancestry_context']=={key:row[key]for key in('ancestry_origin','controlled_ancestry','natural_ordinary_input_route','known_inherited_preparation_byte_writes','ancestry_provenance','actual_call_kind','immediate_transfer_PC','immediate_transfer_proof','real_return_frame_owner')}
   if row['controlled_ancestry']:controlled+=1;assert len(row['inherited_Native_preparation'])==row['known_inherited_preparation_byte_writes']==19
   else:natural+=1;assert not row['inherited_Native_preparation']and row['known_inherited_preparation_byte_writes']==0
   assert row['stage']in(0,1)and row['registers']['pc']in(0xA006,0xBAB3,0xBAC1,0xBB3D,0xBC46)and row['owner_scope']=='Root_NEW5_and_child'
   sp=row['registers']['sp'];assert row['existing_return_PC']==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535
   if row['immediate_transfer_PC']is None:assert row['registers']['pc']in(0xBAC1,0xBB3D)and row['actual_call_kind']=='unknown'
   else:
    proof=row['immediate_transfer_proof'];assert proof is not None and proof['not_inferred_from_return_stack']and proof['callee_opcode_boundary']==event
    previous=proof['previous_watched_opcode_boundary'];assert previous==events[previous['sequence']]and previous['opcode_PC']==row['immediate_transfer_PC']and previous['sequence']<event['sequence']
    assert bytes.fromhex(proof['previous_ROM_bytes'])==self.rom[previous['rom_offset']:previous['rom_offset']+3]
   fixture=(path.parent/'input-n163.bin').read_bytes();assert len(fixture)==128 and digest(fixture)==row['explicit_N163_fixture']['sha256']and row['N163_address']==127 and row['N163_autoincrement']
  assert(controlled,natural)==(7,7);assert Counter(read(path)['actual_call_kind']for path in paths)==dict(trampoline=4,far_indirect_jump=4,unknown=4,call=2);self.counts.update(actual_passive_software_context_exports=14,unique_new_passive_software_inputs=14,inherited_child_passive_inputs=26,new_child_passive_inputs=14,Root_new_passive_inputs=14,actual_parent_ancestry_row_checks=14,production_new_Source_AST_syntax_checks=2)


 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing Root final report')
  qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'README.md');self.pin(OUT/'index.html',qa['final_html_sha256']);assert qa['status']=='passed'and qa['failed_count']==0 and qa['check_count']==len(qa['checks'])and all(x['status']=='passed'for x in qa['checks'])
  assert qa['console_errors']==qa['console_warnings']==[]and qa['Native_frames_added']==qa['Source_CPU_cases_added']==0
  page=base.base.base.PortalPage();page.feed((OUT/'index.html').read_text());payload=json.loads(page.evidence)
  for name in('postbattle_early_services.py','postbattle_early_integration.py'):assert(ROOT/'source/recovered'/name).read_text()in page.sources
  assert len(page.sources)==2 and payload['native']==read(OUT/'runtime/evidence.json')['summary']and payload['acceptance']==read(OUT/'acceptance/requirements.json')and payload['context_checks']==41
  for name,path in(('branches','context/early-stage-branches-and-callers.json'),('boundaries','context/ruler-and-name-pointer-boundaries.json'),('credit','context/historical-credit-and-return-erratum.json'),('ledger','fields-static/analysis-summary.json'),('selected_field_contracts','fields-static/selected-accesses.json'),('name_lifecycle','fields-static/name-pointer-lifecycle-contract.json')):assert payload[name]==read(OUT/path)
  for name,keys,path in(('source',('original_CPU_parent_cases','controlled_cases','passive_software_caller_cases','counts','source_guard_count'),'early-services/validation.json'),('integration',('original_CPU_parent_cases','inherited_regression_cases','new_controlled_AI_stage0_cases','new_early_caller_cases','new_early_targets','new_early_ancestries','comparison_counts','guard_count'),'source-integration.json'),('fields',('original_contract_CPU_cases','counts','actual_caller_RTS_CPU_cases','explicit_prefix_CPU_cases','model_guard_check_count','remaining_access_count','all_indirect_classification_counts','newly_proved_disjoint_all_count'),'fields-static/verification.json')):
   full=read(OUT/path);assert payload[name]=={key:full[key]for key in keys}
  def event_objects(value):
   if isinstance(value,dict):
    if all(k in value for k in('sequence','opcode_PC','actual_PRG_banks','kind')):yield value
    else:
     for x in value.values():yield from event_objects(x)
   elif isinstance(value,list):
    for x in value:yield from event_objects(x)
  def compact(value):
   if isinstance(value,dict):
    if all(k in value for k in('sequence','opcode_PC','actual_PRG_banks','kind')):return{key:value[key]for key in('sequence','frame','opcode_PC')}
    return{key:compact(x)for key,x in value.items()}
   if isinstance(value,list):return[compact(x)for x in value]
   return value
  native=read(OUT/'runtime/evidence.json');observations=read(OUT/'runtime/early-lifecycle-observations.json');assert[x['case']for x in payload['routes']]==list(CASES);point_count=event_count=0
  roles=dict(early_original_entries='early_stage_entry',public_early_software_inputs='actual_software_input',actual_BC46_calls='actual_BC46_JSR_and_entry',mode_targets='original_mode_dispatch',controller_byte_reads='actual_controller_read',original_mode_writes='original_mode_write',early_SRAM_writes='early_SRAM_store',early_city_roster_writes='early_city_roster_store',phase2_ECEE_immediate_returns='ECEE_immediate_request_RTS',phase3_fresh_hold_callbacks='fresh_stage3_hold',phase3_completion_callbacks='fresh_stage3_completion')
  for route in payload['routes']:
   case=route['case'];folder=OUT/'runtime'/case;points=read(folder/'original-control/checkpoints.json');assert route['points']==points==route['observer_points']==read(folder/'observer/checkpoints.json')and route['base']=='runtime/'+case+'/'and route['ancestry']==native['case_ancestry'][case]and all(len(p['fields'])==35 for p in points)
   life=next(x for x in observations['routes']if x['case']==case);assert route['lifecycle']==compact(life);selected={}
   for key,role in roles.items():
    for event in event_objects(life[key]):
     seq=event['sequence']
     if seq not in selected:selected[seq]=dict(event,display_roles=[])
     else:assert{k:v for k,v in selected[seq].items()if k!='display_roles'}==event
     if role not in selected[seq]['display_roles']:selected[seq]['display_roles'].append(role)
   assert route['events']==[selected[k]for k in sorted(selected)]and len(route['audio'])==2
   for variant,audio in zip(('original-control','observer'),route['audio']):
    path=OUT/audio['path'];assert path==folder/variant/'full-audio.wav';self.pin(path,audio['sha256'])
    with wave.open(str(path))as wav:assert(audio['sample_frames'],audio['duration_seconds'])==(wav.getnframes(),wav.getnframes()/48000)
   point_count+=len(points);event_count+=len(selected)
  assert(point_count,event_count)==(48,102)
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path in(OUT/'verification.json',OUT/'package-receipt.json'):continue
   assert path.is_file(),('Broken portal link',link)
  for name,pin in qa['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  self.counts.update(browser_checks=qa['check_count'],browser_Source_modules=len(page.sources),browser_original_points=point_count,browser_original_fields_per_point=35,browser_original_selected_events=event_count)

 def acceptance(self):
  f=OUT/'acceptance';v=self.record(f/'verification.json');r=self.record(f/'requirements.json',False);p=self.record(f/'request-provenance.json',False)
  assert v['source_CPU_cases']==v['original_CPU_cases']==v['Native_frames']==0 and not r['overall_reverse_engineering_complete']and r['completion_percentage']is None and v['direct_user_message_locator_checks']==11 and v['dimension_status_and_receipt_checks']==10 and v['coordinator_report_separately_labelled']
  messages={x['message_id']:x for x in p['source_messages']};locators={x['request_id']:x for x in p['request_locators']};assert len(locators)==11 and len(r['dimensions'])==10
  assert v['evidence_reference_checks']>=128 and v['source_syntax_checks']>=102 and v['current_summary_cross_receipt_checks']==10
  for user in r['user_request_register']:
   locator=locators[user['id']];message=messages[locator['message_id']];assert user['quote']in message['text']and locator['turn_id']==message['turn_id']and message['source_kind']=='read_thread_userMessage'
   source=user['source'];assert source['source_kind']=='direct_human_userMessage'and source['message_id']==locator['message_id']and source['turn_id']==locator['turn_id']
  assert p['coordination_report']['source_kind']=='coordinator_delegation_report'and p['coordination_report']['not_verbatim_user_quote']
  for row in r['dimensions']:
   assert row['acceptance_status']and row['verified_results']and row['pending_results']and row['phase30_change']['result']and row['phase30_change']['remaining_gap']
   for item in row['verified_results']:assert item['claim']and item['evidence']in row['evidence'];self.pin(item['evidence'])
  self.counts.update(acceptance_dimensions=10,acceptance_exact_user_message_locators=11,acceptance_reference_checks_not_gameplay=v['evidence_reference_checks'],acceptance_Source_syntax_checks_not_CPU=v['source_syntax_checks'],acceptance_Source_CPU_cases=0,acceptance_Native_frames=0)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA
 audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[];audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('context',audit.context),('acceptance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');audit.pin(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP and manifest['foundational_archive']['sha256']==V22_ZIP and manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase30']
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in base.base.base.prior.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots']);names=set(manifest['include_files']);included={k:v for k,v in audit.pins.items()if k in names or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase30-postbattle-early-readonly-audit-v1',status='pending_final_artifacts'if pending else'passed',ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v29_incremental_preserved_sha256=OLD_ZIP,old_phase29_audit_sha256=OLD_AUDIT,old_phase29_postZIP_receipt_sha256=OLD_POSTZIP,old_v22_preserved_sha256=V22_ZIP,source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guards',0),source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),limits=['Read-only evidence audit; no CPU/core/producers/analyzers/old audit main executed.','Three separate ordinary-input imported windows: two natural ancestries, one controlled ancestry with19 known bytes and incomplete earlierlegacy preparation.','Separate30 observer alone supplies internal events, no instantaneous N163/PPU/APU.','Native observes humanBAC1 and AIstage1 BB8C modes0/1; BB36/mode2 are CPU matrix coverage, not observed Native closure.','ECEE immediatelyRTS and later BBA0 is a fresh NMI callback; no artificialack.','Source cases/static CPU contracts/context/reference checks/Native frames remain separate;wholeROM and standalone source completion unproven.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))
if __name__=='__main__':main()
