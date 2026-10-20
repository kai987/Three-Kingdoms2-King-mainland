#!/usr/bin/env python3
"""Verify postbattle parent routing and frozen campaign regression fixtures with explicit caller provenance.

OriginalCPU continuation is a comparison oracle only. The production owner
uses named source and inherited exact hardware/service contracts.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle_parent_integration import PostbattleParentGameEngine,PostbattleParentSceneCoordinator,PostbattleReturnBridge
from source.recovered.appearance_pointer_services import AppearancePointerServices
from source.recovered.deployment_pointer_services import DeploymentPointerServices
from source.recovered.postbattle_resource_services import PostbattleResourceServices
from source.recovered.postbattle_parent_services import PostbattleParentServices
from verify_postbattle_parent_services import fixture as parent_fixture
from source.recovered.tactical_cooperation_controller import TacticalCooperationController
from source.recovered.city_action_bridges import CityActionBridges
from source.recovered.global_ui_controller import RulerSelectionUIController
from source.recovered.pointer_lifecycle_services import PointerLifecycleServices
from source.recovered.city_threshold_services import CityThresholdServices
from source.recovered.postbattle_release_services import PostbattleReleaseController,BattleRegisters,ROM_SHA256
from source.recovered.city_recruitment_services import CityRecruitmentServices
from source.recovered.nestopia_context import CapturedServiceMemory,NestopiaContext
from source.recovered.battle_nmi_services import ServiceCall
from verify_postbattle_release_services import fixture,registers
OUT=ROOT/'analysis/phase28'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class OrderedComparisonMemory(CapturedServiceMemory):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.ordered_io=[]
 def io_read(self,address):
  value=super().io_read(address);self.ordered_io.append(('read',address&65535,value));return value
 def io_write(self,address,value):
  super().io_write(address,value);self.ordered_io.append(('write',address&65535,value&255))

def clone(m):
 # This test bus observes logical API accesses, not 6502 dummy cycles.
 b=OrderedComparisonMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),
  read_ports={k:list(v)for k,v in m.read_ports.items()},repeat_read_ports=m.repeat_read_ports,
  controller_buttons=m.controller_buttons)
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement
 return b

def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 assert not set(PostbattleResourceServices.NEW_ENTRIES)&set(TacticalCooperationController.LOCAL_ENTRIES+CityActionBridges.SHOP_ENTRIES+RulerSelectionUIController.PUBLIC_ENTRIES)
 rows=[];guards=[];inputs={};visited=Counter()
 def compare(memory,initial,tag,origin,*,mode='callee',inherited_preparation=None,N163_context_origin=None,caller_kind='call',ancestry_context=None):
  left,right=clone(memory),clone(memory);cpu=MPU(memory=left);r=BattleRegisters(**initial)
  for k,v in initial.items():setattr(cpu,k,v)
  game=PostbattleParentGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules()
  assert isinstance(co,PostbattleParentSceneCoordinator)and co.external_callback is None
  assert isinstance(co.controller(3),PostbattleReleaseController)
  assert isinstance(co.controller(2),PointerLifecycleServices)
  assert isinstance(game.pointer_lifecycle_services(),PointerLifecycleServices)
  assert isinstance(game.postbattle_release_services(),PostbattleReleaseController)
  assert isinstance(game.city_recruitment_services(),CityThresholdServices)
  assert isinstance(game.city_threshold_services(),AppearancePointerServices)
  assert isinstance(game.appearance_pointer_services(),AppearancePointerServices)
  assert isinstance(game.deployment_pointer_services(),DeploymentPointerServices)
  assert isinstance(game.postbattle_resource_services(),PostbattleResourceServices)
  assert isinstance(game.postbattle_parent_services(),PostbattleParentServices)
  target=((right[0x100+((r.sp+1)&255)]|right[0x100+((r.sp+2)&255)]<<8)+1)&65535
  call=ServiceCall(r.pc,target,caller_kind,r,right,tuple(right.banks),(r.sp+2)&255)
  result=co.tick(r,scene=3)if mode=='scene'else co(call)
  for steps in range(2000000):
   if steps and(cpu.pc,cpu.sp)==(r.pc,r.sp)and(result['status']=='returned'or registers(cpu)==registers(r)):break
   assert cpu.pc>=0x8000,(tag,hex(cpu.pc));visited[left.banks[(cpu.pc-0x8000)//8192],cpu.pc]+=1;cpu.step()
  else:raise RuntimeError((tag,'CPU budget',cpu.pc,r.pc))
  assert left.ram==right.ram and left.sram==right.sram,(tag,'memory')
  assert registers(cpu)==registers(r),(tag,'registers',registers(cpu),registers(r))
  assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/PRG')
  assert left.ordered_io==right.ordered_io,(tag,'combined logical IO order')
  assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
  if result['status']=='nonlocal_return':
   before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.io_reads),list(right.io_writes),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement)
   repeated=co(call)
   after=(bytes(right.ram),bytes(right.sram),registers(r),list(right.io_reads),list(right.io_writes),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement)
   assert repeated is result and result['terminal']and before==after
   guards.append('actual_nonlocal_terminal_caller_not_restarted/'+tag)
  if result['status']=='returned':assert id(call)not in getattr(co,'_parent_pending_calls',{})
  if result['status']=='dependency':
   assert co._parent_pending_calls.get(id(call))is call
   before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.banks),list(right.ordered_io));owners={k:id(v[0])for k,v in co._owners.items()}
   repeated=co(call)
   after=(bytes(right.ram),bytes(right.sram),registers(r),list(right.banks),list(right.ordered_io))
   assert repeated['status']=='dependency'and before==after and owners=={k:id(v[0])for k,v in co._owners.items()}
   guards.append('unimplemented_stage_prefix_retains_same_owners_without_fake_ack/'+tag)
  rows.append(dict(case=tag,origin=origin,ancestry_context=ancestry_context,mode=mode,completion=result['status'],comparison={'returned':'actual_caller_RTS','nonlocal_return':'actual_nonlocal_return','dependency':'strict_dependency_prefix'}[result['status']],initial_registers=initial,final_registers=registers(r),original_CPU_instructions=steps,prepared_new_bytes=origin=='controlled_numeric_and_caller_CPU_fixture',inherited_Native_preparation=inherited_preparation or [],N163_context_origin=N163_context_origin,caller_kind=caller_kind,all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal=True,combined_logical_IO_order_equal=True,logical_IO_accesses=len(right.ordered_io),logical_IO_sha256=hashlib.sha256(json.dumps(right.ordered_io,separators=(',',':')).encode()).hexdigest(),source_original_CPU_callbacks=0,calls=co.calls))
  print(json.dumps(dict(case=tag,status=result['status'],original_instructions=steps)),flush=True)
 # Real campaign callee inputs from phase21 remain originalCPU continuations
 # from captured registers. They are not new Native instruction traces.
 for directory in sorted((ROOT/'analysis/phase21/cpu/actual-callers').glob('entry-*')):
  path=directory/'context.json';x=json.loads(path.read_text())
  if x['registers']['pc']not in CityRecruitmentServices.PUBLIC_ENTRIES:continue
  assert x['prepared_numeric_bytes']==[]
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],'actual-campaign/'+directory.name,'actual_Native_snapshot_originalCPU_reached_caller')
 # These four preparation fixtures test new routing and whole caller effects;
 # successful Native release/recruitment is a separate runtime evidence domain.
 for entry in(0xD1F9,0xD20D,0xD299):
  m,r=fixture(rom,entry);r['a']=167 if entry==0xD299 else r['a']
  compare(m,r,'controlled-release/'+hex(entry),'controlled_numeric_and_caller_CPU_fixture')
 m,r=fixture(rom,0xD20D);m[0x540]=4;m[0x6080+17:0x6080+27]=bytes([255])*10
 compare(m,r,'controlled-normal-city-allocation','controlled_numeric_and_caller_CPU_fixture')
 # Native-reached new battle inputs can be appended without routing unsupported
 # arbitrary PCs or manufacturing a software frame.
 for directory in sorted((ROOT/'analysis/phase22/cpu/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text());assert x['prepared_numeric_bytes']==[]
  pair=tuple(x['physical_banks'][1:3])
  if pair==(12,13):prefix='actual-battle/'
  elif pair==(10,11)and x['registers']['pc']in CityRecruitmentServices.PUBLIC_ENTRIES:prefix='actual-recruitment/'
  else:continue
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  origin=x['origin']
  assert origin in('actual_Native_snapshot_originalCPU_reached_caller','Native_snapshot_plus_declared_hardware_NMI_CPU_fixture')
  if origin=='Native_snapshot_plus_declared_hardware_NMI_CPU_fixture':assert x['hardware_events']
  compare(m,x['registers'],prefix+directory.name,origin)
 # New helper inputs retain the real complete caller stack exported from the
 # original saved CPU context; their provenance is checked before dispatch.
 for directory in sorted((ROOT/'analysis/phase23/cpu-threshold/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  if x['registers']['pc'] not in CityThresholdServices.PUBLIC_ENTRIES:continue
  assert tuple(x['physical_banks'][1:3])==(10,11)
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  assert x['additional_CPU_prepared_numeric_bytes']==[]
  if x['origin']=='actual_Native_snapshot_originalCPU_reached_caller':
   assert x['prepared_numeric_bytes']==[]
  else:
   assert x['origin']=='diagnostic_Native_snapshot_originalCPU_reached_caller'
   assert len(x['prepared_numeric_bytes']) in(2,3)
   assert all(v['kind']=='SRAM' and v['address'] in(0x6041,0x6042,0x6043) for v in x['prepared_numeric_bytes'])
  compare(m,x['registers'],'actual-city-threshold/'+directory.name,x['origin'],inherited_preparation=x['prepared_numeric_bytes'])
 # New allocation helper inputs retain declared controller ports and the
 # actual software caller frame; any new hardware event stays in provenance.
 for directory in sorted((ROOT/'analysis/phase24/cpu-lifecycle/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  if x['registers']['pc'] not in PointerLifecycleServices.LOCAL_ENTRIES:continue
  assert tuple(x['physical_banks'][1:3])==(27,28)
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x.get('controller_buttons',(0,0))))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  assert x['prepared_numeric_bytes']==[]
  origin=x['origin']
  assert origin in('actual_Native_snapshot_originalCPU_reached_caller','Native_snapshot_plus_declared_hardware_NMI_CPU_fixture','passive_Native_callee_capture_with_explicit_N163_fixture')
  if origin=='Native_snapshot_plus_declared_hardware_NMI_CPU_fixture':assert x['hardware_events']
  if origin=='passive_Native_callee_capture_with_explicit_N163_fixture':
   assert x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
   assert x['additional_CPU_prepared_numeric_bytes']==[]
  compare(m,x['registers'],'allocation-lifecycle/'+directory.name,origin,N163_context_origin=x.get('N163_origin'))
 # Newly captured phase25 software contexts keep the existing real caller.
 # N163 is a common explicit fixture, never an invented instantaneous Native snapshot.
 new_actual_targets=[]
 for directory in sorted((ROOT/'analysis/phase25/cpu-appearance/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  if x['registers']['pc'] not in AppearancePointerServices.PUBLIC_ENTRIES:continue
  assert tuple(x['physical_banks'][1:3])==(10,11)
  assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'
  assert x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  assert x['prepared_numeric_bytes']==x['additional_CPU_prepared_numeric_bytes']==[]
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x.get('controller_buttons',(0,0))))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],'deployment-pointer/'+directory.name,x['origin'],N163_context_origin=x['N163_origin'])
  new_actual_targets.append(x['registers']['pc'])
 assert {0xC5D2,0xD471}<=set(new_actual_targets),'Both actual appearance and multiplication caller inputs are required'
 submit_count=0
 for directory in sorted((ROOT/'analysis/phase25/cpu-submit/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  assert x['registers']['pc']==0xB431 and tuple(x['physical_banks'][1:3])==(27,28)
  assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'
  assert x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  assert x['prepared_numeric_bytes']==x['additional_CPU_prepared_numeric_bytes']==[]
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x['controller_buttons']))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],'actual-nonzero-submit/'+directory.name,x['origin'],N163_context_origin=x['N163_origin'])
  submit_count+=1
 assert submit_count==1,'Exactly one real action-bearing B431 entry is required'
 # New passive Native software contexts retain their actual callee stacks.
 # Ports and N163 are explicitly shared software fixtures, with no CPU NMI.
 deployment_count=0
 for directory in sorted((ROOT/'analysis/phase26/cpu-deployment/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  assert x['registers']['pc'] in DeploymentPointerServices.PUBLIC_ENTRIES
  assert tuple(x['physical_banks'][1:3])==(8,9)
  assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'
  assert x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  assert x['prepared_numeric_bytes']==x['additional_CPU_prepared_numeric_bytes']==[]
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x.get('controller_buttons',(0,0))))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],'deployment-pointer/'+directory.name,x['origin'],N163_context_origin=x['N163_origin'])
  deployment_count+=1
 assert deployment_count, 'At least one actual passive deployment entry is required'
 # New actual resource inputs remain distinct by ancestry and transfer kind.
 # The parent A006/BAB3 controller is outside this new exact owner.
 resource_count=0;resource_ancestries=Counter();resource_transfers=Counter();resource_targets=set()
 for directory in sorted((ROOT/'analysis/phase27/cpu-resource/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  assert x['registers']['pc'] in PostbattleResourceServices.NEW_ENTRIES
  assert tuple(x['physical_banks'][1:3])==(8,9)
  assert x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  assert x['prepared_numeric_bytes']==x['additional_CPU_prepared_numeric_bytes']==[]
  assert x['ancestry_origin'] in ('natural_ancestry','controlled_ancestry')
  assert x['controlled_ancestry']==(x['ancestry_origin']=='controlled_ancestry')
  assert len(x['inherited_Native_preparation'])==x['known_inherited_preparation_byte_writes']==(19 if x['controlled_ancestry'] else 0)
  assert x['actual_call_kind'] in ('call','tail')
  assert not x['synthetic_caller_PC_or_stack'] and x['immediate_transfer_proof']
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x.get('controller_buttons',(0,0))))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  ancestry={k:x[k] for k in ('ancestry_origin','controlled_ancestry','natural_ordinary_input_route','known_inherited_preparation_byte_writes','ancestry_provenance','actual_call_kind','immediate_transfer_PC','immediate_transfer_proof','real_return_frame_owner')}
  compare(m,x['registers'],'postbattle-resource/'+directory.name,x['origin'],inherited_preparation=x['inherited_Native_preparation'],N163_context_origin=x['N163_origin'],caller_kind=x['actual_call_kind'],ancestry_context=ancestry)
  resource_count+=1;resource_ancestries[x['ancestry_origin']]+=1;resource_transfers[x['actual_call_kind']]+=1;resource_targets.add(x['registers']['pc'])
 assert resource_count==10 and resource_targets==set(PostbattleResourceServices.NEW_ENTRIES)
 assert resource_ancestries=={'natural_ancestry':1,'controlled_ancestry':9}
 assert resource_transfers=={'call':9,'tail':1}
 # Explicit controlled midpoint contexts are separate from passive Native
 # software snapshots. CC29 is never silently supplied by this bridge.
 controlled_parent_cases=0
 for stage in (0,1,2,3):
  for outcome in (0,1):
   m,r=parent_fixture(rom,stage=stage,outcome=outcome)
   r.update(pc=0xD4F5,y=0x28);m.banks[1:3]=[12,13];m[0xE2]=44;m[0xE3]=45
   compare(m,r,f'controlled-far-midpoint/stage{stage}/outcome{outcome}','controlled_numeric_and_caller_CPU_fixture',caller_kind='controlled_midpoint_fixture')
   controlled_parent_cases+=1
 parent_count=0;parent_ancestries=Counter();parent_targets=Counter()
 for directory in sorted((OUT/'cpu-parent/actual-callers').glob('entry-*')):
  x=json.loads((directory/'context.json').read_text())
  pair=tuple(x['physical_banks'][1:3]);entry=x['registers']['pc']
  assert (pair==(8,9)and entry in PostbattleParentServices.NEW_ENTRIES)or(pair==(12,13)and entry==PostbattleReturnBridge.ENTRY)
  assert x['origin']=='passive_Native_callee_capture_with_explicit_N163_fixture'
  assert x['N163_origin']=='explicit_shared_fixture_not_Native_snapshot'
  assert x['prepared_numeric_bytes']==x['additional_CPU_prepared_numeric_bytes']==[]
  assert len(x['inherited_Native_preparation'])==x['known_inherited_preparation_byte_writes']==(19 if x['controlled_ancestry']else 0)
  for path in directory.iterdir():inputs[str(path.relative_to(ROOT))]=sha(path)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=tuple(x.get('controller_buttons',(0,0))))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  ancestry={k:x[k]for k in ('ancestry_origin','controlled_ancestry','natural_ordinary_input_route','known_inherited_preparation_byte_writes','ancestry_provenance','actual_call_kind','immediate_transfer_PC','immediate_transfer_proof','real_return_frame_owner')}
  compare(m,x['registers'],'postbattle-parent/'+directory.name,x['origin'],inherited_preparation=x['inherited_Native_preparation'],N163_context_origin=x['N163_origin'],caller_kind=x['actual_call_kind'],ancestry_context=ancestry)
  parent_count+=1;parent_ancestries[x['ancestry_origin']]+=1;parent_targets[entry]+=1
 assert parent_count==14 and {0xA006,0xBAB3,0xBB93,0xC027,0xD4F5}==set(parent_targets),'All14 actual stage2, stage3-prefix and midpoint inputs are required'
 assert parent_ancestries=={'controlled_ancestry':7,'natural_ancestry':7}
 raw=(ROOT/'analysis/phase21/runtime/original-control/actual-cold-frame10491.state').read_bytes();context=NestopiaContext.parse(raw)
 game,r=PostbattleParentGameEngine.from_nestopia_state(rom,raw)
 assert registers(r)==context.registers and bytes(game.memory.ram)==context.ram and bytes(game.memory.sram)==context.sram
 assert isinstance(game.readable_scene_rules().controller(3),PostbattleReleaseController)
 assert isinstance(game.negotiation_services(),CityThresholdServices)
 assert isinstance(game.city_ui_services(),PointerLifecycleServices)
 guards.append('snapshot_factory_preserves_actual_context_and_inherited_source_domains')
 co=game.readable_scene_rules();old=co.controller(3)
 # A reset must also retire this layer's terminal call identities. This is
 # a lifecycle guard with an explicit sentinel, not another gameplay case.
 co._resource_nonlocal_results={-1:(object(),{'status':'nonlocal_return'})}
 co._parent_nonlocal_results={-2:(object(),{'status':'nonlocal_return'})}
 co._parent_pending_calls={-3:object()}
 result=co._reset_result(dict(status='reset_boundary',body=dict(registers=dict(pc=0xE066,sp=255))))
 assert result['retired_pending_callers']and co.controller(3)is not old and isinstance(co.controller(3),PostbattleReleaseController)
 assert isinstance(co.controller(2),PointerLifecycleServices)
 assert co._resource_nonlocal_results=={} and co._parent_nonlocal_results=={} and co._parent_pending_calls=={}
 guards.append('reset_retires_scene_and_resource_terminal_owners_and_rebuilds_inherited_factories')
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in(Path(__file__),ROOT/'scripts/verify_postbattle_release_services.py'):sources[str(p.relative_to(ROOT))]=sha(p)
 value=dict(schema='phase28-postbattle-stage2-source-composition-v1',status='passed',ROM_sha256=ROM_SHA256,inherited_regression_cases=58,inherited_resource_caller_cases=resource_count,new_controlled_midpoint_cases=controlled_parent_cases,new_parent_caller_cases=parent_count,new_parent_ancestries=dict(parent_ancestries),new_parent_targets=dict(parent_targets),new_resource_ancestries=dict(resource_ancestries),new_resource_transfers=dict(resource_transfers),original_CPU_parent_cases=len(rows),counts=dict(Counter(x['completion']for x in rows)),comparison_counts=dict(Counter(x['comparison']for x in rows)),rows=rows,guard_count=len(guards),guards=guards,source_sha256=sources,input_sha256=inputs,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],limits=['Declared CPU fixture and actual saved-context callee comparisons are separate from Native frame observations.','No originalCPU or IR runs in the production source coordinator.','The reset check is an owner/factory guard; it is not a second CPU gameplay case.','Combined logical IO order is compared at the service API; py65 does not emit hardware dummy bus cycles and no CPU interrupt is injected.','The58 inherited regression fixtures are rerun under the new frontdoor; they are not newly discovered game algorithms.','The D4F5 midpoint excludes CC29 and the preceding LDY28. ECEE starts fade synchronously; stage3 remains a strict dependency.'])
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'source-integration.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='passed',parents=len(rows),counts=value['counts'],guards=len(guards))))
if __name__=='__main__':main()
