#!/usr/bin/env python3
"""Actual original-core F8 snapshot -> source consumer -> same caller resume.

All request writes originate in original/recovered software. The only later
inputs are two real controller bytes and explicit NMI/IRQ arrivals. No text
ready, reply, result, request or program-counter assignment advances the flow.
These are CPU software event sequences, not Nativevideo frames.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.negotiation_integration import NegotiationGameEngine
from source.recovered.negotiation_services import NegotiationServices,UIRegisters,ROM_SHA256
from source.recovered.nestopia_context import NestopiaContext
from verify_domestic_secondary_services import clone,reg,sha
OUT=ROOT/'analysis/phase20/cpu'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--case',choices=('all','alliance-accept','alliance-reject'),default='all');p.add_argument('--max-nmi',type=int,default=1000);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];executed=Counter()
 for case in(('alliance-accept','alliance-reject')if a.case=='all'else(a.case,)):
  native_folder=ROOT/'analysis/phase20/runtime'/('natural-F8-accept'if case=='alliance-accept'else'natural-F8-reject')
  path=native_folder/'F8-request-actually-produced.state'
  captured=NestopiaContext.parse(path.read_bytes())
  hardware=dict(read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  left=captured.service_memory(rom,**hardware);c=MPU(memory=left)
  for k,v in captured.registers.items():setattr(c,k,v)
  prelude=0
  while c.pc!=0xB78B:
   assert prelude<10000 and c.pc>=0x8000,(c.pc,prelude)
   c.step();prelude+=1
  assert left[0x6F8B]==248
  right=clone(left);left.io_reads.clear();left.io_writes.clear()
  initial=reg(c);r=UIRegisters(**initial);entry=0xB78B
  game=NegotiationGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();owner=game.negotiation_services()
  events=[];steps=irq_count=0;inputs=[];stages=[];first_response=None;did_down=False
  def original(result):
   nonlocal steps
   for n in range(2000000):
    match=(c.pc,c.sp)==(r.pc,r.sp)
    if result['status']in('waiting','dependency'):match=match and reg(c)==reg(r)
    if n and match:return
    bank=left.banks[(c.pc-0x8000)//8192]if c.pc>=0x8000 else None
    if bank is not None:executed[bank,c.pc]+=1
    c.step();steps+=1
   raise RuntimeError(f'Originalbudget{c.pc:04X}; source{r.pc:04X}')
  def equal(event,result):
   rd=[(i,left.ram[i],right.ram[i])for i in range(2048)if left.ram[i]!=right.ram[i]];sd=[(i,left.sram[i],right.sram[i])for i in range(8192)if left.sram[i]!=right.sram[i]]
   assert not rd and not sd and reg(c)==reg(r),dict(event=event,RAM=rd[:8],SRAM=sd[:8],regs=(reg(c),reg(r)))
   assert left.io_writes==right.io_writes and left.io_reads==right.io_reads and left.banks==right.banks and left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,event
   events.append(dict(event=event,status=result['status'],registers=reg(r),request=right[0x6F8B],city=[right[x]for x in range(0x400,0x403)],menu_index=right[0x12],text_jobs=[right[0x300],right[0x304]],full_scope_equal=True))
  try:
   out=owner.run_entry(entry,registers=r);original(out);equal('actual-Native-request-await-prefix',out);assert out['status']=='waiting',(case,out)
   request=right[0x6F8B];assert request in(248,249,250)
   for tick in range(a.max_nmi):
    cityphase=right[0x401];citysub=right[0x402]
    buttons=0
    if case=='alliance-reject'and cityphase==16 and citysub==1 and not did_down:
     buttons=128;did_down=True
    elif tick>=20 and tick%12==0:buttons=1
    left.controller_buttons=right.controller_buttons=(buttons,buttons);inputs.append(dict(NMI=tick+1,controller_ports=[buttons,buttons]))
    out=co.run_nmi(r,hardware_entry=True);c.nmi();original(out);equal(f'NMI{tick}',out)
    while out['status']!='returned':
     assert out['status']=='dependency'and r.pc==0xFB28,dict(case=case,tick=tick,status=out['status'],pc=hex(r.pc),calls=co.calls[-3:])
     if right[0x62]:
      child=co.run_irq(r,hardware_entry=True);c.irq();original(child);equal(f'IRQ{irq_count}',child);assert child['status']=='returned';irq_count+=1
     else:
      out=co.resume_nmi();original(out);equal(f'NMI{tick}-resume',out)
    stages.append([right[0x400],right[0x401],right[0x402],right[0x6F8B]])
    if right[0x6F8B]!=request:
     first_response=dict(NMI=tick+1,value=right[0x6F8B],registers=reg(r));break
    again=owner.resume();assert again['status']=='waiting';equal(f'unchanged-request{tick}',again)
   else:raise RuntimeError(f'Explicit NMIbudget; request{right[0x6F8B]:02X},city{stages[-1]}')
   out=owner.resume();original(out);equal('same-secondary-generator-resume',out);assert out['status']=='returned'
   if case=='alliance-accept':assert first_response['value']==0
   if case=='alliance-reject':assert first_response['value']!=0
   rows.append(dict(case=case,completion_kind='actual_caller_RTS_after_genuine_NMI2_consumer',comparison='complete_sequence',initial_registers=initial,final_registers=reg(r),Native_state_path=str(path.relative_to(ROOT)),Native_state_sha256=sha(path),captured_Native_registers=captured.registers,original_CPU_prelude_instructions=prelude,prepared_bytes=[],initial_request_from_original_core=request,actual_response=first_response,explicit_NMI_arrivals=len(inputs),explicit_IRQ_arrivals=irq_count,controller_input_plan=inputs,original_instructions=steps,events=events,city_stages=stages,source_original_CPU_callbacks=0,postentry_memory_injections=0,Native_internal_CPU_trace=False,all_RAM_byte_count=2048,all_SRAM_byte_count=8192,comparison_registers='AXYP SP PC',ordered_IO_equal=True,all4banks_equal=True,N163_state_equal=True,all_services_pure_source=co.external_callback is None))
   print(json.dumps(dict(case=case,status='passed',NMI=len(inputs),IRQ=irq_count,reply=first_response['value'])),flush=True)
  except Exception as e:
   failures.append(dict(case=case,error=str(e),stages=stages[-10:],events=events[-3:],source_PC=r.pc,request=right[0x6F8B]));print(json.dumps(failures[-1]),flush=True)
 pins={str(p.relative_to(ROOT)):sha(p)for p in ROOT.glob('source/recovered/*.py')};pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__);pins['scripts/verify_domestic_secondary_services.py']=sha(ROOT/'scripts/verify_domestic_secondary_services.py')
 receipt=dict(schema='phase20-actual-Native-wait-context-source-continuation-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_sequence_count=len(rows),failed_count=len(failures),rows=rows,failures=failures,source_sha256=pins,source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,comparison=dict(RAM=2048,SRAM=8192,AXYP_SP_PC=True,ordered_IO_banks_N163=True,inactive_stack_included=True),executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(executed.items())],limits=['Initial CPU registers, actual PRG banks, RAM/SRAM and N163 state come from the formal original-core F8 capture. A declared originalCPU prelude reaches the actual B78B wait head; there are zero prepared bytes.','NMI and IRQ arrivals and controller values are explicit software inputs, not a cycleaccurate emulator timeline.','The initial F8 request was produced by the original core. All subsequent replies and text readiness come only from original/readable consumers.','Each long sequence counts once. Parentcomparison rows do not add one case per NMI, IRQ or service call.'])
 (OUT/'native-context-source-sequences.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');return 0 if not failures else 1
if __name__=='__main__':sys.exit(main())
