#!/usr/bin/env python3
"""Compare readable shared scene services with the pinned original6502."""
import argparse,hashlib,json,random,sys
from collections import Counter,deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.scene_shared_services import SceneSharedServices,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 rng=random.Random(0x11C0DE);counts=Counter();failures=[];samples=[];visited=Counter();guards=[]
 def fresh():
  b=PortBus(rom);b.ram[:]=rng.randbytes(2048);b.sram[:]=rng.randbytes(8192);b.banks=[17,12,13,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0x1FE:0x200]=bytes([255,1]);b.ram[0xE1:0xE4]=bytes([49,44,45]);b.ram[0x7C]=0;b.ram[0x7E]=0
  b.ram[0x400:0x416]=bytes([0,16,1,0,128,1,2,3,128,128,128,128,128,128,128,128,128,128,128,128,128,128]);b.ram[0:5]=bytes([0,4,0,0,240])
  b.ram[0xA:0xE]=bytes([40,0,80,0]);b.ram[0x8E:0x92]=bytes([0]*4)
  return b
 def compare(group,entry,prepare=None,regs=None,stop=0x200):
  b=fresh();prepare and prepare(b);reg=regs or {};r=NMIRegisters(a=reg.get('a',17),x=reg.get('x',31),y=reg.get('y',63),p=reg.get('p',32),sp=253,pc=entry)
  mem=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0},repeat_read_ports=(0x2002,));owners={}
  def callback(call):
   if id(call)not in owners:owners[id(call)]=SceneSharedServices(mem,rom,callbacks=callback)
   return owners[id(call)](call)
  service=SceneSharedServices(mem,rom,callbacks=callback)
  cpu=MPU(memory=b,pc=entry);cpu.a=r.a;cpu.x=r.x;cpu.y=r.y;cpu.p=r.p;cpu.sp=r.sp;b.cpu=cpu;b.record_ports=True
  try:
   result=service.run_service(entry,r);assert result['status']=='returned',result
   for n in range(100000):
    if cpu.pc==stop:break
    b.pc=cpu.pc;b.step_no=n;origin=b.origin(cpu.pc)
    if origin:visited[(origin[0],cpu.pc,origin[1]+16)]+=1
    cpu.step()
   else:raise RuntimeError(f'Original service budget ${cpu.pc:04X}')
   scope=[*range(0x140),*range(0x200,0x800)]
   diff=[(hex(i),b.ram[i],mem.ram[i])for i in scope if b.ram[i]!=mem.ram[i]]
   rd=[(k,getattr(cpu,k),getattr(r,k))for k in ('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not diff and bytes(b.sram)==bytes(mem.sram),diff[:12]
   assert not rd,rd;assert b.ports==mem.io_writes,(b.ports[:10],mem.io_writes[:10],len(b.ports),len(mem.io_writes));assert b.banks==mem.banks
   counts[group]+=1
   if len([s for s in samples if s['group']==group])<5:samples.append(dict(group=group,entry=entry,inputs=reg,instructions=n,port_writes=len(mem.io_writes),output_registers=vars(r).copy()))
  except Exception as exc:
   failures.append(dict(group=group,entry=entry,inputs=reg,error=str(exc)))
   if len(failures)<=8:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 vals=(0,1,14,15,99,127,128,255)if a.quick else range(256)
 for entry in (0xF26D,0xF283,0xF28B,0xF293,0xF29B):
  for value in vals:compare('real_message_requests',entry,regs={'a':value})
 for entry in (0xF2AF,0xF2D7,0xF368,0xF387):
  for value in vals:compare('record_pointers',entry,regs={'a':value})
 for entry in (0xE843,0xE84B,0xE850,0xE856,0xE85C,0xE862,0xE87A,0xE88A,0xE89A,0xE8AA):
  for cursor in vals:
   bounds=(1,14,15,100,255)if entry==0xE862 else(99,)
   for bound in bounds:
    compare('RNG_and_rejection_bounds',entry,lambda b,c=cursor:b.ram.__setitem__(slice(0x50,0x56),bytes([c]*6)),{'a':bound,'x':cursor,'p':32|(cursor&~8)})
 for entry in (0xECBF,0xECEE,0xE749,0xE74D,0xE753,0xE768):
  for value in vals:compare('palette_transition_and_display_control',entry,lambda b,v=value:b.ram.__setitem__(0x8B,v),{'a':value})
 for entry in (0xE774,0xE7DF,0xE7B5):
  for high in(32,36,40):compare('complete_nametable_clear',entry,regs={'a':high})
 numbers=(0,1,9,10,99,100,255,999,1000,65535,999999,1000000,16777215)
 for value in numbers:
  compare('destructive_packed_decimal',0xE9BA,lambda b,v=value:b.ram.__setitem__(slice(1,4),v.to_bytes(3,'little')))
  for divisor in (0,1,3,100,255,65535):
   for entry in(0xEA7C,0xEAA5):
    def setup(b,v=value,d=divisor,e=entry):
     b.ram[0:3]=v.to_bytes(3,'little');b.ram[3:5]=d.to_bytes(2,'little')
     if e==0xEA7C:b.ram[1:3]=(v&65535).to_bytes(2,'little')
    compare('long_division_and_zero',entry,setup)
 for value in numbers:
  for factor in(0,1,3,100,255):
   for entry in(0xEBE9,0xEBCA):compare('multiply_and_percentage',entry,lambda b,v=value,f=factor:b.ram.__setitem__(slice(0,4),v.to_bytes(3,'little')+bytes([f])))
 for columns in(1,2,3,4,8):
  for buttons in vals:
   for wrap in(0,1):
    def setup(b,c=columns,v=buttons,w=wrap):
     b.ram[0x10:0x12]=bytes([0,4]);b.ram[0x400:0x420]=bytes([i%8 for i in range(c*3)]+[255]*(32-c*3));b.ram[0x424:0x426]=bytes([c-1,2]);b.ram[0x81]=v;b.ram[0x12]=w
    compare('menu_navigation_and_sentinels',0xED19+5*(columns-1),setup)
 for entry in(0xF092,0xF1AD):
  for value in vals:compare('original_sprite_helpers',entry,lambda b,v=value:b.ram.__setitem__(2,v),{'x':value,'p':32|(value&~8)})
 for entry in (0xE57F,0xE609,0xE66B,0xE673,0xE67B,0xE683,0xE68B,0xE693,0xE69B):
  for sequence in(0,13,18,29):compare('real_audio_request_protocol',entry,regs={'a':sequence})
 for selector in(40,44,55,61):
  def setup_far(b):
   b.ram[0x1FE:0x200]=bytes([255,3]);b.ram[0x400:0x402]=bytes([0x6D,0xF2])
  compare('real_inline_far_call_and_bank_restore',0xEE07,setup_far,{'a':17,'y':selector},stop=0x402)
 # Source guards do not count as more originalCPUcases.
 b=fresh();mem=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));s=SceneSharedServices(mem,rom);r=NMIRegisters(sp=253,pc=0xE753)
 result=s.run_service(0xE753,r);assert result['status']=='dependency' and r.sp==253 and r.pc==0xE753
 writes=list(mem.io_writes);assert s.resume()['status']=='dependency' and mem.io_writes==writes
 mem.read_ports[0x2002]=deque([0]);result=s.resume();assert result['status']=='returned' and r.sp==255 and r.pc==0x200;guards.append('missing_PPSTATUS_preserves_then_returns_real_caller')
 b=fresh();mem=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));s=SceneSharedServices(mem,rom);r=NMIRegisters(a=0,sp=253,pc=0xE862)
 result=s.run_service(0xE862,r);assert result['status']=='dependency' and r.sp==253;guards.append('zero_rng_bound_is_real_nonterminating_dependency')
 for label,buttons,value in [('no_valid_menu_column',64,255),('no_menu_end_sentinel',16,1)]:
  b=fresh();b.ram[0x10:0x12]=bytes([0,6]);b.ram[0x600:0x700]=bytes([value]*256);b.ram[0x81]=buttons;b.ram[0x424:0x426]=bytes([0,0]);b.ram[0x12]=0
  mem=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));s=SceneSharedServices(mem,rom);r=NMIRegisters(sp=253,pc=0xED1E)
  result=s.run_service(0xED1E,r);assert result['status']=='dependency' and r.sp==253
  for _ in range(3):assert s.resume()['status']=='dependency'and r.sp==253 and r.pc in(0xED9E,0xEDCF)
  guards.append(label+'_repeated_resume_never_fakes_RTS')
 out=ROOT/'analysis/phase11/shared';out.mkdir(parents=True,exist_ok=True)
 result=dict(status='passed'if not failures else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,samples=samples,guards=guards,
  declared_RAM_addresses=[*range(0x140),*range(0x200,0x800)],all_SRAM_compared_bytes=8192,free_stack_residue_excluded=True,complete_return_registers_and_ordered_ports_compared=True,source_original_CPU_callbacks=0,source_IR_interpretation=False,
  source_sha256=hashlib.sha256((ROOT/'source/recovered/scene_shared_services.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(visited.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
