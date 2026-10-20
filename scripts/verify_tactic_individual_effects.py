#!/usr/bin/env python3
"""Original6502 differential for three individual tactic effects and deathstages.

No originalhelper/predicate/RNG substituted. FatalHP compares the prefix before
D6CC; the original map-refresh CALL is then actually executed. Its explicit
hostmemory writes are supplied to the semantic resume, which alone runs pure
XP/removal/remainingeffect data logic. This is not renderer acknowledgement.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.tactic_individual_effects import IndividualData,IndividualTactics,ROM_SHA256,DECLARED_RAM_RANGES,EFFECT_ENTRIES
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
RAM=[a for lo,hi in DECLARED_RAM_RANGES for a in range(lo,hi)]

def verify(rom,out):
 data=IndividualData.from_rom(rom);counts=Counter();failures=[];samples=[];coverage=Counter();graphics_services=[];guards=[]
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';baseline_ram=Path(str(prefix)+'-ram.bin').read_bytes();baseline_sram=Path(str(prefix)+'-sram.bin').read_bytes()
 def fresh():
  b=Bus(rom,'alternating');b.ram[:]=baseline_ram;b.sram[:]=baseline_sram;b.banks=[6,12,13,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xDE:0xE4]=bytes([38,44,45,38,44,45]);b.ram[0x1FE:0x200]=bytes([255,1]);b.ram[0x42C:0x435]=bytes(9);b[0x544]=0;b[0x50A]=0;b[0x509]=1;b[0x50F]=0;b[0x504]=0
  b[0x600]=10;b[0x601]=11;b[0x614]=b[0x615]=10;b[0x664]=8;b[0x665]=191;b[0x4D8]=b[0x4DC]=255
  return b
 def record(b,slot,hp=100,war=80,iq=99,xp=1000,flags=0x32,troops=700):
  addr=0x63C0+12*b[0x664+slot]
  values=[hp,war,iq,60,70,0,xp&255,xp>>8,troops&255,troops>>8,0,flags]
  for i,value in enumerate(values):b[addr+i]=value
 def clone(b):
  m=bytearray(65536);m[:2048]=b.ram;m[0x6000:0x8000]=b.sram;return m
 def cpu_new(b,entry,regs=None):
  c=MPU(memory=b,pc=entry);c.sp=0xFD;c.p=32;b.cpu=c
  for key,value in(regs or{}).items():setattr(c,key,value)
  return c
 def advance(b,c,stops,limit=500000):
  for n in range(limit):
   if c.pc in stops:return n
   b.pc=c.pc;b.step_no=n;origin=b.origin(c.pc)
   if origin is None:raise RuntimeError(f'UnexpectedRAMPC{c.pc:04X}')
   bank,offset=origin;coverage[(bank,c.pc,offset)]+=1;c.step()
  raise RuntimeError(f'CPUbudget PC{c.pc:04X}')
 def parity(group,b,m,meta):
  rd=[(i,b.peek(i),m[i])for i in RAM if b.peek(i)!=m[i]];sd=[(0x6000+i,a,v)for i,(a,v)in enumerate(zip(b.sram,m[0x6000:0x8000]))if a!=v]
  assert not rd and not sd,(group,meta,rd[:12],sd[:12]);counts[group]+=1
 def compare(group,b,entry,call,meta=None,regs=None):
  m=clone(b);source=IndividualTactics(m,data);c=cpu_new(b,entry,regs)
  try:
   effect=call(source)
   if effect['status']=='dependency':
    advance(b,c,{0xB615});parity(group+'_death_prefix',b,m,meta)
    pre_ram=b.ram[:];pre_sram=b.sram[:]
    # Real D6CC call, including unchangedoriginalbankedhelpers. No replacement.
    instructions=advance(b,c,{0xB618});ram_host=[i for i,(old,new)in enumerate(zip(pre_ram,b.ram))if old!=new];sram_host=[i for i,(old,new)in enumerate(zip(pre_sram,b.sram))if old!=new]
    for i in ram_host:m[i]=b.ram[i]
    for i in sram_host:m[0x6000+i]=b.sram[i]
    result=source.after_death_graphics(map_refresh_returned=True)
    advance(b,c,{0x200});parity(group+'_after_actual_map_refresh_suffix',b,m,meta)
    graphics_services.append(dict(input=meta,original_map_refresh_instructions=instructions,host_RAM_written=ram_host,host_SRAM_written=[0x6000+i for i in sram_host],asynchronous_job_acknowledged=False))
   else:
    advance(b,c,{0x200});parity(group+'_complete',b,m,meta);result=effect
   if sum(v['group']==group for v in samples)<8:samples.append(dict(group=group,input=meta,result=result))
  except Exception as exc:
   failures.append(dict(group=group,input=meta,error=str(exc)))
   if len(failures)>=10:raise
 # Three actual fullhandlers. Valid initialselectedIDs; typed stats, phase
 # bytes, aliases, rangefailure and distinct side-resource branches.
 for tactic in(1,5,9):
  for side in(0,128):
   for alias in('distinct','same_record','same_slot'):
    for hp in(0,1,10,100,255):
     for cursor in(0,127,255):
      b=fresh();b[0x504]=side;b[0x50]=cursor
      if alias=='same_record':b[0x665]=b[0x664]
      if alias=='same_slot':b[0x509]=0
      record(b,0,hp=hp if alias!='distinct'else 100,war=80,iq=99,flags=0x62,troops=0xFC00|700)
      if alias=='distinct':record(b,1,hp=hp,war=255,iq=0,flags=0x32,troops=0xFC00|700)
      b[0x522]=0xFF;b[0x523]=0xFF;b[0x524]=0x10;b[0x525]=0x27
      compare('handler'+str(tactic),b,EFFECT_ENTRIES[tactic],lambda t,a=tactic:t.apply(a),[tactic,side,alias,hp,cursor])
 # Gate reject branches: out-ofrange no draw, typedlow/high intelligence,
 # actual modifierbytes050F/6F02, and report sentinelwrites.
 for tactic in(1,5,9):
  for distance in(0,1,5,6,255):
   for phase in(0,3):
    for env in(0,1,2,255):
     b=fresh();record(b,0,iq=0);record(b,1,iq=255);b[0x601]=(10+distance)&255;b[0x50F]=phase;b[0x6F02]=env;b[0x50]=127
     compare('gate_branches',b,EFFECT_ENTRIES[tactic],lambda t,a=tactic:t.apply(a),[tactic,distance,phase,env])
 # HPhelper standalone: exactHP thresholds includingzero/zero whichremoves.
 zero_draw=next(i for i,v in enumerate(data.fixed_rng)if v==0)
 for hp in(0,1,5,10,100,255):
  for requested in(0,1,5,10,100,255):
   b=fresh();record(b,0,xp=14999,flags=0x62);record(b,1,hp=hp,war=255,iq=255,flags=0x12,troops=0xFFFF);b[0x50]=zero_draw
   target=0x63C0+12*b[0x665];b[0]=target&255;b[1]=target>>8;b[2]=requested
   for i,value in enumerate([1,11,10,5,1,11,10,5]):b[0x4D8+i]=value
   compare('HPhelper',b,0xB5D8,lambda t,v=requested:t.health_loss(v),[hp,requested])
 # ID9 exactdeath path and postremovalFF record writes, withcasterXP level
 # changes and all original6FB4AIwork bytes part of the8KSRAM comparison.
 for alias in('distinct','same_record','same_slot'):
  for xp in(0,999,14999,49999,65535):
   for level in(0,6,7,15):
    b=fresh();b[0x50]=zero_draw
    if alias=='same_record':b[0x665]=b[0x664]
    if alias=='same_slot':b[0x509]=0
    record(b,0,hp=1 if alias!='distinct'else 100,war=99,iq=99,xp=xp,flags=(level<<4)|2,troops=0xFFFF)
    if alias=='distinct':record(b,1,hp=1,war=255,iq=255,xp=65535,flags=0xF2,troops=0xFFFF)
    # EqualIQ can lowerprobability, but the original permutation draw0passes.
    target=b[0x509];b[0x4D8]=target;b[0x4DC]=target;b[0x4DB]=b[0x4DF]=5
    compare('rockfall_internal_FF_record',b,0xB3B6,lambda t:t.apply(9),[alias,xp,level])
 # Grainhelper word boundaries, actual side0/2 and saturatingreport.
 for side in(0,2):
  for grain in(0,1,50,9999,65535):
   for requested in(0,1,50,9999,65535):
    b=fresh();b[0x522+side]=grain&255;b[0x523+side]=grain>>8;b[0x10]=requested&255;b[0x11]=requested>>8
    compare('grain_helper',b,0xB6F0,lambda t,a=requested,s=side:t.grain_loss(a,side_offset=s),[side,grain,requested],{'y':side})
 # Fire-arrow factor/IQ fullhandleruses grain, targetofficer remainsunchanged.
 for side in(0,128):
  for grain in(0,1,50,9999,65535):
   for iq in(0,4,5,99,255):
    b=fresh();record(b,0,iq=iq,flags=0xF2);record(b,1,iq=0);b[0x50]=zero_draw;b[0x504]=side;offset=0 if side else 2
    b[0x522+offset]=grain&255;b[0x523+offset]=grain>>8
    compare('fire_arrow_grain_formula',b,0xB243,lambda t:t.apply(5),[side,grain,iq])
 # Strictsourceguards/requiredactualprelude, not originalout-of-tableCPU.
 for tactic in(0,2,15,255):
  b=fresh();m=clone(b)
  try:IndividualTactics(m,data).apply(tactic)
  except ValueError:guards.append('unsupported'+str(tactic))
  else:raise AssertionError('missingIDguard')
 b=fresh();record(b,1,hp=0);m=clone(b);source=IndividualTactics(m,data);source.health_loss(0)
 before=m[:];result=source.after_death_graphics(map_refresh_returned=False);assert m==before and result['status']=='dependency';guards.append('false_map_refresh_never_acknowledged')
 try:source.after_death_graphics()
 except TypeError:guards.append('map_refresh_signal_required')
 else:raise AssertionError('missingrequiredmaprefreshsignal')
 for name,prepare,call,exc_type in[
  ('initial_actor20',lambda m:m.__setitem__(0x50A,20),lambda t:t.apply(1),ValueError),
  ('initial_officer237',lambda m:m.__setitem__(0x664,237),lambda t:t.apply(5),ValueError),
  ('grain_side_offset1',lambda m:None,lambda t:t.grain_loss(10,side_offset=1),ValueError),
  ('missing_death_pending',lambda m:None,lambda t:t.after_death_graphics(map_refresh_returned=True),RuntimeError),
  ('unknown_HP_continuation',lambda m:None,lambda t:t.health_loss(0,continuation='unknown'),ValueError)]:
  m=clone(fresh());prepare(m);before=m[:]
  try:call(IndividualTactics(m,data))
  except exc_type:assert m==before;guards.append(name)
  else:raise AssertionError('missingguard'+name)
 out.mkdir(parents=True,exist_ok=True)
 result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),source_guards=guards,failures=failures,samples=samples,graphics_services=graphics_services,
             original_complete_case_count=sum(n for k,n in counts.items()if k.endswith('_complete')),original_death_prefix_case_count=sum(n for k,n in counts.items()if k.endswith('_death_prefix')),original_post_graphics_suffix_case_count=sum(n for k,n in counts.items()if k.endswith('_after_actual_map_refresh_suffix')),compared_SRAM_bytes=8192,declared_RAM_ranges=DECLARED_RAM_RANGES,original_instruction_locations=len(coverage),source_sha256=hashlib.sha256((ROOT/'source/recovered/tactic_individual_effects.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             source_uses_IR_or_original_CPU=False,asynchronous_graphics_acknowledged=False,contract='All8KSRAM and declared gameRAM; CPUflags/registers/stack/arithmeticwork/mapper/video outside semantic scope; fatalprefix and suffixseparate with actualoriginalD6CC precedingservice',
             limits=['apply assumes actual B02B resultreset.','Deathgraphicalcall remains explicit dependency in game source; validatorreally executes its originalcall and supplies only changedhostbytes before pure resume.','Initialselected officer domain0..236; legitimate postdeathFF record6FB4 preserved ratherthan repaired.','No naturalcampaign/nativegraphics/completeNMI claim from these CPUfixtures.'])
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(bank=b,cpu=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts','original_instruction_locations')},indent=2))
 if failures:print(json.dumps(failures[:8],ensure_ascii=False,indent=2));raise SystemExit(1)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/individual');a=p.parse_args();verify(a.rom.read_bytes(),a.out)
