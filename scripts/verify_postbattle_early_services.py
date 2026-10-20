#!/usr/bin/env python3
"""Phase30 early postbattle owner: originalCPU versus independent Source."""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle_early_services import PostbattleEarlyServices
from source.recovered.postbattle_completion_integration import PostbattleCompletionGameEngine
from source.recovered.battle_setup_ai import SetupRegisters,ROM_SHA256
from source.recovered.battle_nmi_services import ServiceWait
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_postbattle_completion_services import fixture as completion_fixture,clone
from verify_deployment_pointer_phase26 import registers
OUT=ROOT/'analysis/phase30/early-services'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fixture(rom,entry=0xA006,*,stage=0,outcome=0,controller=3,mode=0,side=128,current=4,source=11,occupancy=0,units=2,captives=1,sp=253,p=32):
 m,r=completion_fixture(rom,stage=stage,outcome=outcome,sp=sp,p=p);r['pc']=entry
 for who in range(7):m[0x6F07+8*who]=20+who;m[0x6F0A+8*who]=controller
 m[0x507]=0x21;m[0x514]=outcome;m[0x504]=side;m[0x50E]=current;m[0x52A]=source;m[0x52B]=255;m[0x6F91]=mode
 for city in range(30):
  a=0x6000+32*city;m[a]=7;m[a+17:a+27]=bytes([255]*10)
  for n in range(occupancy):m[a+17+n]=(80+city+n)&255
 for slot in range(20):m[0x628+slot]=255;m[0x664+slot]=255
 for n in range(units):
  m[0x628+n]=0;m[0x664+n]=30+n;m[0x628+10+n]=128;m[0x664+10+n]=20+n
 m[0x6F47:0x6F6F]=bytes([255]*40)
 for n in range(captives):m[0x6F47+n]=50+n;m[0x6F5B+n]=60+n
 m[0x6FA1:0x6FA1+256]=bytes([255]*256)
 # Bare helper fixtures explicitly provide their normal caller scratch.
 m[2]=current;m[3]=17+min(occupancy,9);m[4]=0
 if entry in(0xBD96,0xBE55):m[0x6FA1:0x6FA5]=bytes([31,30,20,255])
 ret={0xA006:0xEE4D,0xBAB3:0xEE4D,0xBAC1:0xEE4D,0xBB3D:0xEE4D,0xBC46:0xBB39,0xBC52:0xBB39,0xBD59:0xBB8F,0xBD67:0xBB39,0xBD96:0xBC68,0xBDCD:0xBC55,0xBE55:0xBD5F,0xBE90:0xBC70,0xBB93:0xEE4D,0xBBA0:0xEE4D,0xBC00:0xBBE2}[entry]
 m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8;m.io_reads.clear();m.io_writes.clear();m.combined_IO.clear();return m,r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();input_pins={};passive=0
 def compare(m,initial,tag,*,services=True,resume_ECEE=False,resume_hardware=None,domain='controlled_original_software_caller_fixture',provenance=None):
  left,right=clone(m),clone(m);c=MPU(memory=left)
  for k,v in initial.items():setattr(c,k,v)
  r=SetupRegisters(**initial);co=PostbattleCompletionGameEngine(right,rom=rom,mapped=True).readable_scene_rules();assert co.external_callback is None;owner=PostbattleEarlyServices(right,rom,co if services else None)
  prefix=0;stages=[];early_boundaries=[];previous_CPU_PC=None
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   def step():
    nonlocal previous_CPU_PC
    if c.pc in(0xBB36,0xBB39,0xBB8C,0xBB8F,0xBC46):
     word=left[0x100+((c.sp+1)&255)]|left[0x100+((c.sp+2)&255)]<<8
     early_boundaries.append(dict(actual_original_CPU_registers=registers(c),actual_PRG_banks=list(left.banks),raw_stack_top4=[left[0x100+((c.sp+n)&255)]for n in(1,2,3,4)],raw_return_word=word,immediate_previous_original_CPU_PC=previous_CPU_PC,observed_JSR_transfer=previous_CPU_PC if c.pc==0xBC46 and previous_CPU_PC in(0xBB36,0xBB8C)else None))
     if c.pc==0xBC46 and previous_CPU_PC in(0xBB36,0xBB8C):assert word==previous_CPU_PC+2
    previous_CPU_PC=c.pc
    assert c.pc>=0x8000,(tag,hex(c.pc));visited[left.banks[(c.pc-0x8000)//8192],c.pc]+=1;c.step()
   if resume_ECEE:
    assert owner._drive.__func__ is PostbattleEarlyServices._drive and owner.postbattle_stage_dispatch.__func__ is PostbattleEarlyServices.postbattle_stage_dispatch
    assert result['status']=='dependency'and owner.pending.target==0xECEE;pending,program=owner.pending,owner._program
    for prefix in range(100):
     if registers(c)==registers(r):break
     step()
    else:raise AssertionError('No ECEE original prefix match')
    assert left.ram==right.ram and left.sram==right.sram and left.banks==right.banks and left.combined_IO==right.combined_IO
    before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement,list(owner.events));calls=[]
    def false_completion(call):assert call is pending;calls.append(call.target);return dict(status='returned')
    owner.services=false_completion;assert owner.resume()['status']=='dependency'and owner.pending is pending and owner._program is program
    assert calls==[0xECEE]and before==(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement,list(owner.events))
    stages.append(dict(kind='NEW30_owner_inherited_stage2_missing_ECEE_false_return_same_generator_real_Shared',original_prefix_instructions=prefix,same_pending_ServiceCall=True,same_program_generator=True,false_return_without_PC_SP_rejected=True,no_repeated_state_or_IO=True));owner.services=co;result=owner.resume()
   if resume_hardware is not None:
    assert result['status']=='dependency'and isinstance(owner.pending,ServiceWait);w=owner.pending
    for prefix in range(100):
     if registers(c)==registers(r):break
     step()
    else:raise AssertionError('No original hardware prefix match')
    assert left.ram==right.ram and left.sram==right.sram and left.combined_IO==right.combined_IO and left.banks==right.banks
    program=owner._program;before=bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO)
    assert owner.resume()['status']=='dependency'and owner._program is program and before==(bytes(right.ram),bytes(right.sram),registers(r),list(right.combined_IO))
    for address,value in resume_hardware.items():left.read_ports[address]=deque([value]);right.read_ports[address]=deque([value])
    stages.append(dict(kind='NEW30_owner_same_generator_explicit_device_input',PC=w.pc,address=w.address,SP=w.expected_sp));result=owner.resume()
   for n in range(400000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    step()
   else:raise RuntimeError(('CPU budget',c.pc,r.pc))
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM/SRAM',rd[:10],sd[:10]);assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r));assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.combined_IO==right.combined_IO and left.banks==right.banks,(tag,'combinedIO/banks');assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   rows.append(dict(case=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=registers(r),source_status=result['status'],comparison='actual_caller_RTS'if result['status']=='returned'else'nonlocal_return'if result['status']=='nonlocal_return'else'strict_dependency_prefix',original_CPU_instructions=n+prefix,all2048_RAM_8192_SRAM_AXYP_SP_PC_combined_IO_four_banks_shared_N163_equal=True,source_original_CPU_callbacks=0,sequence_checkpoints=stages,original_early_call_boundaries=early_boundaries,events=result['events'],provenance=provenance,changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(m.sram,right.sram))if x!=y]))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 for stage in(0,1):
  for controller in(0,1,3):
   for outcome in(0,1):
    for entry in(0xA006,0xBAC1 if stage==0 else 0xBB3D):
     m,r=fixture(rom,entry,stage=stage,controller=controller,outcome=outcome);compare(m,r,f'smoke/stage{stage}/{entry:04X}/controller{controller}/outcome{outcome}')
 for mode in range(3):
  for side in(0,128):
   m,r=fixture(rom,0xBC46,mode=mode,side=side);compare(m,r,f'mode/{mode}/side{side}')
 for entry in PostbattleEarlyServices.ALLOCATION_HELPERS:
  m,r=fixture(rom,entry);compare(m,r,f'helper/{entry:04X}')
 for entry in(0xA006,0xBB93):
  m,r=fixture(rom,entry,stage=2);compare(m,r,f'NEW30-driver-stage2-ECEE-resume/{entry:04X}',services=False,resume_ECEE=True)
 for fade in(0,127,128,255):
  m,r=fixture(rom,stage=3);m[0x87]=fade;compare(m,r,f'NEW30-stage3-fresh-callback/fade{fade}')
 for supplied in(False,True):
  m,r=fixture(rom,0xBC00,stage=3);m[0]=128;m[1]=96;m[0x6080]=8;compare(m,r,f'NEW30-stage3-rawowner8-device/supply{supplied}',resume_hardware={0x5F20:14}if supplied else None)
 if not a.quick:
  # Exact controller byte and raw outcome domains stay separate from eligibility.
  for stage in(0,1):
   for controller in range(256):
    m,r=fixture(rom,stage=stage,controller=controller,outcome=stage);compare(m,r,f'controller-byte/stage{stage}/{controller}')
  for stage in(0,1):
   for outcome in(0,1,2,127,128,255):
    for controller in(0,3):
     m,r=fixture(rom,stage=stage,controller=controller,outcome=outcome);compare(m,r,f'outcome-byte/stage{stage}/c{controller}/{outcome}')
  for entry in(0xBAC1,0xBB3D):
   for outcome in(0,1):
    m,r=fixture(rom,entry,stage=255,controller=3,outcome=outcome);compare(m,r,f'bare-early/INC0501-wrap/{entry:04X}/outcome{outcome}',domain='controlled_direct_suffix_phase255_not_full_dispatch_eligibility')
  for mode in range(3):
   for side in(0,1,127,128,129,255):
    for occupancy in(0,1,9,10):
     for count in(0,1,10):
      m,r=fixture(rom,0xBC46,mode=mode,side=side,occupancy=occupancy,units=count,captives=0);compare(m,r,f'allocation/m{mode}/side{side}/occupancy{occupancy}/units{count}')
  # Discriminating helper cases, each with a declared original caller frame.
  for side in(0,128):
   m,r=fixture(rom,0xBDCD,side=side,units=10,captives=20)
   for slot in range(20):m[0x628+slot]=side;m[0x664+slot]=slot
   compare(m,r,f'collect/max40-do-while/side{side}',domain='controlled_maximum_list_size_not_proven_Native_reachable')
   m,r=fixture(rom,0xBDCD,side=side);slot=10 if side else 0;m[0x664+slot]=255
   compare(m,r,f'collect/active-officerFF-kept/side{side}')
   m,r=fixture(rom,0xBE55,side=side);leader=m[0x664+(10 if side else 0)];m[0x6FA1:0x6FA1+20]=bytes([255]*20);m[0x6FA1+19]=leader
   compare(m,r,f'prioritize/FF-holes-match19/side{side}')
  m,r=fixture(rom,0xBE55,side=0);m[0x6FA1:0x6FA1+20]=bytes([31,32,33]+[255]*17)
  compare(m,r,'prioritize/no-commander-in-all20')
  m,r=fixture(rom,0xBC46,mode=1,side=0,occupancy=0,units=10,captives=1)
  compare(m,r,'empty-neighbor/full-first10-then-remaining1-restores-cursor')
  m,r=fixture(rom,0xBC46,mode=2,occupancy=10,units=0,captives=0);m[0x6FA1+0xBD]=88;m[0x6FA1+0xBE]=255
  compare(m,r,'mode2/full-source-retains-BD-cursor-live-read')
  m,r=fixture(rom,0xBC46,mode=1,side=0,occupancy=10,units=0,captives=3);m[0x6F47:0x6F4A]=bytes([99,21,32]);m[0x6F0F]=99
  compare(m,r,'overflow/special-leader-then-release-then-row32-compare')
  rng=rom[16+31*8192+(0xE8BA&8191):16+31*8192+(0xE8BA&8191)+256]
  # E87A's original table beginsE8BA; choose each low3 destination and wrap255.
  for cursor in sorted({255}|{next(i for i,b in enumerate(rng)if b&7==n)for n in range(8)}):
   m,r=fixture(rom,0xBC46,mode=1,side=0,occupancy=10,units=0,captives=1);m[0x50]=cursor
   compare(m,r,f'overflow/RNG-cursor{cursor}',domain='controlled_initial_RNG_cursor_byte_not_Native_preparation')
  for offset in(0,17,26,27,254,255):
   m,r=fixture(rom,0xBD96);m[3]=offset;m[0x52B]=31
   compare(m,r,f'bare-fill/raw-offset{offset}/escape-first',domain='controlled_raw_roster_offset_not_normal_UI_capacity')
  for cursor in(20,189,254,255):
   m,r=fixture(rom,0xBD96);m[4]=cursor;m[0x6FA1+cursor]=88;m[0x6FA1+((cursor+1)&255)]=255
   compare(m,r,f'bare-fill/byte-cursor{cursor}',domain='controlled_raw_cursor_not_normal_roster_capacity')
  for city in range(30):
   m,r=fixture(rom,0xBE90,current=city,occupancy=city%11);compare(m,r,f'neighbor-table/realcity{city}/occupancy{city%11}')
  for supplied in(False,True):
   m,r=fixture(rom,0xBAC1);m[0x507]=0x81
   compare(m,r,f'raw-ruler8/controller-device/supply{supplied}',resume_hardware={0x5F23:0}if supplied else None,domain='explicit_raw_ruler8_hardware_boundary_not_legal_ruler')
  for entry in PostbattleEarlyServices.NEW_ENTRIES:
   for sp in(0,1,2,127,252,253,254,255):
    for bits in range(16):
     flags=32|(bits&3)|((bits&4)<<4)|((bits&8)<<4);m,r=fixture(rom,entry,sp=sp,p=flags);compare(m,r,f'flags-stack/{entry:04X}/SP{sp}/P{flags}')
  for entry in(0xA006,0xBAC1,0xBB3D,0xBC46):
   m,r=fixture(rom,entry);compare(m,r,f'missing-fixed-services/{entry:04X}',services=False)
  for phase in(29,30):
   folder=ROOT/f'analysis/phase{phase}'/('cpu-completion'if phase==29 else'cpu-early')/'actual-callers'
   for path in sorted(folder.glob('entry-*/context.json')):
    x=json.loads(path.read_text());d=path.parent
    if x['registers']['pc']not in PostbattleEarlyServices.PUBLIC_ENTRIES:continue
    assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and x['additional_CPU_prepared_numeric_bytes']==[]and x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
    m=CapturedServiceMemory(rom,(d/'input-ram.bin').read_bytes(),(d/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']));m.n163_ram[:]=(d/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
    compare(m,x['registers'],f'passive-p{phase}/{d.name}',domain=x['origin'],provenance=x);passive+=1
    for p in d.iterdir():input_pins[str(p.relative_to(ROOT))]=sha(p)
 m,r=fixture(rom)
 for name,fn in(('actual_registers_required',lambda:PostbattleEarlyServices(m,rom).run_entry()),('seed_return_rejected',lambda:PostbattleEarlyServices(m,rom).run_entry(registers=SetupRegisters(**r),seed_return=True)),('wrong_PC_rejected',lambda:PostbattleEarlyServices(m,rom).run_entry(0xBC46,registers=SetupRegisters(**r))),('decimal_rejected',lambda:PostbattleEarlyServices(m,rom).run_entry(registers=SetupRegisters(**dict(r,p=40)))),('wrong_return_rejected',lambda:PostbattleEarlyServices(m,rom).run_entry(registers=SetupRegisters(**r),return_pc=0x200))):
  try:fn();raise AssertionError('Guard did not reject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 wrong=clone(m);wrong.banks[1:3]=[12,13]
 try:PostbattleEarlyServices(wrong,rom).run_entry(registers=SetupRegisters(**r));raise AssertionError('Bad pair accepted')
 except ValueError:guards.append(dict(name='wrong_code_pair_rejected',status='passed'))
 for stage in(4,255):
  m,r=fixture(rom,stage=stage);before=bytes(m.ram),bytes(m.sram)
  try:PostbattleEarlyServices(m,rom).run_entry(registers=SetupRegisters(**r));raise AssertionError('Bad stage accepted')
  except ValueError:assert before==(bytes(m.ram),bytes(m.sram));guards.append(dict(name=f'bad-stage{stage}_rejected',status='passed'))
 for mode in(3,255):
  m,r=fixture(rom,0xBC46,mode=mode);before=bytes(m.ram),bytes(m.sram)
  try:PostbattleEarlyServices(m,rom).run_entry(0xBC46,registers=SetupRegisters(**r));raise AssertionError('Bad mode accepted')
  except ValueError:assert before==(bytes(m.ram),bytes(m.sram));guards.append(dict(name=f'bad-mode{mode}_rejected',status='passed'))
 m,r=fixture(rom,0xBC00,stage=3);m[0]=128;m[1]=96;m[0x6080]=8;co=PostbattleCompletionGameEngine(m,rom=rom,mapped=True).readable_scene_rules();owner=PostbattleEarlyServices(m,rom,co);assert owner.run_entry(0xBC00,registers=SetupRegisters(**r))['status']=='dependency';wait=owner.pending;before=bytes(m.ram),bytes(m.sram),list(m.combined_IO);owner.registers.pc+=1
 assert owner.resume()['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),list(m.combined_IO));owner.registers.pc=wait.pc;owner.registers.sp=(wait.expected_sp+1)&255
 assert owner.resume()['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),list(m.combined_IO));guards.append(dict(name='NEW30_owner_device_wait_requires_same_PC_SP',status='passed'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__)
 v=dict(schema='phase30-postbattle-early-exact-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,original_CPU_parent_cases=len(rows),controlled_cases=len(rows)-passive,passive_software_caller_cases=passive,counts=dict(Counter(r['comparison']for r in rows)),source_guard_count=len(guards),guards=guards,nonlocal_return_count=sum(r['comparison']=='nonlocal_return'for r in rows),original_BB36_parent_call_cases=sum(any(x['observed_JSR_transfer']==0xBB36 for x in q['original_early_call_boundaries'])for q in rows),original_BB8C_parent_call_cases=sum(any(x['observed_JSR_transfer']==0xBB8C for x in q['original_early_call_boundaries'])for q in rows),cases=rows,failures=failures,failed_count=len(failures),source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256=input_pins,executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),execution_count=n)for(b,pc),n in sorted(visited.items())],limits=['Existing process_ai_officers gameplay is not first recovered; exact registers/stack/mapper/allocation protocol is new evidence.','No new IRQ/NMI/ready/ack is injected by Source; stage3 is a fresh invocation and ECEE returns immediately.','All2048RAM including stack/8192SRAM/AXYP-SP-PC/fourPRG/combined logicalIO/common declaredN163 are compared. py65 does not issue hardware dummy bus cycles.','Raw aliases/outcomes/counters and prepared CPU callers are not claims of Native eligibility.','Passive software captures preserve ancestry; instantaneousN163 is not captured and is a common declared fixture.'])
 (OUT/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v[k]for k in('status','original_CPU_parent_cases','counts','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
