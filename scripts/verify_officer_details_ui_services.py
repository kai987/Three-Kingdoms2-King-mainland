#!/usr/bin/env python3
"""Unchanged original CPU versus independent ten-row details source; no helper oracle."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.officer_details_ui_services import OfficerDetailsUIServices,OfficerDetailsData,InvalidDetailRow,ROM_SHA256
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
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase12/details');p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 data=OfficerDetailsData.from_rom(rom);rng=random.Random(0x120012);counts=Counter();fail=[];samples=[];visited=set();source_locations=set();guards=[];helper_targets=Counter()
 initial=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(initial)+'-ram.bin').read_bytes();base_sram=Path(str(initial)+'-sram.bin').read_bytes()
 def fresh(ident=131,row=0,selected=0,busy=0):
  ram=bytearray(base_ram);sram=bytearray(base_sram);ram[0x40D]=row;ram[0x40C]=selected;ram[0x410+selected]=ident;ram[0x7E]=busy;ram[0x401]=0
  ram[0x1FE:0x200]=bytes((0x67,0x24));return ram,sram
 def compare(kind,entry,ram,sram,label,sp=253,p=32):
  ram[0x100+((sp+1)&255)]=0x67;ram[0x100+((sp+2)&255)]=0x24
  actual=OriginalBus(rom,ram,sram,[17,25,26,31]);source=ServiceMemory(rom,ram,sram,(17,25,26,31))
  r=NMIRegisters(a=ram[0x51],x=31,y=63,p=p,sp=sp,pc=entry);ctrl=OfficerDetailsUIServices(source,data);cpu=MPU(memory=actual,pc=entry);actual.cpu=cpu
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
 for ident in(range(237)if not a.quick else(0,109,131,236)):
  for row in range(10):
   for busy in(0,4):
    ram,sram=fresh(ident,row,selected=ident%3,busy=busy);compare('all237_officers_all10_rows_busy_and_available',0xA012,ram,sram,[ident,row,busy])
 for ident in(237,254,255):
  for row in range(10):
   ram,sram=fresh(ident,row);compare('out_of_roster_and_FE_sentinel',0xA012,ram,sram,[ident,row])
 for row in(0x80,0xFE,0xFF):
  for busy in(0,1,4,255):
   ram,sram=fresh(131,row,busy=busy);compare('negative_row_and_real_queue_busy_early_RTS',0xA012,ram,sram,[row,busy])
 for selected in(0,1,2,3,9,19,63,255):
  for row in range(10):
   ram,sram=fresh(131,row,selected);compare('mod3_card_slot_and_selected_index',0xB2D7,ram,sram,[selected,row],sp=(243,246,248,253)[selected%4])
 for value in(0,1,9,10,49,50,99,100,101,127,255):
  for row in(1,3,5):
   ram,sram=fresh(131,row);off=0x3C0+12*131
   for j in(0,1,2,3,4):sram[off+j]=value
   compare('attribute_digits_zero_100_loyalty_sentinel',0xA012,ram,sram,[value,row])
 for word in(0,1,255,256,1023,1024,0x7FFF,0xFC00,0xFFFF):
  for experience in(0,49,50,999,1000,24999,49999,65535):
   ram,sram=fresh(131,5);off=0x3C0+12*131;sram[off+8:off+10]=word.to_bytes(2,'little');sram[off+6:off+8]=experience.to_bytes(2,'little')
   compare('u10_troops_high6_and_2xu16_experience',0xA012,ram,sram,[word,experience])
 for flags in range(256):
  for row in(3,4,5):
   ram,sram=fresh(131,row);sram[0x3C0+12*131+11]=flags;compare('packed_level_and_all_affinity_codes',0xA012,ram,sram,[flags,row])
 for equipment in range(256):
  for row in(6,7,8):
   ram,sram=fresh(131,row);sram[0x3C0+12*131+10]=equipment;compare('all_equipment_byte_pairs_top_bottom_cache',0xA012,ram,sram,[equipment,row])
 for row in range(10):
  for mode in(0,3):
   ram,sram=fresh(131,row);ram[0x401]=mode;compare('equipment_shadow_citymode3',0xA012,ram,sram,[row,mode])
 static=json.loads((a.out/'static-control.json').read_text())
 for routine in static['routines']:
  for row in range(10):
   ram,sram=fresh(131,row);ptr=0x63C0+12*131;ram[0x10:0x12]=ptr.to_bytes(2,'little');ram[0x12:0x14]=bytes((0,0x9B));compare('each_local_named_routine',routine['entry'],ram,sram,[routine['name'],row])
 # A queued row is not acknowledged by repeated producer calls.
 ram,sram=fresh(131,0);m=ServiceMemory(rom,ram,sram,(17,25,26,31));c=OfficerDetailsUIServices(m,data)
 first=c.tick(NMIRegisters(sp=253));initial_row=m[0x40D];packet=bytes(m.ram[0x380:0x3A4]);okay=first['status']=='returned'and m[0x7E]&4
 for i in range(3):
  m.ram[0x1FE:0x200]=bytes((0x67,0x24));res=c.tick(NMIRegisters(sp=253));okay=okay and res['status']=='returned'and m[0x40D]==initial_row and bytes(m.ram[0x380:0x3A4])==packet and m[0x7E]&4
 guards.append(dict(name='producer_does_not_ack_its_queued_row',passed=bool(okay)))
 for name,action in [('unknown_entry',lambda:c.run_entry(0xA003,NMIRegisters())),('actual_caller_required',lambda:c.tick())]:
  try:action();passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 ram,sram=fresh(131,10);bad=OfficerDetailsUIServices(ServiceMemory(rom,ram,sram,(17,25,26,31)),data)
 try:bad.tick(NMIRegisters());passed=False
 except InvalidDetailRow:passed=True
 guards.append(dict(name='positive_unproved_row_rejected',passed=passed))
 unknown=ServiceCall(0x8123,0x2468,'unknown',NMIRegisters(pc=0x8123),m,tuple(m.banks),255);guards.append(dict(name='unowned_callee_remains_dependency',passed=c(unknown)['status']=='dependency'))
 fail.extend(dict(kind='sourceguard',guard=g)for g in guards if not g['passed']);a.out.mkdir(parents=True,exist_ok=True)
 providers=[ROOT/'source/recovered'/f'{n}.py'for n in('officer_details_ui_services','scene_shared_services','officer_ui_services','battle_nmi_services','controller_helpers','service_memory')]
 report=dict(schema='phase12-officer-details-v1',status='passed'if not fail else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),original_complete_case_count=sum(counts.values()),original_prefix_case_count=0,source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(fail),counts=dict(counts),
  comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,free_CPU_stack_residue='included',registers='AXYP/SP/PC',all_mapper_banks=True,exact_IO_ports=True),source_original_CPU_callbacks=0,source_IR_interpretation=False,
  pure_recovered_helper_call_counts={hex(k):v for k,v in helper_targets.items()},source_sha256=sha(providers[0]),validator_sha256=sha(Path(__file__)),dependency_pins=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p))for p in providers],guards=guards,failures=fail,samples=samples)
 (a.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(a.out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n');(a.out/'source-executed-locations.json').write_text(json.dumps(sorted(source_locations),indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],CPU=sum(counts.values()),guards=len(guards),failed=len(fail),failures=fail[:8]),ensure_ascii=False));return bool(fail)
if __name__=='__main__':raise SystemExit(main())
