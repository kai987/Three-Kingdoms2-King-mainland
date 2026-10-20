#!/usr/bin/env python3
"""Actual city13 caller owners and same-context main/NMI/IRQ postbattle runs.

Native supplies immutable RAM/SRAM, never internal CPU registers. Original
JSR/EE07 caller contexts and explicit interrupt arrivals remain separate.
Each whole postbattle continuation counts as one parent comparison.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.integrated_scene_services import IntegratedGlobalUI,IntegratedSceneInitialization
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def reg(r):return{k:getattr(r,k)for k in REGS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256;out=ROOT/'analysis/phase16';out.mkdir(parents=True,exist_ok=True)
 files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_phase16_integration.py'];pins={f:sha(ROOT/f)for f in files};artifacts={};rows=[];failures=[];counts=Counter();guards=[];visited=Counter()
 def load(prefix):
  result=[]
  for ext in('-ram.bin','-sram.bin'):
   path=Path(str(prefix)+ext);artifacts[str(path.relative_to(ROOT))]=sha(path);result.append(path.read_bytes())
  return result
 def memory(r,s,banks):return ServiceMemory(rom,r,s,banks,read_ports={0x2002:0,0x5800:127,0x4015:0},repeat_read_ports=(0x2002,0x5800,0x4015),controller_buttons=(0,0))
 def setup(ram,sram,banks,initial):
  left=memory(ram,sram,banks);right=memory(ram,sram,banks);r=NMIRegisters(**initial);c=MPU(memory=left)
  for k,v in initial.items():setattr(c,k,v)
  game=GameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();assert co.external_callback is None
  assert isinstance(co.global_ui,IntegratedGlobalUI)and isinstance(co.setup,IntegratedSceneInitialization)
  return left,right,r,c,game,co
 def equal(left,right,r,c):
  rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y];sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y];rg={k:[getattr(c,k),getattr(r,k)]for k in REGS if getattr(c,k)!=getattr(r,k)}
  assert not rd and not sd and not rg,dict(RAM=rd[:15],SRAM=sd[:15],registers=rg)
  assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks and left.n163_ram==right.n163_ram
 def original(left,right,r,c,result,limit=1000000):
  for n in range(limit):
   if n and c.pc==r.pc and c.sp==r.sp:
    if result['status']in('returned','reset_boundary')or(reg(c)==reg(r)and left.ram==right.ram and left.sram==right.sram and left.io_writes==right.io_writes):return n
   if c.pc<0x8000:raise RuntimeError(f'Original entered RAMPC{c.pc:04X}')
   bank=left.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1;c.step()
  raise RuntimeError(f'Original budget{c.pc:04X}, source{r.pc:04X}/{result["status"]}')
 # Distinct GameEngine coordinator layer, with frames captured from original
 # city callers. The preparation itself is not counted here as extra cases.
 folder=out/'succession/actual-callee-inputs';inputs=sorted(folder.glob('*.json'));assert len(inputs)==22
 for meta_path in inputs:
  meta=json.loads(meta_path.read_text());artifacts[str(meta_path.relative_to(ROOT))]=sha(meta_path);prefix=meta_path.with_suffix('');ram,sram=load(prefix)
  left,right,r,c,game,co=setup(ram,sram,tuple(meta['actual_banks']),meta['initial_registers'])
  try:
   call=ServiceCall(0xA00C,meta['actual_return_PC'],'actual_original_callee',r,right,tuple(right.banks),meta['actual_return_SP'])
   result=co(call);assert result['status']=='returned',result;n=original(left,right,r,c,result);equal(left,right,r,c)
   assert r.pc==0xEE4D and r.sp==meta['actual_return_SP']
   assert any(x['kind']=='battle_succession'for x in co.calls),'New genuine city13 owner was not selected'
   rows.append(dict(group='GameEngine_genuine_city13_owner',input_path=str(meta_path.relative_to(ROOT)),source_call_API='SceneCoordinator(actual_ServiceCall)',input_provenance=meta,initial_registers=meta['initial_registers'],final_registers=reg(r),comparison='complete_return',completion_kind='actual_caller_RTS',original_instructions=n,RAM_bytes=2048,SRAM_bytes=8192,source_original_CPU_callbacks=0,owner_counts=dict(Counter(x['kind']for x in co.calls))));counts['GameEngine_genuine_city13_owner']+=1
  except Exception as exc:failures.append(dict(group='GameEngine_genuine_city13_owner',input=str(meta_path.relative_to(ROOT)),error=str(exc)))
 for name,expected_leader in [('succession-heir',9),('succession-no-heir',255)]:
  prefix=ROOT/'analysis/phase15/runtime'/name/'observed-g01-n02-city-013-000';ram,sram=load(prefix);banks=(ram[0xDE]&31,ram[0xDF]&31,ram[0xE0]&31,31);initial=dict(a=17,x=31,y=63,p=32,sp=255,pc=0xE066)
  left,right,r,c,game,co=setup(ram,sram,banks,initial);session=game.readable_campaign(r);states=[];NMI_count=IRQ_count=main_count=0;total_instructions=0;irq_stages=[]
  try:
   for tick in range(1200):
    result=session.main();assert result['status']=='returned',result
    total_instructions+=original(left,right,r,c,result);equal(left,right,r,c);main_count+=1
    if tick==0:assert any(x['kind']=='audio_request_exact'for x in co.calls),'Global main1 retained legacy semantic audio instead of exact callees'
    result=session.nmi();c.nmi();total_instructions+=original(left,right,r,c,result);equal(left,right,r,c);NMI_count+=1
    arrivals=0
    while result['status']!='returned':
     assert result['status']=='dependency'and r.pc==0xFB28,result
     if right[0x62]:
      child=session.irq();assert child['status']=='returned';c.irq();total_instructions+=original(left,right,r,c,child);equal(left,right,r,c);IRQ_count+=1;arrivals+=1
      irq_stages.append(dict(tick=tick,flag62=right[0x62],PC=r.pc,SP=r.sp))
     else:
      result=session.resume();total_instructions+=original(left,right,r,c,result);equal(left,right,r,c)
     assert arrivals<10,'Original IRQ software does not clear its pending flag'
    fields=[right[0x7A],right[0x400],right[0x401],right[0x409],right[0x6F0F],right[0x300],right[0x304]]
    if not states or states[-1]['fields']!=fields:states.append(dict(tick=tick,fields=fields))
    if fields[:3]==[2,0,1]and fields[5:]==[255,255]:break
   else:raise RuntimeError('1200 explicitly supplied NMI arrivals did not finish world return text')
   assert right[0x6F0F]==expected_leader and not session.pending
   assert any(x['kind']=='battle_succession'for x in co.calls)
   rows.append(dict(group='same_campaign_city13_to_world',case=name,input_prefix=str(prefix.relative_to(ROOT)),input_provenance='Frozen phase15 actual city13/0 after controlled combat; Native memory only, declaredE066 registers, zero postentry ready/ack/state writes',initial_registers=initial,final_registers=reg(r),comparison='complete_return',completion_kind='main_E066_and_actual_interrupt_RTI_sequence',RAM_bytes=2048,SRAM_bytes=8192,idle_stack_exclusion=None,source_original_CPU_callbacks=0,original_instructions=total_instructions,main_updates=main_count,explicit_NMI_arrivals=NMI_count,explicit_IRQ_arrivals=IRQ_count,nested_events_not_extra_CPU_cases=True,states=states,irq_stages=irq_stages,session_events=session.events,final_leader=right[0x6F0F],final_city_owners=[right[0x6000+32*i]&7 for i in range(30)],final_city_rosters=[list(right[0x6011+32*i:0x601B+32*i])for i in range(30)],owner_counts=dict(Counter(x['kind']for x in co.calls)),ordered_ports_sha256=digest(json.dumps(right.io_writes,separators=(',',':')).encode()),same_register_context=True,manual_ack_or_ready_writes=0,all_event_RAM_SRAM_register_port_bank_N163_comparisons_equal=True));counts['same_campaign_city13_to_world']+=1
   print(json.dumps(dict(case=name,status='passed',NMI=NMI_count,IRQ=IRQ_count,leader=right[0x6F0F]),ensure_ascii=False),flush=True)
  except Exception as exc:failures.append(dict(group='same_campaign_city13_to_world',case=name,error=str(exc),registers=reg(r),states=states))
 # Missing/unknown owners retain the genuine caller rather than fake success.
 left,right,r,c,game,co=setup(ram,sram,banks,initial);before=(bytes(right.ram),bytes(right.sram),reg(r),list(right.io_writes),list(right.banks));r.pc=0x8123;old=reg(r)
 result=co(ServiceCall(0x8123,0x200,'unknown',r,right,tuple(right.banks),255));assert result['status']=='dependency'and old==reg(r)and before[:2]==(bytes(right.ram),bytes(right.sram))and not right.io_writes
 guards.extend(['unowned_entry_retains_actual_caller','exact_audio_inside_existing_global_JSR_frames','independent_global_and_setup_owner_without_original_CPU_callback'])
 assert pins=={f:sha(ROOT/f)for f in files},'Source changed during sequence; rerun after freeze'
 result=dict(schema='phase16-pure-gameengine-city13-integration-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=len(rows),complete_return_count=len(rows),strict_prefix_count=0,source_guard_case_count=len(guards),failed_count=len(failures),failures=failures,rows=rows,guards=guards,counts=dict(counts),completion_kinds=dict(Counter(x['completion_kind']for x in rows)),source_original_CPU_callbacks=0,source_IR_interpretation=False,native_internal_CPU_trace=False,source_sha256=pins,artifact_sha256=artifacts,comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC=True,idle_stack='included',ordered_IO_banks_N163=True),limits=['22 callee comparisons validate GameEngine ownership beyond the independent body matrix; their original preparation/city prefix is not counted again here.','Two same-session sequences count as two parent cases. Their main/NMI/IRQ stages are nested, not additional CPU cases or Native video frames.','Native supplies memory only. Actual callee registers come from controlled originalCPU callers, and session starts with explicitE066 registers.','Only explicit controller/PPUSTATUS/APU/IRQ-read inputs and accepted interrupts are supplied afterentry; no ready/ack/controller phase is written.','Readable source issues software/port effects and does not synthesize pixels/PCM or hardware timing.'])
 (out/'source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'integration-executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,CPU_address=pc,ROM_offset=off,visits=n)for(b,pc,off),n in sorted(visited.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','failures')},ensure_ascii=False));raise SystemExit(bool(failures))
if __name__=='__main__':main()
