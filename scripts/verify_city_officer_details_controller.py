#!/usr/bin/env python3
"""Unchanged original CPU versus independent five-phase city card controller; no helper oracle."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.city_officer_details_controller import CityOfficerDetailsController,CityOfficerData,InvalidCityCardPhase,ROM_SHA256
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
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/city-details');p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 data=CityOfficerData.from_rom(rom);rng=random.Random(0x120012);counts=Counter();fail=[];samples=[];visited=set();source_locations=set();guards=[];helper_targets=Counter()
 initial=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(initial)+'-ram.bin').read_bytes();base_sram=Path(str(initial)+'-sram.bin').read_bytes()
 def fresh(phase=2,row=255,selected=0,busy=0,ident=131):
  ram=bytearray(base_ram);sram=bytearray(base_sram);ram[0x400]=12;ram[0x401]=phase;ram[0x402]=0;ram[0x40D]=row;ram[0x40C]=selected;ram[0x408]=selected;ram[0x409]=ram[0x40A]=0
  ram[0x410:0x41A]=bytes((ident,47,109,131,139,191,236,0,1,255));ram[0x7E]=busy;ram[0x7C]=0;ram[0xA4]=0;ram[0x4BC]=0;ram[0x81]=ram[0x83]=0;ram[0x140]=ram[0x150]=ram[0x472]=0;ram[0x470]=0;ram[0x471]=1;ram[0x473]=0
  ram[0xE1:0xE4]=bytes((49,57,58));ram[0x1FE:0x200]=bytes((0x67,0x24));return ram,sram
 def compare(kind,entry,ram,sram,label,sp=253,p=32):
  ram[0x100+((sp+1)&255)]=0x67;ram[0x100+((sp+2)&255)]=0x24
  actual=OriginalBus(rom,ram,sram,[17,25,26,31]);source=ServiceMemory(rom,ram,sram,(17,25,26,31))
  r=NMIRegisters(a=ram[0x51],x=31,y=63,p=p,sp=sp,pc=entry);ctrl=CityOfficerDetailsController(source,data);cpu=MPU(memory=actual,pc=entry);actual.cpu=cpu
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  try:
   result=ctrl.run_entry(entry,r);assert result['status']=='returned',result
   for n in range(200000):
    if n and cpu.pc==0x2468 and cpu.sp==(sp+2)&255:break
    actual.pc=cpu.pc;actual.step_no=n;origin=actual.origin(cpu.pc)
    if origin:visited.add((origin[0],cpu.pc))
    cpu.step()
   else:raise AssertionError(f'Original CPU budget ${cpu.pc:04X}')
   rd=[(hex(i),actual.ram[i],source.ram[i])for i in range(2048)if actual.ram[i]!=source.ram[i]]
   sd=[(hex(i+0x6000),actual.sram[i],source.sram[i])for i in range(8192)if actual.sram[i]!=source.sram[i]]
   assert not rd and not sd,('memory',rd[:8],sd[:4])
   rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not rg,('registers',rg);assert actual.banks==source.banks;assert actual.ports==source.io_writes,('ports',actual.ports,source.io_writes)
   counts[kind]+=1;source_locations.update(ctrl.source_locations);helper_targets.update(e['target']for e in result['events']if e.get('kind')=='callback_return')
   if sum(s['kind']==kind for s in samples)<2:samples.append(dict(kind=kind,input=label,entry=entry,original_instructions=n,registers=result['registers'],queued_packet=source.ram[0x380:0x3A4].hex(' '),row_after=source[0x40D],PPU_jobs_after=source[0x7E]))
  except Exception as exc:fail.append(dict(kind=kind,entry=entry,input=label,error=str(exc)))
 for phase in range(5):
  for buttons in(range(256)if not a.quick else(0,1,2,3,16,32,255)):
   for jobs in(0,4):
    ram,sram=fresh(phase,selected=1,busy=jobs);ram[0x81]=buttons;ram[0x83]=buttons
    compare('five_phases_all_button_bytes_real_queue_busy',0xA021,ram,sram,[phase,buttons,jobs])
 for ident in(range(237)if not a.quick else(0,109,131,236)):
  for phase in(1,2,3):
   for row in((0,3,6,7,9,255)if not a.quick else(0,255)):
    ram,sram=fresh(phase,row,ident=ident);compare('all237_card_rows_and_selected_portrait',0xA021,ram,sram,[ident,phase,row])
 for city in range(30):
  for mode in(0,1,2):
   ram,sram=fresh(0);ram[0x402]=city
   roster=bytes((255 if mode==0 else (131 if i%2==0 else 255)if mode==1 else i)for i in range(10));sram[city*32+17:city*32+27]=roster
   compare('all30_city_compaction_empty_sparse_full',0xA021,ram,sram,[city,mode])
 for selected in range(10):
  for direction in(0,16,32,48):
   for sentinel in(0,255):
    ram,sram=fresh(2,selected=selected);ram[0x83]=direction
    if selected<9:ram[0x411+selected]=sentinel
    compare('roster_navigation_first_last_empty_next',0xA021,ram,sram,[selected,direction,sentinel])
 for direction in(0,1):
  for offset in range(81):
   for row in(0,9,255):
    ram,sram=fresh(4,row,selected=1);ram[0x409]=offset;ram[0x40A]=direction;ram[0x40C]=2 if direction==0 else 0
    compare('both80pixel_transitions_all_boundaries',0xA021,ram,sram,[direction,offset,row])
 for notification in(0,1,2,9,10,11,127,128,255):
  for panel in(0,128):
   ram,sram=fresh(2);ram[0x472]=notification;ram[0x140]=panel
   compare('real_panel_job_readiness_and_notification_phases',0xA021,ram,sram,[notification,panel])
 # The seven remaining original branches: forced notification0 andscroll wrap.
 ram,sram=fresh(2);ram[0x470]=1;ram[0x81]=1;compare('notification_zero_true_A_entry',0xA021,ram,sram,[1,1])
 for direction in(0,1):
  for scroll in(238,239,240,255):
   ram,sram=fresh(4,255,selected=1);ram[0x40A]=direction;ram[0x98]=scroll
   compare('original_scroll_wrap_boundaries',0xA021,ram,sram,[direction,scroll])
 # Guard clauses are source-only contracts, not original CPU cases.
 ram,sram=fresh();m=ServiceMemory(rom,ram,sram,(17,25,26,31));c=CityOfficerDetailsController(m,data)
 for name,action in [('unknown_entry',lambda:c.run_entry(0xA003,NMIRegisters())),('actual_caller_required',lambda:c.tick())]:
  try:action();passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 m[0x401]=5
 try:c.tick(NMIRegisters());passed=False
 except InvalidCityCardPhase:passed=True
 guards.append(dict(name='sixth_unproved_phase_rejected',passed=passed))
 unknown=ServiceCall(0x8123,0x2468,'unknown',NMIRegisters(pc=0x8123),m,tuple(m.banks),255);guards.append(dict(name='unowned_callee_remains_dependency',passed=c(unknown)['status']=='dependency'))
 ram,sram=fresh(1,0,busy=4);m=ServiceMemory(rom,ram,sram,(17,25,26,31));c=CityOfficerDetailsController(m,data);before=bytes(m.ram[0x380:0x3A4]);result=c.tick(NMIRegisters(sp=253))
 guards.append(dict(name='producer_never_acknowledges_busy_tile_packet',passed=result['status']=='returned'and m[0x7E]==4 and m[0x40D]==0 and bytes(m.ram[0x380:0x3A4])==before))
 fail.extend(dict(kind='sourceguard',guard=g)for g in guards if not g['passed']);a.out.mkdir(parents=True,exist_ok=True)
 providers=[ROOT/'source/recovered'/f'{n}.py'for n in('city_officer_details_controller','officer_details_ui_services','portrait_ui_services','scene_initialization','scene_shared_services','officer_ui_services','battle_nmi_services','controller_helpers','service_memory')]
 report=dict(schema='phase13-city-officer-controller-v1',status='passed'if not fail else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),original_complete_case_count=sum(counts.values()),original_prefix_case_count=0,source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(fail),counts=dict(counts),
  comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,free_CPU_stack_residue='included',registers='AXYP/SP/PC',all_mapper_banks=True,exact_IO_ports=True),source_original_CPU_callbacks=0,source_IR_interpretation=False,
  fixture_provenance=dict(base=str(initial.relative_to(ROOT)),RAM_sha256=hashlib.sha256(base_ram).hexdigest(),SRAM_sha256=hashlib.sha256(base_sram).hexdigest(),prepared_fields='phase/row/roster/selected/scroll/buttons/actual queue/notification condition; realRTS callerframe; mapper pair25/26 andmatchingE1..E3'),pure_recovered_helper_call_counts={hex(k):v for k,v in helper_targets.items()},source_sha256=sha(providers[0]),validator_sha256=sha(Path(__file__)),dependency_pins=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p))for p in providers],guards=guards,failures=fail,samples=samples)
 (a.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(a.out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n');(a.out/'source-executed-locations.json').write_text(json.dumps(sorted(source_locations),indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],CPU=sum(counts.values()),guards=len(guards),failed=len(fail),failures=fail[:8]),ensure_ascii=False));return bool(fail)
if __name__=='__main__':raise SystemExit(main())
