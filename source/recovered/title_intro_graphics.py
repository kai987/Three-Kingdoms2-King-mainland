"""Independent five-phase title intro graphics, physical23 A021.

Static original-byte provenance compiled to named Python if/while/calls.
No runtime opcode/IR/program.json or original-CPU fallback is used. Each
call genuinely returns to its caller, but a requested packet is not a
completed PPU upload. Real busy queue bytes are never acknowledged here.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall
from .scene_shared_services import SceneSharedServices
from .controller_helpers import ControlHelpers
ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
@dataclass(frozen=True)
class TitleIntroData:
    rom:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original ROM required')
        return cls(bytes(rom))
class SourceBudget(RuntimeError):pass
class InvalidTitleIntroPhase(ValueError):pass
class TitleIntroGraphics(BattleNMIServices):
    FIXED=()
    def __init__(self,memory,data,services=None):
        super().__init__(memory,callbacks=self._resolve_service)
        self.data=data if isinstance(data,TitleIntroData)else TitleIntroData.from_rom(data)
        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=self._resolve_service)
        self.external_services=services;self.controls=ControlHelpers();self.source_locations=[];self.source_budget=100000;self._call_owner=None
    def _mark(self,pc):
        self.registers.pc=pc;self.source_locations.append(pc)
        if len(self.source_locations)>self.source_budget:raise SourceBudget('Original title intro source operation budget exhausted')
    def _shift(self,address,kind):
        old=self.memory[address];carry=int(bool(self.registers.p&C))
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        self.memory[address]=self.nz((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else (old>>1)|(carry<<7)if kind=='ror'else old>>1)
    def shift_a(self,kind):
        old=self.registers.a;carry=int(bool(self.registers.p&C))
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        return self.a((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else (old>>1)|(carry<<7)if kind=='ror'else old>>1)
    def _resolve_service(self,call):
        if call.target in self.shared.FIXED:result=self.shared(call)
        elif self.external_services is not None:result=self.external_services(call)
        else:return dict(status='dependency',reason='No independent title intro helper owns this exact entry',target=call.target)
        if not isinstance(result,dict)or result.get('status')!='returned':return dict(status='dependency',body=result)
        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='Title intro helper has not reached actual caller PC/SP',body=result)
        return result
    def _service(self,target,kind='tail',return_pc=None,expected_sp=None):
        r=self.registers;r.pc=target
        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        if expected_sp is None:expected_sp=(r.sp+2)&255
        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),expected_sp)
    def call(self,pc,target,*,inline_return=None):
        sp=self.registers.sp;word=pc+2;self.push(word>>8);self.push(word)
        if target in self.LOCAL_ENTRIES:yield from self.routine(target)
        else:yield from self._service(target,'call',inline_return or pc+3,sp)
        if self.registers.pc!=(inline_return or pc+3)or self.registers.sp!=sp:raise RuntimeError('Title intro call has not returned to its real caller')
    def _dispatch(self,pc,targets,methods):
        index=self.registers.a
        if not 0<=index<len(targets):raise InvalidTitleIntroPhase('Only original five title-intro phases are proven')
        word=pc+2;self.push(word>>8);self.push(word);self.controls(self,0xEADE,targets[index],'dispatch')
        yield from methods[index]()
    def result(self,status,**extra):
        value=super().result(status,**extra)
        return dict(value,source_locations=list(self.source_locations),intro_phase=self.memory[0x541],intro_timer=self.memory[0x544],PPU_jobs=self.memory[0x7E],full_NES_frame=False,PPU_upload_completed=False)
    def run_entry(self,entry=0xA021,registers=None,*,max_source_operations=100000):
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Entry is outside the original title intro closure')
        if self._program is not None:raise RuntimeError('A real title intro service is pending; resume it first')
        if registers is None:raise ValueError('Supply actual caller registers and existing RTS frame')
        if tuple(getattr(self.memory,'banks',())[1:3])!=(23,24):raise ValueError('Title intro requires actual physical23/24 pair')
        if entry in(0xA021,0xDE25)and self.memory[0x541]>=5:raise InvalidTitleIntroPhase('Legal title-intro phases are0..4')
        if (entry in(0xA021,0xDE25)and self.memory[0x541]==1 and not self.memory[0x81]&8 or entry==0xDE66)and self.memory[0x543]>=24:raise ValueError('Original intro sequence positions are0..23')
        if entry==0xDEFA and registers.a>=15:raise ValueError('Original intro frame IDs are0..14')
        self.source_locations=[];self.source_budget=max_source_operations
        return self._start(lambda:self.routine(entry),registers,'title_intro_graphics')
    def tick(self,registers=None):return self.run_entry(0xA021,registers)
    def __call__(self,call):
        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(23,24):return dict(status='dependency',reason='No title intro body owns this exact pair/entry')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='Another caller owns pending title intro')
            result=self.resume()
        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':
            self._call_owner=None
            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='Title intro did not reach actualcaller PC/SP',body=result)
        return result

    def public_title_intro(self):
        """Original $A021: public_title_intro."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xA021)
        yield from self.title_intro_phase_dispatch()
        return

    def title_intro_phase_dispatch(self):
        """Original $DE25: start button forces original phase3, otherwise fivephase inline dispatch."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDE25)
        self.a(m[0x0081])
        self._mark(0xDE28)
        self.a(r.a&0x08)
        self._mark(0xDE2A)
        if bool(r.p&Z):
            self._mark(0xDE34)
            self.a(m[0x0541])
            self._mark(0xDE37)
            yield from self._dispatch(0xDE37,(0xDE44,0xDE66,0xDEB9,0xDEC7,0xDED6,),(self.intro_delay,self.advance_intro_frames,self.hold_intro_frame,self.blacken_intro_palette,self.finish_intro_sequence,))
            return
        else:
            self._mark(0xDE2C)
            self.a(0x03)
            self._mark(0xDE2E)
            m[0x0541]=r.a
            self._mark(0xDE31)
            yield from self.blacken_intro_palette()
            return

    def intro_delay(self):
        """Original $DE44: incrementtimer, after32ticks palette andtwoframe dwell."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDE44)
        self.inc(0x0544)
        self._mark(0xDE47)
        self.a(m[0x0544])
        self._mark(0xDE4A)
        self.cmp(r.a,0x20)
        self._mark(0xDE4C)
        if not(not(r.p&C)):
            self._mark(0xDE4E)
            self.a(0x16)
            self._mark(0xDE50)
            m[0x0115]=r.a
            self._mark(0xDE53)
            self.a(0x30)
            self._mark(0xDE55)
            m[0x0116]=r.a
            self._mark(0xDE58)
            self.a(0x00)
            self._mark(0xDE5A)
            m[0x0543]=r.a
            self._mark(0xDE5D)
            self.a(0x02)
            self._mark(0xDE5F)
            m[0x0544]=r.a
            self._mark(0xDE62)
            self.inc(0x0541)
        self._mark(0xDE65)
        self.rts()
        return

    def advance_intro_frames(self):
        """Original $DE66: advance24-entry originalframe sequence, play original audio atindex20."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDE66)
        self.y(m[0x0543])
        self._mark(0xDE69)
        self.cmp(r.y,0x14)
        self._mark(0xDE6B)
        if not(not(r.p&Z)):
            self._mark(0xDE6D)
            self.a(0x62)
            self._mark(0xDE6F)
            yield from self.call(0xDE6F,0xE693)
        self._mark(0xDE72)
        self.y(0x21)
        self._mark(0xDE74)
        yield from self.call(0xDE74,0xF25F)
        self._mark(0xDE77)
        self.y(m[0x0543])
        self._mark(0xDE7A)
        self.a(m[(0xDEA0+r.y)&65535])
        self._mark(0xDE7D)
        yield from self.call(0xDE7D,0xDEFA)
        self._mark(0xDE80)
        self.inc(0x0544,-1)
        self._mark(0xDE83)
        if not(not(r.p&Z)):
            self._mark(0xDE85)
            self.a(0x02)
            self._mark(0xDE87)
            m[0x0544]=r.a
            self._mark(0xDE8A)
            self.inc(0x0543)
            self._mark(0xDE8D)
            self.y(m[0x0543])
            self._mark(0xDE90)
            self.a(m[(0xDEA0+r.y)&65535])
            self._mark(0xDE93)
            self.cmp(r.a,0xFF)
            self._mark(0xDE95)
            if not(not(r.p&Z)):
                self._mark(0xDE97)
                self.inc(0x0541)
                self._mark(0xDE9A)
                self.a(0x40)
                self._mark(0xDE9C)
                m[0x0544]=r.a
        self._mark(0xDE9F)
        self.rts()
        return

    def hold_intro_frame(self):
        """Original $DEB9: hold originalframe8 untiltimer reaches0."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDEB9)
        self.inc(0x0544,-1)
        self._mark(0xDEBC)
        if bool(r.p&Z):
            self._mark(0xDEC3)
            self.inc(0x0541)
            self._mark(0xDEC6)
            self.rts()
            return
        else:
            self._mark(0xDEBE)
            self.a(0x08)
            self._mark(0xDEC0)
            yield from self.draw_intro_frame()
            return

    def blacken_intro_palette(self):
        """Original $DEC7: blacken three palette bytes andadvancephase."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDEC7)
        self.inc(0x0541)
        self._mark(0xDECA)
        self.a(0x0F)
        self._mark(0xDECC)
        m[0x0115]=r.a
        self._mark(0xDECF)
        m[0x0116]=r.a
        self._mark(0xDED2)
        m[0x0117]=r.a
        self._mark(0xDED5)
        self.rts()
        return

    def finish_intro_sequence(self):
        """Original $DED6: advance0540, clearphase/timer/scratch andreset/request originalaudioB0."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDED6)
        self.inc(0x0540)
        self._mark(0xDED9)
        self.a(0x00)
        self._mark(0xDEDB)
        m[0x0541]=r.a
        self._mark(0xDEDE)
        self.a(0xB0)
        self._mark(0xDEE0)
        m[0x00CE]=r.a
        self._mark(0xDEE2)
        self.a(0x04)
        self._mark(0xDEE4)
        m[0x00D6]=r.a
        self._mark(0xDEE6)
        self.a(0x00)
        self._mark(0xDEE8)
        m[0x0544]=r.a
        self._mark(0xDEEB)
        m[0x0470]=r.a
        self._mark(0xDEEE)
        m[0x0471]=r.a
        self._mark(0xDEF1)
        yield from self.call(0xDEF1,0xE57F)
        self._mark(0xDEF4)
        self.a(0xB0)
        self._mark(0xDEF6)
        yield from self.call(0xDEF6,0xE673)
        self._mark(0xDEF9)
        self.rts()
        return

    def draw_intro_frame(self):
        """Original $DEFA: physical1 sprite descriptor lookup and realF1AD caller."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xDEFA)
        self.shift_a("asl")
        self._mark(0xDEFB)
        self.y(r.a)
        self._mark(0xDEFC)
        self.a(m[(0x97EF+r.y)&65535])
        self._mark(0xDEFF)
        m[0x0000]=r.a
        self._mark(0xDF01)
        self.a(m[(0x97F0+r.y)&65535])
        self._mark(0xDF04)
        m[0x0001]=r.a
        self._mark(0xDF06)
        self.a(0x58)
        self._mark(0xDF08)
        m[0x000A]=r.a
        self._mark(0xDF0A)
        self.a(0x68)
        self._mark(0xDF0C)
        m[0x000C]=r.a
        self._mark(0xDF0E)
        self.a(0x01)
        self._mark(0xDF10)
        m[0x0002]=r.a
        self._mark(0xDF12)
        yield from self._service(0xF1AD)
        return

    LOCAL_ENTRIES=(0xA021,0xDE25,0xDE44,0xDE66,0xDEB9,0xDEC7,0xDED6,0xDEFA,)

    def routine(self,entry):
        methods={0xA021:self.public_title_intro,0xDE25:self.title_intro_phase_dispatch,0xDE44:self.intro_delay,0xDE66:self.advance_intro_frames,0xDEB9:self.hold_intro_frame,0xDEC7:self.blacken_intro_palette,0xDED6:self.finish_intro_sequence,0xDEFA:self.draw_intro_frame}
        yield from methods[entry]()
