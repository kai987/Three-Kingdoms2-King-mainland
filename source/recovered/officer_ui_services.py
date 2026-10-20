"""Exact software name packets for pair29/30 officer UI callers.

These routines produce RAM0380 packets and request PPU work. They neither
consume text nor upload pixels. ROM is immutable name/template data only;
production never executes6502 or control IR. Actual caller frames, mapper
writes, scratch and AXYP are preserved, including the fixed F308 name helper.
"""
import hashlib
from .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall,ServiceWait
from .mapped_memory import UnsupportedHardware

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
NAME_PACKET,PPU_JOBS=0x380,0x7E
OFFICER_ID,SIDE_PARAMETER=0x0000,0x0001
SELECTED_SLOT,UNIT_IDS,DUEL_OFFICER=0x509,0x664,0x4AE

class OfficerUIServices(BattleNMIServices):
    """Resumable actual-caller owner for name packet producers and F308.

    ``__call__(ServiceCall)`` accepts F308 in any original pair context; the
    banked entries require physical29/30. run_entry never seeds a fake return.
    Only the palette+name wrapper A02A needs a separately recovered EE07 owner.
    """
    PUBLIC=(0xA027,0xA02A,0xA030,0xA033,0xA036,0xA03C)
    BODIES=(0xA830,0xA890,0xA8A4,0xA8FD,0xBC66,0xA991,0xA957,0xA976)
    ENTRIES=PUBLIC+BODIES+(0xF308,)
    FIXED=BattleNMIServices.FIXED+(0xF308,)
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned officer UI ROM required')
        super().__init__(memory,services);self.rom=bytes(rom);self._call_owner=None
    def __call__(self,call):
        if call.target not in self.ENTRIES:return {'status':'dependency','reason':'Officer UI body has no recovered owner','target':call.target}
        if call.target!=0xF308 and tuple(call.entry_banks[1:3])!=(29,30):
            return {'status':'dependency','reason':'Officer UI requires original physical29/30','target':call.target}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns pending officer UI'}
            result=self.resume()
        else:
            self._call_owner=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':self._call_owner=None
        return result
    def run_entry(self,entry=0xA030,registers=None):
        if entry not in self.ENTRIES:raise ValueError('Unrecovered officer UI entry')
        def body():
            self.registers.pc=entry;yield from self.routine(entry);self.rts()
        return self._start(body,registers or NMIRegisters(),'officer_UI')
    def _drive(self):
        # A callback's label alone cannot finish a caller. Even a mutated
        # caller PC/SP must not turn None/waiting/error/blocked into returned.
        while True:
            if isinstance(self.pending,ServiceCall):
                call=self.pending
                if self.callbacks is None:return self.result('dependency')
                try:outcome=self.callbacks(call)
                except UnsupportedHardware as exc:return self.result('dependency',reason=str(exc))
                if not isinstance(outcome,dict)or outcome.get('status')!='returned':return self.result('dependency')
                if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:
                    return self.result('dependency',reason='Service did not reach actual caller PC/SP')
                self.events.append({'kind':'callback_return','target':call.target,'return_pc':call.return_pc})
            self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:self._program=None;return self.result('returned')
            if isinstance(self.pending,ServiceWait):
                self.pending.expected_sp=self.registers.sp;return self.result('dependency')
    def routine(self,entry):
        if entry in(0xA030,0xA8A4):yield from self.left_name_packet()
        elif entry in(0xA03C,0xA991):yield from self.participant_name_packet()
        elif entry in(0xA033,0xA8FD):yield from self.duel_name_packet()
        elif entry in(0xA027,0xA830):yield from self.selected_unit_name_packet()
        elif entry in(0xA02A,0xA890):yield from self.palette_then_name_packet()
        elif entry in(0xA036,0xBC66):yield from self.clear_attribute_buffer()
        elif entry==0xA957:yield from self.place_name_marks()
        elif entry==0xA976:yield from self.place_name_glyphs()
        elif entry==0xF308:yield from self.name_pointer_and_alignment()
        else:yield from super().routine(entry)
    def local(self,pc,method):
        # Local bodies have no synthetic return of their own. The original
        # JSR frame remains visible in RAM and is consumed exactly once here.
        word=pc+2;self.push(word>>8);self.push(word)
        yield from method();self.rts()
    def copy_name_template(self,source):
        """Copy original59-byte packet descending Y=58..0, ending Y=FF."""
        self.y(58)
        while True:
            self.a(self.memory[source+self.registers.y]);self.memory[NAME_PACKET+self.registers.y]=self.registers.a
            self.y(self.registers.y-1)
            if self.registers.y&128:return
    def request_name_upload(self):
        self.a(self.memory[PPU_JOBS]);self.a(self.registers.a|4);self.memory[PPU_JOBS]=self.registers.a
    def left_name_packet(self):
        self.copy_name_template(0xA8C3)
        self.a(self.memory[OFFICER_ID]);self.push(self.registers.a)
        yield from self.local(0xA8B3,self.place_name_marks)
        self.a(self.pop());yield from self.local(0xA8B7,self.place_name_glyphs)
        self.request_name_upload()
    def participant_name_packet(self):
        self.a(self.memory[SIDE_PARAMETER])
        self.copy_name_template(0xA9FD if self.registers.a==0 else 0xA9C3)
        self.a(self.memory[OFFICER_ID]);self.push(self.registers.a)
        yield from self.local(0xA9B3,self.place_name_marks)
        self.a(self.pop());yield from self.local(0xA9B7,self.place_name_glyphs)
        self.request_name_upload()
    def duel_name_packet(self):
        self.copy_name_template(0xA91D);self.a(self.memory[DUEL_OFFICER])
        yield from self.local(0xA90B,self.place_name_marks)
        self.a(self.memory[DUEL_OFFICER]);yield from self.local(0xA911,self.place_name_glyphs)
        self.request_name_upload()
    def selected_unit_name_packet(self):
        self.copy_name_template(0xA856);self.y(self.memory[SELECTED_SLOT]);self.a(self.memory[UNIT_IDS+self.registers.y])
        yield from self.local(0xA841,self.place_name_marks)
        self.y(self.memory[SELECTED_SLOT]);self.a(self.memory[UNIT_IDS+self.registers.y])
        yield from self.local(0xA84A,self.place_name_glyphs)
        self.request_name_upload()
    def palette_then_name_packet(self):
        self.a(self.memory[OFFICER_ID]);self.push(self.registers.a)
        self.a(0);self.memory[OFFICER_ID]=0;self.y(61)
        word=0xA89D;self.push(word>>8);self.push(word);self.registers.pc=0xEE07
        self.events.append({'kind':'far_call','pc':0xA89B,'target':0xEE07,'inline_target':0xA015})
        yield ServiceCall(0xEE07,0xA8A0,'far_call',self.registers,self.memory,tuple(self.memory.banks),(self.registers.sp+2)&255)
        self.a(self.pop());self.memory[OFFICER_ID]=self.registers.a
        yield from self.left_name_packet()
    def clear_attribute_buffer(self):
        self.y(63);self.a(0)
        while True:
            self.memory[0x140+self.registers.y]=self.registers.a;self.y(self.registers.y-1)
            if self.registers.y&128:return
        yield from ()
    def name_pointer_and_alignment(self):
        """F308: switch original name bank, address10-byte record, count.

        X counts codes other than39/3A; Y counts every code before00. A is
        the raw original F35F[X] alignment. No high-level text callback can
        substitute for the mapper, scratch, carry and actual JSR frame here.
        """
        m=self.memory;r=self.registers;m[2]=r.a;self.y(48)
        yield from self.call(0xF30D,0xF25F)
        pointer=0x901A+10*m[2];m[0]=pointer&255;m[1]=pointer>>8
        # Original final ADC adds high(10*ID)+carry to90. For any byte ID
        # this cannot carry and its unlike-sign operands clear overflow.
        self.flag(1,False);self.flag(64,False);self.a(m[1]);self.y(0);self.x(0)
        while True:
            self.a(m[((m[0]|m[1]<<8)+r.y)&65535])
            if r.a==0:break
            self.y(r.y+1);self.cmp(r.a,57)
            if r.a==57:continue
            self.cmp(r.a,58)
            if r.a==58:continue
            self.x(r.x+1)
        self.a(m[0xF35F+r.x])
    def place_name_marks(self):
        yield from self.local(0xA957,self.name_pointer_and_alignment)
        r=self.registers;m=self.memory;self.x(r.a);self.y(0)
        while True:
            self.a(m[((m[0]|m[1]<<8)+r.y)&65535])
            if r.a==0:return
            self.cmp(r.a,57)
            is_mark=r.a==57
            if not is_mark:self.cmp(r.a,58);is_mark=r.a==58
            if is_mark:m[0x3A5+r.x]=r.a;self.y(r.y+1)
            else:self.y(r.y+1);self.x(r.x+1)
    def place_name_glyphs(self):
        yield from self.local(0xA976,self.name_pointer_and_alignment)
        r=self.registers;m=self.memory;self.x(r.a);self.y(0)
        while True:
            self.a(m[((m[0]|m[1]<<8)+r.y)&65535])
            if r.a==0:return
            self.cmp(r.a,57)
            is_mark=r.a==57
            if not is_mark:self.cmp(r.a,58);is_mark=r.a==58
            if not is_mark:m[0x3B1+r.x]=r.a;self.x(r.x+1)
            self.y(r.y+1)
