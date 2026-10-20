"""Original E000 reset software and F3BD conditional diagnostic services.

Direct byte arithmetic, existing registers and explicit hardware reads only.
This does not emulate the hardware RESET microsequence or generate vblank.
Reset replaces the stack and transfers to E066; it never returns to an old
UI caller. Battery SRAM is retained on the ordinary probe-mismatch path.
"""
import hashlib
from .battle_nmi_services import BattleNMIServices,ServiceWait,I,D,N,Z,C

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'


class BootInitialization(BattleNMIServices):
    FIXED=(0xF3BD,0xF422,0xF43F,0xF458,0xF468)

    def __init__(self,memory,rom,callbacks=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original boot ROM required')
        super().__init__(memory,callbacks);self.rom=bytes(rom);self._call_owner=None

    def __call__(self,call):
        if call.target not in (0xE000,*self.FIXED):
            return {'status':'dependency','reason':'No boot body owns this entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another actual caller owns pending boot work'}
            return self.resume()
        self._call_owner=call
        return self.run_reset(call.registers)if call.target==0xE000 else self.run_service(call.target,call.registers)

    def run_reset(self,registers=None):
        if registers is None:raise ValueError('Supply actual registers at original E000 entry')
        def body():
            self.registers.pc=0xE000
            yield from self.reset_software()
        return self._boundary(self._start(body,registers,'reset_E066_boundary'))

    def run_service(self,entry,registers=None):
        if registers is None:raise ValueError('Supply actual registers and existing caller RTS frame')
        if entry not in self.FIXED:raise ValueError('Unknown fixed boot helper')
        if registers.p&D:raise ValueError('Direct helper CPU fixtures require the original binary-mode context')
        return super().run_service(entry,registers)

    def resume(self):
        pending=self.pending
        if isinstance(pending,ServiceWait)and (self.registers.pc!=pending.pc or self.registers.sp!=pending.expected_sp):
            return self.result('dependency',reason='Hardware/interrupt owner has not restored the paused boot PC/SP')
        return self._boundary(super().resume())

    def _boundary(self,result):
        if result['status']=='returned':
            self._call_owner=None
            if result['mode']=='reset_E066_boundary':
                assert self.registers.pc==0xE066 and self.registers.sp==255
                result['status']='reset_boundary';result['nonlocal_transfer']=True
                result['boundary']='Original next E066 dispatch; stack replaced, no caller RTS'
        return result

    def routine(self,entry):
        if entry==0xF3BD:yield from self.controller_echo_probe()
        elif entry==0xF422:yield from self.check_sram_pattern()
        elif entry==0xF43F:yield from self.write_sram_pattern()
        elif entry==0xF458:yield from self.prepare_sram_pattern()
        elif entry==0xF468:yield from self.next_nonzero_pattern_byte()
        else:raise ValueError('Unknown boot helper')

    def wait_vblank_edges(self,count,set_pc,clear_pc):
        """Original Y=2/4 loops consume3/5 set-and-clear handshakes."""
        r=self.registers;self.y(count)
        while True:
            while True:
                self.a((yield from self.read(0x2002,set_pc)))
                if r.p&N:break
                r.pc=set_pc
                yield ServiceWait('PPUSTATUS_wait_set',set_pc,0x2002,reason='Original BPL still waits for caller-supplied vblank')
            while True:
                self.a((yield from self.read(0x2002,clear_pc)))
                if not r.p&N:break
                r.pc=clear_pc
                yield ServiceWait('PPUSTATUS_wait_clear',clear_pc,0x2002,reason='Original BMI still waits for caller-supplied status clear')
            self.y(r.y-1)
            if r.p&N:return

    def reset_software(self):
        r=self.registers;m=self.memory
        self.flag(I,True);self.flag(D,False);self.a(0)
        yield from self.write(0x2000,r.a,0xE004);yield from self.write(0x2001,r.a,0xE007)
        yield from self.wait_vblank_edges(2,0xE00C,0xE011)
        self.a(0);yield from self.write(0x4010,r.a,0xE01B)
        self.a(15);yield from self.write(0x4015,r.a,0xE020)
        self.a(192);yield from self.write(0x4017,r.a,0xE025)
        self.a(0);yield from self.write(0x2000,r.a,0xE02A);yield from self.write(0x2001,r.a,0xE02D)
        yield from self.wait_vblank_edges(4,0xE032,0xE037)
        self.x(255);r.sp=r.x
        self.a(4);m[1]=r.a;self.y(0);m[2]=r.y
        while True:
            self.a(r.y);m[((m[1]|m[2]<<8)+r.y)&65535]=r.a
            self.inc(1)
            if m[1]:continue
            self.inc(2);self.a(m[2]);self.cmp(r.a,8)
            if r.p&C:break
        yield from self.call(0xE05E,0xF3BD)
        self.a(0);m[0x7A]=r.a;r.pc=0xE066

    def controller_echo_probe(self):
        """F3BD..F421: compare70 ROM low bits with inverted4017 bit1.

        A mismatch returns normally. Complete matching enters SRAM pattern
        diagnostics, fills32 palette positions and permanently halts atF41E.
        The ROM bytes are probe data here, never instructions interpreted by
        this source. Diagnostic meaning is inferred from this code behavior.
        """
        r=self.registers;m=self.memory;self.a(0)
        yield from self.write(0x5000,r.a,0xF3BF);yield from self.write(0x5800,r.a,0xF3C2)
        self.a(224);yield from self.write(0xC000,r.a,0xF3C7);yield from self.write(0xD000,r.a,0xF3CA)
        self.a(225);yield from self.write(0xC800,r.a,0xF3CF);yield from self.write(0xD800,r.a,0xF3D2)
        self.x(0)
        while True:
            self.a(m[0xF3BD+r.x]);self.a(r.a&1);m[1]=r.a
            yield from self.write(0x4016,r.a,0xF3DF)
            self.a((yield from self.read(0x4017,0xF3E2)));self.shift_a('lsr')
            self.a(r.a^255);self.a(r.a&1);self.cmp(r.a,m[1])
            if not r.p&Z:r.pc=0xF421;return
            self.x(r.x+1);self.cmp(r.x,70)
            if r.p&Z:break
        self.a(64);yield from self.write(0xF800,r.a,0xF3F6)
        self.x(1);yield from self.call(0xF3FB,0xF422)
        if not r.p&Z:
            self.x(55);yield from self.call(0xF402,0xF43F)
            yield from self.call(0xF405,0xF422)
            if not r.p&Z:self.x(22)
        self.a(63);yield from self.write(0x2006,r.a,0xF40E)
        self.y(0);yield from self.write(0x2006,r.y,0xF413)
        while True:
            yield from self.write(0x2007,r.x,0xF416);self.y(r.y+1);self.cmp(r.y,32)
            if r.p&Z:break
        while True:
            r.pc=0xF41E
            yield ServiceWait('terminal_boot_diagnostic',0xF41E,reason='Original unconditional JMP F41E is permanent, with no software acknowledgement')

    def prepare_sram_pattern(self):
        r=self.registers;m=self.memory;self.y(0);m[2]=r.y
        self.a(96);m[3]=r.a;self.a(170);m[0]=r.a;r.pc=0xF467
        yield from ()

    def next_nonzero_pattern_byte(self):
        r=self.registers;m=self.memory
        while True:
            self.a(m[0]);self.shift_a('asl');self.shift_a('asl')
            self.flag(C,True);self.add(m[0]);m[0]=r.a
            if not r.p&Z:break
        r.pc=0xF476
        yield from ()

    def check_sram_pattern(self):
        r=self.registers;m=self.memory;yield from self.call(0xF422,0xF458)
        while True:
            self.a(m[((m[2]|m[3]<<8)+r.y)&65535]);self.cmp(r.a,m[0])
            if not r.p&Z:r.pc=0xF43E;return
            yield from self.call(0xF42C,0xF468);self.y(r.y+1)
            if r.y:continue
            self.inc(3);self.a(m[3]);self.cmp(r.a,128)
            if not r.p&Z:continue
            self.a(0);r.pc=0xF43E;return

    def write_sram_pattern(self):
        r=self.registers;m=self.memory;yield from self.call(0xF43F,0xF458)
        while True:
            self.a(m[0]);m[((m[2]|m[3]<<8)+r.y)&65535]=r.a
            yield from self.call(0xF447,0xF468);self.y(r.y+1)
            if r.y:continue
            self.inc(3);self.a(m[3]);self.cmp(r.a,128)
            if r.p&Z:r.pc=0xF457;return
