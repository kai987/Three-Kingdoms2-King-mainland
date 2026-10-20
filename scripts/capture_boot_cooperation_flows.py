#!/usr/bin/env python3
"""Original Nestopia cold/reset/cooperation observations, zero memory injection.

Only controller input, the original libretro reset operation and observation
are permitted. Frame fields are not internal CPU/NMI instruction traces.
Exploratory runs live outside the frozen formal evidence directories.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,sys,wave,subprocess
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from nes_service_runtime import ServiceRuntime
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CASES=('cold-city-domestic-cycle','core-reset-battery-retention','title-intro-software-restart')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json')
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def relative(path):return str(Path(path).resolve().relative_to(ROOT))
def record(sram,ID):
 b=sram[0x3C0+12*ID:0x3C0+12*(ID+1)]
 return dict(ID=ID,raw=b.hex(),health=b[0],status=b[11]&3,experience_raw16=int.from_bytes(b[6:8],'little'),troops_raw16=int.from_bytes(b[8:10],'little'),troops_low10=int.from_bytes(b[8:10],'little')&1023)
def fields(ram,sram):
 g,n=ram[0x7A],ram[0x78];active=None;main=phase=None
 if(g in(9,10)and n==6):active='title';main,phase=ram[0x540:0x542]
 elif(g in(11,12)and n==7):active='ruler-selection';main,phase=ram[0x540:0x542]
 elif(g in(1,2)and n==2):active='city';main,phase=ram[0x400:0x402]
 elif(g in(3,4)and n==3):active='battle';main,phase=ram[0x500:0x502]
 elif(g in(5,6)and n==4):active='attack';main,phase=ram[0x540:0x542]
 elif(g in(7,8)and n==5):active='duel';main,phase=ram[0x4A8:0x4AA]
 return dict(global_state=g,nmi_scene=n,active_controller=active,active_main=main,active_phase=phase,
  city_state_0400_040F=list(ram[0x400:0x410]),title_state_0540_0544=list(ram[0x540:0x545]),battle_state_0500_050F=list(ram[0x500:0x510]),
  calendar_year_6F00=sram[0xF00],calendar_month_zero_based_6F01=sram[0xF01],ruler_6F03=sram[0xF03],turn_slot_6F04=sram[0xF04],remaining_budget_raw_6F05=sram[0xF05],event_flag_6F06=sram[0xF06],
  calendar_and_turn_6F00_6F06=list(sram[0xF00:0xF07]),ruler_records_6F07_6F3E=sram[0xF07:0xF3F].hex(),
  domestic_control_6F5B_6F62=list(sram[0xF5B:0xF63]),domestic_phase_6F5B=sram[0xF5B],domestic_budget_6F5D=sram[0xF5D],domestic_city_6F5E=sram[0xF5E],
  cooperation_status_6F8B=sram[0xF8B],cooperation_6F8B_6FAB=sram[0xF8B:0xFAC].hex(),
  battery_flags_6FE2_6FEB=list(sram[0xFE2:0xFEC]),scenario_variant_6F45=sram[0xF45],boot_saved_6F43=sram[0xF43],
  menu_cursor_0012=ram[0x12],menu_cursor_0013=ram[0x13],buttons_0081_0086=list(ram[0x81:0x87]),control_0470_047F=list(ram[0x470:0x480]),
  PPU_jobs_007E=ram[0x7E],NMI_busy_007B=ram[0x7B],IRQ_pending_0062=ram[0x62],IRQ_fields_0068_0075=ram[0x68:0x76].hex(),
  palette_0100_013F=ram[0x100:0x140].hex(),text_progress_0300=ram[0x300],text_cursor_0304=ram[0x304],text_queue_0310_037F=ram[0x310:0x380].hex(),
  mapper_main_DE_DF_E0=list(ram[0xDE:0xE1]),mapper_NMI_E1_E2_E3=list(ram[0xE1:0xE4]),audio_RAM_0700_07FF=ram[0x700:0x800].hex(),
  scratch_0000_001F=ram[:0x20].hex(),city_done_flags_04E0_04E4=list(ram[0x4E0:0x4E5]),UI_roster_0410_0419=list(ram[0x410:0x41A]),
  city11_record=sram[11*32:12*32].hex(),city11_gold=int.from_bytes(sram[11*32+2:11*32+4],'little'),city11_reserve_raw16=int.from_bytes(sram[11*32+12:11*32+14],'little'),
  recruitment_quantity_raw_048E_048F=int.from_bytes(ram[0x48E:0x490],'little'),allocation_working_reserve_042C_042D=int.from_bytes(ram[0x42C:0x42E],'little'),
  observer_officer_records={str(ID):record(sram,ID)for ID in(5,30,131)},title_intro_counter_0471_0470=ram[0x470]|ram[0x471]<<8)

class Capture:
 def __init__(self,rom,out):
  self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=True);assert not any(self.out.iterdir()),'Use a fresh owned directory'
  assert sha(rom)==ROM_SHA;self.rt=ServiceRuntime(rom,self.out);assert self.rt.info['core_sha256']==CORE_SHA and self.rt.av_info['sample_rate']==48000
  self.rt.core.retro_reset.argtypes=[];self.rt.core.retro_reset.restype=None
  self.rows=[];self.points=[];self.plan=[];self.transitions=[];self.reset_events=[];self.flow_events=[];self.previous_fields=None;self.software_restarts=[];self.labels=set();self.last=None;self.seen=set()
  ram,sram=self.rt.memory(2),self.rt.memory(0);self.initial_RAM=ram;self.initial_SRAM=sram
  (self.out/'initial-ram.bin').write_bytes(ram);(self.out/'initial-sram.bin').write_bytes(sram)
  write(self.out/'initial-fields.json',dict(fields(ram,sram),RAM_sha256=digest(ram),SRAM_sha256=digest(sram),cold_boot=True,state_imported=False,additional_core_memory_writes=0))
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def snap(self,label,reason='ordinary input-plan checkpoint'):
  if label in self.labels:return
  self.labels.add(label);self.rt.snapshot(label);f=self.current()
  self.points.append(dict(label=label,frame=self.rt.frames,reason=reason,image=label+'.png',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',state=label+'.state',
   global_state=f['global_state'],nmi_scene=f['nmi_scene'],active_controller=f['active_controller'],active_main=f['active_main'],active_phase=f['active_phase'],calendar_and_turn_6F00_6F06=f['calendar_and_turn_6F00_6F06'],cooperation_status_6F8B=f['cooperation_status_6F8B'],PCM_stop_byte=len(self.rt.pcm),fields=f))
 def observe(self,rt):
  ram,sram=rt.memory(2),rt.memory(0);pcm=rt.pcm_frame();assert len(ram)==2048 and len(sram)==8192 and rt.frame is not None
  f=fields(ram,sram);f.update(frame=rt.frames,RAM_sha256=digest(ram),SRAM_sha256=digest(sram),RGB_sha256=digest(rt.frame.tobytes()),native_dimensions=list(rt.frame.size),
   PCM_stereo_sample_frames=len(pcm)//4,PCM_sha256=digest(pcm),PCM_nonzero=any(pcm),PCM_stop_byte=len(rt.pcm));self.rows.append(f)
  prev=self.previous_fields
  if prev is not None:
   if f['global_state']==0 and prev['global_state']==10 and prev['active_main']==4:
    self.software_restarts.append(rt.frames);self.flow_events.append(dict(kind='observed-title-to-boot',frame=rt.frames,before=prev,after=f,internal_PC_observed=False));self.snap('software-restart-boot-frame-'+str(rt.frames),'original title4 followed by global0; combined with raw E000 jump evidence, no internal CPU trace')
   for key,kind in(('remaining_budget_raw_6F05','turn-budget-change'),('calendar_month_zero_based_6F01','calendar-month-change')):
    if prev[key]!=f[key]:self.flow_events.append(dict(kind=kind,frame=rt.frames,before=prev[key],after=f[key],ruler=f['ruler_6F03'],active_controller=f['active_controller'],active_main=f['active_main'],active_phase=f['active_phase']))
   if f['active_controller']=='city' and f['active_main']==9 and f['cooperation_status_6F8B']!=prev['cooperation_status_6F8B']:
    label=f'AI-ruler{f["ruler_6F03"]}-status{f["cooperation_status_6F8B"]:02X}-frame{rt.frames}'
    self.flow_events.append(dict(kind='observed-domestic-cooperation-status-change',frame=rt.frames,before=prev['cooperation_status_6F8B'],after=f['cooperation_status_6F8B'],ruler=f['ruler_6F03'],phase=f['domestic_phase_6F5B'],budget_raw=f['domestic_budget_6F5D'],city=f['domestic_city_6F5E'],checkpoint=label));self.snap(label,'original per-frame AI status request/return observation, not an internal CPU trace')
  self.previous_fields=f
  active=(f['global_state'],f['nmi_scene'],f['active_controller'],f['active_main'],f['active_phase'])
  if active!=self.last:self.transitions.append(dict(frame=rt.frames,from_state=self.last,to_state=active));self.last=active
  if active not in self.seen:
   self.seen.add(active);self.snap(f'observed-g{active[0]:02d}-n{active[1]:02d}-{active[2]or"inactive"}-{active[3]if active[3]is not None else 0:03d}-{active[4]if active[4]is not None else 0:03d}',
    'first observed active field tuple; not an internal CPU trace')
 def step(self,frames,buttons=(),purpose='',label=None):
  self.plan.append(dict(start_frame=self.rt.frames,frames=frames,buttons=list(buttons),purpose=purpose,**({'capture':label}if label else{})))
  self.rt.run(frames,buttons,observer=self.observe)
  if label:self.snap(label)
 def press(self,key,release=120,purpose='',label=None):self.step(2,(key,),purpose);self.step(release,(),purpose+' release/observe',label)
 def cold_city(self):
  old=read_cold_plan()
  for item in old:self.step(item['frames'],item.get('buttons',()),'original ordinary cold-boot plan throughcity',item.get('capture'))
  f=self.current();assert(f['global_state'],f['nmi_scene'],f['active_main'],f['active_phase'])==(2,2,1,1),f
 def reset(self):
  self.snap('before-core-reset','last actual core frame before libretro reset')
  ram,sram=self.rt.memory(2),self.rt.memory(0);self.rt.core.retro_reset();after_ram,after_sram=self.rt.memory(2),self.rt.memory(0)
  self.plan.append(dict(start_frame=self.rt.frames,operation='retro_reset',frames=0,buttons=[],purpose='original libretro core reset; no frontend RAM/SRAM writes'))
  for name,raw in(('immediate-reset-ram.bin',after_ram),('immediate-reset-sram.bin',after_sram)): (self.out/name).write_bytes(raw)
  event=dict(at_frame_boundary=self.rt.frames,operation='retro_reset',before_RAM_sha256=digest(ram),after_RAM_sha256=digest(after_ram),before_SRAM_sha256=digest(sram),after_SRAM_sha256=digest(after_sram),
   SRAM_byteidentical=sram==after_sram,SRAM_diff=[dict(address=0x6000+i,before=a,after=b)for i,(a,b)in enumerate(zip(sram,after_sram))if a!=b],
   before_fields=fields(ram,sram),immediate_after_fields=fields(after_ram,after_sram),RGB_at_this_boundary='No new core frame; no immediate-reset PNG fabricated')
  self.reset_events.append(event);self.flow_events.append(dict(kind='original-core-reset-boundary',**event))
 def finish(self,exploratory=True):
  assert len(self.rows)==self.rt.frames;wav=self.rt.save_wav(self.out/'full-flow.wav')
  write(self.out/'frame-services.json',self.rows);write(self.out/'checkpoints.json',self.points);write(self.out/'input-plan.json',self.plan);write(self.out/'audio-callbacks.json',self.rt.audio_calls);write(self.out/'state-transitions.json',self.transitions);write(self.out/'flow-events.json',self.flow_events)
  self.wav=wav
  if exploratory:
   write(self.out/'exploration-summary.json',dict(status='observed',frames=self.rt.frames,checkpoints=len(self.points),final_fields=self.current(),reset_events=self.reset_events,full_audio=wav,
    core=self.rt.info,AV=self.rt.av_info,additional_core_memory_writes=0,ROM_modified=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,script_sha256=sha(Path(__file__))))
  return self.current()
 def close(self):self.rt.close()
def read_cold_plan():
 old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text());stop=next(i for i,s in enumerate(old)if s.get('capture')=='city-commands');return old[:stop+1]

def original_recruitment(c,cycle):
 """Execute an accepted original recruitment/roster allocation command.

 Initial reserve9999 permits only zero recruitment quantity. Its accepted
 command still spends one original command card, and allocating existing
 reserve to Chen Gong creates room for later genuine100-troop recruitment.
 No value, confirmation, controller state or pending flag is supplied by us.
 """
 if cycle>1:c.press('a',120,'open city command icons',f'action{cycle}-icons')
 c.press('right',20,'select military city icon');c.press('a',180,'open military menu',f'action{cycle}-military-menu')
 c.press('right',20,'select original チョウヘイ recruitment command');c.press('a',180,'show original recruitment fee message',f'action{cycle}-fee-message')
 if cycle==1:
  # These original ordinary presses precede quantity entry. Preserve the
  # explored input timings/RNG; they are not an officer-selection stage.
  for _ in range(2):c.press('down',20,'ordinary Down during recruitment fee message')
 c.press('a',180,'open original recruitment quantity input',f'action{cycle}-quantity')
 c.press('up',20 if cycle==1 else 180,'request one quantity unit (100troops); original full-reserve guard retains zero on first action',f'action{cycle}-quantity-after-up')
 quantity=c.current()['recruitment_quantity_raw_048E_048F'];assert quantity==(0 if cycle==1 else 1),quantity
 c.press('a',900 if cycle==1 else 180,'confirm original quantity; await command-card consent',f'action{cycle}-command-consent')
 c.press('a',1200 if cycle==1 else 680,'approve original one-card consent and wait for real animation',f'action{cycle}-animation-returned')
 assert c.current()['remaining_budget_raw_6F05']==3-cycle
 c.press('a',240,'acknowledge completed animation and open troop allocation',f'action{cycle}-allocation-ready')
 assert c.current()['city_state_0400_040F'][:2]==[3,13]
 for _ in range(2 if cycle==1 else 1):c.press('down',20,'select Chen Gong (first action) or Yu Jin (later actions) in original allocation list')
 ID=30 if cycle==1 else 5;before=c.current()['observer_officer_records'][str(ID)]['troops_raw16']
 c.press('right',60,'allocate100 existing reserve troops through original Right input',f'action{cycle}-allocated')
 assert c.current()['observer_officer_records'][str(ID)]['troops_raw16']==before+100
 for _ in range(1 if cycle==1 else 2):c.press('down',20,'select original おわり roster row')
 assert c.current()['menu_cursor_0012']==3
 c.press('a',240 if cycle==1 else 300,'commit original roster allocation and return/advance turn',f'action{cycle}-committed')
 if cycle<3:assert c.current()['city_state_0400_040F'][:2]==[0,1]

def capture_case(rom,out,case):
 c=Capture(rom,out)
 try:
  assert not any(c.initial_SRAM),'Cold instances start without frontend battery import'
  if case=='title-intro-software-restart':
   c.step(4000,(),'ordinary unpressed cold intro; original timeout enters software reboot','software-restarted-title')
   assert c.software_restarts==[3073],c.software_restarts
   at=next(r for r in c.rows if r['active_controller']=='title'and r['active_main']==4)
   assert at['frame']==3063 and at['title_intro_counter_0471_0470']==0x0B58
   assert c.current()['active_controller']=='title'and c.current()['active_main']==1
   assert c.rt.memory(0)==c.initial_SRAM
   termination='unpressed cold title intro timed out, original title4/phase0→phase1→global0→title initialization completed'
  else:
   c.cold_city();city_sram=c.rt.memory(0);assert c.current()['calendar_and_turn_6F00_6F06']==[89,0,0,2,1,3,1]
   if case=='core-reset-battery-retention':
    c.reset();assert c.reset_events[0]['SRAM_byteidentical']
    c.step(1200,(),'run actual original post-reset CPU/NMI initialization','post-core-reset-title')
    assert c.rt.memory(0)==city_sram and c.current()['active_controller']=='title'and c.current()['active_main']==1
    assert c.rt.memory(2)!=(c.out/'before-core-reset-ram.bin').read_bytes()
    termination='original libretro reset returned to title while all8192 SRAM bytes and saved189year/January fields remained identical'
   else:
    for cycle in(1,2,3):original_recruitment(c,cycle)
    c.step(1200,(),'observe original nonplayer domestic cooperation and next-month player message','next-player-turn-message')
    assert c.current()['calendar_and_turn_6F00_6F06']==[89,1,0,2,1,3,1]
    c.press('a',180,'acknowledge original next-month player turn message','next-player-world-return')
    assert(c.current()['global_state'],c.current()['nmi_scene'],c.current()['active_main'],c.current()['active_phase'])==(2,2,0,1)
    final=c.current();assert final['city11_gold']==9959 and final['city11_reserve_raw16']==9899
    assert final['observer_officer_records']['5']['troops_raw16']==900 and final['observer_officer_records']['30']['troops_raw16']==900
    zero=next(r['frame']for r in c.rows if r['frame']>2922 and r['remaining_budget_raw_6F05']==0)
    ai=[e for e in c.flow_events if e['kind']=='observed-domestic-cooperation-status-change'and e['frame']>zero]
    assert len(ai)==12 and sorted({e['ruler']for e in ai})==[0,1,3,4,5,6],ai
    assert [e['after']for e in ai]==[0,255]*6
    assert c.rt.frames==12536,c.rt.frames
    termination='three accepted player command cards exhausted; six original domestic AI request0→returnFF updates completed, January advanced toFebruary, real A returned to player world/city0/1'
  c.snap('final','validated endpoint of the actual original-core flow');final=c.finish(exploratory=False)
  assert len(c.rows)==c.rt.frames and any(r['PCM_nonzero']for r in c.rows)
  assert all(r['native_dimensions']==[256,240]for r in c.rows)
  artifacts={};empty=[]
  for path in sorted(c.out.iterdir()):
   if path.stat().st_size==0:empty.append(path.name);continue
   if path.suffix in('.png','.bin','.state','.wav')or path.name in FORMAL:artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
  diff=[dict(address=0x6000+i,before=a,after=b)for i,(a,b)in enumerate(zip(c.initial_SRAM,c.rt.memory(0)))if a!=b]
  valid=dict(schema='phase14-native-boot-cooperation-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,
   cold_boot=True,state_imported=False,battery_file_imported=False,fresh_process_per_run=True,additional_core_memory_writes=0,additional_ready_or_result_injections=0,source_pipeline_installed=False,
   core=c.rt.info,AV=c.rt.av_info,frames=c.rt.frames,checkpoint_count=len(c.points),input_step_count=len(c.plan),termination=termination,final_fields=final,
   initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),initial_SRAM_all_zero=not any(c.initial_SRAM),SRAM_changed_addresses_since_cold_start=diff,
   script_sha256=sha(Path(__file__)),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),
   cold_button_plan_path=relative(ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json'),cold_button_plan_sha256=sha(ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json'),
   full_audio=c.wav,all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,
   observed_active_states=[list(x)for x in sorted(c.seen,key=repr)],software_restart_observed_frames=c.software_restarts,core_reset_events=c.reset_events,
   artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   limits=['Original-core per-frame fields/RGB/PCM are observations, not internalCPU traces or recovered-source rendering/audio synthesis.',
    'All native cases start by loading the unchanged ROM into a fresh core; no imported state or battery SRAM file.',
    'Core reset tests battery-backed SRAM retention inside one loaded instance; this frontend does not implement process/poweroff battery-file persistence.',
    'The zero-frame reset boundary has memory exports but no fabricated immediate RGB/audio frame; fields only change as subsequent original retro_run executes.',
    'Title intro software reset is observed as title4→global0 combined with pinned original JMP E000 bytes, not a claimed reset menu or captured PC trace.',
    'Only the cold-domestic case completes one calendar transition; other UI state arrays are inactive raw bytes unless active_controller identifies their scene.'])
  write(c.out/'validation.json',valid);return valid
 finally:c.close()

def static_artifact_qa(out,receipts):
 """Decode screenshots/WAV and rehash actual files; no browser simulation."""
 checks=[];images=audio=artifacts=0
 for r in receipts:
  folder=out/r['case']
  for name,expected in r['artifact_sha256'].items():
   path=folder/name;assert path.stat().st_size==expected['bytes']and sha(path)==expected['sha256'];artifacts+=1
   if path.suffix=='.png':
    with Image.open(path)as im:im.load();assert im.size==(256,240)and im.mode=='RGB'
    images+=1
   elif path.suffix=='.wav':
    with wave.open(str(path))as w:
     assert(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(48000,2,2,r['full_audio']['stereo_sample_frames'])
     raw=w.readframes(w.getnframes());assert digest(raw)==r['full_audio']['PCM_sha256']and any(raw)
    audio+=1
  rows=json.loads((folder/'frame-services.json').read_text());points=json.loads((folder/'checkpoints.json').read_text())
  assert sum(x['PCM_stereo_sample_frames']for x in rows)==r['full_audio']['stereo_sample_frames']
  for q in points:
   row=rows[q['frame']-1];raw=(folder/q['RAM']).read_bytes();sram=(folder/q['SRAM']).read_bytes()
   assert digest(raw)==row['RAM_sha256']and digest(sram)==row['SRAM_sha256']and fields(raw,sram)==q['fields']
   with Image.open(folder/q['image'])as im:assert digest(im.tobytes())==row['RGB_sha256']
  checks.append(dict(case=r['case'],frames=len(rows),checkpoints=len(points),RGB_matches_same_frame=True,RAM_SRAM_match_same_frame=True,PCM_size_and_hash_match=True))
 result=dict(status='passed',artifact_rehash_checks=artifacts,decoded_nonempty_RGB_images=images,decoded_WAV_files=audio,checks=checks,failed_count=0,
  scope='static artifact/field parity only; no listening verdict, no browser UI test, no internal CPUtrace',script_sha256=sha(Path(__file__)))
 write(out/'static-validation.json',result);return result

def aggregate(out,receipts):
 cases=[]
 names={'cold-city-domestic-cycle':'真实冷启动→城市→行动耗尽→内政合作AI→二月玩家返回',
  'core-reset-battery-retention':'真实冷启动到城市后原核心复位：8KiB SRAM保留与标题重建',
  'title-intro-software-restart':'无按键冷标题介绍：0B58计时后原软件E000重启'}
 for r in receipts:
  key=r['case'];rep=json.loads((out/key/'repeat-validation.json').read_text());points=json.loads((out/key/'checkpoints.json').read_text())
  cases.append(dict(case=key,title=names[key],validation=key+'/validation.json',repeat_validation=key+'/repeat-validation.json',checkpoints=key+'/checkpoints.json',
   frame_services=key+'/frame-services.json',input_plan=key+'/input-plan.json',flow_events=key+'/flow-events.json',full_WAV=key+'/full-flow.wav',
   images={p['label']:key+'/'+p['image']for p in points},frames=r['frames'],checkpoint_count=r['checkpoint_count'],final_fields=r['final_fields'],
   nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],PCM_stereo_sample_frames=r['full_audio']['stereo_sample_frames'],termination=r['termination']))
 summary=dict(native_case_count=len(receipts),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),
  checkpoint_count=sum(r['checkpoint_count']for r in receipts),nonempty_repeat_artifact_checks=sum(c['nonempty_repeat_artifact_checks']for c in cases),
  formal_JSON_repeat_checks=len(FORMAL)*len(receipts),excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),
  excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),sample_rate=48000,PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),
  additional_core_memory_writes=0,state_import_count=0,battery_file_import_count=0,fresh_process_per_run=True,source_CPU_comparisons_in_this_receipt=0,native_internal_CPU_trace=False,failed_count=0)
 raw=Path(receipts[0]['core']['core_path'])if 'core_path'in receipts[0]['core']else ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
 pins=[dict(path=relative(p),sha256=sha(p))for p in(Path(__file__),ROOT/'scripts/nes_service_runtime.py',ROOT/'scripts/nes_runtime.py',ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json',raw)]
 # Bank11 inline EADE words are separated from actual instructions. These are
 # original bytes, not a CPUtrace executed by this capture script.
 rom=Path(ROM_PATH_FOR_AGGREGATE).read_bytes();ranges=[]
 for name,start,end,kind in(('title-main4-dispatch',0xD732,0xD738,'code'),('title-main4-inline-table',0xD738,0xD73C,'data'),('title-palette-and-software-reset',0xD73C,0xD770,'code')):
  offset=16+11*8192+(start&8191);b=rom[offset:offset+end-start];ranges.append(dict(name=name,kind=kind,physical_bank=11,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(b),raw_hex=b.hex(),sha256=digest(b)))
 evidence=dict(schema='phase14-native-boot-cooperation-flows-v1',status='passed',rom_sha256=ROM_SHA,core=receipts[0]['core'],summary=summary,native_cases=cases,dependency_pins=pins,ranges=ranges)
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))))
 static=static_artifact_qa(out,receipts)
 lines=['# 第十四轮原核心：冷启动、复位与内政合作回放','',
  '三案都直接把只读原ROM载入新的锁定Nestopia核心，没有状态导入、battery文件导入或任何新增core RAM/SRAM、ready、结果、端口写入。普通按键和原libretro `retro_reset()`是唯一控制操作；恢复源码未安装进原核心。','',
  f'首跑{summary["frames_first_run"]}帧，两跑{summary["frames_both_runs"]}帧、{summary["checkpoint_count"]}检查点；{summary["nonempty_repeat_artifact_checks"]}份非空产物逐字节hash一致，含{summary["formal_JSON_repeat_checks"]}份正式JSON。另排除{summary["excluded_empty_VRAM"]}份0B VRAM和{summary["excluded_snapshot_metadata_JSON"]}份含目录路径的snapshot metadata JSON。所有256×240原RGB、RAM2048B/SRAM8192B与实际48000Hz双声道16bit PCM每帧完整hash公开，完整原WAV保留。这里原生帧不是内部CPU指令trace。','',
  '## 三案合同与终点','',
  '1. 冷启动到城市的前24步复用旧只读普通按键计划（2922帧）。原曹操初城11预备兵9999已满，所以首次原招募数量守卫保留0；游戏原同意界面仍消耗1张行动牌，然后普通分配将100现有预备兵交陈宫。后二次Up选择raw1，即100兵，各扣20金，再各给于禁100。行动预算6F05确实3→2→1→0，原队列、动画和名单提交均经原A/方向键完成。六个电脑君主依次出现6F8B请求0→完成FF，日期189年1月→2月；原A确认新玩家回合，最终global2/NMI2/city0/sub1，预算恢复3。未声称FC/FB出现在此自然样本。','',
  '2. 真冷启动城市frame2922之后直接调用原`retro_reset()`。调用本身不先写RAM或SRAM；立即读取的8192B SRAM与复位前完全相同，后续1200个真实帧后仍全部相同，189年1月与场景数据保留，RAM与画面已由原代码重新初始化到标题global10/NMI6。立即边界没有新RGB/PCM帧，故只有真实内存导出，不伪造即时reset截图。此证明同一加载实例的battery-backed SRAM复位保留；本前端没有实现进程退出/断电后的battery文件保存与重载。','',
  '3. 真冷启动无按键4000帧。原介绍计数0471:0470达到0B58（frame3063），标题main4/sub0清调色板，随后sub1的原JMP E000。frame3073观察global0，之后原标题初始化与呈现完成。该路径是介绍超时自动软件重启，不是猜测的菜单项。原JMP字节与实际字段跳转共同支撑解释；未直接采集原核心PC。','',
  '## 字段与证据范围','',
  'active_controller仅按真正global/NMI组合选择title/ruler/city/battle/attack/duel主态；其它状态数组保留为原字节，不能将inactive残余字节计成已执行场景。每帧保存日历/君主/行动预算、6F5B..62内政字段、6F8B..AB请求块、全ruler记录、palette、PPU/NMI/IRQ、text队列、bank缓存、audio RAM、3个相关武将原12B记录与城市11原32B记录。完整原RAM/SRAM只在检查点导出，每帧完整内容均hash。','',
  '原图/原WAV来自Nestopia，不是恢复源码生成。静态QA只核对PNG尺寸/模式/同帧RGBhash、RAM/SRAMhash、WAV格式/实际PCMhash与重复产物；未伪称浏览器验收或人工听音通过。硬件时序、原内部调用链和源码等价性由其它独立CPU回执承担。','']
 for c in cases:lines.extend([f'## {c["title"]}','',f'{c["frames"]}帧，{c["checkpoint_count"]}检查点。{c["termination"]}。','',
  f'- [实际按钮/复位计划]({c["input_plan"]})',f'- [逐帧原字段与四类完整hash]({c["frame_services"]})',f'- [真实检查点图像]({c["checkpoints"]})',f'- [实际完整WAV]({c["full_WAV"]})',
  f'- [观察到的预算/日历/请求/重启事件]({c["flow_events"]})',f'- [病例回执]({c["validation"]})',f'- [第二跑exact parity]({c["repeat_validation"]})',''])
 lines.extend(['```sh',"python3 scripts/capture_boot_cooperation_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat",'```','',
  '[原核心manifest](evidence.json) · [汇总回执](validation.json) · [静态产物QA](static-validation.json)','',
  '每一跑均在独立新的Python进程中创建/关闭原核心，避免复用同一动态库全局状态。所有原serialize输出buffer逐字节原样保留；没有裁去/规范化state尾部。先前同进程探索产生的序列化buffer尾4B差异已保存在探索目录，不纳入正式计数。需要重跑请指定新的输出目录；冻结产物不得覆盖。'])
 (out/'README.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(dict(status='passed',summary=summary,static_QA=static),ensure_ascii=False),flush=True)

def explore(a):
 c=Capture(a.rom,a.out)
 try:
  if a.probe=='title-loop':c.step(12000,(),'uninterrupted original cold title/intro sequence','title-loop-end')
  else:
   c.cold_city()
   if a.probe=='core-reset':c.reset();c.step(1200,(),'original post-reset initialization','reset-title')
   elif a.probe=='city-system':c.press('b',180,'return to world/city cursor','world-ready');c.press('select',180,'original Select interface','system-open')
   elif a.probe=='city-recruit':
    c.press('right',20,'select military icon');c.press('a',180,'open military menu','recruit-military-menu');c.press('right',20,'select original recruitment command');c.press('a',180,'open original recruitment officer choice','recruit-officer-choice')
    for i in range(2):c.press('down',20,'select officer with below-cap troops')
    c.press('a',180,'confirm officer for recruitment','recruit-cost-input');c.press('up',20,'increase recruitment selection by ordinary Up','recruit-cost-positive');c.press('a',900,'confirm recruitment','recruit-completed')
   elif a.probe=='city-doctor':
    for i in range(3):c.press('right',20,'select town city icon')
    c.press('a',180,'open originaltown menu','doctor-town-menu');c.press('right',20,'select next town icon');c.press('right',20,'select physician icon');c.press('a',180,'open original physician officer choice','doctor-officer-choice');c.press('a',900,'confirm original first officer','doctor-confirmed')
   elif a.probe=='city-domestic':c.press('a',180,'open originaldomestic menu','domestic-menu');c.press('a',180,'choose originalland officer','domestic-officer-choice');c.press('a',180,'confirm originalfirst officer','domestic-cost-input')
  if a.tail_plan:
   for step in json.loads(a.tail_plan.read_text()):c.step(step['frames'],step.get('buttons',()),step.get('purpose','exploratory ordinary input'),step.get('capture'))
  final=c.finish();print(json.dumps(dict(frames=c.rt.frames,final=final),ensure_ascii=False))
 finally:c.close()

def main():
 global ROM_PATH_FOR_AGGREGATE
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase14/runtime')
 p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--repeat',action='store_true')
 p.add_argument('--capture-child',action='store_true',help=argparse.SUPPRESS)
 p.add_argument('--probe',choices=('city-system','city-domestic','city-doctor','city-recruit','core-reset','title-loop'));p.add_argument('--tail-plan',type=Path);a=p.parse_args()
 assert sha(a.rom)==ROM_SHA;ROM_PATH_FOR_AGGREGATE=a.rom
 if a.probe:explore(a);return
 assert not a.tail_plan,'Exploratory extra plans require --probe'
 if a.capture_child:
  assert a.case in CASES and not a.repeat
  one=capture_case(a.rom,a.out.resolve()/a.case,a.case)
  print(json.dumps(dict(case=a.case,status='passed',frames=one['frames'],checkpoint_count=one['checkpoint_count']),ensure_ascii=False),flush=True);return
 out=a.out.resolve();receipts=[]
 for case in CASES if a.case=='all'else(a.case,):
  subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out),'--case',case,'--capture-child'],check=True)
  one=json.loads((out/case/'validation.json').read_text())
  if a.repeat:
   second=out.parent/(out.name+'-repeat')/case
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(second.parent),'--case',case,'--capture-child'],check=True)
   two=json.loads((second/'validation.json').read_text())
   checks=[dict(artifact=k,equal=expected==two['artifact_sha256'].get(k),**expected)for k,expected in one['artifact_sha256'].items()]
   assert set(one['artifact_sha256'])==set(two['artifact_sha256'])and all(x['equal']for x in checks),[x for x in checks if not x['equal']]
   assert one['frames']==two['frames']and one['final_fields']==two['final_fields']
   write(out/case/'repeat-validation.json',dict(status='passed',first_run=relative(out/case),second_run=relative(second),nonempty_artifact_checks=len(checks),all_hashes_equal=True,
    artifacts=checks,formal_JSON_exact_parity=list(FORMAL),excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=one['excluded_snapshot_metadata_JSON'],script_sha256=sha(Path(__file__))))
  receipts.append(one);print(json.dumps(dict(case=case,status='passed',frames=one['frames'],checkpoint_count=one['checkpoint_count']),ensure_ascii=False),flush=True)
 if a.repeat:aggregate(out,receipts)
if __name__=='__main__':main()
