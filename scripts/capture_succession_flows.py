#!/usr/bin/env python3
"""Original-core postbattle succession continuations; older artifacts immutable.

New writes, if any, are explicit pre-flow numeric fixtures. No result,
controller state, request, readiness, acknowledgement or death flag is injected.
"""
from pathlib import Path
import argparse,json,sys,ctypes as C,subprocess,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from capture_campaign_flows import Capture as CampaignCapture,fields as campaign_fields,sha,digest,write,relative,ROM_SHA,CORE_SHA
CASES=('heir-city13-month','no-heir-city13-month','player-defeat-successor','affinity-pages')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json','campaign-events.json','preparation.json')

def fields(ram,sram):
 f=campaign_fields(ram,sram)
 f.update(all30_city_records_raw32=sram[:960].hex(),all237_officer_status_low2=[sram[0x3C0+12*i+11]&3 for i in range(237)],
  all237_officer_byte5_raw=[sram[0x3C0+12*i+5]for i in range(237)],all30_city_byte27=[sram[32*i+27]for i in range(30)],all30_city_byte1=[sram[32*i+1]for i in range(30)],
  all30_city_bytes28_31=[sram[32*i+28:32*i+32].hex()for i in range(30)],UI_row_040D=ram[0x40D],UI_main_040C=ram[0x40C],UI_officer_0410=ram[0x410],UI_packet_0380_03BF=ram[0x380:0x3C0].hex())
 return f

class Capture(CampaignCapture):
 def __init__(self,*args):super().__init__(*args);self.phase16_previous=None
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def inherit(self,mother):
  super().inherit(mother)
  self.deaths={ID for ID,r in self.current()['campaign_officers'].items()if r['status']==3}
  self.campaign_events.append(dict(kind='inherited-status3-not-new-death',frame=0,officer_ids=sorted(int(ID)for ID in self.deaths)))
 def observe(self,rt):
  super().observe(rt);extra=fields(rt.memory(2),rt.memory(0))
  for key in ('all30_city_records_raw32','all237_officer_status_low2','all237_officer_byte5_raw','all30_city_byte27','all30_city_byte1','all30_city_bytes28_31','UI_row_040D','UI_main_040C','UI_officer_0410','UI_packet_0380_03BF'):self.rows[-1][key]=extra[key]
  if self.phase16_previous is not None:
   previous=self.phase16_previous
   for i,(before,after)in enumerate(zip(previous['rulers'],extra['rulers'])):
    if before['ID']!=after['ID']:
     self.campaign_events.append(dict(kind='original-frame-ruler-ID-change',frame=rt.frames,ruler=i,before=before['ID'],after=after['ID']));self.snap(f'ruler{i}-ID{after["ID"]}-frame{rt.frames}','actual frame-end leader writeback; not internal CPUtrace')
   for city,(before,after)in enumerate(zip(previous['city_owners'],extra['city_owners'])):
    if before!=after:
     self.campaign_events.append(dict(kind='original-frame-city-owner-change',frame=rt.frames,city=city,before=before,after=after));self.snap(f'city{city}-owner{after}-frame{rt.frames}','actual city owner low3 change, not attributed to unobserved internal callee')
  self.phase16_previous=extra
 def consume_postbattle(self,heir):
  parent=ROOT/'analysis/phase15/runtime'/('succession-heir'if heir else'succession-no-heir')/'observed-g02-n02-city-013-000.state'
  self.inherit(parent);self.step(90,(),'execute original city13 AD81 setup from actual phase15 battle-return mother','actual-city13-consumer-open')
  for i in range(12):
   if self.ready(0,1)(self.current()):break
   self.press('a',240,'ordinary original city13 result/inheritance confirmation',f'city13-A{i}')
  else:raise AssertionError('city13 did not return within12 original A pulses')
  assert self.rt.memory(0)[0xF0F]==(9 if heir else 255)
  self.snap('actual-city13-consumer-return');self.campaign_events.append(dict(kind='original-city13-consumer-ruler-writeback',frame=self.rt.frames,ruler1=self.current()['rulers'][1],heir_fixture=heir))
 def follow_month(self,heir,count=1,consume=False):
  if consume:self.consume_postbattle(heir)
  else:
   parent=ROOT/'analysis/phase15/runtime'/('succession-heir'if heir else'succession-no-heir')/'final.state'
   self.inherit(parent);self.step(90,(),'observe unchanged inherited actual postbattle city','inherited-postbattle-city')
  start=self.current()['calendar_year_6F00']*12+self.current()['calendar_month_zero_based_6F01'];ordinal=0
  while self.current()['calendar_year_6F00']*12+self.current()['calendar_month_zero_based_6F01']-start<count:
   before=self.current()['calendar_year_6F00']*12+self.current()['calendar_month_zero_based_6F01'];budget=self.current()['remaining_budget_raw_6F05']
   for _ in range(budget):ordinal+=1;self.recruitment(ordinal)
   self.next_player_message('next-month-player-message-'+str(before-start+1));self.press_ready('a',0,1,'next-month-player-world-'+str(before-start+1))
   f=self.current();assert f['calendar_year_6F00']*12+f['calendar_month_zero_based_6F01']==before+1
   self.campaign_events.append(dict(kind='original-post-succession-month-return',frame=self.rt.frames,calendar=f['calendar_and_turn_6F00_6F06'],ruler1=f['rulers'][1],city_owners=f['city_owners']))
  self.snap('post-succession-month-final')
 def player_failure(self):
  self.inherit(ROOT/'analysis/runtime/phase3/attack-intro-7.state');self.preparation_begin('controlled-player-failure-preparation')
  for address,value,reason in((0x63C0+131*12,1,'controlled pre-fight player commander health1; death/status/results not prepared'),(0x63C0+131*12+1,1,'controlled player martial1'),(0x63C0+8*12+1,99,'controlled enemy martial99')):self.patch('SRAM',address,value,reason)
  self.patch('RAM',0x600,3,'controlled enemy commander adjacent X for original attack target');self.patch('RAM',0x614,16,'controlled enemy adjacent legal Y');self.preparation_end()
  self.press('right',35,'choose original ordinary attack command');self.press('a',180,'open original enemy cursor');self.press('right',35,'move original cursor onto adjacent enemy');self.press('a',240,'confirm enemy');self.press('a',240,'confirm original ordinary attack','player-failure-attack-enter')
  for i in range(250):
   r=self.rt.memory(2)
   if r[0x7A]in(3,4):break
   self.press('a',90,'original advance/combat/message input until actual battle return',f'player-failure-A{i}'if i<8 else None)
  else:raise AssertionError('player failure battle scene exceeded250 pulses')
  self.step(90,(),'observe actual player attack outcome','player-failure-battle-return')
  for i in range(40):
   f=self.current()
   if f['global_state']in(9,10,13,14)or(f['global_state']==2 and f['active_main']==0 and f['active_phase']==1)or(f['global_state']==2 and f['city_state_0400_040F'][:3]==[13,4,2]):break
   self.press('a',240,'ordinary actual loss/leader-return/inheritance/result input',f'player-loss-A{i}'if i<12 else None)
  f=self.current()
  if f['global_state']==2 and f['city_state_0400_040F'][:3]==[13,4,2]:
   self.snap('player-successor-city-cursor-open')
   # C708 tests low-byte coordinates against the original30-city table.
   # City11 rectangle starts176,72; ordinary cursor moves8 pixels.
   s=self.rt.memory(0);x,y=s[0xF3F],s[0xF41]
   for _ in range((abs(176-x)+7)//8):self.press('right'if x<176 else'left',35,'move actual successor city cursor toward ownedcity11')
   for _ in range((abs(72-y)+7)//8):self.press('down'if y<72 else'up',35,'move actual successor city cursor toward ownedcity11')
   self.snap('player-successor-city11-cursor');self.press('a',240,'select actual ownedcity11','player-successor-city-selected')
   for i in range(12):
    if self.ready(0,1)(self.current()):break
    self.press('a',240,'select original first eligible officer and confirm new player ruler',f'player-successor-A{i}')
   else:raise AssertionError('original player successor selection exceeded12pulses')
   assert self.rt.memory(0)[0xF17]==5
  self.snap('player-failure-final');self.campaign_events.append(dict(kind='original-player-loss-endpoint',frame=self.rt.frames,global_state=self.current()['global_state'],rulers=self.current()['rulers'],player_record=self.current()['campaign_officers']['131']))
 def trait_pages(self):
  self.inherit(ROOT/'analysis/phase12/runtime/battle-officer-info/initial.state');self.step(30,(),'settle inherited natural battle cursor','trait-before-open')
  address=0x63C0+131*12+11;original=self.rt.memory(0)[address-0x6000]
  for code in range(4):
   self.preparation_begin('trait-code'+str(code));self.patch('SRAM',address,(original&~12)|(code<<2),'controlled raw affinity bits only; original tier/status retained; code3 has no official fourth name');self.preparation_end()
   self.press('b',240,'open original full officer-information renderer',f'trait-code{code}-info-open')
   r=self.rt.memory(2);assert list(r[0x500:0x502])==[1,1]and r[0x40D]==255 and r[0x410]==131
   raw=self.rt.memory(0)[address-0x6000];assert raw&~12==original&~12 and(raw>>2)&3==code
   self.campaign_events.append(dict(kind='original-affinity-information-page',frame=self.rt.frames,code=code,packed_byte11=raw,officer_id=131,UI_row_040D=255,official_name={0:'平',1:'山',2:'水'}.get(code),code3_is_unofficial_out_of_table=code==3))
   self.press('a',240,'close actual officer page and return to battlefield cursor',f'trait-code{code}-info-closed');assert list(self.rt.memory(2)[0x500:0x502])==[0,2]
 def finish_campaign(self):
  result=super().finish_campaign();p=self.out/'exploration-summary.json';s=json.loads(p.read_text());s['script_sha256']=sha(Path(__file__));s['capture_base_sha256']=sha(ROOT/'scripts/capture_campaign_flows.py');write(p,s);return result

def inherited_context(c,case):
 if case in('heir-city13-month','no-heir-city13-month'):
  p=ROOT/'analysis/phase15/runtime'/('succession-heir'if case=='heir-city13-month'else'succession-no-heir')/'validation.json';r=json.loads(p.read_text())
  return dict(validation=relative(p),validation_sha256=sha(p),controlled_fixture=True,inherited_preparation_byte_writes=r['additional_core_memory_writes'],preparation=r['preparation'],applied_in_this_run=False,
   scope='Mother is the actual phase15 city13/0 after four original trap kills, before ruler writeback; the original19/26 pre-combat preparations are inherited, not newly applied.')
 p=ROOT/'analysis/phase12/runtime/battle-officer-info/validation.json'if case=='affinity-pages'else ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json'
 return dict(validation=relative(p),validation_sha256=sha(p),controlled_fixture=False,inherited_preparation_byte_writes=0,preparation=[],applied_in_this_run=False,scope='Disclosed original natural battle mother; only the new preparation groups below are applied in this run.')

def capture_case(rom,out,case):
 c=Capture(rom,out/case)
 try:
  if case in('heir-city13-month','no-heir-city13-month'):
   heir=case=='heir-city13-month';c.follow_month(heir,1,True);f=c.current();assert f['calendar_and_turn_6F00_6F06']==[89,1,0,2,1,3,1]
   assert f['rulers'][1]['ID']==(9 if heir else 255)
   ai_rulers=sorted({r['ruler_6F03']for r in c.rows if r['global_state']==2 and r['active_controller']=='city'and r['active_main']==9})
   assert ai_rulers==([0,1,3,4,5,6]if heir else[0,3,4,5,6])
   if not heir:assert f['city_owners'][1]==f['city_owners'][3]==1 and all(ID==255 for city in(1,3)for ID in f['city_rosters'][city])
   verified=dict(actual_city13_consumer=True,actual_ruler1_before=8,actual_ruler1_after=f['rulers'][1]['ID'],AI_rulers_observed=ai_rulers,calendar_before=[89,0],calendar_after=[89,1],city1_owner=f['city_owners'][1],city3_owner=f['city_owners'][3],city1_roster=f['city_rosters'][1],city3_roster=f['city_rosters'][3],
    all30_final_city_owners=f['city_owners'],all30_final_city_rosters=f['city_rosters'],final_status0_officers=[dict(ID=i,byte5=f['all237_officer_byte5_raw'][i])for i,v in enumerate(f['all237_officer_status_low2'])if v==0],intermediate_FC_FB_ack1_observed=False)
   termination='Actual inherited battle return enters originalcity13, writes successor9 or absent leaderFF, then ordinary two command cards and complete monthly rotation return toFebruary player; all30 owners/rosters and237status/byte5 retained'
  elif case=='player-defeat-successor':
   c.player_failure();f=c.current();assert f['global_state']==2 and f['city_state_0400_040F'][:2]==[0,1]and f['rulers'][2]['ID']==5
   assert f['campaign_officers']['131']['health']==255 and f['campaign_officers']['131']['status']==3
   verified=dict(actual_original_attack=True,player_record_131_after=f['campaign_officers']['131'],health_FF_preserved_not_normalized=True,player_ruler_before=131,player_ruler_after=5,chosen_owned_city=11,original_city13_phase4_player_selection=True,
    final_city11_roster=f['city_rosters'][11],all30_final_city_owners=f['city_owners'],all30_final_city_rosters=f['city_rosters'],final_controller=[f['global_state'],f['nmi_scene'],f['active_main'],f['active_phase']])
   termination='Controlled pre-fightHP/martial/adjacent-position data; actual ordinaryattack defeat writes original曹操HPFF/status3; originalcity13/phase4 mapcity11/officer5/confirmation returns toplayercity0/1'
  else:
   c.trait_pages();f=c.current();events=[e for e in c.campaign_events if e['kind']=='original-affinity-information-page'];assert [e['code']for e in events]==[0,1,2,3]
   assert [e['packed_byte11']for e in events]==[18,22,26,30]
   crops=[]
   for code in range(4):
    name=f'trait-code{code}-info-open.png'
    with Image.open(c.out/name)as im:region=im.crop((64,192,80,208));rgb=digest(region.tobytes())
    crops.append(dict(code=code,checkpoint=f'trait-code{code}-info-open',PNG=name,PNG_sha256=sha(c.out/name),box=[64,192,80,208],width=16,height=16,RGB_sha256=rgb))
   assert len({x['RGB_sha256']for x in crops})==4
   verified=dict(actual_four_original_information_open_close_cycles=True,officer_id=131,flags11_address=0x69EF,packed_values=[18,22,26,30],tier_and_status_preserved=True,affinity_glyph_regions=crops,
    official_codes={'0':'平','1':'山','2':'水'},code3_official_name=None,code3_out_of_table_bytes_top=[0xA0,0x0B],code3_out_of_table_bytes_bottom=[0x4A,0x4A],
    final_battle_state=f['battle_state_0500_050F'][:2],actual_completed_pages_row040D=255)
   termination='Natural inherited battle cursor; only officer131 flags11 mid2 are prepared, four actual full information pages redraw and originalA closes; code3 produces out-of-table machinecode glyphs, not a fourth official ability'
  c.finish_campaign();assert len(c.rows)==c.rt.frames and any(r['PCM_nonzero']for r in c.rows)
  artifacts={};empty=[]
  for path in sorted(c.out.iterdir()):
   if path.stat().st_size==0:empty.append(path.name);continue
   if path.suffix in('.png','.bin','.state','.wav')or path.name in FORMAL:artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
  groups=[]
  for group in c.preparation_groups:
   r=dict(group)
   for key in('before','after'):r[key]={k:dict(path=p,bytes=(c.out/p).stat().st_size,sha256=sha(c.out/p))for k,p in group[key].items()}
   groups.append(r)
  valid=dict(schema='phase16-native-succession-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,cold_boot=False,state_imported=True,mother_state=relative(c.mother),mother_sha256=sha(c.mother),
   inherited_context=inherited_context(c,case),controlled_fixture=True,natural_gameplay=False,battery_file_imported=False,fresh_process_per_run=True,additional_core_memory_writes=len(c.preparation),additional_core_memory_writes_after_declared_preparation=0,
   additional_ready_or_result_injections=0,selected_tactic_result_request_cache_animation_ack_injection=False,preparation=c.preparation,preparation_groups=groups,core=c.rt.info,AV=c.rt.av_info,
   frames=c.rt.frames,checkpoint_count=len(c.points),input_step_count=len(c.plan),termination=termination,final_fields=c.current(),campaign_events=c.campaign_events,verified_effects=verified,
   initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),script_sha256=sha(Path(__file__)),capture_base_sha256=sha(ROOT/'scripts/capture_campaign_flows.py'),
   original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),full_audio=c.wav,all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,
   source_pipeline_installed=False,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   limits=['Native end-of-frame fields/RGB/PCM are originalcore observations, not internalCPUtrace or recoveredsource synthesis.',
    'Two city13 cases inherit actual prior four deaths and19/26 prepared precombatbytes; thisrun does not replay thewhole war or prepare death/results.',
    'No-heir keeps empty owner1 cities1/3 after the testedmonth; absent leaderFF is not an automatic claim that all cities neutralize.',
    'Player defeat preserves actualhealthFF/status3; it is not normalized toHP0 or called a confirmed physical death.',
    'Affinity3 is only a deliberately prepared rawbit encoding; originalUI reads following machinecode tiles. It is not an official fourth affinity.',
    'Whole serializedstatebuffers are unchanged; eachrepeat runs in a newprocess.0BVRAM and pathmetadataJSON are excluded.'])
  write(c.out/'validation.json',valid);return valid
 finally:c.close()

def static_qa(out,receipts):
 artifacts=images=audios=groups=0;checks=[]
 for r in receipts:
  folder=out/r['case'];rows=json.loads((folder/'frame-services.json').read_text());points=json.loads((folder/'checkpoints.json').read_text())
  for name,pin in r['artifact_sha256'].items():
   p=folder/name;assert p.stat().st_size==pin['bytes']and sha(p)==pin['sha256'];artifacts+=1
   if p.suffix=='.png':
    with Image.open(p)as im:im.load();assert im.mode=='RGB'and im.size==(256,240)
    images+=1
   if p.suffix=='.wav':
    with wave.open(str(p))as w:
     assert(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(48000,2,2,r['full_audio']['stereo_sample_frames']);raw=w.readframes(w.getnframes());assert digest(raw)==r['full_audio']['PCM_sha256']and any(raw)
    audios+=1
  for p in points:
   row=rows[p['frame']-1];ram=(folder/p['RAM']).read_bytes();sram=(folder/p['SRAM']).read_bytes();assert digest(ram)==row['RAM_sha256']and digest(sram)==row['SRAM_sha256']and fields(ram,sram)==p['fields']
   with Image.open(folder/p['image'])as im:assert digest(im.tobytes())==row['RGB_sha256']
  for group in r['preparation_groups']:
   for kind,base in(('RAM',0),('SRAM',0x6000)):
    raw=bytearray((folder/group['before'][kind]['path']).read_bytes())
    for p in group['writes']:
     if p['kind']==kind:assert raw[p['address']-base]==p['before'];raw[p['address']-base]=p['after']
    assert bytes(raw)==(folder/group['after'][kind]['path']).read_bytes()
   groups+=1
  for crop in r['verified_effects'].get('affinity_glyph_regions',[]):
   with Image.open(folder/crop['PNG'])as im:assert digest(im.crop(crop['box']).tobytes())==crop['RGB_sha256']
  checks.append(dict(case=r['case'],frames=r['frames'],checkpoints=r['checkpoint_count'],all_same_frame_PNG_RAM_SRAM=True,declared_preparation_reconstructed=True))
 result=dict(status='passed',artifact_rehash_checks=artifacts,decoded_nonempty_RGB_images=images,decoded_WAV_files=audios,preparation_group_checks=groups,affinity_region_checks=4,checks=checks,failed_count=0,script_sha256=sha(Path(__file__)),scope='Static files/fields/hash/preparation only; no browser or listening verdict')
 write(out/'static-validation.json',result);return result

def aggregate(out,receipts):
 names={'heir-city13-month':'原city13候选继承→完整下一月轮','no-heir-city13-month':'原city13无候选leaderFF→残余空城与君主跳过','player-defeat-successor':'原普通攻击败北→玩家选城／于禁接任','affinity-pages':'原资料适性0／1／2／3：正式三种与越界字形'}
 cases=[]
 for r in receipts:
  key=r['case'];repeat=json.loads((out/key/'repeat-validation.json').read_text());points=json.loads((out/key/'checkpoints.json').read_text())
  cases.append(dict(case=key,title=names[key],validation=key+'/validation.json',repeat_validation=key+'/repeat-validation.json',checkpoints=key+'/checkpoints.json',frame_services=key+'/frame-services.json',input_plan=key+'/input-plan.json',
   campaign_events=key+'/campaign-events.json',preparation=key+'/preparation.json',flow_events=key+'/flow-events.json',full_WAV=key+'/full-flow.wav',images={p['label']:key+'/'+p['image']for p in points},frames=r['frames'],checkpoint_count=r['checkpoint_count'],
   cold_boot=False,state_imported=True,mother_state=r['mother_state'],mother_sha256=r['mother_sha256'],additional_core_memory_writes=r['additional_core_memory_writes'],inherited_context=r['inherited_context'],verified_effects=r['verified_effects'],final_fields=r['final_fields'],termination=r['termination'],
   nonempty_repeat_artifact_checks=repeat['nonempty_artifact_checks'],PCM_stereo_sample_frames=r['full_audio']['stereo_sample_frames']))
 summary=dict(native_case_count=len(cases),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
  nonempty_repeat_artifact_checks=sum(c['nonempty_repeat_artifact_checks']for c in cases),formal_JSON_repeat_checks=len(FORMAL)*len(cases),excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),
  sample_rate=48000,PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),additional_core_memory_writes=sum(r['additional_core_memory_writes']for r in receipts),inherited_preparation_byte_writes=sum(r['inherited_context']['inherited_preparation_byte_writes']for r in receipts),
  state_import_count=len(cases),fresh_process_per_run=True,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,failed_count=0)
 paths=[Path(__file__),ROOT/'scripts/capture_campaign_flows.py',ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'.toolchain/nestopia/nestopia_libretro.dylib']
 paths.extend(ROOT/r['mother_state']for r in receipts);paths.extend(ROOT/r['inherited_context']['validation']for r in receipts)
 e=dict(schema='phase16-native-succession-flows-v1',status='passed',rom_sha256=ROM_SHA,core=receipts[0]['core'],summary=summary,native_cases=cases,dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in dict.fromkeys(paths)],ranges=[])
 write(out/'evidence.json',e);write(out/'validation.json',dict(schema=e['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))));qa=static_qa(out,receipts)
 lines=['# Phase16：原战后继承、后续月轮、玩家败北与资料适性','',
  '四案都加载公开原核心母档，恢复源码未安装进Nestopia。候选／无候选案继承Phase15真实city13/0战后点：四敌已由旧原核心陥穽死亡，原事前19／26byte受控准备完整引用，但此轮新增writes为0。此轮重新执行的是原city13 AD81继承消费者和完整下一月轮，不冒称重新冷启动打完整战争。','',
  f'首跑{summary["frames_first_run"]}帧／双跑{summary["frames_both_runs"]}帧，{summary["checkpoint_count"]}真实检查点、{summary["nonempty_repeat_artifact_checks"]}非空产物整份双跑一致，其中{summary["formal_JSON_repeat_checks"]}正式JSON。另排除{summary["excluded_empty_VRAM"]}份0B VRAM与{summary["excluded_snapshot_metadata_JSON"]}份路径metadata。每跑新的Python进程，原serializebuffer不裁切／规范化。4完整48kHz双声道16bit WAV和逐帧原PCM/RGB/RAM/SRAMhash保留。','',
  '候选案ruler1 ID8→9，下一月轮AI含0、1、3、4、5、6；无候选案ID8→FF，但下一月轮城1／3仍owner1且名册全FF，AI仅0、3、4、5、6。不能把leaderFF写回叫全部城市自动中立。月轮期间其它城的真实owner变化独立记录，不能擅自归因于继承。两案均从189年1月走到2月、预算恢复3并回playercity0/sub1。','',
  '玩家案只准备曹操事前HP1／武1、敌袁绍武99与敌XY相邻共5byte。真实普通攻击败北后曹操原health=FF、status低2=3，严格保留FF而非规范成0或称已证实肉体死亡。原city13/phase4要求地图选城：普通方向键选ownedcity11、原武将名单选于禁5并确认，原ruler2 ID131→5、忠诚写100、回playercity0/sub1。没有注入结果、controller、request、ready、ack、死亡标志或候选。','',
  '适性案从天然battlecursor母档，在同一个原核心只改变曹操flags11地址69EF的mid2（0Cmask），保留tier/status：packed12、16、1A、1E。每次原B打开完整资料十行再原A关闭；0平／1山／2水，code3从三个合法值表后读原机器码A0、0B／4A、4A，因此是越界乱码，不是官方第四能力。四张原完整PNG的字形区域[64,192,80,208]都有独立RGBhash；门户仅对原图做CSS像素放大，不制造字形图。','',
  '逐帧新增完整30城32B原记录、237武将status低2／byte5原值、城byte1／27／28..31、资料worker040C/D和0380packet；完整原2K RAM／8K SRAM在检查点导出，每帧整份hash。byte5、城未命名尾字段保持raw，不能据单次显示猜新含义。所有新准备组含before/after完整RAM／SRAM并按声明old→new逐字节重建。继承母档的准备和此轮实际写入分开计数。','',
  '原帧是frame-end观测，没有内部PC／callee trace。实际AD81/C132/C386归属由同轮独立原CPU证据承担；Native未捕获FC/FB/ack1，不强套Domestic CA19。静态QA只核原文件、同帧图/内存、WAV和准备差分，Root另做浏览器验收。','']
 for c in cases:lines.extend([f'## {c["title"]}','',f'{c["frames"]}帧，{c["checkpoint_count"]}检查点；此轮新增{c["additional_core_memory_writes"]}byte写，继承旧准备{c["inherited_context"]["inherited_preparation_byte_writes"]}byte。','',f'- [回执]({c["validation"]})',f'- [整份双跑]({c["repeat_validation"]})',f'- [检查点原图]({c["checkpoints"]})',f'- [全部原帧字段]({c["frame_services"]})',f'- [原按钮]({c["input_plan"]})',f'- [准备／前后dump]({c["preparation"]})',f'- [原事件]({c["campaign_events"]})',f'- [完整原WAV]({c["full_WAV"]})',''])
 lines.extend(['```sh',"python3 scripts/capture_succession_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase16/runtime --repeat",'```','', '[Manifest](evidence.json) · [汇总](validation.json) · [静态QA](static-validation.json)','', '冻结产物不能覆盖，复跑使用新目录。探索不参与正式通过计数。'])
 (out/'README.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(status='passed',summary=summary,static_QA=qa),ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase16/runtime');p.add_argument('--probe',choices=('heir-month','no-heir-month','heir-consumer-month','no-heir-consumer-month','player-failure','trait-pages'));p.add_argument('--months',type=int,default=1);p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--capture-child',action='store_true',help=argparse.SUPPRESS);p.add_argument('--repeat',action='store_true');a=p.parse_args()
 if not a.probe:
  out=a.out.resolve()
  if a.capture_child:
   one=capture_case(a.rom,out,a.case);print(json.dumps(dict(case=a.case,frames=one['frames'],checkpoint_count=one['checkpoint_count'],status='passed'),ensure_ascii=False),flush=True);return
  receipts=[]
  for case in CASES if a.case=='all'else(a.case,):
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out),'--case',case,'--capture-child'],check=True);one=json.loads((out/case/'validation.json').read_text())
   if a.repeat:
    second=out.parent/(out.name+'-repeat')/case;subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(second.parent),'--case',case,'--capture-child'],check=True);two=json.loads((second/'validation.json').read_text())
    checks=[dict(artifact=k,equal=v==two['artifact_sha256'].get(k),**v)for k,v in one['artifact_sha256'].items()]
    assert set(one['artifact_sha256'])==set(two['artifact_sha256'])and all(x['equal']for x in checks),[x for x in checks if not x['equal']]
    assert one['frames']==two['frames']and one['verified_effects']==two['verified_effects']and one['final_fields']==two['final_fields']
    write(out/case/'repeat-validation.json',dict(status='passed',first_run=relative(out/case),second_run=relative(second),all_hashes_equal=True,whole_serialized_buffers_exact=True,nonempty_artifact_checks=len(checks),artifacts=checks,
     formal_JSON_exact_parity=list(FORMAL),excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=one['excluded_snapshot_metadata_JSON'],script_sha256=sha(Path(__file__))))
   receipts.append(one)
  if a.repeat:aggregate(out,receipts)
  return
 c=Capture(a.rom,a.out)
 try:
  if a.probe=='player-failure':c.player_failure()
  elif a.probe=='trait-pages':c.trait_pages()
  else:c.follow_month(a.probe.startswith('heir-'),a.months,'consumer'in a.probe)
  c.finish_campaign();print(json.dumps(dict(frames=c.rt.frames,endpoint={k:c.current()[k]for k in('calendar_and_turn_6F00_6F06','city_owners','rulers')},events=c.campaign_events),ensure_ascii=False),flush=True)
 finally:c.close()
if __name__=='__main__':main()
