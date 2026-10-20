#!/usr/bin/env python3
"""Compare additive domestic source through actual main/NMI/IRQ software.

Memory is from a frozen natural Native snapshot, but registers, hardware reads
and interrupt arrival order are explicit software-oracle inputs. Two whole
sequences count twice, not once per nested event or native video frame.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_auxiliary_integration import CityAuxiliaryGameEngine,CityAuxiliarySceneCoordinator
from source.recovered.city_auxiliary_services import CityAuxiliaryServices
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.game_engine import ROM_SHA256
OUT=ROOT/'analysis/phase18';REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regs(c):return{k:getattr(c,k)for k in REGS}
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 prefix=ROOT/'analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame34623'
 ram_path=Path(str(prefix)+'-ram.bin');sram_path=Path(str(prefix)+'-sram.bin');ram=ram_path.read_bytes();sram=sram_path.read_bytes()
 files=list(sorted((ROOT/'source/recovered').glob('*.py')))+[Path(__file__)]
 pins={str(p.relative_to(ROOT)):sha(p)for p in files};artifacts={str(p.relative_to(ROOT)):sha(p)for p in(ram_path,sram_path)}
 rows=[];guards=[];visits=Counter()
 for aux in(0,44):
  sr=bytearray(sram);prepared=[]
  for address,value in[(0x6082,1),(0x6083,1),(0x63C0+167*12+8,132),(0x6081,aux)]:
   if sr[address-0x6000]!=value:prepared.append(dict(address=address,before=sr[address-0x6000],after=value));sr[address-0x6000]=value
  banks=tuple([v&31 for v in ram[0xDE:0xE1]]+[31])
  def memory():return ServiceMemory(rom,ram,sr,banks,read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  left,right=memory(),memory();r=NMIRegisters(a=17,x=31,y=63,p=32,sp=255,pc=0xE066);c=MPU(memory=left)
  for k,v in regs(r).items():setattr(c,k,v)
  initial=regs(r);game=CityAuxiliaryGameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();session=game.readable_campaign(r)
  assert isinstance(co,CityAuxiliarySceneCoordinator)and co.external_callback is None
  assert isinstance(game.city_auxiliary_services(),CityAuxiliaryServices)
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
  assert word(0x63C0+167*12+8)==(900 if aux==0 else 1000)
  assert word(0x608C)==(9499 if aux==0 else 9399)
  assert word(0x6082)==237 and right[0x6F5D]==(10 if aux==0 else 8)
  assert any(x['kind']=='city_auxiliary_domestic'for x in co.calls)
  assert not session.pending
  record=game.city_auxiliary_record(4);assert record['official_byte1_name']is None and not record['tail_unused_or_padding_proved']
  rows.append(dict(case=f'actual-caller-frame34623-aux{aux}',completion_kind='main_E066_and_actual_NMI_IRQ_RTI_sequence',comparison='complete_sequence',
    initial_registers=initial,final_registers=regs(r),preparation=prepared,source_original_CPU_callbacks=0,source_IR_interpretation=False,
    main_updates=2,explicit_NMI_arrivals=2,explicit_IRQ_arrivals=irq_count,original_instructions=steps,RAM_bytes=2048,SRAM_bytes=8192,
    events=events,owner_counts=dict(Counter(x['kind']for x in co.calls)),final_fields=dict(city4=record,troops167=word(0x63C0+167*12+8),reserve4=word(0x608C),gold4=word(0x6082),budget=right[0x6F5D]),
    RAM_sha256=hashlib.sha256(bytes(right.ram)).hexdigest(),SRAM_sha256=hashlib.sha256(bytes(right.sram)).hexdigest()))
  print(json.dumps(dict(case=rows[-1]['case'],status='passed',instructions=steps,IRQ=irq_count)),flush=True)
 guards=['new_domestic_owner_selected_by_real_physical10_11_entry','source_callbacks_have_no_CPU_or_IR_fallback','opaque_city_field_names_remain_unclaimed']
 assert pins=={str(p.relative_to(ROOT)):sha(p)for p in files},'Source changed during verification; rerun afterfreeze'
 result=dict(schema='phase18-additive-city-auxiliary-main-NMI-IRQ-source-v1',status='passed',ROM_sha256=ROM_SHA256,
   source_sha256=pins,artifact_sha256=artifacts,rom_cpu_sequence_count=2,actual_caller_RTS_count=0,source_guard_case_count=len(guards),guards=guards,rows=rows,
   original_Native_internal_CPU_trace=False,source_original_CPU_callbacks=0,source_IR_interpretation=False,
   comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC=True,ordered_IO_banks_N163=True,idle_stack_included=True),
   limitations=['Main/NMI/IRQ event arrivals are explicit CPU fixtures, not Native frame timing.','Two main updates finish at original E066/RTI boundaries; they are not two actual caller RTS cases.','The native core proceeds farther with its own timing and different final strategy/budget/gold results; only matching recruitment event is cross-evidence.'])
 (OUT/'source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (OUT/'integration-executed-instructions.json').write_text(json.dumps(dict(instruction_count=len(visits),instructions=[dict(physical_bank=b,cpu=p,ROM_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visits.items())]),indent=2)+'\n')
 print(json.dumps(dict(status='passed',CPU_sequences=2,guards=len(guards))))
if __name__=='__main__':main()
