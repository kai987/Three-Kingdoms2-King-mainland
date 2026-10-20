#!/usr/bin/env python3
"""Exact G106 resource caller Source comparison; complete/prefix separate."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle_resource_services import PostbattleResourceServices
from source.recovered.postbattle_resource_integration import PostbattleResourceGameEngine
from source.recovered.battle_setup_ai import SetupRegisters,ROM_SHA256
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_deployment_pointer_phase26 import clone,registers
from verify_city_auxiliary_services import base_memory
OUT=ROOT/'analysis/phase27/resources'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class ObservedResources(PostbattleResourceServices):
 """Validator-only observation of production writes, with no CPU fallback."""
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.selected_stores=[]
 def _write_resource_byte(self,index,value):
  m=self.memory;pointer=m[0x1A]|m[0x1B]<<8
  self.selected_stores.append(dict(pointer_before=pointer,Y=index,effective_address=(pointer+index)&65535,value=value&255))
  super()._write_resource_byte(index,value)
def fixture(rom,entry=0xBF0A,*,city=4,outcome=0,rounds=21,value=9999,rate=1,field=6,sp=253,p=32,cursor=0):
 m=clone(base_memory(rom));m.banks[:]=[1,8,9,31];m.ram[0xDE:0xE4]=bytes((33,40,41,33,40,41));m[0x50E]=city;m[0x514]=outcome;m[0x506]=rounds;m[0x50]=cursor
 ptr=0x6000+32*city;m[0x1A]=ptr&255;m[0x1B]=ptr>>8
 for offset in(2,4,6,8,14):m[ptr+offset]=value&255;m[ptr+offset+1]=value>>8
 m[ptr+11]=value&255;m[3]=rate;m[0]=value&255;m[1]=value>>8;m[2]=0
 ret={0xBF0A:0xBB99,0xBF9E:0xBF37,0xBFB3:0xBF84,0xBFEC:0xBF89}[entry]
 m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8
 m.n163_ram[:]=bytes((11+37*i)&255 for i in range(128));m.n163_address=127;m.n163_autoincrement=True;m.io_reads.clear();m.io_writes.clear();m.combined_IO.clear()
 return m,dict(a=17,x=73,y=field,p=p,sp=sp,pc=entry)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();inputs=[]
 def compare(m,initial,tag,domain='controlled_original_software_caller_fixture',services=True,provenance=None):
  left,right=clone(m),clone(m);c=MPU(memory=left);r=SetupRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  co=PostbattleResourceGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None
  owner=ObservedResources(right,rom,co if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   original_stores=[]
   for n in range(1500000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000,(tag,hex(c.pc));bank=left.banks[(c.pc-0x8000)//8192];visited[bank,c.pc]+=1
    if bank==8 and c.pc in(0xBFDF,0xBFE9):
     pointer=left[0x1A]|left[0x1B]<<8;original_stores.append(dict(pointer_before=pointer,Y=c.y,effective_address=(pointer+c.y)&65535,value=c.a))
    c.step()
   else:raise RuntimeError(f'CPU budget{c.pc:04X},Source{r.pc:04X}')
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM/SRAM',rd[:8],sd[:8]);assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.combined_IO==right.combined_IO and left.banks==right.banks,(tag,'combinedIO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   assert original_stores==owner.selected_stores,(tag,'selected_indirect_write_order',original_stores,owner.selected_stores)
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return'}.get(result['status'],'strict_missing_dependency_prefix'),original_instructions=n,RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC_ordered_IO_four_banks_N163_equal=True,combined_logical_IO_read_write_interleaving_equal=True,combined_IO_events=right.combined_IO,source_original_CPU_callbacks=0,changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y],pointer1A_after=right[0x1A]|right[0x1B]<<8,selected_indirect_stores=original_stores,Source_selected_indirect_store_order_equal=True,events=result['events'],provenance=provenance))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 boundaries=(0,1,99,100,255,256,500,501,502,9999,10000,13107,13108,32767,32768,65535)
 for city in((4,)if a.quick else(0,4,29)):
  for rounds in((5,21)if a.quick else(0,5,6,10,11,15,16,20,21,255)):
   for value in((501,65535)if a.quick else boundaries):
    for cursor in((0,)if a.quick else(0,1)):
     m,r=fixture(rom,city=city,rounds=rounds,value=value,cursor=cursor);compare(m,r,f'full-parent/city{city}/round{rounds}/value{value}/cursor{cursor}',domain='complete_BF0A_city_resource_caller')
 for outcome in((1,255)if a.quick else range(1,256)):
  m,r=fixture(rom,outcome=outcome);compare(m,r,f'no-loss-outcome/{outcome}',domain='complete_BF0A_early_return_caller')
 # Raw cities are mechanical F2AF selectors, not legal UI city identities.
 for city in((30,255)if a.quick else range(30,256)):
  m,r=fixture(rom,city=city,value=65535);compare(m,r,f'raw-city/{city}',domain='complete_BF0A_explicit_raw8_city_caller')
 for entry in(0xBF9E,0xBFB3):
  for field in((6,11,255)if a.quick else(0,1,2,4,6,8,11,14,28,31,255)):
   for rate in((1,255)if a.quick else(0,1,2,5,9,10,11,255)):
    for value in((65535,)if a.quick else(0,501,13108,65535)):
     m,r=fixture(rom,entry,field=field,rate=rate,value=value);compare(m,r,f'helper/{entry:04X}/Y{field}/rate{rate}/value{value}',domain='bare_helper_with_explicit_city_base_and_raw_field_rate')
 for value in((0,501,502,65535)if a.quick else range(0,65536,127)):
  m,r=fixture(rom,0xBFEC,field=2,value=value);compare(m,r,f'rate-selection/word{value}',domain='complete_threshold_helper_caller')
 # Deliberate aliases are separate from the typed city contract. The first
 # low write can change1A/1B and therefore the second store's effective
 # address; scratch02 can also alter the value loaded for that second write.
 for pointer in(0x001A,0x001B,0x081A,0,1,2,3,6,8,9):
  m,r=fixture(rom,0xBF9E,field=0,rate=9,value=65535);m[0x1A]=pointer&255;m[0x1B]=pointer>>8
  if pointer==0x001B:m[0x1C]=1
  compare(m,r,f'raw-pointer-alias/{pointer:04X}',domain='controlled_bare_helper_alias_not_typed_city_or_Native')
 for entry in PostbattleResourceServices.NEW_ENTRIES:
  for sp in((0,255)if a.quick else(0,1,2,127,252,253,254,255)):
   for bits in((0,15)if a.quick else range(16)):
    flags=32|(bits&3)|((bits&4)<<4)|((bits&8)<<4);m,r=fixture(rom,entry,p=flags,sp=sp);compare(m,r,f'flags-stack/{entry:04X}/SP{sp}/P{flags}')
 # Missing fixed services are real prefixes. Never claim their effect was
 # supplied; the original oracle stops at the same actual call frame.
 for entry in(0xBF0A,0xBF9E,0xBFB3):
  m,r=fixture(rom,entry);compare(m,r,f'missing-fixed/{entry:04X}',services=False,domain='strict_missing_dependency_fixture')
 for path in sorted((ROOT/'analysis/phase27/cpu-resource/actual-callers').glob('entry-*/context.json')):
  x=json.loads(path.read_text());folder=path.parent
  if x['registers']['pc']not in PostbattleResourceServices.NEW_ENTRIES:continue
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],f'exported/{folder.name}',domain=x['origin'],provenance=x);inputs.extend(folder.iterdir())
 m,r=fixture(rom)
 for name,fn in(('actual_registers_required',lambda:PostbattleResourceServices(m,rom).run_entry()),('seed_return_rejected',lambda:PostbattleResourceServices(m,rom).run_entry(registers=SetupRegisters(**r),seed_return=True)),('wrong_PC_rejected',lambda:PostbattleResourceServices(m,rom).run_entry(0xBF9E,registers=SetupRegisters(**r))),('wrong_pair_rejected',lambda:PostbattleResourceServices(CapturedServiceMemory(rom,banks=(16,10,11,31)),rom).run_entry(registers=SetupRegisters(**r))),('decimal_rejected',lambda:PostbattleResourceServices(m,rom).run_entry(registers=SetupRegisters(**dict(r,p=40)))),('wrong_return_rejected',lambda:PostbattleResourceServices(m,rom).run_entry(registers=SetupRegisters(**r),return_pc=0x0200))):
  try:fn();raise AssertionError('guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 def false_completion(call):return dict(status='returned')
 bad=PostbattleResourceServices(clone(m),rom,false_completion);reply=bad.run_entry(registers=SetupRegisters(**r));assert reply['status']=='dependency'and bad.pending is not None
 guards.append(dict(name='returned_string_without_real_PC_SP_does_not_complete_service',status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in(Path(__file__),ROOT/'scripts/verify_deployment_pointer_phase26.py',ROOT/'scripts/verify_city_auxiliary_services.py'):pins[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase27-postbattle-resource-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),counts=dict(Counter(r['comparison']for r in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],limits=['The resource-loss arithmetic was previously named Source; this module adds exact caller/scratch/stack/mapping protocol, not first discovery.','All2048RAM including free stack,8192SRAM,AXYP-SP-PC,ordered read/write interleaving,4PRG and shared declaredN163 are compared. No IRQ/NMI/fakeack occurs during callee comparisons.','A006/BAB3 and its ECEE parent remain outside this exact owner; direct BF0A/helper success is not completion of that parent.','Bare/raw helpers and invalid city bytes are explicit CPU domains, not naturally reachable menu or field-name evidence.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','source_guard_count','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
