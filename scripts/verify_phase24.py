#!/usr/bin/env python3
"""Read-only phase24 audit. Writes only analysis/phase24/verification.json.

Does not run a CPU, core, capture, analyzer, old audit main or source generator.
Source differential cases, static contracts, syntax checks and Native frames
are distinct evidence classes. --allow-pending never conceals a frozen mismatch.
"""
from pathlib import Path
from collections import Counter
import argparse, ast, hashlib, importlib.util, json, re, sys, wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase24'
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('readonly_phase23_audit',ROOT/'scripts/verify_phase23.py')
prior=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=prior;SPEC.loader.exec_module(prior)
from capture_native_pointer_lifecycle import decode_event,fields,PLAN
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=prior.ROM_SHA;sha=prior.sha;read=prior.read;original=prior.original;DISJOINT=prior.DISJOINT
OLD_AUDIT='8e53b4e8c315d49a407c2f120d56fbd3280ed0043fdec36af93e332e70c90f38'
OLD_ZIP='7b141e38fdc88e6c601d10705b255bb48f04e1047cd0ab40ffa588490bf17e51'
BASE_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
FIVE=prior.FIVE;Pending=prior.Pending
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
WATCH_SHA='16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31'
POSTZIP=prior.old.POSTZIP
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(path):return str(Path(path).resolve().relative_to(ROOT))

def apply_patch_readonly(patch,original_files):
 """Apply ordinary unified hunks in memory, validating every original line."""
 files=dict(original_files);lines=patch.decode().splitlines(keepends=True);i=0
 while i<len(lines):
  if not lines[i].startswith('diff --git '):i+=1;continue
  header=lines[i].split();name=header[3][2:];assert name==header[2][2:]
  assert not Path(name).is_absolute()and'..'not in Path(name).parts
  i+=1
  while i<len(lines)and not lines[i].startswith('@@ '):
   assert not lines[i].startswith('diff --git ');i+=1
  source=files.get(name,b'').decode().splitlines(keepends=True);result=[];cursor=0
  while i<len(lines)and lines[i].startswith('@@ '):
   m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',lines[i]);assert m
   start=int(m[1]);old_count=int(m[2]or 1);new_count=int(m[4]or 1);at=0 if start==0 else start-1
   assert at>=cursor;result.extend(source[cursor:at]);cursor=at;i+=1;removed=added=0
   while i<len(lines)and not lines[i].startswith(('@@ ','diff --git ')):
    line=lines[i]
    if line.startswith(' '):assert source[cursor]==line[1:];result.append(line[1:]);cursor+=1;removed+=1;added+=1
    elif line.startswith('-'):assert source[cursor]==line[1:];cursor+=1;removed+=1
    elif line.startswith('+'):result.append(line[1:]);added+=1
    else:assert line.startswith('\\ No newline')
    i+=1
   assert removed==old_count and added==new_count
  result.extend(source[cursor:]);files[name]=''.join(result).encode()
 return files

class Audit(prior.Audit):
 def record_pins(self,record,folder=None):
  # These named maps use repository-relative paths, including the root
  # README.md. Native artifact_sha256 alone uses local bare filenames.
  # Do not confuse root README with acceptance/README when both exist.
  normalized=dict(record)
  for group in('source_sha256','source_and_validator_sha256','artifact_and_dependency_sha256','input_sha256'):
   value=normalized.get(group)
   if isinstance(value,dict):normalized[group]={str(ROOT/name)if not Path(name).is_absolute()else name:pin for name,pin in value.items()}
  return super().record_pins(normalized,folder)

 def frozen_history(self):
  self.pin('analysis/phase23/verification.json',OLD_AUDIT);value=read(ROOT/'analysis/phase23/verification.json')
  assert value['status']=='passed'and value['ROM_sha256']==ROM_SHA and value['rebuilt_byte_identical']
  assert(len(value['source_and_validator_sha256']),len(value['artifact_and_dependency_sha256']))==(484,37758)
  self.frozen_names=set(value['source_and_validator_sha256'])|set(value['artifact_and_dependency_sha256'])
  for name,pin in value['source_and_validator_sha256'].items():self.pin(name,pin);self.sources[name]=pin
  for name,pin in value['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  self.pin('build/三国志2超级版-逆向分析-v23增量.zip',OLD_ZIP)
  self.pin('build/三国志2超级版-逆向分析-v22.zip',BASE_ZIP)
  assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  canonical=ROOT/'build/三国志2超级版-逆向分析.zip'
  if canonical.exists():self.pin(canonical,BASE_ZIP)
  self.counts.update(unchanged_phase23_source_script_pins=484,unchanged_phase23_artifact_dependency_pins=37758)

 def runtime(self):
  folder=OUT/'runtime';ev=self.record(folder/'evidence.json');v=self.record(folder/'validation.json')
  assert all(ev[k]==v[k]for k in v if k not in('evidence_sha256',))
  self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_pointer_lifecycle.py',v['script_sha256'])
  assert(v['natural_routes'],v['core_variants'],v['fresh_process_runs'],v['frames_per_route'])==(1,2,4,182)
  assert(v['frames_first_run_controls'],v['frames_both_runs_controls'],v['nonempty_artifact_repeat_checks'])==(364,728,1157)
  assert(v['PNG_count'],v['WAV_count'],v['event_count'],v['full_RAM_SRAM_snapshot_count'],v['D987_lifecycles'])==(26,2,32745,123,2)
  assert not v['cold_boot']and v['state_imports_per_run']==1 and v['additional_core_memory_writes']==v['ancestor_preparation_bytes']==0
  assert v['all_five_complete_buffers_match_original_each_frame']and v['all_nonempty_artifacts_repeat_exact']and v['all_initial_serialized_buffers_equal']
  assert not v['original_core_internal_instruction_trace']and v['source_CPU_cases']==v['failed_count']==0
  mother=ROOT/ev['mother']['path'];self.pin(mother,ev['mother']['sha256']);m=NestopiaContext.parse(mother.read_bytes())
  cores={'original-control':('.toolchain/nestopia/nestopia_libretro.dylib',CORE_SHA),'observer':('.toolchain/phase24-observer/observed/nestopia_libretro.dylib',WATCH_SHA)}
  original_rows=None;artifact_count=pngs=wavs=0
  for variant,(core,core_sha)in cores.items():
   self.pin(core,core_sha);one=folder/variant;two=OUT/'runtime-repeat'/variant
   a=self.record(one/'validation.json');b=self.record(two/'validation.json');repeat=self.record(one/'repeat-validation.json');assert a==b
   assert a['status']=='passed'and a['frames']==182 and a['core']['core_sha256']==core_sha
   assert a['AV']['sample_rate']==48000 and a['AV']['native_dimensions']==[256,240]
   assert a['state_imported']and not a['cold_boot']and a['natural_ordinary_input_route']
   assert a['additional_core_memory_writes']==a['inherited_preparation_byte_writes']==0 and a['source_CPU_cases']==0
   assert not a['original_core_internal_instruction_trace']and a['observer_sparse_CPU_events']==(variant=='observer')
   assert a['full_serialized_buffers_not_normalized']and repeat['all_bytes_exact']and repeat['all_serialized_buffers_full']
   assert repeat['nonempty_artifact_checks']==len(a['artifact_sha256'])
   prep=self.record(one/'preparation.json',False)
   assert prep['preparation']==[]and prep['additional_core_memory_writes']==prep['inherited_preparation_byte_writes']==0
   start=NestopiaContext.parse((one/'initial.state').read_bytes())
   assert start.ram==m.ram and start.sram==m.sram
   assert(one/'initial-ram.bin').read_bytes()==m.ram and(one/'initial-sram.bin').read_bytes()==m.sram
   for name,pin in a['artifact_sha256'].items():
    assert pin['bytes']>0
    for parent in(one,two):assert(parent/name).stat().st_size==pin['bytes'];self.pin(parent/name,pin['sha256'])
    artifact_count+=1
   rows=read(one/'frame-services.json');callbacks=read(one/'audio-callbacks.json');points=read(one/'checkpoints.json');plan=read(one/'input-plan.json')
   assert len(rows)==len(callbacks)==182 and len(points)==a['checkpoint_count']==13 and len(plan)==13
   assert [(x['frames'],tuple(x['buttons']),x['capture'])for x in plan]==PLAN
   assert [x['start_frame']for x in plan]==[sum(p['frames']for p in plan[:i])for i in range(len(plan))]
   if original_rows is None:original_rows=rows
   assert rows==original_rows
   with wave.open(str(one/'full-audio.wav'),'rb')as wav:
    assert(wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000)
    whole=hashlib.sha256()
    for i,(row,cb)in enumerate(zip(rows,callbacks),1):
     assert row['frame']==i and cb['emulated_frame_start']==i-1
     pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm)
     assert len(pcm)==row['PCM_bytes']==cb['stereo_sample_frames']*4 and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']
     assert wav.tell()*4==row['PCM_stop_byte']
     stem=one/('frame-%03d'%i);r=Path(str(stem)+'-ram.bin').read_bytes();s=Path(str(stem)+'-sram.bin').read_bytes();state=Path(str(stem)+'.state').read_bytes()
     assert len(r)==2048 and len(s)==8192 and len(state)==row['whole_serialized_state_bytes']
     assert digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']
     n=NestopiaContext.parse(state);assert n.ram==r and n.sram==s
     assert n.registers==row['actual_saved_CPU_registers']and list(n.prg_banks)==row['actual_saved_PRG_banks']
     projected=fields(r,s);assert all(row[k]==x for k,x in projected.items())
    assert not wav.readframes(1)and wav.getnframes()==a['full_audio']['stereo_sample_frames']==145361
    assert wav.tell()*4==a['full_audio']['PCM_bytes']and whole.hexdigest()==a['full_audio']['PCM_sha256'];wavs+=1
   for point in points:
    row=rows[point['frame']-1]
    with Image.open(one/point['image'])as im:im.load();assert im.size==(256,240)and im.mode=='RGB'and digest(im.tobytes())==row['RGB_sha256']
    assert digest((one/point['RAM']).read_bytes())==row['RAM_sha256']and digest((one/point['SRAM']).read_bytes())==row['SRAM_sha256']
    assert digest((one/point['state']).read_bytes())==row['whole_serialized_state_sha256'];pngs+=1
   assert rows[54]['officers']['30']['troops_raw16']==900 and rows[54]['working_reserve_042C_042D']==9899
   assert rows[76]['officers']['30']['troops_raw16']==800 and rows[76]['working_reserve_042C_042D']==9999
   assert rows[-1]['city_state_0400_0403'][:2]==[0,1]and(one/'frame-182-sram.bin').read_bytes()==m.sram
   if variant=='observer':self.observer(one,a)
  assert(artifact_count,pngs,wavs)==(1157,26,2)
  for name in('initial.state','pre-import-initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):
   assert(folder/'original-control'/name).read_bytes()==(folder/'observer'/name).read_bytes()
  self.counts.update(native_natural_routes=1,native_frames_per_route=182,native_fresh_process_runs=4,native_all_control_frames=728,native_state_imports=4,
   native_cold_boots=0,native_preparation_bytes=0,native_nonempty_artifact_repeat_checks=1157,native_PNG_checks=26,native_full_WAV_checks=2,
   observer_event_records=32745,observer_full_2K_8K_snapshots=123,observer_D987_lifecycle_instances=2,observer_city_auxiliary_events=0)

 def observer(self,folder,receipt):
  raw=(folder/'bus-events.bin').read_bytes();events=[json.loads(line)for line in(folder/'events.jsonl').read_text().splitlines()]
  assert len(events)==32745 and len(raw)==len(events)*144
  for i,event in enumerate(events):
   assert decode_event(raw[i*144:(i+1)*144],sequence=i+1)==event
   pc=event['opcode_PC'];pages=event['actual_PRG_banks']
   if pc is not None and pc>=0x8000:
    assert event['physical_bank']==pages[(pc-0x8000)//8192]and event['rom_offset']==original(event['physical_bank'],pc)
   if event['target_type']=='pointer_0000_0001_write':
    assert event['kind']=='write_attempt'and event['address']<0x2000 and(event['address']&0x7FF)in(0,1)
    # Actual binary e17 is a WRAM backing observation only. Physical RAM
    # post-write bytes are captured by the complete ZP snapshot, never invented.
    assert event['physical_storage_byte_after_event']is None
    assert event['ZP_0000_0023'][event['address']&0x7FF]==event['value']
  assert Counter(x['kind']for x in events)==receipt['observer_events']['kinds']
  assert Counter(x['target_type']for x in events)==receipt['observer_events']['targets']
  assert not any(x['target_type']=='city_auxiliary'for x in events)
  schema=self.record(folder/'event-schema.json',False);assert schema['bytes_per_record']==144 and schema['words']==len(schema['raw_layout'])==36
  assert schema['snapshots']['bytes_per_snapshot']==10240 and schema['snapshots']['complete_RAM_and_SRAM']
  snapshots=(folder/'snapshots.bin').read_bytes();index=[json.loads(x)for x in(folder/'snapshot-index.jsonl').read_text().splitlines()]
  assert len(index)==123 and len(snapshots)==123*10240 and sum(bool(x['full_snapshot_sequence'])for x in events)==123
  for i,item in enumerate(index,1):
   payload=snapshots[(i-1)*10240:i*10240];r,s=payload[:2048],payload[2048:];event=events[item['event_sequence']-1]
   assert item['snapshot_sequence']==event['full_snapshot_sequence']==i and item['entry']==event['opcode_PC']and item['frame']==event['frame']
   assert item['physical_bank']==event['physical_bank']==28 and item['entry']in(0xD64A,0xD987)
   assert digest(payload)==item['sha256']and digest(r)==item['RAM_sha256']and digest(s)==item['SRAM_sha256']
   assert list(r[:0x24])==event['ZP_0000_0023']and item['actual_PRG_banks']==event['actual_PRG_banks']
   assert item['actual_registers']==dict(a=event['A'],x=event['X'],y=event['Y'],p=event['P'],sp=event['SP'],pc=event['opcode_PC'])
   assert item['stack_top_word_raw']==event['stack_top_word_raw']==r[0x100+((event['SP']+1)&255)]|(r[0x100+((event['SP']+2)&255)]<<8)
   assert not item['instantaneous_PPU_APU_N163_state_captured']and item['additional_core_memory_writes']==item['inherited_preparation_byte_writes']==0
   if 'exported_RAM'in item:
    assert(folder/item['exported_RAM']).read_bytes()==r and(folder/item['exported_SRAM']).read_bytes()==s
  assert len(list(folder.glob('callee-*-D*.json')))==4
  lifetimes=read(OUT/'runtime/pointer-lifetimes.json')['instances'];assert len(lifetimes)==2
  for item in lifetimes:
   def event(key):return events[item[key]-1]
   entry=event('entry_sequence');division=event('division_entry_sequence');returned=event('division_return_sequence');restored=event('restored_sequence');exit_event=event('RTS_before_sequence')
   assert [x['opcode_PC']for x in(entry,division,returned,restored,exit_event)]==[0xD987,0xEA7C,0xD9AC,0xD9F0,0xDA01]
   assert entry['pointer_0000_0001']==restored['pointer_0000_0001']==exit_event['pointer_0000_0001']==0x6528
   assert division['saved_pointer_0010_0011']==restored['saved_pointer_0010_0011']==0x6528 and division['pointer_0000_0001']!=0x6528
   assert entry['SP']==exit_event['SP']==item['actual_entry_SP']==item['actual_RTS_before_SP']
   assert entry['actual_PRG_banks']==item['actual_NMI_PRG_banks']==[2,27,28,31]
   c=event('city_pointer_entry_sequence');cr=event('city_pointer_return_sequence');o=event('officer_pointer_entry_sequence');orr=event('officer_pointer_return_sequence')
   assert c['A']==11 and cr['pointer_0000_0001']==0x6160 and o['A']==30 and o['Y']==19 and orr['pointer_0000_0001']==0x6528
   assert c['SP']+2==cr['SP']and o['SP']+2==orr['SP']
  build=self.record(OUT/'runtime/core-provenance/build.json',False);assert build['commit']=='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
  assert not build['modified_emulator_object_layout']and not build['toolchain_in_archive']
  self.pin(build['original_core']['path'],CORE_SHA);self.pin(build['passive_observer']['path'],WATCH_SHA)
  self.pin(build['unchanged_phase21_core']['path'],'45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d')
  base=OUT/'runtime/core-provenance';patch=(base/'observer.patch').read_bytes();self.pin(base/'observer.patch',build['patch_sha256'])
  originals={x['path']:(base/'upstream'/x['path']).read_bytes()for x in build['source_files']}
  generated=apply_patch_readonly(patch,originals)
  for item in build['source_files']:
   assert digest(originals[item['path']])==item['original_sha256']and digest(generated[item['path']])==item['patched_sha256']
  for path in(base/'patched').rglob('*'):
   if path.is_file():assert generated[str(path.relative_to(base/'patched'))]==path.read_bytes()
  watch=generated['source/core/NstWatch.cpp.inc'].decode();board=generated['source/core/board/NstBoard.cpp'].decode()
  assert 'map.Peek'not in watch and 'map.Poke'not in watch and 'ram.mem,cycles.count'in watch
  assert 'e[17]=source[5];'in watch and 'e[17]=address<'not in watch
  assert 'out[i]=b.wrk[0][i]'in board and 'watch_snapshot_provider(watch_board,s+2048)'in watch
  assert 'watch_snapshot_overflow' in watch and '++watch_overflow' in watch
  reconstructed=self.record(base/'source-reconstruction.json')
  assert reconstructed['byte_identical']and reconstructed['reconstructed_sha256']==reconstructed['frozen_observer_sha256']==WATCH_SHA
  assert not reconstructed['Native_replayed']and not reconstructed['production_source_changed']
  self.pin(reconstructed['reconstructed_binary'],WATCH_SHA)
  self.pin(base/reconstructed['build_log'],reconstructed['build_log_sha256'])
  assert reconstructed['patch_sha256']==build['patch_sha256']and reconstructed['patched_watch_source_sha256']==digest(generated['source/core/NstWatch.cpp.inc'])
  self.counts['observer_upstream_source_files_patch_reconstructed_readonly']=len(originals)

 def source_cases(self):
  folder=OUT/'lifecycle';body=self.record(folder/'validation.json');evidence=self.record(folder/'evidence.json');catalog=self.record(folder/'static-catalog.json',False)
  if body.get('quick'):raise Pending('Source child quick matrix')
  assert body['failed_count']==0 and body['failures']==[]and body['original_CPU_parent_cases']==len(body['cases'])==1038
  assert Counter(x['comparison']for x in body['cases'])==body['counts']==dict(actual_caller_RTS=1036,strict_missing_dependency_prefix=2)
  assert body['source_guard_count']==len(body['guards'])==5 and all(x['status']=='passed'for x in body['guards'])
  assert body['source_original_CPU_callbacks']==0 and not body['production_IR_interpretation']and not body['production_runtime_codegen']and not body['Native_internal_CPU_trace']
  assert evidence['new_manual_positions']==evidence['dynamic_new_positions']==379 and evidence['new_manual_code_bytes']==913
  assert evidence['immutable_data_bytes']==39 and evidence['not_dynamic_positions']==0 and not evidence['all_paths_or_inputs_proven']
  assert catalog['new_manual_positions']==len(catalog['instructions'])==379 and catalog['new_manual_code_bytes']==913 and catalog['immutable_table_bytes']==39
  assert len(catalog['targeted_G086_sites'])==10 and len(catalog['other_G086_sites_outside_new_body'])==4
  for row in catalog['instructions']:self.raw({**row,'cpu':row['pc']})
  self.nested_raw(catalog);self.nested_raw(evidence)
  actual=0
  for row in body['cases']:
   scope=row['comparison_scope'];assert(scope['RAM_bytes'],scope['SRAM_bytes'])==(2048,8192)
   assert all(scope[k]for k in('AXYP_SP_PC','ordered_IO','four_banks','N163'))and scope['excluded_free_stack_bytes']==0
   assert row['source_original_CPU_callbacks']==0
   if row['domain']=='passive_Native_callee_capture_with_explicit_N163_fixture':actual+=1;self.actual_caller(row['provenance'])
  assert actual==4
  cpu=self.record(OUT/'cpu-lifecycle/evidence.json');assert cpu['exported_caller_inputs']==4 and cpu['source_CPU_cases']==cpu['original_CPU_prefix_instructions']==0 and not cpu['instant_N163_captured']
  contexts=sorted((OUT/'cpu-lifecycle/actual-callers').glob('entry-*/context.json'));assert len(contexts)==4
  for path in contexts:
   context=self.record(path,False);self.actual_caller(context)
   capture=context['passive_capture'];assert(path.parent/'input-ram.bin').read_bytes()==(ROOT/capture['RAM_path']).read_bytes()
   assert(path.parent/'input-sram.bin').read_bytes()==(ROOT/capture['SRAM_path']).read_bytes()
  integration=self.record(OUT/'source-integration.json')
  if integration['original_CPU_parent_cases']!=42:raise Pending('Root integration has not added four actual observer callees')
  assert len(integration['rows'])==42 and Counter(x['completion']for x in integration['rows'])==integration['counts']==dict(returned=41,nonlocal_return=1)
  assert integration['guard_count']==len(integration['guards'])==3 and all(isinstance(x,str)and x for x in integration['guards'])
  assert integration['source_original_CPU_callbacks']==0 and not integration['production_IR_interpretation']and not integration['Native_internal_CPU_trace']
  for row in integration['rows']:assert row['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and row['source_original_CPU_callbacks']==0
  for name in('pointer_lifecycle_services.py','pointer_lifecycle_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
     values=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module or'']
     assert not any(any(bad in value for bad in('py65','state_machine','importlib'))for value in values)
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.counts.update(new_manual_original_code_bytes=913,new_manual_instruction_positions=379,new_immutable_data_bytes=39,
   source_child_CPU_cases=1038,source_child_guards=5,source_child_actual_caller_RTS=1036,source_child_dependency_prefix=2,
   source_integration_CPU_cases=42,source_integration_actual_caller_RTS=41,source_integration_nonlocal_return=1,source_integration_guards=3,
   new_Source_CPU_cases=1080,new_Source_guard_cases=8,new_Source_actual_caller_RTS=1077,new_Source_nonlocal_return=1,new_Source_strict_dependency_prefix=2,
   passive_Native_callee_exports=4,instant_N163_captures=0)

 def actual_caller(self,row):
  assert row['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and row['actual_software_state_captured']
  assert not row['synthetic_caller_PC_or_stack']and not row['unmodified_core_internal_trace']
  assert row['prepared_numeric_bytes']==row['additional_CPU_prepared_numeric_bytes']==row['inherited_Native_preparation']==[]
  assert row['injected_new_NMI']==row['injected_new_IRQ']==0 and row['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  f=row['explicit_N163_fixture'];assert f['bytes']==128 and f['address']==127 and f['autoincrement']and f['sha256']==digest(bytes((11+37*i)&255 for i in range(128)))
  cap=row['passive_capture'];self.pin(cap['metadata'],cap['metadata_sha256']);self.pin(cap['RAM_path'],cap['RAM_sha256']);self.pin(cap['SRAM_path'],cap['SRAM_sha256']);self.pin(cap['manifest'],cap['manifest_sha256'])
  meta=read(ROOT/cap['metadata']);r=(ROOT/cap['RAM_path']).read_bytes();s=(ROOT/cap['SRAM_path']).read_bytes()
  assert len(r)==2048 and len(s)==8192 and meta['actual_registers']==row['registers']and meta['actual_PRG_banks']==row['physical_banks']==[2,27,28,31]
  sp=row['registers']['sp'];assert row['existing_return_PC']==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535

 def static_fields(self):
  folder=OUT/'fields-static';validation=self.record(folder/'verification.json');summary=self.record(folder/'analysis-summary.json');self.record(folder/'evidence.json')
  assert validation['status']=='passed'and summary['source_CPU_cases']==validation['source_CPU_cases']==0
  previous={(x['physical_bank'],x['cpu']):x for x in read(ROOT/'analysis/phase23/fields-static/all-indirect-accesses.json')['accesses']}
  data=self.record(folder/'all-indirect-accesses.json',False);canonical={(x['physical_bank'],x['cpu']):x for x in data['accesses']}
  assert len(canonical)==len(data['accesses'])==1526 and set(canonical)==set(previous)
  for key,row in canonical.items():
   self.raw(row);proof=row['address_contract'];assert row['phase23_classification']==previous[key]['classification']
   if proof:
    hit=prior.old.intersection(proof);assert hit==proof['possible_auxiliary_effective_addresses']and len(hit)==proof['auxiliary_address_intersection_count']
    assert row['whole_pointer_values']==sorted(prior.old.words(proof))and row['Y_values']==prior.old.indices(proof)
    if row['classification']==DISJOINT:assert not hit
   else:assert row['classification']=='unresolved_pointer_or_index_contract'
   assert row['newly_proved_disjoint']==(row['classification']==DISJOINT and previous[key]['classification']!=DISJOINT)
   if row['newly_proved_disjoint']:
    required=proof['required_execution_contract'];assert required['original_entry_physical_bank']==28 and required['original_entry_cpu']==0xD805
    assert required['normal_no_interrupt_execution']and required['raw_roster_ID_bytes']=='all0..255 retained'and not required['arbitrary_bare_access_entry_covered']
    assert row['whole_pointer_values']==[0x63C0+12*i for i in range(256)]and row['Y_values']in([8],[9],[8,9])
   else:assert row['classification']==previous[key]['classification']and proof==previous[key]['address_contract']
  assert Counter(x['classification']for x in canonical.values())==summary['all_indirect_classification_counts']==dict(proved_disjoint_auxiliary_address_domain=1185,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=260)
  assert summary['previous_candidate_count']==351 and summary['new_disjoint_count']==10 and summary['remaining_access_count']==341
  assert not summary['complete_analysis_fixed_point_proven']and all(x is None for x in summary['official_target_field_names'].values())
  for name,count in(('access-contracts.json',589),('new-indirect-accesses.json',45),('phase23-remaining351-handling.json',351),('remaining-accesses.json',341),('unknown270-handling.json',270)):
   r=self.record(folder/name,False);assert r['access_count']==len(r['accesses'])==count and all(x==canonical[x['physical_bank'],x['cpu']]for x in r['accesses'])
  ranking=self.record(folder/'unknown-producer-ranking.json',False);assert ranking['input_group_count']==len(ranking['groups'])==55 and ranking['input_access_count']==270 and ranking['selected_group']=='G086'
  assert sum(x['access_count']for x in ranking['groups'])==270
  selected=self.record(folder/'selected-lifecycle.json',False);assert selected['group']=='G086'and selected['input_access_count']==14 and selected['selected_access_count']==len(selected['selected_accesses'])==10 and len(selected['unselected_accesses'])==4
  assert all(canonical[x['physical_bank'],x['cpu']]['classification']=='unresolved_pointer_or_index_contract'for x in selected['unselected_accesses'])
  contract=self.record(folder/'typed-pointer-return-contract.json',False);self.nested_raw(contract)
  assert contract['entry']['cpu']==0xD987 and contract['normal_RTS']['cpu']==0xDA01 and contract['restore_dominates_normal_RTS']
  assert len(contract['original_local_instructions'])==50 and len(contract['helper']['original_instructions'])==22
  assert contract['input_whole_pointer_values']==[0x63C0+12*i for i in range(256)]
  apps=self.record(folder/'typed-pointer-return-applications.json',False);assert apps['application_count']==len(apps['applications'])==2
  assert {x['call']['cpu']for x in apps['applications']}=={0xD837,0xD87E}
  for name in('logical-vs-dummy-bus-contracts.json','raw345-executability-ledger.json'):self.record(folder/name,False)
  raw=read(folder/'raw345-executability-ledger.json');assert raw['window_count']==345 and Counter(x['phase22_executability_category']for x in raw['windows'])==dict(unresolved_raw_window_no_proved_control_entry=228,trusted_instruction_operand_no_proved_alternate_entry=104,declared_ROM_data_no_proved_instruction_entry=13)
  for row in raw['windows']:
   offset=16+row['physical_bank']*8192+row['bank_offset'];assert row['rom_offset']==offset
   assert self.rom[offset:offset+len(bytes.fromhex(row['raw_hex']))]==bytes.fromhex(row['raw_hex'])and not row['promoted_to_executable_code']
  dummy=read(folder/'logical-vs-dummy-bus-contracts.json');assert len(dummy['accesses'])==1526
  for row in dummy['accesses']:
   authority=canonical[row['physical_bank'],row['cpu']];proof=authority['address_contract']
   actual=prior.old.dummy_intersection(proof,authority['op'])if proof else None
   assert row['logical_classification']==authority['classification']and row['dummy_auxiliary_bus_addresses']==actual
  assert validation['original_contract_CPU_cases']==10757
  assert validation['typed_helper_actual_caller_RTS_CPU_cases']==10240 and validation['D805_actual_caller_RTS_CPU_cases']==512 and validation['raw_alias_counterexample_CPU_cases']==5
  assert validation['model_guard_check_count']==len(validation['model_checks'])==14 and all(x['passed']for x in validation['model_checks'])
  old_models=read(ROOT/'analysis/phase23/fields-static/verification.json')['model_checks']
  assert len(old_models)==19 and all(x['passed']for x in old_models)
  for phrase in('singleton MAY-ZP plus non-ZP','mixed indirect ZP and IO','multiple complete EAs aliasing one physical ZP'):
   assert any(phrase in x['name']for x in old_models)
  self.counts.update(static_all_accesses=1526,static_previous_candidates=351,static_remaining_candidates=341,static_new_conditional_exclusions=10,
   static_input_unknown_producer_groups=55,static_input_unknown_producer_accesses=270,selected_G086_total_sites=14,selected_G086_proved_sites=10,selected_G086_still_unknown_sites=4,
   static_D987_positions=50,static_EA7C_positions=22,static_Source_CPU_cases=0,static_raw_hypotheses_not_code=345)
  self.counts.update(static_normal_caller_RTS_contracts_not_Source=10752,static_raw_alias_counterexamples_not_all_RTS=5,unchanged_old_must_cell_model_guards_not_rerun=19)
  for key,value in validation.items():
   if isinstance(value,int)and('CPU_cases'in key or'guard_check_count'in key):self.counts['static_'+key+'_not_Source']=value

 def acceptance(self):
  folder=OUT/'acceptance';v=self.record(folder/'verification.json');req=self.record(folder/'requirements.json',False);inventory=self.record(folder/'source-dependency-inventory.json',False)
  assert v['source_CPU_cases']==v['original_CPU_cases']==v['Native_frames']==0
  assert req['overall_reverse_engineering_complete']is False and req['completion_percentage']is None
  assert inventory['unknown_unique_services']is None and not inventory['whole_game_service_closure_proven']
  assert len(req['dimensions'])==10 and len(req['user_request_register'])==11
  assert all(x['requirement_kind']in('user_explicit','mixed','engineering_suggestion')for x in req['dimensions'])
  # Explicit quotes, delegated implementation authorization and proposed gaps
  # must remain distinct. The Root checker owns the provenance schema.
  if not(folder/'request-provenance.json').is_file():raise Pending('Root acceptance request/authorization provenance is not final')
  provenance=self.record(folder/'request-provenance.json',False)
  assert provenance['status']=='verified_against_accessible_thread_user_messages'
  messages={x['message_id']:x for x in provenance['source_messages']};locators={x['request_id']:x for x in provenance['request_locators']}
  assert len(locators)==11 and v['direct_user_message_locator_checks']==11 and v['dimension_status_and_receipt_checks']==10
  for user in req['user_request_register']:
   locator=locators[user['id']];message=messages[locator['message_id']]
   assert locator['turn_id']==message['turn_id']and user['quote']in message['text']and message['source_kind']=='read_thread_userMessage'
   origin=user['source'];assert origin['source_kind']=='direct_human_userMessage'and origin['message_id']==locator['message_id']and origin['turn_id']==locator['turn_id']
  coordination=provenance['coordination_report'];assert coordination['not_verbatim_user_quote']and coordination['source_kind']=='coordinator_delegation_report'
  assert v['coordinator_report_separately_labelled']
  for dimension in req['dimensions']:
   assert dimension['acceptance_status']and dimension['verified_results']and dimension['pending_results']==dimension['gaps']
   for result in dimension['verified_results']:
    assert result['claim']and result['receipt_kind']and result['evidence']in dimension['evidence'];self.pin(result['evidence'])
  self.counts.update(acceptance_dimensions=10,acceptance_source_syntax_checks_not_CPU=v['source_syntax_checks'],acceptance_gameplay_CPU_cases=0,acceptance_Native_frames=0)
  self.counts.update(acceptance_exact_user_message_locators=11,acceptance_explicit_dimension_statuses=10,acceptance_reference_checks_not_gameplay=v['evidence_reference_checks'])

 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing final Root README.md')
  self.pin(OUT/'README.md');qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'index.html',qa['HTML_sha256'])
  assert qa['status']=='passed'and qa.get('console_errors',[])==[]and qa['check_count']==len(qa['checks'])and all(x['status']=='passed'for x in qa['checks'])
  page=prior.old.prior.Page();page.feed((OUT/'index.html').read_text())
  expected=[(ROOT/'source/recovered'/name).read_bytes()for name in('pointer_lifecycle_services.py','pointer_lifecycle_integration.py')]
  assert all(raw.decode()in page.sources for raw in expected)
  payload=json.loads(page.evidence)
  assert payload['native']==read(OUT/'runtime/evidence.json')and payload['points']==read(OUT/'runtime/original-control/checkpoints.json')
  assert payload['static_summary']==read(OUT/'fields-static/analysis-summary.json')and payload['acceptance']==read(OUT/'acceptance/requirements.json')
  assert payload['acceptance_sha256']==sha(OUT/'acceptance/requirements.json')
  assert payload['source_counts']==dict(parent_cases=1080,service_cases=1038,integration_cases=42,guards=8,RTS=1077,nonlocal_return=1,strict_prefix=2)
  ranking={x['group_id']:x for x in read(OUT/'fields-static/unknown-producer-ranking.json')['groups']}
  assert len(payload['groups'])==len(ranking)==55
  for projected in payload['groups']:
   full=ranking[projected['group_id']];sites={(x['physical_bank'],x['cpu']):x for x in full['accesses']}
   for key,value in projected.items():
    if key=='accesses':
     assert len(value)==len(sites)
     for site in value:assert all(sites[site['physical_bank'],site['cpu']][k]==v for k,v in site.items())
    elif key in full:assert value==full[key]
  actual_events={x['sequence']:x for x in map(json.loads,(OUT/'runtime/observer/events.jsonl').read_text().splitlines())}
  lifetimes=read(OUT/'runtime/pointer-lifetimes.json')['instances'];assert len(payload['lifecycles'])==len(lifetimes)==2
  for projected,full in zip(payload['lifecycles'],lifetimes):
   assert all(projected[k]==value for k,value in full.items())
   assert all(row==actual_events[row['sequence']]for row in projected['events'])
  assert len(payload['callers'])==4
  for caller in payload['callers']:assert caller['context']==read(OUT/caller['folder']/'context.json')
  assert len(payload['audio'])==2
  for item in payload['audio']:self.pin(OUT/item['path'],item['sha256']);assert item['sample_rate']==48000 and item['channels']==2 and item['sample_frames']==145361
  for item in payload['sources']:self.pin(item['file'],item['sha256']);assert(ROOT/item['file']).stat().st_size==item['UTF8_bytes']
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path==OUT/'verification.json'or path.suffix=='.zip':continue
   assert path.is_file(),('Broken portal link',link)
  shot=qa['screenshot'];self.pin(shot['path'],shot['sha256'])
  self.counts.update(browser_source_modules=len(page.sources),browser_checks=len(qa['checks']))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA;audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[]
 audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('acceptance-provenance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest_path=OUT/'delivery-manifest.json'
 if not manifest_path.is_file():
  if not a.allow_pending:raise Pending('Missing phase24 delivery-manifest.json')
  pending.append(dict(stage='delivery',reason='Missing phase24 delivery-manifest.json'));manifest=None
 else:
  manifest=read(manifest_path);audit.pin(manifest_path)
  assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP
  assert manifest['foundational_archive']['sha256']==BASE_ZIP and manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase24']
  assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included'))
  assert not any(manifest[k]for k in('toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots'])if manifest else('analysis/phase24/',);files=set(manifest['include_files'])if manifest else set()
 included={k:v for k,v in audit.pins.items()if k in files or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase24-one-native-pointer-lifecycle-frozen-history-audit-v1',status='pending_final_artifacts'if pending else'passed',
  ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v23_incremental_preserved_sha256=OLD_ZIP,old_phase23_audit_sha256=OLD_AUDIT,old_v22_preserved_sha256=BASE_ZIP,
  source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,
  checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guard_cases',0),
  source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),
  limits=['Read-only current evidence audit, no CPU/core/source producer executed.',
   'Sparse internal events come from a separate phase24 core; the original core is matched at every complete output/state boundary on one route.',
   'Actual observer callee software contexts and explicit N163/port model fixtures are separate origins.',
   'Typed pointer contracts apply to declared complete-pointer domains and no-interrupt ordinary calls, not arbitrary entries.',
   'Acceptance inventory, static contracts and Native frames are not additional Source differential cases; no whole-ROM completion percentage is asserted.',
   'Incremental release excludes original/rebuilt ROM, full byte-source, core binaries, toolchain and old large history. External frozen bases remain separately pinned.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))

if __name__=='__main__':main()
