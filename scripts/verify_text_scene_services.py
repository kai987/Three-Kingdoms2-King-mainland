#!/usr/bin/env python3
"""Original CPU checks of exact readable text caller/flags/port protocols."""
import argparse,hashlib,json,sys
from collections import Counter,deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.text_scene_services import TextSceneServices,TextRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
SCOPE=[*range(0x140),*range(0x200,0x800)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes();counts=Counter();failures=[];samples=[];guards=[];visited=Counter()
 def fresh():
  b=PortBus(rom);b.ram[:]=ram;b.sram[:]=sram;b.banks=[19,29,30,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0xDE:0xE4]=bytes([51,61,62,51,61,62]);b.ram[0x1FE:0x200]=bytes([0x67,0x24]);b.ram[0x7A]=4;b.ram[0x7E]=b.ram[0x81]=0;b.ram[0x300]=1
  b.ram[0x310:0x314]=bytes([0x6C,255,255,255]);b.ram[0xA6:0xA8]=bytes([0,96]);b.ram[0x306:0x308]=bytes([64,36]);b.ram[0x30C]=b.ram[0x30F]=0;b.ram[0x42C:0x438]=bytes([109,0,0,9,0,0,99,0,0,0,0,0]);return b
 def model(b,reads=True):
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),**({'read_ports':{0x2002:0},'repeat_read_ports':(0x2002,)}if reads else{}));owners={}
  def callback(call):
   if id(call)not in owners:owners[id(call)]=TextSceneServices(m,rom,services=callback)if call.target==0xEE72 else SceneSharedServices(m,rom,callbacks=callback)
   return owners[id(call)](call)
  return m,TextSceneServices(m,rom,services=callback)
 def compare(group,b,entry,meta,regs=None):
  m,source=model(b);r=TextRegisters(a=17,x=23,y=31,p=32,sp=253);r.__dict__.update(regs or{});initial=vars(r).copy();cpu=MPU(memory=b,pc=entry);b.cpu=cpu;b.record_ports=True
  for k in('a','x','y','p','sp'):setattr(cpu,k,initial[k])
  try:
   result=source.run_entry(entry,registers=r);assert result['status']=='returned',(result['status'],hex(r.pc))
   for n in range(200000):
    if cpu.pc==0x2468:break
    b.pc=cpu.pc;b.step_no=n;origin=b.origin(cpu.pc)
    if origin:visited[(origin[0],cpu.pc,origin[1]+16)]+=1
    cpu.step()
   else:raise RuntimeError(f'Original budget ${cpu.pc:04X}')
   diff=[(hex(v),b.ram[v],m.ram[v])for v in SCOPE if b.ram[v]!=m.ram[v]];rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not diff and bytes(b.sram)==bytes(m.sram),diff[:10];assert not rg,rg;assert b.ports==m.io_writes,(b.ports[:8],m.io_writes[:8],len(b.ports),len(m.io_writes));assert b.banks==m.banks
   counts[group]+=1
   if sum(v['group']==group for v in samples)<5:samples.append(dict(group=group,entry=entry,inputs=meta,instructions=n,registers=vars(r).copy(),port_writes=len(m.io_writes)))
  except Exception as exc:
   failures.append(dict(group=group,entry=entry,inputs=meta,error=str(exc)))
   if len(failures)<=8:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 def stream(token,suffix=()):
  b=fresh();data=bytes([1,2,token,*suffix,128]);b.sram[:len(data)]=data;return b
 for token in range(128,160):
  if token==131:continue
  for accents in(0,1):
   for bias in(0,128,255):
    suffix=[108]if token==130 else[66,36]if token in(134,*range(138,144))else[7]if token==137 else[0]if token in(156,157)else[0,3]if token==158 else[0]if token==159 else[]
    b=stream(token,suffix);b.ram[0x30C]=accents;b.ram[0x30F]=bias;compare('all32_game_text_commands',b,0xA003,[token,accents,bias])
 for accents in(0,1):
  for bias in(0,128,255):
   b=stream(131);b.ram[0x30C]=accents;b.ram[0x30F]=bias;b.ram[0x309]=108;b.ram[0x30A:0x30C]=bytes([0,97]);b.sram[256:261]=bytes([108,1,2,3,128]);compare('all32_game_text_commands',b,0xA003,[131,accents,bias])
 for value in(0,1,99,100,99999,999999,1000000,16777215):
  for width in range(8):
   b=stream(158,[0,width]);b.ram[0x44C:0x44F]=value.to_bytes(3,'little');compare('formatted_decimal_exact_scratch',b,0xA003,[value,width])
 for ident in(range(0,237,23)if a.quick else range(237)):
  for token in(144,157,159):
   b=stream(token,[0]if token in(157,159)else[]);b.ram[0x42C]=ident;compare('officer_symbols_and_diacritics',b,0xA003,[token,ident])
 for progress in(0,1,255):
  for job in(0,1,4,255):
   for button in(0,1,128,255):
    b=fresh();b.ram[0x300]=progress;b.ram[0x7E]=job;b.ram[0x81]=button
    if progress==1:b.sram[:4]=bytes([1,2,3,128])
    compare('producer_real_early_RTS_flags',b,0xA003,[progress,job,button])
 for burst in(0,128):
  for skip in(0,1):
   for jobs in(1,4,5):
    for timer in(0,1,2,3):
     for cursor in(0,1,2,255):
      b=fresh();b.ram[0x303]=burst;b.ram[0x308]=skip;b.ram[0x7E]=jobs;b.ram[0x5E]=timer;b.ram[0x305]=3;b.ram[0x304]=cursor;b.ram[0x31C:0x324]=bytes([64,36,7,8,128,1,1,1]);b.ram[0x34C:0x354]=bytes([32,36,1,1,128,1,1,1]);b.ram[0x44D]=128
      compare('consumer_priority_cadence_burst_and_cursor',b,0xA000,[burst,skip,jobs,timer,cursor])
 for entry in(0xA006,0xA11B):
  for tiles in(1,2,17,32):
   b=fresh();b.ram[0x380:0x380+tiles+4]=bytes([tiles,36,64,*range(tiles),255]);compare('nametable_packets_true_RTS',b,entry,[tiles])
 # Existing captured worker states, replayed only as read-only CPU fixtures.
 for case in('cold-battle','ordinary-attack-return','duel-return'):
  for point in json.loads((ROOT/f'analysis/phase11/runtime/{case}/checkpoints.json').read_text()):
   if a.quick and point['frame']%3:continue
   b=fresh();b.ram[:]=(ROOT/f'analysis/phase11/runtime/{case}'/point['RAM']).read_bytes();b.sram[:]=(ROOT/f'analysis/phase11/runtime/{case}'/point['SRAM']).read_bytes();b.ram[0xE2:0xE4]=bytes([61,62]);b.ram[0x1FE:0x200]=bytes([0x67,0x24])
   compare('captured_queue_state_exact_producer',b,0xA003,[case,point['label']])
 b=fresh();b.ram[0x303]=128;b.ram[0x31C:0x321]=bytes([64,36,7,8,128]);b.ram[0x34C:0x351]=bytes([32,36,1,1,128]);m,source=model(b,False);r=TextRegisters(sp=253)
 result=source.run_entry(0xA000,registers=r);assert result['status']=='dependency'and r.pc==0xA0C4 and r.sp==253;before=list(m.io_writes)
 assert source.resume()['status']=='dependency'and m.io_writes==before;m.read_ports[0x2002]=deque([0,0]);assert source.resume()['status']=='returned'and r.pc==0x2468 and r.sp==255;guards.append('missing_PPSTATUS_repeats_same_owner_then_real_RTS')
 for status in(None,'waiting','error','blocked'):
  b=fresh();m,source=model(b);r=TextRegisters(sp=253)
  def fake(call,status=status):
   call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
   return None if status is None else{'status':status}
  source.services=fake;assert source.run_entry(0xA003,registers=r)['status']=='dependency'
  guards.append('nonreturned_'+str(status)+'_never_advances_even_with_mutated_PC_SP')
 b=fresh();m,source=model(b);r=TextRegisters(p=8)
 try:source.run_entry(0xA003,registers=r);okay=False
 except ValueError:okay=True
 assert okay;guards.append('NES_binary_arithmetic_domain')
 b=stream(160);m,source=model(b);r=TextRegisters()
 try:source.run_entry(0xA003,registers=r);okay=False
 except ValueError:okay=True
 assert okay and r.sp!=255;guards.append('text_command_outside_32_entries_has_no_RTS')
 out=ROOT/'analysis/phase12/text';out.mkdir(parents=True,exist_ok=True);files=['source/recovered/text_scene_services.py','source/recovered/scene_shared_services.py','source/recovered/service_memory.py','scripts/verify_text_scene_services.py']
 report=dict(status='passed'if not failures else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,source_guard_case_count=len(guards),counts=dict(counts),guards=guards,failures=failures,failed_count=len(failures),samples=samples,declared_RAM_addresses=SCOPE,all_SRAM_compared_bytes=8192,complete_registers_ports_banks=True,free_stack_residue_excluded=True,source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256=sha(ROOT/'source/recovered/text_scene_services.py'),validator_sha256=sha(Path(__file__)),dependencies={f:sha(ROOT/f)for f in files})
 (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(visited.items())],indent=2)+'\n');print(json.dumps({k:report[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
