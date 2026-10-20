"""Exact byte multiplication used to create the city appearance-table pointer.

Physical11 D471 consumes20/21, writes2A/2B=raw8(20)*raw8(21), and leaves
the original destructive shift work, flags, A/Y and actual caller stack.
The already named C5D2 body is inherited unchanged. Its virtual helper call
uses this readable arithmetic instead of the frozen generated helper.
No original CPU, opcode/IR interpreter or runtime code generator runs here.
"""
from .city_threshold_services import CityThresholdServices


class AppearancePointerServices(CityThresholdServices):
    PUBLIC_ENTRIES=CityThresholdServices.PUBLIC_ENTRIES+(0xD471,)

    def _entry(self,entry):
        if entry==0xD471:return self.multiply_byte_operands()
        return super()._entry(entry)

    def multiply_byte_operands(self):
        """D471..D493: eight shift/add rounds, raw unsigned8×8→16.

        20 is the shifting low multiplicand,2C its high byte;21 is shifted
        right to test each multiplier bit. 2A/2B accumulates the complete
        product. X is not changed. FinalA/V are those of the last real add
        (or the initialized0/oldV when multiplier0), not synthesized from
        the mathematical product. RTS consumes the already existing frame.
        """
        r,m=self.registers,self.memory;self._mark(0xD471);self._y(7);self._a(0)
        m[0x2C]=r.a;m[0x2A]=r.a;m[0x2B]=r.a
        while True:
            m[0x21]=self._shift(m[0x21],False)
            if r.p&1:
                self._a(m[0x20]);self._flag(1,False);self._add(m[0x2A]);m[0x2A]=r.a
                self._a(m[0x2C]);self._add(m[0x2B]);m[0x2B]=r.a
            m[0x20]=self._shift(m[0x20],True);m[0x2C]=self._shift(m[0x2C],True,rotate=True)
            self._y(r.y-1)
            if r.p&128:break
        self._mark(0xD493);self._rts()
        if False:yield None

    # The inherited C5D2 driver owns the real C601 JSR frame already.
    domesticcooperationcontroller_d471=multiply_byte_operands
