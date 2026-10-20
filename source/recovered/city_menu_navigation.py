"""Exact fixed menu navigation with the original nested caller frames.

Readable byte arithmetic and four directional procedures replace the earlier
shared semantic menu protocol. No opcode/IR or original CPU executes here.
Tables are caller data. Missing row/column sentinels stay cyclic dependencies;
they never fabricate a selected item or complete a ready flag.
"""
from .scene_shared_services import SceneSharedServices
from .battle_nmi_services import ServiceWait,C,N,D


class CityMenuNavigation(SceneSharedServices):
    PUBLIC_ENTRIES=(0xED19,0xED1E,0xED23,0xED28,0xED2D,0xED32,0xED37,0xED3C,0xED41,0xEDDD)
    LOCAL_ENTRIES=(0xED71,0xED8D,0xEDA9,0xEDBE)
    FIXED=PUBLIC_ENTRIES+LOCAL_ENTRIES

    def run_service(self,entry,registers=None):
        if entry not in self.FIXED:raise ValueError('Unrecovered menu entry')
        if registers is None:raise ValueError('Supply actual menu caller registers and frame')
        if registers.p&D:
            raise ValueError('Binary CPU comparison requires decimal flag clear')
        return super().run_service(entry,registers)

    def routine(self,entry):
        if entry==0xEDDD:yield from self.value_at_cursor()
        elif entry==0xED71:yield from self.navigate_right()
        elif entry==0xED8D:yield from self.navigate_left()
        elif entry==0xEDA9:yield from self.navigate_down()
        elif entry==0xEDBE:yield from self.navigate_up()
        elif entry in self.PUBLIC_ENTRIES:yield from self.menu(entry)
        else:raise ValueError('Unrecovered menu body')

    def menu(self,entry):
        """ED19..ED70: width stubs then right,left,down,up in that order.

        The old0012 byte controls wrap eligibility; it is written only after
        every requested direction and the actual ED6B JSR EDDD have run.
        ED41 accepts raw A width; the eight public stubs supply1..8.
        """
        m=self.memory;r=self.registers
        if entry!=0xED41:self.a((entry-0xED19)//5+1)
        m[0]=r.a
        self.a(m[0x81]);self.a(r.a&128)
        if r.a:yield from self.call(0xED4A,0xED71)
        self.a(m[0x81]);self.a(r.a&64)
        if r.a:yield from self.call(0xED54,0xED8D)
        self.a(m[0x81]);self.a(r.a&32)
        if r.a:yield from self.call(0xED5E,0xEDA9)
        self.a(m[0x81]);self.a(r.a&16)
        if r.a:yield from self.call(0xED68,0xEDBE)
        yield from self.call(0xED6B,0xEDDD);m[0x12]=r.a

    def value_at_cursor(self):
        """EDDD..EDF4: wrapped row*width+column, read ($10),Y."""
        m=self.memory;r=self.registers;self.a(0);self.y(m[0x425]);self.cmp(r.y,0)
        while r.y:
            self.flag(C,False);self.add(m[0]);self.y(r.y-1);self.cmp(r.y,0)
        self.flag(C,False);self.add(m[0x424]);self.y(r.a)
        self.a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        yield from ()

    def navigate_right(self):
        """ED71..ED8C: advance, reject negative cell/beyond width, optional0 wrap."""
        m=self.memory;r=self.registers;self.inc(0x424)
        yield from self.call(0xED74,0xEDDD)
        reject=bool(r.p&N)
        if not reject:
            self.a(m[0x424]);self.cmp(r.a,m[0]);reject=bool(r.p&C)
        if reject:
            self.inc(0x424,-1);self.a(m[0x12])
            if not r.a:self.a(0);m[0x424]=r.a

    def navigate_left(self):
        """ED8D..EDA8: underflow scan skips onlyFF, not all negative bytes."""
        m=self.memory;r=self.registers;self.inc(0x424,-1)
        if not r.p&N:return
        self.inc(0x424);self.a(m[0x12])
        if r.a:return
        self.a(m[0]);m[0x424]=r.a
        while True:
            for _ in range(256):
                self.inc(0x424,-1);yield from self.call(0xEDA1,0xEDDD);self.cmp(r.a,255)
                if r.a!=255:return
            r.pc=0xED9E
            yield ServiceWait('menu_no_valid_column',0xED9E,reason='Original FF rejection scan completed one byte period without a valid value')

    def navigate_down(self):
        """EDA9..EDBD: advance row, reject sign-bit cell, optional0 wrap."""
        m=self.memory;r=self.registers;self.inc(0x425)
        yield from self.call(0xEDAC,0xEDDD)
        if not r.p&N:return
        self.inc(0x425,-1);self.a(m[0x12])
        if not r.a:self.a(0);m[0x425]=r.a

    def navigate_up(self):
        """EDBE..EDDC: underflow counts rows until any sign-bit sentinel.

        The sign-bit exit differs from horizontal FF skipping. Width and
        Y arithmetic wrap as bytes; failure to encounter a negative cell in
        the whole byte period is an explicit cyclic service dependency.
        """
        m=self.memory;r=self.registers;self.inc(0x425,-1)
        if not r.p&N:return
        self.inc(0x425);self.a(m[0x12])
        if r.a:return
        self.x(255);self.y(m[0x424])
        while True:
            for _ in range(256):
                self.x(r.x+1);self.a(r.y);self.flag(C,False);self.add(m[0]);self.y(r.a)
                self.a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                if r.p&N:m[0x425]=r.x;return
            r.pc=0xEDCF
            yield ServiceWait('menu_no_end_sentinel',0xEDCF,reason='Original wrapped column walk has no sign-bit sentinel in one byte period')
