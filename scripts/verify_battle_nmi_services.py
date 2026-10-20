#!/usr/bin/env python3
"""Actual bank31 CPU versus independent readable NMI/IRQ/port services."""
import argparse,hashlib,json,random,sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from py65.devices.mpu6502 import MPU
from source.recovered.service_memory import ServiceMemory,IOReadUnavailable
from source.recovered.battle_nmi_services import BattleNMIServices,NMIRegisters,SCENE_ENTRIES
from source.recovered.officers import ROM_SHA256

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 out=ROOT/'analysis/phase10/nmi';out.mkdir(parents=True,exist_ok=True)
 rng=random.Random(0x10F800);counts=Counter();failures=[];examples=[];guards=[];callback_evidence=[];plans=[];plan_keys=set()
 def memory(ram,sram,buttons=(0,0),samples=None):
  return ServiceMemory(rom,ram,sram,banks=(6,12,13,31),controller_buttons=buttons,
          read_ports=samples or {0x2002:0,0x5800:127},repeat_read_ports=(0x2002,0x5800))
 def registers(r):return {k:getattr(r,k)for k in ('a','x','y','sp','p','pc')}
 def actual_callback(call):
  # Verification only: execute the unchanged external helper body in a CPU.
  # No original-opcode interpreter is imported by recovered source.
  r=call.registers;cpu=MPU(memory=call.memory)
  for key,value in asdict(r).items():setattr(cpu,key,value)
  for n in range(200000):
   if n and cpu.pc==call.return_pc and cpu.sp==call.expected_sp:
    for key in asdict(r):setattr(r,key,getattr(cpu,key))
    callback_evidence.append(dict(target=call.target,entry_banks=list(call.entry_banks),return_pc=call.return_pc,original_instructions=n))
    return {'status':'returned'}
   cpu.step()
  raise RuntimeError(f'Actual external callback budget target{call.target:04X} pc{cpu.pc:04X}')
 def oracle(m,r,entry,stop=0x200,hardware=None,external=None,limit=200000):
  cpu=MPU(memory=m)
  for key,value in asdict(r).items():setattr(cpu,key,value)
  if hardware=='nmi':cpu.nmi()
  elif hardware=='irq':cpu.irq()
  else:cpu.pc=entry
  for n in range(limit):
   if n and cpu.pc==stop:return cpu,n
   if external and external(cpu,m):continue
   cpu.step()
  raise RuntimeError(f'Original CPU budget at {cpu.pc:04X}')
 def compare(group,entry,ram,sram,r,buttons=(0,0),samples=None,mode='service',stop=0x200,source_callback=None,reference_callback=None):
  counts[group]+=1;src=memory(ram,sram,buttons,samples);ref=memory(ram,sram,buttons,samples);model=BattleNMIServices(src,source_callback)
  try:
   rr=NMIRegisters(**asdict(r))
   result=model.run_service(entry,rr)if mode=='service'else model.run_nmi(rr,hardware_entry=True)if mode=='nmi'else model.run_irq(rr,hardware_entry=True)
   assert result['status']=='returned',result
   cpu,n=oracle(ref,r,entry,stop,mode if mode!='service'else None,reference_callback)
   rd=[(hex(i),x,y)for i,(x,y)in enumerate(zip(src.ram,ref.ram))if x!=y]
   sd=[(hex(i+0x6000),x,y)for i,(x,y)in enumerate(zip(src.sram,ref.sram))if x!=y]
   assert not rd and not sd,(rd[:12],sd[:12])
   assert registers(rr)==registers(cpu),(registers(rr),registers(cpu))
   assert src.banks==ref.banks,(src.banks,ref.banks)
   assert src.io_writes==ref.io_writes,('IO writes',src.io_writes[:12],ref.io_writes[:12])
   assert src.io_reads==ref.io_reads,('IO reads',src.io_reads[:12],ref.io_reads[:12])
   assert src.ppu_register_bytes==ref.ppu_register_bytes
   key=(ram[0x78]&15,ram[0x7B])
   if mode=='nmi'and key not in plan_keys:
    plan_keys.add(key);plans.append(dict(scene=key[0],busy_before=key[1],original_instructions=n,
              source_calls=result['events'],port_writes=src.io_writes,port_reads=src.io_reads,
              full_RAM_SRAM_register_ports_equal=True,
              external_callback_policy='verification-only actual original CPU'if source_callback else'none required'))
   if len([x for x in examples if x['group']==group])<3:examples.append(dict(group=group,entry=entry,original_instructions=n,port_write_count=len(src.io_writes),registers=registers(rr)))
  except Exception as exc:failures.append(dict(group=group,entry=entry,error=f'{type(exc).__name__}: {exc}'))
 def seed():
  ram=bytearray(rng.randrange(256)for _ in range(2048));sram=bytearray(rng.randrange(256)for _ in range(8192));ram[0x1FE:0x200]=bytes((255,1))
  r=NMIRegisters(a=rng.randrange(256),x=rng.randrange(256),y=rng.randrange(256),sp=0xFD,p=rng.choice((0x20,0x21,0x66,0xE7)),pc=0x200)
  return ram,sram,r
 direct=[e for e in BattleNMIServices.FIXED if e not in (0xEE53,0xEEE6,0xE830,0xFB28)]
 for entry in direct:
  for case in range(32):
   ram,sram,r=seed();buttons=(rng.randrange(256),rng.randrange(256));compare('fixed_services_complete',entry,ram,sram,r,buttons)
 for value in (*range(0,256,4),255):
  ram,sram,r=seed();ram[0x7C]=value;compare('OAM_tail_aligned_and_FF',0xE830,ram,sram,r)
 for entry in (0xEE53,0xEEE6):
  for value in range(256):
   if entry==0xEE53 and value&15:continue
   ram,sram,r=seed();ram[0x7D]=0;ram[0x7E]=value;compare('PPU_queue_fixed_consumers',entry,ram,sram,r)
 for case in range(128):
  ram,sram,r=seed();samples={port:[rng.randrange(4)for _ in range(8)]for port in(0x4016,0x4017)}
  compare('controller_expansion_bits_raw_samples',0xE6C6,ram,sram,r,samples=samples)
 for value in range(1,16):
  ram,sram,r=seed();ram[0x7D]=0;ram[0x7E]=value;src=memory(ram,sram);ref=memory(ram,sram);model=BattleNMIServices(src)
  counts['PPU_queue_banked_tail_prefixes']+=1
  try:
   result=model.run_service(0xEE53,NMIRegisters(**asdict(r)));assert result['status']=='dependency'
   assert result['dependency']['category']=='external_call';target=model.pending.target;cpu,n=oracle(ref,r,0xEE53,target)
   assert registers(model.registers)==registers(cpu)and src.ram==ref.ram and src.sram==ref.sram and src.io_writes==ref.io_writes and src.banks==ref.banks
   examples.append(dict(group='PPU_queue_banked_tail_prefixes',flag7E=value,target=target,banks=src.banks,original_prefix_instructions=n,whole_banked_body_restored=False))
  except Exception as exc:failures.append(dict(group='PPU_queue_banked_tail_prefixes',flag7E=value,error=f'{type(exc).__name__}: {exc}'))
 for selector in range(256):
  for entry in (0xF237,0xF24B,0xF25F,0xF266):
   ram,sram,r=seed();r.y=selector;compare('mapper_all_raw_selectors',entry,ram,sram,r)
 for mode in range(256):
  for row in (0,1,2,3):
   ram,sram,r=seed();ram[0x60]=mode;ram[0x63]=row;r.p&=~4
   compare('IRQ_all_mode_bytes_and_rows',0xFB2D,ram,sram,r,mode='irq')
 for scene in(0,1):
  for case in range(128):
   ram,sram,r=seed();ram[0x78]=scene;ram[0x7B]=0;ram[0x69]=0
   ram[0xDE:0xE4]=bytes((38,44,45,38,44,45));compare('NMI_scene0_1_complete',0xF800,ram,sram,r,mode='nmi',buttons=(case,255-case))
 # Native snapshot data are used only as explicit synchronous CPU fixtures.
 # Core video timing is not simulated and IRQ configuration69=0 is disclosed.
 prefixes={2:'analysis/phase5/runtime/city-info/menu-1',3:'analysis/runtime/phase3/attack-intro-7',
           4:'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu',
           5:'analysis/duel_fsm/runtime/injected-core/fixture-state-16',
           6:'analysis/runtime/title',7:'analysis/runtime/ruler-confirm',8:'analysis/phase6/runtime/unification-ending/ending'}
 for scene,prefix in prefixes.items():
  prefix=ROOT/prefix
  assert Path(str(prefix)+'-ram.bin').is_file(),prefix
  ram=bytearray(Path(str(prefix)+'-ram.bin').read_bytes());sram=bytearray(Path(str(prefix)+'-sram.bin').read_bytes())
  ram[0xDE:0xE4]=bytes((38,44,45,38,44,45));ram[0x78]=scene;ram[0x7B]=0;ram[0x69]=0
  r=NMIRegisters(a=0x51,x=0xA5,y=0xC7,p=0x20,sp=0xFD,pc=0x200)
  compare('complete_NMI_with_actual_external_ROM_callbacks',0xF800,ram,sram,r,mode='nmi',source_callback=actual_callback)
 # Busy reentry has one authentic external audio helper, and no normal tail
 # RNG/counter bookkeeping. This is not a stand-alone source audio result.
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
 for busy in(1,255):
  ram=bytearray(Path(str(prefix)+'-ram.bin').read_bytes());sram=bytearray(Path(str(prefix)+'-sram.bin').read_bytes())
  ram[0xDE:0xE4]=bytes((38,44,45,38,44,45));ram[0x7B]=busy;ram[0x69]=0
  compare('busy_NMI_actual_audio_callback',0xF800,ram,sram,NMIRegisters(pc=0x200),mode='nmi',source_callback=actual_callback)
 # Strict prefixes stop at the first actual banked service, then can resume
 # only when a real callback has returned its true stack. No service is stubbed.
 for scene,prefix in prefixes.items():
  prefix=ROOT/prefix;ram=bytearray(Path(str(prefix)+'-ram.bin').read_bytes());sram=bytearray(Path(str(prefix)+'-sram.bin').read_bytes())
  ram[0xDE:0xE4]=bytes((38,44,45,38,44,45));ram[0x78]=scene;ram[0x7B]=0;ram[0x69]=0
  r=NMIRegisters(a=17,x=51,y=99,sp=0xFD,p=0x20,pc=0x200);src=memory(ram,sram);ref=memory(ram,sram)
  model=BattleNMIServices(src);result=model.run_nmi(NMIRegisters(**asdict(r)),hardware_entry=True)
  counts['strict_scene_prefix_at_real_callback']+=1
  try:
   assert result['status']=='dependency'and result['dependency']['category']=='external_call'
   target=model.pending.target;cpu,n=oracle(ref,r,0xF800,target,'nmi')
   assert src.ram==ref.ram and src.sram==ref.sram and src.io_writes==ref.io_writes and registers(model.registers)==registers(cpu)
   saved=(bytes(src.ram),bytes(src.sram),asdict(model.registers),list(src.io_writes));again=model.resume()
   assert again['status']=='dependency'and saved==(bytes(src.ram),bytes(src.sram),asdict(model.registers),list(src.io_writes))
   model.callbacks=actual_callback;result=model.resume();assert result['status']=='returned'
   for n in range(200000):
    if cpu.pc==0x200:break
    cpu.step()
   else:raise RuntimeError('Original strict resume budget')
   assert src.ram==ref.ram and src.sram==ref.sram and src.io_writes==ref.io_writes and src.io_reads==ref.io_reads and registers(model.registers)==registers(cpu)
   examples.append(dict(group='strict_scene_prefix_at_real_callback',scene=scene,first_dependency=target,unchanged_retry=True,resumed_with_actual_ROM_callback=True))
  except Exception as exc:failures.append(dict(group='strict_scene_prefix_at_real_callback',scene=scene,error=f'{type(exc).__name__}: {exc}'))
 # The software IRQ chain is executed explicitly while NMI is waiting. Only
 # real recovered IRQ handlers clear0062; no source set-ready assignment occurs.
 for irq_mode,row in [(6,0),(9,0),*[(kind,row)for kind in(1,7)for row in range(4)]]:
  ram,sram,r=seed();ram[0x78]=0;ram[0x7B]=0;ram[0x69]=128;ram[0x61]=irq_mode;ram[0x63]=row
  ram[0xDE:0xE4]=bytes((38,44,45,38,44,45));src=memory(ram,sram);ref=memory(ram,sram);model=BattleNMIServices(src)
  result=model.run_nmi(NMIRegisters(**asdict(r)),hardware_entry=True);counts['NMI_wait_resumed_by_actual_recovered_IRQ_chain']+=1
  try:
   assert result['status']=='dependency'and result['dependency']['category']=='IRQ_software_flag'
   cpu=MPU(memory=ref)
   for k,v in asdict(r).items():setattr(cpu,k,v)
   cpu.nmi()
   for n in range(200000):
    if n and cpu.pc==0xFB28 and cpu.a==128:break
    cpu.step()
   else:raise RuntimeError('Original IRQ wait prefix budget')
   assert registers(model.registers)==registers(cpu)and src.ram==ref.ram and src.io_writes==ref.io_writes
   chain=[]
   while src[0x62]!=0:
    assert len(chain)<8;before_mode=src[0x60];before_row=src[0x63];sp=cpu.sp
    irq=BattleNMIServices(src);returned=irq.run_irq(model.registers,hardware_entry=True);assert returned['status']=='returned'
    cpu.irq()
    for n in range(200000):
     if n and cpu.pc==0xFB28 and cpu.sp==sp:break
     cpu.step()
    else:raise RuntimeError('Original IRQ chain budget')
    assert registers(model.registers)==registers(cpu)and src.ram==ref.ram and src.io_writes==ref.io_writes
    chain.append(dict(mode=before_mode,row=before_row,flag62_after=src[0x62],original_instructions=n))
   assert model.resume()['status']=='returned'
   for n in range(200000):
    if cpu.pc==0x200:break
    cpu.step()
   else:raise RuntimeError('Original NMI final resume budget')
   assert registers(model.registers)==registers(cpu)and src.ram==ref.ram and src.sram==ref.sram and src.io_writes==ref.io_writes and src.io_reads==ref.io_reads
   examples.append(dict(group='NMI_wait_resumed_by_actual_recovered_IRQ_chain',initial_mode=irq_mode,initial_row=row,IRQ_services=chain))
  except Exception as exc:failures.append(dict(group='NMI_wait_resumed_by_actual_recovered_IRQ_chain',mode=irq_mode,row=row,error=f'{type(exc).__name__}: {exc}'))
 # A separate accepted NMI can interrupt a live source context at a banked
 # service boundary. Share its memory/registers; keep both generator frames.
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
 ram=bytearray(Path(str(prefix)+'-ram.bin').read_bytes());sram=bytearray(Path(str(prefix)+'-sram.bin').read_bytes())
 ram[0xDE:0xE4]=bytes((38,44,45,38,44,45));ram[0x78]=3;ram[0x7B]=0;ram[0x69]=0
 r=NMIRegisters(pc=0x200);src=memory(ram,sram);ref=memory(ram,sram);outer=BattleNMIServices(src)
 counts['nested_busy_NMI_and_original_outer_resume']+=1
 try:
  blocked=outer.run_nmi(NMIRegisters(**asdict(r)),hardware_entry=True);assert blocked['dependency']['category']=='external_call'
  target=outer.pending.target;cpu,n=oracle(ref,r,0xF800,target,'nmi');saved_sp=cpu.sp
  inner=BattleNMIServices(src,actual_callback);assert inner.run_nmi(outer.registers,hardware_entry=True)['status']=='returned'
  cpu.nmi()
  for n in range(200000):
   if n and cpu.pc==target and cpu.sp==saved_sp:break
   cpu.step()
  else:raise RuntimeError('Original nested NMI budget')
  assert registers(outer.registers)==registers(cpu)and src.ram==ref.ram and src.io_writes==ref.io_writes
  outer.callbacks=actual_callback;assert outer.resume()['status']=='returned'
  for n in range(200000):
   if cpu.pc==0x200:break
   cpu.step()
  else:raise RuntimeError('Original outer resume after nested NMI budget')
  assert registers(outer.registers)==registers(cpu)and src.ram==ref.ram and src.sram==ref.sram and src.io_writes==ref.io_writes and src.io_reads==ref.io_reads
  examples.append(dict(group='nested_busy_NMI_and_original_outer_resume',interrupted_banked_service=target,busy_NMI_used_separate_live_context=True,outer_caller_stack_preserved=True))
 except Exception as exc:failures.append(dict(group='nested_busy_NMI_and_original_outer_resume',error=f'{type(exc).__name__}: {exc}'))
 # Explicit hardware read dependencies are resumable without resetting the
 # transaction. These are boundary guards, separate from original CPU cases.
 for entry,missing in ((0xE6C6,0x4016),(0xE70E,0x2002),(0xFB0B,0x2002)):
  ram,sram,r=seed();src=ServiceMemory(rom,ram,sram,banks=(6,12,13,31));model=BattleNMIServices(src)
  blocked=model.run_service(entry,r);assert blocked['status']=='dependency'and blocked['dependency']['address']==missing
  src.controller_buttons=(1,128);src.read_ports[0x2002]=__import__('collections').deque([0]);src.repeat_read_ports.add(0x2002)
  assert model.resume()['status']=='returned';guards.append(dict(category='explicit_input_missing_then_supplied',entry=entry,address=missing,returned_after_real_input=True))
 ram,sram,r=seed();src=memory(ram,sram,samples={0x2002:[64,0]});model=BattleNMIServices(src);blocked=model.run_service(0xFB0B,r)
 assert blocked['status']=='dependency'and blocked['dependency']['category']=='PPUSTATUS_sprite_hit';assert model.resume()['status']=='returned'
 guards.append(dict(category='PPUSTATUS_bit6_wait_then_explicit_clear_sample',returned_after_real_input=True))
 ram,sram,r=seed();r.pc=0x200;r.p&=~4;src=memory(ram,sram,samples={0x5800:[0,127]});model=BattleNMIServices(src)
 blocked=model.run_irq(r,hardware_entry=True);assert blocked['dependency']['category']=='IRQ_counter_not_terminal'
 assert model.resume()['dependency']['category']=='IRQ_counter_not_terminal';guards.append(dict(category='IRQ_nonterminal_counter_irreversible_original_trap',automatic_ack=False))
 ram,sram,r=seed();ram[0x7C]=1;model=BattleNMIServices(memory(ram,sram));blocked=model.run_service(0xE830,r)
 assert blocked['dependency']['category']=='unaligned_OAM_cursor';guards.append(dict(category='unaligned_OAM_original_nonterminating_loop',automatic_completion=False))
 # Clearing62 during an IRQ is insufficient while its own PPU service has
 # not returned. NMI must preserve the live IRQ stack rather than pop it.
 ram,sram,r=seed();ram[0x78]=0;ram[0x7B]=0;ram[0x69]=128;ram[0x61]=5
 src=memory(ram,sram,samples={0x2002:[0,0],0x5800:127});src.repeat_read_ports.discard(0x2002)
 model=BattleNMIServices(src);assert model.run_nmi(r,hardware_entry=True)['dependency']['category']=='IRQ_software_flag'
 irq=BattleNMIServices(src);assert irq.run_irq(model.registers,hardware_entry=True)['dependency']['category']=='hardware_read'
 assert src[0x62]==0;saved=(bytes(src.ram),bytes(src.sram),asdict(model.registers))
 assert model.resume()['status']=='dependency'and saved==(bytes(src.ram),bytes(src.sram),asdict(model.registers))
 src.read_ports[0x2002].append(0);assert irq.resume()['status']=='returned';assert model.resume()['status']=='returned'
 guards.append(dict(category='NMI_cannot_resume_until_actual_IRQ_RTI_even_if62_zero',NMI_stack_preserved=True))
 for value in range(256):
  if value&15<9:continue
  ram,sram,r=seed();ram[0x78]=value;ram[0x7B]=0;ram[0x69]=0;model=BattleNMIServices(memory(ram,sram));blocked=model.run_nmi(r,hardware_entry=True)
  assert blocked['status']=='dependency'and blocked['dependency']['category']=='unproven_NMI_scene'
  assert model.resume()['status']=='dependency';guards.append(dict(category='unproven_masked_scene_rejected',raw=value,masked=value&15))
 report={'status':'passed'if not failures else'failed','rom_sha256':ROM_SHA256,'rom_cpu_case_count':sum(counts.values()),'counts':dict(counts),
    'failed_count':len(failures),'failures':failures,'examples':examples,'source_guard_case_count':len(guards),'guards':guards,
    'actual_external_ROM_callback_count':len(callback_evidence),'actual_external_ROM_callback_evidence':callback_evidence,
    'source_fixture_stub_callback_count':0,
    'comparison_contract':'All2KiBRAM/all8KiBSRAM, A/X/Y/P/SP/PC, PRG mapping, explicit port read/write order and PPU command bytes; no CPU cycles or NES frame timing.',
    'source_sha256':hashlib.sha256((ROOT/'source/recovered/battle_nmi_services.py').read_bytes()).hexdigest(),
    'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'dependency_source_sha256':{name:hashlib.sha256((ROOT/'source/recovered'/name).read_bytes()).hexdigest()for name in ('service_memory.py','mapped_memory.py')},
    'limits':['No native-core frames are added by this CPU verifier.','Explicit PPU/controller/IRQ port samples are fixture inputs, not synthesized readiness or hardware timing.','External scene/audio services require real callbacks; missing callbacks remain pending.']}
 (out/'scene-call-plans.json').write_text(json.dumps({'rom_sha256':ROM_SHA256,'plans':plans,
           'scope':'Original outer NMI control and readable fixed services; banked bodies in these seven scene fixtures execute unchanged bytes only inside the verifier.'},ensure_ascii=False,indent=2)+'\n')
 (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ('status','rom_cpu_case_count','counts','failed_count')},ensure_ascii=False));print(json.dumps(failures[:8],ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
