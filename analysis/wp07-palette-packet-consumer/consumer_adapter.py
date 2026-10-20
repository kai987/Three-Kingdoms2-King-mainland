"""Controlled current-JSR adapter and observed existing raw-register bus.

No new PPU hardware algorithm is implemented here. ServiceMemory consumes
explicit status samples, resets its latches, and records raw14bit data writes.
There is no internal vblank/open-bus/mirroring/timing/rendering claim.
"""
import sys
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import BattleNMIServices

def registers(r):return{k:getattr(r,k)for k in('pc','a','x','y','p','sp')}
def memory_bytes(m):return bytes(m.ram)+bytes(m.sram)+bytes(m.ppu_register_bytes)
def device_state(m):
 return dict(banks=list(m.banks),port_image=dict(m.port_image),ppu_address=m.ppu_address,ppu_increment=m.ppu_increment,
  ppu_latch=m.ppu_latch,ppu_scroll_latch=m.ppu_scroll_latch,ppu_scroll=list(m.ppu_scroll),
  read_ports={str(k):list(v)for k,v in m.read_ports.items()},repeat_read_ports=sorted(m.repeat_read_ports),
  status_success_count=m.status_success_count,controller_buttons=m.controller_buttons,controller_index=list(m.controller_index),controller_strobe=m.controller_strobe,
  N163_bytes=list(m.n163_ram),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
  CHR_selectors=dict(m.chr_selectors),DMA_requests=list(m.dma_requests))
def point(m,r):return dict(registers=registers(r),device=device_state(m),history_counts=dict(IO_reads=len(m.io_reads),IO_writes=len(m.io_writes),PPU_data_writes=len(m.ppu_writes),software_writes=len(m.soft_writes)))
def fingerprint(m,r):
 return(memory_bytes(m),registers(r),device_state(m),list(m.io_reads),list(m.io_writes),list(m.ppu_writes),list(m.hardware_requests),list(m.soft_writes))

class ConsumerMemory(ServiceMemory):
 def __init__(self,*args,side,status_plan,**kw):
  super().__init__(*args,**kw);self.side=side;self.status_plan=status_plan;self.status_success_count=0
  self.registers=None;self.opcode_pc=None;self.soft_writes=[];self.port_events=[];self.missing_attempts=[];self.entry_points=[];self.data_reads=[]
 def origin(self):
  if self.side=='CPU':return dict(original_PC=self.opcode_pc,Source_method=None,Source_line=None,Source_semantic_PC=None)
  frame=sys._getframe(1)
  while frame is not None:
   name=frame.f_code.co_filename
   if '/source/recovered/'in name and not name.endswith(('/service_memory.py','/mapped_memory.py')):
    return dict(original_PC=None,Source_method=frame.f_code.co_name,Source_line=frame.f_lineno,Source_semantic_PC=self.registers.pc)
   frame=frame.f_back
  return dict(original_PC=None,Source_method=None,Source_line=None,Source_semantic_PC=None)
 def __getitem__(self,address):
  if isinstance(address,int)and self.registers is not None:
   frame=sys._getframe(1);method=frame.f_code.co_name
   if self.side=='Source'and method=='pending_ppu'and address==0x7D:
    self.entry_points.append((point(self,self.registers),memory_bytes(self)))
   value=super().__getitem__(address)
   cpu_data=self.side=='CPU'and((self.opcode_pc in(0xE726,0xE72C)and 0x100<=address<0x120)or(self.opcode_pc in(0xA132,0xA13A,0xA140,0xA146)and 0x380<=address<=0x3C3))
   source_data=self.side=='Source'and((method=='palette_upload'and 0x100<=address<0x120)or(method in('next_nametable_packet','write_nametable_packet_tiles')and 0x380<=address<=0x3C3))
   if cpu_data or source_data:self.data_reads.append(dict(address=address,value=value,**self.origin()))
   return value
  return super().__getitem__(address)
 def __setitem__(self,address,value):
  if isinstance(address,int):
   q=address&65535
   if q<8192 or 0x6000<=q<0x8000:
    p=q&2047 if q<8192 else q;before=self.ram[p]if q<8192 else self.sram[q-0x6000]
    self.soft_writes.append(dict(address=q,before=before,value=value&255,**self.origin()))
  return super().__setitem__(address,value)
 def io_read(self,address):
  assert address==0x2002,'No other device read belongs to this locked contract'
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

def current_call(memory,registers,coordinator,caller_pc=0xF8B5):
 if registers.pc!=caller_pc or registers.p&8:raise ValueError('Declared current original JSR with D=0 required')
 owner=BattleNMIServices(memory,callbacks=coordinator)
 def body():yield from owner.call(caller_pc,0xEE53)
 return owner,owner._start(body,registers,'controlled_actual_F8B5_JSR')
