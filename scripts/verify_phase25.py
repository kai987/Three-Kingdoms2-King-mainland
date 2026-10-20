#!/usr/bin/env python3
"""Read-only phase25 audit; writes only the new verification.json.

No CPU, core, analyzer, capture, service producer or old audit main is run.
The known reserve submission, selected G033 context, static contracts, service
inventory and acceptance metadata remain distinct proof/observation scopes.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys,wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase25'
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('readonly_phase24_audit',ROOT/'scripts/verify_phase24.py')
prior=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=prior;SPEC.loader.exec_module(prior)
from capture_native_appearance_pointer import decode_event,fields,CASES
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=prior.ROM_SHA;sha=prior.sha;read=prior.read;original=prior.original;DISJOINT=prior.DISJOINT;Pending=prior.Pending
OLD_AUDIT='b319b0890cf3a27d26463bd55aa98e3a67df3f3209856d8a11e17cd3ad238385'
OLD_ZIP='a0032b3d39b3cbc26707e626319809f8a306a47033ba1a552aca4f8c8a896cfc'
OLD_POSTZIP='54ea3e14f82ddbaea778af7680e08334a75dffa5af8451f4022a37a4b3928a5b'
V23_ZIP='7b141e38fdc88e6c601d10705b255bb48f04e1047cd0ab40ffa588490bf17e51'
V22_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
ORIGINAL_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
OBSERVER_SHA='7ce7eb671327d6bcf629a1b5a5e43fa6a4184781bb75a6db91b0c1ed5c2b82f0'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(path):return str(Path(path).resolve().relative_to(ROOT))
class PortalPage(prior.prior.old.prior.Page):
 def handle_starttag(self,tag,attrs):
  super().handle_starttag(tag,attrs)
  if tag=='script'and dict(attrs).get('id')=='evidence-data':self.in_evidence=True

class Audit(prior.Audit):
 def frozen_history(self):
  self.pin('analysis/phase24/verification.json',OLD_AUDIT);v=read(ROOT/'analysis/phase24/verification.json')
  assert v['status']=='passed'and v['pending']==[]and v['ROM_sha256']==ROM_SHA and v['rebuilt_byte_identical']
  assert(len(v['source_and_validator_sha256']),len(v['artifact_and_dependency_sha256']))==(496,40177)
  self.frozen_names=set(v['source_and_validator_sha256'])|set(v['artifact_and_dependency_sha256'])
  for name,pin in v['source_and_validator_sha256'].items():self.pin(name,pin);self.sources[name]=pin
  for name,pin in v['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  self.pin('analysis/phase24/package-receipt.json',OLD_POSTZIP);receipt=read(ROOT/'analysis/phase24/package-receipt.json')
  assert receipt['status']=='passed'and receipt['phase24_audit_sha256']==OLD_AUDIT and receipt['sha256']==OLD_ZIP
  for name,pin in [('三国志2超级版-逆向分析-v24增量.zip',OLD_ZIP),('三国志2超级版-逆向分析-v23增量.zip',V23_ZIP),('三国志2超级版-逆向分析-v22.zip',V22_ZIP),('三国志2超级版-逆向分析.zip',V22_ZIP)]:self.pin(ROOT/'build'/name,pin)
  assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.counts.update(unchanged_phase24_source_script_pins=496,unchanged_phase24_artifact_dependency_pins=40177,unchanged_phase24_postZIP_receipts=1)

 def runtime(self):
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json')
  assert e['summary']=={k:v[k]for k in e['summary']}
  self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_appearance_pointer.py',v['script_sha256'])
  assert(v['natural_routes'],v['core_variants'],v['fresh_process_runs'],v['original_first_frames'],v['all_control_frames'])==(2,2,8,106,424)
  assert(v['original_checkpoints'],v['nonempty_artifact_repeat_checks'],v['PNG_checks'],v['WAV_checks'],v['observer_events'])==(106,1091,212,4,41104)
  assert v['additional_core_memory_writes']==v['ancestor_preparation_bytes']==v['cold_boots']==v['Source_CPU_cases']==v['failed_count']==0 and v['state_imports']==8
  assert v['all_five_complete_buffers_equal_each_frame']and v['all_complete_initial_API_buffers_equal']and v['all_artifacts_repeat_exact']and v['full_serialized_buffers_not_normalized']
  self.pin('.toolchain/nestopia/nestopia_libretro.dylib',ORIGINAL_SHA);self.pin('.toolchain/phase25-observer/observed/nestopia_libretro.dylib',OBSERVER_SHA)
  artifacts=images=audio=0;event_count=snapshots=0
  for case,config in CASES.items():
   mother=ROOT/config['mother'];self.pin(mother);m=NestopiaContext.parse(mother.read_bytes());original_rows=None
   for variant in('original-control','observer'):
    first=folder/case/variant;second=OUT/'runtime-repeat'/case/variant;a=self.record(first/'validation.json');b=self.record(second/'validation.json');repeat=self.record(first/'repeat-validation.json');assert a==b
    assert a['status']=='passed'and a['frames']==config['frames']and a['checkpoint_count']==config['frames']
    assert a['core']['core_sha256']==(OBSERVER_SHA if variant=='observer'else ORIGINAL_SHA)
    assert a['state_imported']and not a['cold_boot']and a['additional_core_memory_writes']==a['inherited_preparation_byte_writes']==a['Source_CPU_cases']==0
    assert not a['original_core_internal_CPU_trace']and a['full_serialized_buffers_not_normalized']
    assert repeat['all_bytes_exact']and repeat['artifact_checks']==len(a['artifact_sha256'])
    prep=self.record(first/'preparation.json',False);assert prep['preparation']==[]and prep['additional_core_memory_writes']==prep['inherited_preparation_byte_writes']==0
    n=NestopiaContext.parse((first/'initial.state').read_bytes());assert n.ram==m.ram and n.sram==m.sram and n.registers==m.registers and n.prg_banks==m.prg_banks
    assert(first/'initial-ram.bin').read_bytes()==m.ram and(first/'initial-sram.bin').read_bytes()==m.sram
    for name,pin in a['artifact_sha256'].items():
     assert pin['bytes']>0
     for path in(first/name,second/name):assert path.stat().st_size==pin['bytes'];self.pin(path,pin['sha256'])
     artifacts+=1
    rows=read(first/'frame-services.json');points=read(first/'checkpoints.json');callbacks=read(first/'audio-callbacks.json');plan=read(first/'input-plan.json')
    assert len(rows)==len(points)==len(callbacks)==config['frames']
    assert[(x['frames'],tuple(x['buttons']),x['label'])for x in plan]==config['plans']
    if original_rows is None:original_rows=rows
    assert rows==original_rows
    with wave.open(str(first/'full-audio.wav'))as wav:
     assert(wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
     for i,(row,point,cb)in enumerate(zip(rows,points,callbacks),1):
      assert row['frame']==point['frame']==i and cb['emulated_frame_start']==i-1
      pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']
      assert len(pcm)==row['PCM_bytes']and wav.tell()*4==row['PCM_stop_byte']
      r=(first/point['RAM']).read_bytes();s=(first/point['SRAM']).read_bytes();state=(first/point['state']).read_bytes()
      assert len(r)==2048 and len(s)==8192 and digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']
      assert digest(state)==row['whole_serialized_state_sha256']and len(state)==row['whole_serialized_state_bytes']
      n=NestopiaContext.parse(state);assert n.ram==r and n.sram==s and n.registers==row['actual_saved_CPU_registers']and list(n.prg_banks)==row['actual_saved_PRG_banks']
      assert all(row[k]==value for k,value in fields(r,s).items())
      with Image.open(first/point['image'])as im:im.load();assert im.size==(256,240)and im.mode=='RGB'and digest(im.tobytes())==row['RGB_sha256']
      images+=1
     assert not wav.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and wav.tell()*4==a['full_audio']['PCM_bytes']
     assert wav.getnframes()==a['full_audio']['stereo_sample_frames']==(17571 if config['frames']==22 else 67090);audio+=1
    if case=='natural-appearance-pointer':
     assert a['initial_fields']['officer152_status_code']==1 and a['final_fields']['officer152_status_code']==2
     assert rows[2]['officer152_status_code']==1 and rows[3]['officer152_status_code']==2 and rows[-1]['request_6F8B']==255
    else:
     assert a['initial_fields']['officers']['30']['troops_raw16']==a['final_fields']['officers']['30']['troops_raw16']==900
     assert a['initial_fields']['working_reserve_042C_042D']==9899 and a['initial_fields']['city_reserve_raw16']==9999
     assert a['final_fields']['city_reserve_raw16']==9899 and a['final_fields']['city_state_0400_0403'][:2]==[0,1]
    if variant=='observer':
     n,s=self.observer(first,a,case);event_count+=n;snapshots+=s
   for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):
    assert(folder/case/'original-control'/name).read_bytes()==(folder/case/'observer'/name).read_bytes()
  assert(artifacts,images,audio,event_count,snapshots)==(1091,212,4,41104,85)
  self.core_provenance()
  self.counts.update(native_routes=2,native_original_first_frames=106,native_all_control_frames=424,native_fresh_process_runs=8,native_state_imports=8,native_cold_boots=0,
   native_preparation_bytes=0,native_nonempty_repeat_checks=1091,native_PNG_checks=212,native_WAV_checks=4,observer_event_records=41104,observer_full_2K_8K_snapshots=85,
   native_G033_table_reads=6,native_actual_officer_status_writes=1,native_actual_roster_writes=1,native_known_reserve_stores=2,native_reserve_dummy_reads=2,native_city_auxiliary_bus_events=0)

 def observer(self,folder,receipt,case):
  events=[json.loads(x)for x in(folder/'events.jsonl').read_text().splitlines()];raw=(folder/'bus-events.bin').read_bytes();assert len(raw)==160*len(events)==160*receipt['observer_events']['count']
  for i,e in enumerate(events):
   assert decode_event(raw[i*160:(i+1)*160],sequence=i+1)==e
   if e['opcode_PC']is not None and e['opcode_PC']>=0x8000:assert e['physical_bank']==e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]and e['rom_offset']==original(e['physical_bank'],e['opcode_PC'])
   if e['target_type']=='pointer_RAM_write':assert e['kind']=='write_attempt'and e['physical_storage_byte_after_event']is None and e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
  assert not any(x['target_type']=='city_auxiliary_bus'for x in events)
  schema=self.record(folder/'event-schema.json',False);assert len(schema['raw_layout'])==schema['words']==40 and schema['bytes_per_record']==160
  snapshots=(folder/'snapshots.bin').read_bytes();index=[json.loads(x)for x in(folder/'snapshot-index.jsonl').read_text().splitlines()]
  assert len(index)==receipt['observer_events']['full_RAM_SRAM_snapshots']and len(snapshots)==10240*len(index)
  by_sequence={x['sequence']:x for x in events}
  for i,item in enumerate(index,1):
   e=by_sequence[item['event_sequence']];payload=snapshots[(i-1)*10240:i*10240];r,s=payload[:2048],payload[2048:]
   assert item['snapshot_sequence']==e['full_snapshot_sequence']==i and item['entry']==e['opcode_PC']and item['physical_bank']==e['physical_bank']
   assert digest(payload)==item['sha256']and digest(r)==item['RAM_sha256']and digest(s)==item['SRAM_sha256']
   assert list(r[:0x30])==e['ZP_0000_002F']and r[0x36]==item['current_city_0036']==e['current_city_0036']
   assert item['actual_registers']==dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC'])
   assert item['actual_PRG_banks']==e['actual_PRG_banks']and not item['instantaneous_N163_PPU_APU_captured']and item['capture_core_sha256']==OBSERVER_SHA
   assert item['additional_core_memory_writes']==item['inherited_preparation_byte_writes']==0
   if 'exported_RAM'in item:assert(folder/item['exported_RAM']).read_bytes()==r and(folder/item['exported_SRAM']).read_bytes()==s
  observation=self.record(OUT/'runtime'/case/'opcode-observations.json',False)
  if case=='natural-appearance-pointer':
   data=[x for x in events if x['target_type']=='appearance_ROM_bus'];assert data==observation['table_reads']and len(data)==6
   for e in data:
    assert e['kind']=='read'and e['physical_bank']==11 and e['opcode_PC']in(0xC61F,0xC624)
    assert e['address']==(e['pointer_0022_0023']+e['Y'])&65535 and e['actual_PRG_banks'][0]==17
    assert e['value']==self.rom[original(17,e['address'])]
   hit=next(e for e in data if e['value']==152);assert(hit['frame'],hit['current_city_0036'],hit['address'],hit['Y'])==(4,3,0x8B58,0)
   status=[x for x in events if x['target_type']=='officer_status_write'];roster=[x for x in events if x['target_type']=='city_roster_write']
   assert status==observation['status_writes']and roster==observation['roster_writes']and len(status)==len(roster)==1
   assert(status[0]['opcode_PC'],status[0]['officer_index'],status[0]['value'])==(0xC659,152,26)
   assert roster[0]['city_index']==3 and roster[0]['value']==152 and roster[0]['physical_storage_byte_after_event']==152
   assert all(x==by_sequence[x['sequence']]for x in observation['producer_boundaries'])
  else:
   bus=[x for x in events if x['target_type']=='city_reserve_submission_bus'];assert bus==observation['reserve_bus_events']and len(bus)==4
   assert[(x['kind'],x['physical_bank'],x['opcode_PC'],x['address'],x['value'])for x in bus]==[
    ('read',27,0xB449,0x616C,15),('write_attempt',27,0xB449,0x616C,171),('read',27,0xB44F,0x616D,39),('write_attempt',27,0xB44F,0x616D,38)]
   assert all(x['frame']==23 and x['pointer_0000_0001']==0x6160 for x in bus)
  return len(events),len(index)

 def core_provenance(self):
  folder=OUT/'runtime/core-provenance';build=self.record(folder/'build.json',False)
  assert build['commit']=='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'and build['first_build_clean_new_tree']and not build['modified_emulator_object_layout']and build['extra_emulated_bus_reads']==0
  self.pin(build['original_core']['path'],ORIGINAL_SHA);self.pin(build['passive_observer']['path'],OBSERVER_SHA)
  self.pin(build['unchanged_old_observer']['path'],'16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31')
  self.pin(build['parent_corrected_patch']['path'],build['parent_corrected_patch']['sha256']);patch=(folder/'observer.patch').read_bytes();self.pin(folder/'observer.patch',build['patch_sha256'])
  originals={x['path']:(folder/'upstream'/x['path']).read_bytes()for x in build['source_files']};generated=prior.apply_patch_readonly(patch,originals)
  for item in build['source_files']:assert digest(originals[item['path']])==item['original_sha256']and digest(generated[item['path']])==item['patched_sha256']
  for path in(folder/'patched').rglob('*'):
   if path.is_file():assert path.read_bytes()==generated[str(path.relative_to(folder/'patched'))]
  watch=generated['source/core/NstWatch.cpp.inc'].decode();board=generated['source/core/board/NstBoard.cpp'].decode();make=generated['libretro/Makefile'].decode()
  assert 'map.Peek'not in watch and 'map.Poke'not in watch and 'out[i]=b.wrk[0][i]'in board
  assert 'e[17]=source[5];'in watch and 'watch_snapshot_provider(watch_board,s+2048)'in watch
  assert build['include_dependency_declared']in make and '++watch_overflow'in watch and '++watch_snapshot_overflow'in watch
  self.counts['observer_upstream_source_files_patch_reconstructed_readonly']=len(originals)

 def source_cases(self):
  folder=OUT/'appearance';v=self.record(folder/'validation.json');e=self.record(folder/'evidence.json');catalog=self.record(folder/'static-catalog.json',False)
  if v.get('quick'):raise Pending('Child Source matrix is quick')
  assert v['failed_count']==0 and v['failures']==[]and v['original_CPU_parent_cases']==len(v['cases'])
  assert Counter(x['comparison']for x in v['cases'])==v['counts']and v['source_guard_count']==len(v['guards'])and all(x['status']=='passed'for x in v['guards'])
  assert v['source_original_CPU_callbacks']==0 and not v['production_IR_interpretation']and not v['Native_internal_CPU_trace']
  self.pin(e['source_path'],e['source_sha256'][e['source_path']]if isinstance(e['source_sha256'],dict)else e['source_sha256'])
  assert e['newly_named_original_instruction_positions']==catalog['newly_named_original_instruction_positions']==len(catalog['original_instructions'])==19
  assert e['newly_named_original_bytes']==catalog['newly_named_original_bytes']==35
  visited={(x['physical_bank'],x['cpu_address'])for x in v['executed_instruction_positions']}
  for instruction in catalog['original_instructions']:
   self.raw(instruction);assert(instruction['physical_bank'],instruction['cpu'])in visited
  for row in v['cases']:assert(row['RAM_bytes'],row['SRAM_bytes'])==(2048,8192)and row['AXYP_SP_PC_ordered_IO_four_banks_N163_equal']and row['source_original_CPU_callbacks']==0
  integration=self.record(OUT/'source-integration.json');assert len(integration['rows'])==integration['original_CPU_parent_cases']
  assert integration['counts']==Counter(x['completion']for x in integration['rows'])and integration['source_original_CPU_callbacks']==0
  assert all(x['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and x['source_original_CPU_callbacks']==0 for x in integration['rows'])
  assert integration['guard_count']==len(integration['guards'])
  assert v['original_CPU_parent_cases']==2992 and v['counts']==dict(actual_caller_RTS=2991,strict_missing_dependency_prefix=1)
  assert integration['original_CPU_parent_cases']==45 and integration['counts']==dict(returned=44,nonlocal_return=1)
  assert v['source_guard_count']==integration['guard_count']==3
  self.actual_contexts()
  for name in('appearance_pointer_services.py','appearance_pointer_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
     values=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module or''];assert not any(any(b in x for b in('py65','state_machine','importlib'))for x in values)
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.counts.update(source_child_CPU_cases=v['original_CPU_parent_cases'],source_child_guards=v['source_guard_count'],source_integration_CPU_cases=integration['original_CPU_parent_cases'],source_integration_guards=integration['guard_count'],
   new_Source_CPU_cases=v['original_CPU_parent_cases']+integration['original_CPU_parent_cases'],new_Source_guard_cases=v['source_guard_count']+integration['guard_count'],
   new_Source_actual_caller_RTS=v['counts'].get('actual_caller_RTS',0)+integration['counts'].get('returned',0),
   new_Source_nonlocal_return=integration['counts'].get('nonlocal_return',0),new_Source_strict_dependency_prefix=v['counts'].get('strict_missing_dependency_prefix',0))
  self.counts.update(new_manual_code_bytes=35,new_manual_instruction_positions=19,reused_C5D2_body_not_counted_as_new=True)

 def actual_contexts(self):
  paths=sorted((OUT/'cpu-appearance/actual-callers').glob('entry-*/context.json'))+[OUT/'cpu-submit/actual-callers/entry-B431-observer-0023/context.json']
  assert len(paths)==3
  for path in paths:
   row=self.record(path,False);assert row['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'
   assert row['prepared_numeric_bytes']==row['additional_CPU_prepared_numeric_bytes']==[]and row['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   assert row['N163_address']==127 and row['N163_autoincrement']
   if 'passive_capture'in row:
    c=row['passive_capture'];self.pin(c['metadata'],c['metadata_sha256']);meta=read(ROOT/c['metadata'])
    r=(ROOT/c['RAM_path']).read_bytes();s=(ROOT/c['SRAM_path']).read_bytes();self.pin(c['RAM_path'],c['RAM_sha256']);self.pin(c['SRAM_path'],c['SRAM_sha256'])
    self.pin(c['manifest'],c['manifest_sha256']);return_pc=row['existing_return_PC']
    assert not row['synthetic_caller_PC_or_stack']and not row['unmodified_core_internal_trace']and row['actual_software_state_captured']
    assert row['injected_new_NMI']==row['injected_new_IRQ']==0
   else:
    self.pin(row['capture'],row['capture_sha256']);meta=read(ROOT/row['capture']);assert row['original_software_caller_frame_preserved']and not row['instantaneous_N163_PPU_APU_captured']
    for name,pin in row['exact_capture_input_pins'].items():self.pin(name,pin)
    capture=Path(row['capture']);r=capture.with_name(capture.stem+'-ram.bin').read_bytes()if capture.is_absolute()else(ROOT/capture).with_name(capture.stem+'-ram.bin').read_bytes()
    s=(ROOT/capture).with_name(capture.stem+'-sram.bin').read_bytes();return_pc=row['actual_caller_return_pc']
   assert r==(path.parent/'input-ram.bin').read_bytes()and s==(path.parent/'input-sram.bin').read_bytes()
   assert len(r)==2048 and len(s)==8192 and len((path.parent/'input-n163.bin').read_bytes())==128
   assert row['registers']==meta['actual_registers']and row['physical_banks']==meta['actual_PRG_banks']
   sp=row['registers']['sp'];assert return_pc==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535
  self.counts.update(actual_passive_software_callee_exports=3,instant_N163_captures=0)

 def static_fields(self):
  folder=OUT/'fields-static';v=self.record(folder/'verification.json');s=self.record(folder/'analysis-summary.json');self.record(folder/'evidence.json')
  assert v['source_CPU_cases']==s['source_CPU_cases']==0
  old={(x['physical_bank'],x['cpu']):x for x in read(ROOT/'analysis/phase24/fields-static/all-indirect-accesses.json')['accesses']}
  data=self.record(folder/'all-indirect-accesses.json',False);canonical={(x['physical_bank'],x['cpu']):x for x in data['accesses']}
  assert len(canonical)==1526 and set(canonical)==set(old)
  for key,row in canonical.items():
   self.raw(row);proof=row['address_contract']
   if proof:
    hit=prior.prior.old.intersection(proof);assert hit==proof['possible_auxiliary_effective_addresses']and len(hit)==proof['auxiliary_address_intersection_count']
    if row['classification']==DISJOINT:assert not hit
   if row['classification']!=old[key]['classification']:
    assert key in((11,0xC61F),(11,0xC624))and row['classification']==DISJOINT
    assert row['whole_pointer_values']==[0x8B1C+20*i for i in range(256)]
    required=proof['required_execution_contract'];assert required['constructor_entry_cpu']==0xC5F8 and required['constructor_complete_after_cpu']==0xC614
    assert required['must_enter_full_constructor']and required['normal_no_interrupt_execution']and not required['bare_middle_entry_covered']
   else:assert row['classification']==old[key]['classification']and proof==old[key]['address_contract']
  assert s['previous_candidate_count']==341 and s['remaining_access_count']==339 and s['new_disjoint_count']==2
  assert Counter(x['classification']for x in canonical.values())==s['all_indirect_classification_counts']==dict(proved_disjoint_auxiliary_address_domain=1187,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=258)
  assert v['failed_count']==0 and v['original_contract_CPU_cases']==33280
  assert v['actual_caller_RTS_CPU_cases']==len(v['typed_helper_checks'])==256 and v['constructor_prefix_CPU_cases']==len(v['constructor_checks'])==256 and v['pair_read_prefix_CPU_cases']==len(v['pair_read_checks'])==32768
  assert v['model_guard_check_count']==len(v['model_checks'])and all(x['passed']for x in v['model_checks'])
  for row in v['typed_helper_checks']:assert row['product']==row['raw_city']*20 and row['final_PC']==0xC604
  for row in v['constructor_checks']:assert row['output_pointer']==0x8B1C+20*row['raw_city']and row['final_PC']==0xC616
  for row in v['pair_read_checks']:
   assert len(row['accesses'])==2
   for access in row['accesses']:
    pointer=0x8B1C+20*row['raw_city'];assert access['pointer']==pointer and access['logical_address']==pointer+access['Y']
    bank=17 if access['logical_address']<0xA000 else 10;offset=original(bank,access['logical_address'])
    assert access['physical_bank']==bank and access['ROM_offset']==offset and access['value']==self.rom[offset]
    candidate=(pointer&0xFF00)|((pointer+access['Y'])&255);cross=(pointer&255)+access['Y']>255
    assert access['candidate_not_actual_dummy_address']==candidate and access['page_cross_dummy_read_required']==cross
    assert access['actual_dummy_bus_address']==(candidate if cross else None)
    assert 'not observed by py65'in access['actual_dummy_address_basis']and 'dummy_bus_address'not in access
  assert all(x is None for x in s['official_target_field_names'].values())and not s['complete_analysis_fixed_point_proven']
  self.counts.update(static_Source_CPU_cases=0,static_all_accesses=1526,static_remaining_candidates=s['remaining_access_count'])
  for key,value in v.items():
   if isinstance(value,int)and('CPU_cases'in key or'guard_check_count'in key):self.counts['static_'+key+'_not_Source']=value

 def service_index(self):
  folder=OUT/'services';s=self.record(folder/'analysis-summary.json',False);v=self.record(folder/'verification.json');self.record(folder/'evidence.json')
  assert s['source_CPU_cases']==s['original_CPU_cases']==s['Native_runs']==v['source_CPU_cases']==v['original_CPU_cases']==v['Native_runs']==0
  assert s['unknown_unique_services']is None and not s['whole_game_service_closure_proven']
  assert v['check_count']==len(v['checks'])and all(x.get('passed',x.get('status')=='passed')for x in v['checks'])
  values={name:self.record(folder/name,False)for name in('owner-route-catalog.json','observed-service-index.json','captured-caller-index.json','closure-status-ledger.json','acceptance-map.json','receipt-observations.json','source-syntax-boundaries.json','trusted-static-calls.json')}
  observations=values['receipt-observations.json']['observations'];services=values['observed-service-index.json']['services'];callers=values['captured-caller-index.json']['callers'];ledger=values['closure-status-ledger.json']['entries']
  assert len(observations)==s['observation_count']==32504 and Counter(x['disposition']for x in observations)==s['observation_disposition_counts']
  assert len(services)==len(ledger)==s['index_context_key_count']==157 and sum(x['index_key_kind']=='service_identity'for x in services)==s['identified_service_key_count']==74
  assert(len(callers),values['captured-caller-index.json']['new_phase25_opcode_context_count'])==(85,63)
  assert(s['source_file_count'],s['phase24_frozen_source_files'],s['receipt_file_count'])==(96,94,98)
  assert s['frontdoor']=='AppearancePointerSceneCoordinator'and set(s['additional_current_source_files'])=={'source/recovered/appearance_pointer_services.py','source/recovered/appearance_pointer_integration.py'}
  by_key={x['service_key']:x for x in ledger};indices=[]
  for service in services:
   matched=[observations[i]for i in service['contexts']];indices.extend(service['contexts'])
   assert all(x['service_key']==service['service_key']for x in matched)
   assert Counter(x['disposition']for x in matched)==service['disposition_counts']
   entry=by_key[service['service_key']];assert entry['evidence_observation_indices']==service['contexts']and entry['confirmed_unimplemented']is None
  assert sorted(indices)==list(range(len(observations)))
  captured=0
  for caller in callers:
   evidence=caller['evidence'];self.pin(evidence['path'],evidence['sha256'])
   if evidence['path'].startswith('analysis/phase25/runtime/'):
    assert caller['execution_origin_subtype']=='passive_Native_callee_capture';captured+=1
    meta=read(ROOT/evidence['path']);assert meta['entry']==caller['target']and meta['actual_PRG_banks']==caller['entry_banks']and meta['event_sequence']==caller['actual_parent_event_sequence']
    assert meta['snapshot_sequence']==caller['actual_snapshot_sequence']and not meta['instantaneous_N163_PPU_APU_captured']
  assert captured==63
  self.counts.update(service_index_gameplay_Source_CPU_cases=0,service_index_Native_runs=0,service_index_checks=v['check_count'],service_index_observation_records=s['observation_count'],
   service_index_context_keys=s['index_context_key_count'],service_index_identified_keys=s['identified_service_key_count'],service_index_captured_contexts=len(callers),service_index_new_opcode_contexts=63)

 def acceptance(self):
  folder=OUT/'acceptance';v=self.record(folder/'verification.json');r=self.record(folder/'requirements.json',False);p=self.record(folder/'request-provenance.json',False)
  assert v['source_CPU_cases']==v['original_CPU_cases']==v['Native_frames']==0 and r['overall_reverse_engineering_complete']is False and r['completion_percentage']is None
  assert(v['direct_user_message_locator_checks'],v['dimension_status_and_receipt_checks'],v['evidence_reference_checks'],v['source_syntax_checks'])==(11,10,69,96)and v['coordinator_report_separately_labelled']
  messages={x['message_id']:x for x in p['source_messages']};locators={x['request_id']:x for x in p['request_locators']}
  for user in r['user_request_register']:
   locator=locators[user['id']];message=messages[locator['message_id']];assert user['quote']in message['text']and locator['turn_id']==message['turn_id']and message['source_kind']=='read_thread_userMessage'
   source=user['source'];assert source['source_kind']=='direct_human_userMessage'and source['message_id']==locator['message_id']and source['turn_id']==locator['turn_id']
  assert p['coordination_report']['not_verbatim_user_quote']and p['coordination_report']['source_kind']=='coordinator_delegation_report'and len(r['dimensions'])==10
  assert r['coordination_and_continuation']['source_kind']=='coordinator_delegation_report'and r['coordination_and_continuation']['not_verbatim_user_quote']
  assert Counter(x['acceptance_status']for x in r['dimensions'])==v['dimension_status_counts']and len(locators)==11
  for row in r['dimensions']:
   assert row['acceptance_status']and row['verified_results']and row['pending_results']and row['phase25_change']['result']and row['phase25_change']['remaining_gap']
   for item in row['verified_results']:
    assert item['claim']and item['evidence']in row['evidence'];self.pin(item['evidence'])
    if item.get('evidence_scope')=='inherited_frozen_phase24_or_earlier_result':assert item['claim'].startswith('冻结父阶段记录：')
  self.counts.update(acceptance_dimensions=10,acceptance_human_excerpt_locators=len(locators),acceptance_Source_CPU_cases=0,acceptance_Native_frames=0)

 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing final Root report')
  self.pin(OUT/'README.md');qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'index.html',qa['HTML_sha256'])
  assert qa['status']=='passed'and qa.get('console_errors',[])==[]and qa['check_count']==len(qa['checks'])and all(x['status']=='passed'for x in qa['checks'])
  page=PortalPage();page.feed((OUT/'index.html').read_text());payload=json.loads(page.evidence)
  for name in('appearance_pointer_services.py','appearance_pointer_integration.py'):assert(ROOT/'source/recovered'/name).read_text()in page.sources
  assert len(page.sources)==2 and payload['native']==read(OUT/'runtime/evidence.json')['summary']
  for name,keys,path in(('source',('original_CPU_parent_cases','counts','source_guard_count'),'appearance/validation.json'),('integration',('original_CPU_parent_cases','counts','guard_count'),'source-integration.json'),('contract',('original_contract_CPU_cases','actual_caller_RTS_CPU_cases','constructor_prefix_CPU_cases','pair_read_prefix_CPU_cases','model_guard_check_count'),'fields-static/verification.json')):
   full=read(OUT/path);assert payload[name]=={key:full[key]for key in keys}
  assert payload['static']==read(OUT/'fields-static/analysis-summary.json')and payload['acceptance']==read(OUT/'acceptance/requirements.json')
  summary=read(OUT/'services/analysis-summary.json');assert payload['service_summary']=={k:v for k,v in summary.items()if k not in('source_and_validator_sha256','artifact_and_dependency_sha256')}
  assert len(payload['routes'])==2;point_count=event_count=0
  for route in payload['routes']:
   folder=OUT/'runtime'/route['case'];points=read(folder/'original-control/checkpoints.json')
   assert route['points']==points and route['points']==read(folder/'observer/checkpoints.json')
   assert route['base']=='runtime/'+route['case']+'/'and route['raw_events']==route['base']+'observer/events.jsonl'
   events={e['sequence']:e for e in map(json.loads,(folder/'observer/events.jsonl').read_text().splitlines())}
   for event in route['events']:
    raw={k:v for k,v in event.items()if k!='display_bus_role'};assert raw==events[event['sequence']]
    pc=raw['opcode_PC'];role='STA (zp),Y unconditional dummy read'if raw['kind']=='read'and pc in(0xB449,0xB44F)else'logical ROM read'if raw['kind']=='read'and pc in(0xC61F,0xC624)and raw['address']==((raw['pointer_0022_0023']+raw['Y'])&65535)else'write attempt; backing field is separate'if raw['kind']=='write_attempt'else'opcode boundary or other raw bus event'
    assert event['display_bus_role']==role
   assert len(route['audio'])==2
   for variant,audio in zip(('original-control','observer'),route['audio']):
    path=OUT/audio['path'];assert path==folder/variant/'full-audio.wav';self.pin(path,audio['sha256'])
    with wave.open(str(path))as wav:assert(audio['channels'],audio['sample_rate'],audio['sample_frames'],audio['duration_seconds'])==(wav.getnchannels(),wav.getframerate(),wav.getnframes(),wav.getnframes()/wav.getframerate())
   point_count+=len(points);event_count+=len(route['events'])
  assert point_count==106
  observed={x['service_key']:x for x in read(OUT/'services/observed-service-index.json')['services']};static={x['service_key']:x for x in read(OUT/'services/trusted-static-calls.json')['services']};syntax=read(OUT/'services/source-syntax-boundaries.json');syntax={x['syntax_key']:x for x in syntax['external_call_sites']+syntax['dependency_or_wait_markers']}
  assert Counter(x['level']for x in payload['service_search'])==dict(existing_execution=len(observed),trusted_static=len(static),syntax_only=len(syntax))
  for item in payload['service_search']:
   if item['level']=='existing_execution':assert item['key']in observed and item['contexts']==len(observed[item['key']]['contexts'])and item['path']=='services/observed-service-index.json'
   elif item['level']=='trusted_static':assert item['key']in static and item['contexts']==len(static[item['key']]['trusted_callsites'])and item['path']=='services/trusted-static-calls.json'
   else:assert item['key'].split(' target=')[0]in syntax and item['contexts']==1 and item['path']=='services/source-syntax-boundaries.json'
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path in(OUT/'verification.json',OUT/'package-receipt.json')or path.suffix=='.zip':continue
   assert path.is_file(),('Broken portal link',link)
  self.pin(qa['screenshot']['path'],qa['screenshot']['sha256']);self.counts.update(browser_checks=qa['check_count'],browser_Source_modules=len(page.sources),browser_Native_points=point_count,browser_projected_actual_events=event_count)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA;audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[]
 audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('services-index',audit.service_index),('acceptance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');audit.pin(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP and manifest['foundational_archive']['sha256']==V22_ZIP
 assert manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase25']
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in prior.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots']);names=set(manifest['include_files']);included={k:v for k,v in audit.pins.items()if k in names or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase25-one-appearance-pointer-and-known-submit-readonly-audit-v1',status='pending_final_artifacts'if pending else'passed',ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,
  old_v24_incremental_preserved_sha256=OLD_ZIP,old_phase24_audit_sha256=OLD_AUDIT,old_phase24_postZIP_receipt_sha256=OLD_POSTZIP,old_v22_preserved_sha256=V22_ZIP,
  source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,
  checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guard_cases',0),
  source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),
  limits=['Read-only evidence verification; no CPU/core or producer is rerun.',
   'Only the new observer has sparse internal events. Five-buffer equivalence is bounded to the two declared routes.',
   'Known reserve+12/+13 writes and G033 appearance/status1→2 are distinct from unknown auxiliary semantics or the prior wild-status0→2 route.',
   'Actual software callee snapshots do not contain instantaneous N163/PPU/APU. Explicit later device fixtures remain separate.',
   'Static contracts, service index and acceptance syntax/reference checks are not Source game cases; unique service closure and full-ROM completion remain unproven.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))

if __name__=='__main__':main()
