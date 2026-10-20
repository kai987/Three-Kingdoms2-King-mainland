"""Readable scene2 continuation with strict original caller returns.

Algorithms are existing recovered BattleNMIServices methods. The only control
glue models F878 JMP($0000), checks each real callsite and stops before F8C1.
The register environment is an explicit finite raw-command fixture, not a PPU.
"""
import sys
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import BattleNMIServices,ServiceWait

def registers(r):return {k:getattr(r,k) for k in ('pc','a','x','y','p','sp')}
def memory_bytes(m):return bytes(m.ram)+bytes(m.sram)+bytes(m.ppu_register_bytes)
def device_state(m):
 return dict(banks=list(m.banks),port_image=dict(m.port_image),ppu_address=m.ppu_address,ppu_increment=m.ppu_increment,
  ppu_latch=m.ppu_latch,ppu_scroll_latch=m.ppu_scroll_latch,ppu_scroll=list(m.ppu_scroll),
  read_ports={str(k):list(v)for k,v in m.read_ports.items()},repeat_read_ports=sorted(m.repeat_read_ports),
  status_success_count=m.status_success_count,controller_buttons=m.controller_buttons,controller_index=list(m.controller_index),controller_strobe=m.controller_strobe,
  N163_bytes=list(m.n163_ram),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
  CHR_selectors=dict(m.chr_selectors),DMA_requests=[dict(page=d['page'],OAMADDR=d['OAMADDR'],bytes_hex=d['bytes'].hex())for d in m.dma_requests])
def point(m,r):return dict(registers=registers(r),device=device_state(m),history_counts=dict(IO_reads=len(m.io_reads),IO_writes=len(m.io_writes),PPU_data_writes=len(m.ppu_writes),software_writes=len(m.soft_writes)))
def snapshot(m,r):return point(m,r),memory_bytes(m)
def fingerprint(m,r):
 return(snapshot(m,r),list(m.io_reads),list(m.io_writes),list(m.ppu_writes),list(m.hardware_requests),list(m.soft_writes),list(m.mapper_writes))

class ContinuationMemory(ServiceMemory):
 def __init__(self,*args,side,status_plan,**kw):
  super().__init__(*args,**kw);self.side=side;self.status_plan=status_plan;self.status_success_count=0
  self.registers=None;self.opcode_pc=None;self.soft_writes=[];self.port_events=[];self.missing_attempts=[]
 def origin(self):
  if self.side=='CPU':return dict(original_PC=self.opcode_pc,Source_method=None,Source_line=None,Source_semantic_PC=None)
  f=sys._getframe(1)
  while f is not None:
   name=f.f_code.co_filename
   if ('/source/recovered/'in name and not name.endswith(('/service_memory.py','/mapped_memory.py')))or name==__file__:
    if f.f_code.co_name not in ('origin','__setitem__','io_read','io_write'):
     return dict(original_PC=None,Source_method=f.f_code.co_name,Source_line=f.f_lineno,Source_semantic_PC=self.registers.pc)
   f=f.f_back
  return dict(original_PC=None,Source_method=None,Source_line=None,Source_semantic_PC=self.registers.pc)
 def __setitem__(self,address,value):
  if isinstance(address,int):
   q=address&65535
   if q<8192 or 0x6000<=q<0x8000:
    before=self.ram[q&2047]if q<8192 else self.sram[q-0x6000]
    self.soft_writes.append(dict(address=q,before=before,value=value&255,**self.origin()))
  return super().__setitem__(address,value)
 def io_read(self,address):
  assert address==0x2002,'Only explicit PPUSTATUS samples belong to this contract'
  ordinal=self.status_success_count;assert ordinal<len(self.status_plan)
  spec=self.status_plan[ordinal];pc=self.opcode_pc if self.side=='CPU'else self.registers.pc
  assert pc==spec['PC'],(pc,spec)
  if not self.read_ports.get(0x2002):self.missing_attempts.append(dict(ordinal=ordinal+1,PC=pc))
  before=device_state(self);value=super().io_read(address);assert value==spec['value'];self.status_success_count+=1
  self.port_events.append(dict(kind='read',address=address,value=value,ordinal=ordinal+1,before=before,after=device_state(self),**self.origin()))
  return value
 def io_write(self,address,value):
  before=device_state(self);result=super().io_write(address,value)
  self.port_events.append(dict(kind='write',address=address,value=value&255,before=before,after=device_state(self),**self.origin()))
  return result

class ReadableContinuation(BattleNMIServices):
 """Never manufacture the next caller PC after a nonlocal return."""
 def __init__(self,memory):
  super().__init__(memory,callbacks=None);self.calls=[];self.dispatch=None;self.interrupt_snapshot=None;self.stop=None
 def interrupt_entry(self,vector):
  super().interrupt_entry(vector);self.interrupt_snapshot=snapshot(self.memory,self.registers)
 def call(self,pc,target):
  r=self.registers;m=self.memory
  assert r.pc==pc,('actual caller PC required',r.pc,pc)
  caller_sp=r.sp;before=snapshot(m,r);index=len(self.calls)
  row=dict(caller_pc=pc,target=target,expected_return_pc=(pc+3)&65535,expected_sp=caller_sp,before=before)
  self.calls.append(row)
  yield from super().call(pc,target)
  row['after']=snapshot(m,r);row['returned_to_original_caller']=r.pc==row['expected_return_pc']and r.sp==caller_sp
  if not row['returned_to_original_caller']:
   self.stop=dict(category='nonlocal_return',PC=r.pc,SP=r.sp,caller_pc=pc,target=target,expected_PC=row['expected_return_pc'],expected_SP=caller_sp)
   while True:yield ServiceWait('nonlocal_return',r.pc,reason='Actual RTS destination retained; no next callsite is synthesized')
 def routine(self,entry):
  # The most recently appended row owns this actual callee entry.
  row=self.calls[-1];assert row['target']==entry
  row['entry']=snapshot(self.memory,self.registers)
  yield from super().routine(entry)
 def scene(self,scene):
  r=self.registers;m=self.memory
  assert scene==2 and m[0x78]&15==2
  target=m[0]|m[1]<<8;assert target==0xF8B5
  # Actual F878 is JMP($0000); nmi_body has computed the original pointer.
  # This is Source instruction semantics, not a host reentry or fixture patch.
  r.pc=target;self.dispatch=snapshot(m,r)
  yield from self.continue_scene(0xF8B5)
 def continue_scene(self,start):
  r=self.registers;assert r.pc==start
  route=((0xF8B5,0xEE53),(0xF8B8,0xF206),(0xF8BB,0xFB0B),(0xF8BE,0xEC67))
  assert start in (0xF8B5,0xF8B8)
  for pc,target in route:
   if pc<start:continue
   yield from self.call(pc,target)
  assert r.pc==0xF8C1
  self.stop=dict(category='declared_continuation_boundary',PC=r.pc,SP=r.sp)
  while True:yield ServiceWait('declared_continuation_boundary',r.pc,reason='Stop before F8C1 opcode; NMI outer frame remains active')
 def run_existing_scene(self,registers):
  return self._start(lambda:self.continue_scene(0xF8B8),registers,'existing_controlled_F8B8_continuation')
