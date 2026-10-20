"""Readable original audio requests and eleven-slot APU/N163 tick driver.

The ROM supplies immutable music descriptors, music commands and driver tables.
Music commands are parsed as game data; no 6502 opcodes, IR or original CPU are
executed. Writes use the caller's real memory port interface. This module does
not synthesize oscillators, PCM, time, IRQs, audio playback or completion flags.
E6C6 is controller sampling, and E70E palette transfer: neither is audio.
"""
from dataclasses import dataclass
import hashlib

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SLOTS = tuple(range(0, 0xF2, 0x16))
REQUEST_COUNTS = {0xE609:1,0xE66B:8,0xE673:7,0xE67B:6,0xE683:5,0xE68B:4,0xE693:3,0xE69B:2}
DECLARED_RAM_RANGES = ((0xA5,0xA6),(0xE1,0xE3),(0xF0,0xF2),(0x700,0x7FA))


class AudioCommandBudget(RuntimeError):
    """Original data did not produce a note/end within the explicit budget."""


class AudioDataUnavailable(ValueError):
    """An unsupported descriptor or mapped music pointer cannot be fabricated."""


@dataclass(frozen=True)
class AudioData:
    streams: bytes
    driver_tables: bytes
    startup_wave: bytes
    disable_masks: bytes
    descriptor_count: int = 183

    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
            raise ValueError('Audio data requires the pinned original ROM')
        streams=bytes(rom[16+2*8192:16+4*8192])
        assert streams[2:4]==bytes((0xDC,0x42))
        assert streams[183*4:183*4+5]==bytes((0,0,0x10,0,255))
        return cls(streams,bytes(rom[16+15*8192:16+16*8192]),
                   bytes(rom[0x3E6B6:0x3E6D6]),bytes(rom[0x3E677:0x3E67B]))

    def table(self,cpu):
        if not 0xC000<=cpu<0xE000:
            raise AudioDataUnavailable(f'Audio driver table ${cpu:04X} outside bank15')
        return self.driver_tables[cpu-0xC000]


class AudioServices:
    """Shared-memory semantic audio services, with an optional return-register contract.

    The hardware adapter must record actual memory[port] writes. No default
    hardware reads are supplied. All SRAM and declared nonstack RAM are in the
    semantic comparison. Optional registers have a/x/y/p/sp attributes; their
    final values precede the caller's genuine RTS. Caller stack frames remain
    untouched; free stack residual writes are outside this semantic contract.
    """
    def __init__(self,memory,data:AudioData):
        self.memory=memory;self.data=data;self.events=[];self._remaining=0;self._slot=None;self._header_main_reentry=False

    def _set(self,address,value):self.memory[address]=value&255
    def _emit(self,address,value):
        value&=255;self.memory[address]=value
        self.events.append({'address':address,'value':value})
    def _b(self,x,field):return self.memory[0x700+x+field]
    def _s(self,x,field,value):self._set(0x700+x+field,value)
    def _pointer(self):return self.memory[0xF0]|self.memory[0xF1]<<8
    def _put_pointer(self,value):self._set(0xF0,value);self._set(0xF1,value>>8)
    def _read(self,address):
        address&=65535
        if 0x8000<=address<0xC000:return self.data.streams[address-0x8000]
        if address<0x8000:return self.memory[address]
        raise AudioDataUnavailable(f'Music pointer ${address:04X} outside mapped data/RAM')
    def _param(self,y):return self._read(self._pointer()+(y&255))
    def _allowed(self):
        channel=self.memory[0x7F3]
        return not(self.data.table(0xDD4E+channel)&self.memory[0x7F2])
    @staticmethod
    def _register_result(registers,a,x,y,flags):
        result=None
        if registers is not None:
            registers.a=a&255;registers.x=x&255;registers.y=y&255
            registers.p=(registers.p&~0xC3)|flags
            result={k:getattr(registers,k)for k in ('a','x','y','p','sp')}
        return result
    def _result(self,registers,a,x,y,flags,**extra):
        return dict(status='returned',port_writes=list(self.events),
                    contract_registers=self._register_result(registers,a,x,y,flags),
                    register_contract='End of service body; actual caller RTS/return frame external; free stack residue excluded',
                    PCM_generated=False,**extra)

    def _load_sequence(self,sequence_id):
        m=self.memory;descriptor=0x8000+sequence_id*4
        m[0xE1]=0x22;self._emit(0xE000,0x22);self._put_pointer(descriptor)
        x=self._read(descriptor)
        if self._b(x,0)!=255 and self._b(x,1)<4:
            m[0x7F6]&=self.data.disable_masks[self._b(x,1)]
            self._emit(0x4015,m[0x7F6])
        self._s(x,1,self._read(descriptor+1));self._s(x,2,self._read(descriptor+2))
        high=self._read(descriptor+3);self._s(x,3,high+0x40);self._s(x,0,0)
        return high

    def request(self,sequence_id,*,entry=0xE673,registers=None):
        """E609 or a fall-through wrapper: request consecutive descriptor IDs.

        Loads requests; it neither parses a music tick nor acknowledges sound.
        Source rejects IDs outside the original183-descriptor table up front.
        """
        if entry not in REQUEST_COUNTS:raise ValueError('Known original audio request entry required')
        count=REQUEST_COUNTS[entry]
        if not isinstance(sequence_id,int)or not 0<=sequence_id<=self.data.descriptor_count-count:
            raise AudioDataUnavailable('Consecutive requests must remain in the original descriptor table')
        for i in range(sequence_id,sequence_id+count):
            if self.data.streams[i*4]not in SLOTS or self.data.streams[i*4+1]>=8:
                raise AudioDataUnavailable('Unsupported original descriptor slot/channel')
        self.events=[]
        for i in range(sequence_id,sequence_id+count):high=self._load_sequence(i)
        x=registers.x if registers is not None else 0
        total=high+0x40;v=bool(~(high^0x40)&(high^(total&255))&128)
        flags=(128 if x&128 else 2 if x==0 else 0)|(64 if v else 0)|(1 if total>255 else 0)
        return self._result(registers,x,x,3,flags,entry=entry,sequence_id=sequence_id,descriptor_requests=count)

    def reset(self,*,registers=None):
        """Complete E57F reset, including real APU/N163 wave/register requests."""
        m=self.memory;self.events=[]
        for ident in range(7):self._load_sequence(ident)
        self._emit(0x4015,0);m[0x7F6]=0
        for port in (0x4000,0x4004,0x400C):self._emit(port,0x10)
        for port in (0x4001,0x4005):self._emit(port,8)
        self._emit(0x4008,0);m[0x7F2]=0
        for x in SLOTS:self._s(x,0,255);self._s(x,6,0)
        self._emit(0xF800,0xC0)
        for _ in range(64):self._emit(0x4800,0)
        self._emit(0xF800,0x80)
        for value in self.data.startup_wave:self._emit(0x4800,value)
        for address in (0x64,0x6C,0x74,0x7C):
            self._emit(0xF800,address);self._emit(0x4800,0xF0)
        self._emit(0xF800,0x7F);self._emit(0x4800,0x30)
        m[0xA5]=0x4C;self._emit(0xF800,0x4C)
        return self._result(registers,0x4C,0x7F,3,0x40,entry=0xE57F,descriptor_requests=7)

    def _control_port(self,value):
        y=self.memory[0x7F5]
        if y<16:self._emit(0x4000+y,value);return
        pointer=((y*2)|0x67)&255
        self._emit(0xF800,pointer);self._emit(0x4800,(value&15)|0x30)
        self._emit(0xF800,(pointer-1)&255);self._emit(0x4800,(value&0xC0)>>3)
    def _frequency_low(self,value):
        y=self.memory[0x7F5]
        if y<16:self._emit(0x4002+y,value)
        else:self._emit(0xF800,((y*2)|0x60)&255);self._emit(0x4800,value)
    def _frequency_high(self,value):
        y=self.memory[0x7F5]
        if y<16:self._emit(0x4003+y,(value&7)|8)
        else:self._emit(0xF800,((y*2)|0x62)&255);self._emit(0x4800,value)
    def _control(self,x,*,already_allowed=False):
        if not already_allowed and not self._allowed():return
        m=self.memory;value=self._b(x,6)
        if m[0x7F4]&128:self._emit(0x4000+m[0x7F5],value);return
        mode=self._b(x,12)
        if mode:
            a=self._b(x,14);quotient=0;m[0x7F7]=0
            denominator=self._b(x,13)
            for _ in range(4):
                a=(a*2)&255;carry=int(a>=denominator)
                if carry:a=(a-denominator)&255
                quotient=((quotient*2)|carry)&255;m[0x7F7]=quotient
            curve=self.data.table(0xDDCE+(((mode*16)&255)|quotient))
            volume=self.data.table(0xDE6E+((value&15)|curve))
            value=(value&0xC0)|volume
        else:value|=(value&0x10)<<1
        self._control_port(value)
    def _vibrato(self,x):
        m=self.memory
        if not self._allowed()or m[0x7F4]&64 or self._b(x,21)or not self._b(x,1)&128:return
        index=(self._b(x,1)&0x70)|(m[0x7F9]&15);m[0x7F7]=self._b(x,1)&0x70
        self._emit(0x4002+m[0x7F5],self.data.table(0xDD5E+index)+self._b(x,18))
    def _slide(self,x):
        if self.memory[0x7F4]&128 or not self._b(x,15):return
        self._s(x,17,self._b(x,17)-1)
        if self._b(x,17):return
        self._s(x,17,self._b(x,16));volume=self._b(x,6)&31;self.memory[0x7F7]=volume
        if not volume&16:return
        delta=self._b(x,15)
        if delta&128:
            self._s(x,15,delta+1)
            if volume!=16:self._s(x,6,self._b(x,6)-1);self._s(x,7,self._b(x,7)-1)
        else:
            self._s(x,15,delta-1)
            if volume!=31:self._s(x,6,self._b(x,6)+1);self._s(x,7,self._b(x,7)+1)
    def _wave_parameter(self,value):
        encoded=value&127 if self.memory[0x7F4]&128 else (value&3)<<6
        self.memory[0x7F7]=encoded
        return encoded,bool(self.memory[0x7F4]&128)
    def _header(self,x):
        self._put_pointer(self._b(x,2)|(self._b(x,3)<<8))
        tempo=self._param(0)&15;self._s(x,4,tempo);self._s(x,5,tempo)
        self._wave_parameter(self._param(1));volume=self._param(2)|self.memory[0x7F7]
        self._s(x,6,volume);self._s(x,7,volume);self._s(x,9,self._param(3))
        for field in (10,11,12,15):self._s(x,field,0)
        self._s(x,0,2)
    def _stop_note(self,x):
        value=0 if self.memory[0x7F4]&128 else self._b(x,6)&0xC0
        self._s(x,6,value);self._control(x)
    def _note(self,x,note,param):
        m=self.memory;m[0x7F7]=note;self._s(x,8,param)
        if m[0x7F4]&64:
            if note>=16:self._stop_note(x);return
            period=note;m[0x7F8]=0
        else:
            if note&15>=12:self._stop_note(x);return
            index=(note&15)*2+(24 if self._b(x,4)&128 else 0)+(48 if m[0x7F3]>=4 else 0)
            period=self.data.table(0xDD06+index)|(self.data.table(0xDD07+index)<<8)
            octave=note&0x70
            if m[0x7F3]>=4:
                if octave==0x40:period=(period*2)&65535;shift=0
                else:
                    borrow=1 if octave<0x40 else 0
                    sub=octave-0x30-borrow
                    if sub==0:shift=0
                    else:shift=(-((sub&255)if sub<0 else 0xB0)&255)>>4
            else:shift=octave>>4
            period>>=shift
            m[0x7F7]=period&255;m[0x7F8]=(period>>8)&255
        m[0x7F7]=period&255;m[0x7F8]=(period>>8)&255
        self._s(x,14,0);self._s(x,6,self._b(x,7))
        if not self._allowed():return
        channel=m[0x7F3]
        if channel<4:
            m[0x7F6]|=self.data.table(0xDD4E+channel);self._emit(0x4015,m[0x7F6])
        self._control(x,already_allowed=True)
        if m[0x7F5]<16:self._emit(0x4001+m[0x7F5],self._b(x,9))
        low=period&255;self._frequency_low(low);self._s(x,18,2 if low<2 else 0xFD if low>=0xFE else low)
        self._frequency_high((period>>8)&255)

    def _parse(self,x):
        m=self.memory
        restart=True;y=0
        while True:
            if restart:
                self._s(x,21,self._b(x,20));self._put_pointer((self._b(x,0)*2+self._b(x,2)+(self._b(x,3)<<8))&65535)
                y=0;restart=False
            if self._remaining<=0:raise AudioCommandBudget('Music command loop has not returned a note/end')
            self._remaining-=1
            command=self._param(y);self._s(x,0,self._b(x,0)+1);y=(y+1)&255
            param=self._param(y)
            if command>=0xF0:
                if command==0xFD:self._s(x,19,self._b(x,0))
                elif command==0xFF:self._s(x,0,255);self._stop_note(x);return
            elif command>=0xD0:
                delta=command&15
                if command>=0xE0:delta=(-delta)&255
                if not m[0x7F4]&128:
                    self._s(x,15,delta);self._s(x,16,param);self._s(x,17,param)
            elif command>=0xC0:
                mode=command&15;m[0x7F7]=mode
                if not m[0x7F4]&128 and self._b(x,6)&16:self._s(x,13,param);self._s(x,12,mode)
            elif command>=0xB0:
                count=command&15;take=True
                if count:
                    field=11 if param else 10;value=(self._b(x,field)-1)&255;self._s(x,field,value)
                    if value==0:take=False
                    elif value&128:self._s(x,field,count)
                if take:self._s(x,0,param if param else self._b(x,19))
                # Both branches jump toD99B, including a loop counter reaching
                # zero. The next command address is unchanged, butF0/F1 are
                # rebuilt from the current word index rather than retainingY.
                restart=True
            elif command>=0xA0:
                if command==0xA0:
                    if not m[0x7F4]&128:
                        value=(self._b(x,6)&0xC0)|param;self._s(x,6,value);self._s(x,7,value)
                elif command==0xA1:self._s(x,9,param)
                elif command==0xA2:
                    value,triangle=self._wave_parameter(param)
                    if not triangle:value|=self._b(x,6)&31
                    self._s(x,6,value);self._s(x,7,value)
                elif command==0xA3:
                    if param&128:self._s(x,1,self._b(x,1)&7)
                    else:
                        delay=(param&15)*2;self._s(x,20,delay);self._s(x,21,delay)
                        self._s(x,1,self._b(x,1)|(param&0x70)|128)
                elif command==0xA4:self._s(x,1,self._b(x,1)&7)
                elif command==0xAD:
                    index=self._b(x,0)*2;m[0xF1]=(index>>8)&255
                    base=self._b(x,2)|(self._b(x,3)<<8);base=(base+index)&65535
                    self._s(x,2,base);self._s(x,3,base>>8);self._s(x,0,0)
                    if not param:
                        self._header(x);restart=True
                        # The original jumpsD958->D940, nestingD99B under the
                        # current parser call. The restof the slot scan runs,
                        # then an outerD943 also merges the finalslot mask,
                        # including when that finalslot wasinactive.
                        self._header_main_reentry=True
                elif command==0xAE:self._s(x,4,(self._b(x,4)&127)|(param&128))
                elif command==0xAF:
                    self._s(x,5,param&15);self._s(x,4,(self._b(x,4)&240)|(param&15))
            else:self._note(x,command,param);return
            y=(y+1)&255

    def tick(self,*,registers=None,command_budget=4096):
        """Complete14 A003->15D8D4 driver tick, with an explicit loop budget.

        It writes register requests in their original order. A malformed/control
        loop can return a budget prefix; it is never silently ended or acked.
        """
        if not isinstance(command_budget,int)or command_budget<=0:raise ValueError('Positive music command budget required')
        m=self.memory;self.events=[];self._remaining=command_budget;self._header_main_reentry=False
        m[0xE1]=0x22;self._emit(0xE000,0x22);m[0xE2]=0x23;self._emit(0xE800,0xE3)
        m[0x7F2]=0;self._set(0x7F9,m[0x7F9]+1)
        try:
            for x in SLOTS:
                self._slot=x;channel=self._b(x,1)&7;m[0x7F3]=channel;m[0x7F5]=channel*4;m[0x7F4]=self.data.table(0xDD56+channel)
                state=self._b(x,0)
                if state==255:continue
                if state==0:self._header(x);self._parse(x)
                else:
                    self._vibrato(x);self._s(x,14,self._b(x,14)+1)
                    if self._b(x,14)>=self._b(x,13):self._s(x,14,self._b(x,13))
                    self._s(x,5,self._b(x,5)-1)
                    if self._b(x,5)&128:
                        self._s(x,5,self._b(x,4)&15);self._slide(x)
                        if self._b(x,21):self._s(x,21,self._b(x,21)-1)
                        self._s(x,8,self._b(x,8)-1)
                        if self._b(x,8)==0:self._parse(x)
                        else:self._control(x)
                    else:self._control(x)
                m[0x7F2]|=self.data.table(0xDD4E+channel)
            if self._header_main_reentry:m[0x7F2]|=self.data.table(0xDD4E+m[0x7F3])
        except AudioCommandBudget as exc:
            return dict(status='budget',slot_offset=self._slot,commands_consumed=command_budget,
                        port_writes=list(self.events),reason=str(exc),contract_registers=None,PCM_generated=False,
                        original_bank=15,original_cpu_boundary=0xD9BD)
        return self._result(registers,0xF2,0xDC,m[0x7F3],3,entry=0xD8D4,
                            processed_slots=len(SLOTS),commands_consumed=command_budget-self._remaining)
