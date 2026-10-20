#!/usr/bin/env python3
"""Exact Source/originalCPU comparison of the new appearance multiplication."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.appearance_pointer_services import AppearancePointerServices
from source.recovered.appearance_pointer_integration import AppearancePointerGameEngine
from source.recovered.city_threshold_services import UIRegisters,ROM_SHA256
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_city_threshold_services import clone,registers
from verify_city_recruitment_services import fixture as recruitment_fixture
OUT=ROOT/'analysis/phase25/appearance'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fixture(rom,a,b,*,p=32,sp=253,x=73):
 m=CapturedServiceMemory(rom,banks=(17,10,11,31),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 m.ram[:]=bytes((37*i+11)&255 for i in range(2048));m.sram[:]=bytes((19*i+3)&255 for i in range(8192))
 m[0x20]=a;m[0x21]=b;m[0x100+((sp+1)&255)]=3;m[0x100+((sp+2)&255)]=0xC6
 m.n163_ram[:]=bytes((37*i+11)&255 for i in range(128));m.n163_address=127;m.n163_autoincrement=True
 return m,dict(a=193,x=x,y=255,p=p,sp=sp,pc=0xD471)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 OUT.mkdir(parents=True,exist_ok=True);rows=[];failures=[];guards=[];visited=Counter();inputs=[]
 def compare(m,initial,tag,domain='controlled_original_software_caller_fixture',services=True):
  left,right=clone(m),clone(m);c=MPU(memory=left);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  co=AppearancePointerGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None
  owner=AppearancePointerServices(right,rom,co if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   for n in range(1500000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000,(tag,hex(c.pc));visited[left.banks[(c.pc-0x8000)//8192],c.pc]+=1;c.step()
   else:raise RuntimeError(f'CPU budget{c.pc:04X},Source{r.pc:04X}')
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM/SRAM',rd[:8],sd[:8]);assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   if initial['pc']==0xD471:
    assert right[0x2A]|right[0x2B]<<8==m[0x20]*m[0x21]
    assert right[0x20]==right[0x21]==0 and right[0x2C]==m[0x20] and r.x==initial['x']
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return'}.get(result['status'],'strict_missing_dependency_prefix'),original_instructions=n,RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC_ordered_IO_four_banks_N163_equal=True,source_original_CPU_callbacks=0,events=result['events']))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 # All256 raw city bytes at the real multiplier20, plus independent bit,
 # carry and high-product cases. No mathematical shortcut replaces flags.
 for x in(range(0,256,31)if a.quick else range(256)):
  for y in((20,255)if a.quick else(0,1,2,3,7,16,20,127,128,254,255)):
   m,r=fixture(rom,x,y);compare(m,r,f'multiply/{x}x{y}')
 for sp in((0,255)if a.quick else(0,1,2,127,252,253,254,255)):
  for bits in((0,15)if a.quick else range(16)):
   flags=32|(bits&3)|((bits&4)<<4)|((bits&8)<<4)
   m,r=fixture(rom,255,255,p=flags,sp=sp,x=sp);compare(m,r,f'flags-stack/SP{sp}/P{flags}')
 # The inherited already-named C5D2 is compared as a complete caller, not
 # credited as newly recovered Source. Table bytes remain original ROM.
 for city in((2,3)if a.quick else(0,2,3,4,29)):
  for year in((89,)if a.quick else(89,90,93)):
   for cursor in((11,)if a.quick else(0,11,83)):
    m,r=recruitment_fixture(rom,0xC5D2);m[0x36]=city;m[0x6F00]=year;m[0x52]=11;m[0x54]=cursor
    base=0x6000+32*city;m[base]=(m[base]&248)|4;m[base+17:base+27]=bytes((255,))*10
    compare(m,r,f'inherited-caller/city{city}/year{year}/cursor{cursor}',domain='controlled_complete_existing_C5D2_caller')
 m,r=recruitment_fixture(rom,0xC5D2);compare(m,r,'missing-real-F266',services=False,domain='strict_missing_dependency_fixture')
 for path in sorted((ROOT/'analysis/phase25/cpu-appearance/actual-callers').glob('entry-*/context.json')):
  meta=json.loads(path.read_text());folder=path.parent
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),meta['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(meta['controller_buttons']))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=meta['N163_address'];m.n163_autoincrement=meta['N163_autoincrement']
  compare(m,meta['registers'],f'exported/{folder.name}',domain=meta['origin']);inputs.extend(folder.iterdir())
 m,r=fixture(rom,1,20)
 for name,fn in(('actual_registers_required',lambda:AppearancePointerServices(m,rom).run_entry(0xD471)),('wrong_pair_rejected',lambda:AppearancePointerServices(CapturedServiceMemory(rom,banks=(16,12,13,31)),rom).run_entry(0xD471,registers=UIRegisters(**r))),('decimal_rejected',lambda:AppearancePointerServices(m,rom).run_entry(0xD471,registers=UIRegisters(**dict(r,p=40))))):
  try:fn();raise AssertionError('guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in(Path(__file__),ROOT/'scripts/verify_city_threshold_services.py',ROOT/'scripts/verify_city_recruitment_services.py'):pins[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase25-appearance-multiplication-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),counts=dict(Counter(r['comparison']for r in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],limits=['Only D471 is newly named Source; C5D2 and all fixed services remain frozen prior direct-source dependencies.','Controlled software callers are not Native entry captures. Sparse passive inputs retain their separate N163 fixture scope.','No added NMI/IRQ or fake RNG/ready/return during callee comparisons.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
