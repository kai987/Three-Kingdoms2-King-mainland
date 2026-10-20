#!/usr/bin/env python3
"""Unchanged original6502 differential for independent full tactical strategyAI."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.tactical_strategy_ai import StrategyData,TacticalStrategyAI,STRATEGY_ENTRIES,ROM_SHA256
from verify_tactical_ai_control import native_bus
from py65.devices.mpu6502 import MPU
RAM=list(range(0x4D8,0x4E0))+list(range(0x500,0x678))+list(range(0x42C,0x42F))

def verify(rom,out):
 data=StrategyData.from_rom(rom);counts=Counter();failures=[];examples=[];coverage=Counter();guards=[]
 baseprefix=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(baseprefix)+'-ram.bin').read_bytes();base_sram=Path(str(baseprefix)+'-sram.bin').read_bytes()
 def fresh(actor=0,side=0,ap=15):
  ram=bytearray(base_ram);sram=bytearray(base_sram);ram[0xDE:0xE4]=bytes([38,40,41,38,40,41]);ram[0x1FE:0x200]=bytes([255,1]);ram[0x504]=side;ram[0x505]=ap
  sram[0xF8B]=0;sram[0xF8C]=actor;sram[0xF94:0xF97]=bytes(3);sram[0xFA1:0xFB5]=bytes([255]*20);sram[0xFA1+actor]=0
  ram[0x4D8:0x4E0]=bytes([255]*8);ram[0x20:0x3B]=bytes(0x1B)
  return ram,sram
 def clone(ram,sram):
  m=bytearray(65536);m[:2048]=ram;m[0x6000:0x8000]=sram;return m
 def original(bus,entry,stop=0x200,limit=400000):
  c=MPU(memory=bus,pc=entry);c.sp=0xFD;c.p=32;bus.cpu=c
  for n in range(limit):
   if c.pc==stop:return c,n
   bus.pc=c.pc;bus.step_no=n;origin=bus.origin(c.pc)
   if origin is None:raise AssertionError(f'unexpected RAM PC{c.pc:04X}')
   bank,offset=origin;coverage[(bank,c.pc,offset)]+=1;c.step()
  raise RuntimeError(f'original budget at{c.pc:04X}')
 def compare(group,entry,ram,sram,call,meta=None,stop=0x200):
  m=clone(ram,sram);model=TacticalStrategyAI(m,data,data_window_bank=6);bus=native_bus(rom,ram,sram)
  try:
   effect=call(model);c,n=original(bus,entry,stop=stop)
   delta=[(i,bus.peek(i),m[i])for i in RAM if bus.peek(i)!=m[i]]
   sdelta=[(0x6000+i,a,b)for i,(a,b)in enumerate(zip(bus.sram,m[0x6000:0x8000]))if a!=b]
   assert not delta and not sdelta,(delta[:10],sdelta[:10])
   counts[group]+=1
   if sum(v['group']==group for v in examples)<8:examples.append(dict(group=group,input=meta,original_instructions=n,effect=effect))
   return m,effect
  except Exception as exc:
   failures.append(dict(group=group,input=meta,error=str(exc)))
   if len(failures)>=20:raise
 def officer(ram,sram,slot,**values):
  ident=ram[0x664+slot];o=0x3C0+12*ident
  for key,value in values.items():
   if key=='troops':sram[o+8]=value&255;sram[o+9]=value>>8
   else:sram[o+dict(hp=0,iq=2,loyalty=3,flags=11)[key]]=value
 # Complete0..7 bodies with originalcity4 map and meaningful small layouts.
 for strategy in range(8):
  for side in(0,128):
   actor=10 if side else 0;enemy=0 if side else 10
   for ap in(0,1,2,5,10,15,255):
    for scenario in('far','adjacent','same_xy','two_candidates'):
     r,s=fresh(actor,side,ap);s[0xFA1+actor]=strategy;r[0x600+actor]=10;r[0x614+actor]=14;r[0x600+enemy]=20;r[0x614+enemy]=17
     if scenario=='adjacent':r[0x600+enemy]=11;r[0x614+enemy]=14
     if scenario=='same_xy':r[0x600+enemy]=10;r[0x614+enemy]=14
     if scenario=='two_candidates':
      target=1 if side else 11;r[0x664+target]=22;r[0x628+target]=side^128;r[0x600+target]=12;r[0x614+target]=14;r[0x600+enemy]=11;r[0x614+enemy]=15
     officer(r,s,actor,hp=100,iq=80,troops=1000)
     compare('complete_strategy_body',STRATEGY_ENTRIES[strategy],r,s,lambda t,i=strategy:t.run_strategy(i),[strategy,side,ap,scenario])
 # Exact role boundaries. Positive side controlled cityowners/rosters are
 # legitimate records; nearestfriendlyhole/lastneutral/full/allhostile paths.
 for role in('leader','commander','officer'):
  for troops in(0,100,101,200,201,300,301,65535):
   for hp in(0,40,41,50,51,99,100,255):
    for side in(0,128):
     actor=(10 if side else 0)if role!='officer'else 1;r,s=fresh(actor,side)
     if role=='officer':r[0x664+actor]=22;r[0x628+actor]=side;r[0x600+actor]=10;r[0x614+actor]=14
     ruler=(r[0x507]>>(4 if side else 0))&15
     s[0xF07+8*ruler]=r[0x664+actor]if role=='leader'else 109
     officer(r,s,actor,hp=hp,troops=troops);r[0x52A]=3;s[0xF92]=37
     compare('complete_retreat',0xAF0D,r,s,lambda t:t.retreat(),[role,troops,hp,side])
 # Servicearrival: same original map coords with chosen adjacentsource only.
 for service,entry,name in((0,0xA329,'resupply'),(2,0xA507,'heal')):
  for city in range(30):
   tx,ty=data.service_coordinates[city][service]
   if not(1<=tx<30 and 0<=ty<20 and ty!=15):continue
   for gold in(0,49,50,100,9999,65535):
    r,s=fresh();r[0x50E]=city
    from source.recovered.terrain_rules import city_chunks
    r[0xAA:0xAE]=bytes(city_chunks(rom,city));r[0x600]=tx-1;r[0x614]=ty;r[0x505]=255;s[0xFA1]=5 if service==0 else 6
    # Remove accidental neighboring originalarmy units without removingactor.
    for slot in range(1,20):r[0x664+slot]=255
    r[0x650]=0;r[0x526]=gold&255;r[0x527]=gold>>8;r[0x522]=100;r[0x523]=0;r[0x506]=1
    officer(r,s,0,hp=40,troops=1000);s[0xF92]=127
    compare('complete_'+name,entry,r,s,lambda t,n=name:getattr(t,n)(),[city,gold,[tx,ty]])
 # WholeA02D with legal strategy holes, attemptcounters, conditions and AP.
 for strategy in range(8):
  for side in(0,128):
   actor=10 if side else 0
   for cursor in(0,actor,20):
    for ap in(0,2,10,255):
     r,s=fresh(actor,side,ap);s[0xFA1+actor]=strategy;s[0xF94]=cursor;r[0x600+actor]=10;r[0x614+actor]=14
     officer(r,s,actor,hp=100,iq=92,troops=1000,flags=0x34)
     compare('complete_cooperative_update',0xA02D,r,s,lambda t:t.step(),[strategy,side,cursor,ap])
 # Nativeend-of-frame snapshots are wholecooperative input, not moreframes.
 for prefix in sorted((ROOT/'analysis/phase7/runtime/natural-turn').glob('*-ram.bin')):
  r=bytearray(prefix.read_bytes());s=bytearray(prefix.with_name(prefix.name.replace('-ram.bin','-sram.bin')).read_bytes());r[0x1FE:0x200]=bytes([255,1]);r[0xE2:0xE4]=bytes([40,41])
  compare('native_snapshot_cooperative_CPU',0xA02D,r,s,lambda t:t.step(),prefix.stem)
 # Full basic/special pipelines use actual maps/predicates, no predicate stub.
 # Two matched troop candidates exercise equal swaps and inherited2Fpasses.
 from source.recovered.terrain_rules import city_chunks,legal_cell
 representatives={}
 for city in range(30):
  chunks=city_chunks(rom,city)
  r,s=fresh();r[0xAA:0xAE]=bytes(chunks)
  probe=TacticalStrategyAI(clone(r,s),data,data_window_bank=6)
  for y in range(20):
   for x in range(31):
    if legal_cell(x,y):
     terrain=probe.decisions._terrain(x,y)
     representatives.setdefault(terrain,(city,x,y))
 for special in(False,True):
  for ident,iq,level in((22,92,3),(109,99,6),(131,85,5),(22,39,3),(109,255,15)):
   for terrain,(city,tx,ty)in sorted(representatives.items()):
    for ap in(0,4,8,10,12,255):
     r,s=fresh();r[0x664:0x678]=bytes([255])*20;r[0x50E]=city;r[0xAA:0xAE]=bytes(city_chunks(rom,city));r[0x505]=ap
     r[0x664]=ident;r[0x600]=max(0,tx-1);r[0x614]=ty;r[0x628]=0;r[0x650]=0
     for slot,oid in((10,33),(11,34)):
      r[0x664+slot]=oid;r[0x600+slot]=tx if slot==10 else min(30,tx+1);r[0x614+slot]=ty;r[0x628+slot]=128;r[0x650+slot]=1
      officer(r,s,slot,hp=100,iq=90,loyalty=20,troops=700,flags=0x20)
     officer(r,s,0,hp=100,iq=iq,troops=700,flags=level<<4)
     r[0x2F]=0;s[0xF92]=127
     compare('complete_special_pipeline'if special else'complete_basic_pipeline',0xAAF8 if special else 0xA95C,r,s,lambda t,sp=special:t.plan_tactic(sp),[ident,iq,level,terrain,city,ap])
 # Dedicated original army-sum wrap, sorting pass-counter and resource-word
 # arithmetic boundaries; these are selected valid inputs, not broadrandomRAM.
 for counter in(0,1,2,127,128,255):
  for troops in(0,1,65535):
   r,s=fresh();r[0x664:0x678]=bytes([255])*20;r[0x664]=22;r[0x600]=10;r[0x614]=14;r[0x628]=0;r[0x505]=0
   for slot,oid in((10,33),(11,34),(12,35)):
    r[0x664+slot]=oid;r[0x600+slot]=11;r[0x614+slot]=14;r[0x628+slot]=128;r[0x650+slot]=0;officer(r,s,slot,hp=100,troops=troops)
   officer(r,s,0,hp=100,iq=92,troops=700,flags=0x30);r[0x2F]=counter
   compare('pipeline_sort_pass_and_ties',0xAAF8,r,s,lambda t:t.plan_tactic(True),[counter,troops])
 for city in(0,4,12,20,29):
  tx,ty=data.service_coordinates[city][0]
  if not(1<=tx<30 and 0<=ty<20 and ty!=15):continue
  for troops in(0,1,999,65535):
   for grain in(0,1,9999,65535):
    for turn in(0,30,31,255):
     r,s=fresh();r[0x50E]=city;r[0xAA:0xAE]=bytes(city_chunks(rom,city));r[0x664:0x678]=bytes([8]+[255]*19);r[0x600]=tx-1;r[0x614]=ty;r[0x650]=0;r[0x505]=255;r[0x506]=turn
     r[0x526:0x528]=bytes([255,255]);r[0x522]=grain&255;r[0x523]=grain>>8;s[0xFA1]=5;officer(r,s,0,troops=troops)
     compare('resupply_raw_word_boundaries',0xA329,r,s,lambda t:t.resupply(),[city,troops,grain,turn])
 # Legal ROM-backed descriptor exercises logicaldatawindow changes rather
 # than substituting RAMAA. Select only fourbyte descriptors valid in every
 # actual tiledata bank plus6/16/17 callerdata banks; no tableout-of-bounds.
 descriptor_offset=next(i for i in range(0x1FFD)if all(all(v<120 for v in data.data_pages[bank][i:i+4])for bank in(0,3,4,5,6,16,17)))
 for strategy in(1,2,3,4,5,6):
  for side in(0,128):
   actor=10 if side else 0;r,s=fresh(actor,side,255);r[0xA8]=(0x8000+descriptor_offset)&255;r[0xA9]=(0x8000+descriptor_offset)>>8
   r[0x600+actor]=10;r[0x614+actor]=14;s[0xFA1+actor]=strategy;officer(r,s,actor,hp=100,troops=1000,iq=80)
   compare('ROM_descriptor_complete_strategy',STRATEGY_ENTRIES[strategy],r,s,lambda t,i=strategy:t.run_strategy(i),[strategy,side,hex(0x8000+descriptor_offset)])
 # All requestbytes on the complete cooperative API, no eligibleactors;
 # one is the actual B933 route, FF is the direct return, others scan.
 for request in range(256):
  r,s=fresh();s[0xF8B]=request;s[0xFA1:0xFB5]=bytes([255])*20
  compare('complete_all_request_bytes',0xA02D,r,s,lambda t:t.step(),request)
 for side in(0,128):
  actor=10 if side else 0;r,s=fresh(actor,side);s[0xFA1+actor]=7;s[0xF94]=actor
  compare('budget_prefix_before_strategy',0xA02D,r,s,lambda t:t.step(maximum_strategy_calls=0),side,stop=0xA099)
 # Precise source domain guards; originalinvalidtablepathsneverexecuted.
 for name,setup,call in[
  ('strategy8',lambda r,s:None,lambda t:t.run_strategy(8)),
  ('negative_budget',lambda r,s:None,lambda t:t.step(maximum_strategy_calls=-1)),
  ('actor20',lambda r,s:s.__setitem__(0xF8C,20),lambda t:t.run_strategy(0)),
  ('officerFF',lambda r,s:r.__setitem__(0x664,255),lambda t:t.retreat()),
  ('city30',lambda r,s:r.__setitem__(0x50E,30),lambda t:t.resupply()),
  ('ruler7',lambda r,s:r.__setitem__(0x507,0x27),lambda t:t.retreat()),
  ('data_bank32',lambda r,s:None,lambda t:t.step(data_window_bank=32)),
  ('code_descriptor',lambda r,s:r.__setitem__(0xA9,0xA0),lambda t:t.decisions.quote_direction(0))]:
  r,s=fresh();setup(r,s)
  try:call(TacticalStrategyAI(clone(r,s),data,data_window_bank=6))
  except ValueError:guards.append(name)
  else:raise AssertionError('missingguard'+name)
 # FlatRAM ROMdescriptor cannot silently assume physicalbank.
 r,s=fresh();r[0xA8]=0;r[0xA9]=0x80
 try:TacticalStrategyAI(clone(r,s),data).decisions.quote_direction(0)
 except ValueError:guards.append('flatROMdescriptor_withoutbank')
 else:raise AssertionError('missingROMdescriptorcontextguard')
 out.mkdir(parents=True,exist_ok=True);source=ROOT/'source/recovered/tactical_strategy_ai.py'
 result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,case_count=sum(counts.values())+len(guards),rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),source_guards=guards,failures=failures,examples=examples,
             compared_sram_size=8192,declared_ram_addresses=RAM,original_prefix_case_count=counts['budget_prefix_before_strategy'],original_complete_case_count=sum(counts.values())-counts['budget_prefix_before_strategy'],executed_original_instruction_locations=len(coverage),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             source_original_code_calls=0,source_IR_interpretation=False,contract='Full8KSRAM and declared gameplayRAM only; internal2Fsort input maintained but arbitrary CPU scratch/registers/stack/mapper effects excluded; originalhelpers/RNG/mapbytes execute unchanged in oracle',
             limits=['ControlledlegalCPUfixtures are not naturalcampaignreachability.','Nativeframe snapshots reused as synchronousCPU inputs do not add nativeframes.','Strategies produce proposals; no tactic/movement/AP commit or completion acknowledgement is substituted.'])
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(bank=b,cpu=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts','executed_original_instruction_locations')},indent=2))
 if failures:print(json.dumps(failures[:12],ensure_ascii=False,indent=2));raise SystemExit(1)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase8/strategies');a=p.parse_args();verify(a.rom.read_bytes(),a.out)
