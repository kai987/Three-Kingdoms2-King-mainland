#!/usr/bin/env python3
"""Original-CPU comparisons for the city threshold's real resource helpers."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_threshold_services import CityThresholdServices,UIRegisters,ROM_SHA256
from source.recovered.city_threshold_integration import CityThresholdGameEngine
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_city_auxiliary_services import base_memory,controlled
OUT=ROOT/'analysis/phase23/threshold';REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registers(c):return{k:getattr(c,k)for k in REGS}
def clone(m):
 b=CapturedServiceMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement;return b
def fixture(rom,entry=0xD105,*,city=2,gold=8888,grain=9999,cost=0,bound=0,sp=253,p=32):
 m=clone(base_memory(rom));b=0x6000+32*city;m[b+2]=gold&255;m[b+3]=gold>>8;m[b+4]=grain&255;m[b+5]=grain>>8
 m[0x20]=b&255;m[0x21]=b>>8;m[0x22]=cost&255;m[0x23]=cost>>8;m[0x24]=bound;m[0x52]=73
 ret={0xD105:0xBD90,0xD69D:0xD126,0xD36F:0xBE7E}[entry]
 m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8
 return m,dict(a=city,x=0xA5,y=0x73,p=p,sp=sp,pc=entry)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();inputs=[]
 def compare(m,initial,tag,domain='controlled_numeric_and_software_caller_CPU_fixture',services=True):
  left,right=clone(m),clone(m);cpu=MPU(memory=left);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(cpu,k,v)
  game=CityThresholdGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();assert co.external_callback is None
  owner=CityThresholdServices(right,rom,co if services else None)
  try:
   reply=owner.run_entry(initial['pc'],registers=r)
   for steps in range(1500000):
    if steps and(cpu.pc,cpu.sp)==(r.pc,r.sp)and(reply['status']in('returned','nonlocal_return')or registers(cpu)==registers(r)):break
    assert cpu.pc>=0x8000,(tag,hex(cpu.pc));visited[left.banks[(cpu.pc-0x8000)//8192],cpu.pc]+=1;cpu.step()
   else:raise RuntimeError(f'CPU budget{cpu.pc:04X}; source{r.pc:04X}')
   rd=[(n,x,y)for n,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+n,x,y)for n,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'memory',rd[:8],sd[:8])
   assert registers(cpu)==registers(r),(tag,'registers',registers(cpu),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=reply['status'],comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return'}.get(reply['status'],'strict_missing_dependency_prefix'),original_instructions=steps,
    RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC_ordered_IO_four_banks_N163_equal=True,source_original_CPU_callbacks=0,
    changed_SRAM=[dict(address=0x6000+n,before=x,after=y)for n,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y],calls=reply['events']))
  except Exception as exc:failures.append(dict(case=tag,error=str(exc)));print(json.dumps(failures[-1]),flush=True)
 # D105 builds the actual raw8 city pointer, performs both caps, and returns
 # owner low3. Raw30..255 is a byte/mechanical CPU domain, not legal UI cities.
 for city in((0,2,29,255)if a.quick else range(256)):
  for gold,grain in((9999,10000),(10000,9999),(65535,65535)):
   m,r=fixture(rom,city=city,gold=gold,grain=grain);compare(m,r,f'pointer/rawcity{city}/gold{gold}/grain{grain}',domain='legal_city_CPU_fixture'if city<30 else'explicit_raw8_city_CPU_fixture')
 boundaries=(0,255,256,257,258,299,300,512,9999,10000,10001,32767,32768,65535)
 for city in((2,)if a.quick else(0,2,29,255)):
  for gold in((9999,10000,65535)if a.quick else boundaries):
   for grain in((9999,10000)if a.quick else boundaries):
    m,r=fixture(rom,0xD69D,city=city,gold=gold,grain=grain);compare(m,r,f'cap/rawcity{city}/gold{gold}/grain{grain}')
 for city in((2,)if a.quick else(0,2,29,255)):
  for gold in((0,257,9999,10000)if a.quick else(0,1,19,20,255,256,257,9999,10000,65535)):
   for cost in((0,20,65535)if a.quick else(0,1,20,256,9999,10000,65535)):
    for bound in((0,20)if a.quick else(0,1,20,255)):
     m,r=fixture(rom,0xD36F,city=city,gold=gold,grain=10000,cost=cost,bound=bound);compare(m,r,f'pay/rawcity{city}/gold{gold}/cost{cost}/bound{bound}')
 # Actual caller stack wrap and observable NZCV effects of the final grain
 # comparison or failed payment: every binary NZCV combination is included.
 for entry in(0xD105,0xD69D,0xD36F):
  for sp in((0,255)if a.quick else(0,1,2,3,127,252,253,254,255)):
   for bits in((0,195)if a.quick else range(16)):
    flags=32|((bits&1)|((bits&2))|((bits&4)<<4)|((bits&8)<<4))if not a.quick else 32|bits
    m,r=fixture(rom,entry,gold=10000,grain=65535,cost=10000,sp=sp,p=flags);compare(m,r,f'caller-flags/{entry:04X}/SP{sp}/P{flags}')
 # The whole already-recovered consumer uses these new helpers via ordinary
 # virtual calls. Its body is reused, not counted as new Source recovery.
 for aux,gold in((0,257),(0,258),(0,512),(43,257),(44,257),(0,10000)):
  for reserve in((9499,)if a.quick else(0,99,100,101,9499)):
   m,r=controlled(rom,roster=(8,),troops=900,reserve=reserve,aux=aux,gold=gold,budget=2)
   compare(m,r,f'full-consumer/aux{aux}/gold{gold}/reserve{reserve}',domain='controlled_complete_BD7A_caller')
 m,r=controlled(rom,roster=(8,),troops=900,reserve=9499,aux=0,gold=32768,budget=2)
 compare(m,r,'full-consumer/cap_changes_goldlow0_to15',domain='explicit_overcap_BD7A_caller')
 m,r=controlled(rom,roster=(8,),troops=900,reserve=0,aux=44,gold=1,budget=2)
 compare(m,r,'full-consumer/payment_refusal_does_not_cancel_fill',domain='explicit_insufficient_gold_BD7A_caller')
 m,r=fixture(rom,0xD36F,bound=20);compare(m,r,'missing-RNG-service/D36F',services=False,domain='strict_missing_dependency_fixture')
 # New formal exports retain their own actual/prepared origin metadata.
 for path in sorted((ROOT/'analysis/phase23/cpu-threshold/actual-callers').glob('entry-*/context.json')):
  x=json.loads(path.read_text());folder=path.parent
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],f'exported/{folder.name}',domain=x['origin']);inputs.extend(folder.iterdir())
 # Read-only inspection semantics, not CPU-register-equivalent subroutines.
 model_checks=[];m,r=fixture(rom);owner=CityThresholdServices(m,rom)
 for aux in range(256):
  for low in range(256):
   m[0x6041]=aux;m[0x6042]=low;m[0x6043]=1
   before=(bytes(m.ram),bytes(m.sram));x=owner.threshold_snapshot(2)
   assert x['BD97_gate_passes']==(low>=2 or low==1 and aux>=44)
   assert before==(bytes(m.ram),bytes(m.sram))
 model_checks.append(dict(name='inspection_all65536_aux_and_low_byte_pairs',passed=True,finite_formula_inputs=65536,original_CPU_cases=0))
 for name,func in(
  ('actual_registers_required',lambda:CityThresholdServices(m,rom).run_entry(0xD105)),
  ('wrong_pair_rejected',lambda:CityThresholdServices(CapturedServiceMemory(rom,banks=(16,12,13,31)),rom).run_entry(0xD105,registers=UIRegisters())),
  ('decimal_rejected',lambda:CityThresholdServices(m,rom).run_entry(0xD105,registers=UIRegisters(p=40))),
  ('inspection_noncity_rejected',lambda:CityThresholdServices(m,rom).threshold_snapshot(30)),
  ('inspection_bool_rejected',lambda:CityThresholdServices(m,rom).threshold_snapshot(True)),
 ):
  try:func();raise AssertionError('Guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in(Path(__file__),ROOT/'scripts/verify_city_auxiliary_services.py'):sources[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase23-city-threshold-resource-helper-CPU-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),counts=dict(Counter(x['comparison']for x in rows)),source_guard_count=len(guards),guards=guards,model_checks=model_checks,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,
  cases=rows,failures=failures,failed_count=len(failures),source_sha256=sources,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},
  executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],
  limits=['Controlled rawbyte contexts are not Native UI legality claims.','Existing BD7A/B49C and shared RNG remain frozen direct-source dependencies, not newly recovered instruction counts.','The optional inspection API has read-only game-data semantics, not an AXYP/stack/mapper contract.','No additional hardware interrupt or fake readiness is supplied during a callee comparison.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
