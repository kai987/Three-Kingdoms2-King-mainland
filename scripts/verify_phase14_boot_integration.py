#!/usr/bin/env python3
"""Reset and title-restart through the pure GameEngine; original CPU is oracle only.

Native checkpoints provide RAM/SRAM, never CPU registers or caller frames.
Explicit PPUSTATUS/controller inputs exercise the E000 software boundary; no
hardware RESET microsequence, frame clock, NMI acknowledgement or RTS is faked.
"""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_boot_initialization import InputBus
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
REGS=('a','x','y','p','sp','pc')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def regs(r):return {k:getattr(r,k)for k in REGS}
def verify(rom,out):
 assert sha(rom)==ROM_SHA256
 files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_phase14_boot_integration.py','scripts/verify_boot_initialization.py','scripts/verify_battle_graphics_services.py','scripts/trace_startup.py']
 pins={f:file_sha(ROOT/f)for f in files};counts=Counter();rows=[];failures=[];guards=[];artifacts={}
 def fresh(ram,sram,inputs,banks=(0,1,30,31)):
  b=InputBus(rom,inputs);b.ram[:]=ram;b.sram[:]=sram;b.banks=list(banks);b.bank_initialized=[True]*4;b.protect=64;b.record_ports=True
  m=ServiceMemory(rom,ram,sram,banks,read_ports=inputs);game=GameEngine(m,rom=rom,mapped=True);co=game.readable_scene_rules();assert co.external_callback is None
  return b,m,game,co
 def original(b,initial,entry,boundary=0xE066,sp=255):
  cpu=MPU(memory=b,pc=entry);b.cpu=cpu
  for k,v in initial.items():setattr(cpu,k,v)
  cpu.pc=entry
  for n in range(600000):
   if n and cpu.pc==boundary and cpu.sp==sp:return cpu,n
   assert b.origin(cpu.pc)is not None,f'Original entered RAM {cpu.pc:04X}'
   b.pc=cpu.pc;b.step_no=n;cpu.step()
  raise AssertionError(f'Original budget {cpu.pc:04X}')
 def equal(b,m,r,cpu):
  rd=[(i,b.ram[i],m.ram[i])for i in range(2048)if b.ram[i]!=m.ram[i]];sd=[(i,b.sram[i],m.sram[i])for i in range(8192)if b.sram[i]!=m.sram[i]]
  rg={k:[getattr(cpu,k),getattr(r,k)]for k in REGS if getattr(cpu,k)!=getattr(r,k)}
  assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:8],registers=rg)
  assert b.ports==m.io_writes and b.port_reads==m.io_reads and b.banks==m.banks,'Ordered hardware/banks differ'
 def run_case(label,ram,sram,initial,mode='reset',delayed=False):
  try:
   inputs={0x2002:[128,0]*8,0x4017:[0,0]};b,m,game,co=fresh(ram,sram,{}if delayed else inputs,(0,10,11,31)if mode.startswith('title')else(0,1,30,31))
   # This is a declared genuine return-frame fixture, not native captured AXYP.
   if mode.startswith('title'):
    for bus in(b,m):bus[0x1FE]=255;bus[0x1FF]=1
   r=NMIRegisters(**initial);before_title=co.controller(6);before_presentation=co.presentation;before_global=co.global_ui;prep=[]
   if mode=='title_phase0_then_restart':
    first=game.tick_readable_scene(r,scene=6);assert first['status']=='returned',first
    cpu,n=original(b,initial,0xA003,0x200,255);equal(b,m,r,cpu);assert m[0x541]==1
    prep.append(dict(entry=0xA003,original_instructions=n,comparison='actual_caller_RTS_title_phase0'))
    for bus in(b,m):bus[0x1FE]=255;bus[0x1FF]=1
    r.sp=253;r.pc=0xA003;initial=regs(r)
   entry=0xA003 if mode.startswith('title')else 0xE000
   result=game.tick_readable_scene(r,scene=6)if mode.startswith('title')else game.initialize_readable_boot(r)
   if delayed:
    assert result['status']=='dependency'and r.pc==0xE00C
    assert not m.io_reads and co.reset_epoch==0
    pending_boot=co.boot;pending_program=co.boot._program
    # Provide observations through the bus, not gameplay or completion writes.
    m.read_ports.update({k:deque(v)for k,v in inputs.items()});b.inputs.update({k:deque(v)for k,v in inputs.items()})
    result=game.resume_readable_boot();assert pending_boot._program is None and pending_program is not None
   assert result['status']=='reset_boundary'and result['retired_pending_callers']and co.reset_epoch==1,result
   cpu,n=original(b,initial,entry);equal(b,m,r,cpu)
   assert r.pc==0xE066 and r.sp==255 and m.sram==sram and not co._owners and not co._direct
   assert co.controller(6)is not before_title and co.presentation is not before_presentation and co.global_ui is not before_global
   assert m[0x7A]==0
   if not mode.startswith('title'):assert m[0]==ram[0]and m[3]==ram[3]
   counts['reset_E066_boundary']+=1
   rows.append(dict(case=label,mode=mode,entry=entry,initial_registers=initial,comparison='reset_E066_boundary',original_instructions=n,original_preparation=prep,source_status='reset_boundary',registers=regs(r),source_original_CPU_callbacks=0,source_calls=co.calls,
    comparison_scope=dict(RAM_bytes=2048,SRAM_bytes=8192,free_stack_residue='included',AXYP_SP_PC=True,ordered_IO_reads_and_writes=True,banks=True),SRAM_unchanged=True,retired_callers=True,old_UI_RTI_or_RTS=False,late_hardware_input_resume=delayed))
   try:game.resume_readable_boot()
   except RuntimeError:pass
   else:raise AssertionError('Retired reset generator resumable')
  except Exception as exc:
   failures.append(dict(case=label,error=str(exc)));print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 # Declared cold/warm CPU fixtures vary retained scratch, battery and entry SP.
 for seed in range(3):
  ram=bytes((i*17+seed*31)&255 for i in range(2048));sram=bytes(((i*7+seed*11)^85)&255 for i in range(8192))
  for sp in(0,127,253):run_case(f'explicit-reset-{seed}-{sp}',ram,sram,dict(a=17,x=63,y=99,p=40 if seed==0 else 225,sp=sp,pc=0xE000))
 run_case('late-declared-PPUSTATUS-resume-same-owner',ram,sram,dict(a=17,x=63,y=99,p=32,sp=77,pc=0xE000),delayed=True)
 manifest=ROOT/'analysis/phase14/runtime/evidence.json';artifacts[str(manifest.relative_to(ROOT))]=file_sha(manifest)
 # Native SRAM supplies a retained warm game; core_reset is independently observed.
 native=ROOT/'analysis/phase14/runtime/core-reset-battery-retention'
 for label in('before-core-reset',):
  rp=native/(label+'-ram.bin');sp=native/(label+'-sram.bin');raw=rp.read_bytes();saved=sp.read_bytes()
  artifacts[str(rp.relative_to(ROOT))]=sha(raw);artifacts[str(sp.relative_to(ROOT))]=sha(saved)
  run_case('native-battery-input-explicit-E000-caller',raw,saved,dict(a=76,x=raw[0x7C],y=0,p=32,sp=253,pc=0xE000))
 # Genuine title phase0 first returns; its next callback is a nonreturning E000 tail.
 for mode in('title_phase1_restart','title_phase0_then_restart'):
  ram=bytearray(2048);ram[0]=93;ram[3]=45;ram[0x78]=6;ram[0x7A]=10;ram[0x540]=4;ram[0x541]=0 if mode.endswith('then_restart')else 1
  run_case(mode,bytes(ram),saved,dict(a=76,x=0,y=0,p=32,sp=253,pc=0xA003),mode)
 # Source-only guards are not CPU case counts.
 m=ServiceMemory(rom);game=GameEngine(m,rom=rom,mapped=True)
 try:game.initialize_readable_boot(None)
 except ValueError:guards.append('actual_reset_registers_required')
 else:raise AssertionError('Missing reset registers accepted')
 try:game.resume_readable_boot()
 except RuntimeError:guards.append('no_pending_reset_cannot_resume')
 else:raise AssertionError('Missing pending reset accepted')
 after={f:file_sha(ROOT/f)for f in files};assert pins==after,'Source changed during matrix; rerun after freeze'
 receipt=dict(schema='phase14-pure-boot-integration-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),complete_return_count=0,reset_boundary_count=counts['reset_E066_boundary'],strict_prefix_count=0,source_guard_case_count=len(guards),counts=dict(counts),failed_count=len(failures),failures=failures,rows=rows,guards=guards,
  source_original_CPU_callbacks=0,source_IR_interpretation=False,production_fallback=False,native_internal_CPU_trace=False,source_sha256=pins,artifact_sha256=artifacts,source_dependency_hashes_stable_during_run=True,
  preparation_CPU_comparisons_within_cases=sum(len(row['original_preparation'])for row in rows),
  limits=['E066 is the nonreturning reset software handoff, not RTS or full hardware RESET/NMI/frame completion.','Native checkpoints supply RAM/SRAM; AXYP,SP,caller frame and port sequence are declared independent CPU fixtures.','Nested title callback reset must retire old presentation/controller/main generators. No readiness bytes or fake RTS are installed.','Original CPU executes only the oracle side. Source composes readable functions on explicit ServiceMemory; no PPU/PCM/frame timing equivalence.'])
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:receipt[k]for k in('status','rom_cpu_case_count','reset_boundary_count','source_guard_case_count','failed_count')}),flush=True);return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase14/boot-integration.json');a=p.parse_args();r=verify(a.rom.read_bytes(),a.out);raise SystemExit(bool(r['failed_count']))
