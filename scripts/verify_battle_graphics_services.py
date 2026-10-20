#!/usr/bin/env python3
"""Full original graphics-service returns, RAM/SRAM/ports and returnedregs."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_graphics_services import GraphicsData,BattleGraphicsServices,GraphicsRegisters,ROM_SHA256,DECLARED_RAM_ADDRESSES
class PortBus(Bus):
 def __init__(self,rom):super().__init__(rom,'zero');self.ports=[];self.record_ports=False
 def __setitem__(self,address,value):
  if self.record_ports and address>=0x2000 and not 0x6000<=address<0x8000:self.ports.append(dict(address=address&65535,value=value&255))
  super().__setitem__(address,value)
def verify(rom,out):
 data=GraphicsData.from_rom(rom);counts=Counter();failures=[];coverage=Counter();samples=[];guards=[]
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
 def fresh():
  b=PortBus(rom);b.ram[:]=base_ram;b.sram[:]=base_sram;b.banks=[6,12,13,31];b.bank_initialized=[True]*4;b.protect=0x4C;b.ram[0xDE:0xE4]=bytes([38,44,45,38,44,45]);b.ram[0x1FE:0x200]=bytes([255,1]);b[0x7C]=0;b[0x12]=1;b[0x509]=1;b[0x507]=0x10
  b[0x90]=0;b[0x91]=0;b[0x8E]=0;b[0x8F]=0
  for slot in range(20):b[0x600+slot]=b[0x614+slot]=255;b[0x63C+slot]=7;b[0x628+slot]=0
  b[0x601]=10;b[0x615]=10;b[0x604]=11;b[0x618]=11
  for ruler in range(7):b[0x6F0A+8*ruler]=ruler%4
  return b
 def compare(group,b,entry,call,meta,r=None):
  r=r or GraphicsRegisters();b.ports=[];m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));source=BattleGraphicsServices(m,data);cpu=MPU(memory=b,pc=entry);cpu.sp=0xFD;cpu.a=r.a;cpu.x=r.x;cpu.y=r.y;cpu.p=r.p;b.cpu=cpu;b.record_ports=True
  try:
   result=call(source,r)
   for n in range(300000):
    if cpu.pc==0x200:break
    b.pc=cpu.pc;b.step_no=n;origin=b.origin(cpu.pc)
    if origin is None:raise RuntimeError(f'UnexpectedRAMPC{cpu.pc:04X}')
    bank,offset=origin;coverage[(bank,cpu.pc,offset+16)]+=1;cpu.step()
   else:raise RuntimeError(f'Original budget{cpu.pc:04X}')
   rd=[(hex(a),b.peek(a),m[a])for a in DECLARED_RAM_ADDRESSES if b.peek(a)!=m[a]];sd=[(hex(0x6000+i),old,new)for i,(old,new)in enumerate(zip(b.sram,m.sram))if old!=new]
   assert not rd and not sd,(rd[:12],sd[:12])
   assert b.ports==m.io_writes,(b.ports,m.io_writes)
   assert b.banks==m.banks,(b.banks,m.banks)
   if 'registers'in result:
    actual={k:getattr(cpu,k)for k in('a','x','y','p')};assert actual==result['registers'],(actual,result['registers'])
   counts[group]+=1
   if sum(s['group']==group for s in samples)<12:samples.append(dict(group=group,input=meta,entry=entry,original_instructions=n,result=result,port_writes=m.io_writes,all_SRAM_equal=True))
   return result
  except Exception as exc:
   failures.append(dict(group=group,input=meta,error=str(exc)))
   if len(failures)==1:print(json.dumps(failures[-1]))
   if len(failures)>=8:raise
 # Maprefresh rows, bothdraw modes, camera seams/clipping, unitstrength,
 # controller and affinity. Fields are valid typed inputs, plusbyteedges.
 for draw in(0,1):
  for camera in(0,12,16,28,124,127,128,236,252,255):
   for dx in(0,1,14,15,16,255):
    for y in(0,1,14,16,19,255):
     b=fresh();b[0x12]=draw;b[0x8E]=camera;b[0x601]=(BattleGraphicsServices._camera_x(camera)+dx)&255;b[0x615]=y
     compare('map_refresh_complete',b,0xD6CC,lambda g,r:g.map_refresh(r),[draw,camera,dx,y],GraphicsRegisters(a=17,x=23,y=31,p=33))
 for slot in(0,1,10,19):
  for strength in(0,1,9,10):
   for controller in(0,1,2,3):
    for affinity in range(4):
     b=fresh();b[0x509]=slot;b[0x600+slot]=10;b[0x614+slot]=10;b[0x628+slot]=affinity| (128 if slot>=10 else 0);b[0x63C+slot]=strength;b[0x6F0A+8*(1 if slot>=10 else 0)]=controller
     compare('unit_BG_map_refresh_complete',b,0xD6CC,lambda g,r:g.map_refresh(r),[slot,strength,controller,affinity])
 # Cursorworldfixedspriteclipping: byte/wordcamera, OAMcapacity andrawgap.
 for cursor_y in(0,1,8,15,16,239,240,255,256,511):
  for cursor_x in(0,1,7,8,255,256,511):
   for index in(0,4,248,252,255):
    b=fresh();b[0x6F41]=cursor_y&255;b[0x6F42]=cursor_y>>8;b[0x6F3F]=cursor_x&255;b[0x6F40]=cursor_x>>8;b[0x7C]=index
    compare('cursor_complete',b,0xD657,lambda g,r:g.cursor(r),[cursor_y,cursor_x,index],GraphicsRegisters(p=32|64))
 for alternate in(False,True):
  for timer in(0,15,16,31,255):
   for index in(0,4,248,252,255):
    b=fresh();b[0x5E]=timer;b[0x7C]=index
    compare('highlight_complete',b,0xDC70 if alternate else 0xDC63,lambda g,r,a=alternate:g.highlight(r,alternate=a),[alternate,timer,index],GraphicsRegisters(a=17,x=23,y=31,p=32|64|1))
 # FixedF092 underlying record handling, including negative offsets/flip
 # +1xquirk and partialOAM writes before rejecting highX.
 for flags in(0,64,128,192):
  for dx in(0,8,127,128,248,255):
   for dy in(0,8,127,129,248,255):
    b=fresh();b[0]=0x80;b[1]=0;b[2]=flags;b.ram[0x80:0x85]=bytes([dy,6,2,dx,128]);b[0xA]=100;b[0xB]=0;b[0xC]=100;b[0xD]=0
    compare('fixed_world_sprite_complete',b,0xF092,lambda g,r:g.world_sprites(r),[flags,dx,dy])
 # True animationconsumer25A00F->26CFD6, not23AB53 scrollupdate.
 # Sequential original calls receive an explicit NMI OAMcursor reset; jobs
 # areFFinitially, never acknowledged or changed by source. This is a CPU
 # cooperativefixture, not synthesized complete video/NMIframes.
 sequences=[]
 for tactic in range(16):
  b=fresh();b.banks=[6,25,26,31];b.ram[0xDE:0xE4]=bytes([38,57,58,38,57,58]);b[0x4C8]=tactic+1;b[0x300]=b[0x304]=255
  states=[]
  for step in range(230):
   b[0x7C]=0;before=[b[0x4C8],b[0x4C9],b[0x4CA],b[0x4D0]]
   result=compare('animation_all16_sequence_complete',b,0xA00F,lambda g,r:g.animation_tick(r),[tactic,step,before])
   if result is None:break
   states.append(dict(step=step,before=before,after=[b[0x4C8],b[0x4C9],b[0x4CA],b[0x4D0]],ports=len(b.ports)))
   if b[0x4C8]==0:break
  assert b[0x4C8]==0,('Animationdidnotreachoriginalend',tactic,states[-1])
  sequences.append(dict(tactic_id=tactic,mapped_visual_kind=data.animation_kinds[tactic]>>1,source_and_original_calls=len(states),stages=states,complete_original_RTS_each=True,host_inputs='0300/0304 initialFF;007Creset0beforeeachoriginalNMI servicepoint',video_NMI_frames_synthesized=False))
 for request in(0,1,16,128,129):
  for job1,job2 in((0,255),(255,0),(1,1),(255,255)):
   b=fresh();b.banks=[6,25,26,31];b.ram[0xDE:0xE4]=bytes([38,57,58,38,57,58]);b[0x4C8]=request;b[0x4C9]=0;b[0x4CA]=0;b[0x300]=job1;b[0x304]=job2
   compare('animation_wait_or_initial_return',b,0xA00F,lambda g,r:g.animation_tick(r),[request,job1,job2])
 # Sourceguards, never execute invalidtableindices orunterminated data.
 for label,prepare,call in [('slot20',lambda m:m.__setitem__(0x509,20),lambda g:g.map_refresh()),('unit_strength11',lambda m:m.__setitem__(0x63D,11),lambda g:g.unit_tiles(1)),('unit_ruler7',lambda m:m.__setitem__(0x507,7),lambda g:g.unit_tiles(1)),('decimal_fixture',lambda m:None,lambda g:g.cursor(GraphicsRegisters(p=40)))]:
  b=fresh();m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));prepare(m)
  try:call(BattleGraphicsServices(m,data))
  except ValueError:guards.append(label)
  else:raise AssertionError('Missing guard'+label)
 out.mkdir(parents=True,exist_ok=True);v=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,samples=samples,source_guards=guards,animation_sequences=sequences,
    compared_SRAM_bytes=8192,compared_RAM_bytes=len(DECLARED_RAM_ADDRESSES),RAM_addresses=DECLARED_RAM_ADDRESSES,CPU_stack_page_excluded_except=[[0x100,0x120],[0x1B0,0x1B4]],returned_register_contract=['A','X','Y','P'],animation_registers_excluded=True,SP_PC_excluded=True,ordered_port_writes_compared=True,PPU_queue_consumption_or_DMA_synthesized=False,original_instruction_locations=len(coverage),source_sha256=hashlib.sha256((ROOT/'source/recovered/battle_graphics_services.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 (out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
 print(json.dumps({k:v[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')},indent=2));return v
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/graphics');a=p.parse_args();v=verify(a.rom.read_bytes(),a.out)
 if v['failed_count']:raise SystemExit(1)
