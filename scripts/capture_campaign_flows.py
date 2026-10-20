#!/usr/bin/env python3
"""Original-core campaign/battle exploration; frozen older files remain read-only.

Only ordinary controller input is used by the natural probes. Explicit
controlled inheritance preparations will be separately declared. CPU oracle
fixtures and native frame observations are never combined as one trace.
"""
from pathlib import Path
import argparse,hashlib,json,sys,ctypes as C,subprocess,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from capture_boot_cooperation_flows import Capture as BootCapture,fields as boot_fields,ROM_SHA,CORE_SHA,sha,digest,write,relative
CASES=('cold-yearwrap','consecutive-invasions-attack-return','succession-heir','succession-no-heir')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json','flow-events.json','campaign-events.json','preparation.json')

def fields(ram,sram):
 f=boot_fields(ram,sram)
 units=[]
 for slot in range(20)if ram[0x7A]in(3,4)and ram[0x78]==3 else():
  ID=ram[0x664+slot]
  if ID==255:continue
  b=sram[0x3C0+12*ID:0x3C0+12*(ID+1)]if ID<237 else bytes(12)
  units.append(dict(slot=slot,officer_id=ID,x=ram[0x600+slot],y=ram[0x614+slot],side_condition=ram[0x628+slot],condition=ram[0x650+slot],
   troop_hundreds_cache=ram[0x63C+slot],officer_raw=b.hex(),health=b[0],status=b[11]&3,troops_raw16=int.from_bytes(b[8:10],'little')))
 f.update(world_cursor_6F3F_6F42=list(sram[0xF3F:0xF43]),unit_arrays={hex(a):list(ram[a:a+20])for a in(0x600,0x614,0x628,0x63C,0x650,0x664)},active_units=units,
  battle_side_0504=ram[0x504],battle_AP_0505=ram[0x505],battle_round_0506=ram[0x506],battle_actor_050A=ram[0x50A],battle_target_0509=ram[0x509],
  battle_resources_0520_0527=list(ram[0x520:0x528]),battle_side_totals_0518_051F=list(ram[0x518:0x520]),city_owners=[sram[i*32]&7 for i in range(30)],
  ordinary_attack_fields_0550_05D7=ram[0x550:0x5D8].hex(),
  city_rosters=[list(sram[i*32+17:i*32+27])for i in range(30)],city_controls_0478_04DF=ram[0x478:0x4E0].hex(),
  rulers=[dict(index=i,ID=sram[0xF07+i*8],raw=sram[0xF07+i*8:0xF0F+i*8].hex(),leader_raw=sram[0x3C0+12*sram[0xF07+i*8]:0x3C0+12*(sram[0xF07+i*8]+1)].hex()if sram[0xF07+i*8]<237 else None)for i in range(7)])
 f['campaign_officers']={str(ID):dict(raw=sram[0x3C0+12*ID:0x3C0+12*(ID+1)].hex(),health=sram[0x3C0+12*ID],status=sram[0x3C0+12*ID+11]&3)for ID in(8,9,51,131,167,191)}
 return f

class Capture(BootCapture):
 def __init__(self,rom,out):
  super().__init__(rom,out);self.mother=None;self.preparation=[];self.preparation_groups=[];self.campaign_events=[];self.deaths=set()
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def observe(self,rt):
  super().observe(rt);extra=fields(rt.memory(2),rt.memory(0));sram=rt.memory(0)
  for key in('city_rosters','rulers'):extra.pop(key)
  extra['city_rosters_sha256']=digest(bytes(sram[i*32+j]for i in range(30)for j in range(17,27)))
  extra['ruler_ids_and_status']=[dict(ruler=i,ID=sram[0xF07+i*8],status=sram[0x3C0+12*sram[0xF07+i*8]+11]&3 if sram[0xF07+i*8]<237 else None)for i in range(7)]
  self.rows[-1].update(extra)
  for ID,record in extra['campaign_officers'].items():
   if record['status']==3 and ID not in self.deaths:
    self.deaths.add(ID);self.campaign_events.append(dict(kind='original-record-status3-observed',frame=rt.frames,officer_id=int(ID),record=record));self.snap('officer-'+ID+'-status3-frame'+str(rt.frames),'original core first observed health/status removal result')
 def inherit(self,mother):
  mother=Path(mother).resolve();self.rt.load_state(mother);self.mother=mother
  self.initial_RAM=self.rt.memory(2);self.initial_SRAM=self.rt.memory(0)
  (self.out/'initial-ram.bin').write_bytes(self.initial_RAM);(self.out/'initial-sram.bin').write_bytes(self.initial_SRAM);(self.out/'initial.state').write_bytes(mother.read_bytes())
  write(self.out/'initial-fields.json',dict(self.current(),cold_boot=False,state_imported=True,mother=relative(mother),mother_sha256=sha(mother),additional_core_memory_writes=0))
 def until(self,predicate,budget=3000,label=None,purpose='observe actual original-core progression'):
  start=self.rt.frames
  while not predicate(self.current()):
   assert self.rt.frames-start<budget,(purpose,self.current())
   self.step(min(8,budget-(self.rt.frames-start)),(),purpose)
  if label:self.snap(label,'bounded actual-state observation after original progression')
  return self.current()
 def ready(self,main,phase):
  return lambda f:f['global_state']==2 and f['nmi_scene']==2 and f['city_state_0400_040F'][:2]==[main,phase]and f['text_progress_0300']==255 and f['text_cursor_0304']==255
 def press_ready(self,key,main,phase,label=None,budget=3000):
  self.press(key,24,'ordinary '+key+' input');return self.until(self.ready(main,phase),budget,label,purpose=f'await original city{main}/{phase} and completed text')
 def recruitment(self,ordinal):
  # Roster allocation moves only real existing reserve. The original full
  # reserve/quantity guard, zero quantity acceptance and command consent run.
  f=self.current();before_budget=f['remaining_budget_raw_6F05'];before_month=f['calendar_month_zero_based_6F01']
  if f['city_state_0400_040F'][:2]==[0,1]:self.press_ready('a',1,1,f'command{ordinal}-icons')
  assert self.current()['city_state_0400_040F'][:2]==[1,1]
  assert self.current()['menu_cursor_0012']==0
  self.press('right',24,'select original military icon');self.press_ready('a',3,1,f'command{ordinal}-military-menu')
  self.press('right',24,'select チョウヘイ recruitment');self.press_ready('a',3,9,f'command{ordinal}-fee-message')
  self.press_ready('a',3,10,f'command{ordinal}-quantity')
  self.press('up',40,'request one original100-troop quantity unit; full-reserve guard may retain zero',f'command{ordinal}-quantity-after-up')
  quantity=self.current()['recruitment_quantity_raw_048E_048F']
  self.press_ready('a',3,11,f'command{ordinal}-consent')
  self.press_ready('a',3,12,f'command{ordinal}-animation-complete',budget=3000)
  assert self.current()['remaining_budget_raw_6F05']==before_budget-1
  self.press_ready('a',3,13,f'command{ordinal}-allocation-ready')
  m,s=self.rt.memory(2),self.rt.memory(0);city=m[0x402];ids=list(s[32*city+17:32*city+27]);valid=[x for x in ids if x!=255]
  chosen=next((i for i,ID in enumerate(valid)if int.from_bytes(s[0x3C0+12*ID+8:0x3C0+12*ID+10],'little')<1000),None)
  allocated=None
  if chosen is not None:
   for _ in range(chosen):self.press('down',24,'select original below-cap officer allocation row')
   ID=valid[chosen];before=int.from_bytes(self.rt.memory(0)[0x3C0+12*ID+8:0x3C0+12*ID+10],'little')
   self.press('right',40,'allocate existing reserve100 by original Right',f'command{ordinal}-allocated')
   after=int.from_bytes(self.rt.memory(0)[0x3C0+12*ID+8:0x3C0+12*ID+10],'little');assert after==before+100,(ID,before,after)
   allocated=dict(ID=ID,before=before,after=after)
  for _ in range(len(valid)-(chosen or 0)):self.press('down',24,'select original おわり row')
  assert self.current()['menu_cursor_0012']==len(valid)
  self.press('a',40,'commit actual allocation and return city/turn controller',f'command{ordinal}-committed')
  event=dict(kind='accepted-original-recruitment-command',ordinal=ordinal,frame=self.rt.frames,before_budget=before_budget,quantity_raw=quantity,troops_quantity=100*quantity,allocated=allocated,initial_month=before_month)
  self.campaign_events.append(event);print(json.dumps(event,ensure_ascii=False),flush=True)
  if before_budget>1:self.until(self.ready(0,1),3000,f'command{ordinal}-world-return')
 def months(self,count):
  self.cold_city();start=self.current()['calendar_year_6F00']*12+self.current()['calendar_month_zero_based_6F01'];ordinal=0
  while self.current()['calendar_year_6F00']*12+self.current()['calendar_month_zero_based_6F01']-start<count:
   before=self.current()['calendar_year_6F00']*12+self.current()['calendar_month_zero_based_6F01']
   for _ in range(3):ordinal+=1;self.recruitment(ordinal)
   self.next_player_message(f'month{before+1-start}-next-player-message')
   now=self.current();assert now['calendar_year_6F00']*12+now['calendar_month_zero_based_6F01']==before+1,now
   self.press_ready('a',0,1,f'month{before+1-start}-player-world')
   event=dict(kind='monthly-return',frame=self.rt.frames,calendar=self.current()['calendar_and_turn_6F00_6F06']);self.campaign_events.append(event)
   print(json.dumps(event,ensure_ascii=False),flush=True)
  self.snap('campaign-final')
 def next_player_message(self,label):
  start=self.rt.frames;last_event_press=start
  def done(f):return f['global_state']==2 and f['nmi_scene']==2 and f['city_state_0400_040F'][:2]==[11,2]and f['ruler_6F03']==2 and f['text_progress_0300']==255 and f['text_cursor_0304']==255
  while not done(self.current()):
   assert self.rt.frames-start<12000,('next player bounded wait',self.current())
   f=self.current()
   if f['global_state']==2 and f['city_state_0400_040F'][0]==10 and f['text_progress_0300']==255 and f['text_cursor_0304']==255 and self.rt.frames-last_event_press>=180:
    self.snap('calendar-event-before-'+str(self.rt.frames));self.press('a',180,'ordinary A acknowledges original monthly event/choice');last_event_press=self.rt.frames
   else:self.step(8,(),'observe original monthly AI/event progression')
  self.snap(label)
 def first_invasion(self):
  old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
  # The entry is a disclosed naturally-captured cold city. These are the
  # unchanged ordinary invasion/army/supply/battle commands from that city.
  for row in old[24:74]:self.step(row['frames'],row.get('buttons',()),'original natural invasion plan',row.get('capture'))
  self.snap('first-battle-action-menu')
 def second_invasion(self):
  if self.current()['city_state_0400_040F'][:2]==[0,1]:self.press_ready('a',1,1,'second-invasion-city-icons')
  old=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
  for row in old[24:74]:self.step(row['frames'],row.get('buttons',()),'second same-instance original invasion/army/supply plan','second-'+row['capture']if row.get('capture')else None)
  self.snap('second-battle-action-menu')
 def complete_retreat(self,ordinal):
  f=self.current();assert f['global_state']==4 and f['nmi_scene']==3
  if f['battle_state_0500_050F'][:2]==[0,2]:self.press('a',180,'select original player commander action menu')
  assert self.current()['battle_state_0500_050F'][:2]==[0,3]
  for _ in range(2):self.press('down',35,'select original retreat menu row')
  self.press('a',180,'open original retreat action',f'battle{ordinal}-retreat-open')
  for i in range(12):
   if self.current()['global_state']==2:break
   self.press('a',240,'original retreat destination/consent/result A confirmation',f'battle{ordinal}-retreat-A{i}')
  self.until(self.ready(0,1),4000,f'battle{ordinal}-city-world-return')
  self.campaign_events.append(dict(kind='original-invasion-retreat-battle-completed',battle=ordinal,frame=self.rt.frames,remaining_command_budget=self.current()['remaining_budget_raw_6F05'],actual_victory_claimed=False))
 def patch(self,kind,address,value,reason):
  assert kind in('RAM','SRAM')
  # The only write mechanism is confined to explicitly controlled fixtures.
  # No request/result/readiness/controller state address is authorized here.
  allowed_RAM={0x505}|set(range(0x600,0x628));assert kind=='SRAM'or address in allowed_RAM,address
  if kind=='SRAM':assert 0x6000<=address<0x6F00 and not 0x63B0<=address<0x63C0,address
  size=2048 if kind=='RAM'else 8192;ident=2 if kind=='RAM'else 0;base=0 if kind=='RAM'else 0x6000
  view=(C.c_ubyte*size).from_address(self.rt.core.retro_get_memory_data(ident));old=view[address-base]
  if old==value:return
  self.preparation.append(dict(frame=self.rt.frames,kind=kind,address=address,before=old,after=value,reason=reason));view[address-base]=value
 def preparation_begin(self,label):
  group=dict(label=label,frame=self.rt.frames,start_write_index=len(self.preparation),before={})
  for kind,ident in(('RAM',2),('SRAM',0)):
   name=label+'-before-'+kind.lower()+'.bin';(self.out/name).write_bytes(self.rt.memory(ident));group['before'][kind]=name
  self.preparation_groups.append(group)
 def preparation_end(self):
  group=self.preparation_groups[-1];group['after']={};group['writes']=self.preparation[group['start_write_index']:]
  for kind,ident in(('RAM',2),('SRAM',0)):
   name=group['label']+'-after-'+kind.lower()+'.bin';(self.out/name).write_bytes(self.rt.memory(ident));group['after'][kind]=name
  write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups))
 def original_attack_probe(self):
  self.snap('second-battle-before-position-preparation')
  self.preparation_begin('second-battle-position-preparation')
  self.patch('RAM',0x600,3,'controlled second-war enemycommander adjacent to player at2,16; no action/result/target prepared')
  self.patch('RAM',0x614,16,'controlled second-war enemycommander legal gridY')
  self.preparation_end()  # no new original frame yet: retain dumps, no stale RGB caption
  self.press('right',35,'select original ordinary attack menu');self.press('a',180,'confirm ordinary attack target operation','second-battle-attack-target')
  self.press('right',35,'move actual target cursor one grid cell to adjacent enemy commander','second-battle-enemy-cursor')
  self.press('a',240,'confirm actual adjacent enemy target','second-battle-attack-confirmation')
  self.press('a',240,'confirm original attack parameters and enter scene','second-battle-attack-scene')
  self.step(180,(),'observe original attack initialization','second-battle-attack-initialized')
 def attack_return(self):
  # All four tactical columns are selected by original Left/Down input.
  # This is a real ordinary-attack scene, then an original retreat command.
  for i in range(12):
   r=self.rt.memory(2)
   if r[0x7A]==6 and list(r[0x540:0x542])==[3,2]:break
   self.press('a',180,'advance original ordinary attack briefing until actual command grid',f'ordinary-attack-command-{i}')
  else:raise AssertionError('ordinary attack command grid not observed')
  assert self.current()['global_state']==6 and self.current()['nmi_scene']==4,self.current()
  baseline=None
  for round_index in range(20):
   self.press('a',90,'commit original default 前進 commands for an actual combat round')
   for j in range(50):
    r=self.rt.memory(2)
    if r[0x7A]!=6 or list(r[0x540:0x542])==[3,2]:break
    self.press('a',90,'original combat action/message continuation')
   else:raise AssertionError('actual forward round did not return to command grid')
   assert r[0x7A]==6,'battle ended before bounded forward-round observation'
   values=list(r[0x5AC:0x5C2]);self.snap('ordinary-attack-forward-round-'+str(round_index))
   if baseline is None:baseline=values
   elif any(a<b for a,b in zip(values,baseline)):
    self.campaign_events.append(dict(kind='original-ordinary-attack-object-loss-observed',frame=self.rt.frames,round=round_index+1,before_object_values=baseline,after_object_values=values,active_global=6,active_nmi=4));break
  else:raise AssertionError('no actual object health/troop loss observed within20 advance rounds')
  self.snap('ordinary-attack-real-damage-before-withdrawal')
  self.press('left',35,'select original 後退 command in first tactical column','ordinary-attack-retreat-column-0')
  for i in range(1,4):
   self.press('down',35,'select next original tactical command column');self.press('left',35,'select original 後退 command',f'ordinary-attack-retreat-column-{i}')
  for i in range(100):
   self.press('a',90,'ordinary attack action/message/result input',f'ordinary-attack-A{i}'if i<4 else None)
   if i>=2 and self.current()['global_state']in(3,4):break
  else:raise AssertionError('ordinary attack did not return within100 pulses')
  self.step(90,(),'confirm actual battle return','ordinary-attack-battle-return')
  self.campaign_events.append(dict(kind='original-ordinary-attack-scene-returned',frame=self.rt.frames,global_state=self.current()['global_state'],nmi_scene=self.current()['nmi_scene']))
  self.press('left',35,'return actual battlefield cursor to player commander','ordinary-attack-player-cursor')
 def two_battles(self,attack=False):
  self.inherit(ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/city-commands.state');self.first_invasion();self.complete_retreat(1);self.second_invasion()
  if attack:self.original_attack_probe();self.attack_return()
  self.complete_retreat(2);self.snap('two-battle-final')
 def retreat_probe(self):
  self.inherit(ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/city-commands.state');self.first_invasion()
  for _ in range(2):self.press('down',35,'select original retreat menu row')
  self.press('a',180,'confirm original retreat action','retreat-choice-open')
  self.press('a',240,'confirm original retreat prompt','retreat-confirmed')
  self.step(600,(),'observe actual retreat consumer','retreat-after-wait')
 def move_cursor(self,x,y):
  s=self.rt.memory(0);cx=int.from_bytes(s[0xF3F:0xF41],'little')//16;cy=int.from_bytes(s[0xF41:0xF43],'little')//16
  for _ in range(abs(x-cx)):self.press('right'if x>cx else'left',35,'move actual battlefield cursor horizontally')
  ny=y-(y>=16);ncy=cy-(cy>=16)
  for _ in range(abs(ny-ncy)):self.press('down'if ny>ncy else'up',35,'move actual battlefield cursor vertically')
 def trap_target(self,slot,ordinal):
  if list(self.rt.memory(2)[0x500:0x502])==[0,2]:
   self.move_cursor(2,16);self.press('a',180,'select original Cao Cao commander menu')
  assert list(self.rt.memory(2)[0x500:0x502])==[0,3],self.current()
  self.press('down',35,'select original 計略 command');self.press('a',220,'open actual tactic menu',f'cast{ordinal}-menu')
  r=self.rt.memory(2);assert list(r[0x500:0x502])==[5,3];assert r[0x580]==0 and r[0x581]==1
  self.press('right',35,'select original 陥穽 ID1 right column');self.press('a',180,'select actual 陥穽 tactic',f'cast{ordinal}-selected')
  assert self.rt.memory(2)[0x543]==1
  r=self.rt.memory(2);self.move_cursor(r[0x600+slot],r[0x614+slot]);self.snap(f'cast{ordinal}-target-cursor')
  self.press('a',180,'confirm actual target by original cursor',f'cast{ordinal}-confirmation')
  assert list(self.rt.memory(2)[0x500:0x502])==[5,5] and self.rt.memory(2)[0x509]==slot,self.current()
  self.snap(f'cast{ordinal}-effect-before');self.press('a',650,'execute original trap animation and death/effect consumer',f'cast{ordinal}-effect-result')
  for i in range(12):
   r=self.rt.memory(2)
   if r[0x7A]not in(3,4)or r[0x500]!=5:break
   self.press('a',240,'confirm original tactic result or actual level/status notification',f'cast{ordinal}-notification-{i}')
  self.step(90,(),'observe original post-effect controller',f'cast{ordinal}-returned')
  self.campaign_events.append(dict(kind='original-trap-cast',ordinal=ordinal,target_slot=slot,frame=self.rt.frames,result=self.rt.memory(2)[0x544],remaining_AP=self.rt.memory(2)[0x505],target_slot_now=self.rt.memory(2)[0x664+slot]))
 def succession(self,heir):
  self.inherit(ROOT/'analysis/runtime/phase3/attack-intro-7.state');self.preparation_begin('controlled-inheritance-preparation')
  r,s=self.rt.memory(2),self.rt.memory(0);assert r[0x664]==8 and r[0x66E]==131
  self.patch('RAM',0x505,30,'controlled AP resource30 permits four actual5-AP trap casts plus retries; natural reachability not claimed')
  base=0x63C0+12*131
  for off,value,why in((2,99,'caster intelligence99'),(6,15000&255,'caster experience15000 low'),(7,15000>>8,'caster experience15000 high'),(11,(s[base-0x6000+11]&15)|0x70,'caster tier7; original status/affinity low nibble retained')):self.patch('SRAM',base+off,value,'controlled '+why)
  positions={1:(5,16),2:(5,14),3:(5,13),0:(3,12)}
  for slot,(x,y)in positions.items():
   self.patch('RAM',0x600+slot,x,'controlled legal unique target X on original class0/4 trap terrain');self.patch('RAM',0x614+slot,y,'controlled legal unique target Y within original target range')
   ID=r[0x664+slot];self.patch('SRAM',0x63C0+12*ID,1,'controlled pre-combat health1; original cast must write health0/status3/slotclear')
   self.patch('SRAM',0x63C0+12*ID+2,10,'controlled target intelligence10 avoids signed gate wrap; actual RNG still consumed')
  if not heir:
   for city in range(30):
    if(s[city*32]&7)==1:
     for j in range(17,27):self.patch('SRAM',0x6000+city*32+j,255,'controlled no-heir exception: empty dead-ruler-owned city roster; owner and family records retained')
  self.preparation_end();self.step(90,(),'render actual controlled battle starting state','controlled-battle-prepared')
  ordinal=0
  for slot in(1,2,3,0):
   while self.rt.memory(2)[0x664+slot]!=255:
    ordinal+=1;assert ordinal<=6,'actual trap failures exceeded declared AP30/bounded6casts'
    self.trap_target(slot,ordinal)
  self.snap('original-enemy-army-cleared')
  for i in range(50):
   f=self.current()
   if f['global_state']==2 and f['active_main']==0 and f['active_phase']==1:break
   self.press('a',240,'ordinary postbattle victory/return/inheritance message confirmation',f'postbattle-A{i}'if i<12 else None)
  else:raise AssertionError('controlled battle/inheritance did not return within50 original A pulses')
  self.step(180,(),'observe original inheritance consumer and stable city return','inheritance-city-return')
  final=self.current();leader=self.rt.memory(0)[0xF0F]
  assert final['campaign_officers']['8']['health']==0 and final['campaign_officers']['8']['status']==3
  assert leader==(9 if heir else 255),(heir,leader,final)
  self.campaign_events.append(dict(kind='original-inheritance-settlement-observed',heir_fixture=heir,frame=self.rt.frames,dead_ruler=1,leader_before=8,leader_after=leader,city4_owner=final['city_owners'][4]))
 def finish_campaign(self):
  self.snap('final');final=super().finish(exploratory=False);write(self.out/'campaign-events.json',self.campaign_events);write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups))
  write(self.out/'exploration-summary.json',dict(status='observed',frames=self.rt.frames,final_fields=self.current(),cold_boot=self.mother is None,state_imported=self.mother is not None,
   mother=relative(self.mother)if self.mother else None,mother_sha256=sha(self.mother)if self.mother else None,additional_core_memory_writes=len(self.preparation),preparation=self.preparation,
   full_audio=self.wav,ROM_modified=False,native_internal_CPU_trace=False,source_CPU_comparisons=0,script_sha256=sha(Path(__file__))))
  return final

def capture_case(rom,out,case):
 c=Capture(rom,out/case)
 try:
  if case=='cold-yearwrap':
   c.months(12);termination='actual cold189January→190January,12 original monthly returns and36 accepted command cards; no state import or additional core writes'
   assert len([e for e in c.campaign_events if e['kind']=='monthly-return'])==12
   assert c.current()['calendar_and_turn_6F00_6F06'][:2]==[90,0]
  elif case=='consecutive-invasions-attack-return':
   c.two_battles(True);termination='one disclosed natural city mother, two same-instance original invasion/army/supply/battle/retreat/return flows; second ordinary attack advances until actual object loss, then withdraws'
   assert len([e for e in c.campaign_events if e['kind']=='original-invasion-retreat-battle-completed'])==2
   assert len(c.preparation)==2 and all(p['kind']=='RAM'and p['address']in(0x600,0x614)for p in c.preparation)
   assert any(e['kind']=='original-ordinary-attack-object-loss-observed'for e in c.campaign_events)
  else:
   c.succession(case=='succession-heir');termination='controlled pre-combat data; four actual trap casts kill all four enemy officers, commander last; original postbattle ruler-ID9 orFF writeback, occupation and city return observed'
   assert c.deaths=={'8','51','167','191'}
   assert len([e for e in c.campaign_events if e['kind']=='original-trap-cast'])==4
  assert(c.current()['global_state'],c.current()['nmi_scene'],c.current()['active_main'],c.current()['active_phase'])==(2,2,0,1)
  c.finish_campaign();assert len(c.rows)==c.rt.frames and any(x['PCM_nonzero']for x in c.rows)
  artifacts={};empty=[]
  for path in sorted(c.out.iterdir()):
   if path.stat().st_size==0:empty.append(path.name);continue
   if path.suffix in('.png','.bin','.state','.wav')or path.name in FORMAL:artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
  group_evidence=[]
  for group in c.preparation_groups:
   row=dict(group)
   row['before']={k:dict(path=v,bytes=(c.out/v).stat().st_size,sha256=sha(c.out/v))for k,v in group['before'].items()}
   row['after']={k:dict(path=v,bytes=(c.out/v).stat().st_size,sha256=sha(c.out/v))for k,v in group['after'].items()}
   group_evidence.append(row)
  valid=dict(schema='phase15-native-campaign-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,cold_boot=c.mother is None,state_imported=c.mother is not None,
   controlled_fixture=bool(c.preparation),natural_gameplay=not c.preparation,battery_file_imported=False,fresh_process_per_run=True,mother_state=relative(c.mother)if c.mother else None,mother_sha256=sha(c.mother)if c.mother else None,
   additional_core_memory_writes=len(c.preparation),additional_ready_or_result_injections=0,additional_core_memory_writes_after_declared_preparation=0,preparation=c.preparation,preparation_groups=group_evidence,
   selected_tactic_result_request_cache_animation_ack_injection=False,source_pipeline_installed=False,source_CPU_comparisons_in_this_receipt=0,native_internal_CPU_trace=False,
   core=c.rt.info,AV=c.rt.av_info,frames=c.rt.frames,checkpoint_count=len(c.points),input_step_count=len(c.plan),termination=termination,final_fields=c.current(),campaign_events=c.campaign_events,
   initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),full_audio=c.wav,all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,
   script_sha256=sha(Path(__file__)),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),capture_base_sha256=sha(ROOT/'scripts/capture_boot_cooperation_flows.py'),
   observed_active_states=[list(x)for x in sorted(c.seen,key=repr)],observed_cooperation_status_values=sorted({r['cooperation_status_6F8B']for r in c.rows}),
   artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(label+'.json'for label in c.labels),formal_JSON=list(FORMAL),
   limits=['Original Nestopia frame-end fields/RGB/PCM are observations, not an internal CPU/NMI instruction trace or recovered-source rendering/audio synthesis.',
    'Only cold-yearwrap starts without state import. Other cases disclose their unchanged original mother state and all additional data preparations.',
    'Two invasions finish by original retreat consumers; no victory in those two wars is claimed. Second war additionally enters the actual ordinary-attack controller and observes real object loss before withdrawing.',
    'Inheritance fixtures deliberately prepare health/intelligence/tier/AP/positions; no-heir also empties owned-city rosters. Such preparation is not natural campaign reachability.',
    'Death/status3, six-array slot removal, battle results, occupied-city and ruler writebacks come from actual core execution; no readiness/result/request/ack is injected.',
    'The inheritance samples do not observe intermediate FC/FB/ack1: do not infer a specific domestic CA19/CB52/CA7F internal call chain from ruler-ID final fields.',
    'Native PCM is synthesized by the original core. Whole serialized buffers remain unmodified; empty VRAM and path-containing snapshot metadata are excluded.'])
  write(c.out/'validation.json',valid);return valid
 finally:c.close()

def static_qa(out,receipts):
 images=audios=artifacts=groups=0;checks=[]
 for r in receipts:
  folder=out/r['case']
  for name,value in r['artifact_sha256'].items():
   path=folder/name;assert path.stat().st_size==value['bytes']and sha(path)==value['sha256'];artifacts+=1
   if path.suffix=='.png':
    with Image.open(path)as im:im.load();assert im.mode=='RGB'and im.size==(256,240)
    images+=1
   if path.suffix=='.wav':
    with wave.open(str(path))as w:
     assert(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(48000,2,2,r['full_audio']['stereo_sample_frames'])
     raw=w.readframes(w.getnframes());assert digest(raw)==r['full_audio']['PCM_sha256']and any(raw)
    audios+=1
  rows=json.loads((folder/'frame-services.json').read_text());points=json.loads((folder/'checkpoints.json').read_text());assert len(rows)==r['frames']
  assert sum(row['PCM_stereo_sample_frames']for row in rows)==r['full_audio']['stereo_sample_frames']
  for p in points:
   row=rows[p['frame']-1];ram=(folder/p['RAM']).read_bytes();sram=(folder/p['SRAM']).read_bytes()
   assert digest(ram)==row['RAM_sha256']and digest(sram)==row['SRAM_sha256']and fields(ram,sram)==p['fields']
   with Image.open(folder/p['image'])as im:assert digest(im.tobytes())==row['RGB_sha256']
  for group in r['preparation_groups']:
   for kind,base in(('RAM',0),('SRAM',0x6000)):
    raw=bytearray((folder/group['before'][kind]['path']).read_bytes())
    for p in group['writes']:
     if p['kind']==kind:assert raw[p['address']-base]==p['before'];raw[p['address']-base]=p['after']
    assert bytes(raw)==(folder/group['after'][kind]['path']).read_bytes()
   groups+=1
  checks.append(dict(case=r['case'],frames=len(rows),checkpoints=len(points),same_frame_RGB_RAM_SRAM=True,PCM_size_and_hash_match=True,all_declared_preparation_reconstructed=True))
 result=dict(status='passed',artifact_rehash_checks=artifacts,decoded_nonempty_RGB_images=images,decoded_WAV_files=audios,preparation_group_checks=groups,checks=checks,failed_count=0,script_sha256=sha(Path(__file__)),scope='static PNG/WAV/hash/field/preparation checks; no browser or listening verdict, no internal CPUtrace')
 write(out/'static-validation.json',result);return result

def aggregate(out,receipts):
 names={'cold-yearwrap':'真实冷启动：189年1月至190年1月的十二次月回合',
  'consecutive-invasions-attack-return':'同实例两次出征与退却：第二战实际普通攻击交锋',
  'succession-heir':'受控四敌连死：原战后候选9继承与城市返回',
  'succession-no-heir':'受控空名册与四敌连死：原战后君主FF结算'}
 cases=[]
 for r in receipts:
  key=r['case'];repeat=json.loads((out/key/'repeat-validation.json').read_text());points=json.loads((out/key/'checkpoints.json').read_text())
  cases.append(dict(case=key,title=names[key],validation=key+'/validation.json',repeat_validation=key+'/repeat-validation.json',checkpoints=key+'/checkpoints.json',frame_services=key+'/frame-services.json',
   input_plan=key+'/input-plan.json',flow_events=key+'/flow-events.json',campaign_events=key+'/campaign-events.json',preparation=key+'/preparation.json',full_WAV=key+'/full-flow.wav',images={p['label']:key+'/'+p['image']for p in points},
   frames=r['frames'],checkpoint_count=r['checkpoint_count'],cold_boot=r['cold_boot'],state_imported=r['state_imported'],controlled_fixture=r['controlled_fixture'],natural_gameplay=r['natural_gameplay'],
   additional_core_memory_writes=r['additional_core_memory_writes'],mother_state=r['mother_state'],mother_sha256=r['mother_sha256'],final_fields=r['final_fields'],termination=r['termination'],
   nonempty_repeat_artifact_checks=repeat['nonempty_artifact_checks'],PCM_stereo_sample_frames=r['full_audio']['stereo_sample_frames']))
 summary=dict(native_case_count=len(cases),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
  nonempty_repeat_artifact_checks=sum(c['nonempty_repeat_artifact_checks']for c in cases),formal_JSON_repeat_checks=len(FORMAL)*len(cases),excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),
  excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),sample_rate=48000,PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),
  additional_core_memory_writes=sum(r['additional_core_memory_writes']for r in receipts),state_import_count=sum(r['state_imported']for r in receipts),cold_boot_case_count=sum(r['cold_boot']for r in receipts),
  controlled_fixture_count=sum(r['controlled_fixture']for r in receipts),fresh_process_per_run=True,source_CPU_comparisons_in_this_receipt=0,native_internal_CPU_trace=False,failed_count=0)
 paths=[Path(__file__),ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'.toolchain/nestopia/nestopia_libretro.dylib',ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json',ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/city-commands.state',ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/validation.json',ROOT/'analysis/runtime/phase3/attack-intro-7.state']
 evidence=dict(schema='phase15-native-campaign-flows-v1',status='passed',rom_sha256=ROM_SHA,core=receipts[0]['core'],summary=summary,native_cases=cases,dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in paths],ranges=[])
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(Path(__file__))))
 static=static_qa(out,receipts)
 lines=['# Phase15：原核心长期回合、连续出征与受控战后继承','',
  '四案全部来自锁定原ROM/Nestopia。仅冷全年案没有状态导入与新增写入；其它三案导入公开母档，受控数据逐byte列明。恢复源码未安装进原核心，原图与48kHz双声道16bit PCM不是恢复源码生成。','',
  f'首跑{summary["frames_first_run"]}帧、双跑{summary["frames_both_runs"]}帧、{summary["checkpoint_count"]}检查点。{summary["nonempty_repeat_artifact_checks"]}份非空产物整份hash一致，其中{summary["formal_JSON_repeat_checks"]}份正式JSON；{summary["excluded_empty_VRAM"]}份0B VRAM和{summary["excluded_snapshot_metadata_JSON"]}份含路径metadata排除。每跑独立新Python进程，不裁剪或归一化原serializebuffer。','',
  '冷全年案使用原城市招兵/分配命令消耗36张行动牌，十二次回到玩家回合，189年1月推进到190年1月。最初预备兵已满，部分请求数量被原上限守卫保留0；这是实际接受的行动，不称每次都增加兵数。五月等原月事件仅用普通A确认。每帧保存6F06、全30城owner、完整30城名册hash；检查点保存30×10名册及完整原SRAM。','',
  '连续两次出征在同一个导入实例完成原侵略、出兵、军粮、战场、退却和城市返回。第二战仅在战场准备敌指挥官XY两byte相邻坐标，原按键选择普通攻击；原前进数轮直到实际战斗对象数值降低，再在四列原菜单选择後退，返回战场后执行原退却消费者。两场以退却结束，不称两场胜利。','',
  '继承两案以自然战场母档为起点，公开准备曹操知力99/经验15000/等级7、AP30、四敌事前HP1/IQ10和四个唯一合法class0/4坐标。AP30是受控资源，不称自然可达。实际四次陥穽杀死191、51、167后最后袁绍8，原HP0/status3和六个active数组FF由原代码写入。候选案保留城3原袁谭9名册和原记录byte5=0/status2；无候选案另外把袁绍owned城市名册清空，属于异常受控准备。','',
  '原战后最终写ruler1 ID9或FF、城4owner2并回city0/sub1。两个继承案每帧6F8B仅观察FF，没有捕获FC/FB/ack1中间值，不能据此强认Domestic CA19/CB52/CA7F内部调用。具体原指令链和纯源码等价由独立CPU证据承担；此处仅证明已公开的数据准备后原核心实际死亡与战后写回结果。','',
  '每个准备组都有before/after完整2048B RAM与8192B SRAM，静态QA逐old→new重建全部差分；ready、结果、cache、request、ack、controller/global状态均未注入。每帧完整RAM/SRAM/RGB/PCM均hash，原active_controller区分真正场景与inactive残字节。检查点完整state含mapper/PPU，不把不可导出VRAM空文件当证据。','']
 for case in cases:
  lines.extend([f'## {case["title"]}','',f'{case["frames"]}帧，{case["checkpoint_count"]}检查点，新增准备{case["additional_core_memory_writes"]}byte写。{case["termination"]}。','',
   f'- [正式回执]({case["validation"]})',f'- [整份产物双跑]({case["repeat_validation"]})',f'- [原检查点/PNG]({case["checkpoints"]})',f'- [原逐帧字段]({case["frame_services"]})',f'- [实际按键]({case["input_plan"]})',f'- [准备与前后dump]({case["preparation"]})',f'- [原事件观察]({case["campaign_events"]})',f'- [完整原WAV]({case["full_WAV"]})',''])
 lines.extend(['```sh',"python3 scripts/capture_campaign_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase15/runtime --repeat",'```','',
  '[Manifest](evidence.json) · [汇总回执](validation.json) · [PNG/WAV/准备静态QA](static-validation.json)','',
  '冻结目录不可覆盖；复跑指定新的输出目录。探索文件不参与正式通过计数；静态QA不等于浏览器验收或人工听音，也不是内部CPU trace。'])
 (out/'README.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(status='passed',summary=summary,static_QA=static),ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase15/runtime');p.add_argument('--probe',choices=('months','retreat','two-retreats','second-attack','heir','no-heir'));p.add_argument('--months',type=int,default=3);p.add_argument('--tail-plan',type=Path);p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--capture-child',action='store_true',help=argparse.SUPPRESS);p.add_argument('--repeat',action='store_true');a=p.parse_args()
 if not a.probe:
  assert not a.tail_plan;out=a.out.resolve()
  if a.capture_child:
   one=capture_case(a.rom,out,a.case);print(json.dumps(dict(case=a.case,status=one['status'],frames=one['frames'],checkpoint_count=one['checkpoint_count']),ensure_ascii=False),flush=True);return
  receipts=[]
  for case in CASES if a.case=='all'else(a.case,):
   subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out),'--case',case,'--capture-child'],check=True);one=json.loads((out/case/'validation.json').read_text())
   if a.repeat:
    second=out.parent/(out.name+'-repeat')/case
    subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(second.parent),'--case',case,'--capture-child'],check=True);two=json.loads((second/'validation.json').read_text())
    checks=[dict(artifact=k,equal=value==two['artifact_sha256'].get(k),**value)for k,value in one['artifact_sha256'].items()]
    assert set(one['artifact_sha256'])==set(two['artifact_sha256'])and all(x['equal']for x in checks),[x for x in checks if not x['equal']]
    assert one['frames']==two['frames']and one['final_fields']==two['final_fields']and one['preparation']==two['preparation']
    write(out/case/'repeat-validation.json',dict(status='passed',first_run=relative(out/case),second_run=relative(second),nonempty_artifact_checks=len(checks),all_hashes_equal=True,artifacts=checks,formal_JSON_exact_parity=list(FORMAL),whole_serialized_buffers_exact=True,
     excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=one['excluded_snapshot_metadata_JSON'],script_sha256=sha(Path(__file__))))
   receipts.append(one)
  if a.repeat:aggregate(out,receipts)
  return
 c=Capture(a.rom,a.out)
 try:
  if a.probe=='months':c.months(a.months)
  elif a.probe=='retreat':c.retreat_probe()
  elif a.probe in('heir','no-heir'):c.succession(a.probe=='heir')
  else:c.two_battles(attack=a.probe=='second-attack')
  if a.tail_plan:
   for row in json.loads(a.tail_plan.read_text()):c.step(row['frames'],row.get('buttons',()),row.get('purpose','ordinary exploratory input'),row.get('capture'))
  c.finish_campaign();print(json.dumps(dict(frames=c.rt.frames,final=c.current()),ensure_ascii=False),flush=True)
 finally:c.close()
if __name__=='__main__':main()
