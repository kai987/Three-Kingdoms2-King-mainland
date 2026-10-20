#!/usr/bin/env python3
"""Compare additive domestic source through actual main/NMI/IRQ software.

Memory is from a frozen natural Native snapshot, including its actual saved registers and PRG/N163 state.
Hardware reads and interrupt arrival order remain explicit oracle inputs. Two whole
sequences count twice, not once per nested event or native video frame.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.domestic_secondary_integration import DomesticSecondaryGameEngine,DomesticSecondarySceneCoordinator
from source.recovered.domestic_secondary_services import DomesticSecondaryServices
from source.recovered.nestopia_context import NestopiaContext
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.game_engine import ROM_SHA256
OUT=ROOT/'analysis/phase19';REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regs(c):return{k:getattr(c,k)for k in REGS}
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 files=list(sorted((ROOT/'source/recovered').glob('*.py')))+[Path(__file__)]
 pins={str(p.relative_to(ROOT)):sha(p)for p in files};artifacts={}
 rows=[];guards=[];visits=Counter()
 for aux in(0,44):
  path=ROOT/f'analysis/phase18/runtime/ai-reinforce-byte1-{aux}/AI-first-original-frame.state'
  artifacts[str(path.relative_to(ROOT))]=sha(path);captured=NestopiaContext.parse(path.read_bytes())
  hardware=dict(read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  imported,actual=DomesticSecondaryGameEngine.from_nestopia_state(rom,path.read_bytes(),**hardware)
  assert regs(actual)==captured.registers and imported.memory.banks==list(captured.prg_banks)
  assert bytes(imported.memory.ram)==captured.ram and bytes(imported.memory.sram)==captured.sram
  assert imported.memory.n163_ram==captured.n163_ram
  left=captured.service_memory(rom,**hardware);c=MPU(memory=left)
  for k,v in captured.registers.items():setattr(c,k,v)
  prelude=0
  while c.pc!=0xE066:
   assert prelude<200000 and c.pc>=0x8000,(c.pc,prelude)
   c.step();prelude+=1
  def memory():
   m=type(left)(rom,left.ram,left.sram,tuple(left.banks),**hardware)
   m.n163_ram[:]=left.n163_ram;m.n163_address=left.n163_address;m.n163_autoincrement=left.n163_autoincrement
   return m
  # Drop only the oracle prelude's I/O ledger. The entire reached machine RAM,
  # SRAM, registers, actual banks and N163 state initialize both comparison sides.
  right=memory();left.io_reads.clear();left.io_writes.clear()
  r=NMIRegisters(**regs(c));initial=regs(r);game=DomesticSecondaryGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();session=game.readable_campaign(r)
  assert isinstance(co,DomesticSecondarySceneCoordinator)and co.external_callback is None
  assert isinstance(game.domestic_secondary_services(),DomesticSecondaryServices)
  steps=irq_count=0;events=[]
  def original(result):
   nonlocal steps
   for n in range(1500000):
    if n and(c.pc,c.sp)==(r.pc,r.sp):
     if result['status']=='returned' or (regs(c)==regs(r)and left.ram==right.ram and left.sram==right.sram and left.io_writes==right.io_writes):return
    assert c.pc>=0x8000,hex(c.pc)
    bank=left.banks[(c.pc-0x8000)//8192];visits[bank,c.pc]+=1;c.step();steps+=1
   raise RuntimeError(f'Original CPU budget at{c.pc:04X}; source{r.pc:04X}')
  def equal(event,result):
   assert bytes(left.ram)==bytes(right.ram),'RAM '+event
   assert bytes(left.sram)==bytes(right.sram),'SRAM '+event
   assert regs(c)==regs(r),(event,regs(c),regs(r))
   assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks and left.n163_ram==right.n163_ram,event
   assert left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,event
   events.append(dict(event=event,status=result['status'],registers=regs(r),all_RAM_SRAM_registers_IO_banks_N163_equal=True))
  for tick in range(2):
   result=session.main();original(result);equal(f'main{tick}',result);assert result['status']=='returned'
   result=session.nmi();c.nmi();original(result);equal(f'NMI{tick}',result)
   while result['status']!='returned':
    assert result['status']=='dependency'and r.pc==0xFB28,result
    if right[0x62]:
     child=session.irq();c.irq();original(child);equal(f'IRQ{irq_count}',child);assert child['status']=='returned';irq_count+=1
    else:
     result=session.resume();original(result);equal(f'NMI{tick}-resume',result)
    assert irq_count<30
  def word(a):return right[a]|right[a+1]<<8
  assert word(0x63C0+167*12+8)in(900,1000)
  assert any(x['kind']=='named_domestic_secondary'for x in co.calls)
  assert not session.pending
  record=game.city_auxiliary_record(4);assert record['official_byte1_name']is None and not record['tail_unused_or_padding_proved']
  assert record['treasure_count_plus16']==right[0x6090]and record['treasure_original_UI_labels']==['宝','タカラ']
  rows.append(dict(case=f'native-register-continuation-aux{aux}',completion_kind='main_E066_and_actual_NMI_IRQ_RTI_sequence',comparison='complete_sequence',
    initial_registers=initial,final_registers=regs(r),preparation=[],inherited_native_numeric_preparation='frozen phase18 case; zero new writes',actual_native_registers=captured.registers,original_CPU_prelude_instructions=prelude,source_original_CPU_callbacks=0,source_IR_interpretation=False,
    main_updates=2,explicit_NMI_arrivals=2,explicit_IRQ_arrivals=irq_count,original_instructions=steps,RAM_bytes=2048,SRAM_bytes=8192,
    events=events,owner_counts=dict(Counter(x['kind']for x in co.calls)),final_fields=dict(city4=record,troops167=word(0x63C0+167*12+8),reserve4=word(0x608C),gold4=word(0x6082),budget=right[0x6F5D]),
    RAM_sha256=hashlib.sha256(bytes(right.ram)).hexdigest(),SRAM_sha256=hashlib.sha256(bytes(right.sram)).hexdigest()))
  print(json.dumps(dict(case=rows[-1]['case'],status='passed',instructions=steps,IRQ=irq_count)),flush=True)
 guards=['new_domestic_owner_selected_by_real_physical10_11_entry','source_callbacks_have_no_CPU_or_IR_fallback','opaque_city_field_names_remain_unclaimed']
 assert pins=={str(p.relative_to(ROOT)):sha(p)for p in files},'Source changed during verification; rerun afterfreeze'
 result=dict(schema='phase19-Native-register-continuation-main-NMI-IRQ-source-v1',status='passed',ROM_sha256=ROM_SHA256,
   source_sha256=pins,artifact_sha256=artifacts,rom_cpu_sequence_count=2,actual_caller_RTS_count=0,source_guard_case_count=len(guards),guards=guards,rows=rows,
   original_Native_internal_CPU_trace=False,source_original_CPU_callbacks=0,source_IR_interpretation=False,
   comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC=True,ordered_IO_banks_N163=True,idle_stack_included=True),
   limitations=['Initial PC/SP/AXYP, RAM/SRAM, actual PRG banks and N163 state are parsed from a frozen original-core state. A validator-only originalCPU prelude reaches E066; subsequent source execution uses zero CPU callbacks.','Main/NMI/IRQ event arrivals are explicit CPU fixtures, not Native frame timing.','Two main updates finish at original E066/RTI boundaries; they are not two actual caller RTS cases.','The native core proceeds farther with its own timing and different final strategy/budget/gold results; only matching recruitment event is cross-evidence.'])
 (OUT/'source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (OUT/'integration-executed-instructions.json').write_text(json.dumps(dict(instruction_count=len(visits),instructions=[dict(physical_bank=b,cpu=p,ROM_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visits.items())]),indent=2)+'\n')
 print(json.dumps(dict(status='passed',CPU_sequences=2,guards=len(guards))))
if __name__=='__main__':main()
