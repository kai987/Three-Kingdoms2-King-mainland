#!/usr/bin/env python3
"""Original CPU differential for the new exact B49C/BD7A readable source.

AllCPU executions occur only here. Pure source delegates fixed services to the
frozen readable Shared owner. Valid campaign fixtures and explicitly raw byte
edges are separate from two actual original-caller inputs prepared from frozen
Native memory. The original prefix creates the latter caller stack; it is not
Nativeinternal instruction tracing and is not an extra differential case.
"""
from pathlib import Path
from collections import Counter
import argparse,copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_auxiliary_services import CityAuxiliaryServices,UIRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import ServiceWait
OUT=ROOT/'analysis/phase18/services'
PARENT=ROOT/'analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame34623'
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regs(c):return{k:getattr(c,k)for k in REGS}
def base_memory(rom):
 return ServiceMemory(rom,Path(str(PARENT)+'-ram.bin').read_bytes(),Path(str(PARENT)+'-sram.bin').read_bytes(),(16,10,11,31),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
def clone(m):
 b=ServiceMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement
 return b
class PureServices:
 def __init__(self,m,rom):self.owner=SceneSharedServices(m,rom);self.calls=Counter()
 def __call__(self,call):self.calls[call.target]+=1;return self.owner(call)
def before_assignment(rom,aux):
 m=base_memory(rom);ram=bytes(m.ram);sram=bytes(m.sram)
 for a,v in((0x6082,1),(0x6083,1),(0x63C0+167*12+8,132),(0x63C0+167*12+9,3),(0x6081,aux)):m[a]=v
 prepared=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(sram,m.sram))if x!=y]
 assert bytes(m.ram)==ram
 # ExplicitCPUmaincontext; frozen Native bytes do not expose its internalPC.
 c=MPU(memory=m);c.a=17;c.x=31;c.y=63;c.p=32;c.sp=255;c.pc=0xE066
 chain=[]
 for n in range(300000):
  if c.pc==0xB49C and m.banks[1:3]==[10,11]:break
  pc=c.pc;sp=c.sp;op=m[c.pc];target=m[(pc+1)&65535]|m[(pc+2)&65535]<<8 if op==0x20 else None
  c.step()
  if op==0x20:chain.append(dict(call_pc=pc,target=target,return_pc=pc+3,caller_sp=sp))
  elif op==0x60:
   ix=next((i for i in range(len(chain)-1,-1,-1)if chain[i]['return_pc']==c.pc and chain[i]['caller_sp']==c.sp),None)
   if ix is not None:del chain[ix:]
 else:raise RuntimeError('Actual assignment entry not reached')
 return m,regs(c),dict(prefix_instructions=n,entry='E066 explicit AXYP/SP',Native_internal_CPU_trace=False,prepared_bytes=prepared,actual_JSR_chain=chain,return_word=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535,native_prefix=str(PARENT.relative_to(ROOT)),native_sha256={e:sha(str(PARENT)+e)for e in('-ram.bin','-sram.bin')})
def controlled(rom,*,roster=(8,),troops=900,reserve=9499,aux=44,gold=257,budget=2,score=50,raw_high=None):
 m=base_memory(rom)
 # Valid indices and intentionally controlled campaign data, not Native state.
 for city in range(30):
  base=0x6000+city*32;m[base]=7
  for j in range(10):m[base+17+j]=255
 m[0x6000]=1;m[0x6001]=aux;m[0x6002]=gold&255;m[0x6003]=gold>>8
 m[0x600C]=reserve&255;m[0x600D]=reserve>>8
 for j,id in enumerate(roster):
  m[0x6011+j]=id
  if id!=255:
   b=0x63C0+12*id;m[b+1]=score;m[b+8]=troops&255;m[b+9]=troops>>8 if raw_high is None else raw_high
 m[0x6F03]=1;m[0x6F5D]=budget;m[0x6F5B]=1;m[0x6F8B]=0;m[0xEE]=15;m[0xEF]=0x6F
 m[0x6F0F]=8;m[0x6F10]=0;m[0x6F84]=0;m[0x6F5E]=0
 m[0x52]=0;m[0x54]=0;m[0x55]=0
 # Disclosed CPU harness returnE188; source never seeds or repairs the frame.
 m[0x1FE:0x200]=bytes((0x87,0xE1));m[0xE1:0xE4]=bytes((48,42,43))
 return m,dict(a=17,x=23,y=31,p=32,sp=253,pc=0xBD7A)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 OUT.mkdir(parents=True,exist_ok=True);rows=[];failures=[];guards=[];visited=Counter();calls=Counter()
 def compare(m,initial,tag,domain,provenance=None,services=True):
  a=clone(m);b=clone(m);c=MPU(memory=a);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  helper=PureServices(b,rom)if services else None;s=CityAuxiliaryServices(b,rom,helper)
  before=bytes(a.sram);returnedPC=((a[0x100+((c.sp+1)&255)]|a[0x100+((c.sp+2)&255)]<<8)+1)&65535;returnedSP=(c.sp+2)&255
  try:
   result=s.run_entry(initial['pc'],registers=r)
   for n in range(1200000):
    if n and(c.pc,c.sp)==(r.pc,r.sp):break
    bank=a.banks[(c.pc-0x8000)//8192]if c.pc>=0x8000 else None
    if bank is not None:visited[bank,c.pc]+=1
    c.step()
   else:raise RuntimeError(f'Originalbudget{c.pc:04X}; source{r.pc:04X}/SP{r.sp:02X}')
   rd=[dict(address=i,original=a.ram[i],source=b.ram[i])for i in range(2048)if a.ram[i]!=b.ram[i]]
   sd=[dict(address=0x6000+i,original=a.sram[i],source=b.sram[i])for i in range(8192)if a.sram[i]!=b.sram[i]]
   rg=[dict(register=k,original=getattr(c,k),source=getattr(r,k))for k in REGS if getattr(c,k)!=getattr(r,k)]
   assert not(rd or sd or rg),dict(RAM=rd[:8],SRAM=sd[:8],registers=rg)
   assert a.io_writes==b.io_writes and a.io_reads==b.io_reads and a.banks==b.banks and a.n163_ram==b.n163_ram,dict(ports=(a.io_writes,b.io_writes),banks=(a.banks,b.banks))
   if result['status']=='returned':assert(r.pc,r.sp)==(returnedPC,returnedSP)
   if helper:calls.update(helper.calls)
   row=dict(tag=tag,domain=domain,entry=initial['pc'],initial_registers=initial,final_registers=vars(r).copy(),comparison='complete_return'if result['status']=='returned'else'strict_prefix',source_status=result['status'],original_instructions=n,pure_source_CPU_callbacks=0,all_RAM_byte_count=2048,all_SRAM_byte_count=8192,ordered_IO_writes=b.io_writes,ordered_IO_reads=b.io_reads,final_banks=list(b.banks),source_services={f'{k:04X}':v for k,v in(helper.calls.items()if helper else())},provenance=provenance,changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(before,b.sram))if x!=y],selected_officer=b[0x38],selected_city=b[0x39],budget=b[0x6F5D])
   rows.append(row);return row
  except Exception as e:
   failures.append(dict(tag=tag,domain=domain,entry=initial['pc'],error=str(e),source_PC=r.pc));print(json.dumps(failures[-1]),flush=True)
 for aux in(0,44):
  m,r,provenance=before_assignment(rom,aux);prefix=OUT/'actual-caller-inputs'/f'aux{aux}';prefix.parent.mkdir(parents=True,exist_ok=True)
  Path(str(prefix)+'-ram.bin').write_bytes(m.ram);Path(str(prefix)+'-sram.bin').write_bytes(m.sram)
  meta=dict(registers=r,physical_banks=list(m.banks),provenance=provenance);Path(str(prefix)+'.json').write_text(json.dumps(meta,indent=2)+'\n')
  compare(m,r,f'actual-original-caller/aux{aux}','Native_memory_derived_original_caller',provenance)
 for troops in(0,900,999,1000,1001,1023):
  for reserve in((0,100,9499)if not a.quick else(9499,)):
   for budget in((1,2,3,30)if not a.quick else(2,)):
    m,r=controlled(rom,troops=troops,reserve=reserve,budget=budget);compare(m,r,f'fill/t{troops}/reserve{reserve}/budget{budget}','valid_campaign_numeric'if troops<=1000 else'explicit_raw_low10_edge')
 for aux in(0,43,44,45,255):
  for gold in((0,1,257,9999,10000,65535)if not a.quick else(257,)):
   m,r=controlled(rom,aux=aux,gold=gold);compare(m,r,f'gate/aux{aux}/gold{gold}','valid_numeric_and_cap_edges')
 for roster in((255,8),(8,255,9),(8,9),(8,8),(255,)*10,tuple(range(8,18))):
  for score in((0,99,100,101,255)if not a.quick else(100,)):
   m,r=controlled(rom,roster=roster,score=score);compare(m,r,f'roster{list(roster)}/score{score}','explicit_roster_holes_alias_tie')
 for high in(3,7,127,255):
  for low in(232,132):
   m,r=controlled(rom,raw_high=high,troops=(3<<8)|low);compare(m,r,f'raw_high{high}/low{low}','explicit_upper6bit')
 # shortage equality: original still purchases one100block; noceil shortcut.
 for reserve in(99,100,101):
  m,r=controlled(rom,reserve=reserve);compare(m,r,f'exact-shortage-boundary/reserve{reserve}','valid_campaign_numeric')
 # Purchase byte wraps with a raw1001..1023low10 need underflow; the previous
 # matrix retains this integer path rather than treating high bits as padding.
 for budget in(0,255):
  m,r=controlled(rom,budget=budget);compare(m,r,f'budgetbyte{budget}','explicit_budget_edge')
 # Cover B49C secondary sampling paths independently of actualNative RNG.
 for cursor in((0,17,39,83,147,255)if a.quick else range(0,256,11)):
  m,r=controlled(rom,budget=2);m[0x55]=cursor;m[0x54]=cursor;r['pc']=0xB49C
  compare(m,r,f'assignment-cursors{cursor}','explicit_rejection_sampling_context')
 # Exact stack wrap/nonlocal budget contexts, with the already existing
 # harness caller words explicitly relocated before invoking either side.
 for sp in((0,255)if a.quick else(0,1,127,254,255)):
  for budget in(1,2,3):
   m,r=controlled(rom,budget=budget);m[0x100+((sp+1)&255)]=0x87;m[0x100+((sp+2)&255)]=0xE1;r['sp']=sp
   compare(m,r,f'callerSP{sp}/budget{budget}','explicit_caller_stack_wrap')
 for second_actor in(9,8):
  m,r=controlled(rom,score=100);b=0x6000+29*32;m[b]=1;m[b+1]=44;m[b+2]=1;m[b+3]=1;m[b+12]=27;m[b+13]=37;m[b+17]=second_actor
  ob=0x63C0+12*second_actor;m[ob+1]=100;m[ob+8]=132;m[ob+9]=3
  compare(m,r,f'later-city-tie/actor{second_actor}','explicit_cross_city_tie_alias')
 for pattern in(0,255,44):
  m,r=controlled(rom)
  for city in range(30):
   for offset in(28,29,30,31):m[0x6000+city*32+offset]=pattern
  compare(m,r,f'opaque-tail-pattern{pattern}','opaque_bytes_preservation')
 for entry in(0xB49C,):
  m,r=controlled(rom);r['pc']=entry;compare(m,r,'missing-service/actual-E8AA-frame','strict_missing_dependency',services=False)
 for name,fn in[
  ('actual_registers_required',lambda:CityAuxiliaryServices(base_memory(rom),rom).run_entry()),
  ('wrong_pair',lambda:CityAuxiliaryServices(ServiceMemory(rom,banks=(16,12,13,31)),rom).run_entry(0xBD7A,registers=UIRegisters())),
  ('nonowned_entry',lambda:CityAuxiliaryServices(base_memory(rom),rom).run_entry(0xBD95,registers=UIRegisters())),
  ('decimal_flag',lambda:CityAuxiliaryServices(base_memory(rom),rom).run_entry(0xBD7A,registers=UIRegisters(p=40))),
 ]:
  try:fn();raise AssertionError('sourceguard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 for status in(None,'dependency','waiting','blocked','error'):
  m,r=controlled(rom);r['pc']=0xB49C
  def callback(call):call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp;return None if status is None else dict(status=status)
  s=CityAuxiliaryServices(m,rom,callback);out=s.run_entry(0xB49C,registers=UIRegisters(**r));assert out['status']=='dependency'and s.pending is not None
  guards.append(dict(name=f'explicit-return-required/{status}',status='passed'))
 pins={str(x.relative_to(ROOT)):sha(x)for x in ROOT.glob('source/recovered/*.py')}
 pins['scripts/verify_city_auxiliary_services.py']=sha(__file__);pins['scripts/trace_city_auxiliary_fields.py']=sha(ROOT/'scripts/trace_city_auxiliary_fields.py')
 pins.update({str(x.relative_to(ROOT)):sha(x)for x in(OUT/'actual-caller-inputs').glob('*')})
 receipt=dict(schema='phase18-city-auxiliary-services-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=a.quick,rom_cpu_case_count=len(rows),source_guard_case_count=len(guards),case_count=len(rows)+len(guards),failed_count=len(failures),complete_return_count=sum(x['comparison']=='complete_return'for x in rows),strict_prefix_count=sum(x['comparison']=='strict_prefix'for x in rows),source_original_CPU_callbacks=0,production_IR_interpretation=False,cases=rows,failures=failures,guards=guards,source_sha256=pins,executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],pure_fixed_services={f'{k:04X}':v for k,v in calls.items()},scope=dict(RAM='all2048 including active and inactive stack',SRAM='all8192',registers='A X Y P SP PC',ports='ordered writes and reads',mapper='all4banks',N163='all128 modeledbytes',hardware='explicit validator inputs; no rendering or waveform synthesis'),limits=['Originalprefix starts from declaredE066 registers over frozenNative RAM/SRAM, not NativeinternalPC.','Subroutine returnE188 harness is explicitly prepared for numeric fixtures; source itself never seeds a frame.','B49C redistributes rosters using frozen readable helpers; BD7A fallback retains frozen BEC7 development, not new wholeAI recovery.','Incomplete services stop at their original callee frame; no readiness or acknowledgement is synthesized.'])
 (OUT/'validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:receipt[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','failed_count')}));return 0 if not failures else 1
if __name__=='__main__':sys.exit(main())
