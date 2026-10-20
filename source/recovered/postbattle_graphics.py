"""The actual29:A01E/A6B6 year/month packet used by postbattle city13.

This draws a software request: two seven-tile rows at2043/2063. It does not
initialize the world, upload PPU data, advance a scene or acknowledge a job.
The existing exact E9BA decimal service consumes both real JSR frames.
"""
from .global_ui_controller import UIControlBase,C
from .service_memory import ServiceMemory
from .scene_shared_services import SceneSharedServices


class PostbattleGraphics(UIControlBase):
    PAIR=(29,30)
    PUBLIC_ENTRIES=(0xA01E,0xA6B6)

    def __init__(self,memory,rom,services=None):
        if not isinstance(memory,ServiceMemory):
            raise ValueError('Calendar packet requires an explicit ServiceMemory')
        self.shared=SceneSharedServices(memory,rom)
        self.external_services=services
        super().__init__(memory,rom,self._resolve)

    def _resolve(self,call):
        if self.external_services is not None:return self.external_services(call)
        if call.target==0xE9BA:return self.shared(call)
        return dict(status='dependency',reason='No exact calendar helper owner')

    def fields(self):
        m=self.memory
        return dict(year_raw=m[0x6F00],month_raw=m[0x6F01],PPU_jobs=m[0x7E],
                    packet=list(m[0x380:0x395]),PPU_consumed=False)

    def _entry(self,entry):
        if entry==0xA01E:self._mark(0xA01E)  # Original JMP A6B6.
        elif entry!=0xA6B6:raise ValueError('No exact calendar packet entry')
        return (yield from self.draw_calendar_packet())

    def _digit_tiles(self,upper,lower):
        # Original register/flags sequence; this Python factoring has no JSR.
        r=self.registers;m=self.memory
        self._flag(C,False);self._add(4);m[upper]=r.a
        self._flag(C,False);self._add(16);m[lower]=r.a

    def _high_nibble(self,address):
        self._a(self.memory[address])
        for _ in range(4):self.registers.a=self._shift(self.registers.a,False)

    def draw_calendar_packet(self):
        r=self.registers;m=self.memory;self._mark(0xA6B6)
        self._a(m[0x6F00]);self._flag(C,False);self._add(100);m[1]=r.a
        self._a(0);self._add(0);m[2]=r.a
        self._a(0);m[3]=r.a
        yield from self._external(0xA6CB,0xE9BA,0xA6CE,'call')
        if r.pc!=0xA6CE:return
        self._mark(0xA6CE)
        self._a(m[8]);self._a(r.a&15);self._digit_tiles(0x383,0x38D)
        self._high_nibble(7);self._digit_tiles(0x384,0x38E)
        self._a(m[7]);self._a(r.a&15);self._digit_tiles(0x385,0x38F)

        self._mark(0xA703)
        self._a(m[0x6F01]);self._flag(C,False);self._add(1);m[1]=r.a
        self._a(0);m[2]=r.a;m[3]=r.a  # Original stores discard byte carry.
        yield from self._external(0xA714,0xE9BA,0xA717,'call')
        if r.pc!=0xA717:return
        self._mark(0xA717)
        self._high_nibble(7)
        if r.p&2:self._a(14)  # Original blank tens tile for months1..9.
        self._digit_tiles(0x388,0x392)
        self._a(m[7]);self._a(r.a&15);self._digit_tiles(0x389,0x393)

        self._a(7);m[0x380]=r.a
        self._a(0x20);m[0x381]=r.a
        self._a(0x43);m[0x382]=r.a
        self._a(7);m[0x38A]=r.a
        self._a(0x20);m[0x38B]=r.a
        self._a(0x63);m[0x38C]=r.a
        self._a(0x12);m[0x387]=r.a
        self._a(0x22);m[0x391]=r.a
        self._a(0x0E);m[0x386]=r.a
        self._a(0x1E);m[0x390]=r.a
        self._a(255);m[0x394]=r.a
        self._a(m[0x7E]);self._a(r.a|4);m[0x7E]=r.a
        self._mark(0xA77E);self._rts()

    def run_entry(self,entry=0xA01E,*,registers=None,seed_return=False,
                  return_pc=None,max_blocks=200000):
        if registers is None or seed_return:
            raise ValueError('Calendar requires actual registers and existing caller frame')
        if entry not in self.PUBLIC_ENTRIES or registers.pc!=entry:
            raise ValueError('Actual calendar PC must match its owned entry')
        if tuple(self.memory.banks[1:3])!=self.PAIR:
            raise ValueError('Calendar requires actual physical29/30')
        sp=registers.sp
        actual=((self.memory[0x100+((sp+1)&255)]|
                 self.memory[0x100+((sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual:
            raise ValueError('Calendar return must match the real stack word')
        return super().run_entry(entry,registers=registers,return_pc=actual,
                                 max_blocks=max_blocks)

    def __call__(self,call):
        if call.expected_sp!=((call.registers.sp+2)&255):
            return dict(status='dependency',reason='Calendar requires actual caller SP')
        return super().__call__(call)
