#!/usr/bin/env python3
"""OriginalCPU comparison of actual scene setup and banked display loaders."""
import argparse,hashlib,json,random,sys
from collections import Counter,deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.scene_initialization import SceneInitialization
from source.recovered.scene_shared_services import SceneSharedServices,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.game_engine import GameEngine
SCOPE=[*range(0x1B4),*range(0x200,0x800)]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 counts=Counter();failures=[];samples=[];guards=[];visited=Counter();rng=random.Random(0x11BACC);externalCPU=[]
 base=ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-entry';ram=Path(str(base)+'-ram.bin').read_bytes();sram=Path(str(base)+'-sram.bin').read_bytes()
 def fresh(pair=23):
  b=PortBus(rom);b.ram[:]=ram;b.sram[:]=sram;b.banks=[16,pair,pair+1,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xE1:0xE4]=bytes([48,pair+32,pair+33]);b.ram[0x1FE:0x200]=bytes([255,1]);return b
 def compare(group,b,entry,meta,*,setup=False,source_callback=None):
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0},repeat_read_ports=(0x2002,))
  game=GameEngine(m,rom=rom,mapped=True);callback=game.readable_scene_rules()
  r=NMIRegisters(a=meta.get('a',17),x=meta.get('x',31),y=meta.get('y',63),p=32,sp=253,pc=entry)
  controller=SceneInitialization(m,rom,callbacks=callback);cpu=MPU(memory=b,pc=entry);cpu.a=r.a;cpu.x=r.x;cpu.y=r.y;cpu.p=r.p;cpu.sp=r.sp;b.cpu=cpu;b.record_ports=True
  try:
   if setup:result=controller.run_setup(entry,r);stop=0xE066
   elif entry in controller.FIXED:result=controller.run_service(entry,r);stop=0x200
   else:result=controller.banked_graphics(ServiceCall(entry,0x200,'banked_service',r,m,tuple(b.banks),255));stop=0x200
   assert result['status']=='returned',result
   for n in range(500000):
    if cpu.pc==stop:break
    b.pc=cpu.pc;b.step_no=n;origin=b.origin(cpu.pc)
    if origin:visited[(origin[0],cpu.pc,origin[1]+16)]+=1
    cpu.step()
   else:raise RuntimeError(f'Original setup budget at ${cpu.pc:04X}')
   diff=[(hex(v),b.ram[v],m.ram[v])for v in SCOPE if b.ram[v]!=m.ram[v]]
   rd=[(k,getattr(cpu,k),getattr(r,k))for k in ('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not diff and bytes(b.sram)==bytes(m.sram),diff[:12];assert not rd,rd
   assert b.ports==m.io_writes,(b.ports[:10],m.io_writes[:10],len(b.ports),len(m.io_writes));assert b.banks==m.banks
   counts[group]+=1
   if len([v for v in samples if v['group']==group])<6:samples.append(dict(group=group,entry=entry,inputs=meta,instructions=n,ports=len(m.io_writes),registers=vars(r).copy()))
  except Exception as exc:
   failures.append(dict(group=group,entry=entry,inputs=meta,error=str(exc)))
   if len(failures)<=10:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 for entry in (0xECBF,0xECEE,0xE4DA,0xE370,0xE51F):
  for mode in (0,1,2)if a.quick else range(3):
   b=fresh();compare('fixed_display_reset_chr_and_palette',b,entry,{'a':mode})
 for entry in (0xA015,0xA01B,0xA045):
  for mode in range(3 if a.quick else(6 if entry==0xA045 else 14)):
   b=fresh(29);b.ram[0]=mode;compare('banked_palette_chr_IRQ_configuration',b,entry,{'a':mode,'mode':mode})
 for city in range(3 if a.quick else 30):
  b=fresh(23);b.ram[0x50E]=city;compare('four_map_descriptors',b,0xA027,{'city':city})
 for pointer in (0x400,0x8FFE,0x90FC):
  b=fresh(23);b.ram[0xA:0xC]=pointer.to_bytes(2,'little');b.ram[0:2]=bytes([0,32]);compare('complete1024_byte_nametable_copy',b,0xA003,{'pointer':pointer})
 # Constructed encoded game-data fixture, separate from untouched ROM data.
 for count in(1,2,255):
  b=fresh(23);b.ram[0xA:0xC]=bytes([0,4]);b.ram[0:2]=bytes([0,32]);packet=bytes([254,1,2,254,count,9,3,254,0]);b.ram[0x400:0x400+len(packet)]=packet
  compare('marker_run_length_game_data',b,0xA000,{'run_count':count})
 for scene_type in range(2 if a.quick else 7):
  b=fresh(23);b.ram[0x544]=scene_type;b.ram[0:2]=bytes([0,32]);compare('attack_background_two_full_pages',b,0xA024,{'scene_type':scene_type})
 for left in(0,1,128):
  for right in(0,1,128):
   b=fresh();b.ram[0x7A]=7;b.ram[0x4AB:0x4AD]=bytes([left,right]);compare('full_global_duel_setup_with_pure_source_callees',b,0xE2E8,{'left_control':left,'right_control':right},setup=True)
 for kind in range(2 if a.quick else 7):
  b=fresh();b.ram[0x7A]=5;b.ram[0x544]=kind;compare('full_global_attack_setup_with_pure_source_callees',b,0xE22F,{'scene_type':kind},setup=True)
 for state in(0,)if a.quick else(0,3,11):
  b=fresh();b.ram[0x7A]=3;b.ram[0x500]=state
  compare('full_global_battle_setup_with_pure_source_callees',b,0xE18B,{'battle_state':state},setup=True)
 # Missingstatus pauses after exactly one2000 write, without pointer/data ACK.
 b=fresh();m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));controller=SceneInitialization(m,rom);r=NMIRegisters(sp=253,pc=0xA003)
 call=ServiceCall(0xA003,0x200,'banked_service',r,m,tuple(b.banks),255);result=controller.banked_graphics(call)
 assert result['status']=='dependency' and r.sp==253 and r.pc==0xA21A and m[0xA]==b.ram[0xA]
 before=list(m.io_writes);assert controller.banked_graphics(call)['status']=='dependency'and m.io_writes==before
 m.read_ports[0x2002]=deque([0]);result=controller.banked_graphics(call);assert result['status']=='returned'and r.pc==0x200 and r.sp==255
 guards.append('raw_background_wait_preserves_pointer_and_real_stack_then_resumes')
 out=ROOT/'analysis/phase11/initialization';out.mkdir(parents=True,exist_ok=True)
 report=dict(status='passed'if not failures else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,samples=samples,guards=guards,
             compared_RAM_addresses=SCOPE,compared_SRAM_bytes=8192,complete_registers_ports_banks=True,free_stack_residue_excluded=True,source_original_CPU_callbacks=0,source_IR_interpretation=False,
             source_sha256=hashlib.sha256((ROOT/'source/recovered/scene_initialization.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),dependency_source_sha256={v:hashlib.sha256((ROOT/'source/recovered'/v).read_bytes()).hexdigest()for v in('scene_shared_services.py','scene_coordinator.py','game_engine.py','battle_scene_controller.py','attack_scene_controller.py','duel_scene_controller.py','battle_setup_ai.py','battle_background_initialization.py')})
 (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(visited.items())],indent=2)+'\n')
 print(json.dumps({k:report[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
