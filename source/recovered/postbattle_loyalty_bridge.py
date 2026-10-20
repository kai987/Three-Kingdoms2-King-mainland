"""The actual postbattle loyalty caller in physical banks10/11.

A009 is a three-byte JMP to CF7C, whose independent source body was already
recovered. This owner exposes that exact caller without invoking the domestic
main loop, changing a return frame or executing ROM instructions/control IR.
"""
from .domestic_cooperation_controller import DomesticCooperationController
from .service_memory import ServiceMemory


class PostbattleLoyaltyBridge(DomesticCooperationController):
    PAIR=(10,11)
    PUBLIC_ENTRIES=(0xA009,0xCF7C)

    def __init__(self,memory,rom,services=None):
        if not isinstance(memory,ServiceMemory):
            raise ValueError('Postbattle loyalty requires an explicit ServiceMemory')
        super().__init__(memory,rom,services)

    def _entry(self,entry):
        if entry==0xA009:
            self._mark(0xA009)  # Original JMP CF7C; no flag/stack operation.
            return (yield from self.recalculate_other_loyalty())
        if entry==0xCF7C:
            return (yield from self.recalculate_other_loyalty())
        raise ValueError('Only actual A009/CF7C loyalty entries are owned')

    def run_entry(self,entry=0xA009,*,registers=None,seed_return=False,
                  return_pc=None,max_blocks=200000):
        if registers is None:
            raise ValueError('Supply actual loyalty callee registers and caller stack')
        if seed_return:
            raise ValueError('Production loyalty never inserts a return frame')
        if entry not in self.PUBLIC_ENTRIES or registers.pc!=entry:
            raise ValueError('Actual loyalty PC must match its owned entry')
        if tuple(self.memory.banks[1:3])!=self.PAIR:
            raise ValueError('Original loyalty data requires physical10/11')
        sp=registers.sp
        actual=((self.memory[0x100+((sp+1)&255)]|
                 self.memory[0x100+((sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual:
            raise ValueError('Declared return must be the actual caller stack word')
        return super().run_entry(entry,registers=registers,return_pc=actual,
                                 max_blocks=max_blocks)

    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=self.PAIR or call.target not in self.PUBLIC_ENTRIES:
            return dict(status='dependency',reason='No exact postbattle loyalty entry')
        if call.expected_sp!=((call.registers.sp+2)&255):
            return dict(status='dependency',reason='Actual caller SP is required')
        return super().__call__(call)
