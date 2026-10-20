#!/usr/bin/env python3
"""Compare campaign recruitment ownership at actual reached caller inputs.

Real inputs are exported by an independent original CPU from a frozen Native
snapshot. One additional, explicitly prepared fixture verifies the bare
double-PLA return and safe repeated observation of its terminal result.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_recruitment_integration import CityRecruitmentGameEngine,CityRecruitmentSceneCoordinator
from source.recovered.city_recruitment_services import CityRecruitmentServices,UIRegisters,ROM_SHA256
from source.recovered.nestopia_context import CapturedServiceMemory,NestopiaContext
from source.recovered.battle_nmi_services import ServiceCall
from verify_city_recruitment_services import clone,fixture,registers
OUT=ROOT/'analysis/phase21'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 rows=[];inputs={};guards=[];visited=Counter()
 def compare(memory,initial,tag,origin):
  left,right=clone(memory),clone(memory);c=MPU(memory=left);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  game=CityRecruitmentGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules()
  assert isinstance(co,CityRecruitmentSceneCoordinator)and co.external_callback is None
  assert isinstance(game.domestic_secondary_services(),CityRecruitmentServices)
  assert isinstance(game.negotiation_services(),CityRecruitmentServices)
  target=(right[0x100+((r.sp+1)&255)]|right[0x100+((r.sp+2)&255)]<<8)+1&65535
  call=ServiceCall(r.pc,target,'call',r,right,tuple(right.banks),(r.sp+2)&255)
  result=co(call)
  for steps in range(2000000):
   if steps and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']in('returned','nonlocal_return')or registers(c)==registers(r)):break
   assert c.pc>=0x8000,(tag,hex(c.pc));visited[left.banks[(c.pc-0x8000)//8192],c.pc]+=1;c.step()
  else:raise RuntimeError((tag,'CPU budget',c.pc,r.pc))
  assert left.ram==right.ram and left.sram==right.sram,(tag,'memory')
  assert registers(c)==registers(r),(tag,'registers',registers(c),registers(r))
  assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/banks')
  assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
  repeat_unchanged=None
  if result['status']=='nonlocal_return':
   before=(bytes(right.ram),bytes(right.sram),registers(r),list(right.io_reads),list(right.io_writes),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement)
   second=co(call)
   after=(bytes(right.ram),bytes(right.sram),registers(r),list(right.io_reads),list(right.io_writes),list(right.banks),bytes(right.n163_ram),right.n163_address,right.n163_autoincrement)
   assert second is result and second['terminal']and before==after
   assert co._owners[id(call)][0]._program is None
   repeat_unchanged=True;guards.append('terminal_nonlocal_result_never_restarted_or_resumed')
   # This is an ownership guard for the inherited explicit reset protocol,
   # not a second original-CPU gameplay comparison or a simulated reset run.
   reset=co._reset_result(dict(status='reset_boundary',body=dict(registers=dict(pc=0xE066,sp=255))))
   assert reset['retired_pending_callers']and not co._owners and not co._recruitment_nonlocal_results
   guards.append('explicit_reset_retires_terminal_identity_together_with_source_owners')
  rows.append(dict(case=tag,origin=origin,completion=result['status'],initial_registers=initial,final_registers=registers(r),original_CPU_instructions=steps,prepared_new_bytes=origin=='controlled_terminal_fixture',all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal=True,source_original_CPU_callbacks=0,terminal_repeat_unchanged=repeat_unchanged,owner_counts=dict(Counter(x['kind']for x in co.calls)),calls=co.calls))
  print(json.dumps(dict(case=tag,status=result['status'],original_instructions=steps)),flush=True)
 for directory in sorted((OUT/'cpu/actual-callers').glob('entry-*')):
  path=directory/'context.json';x=json.loads(path.read_text());assert x['prepared_numeric_bytes']==[]
  # Local C71A is covered by the callee matrix. It is not a public campaign
  # service and must not be silently sent through the coordinator fallback.
  if x['registers']['pc'] not in CityRecruitmentServices.PUBLIC_ENTRIES:continue
  for p in directory.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  m=CapturedServiceMemory(rom,(directory/'input-ram.bin').read_bytes(),(directory/'input-sram.bin').read_bytes(),x['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(directory/'input-n163.bin').read_bytes();m.n163_address=x['N163_address'];m.n163_autoincrement=x['N163_autoincrement']
  compare(m,x['registers'],'actual/'+directory.name,'actual_Native_snapshot_original_CPU_reached_caller')
 # A controlled success has an explicit nested software call shape. It does
 # not represent a naturally observed campaign or an original-core frame.
 m,r=fixture(rom,0xC6CC);m[0x54]=11
 for i in range(237):m[0x63C0+12*i+11]=(m[0x63C0+12*i+11]&252)|2
 m[0x63C0+12*112+5]=2;m[0x63C0+12*112+11]&=252
 compare(m,r,'controlled/naked-C6CC-nonlocal-success','controlled_terminal_fixture')
 assert rows[-1]['completion']=='nonlocal_return'
 native=ROOT/'analysis/phase20/runtime/natural-F8-accept/F8-request-actually-produced.state'
 raw=native.read_bytes();captured=NestopiaContext.parse(raw)
 game,r=CityRecruitmentGameEngine.from_nestopia_state(rom,raw)
 assert registers(r)==captured.registers and bytes(game.memory.ram)==captured.ram and bytes(game.memory.sram)==captured.sram
 assert list(game.memory.banks)==list(captured.prg_banks)and game.memory.n163_ram==captured.n163_ram
 assert isinstance(game.city_recruitment_services(),CityRecruitmentServices)
 guards.append('snapshot_constructor_preserves_captured_context_and_new_factory')
 inputs[str(native.relative_to(ROOT))]=sha(native)
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for p in [Path(__file__),ROOT/'scripts/verify_city_recruitment_services.py']:sources[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase21-city-recruitment-campaign-ownership-v1',status='passed',ROM_sha256=ROM_SHA256,original_CPU_parent_cases=len(rows),counts=dict(Counter(x['completion']for x in rows)),rows=rows,guard_count=len(guards),guards=guards,source_sha256=sources,input_sha256=inputs,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],limits=['OriginalCPU-reached inputs start at formal captured Native PC/registers; this is not an original-core instruction trace.','The naked C6CC success is an explicitly prepared CPU fixture, not Native gameplay.','A terminal nonlocal result is retained by owner identity; it is not an artificial RTS or resumable pending callee.'])
 (OUT/'source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='passed',parents=len(rows),counts=result['counts'],guards=len(guards))))
if __name__=='__main__':main()
