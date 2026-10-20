#!/usr/bin/env python3
"""Exact originalCPU comparisons of named city recruitment; no source CPU hook."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_recruitment_services import CityRecruitmentServices,UIRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_city_auxiliary_services import base_memory
OUT=ROOT/'analysis/phase21/recruitment'
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registers(c):return {k:getattr(c,k)for k in REGS}
def clone(m):
 b=CapturedServiceMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement;return b
def fixture(rom,entry):
 m=base_memory(rom);m[0x6F03]=4;m[0x36]=2;m[0x6F02]=1;m[0x6F8B]=0;m[0x6F5D]=30
 m[0x52]=11;m[0x54]=11
 # Genuine software frame shapes, explicitly prepared CPU fixtures:
 # C6CC/C71A/C765 is below C5B9; its successful doublePLA returns to A027.
 sp=251 if entry in(0xC6CC,0xC71A,0xC765)else 253
 m[0x1FC:0x200]=bytes((0xC3,0xC5,0x26,0xA0))
 return m,dict(a=17,x=23,y=31,p=32,sp=sp,pc=entry)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter()
 def compare(m,initial,tag,services=True,domain='controlled_numeric_CPU_fixture'):
  left,right=clone(m),clone(m);c=MPU(memory=left);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  owner=CityRecruitmentServices(right,rom,SceneSharedServices(right,rom)if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r,max_blocks=200000)
   officer_scan=[];rng=[];active_rng=[]
   for n in range(1500000):
    match=(c.pc,c.sp)==(r.pc,r.sp)
    if n and match and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000,(tag,hex(c.pc),result['status'],hex(r.pc))
    bank=left.banks[(c.pc-0x8000)//8192];visited[bank,c.pc]+=1
    if bank==11 and c.pc==0xC726:officer_scan.append(dict(X=c.x,pointer=left[0x22]|left[0x23]<<8,effective_address=(left[0x22]|left[0x23]<<8)+c.y))
    if c.pc==0xE89A:active_rng.append(dict(X=c.x,SP=c.sp,return_PC=((left[0x100+((c.sp+1)&255)]|left[0x100+((c.sp+2)&255)]<<8)+1)&65535,cursor54=left[0x54]))
    c.step()
    if active_rng and(c.pc,c.sp)==(active_rng[-1]['return_PC'],(active_rng[-1]['SP']+2)&255):
     start=active_rng.pop();rng.append(dict(**start,returned_X=c.x));assert start['X']==c.x,'Uninterrupted E89A changed X'
   else:raise RuntimeError(f'Original CPU budget PC{c.pc:04X};sourcePC{r.pc:04X}')
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y]
   sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'memory',rd[:8],sd[:8])
   assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
   assert left.banks==right.banks and left.io_reads==right.io_reads and left.io_writes==right.io_writes,(tag,'IO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return','waiting':'original_loop_wait'}.get(result['status'],'strict_missing_dependency_prefix')
   if tag.startswith('full-scan/'):
    assert len(officer_scan)==237 and [x['X']for x in officer_scan]==list(range(237)),(tag,len(officer_scan))
    assert [x['effective_address']for x in officer_scan]==[0x63C0+12*i+11 for i in range(237)]
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison=comparison,
    original_instructions=n,RAM_bytes=2048,SRAM_bytes=8192,all_registers_ordered_IO_banks_N163_equal=True,source_original_CPU_callbacks=0,
    scanned_record_count=len(officer_scan),scan_first=officer_scan[:1],scan_last=officer_scan[-1:],uninterrupted_E89A_calls=len(rng),all_E89A_X_preserved=True,
    committed_officer=right[0x31]if result['status']=='nonlocal_return'else None,changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y],events=result['events']))
   return result
  except Exception as exc:
   failures.append(dict(case=tag,error=str(exc),source_PC=r.pc));print(json.dumps(failures[-1]),flush=True)
 # Exact historical 90/10 preferences and flags; all raw officer bytes matter.
 for ruler in((2,4)if a.quick else(0,1,2,3,4,5,6,7,255)):
  for officer in((0,109,236,255)if a.quick else range(256)):
   m,r=fixture(rom,0xC66F);m[0x6F03]=ruler;r['a']=officer;r['x']=(officer*37)&255
   compare(m,r,f'preference/ruler{ruler}/rawID{officer}')
 for entry in(0xC5B9,0xC5D2,0xC6CC):
  for cur in((11,)if a.quick else(0,11,17,31,83,144,255)):
   m,r=fixture(rom,entry);m[0x52]=m[0x54]=cur;compare(m,r,f'baseline/{entry:04X}/cursor{cur}')
 # Full237 scans: status and unrelated location avoid success without faking RNG.
 for status in(0,1,2,3):
  m,r=fixture(rom,0xC71A);m[0x6F73:0x6F7B]=bytes((1,4,5,8,255,255,255,255))
  for i in range(237):m[0x63C0+12*i+11]=status;m[0x63C0+12*i+5]=29
  compare(m,r,f'full-scan/status{status}')
 # Success really appends, sets status2 and discards one caller frame.
 for officer in((109,)if a.quick else(0,109,236)):
  for health in((99,)if a.quick else(0,1,99,255)):
   for location in((2,)if a.quick else(2,1,29)):
    m,r=fixture(rom,0xC71A);m[0x54]=11;m[0x6F73:0x6F7B]=bytes((1,4,5,8,255,255,255,255))
    for i in range(237):m[0x63C0+12*i+11]=(m[0x63C0+12*i+11]&252)|2
    b=0x63C0+12*officer;m[b]=health;m[b+5]=location;m[b+11]&=252
    compare(m,r,f'candidate/ID{officer}/HP{health}/location{location}')
 for difficulty in(0,1,2):
  for full in(False,True):
   m,r=fixture(rom,0xC6CC);m[0x6F02]=difficulty
   m[0x6051:0x605B]=bytes(range(10))if full else bytes((222,255,109,255,255,255,255,255,255,255))
   compare(m,r,f'capacity/difficulty{difficulty}/full{full}')
 # City2 original appearance table begins (ID50,year190), then (226,193).
 # The data window and literal table are original ROM, never patched.
 for year in((90,)if a.quick else(89,90,92,93,154,155)):
  for status in((1,)if a.quick else(0,1,2,3)):
   for cursor in((11,)if a.quick else(0,11,17)):
    m,r=fixture(rom,0xC5D2);m[0x6F00]=year;m[0x52]=11;m[0x54]=cursor
    for ID in(50,226):m[0x63C0+12*ID+11]=(m[0x63C0+12*ID+11]&252)|status
    # For rawyear155, guarantee an eligible first candidate so this case
    # does not claim the FF/yearFF pair is an unconditional list terminator.
    if year==155 and status!=1:continue
    compare(m,r,f'appearance/year{year}/status{status}/cursor{cursor}')
 # Naked success suffix fixtures deliberately bypass the parent capacity
 # check: demonstrate rawY aliasing, rather than assert natural reachability.
 for offset in((28,)if a.quick else(1,27,28,29,30,31)):
  m,r=fixture(rom,0xC765);r['x']=109;m[0x22]=(0x63C0+109*12)&255;m[0x23]=(0x63C0+109*12)>>8
  m[0x6040:0x6140]=bytes(256);m[0x6040+offset]=255
  compare(m,r,f'raw-suffix-firstFF/offset{offset}',domain='explicit_suffix_fixture_bypasses_parent_capacity')
 m,r=fixture(rom,0xC765);r['x']=109;m[0x22]=(0x63C0+109*12)&255;m[0x23]=(0x63C0+109*12)>>8;m[0x6040:0x6140]=bytes(256)
 compare(m,r,'raw-suffix-noFF/full-Y-cycle',domain='explicit_suffix_fixture_bypasses_parent_capacity')
 # Real existing Native caller dumps are optionally produced by the trace tool.
 actual_inputs=[]
 for path in sorted((ROOT/'analysis/phase21/cpu/actual-callers').glob('entry-*/context.json')):
  x=json.loads(path.read_text());folder=path.parent
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),tuple(x['physical_banks']),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],f'actual-Native-context-caller/{folder.name}',domain='actual_saved_Native_context_original_CPU_callee')
  actual_inputs.extend(folder.glob('*'))
 for entry in(0xC5D2,0xC6CC):
  m,r=fixture(rom,entry);compare(m,r,f'missing-fixed/{entry:04X}',False,'strict_missing_dependency_fixture')
 for label,func in(
  ('mandatory_actual_registers',lambda:CityRecruitmentServices(base_memory(rom),rom).run_entry(0xC5B9)),
  ('decimal_rejected',lambda:CityRecruitmentServices(base_memory(rom),rom).run_entry(0xC66F,registers=UIRegisters(p=40))),
  ('wrong_pair',lambda:CityRecruitmentServices(CapturedServiceMemory(rom,banks=(16,12,13,31)),rom).run_entry(0xC5B9,registers=UIRegisters())),
 ):
  try:func();raise AssertionError('Guard did not reject')
  except ValueError:guards.append(dict(name=label,status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in ROOT.glob('source/recovered/*.py')}
 for p in [Path(__file__),ROOT/'scripts/verify_city_auxiliary_services.py',*actual_inputs]:pins[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase21-named-city-recruitment-originalCPU-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,
  original_CPU_parent_cases=len(rows),counts=dict(Counter(x['comparison']for x in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),
  source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,
  executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],
  limits=['Controlled numeric/game-data and caller frames are not Native reachability claims.','Ordinary E89A X passthrough is a no-interrupt callee contract; actual midcallee interrupt effects require separate passive Native observation.','Success in naked C6CC is a true nonlocal return; the C5B9 parent owns the complete outer caller.','Full237 scan contracts do not bound the subsequent raw firstFF roster search.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
