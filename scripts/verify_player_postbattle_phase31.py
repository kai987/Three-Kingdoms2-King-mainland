#!/usr/bin/env python3
"""Phase31: revalidate frozen readable human postbattle control, no new owner.

OriginalCPU executes only the comparison side. All source callbacks use the
frozen phase30 GameEngine/SceneCoordinator and independent source services.
Controlled initial queue/cursor states are fixtures, never Native ready writes.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle_early_integration import PostbattleEarlyGameEngine
from source.recovered.postbattle_release_services import PostbattleReleaseController,BattleRegisters,ROM_SHA256
from source.recovered.battle_nmi_services import ServiceCall
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_postbattle_release_services import fixture as release_fixture,registers
from verify_postbattle_early_services import clone,fixture as early_fixture
OUT=ROOT/'analysis/phase31/player-disposition';CPU=ROOT/'analysis/phase31/cpu-disposition'
PHASES={13:(0xCD2A,0xCD52,0xCDF2,0xCE56,0xCE76,0xCE9E,0xCF09),14:(0xD2E1,0xD310,0xD34B,0xD3AF,0xD3D7,0xD3F7,0xD462)}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fixture(rom,state=13,phase=0,*,entry=0xA028,buttons=0,busy=False,count=3,selected=False,cursor_end=False,attacking_side=True):
 m,r=release_fixture(rom);r.update(pc=entry,sp=253,a=17,x=31,y=63,p=32);m[0x1FE:0x200]=bytes((255,1))
 m[0x500]=state;m[0x501]=phase;m[0x50B]=0x11 if attacking_side else 2;m[0x507]=0x21;m[0x50E]=4;m[0x504]=128 if attacking_side else 0;m[0x78]=3;m[0x7A]=4
 m[0x81]=buttons;m[0x83]=buttons;m[0x300]=0 if busy else 255;m[0x304]=0 if busy else 255;m[0x310]=255;m[0x7E]=0;m[0x7C]=0
 m[0x5E]=0;m[0x424]=0;m[0x425]=0;m[0x12]=0;m[0x508]=0;m[0x518]=255;m[0x4C8]=255
 m[0x87]=128;m[0x8E]=0;m[0x90]=0;m[0x8F]=0;m[0x91]=0;m[0x540]=30;m[0x541]=1;m[0x44C]=131 if attacking_side else 8
 for base in(0x600,0x614,0x628,0x63C,0x650,0x664):m[base:base+20]=bytes([255])*20
 ids=[131,5,30,130,29,126,26,11,10,9]if attacking_side else[8,191,51,167,77,9,7,109,153,222]
 for i in range(min(count,10)):
  slot=(10 if attacking_side else 0)+i;m[0x600+slot]=2+i;m[0x614+slot]=16;m[0x628+slot]=128 if attacking_side else 0;m[0x63C+slot]=7;m[0x650+slot]=0;m[0x664+slot]=ids[i]
 m[0x6F47:0x6F6F]=bytes([255]*40)
 for i in range(max(0,count-10)):m[(0x6F5B if attacking_side else 0x6F47)+i]=80+i
 m[0x6000+32*11+17:0x6000+32*11+27]=bytes([255]*10)
 m[0x42C:0x46C]=bytes([255]*64);m[0x550:0x560]=bytes([255]*16);m[0x580:0x5A1]=bytes([255]*33)
 if phase==2:
  m[0x50A]=1;m[0x42C:0x42F]=bytes((11,30,255));m[0x550:0x552]=bytes((0,0))
 else:
  roster=ids[:min(count,10)]+[80+i for i in range(max(0,count-10))]
  m[0x42C:0x42C+len(roster)]=bytes(roster);m[0x50A]=count
 if selected and count>1:m[0x581]=0
 if cursor_end and phase==5:
  # OriginalCF5E table is menu data, not an instruction or a synthesized choice.
  o=16+13*8192+(0xCF5E&8191)+2*count;ptr=int.from_bytes(rom[o:o+2],'little');o=16+13*8192+(ptr&8191);table=rom[o:o+64];i=table.index(count)
  m[0x424]=i%3;m[0x425]=i//3
 m.io_reads.clear();m.io_writes.clear();return m,r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 cases=[];failures=[];visited=Counter();inputs={};guards=[]
 def compare(memory,initial,tag,*,origin='controlled_initial_numeric_queue_and_caller_fixture_not_Native',source_services=True,metadata=None):
  left,right=clone(memory),clone(memory);c=MPU(memory=left);r=BattleRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  game=PostbattleEarlyGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();assert co.external_callback is None;assert isinstance(co.controller(3),PostbattleReleaseController)
  owner=co.controller(3);target=((right[0x100+((r.sp+1)&255)]|right[0x100+((r.sp+2)&255)]<<8)+1)&65535
  call=ServiceCall(initial['pc'],target,metadata.get('actual_call_kind','controlled_software_caller_fixture')if metadata else'controlled_software_caller_fixture',r,right,tuple(right.banks),(r.sp+2)&255)
  try:
   if source_services:result=co.tick(r,scene=3)if initial['pc']==0xA000 else co(call)
   else:owner.services=None;result=owner.run_entry(initial['pc'],registers=r)
   protocol=[]
   for n in range(1000000):
    if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
    assert c.pc>=0x8000,(tag,hex(c.pc));bank=left.banks[(c.pc-0x8000)//8192];visited[bank,c.pc]+=1
    if(bank,c.pc)in((13,0xCF2D),(13,0xD486),(13,0xD4F0),(13,0xD4F5),(8,0xA006),(8,0xBB36),(8,0xBB8C),(8,0xBC46),(8,0xBB39),(8,0xBB8F)):
     word=left[0x100+((c.sp+1)&255)]|left[0x100+((c.sp+2)&255)]<<8;protocol.append(dict(physical_bank=bank,registers=registers(c),physical_banks=list(left.banks),raw_return_word=word))
    c.step()
   else:raise RuntimeError(('originalCPU budget',c.pc,r.pc))
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
   assert not rd and not sd,(tag,'RAM/SRAM',rd[:10],sd[:10]);assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r));assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.combined_IO==right.combined_IO and left.banks==right.banks,(tag,'combinedIO/banks');assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
   assert (result['status']in('returned','nonlocal_return')if source_services else result['status']=='dependency'),(tag,'unexpected Source boundary',result['status'],str(result.get('pending')))
   pending=owner.pending if not source_services else None
   missing=dict(target=pending.target,return_pc=pending.return_pc,kind=pending.kind,expected_sp=pending.expected_sp)if pending is not None else None
   cases.append(dict(case=tag,origin=origin,entry=initial['pc'],initial_registers=initial,final_registers=registers(r),before_state_phase=[memory[0x500],memory[0x501]],after_state_phase=[right[0x500],right[0x501]],initial_buttons=memory[0x81],initial_queue_state=[memory[0x300],memory[0x304],memory[0x310]],final_queue_state=[right[0x300],right[0x304],right[0x310]],source_status=result['status'],comparison='actual_caller_RTS'if result['status']=='returned'else'actual_nonlocal_return'if result['status']=='nonlocal_return'else'strict_dependency_prefix',original_CPU_instructions=n,source_original_CPU_callbacks=0,all2048_RAM_8192_SRAM_AXYP_SP_PC_four_banks_combined_IO_common_N163_equal=True,source_calls=co.calls,pending_dependency=missing,original_local_caller_protocol=protocol,metadata=metadata,changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(memory.sram,right.sram))if x!=y]))
  except Exception as e:failures.append(dict(case=tag,error=str(e)));print(json.dumps(failures[-1]),flush=True)
 for state in(13,14):
  for phase in range(7):
   for buttons in(0,1,2,3):
    for busy in(False,True):
     m,r=fixture(rom,state,phase,buttons=buttons,busy=busy);compare(m,r,f'controlled/state{state}/phase{phase}/buttons{buttons}/busy{busy}')
 if not a.quick:
  for state in(13,14):
   for phase in range(7):
    m,r=fixture(rom,state,phase,entry=0xA000,buttons=1);compare(m,r,f'controlled-A000-wrapper/state{state}/phase{phase}')
    m,r=fixture(rom,state,phase,buttons=1,attacking_side=False);compare(m,r,f'controlled-defending-side/state{state}/phase{phase}')
  for state in(13,14):
   for phase in(0,5,6):
    for count in(0,1,10,11):
     m,r=fixture(rom,state,phase,count=count,buttons=1,selected=count>1,cursor_end=phase==5);compare(m,r,f'controlled-roster-size/state{state}/phase{phase}/count{count}')
  for state in(13,14):
   for button in(16,32,64,128,129):
    for phase in(2,5):
     m,r=fixture(rom,state,phase,buttons=button);compare(m,r,f'controlled-menu-direction/state{state}/phase{phase}/buttons{button}')
  for state in(13,14):
   for phase in(0,1,5,6):
    m,r=fixture(rom,state,phase);compare(m,r,f'declared-missing-services/state{state}/phase{phase}',source_services=False)
  # These original caller contracts are inherited regression evidence. They
  # remain separately labelled, and are not new Native observations in31.
  for outcome in(0,1):
   m,r=early_fixture(rom,stage=0,outcome=outcome,controller=3)
   compare(m,r,f'inherited30-controlled-BB36-parent/outcome{outcome}',origin='phase30_reused_controlled_AI_stage0_caller_fixture_not_Native')
  paths=[(path,'inherited30-passive')for path in sorted((ROOT/'analysis/phase30/cpu-early/actual-callers').glob('entry-*/context.json'))]
  paths += [(path,'passive31')for path in sorted((CPU/'actual-callers').glob('entry-*/context.json'))]
  for path,group in paths:
   x=json.loads(path.read_text());d=path.parent
   assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'and x['additional_CPU_prepared_numeric_bytes']==[]and x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   m=CapturedServiceMemory(rom,(d/'input-ram.bin').read_bytes(),(d/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']));m.n163_ram[:]=(d/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
   compare(m,x['registers'],group+'/'+d.name,origin=x['origin'],metadata=x)
   for p in d.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
 for stem in('analysis/runtime/phase3/attack-intro-7','analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame34623'):
  for suffix in('-ram.bin','-sram.bin'):
   path=ROOT/(stem+suffix);inputs[str(path.relative_to(ROOT))]=sha(path)
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__)
 for filename in('verify_postbattle_release_services.py','verify_postbattle_early_services.py','verify_postbattle_completion_services.py','verify_postbattle_parent_services.py','verify_postbattle_resource_services.py','verify_deployment_pointer_phase26.py','verify_city_auxiliary_services.py'):
  path=ROOT/'scripts'/filename;pins[str(path.relative_to(ROOT))]=sha(path)
 v=dict(schema='phase31-reused-player-postbattle-Source-validation-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,quick=a.quick,new_production_source_modules=0,new_gameplay_algorithm_claim=False,original_CPU_parent_cases=len(cases),counts=dict(Counter(r['comparison']for r in cases)),source_guard_count=len(guards),guards=guards,cases=cases,failed_count=len(failures),failures=failures,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,source_sha256=pins,input_sha256=inputs,executed_instruction_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191),count=n)for(b,pc),n in sorted(visited.items())],limits=['No new production owner: frozen PostbattleReleaseController and phase30 GameEngine/SceneCoordinator are actually reused.','Controlled initial queue/cursor/button/roster values are numerical caller fixtures, not Native readiness writes or observed natural inputs.','All2K RAM including stack/all8K SRAM/AXYP-SP-PC/fourPRG/combined logicalIO/common declaredN163 are compared. No CPU executes on source side.','Normal text busy/noinput paths return as original; Source never fabricates queue readiness.','No Native core or capture producer executes in this verifier. py65 is not a hardware dummy-cycle model.'])
 (OUT/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v[k]for k in('status','original_CPU_parent_cases','counts','failed_count')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
