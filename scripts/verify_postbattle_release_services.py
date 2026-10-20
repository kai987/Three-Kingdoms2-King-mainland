#!/usr/bin/env python3
"""Original-CPU differential tests of independent postbattle release source.

The numeric and software-caller fixtures below are explicit CPU fixtures,
never Native gameplay. No original CPU is called from the production side.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import CapturedServiceMemory
from source.recovered.postbattle_release_services import PostbattleReleaseController,BattleRegisters,ROM_SHA256
from source.recovered.wild_recruitment_integration import WildRecruitmentGameEngine
from source.recovered.city_recruitment_services import CityRecruitmentServices,UIRegisters
OUT=ROOT/'analysis/phase22/release'
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registers(r):return{k:getattr(r,k)for k in REGS}
def clone(m):
 b=CapturedServiceMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement;return b
def fixture(rom,entry=0xD20D,*,city=4,officer=167,cursor=0):
 """Controlled valid-row fixture, with a declared existing software frame."""
 pre=ROOT/'analysis/runtime/phase3/attack-intro-7'
 m=CapturedServiceMemory(rom,Path(str(pre)+'-ram.bin').read_bytes(),Path(str(pre)+'-sram.bin').read_bytes(),(16,12,13,31),
  read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 m[0xDE:0xE4]=bytes((48,44,45,48,44,45));m[0x1FC:0x200]=bytes((0x2F,0xCF,0x80,0xF9))
 m[0x50E]=city;m[0x540]=30;m[0x50B]=2;m[0x507]=0x21;m[0x50]=cursor
 m[0x42C:0x440]=bytes((officer,))+bytes([255])*19;m[0x580:0x594]=bytes((0,))+bytes([255])*19
 for base in(0x600,0x614,0x628,0x63C,0x650,0x664):m[base:base+20]=bytes([255])*20
 m[0x600]=10;m[0x614]=12;m[0x628]=3;m[0x63C]=8;m[0x650]=7;m[0x664]=officer
 m[0x6F47:0x6F6F]=bytes([255])*40
 return m,dict(a=17,x=23,y=0,p=32,sp=251,pc=entry)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();inputs=[]
 def compare(m,initial,tag,*,services=True,domain='controlled_numeric_and_caller_CPU_fixture'):
  left,right=clone(m),clone(m);c=MPU(memory=left);recruit=tuple(right.banks[1:3])==(10,11);r=(UIRegisters if recruit else BattleRegisters)(**initial)
  for k,v in initial.items():setattr(c,k,v)
  game=WildRecruitmentGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();assert co.external_callback is None
  owner=(CityRecruitmentServices if recruit else PostbattleReleaseController)(right,rom,co if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   for steps in range(250000):
    if steps and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000,(tag,hex(c.pc));visited[left.banks[(c.pc-0x8000)//8192],c.pc]+=1;c.step()
   else:raise RuntimeError(f'OriginalCPU budget PC{c.pc:04X}; source{r.pc:04X}')
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'memory',rd[:8],sd[:8])
   assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],
    comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return'}.get(result['status'],'strict_missing_dependency_prefix'),original_instructions=steps,
    RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC_ordered_IO_banks_N163_equal=True,source_original_CPU_callbacks=0,
    changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y],
    requested_calls=result['events'],final_data_bank=right.banks[0]))
  except Exception as exc:failures.append(dict(case=tag,error=str(exc)));print(json.dumps(failures[-1]),flush=True)
 # Every RNG cursor and several actual neighbor topologies: preserve original
 # random_eight and bank16 addressing, including missing-neighbor fallback.
 for city in((4,)if a.quick else(0,2,4,29)):
  for cursor in((0,1,127,255)if a.quick else range(256)):
   m,r=fixture(rom,city=city,cursor=cursor);compare(m,r,f'release/city{city}/cursor{cursor}')
 # Health/troop bits and incoming status are not release predicates; retain
 # them apart from the actual status low2 clear.
 for officer in((167,)if a.quick else(0,109,236)):
  for status in((2,)if a.quick else(0,1,2,3,0xAE,0xFE,0xFF)):
   for troops in((1098,)if a.quick else(0,1023,1098,65535)):
    for hp in((99,)if a.quick else(0,99,255)):
     m,r=fixture(rom,officer=officer,cursor=73);at=0x63C0+12*officer;m[at]=hp;m[at+8]=troops&255;m[at+9]=troops>>8;m[at+11]=status
     compare(m,r,f'release-numeric/id{officer}/status{status}/rawtroops{troops}/HP{hp}')
 # Cleanup first-match priority, duplicate aliases, both captive halves and no
 # match. These entry-A values do not depend on the separate officer pointer.
 for officer in((167,)if a.quick else(0,109,236,255)):
  for kind in('active-first','active-last','active-and-captive','captive-0','captive-19','captive-20','captive-39','no-match'):
   m,r=fixture(rom,0xD299,officer=officer);r['a']=officer
   m[0x664:0x678]=bytes([254])*20;m[0x6F47:0x6F6F]=bytes([254])*40
   if kind=='active-first':m[0x664]=officer
   elif kind=='active-last':m[0x677]=officer
   elif kind=='active-and-captive':m[0x664]=m[0x665]=m[0x6F47]=officer
   elif kind.startswith('captive-'):m[0x6F47+int(kind.split('-')[1])]=officer
   compare(m,r,f'cleanup/id{officer}/{kind}')
 # Real city allocation remains part of the shared body: firstFF, neutral
 # owner high-nibble mask, commander destination and returned side context.
 for city in((4,)if a.quick else(0,4,29)):
  for count in((0,)if a.quick else(0,9)):
   for owner_byte in((7,)if a.quick else(1,7,0xAF,0xF7)):
    for side in((2,)if a.quick else(2,0x12)):
     m,r=fixture(rom,city=4);m[0x540]=city;m[0x50B]=side;m[0x52B]=167
     b=0x6000+32*city;m[b]=owner_byte;m[b+17:b+27]=bytes(range(count))+bytes([255])*(10-count)
     compare(m,r,f'allocate/city{city}/prefix{count}/owner{owner_byte}/side{side}')
 # Parent selection: all20 raw flags checked; active cleanup and duplicate
 # selections are ordered. Nonnegative flags are all selected, not only0.
 for flags in((bytes([255])*20,bytes((0,))+bytes([255])*19)if a.quick else(bytes([255])*20,bytes((0,))+bytes([255])*18+bytes((127,)),bytes(20),bytes([127])*20)):
  m,r=fixture(rom,0xD1F9);m[0x580:0x594]=flags;m[0x42C:0x440]=bytes(range(20));m[0x664:0x678]=bytes(range(20))
  compare(m,r,f'selected-parent/nonnegative{sum(v<128 for v in flags)}/value{flags[0]}')
 for entry in(0xD1F9,0xD20D):
  m,r=fixture(rom,entry);compare(m,r,f'missing-fixed/{entry:04X}',services=False,domain='strict_missing_dependency_fixture')
 # The diagnostic exporter never seeds a software frame. Origin explicitly
 # separates a pure saved-PC prefix from the release hardware-NMI fixture.
 for path in sorted((ROOT/'analysis/phase22/cpu/actual-callers').glob('entry-*/context.json')):
  x=json.loads(path.read_text());folder=path.parent;assert x['prepared_numeric_bytes']==[]
  assert x['origin']in('actual_Native_snapshot_originalCPU_reached_caller','Native_snapshot_plus_declared_hardware_NMI_CPU_fixture')
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(1,0)if x['injected_new_NMI']else(0,0))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],f'exported-caller/{folder.name}',domain=x['origin']);inputs.extend(folder.iterdir())
 # Source-domain guards do not count as original CPU cases.
 m,r=fixture(rom)
 for name,func in(
  ('actual_registers_required',lambda:PostbattleReleaseController(clone(m),rom).run_entry(0xD20D)),
  ('seeded_return_rejected',lambda:PostbattleReleaseController(clone(m),rom).run_entry(0xD20D,registers=BattleRegisters(**r),seed_return=True)),
  ('wrong_return_word_rejected',lambda:PostbattleReleaseController(clone(m),rom).run_entry(0xD20D,registers=BattleRegisters(**r),return_pc=0x0200)),
  ('decimal_mode_rejected',lambda:PostbattleReleaseController(clone(m),rom).run_entry(0xD20D,registers=BattleRegisters(**{**r,'p':40}))),
  ('wrong_pair_rejected',lambda:PostbattleReleaseController(CapturedServiceMemory(rom,banks=(16,10,11,31)),rom).run_entry(0xD20D,registers=BattleRegisters(**r))),
 ):
  try:func();raise AssertionError('Source guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};sources[str(Path(__file__).relative_to(ROOT))]=sha(__file__)
 result=dict(schema='phase22-postbattle-release-originalCPU-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),counts=dict(Counter(x['comparison']for x in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),
  source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=sources,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},
  executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],
  limits=['These are declared numeric and software-caller fixtures, not Native reachability observations.','The real battle controller creates destination30 and selected rows; direct D20D does not rerun its UI predicates.','Source has no original-CPU fallback or automatic text/NMI/IRQ readiness.','BC11 allocation and E856 RNG use existing frozen direct source; new hand-written code is D1F9..D2CC only.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
