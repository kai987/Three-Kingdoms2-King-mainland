#!/usr/bin/env python3
"""Exact CPU caller comparisons for the missing postbattle header/loyalty services.

Native memory is input provenance only. Registers, caller frames and boundary
values are explicitly controlled CPU fixtures. No source CPU/IR callback runs.
"""
from pathlib import Path
from collections import Counter
from itertools import product
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.service_memory import ServiceMemory
from source.recovered.global_ui_controller import UIRegisters
from source.recovered.postbattle_graphics import PostbattleGraphics
from source.recovered.postbattle_loyalty_bridge import PostbattleLoyaltyBridge
from source.recovered.battle_nmi_services import ServiceCall
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--area',choices=('graphics','loyalty'),required=True);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==SHA
 area=a.area;out=ROOT/'analysis/phase16'/area;out.mkdir(parents=True,exist_ok=True)
 native=ROOT/'analysis/phase15/runtime/succession-heir/observed-g01-n02-city-013-000';rp=Path(str(native)+'-ram.bin');sp=Path(str(native)+'-sram.bin');ram=rp.read_bytes();sram=sp.read_bytes()
 cls=PostbattleGraphics if area=='graphics'else PostbattleLoyaltyBridge;pair=cls.PAIR
 files=['source/recovered/'+n+'.py'for n in('postbattle_graphics','postbattle_loyalty_bridge','global_ui_controller','domestic_cooperation_controller','scene_shared_services','audio_services','battle_nmi_services','controller_helpers','service_memory','mapped_memory')]+['scripts/verify_postbattle_services.py']
 pins={f:sha(ROOT/f)for f in files};counts=Counter();rows=[];failures=[];visited=Counter();guards=[]
 def memory(r,s):return ServiceMemory(rom,r,s,(17,*pair,31),read_ports={0x2002:0},repeat_read_ports=(0x2002,),controller_buttons=(0,0))
 def build(prep,caller_sp=253,entry=None):
  r=bytearray(ram);s=bytearray(sram)
  for address,value in prep.items():
   if address<2048:r[address]=value
   else:s[address-0x6000]=value
  entry=entry or cls.PUBLIC_ENTRIES[0]
  for address,value in [(0x100+((caller_sp+1)&255),255),(0x100+((caller_sp+2)&255),1)]:r[address]=value
  left=memory(r,s);right=memory(r,s);registers=UIRegisters(a=17,x=31,y=63,p=32,sp=caller_sp,pc=entry);cpu=MPU(memory=left)
  for k,v in reg(registers).items():setattr(cpu,k,v)
  owner=cls(right,rom)
  return left,right,registers,cpu,owner
 def original(bus,cpu,r,*,limit=20000,stop=None):
  for n in range(limit):
   if n and((stop(cpu)if stop else cpu.pc==r.pc and cpu.sp==r.sp)):return n
   assert cpu.pc>=0x8000,'Original unexpectedly entered RAM code'
   bank=bus.banks[(cpu.pc-0x8000)//8192];visited[(bank,cpu.pc,16+bank*8192+(cpu.pc&8191))]+=1;cpu.step()
  raise RuntimeError(f'Original budget {cpu.pc:04X}')
 def equal(left,right,r,cpu):
  rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
  rg={k:(getattr(cpu,k),getattr(r,k))for k in REGS if getattr(cpu,k)!=getattr(r,k)}
  assert not rd and not sd and not rg,dict(RAM=rd[:15],SRAM=sd[:8],registers=rg)
  assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks and left.n163_ram==right.n163_ram
 def case(group,prep,metadata,caller_sp=253,entry=None):
  left,right,r,cpu,owner=build(prep,caller_sp,entry);initial=reg(r)
  try:
   result=owner.run_entry(r.pc,registers=r);assert result['status']=='returned',result
   n=original(left,cpu,r);equal(left,right,r,cpu)
   assert r.pc==0x200 and r.sp==(caller_sp+2)&255
   rows.append(dict(group=group,input=metadata,entry=initial['pc'],initial_registers=initial,final_registers=reg(r),original_instructions=n,comparison='complete_return',completion_kind='actual_caller_RTS',RAM_bytes=2048,SRAM_bytes=8192,ports=len(right.io_writes),source_original_CPU_callbacks=0));counts[group]+=1
  except Exception as exc:failures.append(dict(group=group,input=metadata,error=str(exc),source_registers=reg(r)))
 if area=='graphics':
  for year,month in product(range(256)if not a.quick else(0,89,90,255),range(12)):
   case('all_years_normal_months',{0x6F00:year,0x6F01:month},{'year':year,'month':month},entry=0xA01E if(year+month)&1 else 0xA6B6)
  for year,month in product((0,89,99,155,255),range(12,256)if not a.quick else(12,99,255)):
   case('raw_month_boundary',{0x6F00:year,0x6F01:month},{'year':year,'month':month})
  for caller_sp in range(256)if not a.quick else(0,127,253,255):case('caller_stack_byte_wrap',{0x6F00:90,0x6F01:0},{'SP':caller_sp},caller_sp)
 else:
  for ruler,leader_a,leader_b,officer,caller_sp in product(range(7),(8,131,173,255),(9,5,182,255),(0,8,131,236,255),range(3)if not a.quick else(1,)):
   sp_value=(127,253,255)[caller_sp]
   case('family_alias_and_stack',{0x30:leader_a,0x31:officer,0x32:ruler,0x33:leader_b},{'ruler':ruler,'30':leader_a,'31':officer,'33':leader_b,'SP':sp_value},sp_value,0xA009 if caller_sp&1 else 0xCF7C)
  for ruler in range(7):
   pointer_offset=16+11*8192+(0xCAD8&8191)+2*ruler
   pointer=int.from_bytes(rom[pointer_offset:pointer_offset+2],'little');offset=16+11*8192+(pointer&8191)
   exempt_ids=rom[offset:rom.index(255,offset)]
   for officer in exempt_ids:
    case('actual_family_exemption_early_RTS',{0x30:officer,0x31:236,0x32:ruler,0x33:9},{'ruler':ruler,'exempt_ID':officer})
  for loyalty,(virtue_a,virtue_b)in product(range(256)if not a.quick else(0,9,10,98,99,100,255),((0,255),(255,0),(49,51))):
   prep={0x30:8,0x31:236,0x32:2,0x33:9,0x63C0+12*8+4:virtue_a,0x63C0+12*9+4:virtue_b,0x63C0+12*236+3:loyalty}
   case('raw_loyalty_and_virtue_clamp',prep,{'loyalty':loyalty,'virtues':[virtue_a,virtue_b]})
 # Refuse fabricated inputs/return frames before touching software memory.
 for name,action in [('missing_registers',lambda owner,r:owner.run_entry(registers=None)),('seed_return',lambda owner,r:owner.run_entry(registers=r,seed_return=True)),('wrong_entry',lambda owner,r:owner.run_entry(0x8123,registers=r)),('mismatched_return_word',lambda owner,r:owner.run_entry(registers=r,return_pc=0xBEEF)),('wrong_pair',lambda owner,r:(owner.memory.banks.__setitem__(1,12),owner.run_entry(registers=r))),('decimal_flag',lambda owner,r:(setattr(r,'p',40),owner.run_entry(registers=r)))]:
  left,right,r,cpu,owner=build({});before=(bytes(right.ram),bytes(right.sram),list(right.io_writes))
  try:action(owner,r)
  except ValueError:guards.append(name)
  else:raise AssertionError(name)
  assert before==(bytes(right.ram),bytes(right.sram),list(right.io_writes))
 try:cls(bytearray(65536),rom)
 except ValueError:guards.append('explicit_ServiceMemory_required')
 else:raise AssertionError('Raw memory accepted')
 left,right,r,cpu,owner=build({});before=(bytes(right.ram),bytes(right.sram),list(right.io_writes))
 refused=owner(ServiceCall(r.pc,0x200,'actual_fixture',r,right,tuple(right.banks),r.sp))
 assert refused['status']=='dependency'and before==(bytes(right.ram),bytes(right.sram),list(right.io_writes));guards.append('incorrect_actual_caller_SP_rejected')
 assert pins=={f:sha(ROOT/f)for f in files},'Source changed during matrix; rerun after freeze'
 result=dict(schema='phase16-'+area+'-exact-CPU-v1',status='passed'if not failures else'failed',rom_sha256=SHA,quick=a.quick,rom_cpu_case_count=len(rows),complete_return_count=len(rows),strict_prefix_count=0,source_guard_case_count=len(guards),failed_count=len(failures),failures=failures,rows=rows,guards=guards,counts=dict(counts),source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256=pins,artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(rp,sp)},comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,registers=REGS,ordered_IO_reads_writes_banks=True,N163_image=True,idle_stack='included'),limits=['Explicit register/caller and byte-boundary CPU fixtures, not internal NativeCPU traces.','Audio/PPU timing or completed frame synthesis is not implemented here.','Raw ID237/255 and month12..255 fixtures are original byte semantics, not normal game identities/months.'])
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=off,visits=n)for(b,pc,off),n in sorted(visited.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts','failures')},ensure_ascii=False));raise SystemExit(bool(failures))
if __name__=='__main__':main()
