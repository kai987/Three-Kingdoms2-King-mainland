"""Exact readable formation-pointer constructors, physical8 B2AE/B312.

B1B0's previously named strategy distribution and coordinate consumers remain
inherited unchanged. These two bodies make the data-window transitions and
byte arithmetic explicit; they never read opcodes, run IR or invoke a CPU.
An actual caller frame and physical8/9 code windows are required.
"""
from .battle_setup_ai import BattleSetupAI,C,Z,N


class DeploymentPointerServices(BattleSetupAI):
    PUBLIC_ENTRIES=(0xA003,0xB130,0xB1B0,0xB2AE,0xB312)
    LOCAL_ENTRIES=PUBLIC_ENTRIES

    def run_entry(self,entry=0xA003,*,registers=None,seed_return=False,
                  return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('An actual caller register context is required')
        if seed_return:raise ValueError('No synthetic caller is created by deployment services')
        if entry not in self.PUBLIC_ENTRIES:raise ValueError('Entry is outside the deployment chain')
        if registers.pc!=entry:raise ValueError('Register PC must already identify the requested entry')
        if tuple(getattr(self.memory,'banks',())[1:3])!=(8,9):raise ValueError('Physical8/9 code windows required')
        r=registers;m=self.memory
        actual=((m[0x100+((r.sp+1)&255)]|m[0x100+((r.sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual:raise ValueError('Requested return differs from the existing caller frame')
        self._expected_return_sp=(r.sp+2)&255
        return super().run_entry(entry,registers=r,seed_return=False,
                                 return_pc=actual,max_blocks=max_blocks)

    def __call__(self,call):
        if call.memory is not self.memory:raise ValueError('Caller must share this exact memory')
        if tuple(call.entry_banks[1:3])!=(8,9):raise ValueError('Caller code windows must be physical8/9')
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

    def _drive(self):
        while True:
            if self.pending is not None:
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                same=(self.registers.pc,self.registers.sp)==(self._return_pc,self._expected_return_sp)
                return self._result('returned'if same else'nonlocal_return')

    def first_side_formation(self):
        """B2AE: neighbor selector→bank17 template→bank6 coordinate word.

        Y scans the original byte-indexed neighbor table until a negative
        sentinel or exact052A match. A match saves the index on the actual
        stack while F266 selects17. The template is multiplied by32 modulo
        256, then added to the complete bank6 city pointer with real carry.
        """
        r,m=self.registers,self.memory;self._mark(0xB2AE);self._y(0x30)
        yield from self._external(0xB2B0,0xF266,0xB2B3,'call')
        if r.pc!=0xB2B3:return
        self._a(m[0x50E])
        for _ in range(3):r.a=self._shift(r.a,True)
        self._y(r.a)
        while True:
            self._mark(0xB2BA);self._a(m[0x9D72+r.y])
            if r.p&N:
                self._a(0);break
            self._compare(r.a,m[0x52A])
            if not r.p&Z:
                self._y(r.y+1);continue
            self._a(r.y);self._push(r.a);self._y(0x31)
            yield from self._external(0xB2D1,0xF266,0xB2D4,'call')
            if r.pc!=0xB2D4:return
            self._a(self._pop());self._y(r.a);self._a(m[0x9AB4+r.y]);break
        m[0x20]=r.a
        for _ in range(5):r.a=self._shift(r.a,True)
        m[0x20]=r.a;self._y(0x26)
        yield from self._external(0xB2E6,0xF266,0xB2E9,'call')
        if r.pc!=0xB2E9:return
        self._a(m[0x50E]);r.a=self._shift(r.a,True);self._y(r.a)
        self._a(m[0x8C52+r.y]);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
        self._a(m[0x8C53+r.y]);self._add(0);m[0x21]=r.a
        self._y(0)
        while True:
            self._mark(0xB302);self._a(m[0xB30E+r.y]);m[0x22+r.y]=r.a
            self._y(r.y+1);self._compare(r.y,4)
            if r.p&C:break
        self._mark(0xB30D);self._rts()

    def second_side_formation(self):
        """B312: bank16 selector, exact34×byte offset, bank6 city pointer.

        Four ASL, CLC/ADC originalbyte, then ASL is34× modulo256. It is
        neither a36-byte stride nor an unbounded integer multiplication.
        Negative neighbor sentinel selects0; no bank17 step occurs here.
        """
        r,m=self.registers,self.memory;self._mark(0xB312);self._y(0x30)
        yield from self._external(0xB314,0xF266,0xB317,'call')
        if r.pc!=0xB317:return
        self._a(m[0x50E])
        for _ in range(3):r.a=self._shift(r.a,True)
        self._y(r.a)
        while True:
            self._mark(0xB31E);self._a(m[0x9D72+r.y])
            if r.p&N:
                self._a(0);break
            self._compare(r.a,m[0x52A])
            if not r.p&Z:
                self._y(r.y+1);continue
            self._a(m[0x9E62+r.y]);break
        m[0x20]=r.a
        for _ in range(4):r.a=self._shift(r.a,True)
        self._flag(C,False);self._add(m[0x20]);r.a=self._shift(r.a,True)
        m[0x20]=r.a;self._y(0x26)
        yield from self._external(0xB345,0xF266,0xB348,'call')
        if r.pc!=0xB348:return
        self._a(m[0x50E]);r.a=self._shift(r.a,True);self._y(r.a)
        self._a(m[0x8000+r.y]);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
        self._a(m[0x8001+r.y]);self._add(0);m[0x21]=r.a
        self._y(0)
        while True:
            self._mark(0xB361);self._a(m[0xB36D+r.y]);m[0x22+r.y]=r.a
            self._y(r.y+1);self._compare(r.y,4)
            if r.p&C:break
        self._mark(0xB36C);self._rts()
