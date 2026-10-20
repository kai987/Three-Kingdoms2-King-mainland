#!/usr/bin/env python3
"""Read-only phase31 audit; only its new verification.json may be written.

No Native/core, CPU, producer main, analyzer, old audit main or generator runs.
Large logs are verified one 288-byte record and one JSONL line at a time.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,os,sys,wave
from urllib.parse import urlparse,unquote
from html.parser import HTMLParser
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase31';sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SPEC=importlib.util.spec_from_file_location('frozen30_readonly_helpers',ROOT/'scripts/verify_phase30.py');old=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=old;SPEC.loader.exec_module(old)
from capture_native_postbattle_disposition import decode_event,fields,compare_files_exact,observations,CORE_SHA,OBSERVER_SHA,RECORD_BYTES,FIVE
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA=old.ROM_SHA;read=old.read;original=old.original;DISJOINT=old.DISJOINT;Pending=old.Pending
OLD_AUDIT='6cabf530d87046ca0df8d13775b8180b793c92a4a51ed1ab2772533bfb00d4d5'
OLD_ZIP='de57684b382f7e02b333b1ac7f530fce08a8c7a6dc4fe2c36b46cd33d0fabaeb'
OLD_POSTZIP='b38c72749278a658e7fdbe7d22bedeebeac82807a66df75abc7bae364b0db266'
V22_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(path):return str(Path(path).resolve().relative_to(ROOT))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def event_objects(value):
 if isinstance(value,dict):
  if all(k in value for k in('sequence','kind','opcode_PC','actual_PRG_banks')):yield value
  else:
   for x in value.values():yield from event_objects(x)
 elif isinstance(value,list):
  for x in value:yield from event_objects(x)
class Portal31(HTMLParser):
 def __init__(self):super().__init__();self.sources=[];self.evidence='';self.links=[];self.ids=[];self.in_source=False;self.in_pre=False;self.in_data=False;self.current=''
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if'id'in a:self.ids.append(a['id'])
  if tag=='details'and a.get('class')=='source':self.in_source=True
  if tag=='pre'and self.in_source:self.in_pre=True;self.current=''
  if tag=='script'and a.get('id')=='evidence-data':self.in_data=True
  if tag=='a'and'href'in a:self.links.append(a['href'])
 def handle_data(self,value):
  if self.in_pre:self.current+=value
  if self.in_data:self.evidence+=value
 def handle_endtag(self,tag):
  if tag=='pre'and self.in_pre:self.sources.append(self.current);self.in_pre=False
  if tag=='details':self.in_source=False
  if tag=='script':self.in_data=False

class Audit(old.Audit):
 def pin(self,path,expected=None):
  p=Path(path);p=p if p.is_absolute()else ROOT/p;key=relative(p)
  assert not any(x.startswith('exploratory')or x=='__pycache__'for x in p.parts),key
  assert p.is_file()and not p.is_symlink(),('Missing required nonsymlink artifact',key)
  st=p.stat();identity=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
  if not hasattr(self,'inode_sha'):self.inode_sha={}
  if identity not in self.inode_sha:self.inode_sha[identity]=sha(p)
  actual=self.inode_sha[identity];assert expected is None or actual==expected,(key,'stale pin',expected,actual)
  assert key not in self.pins or self.pins[key]==actual;self.pins[key]=actual;return actual

 def frozen_history(self):
  self.pin('analysis/phase30/verification.json',OLD_AUDIT);v=read(ROOT/'analysis/phase30/verification.json')
  assert v['status']=='passed'and not v['pending']and v['ROM_sha256']==ROM_SHA and v['rebuilt_byte_identical']
  assert(len(v['source_and_validator_sha256']),len(v['artifact_and_dependency_sha256']))==(577,53960)
  self.frozen_names=set(v['source_and_validator_sha256'])|set(v['artifact_and_dependency_sha256'])
  for name,p in v['source_and_validator_sha256'].items():self.pin(name,p);self.sources[name]=p
  for name,p in v['artifact_and_dependency_sha256'].items():self.pin(name,p)
  self.pin('analysis/phase30/package-receipt.json',OLD_POSTZIP);p=read(ROOT/'analysis/phase30/package-receipt.json')
  assert p['status']=='passed'and p['phase30_audit_sha256']==OLD_AUDIT and p['sha256']==OLD_ZIP and p['file_count']==2381
  self.pin('build/三国志2超级版-逆向分析-v30增量.zip',OLD_ZIP);self.pin('build/三国志2超级版-逆向分析.zip',V22_ZIP)
  assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==self.rom
  self.counts.update(unchanged_phase30_source_script_pins=577,unchanged_phase30_artifact_dependency_pins=53960,unchanged_phase30_postZIP_receipts=1)

 def ancestry31(self,c,a):
  def pins(x):
   if isinstance(x,dict):
    if all(k in x for k in('path','sha256')):
     path=Path(x['path'])
     if not path.is_absolute()and not(ROOT/path).is_file()and a.get('historical_preparation_base'):path=ROOT/a['historical_preparation_base']/path
     self.pin(path,x['sha256'])
    for v in x.values():pins(v)
   elif isinstance(x,list):
    for v in x:pins(v)
  pins(a);self.record_pins(a);assert a['additional_core_memory_writes']==0 and a['additional_preparation']==[]and a['new_case_state_imported']and not a['new_case_cold_boot']
  assert a['mother']['sha256']==c['mother_sha256']==self.pin(c['mother'])
  assert a['natural_ordinary_input_route']==c['natural']and a['controlled_ancestry']==(not c['natural'])
  if c.get('ancestry_case'):return old.Audit.ancestry30(self,c,a)
  if c['natural']:assert a['known_inherited_preparation_byte_writes']==0 and a['known_inherited_preparation']==[]
  else:assert a['known_inherited_preparation_byte_writes']==len(a['known_inherited_preparation'])==19
  if c.get('ancestry_path'):
   original_ancestry=read(ROOT/c['ancestry_path']);assert set(a)==set(original_ancestry)|{'parent_checkpoint'}and all(a[k]==value for k,value in original_ancestry.items())
   assert a['parent_checkpoint']in read(ROOT/a['parent_checkpoints']['path'])and a['parent_checkpoint']['frame']==c['parent_frame']
   if a.get('schema')=='phase31-natural-AI-ordinary-segmented-ancestry-v1':self.segmented_ancestry(c,a)
  else:
   p=read(ROOT/a['parent_validation']['path']);assert p['cold_boot']and not p['state_imported']and p['additional_core_memory_writes']==0
   assert a['parent_checkpoint']in read(ROOT/a['parent_checkpoints']['path'])and a['parent_checkpoint']['frame']==c['parent_frame']

 def segmented_ancestry(self,c,a):
  if getattr(self,'checked_segmented_ancestry',False):return
  def clip(plan,start,end):
   result=[]
   for i,s in enumerate(plan):
    lo=max(start,s['start_frame']);hi=min(end,s['start_frame']+s['frames'])
    if hi>lo:result.append(dict(s,start_frame=lo-start,frames=hi-lo,original_step=i,original_start_frame=s['start_frame']))
   cursor=0
   for step in result:assert step['start_frame']==cursor and set(step['buttons'])<=set(('a','b','start','select','up','down','left','right'));cursor+=step['frames']
   assert cursor==end-start;return result
  assert len(a['segments'])==a['upstream_original_core_runs']==10 and not a['upstream_fresh_repeat_claim']and not a['upstream_internal_CPU_trace']
  parent=self.record(ROOT/a['root_frozen_ancestor']['path']);assert parent['additional_core_memory_writes']==0 and parent['preparation']==[]and parent['state_imported']and not parent['cold_boot']
  previous=ROOT/'analysis/phase22/runtime/original-control/final.state';total=0
  for i,segment in enumerate(a['segments'],1):
   assert segment['index']==i and segment['state_import_at_start']and segment['new_preparation']==[]and segment['additional_core_memory_writes']==0
   first=ROOT/segment['initial_state']['path'];last=ROOT/segment['final_state']['path'];compare_files_exact(first,previous)
   receipt=read(ROOT/segment['original_result']['path']);assert receipt['mother']['sha256']==self.pin(first)and receipt['ROM_sha256']==ROM_SHA and receipt['core_sha256']==CORE_SHA and receipt['additional_core_memory_writes']==0 and receipt.get('new_preparation',[])==[]and receipt['frames']>=segment['frames']
   folder=last.parent;fullplan=read(folder/'original-input-plan.json');used=read(ROOT/segment['input_plan']['path']);assert used==clip(fullplan,0,segment['frames'])
   logs=read(ROOT/segment['complete_frame_hash_log']['path']);assert len(logs)==segment['frames']and [x['frame']for x in logs]==list(range(1,len(logs)+1))
   for row in logs:
    for key in('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256'):assert len(row[key])==64 and all(ch in'0123456789abcdef'for ch in row[key])
    assert len(row.get('whole_serialized_state_sha256',row.get('state_sha256','')))==64
   ctx=NestopiaContext.parse(last.read_bytes());r=(ROOT/segment['final_RAM']['path']).read_bytes();s=(ROOT/segment['final_SRAM']['path']).read_bytes();tail=logs[-1]
   assert(ctx.ram,ctx.sram,ctx.registers,list(ctx.prg_banks))==(r,s,segment['observed_final_CPU_registers'],segment['observed_final_PRG_banks'])
   assert digest(r)==tail['RAM_sha256']and digest(s)==tail['SRAM_sha256']and self.pin(last)==tail.get('whole_serialized_state_sha256',tail.get('state_sha256'))
   assert tail.get('actual_saved_CPU_registers',tail.get('registers'))==ctx.registers and tail.get('actual_saved_PRG_banks',tail.get('banks'))==list(ctx.prg_banks)
   previous=last;total+=segment['frames']
  assert total==a['segmented_upstream_frames']==141636 and a['segments'][-1]['frames']==c['parent_frame']==1211
  compare_files_exact(previous,ROOT/c['mother']);ctx=NestopiaContext.parse((ROOT/c['mother']).read_bytes());assert ctx.ram[0x514]==131 and list(ctx.ram[0x500:0x502])==[11,0]
  home=(ROOT/c['ancestry_path']).parent;supplement=self.record(home/'ancestry-proof-inputs.json',False)
  assert supplement['execution']==dict(CPU=0,Source=0,Native=0)and not supplement['changes_to_used_ancestry_case_spec_producer_or_core'];self.pin(supplement['copied_original_plan']['path'],supplement['copied_original_plan']['sha256']);self.pin(supplement['formal_plan']['path'],supplement['formal_plan']['sha256'])
  duel=read(home/'segment-10/original-input-plan.json');post=read(ROOT/supplement['copied_original_plan']['path']);head=clip(duel,1211,1528);tail=clip(post,0,240)
  for step in tail:step['start_frame']+=317
  assert read(ROOT/c['plan_source'])==head+tail and c['frames']==557 and c['plan_start']==0 and c['plan_end']==557
  self.checked_segmented_ancestry=True;self.counts.update(upstream_single_original_segments=10,upstream_single_original_frames=141636,upstream_fresh_repeat_claim=False,formal_AI_duel_prefix_frames=317,formal_AI_postbattle_tail_frames=240,context_lineage_checks_are_not_Native_runs=True)

 def runtime(self):
  folder=OUT/'runtime';e=self.record(folder/'evidence.json');v=self.record(folder/'validation.json')
  assert e['summary']=={k:v[k]for k in e['summary']};self.pin(folder/'evidence.json',v['evidence_sha256']);self.pin('scripts/capture_native_postbattle_disposition.py',v['script_sha256'])
  self.pin(v['storage_deduplication']['path'],v['storage_deduplication']['sha256'])
  assert v['failed_count']==v['Source_CPU_cases']==v['additional_core_memory_writes']==v['cold_boots']==0
  assert all(v[k]for k in('all_five_complete_buffers_equal_each_frame','initial_API_complete_buffers_equal','all_artifacts_repeat_exact','full_serialized_buffers_not_normalized'))
  assert v['fresh_process_runs']==v['state_imports']==4*len(e['routes'])and v['all_control_frames']==4*v['first_original_frames']
  assert{r['case']:r['frames']for r in e['routes']}=={'natural13-continuous':1551,'controlled14-direct':32,'all-AI-Start-bypass':64,'natural-AI-mode2':557}
  expected=dict(routes=4,natural_routes=3,controlled_ancestry_routes=1,fresh_process_runs=16,first_original_frames=2204,all_control_frames=8816,nonempty_repeat_checks=18639,PNG_checks=4408,WAV_checks=8,observer_events=1376552,software_snapshots=297)
  assert all(v[k]==x for k,x in expected.items())
  self.native_events={};self.native_routes={x['case']:x for x in e['routes']};self.native_configs={};checks=images=wavs=frames=0;storage_files={}
  for route in e['routes']:
   case=route['case'];home=folder/case;c=self.record(home/'original-control/case-spec.json',False);self.native_configs[case]=c;self.ancestry31(c,route['ancestry']);m=NestopiaContext.parse((ROOT/c['mother']).read_bytes());original_rows=None
   for variant,core in(('original-control',CORE_SHA),('observer',OBSERVER_SHA)):
    first=home/variant;second=OUT/'runtime-repeat'/case/variant;a=self.record(first/'validation.json');b=self.record(second/'validation.json');rv=self.record(first/'repeat-validation.json')
    assert a==b and a['core']['core_sha256']==core and a['frames']==a['checkpoint_count']==c['frames']
    assert a['execution_owner']=='Root_only'and a['additional_core_memory_writes']==a['Source_CPU_cases']==0 and a['state_imported']and not a['cold_boot']and not a['original_core_internal_CPU_trace']
    assert a['ancestry']==route['ancestry']==self.record(first/'preparation.json',False);self.ancestry31(c,a['ancestry'])
    assert rv['all_bytes_exact']and rv['artifact_checks']==len(a['artifact_sha256'])
    for name,p in a['artifact_sha256'].items():
     assert p['bytes']>0 and compare_files_exact(first/name,second/name)==p
     for path in(first/name,second/name):assert path.stat().st_size==p['bytes'];self.pin(path,p['sha256'])
     for path in(first/name,second/name):storage_files[relative(path)]=path.stat()
     checks+=1
    initial=NestopiaContext.parse((first/'initial.state').read_bytes());assert(initial.ram,initial.sram,initial.registers,initial.prg_banks)==(m.ram,m.sram,m.registers,m.prg_banks)
    rows=read(first/'frame-services.json');points=read(first/'checkpoints.json');calls=read(first/'audio-callbacks.json');plan=read(first/'input-plan.json');assert len(rows)==len(points)==len(calls)==c['frames']and sum(x['frames']for x in plan)==c['frames']
    if c.get('plan_source'):
     source=read(ROOT/c['plan_source']);expected=[]
     for j,step in enumerate(source):
      lo=max(c['plan_start'],step['start_frame']);hi=min(c['plan_end'],step['start_frame']+step['frames'])
      if hi>lo:expected.append(dict(start_frame=lo-c['plan_start'],frames=hi-lo,buttons=step['buttons'],parent_step=j,parent_start_frame=step['start_frame']))
    else:expected=c.get('direct_plan',[dict(start_frame=0,frames=c['frames'],buttons=[])])
    assert plan==expected;cursor=0
    for step in plan:assert step['start_frame']==cursor and set(step['buttons'])<=set(('a','b','start','select','up','down','left','right'));cursor+=step['frames']
    assert cursor==c['frames']
    if original_rows is None:original_rows=rows;frames+=len(rows)
    assert rows==original_rows
    with wave.open(str(first/'full-audio.wav'))as audio:
     assert(audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
     for i,(row,point,cb)in enumerate(zip(rows,points,calls),1):
      assert row['frame']==point['frame']==cb['emulated_frame_start']+1==i and row['parent_route_frame']==c['parent_frame']+i
      pcm=audio.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']and audio.tell()*4==row['PCM_stop_byte']
      r=(first/point['RAM']).read_bytes();s=(first/point['SRAM']).read_bytes();state=(first/point['state']).read_bytes();ctx=NestopiaContext.parse(state)
      assert(ctx.ram,ctx.sram,ctx.registers,list(ctx.prg_banks))==(r,s,row['actual_saved_CPU_registers'],row['actual_saved_PRG_banks'])and all(row[k]==x for k,x in fields(r,s).items())and all(row[k]==x for k,x in point['fields'].items())
      assert digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']
      for key in('RAM','SRAM','state','image'):compare_files_exact(first/point[key],home/'original-control'/point[key])
      with Image.open(first/point['image'])as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
      images+=1
     assert not audio.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and audio.tell()*4==a['full_audio']['PCM_bytes'];wavs+=1
    for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):compare_files_exact(first/name,home/'original-control'/name)
    storage=self.record(second/'storage-deduplication.json');assert storage['status']=='passed'and not storage['byte_normalization']
    for p in storage['checks']:
     assert p['complete_byte_comparison_passed']and p['storage_only'];anchor,target=ROOT/p['anchor'],ROOT/p['target'];assert os.path.samefile(anchor,target)and compare_files_exact(anchor,target)=={k:p[k]for k in('bytes','sha256')}
   self.observer31(home/'observer',case)
  assert(checks,images,wavs,frames)==tuple(v[k]for k in('nonempty_repeat_checks','PNG_checks','WAV_checks','first_original_frames'))
  assert sum(r['observer_events']for r in e['routes'])==v['observer_events']and sum(r['software_snapshots']for r in e['routes'])==v['software_snapshots']
  storage=self.record(folder/'storage-deduplication.json');inodes={(s.st_dev,s.st_ino):s.st_size for s in storage_files.values()};logical=sum(s.st_size for s in storage_files.values());unique=sum(inodes.values())
  assert(storage['captured_file_paths'],storage['logical_path_bytes'],storage['unique_inode_count'],storage['unique_inode_logical_bytes'],storage['logical_duplicate_bytes'])==(len(storage_files),logical,len(inodes),unique,logical-unique)
  assert storage['all_paths_preserved']and not storage['serialized_buffers_normalized']and not storage['old_phase_files_modified']
  self.core_provenance();media=self.record(folder/'media-static-validation.json');assert media['Native_frames_added']==media['CPU_cases_added']==media['Source_cases_added']==0 and(media['PNG_checks'],media['WAV_checks'])==(images,wavs)
  self.counts.update({f'Native_{k}':v[k]for k in('fresh_process_runs','first_original_frames','all_control_frames','nonempty_repeat_checks','PNG_checks','WAV_checks','observer_events','software_snapshots')})

 def observer31(self,folder,case):
  schema=self.record(folder/'event-schema.json',False);assert schema['words']==len(schema['raw_layout'])==72 and schema['bytes_per_record']==RECORD_BYTES==288
  ob=self.record(folder.parent/'observations.json',False);assert ob==observations(folder)
  wanted={e['sequence']for e in event_objects(ob)};index={x['event_sequence']:x for x in map(json.loads,(folder/'snapshot-index.jsonl').read_text().splitlines())};selected={};previous=None;count=snaps=0
  with(folder/'bus-events.bin').open('rb')as raw,(folder/'events.jsonl').open()as decoded,(folder/'snapshots.bin').open('rb')as snapshots:
   for count,line in enumerate(decoded,1):
    event=json.loads(line);block=raw.read(RECORD_BYTES);assert len(block)==RECORD_BYTES and decode_event(block,sequence=count)==event;e=event
    if e['opcode_PC']is not None and e['opcode_PC']>=0x8000:assert e['physical_bank']==e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]and e['rom_offset']==original(e['physical_bank'],e['opcode_PC'])
    if e['data_ROM_offset']is not None:assert self.rom[e['data_ROM_offset']]==e['value']and e['data_physical_bank']==e['actual_PRG_banks'][(e['address']-0x8000)//8192]
    if e['sequence']in wanted:selected[e['sequence']]=e
    if e['full_snapshot_sequence']:
     snaps+=1;item=index[e['sequence']];payload=snapshots.read(10240);r,s=payload[:2048],payload[2048:];assert len(payload)==10240 and e['full_snapshot_sequence']==item['snapshot_sequence']==snaps
     assert item['event_sequence']==e['sequence']and item['frame']==e['frame']and item['byte_offset']==(snaps-1)*10240 and item['bytes']==10240
     assert digest(payload)==item['sha256']and digest(r)==item['RAM_sha256']and digest(s)==item['SRAM_sha256']and list(r[:48])==e['ZP_0000_002F']
     assert item['actual_registers']==dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC'])and item['actual_PRG_banks']==e['actual_PRG_banks']
     assert item['capture_core_sha256']==OBSERVER_SHA and not item['instantaneous_N163_PPU_APU_captured']and item['additional_core_memory_writes']==0
     c=self.native_configs[case];assert item['mother']['path']==c['mother']and item['mother']['sha256']==c['mother_sha256']and item['known_inherited_preparation_byte_writes']==(0 if c['natural']else 19)
     assert item['actual_battle_state']==list(r[0x500:0x502])and item['actual_outcome']==r[0x514]and item['actual_side_0504']==r[0x504]and item['actual_mode_6F91']==s[0xF91]and item['actual_050B']==r[0x50B]and item['actual_UI_0540_0547']==list(r[0x540:0x548])
     assert list(r[0x81:0x87])==e['buttons_0081_0086']and r[0x504]==e['side_0504']and r[0x50B]==e['raw_050B']and list(r[0x540:0x548])==e['UI_0540_0547']
     assert(folder/item['exported_RAM']).read_bytes()==r and(folder/item['exported_SRAM']).read_bytes()==s
     sp=e['SP'];assert(r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)==e['stack_top_word_raw']&65535
     selected[e['sequence']]=e
     if previous:selected[previous['sequence']]=previous
    if e['kind']=='opcode_boundary':previous=e
   assert not raw.read(1)and not snapshots.read(1)and count==ob['event_count']and snaps==ob['full_software_snapshots']==len(index)
  assert all(e==selected[e['sequence']]for e in event_objects(ob));self.native_events[case]=selected
  for c in ob['actual_BC46_calls']:
   e=c['entry'];p=c['actual_previous_watched_opcode']
   if c['actual_transfer_PC']is not None:
    assert p['physical_bank']==e['physical_bank']==8 and p['opcode_PC']in(0xBB36,0xBB8C)and p['SP']==e['SP']+2 and e['stack_top_word_raw']&65535==p['opcode_PC']+2
    assert self.rom[p['rom_offset']:p['rom_offset']+3]==bytes.fromhex('2046BC')and c['derived_expected_return_PC']==p['opcode_PC']+3
   if c.get('return_PC_and_SP_observed'):
    ret=c['observed_return_boundary'];assert ret['opcode_PC']==c['real_return_PC']==c['derived_expected_return_PC']and ret['SP']==p['SP']and ret['sequence']>e['sequence']
  for e in ob['commander_outcome_producer_writes']:assert e['commander_outcome_producer']and e['physical_bank']==13 and e['opcode_PC']in(0xDD82,0xDD9E)and self.rom[e['rom_offset']:e['rom_offset']+3]==bytes.fromhex('8D1405')
  if case=='natural13-continuous':assert{e['RAM0500_0503'][1]for e in ob['human_entries']if e['RAM0500_0503'][0]==13}==set(range(7))
  if case=='controlled14-direct':assert{tuple(e['RAM0500_0503'][:2])for e in ob['human_entries']}=={(14,0)}
  if case=='all-AI-Start-bypass':
   assert len(ob['title_Start_bypass'])==1 and not ob['ruler_controller_writes']and not ob['actual_BC46_calls']
   rows=read(folder/'frame-services.json');assert all(x['all7_ruler_controllers']==[3]*7 for x in rows)and(rows[-1]['global_007A'],rows[-1]['NMI_0078'])==(2,2)
  if case=='natural-AI-mode2':
   assert len(ob['commander_outcome_producer_writes'])==1;writer=ob['commander_outcome_producer_writes'][0];assert(writer['frame'],writer['opcode_PC'],writer['storage_byte_before_write'],writer['value'])==(4,0xDD9E,131,1)
   assert len(ob['actual_BC46_calls'])==1;call=ob['actual_BC46_calls'][0];assert(call['actual_transfer_PC'],call['mode'],call['real_return_PC'],call['entry']['frame'])==(0xBB36,2,0xBB39,502)and call['return_PC_and_SP_observed']
   assert call['entry']['battle_0506_0507_050E_0514'][1:]==[0x32,11,1]and call['entry']['side_0504']==128
   controller=[e for e in ob['controller_byte_reads']if e['physical_bank']==8 and e['opcode_PC']==0xBAEF];assert len(controller)==1 and(controller[0]['address'],controller[0]['value'])==(0x6F22,3)
   modewrite=[e for e in ob['postbattle_SRAM_writes']if e['address']==0x6F91];assert len(modewrite)==1 and(modewrite[0]['opcode_PC'],modewrite[0]['storage_byte_before_write'],modewrite[0]['value'])==(0xBB2B,10,2)
   assert writer['sequence']<controller[0]['sequence']<modewrite[0]['sequence']<call['actual_previous_watched_opcode']['sequence']<call['entry']['sequence']
   assert any(e['physical_bank']==8 and e['opcode_PC']==0xBD67 and e['frame']==502 for e in ob['mode_targets'])
   begin,end=call['entry']['sequence'],call['observed_return_boundary']['sequence'];stores=[e for e in ob['postbattle_SRAM_writes']if begin<e['sequence']<end]
   assert len(stores)==21 and all(e['opcode_PC']==0xBE4C and 0x6FA1<=e['address']<=0x6FB5 and e['storage_byte_before_write']==e['physical_storage_byte_after_event']==255 for e in stores)
   assert not any(e['address']<0x63C0 or e['opcode_PC']==0xBDB8 for e in stores)
   self.counts.update(Native_new_commander_outcome_writes=1,Native_actual_BB36_mode2_call_return=1,Native_mode2_same_value_temporary_buffer_writes=21,Native_mode2_city_or_BDB8_writes=0)

 def core_provenance(self):
  folder=OUT/'runtime/core-provenance';v=self.record(folder/'build.json',False);assert v['commit']=='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
  assert v['first_build_clean_new_tree']and v['final_source_clean_build']and v['dependency_rebuild_byte_identical']and not v['modified_emulator_object_layout']and v['extra_emulated_bus_reads']==v['extra_emulated_bus_writes']==0
  for p in[v['original_core'],v['passive_observer'],v['parent_frozen_patch']]+v['unchanged_old_observers']:self.pin(p['path'],p['sha256'])
  assert v['original_core']['sha256']==CORE_SHA and v['passive_observer']['sha256']==OBSERVER_SHA
  patch=(folder/'observer.patch').read_bytes();assert digest(patch)==v['patch_sha256'];originals={x['path']:(folder/'upstream'/x['path']).read_bytes()for x in v['source_files']};generated=old.base.base.base.prior.apply_patch_readonly(patch,originals)
  for x in v['source_files']:assert digest(originals[x['path']])==x['original_sha256']and digest(generated[x['path']])==x['patched_sha256']
  for p in(folder/'patched').rglob('*'):
   if p.is_file():assert p.read_bytes()==generated[str(p.relative_to(folder/'patched'))]
  watch=generated['source/core/NstWatch.cpp.inc'].decode();board=generated['source/core/board/NstBoard.cpp'].decode();make=generated['libretro/Makefile'].decode()
  assert 'map.Peek'not in watch and 'map.Poke'not in watch and 'out[i]=b.wrk[0][i]'in board and '++watch_overflow'in watch and '++watch_snapshot_overflow'in watch and v['include_dependency_declared']in make
  assert generated['source/core/NstCpu.hpp']==originals['source/core/NstCpu.hpp'];self.counts['observer_upstream_source_files_patch_reconstructed_readonly']=len(originals)

 def source_cases(self):
  f=OUT/'player-disposition';v=self.record(f/'validation.json');self.record(f/'evidence.json');catalog=self.record(f/'static-catalog.json',False)
  if v['quick']:raise Pending('Source still quick')
  assert v['new_production_source_modules']==0 and not v['new_gameplay_algorithm_claim']and v['original_CPU_parent_cases']==len(v['cases'])==325
  assert v['counts']==dict(actual_caller_RTS=317,strict_dependency_prefix=8)==Counter(x['comparison']for x in v['cases'])
  assert v['failed_count']==0 and v['failures']==[]and v['source_guard_count']==len(v['guards'])==0 and v['source_original_CPU_callbacks']==0 and not v['production_IR_interpretation']and not v['Native_internal_CPU_trace']
  assert all(x['all2048_RAM_8192_SRAM_AXYP_SP_PC_four_banks_combined_IO_common_N163_equal']and x['source_original_CPU_callbacks']==0 for x in v['cases'])
  groups=Counter(x['case'].split('/')[0]for x in v['cases']);assert groups['passive31']==117 and groups['inherited30-passive']==14 and groups['inherited30-controlled-BB36-parent']==2 and len(v['cases'])-117-14-2==192
  assert catalog['new_production_source_modules']==0 and not catalog['new_gameplay_first_recovery']and len(catalog['states'])==14 and len(catalog['tables'])==2 and len(catalog['state_handler_node_union'])==415
  assert{(x['state'],x['phase'])for x in catalog['states']}=={(state,phase)for state in(13,14)for phase in range(7)}
  self.actual_contexts31(v)
  self.counts.update(source_child_CPU_cases=325,new_Source_CPU_cases=325,new_Source_guards=0,new_Source_actual_caller_RTS=317,new_Source_nonlocal_return=0,new_Source_strict_dependency_prefix=8,Source_new_controlled_cases=192,Source_inherited_controlled_BB36_cases=2,Source_inherited_passive_cases=14,Source_new_passive_cases=117,new_production_source_modules=0,new_gameplay_first_recovery=False)

 def actual_contexts31(self,validation):
  evidence=self.record(OUT/'cpu-disposition/evidence.json');paths=sorted((OUT/'cpu-disposition/actual-callers').glob('*/context.json'))
  assert evidence['source_CPU_cases']==evidence['original_CPU_prefix_instructions']==0 and not evidence['instant_N163_captured']and evidence['exported_caller_inputs']==len(paths)==117
  source_rows={x['case'].split('/',1)[1]:x for x in validation['cases']if x['case'].startswith('passive31/')};assert set(source_rows)=={p.parent.name for p in paths}
  ancestors=Counter();targets=Counter();kinds=Counter()
  for path in paths:
   row=self.record(path,False);assert row['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and row['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   assert row['prepared_numeric_bytes']==row['additional_CPU_prepared_numeric_bytes']==[]and row['injected_new_NMI']==row['injected_new_IRQ']==0 and not row['synthetic_caller_PC_or_stack']and not row['unmodified_core_internal_trace']
   capture=row['passive_capture'];self.pin(capture['metadata'],capture['metadata_sha256']);meta=read(ROOT/capture['metadata']);self.pin(capture['manifest'],capture['manifest_sha256']);self.pin(capture['events_path'],capture['events_sha256']);self.pin(capture['preparation_path'],capture['preparation_sha256'])
   r=(ROOT/capture['RAM_path']).read_bytes();s=(ROOT/capture['SRAM_path']).read_bytes();self.pin(capture['RAM_path'],capture['RAM_sha256']);self.pin(capture['SRAM_path'],capture['SRAM_sha256'])
   assert r==(path.parent/'input-ram.bin').read_bytes()and s==(path.parent/'input-sram.bin').read_bytes()and row['registers']==meta['actual_registers']and row['physical_banks']==meta['actual_PRG_banks']and row['actual_software_state_captured']
   case=next(name for name in self.native_routes if'/'+name+'/'in capture['metadata']);ancestor=self.native_routes[case]['ancestry'];assert row['ancestry_provenance']==ancestor and row['inherited_Native_preparation']==ancestor['known_inherited_preparation']and row['known_inherited_preparation_byte_writes']==ancestor['known_inherited_preparation_byte_writes']
   assert row['controlled_ancestry']==self.native_routes[case]['controlled_ancestry']and row['natural_ordinary_input_route']==self.native_routes[case]['natural_ordinary_input_route']
   ancestors['controlled_ancestry'if row['controlled_ancestry']else'natural_ancestry']+=1
   if row['controlled_ancestry']:assert len(row['inherited_Native_preparation'])==19
   else:assert row['inherited_Native_preparation']==[]
   event=self.native_events[case][capture['event_sequence']];assert event['full_snapshot_sequence']==meta['snapshot_sequence']==capture['snapshot_sequence']and event['frame']==meta['frame']==capture['frame']and event['opcode_PC']==row['registers']['pc']and event['actual_PRG_banks']==row['physical_banks']
   assert meta['capture_core_sha256']==OBSERVER_SHA and not meta['instantaneous_N163_PPU_APU_captured']and source_rows[path.parent.name]['metadata']==row and source_rows[path.parent.name]['initial_registers']==row['registers']
   sp=row['registers']['sp'];assert row['existing_return_PC']==((r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8)+1)&65535
   proof=row['immediate_transfer_proof'];kinds[row['actual_call_kind']]+=1;targets[f'{row["registers"]["pc"]:04X}']+=1
   assert proof['not_inferred_from_return_stack']and proof['callee_opcode_boundary']==event
   previous=proof['previous_watched_opcode_boundary'];assert previous==self.native_events[case][previous['sequence']]and previous['sequence']<event['sequence']
   assert bytes.fromhex(proof['previous_ROM_bytes'])==self.rom[previous['rom_offset']:previous['rom_offset']+3]
   if row['immediate_transfer_PC']is None:assert row['actual_call_kind']=='unknown'
   else:assert previous['opcode_PC']==row['immediate_transfer_PC']
   fixture=(path.parent/'input-n163.bin').read_bytes();assert fixture==bytes((11+37*i)&255 for i in range(128))and digest(fixture)==row['explicit_N163_fixture']['sha256']and row['N163_address']==127 and row['N163_autoincrement']
  assert ancestors==evidence['ancestries']==dict(controlled_ancestry=30,natural_ancestry=87)and targets==evidence['targets']
  self.counts.update(unique_new_passive_software_inputs=117,actual_context_natural_ancestry=87,actual_context_controlled_ancestry=30,actual_contexts_not_instantaneous_N163=True,actual_unknown_transfer_PC_retained=kinds['unknown'])
 def static_fields(self):
  f=OUT/'fields-static';v=self.record(f/'verification.json');s=self.record(f/'analysis-summary.json');self.record(f/'evidence.json')
  assert v['source_CPU_cases']==v['Native_runs']==v['failed_count']==0
  assert(v['original_contract_CPU_cases'],v['actual_caller_RTS_CPU_cases'],v['explicit_prefix_CPU_cases'],v['model_guard_check_count'])==(13998,13992,6,29)
  assert len(v['model_checks'])==29 and all(x['passed']for x in v['model_checks'])
  expected=dict(proved_disjoint_auxiliary_address_domain=1201,possible_city_auxiliary_alias=80,unresolved_pointer_or_index_contract=245)
  assert s['all_indirect_classification_counts']==v['all_indirect_classification_counts']==expected and s['previous_candidate_count']==326 and s['remaining_access_count']==v['remaining_access_count']==325 and s['newly_proved_disjoint_all_count']==1
  assert not s['whole_game_closure_proven']and not s['complete_analysis_fixed_point_proven']and all(x is None for x in s['official_city_auxiliary_names'].values())
  before=read(ROOT/'analysis/phase30/fields-static/all-indirect-accesses.json');after=self.record(f/'all-indirect-accesses.json',False);selected=self.record(f/'selected-accesses.json',False);contract=self.record(f/'roster-write-lifecycle-contract.json',False)
  oldrows={(x['physical_bank'],x['cpu']):x for x in before['accesses']};newrows={(x['physical_bank'],x['cpu']):x for x in after['accesses']};assert set(oldrows)==set(newrows)and len(newrows)==1526
  assert len(selected['accesses'])==1 and(selected['accesses'][0]['physical_bank'],selected['accesses'][0]['cpu'])==(8,0xBDB8)
  unchanged=0;aux={0x6000+32*c+y for c in range(30)for y in(1,28,29,30,31)}
  for key,row in newrows.items():
   self.raw(row);previous=oldrows[key]
   if key!=(8,0xBDB8):
    for field in('classification','address_contract','raw_hex','rom_offset','Y_values','whole_pointer_values'):assert row.get(field)==previous.get(field),(key,field)
    unchanged+=1
   else:
    proof=row['address_contract'];assert previous['classification']=='possible_city_auxiliary_alias'and row['classification']==DISJOINT and proof['logical_effective_address_only']
    assert 'Conditional complete BC46'in proof['authority']and proof['Y_values']==list(range(17,27))and proof['whole_pointer_values']==[0x6000+32*x for x in range(256)]
    assert not{(p+y)&65535 for p in proof['whole_pointer_values']for y in proof['Y_values']}&aux and proof['auxiliary_address_intersection_count']==0
  assert unchanged==1525 and Counter(x['classification']for x in newrows.values())==expected
  compare_files_exact(f/'raw345-executability-ledger.json',ROOT/'analysis/phase30/fields-static/raw345-executability-ledger.json')
  assert contract['source_CPU_cases']==contract['Native_runs']==0 and contract['root_entry']==dict(physical_bank=8,cpu=0xBC46)and contract['selected_targets']==[dict(physical_bank=8,cpu=0xBDB8)]
  for row in contract['original_instructions']+contract['F2AF_complete_instructions']:self.raw(row)
  self.counts.update(new_static_Source_CPU_cases=0,new_static_Native_runs=0,new_static_original_CPU_contract_cases=13998,new_static_contract_RTS=13992,new_static_contract_prefixes=6,new_static_model_premise_checks=29,new_static_exclusions=1,current_static_remaining_candidates=325,unchanged1525_static_contract_classifications=unchanged,raw345_bytes_unchanged=True)

 def context(self):
  # No invented context execution domain: checks here are read-only projections.
  paths=('source/recovered/battle_scene_controller.py','source/recovered/postbattle_release_services.py','source/recovered/postbattle_early_services.py','source/recovered/postbattle_early_integration.py')
  for name in paths:self.pin(name);ast.parse((ROOT/name).read_text())
  producer=ast.parse((ROOT/'scripts/capture_native_postbattle_disposition.py').read_text());calls=[x for x in ast.walk(producer)if isinstance(x,ast.Call)]
  assert not any(isinstance(x.func,ast.Attribute)and x.func.attr in('poke','write_memory','set_memory')for x in calls)
  assert 'Only Root is authorized to execute Native flows'in(ROOT/'scripts/capture_native_postbattle_disposition.py').read_text()
  dummy=logical=unknown=0
  for case in self.native_routes:
   ob=read(OUT/'runtime'/case/'observations.json')
   for e in ob['auxiliary_bus_events']:
    raw=self.rom[e['rom_offset']:e['rom_offset']+2];op=raw[0];zp=raw[1];memory=e['ZP_0000_002F']
    if op in(0x91,0xB1)and zp+1<len(memory):
     pointer=memory[zp]|memory[(zp+1)&255]<<8;effective=(pointer+e['Y'])&65535;bus=(pointer&0xFF00)|((pointer+e['Y'])&255)
     if e['kind']=='read'and e['address']==bus and e['address']!=effective and(op==0x91 or(pointer&0xFF00)!=(effective&0xFF00)):
      dummy+=1
     elif e['address']==effective:logical+=1
     else:unknown+=1
    else:unknown+=1
  self.counts.update(new_readonly_context_AST_checks=len(paths)+1,context_Source_CPU_cases=0,context_original_CPU_cases=0,context_Native_runs=0,Native_auxiliary_dummy_bus_events=dummy,Native_auxiliary_logical_events=logical,Native_auxiliary_unclassified_events=unknown)

 def acceptance(self):
  f=OUT/'acceptance';v=self.record(f/'verification.json');r=self.record(f/'requirements.json',False);p=self.record(f/'request-provenance.json',False)
  assert v['source_CPU_cases']==v['original_CPU_cases']==v['Native_frames']==0 and not r['overall_reverse_engineering_complete']and r['completion_percentage']is None and v['direct_user_message_locator_checks']==11 and v['dimensions']==10 and v['request_excerpts']==11
  messages={x['message_id']:x for x in p['source_messages']};locators={x['request_id']:x for x in p['request_locators']};assert len(locators)==11 and len(r['dimensions'])==10
  assert v['current_summary_cross_receipt_checks']==10
  for user in r['user_request_register']:
   locator=locators[user['id']];message=messages[locator['message_id']];assert user['quote']in message['text']and locator['turn_id']==message['turn_id']and message['source_kind']=='read_thread_userMessage'
   source=user['source'];assert source['source_kind']=='direct_human_userMessage'and source['message_id']==locator['message_id']and source['turn_id']==locator['turn_id']
  assert p['coordination_report']['source_kind']=='coordinator_delegation_report'and p['coordination_report']['not_verbatim_user_quote']
  for row in r['dimensions']:
   assert row['acceptance_status']and row['verified_results']and row['pending_results']and row['phase31_change']['result']and row['phase31_change']['remaining_gap']
   for item in row['verified_results']:assert item['claim']and item['evidence']in row['evidence'];self.pin(item['evidence'])
  self.counts.update(acceptance_dimensions=10,acceptance_dimension_status_and_receipt_checks=10,coordinator_report_separately_labelled=True,acceptance_exact_user_message_locators=11,acceptance_reference_checks_not_gameplay=v['evidence_reference_checks'],acceptance_Source_syntax_checks_not_CPU=v['source_syntax_checks'],acceptance_Source_CPU_cases=0,acceptance_Native_frames=0)
 def browser(self):
  qa=self.record(OUT/'browser-validation.json');self.pin(OUT/'README.md');self.pin(OUT/'index.html',qa['final_html_sha256'])
  assert qa['status']=='passed'and qa['failed_count']==0 and qa['check_count']==len(qa['checks'])and all(x['status']=='passed'for x in qa['checks'])
  assert qa['console_errors']==qa['console_warnings']==[]and qa['Native_frames_added']==qa['Source_CPU_cases_added']==0
  page=Portal31();page.feed((OUT/'index.html').read_text());payload=json.loads(page.evidence);assert len(page.ids)==len(set(page.ids))
  assert len(page.sources)==3
  for name in('battle_scene_controller.py','postbattle_release_services.py','postbattle_early_services.py'):assert(ROOT/'source/recovered'/name).read_text()in page.sources
  native=read(OUT/'runtime/evidence.json');assert payload['native']==native['summary']and payload['acceptance']==read(OUT/'acceptance/requirements.json')
  for name,keys,path in(('source',('original_CPU_parent_cases','counts','source_guard_count','new_production_source_modules','new_gameplay_algorithm_claim','limits'),'player-disposition/validation.json'),('fields',('original_contract_CPU_cases','actual_caller_RTS_CPU_cases','explicit_prefix_CPU_cases','model_guard_check_count','remaining_access_count','all_indirect_classification_counts','newly_proved_disjoint_all_count'),'fields-static/verification.json')):
   full=read(OUT/path);assert payload[name]=={key:full[key]for key in keys}
  assert payload['roster_contract']==read(OUT/'fields-static/roster-write-lifecycle-contract.json')
  full=read(OUT/'fields-static/verification.json');assert payload['field_counterexamples']=={key:full[key]for key in('bare_BD96_counterexamples','bare_BDB8_alias_prefixes','controlled_nontrivial_swaps','controlled_same_value_escape_protocol','controlled_raw_city_future_aliases')}
  roles=dict(human_entries='human_phase_entry',software_inputs='passive_software_input',actual_BC46_calls='actual_BC46_call_return',mode_targets='actual_mode_target',actual_early_JSR_boundaries='actual_JSR_boundary',outcome_0514_original_writes='all_original_0514_writes',commander_outcome_producer_writes='commander_outcome_producer',title_Start_bypass='ordinary_Start_bypass',ruler_controller_writes='original_ruler_controller_write',postbattle_SRAM_writes='postbattle_SRAM_write',auxiliary_bus_events='auxiliary_bus_event',controller_byte_reads='controller_read')
  assert payload['event_roles']==roles and[x['case']for x in payload['routes']]==[x['case']for x in native['routes']];displayed=events=0
  for route in payload['routes']:
   case=route['case'];home=OUT/'runtime'/case;original_points=read(home/'original-control/checkpoints.json');other_points=read(home/'observer/checkpoints.json');ob=read(home/'observations.json');plan=read(home/'original-control/input-plan.json')
   by={x['frame']:x for x in original_points};others={x['frame']:x for x in other_points};reasons={}
   def add(frame,reason):
    for target in(frame-1,frame,frame+1):
     if target in by:reasons.setdefault(target,set()).add(reason+(' / adjacent'if target!=frame else''))
   add(min(by),'first frame');add(max(by),'last frame');previous=None
   for frame,point in sorted(by.items()):
    assert point['fields']==others[frame]['fields']and len(point['fields'])==49
    signature=tuple(json.dumps(point['fields'].get(k),sort_keys=True)for k in('global_007A','NMI_0078','battle_0500_0501','active_human_disposition','raw_destination_0540'))
    if previous is not None and signature!=previous:add(frame,'observed main/NMI/phase/human/destination change')
    previous=signature
   for step in plan:add(step['start_frame']+1,'ordinary input-plan boundary')
   for key in('actual_BC46_calls','actual_early_JSR_boundaries','commander_outcome_producer_writes','outcome_0514_original_writes','title_Start_bypass','ruler_controller_writes','postbattle_SRAM_writes'):
    for event in event_objects(ob.get(key,[])):add(event['frame'],'original event:'+key)
   assert route['points']==[dict(by[f],display_selection_reasons=sorted(reasons[f]))for f in sorted(reasons)]and route['observer_points']==[others[f]for f in sorted(reasons)]
   assert route['full_route_frames']==len(original_points)==self.native_routes[case]['frames']and route['displayed_point_count']==len(reasons)and route['base']=='runtime/'+case+'/'and route['ancestry']==self.native_routes[case]['ancestry']and route['input_plan']==plan
   selected={}
   for key,role in roles.items():
    for event in event_objects(ob.get(key,[])):
     seq=event['sequence']
     if seq not in selected:selected[seq]=dict(event,display_roles=[])
     else:assert{k:v for k,v in selected[seq].items()if k!='display_roles'}==event
     if role not in selected[seq]['display_roles']:selected[seq]['display_roles'].append(role)
   assert route['events']==[selected[k]for k in sorted(selected)]
   compact={k:v for k,v in ob.items()if not isinstance(v,list)};compact.update(actual_BC46_calls=ob['actual_BC46_calls'],displayed_event_counts=dict(Counter(role for event in selected.values()for role in event['display_roles'])),complete_observation_path='runtime/'+self.native_routes[case]['observations'])
   assert route['observations']==compact
   for variant,audio in zip(('original-control','observer'),route['audio']):
    path=OUT/audio['path'];assert path==home/variant/'full-audio.wav';self.pin(path,audio['sha256'])
    with wave.open(str(path))as wav:assert(audio['sample_frames'],audio['duration_seconds'])==(wav.getnframes(),wav.getnframes()/48000)
   assert len(route['audio'])==2;displayed+=len(reasons);events+=len(selected)
  assert sum(x['full_route_frames']for x in payload['routes'])==2204
  assert(displayed,events)==(124,409)and qa['check_count']==801
  scope=qa['scope'];assert all(scope[k]==value for k,value in dict(routes=4,complete_native_first_original_frames=2204,explicit_display_points=124,paired_fields_per_display_point=49,field_selector_options=98,displayed_original_events=409,event_role_filters=48,complete_WAV=8,complete_Source_files=3,acceptance_dimensions=10).items())
  assert qa['initial_html_sha256']==qa['final_html_sha256']
  for link in page.links:
   u=urlparse(link)
   if u.scheme or not u.path:continue
   path=(OUT/unquote(u.path)).resolve()
   if path in(OUT/'verification.json',OUT/'package-receipt.json'):continue
   assert path.is_file(),('Broken portal link',link)
  for name,value in qa['artifact_and_dependency_sha256'].items():self.pin(name,value)
  self.counts.update(browser_checks=qa['check_count'],browser_Source_modules=3,browser_original_complete_frames=2204,browser_explicit_display_points=displayed,browser_original_fields_per_point=49,browser_selected_original_events=events,browser_WAV_options=8)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA
 audit=Audit(rom);audit.allow_pending=a.allow_pending;pending=[];audit.frozen_history();audit.runtime()
 for name,method in(('Source',audit.source_cases),('fields-static',audit.static_fields),('context',audit.context),('acceptance',audit.acceptance),('Root-browser-report',audit.browser)):
  try:method()
  except Pending as exc:
   if not a.allow_pending:raise
   pending.append(dict(stage=name,reason=str(exc)))
 manifest=read(OUT/'delivery-manifest.json');audit.pin(OUT/'delivery-manifest.json');assert manifest['base_audit']['sha256']==OLD_AUDIT and manifest['base_archive']['sha256']==OLD_ZIP and manifest['foundational_archive']['sha256']==V22_ZIP and manifest['include_roots']==['source/recovered','source/readable_c','scripts','analysis/phase31']
 assert not any(manifest[k]for k in('original_ROM_included','rebuilt_ROM_included','full_ROM_byte_source_included','toolchain_included','old_large_evidence_copied','canonical_v22_archive_replaced','external_publication'))
 for path in sorted(OUT.rglob('*')):
  if path.is_file()and path!=OUT/'verification.json'and path.name not in old.base.base.base.prior.POSTZIP and '__pycache__'not in path.parts and not any(x.startswith('exploratory')for x in path.parts):audit.pin(path)
 for folder in('source','scripts'):
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.suffix not in('.pyc','.pyo')and not any(x.startswith('exploratory')for x in path.parts):
    key=relative(path);pin=audit.pin(path);assert key not in audit.sources or audit.sources[key]==pin;audit.sources[key]=pin
 roots=tuple(x+'/'for x in manifest['include_roots']);names=set(manifest['include_files']);included={k:v for k,v in audit.pins.items()if k in names or k.startswith(roots)};external={k:v for k,v in audit.pins.items()if k not in included}
 result=dict(schema='phase31-postbattle-disposition-readonly-audit-v1',status='pending_final_artifacts'if pending else'passed',ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v30_incremental_preserved_sha256=OLD_ZIP,old_phase30_audit_sha256=OLD_AUDIT,old_phase30_postZIP_receipt_sha256=OLD_POSTZIP,old_v22_preserved_sha256=V22_ZIP,source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,included_dependency_sha256=included,external_dependency_sha256=external,checks=dict(audit.counts),pending=pending,source_CPU_cases=audit.counts.get('new_Source_CPU_cases',0),source_guard_cases=audit.counts.get('new_Source_guards',0),source_actual_caller_RTS_cases=audit.counts.get('new_Source_actual_caller_RTS',0),source_nonlocal_return_cases=audit.counts.get('new_Source_nonlocal_return',0),source_strict_dependency_prefix_cases=audit.counts.get('new_Source_strict_dependency_prefix',0),limits=['Read-only evidence audit; no CPU/core/producers/analyzers/old audit main executed.','Separate31 observer alone supplies selected internal software contexts, with no instantaneous N163/PPU/APU claim.','Initial and per-frame complete five buffers are compared within new schedules; historical PCM/state identity is not asserted.','New31 hardlinks are storage-only after full byte comparisons; no normalization or old output changes.','Natural imported ancestry, controlled19-byte ancestry with earlier legacy uncertainty, and any single-run discovery history remain separately disclosed.','Source cases, static CPU contracts, model checks, acceptance/BQA and Native frames retain distinct domains.','Stop after31; whole-ROM closure and a standalone complete emulator are not asserted.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=result['checks'],pending=pending,source_pins=len(audit.sources),artifact_pins=len(audit.pins))))
if __name__=='__main__':main()
