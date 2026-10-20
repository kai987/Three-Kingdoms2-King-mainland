#!/usr/bin/env python3
"""Observe original-core player extinction after a real ordinary attack.

Only explicit pre-flow officer, roster, ownership and position data may be
prepared. Controller state, results, death/status bits, ready and ack are never
supplied. Exploratory observations are not a source-CPU or hardware trace.
"""
from pathlib import Path
import argparse,json,sys,subprocess,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from capture_succession_flows import Capture as SuccessionCapture,fields as succession_fields
from capture_campaign_flows import sha,digest,write,relative,ROM_SHA,CORE_SHA
from nes_runtime import INPUT,BUTTONS

MOTHER=ROOT/'analysis/phase16/runtime/player-defeat-successor/initial.state'
ANCESTOR=ROOT/'analysis/runtime/phase3/attack-intro-7.state'
PROBES=('owned-empty','no-owned-cities','former-leader-only','two-player-city','two-player-extinction')
CASES=('single-player-empty-rosters-reset','two-player-empty-rosters-continue','former-leader-only-candidate')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json','campaign-events.json','preparation.json','probe-outcome.json')

def fields(ram,sram):
 f=succession_fields(ram,sram)
 f.update(ending_mode_0541=ram[0x541],ending_phase_0542=ram[0x542],ending_fields_04C9_04CE=list(ram[0x4C9:0x4CF]),
  ending_animation_marker_04CB=ram[0x4CB],ending_parent_0472_0473=list(ram[0x472:0x474]),ending_substitutions_042C_0434=list(ram[0x42C:0x435]),
  succession_fields_040A_040F=list(ram[0x40A:0x410]),ending_continue_flag_6F43=sram[0xF43])
 if ram[0x7A]in(13,14)and ram[0x78]==8:
  f.update(active_controller='ending',active_main=ram[0x541],active_phase=ram[0x542])
 return f

class Capture(SuccessionCapture):
 def __init__(self,*args):
  super().__init__(*args);self.ending_seen=set();self.phase17_previous=None;self.flow_outcome={};self.player2_buttons=set()
  # The frozen older frontend emits only port0. This new callback supplies
  # actual port1 controller input, never a RAM-ready or synthetic result.
  self.player2_callback=INPUT(self.controller_input)
  self.rt.core.retro_set_input_state(self.player2_callback)
 def controller_input(self,port,device,index,ident):
  if port==1:return int(device==1 and ident in self.player2_buttons)
  return self.rt.input(port,device,index,ident)
 def press_player2(self,key,release=120,purpose='',label=None):
  self.player2_buttons={BUTTONS[key]};self.step(2,(),purpose);self.plan[-1].update(controller_port=1,buttons=[key]);self.player2_buttons=set()
  self.step(release,(),purpose+' release/observe',label);self.plan[-1]['controller_port']=1
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def observe(self,rt):
  super().observe(rt);f=fields(rt.memory(2),rt.memory(0))
  for key in ('ending_mode_0541','ending_phase_0542','ending_fields_04C9_04CE','ending_animation_marker_04CB','ending_parent_0472_0473','ending_substitutions_042C_0434','succession_fields_040A_040F','ending_continue_flag_6F43','active_controller','active_main','active_phase'):
   self.rows[-1][key]=f[key]
  if f['active_controller']=='ending':
   key=(f['global_state'],f['ending_mode_0541'],f['ending_phase_0542'],f['ending_animation_marker_04CB'])
   if key not in self.ending_seen:
    self.ending_seen.add(key);self.snap('ending-g%d-mode%d-phase%d-marker%02X'%key,'first actual ending mode/phase/marker tuple; not internal CPU trace')
  p=self.phase17_previous
  if p and p['global_state']in(13,14)and f['global_state']not in(13,14):
   self.campaign_events.append(dict(kind='original-ending-global-handoff',frame=rt.frames,before=p['global_state'],after=f['global_state'],continue_flag_before=p['ending_continue_flag_6F43']))
   self.snap('ending-handoff-g%d-frame%d'%(f['global_state'],rt.frames),'actual original ending exit, no reset or state write supplied')
  self.phase17_previous=f
 def prepare(self,mode,inherit=True):
  if inherit:
   assert MOTHER.read_bytes()==ANCESTOR.read_bytes(),'Phase16 pre-preparation mother must remain natural ancestor byteidentical'
   self.inherit(MOTHER)
  self.preparation_begin('declared-pre-fight-'+mode)
  for address,value,reason in((0x69E4,1,'player commander131 pre-fight health1; not a death or result'),(0x69E5,1,'player commander131 martial1'),(0x6421,99,'enemy commander8 martial99')):
   self.patch('SRAM',address,value,reason)
  self.patch('RAM',0x600,3,'enemy commander legal adjacent X before original attack')
  self.patch('RAM',0x614,16,'enemy commander legal adjacent Y before original attack')
  s=self.rt.memory(0);owned=[i for i in range(30)if s[32*i]&7==2]
  assert owned==[11,14],owned
  for city in owned:
   if mode=='no-owned-cities':
    self.patch('SRAM',0x6000+city*32,(s[32*city]&0xF8)|7,'controlled neutral owner low3 before battle; not an extinction result')
   else:
    for index in range(10):
     value=131 if mode=='former-leader-only'and city==11 and index==0 else 255
     self.patch('SRAM',0x6000+city*32+17+index,value,'controlled candidate roster before battle: '+('only still-living original commander131'if value==131 else'empty FF slot'))
  assert not any(p['kind']=='SRAM'and 0x63C0<=p['address']<0x6EDC and(p['address']-0x63C0)%12==11 for p in self.preparation)
  self.preparation_end()
 def defeat(self):
  self.press('right',35,'choose original ordinary attack command');self.press('a',180,'open original enemy cursor')
  self.press('right',35,'move original cursor onto adjacent enemy');self.press('a',240,'confirm original enemy')
  self.press('a',240,'confirm original ordinary attack','ordinary-attack-enter')
  for i in range(250):
   if self.current()['global_state']in(3,4):break
   self.press('a',90,'original advance/combat/message input until actual battle return','ordinary-attack-A'+str(i)if i<8 else None)
  else:raise AssertionError('actual ordinary attack exceeded250 pulses')
  self.step(90,(),'observe actual original player attack outcome','ordinary-attack-battle-return')
  f=self.current();assert f['campaign_officers']['131']['health']==255 and f['campaign_officers']['131']['status']==3,f['campaign_officers']['131']
  for i in range(40):
   f=self.current()
   if f['global_state']in(13,14)or(f['global_state']==2 and f['city_state_0400_040F'][:2]==[13,6])or(f['global_state']==2 and f['city_state_0400_040F'][:3]==[13,4,2]):break
   self.press('a',240,'original battle-loss/postbattle/succession message input','postbattle-A'+str(i)if i<12 else None)
  else:raise AssertionError('postbattle did not reach ending/no-candidate or candidate map within40 pulses')
  self.snap('postbattle-candidate-or-retirement-boundary')
 def ending(self,reactivate=False):
  for i in range(20):
   if self.current()['global_state']in(13,14):break
   self.press('a',180,'original no-candidate notice acknowledgement','retirement-A'+str(i))
  else:raise AssertionError('no-candidate route did not enter original ending')
  self.snap('loss-ending-entered');assert self.rt.memory(0)[0xF17]==255
  start=self.rt.frames
  while not(self.current()['global_state']==14 and self.current()['nmi_scene']==8 and self.current()['ending_animation_marker_04CB']==254):
   assert self.rt.frames-start<12000,('ending marker bounded wait',self.current())
   self.step(8,(),'wait for actual original ending message/animation; no readiness prepared')
  self.snap('loss-ending-ready-for-original-A');self.flow_outcome['ending_before_A']=self.current()
  if reactivate:
   self.press('b',120,'ordinary B at fully ready loss ending; original exit accepts only A','loss-ending-B-does-not-exit')
   assert self.current()['global_state']==14 and self.current()['ending_animation_marker_04CB']==254
   self.flow_outcome['ending_after_B']=self.current()
  self.press('a',900,'original A exits ready loss ending and performs original software reset or parent restore','loss-ending-after-original-A')
  self.flow_outcome['ending_after_A']=self.current()
  if reactivate:
   old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
   for item in old[1:24]:self.step(item['frames'],item.get('buttons',()),'original new-game/title plan after actual gameover software reset','reactivated-'+item['capture']if item.get('capture')else None)
   self.snap('reactivated-player-city');assert self.ready(1,1)(self.current())
  elif self.flow_outcome['ending_before_A']['ending_continue_flag_6F43']:
   assert self.current()['global_state']==2 and self.current()['ruler_6F03']==4
   self.press_player2('a',180,'actual remaining-player prompt acknowledgement by original controller2','remaining-player-world')
   self.until(self.ready(0,1),4000,'remaining-player-world-ready','wait for actual remaining-player world after original prompt')
   assert self.current()['ruler_6F03']==4 and self.current()['ending_continue_flag_6F43']==0
 def former_leader(self):
  f=self.current();assert f['global_state']==2 and f['city_state_0400_040F'][:3]==[13,4,2],f
  x,y=self.rt.memory(0)[0xF3F],self.rt.memory(0)[0xF41]
  for _ in range((abs(176-x)+7)//8):self.press('right'if x<176 else'left',35,'original candidate cursor toward ownedcity11')
  for _ in range((abs(72-y)+7)//8):self.press('down'if y<72 else'up',35,'original candidate cursor toward ownedcity11')
  self.snap('former-leader-candidate-city11');self.press('a',240,'select original city11 candidate roster','former-leader-candidate-list')
  for i in range(12):
   if self.ready(0,1)(self.current()):break
   self.press('a',240,'select and confirm actual roster131 without filtering its original defeat status','former-leader-confirm-A'+str(i))
  else:raise AssertionError('former-leader candidate did not complete12 pulses')
  self.snap('former-leader-selection-final')
 def two_player_city(self):
  old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
  for item in old[:3]:self.step(item['frames'],item.get('buttons',()),'ordinary original cold title plan',item.get('capture'))
  self.press('down',35,'choose actual title 2人プレイ option','two-player-title-option');assert self.rt.memory(2)[0x12]==1
  for item in old[3:17]:self.step(item['frames'],item.get('buttons',()),'ordinary first-player scenario/ruler plan',item.get('capture'))
  self.snap('two-player-second-prompt');assert self.rt.memory(0)[0xF43]==1
  self.press_player2('a',180,'acknowledge actual second-player ruler prompt','two-player-second-selector')
  assert self.rt.memory(2)[0x12]==0
  self.snap('two-player-second-ruler-cursor');self.press_player2('a',180,'choose actual second-player default ruler4/officer222','two-player-second-ruler-selected')
  self.press_player2('a',600,'confirm actual two-player game start','two-player-map-ready')
  for item in old[18:24]:self.step(item['frames'],item.get('buttons',()),'ordinary city-panel/cursor/icon plan',item.get('capture'))
  self.snap('two-player-city-ready');assert self.ready(1,1)(self.current())
  assert self.rt.memory(0)[0xF43]==1 and self.rt.memory(0)[0xF1A]==0 and self.rt.memory(0)[0xF2A]==1
 def probe(self,mode,reactivate=False):
  if mode.startswith('two-player'):
   self.two_player_city()
   if mode=='two-player-extinction':
    old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
    for item in old[24:74]:self.step(item['frames'],item.get('buttons',()),'ordinary first-player invasion/army/supply plan',item.get('capture'))
    self.prepare('owned-empty',False);self.defeat();self.ending(False)
  else:
   self.prepare(mode);self.defeat()
   if mode=='former-leader-only':self.former_leader()
   else:self.ending(reactivate)
  self.flow_outcome['final']=self.current();self.finish_campaign()
  write(self.out/'probe-outcome.json',dict(mode=mode,frames=self.rt.frames,points=len(self.points),writes=len(self.preparation),flow=self.flow_outcome,
   source_CPU_comparisons=0,native_internal_CPU_trace=False,script_sha256=sha(Path(__file__))))
  return self.flow_outcome

def capture_case(rom,out,case):
 c=Capture(rom,Path(out)/case)
 try:
  mode={'single-player-empty-rosters-reset':'owned-empty','two-player-empty-rosters-continue':'two-player-extinction','former-leader-only-candidate':'former-leader-only'}[case]
  c.probe(mode,case=='single-player-empty-rosters-reset');f=c.current()
  assert len(c.preparation)==11 and len(c.preparation_groups)==1
  assert len(c.rows)==c.rt.frames and any(r['PCM_nonzero']for r in c.rows)
  deaths=[e for e in c.campaign_events if e['kind']=='original-record-status3-observed'and e['officer_id']==131]
  assert len(deaths)==1 and deaths[0]['record']['health']==255
  verified=dict(actual_original_ordinary_attack=True,original_defeat_record=deaths[0]['record'],original_defeat_frame=deaths[0]['frame'],
   health_FF_preserved_not_normalized=True,all30_final_city_owners=f['city_owners'],all30_final_city_rosters=f['city_rosters'],all7_final_rulers=f['rulers'],
   original_ending_global_handoffs=[e for e in c.campaign_events if e['kind']=='original-ending-global-handoff'],final_controller=[f['global_state'],f['nmi_scene'],f['active_main'],f['active_phase']],
   controller2_button_pulses=sum(p.get('controller_port')==1 and bool(p['buttons'])for p in c.plan),ending_observed=bool(c.ending_seen))
  if case=='former-leader-only-candidate':
   assert f['global_state']==2 and f['city_state_0400_040F'][:2]==[0,1]and f['rulers'][2]['ID']==131
   assert f['campaign_officers']['131']['health']==255 and f['campaign_officers']['131']['status']==3 and not c.ending_seen
   verified.update(original_candidate_city11_accepted=True,original_candidate_officer131_accepted=True,candidate_health_status_not_filtered=True,
    prepared_city11_roster=[131]+[255]*9,prepared_city14_roster=[255]*10,leader_after=131,leader_record_after=f['campaign_officers']['131'])
   termination='Disclosed natural battle mother; only live131 remains in ownedcity11 before combat. Original ordinaryattack producesHPFF/status3, original city/officer/confirm menus accept131 again and returncity0/1 without ending.'
  else:
   before=c.flow_outcome['ending_before_A'];after=c.flow_outcome['ending_after_A']
   assert before['global_state']==14 and before['nmi_scene']==8 and before['ending_mode_0541']==0 and before['ending_animation_marker_04CB']==254
   assert before['rulers'][2]['ID']==255 and before['city_owners'][11]==before['city_owners'][14]==2
   assert before['city_rosters'][11]==before['city_rosters'][14]==[255]*10
   verified.update(original_owned_empty_rosters_no_candidate=True,leader_before_ending=255,ending_mode=0,original_ready_marker_FE=True,
    owners_before_ending_A=before['city_owners'],rosters_before_ending_A=before['city_rosters'],ending_continue_flag_before_A=before['ending_continue_flag_6F43'],
    actual_ending_after_A_controller=[after['global_state'],after['nmi_scene'],after['active_main'],after['active_phase']],ending_parent_before_A=before['ending_parent_0472_0473'])
   if case=='single-player-empty-rosters-reset':
    assert before['ending_continue_flag_6F43']==0 and any(r['global_state']==0 for r in c.rows)
    assert after['global_state']==10 and after['nmi_scene']==6 and f['city_state_0400_040F'][:2]==[1,1]and f['rulers'][2]['ID']==131
    verified.update(original_B_does_not_exit=True,original_A_software_reset=True,actual_title_return=True,actual_new_game_reactivated=True,
     reactivated_player_ruler=2,reactivated_leader=131,reset_via_frontend=False)
    termination='Disclosed natural battle mother; empty ownedcity11/14 rosters and numeric combat preparation. Real defeat→leaderFF→lossending0; B waits, original A software-resets throughglobal0/title, original new-game inputs reinitialize scenario and returnplayercity1/1.'
   else:
    assert c.mother is None and before['ending_continue_flag_6F43']==1
    assert verified['original_ending_global_handoffs'][0]['after']==1 and f['rulers'][2]['ID']==255
    assert f['city_state_0400_040F'][:2]==[0,1]and f['ruler_6F03']==4 and f['ending_continue_flag_6F43']==0
    assert f['rulers'][4]['raw'][6:8]=='01'
    verified.update(actual_cold_title_two_player_selection=True,two_player_flag_generated_by_original_title=True,flag_not_prepared=True,
     first_player_ruler=2,second_player_ruler=4,second_player_leader=222,original_A_parent_restore=True,original_A_clears_continue_flag=True,
     remaining_player_original_prompt_acknowledged=True,remaining_player_world_ready=True,software_reset_after_loss=False)
    termination='True original coldboot/title2-player selection, port1 default secondruler4 and ordinary firstplayer invasion/army/supply; then11 combat/roster preparations. Actual defeat→lossending0, A clears original6F43=1 and restoresglobal1 parent; original controller2 acknowledges remainingruler4 prompt and returnscity0/1.'
  artifacts={};empty=[]
  for p in sorted(c.out.iterdir()):
   if not p.stat().st_size:empty.append(p.name);continue
   if p.suffix in('.png','.bin','.state','.wav')or p.name in FORMAL:artifacts[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
  groups=[]
  for original in c.preparation_groups:
   g=dict(original)
   for key in('before','after'):g[key]={k:dict(path=p,bytes=(c.out/p).stat().st_size,sha256=sha(c.out/p))for k,p in g[key].items()}
   groups.append(g)
  inherited=dict(controlled_fixture=False,inherited_preparation_byte_writes=0,applied_in_this_run=False,
   scope='Natural Phase3 battle copied into Phase16 initial.state before that earlier case applied5preparedbytes; exact whole mother bytes checked.'if c.mother else'True fresh coldboot; no state or battery file imported.')
  if c.mother:inherited.update(ancestor_state=relative(ANCESTOR),ancestor_state_sha256=sha(ANCESTOR),whole_mother_equal_to_natural_ancestor=True,
   documented_parent_validation='analysis/phase16/runtime/player-defeat-successor/validation.json',documented_parent_validation_sha256=sha(ROOT/'analysis/phase16/runtime/player-defeat-successor/validation.json'))
  receipt=dict(schema='phase17-native-player-extinction-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,
   cold_boot=c.mother is None,state_imported=c.mother is not None,mother_state=relative(c.mother)if c.mother else None,mother_sha256=sha(c.mother)if c.mother else None,
   inherited_context=inherited,controlled_fixture=True,natural_gameplay=False,battery_file_imported=False,fresh_process_per_run=True,
   additional_core_memory_writes=len(c.preparation),additional_core_memory_writes_after_declared_preparation=0,additional_ready_or_result_injections=0,
   death_or_status_bit_preparation=False,selected_tactic_result_request_cache_animation_ack_injection=False,frontend_reset_calls=0,
   preparation=c.preparation,preparation_groups=groups,core=c.rt.info,AV=c.rt.av_info,frames=c.rt.frames,checkpoint_count=len(c.points),input_step_count=len(c.plan),
   termination=termination,final_fields=f,campaign_events=c.campaign_events,verified_effects=verified,initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),
   script_sha256=sha(Path(__file__)),capture_base_sha256=sha(ROOT/'scripts/capture_succession_flows.py'),campaign_capture_base_sha256=sha(ROOT/'scripts/capture_campaign_flows.py'),
   original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),full_audio=c.wav,
   all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,
   artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   limits=['All three cases use explicit abnormal pre-fight roster/combat preparation; these are not claims of naturally reachable extinction campaigns.',
    'Native frame-end RGB/PCM/fields are originalcore observations, not internalCPUtrace, pure-source execution or synthesized audio.',
    'OriginalHPFF/status3 is kept literally; this defeat record is not normalized toHP0 or asserted as physical death.',
    'LeaderFF alone does not clear or neutralize owned cities. Before ending exit, emptycities11/14 remainowner2.',
    'The title2-player setting is produced by original port0/port1 buttons. It is not a live surviving-player count and no6F43byte is prepared.',
    'Whole originalserializedstatebuffers are unnormalized; every repeat is a fresh Python process.0BVRAM and pathmetadataJSON are excluded.'])
  write(c.out/'validation.json',receipt);return receipt
 finally:c.close()

def static_qa(out,receipts):
 out=Path(out);artifact_count=image_count=wav_count=preparation_count=frame_count=callback_count=0
 for r in receipts:
  folder=out/r['case'];rows=json.loads((folder/'frame-services.json').read_text());points=json.loads((folder/'checkpoints.json').read_text())
  assert len(rows)==r['frames']and [x['frame']for x in rows]==list(range(1,r['frames']+1))
  for name,expected in r['artifact_sha256'].items():
   p=folder/name;assert p.stat().st_size==expected['bytes']and sha(p)==expected['sha256'];artifact_count+=1
  for p in points:
   row=rows[p['frame']-1]
   with Image.open(folder/p['image'])as im:
    assert im.size==(256,240)and digest(im.convert('RGB').tobytes())==row['RGB_sha256'];image_count+=1
   for kind,key in(('RAM','RAM_sha256'),('SRAM','SRAM_sha256')):assert sha(folder/p[kind])==row[key]
  with wave.open(str(folder/'full-flow.wav'),'rb')as w:
   assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000);pcm=w.readframes(w.getnframes());assert digest(pcm)==r['full_audio']['PCM_sha256'];wav_count+=1
  start=0
  for row in rows:
   stop=row['PCM_stop_byte'];segment=pcm[start:stop]
   assert digest(segment)==row['PCM_sha256']and len(segment)//4==row['PCM_stereo_sample_frames'];start=stop;frame_count+=1
  assert start==len(pcm)
  start=0
  for event in json.loads((folder/'audio-callbacks.json').read_text()):
   stop=start+event['stereo_sample_frames']*4;assert digest(pcm[start:stop])==event['pcm_sha256'];start=stop;callback_count+=1
  assert start==len(pcm)
  for g in r['preparation_groups']:
   for kind,base,size in(('RAM',0,2048),('SRAM',0x6000,8192)):
    before=bytearray((folder/g['before'][kind]['path']).read_bytes());after=(folder/g['after'][kind]['path']).read_bytes();assert len(before)==len(after)==size
    for p in g['writes']:
     if p['kind']!=kind:continue
     offset=p['address']-base;assert before[offset]==p['before'];before[offset]=p['after']
     assert kind=='RAM'and p['address']in(0x600,0x614)or kind=='SRAM'and(p['address']in(0x69E4,0x69E5,0x6421)or any(0x6000+city*32+17<=p['address']<0x6000+city*32+27 for city in(11,14)))
    assert bytes(before)==after
   preparation_count+=1
 result=dict(schema='phase17-native-static-v1',status='passed',nonempty_artifact_rehash_checks=artifact_count,decoded_same_frame_PNG_RGB_RAM_SRAM=image_count,
  decoded_48k_stereo_WAV=wav_count,frame_PCM_segment_checks=frame_count,audio_callback_segment_checks=callback_count,preparation_full_dump_reconstruction_checks=preparation_count,
  failed_count=0,source_CPU_comparisons=0,browser_or_listening_acceptance=False,script_sha256=sha(Path(__file__)))
 write(out/'static-validation.json',result);return result

def aggregate(out,receipts):
 out=Path(out);qa=static_qa(out,receipts)
 titles={'single-player-empty-rosters-reset':'单人无候选：原败亡结局→软件重启→重新开局','two-player-empty-rosters-continue':'真实双人开局：原败亡结局→另一玩家继续','former-leader-only-candidate':'资格对照：实际败北后的曹操仍被原名单接受'}
 cases=[];repeat_count=formal_count=0
 for r in receipts:
  name=r['case'];repeat=json.loads((out/name/'repeat-validation.json').read_text());assert repeat['status']=='passed'and repeat['all_hashes_equal']
  repeat_count+=repeat['nonempty_artifact_checks'];formal_count+=len(repeat['formal_JSON_exact_parity'])
  points=json.loads((out/name/'checkpoints.json').read_text())
  cases.append(dict(case=name,title=titles[name],validation=name+'/validation.json',repeat_validation=name+'/repeat-validation.json',checkpoints=name+'/checkpoints.json',frame_services=name+'/frame-services.json',
   input_plan=name+'/input-plan.json',preparation=name+'/preparation.json',campaign_events=name+'/campaign-events.json',full_WAV=name+'/full-flow.wav',images={p['label']:name+'/'+p['image']for p in points},
   frames=r['frames'],checkpoint_count=r['checkpoint_count'],cold_boot=r['cold_boot'],state_imported=r['state_imported'],mother_state=r['mother_state'],mother_sha256=r['mother_sha256'],
   inherited_context=r['inherited_context'],additional_core_memory_writes=r['additional_core_memory_writes'],preparation_groups=r['preparation_groups'],verified_effects=r['verified_effects'],final_fields=r['final_fields'],termination=r['termination']))
 summary=dict(case_count=len(receipts),cold_boot_cases=sum(r['cold_boot']for r in receipts),state_imports=sum(r['state_imported']for r in receipts),
  original_core_frames_first_run=sum(r['frames']for r in receipts),original_core_frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
  nonempty_artifacts_double_run_hash_checks=repeat_count,formal_JSON_exact_parity=formal_count,whole_serialized_buffers_exact=True,
  excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),
  actual_original_full_WAV_files=len(receipts),sample_rate=48000,PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),
  additional_core_memory_writes=sum(r['additional_core_memory_writes']for r in receipts),inherited_preparation_byte_writes=0,additional_ready_or_result_injections=0,frontend_reset_calls=0,
  source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,failed_count=0)
 pins=[ROOT/'scripts/capture_player_extinction.py',ROOT/'scripts/capture_succession_flows.py',ROOT/'scripts/capture_campaign_flows.py',ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'.toolchain/nestopia/nestopia_libretro.dylib',MOTHER,ANCESTOR,ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json',ROOT/'analysis/phase16/runtime/player-defeat-successor/validation.json']
 e=dict(schema='phase17-native-player-extinction-flows-v1',status='passed',rom_sha256=ROM_SHA,summary=summary,native_cases=cases,core=receipts[0]['core'],
  dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in pins],Native_scope='Original Nestopia RGB/48kPCM/frame fields and unnormalized serialized buffers; sourceCPU validation is separate.')
 write(out/'evidence.json',e);write(out/'validation.json',dict(schema=e['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))))
 lines=['# 原玩家败亡与结局退出：三案双跑','',
  '三案均运行只读原ROM和固定Nestopia。恢复源码没有安装进核心，帧字段不等于CPU内部trace，原WAV也不是Python源码合成。每次重复都用新Python进程；整份序列化buffer不截断、不归一化。','',
  '单人和名单资格案加载Phase16玩家案的initial.state，该档是战前、准备之前的自然Phase3母档全文复制；whole bytes已断言相同，所以未继承Phase16后来5byte准备。双人案从真实coldboot、标题2人プレイ、原两只手柄、君主选择、出征、军队与补给完整开始，没有state/battery导入。三案都在实际普通攻击前声明11byte数值/名册准备，不冒称自然完整灭亡战役。','',
  '准备共同5byte：曹操131体力1、武力1，敌袁绍8武力99，敌slot0 X3/Y16相邻。空名单案清城11与14完整10槽，只有原6个非FF名单字节实际改变，owner保持2。资格案则城11首槽原5→仍活着的131，其余槽FF；曹操低2状态没有准备，后来HPFF/status3由真实原普通攻击产生。全部准备前后2048B RAM/8192B SRAM dump已逐byte重建；后续没有新增核心memorywrite、按钮之外的ready/ack/result/status/controller注入。','',
  '原BE2E只看所属city.owner低3和名单首槽是否FF，不筛候选体力/status/byte5。空名册→原city13/6 C386仅写leaderFF，再原文字完成与按键进入global13、原NMI8 loss模式0。结局动画04CB=FE后，单人B不能退出，A由原D752跳E000，实见global0→标题→原newgame重新初始化回城。该环节的场景重新初始化不能说成战后自动复活或城市中立。','',
  '双人设置6F43=1由原title和ruler初始化产生，第二手柄普通输入逐步记录controller_port=1。败亡结局A清该flag并global14→1恢复0472/73父流程，随后原第二玩家提示、手柄2 A和city0/1；它不是实时活玩家计数，未准备此flag。空城11/14在结局A之前仍owner2/空名单。名单仅曹操案原菜单确实接受HPFF/status3的131并回city0/1，没有ending；这是受控异常数据对照，不能称健康继任者或自然可达。','',
  f"正式总计：{summary['original_core_frames_first_run']}首跑帧／{summary['original_core_frames_both_runs']}两跑帧；{summary['checkpoint_count']}检查点；{repeat_count}非空artifact原样hash相等（含{formal_count}正式JSON）；{len(receipts)}整份48kHz双声道16bit WAV；{summary['additional_core_memory_writes']}准备byte写／0继承准备。{summary['excluded_empty_VRAM']}个0B VRAM及同数路径metadata JSON明确排除。",'',
  '[正式总证据](evidence.json) · [总回执](validation.json) · [静态图像／WAV／准备审计](static-validation.json) · [脚本](../../../scripts/capture_player_extinction.py)','']
 for case in cases:
  lines.extend(['## '+case['title'],'',f"{case['frames']}帧，{case['checkpoint_count']}检查点，{case['additional_core_memory_writes']}战前byte准备。",'',
   f"[回执]({case['validation']}) · [双跑全文hash]({case['repeat_validation']}) · [原检查点]({case['checkpoints']}) · [每帧字段]({case['frame_services']}) · [原手柄输入]({case['input_plan']}) · [准备全文dump]({case['preparation']}) · [原WAV]({case['full_WAV']})",''])
 (out/'README.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(dict(status='passed',summary=summary,static_QA=qa),ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase17/runtime');p.add_argument('--probe',choices=PROBES);p.add_argument('--reactivate',action='store_true');p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--capture-child',action='store_true',help=argparse.SUPPRESS);p.add_argument('--repeat',action='store_true');a=p.parse_args()
 if a.probe:
  c=Capture(a.rom,a.out)
  try:
   result=c.probe(a.probe,a.reactivate);f=result['final'];print(json.dumps(dict(status='observed',mode=a.probe,frames=c.rt.frames,checkpoints=len(c.points),writes=len(c.preparation),endpoint={k:f[k]for k in('global_state','nmi_scene','city_state_0400_040F','rulers','city_owners','ending_continue_flag_6F43')},ending_observed=bool(c.ending_seen)),ensure_ascii=False),flush=True)
  finally:c.close()
  return
 if a.capture_child:
  r=capture_case(a.rom,a.out,a.case);print(json.dumps(dict(status='passed',case=a.case,frames=r['frames'],checkpoints=r['checkpoint_count'],writes=r['additional_core_memory_writes']),ensure_ascii=False),flush=True);return
 out=a.out.resolve();receipts=[]
 for case in CASES if a.case=='all'else(a.case,):
  subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out),'--case',case,'--capture-child'],check=True);one=json.loads((out/case/'validation.json').read_text())
  if a.repeat:
   second=out.parent/(out.name+'-repeat')/case
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(second.parent),'--case',case,'--capture-child'],check=True);two=json.loads((second/'validation.json').read_text())
   checks=[dict(artifact=k,equal=v==two['artifact_sha256'].get(k),**v)for k,v in one['artifact_sha256'].items()]
   assert set(one['artifact_sha256'])==set(two['artifact_sha256'])and all(x['equal']for x in checks),[x for x in checks if not x['equal']]
   assert one['frames']==two['frames']and one['verified_effects']==two['verified_effects']and one['final_fields']==two['final_fields']
   write(out/case/'repeat-validation.json',dict(status='passed',first_run=relative(out/case),second_run=relative(second),all_hashes_equal=True,whole_serialized_buffers_exact=True,nonempty_artifact_checks=len(checks),artifacts=checks,
    formal_JSON_exact_parity=list(FORMAL),excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=one['excluded_snapshot_metadata_JSON'],script_sha256=sha(Path(__file__))))
  receipts.append(one)
 if a.repeat:aggregate(out,receipts)
if __name__=='__main__':main()
