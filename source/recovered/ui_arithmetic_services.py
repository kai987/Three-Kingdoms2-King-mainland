"""Exact fixed-bank 24-by-16 multiplication used by city UI actions."""
from .battle_nmi_services import BattleNMIServices

class UIArithmeticServices(BattleNMIServices):
    FIXED=(0xEC22,)
    def __call__(self,call):
        if call.target not in self.FIXED:
            return {'status':'dependency','reason':'No arithmetic body owns this fixed entry'}
        return self.run_service(call.target,call.registers)
    def run_service(self,entry,registers=None):
        if registers is None:raise ValueError('Supply actual caller registers and an existing RTS frame')
        return super().run_service(entry,registers)
    def routine(self,entry):
        if entry!=0xEC22:raise ValueError('Only original EC22 multiplication is owned here')
        yield from self.multiply_24_by_16()

    def _shift_memory(self,address,kind):
        value=self.memory[address];carry=self.registers.p&1
        self.flag(1,bool(value&128)if kind in ('asl','rol')else bool(value&1))
        if kind=='asl':value<<=1
        elif kind=='rol':value=(value<<1)|carry
        elif kind=='lsr':value>>=1
        elif kind=='ror':value=(value>>1)|(carry<<7)
        else:raise ValueError('Unsupported arithmetic shift')
        self.memory[address]=self.nz(value)

    def multiply_24_by_16(self):
        """EC22..EC66: 24-bit0000..2 ×16-bit0003..4 →40-bit0006..A.

        The multiplier and multiplicand shift destructively, with original
        accumulator/flags,000B/C extension bytes,Y and actual caller RTS.
        """
        r=self.registers;m=self.memory;self.y(15);self.a(0)
        if False:yield
        for address in range(6,13):m[address]=r.a
        while True:
            r.pc=0xEC34;self._shift_memory(4,'lsr');self._shift_memory(3,'ror')
            if r.p&1:
                self.a(m[0]);self.flag(1,False);self.add(m[6]);m[6]=r.a
                for left,right in((1,7),(2,8),(11,9),(12,10)):
                    self.a(m[left]);self.add(m[right]);m[right]=r.a
            self._shift_memory(0,'asl')
            for address in(1,2,11,12):self._shift_memory(address,'rol')
            self.y(r.y-1)
            if r.p&128:break
        r.pc=0xEC66
