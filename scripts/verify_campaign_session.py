#!/usr/bin/env python3
"""Original CPU versus explicit readable main/NMI/IRQ session sequences.

Accepted interrupts are declared fixture inputs, never scheduled scanlines.
The same register object and source owner remain live across pending services.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
REGS=('a','x','y','p','sp','pc')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);args=p.parse_args();rom=args.rom.read_bytes();assert sha(args.rom)==ROM_SHA256
 out=ROOT/'analysis/phase15/session';out.mkdir(parents=True,exist_ok=True)
 files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_campaign_session.py'];pins={f:sha(ROOT/f)for f in files}
 rows=[];failures=[];guards=[];counts=Counter();native=ROOT/'analysis/phase11/runtime/cold-battle/city-commands';raw=Path(str(native)+'-ram.bin').read_bytes();saved=Path(str(native)+'-sram.bin').read_bytes()
 def memory(ram):return ServiceMemory(rom,ram,saved,(16,10,11,31),read_ports={0x2002:0,0x5800:127},repeat_read_ports=(0x2002,0x5800),controller_buttons=(0,0))
 def pair(ram,sp=255):
  a=memory(ram);b=memory(ram);r=NMIRegisters(a=17,x=31,y=63,p=32,sp=sp,pc=0xE066);c=MPU(memory=a)
  for k,v in reg(r).items():setattr(c,k,v)
  game=GameEngine(b,rom=rom,mapped=True);session=game.readable_campaign(r)
  return a,b,r,c,game,session
 def original(c,r,*,stop=None,limit=1500000):
  for n in range(limit):
   if n and((stop(c)if stop else(c.pc==r.pc and c.sp==r.sp))):return n
   assert c.pc>=0x8000,'Unexpected original RAM execution';c.step()
  raise RuntimeError(f'Original event budget {c.pc:04X}')
 def equal(a,b,r,c):
  rd=[(i,a.ram[i],b.ram[i])for i in range(2048)if a.ram[i]!=b.ram[i]];sd=[(i,a.sram[i],b.sram[i])for i in range(8192)if a.sram[i]!=b.sram[i]];rg={k:[getattr(c,k),getattr(r,k)]for k in REGS if getattr(c,k)!=getattr(r,k)}
  assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:8],registers=rg)
  assert a.io_reads==b.io_reads and a.io_writes==b.io_writes and a.banks==b.banks,'OrderedIO/banks differ'
 # Repeated real main2 initialization/decisions use a persistent source session.
 for ruler in range(7):
  for strategy in range(3):
   ram=bytearray(raw);ram[0x7A]=2;ram[0x78]=2;ram[0xDE:0xE4]=bytes([48,42,43,48,59,60]);s=bytearray(saved)
   for address,value in{0x6F03:ruler,0x6F02:strategy,0x6F8B:0,0x6F5B:0,0x6F5D:30,0x6F62:0}.items():s[address-0x6000]=value
   ram[0xEE]=7+8*ruler;ram[0xEF]=0x6F
   a,b,r,c,g,session=pair(ram);a.sram[:]=s;b.sram[:]=s;stages=[]
   try:
    for cycle in range(4):
     result=session.main();assert result['status']=='returned',result
     n=original(c,r);equal(a,b,r,c);assert not session.pending and r.pc==0xE066 and r.sp==255
     stages.append(dict(cycle=cycle,original_instructions=n,request=b[0x6F8B],phase=b[0x6F5B],budget=b[0x6F5D]))
    counts['four_main2_updates_same_context']+=1;rows.append(dict(group='four_main2_updates_same_context',ruler=ruler,strategy=strategy,comparison='complete_return',completion_kind='main_E066_boundary',stages=stages,session_events=session.events,source_original_CPU_callbacks=0))
   except Exception as e:failures.append(dict(group='main2',ruler=ruler,strategy=strategy,error=str(e)))
 # Actual IRQ software interrupts a still-pending NMI, then genuine RTI and resume.
 for mode,start_row in [(6,0),(9,0),*[(m,row)for m in(1,7)for row in range(4)]]:
  for sp in(127,253,255):
   ram=bytearray(raw);ram[0x78]=0;ram[0x7B]=0;ram[0x69]=128;ram[0x61]=mode;ram[0x63]=start_row;ram[0xDE:0xE4]=bytes((48,42,43,48,42,43))
   a,b,r,c,g,session=pair(ram,sp);stages=[]
   try:
    result=session.nmi();assert result['status']=='dependency'and result['body']['dependency']['category']=='IRQ_software_flag'
    c.nmi();n=original(c,r,stop=lambda cpu:cpu.pc==0xFB28 and cpu.a==128);equal(a,b,r,c)
    phase=session.pending[-1];stages.append(dict(kind='NMI_wait',original_instructions=n,PC=r.pc,SP=r.sp))
    nested=session.nmi();assert nested['status']=='dependency'and nested['body']['dependency']['category']=='IRQ_software_flag'
    c.nmi();n=original(c,r,stop=lambda cpu:cpu.pc==r.pc and cpu.sp==r.sp and cpu.a==r.a);equal(a,b,r,c)
    nested_phase=session.pending[-1];assert len(session.pending)==2 and session.pending[0]is phase
    stages.append(dict(kind='accepted_nested_busy_NMI_wait',original_instructions=n,PC=r.pc,SP=r.sp))
    while b[0x62]!=0:
     assert len(stages)<12
     result=session.irq();assert result['status']=='returned';c.irq();n=original(c,r);equal(a,b,r,c)
     assert session.pending[-1]is nested_phase
     stages.append(dict(kind='actual_IRQ_RTI',original_instructions=n,PC=r.pc,SP=r.sp,flag62=b[0x62]))
    result=session.resume();assert result['status']=='returned';n=original(c,r);equal(a,b,r,c)
    assert session.pending[-1]is phase and len(session.pending)==1
    stages.append(dict(kind='same_nested_NMI_resume_RTI',original_instructions=n,PC=r.pc,SP=r.sp))
    result=session.resume();assert result['status']=='returned';n=original(c,r);equal(a,b,r,c);assert not session.pending and r.pc==0xE066 and r.sp==sp
    stages.append(dict(kind='same_NMI_resume_RTI',original_instructions=n,PC=r.pc,SP=r.sp))
    counts['NMI_IRQ_chain_then_same_owner_resume']+=1;rows.append(dict(group='NMI_IRQ_chain_then_same_owner_resume',IRQ_mode=mode,initial_row=start_row,caller_SP=sp,comparison='complete_return',completion_kind='actual_interrupt_RTI',stages=stages,session_events=session.events,source_original_CPU_callbacks=0))
   except Exception as e:failures.append(dict(group='NMI_IRQ_chain',mode=mode,row=start_row,sp=sp,error=str(e)))
 # Source guards preserve the current caller and bus; they are not CPU cases.
 for typ in('missing_registers','missing_service_bus'):
  try:GameEngine(ServiceMemory(rom)if typ=='missing_registers'else bytearray(65536),rom=rom).readable_campaign(None if typ=='missing_registers'else NMIRegisters())
  except ValueError:guards.append(typ)
  else:raise AssertionError(typ)
 a,b,r,c,g,session=pair(bytearray(raw));r.pc=0xA000
 before=(bytes(b.ram),bytes(b.sram),reg(r),list(b.io_writes))
 try:session.main()
 except ValueError:guards.append('actual_E066_entry_required')
 else:raise AssertionError('Entry accepted')
 assert before==(bytes(b.ram),bytes(b.sram),reg(r),list(b.io_writes))
 try:session.resume()
 except RuntimeError:guards.append('no_pending_owner_cannot_resume')
 else:raise AssertionError('No pending accepted')
 r.p|=4
 try:session.irq()
 except ValueError:guards.append('IRQ_mask_not_bypassed')
 else:raise AssertionError('IRQ mask bypassed')
 ram=bytearray(raw);ram[0x78]=0;ram[0x69]=128;ram[0x7B]=0;ram[0xDE:0xE4]=bytes((48,42,43,48,42,43));a,b,r,c,g,session=pair(ram)
 assert session.nmi()['status']=='dependency';before=(bytes(b.ram),bytes(b.sram),reg(r),list(b.io_writes))
 try:session.main()
 except RuntimeError:guards.append('pending_main_not_restarted')
 else:raise AssertionError('Pending restart')
 assert before==(bytes(b.ram),bytes(b.sram),reg(r),list(b.io_writes));r.sp=(r.sp-1)&255
 try:session.resume()
 except ValueError:guards.append('mutated_paused_PC_SP_rejected')
 else:raise AssertionError('Mutated context')
 after={f:sha(ROOT/f)for f in files};assert pins==after,'Source changed during matrix, rerun after freeze'
 result=dict(schema='phase15-campaign-session-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,source_guard_case_count=len(guards),counts=dict(counts),failed_count=len(failures),failures=failures,guards=guards,rows=rows,source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256=pins,
  artifact_sha256={str(Path(str(native)+suffix).relative_to(ROOT)):sha(Path(str(native)+suffix))for suffix in('-ram.bin','-sram.bin')},comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC=True,ordered_IO_reads_writes_and_banks=True),
  limits=['Explicit CPU fixtures, not natural campaign or new originalcore frames.','Each repeated-main or NMI/IRQ chain is one parentCPUcase; nested stages are not counted again.','All actual interrupt arrivals/status values are caller-provided inputs; no scanline scheduling or framebuffer/audio synthesis.','Each accepted nested interrupt retains its independent source generator and real interrupted caller frame.'])
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','failures')}));raise SystemExit(bool(failures))
if __name__=='__main__':main()
