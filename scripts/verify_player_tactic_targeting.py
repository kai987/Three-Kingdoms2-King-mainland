#!/usr/bin/env python3
"""Execute actual AD80/ADA4/AA03 targeting bytes and compare pure source."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.player_tactic_targeting import PlayerTacticTargeting,TargetingData,ROM_SHA256,DECLARED_RAM_RANGES
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
RAM=[a for lo,hi in DECLARED_RAM_RANGES for a in range(lo,hi)]
def verify(rom,out):
 data=TargetingData.from_rom(rom);counts=Counter();coverage=Counter();samples=[];failures=[];guards=[];native_inputs=[]
 p=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(p)+'-ram.bin').read_bytes();sram=Path(str(p)+'-sram.bin').read_bytes()
 def fresh():
  b=Bus(rom,'alternating');b.ram[:]=ram;b.sram[:]=sram;b.banks=[6,12,13,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xDE:0xE4]=bytes([38,44,45,38,44,45]);b.ram[0x1FE:0x200]=bytes([255,1]);b[0x50A]=0;b[0x509]=1;b[0x504]=0
  for i in range(20):b[0x600+i]=b[0x614+i]=255;b[0x628+i]=0;b[0x664+i]=255
  b[0x664]=8;b[0x665]=191;b[0x600]=10;b[0x614]=10;b[0x601]=11;b[0x615]=10;b[0x629]=128
  b[0x4D8]=b[0x4DC]=255;addr=0x63C0+12*8;b[addr+8]=100;b[addr+9]=0
  return b
 def clone(b):
  m=bytearray(65536);m[:2048]=b.ram;m[0x6000:0x8000]=b.sram;return m
 def compare(group,b,tactic,entry,call,meta,*,y=0,stops=None):
  m=clone(b);source=PlayerTacticTargeting(m,data,data_window_bank=b.banks[0]);c=MPU(memory=b,pc=entry);c.sp=0xFD;c.p=32;c.y=y;b.cpu=c
  try:
   result=call(source)
   for n in range(100000):
    if c.pc in(stops or{0x200}):break
    b.pc=c.pc;b.step_no=n;origin=b.origin(c.pc)
    if origin is None:raise RuntimeError(f'Unexpected RAMPC{c.pc:04X}')
    bank,offset=origin;coverage[(bank,c.pc,offset)]+=1;c.step()
   else:raise RuntimeError('CPU budget')
   carry=bool(c.p&1)if stops is None else c.pc==0xAA1D
   rd=[(a,b.peek(a),m[a])for a in RAM if b.peek(a)!=m[a]];sd=[(0x6000+i,a,v)for i,(a,v)in enumerate(zip(b.sram,m[0x6000:0x8000]))if a!=v]
   assert not rd and not sd and result['carry']==carry,(rd[:8],sd[:8],result,carry,hex(c.pc))
   counts[group]+=1
   if sum(r['group']==group for r in samples)<16:samples.append(dict(group=group,tactic=tactic,input=meta,result=result,original_end_pc=c.pc))
  except Exception as exc:
   failures.append(dict(group=group,tactic=tactic,input=meta,error=str(exc)))
   if len(failures)>=5:raise
 # All16 exact predicates, actual side/neighbor/map helpers; terrain classes
 # are the legitimate prelude output byte domain with extremebyte also tested.
 classes=(0,1,2,3,4,5,6,7,8,255)
 for tactic in range(16):
  for tt in classes:
   for at in classes:
    b=fresh();b[0x543]=tactic;b[0xA]=tt;b[0xB]=at
    compare('predicate_suffix',b,tactic,0xADA4,lambda t,i=tactic,x=tt,z=at:t.eligibility_suffix(i,x,z),[tt,at])
 # Repeatedmatching coordinates (highestslot), side signs, explicitneighbor
 # bytes, Y15gap and fullword troop thresholds. No implicitactiveID filtering.
 for tactic in(6,7,9,10,11,12,13,14):
  for side in(0,128):
   for geometry in('same','right','left','down','up','gap_down','corner','far'):
    for duplicate in(False,True):
     b=fresh();b[0x543]=tactic;b[0x504]=side;b[0xA]=3 if tactic in(10,12)else(5 if tactic==6 else 0);b[0xB]=5 if tactic in(9,13)else 0
     ax,ay,tx,ty={'same':(10,10,10,10),'right':(11,10,10,10),'left':(9,10,10,10),'down':(10,11,10,10),'up':(10,9,10,10),'gap_down':(10,16,10,14),'corner':(0,0,1,0),'far':(18,18,10,10)}[geometry]
     b[0x600]=ax;b[0x614]=ay;b[0x601]=tx;b[0x615]=ty
     b[0x602]=(tx+1)&255;b[0x616]=ty;b[0x62A]=side^128;b[0x666]=33
     if duplicate:b[0x613]=b[0x602];b[0x627]=ty;b[0x63B]=side # higher matching friendly wins
     compare('neighbor_side_gap_suffix',b,tactic,0xADA4,lambda t,i=tactic,x=b[0xA],z=b[0xB]:t.eligibility_suffix(i,x,z),[side,geometry,duplicate])
 for side in(0,128):
  for troops in(0,1,99,100,101,255,256,1023,1024,65535):
   for cache in(0,19,255):
    b=fresh();b[0x543]=11;b[0x504]=side;b[0xA]=b[0xB]=0;addr=0x63C0+12*8;b[addr+8]=troops&255;b[addr+9]=troops>>8;b[0x4D8+(4 if side else 0)]=cache
    compare('ambush_raw16_cache_suffix',b,11,0xADA4,lambda t:t.eligibility_suffix(11,0,0),[side,troops,cache])
 # Full AD80terrainprelude on the actual city4 descriptor and all16handlers.
 for tactic in range(16):
  for actor_xy,target_xy in[((19,14),(18,14)),((19,14),(20,14)),((5,16),(4,16)),((2,16),(3,17)),((0,0),(1,0)),((31,19),(30,19)),((16,16),(15,14)),((128,255),(255,128))]:
   b=fresh();b[0x543]=tactic;b[0x600],b[0x614]=actor_xy;b[0x601],b[0x615]=target_xy
   compare('full_AD80',b,tactic,0xAD80,lambda t,i=tactic:t.eligible(i),[actor_xy,target_xy])
 # Guarded ROMdescriptor has a realcurrentbank, and every internalF266 read
 # changes the logical datawindow, just like the CPU. Use bank6 citydescriptor.
 banks=set(data.chunk_banks)|{6}
 descriptor=0x8000+next(i for i in range(0x1FFD)if all(all(v<120 for v in data.data_pages[bank][i:i+4])for bank in banks))
 for tactic in range(16):
  b=fresh();b[0x543]=tactic;b[0xA8]=descriptor&255;b[0xA9]=descriptor>>8
  compare('ROM_descriptor_full_AD80',b,tactic,0xAD80,lambda t,i=tactic:t.eligible(i),[descriptor,6])
 # Exact AA03 gameplayprefix stops before UI message procedures. The cursor
 # enemyfilter was performed before AA03, and ID11 entered withselftarget.
 for tactic in range(16):
  for distance in(0,1,5,6):
   b=fresh();b[0x543]=tactic;b[0x601]=(10+distance)&255;target=0 if tactic==11 else 1;b[0x509]=target
   compare('cursor_AA03_prefix',b,tactic,0xAA03,lambda t,i=tactic,tar=target:t.can_target(i,0,tar),[distance,target],y=target,stops={0xAA1D,0xAA12,0xAA29})
 # Actual DC4B/CMPFF enemy-filter failure leaves previous0509 untouched.
 for side in(0,128):
  for target_flag in(0,127,128,255):
   if (side^target_flag)&128:continue
   b=fresh();b[0x543]=9;b[0x504]=side;b[0x629]=target_flag;b[0x509]=2
   compare('cursor_enemy_filter_prefix',b,9,0xA9FC,lambda t:t.can_target(9,0,1),[side,target_flag,2],y=1,stops={0xAA28})
 # Reuse formal original-core snapshots asCPUinputs. These comparisons do
 # not rerun the nativecore or substitute CPUfixture successfornativeevidence.
 for tactic,dirname in [(i,f'tactic-{i:02}')for i in(1,5,7,8,9,10,12,14)]+[(1,'tactic-01-death'),(9,'tactic-09-levelup')]:
  folder=ROOT/'analysis/phase9/runtime'/dirname
  confirmed=(folder/'cast-confirmation-ram.bin').read_bytes();target=confirmed[0x509];actor=confirmed[0x50A]
  for label,group,prefix in [('cast-confirmation','native_confirmed_full_AD80',False),('target-cursor','native_cursor_AA03_prefix',True)]:
   rpath=folder/(label+'-ram.bin');spath=folder/(label+'-sram.bin');b=fresh();b.ram[:]=rpath.read_bytes();b.sram[:]=spath.read_bytes()
   bank=b[0xDE]&63;b.banks=[bank%32,12,13,31];b.ram[0xDE:0xE4]=bytes([bank,44,45,bank,44,45]);b.ram[0x1FE:0x200]=bytes([255,1])
   header=folder/(label+'.json');metadata=json.loads(header.read_text());assert metadata['rom_sha256']==ROM_SHA256
   native_inputs.append(dict(tactic_id=tactic,case=dirname,label=label,header_path=str(header.relative_to(ROOT)),header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),RAM_path=str(rpath.relative_to(ROOT)),RAM_sha256=hashlib.sha256(rpath.read_bytes()).hexdigest(),SRAM_path=str(spath.relative_to(ROOT)),SRAM_sha256=hashlib.sha256(spath.read_bytes()).hexdigest(),current_data_bank=bank%32,actor_slot=actor,confirmed_target_slot=target))
   if prefix:
    b[0x509]=target;b[0x50A]=actor;b[0x543]=tactic
    compare(group,b,tactic,0xAA03,lambda t,i=tactic,a=actor,z=target:t.can_target(i,a,z),[tactic,label,actor,target],y=target,stops={0xAA1D,0xAA12,0xAA29})
   else:compare(group,b,tactic,0xAD80,lambda t,i=tactic:t.eligible(i),[tactic,label,actor,target])
 # Illegal tableindices/context are rejected onlyby source, neverrunOriginal.
 for name,call in [('ID16',lambda t:t.eligible(16)),('IDnegative',lambda t:t.eligible(-1)),('slot20',lambda t:t.can_target(9,20,1)),('unknown_ROM_descriptor',lambda t:t.eligible(9)),('chunk120',lambda t:t.eligible(9)),('bank32',lambda t:t.eligible(9,data_window_bank=32))]:
  m=clone(fresh())
  if name=='unknown_ROM_descriptor':m[0xA8]=0x54;m[0xA9]=0x8C
  if name=='chunk120':pointer=m[0xA8]|m[0xA9]<<8;m[pointer:pointer+4]=bytes([120]*4)
  try:call(PlayerTacticTargeting(m,data))
  except ValueError:guards.append(name)
  else:raise AssertionError('Missing guard'+name)
 out.mkdir(parents=True,exist_ok=True)
 v=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),original_complete_case_count=sum(n for k,n in counts.items()if not k.endswith('_prefix')),original_prefix_case_count=sum(n for k,n in counts.items()if k.endswith('_prefix')),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,samples=samples,guards=guards,native_snapshot_inputs=native_inputs,
        compared_SRAM_bytes=8192,declared_RAM_ranges=DECLARED_RAM_RANGES,original_instruction_locations=len(coverage),source_sha256=hashlib.sha256((ROOT/'source/recovered/player_tactic_targeting.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),contract='All8KSRAM plus declaredRAM and originalreturnedcarry; CPUotherflags/registers/mapper/stack/arithmeticwork excluded; AA03prefix stops beforeactualUI messages',effects_probability_or_AP_consumption=False)
 (out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(bank=b,cpu=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
 print(json.dumps({k:v[k]for k in('status','rom_cpu_case_count','original_complete_case_count','original_prefix_case_count','source_guard_case_count','failed_count','counts')},indent=2));return v
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/targeting');a=p.parse_args();v=verify(a.rom.read_bytes(),a.out)
 if v['failed_count']:raise SystemExit(1)
