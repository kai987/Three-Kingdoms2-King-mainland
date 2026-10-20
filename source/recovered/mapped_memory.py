"""PRG data windows and RAM for recovered logic, without an NES CPU emulator.

ROM bytes are read-only data. CPU controllers execute their separate lifted IR.
PPU/audio/IRQ synthesis is unsupported. The selected APU-enable write is an
explicit hardware request, not a synthesized channel or completed audio frame.
"""
import hashlib
from .officers import ROM_SHA256

class UnsupportedHardware(RuntimeError):
    pass

class PrgDataMemory:
    def __init__(self,rom,ram=None,sram=None,banks=(2,12,13,31)):
        self.rom=bytes(rom)
        if hashlib.sha256(self.rom).hexdigest()!=ROM_SHA256:raise ValueError('Wrong ROM identity')
        self.ram=bytearray(0x800) if ram is None else bytearray(ram)
        self.sram=bytearray(0x2000) if sram is None else bytearray(sram)
        if len(self.ram)!=0x800 or len(self.sram)!=0x2000:raise ValueError('RAM/SRAM sizes')
        self.banks=list(banks);self.mapper_writes=[];self.hardware_requests=[]
        if len(self.banks)!=4 or self.banks[3]!=31:raise ValueError('Four PRG windows; fixed bank31')

    def __len__(self):return 0x10000

    def __getitem__(self,address):
        if isinstance(address,slice):
            start,stop,step=address.indices(0x10000)
            return bytearray(self[i] for i in range(start,stop,step))
        address&=65535
        if address<0x2000:return self.ram[address&0x7ff]
        if 0x6000<=address<0x8000:return self.sram[address-0x6000]
        if address>=0x8000:
            window=(address-0x8000)//8192
            return self.rom[16+self.banks[window]*8192+(address&8191)]
        raise UnsupportedHardware(f'Read hardware ${address:04X}')

    def __setitem__(self,address,value):
        if isinstance(address,slice):
            start,stop,step=address.indices(0x10000);positions=range(start,stop,step)
            if len(positions)!=len(value):raise ValueError('Fixed address space cannot resize')
            for p,v in zip(positions,value):self[p]=v
            return
        address&=65535;value&=255
        if address<0x2000:self.ram[address&0x7ff]=value;return
        if 0x6000<=address<0x8000:self.sram[address-0x6000]=value;return
        if address in (0xE000,0xE800,0xF000):
            window={0xE000:0,0xE800:1,0xF000:2}[address]
            self.banks[window]=(value&63)%32
            self.mapper_writes.append({'address':address,'selector':value,'physical_bank':self.banks[window]})
            return
        if address==0x4015:
            self.hardware_requests.append({'address':address,'value':value,'kind':'APU channel enable request'})
            return
        raise UnsupportedHardware(f'Write hardware/ROM ${address:04X}')

    def activate_scene(self,pair,data_bank):
        """Explicit control-entry data mapping, without inventing NMI work."""
        self.banks[:]=[data_bank,pair,pair+1,31]

    def prepare_callback(self,pair,data_bank):
        """Known callback preconditions; no PPU or job completion is implied."""
        self.activate_scene(pair,data_bank)
        self.ram[0xe1:0xe4]=bytes([data_bank|32,pair|32,(pair+1)|32])
        self.ram[0x7c]=0
