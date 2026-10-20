"""Independent ten-row officer detail packet producer, physical25 A012.

Static original-byte provenance compiled to named Python if/while/calls.
No runtime opcode/IR/program.json or original-CPU fallback is used. Each
call genuinely returns to its caller, but a requested packet is not a
completed PPU upload. Real busy queue bytes are never acknowledged here.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall
from .scene_shared_services import SceneSharedServices
from .officer_ui_services import OfficerUIServices
from .controller_helpers import ControlHelpers
ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
@dataclass(frozen=True)
class OfficerDetailsData:
    rom:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original ROM required')
        return cls(bytes(rom))
class SourceBudget(RuntimeError):pass
class InvalidDetailRow(ValueError):pass
class OfficerDetailsUIServices(BattleNMIServices):
    FIXED=()
    def __init__(self,memory,data,services=None):
        super().__init__(memory,callbacks=self._resolve_service)
        self.data=data if isinstance(data,OfficerDetailsData)else OfficerDetailsData.from_rom(data)
        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=services)
        self.names=OfficerUIServices(memory,self.data.rom,services=services)
        self.external_services=services;self.controls=ControlHelpers();self.source_locations=[];self.source_budget=100000;self._call_owner=None
    def _mark(self,pc):
        self.registers.pc=pc;self.source_locations.append(pc)
        if len(self.source_locations)>self.source_budget:raise SourceBudget('Original detail source operation budget exhausted')
    def _shift(self,address,kind):
        old=self.memory[address];carry=int(bool(self.registers.p&C))
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        self.memory[address]=self.nz((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else (old>>1)|(carry<<7)if kind=='ror'else old>>1)
    def shift_a(self,kind):
        old=self.registers.a;carry=int(bool(self.registers.p&C))
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        return self.a((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else (old>>1)|(carry<<7)if kind=='ror'else old>>1)
    def _resolve_service(self,call):
        if call.target==0xF308:result=self.names(call)
        elif call.target in self.shared.FIXED:result=self.shared(call)
        elif self.external_services is not None:result=self.external_services(call)
        else:return dict(status='dependency',reason='No independent details helper owns this exact entry',target=call.target)
        if not isinstance(result,dict)or result.get('status')!='returned':return dict(status='dependency',body=result)
        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='Details helper has not reached actual caller PC/SP',body=result)
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
        if self.registers.pc!=(inline_return or pc+3)or self.registers.sp!=sp:raise RuntimeError('Details call has not returned to its real caller')
    def _dispatch(self,pc,targets,methods):
        index=self.registers.a
        if not 0<=index<len(targets):raise InvalidDetailRow('Only original ten row handlers are proven')
        word=pc+2;self.push(word>>8);self.push(word);self.controls(self,0xEADE,targets[index],'dispatch')
        yield from methods[index]()
    def result(self,status,**extra):
        value=super().result(status,**extra)
        return dict(value,source_locations=list(self.source_locations),detail_row=self.memory[0x40D],PPU_jobs=self.memory[0x7E],full_NES_frame=False,PPU_upload_completed=False)
    def run_entry(self,entry=0xA012,registers=None,*,max_source_operations=100000):
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Entry is outside the original details closure')
        if self._program is not None:raise RuntimeError('A real details service is pending; resume it first')
        if registers is None:raise ValueError('Supply actual caller registers and existing RTS frame')
        if tuple(getattr(self.memory,'banks',())[1:3])!=(25,26):raise ValueError('Details requires actual physical25/26 pair')
        if entry in(0xA012,0xB2D7,0xB4BF)and not self.memory[0x7E]&4 and 10<=self.memory[0x40D]<128:raise InvalidDetailRow('Positive row is outside the legal0..9 domain')
        self.source_locations=[];self.source_budget=max_source_operations
        return self._start(lambda:self.routine(entry),registers,'officer_details')
    def tick(self,registers=None):return self.run_entry(0xA012,registers)
    def __call__(self,call):
        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(25,26):return dict(status='dependency',reason='No details body owns this exact pair/entry')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='Another caller owns pending details')
            result=self.resume()
        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':
            self._call_owner=None
            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='Details did not reach actualcaller PC/SP',body=result)
        return result

    def public_detail_row(self):
        """Original $A012: public_detail_row."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xA012)
        yield from self.produce_next_detail_row()
        return

    def produce_next_detail_row(self):
        """Original $B2D7: one real32tile request; busy7Ebit2/negative040D return; advance0..9 thenFF."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB2D7)
        self.a(m[0x007E])
        self._mark(0xB2DA)
        self.a(r.a&0x04)
        self._mark(0xB2DC)
        if not(r.p&Z):
            self._mark(0xB2E8)
            self.rts()
            return
        else:
            self._mark(0xB2DE)
            self.a(0x00)
            self._mark(0xB2E0)
            m[0x0001]=r.a
            self._mark(0xB2E3)
            self.a(m[0x040D])
            self._mark(0xB2E6)
            if not(r.p&N):
                self._mark(0xB2E9)
                self.push(r.a)
                self._mark(0xB2EA)
                self.shift_a("asl")
                self._mark(0xB2EB)
                self._shift(0x0001,"rol")
                self._mark(0xB2EE)
                self.shift_a("asl")
                self._mark(0xB2EF)
                self._shift(0x0001,"rol")
                self._mark(0xB2F2)
                self.shift_a("asl")
                self._mark(0xB2F3)
                self._shift(0x0001,"rol")
                self._mark(0xB2F6)
                self.shift_a("asl")
                self._mark(0xB2F7)
                self._shift(0x0001,"rol")
                self._mark(0xB2FA)
                self.shift_a("asl")
                self._mark(0xB2FB)
                self._shift(0x0001,"rol")
                self._mark(0xB2FE)
                m[0x0382]=r.a
                self._mark(0xB301)
                self.a(m[0x0001])
                self._mark(0xB304)
                m[0x0381]=r.a
                self._mark(0xB307)
                self.a(0x20)
                self._mark(0xB309)
                m[0x0380]=r.a
                self._mark(0xB30C)
                self.a(m[0x040C])
                self._mark(0xB30F)
                m[0x0001]=r.a
                self._mark(0xB312)
                self.a(0x00)
                self._mark(0xB314)
                m[0x0002]=r.a
                self._mark(0xB317)
                m[0x0004]=r.a
                self._mark(0xB31A)
                self.a(0x03)
                self._mark(0xB31C)
                m[0x0003]=r.a
                self._mark(0xB31F)
                yield from self.call(0xB31F,0xEA7C)
                self._mark(0xB322)
                self.a(m[0x0005])
                self._mark(0xB325)
                self.shift_a("asl")
                self._mark(0xB326)
                self.y(r.a)
                self._mark(0xB327)
                self.a(m[(0xB4B9+r.y)&65535])
                self._mark(0xB32A)
                self.flag(C,False)
                self._mark(0xB32B)
                self.add(m[0x0382])
                self._mark(0xB32E)
                m[0x0382]=r.a
                self._mark(0xB331)
                self.a(m[(0xB4BA+r.y)&65535])
                self._mark(0xB334)
                self.add(m[0x0381])
                self._mark(0xB337)
                m[0x0381]=r.a
                self._mark(0xB33A)
                self.y(m[0x040C])
                self._mark(0xB33D)
                self.a(m[(0x0410+r.y)&65535])
                self._mark(0xB340)
                self.cmp(r.a,0xFE)
                self._mark(0xB342)
                if not(r.p&Z):
                    self._mark(0xB34A)
                    self.a(self.pop())
                    self._mark(0xB34B)
                    self.shift_a("asl")
                    self._mark(0xB34C)
                    self.y(r.a)
                else:
                    self._mark(0xB344)
                    self.a(self.pop())
                    self._mark(0xB345)
                    self.y(0x10)
                    self._mark(0xB347)
                self._mark(0xB34D)
                self.a(m[(0xB385+r.y)&65535])
                self._mark(0xB350)
                m[0x0000]=r.a
                self._mark(0xB353)
                self.a(m[(0xB386+r.y)&65535])
                self._mark(0xB356)
                m[0x0001]=r.a
                self._mark(0xB359)
                self.y(0x00)
                while True:
                    self._mark(0xB35B)
                    self.a(m[(self.memory[0x00]|(self.memory[0x01]<<8))+r.y&65535])
                    self._mark(0xB35D)
                    m[(0x0383+r.y)&65535]=r.a
                    self._mark(0xB360)
                    self.y(r.y+1)
                    self._mark(0xB361)
                    self.cmp(r.y,0x20)
                    self._mark(0xB363)
                    if not(r.p&C):
                        continue
                    break
                self._mark(0xB365)
                yield from self.call(0xB365,0xB4BF)
                self._mark(0xB368)
                self.a(0xFF)
                self._mark(0xB36A)
                m[0x03A3]=r.a
                self._mark(0xB36D)
                self.a(m[0x007E])
                self._mark(0xB370)
                self.a(r.a|0x04)
                self._mark(0xB372)
                m[0x007E]=r.a
                self._mark(0xB375)
                self.inc(0x040D)
                self._mark(0xB378)
                self.a(m[0x040D])
                self._mark(0xB37B)
                self.cmp(r.a,0x0A)
                self._mark(0xB37D)
                if not(not(r.p&C)):
                    self._mark(0xB37F)
                    self.a(0xFF)
                    self._mark(0xB381)
                    m[0x040D]=r.a
                self._mark(0xB384)
                self.rts()
                return
            else:
                self._mark(0xB2E8)
                self.rts()
                return

    def populate_detail_values(self):
        """Original $B4BF: selected0410[040C] officer guard<237 andtenrow inline dispatch."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB4BF)
        self.y(m[0x040C])
        self._mark(0xB4C2)
        self.a(m[(0x0410+r.y)&65535])
        self._mark(0xB4C5)
        self.cmp(r.a,0xED)
        self._mark(0xB4C7)
        if not(r.p&C):
            self._mark(0xB4CA)
            yield from self.call(0xB4CA,0xF2D7)
            self._mark(0xB4CD)
            self.a(m[0x0000])
            self._mark(0xB4D0)
            m[0x0010]=r.a
            self._mark(0xB4D3)
            self.a(m[0x0001])
            self._mark(0xB4D6)
            m[0x0011]=r.a
            self._mark(0xB4D9)
            self.a(m[0x040D])
            self._mark(0xB4DC)
            yield from self._dispatch(0xB4DC,(0xB508,0xB52D,0xB507,0xB5A6,0xB630,0xB64D,0xB730,0xB770,0xB4F3,0xB507,),(self.name_diacritic_marks,self.name_health_and_de,self.empty_detail_row,self.level_iq_loyalty,self.terrain_affinity_caption_top,self.troop_strength_experience_values,self.equipment_top_row,self.equipment_bottom_row,self.refresh_equipment_CHR_shadows,self.empty_detail_row,))
            return
        else:
            self._mark(0xB4C9)
            self.rts()
            return

    def refresh_equipment_CHR_shadows(self):
        """Original $B4F3: 0401!=3 copies040E/F→BC/BD."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB4F3)
        self.a(m[0x0401])
        self._mark(0xB4F6)
        self.cmp(r.a,0x03)
        self._mark(0xB4F8)
        if not(bool(r.p&Z)):
            self._mark(0xB4FA)
            self.a(m[0x040E])
            self._mark(0xB4FD)
            m[0x00BC]=r.a
            self._mark(0xB500)
            self.a(m[0x040F])
            self._mark(0xB503)
            m[0x00BD]=r.a
        self._mark(0xB506)
        self.rts()
        return

    def empty_detail_row(self):
        """Original $B507: empty_detail_row."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB507)
        self.rts()
        return

    def name_diacritic_marks(self):
        """Original $B508: copyname39/3A marks withoutadvancingX."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB508)
        self.y(m[0x040C])
        self._mark(0xB50B)
        self.a(m[(0x0410+r.y)&65535])
        self._mark(0xB50E)
        yield from self.call(0xB50E,0xF308)
        self._mark(0xB511)
        self.x(r.a)
        self._mark(0xB512)
        self.y(0x00)
        while True:
            self._mark(0xB514)
            self.a(m[(self.memory[0x00]|(self.memory[0x01]<<8))+r.y&65535])
            self._mark(0xB516)
            if bool(r.p&Z):
                break
            self._mark(0xB518)
            self.cmp(r.a,0x39)
            self._mark(0xB51A)
            if bool(r.p&Z):
                self._mark(0xB525)
                m[(0x038A+r.x)&65535]=r.a
                self._mark(0xB528)
                self.y(r.y+1)
                self._mark(0xB529)
            else:
                self._mark(0xB51C)
                self.cmp(r.a,0x3A)
                self._mark(0xB51E)
                if bool(r.p&Z):
                    self._mark(0xB525)
                    m[(0x038A+r.x)&65535]=r.a
                    self._mark(0xB528)
                    self.y(r.y+1)
                    self._mark(0xB529)
                else:
                    self._mark(0xB520)
                    self.y(r.y+1)
                    self._mark(0xB521)
                    self.x(r.x+1)
                    self._mark(0xB522)
            continue
        self._mark(0xB52C)
        self.rts()
        return

    def name_health_and_de(self):
        """Original $B52D: nameglyphs andrecord0体/record4徳."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB52D)
        self.y(m[0x040C])
        self._mark(0xB530)
        self.a(m[(0x0410+r.y)&65535])
        self._mark(0xB533)
        yield from self.call(0xB533,0xF308)
        self._mark(0xB536)
        self.x(r.a)
        self._mark(0xB537)
        self.y(0x00)
        while True:
            self._mark(0xB539)
            self.a(m[(self.memory[0x00]|(self.memory[0x01]<<8))+r.y&65535])
            self._mark(0xB53B)
            if bool(r.p&Z):
                break
            self._mark(0xB53D)
            self.cmp(r.a,0x39)
            self._mark(0xB53F)
            if not(bool(r.p&Z)):
                self._mark(0xB541)
                self.cmp(r.a,0x3A)
                self._mark(0xB543)
                if not(bool(r.p&Z)):
                    self._mark(0xB545)
                    m[(0x038B+r.x)&65535]=r.a
                    self._mark(0xB548)
                    self.x(r.x+1)
            self._mark(0xB549)
            self.y(r.y+1)
            self._mark(0xB54A)
            continue
        self._mark(0xB54D)
        self.y(0x00)
        self._mark(0xB54F)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB551)
        m[0x0001]=r.a
        self._mark(0xB554)
        self.a(0x00)
        self._mark(0xB556)
        m[0x0002]=r.a
        self._mark(0xB559)
        m[0x0003]=r.a
        self._mark(0xB55C)
        yield from self.call(0xB55C,0xE9BA)
        self._mark(0xB55F)
        self.a(m[0x0007])
        self._mark(0xB562)
        self.shift_a("lsr")
        self._mark(0xB563)
        self.shift_a("lsr")
        self._mark(0xB564)
        self.shift_a("lsr")
        self._mark(0xB565)
        self.shift_a("lsr")
        self._mark(0xB566)
        if not(bool(r.p&Z)):
            self._mark(0xB568)
            self.flag(C,False)
            self._mark(0xB569)
            self.add(0x76)
            self._mark(0xB56B)
            m[0x0398]=r.a
        self._mark(0xB56E)
        self.a(m[0x0007])
        self._mark(0xB571)
        self.a(r.a&0x0F)
        self._mark(0xB573)
        self.flag(C,False)
        self._mark(0xB574)
        self.add(0x76)
        self._mark(0xB576)
        m[0x0399]=r.a
        self._mark(0xB579)
        self.y(0x04)
        self._mark(0xB57B)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB57D)
        m[0x0001]=r.a
        self._mark(0xB580)
        self.a(0x00)
        self._mark(0xB582)
        m[0x0002]=r.a
        self._mark(0xB585)
        m[0x0003]=r.a
        self._mark(0xB588)
        yield from self.call(0xB588,0xE9BA)
        self._mark(0xB58B)
        self.a(m[0x0007])
        self._mark(0xB58E)
        self.shift_a("lsr")
        self._mark(0xB58F)
        self.shift_a("lsr")
        self._mark(0xB590)
        self.shift_a("lsr")
        self._mark(0xB591)
        self.shift_a("lsr")
        self._mark(0xB592)
        if not(bool(r.p&Z)):
            self._mark(0xB594)
            self.flag(C,False)
            self._mark(0xB595)
            self.add(0x76)
            self._mark(0xB597)
            m[0x039E]=r.a
        self._mark(0xB59A)
        self.a(m[0x0007])
        self._mark(0xB59D)
        self.a(r.a&0x0F)
        self._mark(0xB59F)
        self.flag(C,False)
        self._mark(0xB5A0)
        self.add(0x76)
        self._mark(0xB5A2)
        m[0x039F]=r.a
        self._mark(0xB5A5)
        self.rts()
        return

    def level_iq_loyalty(self):
        """Original $B5A6: record11high4+1 level,record2知,record3忠(100→two32tiles)."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB5A6)
        self.y(0x0B)
        self._mark(0xB5A8)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB5AA)
        self.shift_a("lsr")
        self._mark(0xB5AB)
        self.shift_a("lsr")
        self._mark(0xB5AC)
        self.shift_a("lsr")
        self._mark(0xB5AD)
        self.shift_a("lsr")
        self._mark(0xB5AE)
        self.flag(C,False)
        self._mark(0xB5AF)
        self.add(0x01)
        self._mark(0xB5B1)
        m[0x0001]=r.a
        self._mark(0xB5B4)
        self.a(0x00)
        self._mark(0xB5B6)
        m[0x0002]=r.a
        self._mark(0xB5B9)
        m[0x0003]=r.a
        self._mark(0xB5BC)
        yield from self.call(0xB5BC,0xE9BA)
        self._mark(0xB5BF)
        self.a(m[0x0007])
        self._mark(0xB5C2)
        self.a(r.a&0x0F)
        self._mark(0xB5C4)
        self.flag(C,False)
        self._mark(0xB5C5)
        self.add(0x76)
        self._mark(0xB5C7)
        m[0x0391]=r.a
        self._mark(0xB5CA)
        self.y(0x02)
        self._mark(0xB5CC)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB5CE)
        m[0x0001]=r.a
        self._mark(0xB5D1)
        self.a(0x00)
        self._mark(0xB5D3)
        m[0x0002]=r.a
        self._mark(0xB5D6)
        m[0x0003]=r.a
        self._mark(0xB5D9)
        yield from self.call(0xB5D9,0xE9BA)
        self._mark(0xB5DC)
        self.a(m[0x0007])
        self._mark(0xB5DF)
        self.shift_a("lsr")
        self._mark(0xB5E0)
        self.shift_a("lsr")
        self._mark(0xB5E1)
        self.shift_a("lsr")
        self._mark(0xB5E2)
        self.shift_a("lsr")
        self._mark(0xB5E3)
        if not(bool(r.p&Z)):
            self._mark(0xB5E5)
            self.flag(C,False)
            self._mark(0xB5E6)
            self.add(0x76)
            self._mark(0xB5E8)
            m[0x0398]=r.a
        self._mark(0xB5EB)
        self.a(m[0x0007])
        self._mark(0xB5EE)
        self.a(r.a&0x0F)
        self._mark(0xB5F0)
        self.flag(C,False)
        self._mark(0xB5F1)
        self.add(0x76)
        self._mark(0xB5F3)
        m[0x0399]=r.a
        self._mark(0xB5F6)
        self.y(0x03)
        self._mark(0xB5F8)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB5FA)
        m[0x0001]=r.a
        self._mark(0xB5FD)
        self.cmp(r.a,0x64)
        self._mark(0xB5FF)
        if bool(r.p&Z):
            self._mark(0xB627)
            self.a(0x32)
            self._mark(0xB629)
            m[0x039E]=r.a
            self._mark(0xB62C)
            m[0x039F]=r.a
            self._mark(0xB62F)
            self.rts()
            return
        else:
            self._mark(0xB601)
            self.a(0x00)
            self._mark(0xB603)
            m[0x0002]=r.a
            self._mark(0xB606)
            m[0x0003]=r.a
            self._mark(0xB609)
            yield from self.call(0xB609,0xE9BA)
            self._mark(0xB60C)
            self.a(m[0x0007])
            self._mark(0xB60F)
            self.shift_a("lsr")
            self._mark(0xB610)
            self.shift_a("lsr")
            self._mark(0xB611)
            self.shift_a("lsr")
            self._mark(0xB612)
            self.shift_a("lsr")
            self._mark(0xB613)
            if not(bool(r.p&Z)):
                self._mark(0xB615)
                self.flag(C,False)
                self._mark(0xB616)
                self.add(0x76)
                self._mark(0xB618)
                m[0x039E]=r.a
            self._mark(0xB61B)
            self.a(m[0x0007])
            self._mark(0xB61E)
            self.a(r.a&0x0F)
            self._mark(0xB620)
            self.flag(C,False)
            self._mark(0xB621)
            self.add(0x76)
            self._mark(0xB623)
            m[0x039F]=r.a
            self._mark(0xB626)
            self.rts()
            return

    def terrain_affinity_caption_top(self):
        """Original $B630: record11mid2 affinity captiontop."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB630)
        self.y(0x0B)
        self._mark(0xB632)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB634)
        self.shift_a("lsr")
        self._mark(0xB635)
        self.shift_a("lsr")
        self._mark(0xB636)
        self.a(r.a&0x03)
        self._mark(0xB638)
        self.shift_a("asl")
        self._mark(0xB639)
        self.y(r.a)
        self._mark(0xB63A)
        self.a(m[(0xB647+r.y)&65535])
        self._mark(0xB63D)
        m[0x038B]=r.a
        self._mark(0xB640)
        self.a(m[(0xB648+r.y)&65535])
        self._mark(0xB643)
        m[0x038C]=r.a
        self._mark(0xB646)
        self.rts()
        return

    def troop_strength_experience_values(self):
        """Original $B64D: affinitybottom,u10troops,record1武,and2*u16experience lowdecimaldigits."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB64D)
        self.y(0x0B)
        self._mark(0xB64F)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB651)
        self.shift_a("lsr")
        self._mark(0xB652)
        self.shift_a("lsr")
        self._mark(0xB653)
        self.a(r.a&0x03)
        self._mark(0xB655)
        self.shift_a("asl")
        self._mark(0xB656)
        self.y(r.a)
        self._mark(0xB657)
        self.a(m[(0xB713+r.y)&65535])
        self._mark(0xB65A)
        m[0x038B]=r.a
        self._mark(0xB65D)
        self.a(m[(0xB714+r.y)&65535])
        self._mark(0xB660)
        m[0x038C]=r.a
        self._mark(0xB663)
        self.y(0x08)
        self._mark(0xB665)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB667)
        m[0x0001]=r.a
        self._mark(0xB66A)
        self.y(0x09)
        self._mark(0xB66C)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB66E)
        self.a(r.a&0x03)
        self._mark(0xB670)
        m[0x0002]=r.a
        self._mark(0xB673)
        self.a(0x00)
        self._mark(0xB675)
        m[0x0003]=r.a
        self._mark(0xB678)
        yield from self.call(0xB678,0xE9BA)
        self._mark(0xB67B)
        self.x(0x00)
        self._mark(0xB67D)
        self.y(0x00)
        self._mark(0xB67F)
        self.a(m[0x0008])
        self._mark(0xB682)
        yield from self.call(0xB682,0xB719)
        self._mark(0xB685)
        self.a(m[0x0008])
        self._mark(0xB688)
        yield from self.call(0xB688,0xB71D)
        self._mark(0xB68B)
        self.a(m[0x0007])
        self._mark(0xB68E)
        yield from self.call(0xB68E,0xB719)
        self._mark(0xB691)
        self.a(m[0x0007])
        self._mark(0xB694)
        self.a(r.a&0x0F)
        self._mark(0xB696)
        yield from self.call(0xB696,0xB727)
        self._mark(0xB699)
        self.y(0x01)
        self._mark(0xB69B)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB69D)
        m[0x0001]=r.a
        self._mark(0xB6A0)
        self.a(0x00)
        self._mark(0xB6A2)
        m[0x0002]=r.a
        self._mark(0xB6A5)
        m[0x0003]=r.a
        self._mark(0xB6A8)
        yield from self.call(0xB6A8,0xE9BA)
        self._mark(0xB6AB)
        self.a(m[0x0007])
        self._mark(0xB6AE)
        self.shift_a("lsr")
        self._mark(0xB6AF)
        self.shift_a("lsr")
        self._mark(0xB6B0)
        self.shift_a("lsr")
        self._mark(0xB6B1)
        self.shift_a("lsr")
        self._mark(0xB6B2)
        if not(bool(r.p&Z)):
            self._mark(0xB6B4)
            self.flag(C,False)
            self._mark(0xB6B5)
            self.add(0x76)
            self._mark(0xB6B7)
            m[0x0398]=r.a
        self._mark(0xB6BA)
        self.a(m[0x0007])
        self._mark(0xB6BD)
        self.a(r.a&0x0F)
        self._mark(0xB6BF)
        self.flag(C,False)
        self._mark(0xB6C0)
        self.add(0x76)
        self._mark(0xB6C2)
        m[0x0399]=r.a
        self._mark(0xB6C5)
        self.y(0x06)
        self._mark(0xB6C7)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB6C9)
        m[0x0001]=r.a
        self._mark(0xB6CC)
        self.y(0x07)
        self._mark(0xB6CE)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB6D0)
        m[0x0002]=r.a
        self._mark(0xB6D3)
        self.a(0x00)
        self._mark(0xB6D5)
        m[0x0003]=r.a
        self._mark(0xB6D8)
        self._shift(0x0001,"asl")
        self._mark(0xB6DB)
        self._shift(0x0002,"rol")
        self._mark(0xB6DE)
        self._shift(0x0003,"rol")
        self._mark(0xB6E1)
        yield from self.call(0xB6E1,0xE9BA)
        self._mark(0xB6E4)
        self.x(0x00)
        self._mark(0xB6E6)
        self.a(m[0x0009])
        self._mark(0xB6E9)
        self.a(r.a&0x0F)
        self._mark(0xB6EB)
        if not(bool(r.p&Z)):
            self._mark(0xB6ED)
            self.flag(C,False)
            self._mark(0xB6EE)
            self.add(0x76)
            self._mark(0xB6F0)
            m[0x039D]=r.a
            self._mark(0xB6F3)
            self.x(r.x+1)
        self._mark(0xB6F4)
        self.a(m[0x0008])
        self._mark(0xB6F7)
        self.shift_a("lsr")
        self._mark(0xB6F8)
        self.shift_a("lsr")
        self._mark(0xB6F9)
        self.shift_a("lsr")
        self._mark(0xB6FA)
        self.shift_a("lsr")
        self._mark(0xB6FB)
        if not(r.p&Z):
            self._mark(0xB701)
            self.flag(C,False)
            self._mark(0xB702)
            self.add(0x76)
            self._mark(0xB704)
            m[0x039E]=r.a
        else:
            self._mark(0xB6FD)
            self.cmp(r.x,0x00)
            self._mark(0xB6FF)
            if not(bool(r.p&Z)):
                self._mark(0xB701)
                self.flag(C,False)
                self._mark(0xB702)
                self.add(0x76)
                self._mark(0xB704)
                m[0x039E]=r.a
        self._mark(0xB707)
        self.a(m[0x0008])
        self._mark(0xB70A)
        self.a(r.a&0x0F)
        self._mark(0xB70C)
        self.flag(C,False)
        self._mark(0xB70D)
        self.add(0x76)
        self._mark(0xB70F)
        m[0x039F]=r.a
        self._mark(0xB712)
        self.rts()
        return

    def put_BCD_high_nibble(self):
        """Original $B719: put_BCD_high_nibble."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB719)
        self.shift_a("lsr")
        self._mark(0xB71A)
        self.shift_a("lsr")
        self._mark(0xB71B)
        self.shift_a("lsr")
        self._mark(0xB71C)
        self.shift_a("lsr")
        yield from self.put_BCD_low_nibble()
        return

    def put_BCD_low_nibble(self):
        """Original $B71D: put_BCD_low_nibble."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB71D)
        self.a(r.a&0x0F)
        self._mark(0xB71F)
        self.cmp(r.x,0x00)
        self._mark(0xB721)
        if not(r.p&Z):
            yield from self.put_decimal_tile()
            return
        else:
            self._mark(0xB723)
            self.cmp(r.a,0x00)
            self._mark(0xB725)
            if bool(r.p&Z):
                self._mark(0xB72E)
                self.y(r.y+1)
                self._mark(0xB72F)
                self.rts()
                return
            else:
                yield from self.put_decimal_tile()
                return

    def put_decimal_tile(self):
        """Original $B727: put_decimal_tile."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB727)
        self.flag(C,False)
        self._mark(0xB728)
        self.add(0x76)
        self._mark(0xB72A)
        m[(0x0390+r.y)&65535]=r.a
        self._mark(0xB72D)
        self.x(r.x+1)
        self._mark(0xB72E)
        self.y(r.y+1)
        self._mark(0xB72F)
        self.rts()
        return

    def equipment_top_row(self):
        """Original $B730: equipmenttoptiles/CHRcache."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB730)
        self.y(0x0A)
        self._mark(0xB732)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB734)
        m[0x0015]=r.a
        self._mark(0xB737)
        self.a(r.a&0x1F)
        self._mark(0xB739)
        yield from self.call(0xB739,0xB7C1)
        self._mark(0xB73C)
        self.a(0x00)
        self._mark(0xB73E)
        self.x(0x0E)
        self._mark(0xB740)
        self.y(0x01)
        self._mark(0xB742)
        yield from self.call(0xB742,0xB7A2)
        self._mark(0xB745)
        self.y(0x00)
        self._mark(0xB747)
        self.a(m[(self.memory[0x12]|(self.memory[0x13]<<8))+r.y&65535])
        self._mark(0xB749)
        m[0x040E]=r.a
        self._mark(0xB74C)
        self.a(m[0x0015])
        self._mark(0xB74F)
        self.shift_a("rol")
        self._mark(0xB750)
        self.shift_a("rol")
        self._mark(0xB751)
        self.shift_a("rol")
        self._mark(0xB752)
        self.shift_a("rol")
        self._mark(0xB753)
        self.a(r.a&0x07)
        self._mark(0xB755)
        self.flag(C,False)
        self._mark(0xB756)
        self.add(0x18)
        self._mark(0xB758)
        yield from self.call(0xB758,0xB7C1)
        self._mark(0xB75B)
        self.a(0x40)
        self._mark(0xB75D)
        self.x(0x1A)
        self._mark(0xB75F)
        self.y(0x01)
        self._mark(0xB761)
        yield from self.call(0xB761,0xB7A2)
        self._mark(0xB764)
        self.y(0x00)
        self._mark(0xB766)
        self.a(m[(self.memory[0x12]|(self.memory[0x13]<<8))+r.y&65535])
        self._mark(0xB768)
        m[0x040F]=r.a
        self._mark(0xB76B)
        self.y(0x31)
        self._mark(0xB76D)
        yield from self._service(0xF25F)
        return

    def equipment_bottom_row(self):
        """Original $B770: equipmentbottomtiles."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB770)
        self.y(0x0A)
        self._mark(0xB772)
        self.a(m[(self.memory[0x10]|(self.memory[0x11]<<8))+r.y&65535])
        self._mark(0xB774)
        m[0x0015]=r.a
        self._mark(0xB777)
        self.a(r.a&0x1F)
        self._mark(0xB779)
        yield from self.call(0xB779,0xB7C1)
        self._mark(0xB77C)
        self.a(0x00)
        self._mark(0xB77E)
        self.x(0x0E)
        self._mark(0xB780)
        self.y(0x09)
        self._mark(0xB782)
        yield from self.call(0xB782,0xB7A2)
        self._mark(0xB785)
        self.a(m[0x0015])
        self._mark(0xB788)
        self.shift_a("rol")
        self._mark(0xB789)
        self.shift_a("rol")
        self._mark(0xB78A)
        self.shift_a("rol")
        self._mark(0xB78B)
        self.shift_a("rol")
        self._mark(0xB78C)
        self.a(r.a&0x07)
        self._mark(0xB78E)
        self.flag(C,False)
        self._mark(0xB78F)
        self.add(0x18)
        self._mark(0xB791)
        yield from self.call(0xB791,0xB7C1)
        self._mark(0xB794)
        self.a(0x40)
        self._mark(0xB796)
        self.x(0x1A)
        self._mark(0xB798)
        self.y(0x09)
        self._mark(0xB79A)
        yield from self.call(0xB79A,0xB7A2)
        self._mark(0xB79D)
        self.y(0x31)
        self._mark(0xB79F)
        yield from self._service(0xF25F)
        return

    def copy_equipment_tiles(self):
        """Original $B7A2: copy_equipment_tiles."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB7A2)
        m[0x0014]=r.a
        self._mark(0xB7A5)
        self.a(r.y)
        self._mark(0xB7A6)
        self.flag(C,False)
        self._mark(0xB7A7)
        self.add(0x08)
        self._mark(0xB7A9)
        m[0x0002]=r.a
        while True:
            self._mark(0xB7AC)
            self.a(m[(self.memory[0x12]|(self.memory[0x13]<<8))+r.y&65535])
            self._mark(0xB7AE)
            self.cmp(r.a,0x01)
            self._mark(0xB7B0)
            if not(bool(r.p&Z)):
                self._mark(0xB7B2)
                self.flag(C,False)
                self._mark(0xB7B3)
                self.add(m[0x0014])
            self._mark(0xB7B6)
            m[(0x0380+r.x)&65535]=r.a
            self._mark(0xB7B9)
            self.x(r.x+1)
            self._mark(0xB7BA)
            self.y(r.y+1)
            self._mark(0xB7BB)
            self.cmp(r.y,m[0x0002])
            self._mark(0xB7BE)
            if not(r.p&C):
                continue
            break
        self._mark(0xB7C0)
        self.rts()
        return

    def locate_equipment_resource(self):
        """Original $B7C1: locate_equipment_resource."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB7C1)
        self.shift_a("asl")
        self._mark(0xB7C2)
        self.x(r.a)
        self._mark(0xB7C3)
        self.y(0x30)
        self._mark(0xB7C5)
        yield from self.call(0xB7C5,0xF25F)
        self._mark(0xB7C8)
        self.a(m[(0x9B12+r.x)&65535])
        self._mark(0xB7CB)
        m[0x0012]=r.a
        self._mark(0xB7CE)
        self.x(r.x+1)
        self._mark(0xB7CF)
        self.a(m[(0x9B12+r.x)&65535])
        self._mark(0xB7D2)
        self.flag(C,False)
        self._mark(0xB7D3)
        self.add(0x80)
        self._mark(0xB7D5)
        m[0x0013]=r.a
        self._mark(0xB7D8)
        self.rts()
        return

    LOCAL_ENTRIES=(0xA012,0xB2D7,0xB4BF,0xB4F3,0xB507,0xB508,0xB52D,0xB5A6,0xB630,0xB64D,0xB719,0xB71D,0xB727,0xB730,0xB770,0xB7A2,0xB7C1,)

    def routine(self,entry):
        methods={0xA012:self.public_detail_row,0xB2D7:self.produce_next_detail_row,0xB4BF:self.populate_detail_values,0xB4F3:self.refresh_equipment_CHR_shadows,0xB507:self.empty_detail_row,0xB508:self.name_diacritic_marks,0xB52D:self.name_health_and_de,0xB5A6:self.level_iq_loyalty,0xB630:self.terrain_affinity_caption_top,0xB64D:self.troop_strength_experience_values,0xB719:self.put_BCD_high_nibble,0xB71D:self.put_BCD_low_nibble,0xB727:self.put_decimal_tile,0xB730:self.equipment_top_row,0xB770:self.equipment_bottom_row,0xB7A2:self.copy_equipment_tiles,0xB7C1:self.locate_equipment_resource}
        yield from methods[entry]()
