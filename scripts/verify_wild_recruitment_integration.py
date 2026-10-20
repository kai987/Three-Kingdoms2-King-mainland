#!/usr/bin/env python3
"""Verify postbattle/campaign factories with explicit caller provenance.

OriginalCPU continuation is a comparison oracle only. The production owner
uses named source and inherited exact hardware/service contracts.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.wild_recruitment_integration import WildRecruitmentGameEngine,WildRecruitmentSceneCoordinator
from source.recovered.postbattle_release_services import PostbattleReleaseController,BattleRegisters,ROM_SHA256
from source.recovered.city_recruitment_services import CityRecruitmentServices
from source.recovered.nestopia_context import CapturedServiceMemory,NestopiaContext
from source.recovered.battle_nmi_services import ServiceCall
from verify_postbattle_release_services import clone,fixture,registers
OUT=ROOT/'analysis/phase22'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 rows=[];guards=[];inputs={};visited=Counter()
 def compare(memory,initial,tag,origin,*,mode='callee'):
  left,right=clone(memory),clone(memory);cpu=MPU(memory=left);r=BattleRegisters(**initial)
  for k,v in initial.items():setattr(cpu,k,v)
  game=WildRecruitmentGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules()
  assert isinstance(co,WildRecruitmentSceneCoordinator)and co.external_callback is None
  assert isinstance(co.controller(3),PostbattleReleaseController)
  assert isinstance(game.postbattle_release_services(),PostbattleReleaseController)
  assert isinstance(game.city_recruitment_services(),CityRecruitmentServices)
  target=((right[0x100+((r.sp+1)&255)]|right[0x100+((r.sp+2)&255)]<<8)+1)&65535
  call=ServiceCall(r.pc,target,'call',r,right,tuple(right.banks),(r.sp+2)&255)
  result=co.tick(r,scene=3)if mode=='scene'else co(call)
  for steps in range(2000000):
   if steps and(cpu.pc,cpu.sp)==(r.pc,r.sp)and(result['status']=='returned'or registers(cpu)==registers(r)):break
   assert cpu.pc>=0x8000,(tag,hex(cpu.pc));visited[left.banks[(cpu.pc-0x8000)//8192],cpu.pc]+=1;cpu.step()
  else:raise RuntimeError((tag,'CPU budget',cpu.pc,r.pc))
  assert left.ram==right.ram and left.sram==right.sram,(tag,'memory')
  assert registers(cpu)==registers(r),(tag,'registers',registers(cpu),registers(r))
  assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/PRG')
  assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
  if result['status']=='nonlocal_return':
   before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.io_reads),list(right.io_writes),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement)
   repeated=co(call)
   after=(bytes(right.ram),bytes(right.sram),registers(r),list(right.io_reads),list(right.io_writes),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement)
   assert repeated is result and result['terminal']and before==after
   guards.append('actual_nonlocal_terminal_caller_not_restarted/'+tag)
  rows.append(dict(case=tag,origin=origin,mode=mode,completion=result['status'],initial_registers=initial,final_registers=registers(r),original_CPU_instructions=steps,prepared_new_bytes=origin=='controlled_numeric_and_caller_CPU_fixture',all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal=True,source_original_CPU_callbacks=0,calls=co.calls))
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
 for directory in sorted((OUT/'cpu/actual-callers').glob('entry-*')):
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
 raw=(ROOT/'analysis/phase21/runtime/original-control/actual-cold-frame10491.state').read_bytes();context=NestopiaContext.parse(raw)
 game,r=WildRecruitmentGameEngine.from_nestopia_state(rom,raw)
 assert registers(r)==context.registers and bytes(game.memory.ram)==context.ram and bytes(game.memory.sram)==context.sram
 assert isinstance(game.readable_scene_rules().controller(3),PostbattleReleaseController)
 assert isinstance(game.negotiation_services(),CityRecruitmentServices)
 guards.append('snapshot_factory_preserves_actual_context_and_composes_both_source_domains')
 co=game.readable_scene_rules();old=co.controller(3)
 result=co._reset_result(dict(status='reset_boundary',body=dict(registers=dict(pc=0xE066,sp=255))))
 assert result['retired_pending_callers']and co.controller(3)is not old and isinstance(co.controller(3),PostbattleReleaseController)
 guards.append('reset_retires_scene_owner_and_rebuilds_named_postbattle_factory')
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in(Path(__file__),ROOT/'scripts/verify_postbattle_release_services.py'):sources[str(p.relative_to(ROOT))]=sha(p)
 value=dict(schema='phase22-wild-recruitment-source-composition-v1',status='passed',ROM_sha256=ROM_SHA256,original_CPU_parent_cases=len(rows),counts=dict(Counter(x['completion']for x in rows)),rows=rows,guard_count=len(guards),guards=guards,source_sha256=sources,input_sha256=inputs,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],limits=['Declared CPU fixture and actual saved-context callee comparisons are separate from Native frame observations.','No originalCPU or IR runs in the production source coordinator.','The reset check is an owner/factory guard; it is not a second CPU gameplay case.'])
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'source-integration.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='passed',parents=len(rows),counts=value['counts'],guards=len(guards))))
if __name__=='__main__':main()
