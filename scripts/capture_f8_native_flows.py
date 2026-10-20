#!/usr/bin/env python3
"""Original Nestopia F8 request/consumer/choice/settlement observations.

This frontend never writes a request, reply, readiness flag, CPU register,
strategy weight or RNG state. Optional pre-flow numeric data is declared with
complete before/after memory. Original video/audio/state bytes are retained.
"""
from pathlib import Path
import argparse,ctypes as C,json,sys,subprocess,wave
from collections import deque
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from capture_domestic_secondary_flows import Capture as SecondaryCapture,fields as secondary_fields
from capture_boot_cooperation_flows import Capture as BootCapture,write,sha,digest,relative,ROM_SHA,CORE_SHA
from source.recovered.nestopia_context import NestopiaContext
from nes_service_runtime import ServiceRuntime

DEFAULT_MOTHER=ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window/AI-ruler4-status00-frame10405.state'
ALLOCATION_MOTHER=ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window/zero-recruit2-allocation.state'
CASES=('natural-F8-accept','natural-F8-reject')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json','preparation.json','auxiliary-events.json','secondary-events.json','F8-events.json','observation-summary.json')

def fields(ram,sram):
 f=secondary_fields(ram,sram)
 f.update(all30_city_food=[int.from_bytes(sram[32*c+4:32*c+6],'little')for c in range(30)],
  rulers=[dict(ruler=i,leader=sram[0xF07+8*i],raw_byte1=sram[0xF08+8*i],controller=sram[0xF0A+8*i],
   diplomatic_bytes=list(sram[0xF0B+8*i:0xF0F+8*i]),raw=sram[0xF07+8*i:0xF0F+8*i].hex())for i in range(7)],
  offer_cache_0036_0045=list(ram[0x36:0x46]),offer_resource_kind_0039=ram[0x39],offer_committed_word_003A_003B=int.from_bytes(ram[0x3A:0x3C],'little'),
  offer_quote_042F_0431=list(ram[0x42F:0x432]),consumer_choice_040C=ram[0x40C],consumer_text_0300_0304=[ram[0x300],ram[0x304]],
  readonly_RNG_cursor_bytes_0050_0055=list(ram[0x50:0x56]))
 return f

class Capture(SecondaryCapture):
 def __init__(self,*args):
  super().__init__(*args);self.f8_seen=False;self.f8_states=set();self.f8_events=[];self.f8_previous=None;self.prepared_numeric=[];self.retained_frames=deque(maxlen=4);self.first_offer=None;self.first_reply=None
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def serialize_bytes(self):
  raw=super().serialize_bytes();self.latest_original_serialized_buffer=raw;return raw
 def observe(self,rt):
  super().observe(rt);f=self.current()
  for key in('all30_city_food','rulers','offer_cache_0036_0045','offer_resource_kind_0039','offer_committed_word_003A_003B','offer_quote_042F_0431','consumer_choice_040C','consumer_text_0300_0304','readonly_RNG_cursor_bytes_0050_0055'):self.rows[-1][key]=f[key]
  context=NestopiaContext.parse(self.latest_original_serialized_buffer)
  assert context.ram==rt.memory(2)and context.sram==rt.memory(0)
  self.rows[-1].update(actual_saved_CPU_registers=context.registers,actual_saved_PRG_banks=context.prg_banks,Native_instruction_trace=False)
  if f['cooperation_status_6F8B']==248 and not self.f8_seen:
   for distance,p in enumerate(reversed(self.retained_frames),1):self.save_retained('F8-previous-%d-actual-frame'%distance,p)
   self.first_offer=dict(frame=rt.frames,producer_ruler=f['ruler_6F03'],resource_kind=f['offer_resource_kind_0039'],quote=f['offer_quote_042F_0431'],commit_word=f['offer_committed_word_003A_003B'],leaders_and_messenger=list(rt.memory(2)[0x40:0x43]),rulers=f['rulers'],city_gold=f['all30_city_gold'],city_food=f['all30_city_food'])
   self.f8_seen=True
  if self.f8_seen:
   state=(f['cooperation_status_6F8B'],*f['city_state_0400_040F'][:3],f['consumer_choice_040C'],f['text_progress_0300'],f['text_cursor_0304'])
   if state not in self.f8_states:
    self.f8_states.add(state);self.snap('F8-observed-%02X-city%d-%d-%d-choice%d-frame%d'%(state[0],state[1],state[2],state[3],state[4],rt.frames),'first actual post-F8 request/UI/text tuple, no injected completion')
   previous=self.f8_previous
   if previous is not None:
    for kind,key in(('request-change','cooperation_status_6F8B'),('ruler-diplomacy-change','rulers'),('city-gold-change','all30_city_gold'),('city-food-change','all30_city_food')):
     if previous[key]!=f[key]:self.f8_events.append(dict(kind=kind,frame=rt.frames,before=previous[key],after=f[key],city_state=f['city_state_0400_040F'][:3]))
   if self.first_reply is None and f['cooperation_status_6F8B']!=248:
    self.first_reply=dict(frame=rt.frames,observed_status=f['cooperation_status_6F8B'],city_state=f['city_state_0400_040F'][:3],ruler=f['ruler_6F03'],rulers=f['rulers'],city_gold=f['all30_city_gold'],city_food=f['all30_city_food'])
    self.snap('F8-first-observed-request-return','first actual frame-end nonF8; a transient reply within the frame is not invented')
   self.f8_previous=f
  self.retained_frames.append(dict(frame=rt.frames,RAM=bytes(context.ram),SRAM=bytes(context.sram),state=self.latest_original_serialized_buffer,image=rt.frame.copy(),fields=f,PCM_stop_byte=len(rt.pcm)))
 def save_retained(self,label,p):
  assert label not in self.labels;self.labels.add(label)
  p['image'].save(self.out/(label+'.png'))
  for key,suffix in(('RAM','-ram.bin'),('SRAM','-sram.bin'),('state','.state')):(self.out/(label+suffix)).write_bytes(p[key])
  (self.out/(label+'-vram.bin')).write_bytes(b'')
  write(self.out/(label+'.json'),dict(frame=p['frame'],actual_retained_previous_frame=True,no_state_reimport=True))
  self.points.append(dict(label=label,frame=p['frame'],reason='actual immediately previous retained RGB/RAM/SRAM/wholeState, never reconstructed or reimported',image=label+'.png',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',state=label+'.state',PCM_stop_byte=p['PCM_stop_byte'],fields=p['fields']))
 def prepare_numeric(self,changes):
  self.prepare_begin('declared-legitimate-pre-request-numeric-data')
  for change in changes:
   address,value=change['address'],change['after'];assert 0<=value<256
   if 0x6000<=address<0x63C0:assert(address-0x6000)%32 in(2,3,4,5,12,13)
   else:assert 0x63C0<=address<0x6EDC and(address-0x63C0)%12 in(0,1,2,3,4,6,7,8,9,10)
   view=(C.c_ubyte*8192).from_address(self.rt.core.retro_get_memory_data(0));before=view[address-0x6000]
   if 'before'in change:assert before==change['before']
   if before!=value:
    row=dict(frame=self.rt.frames,kind='SRAM',address=address,before=before,after=value,reason=change['reason']);self.preparation.append(row);view[address-0x6000]=value
  self.prepare_end();self.prepared_numeric=changes
 def seek(self,budget):
  start=self.rt.frames;entered_sponsor=self.current()['ruler_6F03']==4 and self.current()['cooperation_status_6F8B']==0
  while self.rt.frames-start<budget:
   if self.current()['cooperation_status_6F8B']==248:
    self.snap('F8-request-actually-produced');return True
   if self.current()['ruler_6F03']==4 and self.current()['cooperation_status_6F8B']==0:entered_sponsor=True
   if self.rt.frames>start and entered_sponsor and self.current()['ruler_6F03']==4 and self.current()['cooperation_status_6F8B']==255:return False
   self.step(1,(),'ordinary unpressed original main/NMI/IRQ under declared numeric starting data')
  return False
 def replay_natural_prefix(self,delay):
  plan=json.loads((ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window/input-plan.json').read_text())
  for p in plan:
   self.step(p['frames'],p.get('buttons',()),'frozen natural19 prefix: '+p['purpose'],p.get('capture'))
   if p.get('capture')=='zero-recruit2-allocation':break
  assert self.rt.frames==10152 and self.current()['city_state_0400_040F'][:2]==[3,13]
  for _ in range(2):self.press('down',25,'ordinary original allocation cursor to おわり')
  self.step(delay,(),'ordinary unpressed legal confirmation phase %d; no RNG write'%delay,'natural-confirmation-delay')
  self.press('a',1,'ordinary final allocation A starts original monthly progression','natural-allocation-confirmed')
 def respond(self,choice):
  assert self.f8_seen and self.current()['cooperation_status_6F8B']==248
  start=self.rt.frames
  while self.rt.frames-start<1200:
   f=self.current()
   if f['city_state_0400_040F'][:3]==[9,16,1]and f['text_progress_0300']==f['text_cursor_0304']==255:break
   if f['city_state_0400_040F'][:3]==[9,16,0]and f['text_progress_0300']==f['text_cursor_0304']==255:
    self.press('a',60,'ordinary original A advances completed F8 offer message')
   else:self.step(1,(),'wait for original F8 consumer text/choice, no ready injection')
  else:raise AssertionError('F8 consumer did not reach completed choice menu')
  self.snap('F8-original-choice-menu')
  if choice=='reject':self.press('right',45,'ordinary original Right selects rejection')
  self.snap('F8-original-choice-'+choice)
  self.press('a',1,'ordinary original A confirms '+choice,'F8-original-choice-confirmed')
  start=self.rt.frames
  while self.rt.frames-start<1800:
   f=self.current()
   if f['cooperation_status_6F8B']!=248:
    self.snap('F8-original-consumer-return');break
   if f['text_progress_0300']==f['text_cursor_0304']==255:self.press('a',1,'ordinary original message acknowledgement after chosen response')
   else:self.step(1,(),'wait for original response/consumer completion')
  else:raise AssertionError('F8 request remained pending after ordinary response inputs')
  start=self.rt.frames
  while self.rt.frames-start<3000:
   f=self.current()
   if f['global_state']==2 and f['ruler_6F03']==1 and f['city_state_0400_040F'][:2]==[0,1]and f['cooperation_status_6F8B']==255 and f['text_progress_0300']==f['text_cursor_0304']==255:break
   if f['global_state']==2 and f['text_progress_0300']==f['text_cursor_0304']==255 and(f['city_state_0400_040F'][:2]==[11,2]or f['city_state_0400_040F'][0]==10 or(f['city_state_0400_040F'][0]==9 and f['city_state_0400_040F'][1]in(14,15))):self.press('a',1,'ordinary later notice/next-human-turn acknowledgement, no flags supplied')
   else:self.step(1,(),'ordinary original AI continuation until actual next human world')
  else:raise AssertionError('original AI did not return to actual next human world')
  self.snap('F8-original-AI-continuation-human-world','original requestFF and actual human ruler1 world reached after all original AI continuation')
 def finish(self,formal=False):
  self.snap('final');BootCapture.finish(self,exploratory=False);(self.out/'full-flow.wav').rename(self.out/'full-audio.wav')
  for name,value in(('preparation.json',dict(writes=self.preparation,groups=self.preparation_groups)),('auxiliary-events.json',self.aux_events),('secondary-events.json',self.secondary_events),('F8-events.json',self.f8_events)):write(self.out/name,value)
  write(self.out/('observation-summary.json'if formal else'exploration-summary.json'),dict(status='observed',frames=self.rt.frames,checkpoints=len(self.points),F8_observed=self.f8_seen,preparation=self.preparation,F8_events=self.f8_events,final_fields=self.current(),
   mother_state=relative(self.mother)if self.mother else None,mother_sha256=sha(self.mother)if self.mother else None,first_offer=self.first_offer,first_observed_reply=self.first_reply,full_audio=self.wav,script_sha256=sha(Path(__file__)),rom_sha256=ROM_SHA,source_pipeline_installed=False,native_internal_CPU_trace=False))

def light_phase_probe(rom,out,delay):
 """One actual input phase from one natural state, no completed request prep."""
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir())
 rt=ServiceRuntime(rom,out);rows=[];plan=[];found=False;last=None;first_r4=False
 try:
  rt.load_state(ALLOCATION_MOTHER)
  assert rt.memory(2)[0x400:0x402]==bytes((3,13))and rt.memory(0)[0xF05]==0
  def serialized():
   size=rt.core.retro_serialize_size();raw=C.create_string_buffer(size);assert rt.core.retro_serialize(raw,size);return raw.raw
  def observe(runtime):
   nonlocal found,last,first_r4
   r,s=rt.memory(2),rt.memory(0);state=(s[0xF03],s[0xF8B],*r[0x400:0x403]);row=dict(frame=rt.frames,ruler=state[0],request=state[1],city_state=list(state[2:]),RNG_readonly=list(r[0x50:0x56]),domestic=list(s[0xF5B:0xF63]))
   if state!=last:
    if state[:2]==(4,0)and not first_r4:
     first_r4=True;raw=serialized();n=NestopiaContext.parse(raw);row.update(actual_saved_REG=n.registers,actual_PRG_banks=n.prg_banks)
     if delay in(36,40):
      (out/'ruler4-status00.state').write_bytes(raw);(out/'ruler4-status00-ram.bin').write_bytes(r);(out/'ruler4-status00-sram.bin').write_bytes(s)
    last=state
   rows.append(row)
   if s[0xF8B]==248:found=True
  def step(frames,buttons,purpose):
   plan.append(dict(start_frame=rt.frames,frames=frames,buttons=list(buttons),purpose=purpose));rt.run(frames,buttons,observer=observe)
  for _ in range(2):step(2,('down',),'ordinary allocation cursor Down');step(25,(),'ordinary release')
  if delay:step(delay,(),'bounded ordinary unpressed input phase, no memory preparation')
  step(2,('a',),'ordinary original allocation completion A')
  for _ in range(900):
   if found:break
   r,s=rt.memory(2),rt.memory(0)
   if rt.frames>delay+100 and r[0x7A]==2 and r[0x400]==11 and r[0x401]==2 and s[0xF03]==1:break
   step(1,(),'ordinary unpressed original AI progression')
  if found:rt.snapshot('actual-F8-produced')
  result=dict(schema='phase20-bounded-original-input-phase-probe-v1',status='observed',delay=delay,F8_observed=found,frames=rt.frames,mother_state=relative(ALLOCATION_MOTHER),mother_sha256=sha(ALLOCATION_MOTHER),
   original_ROM_sha256=sha(rom),original_core=rt.info,additional_core_memory_writes=0,request_ready_reply_RNG_PC_or_weights_prepared=False,input_plan=plan,frame_fields=rows,
   Native_instruction_trace=False,source_pipeline_installed=False,script_sha256=sha(Path(__file__)),scope='One legal confirmation phase; negative light probes generate no PNG/WAV. No internal instruction trace.')
  write(out/'phase-probe.json',result);return result
 finally:rt.close()

def capture_case(rom,out,case):
 """A complete original cold boot, original offer and actual next human turn."""
 assert case in CASES
 choice=case.removeprefix('natural-F8-');reply=0 if choice=='accept'else 1
 c=Capture(rom,Path(out)/case);c.rom_path=rom
 try:
  c.replay_natural_prefix(73);assert c.seek(900);c.respond(choice)
  f=c.current();assert c.mother is None and not c.preparation and not c.preparation_groups
  assert f['global_state']==f['nmi_scene']==2 and f['ruler_6F03']==1 and f['city_state_0400_040F'][:2]==[0,1]and f['cooperation_status_6F8B']==255
  assert c.first_offer['frame']==10500 and c.first_offer['resource_kind']==1 and c.first_offer['quote']==[114,0,0]and c.first_offer['commit_word']==114 and c.first_offer['leaders_and_messenger']==[222,8,38]
  response=c.first_reply;assert response['observed_status']==reply
  assert all('F8-previous-%d-actual-frame'%i in c.labels for i in range(1,5))
  points={p['label']:p for p in c.points};assert points['F8-original-choice-'+choice]['fields']['menu_cursor_0012']==reply
  clear=next(e for e in c.f8_events if e['kind']=='request-change'and e['before']==reply and e['after']==255)
  assert clear['frame']>response['frame']
  if choice=='accept':
   assert response['city_food'][2]==9885 and response['city_food'][4]==10113
   assert response['rulers'][1]['diplomatic_bytes']==[0,0,10,0]and response['rulers'][4]['diplomatic_bytes']==[160,0,0,0]
   cap=next(e for e in c.f8_events if e['kind']=='city-food-change'and e['before'][4]==10113 and e['after'][4]==9999)
  else:
   assert response['city_food'][2]==response['city_food'][4]==9999
   assert response['rulers'][1]['diplomatic_bytes']==response['rulers'][4]['diplomatic_bytes']==[0,0,0,0];cap=None
  effects=dict(cohort='natural-cold-boot-ordinary-input-F8-'+choice,choice=choice,ordinary_confirmation_delay_frames=73,
   natural_neutral_city_occupation=dict(city=0,owner_before=7,owner_after=1,ruler1_city_count_before=3,ruler1_city_count_after=4),
   ordinary_zero_quantity_recruitments=2,original_F8_observed=True,F8_consumer_or_return_verified=True,
   offer=c.first_offer,actual_menu_cursor=reply,first_observed_reply=response,original_request_FF_frame=clear['frame'],
   recipient_grain_later_cap_frame=cap['frame']if cap else None,AI_continuation_verified=True,
   next_human_world_frame=c.rt.frames,next_human_ruler=1,final_controller=[f['global_state'],f['nmi_scene'],*f['city_state_0400_040F'][:2]],
   scope='Original frame-ended buffers and ordinary inputs; saved CPU registers are snapshots, not an internal Native instruction trace. Later AI work is distinct from offer settlement.')
  c.finish(True)
  artifacts={};empty=[]
  for p in sorted(c.out.iterdir()):
   if not p.stat().st_size:empty.append(p.name);continue
   if p.suffix in('.png','.bin','.state','.wav')or p.name in FORMAL:artifacts[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
  r=dict(schema='phase20-native-F8-flow-v1',status='passed',case=case,frames=c.rt.frames,checkpoint_count=len(c.points),rom_sha256=ROM_SHA,rom_modified=False,
   cold_boot=True,state_imported=False,mother_state=None,mother_sha256=None,battery_file_imported=False,fresh_process_per_run=True,
   controlled_fixture=False,natural_gameplay=True,additional_core_memory_writes=0,additional_core_memory_writes_after_declared_preparation=0,
   additional_ready_or_result_injections=0,controller_pointer_request_RNG_weights_prepared=False,preparation=[],preparation_groups=[],
   verified_effects=effects,termination='Original request replied and cleared; subsequent original AI and notices completed, human ruler1 world/global2 NMI2 city0/1 actually reached.',
   final_fields=c.current(),core=c.rt.info,AV=c.rt.av_info,full_audio=dict(path='full-audio.wav',**c.wav),
   initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),
   all_frames_original_RGB_PCM_RAM_SRAM_hashed=True,all_frames_whole_serialized_buffer_hashed=True,serialized_buffer_normalized=False,
   source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,original_F8_observed=True,F8_consumer_or_return_verified=True,
   artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   script_sha256=sha(Path(__file__)),limits=[
    'Both cases are complete original cold boots, without state or battery import and without frontend data writes.',
    'The recorded ordinary confirmation delay73 changes execution timing; no RNG/request/reply/readiness/controller/pointer/weight is prepared.',
    'Every frame hashes full original2KRAM/8KSRAM/RGB/PCM/whole serialized API buffer. Actual checkpoints retain complete buffers and original saved REG/PRG mappings are read only.',
    'Offer recipient grain10113 and later clamp9999 are distinct actual frame observations in the accept case. Later whole-month resource changes must not be attributed solely to the offer.',
    'Empty0BVRAM and path-dependent snapshot metadata JSON are excluded from nonempty repeat totals.'])
  write(c.out/'validation.json',r);return r
 finally:c.close()

def static_qa(out,receipts):
 counts=dict(artifact_rehashes=0,PNG_RAM_SRAM_wholeState_same_frame=0,actual_saved_contexts=0,frame_PCM_segments=0,audio_callback_segments=0,WAV_48k_stereo=0,raw_field_checks=0)
 for r in receipts:
  folder=out/r['case'];rows=json.loads((folder/'frame-services.json').read_text());points=json.loads((folder/'checkpoints.json').read_text());assert len(rows)==r['frames']and len(points)==r['checkpoint_count']
  for name,pin in r['artifact_sha256'].items():assert(folder/name).stat().st_size==pin['bytes']>0 and sha(folder/name)==pin['sha256'];counts['artifact_rehashes']+=1
  for p in folder.glob('*.state'):
   ram=p.with_name(p.stem+'-ram.bin').read_bytes();sram=p.with_name(p.stem+'-sram.bin').read_bytes();context=NestopiaContext.parse(p.read_bytes())
   assert len(ram)==2048 and len(sram)==8192 and context.ram==ram and context.sram==sram;counts['actual_saved_contexts']+=1
  for p in points:
   row=rows[p['frame']-1];ram=(folder/p['RAM']).read_bytes();sram=(folder/p['SRAM']).read_bytes()
   with Image.open(folder/p['image'])as im:assert im.size==(256,240)and digest(im.convert('RGB').tobytes())==row['RGB_sha256']
   assert digest(ram)==row['RAM_sha256']and digest(sram)==row['SRAM_sha256']and sha(folder/p['state'])==row['whole_serialized_state_sha256'];counts['PNG_RAM_SRAM_wholeState_same_frame']+=1
   rebuilt=fields(ram,sram)
   for key in('rulers','all30_city_food','all30_city_gold','all30_city_records_raw32','all30_city_auxiliary_bytes','offer_cache_0036_0045','offer_resource_kind_0039','offer_committed_word_003A_003B','offer_quote_042F_0431','consumer_choice_040C','consumer_text_0300_0304'):
    assert row[key]==p['fields'][key]==rebuilt[key];counts['raw_field_checks']+=1
   n=NestopiaContext.parse((folder/p['state']).read_bytes());assert row['actual_saved_CPU_registers']==n.registers and row['actual_saved_PRG_banks']==list(n.prg_banks)
  with wave.open(str(folder/'full-audio.wav'),'rb')as wav:
   assert(wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000);pcm=wav.readframes(wav.getnframes());assert digest(pcm)==r['full_audio']['PCM_sha256'];counts['WAV_48k_stereo']+=1
  position=0;callbacks=json.loads((folder/'audio-callbacks.json').read_text());assert len(callbacks)==len(rows)
  for i,row in enumerate(rows):
   assert row['frame']==i+1 and len(row['rulers'])==7 and len(row['all30_city_food'])==30 and len(row['all30_city_auxiliary_bytes'])==30 and all(len(x)==5 for x in row['all30_city_auxiliary_bytes'])
   stop=row['PCM_stop_byte'];assert digest(pcm[position:stop])==row['PCM_sha256']and(stop-position)//4==row['PCM_stereo_sample_frames'];position=stop
   assert callbacks[i]==dict(emulated_frame_start=i,stereo_sample_frames=row['PCM_stereo_sample_frames'],pcm_sha256=row['PCM_sha256']);counts['frame_PCM_segments']+=1;counts['audio_callback_segments']+=1
  assert position==len(pcm)
 result=dict(schema='phase20-native-static-v1',status='passed',checks=counts,failed_count=0,browser_or_listening_acceptance=False,script_sha256=sha(Path(__file__)))
 write(out/'static-validation.json',result);return result

def aggregate(out,receipts):
 static_qa(out,receipts);cases=[];checks=JSON_count=0
 for r in receipts:
  case=r['case'];rep=json.loads((out/case/'repeat-validation.json').read_text());assert rep['status']=='passed'and rep['all_hashes_equal'];checks+=rep['nonempty_artifact_checks'];JSON_count+=len(rep['formal_JSON_exact_parity'])
  points=json.loads((out/case/'checkpoints.json').read_text())
  cases.append(dict(case=case,title='自然冷启动F8：'+('接受'if case.endswith('accept')else'拒绝'),folder=case,
   validation=case+'/validation.json',repeat_validation=case+'/repeat-validation.json',checkpoints=case+'/checkpoints.json',frame_services=case+'/frame-services.json',input_plan=case+'/input-plan.json',preparation_file=case+'/preparation.json',F8_events=case+'/F8-events.json',
   images={p['label']:case+'/'+p['image']for p in points},full_audio=dict(r['full_audio'],path=case+'/full-audio.wav'),full_WAV=case+'/full-audio.wav',
   frames=r['frames'],checkpoint_count=r['checkpoint_count'],cold_boot=True,state_imported=False,mother_state=None,mother_sha256=None,preparation=[],preparation_groups=[],additional_core_memory_writes=0,
   verified_effects=r['verified_effects'],final_fields=r['final_fields'],termination=r['termination']))
 summary=dict(case_count=len(cases),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
  nonempty_repeat_artifact_checks=checks,formal_JSON_repeat_checks=JSON_count,whole_serialized_buffers_exact=True,whole_serialized_hash_frames=sum(r['frames']for r in receipts),actual_full_WAV_count=len(cases),sample_rate=48000,
  PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),additional_core_memory_writes=0,inherited_preparation_byte_writes=0,state_imports=0,cold_boot_cases=len(cases),additional_ready_or_result_injections=0,
  source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,original_F8_observed=True,F8_consumer_or_return_verified=True,
  excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),failed_count=0)
 paths=[Path(__file__),ROOT/'scripts/capture_domestic_secondary_flows.py',ROOT/'scripts/capture_city_auxiliary_fields.py',ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',ROOT/'source/recovered/service_memory.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'.toolchain/nestopia/nestopia_libretro.dylib',ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window/input-plan.json',ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window/validation.json',ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json']
 e=dict(schema='phase20-native-F8-flows-v1',status='passed',rom_sha256=ROM_SHA,summary=summary,native_cases=cases,core=receipts[0]['core'],dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in paths])
 write(out/'evidence.json',e);write(out/'validation.json',dict(schema=e['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))))
 text=['# 阶段20：原Nestopia实际F8请求、选择、结算与AI续行','',
  '两案均为原ROM与原Nestopia真正冷启动，不导入state或battery，不写任何核心数据。沿冻结阶段19自然输入：标题选择袁紹、正常占领邻接中立城0令城数3→4、两次原征兵0数量消耗行动卡；第二次原分配菜单到おわり后额外无键等待73帧，再普通A确认。',
  '', '73帧来自独立探索的有界8位正常输入相位扫描（命中即停）；正式两案重新从冷启动完整回放，未使用探索存档、RNG/策略权重准备或请求/回复/ready/PC注入。所有输入逐项公开。',
  '', '原请求F8实际出现于10500帧，生产者ruler4/leader222、目标human ruler1/leader8、使者38，粮食报价与实际缓存均114。原city9/phase16显示原消息和横向选择；接受保持光标0、拒绝按Right至1，两者原A确认。',
  '', '接受案实际reply0后清FF，原city2粮9999→9885、city4粮9999→10113，后续原帧再cap9999；双方外交原字节分别ruler1 [00,00,0A,00]与ruler4 [A0,00,00,00]。拒绝案实际reply1后清FF，回复当帧双方外交仍0、城2/4粮仍9999。后续AI继续执行，不能把最终月轮全部资源变化归因于这一请求。',
  '', '每帧保存全部30城原32B/150B辅助字段、金粮/名册/owner、7君主完整8B及packed外交、报价与缓存、选择/文本/请求、实际保存的REG/PRG映射和原RGB/PCM/2KRAM/8KSRAM/wholeState hash。检查点保留全部原缓冲；首次F8前4/3/2/1真实帧另存，未重构或重新导入。君主byte1明确保留raw_byte1，未猜测正式含义。',
  '',f'正式{summary["case_count"]}案，首跑{summary["frames_first_run"]}帧／双跑{summary["frames_both_runs"]}帧，{summary["checkpoint_count"]}检查点；{checks}非空文件精确复跑（含{JSON_count}正式JSON）。每run独立fresh Python进程，原serialized API全buffer不截断、不归一化。',
  '', '[证据](evidence.json) · [回执](validation.json) · [原RGB/WAV/state静态QA](static-validation.json) · [捕获脚本](../../../scripts/capture_f8_native_flows.py)',
  '', '原core逐帧C API观察与独立CPU指令验证分列；saved REG是边界快照，不是Native内部指令trace。原48000Hz双声道16bit PCM/WAV不称恢复源码的波形合成。0B VRAM和含目录路径的snapshot metadata JSON不计入非空精确复跑。']
 for c in cases:text+=['', '## '+c['case'],f'[回执]({c["validation"]}) · [双跑]({c["repeat_validation"]}) · [原输入]({c["input_plan"]}) · [逐帧]({c["frame_services"]}) · [检查点]({c["checkpoints"]}) · [F8实际事件]({c["F8_events"]}) · [原WAV]({c["full_WAV"]})']
 (out/'README.md').write_text('\n'.join(text)+'\n');print(json.dumps(summary,ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase20/runtime');p.add_argument('--mother',type=Path,default=DEFAULT_MOTHER);p.add_argument('--numeric',type=Path);p.add_argument('--choice',choices=('none','accept','reject'),default='none');p.add_argument('--seek-budget',type=int,default=900);p.add_argument('--phase-scan',action='store_true');p.add_argument('--phase-child',type=int,choices=range(256));p.add_argument('--natural-delay',type=int,choices=range(256));p.add_argument('--case',choices=('all',)+CASES);p.add_argument('--capture-child',action='store_true');p.add_argument('--repeat',action='store_true');a=p.parse_args()
 if a.case:
  assert not a.numeric and a.natural_delay is None and not a.phase_scan and a.phase_child is None
  if a.capture_child:
   assert a.case in CASES;r=capture_case(a.rom,a.out,a.case);print(json.dumps(dict(status='passed',case=a.case,frames=r['frames'],checkpoints=r['checkpoint_count'],writes=0)),flush=True);return
  out=a.out.resolve();receipts=[]
  for case in CASES if a.case=='all'else(a.case,):
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out),'--case',case,'--capture-child'],check=True);one=json.loads((out/case/'validation.json').read_text())
   if a.repeat:
    second=out.parent/(out.name+'-repeat')/case;subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(second.parent),'--case',case,'--capture-child'],check=True);two=json.loads((second/'validation.json').read_text())
    checks=[dict(artifact=k,equal=v==two['artifact_sha256'].get(k),**v)for k,v in one['artifact_sha256'].items()]
    assert set(one['artifact_sha256'])==set(two['artifact_sha256'])and all(c['equal']for c in checks),[c for c in checks if not c['equal']]
    assert one['frames']==two['frames']and one['verified_effects']==two['verified_effects']and one['final_fields']==two['final_fields']
    write(out/case/'repeat-validation.json',dict(status='passed',first_run=relative(out/case),second_run=relative(second),all_hashes_equal=True,whole_serialized_buffers_exact=True,nonempty_artifact_checks=len(checks),artifacts=checks,
     formal_JSON_exact_parity=list(FORMAL),excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=one['excluded_snapshot_metadata_JSON'],script_sha256=sha(Path(__file__))))
   receipts.append(one)
  if a.repeat:
   assert a.case=='all';aggregate(out,receipts)
  return
 if a.phase_child is not None:
  r=light_phase_probe(a.rom,a.out,a.phase_child);print(json.dumps(dict(delay=r['delay'],F8_observed=r['F8_observed'],frames=r['frames'])),flush=True);return
 if a.phase_scan:
  a.out.mkdir(parents=True,exist_ok=True);ledger=[]
  for delay in(36,40)+tuple(x for x in range(256)if x not in(36,40)):
   folder=a.out/('delay-%03d'%delay)
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(folder),'--phase-child',str(delay)],check=True)
   r=json.loads((folder/'phase-probe.json').read_text());ledger.append(dict(delay=delay,F8_observed=r['F8_observed'],frames=r['frames'],path=relative(folder/'phase-probe.json'),sha256=sha(folder/'phase-probe.json')))
   write(a.out/'phase-scan-ledger.json',dict(schema='phase20-bounded-input-phase-scan-v1',status='F8_observed'if r['F8_observed']else'in_progress',maximum_phases=256,additional_core_memory_writes=0,probes=ledger))
   if r['F8_observed']:break
  return
 c=Capture(a.rom,a.out);c.rom_path=a.rom
 try:
  if a.natural_delay is None:
   c.inherit(a.mother);n=NestopiaContext.parse(a.mother.read_bytes());write(c.out/'captured-context.json',dict(registers=n.registers,actual_PRG_banks=n.prg_banks,mother_state=relative(a.mother),mother_sha256=sha(a.mother),Native_instruction_trace=False));c.prepare_numeric(json.loads(a.numeric.read_text())if a.numeric else[])
  else:
   assert a.numeric is None;c.replay_natural_prefix(a.natural_delay)
  found=c.seek(a.seek_budget)
  if found and a.choice!='none':c.respond(a.choice)
  c.finish();print(json.dumps(dict(F8_observed=found,frames=c.rt.frames,points=len(c.points),writes=len(c.preparation),request=c.current()['cooperation_status_6F8B'],city=c.current()['city_state_0400_040F'][:3]),ensure_ascii=False),flush=True)
 except BaseException:c.finish();raise
 finally:c.close()
if __name__=='__main__':main()
