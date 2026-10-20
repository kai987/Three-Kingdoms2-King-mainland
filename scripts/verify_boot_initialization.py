#!/usr/bin/env python3
"""Original reset/probe CPU versus direct source with explicit port inputs."""
from pathlib import Path
from collections import deque,Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.boot_initialization import BootInitialization,ROM_SHA256
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.service_memory import ServiceMemory
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class InputBus(PortBus):
 def __init__(self,rom,inputs,fault=None):
  super().__init__(rom);self.inputs={a:deque(v)for a,v in inputs.items()};self.port_reads=[];self.fault=fault
 def __getitem__(self,address):
  if isinstance(address,slice):return super().__getitem__(address)
  key=0x2000+(address&7)if 0x2000<=address<0x4000 else address
  if key in self.inputs:
   if not self.inputs[key]:raise RuntimeError(f'Explicit original port inputs exhausted {key:04X}')
   value=self.inputs[key].popleft();self.port_reads.append(dict(address=address,value=value))
   if key==0x2002:self.ppu_latch=0
   return value
  if 0x2000<=address<0x6000:raise RuntimeError(f'Undeclared original hardware read {address:04X}')
  return super().__getitem__(address)
 def __setitem__(self,address,value):
  if address==self.fault:return
  super().__setitem__(address,value)
class FaultMemory(ServiceMemory):
 def __init__(self,*args,fault=None,**kwargs):super().__init__(*args,**kwargs);self.fault=fault
 def __setitem__(self,address,value):
  if address==self.fault:return
  super().__setitem__(address,value)
def pattern():
 out=[];v=170
 for _ in range(8192):
  out.append(v);v=(5*v+1)&255
  if v==0:v=1
 return bytes(out)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 out=ROOT/'analysis/phase14/boot';out.mkdir(parents=True,exist_ok=True);rng=random.Random(0x14E000);counts=Counter();completion_kinds=Counter();groups=Counter();fails=[];rows=[];visited=set();guards=[];read_count=0
 def compare(group,entry,ram,sram,inputs,regs,reset=False,halt=False,fault=None):
  nonlocal read_count
  b=InputBus(rom,inputs,fault);b.ram[:]=ram;b.sram[:]=sram;b.banks=[0,1,30,31];b.bank_initialized=[True]*4;b.protect=64;b.record_ports=True
  m=FaultMemory(rom,ram,sram,tuple(b.banks),read_ports=inputs,fault=fault);r=NMIRegisters(**regs,pc=entry);cpu=MPU(memory=b,pc=entry);b.cpu=cpu
  for k in ('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  if not reset:
   for bus in(b,m):bus[0x100+((r.sp+1)&255)]=0x67;bus[0x100+((r.sp+2)&255)]=0x24
  src=BootInitialization(m,rom);res=src.run_reset(r)if reset else src.run_service(entry,r);resumes=0
  try:
   while res['status']=='dependency'and res['dependency']['category']!='terminal_boot_diagnostic':
    assert resumes<200 and res['dependency']['category']in ('PPUSTATUS_wait_set','PPUSTATUS_wait_clear'),res
    res=src.resume();resumes+=1
   expected='dependency'if halt else'reset_boundary'if reset else'returned';assert res['status']==expected,res
   boundary=0xF41E if halt else 0xE066 if reset else 0x2468
   for n in range(600000):
    if cpu.pc==boundary and n:break
    visited.add((31,cpu.pc));b.pc=cpu.pc;b.step_no=n;cpu.step()
   else:raise AssertionError(f'Original boot budget {cpu.pc:04X}')
   rd=[(i,b.ram[i],m.ram[i])for i in range(2048)if b.ram[i]!=m.ram[i]];sd=[(i,b.sram[i],m.sram[i])for i in range(8192)if b.sram[i]!=m.sram[i]];rg={k:(getattr(cpu,k),getattr(r,k))for k in REGS if getattr(cpu,k)!=getattr(r,k)}
   assert not rd and not sd and not rg,dict(RAM=rd[:10],SRAM=sd[:6],regs=rg)
   assert b.ports==m.io_writes and b.port_reads==m.io_reads and b.banks==m.banks,dict(ports=b.ports[-8:],source_ports=m.io_writes[-8:])
   if reset and not halt:
    assert m.sram==sram and r.sp==255 and m[0x7A]==0 and m[0]==ram[0]and m[3]==ram[3]
    assert all(m.ram[i]==0 for i in range(4,2048)if i not in(0x1FE,0x1FF))
   if halt:
    assert res['dependency']['category']=='terminal_boot_diagnostic';assert len([x for x in m.io_writes if x['address']==0x2007])==32
   kind='strict_prefix'if halt else'complete_return';counts[kind]+=1;groups[group]+=1;completion_kinds['permanent_F41E_diagnostic'if halt else'reset_E066_boundary'if reset else'actual_caller_RTS']+=1;read_count+=len(m.io_reads)
   if sum(x['group']==group for x in rows)<12:rows.append(dict(group=group,entry=entry,initial_registers=regs,comparison=kind,boundary=boundary,original_instructions=n,explicit_hardware_read_count=len(m.io_reads),source_resumes=resumes,final_registers=vars(r),SRAM_changed=m.sram!=sram,diagnostic_palette_color=r.x if halt else None,declared_SRAM_write_fault=fault))
  except Exception as e:
   fails.append(dict(group=group,entry=entry,registers=regs,error=str(e)));print(json.dumps(fails[-1]),flush=True)
 base_ram=bytes(rng.randrange(256)for _ in range(2048));base_sram=bytes(rng.randrange(256)for _ in range(8192));reg=lambda p=32,sp=253:dict(a=17,x=63,y=99,p=p,sp=sp)
 for seed in range(2 if a.quick else 12):
  ram=bytes(((i*17+seed*31)^seed)&255 for i in range(2048));sram=bytes(((i*7+seed*11)^85)&255 for i in range(8192))
  for sp in((253,)if a.quick else(0,1,127,253,255)):
   for flags in((32,)if a.quick else(32,33,96,225,40)):
    compare('reset_E000_preserves_SRAM_and_real_stack_replacement',0xE000,ram,sram,{0x2002:[128,0]*8,0x4017:[0,0]},reg(flags,sp),reset=True)
 for delay in(1,2,3,8):compare('both_vblank_levels_explicit_resumable_waits',0xE000,base_ram,base_sram,{0x2002:([0]*delay+[128]*delay+[0])*8,0x4017:[0,0]},reg(225,77),reset=True)
 matching=[((rom[16+31*8192+0x13BD+i]&1)^1)<<1 for i in range(70)]
 for mismatch in(range(3)if a.quick else range(70)):
  seq=matching[:mismatch]+[matching[mismatch]^2]
  for sp in((253,)if a.quick else(0,127,253,255)):
   compare('every_controller_echo_mismatch_position',0xF3BD,base_ram,base_sram,{0x4017:seq},reg(96,sp))
 for value in(range(8)if a.quick else range(256)):
  ram=bytearray(base_ram);ram[0]=value;compare('all_nonzero_byte_recurrence_inputs',0xF468,ram,base_sram,{},reg(33))
 for sp in(0,1,127,253,255):compare('prepare_pattern_existing_caller_frames',0xF458,base_ram,base_sram,{},reg(96,sp))
 good=pattern()
 for index in(-1,0,1,255,256,4096,8191):
  sram=bytearray(good)
  if index>=0:sram[index]^=1
  compare('whole_8K_pattern_success_or_first_mismatch',0xF422,base_ram,sram,{},reg(225))
 compare('write_entire_pattern_with_declared_writable_SRAM',0xF43F,base_ram,base_sram,{},reg(96))
 for kind,sram,fault in [('matching_pattern',good,None),('rewrite_needed',bytes(8192),None),('declared_write_fault',bytes(8192),0x6010)]:
  compare('diagnostic_palette_and_permanent_halt_'+kind,0xF3BD,base_ram,sram,{0x4017:matching},reg(32),halt=True,fault=fault)
 # Strict guards are never original-CPU success counts.
 for method in('run_reset','run_service'):
  src=BootInitialization(ServiceMemory(rom),rom)
  try:src.run_reset()if method=='run_reset'else src.run_service(0xF3BD)
  except ValueError:guards.append('actual_registers_required_'+method)
  else:raise AssertionError('Missing caller accepted')
 m=ServiceMemory(rom);r=NMIRegisters(sp=77,pc=0xE000);src=BootInitialization(m,rom);v=src.run_reset(r);assert v['status']=='dependency'and r.pc==0xE00C and r.sp==77;guards.append('missing_PPU_input_stops_without_fabricated_vblank')
 r.sp=76;v=src.resume();assert v['status']=='dependency'and r.pc==0xE00C;guards.append('paused_register_context_must_be_restored')
 m=ServiceMemory(rom);r=NMIRegisters(sp=253,pc=0xF3BD);m[0x1FE]=0x67;m[0x1FF]=0x24;src=BootInitialization(m,rom);call=ServiceCall(0xF3BD,0x2468,'caller',r,m,tuple(m.banks),255);assert src(call)['status']=='dependency'and r.pc==0xF3E2
 other=ServiceCall(0xF3BD,0x2468,'other',r,m,tuple(m.banks),255);assert src(other)['status']=='dependency';guards.append('pending_probe_actual_call_owner_retained')
 assert src(ServiceCall(0xE001,0x2468,'unknown',r,m,tuple(m.banks),255))['status']=='dependency';guards.append('unknown_entry_not_owned')
 source='source/recovered/boot_initialization.py';ranges=[]
 for lo,hi in[(0xE000,0xE066),(0xF3BD,0xF477)]:
  offset=16+31*8192+(lo&8191);raw=rom[offset:offset+hi-lo];ranges.append(dict(physical_bank=31,cpu_start=lo,cpu_end_exclusive=hi,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
 evidence=dict(status='passed',rom_sha256=ROM_SHA256,source_path=source,source_sha256=sha(ROOT/source),analyzer_path='scripts/verify_boot_initialization.py',analyzer_sha256=sha(Path(__file__)),ranges=ranges,REA_archive='analysis/rea/pairs/pair-27',REA_functions=['analysis/rea/mcp/functions/0xe000.asm','analysis/rea/mcp/functions/0xf3bd.asm','analysis/rea/mcp/functions/0xf422.asm','analysis/rea/mcp/functions/0xf43f.asm','analysis/rea/mcp/functions/0xf458.asm','analysis/rea/mcp/functions/0xf468.asm'],source_original_CPU_callbacks=0,source_IR_interpretation=False,limits=['Controlled explicit status/4017 inputs are not native internal hardware traces.','Direct SRAM helper fixtures declare all8K writable; the full diagnostic selects actualF800=40 before writes.','The third diagnostic case uses an explicit single-address SRAM write-fault environment, not an observed native hardware fault.','E000 software begins after the hardware RESET entry sequence and transfers to nextE066, not a callerRTS.'])
 evidence['source_and_validator_sha256']={f:sha(ROOT/f)for f in[source,'scripts/verify_boot_initialization.py','source/recovered/battle_nmi_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py',*evidence['REA_functions']]};(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
 receipt=dict(status='passed'if not fails else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),complete_return_count=counts['complete_return'],strict_prefix_count=counts['strict_prefix'],source_guard_case_count=len(guards),counts=dict(counts),completion_kinds=dict(completion_kinds),group_case_counts=dict(groups),failed_count=len(fails),failures=fails,guards=guards,source_path=source,source_sha256=sha(ROOT/source),validator_path='scripts/verify_boot_initialization.py',validator_sha256=sha(Path(__file__)),evidence_sha256=sha(out/'evidence.json'),comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,registers='AXYP/SP/PC',ordered_IO_reads_and_writes=True,mapper_banks=True,full_stack_included=True),source_original_CPU_callbacks=0,source_IR_interpretation=False,explicit_hardware_read_count=read_count,rows=rows,complete_reset_meaning='Actual original E066 pre-dispatch boundary with SPFF; not an RTS or complete hardware frame',limits=evidence['limits'])
 (out/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n');print(json.dumps(dict(status=receipt['status'],CPU=sum(counts.values()),counts=dict(counts),guards=len(guards),failed=len(fails))));return bool(fails)
if __name__=='__main__':raise SystemExit(main())
