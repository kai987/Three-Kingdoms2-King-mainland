#!/usr/bin/env python3
"""Read-only phase27 audit. Only new analysis/phase27/verification.json is written.

No CPU/core, producer, analyzer, historical audit main or generator is executed.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys,wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase27';sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('readonly_phase26_audit',ROOT/'scripts/verify_phase26.py');base=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=base;SPEC.loader.exec_module(base)
from capture_native_postbattle_pointer import decode_event,fields,CASES,CORE_SHA,OBSERVER_SHA,RECORD_BYTES
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=base.ROM_SHA;sha=base.sha;read=base.read;original=base.original;DISJOINT=base.DISJOINT;Pending=base.Pending
OLD_AUDIT='91dda198dbd978eaa76a0b3a98b1bcf6cf40032c622594416f5d90e3ef778577'
OLD_ZIP='ed9f9cbf4e1e7ced4a4ff03dc70793b37bce31ad94b38597db7759a430be3f23'
OLD_POSTZIP='15436b939aea46f21236d85ab64d398da088a3f1815533f9471442981264c867'
V22_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(p):return str(Path(p).resolve().relative_to(ROOT))

class Audit(base.Audit):
 def frozen_history(self):
  self.pin('analysis/phase26/verification.json',OLD_AUDIT);v=read(ROOT/'analysis/phase26/verification.json');assert v['status']=='passed'and not v['pending']and v['ROM_sha256']==ROM_SHA and v['rebuilt_byte_identical']
  assert(len(v['source_and_validator_sha256']),len(v['artifact_and_dependency_sha256']))==(525,45263)
  self.frozen_names=set(v['source_and_validator_sha256'])|set(v['artifact_and_dependency_sha256'])
  for name,p in v['source_and_validator_sha256'].items():self.pin(name,p);self.sources[name]=p
  for name,p in v['artifact_and_dependency_sha256'].items():self.pin(name,p)
  self.pin('analysis/phase26/package-receipt.json',OLD_POSTZIP);p=read(ROOT/'analysis/phase26/package-receipt.json');assert p['status']=='passed'and p['phase26_audit_sha256']==OLD_AUDIT and p['sha256']==OLD_ZIP and p['file_count']==3145
  self.pin('build/三国志2超级版-逆向分析-v26增量.zip',OLD_ZIP);self.pin('build/三国志2超级版-逆向分析.zip',V22_ZIP);assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.counts.update(unchanged_phase26_source_script_pins=525,unchanged_phase26_artifact_dependency_pins=45263,unchanged_phase26_postZIP_receipts=1)

 def ancestry27(self,c,ancestor):
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
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json');assert e['summary']=={k:v[k]for k in e['summary']};self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_postbattle_pointer.py',v['script_sha256'])
  expected=dict(routes=2,natural_routes=1,controlled_ancestry_routes=1,core_variants=2,fresh_process_runs=8,original_first_frames=96,all_control_frames=384,original_checkpoints=96,nonempty_artifact_repeat_checks=864,PNG_checks=192,WAV_checks=4,observer_events=17378,full_software_snapshots=14,logical_G106_reads=15,G106_STA_dummy_read_count=11,G106_store_count=11,G106_changed_byte_count=7,G106_unchanged_store_count=4,city_auxiliary_bus_events=0,additional_core_memory_writes=0,cold_boots=0,state_imports=8,Source_CPU_cases=0,failed_count=0)
  assert all(v[k]==x for k,x in expected.items())and all(v[k]for k in('all_five_complete_buffers_equal_each_frame','all_complete_initial_API_buffers_equal','all_artifacts_repeat_exact','full_serialized_buffers_not_normalized'))
  artifacts=images=wavs=0
  for case,c in CASES.items():
   self.ancestry27(c,e['case_ancestry'][case]);mother=ROOT/c['mother'];m=NestopiaContext.parse(mother.read_bytes());original_rows=None
   for variant,core in(('original-control',CORE_SHA),('observer',OBSERVER_SHA)):
    first=folder/case/variant;second=OUT/'runtime-repeat'/case/variant;a=self.record(first/'validation.json');b=self.record(second/'validation.json');repeat=self.record(first/'repeat-validation.json');assert a==b and a['core']['core_sha256']==core
    assert a['frames']==a['checkpoint_count']==c['frames']and a['state_imported']and not a['cold_boot']and a['additional_core_memory_writes']==a['Source_CPU_cases']==0 and not a['original_core_internal_CPU_trace']
    assert a['natural_ordinary_input_route']==c['natural']and a['controlled_ancestry']==(not c['natural'])and a['known_inherited_preparation_byte_writes']==(0 if c['natural']else 19)
    self.ancestry27(c,a['ancestry']);prep=self.record(first/'preparation.json',False);assert prep==e['case_ancestry'][case]==a['ancestry']and repeat['all_bytes_exact']and repeat['artifact_checks']==len(a['artifact_sha256'])
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
    assert a['initial_fields']['outcome_0514']==c['outcome']and rows[0]['battle_0500_0501']==[15,3]
   self.observer27(folder/case/'observer',case)
  assert(artifacts,images,wavs)==(864,192,4);self.core_provenance();self.record(folder/'media-static-validation.json')
  self.counts.update({f'Native_{k}':x for k,x in expected.items()})

 def observer27(self,folder,case):
  events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()));raw=(folder/'bus-events.bin').read_bytes();assert len(raw)==len(events)*RECORD_BYTES
  schema=self.record(folder/'event-schema.json',False);assert len(schema['raw_layout'])==schema['words']==48 and schema['bytes_per_record']==192
  for i,e in enumerate(events,1):
   assert decode_event(raw[(i-1)*RECORD_BYTES:i*RECORD_BYTES],sequence=i)==e
   if e['opcode_PC']is not None and e['opcode_PC']>=0x8000:assert e['physical_bank']==e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]and e['rom_offset']==original(e['physical_bank'],e['opcode_PC'])
   if e['data_ROM_offset']is not None:assert e['value']==self.rom[e['data_ROM_offset']]and e['data_physical_bank']==e['actual_PRG_banks'][(e['address']-0x8000)//8192]
   if e['target_type']=='pointer_001A_001B_RAM_write':assert e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
  shadow=bytearray((folder/'initial-sram.bin').read_bytes());frame=1
  for e in events:
   while frame<e['frame']:
    assert shadow[:960]==(folder/f'frame-{frame:03d}-sram.bin').read_bytes()[:960];frame+=1
   if e['kind']=='write_attempt'and 0x6000<=e['address']<0x63C0:
    address=e['address']-0x6000;assert shadow[address]==e['storage_byte_before_write'];shadow[address]=e['physical_storage_byte_after_event']
  while frame<=CASES[case]['frames']:
   assert shadow[:960]==(folder/f'frame-{frame:03d}-sram.bin').read_bytes()[:960];frame+=1
  snapshots=(folder/'snapshots.bin').read_bytes();index=list(map(json.loads,(folder/'snapshot-index.jsonl').read_text().splitlines()));by_seq={e['sequence']:e for e in events};assert len(snapshots)==len(index)*10240
  for i,item in enumerate(index,1):
   e=by_seq[item['event_sequence']];payload=snapshots[(i-1)*10240:i*10240];r,s=payload[:2048],payload[2048:];assert item['snapshot_sequence']==e['full_snapshot_sequence']==i and item['frame']==e['frame']==1
   assert digest(payload)==item['sha256']and digest(r)==item['RAM_sha256']and digest(s)==item['SRAM_sha256']and list(r[:0x30])==e['ZP_0000_002F']
   assert e['battle_0506_0507_050E_0514']==[r[x]for x in(0x506,0x507,0x50E,0x514)]and e['RAM0500_0503']==list(r[0x500:0x504])and e['RAM0514_0517']==list(r[0x514:0x518])and e['RAM0518_051B']==list(r[0x518:0x51C])
   assert item['actual_registers']==dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC'])and item['actual_PRG_banks']==e['actual_PRG_banks']
   assert not item['instantaneous_N163_PPU_APU_captured']and item['capture_core_sha256']==OBSERVER_SHA and item['additional_core_memory_writes']==0
   assert(folder/item['exported_RAM']).read_bytes()==r and(folder/item['exported_SRAM']).read_bytes()==s
   sp=e['SP'];word=r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8;assert word==e['stack_top_word_raw']&65535
  ob=next(x for x in self.record(OUT/'runtime/postbattle-observations.json',False)['routes']if x['case']==case);stores=[e for e in events if e['logical_G106_city_store']];reads=[e for e in events if e['logical_G106_city_read']];dummy=[e for e in events if e['G106_STA_dummy_read']]
  assert ob['logical_G106_stores']==stores and ob['logical_G106_reads']==reads and ob['STA_indirect_Y_dummy_bus_reads']==dummy
  assert not any(e['target_type']=='city_auxiliary_bus'for e in events)
  if CASES[case]['natural']:assert not stores and not reads and len(index)==3
  else:
   assert(len(stores),len(reads),len(dummy),len(index))==(11,15,11,11)
   assert Counter(x['opcode_PC']for x in reads)=={0xBF74:1,0xBFA0:5,0xBFA6:5,0xBFEC:2,0xBFF2:2}
   assert Counter(x['opcode_PC']for x in stores)=={0xBFDF:6,0xBFE9:5}and all(x['actual_PRG_banks']==[16,8,9,31]and x['pointer_001A_001B']==0x6080 and x['address']==0x6080+x['Y']and x['value']==x['physical_storage_byte_after_event']for x in stores)
   assert sum(x['storage_byte_before_write']!=x['physical_storage_byte_after_event']for x in stores)==7
   for store in stores:
    prev=next(x for x in reversed(events[:store['sequence']-1])if x['kind']=='read'and x['opcode_PC']==store['opcode_PC']and x['address']==store['address']);assert prev['physical_storage_byte_after_event']==store['storage_byte_before_write']and prev['G106_STA_dummy_read']
   assert Counter(x['entry']for x in index)=={0xBAB3:1,0xBF0A:1,0xBF9E:5,0xBFB3:1,0xBFEC:2,0xC027:1}
  bf=next(x for x in index if x['entry']==0xBF0A);assert bf['stack_top_word_raw']&65535==0xBB98

 def core_provenance(self):
  folder=OUT/'runtime/core-provenance';v=self.record(folder/'build.json',False);assert v['commit']=='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
  assert v['first_build_clean_new_tree']and v['final_source_clean_build']and v['dependency_rebuild_byte_identical']and not v['modified_emulator_object_layout']and v['extra_emulated_bus_reads']==v['extra_emulated_bus_writes']==0
  for item in[v['original_core'],v['passive_observer'],v['parent_frozen_patch']]+v['unchanged_old_observers']:self.pin(item['path'],item['sha256'])
  assert v['original_core']['sha256']==CORE_SHA and v['passive_observer']['sha256']==OBSERVER_SHA
  patch=(folder/'observer.patch').read_bytes();assert digest(patch)==v['patch_sha256'];originals={x['path']:(folder/'upstream'/x['path']).read_bytes()for x in v['source_files']};generated=base.base.prior.apply_patch_readonly(patch,originals)
  for item in v['source_files']:assert digest(originals[item['path']])==item['original_sha256']and digest(generated[item['path']])==item['patched_sha256']
  for path in(folder/'patched').rglob('*'):
   if path.is_file():assert path.read_bytes()==generated[str(path.relative_to(folder/'patched'))]
  watch=generated['source/core/NstWatch.cpp.inc'].decode();board=generated['source/core/board/NstBoard.cpp'].decode();make=generated['libretro/Makefile'].decode()
  assert 'map.Peek'not in watch and 'map.Poke'not in watch and 'out[i]=b.wrk[0][i]'in board and 'e[17]=source[5];'in watch
  assert 'memory[0xDE]'in watch and 'memory[0xDF]'in watch and '++watch_overflow'in watch and '++watch_snapshot_overflow'in watch and v['include_dependency_declared']in make
  assert generated['source/core/NstCpu.hpp']==originals['source/core/NstCpu.hpp']
  self.counts['observer_upstream_source_files_patch_reconstructed_readonly']=len(originals)

 def source_cases(self):
  v=self.record(OUT/'resources/validation.json');e=self.record(OUT/'resources/evidence.json');c=self.record(OUT/'resources/static-catalog.json',False)
  if v['quick']:raise Pending('Child Source still quick')
  assert v['failed_count']==0 and v['failures']==[]and v['original_CPU_parent_cases']==len(v['cases'])==3197 and v['counts']==dict(actual_caller_RTS=3194,strict_missing_dependency_prefix=3)and Counter(x['comparison']for x in v['cases'])==v['counts']
  assert v['source_guard_count']==len(v['guards'])==7 and all(x['status']=='passed'for x in v['guards'])and v['source_original_CPU_callbacks']==0 and not v['production_IR_interpretation']and not v['Native_internal_CPU_trace']
  for row in v['cases']:assert(row['RAM_bytes'],row['SRAM_bytes'])==(2048,8192)and row['AXYP_SP_PC_ordered_IO_four_banks_N163_equal']and row['combined_logical_IO_read_write_interleaving_equal']and row['source_original_CPU_callbacks']==0
  visited={(x['physical_bank'],x['cpu_address'])for x in v['executed_instruction_positions']}
  for row in c['original_instructions']:
   bank=row.get('physical_bank',row.get('bank'));pc=row.get('cpu',row.get('pc'));self.raw(dict(row,physical_bank=bank,cpu=pc));assert(bank,pc)in visited
  i=self.record(OUT/'source-integration.json');assert i['original_CPU_parent_cases']==len(i['rows'])and Counter(x['completion']for x in i['rows'])==i['counts']and i['guard_count']==len(i['guards'])==4 and i['source_original_CPU_callbacks']==0
  assert i['original_CPU_parent_cases']==58 and i['inherited_regression_cases']==48 and i['new_resource_caller_cases']==10 and i['counts']==dict(returned=57,nonlocal_return=1)
  assert i['new_resource_ancestries']==dict(controlled_ancestry=9,natural_ancestry=1)and i['new_resource_transfers']==dict(call=9,tail=1)
  assert all(x['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and x['combined_logical_IO_order_equal']and x['source_original_CPU_callbacks']==0 for x in i['rows'])
  ancestry_keys=('ancestry_origin','controlled_ancestry','natural_ordinary_input_route','known_inherited_preparation_byte_writes','ancestry_provenance','actual_call_kind','immediate_transfer_PC','immediate_transfer_proof','real_return_frame_owner')
  for row in i['rows']:
   if not row['case'].startswith('postbattle-resource/'):continue
   context=read(OUT/'cpu-resource/actual-callers'/row['case'].split('/',1)[1]/'context.json')
   assert row['ancestry_context']=={k:context[k]for k in ancestry_keys}and row['inherited_Native_preparation']==context['inherited_Native_preparation']and row['prepared_new_bytes']is False
  for name in('postbattle_resource_services.py','postbattle_resource_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
     names=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module or''];assert not any(any(b in n for b in('py65','state_machine','importlib'))for n in names)
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.actual_contexts27();counts=v['counts'];self.counts.update(source_child_CPU_cases=len(v['cases']),source_child_guards=7,source_integration_CPU_cases=len(i['rows']),source_integration_guards=4,new_Source_CPU_cases=len(v['cases'])+len(i['rows']),new_Source_guards=11,new_Source_actual_caller_RTS=counts.get('actual_caller_RTS',0)+i['counts'].get('returned',0),new_Source_nonlocal_return=i['counts'].get('nonlocal_return',0),new_Source_strict_dependency_prefix=counts.get('strict_missing_dependency_prefix',0),new_semantic_first_recovery=0)

 def actual_contexts27(self):
  paths=sorted((OUT/'cpu-resource/actual-callers').glob('entry-*/context.json'))
  if not paths:raise Pending('No formal actual-caller exports yet')
  assert len(paths)==10
  controlled=natural=0
  for path in paths:
   row=self.record(path,False);assert row['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and row['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   assert row['prepared_numeric_bytes']==row['additional_CPU_prepared_numeric_bytes']==[]and row['injected_new_NMI']==row['injected_new_IRQ']==0 and not row['synthetic_caller_PC_or_stack']
   capture=row['passive_capture'];self.pin(capture['metadata'],capture['metadata_sha256']);meta=read(ROOT/capture['metadata']);self.pin(capture['manifest'],capture['manifest_sha256']);r=(ROOT/capture['RAM_path']).read_bytes();s=(ROOT/capture['SRAM_path']).read_bytes();self.pin(capture['RAM_path'],capture['RAM_sha256']);self.pin(capture['SRAM_path'],capture['SRAM_sha256'])
   assert r==(path.parent/'input-ram.bin').read_bytes()and s==(path.parent/'input-sram.bin').read_bytes()and row['registers']==meta['actual_registers']and row['physical_banks']==meta['actual_PRG_banks']and row['actual_software_state_captured']and not row['unmodified_core_internal_trace']
   assert row['known_inherited_preparation_byte_writes']==meta['known_inherited_preparation_byte_writes']
   if row['controlled_ancestry']:
    controlled+=1;assert not row['natural_ordinary_input_route']and row['known_inherited_preparation_byte_writes']==19 and len(row['inherited_Native_preparation'])==19
   else:
    natural+=1;assert row['natural_ordinary_input_route']and row['known_inherited_preparation_byte_writes']==0 and not row['inherited_Native_preparation']
   sp=row['registers']['sp'];assert row['existing_return_PC']==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535
   proof=row['immediate_transfer_proof'];preceding=proof['preceding_observed_opcode_boundary'];callee=proof['callee_opcode_boundary']
   event_folder=(ROOT/capture['metadata']).parent;by_sequence={x['sequence']:x for x in map(json.loads,(event_folder/'events.jsonl').read_text().splitlines())}
   assert preceding==by_sequence[preceding['sequence']]and callee==by_sequence[callee['sequence']]and callee['full_snapshot_sequence']==meta['snapshot_sequence']and proof['not_inferred_from_return_stack']
   for event in proof['actual_operand_bus_events']:assert event==by_sequence[event['sequence']]
   transfer=row['immediate_transfer_PC'];assert preceding['opcode_PC']==transfer and callee['opcode_PC']==row['registers']['pc']
   offset=original(preceding['physical_bank'],transfer);raw=self.rom[offset:offset+3];assert proof['ROM_bytes']==' '.join(f'{b:02X}'for b in raw)and raw[0]==(0x4C if row['actual_call_kind']=='tail'else 0x20)and raw[1]|raw[2]<<8==callee['opcode_PC']
   if row['actual_call_kind']=='tail':assert callee['SP']==preceding['SP']and callee['stack_top_word_raw']==preceding['stack_top_word_raw']and transfer==0xBF9B and row['existing_return_PC']==0xBB99
   else:assert callee['SP']==(preceding['SP']-2)&255 and row['existing_return_PC']==(transfer+3)&65535
   fixture=(path.parent/'input-n163.bin').read_bytes();assert len(fixture)==128 and digest(fixture)==row['explicit_N163_fixture']['sha256']and row['N163_address']==127 and row['N163_autoincrement']
  assert(controlled,natural)==(9,1)
  self.counts['actual_passive_software_callee_exports']=10

 def static_fields(self):
  f=OUT/'fields-static';v=self.record(f/'verification.json');s=self.record(f/'analysis-summary.json');self.record(f/'evidence.json');rows=self.record(f/'all-indirect-accesses.json',False)['accesses'];old={(x['physical_bank'],x['cpu']):x for x in read(ROOT/'analysis/phase26/fields-static/all-indirect-accesses.json')['accesses']}
  assert v['source_CPU_cases']==s['source_CPU_cases']==0 and v['failed_count']==0 and v['original_contract_CPU_cases']==5891 and(v['actual_caller_RTS_CPU_cases'],v['constructor_prefix_CPU_cases'],v['bare_access_counterexample_prefix_CPU_cases'])==(5632,256,3)and v['model_guard_check_count']==len(v['model_checks'])==16 and all(x['passed']for x in v['model_checks'])and len(rows)==1526 and{(x['physical_bank'],x['cpu'])for x in rows}==set(old)
  changed=[]
  for row in rows:
   self.raw(row);key=(row['physical_bank'],row['cpu']);p=row['address_contract']
   if p:
    hit=base.base.prior.prior.old.intersection(p);assert hit==p['possible_auxiliary_effective_addresses']and len(hit)==p['auxiliary_address_intersection_count']
    if row['classification']==DISJOINT:assert not hit
   if row['classification']!=old[key]['classification']:changed.append(key);assert row['classification']==DISJOINT
   else:assert p==old[key]['address_contract']
  assert set(changed)=={(8,pc)for pc in(0xBF74,0xBFA0,0xBFA6,0xBFDF,0xBFE9,0xBFEC,0xBFF2)}and s['previous_candidate_count']==335 and s['remaining_access_count']==328 and s['newly_proved_disjoint_all_count']==7
  assert Counter(x['classification']for x in rows)==s['all_indirect_classification_counts']==dict(proved_disjoint_auxiliary_address_domain=1198,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=247)
  assert all(x is None for x in s['official_target_field_names'].values())and not s['complete_analysis_fixed_point_proven']
  self.counts.update(static_Source_CPU_cases=0,static_original_CPU_contract_cases=v['original_contract_CPU_cases'],static_model_guards=v['model_guard_check_count'],static_remaining_candidates=328,static_new_conditional_exclusions=7)

 def context(self):
  f=OUT/'context';v=self.record(f/'verification.json');s=self.record(f/'analysis-summary.json',False);self.record(f/'evidence.json');assert v['Source_CPU_cases']==v['original_CPU_cases']==v['Native_runs']==s['Source_CPU_cases']==s['original_CPU_cases']==s['Native_runs']==0 and v['check_count']==len(v['checks'])==43 and all(x['status']=='passed'for x in v['checks'])
  assert s['focused_group']=='G106'and s['selected_access_count']==7 and s['baseline_remaining_candidates']==335 and s['context_new_static_exclusions']==0 and s['current27_new_owned_entries']==4 and not s['parent_A006_BAB3_BB93_owner_found']and not s['new_Source_first_recovery_claim']and s['unknown_unique_services']is None
  for name in('owner-and-caller-chain','current27-owner-scope','semantic-deduplication','pointer-and-field-context','stable-denominators-and-acceptance'):self.record(f/(name+'.json'),False)
  self.counts.update(context_reference_checks=43,context_Source_CPU_cases=0,context_original_CPU_cases=0,context_Native_runs=0)

 def acceptance(self):
  f=OUT/'acceptance';v=self.record(f/'verification.json');r=self.record(f/'requirements.json',False);p=self.record(f/'request-provenance.json',False)
  assert v['source_CPU_cases']==v['original_CPU_cases']==v['Native_frames']==0 and not r['overall_reverse_engineering_complete']and r['completion_percentage']is None and v['direct_user_message_locator_checks']==11 and v['dimension_status_and_receipt_checks']==10 and v['coordinator_report_separately_labelled']
  messages={x['message_id']:x for x in p['source_messages']};locators={x['request_id']:x for x in p['request_locators']};assert len(locators)==11 and len(r['dimensions'])==10
  assert v['evidence_reference_checks']==104 and v['source_syntax_checks']==100 and v['current_summary_cross_receipt_checks']==10
  for user in r['user_request_register']:
   locator=locators[user['id']];message=messages[locator['message_id']];assert user['quote']in message['text']and locator['turn_id']==message['turn_id']and message['source_kind']=='read_thread_userMessage'
   source=user['source'];assert source['source_kind']=='direct_human_userMessage'and source['message_id']==locator['message_id']and source['turn_id']==locator['turn_id']
  assert p['coordination_report']['source_kind']=='coordinator_delegation_report'and p['coordination_report']['not_verbatim_user_quote']
  for row in r['dimensions']:
   assert row['acceptance_status']and row['verified_results']and row['pending_results']and row['phase27_change']['result']and row['phase27_change']['remaining_gap']
   for item in row['verified_results']:assert item['claim']and item['evidence']in row['evidence'];self.pin(item['evidence'])
  self.counts.update(acceptance_dimensions=10,acceptance_exact_user_message_locators=11,acceptance_reference_checks_not_gameplay=v['evidence_reference_checks'],acceptance_Source_syntax_checks_not_CPU=v['source_syntax_checks'],acceptance_Source_CPU_cases=0,acceptance_Native_frames=0)

 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing final Root report')
  qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'README.md');self.pin(OUT/'index.html',qa['final_html_sha256']);assert qa['status']=='passed'and qa['failed_count']==0 and qa['check_count']==len(qa['checks'])and all(x['status']=='passed'for x in qa['checks'])
  assert qa['console_errors']==qa['console_warnings']==[]and qa['Native_frames_added']==qa['Source_CPU_cases_added']==0
  page=base.base.PortalPage();page.feed((OUT/'index.html').read_text());payload=json.loads(page.evidence)
  assert len(page.sources)==2 and all((ROOT/'source/recovered'/name).read_text()in page.sources for name in('postbattle_resource_services.py','postbattle_resource_integration.py'))
  assert payload['native']==read(OUT/'runtime/evidence.json')['summary']and payload['acceptance']==read(OUT/'acceptance/requirements.json')
  for key,file in(('owners','current27-owner-scope'),('chain','owner-and-caller-chain'),('pointer','pointer-and-field-context')):assert payload[key]==read(OUT/'context'/(file+'.json'))
  for key,name,keys in(('source','resources/validation.json',('original_CPU_parent_cases','counts','source_guard_count')),('integration','source-integration.json',('original_CPU_parent_cases','counts','guard_count')),('static','fields-static/analysis-summary.json',('all_indirect_classification_counts','remaining_access_count','newly_proved_disjoint_all_count'))):
   value=read(OUT/name);assert payload[key]=={k:value[k]for k in keys}
  cv=read(OUT/'fields-static/verification.json');assert payload['contract_counts']=={k:v for k,v in cv.items()if type(v)is int}
  observed=read(OUT/'runtime/postbattle-observations.json');native=read(OUT/'runtime/evidence.json');event_total=0
  assert len(payload['routes'])==2
  for route,(case,config)in zip(payload['routes'],CASES.items()):
   folder=OUT/'runtime'/case;ob=next(x for x in observed['routes']if x['case']==case)
   assert route['case']==case and route['base']=='runtime/'+case+'/'and route['points']==read(folder/'original-control/checkpoints.json')==read(folder/'observer/checkpoints.json')and route['ancestry']==native['case_ancestry'][case]
   keys=('observer_events','logical_read_count','STA_dummy_read_count','store_count','changed_byte_count','unchanged_write_count');assert route['observed_counts']=={k:ob[k]for k in keys}
   expected=[]
   for key,role in(('software_entries','actual_opcode_entry'),('logical_G106_reads','G106_logical_LDA'),('STA_indirect_Y_dummy_bus_reads','G106_STA_dummy'),('logical_G106_stores','G106_STA_store'),('following_other_city_gold_grain_writes','later_supply_return_not_G106')):expected.extend(dict(**event,display_role=role)for event in ob[key])
   assert route['events']==sorted({e['sequence']:e for e in expected}.values(),key=lambda e:e['sequence']);event_total+=len(route['events']);assert len(route['audio'])==2
   for variant,audio in zip(('original-control','observer'),route['audio']):
    path=OUT/audio['path'];assert path==folder/variant/'full-audio.wav';self.pin(path,audio['sha256'])
    with wave.open(str(path))as wav:assert(audio['sample_frames'],audio['duration_seconds'])==(wav.getnframes(),wav.getnframes()/48000)and(wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000)
  assert event_total==67
  selected={x['cpu']:x for x in read(OUT/'fields-static/selected-accesses.json')['accesses']};assert len(payload['accesses'])==len(selected)==7
  for item in payload['accesses']:
   row=selected[item['cpu']];contract=row['address_contract'];assert item['physical_bank']==row['physical_bank']and item['raw_hex']==row['raw_hex']and item['pointer_count']==len(contract['whole_pointer_values'])and item['Y_values']==contract['Y_values']and item['requirements']==contract['required_execution_contract']and item['auxiliary_intersection']==0
   assert item['logical_address_count']==len({(p+y)&65535 for p in contract['whole_pointer_values']for y in contract['Y_values']})
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path in(OUT/'verification.json',OUT/'package-receipt.json')or path.suffix=='.zip':continue
   assert path.is_file(),('Broken portal link',link)
  for name,pin in qa['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  self.counts.update(browser_checks=qa['check_count'],browser_Source_modules=2,browser_Native_points=96,browser_actual_events=67,browser_WAVs=4)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA
 audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[];audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('context',audit.context),('acceptance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');audit.pin(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP and manifest['foundational_archive']['sha256']==V22_ZIP and manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase27']
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in base.base.prior.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots']);names=set(manifest['include_files']);included={k:v for k,v in audit.pins.items()if k in names or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase27-G106-postbattle-pointer-readonly-audit-v1',status='pending_final_artifacts'if pending else'passed',ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v26_incremental_preserved_sha256=OLD_ZIP,old_phase26_audit_sha256=OLD_AUDIT,old_phase26_postZIP_receipt_sha256=OLD_POSTZIP,old_v22_preserved_sha256=V22_ZIP,source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guards',0),source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),limits=['Read-only evidence audit; no CPU/core/producers/analyzers/old audit main executed.','Natural skip and controlled-ancestry positive paths are separate;19 known ancestor bytes plus incomplete earlierlegacy preparation are explicit.','Separate27 observer alone suppliesinternal events, no instantaneous N163/PPU/APU.','G106 logicalLDA15,STA11,dummy11,changed7/same4 and followingC027 supply return are separate scopes.','Source cases/static CPU contracts/context/reference checks/Native frames never added together;wholeROM completionandstandalone source are unproven.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))
if __name__=='__main__':main()
