#!/usr/bin/env python3
"""Phase28 exact postbattle stage2; pure Source and originalCPU separate."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle_parent_services import PostbattleParentServices
from source.recovered.postbattle_resource_integration import PostbattleResourceGameEngine
from source.recovered.battle_setup_ai import SetupRegisters,ROM_SHA256
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_postbattle_resource_services import fixture as resource_fixture
from verify_deployment_pointer_phase26 import clone,registers
OUT=ROOT/'analysis/phase28/parent-services'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _wrong_pair(memory):
 m=clone(memory);m.banks[1:3]=[12,13];return m
def fixture(rom,entry=0xA006,*,stage=2,outcome=0,escaped=255,status=2,city=4,destination=11,value=9999,supply=9999,sp=253,p=32):
 m,r=resource_fixture(rom,city=city,outcome=outcome,value=value,sp=sp,p=p);r['pc']=entry;m[0x501]=stage;m[0x52B]=escaped;m[0x52C]=destination
 for offset in(2,4):m[0x6000+32*destination+offset]=value&255;m[0x6000+32*destination+offset+1]=value>>8
 if escaped!=255:
  a=0x63C0+12*escaped+11;m[a]=(m[a]&252)|status
 for at in(0x522,0x524,0x526,0x528):m[at]=supply&255;m[at+1]=supply>>8
 m.ram[0x100:0x140]=bytes((13*i+7)&255 for i in range(64))
 ret=0xBB9C if entry==0xC027 else 0xEE4D;m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8
 m.io_reads.clear();m.io_writes.clear();m.combined_IO.clear();return m,r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();input_pins={};passive_count=0
 def compare(m,initial,tag,services=True,pause_then_resume=False,domain='controlled_original_software_caller_fixture',provenance=None):
  left,right=clone(m),clone(m);c=MPU(memory=left)
  for k,v in initial.items():setattr(c,k,v)
  r=SetupRegisters(**initial);co=PostbattleResourceGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None
  owner=PostbattleParentServices(right,rom,co if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   stages=[]
   if pause_then_resume:
    assert result['status']=='dependency'and owner.pending.target==0xECEE
    pending=owner.pending
    for prefix in range(100):
     if registers(c)==registers(r):break
     c.step()
    else:raise AssertionError('No original ECEE prefix match')
    assert left.ram==right.ram and left.sram==right.sram and left.combined_IO==right.combined_IO and left.banks==right.banks
    before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO),list(right.banks))
    owner.services=lambda call:dict(status='returned')
    assert owner.resume()['status']=='dependency'and owner.pending is pending
    assert before==(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO),list(right.banks))
    stages.append(dict(kind='strict_same_generator_ECEE_pending',original_prefix_instructions=prefix,registers=registers(r),fake_return_did_not_advance=True))
    owner.services=co;result=owner.resume()
   for n in range(200000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000;visited[left.banks[(c.pc-0x8000)//8192],c.pc]+=1;c.step()
   else:raise RuntimeError(('budget',c.pc,r.pc))
   assert left.ram==right.ram and left.sram==right.sram,(tag,'RAM/SRAM',[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y][:8])
   assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.combined_IO==right.combined_IO and left.banks==right.banks,(tag,'combinedIO/banks')
   assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   if result['status']=='returned'and initial['pc']in(0xA006,0xBAB3,0xBB93):
    assert list(right.ram[0x87:0x8A])==[1,0,4]and right[0x8A]==m[0x8A]and right[0x501]==(m[0x501]+1)&255,(tag,'Immediate fade request never waits or fabricates completion')
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison='actual_caller_RTS'if result['status']=='returned'else'nonlocal_return'if result['status']=='nonlocal_return'else'strict_dependency_prefix',original_CPU_instructions=n+(prefix if pause_then_resume else 0),RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC_combined_IO_four_banks_shared_N163_equal=True,source_original_CPU_callbacks=0,initial_stage=m[0x501],final_stage=right[0x501],initial_fade=list(m.ram[0x87:0x8B]),final_fade=list(right.ram[0x87:0x8B]),events=result['events'],sequence_checkpoints=stages,provenance=provenance))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 # Quick first checks are small controlled callers, not passive Native inputs.
 for entry in PostbattleParentServices.NEW_ENTRIES:
  for outcome in(0,1):
   for escaped,status in((255,0),(5,0),(5,1),(5,2),(5,3)):
    m,r=fixture(rom,entry,outcome=outcome,escaped=escaped,status=status);compare(m,r,f'controlled/{entry:04X}/outcome{outcome}/escape{escaped}/status{status}')
 for stage in(0,1,3):
  m,r=fixture(rom,stage=stage);compare(m,r,f'unimplemented-stage/{stage}')
 for entry in(0xA006,0xBB93,0xC027):
  m,r=fixture(rom,entry);compare(m,r,f'missing-services/{entry:04X}',services=False)
 if not a.quick:
  for outcome in(0,1):
   for escaped,status in((255,0),(5,0),(5,1),(5,2),(5,3)):
    for value in(0,1,9999,10000,32767,65535):
     for supply in(0,1,9999,32768,65535):
      m,r=fixture(rom,0xC027,outcome=outcome,escaped=escaped,status=status,value=value,supply=supply);compare(m,r,f'supply-boundary/o{outcome}/e{escaped}/s{status}/v{value}/a{supply}')
  for outcome in(0,1):
   for status in(1,2):
    for destination in(4,11):
     for value in(1,65535):
      for supply in(0,65535):
       m,r=fixture(rom,0xC027,outcome=outcome,escaped=5,status=status,destination=destination,value=value,supply=supply);compare(m,r,f'destination-alias/o{outcome}/s{status}/d{destination}/v{value}/a{supply}')
  for outcome in range(256):
   m,r=fixture(rom,0xC027,outcome=outcome,supply=65535);compare(m,r,f'raw-outcome-byte/{outcome}',domain='explicit_raw8_outcome_CPU_domain_not_UI_eligibility')
  for city in(30,255):
   for destination in(0,29,255):
    for outcome in(2,127,128,255):
     for escaped,status in((255,0),(254,1),(254,3)):
      m,r=fixture(rom,0xC027,city=city,destination=destination,outcome=outcome,escaped=escaped,status=status);compare(m,r,f'raw-domain/c{city}/d{destination}/o{outcome}/e{escaped}/s{status}',domain='explicit_raw_selector_CPU_domain_not_legal_city_or_officer')
  for entry in PostbattleParentServices.NEW_ENTRIES:
   for sp in(0,1,2,127,252,253,254,255):
    for bits in range(16):
     flags=32|(bits&3)|((bits&4)<<4)|((bits&8)<<4);m,r=fixture(rom,entry,sp=sp,p=flags);compare(m,r,f'flags-stack/{entry:04X}/SP{sp}/P{flags}')
  for entry in(0xA006,0xBB93):
   for fade_timer in(0,4,127,255):
    m,r=fixture(rom,entry);m[0x8A]=fade_timer;compare(m,r,f'fade-does-not-wait/{entry:04X}/8A{fade_timer}')
  for entry in(0xA006,0xBB93):
   m,r=fixture(rom,entry);compare(m,r,f'same-generator-resume/{entry:04X}',services=False,pause_then_resume=True)
  for path in sorted((ROOT/'analysis/phase28/cpu-parent/actual-callers').glob('entry-*/context.json')):
   x=json.loads(path.read_text());folder=path.parent
   if x['registers']['pc']not in PostbattleParentServices.NEW_ENTRIES:continue
   assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and x['additional_CPU_prepared_numeric_bytes']==[]and x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']))
   m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
   compare(m,x['registers'],f'passive/{folder.name}',domain=x['origin'],provenance=x);passive_count+=1
   for p in folder.iterdir():input_pins[str(p.relative_to(ROOT))]=sha(p)
 m,r=fixture(rom)
 for name,fn in(('actual_registers_required',lambda:PostbattleParentServices(m,rom).run_entry()),('seed_return_rejected',lambda:PostbattleParentServices(m,rom).run_entry(registers=SetupRegisters(**r),seed_return=True)),('wrong_PC_rejected',lambda:PostbattleParentServices(m,rom).run_entry(0xC027,registers=SetupRegisters(**r))),('wrong_pair_rejected',lambda:PostbattleParentServices(_wrong_pair(m),rom).run_entry(registers=SetupRegisters(**r))),('decimal_rejected',lambda:PostbattleParentServices(m,rom).run_entry(registers=SetupRegisters(**dict(r,p=40)))),('wrong_return_rejected',lambda:PostbattleParentServices(m,rom).run_entry(registers=SetupRegisters(**r),return_pc=0x200))):
  try:fn();raise AssertionError('Guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 for stage in(4,255):
  m,r=fixture(rom,stage=stage);before=bytes(m.ram),bytes(m.sram),registers(SetupRegisters(**r));owner=PostbattleParentServices(m,rom)
  try:owner.run_entry(registers=SetupRegisters(**r));raise AssertionError('Bad dispatch not rejected')
  except ValueError:assert before[:2]==(bytes(m.ram),bytes(m.sram));guards.append(dict(name=f'out_of_table_stage{stage}_rejected_without_mutation',status='passed'))
 m,r=fixture(rom);owner=PostbattleParentServices(m,rom);reply=owner.run_entry(registers=SetupRegisters(**r));pending=owner.pending;before=bytes(m.ram),bytes(m.sram),registers(owner.registers)
 owner.services=lambda call:dict(status='returned');assert owner.resume()['status']=='dependency'and owner.pending is pending and before==(bytes(m.ram),bytes(m.sram),registers(owner.registers));guards.append(dict(name='returned_string_without_PC_SP_never_completes_ECEE',status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__)
 result=dict(schema='phase28-postbattle-stage2-exact-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),controlled_cases=len(rows)-passive_count,passive_software_caller_cases=passive_count,counts=dict(Counter(r['comparison']for r in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256=input_pins,executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],limits=['ECEE is immediate fade initiation plus32B palette backup, not a synchronous wait.87 completion is observed later in separate stage3 invocations.','Only stage2 is implemented. Other original dispatch states preserve real target/frame as strict dependency; out-of-table indexes are Source guards, not executed original rawcode.','Full2048RAM including stack,8192SRAM,AXYP-SP-PC,combined logicalIO,4PRG and common declaredN163 are compared. No IRQ/NMI/ack/ready is injected.','SP test values are a declared subset; no theorem covers arbitrary stack overlap with palette backup or control data.','Existing finalization_phase/return_campaign_supplies gameplay and Shared ECEE were already recovered. New source adds exact parent/supply caller protocol.','C027 raw outcome/city/officer domains are mechanical fixtures, not UI eligibility or natural-gameplay claims.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
