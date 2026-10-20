#!/usr/bin/env python3
"""Exact postbattle stage3, full software state and declared device comparison."""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle_completion_services import PostbattleCompletionServices
from source.recovered.postbattle_parent_integration import PostbattleParentGameEngine
from source.recovered.battle_setup_ai import SetupRegisters,ROM_SHA256
from source.recovered.battle_nmi_services import ServiceWait
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_postbattle_parent_services import fixture as parent_fixture
from verify_deployment_pointer_phase26 import OrderedComparisonMemory,registers
OUT=ROOT/'analysis/phase29/completion-services'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clone(m):
 b=OrderedComparisonMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={k:list(v)for k,v in m.read_ports.items()},repeat_read_ports=tuple(m.repeat_read_ports),controller_buttons=m.controller_buttons)
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement;b.controller_index=list(m.controller_index);b.controller_strobe=m.controller_strobe
 b.port_image=dict(m.port_image);b.ppu_register_bytes[:]=m.ppu_register_bytes;b.ppu_address=m.ppu_address;b.ppu_increment=m.ppu_increment;b.ppu_latch=m.ppu_latch;b.ppu_scroll=list(m.ppu_scroll);b.ppu_scroll_latch=m.ppu_scroll_latch
 return b
class ObservedCompletion(PostbattleCompletionServices):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.stores=[]
 def _write_pointed(self,zp,index,value):
  m=self.memory;p=m[zp]|m[(zp+1)&255]<<8;self.stores.append(dict(pc=self.registers.pc,zp=zp,pointer_before=p,Y=index,address=(p+index)&65535,value=value&255));super()._write_pointed(zp,index,value)
def _wrong_pair(memory):
 m=clone(memory);m.banks[1:3]=[12,13];return m
def fixture(rom,entry=0xA006,*,stage=3,fade=255,outcome=0,city=4,owner=1,ruler=2,slot=4,sp=253,p=32):
 m,r=parent_fixture(rom,entry=0xA006,stage=stage,outcome=outcome,city=city,sp=sp,p=p);r['pc']=entry;m[0x87]=fade;m[0x507]=(ruler<<4)|1
 for who in range(7):m[0x6F07+8*who]=10+who
 for n in range(30):
  a=0x6000+32*n;m[a]=0xA0|(n%7);m[a+17:a+27]=bytes([30+i for i in range(10)]);m[a+17+slot]=10+n%7
 a=0x6000+32*city;m[a]=0xA0|owner;m[a+17+slot]=10+(ruler if outcome==0 and entry!=0xBC00 else owner)%7
 m[0]=a&255;m[1]=a>>8
 ret={0xA006:0xEE4D,0xBAB3:0xEE4D,0xBB93:0xEE4D,0xBBA0:0xEE4D,0xBBB8:0xBBA8,0xBC00:0xBBE2}[entry]
 m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8;m.io_reads.clear();m.io_writes.clear();m.combined_IO.clear();return m,r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();inputs={};passive=0
 def compare(m,initial,tag,*,services=True,resume_hardware=None,resume_ECEE=False,domain='controlled_original_software_caller_fixture',provenance=None):
  left,right=clone(m),clone(m);c=MPU(memory=left)
  for k,v in initial.items():setattr(c,k,v)
  r=SetupRegisters(**initial);co=PostbattleParentGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None;owner=ObservedCompletion(right,rom,co if services else None)
  try:
   result=owner.run_entry(initial['pc'],registers=r);stages=[];original_stores=[]
   def step():
    assert c.pc>=0x8000,(tag,hex(c.pc));bank=left.banks[(c.pc-0x8000)//8192];visited[bank,c.pc]+=1
    if bank==8 and c.pc in(0xBBDD,0xBC3C,0xBC43):
     z=0 if c.pc==0xBBDD else 10;p=left[z]|left[(z+1)&255]<<8;original_stores.append(dict(pc=c.pc,zp=z,pointer_before=p,Y=c.y,address=(p+c.y)&65535,value=c.a))
    c.step()
   prefix=0
   if resume_ECEE:
    assert owner._drive.__func__ is PostbattleCompletionServices._drive
    assert result['status']=='dependency'and owner.pending.target==0xECEE
    pending,program=owner.pending,owner._program
    for prefix in range(100):
     if registers(c)==registers(r):break
     step()
    else:raise AssertionError('No original ECEE caller prefix match')
    assert left.ram==right.ram and left.sram==right.sram and left.combined_IO==right.combined_IO and left.banks==right.banks
    before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement,list(owner.events))
    attempted=[]
    def false_completion(call):
     assert call is pending;attempted.append(call.target);return dict(status='returned')
    owner.services=false_completion
    assert owner.resume()['status']=='dependency'and owner.pending is pending and owner._program is program
    assert attempted==[0xECEE]and before==(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement,list(owner.events))
    stages.append(dict(kind='same_generator_ECEE_missing_service_false_completion_then_real_Shared',original_prefix_instructions=prefix,actual_prefix_registers=registers(r),same_pending_ServiceCall=True,same_program_generator=True,false_returned_without_PC_SP_did_not_advance=True,no_repeated_previously_executed_state_or_IO=True,Source_driver='PostbattleCompletionServices._drive',fake_completion_attempts=1,real_service_environment='Frozen PostbattleParentGameEngine fixed Shared services, no originalCPU callback',not_a_cross_frame_palette_completion_wait=True))
    owner.services=co;result=owner.resume()
   if resume_hardware is not None:
    assert result['status']=='dependency'and isinstance(owner.pending,ServiceWait);w=owner.pending
    for prefix in range(100):
     if registers(c)==registers(r):break
     step()
    else:raise AssertionError('No original hardware prefix match')
    assert left.ram==right.ram and left.sram==right.sram and left.combined_IO==right.combined_IO and left.banks==right.banks
    before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO));assert owner.resume()['status']=='dependency';assert before==(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO))
    stages.append(dict(kind='same_generator_explicit_missing_hardware_read',pc=w.pc,address=w.address,SP=w.expected_sp))
    for address,value in resume_hardware.items():left.read_ports[address]=deque([value]);right.read_ports[address]=deque([value])
    result=owner.resume()
   for n in range(300000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    step()
   else:raise RuntimeError(('CPU budget',c.pc,r.pc))
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM/SRAM',rd[:10],sd[:10]);assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r));assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.combined_IO==right.combined_IO and left.banks==right.banks,(tag,'combinedIO/banks');assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163');assert original_stores==owner.stores,(tag,'ordered pointed stores',original_stores,owner.stores)
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison='actual_caller_RTS'if result['status']=='returned'else'nonlocal_return'if result['status']=='nonlocal_return'else'strict_dependency_prefix',original_CPU_instructions=n+prefix,all2048_RAM_8192_SRAM_AXYP_SP_PC_combined_IO_four_banks_shared_N163_equal=True,source_original_CPU_callbacks=0,ordered_pointed_stores=original_stores,sequence_checkpoints=stages,new_regression_group='inherited_stage2_ECEE_protocol_in_completion_driver'if resume_ECEE else None,provenance=provenance,events=result['events'],changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y]))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 for entry in PostbattleCompletionServices.NEW_ENTRIES:
  for outcome in(0,1):
   for fade in(0,255):
    m,r=fixture(rom,entry,outcome=outcome,fade=fade);compare(m,r,f'smoke/{entry:04X}/o{outcome}/fade{fade}')
 for stage in(0,1):
  m,r=fixture(rom,stage=stage);compare(m,r,f'unimplemented-stage/{stage}')
 # One exact invalid-ruler hardware boundary, not a declared legal owner.
 m,r=fixture(rom,0xBC00,owner=8);compare(m,r,'rawowner8/missing5F20',domain='explicit_rawowner_hardware_boundary_not_legal_ruler')
 m,r=fixture(rom,0xBC00,owner=8);compare(m,r,'rawowner8/samegenerator5F20',resume_hardware={0x5F20:14},domain='explicit_rawowner_and_device_input_fixture_not_Native')
 if not a.quick:
  for entry in(0xA006,0xBAB3,0xBBA0):
   for outcome in(0,1):
    for fade in range(256):
     m,r=fixture(rom,entry,outcome=outcome,fade=fade);compare(m,r,f'fade-byte/{entry:04X}/o{outcome}/v{fade}')
  for owner in range(7):
   for slot in(-1,0,1,9):
    for hole in(0,1):
     for duplicate in(0,1):
      for high in(0,240):
       m,r=fixture(rom,0xBC00,owner=owner);p=0x6080;m[p]=high|owner;m[p+17:p+27]=bytes(range(30,40))
       if hole:m[p+17]=255
       if slot>=0:m[p+17+slot]=10+owner
       if duplicate and 0<=slot<9:m[p+26]=10+owner
       compare(m,r,f'roster/o{owner}/slot{slot}/hole{hole}/duplicate{duplicate}/high{high}')
  for owner in(0,6):
   for slot in range(10):
    m,r=fixture(rom,0xBC00,owner=owner,slot=slot);compare(m,r,f'all-ten-slots/o{owner}/slot{slot}')
  for owner in(0,6):
   for leader in(0,1,127,128,236,237,254,255):
    m,r=fixture(rom,0xBC00,owner=owner);m[0x6F07+8*owner]=leader;m[0x6080+17:0x6080+27]=bytes([30,255,31,32,33,34,35,36,37,leader]);compare(m,r,f'raw-leader-byte/o{owner}/leader{leader}',domain='complete_BC00_with_raw_leader_byte_no_health_status_filter')
  for city in range(30):
   for outcome in(0,1):
    for ruler in(0,6):
     owner=7 if city%2 else 1;m,r=fixture(rom,0xBBB8,city=city,outcome=outcome,ruler=ruler,owner=owner);compare(m,r,f'all-cities/c{city}/o{outcome}/ruler{ruler}/owner{owner}')
  for owner in range(8,16):
   m,r=fixture(rom,0xBC00,owner=owner)
   if owner==8:m.read_ports[0x5F20]=deque([14]);m.repeat_read_ports.add(0x5F20)
   compare(m,r,f'raw-low-nibble-owner/{owner}',domain='explicit_raw_owner8_15_machine_table_not_legal_ruler')
  for whole in(7,23,119,135,247):
   m,r=fixture(rom,0xBC00,owner=7);m[0x6080]=whole;compare(m,r,f'neutral-low-nibble/{whole}')
  for city in range(30,256):
   m,r=fixture(rom,0xBBB8,city=city,outcome=1,owner=1);compare(m,r,f'raw-city-byte/{city}',domain='explicit_raw_city_30_255_not_UI_eligibility')
  # Bare BC00 inputs deliberately break the complete F2AF city-base type.
  for pointer in(0x6001,0x600B):
   m,r=fixture(rom,0xBC00);m[0]=pointer&255;m[1]=pointer>>8;m[pointer]=0;m[pointer+17:pointer+27]=bytes(range(30,40));m[pointer+18]=10
   compare(m,r,f'bare-helper-cityaux/{pointer:04X}',domain='controlled_bare_suffix_auxiliary_alias_not_complete_parent')
  m,r=fixture(rom,0xBC00);m[0]=249;m[1]=255;m[0x6F07]=255
  compare(m,r,'bare-helper-live-pointer/FFF9',domain='controlled_bare_wrap_alias_firststore_changes_pointer_for_secondstore')
  for entry in PostbattleCompletionServices.NEW_ENTRIES:
   for sp in(0,1,2,127,252,253,254,255):
    for bits in range(16):
     flags=32|(bits&3)|((bits&4)<<4)|((bits&8)<<4);m,r=fixture(rom,entry,sp=sp,p=flags);compare(m,r,f'flags-stack/{entry:04X}/SP{sp}/P{flags}')
  for entry in(0xA006,0xBBB8,0xBC00):
   m,r=fixture(rom,entry);compare(m,r,f'missing-services/{entry:04X}',services=False)
  for entry in(0xA006,0xBB93):
   m,r=fixture(rom,entry,stage=2);compare(m,r,f'new-driver-stage2-ECEE-resume/{entry:04X}',services=False,resume_ECEE=True,domain='controlled_same_generator_service_availability_regression_not_Native')
  for path in sorted((ROOT/'analysis/phase29/cpu-completion/actual-callers').glob('entry-*/context.json')):
   x=json.loads(path.read_text());folder=path.parent
   if x['registers']['pc']not in PostbattleCompletionServices.NEW_ENTRIES:continue
   assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and x['additional_CPU_prepared_numeric_bytes']==[]and x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']))
   m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
   compare(m,x['registers'],f'passive/{folder.name}',domain=x['origin'],provenance=x);passive+=1
   for p in folder.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
 m,r=fixture(rom)
 for name,fn in(('actual_registers_required',lambda:PostbattleCompletionServices(m,rom).run_entry()),('seed_return_rejected',lambda:PostbattleCompletionServices(m,rom).run_entry(registers=SetupRegisters(**r),seed_return=True)),('wrong_PC_rejected',lambda:PostbattleCompletionServices(m,rom).run_entry(0xBC00,registers=SetupRegisters(**r))),('wrong_pair_rejected',lambda:PostbattleCompletionServices(_wrong_pair(m),rom).run_entry(registers=SetupRegisters(**r))),('decimal_rejected',lambda:PostbattleCompletionServices(m,rom).run_entry(registers=SetupRegisters(**dict(r,p=40)))),('wrong_return_rejected',lambda:PostbattleCompletionServices(m,rom).run_entry(registers=SetupRegisters(**r),return_pc=0x200))):
  try:fn();raise AssertionError('Guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 for stage in(4,255):
  m,r=fixture(rom,stage=stage);before=bytes(m.ram),bytes(m.sram)
  try:PostbattleCompletionServices(m,rom).run_entry(registers=SetupRegisters(**r));raise AssertionError('Bad dispatch not rejected')
  except ValueError:assert before==(bytes(m.ram),bytes(m.sram));guards.append(dict(name=f'bad-stage{stage}_rejected_without_mutation',status='passed'))
 m,r=fixture(rom,0xBC00,owner=8);co=PostbattleParentGameEngine(m,rom=rom,mapped=True).readable_scene_rules();owner=PostbattleCompletionServices(m,rom,co);assert owner.run_entry(0xBC00,registers=SetupRegisters(**r))['status']=='dependency';wait=owner.pending;before=bytes(m.ram),bytes(m.sram),list(m.combined_IO);owner.registers.pc+=1
 assert owner.resume()['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),list(m.combined_IO));owner.registers.pc=wait.pc;owner.registers.sp=(wait.expected_sp+1)&255
 assert owner.resume()['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),list(m.combined_IO));guards.append(dict(name='missing_IO_resume_requires_same_PC_SP_and_never_mutates_ack',status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__)
 result=dict(schema='phase29-postbattle-stage3-exact-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),controlled_cases=len(rows)-passive,passive_software_caller_cases=passive,new_regression_groups={'inherited_stage2_ECEE_protocol_in_completion_driver':sum(r['new_regression_group']is not None for r in rows)},counts=dict(Counter(r['comparison']for r in rows)),source_guard_count=len(guards),guards=guards,cases=rows,failures=failures,failed_count=len(failures),source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256=inputs,executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],limits=['Existing promote_city_leader/finalize_city_ownership gameplay is not first recovered here. New evidence covers exact protocol.','Stage3 nonnegative87 returns on each callback; no suspended fade or forged acknowledgement. Stages0/1 remain true dispatch dependencies.','Complete2048RAM including stack,8192SRAM,AXYP-SP-PC,4PRG,mixed logicalIO and explicit sharedN163 are compared. No IRQ/NMI is injected.','Two new controlled parent sequences execute inherited stage2 through the NEW Completion driver: real ECEE prefix, false returned response without PC/SP rejected with no repeated effects, then same generator and genuine Shared complete. They are complete parentCPU cases, not additional Native inputs or standalone Source guards.','Rawowner8..15 are mechanical16-table selectors, not legal rulers; owner8 missing5F20 is a genuine explicit hardware-input boundary.','BareBC00 pointer aliases and rawcities are controlled machine domains, not parent pointer construction or Native eligibility.','No instantN163 is claimed for passive software captures; ancestor preparation stays explicit.'])
 (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','counts','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
