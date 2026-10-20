#!/usr/bin/env python3
"""Original-core city auxiliary-byte experiments with bounded declarations.

Unknown official field meanings remain unnamed. An unchanged menu cycle is
only a local observation, never an unused/padding or whole-ROM conclusion.
Older source, captures, HTML and archives are read-only.
"""
from pathlib import Path
import argparse,json,sys,ctypes as C,subprocess,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from capture_boot_cooperation_flows import Capture as BootCapture,fields as boot_fields,sha,digest,write,relative,ROM_SHA,CORE_SHA
MENU_MOTHER=ROOT/'analysis/phase13/runtime/city-menu-cancel-cycle/initial.state'
MENU_PLAN=ROOT/'analysis/phase13/runtime/city-menu-cancel-cycle/input-plan.json'
AI_MOTHER=ROOT/'analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame34623.state'
AUX_OFFSETS=(1,28,29,30,31)
CASES=('city-menu-baseline','city-menu-byte1-44','city-menu-tail-markers','ai-reinforce-byte1-0','ai-reinforce-byte1-44')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json','preparation.json','auxiliary-events.json','resource-events.json','observation-summary.json')

def fields(ram,sram):
 f=boot_fields(ram,sram)
 f.update(all30_city_auxiliary_bytes=[[sram[city*32+k]for k in AUX_OFFSETS]for city in range(30)],
  all30_city_records_raw32=sram[:960].hex(),all30_city_owners=[sram[32*i]&7 for i in range(30)],
  all30_city_rosters=[list(sram[32*i+17:32*i+27])for i in range(30)],all30_city_gold=[int.from_bytes(sram[32*i+2:32*i+4],'little')for i in range(30)],
  all30_city_reserve=[int.from_bytes(sram[32*i+12:32*i+14],'little')for i in range(30)],domestic_candidate_city_0036=ram[0x36],
  domestic_city_pointer_0020_0021=ram[0x20]|ram[0x21]<<8,
  observed_officers={str(ID):dict(raw=sram[0x3C0+12*ID:0x3C0+12*(ID+1)].hex(),health=sram[0x3C0+12*ID],
   status=sram[0x3C0+12*ID+11]&3,troops_raw16=int.from_bytes(sram[0x3C0+12*ID+8:0x3C0+12*ID+10],'little'))for ID in(5,8,30,131,167,191)})
 return f

class Capture(BootCapture):
 def __init__(self,*args):
  super().__init__(*args);self.mother=None;self.preparation=[];self.preparation_groups=[];self.aux_events=[];self.resource_events=[];self._previous_sram=None
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def serialize_bytes(self):
  size=self.rt.core.retro_serialize_size();buf=C.create_string_buffer(size)
  if not self.rt.core.retro_serialize(buf,size):raise RuntimeError('Original core serialization failed')
  return buf.raw  # Whole API buffer, without normalization or truncation.
 def observe(self,rt):
  super().observe(rt);ram,sram=rt.memory(2),rt.memory(0);extra=fields(ram,sram)
  for key in('all30_city_auxiliary_bytes','all30_city_records_raw32','all30_city_owners','all30_city_rosters','all30_city_gold','all30_city_reserve','domestic_candidate_city_0036','domestic_city_pointer_0020_0021','observed_officers'):self.rows[-1][key]=extra[key]
  self.rows[-1]['whole_serialized_state_sha256']=digest(self.serialize_bytes())
  comparison=bytearray(sram)
  for p in self.preparation:
   if p['address']in(0x6161,0x617C,0x617D,0x617E,0x617F):comparison[p['address']-0x6000]=p['before']
  self.rows[-1]['SRAM_comparison_copy_restoring_declared_menu_aux_sha256']=digest(comparison)
  if self._previous_sram is not None:
   changes=[dict(city=i,offset=k,before=self._previous_sram[32*i+k],after=sram[32*i+k])for i in range(30)for k in AUX_OFFSETS if self._previous_sram[32*i+k]!=sram[32*i+k]]
   if changes:
    self.aux_events.append(dict(kind='original-frame-end-city-auxiliary-change',frame=rt.frames,changes=changes));self.snap('original-aux-change-frame'+str(rt.frames),'actual per-frame SRAM change after declared preparation; no internalCPUtrace')
   troop=0x3C0+167*12+8
   before=int.from_bytes(self._previous_sram[troop:troop+2],'little');after=int.from_bytes(sram[troop:troop+2],'little')
   if before!=after:
    self.resource_events.append(dict(kind='original-frame-end-officer167-troop-change',frame=rt.frames,before=before,after=after,city4_gold=int.from_bytes(sram[130:132],'little'),city4_reserve=int.from_bytes(sram[140:142],'little'),domestic_budget=sram[0xF5D]));self.snap('original-officer167-troop-change-frame'+str(rt.frames),'actual original game-record writeback, not an internal helper trace')
  self._previous_sram=sram
 def inherit(self,mother):
  self.mother=Path(mother).resolve();self.rt.load_state(self.mother)
  self.initial_RAM=self.rt.memory(2);self.initial_SRAM=self.rt.memory(0)
  (self.out/'initial-ram.bin').write_bytes(self.initial_RAM);(self.out/'initial-sram.bin').write_bytes(self.initial_SRAM);(self.out/'initial.state').write_bytes(self.mother.read_bytes())
  write(self.out/'initial-fields.json',dict(self.current(),cold_boot=False,state_imported=True,mother=relative(self.mother),mother_sha256=sha(self.mother)))
 def prepare_begin(self,label):
  g=dict(label=label,frame=self.rt.frames,start_write_index=len(self.preparation),before={});self.preparation_groups.append(g)
  for kind,ident in(('RAM',2),('SRAM',0)):
   p=label+'-before-'+kind.lower()+'.bin';(self.out/p).write_bytes(self.rt.memory(ident));g['before'][kind]=p
 def patch(self,address,value,reason):
  # All permissions are data-specific. No controller, pointer, input,
  # request, result, status/death bit, text-ready or hardware acknowledgement.
  allowed={0x6161,0x617C,0x617D,0x617E,0x617F,0x6081,0x6082,0x6083,0x6B9C,0x6B9D}
  assert address in allowed and 0<=value<256
  view=(C.c_ubyte*8192).from_address(self.rt.core.retro_get_memory_data(0));old=view[address-0x6000]
  if old!=value:
   self.preparation.append(dict(frame=self.rt.frames,kind='SRAM',address=address,before=old,after=value,reason=reason));view[address-0x6000]=value
 def prepare_end(self):
  g=self.preparation_groups[-1];g['after']={};g['writes']=self.preparation[g['start_write_index']:]
  for kind,ident in(('RAM',2),('SRAM',0)):
   p=g['label']+'-after-'+kind.lower()+'.bin';(self.out/p).write_bytes(self.rt.memory(ident));g['after'][kind]=p
  self._previous_sram=self.rt.memory(0)
  write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups))
 def menu(self,variant):
  self.inherit(MENU_MOTHER);self.prepare_begin('menu-data-'+variant)
  if variant=='byte1':self.patch(0x6161,44,'controlled city11+1 raw44 only; official meaning unconfirmed')
  elif variant=='tail':
   for offset,value in zip(range(28,32),(0x12,0x34,0x56,0x78)):self.patch(0x6160+offset,value,'controlled city11 tail rawbyte%d only; official meaning unconfirmed'%offset)
  self.prepare_end()
  plan=json.loads(MENU_PLAN.read_text())
  for item in plan:self.step(item['frames'],item.get('buttons',()),'frozen original city-menu/cancel plan: '+item['purpose'],item.get('capture'))
  assert self.current()['global_state']==2 and self.current()['city_state_0400_040F'][:2]==[0,1]
  self.snap('menu-cycle-final','actual original four-icon menus / officer choices / cancellations return to world cursor')
 def AI(self,variant):
  self.inherit(AI_MOTHER);s=self.rt.memory(0)
  assert s[0xF8B]==0 and s[0xF5B]==0 and s[0xF5D]==30 and s[145]==167
  self.prepare_begin('AI-data-'+variant)
  self.patch(0x6082,1,'common valid city4 gold257 lowbyte before original AI request consumer')
  self.patch(0x6083,1,'common valid city4 gold257 highbyte before original AI request consumer')
  self.patch(0x6B9C,0x84,'common officer167 troops900 lowbyte; original highbyte03 retained, no status/result changes')
  if variant=='byte1':self.patch(0x6081,44,'only city4+1 raw44 contrasts baseline0; wrongword256 vs300 before original consumer')
  self.prepare_end()
  self.step(1,(),'ordinary idle original main/NMI/IRQ after disclosed natural AI request','AI-first-original-frame')
  start=self.rt.frames
  while self.current()['cooperation_status_6F8B']!=255:
   assert self.rt.frames-start<300,('bounded original AI request return',self.current())
   self.step(1,(),'ordinary idle; let original main/NMI consume real AI request without acknowledgement injection')
  assert self.current()['ruler_6F03']==1
  self.snap('AI-original-request-returned','actual original requestFF/ruler1 return; city subphase is captured, not forced; no internal CPU PC')
 def finish_observation(self,formal=False):
  self.snap('final');self.finish(exploratory=False);write(self.out/'auxiliary-events.json',self.aux_events);write(self.out/'resource-events.json',self.resource_events);write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups))
  (self.out/'full-flow.wav').rename(self.out/'full-audio.wav')
  result=dict(status='observed',frames=self.rt.frames,checkpoints=len(self.points),additional_core_memory_writes=len(self.preparation),preparation=self.preparation,
   mother=relative(self.mother),mother_sha256=sha(self.mother),final_fields=self.current(),auxiliary_original_changes=self.aux_events,resource_events=self.resource_events,full_audio=self.wav,
   script_sha256=sha(Path(__file__)),ROM_modified=False,source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,
   scope='Exploratory native observation only; no all-ROM unused/padding or official city-field name inferred.')
  write(self.out/('observation-summary.json'if formal else'exploration-summary.json'),result);return result

def capture_case(rom,out,case):
 c=Capture(rom,Path(out)/case)
 try:
  if case.startswith('city-menu'):
   variant={'city-menu-baseline':'baseline','city-menu-byte1-44':'byte1','city-menu-tail-markers':'tail'}[case];c.menu(variant)
   f=c.current();assert c.rt.frames==2220 and not c.aux_events and not c.resource_events
   expected=[0,0,0,0,0]if variant=='baseline'else[44,0,0,0,0]if variant=='byte1'else[0,0x12,0x34,0x56,0x78]
   assert f['all30_city_auxiliary_bytes'][11]==expected
   effects=dict(cohort='four-menu-original-cancel-cycle',variant=variant,city11_auxiliary_after=expected,original_auxiliary_write_events=0,
    final_controller=[f['global_state'],f['nmi_scene'],*f['city_state_0400_040F'][:2]],official_field_name=None,
    scope='Only this2220frame menu/officer-selection/cancel cycle. Cohort RGB/PCM/RAM comparison is separately audited; no unused/padding conclusion.')
   termination='Frozen ordinary original four-menu / domestic-officer / invasion-target / weapon-officer selections and B cancellation return to actual player world0/1; no command card spent.'
  else:
   variant='baseline'if case.endswith('-0')else'byte1';c.AI(variant);f=c.current();target=variant=='byte1'
   assert f['observed_officers']['167']['troops_raw16']==(1000 if target else 900)
   assert f['all30_city_reserve'][4]==(9399 if target else 9499)
   assert f['all30_city_gold'][4]==(239 if target else 229)and f['domestic_budget_6F5D']==(1 if target else 3)
   assert f['cooperation_status_6F8B']==255 and f['ruler_6F03']==1 and f['calendar_year_6F00']==89 and f['calendar_month_zero_based_6F01']==6
   assert len(c.resource_events)==(1 if target else 0)
   if target:assert c.resource_events[0]['frame']==20 and c.resource_events[0]['city4_gold']==257 and c.resource_events[0]['city4_reserve']==9399 and c.resource_events[0]['domestic_budget']==28
   effects=dict(cohort='real-AI-request-original-core',variant=variant,city4_auxiliary_after=f['all30_city_auxiliary_bytes'][4],
    final_troops167=f['observed_officers']['167']['troops_raw16'],final_reserve_city4=f['all30_city_reserve'][4],final_gold_city4=f['all30_city_gold'][4],final_budget=f['domestic_budget_6F5D'],
    original_troop_write_events=c.resource_events,actual_original_request_status_before=0,actual_original_request_status_after=255,
    calendar_original=[89,6],displayed_year_month=[189,7],reserve_natural_9499_preserved=True,request_pointer_RNG_or_weights_prepared=False,
    scope='Original core executes whole cooperation request; finalgold229/239,budget3/1 are thisNative window, not CPUtwo-main gold237/budget10/8. NoNative internalinstructiontrace.')
   termination='Natural frame34623 original July189 AI request0 mother; common validgold257/officer167troops900 plus onlyaux0/44; ordinary idle until originalFF while stillruler1, no subphase forced.'
  c.finish_observation(True);assert len(c.rows)==c.rt.frames and any(r['PCM_nonzero']for r in c.rows)
  artifacts={};empty=[]
  for p in sorted(c.out.iterdir()):
   if not p.stat().st_size:empty.append(p.name);continue
   if p.suffix in('.png','.bin','.state','.wav')or p.name in FORMAL:artifacts[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
  groups=[]
  for original in c.preparation_groups:
   g=dict(original)
   for key in('before','after'):g[key]={k:dict(path=p,bytes=(c.out/p).stat().st_size,sha256=sha(c.out/p))for k,p in g[key].items()}
   groups.append(g)
  inherited_validation=ROOT/'analysis/phase13/runtime/city-menu-cancel-cycle/validation.json'if case.startswith('city-menu')else ROOT/'analysis/phase15/runtime/cold-yearwrap/validation.json'
  r=dict(schema='phase18-native-city-auxiliary-flow-v1',status='passed',case=case,frames=c.rt.frames,checkpoint_count=len(c.points),rom_sha256=ROM_SHA,rom_modified=False,
   cold_boot=False,state_imported=True,mother_state=relative(c.mother),mother_sha256=sha(c.mother),battery_file_imported=False,fresh_process_per_run=True,
   inherited_context=dict(validation=relative(inherited_validation),validation_sha256=sha(inherited_validation),inherited_preparation_byte_writes=0,applied_in_this_run=False,natural_parent=True),
   controlled_fixture=bool(c.preparation),natural_gameplay=not bool(c.preparation),additional_core_memory_writes=len(c.preparation),additional_core_memory_writes_after_declared_preparation=0,
   additional_ready_or_result_injections=0,controller_pointer_request_RNG_weights_prepared=False,preparation=c.preparation,preparation_groups=groups,verified_effects=effects,
   termination=termination,final_fields=c.current(),core=c.rt.info,AV=c.rt.av_info,full_audio=dict(path='full-audio.wav',**c.wav),
   initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),all_frames_original_RGB_PCM_RAM_SRAM_hashed=True,
   all_frames_whole_serialized_buffer_hashed=True,serialized_buffer_normalized=False,source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,
   artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   script_sha256=sha(Path(__file__)),capture_base_sha256=sha(ROOT/'scripts/capture_boot_cooperation_flows.py'),runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),
   limits=['City+1 and28..31 remain without official names. Localmenu no-observed-effect is not unused/padding or a whole-ROM theorem.',
    'Prepared menuSRAM and wholeState differ frombaseline by explicit auxiliarydata, despite matching RAM/RGB/PCM in thisscope.',
    'AI Native whole-request effects and separately controlledCPU prefixes/two-main results have different end boundaries; they are never pooled into one internaltrace.',
    'Eachframe hashes all original2KRAM/8KSRAM/RGB/PCM/whole serializedAPIbuffer. Original files for checkpoints and preparation groups preserve fullbytes.',
    'Actual originalcore PNG/WAV do not claim restoredsource cycle hardware/PPU/PCM equivalence.0BVRAM/pathmetadataexcluded.'])
  write(c.out/'validation.json',r);return r
 finally:c.close()

def static_qa(out,receipts):
 out=Path(out);artifacts=images=audios=frames=callbacks=groups=0
 for r in receipts:
  folder=out/r['case'];rows=json.loads((folder/'frame-services.json').read_text());points=json.loads((folder/'checkpoints.json').read_text())
  assert len(rows)==r['frames']and [x['frame']for x in rows]==list(range(1,r['frames']+1))
  for name,pin in r['artifact_sha256'].items():
   p=folder/name;assert p.stat().st_size==pin['bytes']and sha(p)==pin['sha256'];artifacts+=1
  for p in points:
   row=rows[p['frame']-1]
   with Image.open(folder/p['image'])as im:assert im.size==(256,240)and digest(im.convert('RGB').tobytes())==row['RGB_sha256'];images+=1
   assert sha(folder/p['RAM'])==row['RAM_sha256']and sha(folder/p['SRAM'])==row['SRAM_sha256']and sha(folder/p['state'])==row['whole_serialized_state_sha256']
  with wave.open(str(folder/'full-audio.wav'),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000);pcm=w.readframes(w.getnframes());assert digest(pcm)==r['full_audio']['PCM_sha256'];audios+=1
  position=0
  for row in rows:
   stop=row['PCM_stop_byte'];assert digest(pcm[position:stop])==row['PCM_sha256']and(stop-position)//4==row['PCM_stereo_sample_frames'];position=stop;frames+=1
   assert len(row['all30_city_auxiliary_bytes'])==30 and all(len(x)==5 for x in row['all30_city_auxiliary_bytes'])and len(row['all30_city_rosters'])==30
  assert position==len(pcm);position=0
  for call in json.loads((folder/'audio-callbacks.json').read_text()):
   stop=position+call['stereo_sample_frames']*4;assert digest(pcm[position:stop])==call['pcm_sha256'];position=stop;callbacks+=1
  assert position==len(pcm)
  for g in r['preparation_groups']:
   for kind,base,size in(('RAM',0,2048),('SRAM',0x6000,8192)):
    before=bytearray((folder/g['before'][kind]['path']).read_bytes());after=(folder/g['after'][kind]['path']).read_bytes();assert len(before)==len(after)==size
    for p in g['writes']:
     if p['kind']==kind:assert before[p['address']-base]==p['before'];before[p['address']-base]=p['after']
    assert bytes(before)==after
   groups+=1
 result=dict(schema='phase18-native-static-v1',status='passed',nonempty_artifact_rehash_checks=artifacts,PNG_RAM_SRAM_wholeState_same_frame_checks=images,
  WAV_48k_stereo_checks=audios,frame_PCM_segment_checks=frames,audio_callback_segment_checks=callbacks,full_preparation_reconstruction_checks=groups,
  whole_state_hashes_recorded_per_frame=frames,failed_count=0,browser_or_listening_acceptance=False,script_sha256=sha(Path(__file__)))
 write(out/'static-validation.json',result);return result

def compare_cohorts(out):
 out=Path(out);baseline=json.loads((out/'city-menu-baseline/frame-services.json').read_text());result={}
 keys=('RGB_sha256','PCM_sha256','RAM_sha256','SRAM_sha256','whole_serialized_state_sha256','SRAM_comparison_copy_restoring_declared_menu_aux_sha256','all30_city_owners','all30_city_rosters','all30_city_gold','all30_city_reserve','observed_officers','city_state_0400_040F','text_progress_0300','text_cursor_0304')
 for name in('city-menu-byte1-44','city-menu-tail-markers'):
  rows=json.loads((out/name/'frame-services.json').read_text());assert len(rows)==len(baseline)
  counts={key:sum(a[key]!=b[key]for a,b in zip(baseline,rows))for key in keys}
  assert all(counts[k]==0 for k in keys if k not in('SRAM_sha256','whole_serialized_state_sha256'))
  assert counts['SRAM_sha256']==counts['whole_serialized_state_sha256']==len(rows)
  pointsA=json.loads((out/'city-menu-baseline/checkpoints.json').read_text());pointsB=json.loads((out/name/'checkpoints.json').read_text());state_checks=[]
  prepared={p['address']-0x6000 for p in json.loads((out/name/'validation.json').read_text())['preparation']}
  for a,b in zip(pointsA,pointsB):
   assert(a['label'],a['frame'])==(b['label'],b['frame'])
   srA=(out/'city-menu-baseline'/a['SRAM']).read_bytes();srB=(out/name/b['SRAM']).read_bytes()
   differences={i for i,(x,y)in enumerate(zip(srA,srB))if x!=y};assert differences==prepared
   stA=(out/'city-menu-baseline'/a['state']).read_bytes();stB=(out/name/b['state']).read_bytes();position=stA.find(srA)
   assert position>=0 and stA.find(srA,position+1)==-1 and stB[position:position+8192]==srB
   assert stA[:position]==stB[:position]and stA[position+8192:]==stB[position+8192:]
   state_checks.append(dict(label=a['label'],frame=a['frame'],matched_literal_SRAM_offset=position,all_State_differences_inside_declared_SRAM=True))
  result[name]=dict(baseline='city-menu-baseline',frames=len(rows),different_frame_counts=counts,original_checkpoint_State_difference_checks=state_checks,
   comparison_copy_scope='Only a temporary SRAM comparison copy restores declared menuaux toparentvalues; actual SRAM/state files and wholeState hashes are never altered.',
   scope='Only original four-menu cycle; SRAM/wholeState prepareddifferences persist, no auxiliary unused/padding inference.')
 a=json.loads((out/'ai-reinforce-byte1-0/validation.json').read_text());b=json.loads((out/'ai-reinforce-byte1-44/validation.json').read_text())
 result['AI']=dict(baseline_case=a['case'],target_case=b['case'],baseline=a['verified_effects'],target=b['verified_effects'],source_CPU_count_in_this_comparison=0,
  scope='Full original-core request ends at its actualFF boundary; baseline26,target27frames. IndependentCPU actualcaller/two-main differ in scheduling and end boundaries.')
 write(out/'cohort-comparison.json',dict(schema='phase18-native-cohort-comparison-v1',status='passed',comparisons=result,script_sha256=sha(Path(__file__))));return result

def aggregate(out,receipts):
 out=Path(out);qa=static_qa(out,receipts);compare_cohorts(out)
 titles={'city-menu-baseline':'自然城市菜单周期基线','city-menu-byte1-44':'仅城市11+1扰动44','city-menu-tail-markers':'仅城市11尾28..31分别标记','ai-reinforce-byte1-0':'原AI请求：错位word256基线','ai-reinforce-byte1-44':'原AI请求：错位word300／实际补兵'}
 cases=[];repeat_checks=JSON_count=0
 for r in receipts:
  name=r['case'];rep=json.loads((out/name/'repeat-validation.json').read_text());assert rep['status']=='passed'and rep['all_hashes_equal'];repeat_checks+=rep['nonempty_artifact_checks'];JSON_count+=len(rep['formal_JSON_exact_parity'])
  points=json.loads((out/name/'checkpoints.json').read_text());cases.append(dict(case=name,title=titles[name],folder=name,validation=name+'/validation.json',repeat_validation=name+'/repeat-validation.json',checkpoints=name+'/checkpoints.json',
   frame_services=name+'/frame-services.json',input_plan=name+'/input-plan.json',preparation_file=name+'/preparation.json',preparation=r['preparation'],preparation_groups=r['preparation_groups'],full_audio={**r['full_audio'],'path':name+'/full-audio.wav'},full_WAV=name+'/full-audio.wav',
   images={p['label']:name+'/'+p['image']for p in points},frames=r['frames'],checkpoint_count=r['checkpoint_count'],mother_state=r['mother_state'],mother_sha256=r['mother_sha256'],inherited_context=r['inherited_context'],
   additional_core_memory_writes=r['additional_core_memory_writes'],verified_effects=r['verified_effects'],final_fields=r['final_fields'],termination=r['termination']))
 summary=dict(case_count=len(receipts),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
  nonempty_repeat_artifact_checks=repeat_checks,formal_JSON_repeat_checks=JSON_count,whole_serialized_buffers_exact=True,whole_serialized_hash_frames=sum(r['frames']for r in receipts),
  actual_full_WAV_count=len(receipts),sample_rate=48000,PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),additional_core_memory_writes=sum(r['additional_core_memory_writes']for r in receipts),
  inherited_preparation_byte_writes=0,state_imports=len(receipts),cold_boot_cases=0,additional_ready_or_result_injections=0,source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,
  excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),failed_count=0)
 paths=[Path(__file__),ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'.toolchain/nestopia/nestopia_libretro.dylib',MENU_MOTHER,MENU_PLAN,AI_MOTHER,
  ROOT/'analysis/phase13/runtime/city-menu-cancel-cycle/validation.json',ROOT/'analysis/phase15/runtime/cold-yearwrap/validation.json']
 e=dict(schema='phase18-native-city-auxiliary-flows-v1',status='passed',rom_sha256=ROM_SHA,summary=summary,native_cases=cases,core=receipts[0]['core'],
  cohort_comparison='cohort-comparison.json',dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in paths])
 write(out/'evidence.json',e);write(out/'validation.json',dict(schema=e['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))))
 lines=['# 原城市辅助字节：菜单与真实AI补兵五组对照','',
  '五案只运行固定原ROM与Nestopia；恢复源码未安装，帧字段不是Native内部CPU trace，原WAV不是Python合成。每个重复独立fresh process，整份序列化buffer未截断、未归一化；每个原frame还保留整buffer hash。','',
  '前三案公开phase13自然城市菜单母档和冻结原按钮计划。基线无core写；仅city11+1 0→44一byte或尾28..31 0→12/34/56/78hex四byte；完整四菜单、资料/武将选择与B取消、2220帧回world0/1。这2220帧RGB/PCM/全部RAM及观察owner/名册/金/预备兵/武将记录与基线相同。准备的SRAM字节与wholeState不同并持续保留，不能把本地no-observed-effect写成unused/padding或官方含义。','',
  'AI两案自然母档是phase15零write全年回放frame34623，原calendar[89,6]表示189年7月。原已有request0，city4首167；共同仅真gold9504→257两byte、167兵1000→900低一byte，保留天然reserve9499、原兵highbyte03和所有状态。仅target另改city4+1 0→44，原错位word由256变300；不改pointer、RNG、weights、request、ready、ack或controller。','',
  '原核心target第20帧真实167兵900→1000、reserve9499→9399，当时gold257/budget28；baseline没有补兵。完整原AI请求FF时baseline26帧末兵900/res9499/gold229/budget3，target27帧末兵1000/res9399/gold239/budget1。后续原策略可以改变金与预算，故这些Native整个请求结果不能与独立CPU两main或前缀的gold237/budget10/8混成一条trace；补兵本身没有统一300金币费用。','',
  f"正式总计：{summary['frames_first_run']}首跑帧／{summary['frames_both_runs']}双跑帧，{summary['checkpoint_count']}points；{repeat_checks}非空artifact全文双跑相等（含{JSON_count}formal JSON）、{len(receipts)}完整48k stereo16bit WAV；{summary['additional_core_memory_writes']}公开准备byte写、5自然母档imports／0cold／0继承准备／0ready或result注入。",'',
  '[总证据](evidence.json) · [总回执](validation.json) · [完整cohort比较](cohort-comparison.json) · [图像/WAV/准备/逐帧wholeState静态QA](static-validation.json) · [捕获脚本](../../../scripts/capture_city_auxiliary_fields.py)','']
 for c in cases:lines.extend(['## '+c['title'],'',f"{c['frames']}原帧／{c['checkpoint_count']}检查点／{c['additional_core_memory_writes']}准备byte。",'',f"[回执]({c['validation']}) · [双跑全文hash]({c['repeat_validation']}) · [真实检查点]({c['checkpoints']}) · [每帧字段/hash]({c['frame_services']}) · [原按钮/idle]({c['input_plan']}) · [全部准备与前后dump]({c['preparation_file']}) · [原WAV]({c['full_WAV']})",''])
 (out/'README.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(status='passed',summary=summary,static_QA=qa),ensure_ascii=False),flush=True)

def review_existing(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);base=ROOT/'analysis/phase15/runtime/cold-yearwrap';points=json.loads((base/'checkpoints.json').read_text());changes=[];previous=None;values=set();proof=[]
 for p in points:
  path=base/p['SRAM'];s=path.read_bytes();vector=bytes(s[32*city+k]for city in range(30)for k in AUX_OFFSETS);values.update(vector)
  if previous is not None and vector!=previous[1]:changes.append(dict(frame=p['frame'],label=p['label'],changes=[dict(city=i//5,offset=AUX_OFFSETS[i%5],before=a,after=b)for i,(a,b)in enumerate(zip(previous[1],vector))if a!=b]))
  previous=p,vector;proof.append(dict(frame=p['frame'],label=p['label'],SRAM=relative(path),SRAM_sha256=sha(path),city_auxiliary_150B_sha256=digest(vector)))
 r=dict(schema='phase18-prior-natural-checkpoint-review-v1',status='observed',parent_validation=relative(base/'validation.json'),parent_validation_sha256=sha(base/'validation.json'),
  original_frames=json.loads((base/'validation.json').read_text())['frames'],checkpoint_count=len(points),observed_auxiliary_byte_values=sorted(values),checkpoint_auxiliary_changes=changes,
  scope='Only620 existing wholeSRAM checkpoints of zero-write natural yearwrap; not per-frame audit and not an all-ROM no-write/no-consumer theorem.',checkpoints=proof,
  proposed_menu_mother=relative(MENU_MOTHER),proposed_menu_mother_sha256=sha(MENU_MOTHER),proposed_menu_plan=relative(MENU_PLAN),proposed_menu_plan_sha256=sha(MENU_PLAN),
  proposed_AI_mother=relative(AI_MOTHER),proposed_AI_mother_sha256=sha(AI_MOTHER))
 write(out/'prior-natural-review.json',r);print(json.dumps({k:v for k,v in r.items()if k!='checkpoints'},ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path,nargs='?');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase18/runtime');p.add_argument('--review-existing',action='store_true');p.add_argument('--probe-menu',choices=('baseline','byte1','tail'));p.add_argument('--probe-AI',choices=('baseline','byte1'));p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--capture-child',action='store_true');p.add_argument('--repeat',action='store_true');a=p.parse_args()
 if a.review_existing:review_existing(a.out);return
 if a.rom is None:p.error('ROM required for capture')
 if not(a.probe_menu or a.probe_AI):
  if a.capture_child:
   r=capture_case(a.rom,a.out,a.case);print(json.dumps(dict(status='passed',case=a.case,frames=r['frames'],checkpoints=r['checkpoint_count'],writes=r['additional_core_memory_writes']),ensure_ascii=False),flush=True);return
  out=a.out.resolve();receipts=[]
  for case in CASES if a.case=='all'else(a.case,):
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out),'--case',case,'--capture-child'],check=True);one=json.loads((out/case/'validation.json').read_text())
   if a.repeat:
    second=out.parent/(out.name+'-repeat')/case;subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(second.parent),'--case',case,'--capture-child'],check=True);two=json.loads((second/'validation.json').read_text())
    checks=[dict(artifact=k,equal=v==two['artifact_sha256'].get(k),**v)for k,v in one['artifact_sha256'].items()]
    assert set(one['artifact_sha256'])==set(two['artifact_sha256'])and all(r['equal']for r in checks),[r for r in checks if not r['equal']]
    assert one['frames']==two['frames']and one['verified_effects']==two['verified_effects']and one['final_fields']==two['final_fields']
    write(out/case/'repeat-validation.json',dict(status='passed',first_run=relative(out/case),second_run=relative(second),all_hashes_equal=True,whole_serialized_buffers_exact=True,nonempty_artifact_checks=len(checks),artifacts=checks,
     formal_JSON_exact_parity=list(FORMAL),excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=one['excluded_snapshot_metadata_JSON'],script_sha256=sha(Path(__file__))))
   receipts.append(one)
  if a.repeat:aggregate(out,receipts)
  return
 c=Capture(a.rom,a.out)
 try:
  if a.probe_AI:c.AI(a.probe_AI)
  else:c.menu(a.probe_menu)
  r=c.finish_observation();print(json.dumps({k:r[k]for k in('status','frames','checkpoints','additional_core_memory_writes','auxiliary_original_changes','resource_events')},ensure_ascii=False),flush=True)
 finally:c.close()
if __name__=='__main__':main()
