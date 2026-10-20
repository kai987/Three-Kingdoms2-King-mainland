#!/usr/bin/env python3
"""Complete deployment callers: exact Source versus originalCPU, no fallback."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.deployment_pointer_services import DeploymentPointerServices
from source.recovered.battle_setup_ai import SetupRegisters,ROM_SHA256
from source.recovered.appearance_pointer_integration import AppearancePointerGameEngine
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_city_threshold_services import registers
from verify_city_auxiliary_services import base_memory
OUT=ROOT/'analysis/phase26/deployment'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class OrderedComparisonMemory(CapturedServiceMemory):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.combined_IO=[]
 def io_read(self,address):
  value=super().io_read(address);self.combined_IO.append(('read',address&65535,value));return value
 def io_write(self,address,value):
  super().io_write(address,value);self.combined_IO.append(('write',address&65535,value&255))
def clone(m):
 b=OrderedComparisonMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement;return b
def fixture(rom,entry=0xB2AE,*,city=4,origin=3,side=0,count=3,ruler=2,sp=253,p=32):
 m=clone(base_memory(rom));m.banks[:]=[16,8,9,31];m.ram[0xDE:0xE4]=bytes((48,40,41,48,40,41))
 m[0x50E]=city;m[0x52A]=origin;m[0x507]=0x21;m[0x6F91]=side;m[0x6F94]=count;m[0x20]=54 if side else 0;m[0x22]=ruler
 for ident in range(7):m[0x6F07+8*ident+3]=3
 for slot in range(20):
  m[0x664+slot]=20+slot if slot%10<=count else 255;m[0x628+slot]=(128 if slot>=10 else 0)|(slot%3);m[0x63C+slot]=slot%11;m[0x6FA1+slot]=255
  b=0x63C0+12*(20+slot);m[b+1]=(99 if count&1 else 50)-slot%10
 m[0x6FA1]=m[0x6FAB]=0
 ret={0xA003:0xE1BA,0xB130:0xE1BA,0xB1B0:0xB16E if side==0 else 0xB198,0xB2AE:0xB260,0xB312:0xB266}[entry]
 m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8
 m.n163_ram[:]=bytes((11+37*i)&255 for i in range(128));m.n163_address=127;m.n163_autoincrement=True
 m.io_reads.clear();m.io_writes.clear()
 return m,dict(a=17,x=73,y=255,p=p,sp=sp,pc=entry)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 OUT.mkdir(parents=True,exist_ok=True);rows=[];failures=[];guards=[];visited=Counter();inputs=[]
 def compare(m,initial,tag,domain='controlled_original_software_caller_fixture',services=True):
  left,right=clone(m),clone(m);c=MPU(memory=left);r=SetupRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  co=AppearancePointerGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None
  owner=DeploymentPointerServices(right,rom,co if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   for n in range(1500000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000,(tag,hex(c.pc));visited[left.banks[(c.pc-0x8000)//8192],c.pc]+=1;c.step()
   else:raise RuntimeError(f'CPU budget{c.pc:04X},Source{r.pc:04X}')
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM/SRAM',rd[:8],sd[:8]);assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.combined_IO==right.combined_IO and left.banks==right.banks,(tag,'IO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return'}.get(result['status'],'strict_missing_dependency_prefix'),original_instructions=n,RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC_ordered_IO_four_banks_N163_equal=True,combined_logical_IO_read_write_interleaving_equal=True,combined_IO_events=right.combined_IO,source_original_CPU_callbacks=0,pointer20_after=right[0x20]|right[0x21]<<8,group_offsets22_25=list(right[0x22:0x26]),unit_Y20=list(right[0x614:0x628]),unit_X20=list(right[0x600:0x614]),events=result['events']))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 for city in((0,4,29)if a.quick else range(30)):
  o=16+16*8192+(0x9D72&8191)+8*city;origins=list(dict.fromkeys([city,255]+[v for v in rom[o:o+8]if v<30]))
  for origin in(origins[:2]if a.quick else origins):
   for entry in(0xB2AE,0xB312):
    m,r=fixture(rom,entry,city=city,origin=origin);compare(m,r,f'legal-formation/{entry:04X}/city{city}/origin{origin}',domain='typed_city0_29_complete_formation_caller')
 # All raw byte cities retain modulo8/2 addressing and real table aliases;
 # this is a mechanical domain, not a claim that raw30..255 are legal cities.
 for city in((30,127,128,255)if a.quick else range(30,256)):
  for origin in(0,255):
   for entry in(0xB2AE,0xB312):
    m,r=fixture(rom,entry,city=city,origin=origin);compare(m,r,f'raw-formation/{entry:04X}/rawcity{city}/origin{origin}',domain='explicit_raw8_city_complete_formation_caller')
 for ruler in((2,)if a.quick else range(7)):
  for side in(0,10):
   for count in((0,9)if a.quick else range(10)):
    for city in((4,)if a.quick else(0,4,29)):
     m,r=fixture(rom,0xB1B0,city=city,origin=city,side=side,count=count,ruler=ruler);compare(m,r,f'inherited-B1B0/ruler{ruler}/side{side}/n{count}/city{city}',domain='existing_named_B1B0_complete_caller')
 for count in((0,9)if a.quick else(0,1,3,9)):
  for controllers in((3,)if a.quick else range(4)):
   for city in((4,)if a.quick else(0,4,29)):
    m,r=fixture(rom,0xA003,city=city,origin=city,count=count);m[0x6F12]=3 if controllers&1 else 1;m[0x6F1A]=3 if controllers&2 else 1
    compare(m,r,f'inherited-parent/A003/n{count}/controllers{controllers}/city{city}',domain='existing_named_A003_B130_parent_caller')
 for entry in(0xB2AE,0xB312):
  for sp in((0,255)if a.quick else(0,1,2,127,252,253,254,255)):
   for bits in((0,15)if a.quick else range(16)):
    flags=32|(bits&3)|((bits&4)<<4)|((bits&8)<<4);m,r=fixture(rom,entry,p=flags,sp=sp);compare(m,r,f'flags-stack/{entry:04X}/SP{sp}/P{flags}')
  m,r=fixture(rom,entry);compare(m,r,f'missing-F266/{entry:04X}',services=False,domain='strict_missing_dependency_fixture')
 for path in sorted((ROOT/'analysis/phase26/cpu-deployment/actual-callers').glob('entry-*/context.json')):
  x=json.loads(path.read_text());folder=path.parent
  if x['registers']['pc']not in DeploymentPointerServices.PUBLIC_ENTRIES:continue
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],f'exported/{folder.name}',domain=x['origin']);inputs.extend(folder.iterdir())
 m,r=fixture(rom)
 for name,fn in(('actual_registers_required',lambda:DeploymentPointerServices(m,rom).run_entry()),('seed_return_rejected',lambda:DeploymentPointerServices(m,rom).run_entry(r['pc'],registers=SetupRegisters(**r),seed_return=True)),('wrong_PC_rejected',lambda:DeploymentPointerServices(m,rom).run_entry(0xB312,registers=SetupRegisters(**r))),('wrong_pair_rejected',lambda:DeploymentPointerServices(CapturedServiceMemory(rom,banks=(16,10,11,31)),rom).run_entry(r['pc'],registers=SetupRegisters(**r))),('decimal_rejected',lambda:DeploymentPointerServices(m,rom).run_entry(r['pc'],registers=SetupRegisters(**dict(r,p=40)))),('wrong_return_rejected',lambda:DeploymentPointerServices(m,rom).run_entry(r['pc'],registers=SetupRegisters(**r),return_pc=0x0200))):
  try:fn();raise AssertionError('guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 def false_completion(call):return dict(status='returned')
 bad=DeploymentPointerServices(clone(m),rom,false_completion);reply=bad.run_entry(r['pc'],registers=SetupRegisters(**r));assert reply['status']=='dependency'and bad.pending is not None
 guards.append(dict(name='returned_string_without_real_PC_SP_does_not_complete_service',status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in(Path(__file__),ROOT/'scripts/verify_city_threshold_services.py',ROOT/'scripts/verify_city_auxiliary_services.py'):pins[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase26-deployment-pointer-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),counts=dict(Counter(r['comparison']for r in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],limits=['The two formation bodies are readable refactoring of prior direct Source, not first discovery of B1B0 deployment behavior.','All2048RAM includes free stack; all8192SRAM and actual PC/SP/AXYP/orderedIO/4banks/commonN163 are compared without hardware interrupts.','Controlled rawcity contexts are not Native legality or field-name evidence.','Missing F266 remains the actual dependency prefix, not an implicit return.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
