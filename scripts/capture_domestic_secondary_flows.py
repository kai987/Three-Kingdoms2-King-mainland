#!/usr/bin/env python3
"""Original Nestopia observations for secondary domestic requests and city data.

All old captures are immutable. Preparations are explicit ordinary game data,
never controller/request/result/ready/pointer/RNG state. Native fields do not
claim internal CPU instruction tracing or recovered-source hardware synthesis.
"""
from pathlib import Path
import argparse,ctypes as C,json,sys,subprocess,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from capture_city_auxiliary_fields import Capture as AuxCapture,fields as aux_fields
from capture_boot_cooperation_flows import Capture as BootCapture,write,sha,digest,relative,ROM_SHA,CORE_SHA

RESOURCE_MOTHER=ROOT/'analysis/phase13/runtime/city-menu-cancel-cycle/resource-menu.state'
CASES=('resource-transfer-baseline','resource-transfer-source-byte1-44','resource-transfer-destination-tail','natural-expansion-monthly-secondary-window')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json','preparation.json','auxiliary-events.json','secondary-events.json','observation-summary.json')

def fields(ram,sram):
 f=aux_fields(ram,sram)
 f.update(world_cursor_6F3F_6F42=list(sram[0xF3F:0xF43]),
  transfer_fields_0424_0434=list(ram[0x424:0x435]),transfer_fields_048E_049F=list(ram[0x48E:0x4A0]),
  confirmation_046C=ram[0x46C],cooperation_UI_040A_040F=list(ram[0x40A:0x410]),
  secondary_working_0036_0049=list(ram[0x36:0x4A]),
  city_counts_by_owner=[sum(sram[32*c]&7==r for c in range(30))for r in range(8)])
 return f

class Capture(AuxCapture):
 def __init__(self,*args):
  super().__init__(*args);self.secondary_events=[];self.secondary_previous=None
  (self.out/'initial.state').write_bytes(self.serialize_bytes())
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def observe(self,rt):
  super().observe(rt);f=self.current()
  self.rows[-1].pop('SRAM_comparison_copy_restoring_declared_menu_aux_sha256',None)
  for key in('world_cursor_6F3F_6F42','transfer_fields_0424_0434','transfer_fields_048E_049F','confirmation_046C','cooperation_UI_040A_040F','secondary_working_0036_0049','city_counts_by_owner'):self.rows[-1][key]=f[key]
  previous=self.secondary_previous
  if previous is not None and previous['cooperation_status_6F8B']!=f['cooperation_status_6F8B']:
   event=dict(frame=rt.frames,before=previous['cooperation_status_6F8B'],after=f['cooperation_status_6F8B'],ruler=f['ruler_6F03'],domestic_phase=f['domestic_phase_6F5B'],city_state=f['city_state_0400_040F'][:3],request_block=f['cooperation_6F8B_6FAB'])
   self.secondary_events.append(event)
   self.snap('request-%02X-frame%d'%(event['after'],rt.frames),'actual frame-end original request/status transition; no internal CPU trace')
  self.secondary_previous=f
 def patch(self,address,value,reason):
  assert 0<=value<256
  # Only city raw auxiliary/resource data or officer numeric attributes.
  if 0x6000<=address<0x63C0:assert(address-0x6000)%32 in(1,2,3,4,5,28,29,30,31)
  else:assert 0x63C0<=address<0x6EDC and(address-0x63C0)%12 in(0,1,2,3,4,6,7,8,9,10)
  view=(C.c_ubyte*8192).from_address(self.rt.core.retro_get_memory_data(0));old=view[address-0x6000]
  if old!=value:
   self.preparation.append(dict(frame=self.rt.frames,kind='SRAM',address=address,before=old,after=value,reason=reason));view[address-0x6000]=value
 def navigate_city(self,city):
  # Coordinate data is immutable ROM, not a controller-state shortcut.
  raw=Path(self.rom_path).read_bytes();offset=lambda pc:16+28*8192+(pc&8191)
  tx,ty=raw[offset(0xDEE9)+city],raw[offset(0xDF07)+city]
  for axis,target,negative,positive in((0,tx,'left','right'),(2,ty,'up','down')):
   for _ in range(40):
    current=self.current()['world_cursor_6F3F_6F42'][axis]
    if target<=current<target+16:break
    self.press(positive if current<target else negative,25,'ordinary world cursor toward city%d original ROM rectangle'%city)
   else:raise AssertionError(('bounded cursor navigation',city,axis,self.current()))
 def resource_transfer(self,variant):
  self.inherit(RESOURCE_MOTHER);assert self.current()['city_state_0400_040F'][:2]==[4,1]
  self.prepare_begin('pre-command-valid-city-data-'+variant)
  for a,v in((0x61C2,0xAB),(0x61C3,0x26)):self.patch(a,v,'common city14 gold9899 leaves legitimate 100-gold receiving capacity')
  if variant=='byte1':self.patch(0x6161,44,'city11+1 raw44 contrast before actual cross-city transfer command; official name unconfirmed')
  elif variant=='tail':
   for k,v in zip(range(28,32),(0x12,0x34,0x56,0x78)):self.patch(0x61C0+k,v,'destination city14 tail marker at raw offset%d before actual transfer'%k)
  self.prepare_end()
  self.press('a',180,'choose original 物資輸送 command','transfer-destination-cursor')
  self.navigate_city(14);self.snap('transfer-city14-cursor')
  self.press('a',240,'choose original adjacent owned city14','transfer-gold-input')
  self.press('up',35,'request one original gold increment','transfer-gold-after-up')
  self.press('a',180,'confirm original gold amount','transfer-rice-input')
  self.press('a',180,'confirm original zero rice amount','transfer-third-resource-input')
  self.press('a',240,'confirm original zero third amount','transfer-consent')
  self.press('a',900,'approve original command consent and execute transfer','transfer-executed')
  self.press('a',240,'acknowledge actual transfer outcome','transfer-return')
 def cold_ruler1(self):
  old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
  for item in old[:13]:self.step(item['frames'],item.get('buttons',()),'original cold boot and scenario entry',item.get('capture'))
  self.press('down',25,'ordinary original ruler list down to row2')
  self.press('right',25,'ordinary original ruler list right to 袁紹')
  self.snap('ruler1-before-confirm')
  self.press('a',720,'choose original 袁紹/ruler1 human faction','ruler1-map-ready')
  self.press('a',120,'acknowledge original ruler turn prompt','ruler1-city-panel')
  self.press('a',120,'close original city panel to world cursor','ruler1-world-ready')
 def occupy_neutral0(self):
  self.cold_ruler1();assert self.current()['ruler_6F03']==1
  self.navigate_city(1);self.snap('ruler1-owned-city1-cursor')
  self.press('a',120,'open original commands at owned city1','ruler1-city1-icons')
  self.press('right',25,'select original military icon')
  self.press('a',180,'open original military submenu','ruler1-city1-military')
  self.press('a',180,'select original invasion command','ruler1-neutral0-target')
  self.navigate_city(0);self.snap('ruler1-neutral0-cursor')
  self.press('a',180,'confirm neutral city0 original invasion target','ruler1-neutral0-army')
  self.press('a',180,'select original city1 first officer77 for neutral occupation','ruler1-neutral0-army-selected')
  for _ in range(3):self.press('down',25,'move original army cursor toward おわり')
  self.snap('ruler1-neutral0-army-end-cursor')
  self.press('a',240,'confirm original army roster','ruler1-neutral0-army-confirmed')
  for i in range(12):
   f=self.current()
   if f['all30_city_owners'][0]==1 and f['global_state']==2 and f['city_state_0400_040F'][0]==0:break
   self.press('a',240,'ordinary original supplies/consent/neutral occupation acknowledgement','neutral-occupation-A%d'%i)
  self.snap('neutral-occupation-bounded-end')
  assert self.current()['all30_city_owners'][0]==1 and self.current()['city_counts_by_owner'][1]==4
 def zero_recruitment(self,ordinal):
  self.wait_ready(0,1)
  self.press('a',120,'open original city1 commands for legal zero-quantity recruitment')
  assert self.current()['city_state_0400_040F'][:2]==[1,1]
  self.press('right',25,'select original military icon')
  self.press('a',180,'open original military submenu')
  assert self.current()['city_state_0400_040F'][:2]==[3,1]
  self.press('right',25,'select original チョウヘイ command')
  assert self.current()['menu_cursor_0012']==1
  self.press('a',180,'open original recruitment fee message')
  self.press('a',180,'open original full-reserve quantity0 input','zero-recruit%d-quantity'%ordinal)
  self.press('a',180,'confirm original quantity0, not a frontend resource write')
  self.press('a',900,'approve original command card and let animation execute')
  self.press('a',240,'acknowledge original animation and open allocation roster','zero-recruit%d-allocation'%ordinal)
  for _ in range(2):self.press('down',25,'move original two-officer allocation cursor to おわり without assigning troops')
  self.press('a',300,'finish original allocation and return/advance turn','zero-recruit%d-finished'%ordinal)
 def wait_ready(self,main,phase,limit=900):
  start=self.rt.frames
  while True:
   f=self.current()
   if f['global_state']==2 and f['nmi_scene']==2 and f['city_state_0400_040F'][:2]==[main,phase]and f['text_progress_0300']==255 and f['text_cursor_0304']==255 and f['PPU_jobs_007E']==0:return
   assert self.rt.frames-start<limit,('bounded original UI readiness',main,phase,f)
   self.step(1,(),'wait for actual original text/PPU readiness before ordinary input')
 def natural_secondary(self):
  self.occupy_neutral0()
  for ordinal in(1,2):self.zero_recruitment(ordinal)
  self.snap('first-post-expansion-monthly-window')
  self.observe_monthly_secondary()
 def observe_monthly_secondary(self):
  start=self.rt.frames
  while self.rt.frames-start<2400:
   f=self.current()
   if any(e['after']==0xF8 for e in self.secondary_events):break
   if f['global_state']==2 and f['city_state_0400_040F'][:2]==[0,1]and f['ruler_6F03']==1:break
   if f['global_state']==2 and f['city_state_0400_040F'][0]in(10,11)and f['text_progress_0300']==255 and f['text_cursor_0304']==255:
    self.press('a',180,'ordinary original monthly notice acknowledgement while awaiting next human turn')
   else:self.step(8,(),'observe original post-expansion monthly AI/controller work')
  self.snap('natural-secondary-bounded-end')
 def continue_secondary(self,mother):
  self.inherit(mother);self.navigate_city(1)
  budget=self.current()['remaining_budget_raw_6F05'];assert 0<budget<8
  for ordinal in range(1,budget+1):self.zero_recruitment(ordinal)
  self.observe_monthly_secondary()
 def timing_probe(self,mother,delay):
  self.inherit(mother)
  assert self.current()['city_state_0400_040F'][:2]==[3,13]and self.current()['remaining_budget_raw_6F05']==0
  for _ in range(2):self.press('down',25,'ordinary allocation cursor to おわり without assigning troops')
  if delay:self.step(delay,(),'bounded ordinary unpressed confirmation delay, no RNG writes')
  self.press('a',700,'original final allocation confirmation, then no buttons during actual AI progression','bounded-confirmation-delay-%d'%delay)
 def finish_probe(self,formal=False):
  self.snap('final');BootCapture.finish(self,exploratory=False)
  (self.out/'full-flow.wav').rename(self.out/'full-audio.wav')
  write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups));write(self.out/'auxiliary-events.json',self.aux_events);write(self.out/'secondary-events.json',self.secondary_events)
  write(self.out/('observation-summary.json'if formal else'exploration-summary.json'),dict(status='observed',frames=self.rt.frames,checkpoints=len(self.points),mother=relative(self.mother)if self.mother else None,mother_sha256=sha(self.mother)if self.mother else None,
   preparation=self.preparation,secondary_events=self.secondary_events,auxiliary_events=self.aux_events,final_fields=self.current(),full_audio=self.wav,script_sha256=sha(Path(__file__)),rom_sha256=ROM_SHA,
   source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,additional_ready_or_result_injections=0,
   scope=('Frozen bounded original-core observation.'if formal else'Exploratory only.')+' No official auxiliary names, unused/padding, complete source-hardware or internal CPU trace claim.'))

def capture_case(rom,out,case):
 c=Capture(rom,Path(out)/case);c.rom_path=rom
 try:
  if case.startswith('resource-transfer-'):
   variant={'resource-transfer-baseline':'baseline','resource-transfer-source-byte1-44':'byte1','resource-transfer-destination-tail':'tail'}[case]
   c.resource_transfer(variant);f=c.current();assert c.rt.frames==2265 and len(c.preparation)=={'baseline':2,'byte1':3,'tail':6}[variant]
   assert f['all30_city_gold'][11]==9998 and f['all30_city_gold'][14]==9900 and f['remaining_budget_raw_6F05']==2
   assert f['global_state']==f['nmi_scene']==2 and f['city_state_0400_040F'][:2]==[0,1]and not c.aux_events
   effects=dict(cohort='actual-cross-city-resource-transfer',variant=variant,source_city=11,destination_city=14,gold_transferred=1,
    source_gold_before=9999,source_gold_after=9998,destination_gold_before_preparation=9999,destination_gold_prepared=9899,destination_gold_after=9900,
    command_cards_before=3,command_cards_after=2,third_amount_raw=0,city16_official_name_confirmed=False,original_auxiliary_write_events=0,
    source_auxiliary_after=f['all30_city_auxiliary_bytes'][11],destination_auxiliary_after=f['all30_city_auxiliary_bytes'][14],
    source_CPU_comparisons=0,scope='One actually committed original command; no unused/padding or official auxiliary-name conclusion.')
   termination='Natural resource menu mother; ordinary original destination/amount/command-consent/animation/return, not the prior four-menu cancellation cycle.'
  else:
   c.natural_secondary();f=c.current();assert not c.preparation and c.mother is None
   assert f['calendar_and_turn_6F00_6F06']==[89,1,0,1,4,4,1]and f['city_state_0400_040F'][:2]==[0,1]
   assert f['all30_city_owners'][0]==1 and f['city_counts_by_owner'][1]==4 and f['all30_city_rosters'][0][0]==77
   assert not any(e['after']==248 for e in c.secondary_events)
   occupied=next(p for p in c.points if p['label']=='neutral-occupation-bounded-end')
   effects=dict(cohort='natural-cold-expansion-and-one-monthly-window',cold_boot=True,selected_human_ruler=1,neutral_city=0,city0_owner_before=7,city0_owner_after=1,
    ruler1_city_count_before=3,ruler1_city_count_after=4,officer77_original_roster_move=dict(source_city=1,destination_city=0),neutral_occupation_checkpoint=occupied['label'],neutral_occupation_frame=occupied['frame'],
    original_remaining_cards_after_occupation=occupied['fields']['remaining_budget_raw_6F05'],ordinary_zero_quantity_recruitments=2,
    displayed_start_year_month=[189,1],displayed_end_year_month=[189,2],original_F8_observed=False,F8_consumer_or_return_verified=False,
    observed_request_transitions=c.secondary_events,final_controller=[f['global_state'],f['nmi_scene'],*f['city_state_0400_040F'][:2]],
    scope='One full original monthly progression after natural expansion; negative F8 observation is bounded and distinct from independent CPU branch coverage.')
   termination='True zero-write cold boot/title ruler1 selection, ordinary city1 army/supply/consent occupation of neutral0, two accepted zero-quantity recruitment commands, next original February ruler1 world turn. No F8 was observed.'
  c.finish_probe(True)
  groups=[]
  for original in c.preparation_groups:
   g=dict(original)
   for key in('before','after'):g[key]={k:dict(path=p,bytes=(c.out/p).stat().st_size,sha256=sha(c.out/p))for k,p in g[key].items()}
   groups.append(g)
  artifacts={};empty=[]
  for p in sorted(c.out.iterdir()):
   if not p.stat().st_size:empty.append(p.name);continue
   if p.suffix in('.png','.bin','.state','.wav')or p.name in FORMAL:artifacts[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
  r=dict(schema='phase19-native-domestic-secondary-flow-v1',status='passed',case=case,frames=c.rt.frames,checkpoint_count=len(c.points),rom_sha256=ROM_SHA,rom_modified=False,
   cold_boot=c.mother is None,state_imported=c.mother is not None,mother_state=relative(c.mother)if c.mother else None,mother_sha256=sha(c.mother)if c.mother else None,
   inherited_context=dict(validation='analysis/phase13/runtime/city-menu-cancel-cycle/validation.json',validation_sha256=sha(ROOT/'analysis/phase13/runtime/city-menu-cancel-cycle/validation.json'),inherited_preparation_byte_writes=0,natural_parent=True)if c.mother else None,
   battery_file_imported=False,fresh_process_per_run=True,controlled_fixture=bool(c.preparation),natural_gameplay=not bool(c.preparation),additional_core_memory_writes=len(c.preparation),
   additional_core_memory_writes_after_declared_preparation=0,additional_ready_or_result_injections=0,controller_pointer_request_RNG_weights_prepared=False,
   preparation=c.preparation,preparation_groups=groups,verified_effects=effects,termination=termination,final_fields=c.current(),core=c.rt.info,AV=c.rt.av_info,
   full_audio=dict(path='full-audio.wav',**c.wav),initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),
   all_frames_original_RGB_PCM_RAM_SRAM_hashed=True,all_frames_whole_serialized_buffer_hashed=True,serialized_buffer_normalized=False,
   source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,original_F8_observed=False,F8_consumer_or_return_verified=False,
   artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   script_sha256=sha(Path(__file__)),capture_auxiliary_base_sha256=sha(ROOT/'scripts/capture_city_auxiliary_fields.py'),capture_base_sha256=sha(ROOT/'scripts/capture_boot_cooperation_flows.py'),runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),
   limits=['F8 production/consumer/return were not observed in these Native cases. Independent CPU path validation is separate.',
    'Transfer contrasts only establish local no-observed-extra-effect for this one command. City+1/tail official meanings and unused/padding remain unproved.',
    'Every frame hashes complete original2KRAM/8KSRAM/RGB/PCM/whole serialized API buffer, without normalization. Checkpoints preserve actual full buffers.',
    'The third transfer amount/city+16 remains raw; it is not labelled loyalty.',
    'Empty0BVRAM and snapshot path-metadata JSON are excluded from nonempty exact-repeat totals.'])
  write(c.out/'validation.json',r);return r
 finally:c.close()

def static_qa(out,receipts):
 counts=dict(artifact_rehashes=0,PNG_RAM_SRAM_wholeState_same_frame=0,frame_PCM_segments=0,audio_callback_segments=0,preparation_reconstructions=0,WAV_48k_stereo=0)
 for r in receipts:
  f=out/r['case'];rows=json.loads((f/'frame-services.json').read_text());points=json.loads((f/'checkpoints.json').read_text());assert len(rows)==r['frames']and len(points)==r['checkpoint_count']
  for name,pin in r['artifact_sha256'].items():assert(f/name).stat().st_size==pin['bytes']>0 and sha(f/name)==pin['sha256'];counts['artifact_rehashes']+=1
  for p in f.glob('*.state'):
   assert p.with_name(p.stem+'-ram.bin').stat().st_size==2048 and p.with_name(p.stem+'-sram.bin').stat().st_size==8192
  for p in points:
   row=rows[p['frame']-1]
   with Image.open(f/p['image'])as im:assert im.size==(256,240)and digest(im.convert('RGB').tobytes())==row['RGB_sha256']
   assert sha(f/p['RAM'])==row['RAM_sha256']and sha(f/p['SRAM'])==row['SRAM_sha256']and sha(f/p['state'])==row['whole_serialized_state_sha256'];counts['PNG_RAM_SRAM_wholeState_same_frame']+=1
   assert(f/p['SRAM']).read_bytes()[:960].hex()==row['all30_city_records_raw32']
  with wave.open(str(f/'full-audio.wav'),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000);pcm=w.readframes(w.getnframes());assert digest(pcm)==r['full_audio']['PCM_sha256'];counts['WAV_48k_stereo']+=1
  position=0;callbacks=json.loads((f/'audio-callbacks.json').read_text());assert len(callbacks)==len(rows)
  for i,row in enumerate(rows):
   assert row['frame']==i+1 and len(row['all30_city_auxiliary_bytes'])==30 and all(len(x)==5 for x in row['all30_city_auxiliary_bytes'])
   stop=row['PCM_stop_byte'];assert digest(pcm[position:stop])==row['PCM_sha256']and(stop-position)//4==row['PCM_stereo_sample_frames'];position=stop
   assert callbacks[i]==dict(emulated_frame_start=i,stereo_sample_frames=row['PCM_stereo_sample_frames'],pcm_sha256=row['PCM_sha256']);counts['frame_PCM_segments']+=1;counts['audio_callback_segments']+=1
  assert position==len(pcm)
  for g in r['preparation_groups']:
   for kind,base,size in(('RAM',0,2048),('SRAM',0x6000,8192)):
    before=bytearray((f/g['before'][kind]['path']).read_bytes());after=(f/g['after'][kind]['path']).read_bytes();assert len(before)==len(after)==size
    for p in g['writes']:
     if p['kind']==kind:assert before[p['address']-base]==p['before'];before[p['address']-base]=p['after']
    assert bytes(before)==after
   counts['preparation_reconstructions']+=1
 result=dict(schema='phase19-native-static-v1',status='passed',checks=counts,failed_count=0,browser_or_listening_acceptance=False,script_sha256=sha(Path(__file__)))
 write(out/'static-validation.json',result);return result

def aggregate(out,receipts):
 static_qa(out,receipts);cases=[];checks=JSON_count=0
 baseline=json.loads((out/CASES[0]/'frame-services.json').read_text());comparison={}
 for case in CASES[1:3]:
  target=json.loads((out/case/'frame-services.json').read_text());assert len(baseline)==len(target)==2265
  keys=('RAM_sha256','RGB_sha256','PCM_sha256','SRAM_sha256','whole_serialized_state_sha256','all30_city_owners','all30_city_gold','all30_city_reserve','all30_city_rosters','observed_officers')
  different={k:sum(a[k]!=b[k]for a,b in zip(baseline,target))for k in keys}
  assert all(v==(2265 if k in('SRAM_sha256','whole_serialized_state_sha256')else 0)for k,v in different.items())
  comparison[case]=dict(baseline=CASES[0],frames=2265,different_frame_counts=different,scope='One committed cross-city transfer only; actual SRAM/state keep preparation differences, no normalization or unused inference.')
 write(out/'cohort-comparison.json',dict(schema='phase19-native-transfer-comparison-v1',status='passed',comparisons=comparison,script_sha256=sha(Path(__file__))))
 for r in receipts:
  case=r['case'];rep=json.loads((out/case/'repeat-validation.json').read_text());assert rep['status']=='passed'and rep['all_hashes_equal'];checks+=rep['nonempty_artifact_checks'];JSON_count+=len(rep['formal_JSON_exact_parity'])
  points=json.loads((out/case/'checkpoints.json').read_text())
  cases.append(dict(case=case,title='自然冷启动袁紹扩城与一个月轮：未观察F8'if r['cold_boot']else'原物资输送提交：'+case,folder=case,
   validation=case+'/validation.json',repeat_validation=case+'/repeat-validation.json',checkpoints=case+'/checkpoints.json',frame_services=case+'/frame-services.json',input_plan=case+'/input-plan.json',preparation_file=case+'/preparation.json',
   images={p['label']:case+'/'+p['image']for p in points},full_audio=dict(r['full_audio'],path=case+'/full-audio.wav'),full_WAV=case+'/full-audio.wav',
   frames=r['frames'],checkpoint_count=r['checkpoint_count'],cold_boot=r['cold_boot'],state_imported=r['state_imported'],mother_state=r['mother_state'],mother_sha256=r['mother_sha256'],
   preparation=r['preparation'],preparation_groups=r['preparation_groups'],additional_core_memory_writes=r['additional_core_memory_writes'],verified_effects=r['verified_effects'],final_fields=r['final_fields'],termination=r['termination']))
 summary=dict(case_count=len(cases),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
  nonempty_repeat_artifact_checks=checks,formal_JSON_repeat_checks=JSON_count,whole_serialized_buffers_exact=True,whole_serialized_hash_frames=sum(r['frames']for r in receipts),actual_full_WAV_count=len(cases),sample_rate=48000,
  PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),additional_core_memory_writes=sum(r['additional_core_memory_writes']for r in receipts),
  inherited_preparation_byte_writes=0,state_imports=sum(r['state_imported']for r in receipts),cold_boot_cases=sum(r['cold_boot']for r in receipts),additional_ready_or_result_injections=0,
  source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,original_F8_observed=False,F8_consumer_or_return_verified=False,
  excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),failed_count=0)
 paths=[Path(__file__),ROOT/'scripts/capture_city_auxiliary_fields.py',ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'.toolchain/nestopia/nestopia_libretro.dylib',RESOURCE_MOTHER,RESOURCE_MOTHER.parent/'validation.json',ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json']
 e=dict(schema='phase19-native-domestic-secondary-flows-v1',status='passed',rom_sha256=ROM_SHA,summary=summary,native_cases=cases,core=receipts[0]['core'],cohort_comparison='cohort-comparison.json',dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in paths])
 write(out/'evidence.json',e);write(out/'validation.json',dict(schema=e['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))))
 text=['# 阶段19：原模拟器输送命令与自然扩城月轮','',
  '原ROM和Nestopia未改。三组输送导入同一旧自然resource-menu母档；第四组真正冷启动，不导入存档或电池文件。所有双跑各用fresh Python进程，完整serialized API buffer不截断、不归一化。',
  '', '三组都通过普通按键实际传送1金：城11 9999→9998、城14准备9899→9900，原行动卡3→2并回city0/1。共同仅准备目的城合法金容量2B；source+1组额外1B，destination tail组额外4B。对应完整准备前后2K/8K与每byte old→new见各案preparation和validation。',
  '', '两扰动案与基线的2265实际帧RGB/PCM/2KRAM一致；实际SRAM与wholeState保留准备差异。所有150B辅助字节每帧保存且没有观察到原写入。这只说明该输送命令窗口没有可观察额外作用，不能证明unused/padding或正式名称。第三个输送数量对应city+16，仍叫raw第三项，不叫忠诚。',
  '', '自然案原标题普通选择袁紹ruler1，自城1出征邻接中立0：原owner7→1、77原名册从1移至0、城数3→4、卡3→2。随后两次原征兵0数量且不分配兵力，原卡耗尽，实际月轮推进189年1月→2月并回ruler1世界界面。它是零前端内存写入的自然冷启动流程，未观察F8，更未验证其consumer/return。',
  '', '探索最多四个普通月轮和同一自然allocation母档的八种正常确认时机仍无F8，保留在excluded exploratory目录，不作为正式通过病例或CPU内部trace。另行独立CPU分支覆盖不能改写这个Native负结果。',
  '',f'正式 {summary["case_count"]}案；首跑{summary["frames_first_run"]}帧／双跑{summary["frames_both_runs"]}帧；{summary["checkpoint_count"]}检查点；{checks}非空文件逐字节复跑（含{JSON_count}正式JSON）；{summary["additional_core_memory_writes"]}额外数据byte准备，{summary["cold_boot_cases"]}冷启动／{summary["state_imports"]}自然母档导入。',
  '', '[总证据](evidence.json) · [回执](validation.json) · [静态RGB/WAV/全State检查](static-validation.json) · [跨组比较](cohort-comparison.json) · [捕获脚本](../../../scripts/capture_domestic_secondary_flows.py)',
  '', 'Native公开API的逐帧内存/画面/音频与独立原CPU指令验证是不同证据，未把原core的PCM称为源码波形合成。空0BVRAM和snapshot路径metadata JSON从非空复跑计数排除。']
 for c in cases:text+=['',f'## {c["case"]}',f'[结果]({c["case"]}/validation.json) · [双跑]({c["case"]}/repeat-validation.json) · [输入]({c["case"]}/input-plan.json) · [逐帧字段]({c["case"]}/frame-services.json) · [检查点]({c["case"]}/checkpoints.json) · [原48kHz WAV]({c["full_WAV"]})']
 (out/'README.md').write_text('\n'.join(text)+'\n');print(json.dumps(summary,ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase19/runtime');p.add_argument('--probe',choices=('resource','cold-ruler1','occupy-neutral0','natural-secondary','continue-secondary','timing'));p.add_argument('--variant',choices=('baseline','byte1','tail'),default='baseline');p.add_argument('--mother',type=Path);p.add_argument('--delay',type=int,choices=(0,1,2,4,8,16,32,64),default=0);p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--capture-child',action='store_true');p.add_argument('--repeat',action='store_true');a=p.parse_args()
 if a.probe is None:
  if a.capture_child:
   assert a.case in CASES;r=capture_case(a.rom,a.out,a.case);print(json.dumps(dict(status='passed',case=a.case,frames=r['frames'],checkpoints=r['checkpoint_count'],writes=r['additional_core_memory_writes']),ensure_ascii=False),flush=True);return
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
 c=Capture(a.rom,a.out);c.rom_path=a.rom
 try:
  if a.probe=='resource':c.resource_transfer(a.variant)
  elif a.probe=='timing':
   assert a.mother is not None;c.timing_probe(a.mother,a.delay)
  elif a.probe=='continue-secondary':
   assert a.mother is not None;c.continue_secondary(a.mother)
  elif a.probe=='natural-secondary':c.natural_secondary()
  elif a.probe=='occupy-neutral0':c.occupy_neutral0()
  else:c.cold_ruler1()
  c.finish_probe();print(json.dumps(dict(status='observed',frames=c.rt.frames,points=len(c.points),writes=len(c.preparation),final_controller=[c.current()['global_state'],c.current()['nmi_scene'],*c.current()['city_state_0400_040F'][:3]]),ensure_ascii=False),flush=True)
 except BaseException:
  c.finish_probe();raise
 finally:c.close()
if __name__=='__main__':main()
