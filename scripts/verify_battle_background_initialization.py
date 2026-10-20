#!/usr/bin/env python3
"""OriginalCPU comparisons of direct initial rows, full background and F09C."""
import argparse,hashlib,json,sys
from collections import Counter,deque
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.battle_background_initialization import BattleBackgroundInitialization,InitialRows
from source.recovered.battle_graphics_services import GraphicsRegisters,GraphicsData,ROM_SHA256
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall,ServiceWait
from source.recovered.service_memory import ServiceMemory
from source.recovered.scroll_graphics_services import DECLARED_RAM_ADDRESSES
from source.recovered.text_services import TextServices,TextData
OUT=ROOT/'analysis/phase11/background'
SCOPE=tuple(a for a in range(2048)if not 0x1B4<=a<0x1F9)

def verify(rom,out):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 base=ROOT/'analysis/runtime/phase3/attack-intro-7'
 br=Path(str(base)+'-ram.bin').read_bytes();bs=Path(str(base)+'-sram.bin').read_bytes()
 counts=Counter();failures=[];guards=[];samples=[];coverage=Counter()
 def fresh(x=0,y=0,cache=0,units=False):
  b=PortBus(rom);b.ram[:]=br;b.sram[:]=bs;b.banks=[17,23,24,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xDE:0xE4]=bytes([49,55,56,49,55,56]);b.ram[0x1FE:0x200]=bytes([255,1])
  b.ram[0x8E:0x92]=x.to_bytes(2,'little')+y.to_bytes(2,'little');b[0x9C]=cache;b[0x9D]=cache^255;b[0x7E]=0
  b.ram[0xA8:0xAA]=bytes([0,4]);b.ram[0x400:0x500]=bytes((16+i*7)%120 for i in range(256))
  b.ram[0x600:0x628]=bytes([255]*40);b[0x507]=0x10
  for ruler in range(7):b[0x6F0A+8*ruler]=ruler%3
  for slot in range(20):
   b[0x63C+slot]=slot%11;b[0x628+slot]=(slot%4)|((slot&1)<<7)
   if units:b[0x600+slot]=(x//16+slot%4)&31;b[0x614+slot]=(y//16+slot%5)&31
  return b
 def memory(b,readable=True):
  return ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0}if readable else{},repeat_read_ports=(0x2002,)if readable else())
 def original(b,entry,r,stop=0x200,prefix=None):
  cpu=MPU(memory=b,pc=entry);b.cpu=cpu;b.record_ports=True
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  for n in range(300000):
   if prefix is not None:
    pc,sp,jobs=prefix
    if cpu.pc==pc and cpu.sp==sp and(jobs is None or b.peek(0x7E)==jobs):break
   elif cpu.pc==stop:break
   b.pc=cpu.pc;bank,offset=b.origin(cpu.pc);coverage[(bank,cpu.pc,offset+16)]+=1;cpu.step()
  else:raise RuntimeError(f'Original background budget ${cpu.pc:04X}')
  return cpu,n
 def equal(b,m,cpu,registers,scope=SCOPE,full_return=True):
  keys=('a','x','y','p','sp','pc')if full_return else('a','x','y','p')
  assert all(getattr(cpu,k)==getattr(registers,k)for k in keys),('registers',{k:getattr(cpu,k)for k in keys},vars(registers))
  rd=[(hex(a),b.peek(a),m[a])for a in scope if b.peek(a)!=m[a]]
  sd=[(hex(0x6000+i),v,w)for i,(v,w)in enumerate(zip(b.sram,m.sram))if v!=w]
  assert not rd and not sd,(rd[:14],sd[:8]);assert b.ports==m.io_writes,(len(b.ports),len(m.io_writes),b.ports[:10],m.io_writes[:10])
  assert b.banks==m.banks,(b.banks,m.banks)
 def compare(kind,b,entry,meta,call,primitive=False):
  m=memory(b);bg=BattleBackgroundInitialization(m,rom);r=NMIRegisters(a=17,x=23,y=31,p=33,sp=0xFD)
  try:
   result=call(bg,r);cpu,n=original(b,entry,NMIRegisters(a=17,x=23,y=31,p=33,sp=0xFD))
   equal(b,m,cpu,r,scope=DECLARED_RAM_ADDRESSES if primitive else SCOPE,full_return=not primitive)
   assert result['status']=='returned',result['status'];counts[kind]+=1
   if kind=='complete31_row_background':assert bg.row_pairs==31 and len(bg.events)==62
   if sum(s['kind']==kind for s in samples)<12:
    samples.append(dict(kind=kind,input=meta,entry=entry,original_instructions=n,
                        returned_registers={k:getattr(cpu,k)for k in('a','x','y','p','sp','pc')},
                        row_pairs=bg.row_pairs,fast_PPU_calls=len(bg.events),port_write_count=len(m.io_writes),
                        ordered_ports_sha256=hashlib.sha256(json.dumps(m.io_writes,separators=(',',':')).encode()).hexdigest(),
                        camera_after=list(m.ram[0x8E:0x96]),cache9C9D_after=list(m.ram[0x9C:0x9E])))
  except Exception as exc:
   failures.append(dict(kind=kind,input=meta,error=str(exc)))
   if len(failures)<=6:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 for x in(0,15,252,256):
  for y in(0,112):
   for cache in(0,255):
    for units in(False,True):
     b=fresh(x,y,cache,units)
     compare('direct_A485_tile_row',b,0xA485,[x,y,cache,units],lambda bg,r:bg.rows.tile_row(r),True)
     b=fresh(x,y,cache,units)
     compare('direct_AD9F_attribute_row',b,0xAD9F,[x,y,cache,units],lambda bg,r:bg.rows.attribute_row(r),True)
 for x in(0,15,252,256):
  for y in(0,112):
   for units in(False,True):
    b=fresh(x,y,255,units)
    compare('complete31_row_background',b,0xA009,[x,y,units],lambda bg,r:bg.run_entry(registers=r))
 # F09C preserves caller clip/tile parameters and returns through that caller.
 for flags in(0,64,128,192):
  for offset in(0,17,255):
   for clip in(0,1,240,255):
    for capacity in(0,252,255):
     b=fresh();b[0]=0;b[1]=4;b[2]=flags;b[3]=offset;b[4]=clip;b[0xA]=100;b[0xB]=0;b[0xC]=100;b[0xD]=0;b[0x7C]=capacity
     b.ram[0x400:0x409]=bytes([8,6,2,255,255,7,3,0,128])
     compare('F09C_original_caller_return',b,0xF09C,[flags,offset,clip,capacity],
             lambda bg,r:bg(ServiceCall(0xF09C,0x200,'call',r,bg.memory,tuple(bg.memory.banks),0xFF)))
 # Actual prefix at missing PPUSTATUS; then explicit input resumes the same
 # independent consumer without replaying preceding port writes.
 for x in(0,252):
  b=fresh(x,0,255,True);m=memory(b,False);bg=BattleBackgroundInitialization(m,rom);r=NMIRegisters(a=17,x=23,y=31,p=33,sp=0xFD)
  try:
   result=bg.run_entry(registers=r);assert result['status']=='dependency' and bg.pending is not None
   cpu,n=original(b,0xA009,NMIRegisters(a=17,x=23,y=31,p=33,sp=0xFD),prefix=(r.pc,r.sp,None));equal(b,m,cpu,r)
   counts['missing_hardware_strict_prefix']+=1
   writes=list(m.io_writes);state=vars(r).copy();assert bg.resume()['status']=='dependency' and m.io_writes==writes and vars(r)==state
   m.read_ports[0x2002]=deque([0]);m.repeat_read_ports.add(0x2002);assert bg.resume()['status']=='returned'
   # Original finishes after the same already-recorded prefix; no new CPU
   # comparator is counted for this source ownership/continuation check.
   for _ in range(300000):
    if cpu.pc==0x200:break
    b.pc=cpu.pc;cpu.step()
   else:raise RuntimeError('Original resume did not return')
   equal(b,m,cpu,r);guards.append('missing_status_resumes_without_duplicate_ports_'+str(x))
  except Exception as exc:failures.append(dict(kind='missing_hardware',x=x,error=str(exc)))
 # A real low-bit text job cannot be consumed by EEE6. Pausing preserves it.
 b=fresh();b[0x7E]=1;b[0x304]=0;b[0x300]=255;b[0x34E]=128
 b[0x303]=b[0x308]=b[0x5E]=0
 m=memory(b);bg=BattleBackgroundInitialization(m,rom);r=NMIRegisters(a=17,x=23,y=31,p=33,sp=0xFD)
 try:
  result=bg.run_entry(registers=r);assert result['status']=='dependency' and isinstance(bg.pending,ServiceWait)
  cpu,n=original(b,0xA009,NMIRegisters(a=17,x=23,y=31,p=33,sp=0xFD),prefix=(r.pc,r.sp,m[0x7E]));equal(b,m,cpu,r)
  counts['unconsumed_low_job_strict_prefix']+=1
  writes=list(m.io_writes);before=bytes(m.ram);assert bg.resume()['status']=='dependency' and m.io_writes==writes and bytes(m.ram)==before
  # The frozen real text consumer clears its own well-formed empty text job;
  # the test never directly writes an acknowledgement/ready flag.
  text_result=TextServices(m,TextData.from_rom(rom)).consume_text()
  assert text_result['status']=='returned' and text_result['text_job_consumed'],text_result
  # At this prefix EEE6 consumed the tile request only. Text owns bit0;
  # the still-pending attribute bit10 belongs to the next real EEE6 call.
  assert m[0x7E]==0x10 and m[0x304]==255,(m[0x7E],m[0x304])
  assert bg.resume()['status']=='returned' and m[0x7E]==0
  guards.append('low_job_requires_actual_text_consumer_then_pending_attribute_consumer')
 except Exception as exc:failures.append(dict(kind='remaining_low_job',error=str(exc)))
 result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),
             actual_ROM_CPU_comparison_count=sum(counts.values()),counts=dict(counts),failed_count=len(failures),failures=failures,
             source_guard_case_count=len(guards),source_guards=guards,samples=samples,
             case_count=sum(counts.values())+len(guards),original_complete_case_count=sum(counts.values())-counts['missing_hardware_strict_prefix']-counts['unconsumed_low_job_strict_prefix'],
             original_prefix_case_count=counts['missing_hardware_strict_prefix']+counts['unconsumed_low_job_strict_prefix'],
             complete_background_row_pairs=31,default_empty_queue_fast_PPU_calls=62,
             declared_RAM_addresses=SCOPE,compared_RAM_bytes=len(SCOPE),all_SRAM_compared_bytes=8192,
             row_primitive_RAM_addresses=DECLARED_RAM_ADDRESSES,inactive_stack_residue_excluded=[0x1B4,0x1F9],
             active_saved_camera_and_caller_stack_compared=True,complete_body_AXYP_SP_PC_compared=True,row_primitive_AXYP_compared=True,
             ordered_ports_compared=True,banks_compared=True,source_original_CPU_callbacks=0,source_IR_interpretation=False,
             actual_frames_or_fake_ack_or_PCM_synthesized=False,PPUSTATUS_input='explicit0 for full cases; absent thenexplicit0 for two resumable cases',
             fixture_provenance=dict(base=str(base.relative_to(ROOT)),RAM_sha256=hashlib.sha256(br).hexdigest(),SRAM_sha256=hashlib.sha256(bs).hexdigest(),
                                     prepared_fields='camera/cache,256legalchunkIDs RAM descriptor at0400,unit coordinates/hundreds/rulers,caller;F09C uses its separate typed sprite descriptor'),
             source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in('source/recovered/battle_background_initialization.py','source/recovered/scroll_graphics_services.py','source/recovered/battle_graphics_services.py','source/recovered/battle_nmi_services.py','source/recovered/text_services.py','source/recovered/service_memory.py','scripts/verify_battle_background_initialization.py','scripts/analyze_battle_background_initialization.py')},
             dynamic_original_instruction_locations=len(coverage),limits=['Row methods have a body-end AXYP contract; caller owns RTS. Full background and F09C service adapter compare actual callerPC/SP.',
                                                                       'Inactive CPU stack residue excluded; real palette,scrollbuffers,unittiles,activecamera/caller stack included.',
                                                                       'The low-job consumer/resume suffix is a source-only ownership check, not another complete originalCPU comparison.'])
 out.mkdir(parents=True,exist_ok=True);(out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False))
 if failures:raise SystemExit(1)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=OUT);a=p.parse_args();verify(a.rom.read_bytes(),a.out)
