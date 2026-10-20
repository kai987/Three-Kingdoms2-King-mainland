#!/usr/bin/env python3
"""Unchanged original CPU versus independent graphics data call protocols."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_portrait_ui_services import OriginalBus
from source.recovered.ui_graphics_initialization import UIGraphicsInitialization,UIGraphicsData,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/graphics');p.add_argument('--quick',action='store_true');args=p.parse_args()
 rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=UIGraphicsData.from_rom(rom);rng=random.Random(0x130023)
 counts=Counter();failures=[];guards=[];samples=[];visited=set()
 def fresh():return bytearray(rng.randbytes(2048)),bytearray(rng.randbytes(8192))
 def compare(kind,entry,ram,sram,meta,p=32,sp=253,caller=False):
  ram[0x100+((sp+1)&255)]=0x67;ram[0x100+((sp+2)&255)]=0x24
  b=OriginalBus(rom,ram,sram,[17,23,24,31]);m=ServiceMemory(rom,ram,sram,(17,23,24,31));r=NMIRegisters(a=17,x=29,y=55,p=p,sp=sp,pc=entry)
  c=UIGraphicsInitialization(m,data);cpu=MPU(memory=b,pc=entry);b.cpu=cpu
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  try:
   result=c(ServiceCall(entry,0x2468,'fixture',r,m,tuple(m.banks),(sp+2)&255))if caller else c.run_entry(entry,r)
   assert result['status']=='returned',result
   for n in range(1000):
    if cpu.pc==0x2468:break
    b.pc=cpu.pc;origin=b.origin(cpu.pc);visited.add((origin[0],cpu.pc));cpu.step()
   else:raise AssertionError('Original helper did not return')
   rd=[(hex(a),b.ram[a],m.ram[a])for a in range(2048)if b.ram[a]!=m.ram[a]]
   sd=[(hex(a+0x6000),b.sram[a],m.sram[a])for a in range(8192)if b.sram[a]!=m.sram[a]]
   rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not rd and not sd and not rg,('mismatch',rd[:7],sd[:5],rg)
   assert b.ports==m.io_writes and b.banks==m.banks,('mapper',b.ports,m.io_writes,b.banks,m.banks)
   counts[kind]+=1
   if sum(v['kind']==kind for v in samples)<4:samples.append(dict(kind=kind,input=meta,entry=entry,original_instructions=n,registers=vars(r),ports=m.io_writes,unit_tiles=list(m.ram[0x1B0:0x1B4])))
  except Exception as exc:
   failures.append(dict(kind=kind,input=meta,error=str(exc)))
   if len(failures)<6:print(json.dumps(failures[-1]),flush=True)
 for chunk in (range(120)if not args.quick else(0,59,119)):
  for entry in(0xA012,0xA015,0xA61C,0xAEF0):
   for flags in(32,33,98,160,227):
    ram,sram=fresh();ram[0]=chunk;compare('all120_chunk_resource_bodies',entry,ram,sram,[chunk,flags],p=flags,sp=243 if flags&1 else 253,caller=entry<0xA020)
 for slot in(range(20)if not args.quick else(0,1,10,19)):
  for hundreds in(range(11)if not args.quick else(0,10)):
   for affinity in range(4):
    for controller in(0,1,2,255):
     for side in(0,128):
      ram,sram=fresh();ram[0]=slot;ram[0x507]=0x65;ram[0x628+slot]=side|affinity;ram[0x63C+slot]=hundreds
      sram[0xF07+8*(6 if side else 5)+3]=controller
      compare('unit_all_slots_strength_affinity_controller_side',0xA018,ram,sram,[slot,hundreds,affinity,controller,side],p=(32,33,98,160)[affinity],sp=239 if side else 253,caller=True)
 for name,entry,prepare in(('unknown_entry',0xA021,lambda m:None),('chunk120',0xA012,lambda m:m.__setitem__(0,120)),('slot20',0xA018,lambda m:m.__setitem__(0,20)),('strength11',0xA018,lambda m:(m.__setitem__(0,0),m.__setitem__(0x63C,11))),('ruler7',0xA018,lambda m:(m.__setitem__(0,0),m.__setitem__(0x63C,0),m.__setitem__(0x628,0),m.__setitem__(0x507,7)))):
  ram,sram=fresh();m=ServiceMemory(rom,ram,sram,(17,23,24,31));prepare(m);c=UIGraphicsInitialization(m,data)
  try:c.run_entry(entry,NMIRegisters());passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 for name,action in(('missing_caller',lambda:UIGraphicsInitialization(ServiceMemory(rom,*fresh(),(17,23,24,31)),data).run_entry()),('wrong_pair',lambda:UIGraphicsInitialization(ServiceMemory(rom,*fresh(),(17,25,26,31)),data).run_entry(0xA012,NMIRegisters()))):
  try:action();passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 failures.extend(dict(kind='guard',guard=g)for g in guards if not g['passed'])
 def pin(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
 report=dict(schema='phase13-ui-graphics-data-v1',status='failed'if failures else'passed',quick=args.quick,rom_sha256=ROM_SHA256,
  rom_cpu_case_count=sum(counts.values()),original_complete_case_count=sum(counts.values()),original_prefix_case_count=0,source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(failures),
  source_sha256=pin('source/recovered/ui_graphics_initialization.py'),validator_sha256=pin('scripts/verify_ui_graphics_initialization.py'),
  comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,free_CPU_stack_residue='included',registers='AXYP/SP/PC',ordered_IO_ports=True,all_mapper_banks=True,hardware_reads=0),
  source_original_CPU_callbacks=0,source_IR_interpretation=False,fixture_provenance=dict(kind='typed_CPU_conditions',random_seed=0x130023,all_RAM_SRAM_initial='deterministic random bytes, source/CPU byteidentical',caller='prepared real two-byte RTS frame2468; actualSP explicit',hardware_reads='none',SRAM_protection='original Bus4C, lower4KiB writable'),counts=dict(counts),guards=guards,failures=failures,samples=samples,dynamic_original_instruction_locations=len(visited))
 args.out.mkdir(parents=True,exist_ok=True);(args.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (args.out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n')
 print(json.dumps({k:report[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count')}));return bool(failures)
if __name__=='__main__':raise SystemExit(main())
