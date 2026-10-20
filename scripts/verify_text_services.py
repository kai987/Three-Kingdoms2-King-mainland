#!/usr/bin/env python3
"""Original full-return text workers/PPU consumers against readable source."""
import argparse,hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.service_memory import ServiceMemory
from collections import deque
from source.recovered.text_services import TextData,TextServices
from source.recovered.officers import ROM_SHA256
class PortBus(Bus):
 def __init__(self,rom):super().__init__(rom,'zero');self.ports=[];self.record_ports=False
 def __setitem__(self,address,value):
  if self.record_ports and address>=0x2000 and not 0x6000<=address<0x8000:self.ports.append(dict(address=address&65535,value=value&255))
  super().__setitem__(address,value)

def verify(rom,out):
 data=TextData.from_rom(rom);counts=Counter();failures=[];samples=[];coverage=Counter();guards=[]
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
 base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
 declared=[0x7D,0x7E,0xA6,0xA7,0xE1,*range(0x300,0x375)]
 def fresh():
  b=PortBus(rom);b.ram[:]=base_ram;b.sram[:]=base_sram;b.banks=[19,29,30,31];b.bank_initialized=[True]*4;b.protect=0x4C
  b.ram[0x1FE:0x200]=bytes([255,1]);b.ram[0xE1]=51;b.ram[0x7A]=4;b.ram[0x7E]=0;b.ram[0x81]=0;b.ram[0x300]=1
  b.ram[0x310:0x314]=bytes([0x6C,255,255,255]);b.ram[0xA6:0xA8]=bytes([0,0x60]);b.ram[0x306:0x308]=bytes([0x40,0x24]);b.ram[0x30C]=0;b.ram[0x30F]=0
  b.ram[0x42C:0x438]=bytes([109,0,0,9,0,0,99,0,0,0,0,0]);return b
 def compare(group,b,entry,method,meta,extra=()):
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0},repeat_read_ports=(0x2002,));source=TextServices(m,data)
  cpu=MPU(memory=b,pc=entry);cpu.sp=0xFD;b.cpu=cpu;b.record_ports=True
  try:
   result=getattr(source,method)()
   for n in range(200000):
    if cpu.pc==0x200:break
    b.pc=cpu.pc;b.step_no=n;origin=b.origin(cpu.pc)
    assert origin is not None,f'Original out-of-code at {cpu.pc:04X}'
    bank,offset=origin;coverage[(bank,cpu.pc,offset+16)]+=1;cpu.step()
   else:raise RuntimeError(f'Original budget at {cpu.pc:04X}')
   rd=[(hex(a),b.peek(a),m[a])for a in declared+list(extra) if b.peek(a)!=m[a]]
   sd=[(hex(0x6000+i),x,y)for i,(x,y)in enumerate(zip(b.sram,m.sram))if x!=y]
   assert not rd and not sd,(rd[:12],sd[:12]);assert b.ports==m.io_writes,(b.ports[:8],m.io_writes[:8],len(b.ports),len(m.io_writes))
   assert b.banks==m.banks,(b.banks,m.banks);counts[group]+=1
   if method=='text_ready':assert bool(cpu.p&1)==result
   if sum(v['kind']==group for v in samples)<10:samples.append(dict(kind=group,input=meta,original_instructions=n,result=result,port_writes=m.io_writes))
  except Exception as exc:
   failures.append(dict(kind=group,input=meta,error=str(exc)))
   if len(failures)<=5:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 def stream_case(token,suffix):
  b=fresh();s=bytes([1,2,token,*suffix,0x80]);b.sram[:len(s)]=s;return b
 for token in range(0x80,0xA0):
  for mode in (0,1):
   for offset in (0,128,255):
    suffix=([0x6C]if token==0x82 else[0x42,0x24]if token in(0x86,*range(0x8A,0x90))else[7]if token==0x89 else[0]if token in(0x9C,0x9D)else[0,3]if token==0x9E else[109]if token==0x9F else[])
    if token==0x83:continue # tested with original nested-message inputs below
    b=stream_case(token,suffix);b.ram[0x30C]=mode;b.ram[0x30F]=offset
    compare('all32_text_data_commands',b,0xA003,'produce_text',[token,mode,offset],extra=range(7,10)if token in range(0x98,0x9C)or token==0x9E else())
 for mode in(0,1):
  for offset in(0,128,255):
   b=stream_case(0x83,[]);b.ram[0x30C]=mode;b.ram[0x30F]=offset
   b.ram[0x309]=0x6C;b.ram[0x30A:0x30C]=bytes([0,0x61]);b.sram[0x100:0x105]=bytes([0x6C,1,2,3,128])
   compare('all32_text_data_commands',b,0xA003,'produce_text',[0x83,mode,offset])
 for value in (0,1,9,10,99,100,999,1000,99999,999999,1000000,16777215):
  for token in (0x98,0x99,0x9A,0x9B):
   b=stream_case(token,[]);a=0x42C+3*(token-0x98);b.ram[a:a+3]=value.to_bytes(3,'little')
   compare('report_decimal',b,0xA003,'produce_text',[token,value],extra=range(7,10))
 for value in (0,1,100,9999,0xFF0000,0xFE0000,16777215):
  for width in range(8):
   b=stream_case(0x9E,[0,width]);b.ram[0x44C:0x44F]=value.to_bytes(3,'little')
   compare('field_decimal_and_sentinels',b,0xA003,'produce_text',[value,width],extra=range(7,10))
 for ident in(0,1,38,109,236,255):
  for token in (0x90,0x9C,0x9D,0x9F):
   b=stream_case(token,[ident]if token==0x9F else[0]if token in(0x9C,0x9D)else[]);b.ram[0x42C]=ident
   # city valid IDs0..29 or negative placeholders; do not reinterpret name IDs as cities.
   if token==0x9C and 30<=ident<128:continue
   compare('name_city_and_diacritics',b,0xA003,'produce_text',[token,ident])
 for progress in (0,1,255):
  for job in(0,1,4,255):
   for button in(0,1,128,255):
    b=fresh();b.ram[0x300]=progress;b.ram[0x7E]=job;b.ram[0x81]=button
    if progress==1:b.sram[:4]=bytes([1,2,3,128])
    compare('worker_wait_and_real_message_init',b,0xA003,'produce_text',[progress,job,button])
 # True original menu, cast, result and final-core frames; no new native input.
 for case in json.loads((ROOT/'analysis/phase9/runtime/evidence.json').read_text())['native_cases']:
  path=ROOT/'analysis/phase9/runtime'/case['case']
  for label in case['images']:
   b=fresh();b.ram[:]=(path/(label+'-ram.bin')).read_bytes();b.sram[:]=(path/(label+'-sram.bin')).read_bytes();b.ram[0x1FE:0x200]=bytes([255,1])
   compare('native_snapshot_worker',b,0xA003,'produce_text',[case['case'],label])
 for burst in(0,1,128):
  for one_row in(0,1):
   for cadence in(0,1,3,255):
    for count in(0,1,7,39):
     b=fresh();b.ram[0x303]=burst;b.ram[0x308]=0;b.ram[0x30C]=one_row;b.ram[0x5E]=cadence;b.ram[0x305]=3;b.ram[0x304]=0;b.ram[0x7E]=1
     b.ram[0x31C:0x31E]=bytes([0x20,0x24]);b.ram[0x34C:0x34E]=bytes([0x00,0x24]);b.ram[0x31E:0x31E+count]=bytes([7]*count);b.ram[0x34E:0x34E+count]=bytes([8]*count);b.ram[0x31E+count]=b.ram[0x34E+count]=128
     compare('text_PPU_consumer',b,0xA000,'consume_text',[burst,one_row,cadence,count])
 for count in(1,2,15,255):
  b=fresh();packet=bytes([count,0x24,0x20])+bytes(i&255 for i in range(count))+bytes([255]);b.ram[0x380:0x380+len(packet)]=packet
  if len(b.ram)!=2048:raise AssertionError('Fixture RAM resized')
  compare('map_PPU_consumer',b,0xA006,'consume_map_commands',count,extra=(0,1))
 for mask in range(256):
  b=fresh();b.ram[0x7E]=mask;compare('explicit_text_cancel',b,0xA10A,'cancel_text',mask)
 for cursor in(0,1,127,255):
  for progress in(0,1,127,255):
   for jobs in(0,1,4,255):
    b=fresh();b.banks=[19,12,13,31];b.ram[0x304]=cursor;b.ram[0x300]=progress;b.ram[0x7E]=jobs
    compare('actual_text_readiness',b,0xDF27,'text_ready',[cursor,progress,jobs])
 for slot in(0,1,10,19):
  for ident in(0,1,38,99,109,236):
   b=fresh();b.ram[0x509]=slot;b.ram[0x664+slot]=ident
   compare('actor_name_panel_command_generation',b,0xA027,'draw_actor_panel',[slot,ident],extra=[0,1,2,*range(0x380,0x3C0)])
 for label,prepare in [('mode15',lambda b:b.ram.__setitem__(0x7A,15)),('commandA0',lambda b:b.sram.__setitem__(slice(0,1),bytes([160]))),('width8',lambda b:b.sram.__setitem__(slice(0,4),bytes([158,0,8,128])))]:
  b=fresh();b.sram[:4]=bytes([128,128,128,128]);prepare(b);m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks))
  try:TextServices(m,data).produce_text()
  except ValueError:guards.append(label)
  else:raise AssertionError('Missing source guard '+label)
 # Source ownership checks are separate from original CPU comparisons above.
 # Suspend before the second PPUSTATUS read: the first row must not be replayed.
 for kind in ('character','burst','palette','map'):
  b=fresh();b.ram[0x304]=0;b.ram[0x303]=int(kind=='burst');b.ram[0x30C]=0;b.ram[0x5E]=1 if kind=='palette' else 0;b.ram[0x305]=3;b.ram[0x7E]=1
  b.ram[0x31C:0x31F]=bytes([32,36,7]);b.ram[0x34C:0x34F]=bytes([0,36,8]);b.ram[0x31F]=b.ram[0x34F]=128
  b.ram[0x380:0x385]=bytes([1,36,32,9,255])
  initial_reads=[] if kind in ('palette','map') else [0]
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:initial_reads});s=TextServices(m,data)
  reference=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0},repeat_read_ports=(0x2002,));sr=TextServices(reference,data)
  fn=s.consume_map_commands if kind=='map' else s.consume_text
  rf=sr.consume_map_commands if kind=='map' else sr.consume_text
  expected=rf();pending=fn();assert pending['status']=='dependency' and pending.get('hardware_read',pending.get('dependency',{}).get('address'))==0x2002,pending
  writes=list(m.io_writes);jobs=m[0x7E];cursor=m[0x304]
  assert fn()['status']=='dependency' and m.io_writes==writes and m[0x7E]==jobs and m[0x304]==cursor
  opposite=s.consume_text if kind=='map' else s.consume_map_commands
  try:opposite()
  except RuntimeError:pass
  else:raise AssertionError('Consumer ownership was lost')
  m.read_ports[0x2002]=deque([0]);m.repeat_read_ports.add(0x2002)
  actual=fn();assert actual==expected and m.io_writes==reference.io_writes and m.ram==reference.ram and m.sram==reference.sram,(kind,actual,expected)
  guards.append(kind+'_missing_status_resumes_without_duplicate_writes')
 out.mkdir(parents=True,exist_ok=True)
 result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,samples=samples,
             declared_RAM_addresses=declared,conditional_packed_BCD_scratch=[7,8,9],all_SRAM_compared_bytes=8192,ordered_IO_writes_compared=True,banks_compared=True,CPU_registers_stack_arithmetic_scratch_excluded=True,
             native_field_comparison_count=0,native_snapshot_CPU_fixture_count=counts['native_snapshot_worker'],source_original_code_calls=0,source_IR_interpretation=False,source_guards=guards,
             source_sha256=hashlib.sha256((ROOT/'source/recovered/text_services.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             dependencies={'source/recovered/service_memory.py':hashlib.sha256((ROOT/'source/recovered/service_memory.py').read_bytes()).hexdigest(),'source/recovered/battle_nmi_services.py':hashlib.sha256((ROOT/'source/recovered/battle_nmi_services.py').read_bytes()).hexdigest()},
             original_instruction_locations=len(coverage))
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
 print(json.dumps({k:result[k]for k in ('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False),flush=True)
 if failures:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/text');a=p.parse_args();verify(a.rom.read_bytes(),a.out)
