"""Explicit NES register environment for the recovered game services.

This is an observable register/command sink, not a cycle-accurate NES core.
PPUSTATUS, APU status and controller inputs are caller-supplied. No IRQ, NMI,
rendering, audio synthesis or software readiness flag is completed by this bus.
Its optional PPU/N163 register images let consumers inspect actual writes.
"""
from collections import deque
from .mapped_memory import PrgDataMemory,UnsupportedHardware

class IOReadUnavailable(UnsupportedHardware):
    """The software service requested an input absent from the caller contract."""

class ServiceMemory(PrgDataMemory):
    def __init__(self,rom,ram=None,sram=None,banks=(2,12,13,31),*,read_ports=None,
                 repeat_read_ports=(),controller_buttons=None):
        super().__init__(rom,ram,sram,banks)
        self.io_writes=[];self.io_reads=[]
        self.read_ports={a:deque([v]if isinstance(v,int)else v)for a,v in (read_ports or {}).items()}
        self.repeat_read_ports=set(repeat_read_ports)
        self.controller_buttons=None if controller_buttons is None else tuple(controller_buttons)
        if self.controller_buttons is not None and (len(self.controller_buttons)!=2 or any(not 0<=v<256 for v in self.controller_buttons)):
            raise ValueError('Two controller bytes, bit0 A .. bit7 Right, required')
        self.controller_index=[0,0];self.controller_strobe=0
        self.port_image={};self.n163_ram=bytearray(128);self.n163_address=0;self.n163_autoincrement=False
        self.ppu_writes=[];self.ppu_address=0;self.ppu_increment=1;self.ppu_latch=0
        self.ppu_register_bytes=bytearray(0x4000)
        self.ppu_scroll=[0,0];self.ppu_scroll_latch=0
        self.chr_selectors={};self.dma_requests=[]

    @staticmethod
    def is_write_port(address):
        return (0x2000<=address<0x4000 or 0x4000<=address<=0x401F or
                0x4800<=address<0x6000 or address>=0x8000)

    def io_read(self,address):
        address&=65535
        key=0x2000+(address&7)if 0x2000<=address<0x4000 else address
        if 0x4800<=address<0x5000:key=0x4800
        if key in self.read_ports:
            values=self.read_ports[key]
            if not values:raise IOReadUnavailable(f'Explicit read sequence exhausted at ${key:04X}')
            value=values[0]
            if len(values)>1 or key not in self.repeat_read_ports:values.popleft()
        elif key in (0x4016,0x4017) and self.controller_buttons is not None:
            port=key-0x4016;index=self.controller_index[port]
            value=(self.controller_buttons[port]>>min(index,7))&1 if index<8 else 1
            if not self.controller_strobe:self.controller_index[port]+=1
        elif key==0x4800:
            value=self.n163_ram[self.n163_address]
            if self.n163_autoincrement:self.n163_address=min(127,self.n163_address+1)
        else:raise IOReadUnavailable(f'Caller must supply hardware read ${key:04X}')
        value&=255;self.io_reads.append({'address':address,'value':value})
        if key==0x2002:self.ppu_latch=self.ppu_scroll_latch=0
        return value

    def io_write(self,address,value):
        address&=65535;value&=255
        if not self.is_write_port(address):raise UnsupportedHardware(f'Unsupported service port ${address:04X}')
        self.io_writes.append({'address':address,'value':value});self.port_image[address]=value
        key=0x2000+(address&7)if 0x2000<=address<0x4000 else address
        if 0x4800<=address<0x5000:key=0x4800
        register=address&0xF800
        if register in (0xE000,0xE800,0xF000):
            super().__setitem__(register,value)
        elif 0x8000<=register<0xE000:self.chr_selectors[register]=value
        elif register==0xF800:key=0xF800
        if key==0xF800:
            self.n163_address=value&127;self.n163_autoincrement=bool(value&128)
        elif key==0x4800:
            self.n163_ram[self.n163_address]=value
            if self.n163_autoincrement:self.n163_address=min(127,self.n163_address+1)
        elif key==0x2000:self.ppu_increment=32 if value&4 else 1
        elif key==0x2005:
            self.ppu_scroll[self.ppu_latch]=value;self.ppu_latch^=1
            self.ppu_scroll_latch=self.ppu_latch
        elif key==0x2006:
            if self.ppu_latch==0:self.ppu_address=(value&63)<<8 | (self.ppu_address&255)
            else:self.ppu_address=(self.ppu_address&0x3F00)|value
            self.ppu_latch^=1
        elif key==0x2007:
            self.ppu_register_bytes[self.ppu_address&0x3FFF]=value
            self.ppu_writes.append({'address':self.ppu_address&0x3FFF,'value':value})
            self.ppu_address=(self.ppu_address+self.ppu_increment)&0x3FFF
        elif key==0x4014:
            self.dma_requests.append({'page':value,'OAMADDR':self.port_image.get(0x2003,0),
                                      'bytes':bytes(self[(value<<8)+i]for i in range(256))})
        elif key==0x4016:
            self.controller_strobe=value&1
            if self.controller_strobe:self.controller_index=[0,0]
        self.hardware_requests.append({'address':address,'value':value,'kind':'explicit recovered-service register write'})

    def __getitem__(self,address):
        if isinstance(address,slice):return super().__getitem__(address)
        if address<0x2000 or 0x6000<=address<0x8000 or address>=0x8000:return super().__getitem__(address)
        return self.io_read(address)

    def __setitem__(self,address,value):
        if isinstance(address,slice):return super().__setitem__(address,value)
        address&=65535
        if address<0x2000 or 0x6000<=address<0x8000:return super().__setitem__(address,value)
        self.io_write(address,value)
