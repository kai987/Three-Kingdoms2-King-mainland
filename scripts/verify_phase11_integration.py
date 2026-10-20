#!/usr/bin/env python3
"""Check the public readable-scene composition against the original CPU."""
import argparse,hashlib,json,sys
from pathlib import Path
from collections import Counter,deque
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
SCOPE=[*range(0x1B4),*range(0x200,0x800)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'));a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 base=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(base)+'-ram.bin').read_bytes();sram=Path(str(base)+'-sram.bin').read_bytes()
 counts=Counter();rows=[];failures=[];guards=[]
 def fresh(pair=12):
  b=PortBus(rom);b.ram[:]=ram;b.sram[:]=sram;b.banks=[17,pair,pair+1,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xDE:0xE4]=bytes([49,pair+32,pair+33,49,pair+32,pair+33]);b.ram[0x1FE:0x200]=bytes([0x67,0x24]);b.ram[0x300]=b.ram[0x304]=255;b.ram[0x310:0x314]=bytes([255]*4)
  b.ram[0x7C]=b.ram[0x7E]=b.ram[0x81]=0;b.ram[0x69]=0;return b
 def game(b,hardware=True):
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),**({'read_ports':{0x2002:0},'repeat_read_ports':(0x2002,),'controller_buttons':(0,0)}if hardware else{}))
  return GameEngine(m,rom=rom,mapped=True)
 def compare(label,b,entry,*,nmi=False,scene=None,allow_prefix=False):
  g=game(b);c=g.readable_scene_rules();r=NMIRegisters(a=17,x=31,y=63,p=32,sp=253,pc=entry);cpu=MPU(memory=b,pc=entry);b.cpu=cpu;b.record_ports=True
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  try:
   if nmi:result=g.tick_readable_nmi(r,hardware_entry=True);cpu.nmi();stop=entry
   elif scene is not None:result=g.tick_readable_scene(r,scene=scene);stop=0x2468
   else:result=c(ServiceCall(entry,0x2468,'real_caller_fixture',r,g.memory,tuple(b.banks),255));stop=0x2468
   prefix=allow_prefix and result['status']=='dependency'
   assert result['status']=='returned' or prefix,(result['status'],hex(r.pc),[(hex(v['target']),v['status'])for v in c.calls[-5:]])
   if prefix:stop=r.pc
   for n in range(500000):
    if cpu.pc==stop and(not prefix or cpu.sp==r.sp and b.banks==g.memory.banks):break
    b.pc=cpu.pc;b.step_no=n;cpu.step()
   else:raise RuntimeError(f'Original CPU budget ${cpu.pc:04X}')
   diff=[(hex(i),b.ram[i],g.memory.ram[i])for i in SCOPE if b.ram[i]!=g.memory.ram[i]]
   rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not diff and bytes(b.sram)==bytes(g.memory.sram),diff[:12];assert not rg,rg;assert b.ports==g.memory.io_writes,(b.ports[:8],g.memory.io_writes[:8],len(b.ports),len(g.memory.io_writes));assert b.banks==g.memory.banks
   counts[label]+=1;rows.append(dict(kind=label,entry=entry,comparison='strict_prefix'if prefix else'complete_return',original_instructions=n,source_callbacks=len(c.calls),source_original_CPU_callbacks=0,boundary_PC=r.pc,boundary_SP=r.sp))
  except Exception as exc:
   failures.append(dict(kind=label,entry=entry,error=str(exc)));print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 for scene in(0,1,3,4,5):
  for busy in(1,):
   b=fresh();b.ram[0x78]=scene;b.ram[0x7B]=busy;compare('full_busy_NMI_with_source_audio',b,0xE221,nmi=True)
 for scene in(0,1):
  b=fresh();b.ram[0x78]=scene;b.ram[0x7B]=0;compare('full_nonbattle_NMI',b,0xE221,nmi=True)
 for request in(0,1,2,4,8,15,128,255):
  b=fresh(8);b.ram[0x500]=0;b.ram[0x508]=request;compare('owned_battle_camera_callback',b,0xA021)
 for entry in(0xF26D,0xECBF,0xECEE,0xE753,0xE57F):compare('owned_shared_real_return',fresh(),entry)
 for sub in(0,2):
  b=fresh();b.ram[0x78]=3;b.ram[0x500]=0;b.ram[0x501]=sub;b.ram[0x508]=0;b.ram[0x4C8]=0
  compare('actual_battle_A000_wrapper',b,0xA000,scene=3)
  b=fresh();b.ram[0x78]=3;b.ram[0x7B]=0;b.ram[0x500]=0;b.ram[0x501]=sub;b.ram[0x508]=0;b.ram[0x4C8]=0
  compare('full_active_battle_NMI',b,0xE221,nmi=True)
 b=fresh(14);b.ram[0x78]=4;b.ram[0x540:0x542]=bytes([3,2]);b.ram[0x87]=255
 compare('actual_attack_A000_wrapper_portrait_dependency_prefix',b,0xA000,scene=4,allow_prefix=True)
 b=fresh(23);b.ram[0x78]=5;b.ram[0x4A8:0x4AA]=bytes([3,2]);b.ram[0x87]=255
 compare('actual_duel_B100_entry',b,0xB100,scene=5)
 # Missing hardware and unknown services never manufacture completion.
 b=fresh();g=game(b,False);c=g.readable_scene_rules();r=NMIRegisters(sp=253,pc=0xE753);call=ServiceCall(0xE753,0x2468,'fixture',r,g.memory,tuple(b.banks),255)
 before=list(g.memory.io_writes);assert c(call)['status']=='dependency'and r.pc==0xE753 and r.sp==253;assert c(call)['status']=='dependency'and g.memory.io_writes==before
 g.memory.read_ports[0x2002]=deque([0]);assert c(call)['status']=='returned'and r.pc==0x2468 and r.sp==255;guards.append('same_owner_resumes_real_hardware_wait')
 r=NMIRegisters(sp=253,pc=0x8123);call=ServiceCall(0x8123,0x2468,'unknown',r,g.memory,tuple(b.banks),255);assert c(call)['status']=='dependency'and r.pc==0x8123 and r.sp==253;guards.append('unknown_callee_never_returns')
 assert c.setup.memory is g.memory and c.presentation.memory is g.memory and all(c.controller(s).memory is g.memory for s in(3,4,5));guards.append('all_scene_owners_share_same_explicit_bus')
 for status in(None,'waiting','error','blocked'):
  r=NMIRegisters(sp=253,pc=0x8123);call=ServiceCall(0x8123,0x2468,'unknown',r,g.memory,tuple(b.banks),255)
  def bad_callback(call,status=status):
   call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
   return None if status is None else{'status':status}
  c.external_callback=bad_callback;assert c(call)['status']=='dependency'
  guards.append('external_'+str(status)+'_cannot_fake_completion_despite_PC_SP')
 c.external_callback=None
 files=['source/recovered/'+v+'.py'for v in('game_engine','scene_coordinator','scene_initialization','scene_shared_services','battle_scene_controller','attack_scene_controller','duel_scene_controller','battle_setup_ai','battle_background_initialization')]+['scripts/verify_phase11_integration.py']
 out=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,actual_ROM_CPU_comparison_count=sum(counts.values()),complete_return_count=sum(v['comparison']=='complete_return'for v in rows),strict_prefix_count=sum(v['comparison']=='strict_prefix'for v in rows),counts=dict(counts),failures=failures,rows=rows,source_guard_count=len(guards),source_guards=guards,compared_RAM_addresses=SCOPE,compared_SRAM_bytes=8192,complete_return_registers_ports_banks=True,source_original_CPU_callbacks=0,native_core_field_comparison_count=0,source_IR_interpretation=False,source_sha256={f:sha(ROOT/f)for f in files})
 (ROOT/'analysis/phase11/source-integration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k]for k in('status','actual_ROM_CPU_comparison_count','source_guard_count','counts','failures')},ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
