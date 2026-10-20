#!/usr/bin/env python3
"""Compare named G086 city UI lifetime against original CPU, no Source CPU help."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.pointer_lifecycle_services import PointerLifecycleServices
from source.recovered.city_ui_controller import CityRegisters,ROM_SHA256
from source.recovered.pointer_lifecycle_integration import PointerLifecycleGameEngine
from source.recovered.nestopia_context import CapturedServiceMemory,NestopiaContext
OUT=ROOT/'analysis/phase24/lifecycle';REGS=('a','x','y','p','sp','pc')
PARENT=ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/action1-allocation-ready.state'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registers(c):return{k:getattr(c,k)for k in REGS}
def clone(m):
 b=CapturedServiceMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement;return b
def fixture(rom,entry=0xD64A,*,raw=700,reserve=1000,officer=131,mode=16,row=0,button=128,sp=253,p=32):
 saved=NestopiaContext.parse(PARENT.read_bytes());m=saved.service_memory(rom,read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 m.banks[:]=[16,27,28,31];m[0xE2]=59;m[0xE3]=60
 m[0x400]=3;m[0x401]=13;m[0x402]=11;m[0x424]=0;m[0x425]=row;m[0x12]=row;m[0x81]=button;m[0x87]=button
 m[0x47B]=3;m[0x47C]=mode;m[0x478]=0;m[0x300]=m[0x304]=255;m[0x7E]=0;m[0x7C]=0
 m[0x42C]=reserve&255;m[0x42D]=reserve>>8
 ids=[officer,5,30]+[255]*7;m[0x6171:0x617B]=bytes(ids);m[0x151:0x15B]=bytes(ids);m[0x481:0x48B]=bytes([255]*10)
 pointer=0x63C0+12*officer;m[pointer+8]=raw&255;m[pointer+9]=raw>>8
 m[0]=pointer&255;m[1]=pointer>>8;m[2]=raw&255;m[3]=raw>>8
 ret={0xD64A:0xB439,0xD987:0xD83A,0xD773:0xD71A,0xD7A8:0xB439,0xD94E:0xD8D9,0xD96F:0xD958}.get(entry,0x2468)
 m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8
 return m,dict(a=17,x=0,y=1,p=p,sp=sp,pc=entry)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];visited=Counter();guards=[];inputs={}
 def compare(m,initial,tag,domain='controlled_numeric_and_existing_software_frame_CPU_fixture',services=True,provenance=None):
  left,right=clone(m),clone(m);cpu=MPU(memory=left);r=CityRegisters(**initial)
  for k,v in initial.items():setattr(cpu,k,v)
  co=PointerLifecycleGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None
  owner=PointerLifecycleServices(right,rom,co if services else None)
  try:
   reply=owner.run_entry(initial['pc'],registers=r)
   for steps in range(1500000):
    if steps and(cpu.pc,cpu.sp)==(r.pc,r.sp)and(reply['status']in('returned','nonlocal_return')or registers(cpu)==registers(r)):break
    assert cpu.pc>=0x8000,(tag,hex(cpu.pc));visited[left.banks[(cpu.pc-0x8000)//8192],cpu.pc]+=1;cpu.step()
   else:raise RuntimeError(f'Original budget{cpu.pc:04X}; Source{r.pc:04X}')
   rd=[(n,x,y)for n,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+n,x,y)for n,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM',rd[:8],'SRAM',sd[:8])
   assert registers(cpu)==registers(r),(tag,'registers',registers(cpu),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/banks')
   assert left.n163_ram==right.n163_ram and(left.n163_address,left.n163_autoincrement)==(right.n163_address,right.n163_autoincrement),(tag,'N163')
   rows.append(dict(case=tag,domain=domain,initial_registers=initial,final_registers=registers(r),source_status=reply['status'],comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return'}.get(reply['status'],'strict_missing_dependency_prefix'),original_instructions=steps,
    comparison_scope=dict(RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC=True,ordered_IO=True,four_banks=True,N163=True,excluded_free_stack_bytes=0),source_original_CPU_callbacks=0,provenance=provenance,
    changes_SRAM=[dict(address=0x6000+n,before=x,after=y)for n,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y],calls=reply['events']))
  except Exception as exc:failures.append(dict(case=tag,error=str(exc)));print(json.dumps(failures[-1]),flush=True)
 raw_values=(0,99,100,700,999,1000,1098,65535)if not a.quick else(0,999,1098)
 reserves=(0,1,99,100,1000,9899,9900,9901,9999,10000,65535)if not a.quick else(0,9999)
 for officer in((0,131,236,255)if not a.quick else(131,)):
  for raw in raw_values:
   for reserve in reserves:
    m,r=fixture(rom,0xD987,raw=raw,reserve=reserve,officer=officer);compare(m,r,f'normalization/officer{officer}/raw{raw}/reserve{reserve}',domain='raw_officer_byte_mechanical_CPU_fixture'if officer>=237 else'controlled_valid_officer_record_CPU_fixture')
 # The lifecycle postcondition is conditional on genuine officer pointers.
 # Bare alias inputs retain original ordered accesses instead of receiving
 # the valid-record theorem or a repaired pointer/caller from the Source.
 if not a.quick:
  for pointer in(0,1,0x18,0xFF,0x100,0x1F0,0x7F8,0xFFF8):
   m,r=fixture(rom,0xD987,raw=199,reserve=9999);m[0]=pointer&255;m[1]=pointer>>8
   compare(m,r,f'bare-normalization/pointer{pointer:04X}',domain='explicit_bare_pointer_alias_CPU_fixture_not_legal_UI')
 # Full selector body: actual directional menu calls, readiness and packet
 # production are included. These are explicit software/input fixtures.
 for mode in((0,1,3,10,15,16)if not a.quick else(1,15,16)):
  for row in((0,1,2,3)if not a.quick else(0,3)):
   for button in((0,1,2,16,32,64,128,255)if not a.quick else(0,1,64,128)):
    m,r=fixture(rom,mode=mode,row=row,button=button);compare(m,r,f'full-selector/mode{mode}/row{row}/button{button}')
 for raw in raw_values:
  for reserve in reserves:
   for button in(64,128):
    m,r=fixture(rom,raw=raw,reserve=reserve,button=button);compare(m,r,f'full-allocation/raw{raw}/reserve{reserve}/button{button}')
 for tag,row,selection in(('deselect-current-row',0,[131]+[255]*9),('compact-holes-at-end',3,[255,5,255,30]+[255]*6)):
  m,r=fixture(rom,mode=2,row=row,button=1);m[0x481:0x48B]=bytes(selection)
  compare(m,r,'selection-lifetime/'+tag)
 # Exact parent commits the working reserve to city+12/+13 only after end-row
 # confirmation; ordinary edits themselves write the officer record directly.
 for button in(0,1,2,64,128):
  m,r=fixture(rom,0xB431,row=3,button=button,reserve=2345);compare(m,r,f'parent-reserve-commit/button{button}',domain='explicit_original_parent_caller_CPU_fixture')
 for text300,text304 in((0,255),(255,0),(0,0)):
  m,r=fixture(rom);m[0x300]=text300;m[0x304]=text304;compare(m,r,f'real-readiness/text{text300}-{text304}')
 for entry in(0xD64A,0xD987,0xD773,0xD7A8,0xD94E,0xD96F):
  for sp in((0,1,127,252,253,254,255)if not a.quick else(0,255)):
   for bits in((0,1,2,3,4,8,15)if not a.quick else(0,15)):
    flags=32|(bits&1)|(bits&2)|((bits&4)<<4)|((bits&8)<<4)
    m,r=fixture(rom,entry,sp=sp,p=flags,button=0);r['a']=0 if bits&1 else 15;r['x']=0;r['y']=1
    compare(m,r,f'caller-flags/{entry:04X}/SP{sp}/NZCV{bits}')
 m,r=fixture(rom,0xD987);compare(m,r,'strict-no-division-owner',services=False,domain='strict_dependency_fixture')
 m,r=fixture(rom);compare(m,r,'strict-no-menu-owner',services=False,domain='strict_dependency_fixture')
 for directory in sorted((ROOT/'analysis/phase24/cpu-lifecycle/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  assert x['prepared_numeric_bytes']==x['additional_CPU_prepared_numeric_bytes']==[]and x['controller_buttons']==[0,0]
  captured=x['passive_capture'];assert sha(ROOT/captured['metadata'])==captured['metadata_sha256']
  assert sha(ROOT/captured['RAM_path'])==captured['RAM_sha256']==sha(directory/'input-ram.bin')
  assert sha(ROOT/captured['SRAM_path'])==captured['SRAM_sha256']==sha(directory/'input-sram.bin')
  assert sha(ROOT/captured['manifest'])==captured['manifest_sha256']
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],'exported/'+directory.name,domain=x['origin'],provenance=x)
  for path in directory.iterdir():inputs[str(path.relative_to(ROOT))]=sha(path)
 m,r=fixture(rom)
 for name,func in(
  ('actual_registers_required',lambda:PointerLifecycleServices(m,rom).run_entry(0xD64A)),
  ('seed_return_forbidden',lambda:PointerLifecycleServices(m,rom).run_entry(0xD64A,registers=CityRegisters(**r),seed_return=True)),
  ('actual_entry_PC_required',lambda:PointerLifecycleServices(m,rom).run_entry(0xD987,registers=CityRegisters(**r))),
  ('wrong_physical_pair_rejected',lambda:PointerLifecycleServices(CapturedServiceMemory(rom,banks=(16,25,26,31)),rom).run_entry(0xD64A,registers=CityRegisters(**r))),
  ('NES_decimal_rejected',lambda:PointerLifecycleServices(m,rom).run_entry(0xD64A,registers=CityRegisters(**dict(r,p=40)))),
 ):
  try:func();raise AssertionError('Guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};sources[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
 result=dict(schema='phase24-pointer-lifecycle-exact-source-CPU-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),counts=dict(Counter(x['comparison']for x in rows)),source_guard_count=len(guards),guards=guards,failed_count=len(failures),failures=failures,cases=rows,source_original_CPU_callbacks=0,production_IR_interpretation=False,production_runtime_codegen=False,Native_internal_CPU_trace=False,
  source_sha256=sources,input_sha256=inputs,inherited_fixture_parent=dict(path=str(PARENT.relative_to(ROOT)),sha256=sha(PARENT),prepared_numeric_bytes=0),
  executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],
  limits=['Rawbyte and software caller matrices are controlled CPU contexts, not additional natural gameplay sequences.','Actual Native inputs are separately tagged and any explicit hardware events remain part of their provenance.','Existing phase5 arithmetic conclusions and other frozen parent helpers are reused, not recounted as newly discovered formulas.','Pending PPU jobs are produced, never cleared or automatically acknowledged.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':raise SystemExit(main())
