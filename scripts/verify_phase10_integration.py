#!/usr/bin/env python3
"""Original CPU checks of shared presentation services and full tactic bodies."""
import argparse,hashlib,json,sys
from collections import Counter
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.battle_nmi_services import ServiceCall
RAM=[0x12,0x50,0x7C,0x7D,0x7E,0xA4,0xA5,*range(0x30,0x33),*range(0x100,0x120),*range(0x1B0,0x1B4),*range(0x200,0x800)]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'));a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 base=ROOT/'analysis/phase9/runtime/tactic-09-levelup/cast-confirmation'
 bram=Path(str(base)+'-ram.bin').read_bytes();bsram=Path(str(base)+'-sram.bin').read_bytes()
 counts=Counter();failures=[];samples=[];guards=[];native=[]
 def fresh():
  b=PortBus(rom);b.ram[:]=bram;b.sram[:]=bsram;b.banks=[6,12,13,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xDE:0xE4]=bytes([38,44,45,38,44,45]);b.ram[0x1FE:0x200]=bytes([255,1]);b.ram[0x7C]=0
  b.ram[0x500]=5;b.ram[0x504]=128;b.ram[0x509]=1;b.ram[0x50A]=10;b.ram[0x505]=16;b.ram[0x5E]=0
  b.ram[0x300]=b.ram[0x304]=255;b.ram[0x7E]=0;b.ram[0x4C8]=0
  b.ram[0x310:0x314]=bytes([255]*4);return b
 def source_game(b):
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0},repeat_read_ports=(0x2002,),controller_buttons=(0,0))
  return GameEngine(m,rom=rom,mapped=True,data_window_bank=6)
 def compare(kind,b,entry,call,meta,ram_scope=RAM):
  game=source_game(b);service=game.presentation_rules();cpu=MPU(memory=b,pc=entry);cpu.sp=0xFD;b.cpu=cpu;b.record_ports=True
  try:
   result=call(service)
   for n in range(500000):
    if cpu.pc==0x200:break
    b.pc=cpu.pc;b.step_no=n;cpu.step()
   else:raise RuntimeError(f'Original budget at {cpu.pc:04X}')
   m=game.memory;rd=[(hex(v),b.peek(v),m[v])for v in ram_scope if b.peek(v)!=m[v]]
   sd=[(hex(0x6000+i),x,y)for i,(x,y)in enumerate(zip(b.sram,m.sram))if x!=y]
   assert not rd and not sd,(rd[:12],sd[:12]);assert b.ports==m.io_writes,(len(b.ports),len(m.io_writes),b.ports[:12],m.io_writes[:12])
   assert b.banks==m.banks;counts[kind]+=1
   if sum(v['kind']==kind for v in samples)<12:samples.append(dict(kind=kind,input=meta,entry=entry,original_instructions=n,result=result))
  except Exception as exc:
   failures.append(dict(kind=kind,input=meta,error=str(exc)))
   if len(failures)<=6:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 for cursor in(0,255):
  for progress in(0,255):
   for button in(0,1,2,255):
    for blink in(0,16):
     b=fresh();b.ram[0x501]=5;b.ram[0x304]=cursor;b.ram[0x300]=progress;b.ram[0x81]=button;b.ram[0x5E]=blink
     compare('player_confirm_actual_services',b,0xAA2E,lambda s:s.player_tactic_body(),[cursor,progress,button,blink])
 for tactic in range(16):
  for rng in(0,17,63,127):
   for hp in(1,99):
    b=fresh();b.ram[0x501]=6;b.ram[0x543]=tactic;b.ram[0x50]=rng
    b.sram[0x3C0+12*b.ram[0x665]]=hp
    compare('all16_effects_full_death_refresh_and_caller',b,0xAA6C,lambda s:s.player_tactic_body(),[tactic,rng,hp])
 for tactic in range(16):
  for cursor in(0,18,19):
   for failed in(0,255):
    for dead in(255,22):
     b=fresh();b.ram[0x501]=7;b.ram[0x50B]=cursor;b.ram[0x543]=tactic;b.ram[0x544]=failed;b.ram[0x432]=dead;b.ram[0x42C:0x42E]=bytes([99,0])
     compare('all16_result_scan_and_actual_actor_panel',b,0xAAA7,lambda s:s.player_tactic_body(),[tactic,cursor,failed,dead])
 for sub,entry in[(8,0xAB2A),(9,0xAB52),(10,0xAB90)]:
  for ready in(0,1):
   for button in(0,1,2,255):
    for change in(0,1):
     for second in(0,255):
      b=fresh();b.ram[0x501]=sub;b.ram[0x81]=button;b.ram[0x300]=255 if ready else 0;b.ram[0x42D]=second
      address=0x63C0+12*b.ram[0x66E];b.ram[0x52C]=(b.peek(address+11)&240)-(16 if change else 0);b.ram[0x52E]=(b.peek(address+1)-5)&255
      compare('confirmation_upgrade_audio_and_full_cursor_return',b,entry,lambda s:s.player_tactic_body(),[sub,ready,button,change,second])
 # Full hardware-entry NMI with all reached software callbacks independent.
 # Mode0/1 have fixed services; busy-reentry actually runs recovered audio.
 for busy in(0,1):
  for scene in(0,1,3,4):
   if not busy and scene not in(0,1):continue
   for timer in(0,255):
    b=fresh();b.ram[0x7B]=busy;b.ram[0x78]=scene;b.ram[0x69]=0;b.ram[0x5E]=timer;b.ram[0x5F]=127;b.ram[0xA5]=0x4C
    g=source_game(b);s=g.presentation_rules();r=NMIRegisters(a=17,x=31,y=63,p=32,sp=0xFD,pc=0xE221)
    cpu=MPU(memory=b,pc=0xE221);cpu.a=r.a;cpu.x=r.x;cpu.y=r.y;cpu.p=r.p;cpu.sp=r.sp;b.cpu=cpu;b.record_ports=True
    try:
     result=g.tick_nmi_services(r,hardware_entry=True);assert result['status']=='returned',result
     cpu.nmi()
     for n in range(200000):
      if cpu.pc==0xE221:break
      b.pc=cpu.pc;b.step_no=n;cpu.step()
     else:raise RuntimeError('OriginalNMI budget')
     scope=[*range(0x120),*range(0x200,0x800)]
     rd=[(hex(v),b.peek(v),g.memory[v])for v in scope if b.peek(v)!=g.memory[v]]
     assert not rd and bytes(b.sram)==bytes(g.memory.sram),rd[:12]
     assert b.ports==g.memory.io_writes,(len(b.ports),len(g.memory.io_writes))
     assert all(getattr(cpu,k)==getattr(r,k)for k in('a','x','y','p','sp','pc'))
     counts['full_NMI_with_pure_software_callbacks']+=1
     samples.append(dict(kind='full_NMI_with_pure_software_callbacks',input=[busy,scene,timer],original_instructions=n,source_original_CPU_callbacks=0,result=result['status']))
    except Exception as exc:failures.append(dict(kind='pure_NMI',input=[busy,scene,timer],error=str(exc)))
 # Identified scroll callee through the same production callback used by NMI.
 # Complete callee RTS/register protocol, not an active battle controller/NMI.
 for target in(0xA00C,0xA00F):
  for x,y in((0,0),(248,232),(255,239),(264,256)):
   b=fresh();b.banks=[2,23,24,31];b.ram[0x7E]=0;b.ram[0xA8:0xAA]=bytes([0,4]);b.ram[0x400:0x500]=bytes(i%120 for i in range(256))
   b.ram[0x8E:0x92]=bytes([x&255,x>>8,y&255,y>>8]);b.ram[0x92:0x96]=bytes([255]*4);b.ram[0x9C]=240
   b.ram[0x600:0x628]=bytes([255]*40);g=source_game(b);s=g.presentation_rules()
   r=NMIRegisters(a=17,x=31,y=63,p=32,sp=0xFD,pc=target)
   call=ServiceCall(target=target,return_pc=0x200,kind='banked_service',registers=r,memory=g.memory,entry_banks=tuple(b.banks),expected_sp=255)
   cpu=MPU(memory=b,pc=target);cpu.a=r.a;cpu.x=r.x;cpu.y=r.y;cpu.p=r.p;cpu.sp=r.sp;b.cpu=cpu;b.record_ports=True
   try:
    result=s.source_callback(call);assert result['status']=='returned' and r.pc==0x200 and r.sp==255,result
    for n in range(200000):
     if cpu.pc==0x200:break
     b.pc=cpu.pc;b.step_no=n;cpu.step()
    else:raise RuntimeError('Original scroll budget')
    scope=[*range(0x120),*range(0x140,0x1B4),*range(0x200,0x800)]
    assert all(b.peek(v)==g.memory[v]for v in scope) and bytes(b.sram)==bytes(g.memory.sram)
    assert b.ports==g.memory.io_writes and b.banks==g.memory.banks
    assert all(getattr(cpu,k)==getattr(r,k)for k in('a','x','y','p','sp','pc'))
    counts['scroll_pure_source_callback_full_return']+=1
   except Exception as exc:failures.append(dict(kind='scroll_source_callback',input=[target,x,y],error=str(exc)))
 # Explicit source-only ownership/contracts, not more original CPU cases.
 b=fresh();g=source_game(b);s=g.presentation_rules()
 for label,call in [('invalid_body_state',lambda:s.player_tactic_body()),('no_IO_bus',lambda:GameEngine.from_snapshot(base,rom=rom,mapped=True,data_window_bank=6).presentation_rules())]:
  if label=='invalid_body_state':g.memory[0x500]=0
  try:call()
  except ValueError:guards.append(label)
  else:raise AssertionError(label+' not rejected')
 # An unresolved controller and a partially serviced PPU request must keep
 # the actual callee stack. Resumption may pop it only after a real return.
 b=fresh();g=source_game(b);s=g.presentation_rules();r=NMIRegisters(sp=0xFD,pc=0xA028)
 call=ServiceCall(0xA028,0x200,'scene_controller',r,g.memory,tuple(b.banks),255)
 before=bytes(g.memory.ram)+bytes(g.memory.sram);result=s.source_callback(call)
 assert result['status']=='dependency' and r.pc==0xA028 and r.sp==0xFD and before==bytes(g.memory.ram)+bytes(g.memory.sram) and not g.memory.io_writes
 guards.append('unknown_scene_controller_keeps_real_call_stack')
 b=fresh();b.banks=[2,29,30,31];b.ram[0x7E]=1;b.ram[0x304]=0;b.ram[0x303]=b.ram[0x308]=b.ram[0x30C]=b.ram[0x5E]=0
 b.ram[0x31C:0x31F]=bytes([32,36,7]);b.ram[0x34C:0x34F]=bytes([0,36,8]);g=source_game(b);s=g.presentation_rules()
 g.memory.read_ports[0x2002]=deque([0]);g.memory.repeat_read_ports.clear();r=NMIRegisters(sp=0xFD,pc=0xA000)
 call=ServiceCall(0xA000,0x200,'banked_service',r,g.memory,tuple(b.banks),255)
 result=s.source_callback(call);assert result['status']=='dependency' and r.pc==0xA000 and r.sp==0xFD and g.memory[0x304]==0 and g.memory[0x7E]==1
 writes=list(g.memory.io_writes);assert s.source_callback(call)['status']=='dependency' and g.memory.io_writes==writes
 g.memory.read_ports[0x2002]=deque([0]);g.memory.repeat_read_ports.add(0x2002)
 result=s.source_callback(call);assert result['status']=='returned' and r.pc==0x200 and r.sp==255 and g.memory[0x304]==1
 assert [v for v in g.memory.io_writes if v['address']==0x2007]==[dict(address=0x2007,value=7),dict(address=0x2007,value=8)]
 guards.append('partial_text_callback_keeps_stack_until_actual_return')
 result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,actual_ROM_CPU_comparison_count=sum(counts.values()),counts=dict(counts),source_guard_count=len(guards),source_guards=guards,failures=failures,samples=samples,
             declared_RAM_addresses=RAM,all_SRAM_compared_bytes=8192,ordered_ports_compared=True,banks_compared=True,CPU_scratch_and_stack_excluded_for_tactic_bodies=True,
             complete_NMI_return_registers_compared=True,NMI_original_CPU_callbacks=0,native_core_field_comparison_count=len(native),native_core_field_cases=native,
             source_original_code_calls=0,new_service_IR_interpretation=False,
             source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in ('source/recovered/game_engine.py','source/recovered/battle_presentation_services.py','source/recovered/tactic_presentation_effects.py','source/recovered/service_memory.py','source/recovered/text_services.py','source/recovered/audio_services.py','source/recovered/battle_graphics_services.py','source/recovered/battle_nmi_services.py','source/recovered/scroll_graphics_services.py')})
 out=ROOT/'analysis/phase10/source-integration.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','actual_ROM_CPU_comparison_count','source_guard_count','counts')},ensure_ascii=False))
 if failures:print(json.dumps(failures[:12],ensure_ascii=False));raise SystemExit(1)
if __name__=='__main__':main()
