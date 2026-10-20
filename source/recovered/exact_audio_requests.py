"""Original fixed audio reset/requests with real caller and idle-stack effects.

Descriptors and wave bytes are immutable game data, not6502 instructions.
Named direct functions retain every localframe/PHA/PLA and orderedAPU/N163
request. They synthesize noPCM, video clock, interrupt, input or ready/ack.
"""
from dataclasses import dataclass
from .global_ui_controller import UIControlBase,UIRegisters,C,Z,I,D,B,U,V,N

AudioRequestRegisters=UIRegisters
ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
@dataclass(frozen=True)
class AudioRequestBudget:
    pc:int
    reason:str='Explicit source block budget; no artificial return'

class ExactAudioRequests(UIControlBase):
    PUBLIC_ENTRIES=(0xE57F,0xE590,0xE5F3,0xE5FA,0xE609,0xE66B,0xE673,0xE67B,0xE683,0xE68B,0xE693,0xE69B)
    def __init__(self,memory,rom,services=None):
        super().__init__(memory,rom,services);self._call_owner=None
    def fields(self):
        m=self.memory
        return dict(data_window=m[0xE1],N163_address_shadow=m[0xA5],disable_mask=m[0x7F2],APU_enable=m[0x7F6],
            descriptor_pointer=m[0xF0]|m[0xF1]<<8,slots=tuple(m[0x700+x]for x in range(0,242,22)))
    def _checkpoint(self,pc):
        self.registers.pc=pc
        if self._blocks>=self._limit:yield AudioRequestBudget(pc)
        self._blocks+=1
    def _drive(self):
        while True:
            if self.pending is not None:
                if isinstance(self.pending,AudioRequestBudget):return self._result('budget')
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def resume(self,*,max_blocks=None):
        if self._program is None:raise RuntimeError('No pending actual audio request')
        if max_blocks is not None:
            if not isinstance(max_blocks,int)or max_blocks<=0:raise ValueError('Positive explicit additional budget required')
            if not isinstance(self.pending,AudioRequestBudget):raise ValueError('No block budget is pending')
            self._limit=self._blocks+max_blocks;self.pending=None
        return self._drive()
    def run_entry(self,entry=0xE57F,*,registers=None,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('Actual caller registers and existing frame required')
        if entry not in self.PUBLIC_ENTRIES:raise ValueError('Entry outside original fixed audio request domain')
        if getattr(self.memory,'banks',())[3:]!=[31]and tuple(getattr(self.memory,'banks',())[3:])!=(31,):raise ValueError('Original fixedbank31 required')
        if not isinstance(max_blocks,int)or max_blocks<0:raise ValueError('Nonnegative explicit block budget required')
        actual=((self.memory[0x100+((registers.sp+1)&255)]|self.memory[0x100+((registers.sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual:raise ValueError('ReturnPC must match the actual caller word')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)
    def __call__(self,call):
        if call.target not in self.PUBLIC_ENTRIES or tuple(call.entry_banks[3:])!=(31,):return dict(status='dependency',reason='Not an identified fixed31 audio request')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='A different caller owns the pending audio request')
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)
    def _entry(self,entry):
        if entry==0xE57F:return self.reset_audio()
        if entry==0xE590:return self.configure_audio_hardware()
        if entry==0xE5F3:return self.write_N163_pair()
        if entry==0xE5FA:return self.fill_N163_control_slots()
        if entry==0xE609:return self.load_descriptor()
        if entry==0xE66B:return self.request_eight_descriptors()
        if entry==0xE673:return self.request_seven_descriptors()
        if entry==0xE67B:return self.request_six_descriptors()
        if entry==0xE683:return self.request_five_descriptors()
        if entry==0xE68B:return self.request_four_descriptors()
        if entry==0xE693:return self.request_three_descriptors()
        if entry==0xE69B:return self.request_two_descriptors()
        raise ValueError('Unknown fixed audio request')
    def reset_audio(self):
        """E57F..E58F: load0..6, configurehardware and select N163address4C."""
        r=self.registers;m=self.memory;yield from self._checkpoint(0xE57F);self._a(0)
        if not(yield from self._local_call(self.request_seven_descriptors,0xE581,0xE584)):return
        if not(yield from self._local_call(self.configure_audio_hardware,0xE584,0xE587)):return
        self._a(0x4C);m[0xA5]=r.a;m[0xF800]=r.a;self._rts();return
    def configure_audio_hardware(self):
        """E590..E5F9: disableAPU, clear eleven slots, N16364B and wave32B."""
        r=self.registers;m=self.memory;yield from self._checkpoint(0xE590);self._a(0);m[0x4015]=r.a;m[0x7F6]=r.a
        self._a(16);m[0x4000]=r.a;m[0x4004]=r.a;m[0x400C]=r.a
        self._a(8);m[0x4001]=r.a;m[0x4005]=r.a
        self._a(0);m[0x4008]=r.a;m[0x7F2]=r.a;self._x(r.a)
        while True:
            yield from self._checkpoint(0xE5B4);self._a(255);m[0x700+r.x]=r.a;self._a(0);m[0x706+r.x]=r.a
            self._a(r.x);self._flag(C,False);self._add(22);self._x(r.a);self._compare(r.a,242)
            if r.p&Z:break
        self._a(192);m[0xF800]=r.a;self._x(63);self._a(0)
        while True:
            yield from self._checkpoint(0xE5D0);m[0x4800]=r.a;self._x(r.x-1)
            if r.p&N:break
        self._x(128);m[0xF800]=r.x;self._x(0)
        while True:
            yield from self._checkpoint(0xE5DD);self._a(m[0xE6A6+r.x]);m[0x4800]=r.a;self._x(r.x+1);self._compare(r.x,32)
            if r.p&C:break
        self._x(100);self._a(240)
        if not(yield from self._local_call(self.fill_N163_control_slots,0xE5EC,0xE5EF)):return
        self._x(127);self._a(48);return(yield from self.write_N163_pair())
    def write_N163_pair(self):
        """E5F3..E5F9: actual F800=X,4800=A write and callerRTS."""
        r=self.registers;m=self.memory;yield from self._checkpoint(0xE5F3);m[0xF800]=r.x;m[0x4800]=r.a;self._rts();return
    def fill_N163_control_slots(self):
        """E5FA..E608: PHA/PLA loop for X100,108,116,124, preserving idlebytes."""
        r=self.registers;yield from self._checkpoint(0xE5FA);self._push(r.a)
        while True:
            yield from self._checkpoint(0xE5FB);self._a(self._pop())
            if not(yield from self._local_call(self.write_N163_pair,0xE5FC,0xE5FF)):return
            self._push(r.a);self._a(r.x);self._flag(C,False);self._add(8);self._x(r.a)
            if r.p&N:break
        self._a(self._pop());self._rts();return
    def load_descriptor(self):
        """E609..E666: read4-byte descriptor, preserve X with actual PHA/PLA.

        F25F selectsphysical2. Existing activeAPUchannel0..3 disables its bit
        before replacing the channel/stream. Descriptor highbyte adds40 and
        wraps8bits; slotstate becomes0. No channelready or musicend is faked.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xE609);self._y(34)
        yield from self._external(0xE60B,0xF25F,0xE60E,'call')
        if r.pc!=0xE60E:return
        self._y(0);m[0xF1]=r.y;r.a=self._shift(r.a,True);m[0xF1]=self._shift(m[0xF1],True,True)
        r.a=self._shift(r.a,True);m[0xF1]=self._shift(m[0xF1],True,True)
        self._flag(C,False);self._add(0);m[0xF0]=r.a;self._a(128);self._add(m[0xF1]);m[0xF1]=r.a
        self._a(r.x);self._push(r.a);self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535]);self._x(r.a)
        self._a(m[0x700+r.x]);self._compare(r.a,255)
        if not r.p&Z:
            self._a(m[0x701+r.x]);self._compare(r.a,4)
            if not r.p&C:
                self._y(r.a);self._a(m[0xE667+r.y]);self._a(r.a&m[0x7F6]);m[0x7F6]=r.a;m[0x4015]=r.a
        self._y(1);self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535]);m[0x701+r.x]=r.a
        self._y(r.y+1);self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535]);m[0x702+r.x]=r.a
        self._y(r.y+1);self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535]);self._flag(C,False);self._add(64);m[0x703+r.x]=r.a
        self._a(0);m[0x700+r.x]=r.a;self._a(self._pop());self._x(r.a);self._rts();return
    def _request_link(self,pc):
        """One genuine PHA/JSR E609/PLA/CLC/ADC1, retaining bytewrap."""
        r=self.registers;yield from self._checkpoint(pc);self._push(r.a)
        if not(yield from self._local_call(self.load_descriptor,pc+1,pc+4)):return False
        self._a(self._pop());self._flag(C,False);self._add(1);return True
    def request_eight_descriptors(self):
        if not(yield from self._request_link(0xE66B)):return
        return(yield from self.request_seven_descriptors())
    def request_seven_descriptors(self):
        if not(yield from self._request_link(0xE673)):return
        return(yield from self.request_six_descriptors())
    def request_six_descriptors(self):
        """E67B: also a genuine public fixedentry; no extra localJSR frame."""
        if not(yield from self._request_link(0xE67B)):return
        return(yield from self.request_five_descriptors())
    def request_five_descriptors(self):
        if not(yield from self._request_link(0xE683)):return
        return(yield from self.request_four_descriptors())
    def request_four_descriptors(self):
        if not(yield from self._request_link(0xE68B)):return
        return(yield from self.request_three_descriptors())
    def request_three_descriptors(self):
        if not(yield from self._request_link(0xE693)):return
        return(yield from self.request_two_descriptors())
    def request_two_descriptors(self):
        if not(yield from self._request_link(0xE69B)):return
        return(yield from self.load_descriptor())
