#!/usr/bin/env python3
"""Unchanged original CPU versus independent five-phase title intro graphics; no helper oracle."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.title_intro_graphics import TitleIntroGraphics,TitleIntroData,InvalidTitleIntroPhase,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall

class OriginalBus(Bus):
 def __init__(self,rom,ram,sram,banks):
  super().__init__(rom,'zero');self.ram[:]=ram;self.sram[:]=sram;self.banks[:]=banks;self.bank_initialized=[True]*4;self.protect=0x4C;self.ports=[]
 def __setitem__(self,a,v):
  if ServiceMemory.is_write_port(a&65535):self.ports.append(dict(address=a&65535,value=v&255))
  super().__setitem__(a,v)
 def __getitem__(self,a):
  if isinstance(a,int)and 0x2000<=a<0x6000:raise RuntimeError('Details closure has no hardware reads')
  return super().__getitem__(a)
SCOPE=tuple(range(0x1B4))+tuple(range(0x200,0x800))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/title-intro');p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 data=TitleIntroData.from_rom(rom);rng=random.Random(0x120012);counts=Counter();fail=[];samples=[];visited=set();source_locations=set();guards=[];helper_targets=Counter()
 initial=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(initial)+'-ram.bin').read_bytes();base_sram=Path(str(initial)+'-sram.bin').read_bytes()
 def fresh(phase=0,index=0,timer=0,button=0,cursor=0):
  ram=bytearray(base_ram);sram=bytearray(base_sram);ram[0x540]=0;ram[0x541]=phase;ram[0x543]=index;ram[0x544]=timer;ram[0x81]=button;ram[0x7C]=cursor
  ram[0xE1:0xE4]=bytes((33,55,56));ram[0x1FE:0x200]=bytes((0x67,0x24));return ram,sram
 def compare(kind,entry,ram,sram,label,sp=253,p=32):
  ram[0x100+((sp+1)&255)]=0x67;ram[0x100+((sp+2)&255)]=0x24
  actual=OriginalBus(rom,ram,sram,[1,23,24,31]);source=ServiceMemory(rom,ram,sram,(1,23,24,31))
  r=NMIRegisters(a=ram[0x51],x=31,y=63,p=p,sp=sp,pc=entry);ctrl=TitleIntroGraphics(source,data);cpu=MPU(memory=actual,pc=entry);actual.cpu=cpu
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  try:
   result=ctrl.run_entry(entry,r);assert result['status']=='returned',result
   for n in range(200000):
    if n and cpu.pc==0x2468 and cpu.sp==(sp+2)&255:break
    actual.pc=cpu.pc;actual.step_no=n;origin=actual.origin(cpu.pc)
    if origin:visited.add((origin[0],cpu.pc))
    cpu.step()
   else:raise AssertionError(f'Original CPU budget ${cpu.pc:04X}')
   rd=[(hex(i),actual.ram[i],source.ram[i])for i in sorted(set(SCOPE)|set(range(0x100+sp+1,0x200)))if actual.ram[i]!=source.ram[i]]
   sd=[(hex(i+0x6000),actual.sram[i],source.sram[i])for i in range(8192)if actual.sram[i]!=source.sram[i]]
   assert not rd and not sd,('memory',rd[:8],sd[:4])
   rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not rg,('registers',rg);assert actual.banks==source.banks;assert actual.ports==source.io_writes,('ports',actual.ports,source.io_writes)
   counts[kind]+=1;source_locations.update(ctrl.source_locations);helper_targets.update(e['target']for e in result['events']if e.get('kind')=='callback_return')
   if sum(s['kind']==kind for s in samples)<2:samples.append(dict(kind=kind,input=label,entry=entry,original_instructions=n,active_caller_RAM_addresses=list(range(0x100+sp+1,0x200)),compared_RAM_bytes=len(set(SCOPE)|set(range(0x100+sp+1,0x200))),registers=result['registers'],queued_packet=source.ram[0x380:0x3A4].hex(' '),row_after=source[0x40D],PPU_jobs_after=source[0x7E]))
  except Exception as exc:fail.append(dict(kind=kind,entry=entry,input=label,error=str(exc)))
 for phase in range(5):
  for button in(0,8,255):
   for timer in(0,1,2,31,32,63,64,255):
    for index in(range(24)if not a.quick else(0,20,23)):
     ram,sram=fresh(phase,index,timer,button);compare('five_intro_phases_timer_frame_start',0xA021,ram,sram,[phase,index,timer,button])
 for index in range(24):
  for cursor in(0,4,176,240,248,252,255):
   ram,sram=fresh(1,index,2,cursor=cursor);compare('frame_descriptors_OAM_capacity',0xA021,ram,sram,[index,cursor])
 for index in range(24):
  for sp in(243,246,248):
   ram,sram=fresh(1,index,2);compare('actual_caller_SP_boundaries',0xA021,ram,sram,[index,sp],sp=sp,p=(32,33,160)[sp%3])
 # Guard clauses are source-only contracts, not original CPU cases.
 ram,sram=fresh();m=ServiceMemory(rom,ram,sram,(1,23,24,31));c=TitleIntroGraphics(m,data)
 for name,action in [('unknown_entry',lambda:c.run_entry(0xA003,NMIRegisters())),('actual_caller_required',lambda:c.tick())]:
  try:action();passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 m[0x541]=5
 try:c.tick(NMIRegisters());passed=False
 except InvalidTitleIntroPhase:passed=True
 guards.append(dict(name='sixth_unproved_phase_rejected',passed=passed))
 unknown=ServiceCall(0x8123,0x2468,'unknown',NMIRegisters(pc=0x8123),m,tuple(m.banks),255);guards.append(dict(name='unowned_callee_remains_dependency',passed=c(unknown)['status']=='dependency'))
 for name,entry,phase,index,aval in(('sequence_index24',0xA021,1,24,0),('frameID15',0xDEFA,0,0,15)):
  ram,sram=fresh(phase,index);m=ServiceMemory(rom,ram,sram,(1,23,24,31));c=TitleIntroGraphics(m,data)
  try:c.run_entry(entry,NMIRegisters(a=aval));passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 fail.extend(dict(kind='sourceguard',guard=g)for g in guards if not g['passed']);a.out.mkdir(parents=True,exist_ok=True)
 providers=[ROOT/'source/recovered'/f'{n}.py'for n in('title_intro_graphics','scene_shared_services','audio_services','battle_graphics_services','battle_nmi_services','controller_helpers','service_memory')]
 report=dict(schema='phase13-title-intro-graphics-v1',status='passed'if not fail else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),original_complete_case_count=sum(counts.values()),original_prefix_case_count=0,source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(fail),counts=dict(counts),
  comparison=dict(RAM_bytes=len(SCOPE),RAM_addresses=SCOPE,additional_active_caller_stack='entrySP+1..1FF, variable by actualcaller; default2bytes',SRAM_bytes=8192,free_CPU_stack_residue='excluded by reused frozenAudioServices contract; palette0100..013F andunit01B0..01B3 included',registers='AXYP/SP/PC',all_mapper_banks=True,exact_IO_ports=True),source_original_CPU_callbacks=0,source_IR_interpretation=False,active_caller_frame_byte_count_range=[2,12],fixture_provenance=dict(base=str(initial.relative_to(ROOT)),RAM_sha256=hashlib.sha256(base_ram).hexdigest(),SRAM_sha256=hashlib.sha256(base_sram).hexdigest(),prepared_fields='0540/1/3/4 intro conditions;81 buttons/7C OAMcursor; mapped physical1+23/24 withmatchingE1..E3; actualRTS frame andSP/flags'),
  pure_recovered_helper_call_counts={hex(k):v for k,v in helper_targets.items()},source_sha256=sha(providers[0]),validator_sha256=sha(Path(__file__)),dependency_pins=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p))for p in providers],guards=guards,failures=fail,samples=samples)
 (a.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(a.out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n');(a.out/'source-executed-locations.json').write_text(json.dumps(sorted(source_locations),indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],CPU=sum(counts.values()),guards=len(guards),failed=len(fail),failures=fail[:8]),ensure_ascii=False));return bool(fail)
if __name__=='__main__':raise SystemExit(main())
