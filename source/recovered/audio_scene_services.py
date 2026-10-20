"""Exact audio scene caller service, including real local frames and idle stack.

Named Python functions implement the original stream parser and APU/N163
requests. Immutable ROM bytes supply tables/music data, never executable code
or IR. No oscillator, PCM, video frame, IRQ or readiness is synthesized.
"""
class _ContinueLoop_D8EB(Exception):pass
class _ContinueLoop_D940(Exception):pass
class _ContinueLoop_D943(Exception):pass
class _ContinueLoop_D94F(Exception):pass
class _ContinueLoop_D958(Exception):pass
class _ContinueLoop_D99B(Exception):pass
class _ContinueLoop_D9BD(Exception):pass
class _ContinueLoop_DB8D(Exception):pass
class _ContinueLoop_DC68(Exception):pass

from dataclasses import dataclass
from .global_ui_controller import UIControlBase,UIRegisters,C,Z,I,D,B,U,V,N
from .battle_nmi_services import ServiceCall

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
AudioRegisters=UIRegisters

@dataclass(frozen=True)
class AudioBlockBudget:
    pc:int
    reason:str='Explicit structured-control block budget; no artificial return'

class AudioSceneServices(UIControlBase):
    """Physical14 A003 ->15D8D4 caller protocol on shared mapped memory.

    run_entry requires actual registers and an existing caller frame. Only
    fixedF25F is external. All localJSR/PHA/PLA/free-stack writes are real,
    notably the pairedDF92/DF93 pushes used for N163 volume/wave requests.
    LegacyAudioServices remains unchanged with its semantic stack exclusions.
    """
    PAIR=(14,15)
    PUBLIC_ENTRIES=(0xA003,0xD8D4)
    def __init__(self,memory,rom,services=None):
        super().__init__(memory,rom,services);self._call_owner=None
    def fields(self):
        m=self.memory
        return dict(slot_states=tuple(m[0x700+x]for x in range(0,242,22)),
            channel=m[0x7F3],disable_mask=m[0x7F2],frame_cursor=m[0x7F9],
            data_window=m[0xE1],second_data_window=m[0xE2],wave_address=m[0xA5])
    def _checkpoint(self,pc):
        self.registers.pc=pc
        if self._blocks>=self._limit:yield AudioBlockBudget(pc)
        self._blocks+=1
    def _drive(self):
        while True:
            if self.pending is not None:
                if isinstance(self.pending,AudioBlockBudget):return self._result('budget')
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
        if self._program is None:raise RuntimeError('No actual pending audio caller')
        if max_blocks is not None:
            if not isinstance(max_blocks,int)or max_blocks<=0:raise ValueError('Explicit positive additional block budget required')
            if not isinstance(self.pending,AudioBlockBudget):raise ValueError('No structured budget boundary is pending')
            self._limit=self._blocks+max_blocks;self.pending=None
        return self._drive()
    def run_entry(self,entry=0xA003,*,registers=None,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('Supply actual caller registers and existing stack; no seeded return')
        if entry not in self.PUBLIC_ENTRIES:raise ValueError('Only genuine audio scene export/body entries')
        if tuple(getattr(self.memory,'banks',())[1:3])!=self.PAIR:raise ValueError('Audio entry requires physical14/15 caller context')
        if not isinstance(max_blocks,int)or max_blocks<0:raise ValueError('Nonnegative explicit block budget required')
        actual_return=((self.memory[0x100+((registers.sp+1)&255)]|self.memory[0x100+((registers.sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual_return:raise ValueError('Caller returnPC must match the existing stack word')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA003,registers=registers,**kwargs)

    def _entry(self,entry):
        if entry==0xA003:return self.audio_entry()
        elif entry==0xD8D4:return self.update_audio_driver()
        elif entry==0xD99B:return self.decode_stream_commands()
        elif entry==0xDC03:return self.write_frequency_high()
        elif entry==0xDC31:return self.channel_disabled_mask()
        elif entry==0xDC3F:return self.stop_note()
        elif entry==0xDC90:return self.apply_vibrato()
        elif entry==0xDCD8:return self.apply_volume_slide()
        elif entry==0xDF6E:return self.apply_volume()
        elif entry==0xDF71:return self.emit_current_volume()
        elif entry==0xDF92:return self.write_N163_volume_and_wave_pair()
        raise ValueError("Outside named original audio body")

    def audio_entry(self):
        """$A003: audio entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA003)
        return (yield from self.update_audio_driver())

    def update_audio_driver(self):
        """$D8D4: update audio driver; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xD8D4)
        self._y(0x22)
        yield from self._external(0xD8D6,0xF25F,0xD8D9,"call",None)
        if r.pc!=0xD8D9:return  # preserve nonlocal stack return
        self._a(0x23)
        m[0x00E2]=r.a
        self._a(r.a | 0xC0)
        m[0xE800]=r.a
        self._a(0x00)
        m[0x07F2]=r.a
        m[0x07F9]=self._nz(m[0x07F9]+1)
        while True:  # natural loop $D8EB
            try:
                self._x(r.a)
                self._a(m[(0x0701+r.x)&65535])
                self._a(r.a & 0x07)
                m[0x07F3]=r.a
                self._y(r.a)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x07F5]=r.a
                self._a(m[(0xDD56+r.y)&65535])
                m[0x07F4]=r.a
                self._a(m[(0x0700+r.x)&65535])
                yield from self._checkpoint(0xD903)
                if r.p&Z:
                    self._a(m[(0x0702+r.x)&65535])
                    m[0x00F0]=r.a
                    self._a(m[(0x0703+r.x)&65535])
                    m[0x00F1]=r.a
                    self._y(0x00)
                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                    self._a(r.a & 0x0F)
                    m[(0x0704+r.x)&65535]=r.a
                    m[(0x0705+r.x)&65535]=r.a
                    self._y(r.y+1)
                    if not (yield from self._local_call(self.stop_note,0xD971,0xD974)):return
                    self._y(r.y+1)
                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                    self._a(r.a | m[0x07F7])
                    m[(0x0706+r.x)&65535]=r.a
                    m[(0x0707+r.x)&65535]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                    m[(0x0709+r.x)&65535]=r.a
                    self._a(0x00)
                    m[(0x070A+r.x)&65535]=r.a
                    m[(0x070B+r.x)&65535]=r.a
                    m[(0x070C+r.x)&65535]=r.a
                    m[(0x070F+r.x)&65535]=r.a
                    self._a(0x02)
                    m[(0x0700+r.x)&65535]=r.a
                    yield from self._checkpoint(0xD999)
                    if not r.p&Z:
                        if not (yield from self._local_call(self.decode_stream_commands,0xD940,0xD943)):return
                        self._y(m[0x07F3])
                        self._a(m[(0xDD4E+r.y)&65535])
                        self._a(r.a | m[0x07F2])
                        m[0x07F2]=r.a
                        self._a(r.x)
                        self._flag(C,False)
                        self._add(0x16)
                        self._compare(r.a,0xF2)
                        yield from self._checkpoint(0xD955)
                        if not r.p&Z:
                            continue
                        else:
                            yield from self._checkpoint(0xD957)
                            self._rts();return
                    else:
                        return (yield from self.decode_stream_commands())
                else:
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xD907)
                    if r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.apply_volume_slide,0xD909,0xD90C)):return
                        m[(0x070E+r.x)&65535]=self._nz(m[(0x070E+r.x)&65535]+1)
                        self._a(m[(0x070E+r.x)&65535])
                        self._compare(r.a,m[(0x070D+r.x)&65535])
                        yield from self._checkpoint(0xD915)
                        if not r.p&C:
                            pass
                        else:
                            self._a(m[(0x070D+r.x)&65535])
                            m[(0x070E+r.x)&65535]=r.a
                            pass
                        m[(0x0705+r.x)&65535]=self._nz(m[(0x0705+r.x)&65535]-1)
                        yield from self._checkpoint(0xD920)
                        if not r.p&N:
                            if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                            pass
                        else:
                            self._a(m[(0x0704+r.x)&65535])
                            self._a(r.a & 0x0F)
                            m[(0x0705+r.x)&65535]=r.a
                            if not (yield from self._local_call(self.apply_vibrato,0xD92A,0xD92D)):return
                            self._a(m[(0x0715+r.x)&65535])
                            yield from self._checkpoint(0xD930)
                            if r.p&Z:
                                pass
                            else:
                                m[(0x0715+r.x)&65535]=self._nz(m[(0x0715+r.x)&65535]-1)
                                pass
                            m[(0x0708+r.x)&65535]=self._nz(m[(0x0708+r.x)&65535]-1)
                            yield from self._checkpoint(0xD938)
                            if r.p&Z:
                                if not (yield from self._local_call(self.decode_stream_commands,0xD940,0xD943)):return
                                pass
                            else:
                                if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                pass
                            pass
                        self._y(m[0x07F3])
                        self._a(m[(0xDD4E+r.y)&65535])
                        self._a(r.a | m[0x07F2])
                        m[0x07F2]=r.a
                        pass
                    self._a(r.x)
                    self._flag(C,False)
                    self._add(0x16)
                    self._compare(r.a,0xF2)
                    yield from self._checkpoint(0xD955)
                    if not r.p&Z:
                        continue
                    else:
                        yield from self._checkpoint(0xD957)
                        self._rts();return
            except _ContinueLoop_D8EB:
                continue

    def decode_stream_commands(self):
        """$D99B: decode stream commands; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $D99B
            try:
                yield from self._checkpoint(0xD99B)
                self._a(m[(0x0714+r.x)&65535])
                m[(0x0715+r.x)&65535]=r.a
                self._y(0x00)
                m[0x00F1]=r.y
                self._a(m[(0x0700+r.x)&65535])
                r.a=self._shift(r.a,True,rotate=False)
                m[0x00F1]=self._shift(m[0x00F1],True,rotate=True)
                self._add(m[(0x0702+r.x)&65535])
                m[0x00F0]=r.a
                self._a(m[(0x0703+r.x)&65535])
                self._add(m[0x00F1])
                m[0x00F1]=r.a
                self._y(r.y-1)
                while True:  # natural loop $D9BD
                    try:
                        self._y(r.y+1)
                        self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                        m[(0x0700+r.x)&65535]=self._nz(m[(0x0700+r.x)&65535]+1)
                        self._y(r.y+1)
                        self._compare(r.a,0xF0)
                        yield from self._checkpoint(0xD9C6)
                        if r.p&C:
                            self._compare(r.a,0xFD)
                            yield from self._checkpoint(0xD9E4)
                            if not r.p&Z:
                                self._compare(r.a,0xFF)
                                yield from self._checkpoint(0xD9F1)
                                if not r.p&Z:
                                    continue
                                else:
                                    m[(0x0700+r.x)&65535]=r.a
                                    self._a(m[(0x0706+r.x)&65535])
                                    self._a(r.a & 0xC0)
                                    bit_value=m[0x07F4]
                                    self._flag(Z,not(r.a&bit_value))
                                    self._flag(N,bit_value&128)
                                    self._flag(V,bit_value&64)
                                    yield from self._checkpoint(0xDBF9)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._a(0x00)
                                        pass
                                    m[(0x0706+r.x)&65535]=r.a
                                    return (yield from self.apply_volume())
                            else:
                                self._a(m[(0x0700+r.x)&65535])
                                m[(0x0713+r.x)&65535]=r.a
                                continue
                        else:
                            self._compare(r.a,0xE0)
                            yield from self._checkpoint(0xD9CA)
                            if r.p&C:
                                self._a(r.a & 0x0F)
                                self._a(r.a ^ 0xFF)
                                self._flag(C,False)
                                self._add(0x01)
                                bit_value=m[0x07F4]
                                self._flag(Z,not(r.a&bit_value))
                                self._flag(N,bit_value&128)
                                self._flag(V,bit_value&64)
                                yield from self._checkpoint(0xDA08)
                                if r.p&N:
                                    pass
                                else:
                                    m[(0x070F+r.x)&65535]=r.a
                                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                    m[(0x0710+r.x)&65535]=r.a
                                    m[(0x0711+r.x)&65535]=r.a
                                    pass
                                continue
                            else:
                                self._compare(r.a,0xD0)
                                yield from self._checkpoint(0xD9CE)
                                if r.p&C:
                                    self._a(r.a & 0x0F)
                                    bit_value=m[0x07F4]
                                    self._flag(Z,not(r.a&bit_value))
                                    self._flag(N,bit_value&128)
                                    self._flag(V,bit_value&64)
                                    yield from self._checkpoint(0xDA08)
                                    if r.p&N:
                                        pass
                                    else:
                                        m[(0x070F+r.x)&65535]=r.a
                                        self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                        m[(0x0710+r.x)&65535]=r.a
                                        m[(0x0711+r.x)&65535]=r.a
                                        pass
                                    continue
                                else:
                                    self._compare(r.a,0xC0)
                                    yield from self._checkpoint(0xD9D2)
                                    if r.p&C:
                                        self._a(r.a & 0x0F)
                                        m[0x07F7]=r.a
                                        bit_value=m[0x07F4]
                                        self._flag(Z,not(r.a&bit_value))
                                        self._flag(N,bit_value&128)
                                        self._flag(V,bit_value&64)
                                        yield from self._checkpoint(0xDA20)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._a(m[(0x0706+r.x)&65535])
                                            self._a(r.a & 0x10)
                                            yield from self._checkpoint(0xDA27)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                m[(0x070D+r.x)&65535]=r.a
                                                self._a(m[0x07F7])
                                                m[(0x070C+r.x)&65535]=r.a
                                                pass
                                            pass
                                        continue
                                    else:
                                        self._compare(r.a,0xB0)
                                        yield from self._checkpoint(0xD9D6)
                                        if r.p&C:
                                            self._a(r.a & 0x0F)
                                            yield from self._checkpoint(0xDA39)
                                            if r.p&Z:
                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                yield from self._checkpoint(0xDA5A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._a(m[(0x0713+r.x)&65535])
                                                    pass
                                                m[(0x0700+r.x)&65535]=r.a
                                                pass
                                            else:
                                                self._push(r.a)
                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                yield from self._checkpoint(0xDA3E)
                                                if not r.p&Z:
                                                    self._a(self._pop())
                                                    m[(0x070B+r.x)&65535]=self._nz(m[(0x070B+r.x)&65535]-1)
                                                    yield from self._checkpoint(0xDA51)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        yield from self._checkpoint(0xDA53)
                                                        if not r.p&N:
                                                            pass
                                                        else:
                                                            m[(0x070B+r.x)&65535]=r.a
                                                            pass
                                                        self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                        yield from self._checkpoint(0xDA5A)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._a(m[(0x0713+r.x)&65535])
                                                            pass
                                                        m[(0x0700+r.x)&65535]=r.a
                                                        pass
                                                    pass
                                                else:
                                                    self._a(self._pop())
                                                    m[(0x070A+r.x)&65535]=self._nz(m[(0x070A+r.x)&65535]-1)
                                                    yield from self._checkpoint(0xDA44)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        yield from self._checkpoint(0xDA46)
                                                        if not r.p&N:
                                                            self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                            yield from self._checkpoint(0xDA5A)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                self._a(m[(0x0713+r.x)&65535])
                                                                pass
                                                            m[(0x0700+r.x)&65535]=r.a
                                                            pass
                                                        else:
                                                            m[(0x070A+r.x)&65535]=r.a
                                                            yield from self._checkpoint(0xDA4B)
                                                            if r.p&N:
                                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                yield from self._checkpoint(0xDA5A)
                                                                if not r.p&Z:
                                                                    pass
                                                                else:
                                                                    self._a(m[(0x0713+r.x)&65535])
                                                                    pass
                                                                m[(0x0700+r.x)&65535]=r.a
                                                                pass
                                                            else:
                                                                self._a(self._pop())
                                                                m[(0x070B+r.x)&65535]=self._nz(m[(0x070B+r.x)&65535]-1)
                                                                yield from self._checkpoint(0xDA51)
                                                                if r.p&Z:
                                                                    pass
                                                                else:
                                                                    yield from self._checkpoint(0xDA53)
                                                                    if not r.p&N:
                                                                        pass
                                                                    else:
                                                                        m[(0x070B+r.x)&65535]=r.a
                                                                        pass
                                                                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                    yield from self._checkpoint(0xDA5A)
                                                                    if not r.p&Z:
                                                                        pass
                                                                    else:
                                                                        self._a(m[(0x0713+r.x)&65535])
                                                                        pass
                                                                    m[(0x0700+r.x)&65535]=r.a
                                                                    pass
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            raise _ContinueLoop_D99B
                                        else:
                                            self._compare(r.a,0xA0)
                                            yield from self._checkpoint(0xD9DA)
                                            if not r.p&C:
                                                m[0x07F7]=r.a
                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                m[(0x0708+r.x)&65535]=r.a
                                                self._a(m[0x07F7])
                                                bit_value=m[0x07F4]
                                                self._flag(Z,not(r.a&bit_value))
                                                self._flag(N,bit_value&128)
                                                self._flag(V,bit_value&64)
                                                yield from self._checkpoint(0xDB2F)
                                                if not r.p&V:
                                                    self._push(r.a)
                                                    self._a(r.a & 0x0F)
                                                    self._compare(r.a,0x0C)
                                                    yield from self._checkpoint(0xDB39)
                                                    if not r.p&C:
                                                        r.a=self._shift(r.a,True,rotate=False)
                                                        self._y(r.a)
                                                        self._a(m[(0x0704+r.x)&65535])
                                                        yield from self._checkpoint(0xDB43)
                                                        if not r.p&N:
                                                            pass
                                                        else:
                                                            self._a(r.y)
                                                            self._flag(C,False)
                                                            self._add(0x18)
                                                            self._y(r.a)
                                                            pass
                                                        self._a(m[0x07F3])
                                                        self._compare(r.a,0x04)
                                                        yield from self._checkpoint(0xDB4F)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._a(r.y)
                                                            self._flag(C,False)
                                                            self._add(0x30)
                                                            self._y(r.a)
                                                            pass
                                                        self._a(m[(0xDD06+r.y)&65535])
                                                        m[0x07F7]=r.a
                                                        self._a(m[(0xDD07+r.y)&65535])
                                                        m[0x07F8]=r.a
                                                        self._a(self._pop())
                                                        self._a(r.a & 0x70)
                                                        self._y(m[0x07F3])
                                                        self._compare(r.y,0x04)
                                                        yield from self._checkpoint(0xDB6A)
                                                        if not r.p&C:
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            yield from self._checkpoint(0xDB8A)
                                                            if r.p&Z:
                                                                pass
                                                            else:
                                                                self._y(r.a)
                                                                while True:  # natural loop $DB8D
                                                                    try:
                                                                        m[0x07F8]=self._shift(m[0x07F8],False,rotate=False)
                                                                        m[0x07F7]=self._shift(m[0x07F7],False,rotate=True)
                                                                        self._y(r.y-1)
                                                                        yield from self._checkpoint(0xDB94)
                                                                        if not r.p&Z:
                                                                            continue
                                                                        else:
                                                                            pass
                                                                        self._a(0x00)
                                                                        m[(0x070E+r.x)&65535]=r.a
                                                                        self._a(m[(0x0707+r.x)&65535])
                                                                        m[(0x0706+r.x)&65535]=r.a
                                                                        if not (yield from self._local_call(self.channel_disabled_mask,0xDBA1,0xDBA4)):return
                                                                        self._compare(r.y,0x04)
                                                                        yield from self._checkpoint(0xDBA6)
                                                                        if r.p&C:
                                                                            pass
                                                                        else:
                                                                            self._a(m[(0xDD4E+r.y)&65535])
                                                                            self._a(r.a | m[0x07F6])
                                                                            m[0x07F6]=r.a
                                                                            m[0x4015]=r.a
                                                                            pass
                                                                        self._a(m[0x07F8])
                                                                        self._push(r.a)
                                                                        self._a(m[0x07F7])
                                                                        self._push(r.a)
                                                                        if not (yield from self._local_call(self.emit_current_volume,0xDBBC,0xDBBF)):return
                                                                        self._compare(r.y,0x10)
                                                                        yield from self._checkpoint(0xDBC1)
                                                                        if r.p&C:
                                                                            pass
                                                                        else:
                                                                            self._a(m[(0x0709+r.x)&65535])
                                                                            m[(0x4001+r.y)&65535]=r.a
                                                                            pass
                                                                        self._a(self._pop())
                                                                        if not (yield from self._local_call(self.write_frequency_high,0xDBCA,0xDBCD)):return
                                                                        self._compare(r.a,0x02)
                                                                        yield from self._checkpoint(0xDBCF)
                                                                        if not r.p&C:
                                                                            self._a(0x02)
                                                                            pass
                                                                        else:
                                                                            self._compare(r.a,0xFE)
                                                                            yield from self._checkpoint(0xDBD3)
                                                                            if not r.p&C:
                                                                                pass
                                                                            else:
                                                                                self._a(0xFD)
                                                                                yield from self._checkpoint(0xDBD7)
                                                                                if not r.p&Z:
                                                                                    pass
                                                                                else:
                                                                                    self._a(0x02)
                                                                                    pass
                                                                                pass
                                                                            pass
                                                                        m[(0x0712+r.x)&65535]=r.a
                                                                        self._a(self._pop())
                                                                        self._compare(r.y,0x10)
                                                                        yield from self._checkpoint(0xDC1A)
                                                                        if r.p&C:
                                                                            self._push(r.a)
                                                                            self._a(r.y)
                                                                            r.a=self._shift(r.a,True,rotate=False)
                                                                            self._a(r.a | 0x62)
                                                                            m[0xF800]=r.a
                                                                            self._a(self._pop())
                                                                            m[0x4800]=r.a
                                                                            yield from self._checkpoint(0xDC30)
                                                                            self._rts();return
                                                                        else:
                                                                            self._a(r.a & 0x07)
                                                                            self._a(r.a | 0x08)
                                                                            m[(0x4003+r.y)&65535]=r.a
                                                                            yield from self._checkpoint(0xDC23)
                                                                            self._rts();return
                                                                    except _ContinueLoop_DB8D:
                                                                        continue
                                                            pass
                                                        else:
                                                            self._compare(r.a,0x40)
                                                            yield from self._checkpoint(0xDB6E)
                                                            if not r.p&Z:
                                                                self._add(0x30,subtract=True)
                                                                yield from self._checkpoint(0xDB7B)
                                                                if r.p&Z:
                                                                    pass
                                                                else:
                                                                    yield from self._checkpoint(0xDB7D)
                                                                    if not r.p&C:
                                                                        pass
                                                                    else:
                                                                        self._a(0xB0)
                                                                        pass
                                                                    self._a(r.a ^ 0xFF)
                                                                    self._flag(C,False)
                                                                    self._add(0x01)
                                                                    pass
                                                                r.a=self._shift(r.a,False,rotate=False)
                                                                r.a=self._shift(r.a,False,rotate=False)
                                                                r.a=self._shift(r.a,False,rotate=False)
                                                                r.a=self._shift(r.a,False,rotate=False)
                                                                yield from self._checkpoint(0xDB8A)
                                                                if r.p&Z:
                                                                    pass
                                                                else:
                                                                    self._y(r.a)
                                                                    while True:  # natural loop $DB8D
                                                                        try:
                                                                            m[0x07F8]=self._shift(m[0x07F8],False,rotate=False)
                                                                            m[0x07F7]=self._shift(m[0x07F7],False,rotate=True)
                                                                            self._y(r.y-1)
                                                                            yield from self._checkpoint(0xDB94)
                                                                            if not r.p&Z:
                                                                                continue
                                                                            else:
                                                                                pass
                                                                            self._a(0x00)
                                                                            m[(0x070E+r.x)&65535]=r.a
                                                                            self._a(m[(0x0707+r.x)&65535])
                                                                            m[(0x0706+r.x)&65535]=r.a
                                                                            if not (yield from self._local_call(self.channel_disabled_mask,0xDBA1,0xDBA4)):return
                                                                            self._compare(r.y,0x04)
                                                                            yield from self._checkpoint(0xDBA6)
                                                                            if r.p&C:
                                                                                pass
                                                                            else:
                                                                                self._a(m[(0xDD4E+r.y)&65535])
                                                                                self._a(r.a | m[0x07F6])
                                                                                m[0x07F6]=r.a
                                                                                m[0x4015]=r.a
                                                                                pass
                                                                            self._a(m[0x07F8])
                                                                            self._push(r.a)
                                                                            self._a(m[0x07F7])
                                                                            self._push(r.a)
                                                                            if not (yield from self._local_call(self.emit_current_volume,0xDBBC,0xDBBF)):return
                                                                            self._compare(r.y,0x10)
                                                                            yield from self._checkpoint(0xDBC1)
                                                                            if r.p&C:
                                                                                pass
                                                                            else:
                                                                                self._a(m[(0x0709+r.x)&65535])
                                                                                m[(0x4001+r.y)&65535]=r.a
                                                                                pass
                                                                            self._a(self._pop())
                                                                            if not (yield from self._local_call(self.write_frequency_high,0xDBCA,0xDBCD)):return
                                                                            self._compare(r.a,0x02)
                                                                            yield from self._checkpoint(0xDBCF)
                                                                            if not r.p&C:
                                                                                self._a(0x02)
                                                                                pass
                                                                            else:
                                                                                self._compare(r.a,0xFE)
                                                                                yield from self._checkpoint(0xDBD3)
                                                                                if not r.p&C:
                                                                                    pass
                                                                                else:
                                                                                    self._a(0xFD)
                                                                                    yield from self._checkpoint(0xDBD7)
                                                                                    if not r.p&Z:
                                                                                        pass
                                                                                    else:
                                                                                        self._a(0x02)
                                                                                        pass
                                                                                    pass
                                                                                pass
                                                                            m[(0x0712+r.x)&65535]=r.a
                                                                            self._a(self._pop())
                                                                            self._compare(r.y,0x10)
                                                                            yield from self._checkpoint(0xDC1A)
                                                                            if r.p&C:
                                                                                self._push(r.a)
                                                                                self._a(r.y)
                                                                                r.a=self._shift(r.a,True,rotate=False)
                                                                                self._a(r.a | 0x62)
                                                                                m[0xF800]=r.a
                                                                                self._a(self._pop())
                                                                                m[0x4800]=r.a
                                                                                yield from self._checkpoint(0xDC30)
                                                                                self._rts();return
                                                                            else:
                                                                                self._a(r.a & 0x07)
                                                                                self._a(r.a | 0x08)
                                                                                m[(0x4003+r.y)&65535]=r.a
                                                                                yield from self._checkpoint(0xDC23)
                                                                                self._rts();return
                                                                        except _ContinueLoop_DB8D:
                                                                            continue
                                                                pass
                                                            else:
                                                                m[0x07F7]=self._shift(m[0x07F7],True,rotate=False)
                                                                m[0x07F8]=self._shift(m[0x07F8],True,rotate=True)
                                                                pass
                                                            pass
                                                        self._a(0x00)
                                                        m[(0x070E+r.x)&65535]=r.a
                                                        self._a(m[(0x0707+r.x)&65535])
                                                        m[(0x0706+r.x)&65535]=r.a
                                                        if not (yield from self._local_call(self.channel_disabled_mask,0xDBA1,0xDBA4)):return
                                                        self._compare(r.y,0x04)
                                                        yield from self._checkpoint(0xDBA6)
                                                        if r.p&C:
                                                            pass
                                                        else:
                                                            self._a(m[(0xDD4E+r.y)&65535])
                                                            self._a(r.a | m[0x07F6])
                                                            m[0x07F6]=r.a
                                                            m[0x4015]=r.a
                                                            pass
                                                        self._a(m[0x07F8])
                                                        self._push(r.a)
                                                        self._a(m[0x07F7])
                                                        self._push(r.a)
                                                        if not (yield from self._local_call(self.emit_current_volume,0xDBBC,0xDBBF)):return
                                                        self._compare(r.y,0x10)
                                                        yield from self._checkpoint(0xDBC1)
                                                        if r.p&C:
                                                            pass
                                                        else:
                                                            self._a(m[(0x0709+r.x)&65535])
                                                            m[(0x4001+r.y)&65535]=r.a
                                                            pass
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.write_frequency_high,0xDBCA,0xDBCD)):return
                                                        self._compare(r.a,0x02)
                                                        yield from self._checkpoint(0xDBCF)
                                                        if not r.p&C:
                                                            self._a(0x02)
                                                            pass
                                                        else:
                                                            self._compare(r.a,0xFE)
                                                            yield from self._checkpoint(0xDBD3)
                                                            if not r.p&C:
                                                                pass
                                                            else:
                                                                self._a(0xFD)
                                                                yield from self._checkpoint(0xDBD7)
                                                                if not r.p&Z:
                                                                    pass
                                                                else:
                                                                    self._a(0x02)
                                                                    pass
                                                                pass
                                                            pass
                                                        m[(0x0712+r.x)&65535]=r.a
                                                        self._a(self._pop())
                                                        self._compare(r.y,0x10)
                                                        yield from self._checkpoint(0xDC1A)
                                                        if r.p&C:
                                                            self._push(r.a)
                                                            self._a(r.y)
                                                            r.a=self._shift(r.a,True,rotate=False)
                                                            self._a(r.a | 0x62)
                                                            m[0xF800]=r.a
                                                            self._a(self._pop())
                                                            m[0x4800]=r.a
                                                            yield from self._checkpoint(0xDC30)
                                                            self._rts();return
                                                        else:
                                                            self._a(r.a & 0x07)
                                                            self._a(r.a | 0x08)
                                                            m[(0x4003+r.y)&65535]=r.a
                                                            yield from self._checkpoint(0xDC23)
                                                            self._rts();return
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(m[(0x0706+r.x)&65535])
                                                        self._a(r.a & 0xC0)
                                                        bit_value=m[0x07F4]
                                                        self._flag(Z,not(r.a&bit_value))
                                                        self._flag(N,bit_value&128)
                                                        self._flag(V,bit_value&64)
                                                        yield from self._checkpoint(0xDBF9)
                                                        if not r.p&N:
                                                            pass
                                                        else:
                                                            self._a(0x00)
                                                            pass
                                                        m[(0x0706+r.x)&65535]=r.a
                                                        return (yield from self.apply_volume())
                                                else:
                                                    self._compare(r.a,0x10)
                                                    yield from self._checkpoint(0xDBE4)
                                                    if r.p&C:
                                                        self._a(m[(0x0706+r.x)&65535])
                                                        self._a(r.a & 0xC0)
                                                        bit_value=m[0x07F4]
                                                        self._flag(Z,not(r.a&bit_value))
                                                        self._flag(N,bit_value&128)
                                                        self._flag(V,bit_value&64)
                                                        yield from self._checkpoint(0xDBF9)
                                                        if not r.p&N:
                                                            pass
                                                        else:
                                                            self._a(0x00)
                                                            pass
                                                        m[(0x0706+r.x)&65535]=r.a
                                                        return (yield from self.apply_volume())
                                                    else:
                                                        m[0x07F7]=r.a
                                                        self._a(0x00)
                                                        m[0x07F8]=r.a
                                                        yield from self._checkpoint(0xDBEE)
                                                        if r.p&Z:
                                                            self._a(0x00)
                                                            m[(0x070E+r.x)&65535]=r.a
                                                            self._a(m[(0x0707+r.x)&65535])
                                                            m[(0x0706+r.x)&65535]=r.a
                                                            if not (yield from self._local_call(self.channel_disabled_mask,0xDBA1,0xDBA4)):return
                                                            self._compare(r.y,0x04)
                                                            yield from self._checkpoint(0xDBA6)
                                                            if r.p&C:
                                                                pass
                                                            else:
                                                                self._a(m[(0xDD4E+r.y)&65535])
                                                                self._a(r.a | m[0x07F6])
                                                                m[0x07F6]=r.a
                                                                m[0x4015]=r.a
                                                                pass
                                                            self._a(m[0x07F8])
                                                            self._push(r.a)
                                                            self._a(m[0x07F7])
                                                            self._push(r.a)
                                                            if not (yield from self._local_call(self.emit_current_volume,0xDBBC,0xDBBF)):return
                                                            self._compare(r.y,0x10)
                                                            yield from self._checkpoint(0xDBC1)
                                                            if r.p&C:
                                                                pass
                                                            else:
                                                                self._a(m[(0x0709+r.x)&65535])
                                                                m[(0x4001+r.y)&65535]=r.a
                                                                pass
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.write_frequency_high,0xDBCA,0xDBCD)):return
                                                            self._compare(r.a,0x02)
                                                            yield from self._checkpoint(0xDBCF)
                                                            if not r.p&C:
                                                                self._a(0x02)
                                                                pass
                                                            else:
                                                                self._compare(r.a,0xFE)
                                                                yield from self._checkpoint(0xDBD3)
                                                                if not r.p&C:
                                                                    pass
                                                                else:
                                                                    self._a(0xFD)
                                                                    yield from self._checkpoint(0xDBD7)
                                                                    if not r.p&Z:
                                                                        pass
                                                                    else:
                                                                        self._a(0x02)
                                                                        pass
                                                                    pass
                                                                pass
                                                            m[(0x0712+r.x)&65535]=r.a
                                                            self._a(self._pop())
                                                            self._compare(r.y,0x10)
                                                            yield from self._checkpoint(0xDC1A)
                                                            if r.p&C:
                                                                self._push(r.a)
                                                                self._a(r.y)
                                                                r.a=self._shift(r.a,True,rotate=False)
                                                                self._a(r.a | 0x62)
                                                                m[0xF800]=r.a
                                                                self._a(self._pop())
                                                                m[0x4800]=r.a
                                                                yield from self._checkpoint(0xDC30)
                                                                self._rts();return
                                                            else:
                                                                self._a(r.a & 0x07)
                                                                self._a(r.a | 0x08)
                                                                m[(0x4003+r.y)&65535]=r.a
                                                                yield from self._checkpoint(0xDC23)
                                                                self._rts();return
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(m[(0x0706+r.x)&65535])
                                                            self._a(r.a & 0xC0)
                                                            bit_value=m[0x07F4]
                                                            self._flag(Z,not(r.a&bit_value))
                                                            self._flag(N,bit_value&128)
                                                            self._flag(V,bit_value&64)
                                                            yield from self._checkpoint(0xDBF9)
                                                            if not r.p&N:
                                                                pass
                                                            else:
                                                                self._a(0x00)
                                                                pass
                                                            m[(0x0706+r.x)&65535]=r.a
                                                            return (yield from self.apply_volume())
                                            else:
                                                yield from self._checkpoint(0xDA65)
                                                if not r.p&Z:
                                                    self._compare(r.a,0xA1)
                                                    yield from self._checkpoint(0xDA78)
                                                    if not r.p&Z:
                                                        self._compare(r.a,0xA2)
                                                        yield from self._checkpoint(0xDA84)
                                                        if not r.p&Z:
                                                            self._compare(r.a,0xA3)
                                                            yield from self._checkpoint(0xDA9E)
                                                            if not r.p&Z:
                                                                self._compare(r.a,0xA4)
                                                                yield from self._checkpoint(0xDABE)
                                                                if not r.p&Z:
                                                                    self._compare(r.a,0xAD)
                                                                    yield from self._checkpoint(0xDACD)
                                                                    if not r.p&Z:
                                                                        self._compare(r.a,0xAE)
                                                                        yield from self._checkpoint(0xDAFA)
                                                                        if not r.p&Z:
                                                                            self._compare(r.a,0xAF)
                                                                            yield from self._checkpoint(0xDB0A)
                                                                            if not r.p&Z:
                                                                                pass
                                                                            else:
                                                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                                self._a(r.a & 0x0F)
                                                                                m[(0x0705+r.x)&65535]=r.a
                                                                                self._a(m[(0x0704+r.x)&65535])
                                                                                self._a(r.a & 0xF0)
                                                                                self._a(r.a | m[(0x0705+r.x)&65535])
                                                                                m[(0x0704+r.x)&65535]=r.a
                                                                                pass
                                                                            pass
                                                                        else:
                                                                            m[(0x0704+r.x)&65535]=self._shift(m[(0x0704+r.x)&65535],True,rotate=False)
                                                                            self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                            r.a=self._shift(r.a,True,rotate=False)
                                                                            m[(0x0704+r.x)&65535]=self._shift(m[(0x0704+r.x)&65535],False,rotate=True)
                                                                            pass
                                                                        continue
                                                                    else:
                                                                        self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                        self._push(r.a)
                                                                        self._a(0x00)
                                                                        m[0x00F1]=r.a
                                                                        self._a(m[(0x0700+r.x)&65535])
                                                                        r.a=self._shift(r.a,True,rotate=False)
                                                                        m[0x00F1]=self._shift(m[0x00F1],True,rotate=True)
                                                                        self._add(m[(0x0702+r.x)&65535])
                                                                        m[(0x0702+r.x)&65535]=r.a
                                                                        self._a(m[(0x0703+r.x)&65535])
                                                                        self._add(m[0x00F1])
                                                                        m[(0x0703+r.x)&65535]=r.a
                                                                        self._a(0x00)
                                                                        m[(0x0700+r.x)&65535]=r.a
                                                                        self._a(self._pop())
                                                                        yield from self._checkpoint(0xDAF3)
                                                                        if not r.p&Z:
                                                                            continue
                                                                        else:
                                                                            while True:  # natural loop $D958
                                                                                try:
                                                                                    self._a(m[(0x0702+r.x)&65535])
                                                                                    m[0x00F0]=r.a
                                                                                    self._a(m[(0x0703+r.x)&65535])
                                                                                    m[0x00F1]=r.a
                                                                                    self._y(0x00)
                                                                                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                                    self._a(r.a & 0x0F)
                                                                                    m[(0x0704+r.x)&65535]=r.a
                                                                                    m[(0x0705+r.x)&65535]=r.a
                                                                                    self._y(r.y+1)
                                                                                    if not (yield from self._local_call(self.stop_note,0xD971,0xD974)):return
                                                                                    self._y(r.y+1)
                                                                                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                                    self._a(r.a | m[0x07F7])
                                                                                    m[(0x0706+r.x)&65535]=r.a
                                                                                    m[(0x0707+r.x)&65535]=r.a
                                                                                    self._y(r.y+1)
                                                                                    self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                                    m[(0x0709+r.x)&65535]=r.a
                                                                                    self._a(0x00)
                                                                                    m[(0x070A+r.x)&65535]=r.a
                                                                                    m[(0x070B+r.x)&65535]=r.a
                                                                                    m[(0x070C+r.x)&65535]=r.a
                                                                                    m[(0x070F+r.x)&65535]=r.a
                                                                                    self._a(0x02)
                                                                                    m[(0x0700+r.x)&65535]=r.a
                                                                                    yield from self._checkpoint(0xD999)
                                                                                    if not r.p&Z:
                                                                                        while True:  # natural loop $D940
                                                                                            try:
                                                                                                if not (yield from self._local_call(self.decode_stream_commands,0xD940,0xD943)):return
                                                                                                while True:  # natural loop $D943
                                                                                                    try:
                                                                                                        self._y(m[0x07F3])
                                                                                                        self._a(m[(0xDD4E+r.y)&65535])
                                                                                                        self._a(r.a | m[0x07F2])
                                                                                                        m[0x07F2]=r.a
                                                                                                        while True:  # natural loop $D94F
                                                                                                            try:
                                                                                                                self._a(r.x)
                                                                                                                self._flag(C,False)
                                                                                                                self._add(0x16)
                                                                                                                self._compare(r.a,0xF2)
                                                                                                                yield from self._checkpoint(0xD955)
                                                                                                                if not r.p&Z:
                                                                                                                    self._x(r.a)
                                                                                                                    self._a(m[(0x0701+r.x)&65535])
                                                                                                                    self._a(r.a & 0x07)
                                                                                                                    m[0x07F3]=r.a
                                                                                                                    self._y(r.a)
                                                                                                                    r.a=self._shift(r.a,True,rotate=False)
                                                                                                                    r.a=self._shift(r.a,True,rotate=False)
                                                                                                                    m[0x07F5]=r.a
                                                                                                                    self._a(m[(0xDD56+r.y)&65535])
                                                                                                                    m[0x07F4]=r.a
                                                                                                                    self._a(m[(0x0700+r.x)&65535])
                                                                                                                    yield from self._checkpoint(0xD903)
                                                                                                                    if r.p&Z:
                                                                                                                        raise _ContinueLoop_D958
                                                                                                                    else:
                                                                                                                        self._compare(r.a,0xFF)
                                                                                                                        yield from self._checkpoint(0xD907)
                                                                                                                        if r.p&Z:
                                                                                                                            pass
                                                                                                                        else:
                                                                                                                            if not (yield from self._local_call(self.apply_volume_slide,0xD909,0xD90C)):return
                                                                                                                            m[(0x070E+r.x)&65535]=self._nz(m[(0x070E+r.x)&65535]+1)
                                                                                                                            self._a(m[(0x070E+r.x)&65535])
                                                                                                                            self._compare(r.a,m[(0x070D+r.x)&65535])
                                                                                                                            yield from self._checkpoint(0xD915)
                                                                                                                            if not r.p&C:
                                                                                                                                m[(0x0705+r.x)&65535]=self._nz(m[(0x0705+r.x)&65535]-1)
                                                                                                                                yield from self._checkpoint(0xD920)
                                                                                                                                if not r.p&N:
                                                                                                                                    if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                                                                                                                    pass
                                                                                                                                else:
                                                                                                                                    self._a(m[(0x0704+r.x)&65535])
                                                                                                                                    self._a(r.a & 0x0F)
                                                                                                                                    m[(0x0705+r.x)&65535]=r.a
                                                                                                                                    if not (yield from self._local_call(self.apply_vibrato,0xD92A,0xD92D)):return
                                                                                                                                    self._a(m[(0x0715+r.x)&65535])
                                                                                                                                    yield from self._checkpoint(0xD930)
                                                                                                                                    if r.p&Z:
                                                                                                                                        m[(0x0708+r.x)&65535]=self._nz(m[(0x0708+r.x)&65535]-1)
                                                                                                                                        yield from self._checkpoint(0xD938)
                                                                                                                                        if r.p&Z:
                                                                                                                                            raise _ContinueLoop_D940
                                                                                                                                        else:
                                                                                                                                            if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                                                                                                                            pass
                                                                                                                                        pass
                                                                                                                                    else:
                                                                                                                                        m[(0x0715+r.x)&65535]=self._nz(m[(0x0715+r.x)&65535]-1)
                                                                                                                                        m[(0x0708+r.x)&65535]=self._nz(m[(0x0708+r.x)&65535]-1)
                                                                                                                                        yield from self._checkpoint(0xD938)
                                                                                                                                        if r.p&Z:
                                                                                                                                            raise _ContinueLoop_D940
                                                                                                                                        else:
                                                                                                                                            if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                                                                                                                            pass
                                                                                                                                        pass
                                                                                                                                    pass
                                                                                                                                raise _ContinueLoop_D943
                                                                                                                            else:
                                                                                                                                self._a(m[(0x070D+r.x)&65535])
                                                                                                                                m[(0x070E+r.x)&65535]=r.a
                                                                                                                                m[(0x0705+r.x)&65535]=self._nz(m[(0x0705+r.x)&65535]-1)
                                                                                                                                yield from self._checkpoint(0xD920)
                                                                                                                                if not r.p&N:
                                                                                                                                    if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                                                                                                                    pass
                                                                                                                                else:
                                                                                                                                    self._a(m[(0x0704+r.x)&65535])
                                                                                                                                    self._a(r.a & 0x0F)
                                                                                                                                    m[(0x0705+r.x)&65535]=r.a
                                                                                                                                    if not (yield from self._local_call(self.apply_vibrato,0xD92A,0xD92D)):return
                                                                                                                                    self._a(m[(0x0715+r.x)&65535])
                                                                                                                                    yield from self._checkpoint(0xD930)
                                                                                                                                    if r.p&Z:
                                                                                                                                        m[(0x0708+r.x)&65535]=self._nz(m[(0x0708+r.x)&65535]-1)
                                                                                                                                        yield from self._checkpoint(0xD938)
                                                                                                                                        if r.p&Z:
                                                                                                                                            raise _ContinueLoop_D940
                                                                                                                                        else:
                                                                                                                                            if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                                                                                                                            pass
                                                                                                                                        pass
                                                                                                                                    else:
                                                                                                                                        m[(0x0715+r.x)&65535]=self._nz(m[(0x0715+r.x)&65535]-1)
                                                                                                                                        m[(0x0708+r.x)&65535]=self._nz(m[(0x0708+r.x)&65535]-1)
                                                                                                                                        yield from self._checkpoint(0xD938)
                                                                                                                                        if r.p&Z:
                                                                                                                                            raise _ContinueLoop_D940
                                                                                                                                        else:
                                                                                                                                            if not (yield from self._local_call(self.apply_volume,0xD93A,0xD93D)):return
                                                                                                                                            pass
                                                                                                                                        pass
                                                                                                                                    pass
                                                                                                                                raise _ContinueLoop_D943
                                                                                                                        continue
                                                                                                                else:
                                                                                                                    yield from self._checkpoint(0xD957)
                                                                                                                    self._rts();return
                                                                                                            except _ContinueLoop_D94F:
                                                                                                                continue
                                                                                                    except _ContinueLoop_D943:
                                                                                                        continue
                                                                                            except _ContinueLoop_D940:
                                                                                                continue
                                                                                    else:
                                                                                        raise _ContinueLoop_D99B
                                                                                except _ContinueLoop_D958:
                                                                                    continue
                                                                else:
                                                                    self._a(m[(0x0701+r.x)&65535])
                                                                    self._a(r.a & 0x07)
                                                                    m[(0x0701+r.x)&65535]=r.a
                                                                    continue
                                                            else:
                                                                self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                                yield from self._checkpoint(0xDAA2)
                                                                if r.p&N:
                                                                    self._a(m[(0x0701+r.x)&65535])
                                                                    self._a(r.a & 0x07)
                                                                    m[(0x0701+r.x)&65535]=r.a
                                                                    pass
                                                                else:
                                                                    self._push(r.a)
                                                                    self._a(r.a & 0x0F)
                                                                    r.a=self._shift(r.a,True,rotate=False)
                                                                    m[(0x0714+r.x)&65535]=r.a
                                                                    m[(0x0715+r.x)&65535]=r.a
                                                                    self._a(self._pop())
                                                                    self._a(r.a & 0x70)
                                                                    self._a(r.a | m[(0x0701+r.x)&65535])
                                                                    self._a(r.a | 0x80)
                                                                    m[(0x0701+r.x)&65535]=r.a
                                                                    pass
                                                                continue
                                                        else:
                                                            if not (yield from self._local_call(self.stop_note,0xDA86,0xDA89)):return
                                                            yield from self._checkpoint(0xDA89)
                                                            if r.p&C:
                                                                pass
                                                            else:
                                                                self._a(m[(0x0706+r.x)&65535])
                                                                self._a(r.a & 0x1F)
                                                                self._a(r.a | m[0x07F7])
                                                                pass
                                                            m[(0x0706+r.x)&65535]=r.a
                                                            m[(0x0707+r.x)&65535]=r.a
                                                            continue
                                                    else:
                                                        self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                        m[(0x0709+r.x)&65535]=r.a
                                                        continue
                                                else:
                                                    bit_value=m[0x07F4]
                                                    self._flag(Z,not(r.a&bit_value))
                                                    self._flag(N,bit_value&128)
                                                    self._flag(V,bit_value&64)
                                                    yield from self._checkpoint(0xDA6A)
                                                    if r.p&N:
                                                        pass
                                                    else:
                                                        self._a(m[(0x0706+r.x)&65535])
                                                        self._a(r.a & 0xC0)
                                                        self._a(r.a | m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
                                                        m[(0x0706+r.x)&65535]=r.a
                                                        m[(0x0707+r.x)&65535]=r.a
                                                        pass
                                                    continue
                    except _ContinueLoop_D9BD:
                        continue
            except _ContinueLoop_D99B:
                continue

    def write_frequency_high(self):
        """$DC03: write frequency high; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDC03)
        self._compare(r.y,0x10)
        yield from self._checkpoint(0xDC05)
        if r.p&C:
            self._push(r.a)
            self._a(r.y)
            r.a=self._shift(r.a,True,rotate=False)
            self._a(r.a | 0x60)
            m[0xF800]=r.a
            self._a(self._pop())
            m[0x4800]=r.a
            yield from self._checkpoint(0xDC17)
            self._rts();return
        else:
            m[(0x4002+r.y)&65535]=r.a
            yield from self._checkpoint(0xDC0A)
            self._rts();return

    def channel_disabled_mask(self):
        """$DC31: channel disabled mask; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDC31)
        self._y(m[0x07F3])
        self._a(m[(0xDD4E+r.y)&65535])
        bit_value=m[0x07F2]
        self._flag(Z,not(r.a&bit_value))
        self._flag(N,bit_value&128)
        self._flag(V,bit_value&64)
        yield from self._checkpoint(0xDC3A)
        if r.p&Z:
            pass
        else:
            self._a(self._pop())
            self._a(self._pop())
            pass
        yield from self._checkpoint(0xDC3E)
        self._rts();return

    def stop_note(self):
        """$DC3F: stop note; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDC3F)
        bit_value=m[0x07F4]
        self._flag(Z,not(r.a&bit_value))
        self._flag(N,bit_value&128)
        self._flag(V,bit_value&64)
        yield from self._checkpoint(0xDC42)
        if r.p&N:
            self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
            self._a(r.a & 0x7F)
            m[0x07F7]=r.a
            self._flag(C,True)
            yield from self._checkpoint(0xDC58)
            self._rts();return
        else:
            self._a(m[((m[0xF0]|m[0xF1]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=True)
            r.a=self._shift(r.a,False,rotate=True)
            r.a=self._shift(r.a,False,rotate=True)
            self._a(r.a & 0xC0)
            m[0x07F7]=r.a
            self._flag(C,False)
            yield from self._checkpoint(0xDC4F)
            self._rts();return

    def apply_vibrato(self):
        """$DC90: apply vibrato; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDC90)
        bit_value=m[0x07F4]
        self._flag(Z,not(r.a&bit_value))
        self._flag(N,bit_value&128)
        self._flag(V,bit_value&64)
        yield from self._checkpoint(0xDC93)
        if r.p&N:
            yield from self._checkpoint(0xDCC6)
            self._rts();return
        else:
            self._a(m[(0x070F+r.x)&65535])
            yield from self._checkpoint(0xDC98)
            if r.p&Z:
                yield from self._checkpoint(0xDCC6)
                self._rts();return
            else:
                m[(0x0711+r.x)&65535]=self._nz(m[(0x0711+r.x)&65535]-1)
                yield from self._checkpoint(0xDC9D)
                if not r.p&Z:
                    yield from self._checkpoint(0xDCC6)
                    self._rts();return
                else:
                    self._a(m[(0x0710+r.x)&65535])
                    m[(0x0711+r.x)&65535]=r.a
                    self._a(m[(0x0706+r.x)&65535])
                    self._a(r.a & 0x1F)
                    m[0x07F7]=r.a
                    self._a(r.a & 0x10)
                    yield from self._checkpoint(0xDCAF)
                    if r.p&Z:
                        yield from self._checkpoint(0xDCC6)
                        self._rts();return
                    else:
                        self._a(m[(0x070F+r.x)&65535])
                        yield from self._checkpoint(0xDCB4)
                        if r.p&N:
                            m[(0x070F+r.x)&65535]=self._nz(m[(0x070F+r.x)&65535]+1)
                            self._a(m[0x07F7])
                            self._compare(r.a,0x10)
                            yield from self._checkpoint(0xDCCF)
                            if r.p&Z:
                                yield from self._checkpoint(0xDCC6)
                                self._rts();return
                            else:
                                m[(0x0706+r.x)&65535]=self._nz(m[(0x0706+r.x)&65535]-1)
                                m[(0x0707+r.x)&65535]=self._nz(m[(0x0707+r.x)&65535]-1)
                                yield from self._checkpoint(0xDCD7)
                                self._rts();return
                        else:
                            m[(0x070F+r.x)&65535]=self._nz(m[(0x070F+r.x)&65535]-1)
                            self._a(m[0x07F7])
                            self._compare(r.a,0x1F)
                            yield from self._checkpoint(0xDCBE)
                            if r.p&Z:
                                pass
                            else:
                                m[(0x0706+r.x)&65535]=self._nz(m[(0x0706+r.x)&65535]+1)
                                m[(0x0707+r.x)&65535]=self._nz(m[(0x0707+r.x)&65535]+1)
                                pass
                            yield from self._checkpoint(0xDCC6)
                            self._rts();return

    def apply_volume_slide(self):
        """$DCD8: apply volume slide; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDCD8)
        if not (yield from self._local_call(self.channel_disabled_mask,0xDCD8,0xDCDB)):return
        bit_value=m[0x07F4]
        self._flag(Z,not(r.a&bit_value))
        self._flag(N,bit_value&128)
        self._flag(V,bit_value&64)
        yield from self._checkpoint(0xDCDE)
        if r.p&V:
            pass
        else:
            self._a(m[(0x0715+r.x)&65535])
            yield from self._checkpoint(0xDCE3)
            if not r.p&Z:
                pass
            else:
                self._a(m[(0x0701+r.x)&65535])
                yield from self._checkpoint(0xDCE8)
                if not r.p&N:
                    pass
                else:
                    self._a(r.a & 0x70)
                    m[0x07F7]=r.a
                    self._a(m[0x07F9])
                    self._a(r.a & 0x0F)
                    self._a(r.a | m[0x07F7])
                    self._y(r.a)
                    self._a(m[(0xDD5E+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[(0x0712+r.x)&65535])
                    self._y(m[0x07F5])
                    m[(0x4002+r.y)&65535]=r.a
                    pass
                pass
            pass
        yield from self._checkpoint(0xDD05)
        self._rts();return

    def apply_volume(self):
        """$DF6E: apply volume; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDF6E)
        if not (yield from self._local_call(self.channel_disabled_mask,0xDF6E,0xDF71)):return
        return (yield from self.emit_current_volume())

    def emit_current_volume(self):
        """$DF71: emit current volume; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDF71)
        bit_value=m[0x07F4]
        self._flag(Z,not(r.a&bit_value))
        self._flag(N,bit_value&128)
        self._flag(V,bit_value&64)
        yield from self._checkpoint(0xDF74)
        if r.p&N:
            self._y(m[0x07F5])
            self._a(m[(0x0706+r.x)&65535])
            m[(0x4000+r.y)&65535]=r.a
            yield from self._checkpoint(0xDFBE)
            self._rts();return
        else:
            self._a(m[(0x070C+r.x)&65535])
            yield from self._checkpoint(0xDF79)
            if r.p&Z:
                self._a(m[(0x0706+r.x)&65535])
                self._a(r.a & 0x10)
                r.a=self._shift(r.a,True,rotate=False)
                self._a(r.a | m[(0x0706+r.x)&65535])
                pass
            else:
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._push(r.a)
                self._a(0x00)
                m[0x07F7]=r.a
                self._a(m[(0x070E+r.x)&65535])
                self._y(0x03)
                while True:  # natural loop $DC68
                    try:
                        r.a=self._shift(r.a,True,rotate=False)
                        self._compare(r.a,m[(0x070D+r.x)&65535])
                        yield from self._checkpoint(0xDC6C)
                        if not r.p&C:
                            pass
                        else:
                            self._add(m[(0x070D+r.x)&65535],subtract=True)
                            pass
                        m[0x07F7]=self._shift(m[0x07F7],True,rotate=True)
                        self._y(r.y-1)
                        yield from self._checkpoint(0xDC75)
                        if not r.p&N:
                            continue
                        else:
                            pass
                        self._a(self._pop())
                        self._a(r.a | m[0x07F7])
                        self._y(r.a)
                        self._a(m[(0x0706+r.x)&65535])
                        self._a(r.a & 0x0F)
                        self._a(r.a | m[(0xDDCE+r.y)&65535])
                        self._y(r.a)
                        self._a(m[(0x0706+r.x)&65535])
                        self._a(r.a & 0xC0)
                        self._a(r.a | m[(0xDE6E+r.y)&65535])
                        self._y(m[0x07F5])
                        self._compare(r.y,0x10)
                        yield from self._checkpoint(0xDF8C)
                        if r.p&C:
                            return (yield from self.write_N163_volume_and_wave_pair())
                        else:
                            m[(0x4000+r.y)&65535]=r.a
                            yield from self._checkpoint(0xDF91)
                            self._rts();return
                    except _ContinueLoop_DC68:
                        continue
            self._y(m[0x07F5])
            self._compare(r.y,0x10)
            yield from self._checkpoint(0xDF8C)
            if r.p&C:
                return (yield from self.write_N163_volume_and_wave_pair())
            else:
                m[(0x4000+r.y)&65535]=r.a
                yield from self._checkpoint(0xDF91)
                self._rts();return

    def write_N163_volume_and_wave_pair(self):
        """$DF92: write N163 volume and wave pair; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xDF92)
        self._push(r.a)
        self._push(r.a)
        self._a(r.y)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | 0x67)
        self._y(r.a)
        m[0xF800]=r.a
        self._a(self._pop())
        self._a(r.a & 0x0F)
        self._a(r.a | 0x30)
        m[0x4800]=r.a
        self._y(r.y-1)
        m[0xF800]=r.y
        self._a(self._pop())
        self._a(r.a & 0xC0)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x4800]=r.a
        self._y(m[0x07F5])
        yield from self._checkpoint(0xDFB4)
        self._rts();return

