#!/usr/bin/env python3
"""Read-only phase29 audit. Only new analysis/phase29/verification.json is written.

No CPU/core, producer, analyzer, historical audit main or generator is executed.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys,wave
from urllib.parse import urlparse,unquote
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase29';sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('readonly_phase27_audit',ROOT/'scripts/verify_phase27.py');base=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=base;SPEC.loader.exec_module(base)
from capture_native_postbattle_completion import decode_event,fields,CASES,CORE_SHA,OBSERVER_SHA,RECORD_BYTES
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=base.ROM_SHA;sha=base.sha;read=base.read;original=base.original;DISJOINT=base.DISJOINT;Pending=base.Pending
OLD_AUDIT='898835c1f8872349057258ee970f0bb7e0299d9705517ee78e0ab659c9926feb'
OLD_ZIP='d85403fec9ad380c8490cfe93947605dacf1ef7981ebe83101ee0e466e468f7e'
OLD_POSTZIP='563820c7c83d7023c223855369592d3e61887c53806e799490f073436b3d72e6'
V22_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(p):return str(Path(p).resolve().relative_to(ROOT))

class Audit(base.Audit):
 def frozen_history(self):
  self.pin('analysis/phase28/verification.json',OLD_AUDIT);v=read(ROOT/'analysis/phase28/verification.json');assert v['status']=='passed'and not v['pending']and v['ROM_sha256']==ROM_SHA and v['rebuilt_byte_identical']
  assert(len(v['source_and_validator_sha256']),len(v['artifact_and_dependency_sha256']))==(551,49452)
  self.frozen_names=set(v['source_and_validator_sha256'])|set(v['artifact_and_dependency_sha256'])
  for name,p in v['source_and_validator_sha256'].items():self.pin(name,p);self.sources[name]=p
  for name,p in v['artifact_and_dependency_sha256'].items():self.pin(name,p)
  self.pin('analysis/phase28/package-receipt.json',OLD_POSTZIP);p=read(ROOT/'analysis/phase28/package-receipt.json');assert p['status']=='passed'and p['phase28_audit_sha256']==OLD_AUDIT and p['sha256']==OLD_ZIP and p['file_count']==2730
  self.pin('build/三国志2超级版-逆向分析-v28增量.zip',OLD_ZIP);self.pin('build/三国志2超级版-逆向分析.zip',V22_ZIP);assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.counts.update(unchanged_phase28_source_script_pins=551,unchanged_phase28_artifact_dependency_pins=49452,unchanged_phase28_postZIP_receipts=1)

 def ancestry28(self,c,ancestor):
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
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json');assert e['summary']=={k:v[k]for k in e['summary']};self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_postbattle_completion.py',v['script_sha256'])
  expected=dict(completion_city_read_count=77,completion_adjacency_read_count=12,completion_leader_read_count=12,completion_city_store_count=15,completion_changed_bytes=1,completion_same_value_stores=14,completion_STA_dummy_read_count=15,routes=2,natural_routes=1,controlled_ancestry_routes=1,core_variants=2,fresh_process_runs=8,original_first_frames=96,all_control_frames=384,original_checkpoints=96,nonempty_artifact_repeat_checks=1182,PNG_checks=192,WAV_checks=4,observer_events=256197,full_software_snapshots=120,logical_G106_reads=15,G106_STA_dummy_read_count=11,G106_store_count=11,G106_changed_byte_count=7,G106_unchanged_store_count=4,city_auxiliary_bus_events=0,ECEE_requests=2,ECEE_immediate_RTS_returns=2,sub3_hold_checks=38,fade_completion_EC95_writes=2,phase3_native_releases=2,unchanged_phase28_original_fivebuffer_frames=96,additional_core_memory_writes=0,cold_boots=0,state_imports=8,Source_CPU_cases=0,failed_count=0)
  assert all(v[k]==x for k,x in expected.items())and all(v[k]for k in('all_five_complete_buffers_equal_each_frame','all_complete_initial_API_buffers_equal','all_artifacts_repeat_exact','full_serialized_buffers_not_normalized'))
  artifacts=images=wavs=0
  for case,c in CASES.items():
   self.ancestry28(c,e['case_ancestry'][case]);mother=ROOT/c['mother'];m=NestopiaContext.parse(mother.read_bytes());original_rows=None
   for variant,core in(('original-control',CORE_SHA),('observer',OBSERVER_SHA)):
    first=folder/case/variant;second=OUT/'runtime-repeat'/case/variant;a=self.record(first/'validation.json');b=self.record(second/'validation.json');repeat=self.record(first/'repeat-validation.json');assert a==b and a['core']['core_sha256']==core
    assert a['frames']==a['checkpoint_count']==c['frames']and a['state_imported']and not a['cold_boot']and a['additional_core_memory_writes']==a['Source_CPU_cases']==0 and not a['original_core_internal_CPU_trace']
    assert a['natural_ordinary_input_route']==c['natural']and a['controlled_ancestry']==(not c['natural'])and a['known_inherited_preparation_byte_writes']==(0 if c['natural']else 19)
    self.ancestry28(c,a['ancestry']);prep=self.record(first/'preparation.json',False);assert prep==e['case_ancestry'][case]==a['ancestry']and repeat['all_bytes_exact']and repeat['artifact_checks']==len(a['artifact_sha256'])
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
   self.observer28(folder/case/'observer',case)
  assert(artifacts,images,wavs)==(1182,192,4);self.core_provenance();self.record(folder/'media-static-validation.json')
  self.counts.update({f'Native_{k}':x for k,x in expected.items()})

 def observer28(self,folder,case):
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
    assert shadow[:960]==(folder/f'frame-{frame:03d}-sram.bin').read_bytes()[:960];frame+=1
   if e['kind']=='write_attempt'and 0x6000<=e['address']<0x63C0:
    address=e['address']-0x6000;assert shadow[address]==e['storage_byte_before_write'];shadow[address]=e['physical_storage_byte_after_event']
  while frame<=CASES[case]['frames']:
   assert shadow[:960]==(folder/f'frame-{frame:03d}-sram.bin').read_bytes()[:960];frame+=1
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
  ob=next(x for x in self.record(OUT/'runtime/postbattle-observations.json',False)['routes']if x['case']==case);stores=[e for e in events if e['logical_G106_city_store']];reads=[e for e in events if e['logical_G106_city_read']];dummy=[e for e in events if e['G106_STA_dummy_read']]
  assert ob['logical_G106_stores']==stores and ob['logical_G106_reads']==reads and ob['STA_indirect_Y_dummy_bus_reads']==dummy
  assert not any(e['target_type']=='city_auxiliary_bus'for e in events)
  if CASES[case]['natural']:assert not stores and not reads and len(index)==56
  else:
   assert(len(stores),len(reads),len(dummy),len(index))==(11,15,11,64)
   assert Counter(x['opcode_PC']for x in reads)=={0xBF74:1,0xBFA0:5,0xBFA6:5,0xBFEC:2,0xBFF2:2}
   assert Counter(x['opcode_PC']for x in stores)=={0xBFDF:6,0xBFE9:5}and all(x['actual_PRG_banks']==[16,8,9,31]and x['pointer_001A_001B']==0x6080 and x['address']==0x6080+x['Y']and x['value']==x['physical_storage_byte_after_event']for x in stores)
   assert sum(x['storage_byte_before_write']!=x['physical_storage_byte_after_event']for x in stores)==7
   for store in stores:
    prev=next(x for x in reversed(events[:store['sequence']-1])if x['kind']=='read'and x['opcode_PC']==store['opcode_PC']and x['address']==store['address']);assert prev['physical_storage_byte_after_event']==store['storage_byte_before_write']and prev['G106_STA_dummy_read']
   assert sum(x['entry']==0xBF9E for x in index)==5
  bf=next(x for x in index if x['entry']==0xBF0A);assert bf['stack_top_word_raw']&65535==0xBB98
  self.palette_lifecycle_check(folder,case,events)
  self.completion_lifecycle_check(folder,case,events,index,snapshots)

 def completion_lifecycle_check(self,folder,case,events,index,snapshots):
  ob=next(x for x in self.record(OUT/'runtime/completion-lifecycle-observations.json',False)['routes']if x['case']==case)
  start=next(e for e in events if e['kind']=='opcode_boundary'and e['physical_bank']==8 and e['opcode_PC']==0xBBB8);end=next(e for e in events if e['kind']=='opcode_boundary'and e['physical_bank']==8 and e['opcode_PC']==0xBBB7 and e['sequence']>start['sequence']);window=[e for e in events if start['sequence']<=e['sequence']<=end['sequence']]
  assert ob['BBB8_entry']==start and ob['parent_BBB7_before_RTS']==end and ob['all_selected_completion_events']==window and start['frame']==end['frame']==21 and start['stack_top_word_raw']&65535==0xBBA7 and end['SP']==start['SP']+2
  city=[];leader=[];adj=[];stores=[];dummy=[]
  for e in window:
   if e['physical_bank']!=8:continue
   pc,a,y=e['opcode_PC'],e['address'],e['Y'];zp=e['ZP_0000_002F'];p0=zp[0]|zp[1]<<8;pA=zp[10]|zp[11]<<8;ea=((p0 if pc in(0xBBD6,0xBC1C,0xBBDD)else pA)+y)&65535
   if e['kind']=='read'and pc in(0xBBD6,0xBC0E,0xBC23,0xBC34)and a==ea:city.append(e)
   if e['kind']=='read'and pc==0xBC1C and a==ea:leader.append(e)
   if e['kind']=='read'and pc==0xBBEB and a==(0x9D72+y)&65535:adj.append(e)
   if pc in(0xBBDD,0xBC3C,0xBC43)and a==ea:
    if e['kind']=='write_attempt':stores.append(e)
    elif e['kind']=='read':dummy.append(e)
  assert(city,leader,adj,stores,dummy)==tuple(ob[k]for k in('logical_city_reads','leader_record_reads','adjacency_ROM_reads','city_stores','STA_dummy_bus_reads'))
  assert(len(city),len(leader),len(adj),len(stores),len(dummy))==((34,6,6,8,8)if CASES[case]['natural']else(43,6,6,7,7))
  assert [e['value']for e in adj]==[2,12,11,3,1,255]and all(e['data_physical_bank']==16 and e['value']==self.rom[e['data_ROM_offset']]for e in adj)
  entries=[e for e in window if e['kind']=='opcode_boundary'and e['opcode_PC']==0xBC00];assert entries==ob['BC00_entries']and[e['pointer_0000_0001']for e in entries]==[0x6080,0x6040,0x6180,0x6160,0x6060,0x6020]
  for entry in entries:
   i=entry['full_snapshot_sequence']-1;ram=snapshots[i*10240:i*10240+2048];sram=snapshots[i*10240+2048:(i+1)*10240];p0=ram[0]|ram[1]<<8;assert p0==entry['pointer_0000_0001']and index[i]['entry']==0xBC00 and sram[p0-0x6000]&15!=7
  changed=[e for e in stores if e['storage_byte_before_write']!=e['physical_storage_byte_after_event']];assert len(changed)==ob['changed_store_count']==(0 if CASES[case]['natural']else 1)and len(stores)-len(changed)==ob['same_value_store_count']==(8 if CASES[case]['natural']else 6)and not ob['observed_nontrivial_roster_swap']
  if changed:assert(changed[0]['opcode_PC'],changed[0]['address'],changed[0]['storage_byte_before_write'],changed[0]['physical_storage_byte_after_event'])==(0xBBDD,0x6080,1,2)
  assert all(e['actual_PRG_banks']==[16,8,9,31]for e in stores)and all(e['Y']in range(17,27)for e in city if e['opcode_PC']==0xBC23)
  for offset in(0x6060,0x6020):assert [e['Y']for e in city if e['opcode_PC']==0xBC23 and e['saved_city_pointer_000A_000B']==offset]==list(range(17,27))
  self.counts['completion_actual_BC00_software_entries']=self.counts.get('completion_actual_BC00_software_entries',0)+len(entries)

 def palette_lifecycle_check(self,folder,case,events):
  byseq={e['sequence']:e for e in events};life=next(x for x in self.record(OUT/'runtime/palette-lifecycle-observations.json',False)['routes']if x['case']==case)
  def checkevents(value):
   if isinstance(value,dict):
    if value.get('kind')in('opcode_boundary','read','word_read_low','word_read_high','write_attempt')and'sequence'in value:assert value==byseq[value['sequence']]
    else:
     for x in value.values():checkevents(x)
   elif isinstance(value,list):
    for x in value:checkevents(x)
  checkevents(life);begin,ret,resume=life['ECEE_entry'],life['ECEE_before_immediate_RTS'],life['same_caller_resumed_BB96'];end=life['fade_original_completion87_write'];assert(begin['opcode_PC'],ret['opcode_PC'],resume['opcode_PC'],end['opcode_PC'])==(0xECEE,0xED18,0xBB96,0xEC95)
  assert begin['frame']==ret['frame']==resume['frame']==1 and end['frame']==21 and begin['SP']==ret['SP']and resume['SP']==(ret['SP']+2)&255
  assert begin['stack_top_word_raw']&65535==ret['stack_top_word_raw']&65535==0xBB95 and begin['fade_0087_008A']==[255,0,4,4]and ret['fade_0087_008A']==[1,0,4,4]
  assert ret['palette_backup_0120_013F']==begin['palette_active_0100_011F']and ret['palette_active_0100_011F']==begin['palette_active_0100_011F']
  assert[(x['storage_byte_before_write'],x['captured_RAM_byte_after_write'])for x in life['phase2_to3_original_RMW_write_attempts']]==[(2,2),(2,3)]
  assert life['phase2_before_RTS']['RAM0500_0503'][1]==3 and life['phase2_before_RTS']['fade_0087_008A'][0]==1
  holds=life['sub3_hold_records'];assert len(holds)==19 and[x['gate']['frame']for x in holds]==list(range(2,21))
  for h in holds:
   assert h['gate']['fade_0087_008A'][0]==h['BPL_branch']['A']==1 and not h['BPL_branch']['P']&128 and h['hold_return_before_RTS']['opcode_PC']==0xBBB7
   assert h['gate']['SP']==h['hold_return_before_RTS']['SP']and h['gate']['stack_top_word_raw']==h['hold_return_before_RTS']['stack_top_word_raw']and h['fresh_parent_far_call']['stack_top_word_raw']&65535==0xD4F7
  assert[(x['frame'],x['captured_RAM_byte_after_write'])for x in life['fade_original_88_progression']]==[(6,1),(11,2),(16,3),(21,4)]and len(life['fade_original_0100_011F_writes'])==128
  assert life['sub3_completion_gate']['fade_0087_008A'][0]==255 and life['sub3_native_cleanup_entry']['opcode_PC']==0xBBB8 and life['later_independent_palette_requests'][0]['opcode_PC']==0xECBF and life['later_independent_palette_requests'][0]['frame']==24
  assert life['D4F5_middle_entry']['Y']==40 and life['first_parent_bridge_return']['actual_PRG_banks']==[16,12,13,31]
  assert life['D4F5_middle_entry']['shadow_bank_bytes_00DE_00E5'][3]==49 and life['first_parent_far_before_RTS']['shadow_bank_bytes_00DE_00E5'][3]==48 and life['first_parent_far_before_RTS']['shadow_bank_bytes_00DE_00E5'][4]==44
  assert len(life['phase2_Source_actual_software_entries'])==4 and len(life['phase3_Source_unsupported_actual_inputs'])==2 and not read(OUT/'runtime/palette-lifecycle-observations.json')['Source_stage3_closure_claim']
  addresses=set((0,1,2,3,6,7,10,11,12,0x1A,0x1B,0x78,0x7A,0x400,0x401,0x500,0x501))|set(range(0x7D,0x81))|set(range(0x87,0x8B))|set(range(0xDE,0xE6))|set(range(0x100,0x140));ram=bytearray((folder/'initial-ram.bin').read_bytes());frame=1
  for e in events:
   while frame<e['frame']:
    final=(folder/f'frame-{frame:03d}-ram.bin').read_bytes();assert all(ram[a]==final[a]for a in addresses);frame+=1
   a=e['address']&0x7FF
   if e['kind']=='write_attempt'and e['address']<0x2000 and a in addresses:
    assert ram[a]==e['storage_byte_before_write'];ram[a]=e['value']
    if e['captured_RAM_byte_after_write']is not None:assert ram[a]==e['captured_RAM_byte_after_write']
  while frame<=CASES[case]['frames']:
   final=(folder/f'frame-{frame:03d}-ram.bin').read_bytes();assert all(ram[a]==final[a]for a in addresses);frame+=1

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

 def source_cases(self):
  v=self.record(OUT/'completion-services/validation.json');self.record(OUT/'completion-services/evidence.json');c=self.record(OUT/'completion-services/static-catalog.json',False)
  if v['quick']:raise Pending('Child Source still quick')
  assert v['failed_count']==0 and v['failures']==[]and v['original_CPU_parent_cases']==len(v['cases'])and Counter(x['comparison']for x in v['cases'])==v['counts']
  assert v['original_CPU_parent_cases']==2853 and v['controlled_cases']==2827 and v['passive_software_caller_cases']==26 and v['counts']==dict(actual_caller_RTS=2847,strict_dependency_prefix=6)
  assert v['source_guard_count']==len(v['guards'])==9 and all(x['status']=='passed'for x in v['guards'])and v['source_original_CPU_callbacks']==0 and not v['production_IR_interpretation']and not v['Native_internal_CPU_trace']
  for row in v['cases']:assert row['all2048_RAM_8192_SRAM_AXYP_SP_PC_combined_IO_four_banks_shared_N163_equal']and row['source_original_CPU_callbacks']==0
  assert(c['new_exact_protocol_positions'],c['new_exact_protocol_bytes'])==(81,166)and not c['new_semantic_first_recovery']
  assert v['new_regression_groups']=={'inherited_stage2_ECEE_protocol_in_completion_driver':2}
  stage2=[x for x in v['cases']if x['new_regression_group']=='inherited_stage2_ECEE_protocol_in_completion_driver'];assert len(stage2)==2 and{x['entry']for x in stage2}=={0xA006,0xBB93}
  for row in stage2:
   assert row['comparison']=='actual_caller_RTS'and len(row['sequence_checkpoints'])==1
   checkpoint=row['sequence_checkpoints'][0];assert checkpoint['kind']=='same_generator_ECEE_missing_service_false_completion_then_real_Shared'and checkpoint['same_pending_ServiceCall']and checkpoint['same_program_generator']and checkpoint['false_returned_without_PC_SP_did_not_advance']and checkpoint['no_repeated_previously_executed_state_or_IO']and checkpoint['fake_completion_attempts']==1 and checkpoint['not_a_cross_frame_palette_completion_wait']

  visited={(x['physical_bank'],x['cpu_address'])for x in v['executed_instruction_positions']}
  for row in c['original_instructions']:
   bank=row.get('physical_bank',row.get('bank'));pc=row.get('cpu',row.get('pc'));self.raw(dict(row,physical_bank=bank,cpu=pc));assert(bank,pc)in visited
  i=self.record(OUT/'source-integration.json');assert i['original_CPU_parent_cases']==len(i['rows'])and Counter(x['completion']for x in i['rows'])==i['counts']and i['guard_count']==len(i['guards'])and i['source_original_CPU_callbacks']==0
  assert all(x['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal']and x['combined_logical_IO_order_equal']and x['source_original_CPU_callbacks']==0 for x in i['rows'])
  assert i['original_CPU_parent_cases']==115 and i['inherited_regression_cases']==80 and i['new_completion_caller_cases']==34 and i['new_controlled_ECEE_regression_cases']==1 and i['counts']==dict(returned=110,nonlocal_return=1,dependency=4)and i['guard_count']==8
  assert Counter(x['comparison']for x in i['rows'])==i['comparison_counts']==dict(actual_caller_RTS=110,actual_nonlocal_return=1,strict_dependency_prefix=4)
  assert not i['production_IR_interpretation']and not i['Native_internal_CPU_trace']
  regressions=[x for x in i['rows']if x.get('ECEE_regression')];assert len(regressions)==1;reg=regressions[0]['ECEE_regression'];assert reg['entry']==0xA006 and reg['stage']==2 and reg['initial_missing']and reg['fake_return_checks']==2 and reg['same_original_call']and reg['same_owner_and_generator']and reg['unchanged_RAM_SRAM_registers_banks_IO_on_fake']and reg['real_Shared_continuation']and reg['real_Shared_ECEE_resolutions']==reg['parent_ECEE_call_records']==1 and reg['no_restart_or_repeated_partial_effects_compared_to_originalCPU']
  assert regressions[0]['comparison']=='actual_caller_RTS'

  for name in('postbattle_completion_services.py','postbattle_completion_integration.py'):
   tree=ast.parse((ROOT/'source/recovered'/name).read_text())
   for node in ast.walk(tree):
    if isinstance(node,ast.Import):assert all(not x.name.startswith(('py65','capture_','nes_runtime'))for x in node.names)
    if isinstance(node,ast.ImportFrom):assert not(node.module or'').startswith(('py65','capture_','nes_runtime'))
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
  self.actual_contexts29()
  self.counts.update(source_child_CPU_cases=len(v['cases']),source_child_guards=9,source_integration_CPU_cases=len(i['rows']),source_integration_guards=i['guard_count'],new_Source_CPU_cases=len(v['cases'])+len(i['rows']),new_Source_guards=9+i['guard_count'],new_Source_actual_caller_RTS=v['counts'].get('actual_caller_RTS',0)+i['counts'].get('returned',0),new_Source_nonlocal_return=i['counts'].get('nonlocal_return',0),new_Source_strict_dependency_prefix=v['counts'].get('strict_dependency_prefix',0)+i['counts'].get('dependency',0),new_semantic_first_recovery=0)

 def actual_contexts29(self):
  paths=sorted((OUT/'cpu-completion/actual-callers').glob('entry-*/context.json'))
  if len(paths)!=34:raise Pending('Final34 actual software caller exports not all present')
  controlled=natural=stage3=middle=0;integration=read(OUT/'source-integration.json');rootrows={x['case'].split('/',1)[1]:x for x in integration['rows']if x['case'].startswith('postbattle-completion/')};assert set(rootrows)=={x.parent.name for x in paths}
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
   if row['stage']==3:stage3+=1
   p0=r[0]|r[1]<<8;assert row['input_pointer00']==p0 and row['aligned_real_city_pointer00']==((p0-0x6000)//32 if 0x6000<=p0<0x63C0 and p0%32==0 else None)
   if row['registers']['pc']in(0xCC29,0xD4F0):middle+=1;assert row['owner_scope']=='Root_frozen_CC29_or_full_D4F0_only'
   else:assert row['stage']==3 and row['owner_scope']=='PostbattleCompletionServices'
   sp=row['registers']['sp'];assert row['existing_return_PC']==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535
   if row['immediate_transfer_PC']is None:assert row['registers']['pc']in(0xBBA0,0xD4F0)
   else:
    proof=row['immediate_transfer_proof'];assert proof is not None and proof['not_inferred_from_return_stack']and proof['callee_opcode_boundary']==event
    previous=proof['previous_watched_opcode_boundary'];assert previous==events[previous['sequence']]and previous['opcode_PC']==row['immediate_transfer_PC']and previous['sequence']<event['sequence']
    assert bytes.fromhex(proof['previous_ROM_bytes'])==self.rom[previous['rom_offset']:previous['rom_offset']+3]
   fixture=(path.parent/'input-n163.bin').read_bytes();assert len(fixture)==128 and digest(fixture)==row['explicit_N163_fixture']['sha256']and row['N163_address']==127 and row['N163_autoincrement']
  assert(controlled,natural,stage3,middle)==(17,17,30,8);self.counts.update(actual_passive_software_context_exports=34,unique_new_passive_software_inputs=34,Source_child_passive_inputs=26,Root_passive_inputs=34,actual_parent_ancestry_row_checks=34,production_new_Source_AST_syntax_checks=2)

 def static_fields(self):
  v=self.record(ROOT/'analysis/phase27/fields-static/verification.json');s=self.record(ROOT/'analysis/phase27/fields-static/analysis-summary.json');assert v['source_CPU_cases']==0 and v['failed_count']==0 and s['remaining_access_count']==328 and s['all_indirect_classification_counts']==dict(proved_disjoint_auxiliary_address_domain=1198,possible_city_auxiliary_alias=81,unresolved_pointer_or_index_contract=247)
  assert not(OUT/'fields-static').exists()and all(x is None for x in s['official_target_field_names'].values());self.counts.update(new_static_Source_CPU_cases=0,new_static_original_CPU_contract_cases=0,new_static_exclusions=0,inherited_static_remaining_candidates=328)

 def context(self):
  f=OUT/'context';v=self.record(f/'verification.json');s=self.record(f/'analysis-summary.json',False);self.record(f/'evidence.json');assert v['Source_CPU_cases']==v['original_CPU_cases']==v['Native_runs']==0 and v['check_count']==len(v['checks'])==58 and all(x['status']=='passed'for x in v['checks'])
  assert v['new_exclusions']==0
  self.counts.update(context_reference_checks=58,context_Source_CPU_cases=0,context_original_CPU_cases=0,context_Native_runs=0)

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
   assert row['acceptance_status']and row['verified_results']and row['pending_results']and row['phase29_change']['result']and row['phase29_change']['remaining_gap']
   for item in row['verified_results']:assert item['claim']and item['evidence']in row['evidence'];self.pin(item['evidence'])
  self.counts.update(acceptance_dimensions=10,acceptance_exact_user_message_locators=11,acceptance_reference_checks_not_gameplay=v['evidence_reference_checks'],acceptance_Source_syntax_checks_not_CPU=v['source_syntax_checks'],acceptance_Source_CPU_cases=0,acceptance_Native_frames=0)

 def browser(self):
  if not(OUT/'README.md').is_file():raise Pending('Missing Root final report')
  qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'README.md');self.pin(OUT/'index.html',qa['final_html_sha256']);assert qa['status']=='passed'and qa['failed_count']==0 and qa['check_count']==len(qa['checks'])and all(x['status']=='passed'for x in qa['checks'])
  assert qa['console_errors']==qa['console_warnings']==[]and qa['Native_frames_added']==qa['Source_CPU_cases_added']==0
  # Final formal portal schema is checked here before strict release.
  page=base.base.base.PortalPage();page.feed((OUT/'index.html').read_text());payload=json.loads(page.evidence)
  for name in('postbattle_completion_services.py','postbattle_completion_integration.py'):assert(ROOT/'source/recovered'/name).read_text()in page.sources
  assert len(page.sources)==2 and payload['native']==read(OUT/'runtime/evidence.json')['summary']and payload['acceptance']==read(OUT/'acceptance/requirements.json')
  for name,path in(('parent','completion-chain'),('fade','ownership-and-roster-contract'),('far','CC29-name-draw-context'),('credit','historical-credit')):assert payload[name]==read(OUT/'context'/(path+'.json'))
  for name,keys,path in(('source',('original_CPU_parent_cases','controlled_cases','passive_software_caller_cases','new_regression_groups','counts','source_guard_count'),'completion-services/validation.json'),('integration',('original_CPU_parent_cases','inherited_regression_cases','new_controlled_ECEE_regression_cases','new_completion_caller_cases','new_completion_ancestries','counts','comparison_counts','guard_count'),'source-integration.json')):
   full=read(OUT/path);assert payload[name]=={key:full[key]for key in keys}
  static=read(ROOT/'analysis/phase27/fields-static/analysis-summary.json');assert payload['frozen27_static']==dict(origin='analysis/phase27/fields-static/analysis-summary.json',all_indirect_positions=1526,counts=static['all_indirect_classification_counts'],remaining=328,phase29_new_exclusions=0,raw345=dict(total=345,operand=104,data=13,no_control_entry=228))
  assert [x['case']for x in payload['routes']]==list(CASES);point_count=event_count=0
  observations=read(OUT/'runtime/postbattle-observations.json');lifecycles=read(OUT/'runtime/palette-lifecycle-observations.json');completions=read(OUT/'runtime/completion-lifecycle-observations.json');native=read(OUT/'runtime/evidence.json')
  for route in payload['routes']:
   case=route['case'];folder=OUT/'runtime'/case;points=read(folder/'original-control/checkpoints.json');assert route['points']==points==read(folder/'observer/checkpoints.json')and route['base']=='runtime/'+case+'/'and route['ancestry']==native['case_ancestry'][case]
   life=next(x for x in lifecycles['routes']if x['case']==case);ob=next(x for x in observations['routes']if x['case']==case);assert route['lifecycle']==life
   selected={}
   def add(event,role):selected[event['sequence']]=dict(**event,display_role=role)
   for key,role in(('logical_G106_reads','inherited_resource_LDA'),('logical_G106_stores','inherited_resource_STA'),('STA_indirect_Y_dummy_bus_reads','resource_STA_dummy'),('following_other_city_gold_grain_writes','supply_return_store')):
    for event in ob[key]:add(event,role)
   for key in('D4F5_middle_entry','first_parent_far_entry','first_parent_far_after_callee','first_parent_far_before_RTS','first_parent_bridge_return'):add(life[key],'far_call_protocol')
   add(life['CC29_predecessor_entry'],'inherited_CC29_caller')
   for key in('ECEE_entry','ECEE_request_write','ECEE_before_immediate_RTS'):add(life[key],'ECEE_immediate_request_return')
   for key in('same_caller_resumed_BB96','phase2_BB99_before_supply','phase2_BB9C_after_supply','phase2_before_RTS'):add(life[key],'stage2_protocol')
   for event in life['phase2_Source_actual_software_entries']+life['phase2_to3_original_RMW_write_attempts']:add(event,'stage2_protocol')
   for hold in life['sub3_hold_records']:
    for key in('gate','BPL_branch','hold_return_before_RTS','fresh_parent_far_call'):add(hold[key],'fresh_sub3_callback')
   for key in('sub3_completion_gate','sub3_native_cleanup_entry'):add(life[key],'fresh_sub3_callback')
   for event in life['phase3_Source_unsupported_actual_inputs']:add(event,'fresh_sub3_callback')
   for event in life['fade_original_88_progression']+[life['fade_original_completion87_write']]:add(event,'NMI_fade_progress')
   for event in life['later_independent_palette_requests']:add(event,'later_new_fade_epoch')
   completion=next(x for x in completions['routes']if x['case']==case)
   for key,role in(('logical_city_reads','completion_city_read'),('leader_record_reads','completion_leader_read'),('adjacency_ROM_reads','completion_adjacency_ROM'),('city_stores','completion_city_store'),('STA_dummy_bus_reads','completion_STA_dummy'),('BC00_entries','bounded_roster_entry')):
    for event in completion[key]:add(event,role)
   add(completion['BBB8_entry'],'completion_entry');add(completion['parent_BBB7_before_RTS'],'completion_RTS')
   for event in completion['CC29_profile_ROM_reads'][:26]:add(event,'inherited_CC29_profile_sample')
   compact={key:value for key,value in completion.items()if key not in('all_selected_completion_events','CC29_profile_ROM_reads','pointer_and_scratch_writes')}
   compact['CC29_profile_sample_scope']='First26 of '+str(len(completion['CC29_profile_ROM_reads']))+' original namepacket reads; remaining records linked in the formal completion lifecycle JSON.';compact['CC29_profile_sample']=completion['CC29_profile_ROM_reads'][:26]
   assert route['completion']==compact and route['events']==[selected[k]for k in sorted(selected)]
   assert len(route['audio'])==2
   for variant,audio in zip(('original-control','observer'),route['audio']):
    path=OUT/audio['path'];assert path==folder/variant/'full-audio.wav';self.pin(path,audio['sha256'])
    with wave.open(str(path))as wav:assert(audio['sample_frames'],audio['duration_seconds'])==(wav.getnframes(),wav.getnframes()/48000)
   point_count+=len(points);event_count+=len(selected)
  assert(point_count,event_count)==(96,460)
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path in(OUT/'verification.json',OUT/'package-receipt.json'):continue
   assert path.is_file(),('Broken portal link',link)
  for name,pin in qa['artifact_and_dependency_sha256'].items():self.pin(name,pin)
  self.counts.update(browser_checks=qa['check_count'],browser_Source_modules=len(page.sources),browser_original_points=point_count,browser_original_fields_per_point=29,browser_original_selected_events=event_count)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA
 audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[];audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('context',audit.context),('acceptance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');audit.pin(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP and manifest['foundational_archive']['sha256']==V22_ZIP and manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase29']
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in base.base.base.prior.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots']);names=set(manifest['include_files']);included={k:v for k,v in audit.pins.items()if k in names or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase29-postbattle-parent-palette-readonly-audit-v1',status='pending_final_artifacts'if pending else'passed',ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v28_incremental_preserved_sha256=OLD_ZIP,old_phase28_audit_sha256=OLD_AUDIT,old_phase28_postZIP_receipt_sha256=OLD_POSTZIP,old_v22_preserved_sha256=V22_ZIP,source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guards',0),source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),limits=['Read-only evidence audit; no CPU/core/producers/analyzers/old audit main executed.','Natural skip and controlled-ancestry positive paths are separate;19 known ancestor bytes plus incomplete earlierlegacy preparation are explicit.','Separate29 observer alone supplies internal events, no instantaneous N163/PPU/APU.','ECEE starts async palette and immediately RTS; subsequent BBA0 is a fresh sign-only invocation, not a suspended wait. Native21frame completion depends on observed old8A4. Later city fade is separate.','Source cases/static CPU contracts/context/reference checks/Native frames never added together;wholeROM completionandstandalone source are unproven.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))
if __name__=='__main__':main()
