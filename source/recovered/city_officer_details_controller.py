"""Independent five-phase city officer detail controller, physical25 A021.

Static original-byte provenance compiled to named Python if/while/calls.
No runtime opcode/IR/program.json or original-CPU fallback is used. Each
call genuinely returns to its caller, but a requested packet is not a
completed PPU upload. Real busy queue bytes are never acknowledged here.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall
from .scene_shared_services import SceneSharedServices
from .officer_details_ui_services import OfficerDetailsUIServices
from .portrait_ui_services import PortraitUIServices
from .scene_initialization import SceneInitialization
from .controller_helpers import ControlHelpers
ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
@dataclass(frozen=True)
class CityOfficerData:
    rom:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original ROM required')
        return cls(bytes(rom))
class SourceBudget(RuntimeError):pass
class InvalidCityCardPhase(ValueError):pass
class CityOfficerDetailsController(BattleNMIServices):
    FIXED=()
    def __init__(self,memory,data,services=None):
        super().__init__(memory,callbacks=self._resolve_service)
        self.data=data if isinstance(data,CityOfficerData)else CityOfficerData.from_rom(data)
        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=self._resolve_service)
        self.detail_worker=OfficerDetailsUIServices(memory,self.data.rom,services=services)
        self.portrait_worker=PortraitUIServices(memory,self.data.rom,services=services)
        self.initialization=SceneInitialization(memory,self.data.rom,callbacks=services)
        self.external_services=services;self.controls=ControlHelpers();self.source_locations=[];self.source_budget=100000;self._call_owner=None
    def _mark(self,pc):
        self.registers.pc=pc;self.source_locations.append(pc)
        if len(self.source_locations)>self.source_budget:raise SourceBudget('Original city card source operation budget exhausted')
    def _shift(self,address,kind):
        old=self.memory[address];carry=int(bool(self.registers.p&C))
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        self.memory[address]=self.nz((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else (old>>1)|(carry<<7)if kind=='ror'else old>>1)
    def shift_a(self,kind):
        old=self.registers.a;carry=int(bool(self.registers.p&C))
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        return self.a((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else (old>>1)|(carry<<7)if kind=='ror'else old>>1)
    def _resolve_service(self,call):
        pair=tuple(call.entry_banks[1:3])
        if pair==(25,26) and call.target==0xB2D7:result=self.detail_worker(call)
        elif pair==(25,26) and call.target==0xCE1F:result=self.portrait_worker(call)
        elif pair==(29,30) and call.target in(0xA015,0xDBB1):result=self.initialization.banked_graphics(call)
        elif call.target in self.shared.FIXED:result=self.shared(call)
        elif self.external_services is not None:result=self.external_services(call)
        else:return dict(status='dependency',reason='No independent city-card helper owns this exact entry',target=call.target)
        if not isinstance(result,dict)or result.get('status')!='returned':return dict(status='dependency',body=result)
        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='City card helper has not reached actual caller PC/SP',body=result)
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
        if self.registers.pc!=(inline_return or pc+3)or self.registers.sp!=sp:raise RuntimeError('City card call has not returned to its real caller')
    def _dispatch(self,pc,targets,methods):
        index=self.registers.a
        if not 0<=index<len(targets):raise InvalidCityCardPhase('Only original five city-card phases are proven')
        word=pc+2;self.push(word>>8);self.push(word);self.controls(self,0xEADE,targets[index],'dispatch')
        yield from methods[index]()
    def result(self,status,**extra):
        value=super().result(status,**extra)
        return dict(value,source_locations=list(self.source_locations),city_card_phase=self.memory[0x401],detail_row=self.memory[0x40D],PPU_jobs=self.memory[0x7E],full_NES_frame=False,PPU_upload_completed=False)
    def run_entry(self,entry=0xA021,registers=None,*,max_source_operations=100000):
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Entry is outside the original city card closure')
        if self._program is not None:raise RuntimeError('A real city card service is pending; resume it first')
        if registers is None:raise ValueError('Supply actual caller registers and existing RTS frame')
        if tuple(getattr(self.memory,'banks',())[1:3])!=(25,26):raise ValueError('City card requires actual physical25/26 pair')
        if entry in(0xA021,0xAFE5)and self.memory[0x401]>=5:raise InvalidCityCardPhase('Legal city-card phases are0..4')
        self.source_locations=[];self.source_budget=max_source_operations
        return self._start(lambda:self.routine(entry),registers,'city_officer_details')
    def tick(self,registers=None):return self.run_entry(0xA021,registers)
    def __call__(self,call):
        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(25,26):return dict(status='dependency',reason='No city card body owns this exact pair/entry')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='Another caller owns pending city card')
            result=self.resume()
        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':
            self._call_owner=None
            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='City card did not reach actualcaller PC/SP',body=result)
        return result

    def public_city_card(self):
        """Original $A021: public_city_card."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xA021)
        yield from self.city_card_phase_dispatch()
        return

    def city_card_phase_dispatch(self):
        """Original $AFE5: city_card_phase_dispatch."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xAFE5)
        self.a(m[0x0401])
        self._mark(0xAFE8)
        yield from self._dispatch(0xAFE8,(0xAFF5,0xB041,0xB086,0xB136,0xB155,),(self.initialize_city_cards,self.produce_initial_detail_rows,self.show_selected_card_and_inputs,self.produce_adjacent_card,self.animate_card_transition,))
        return

    def initialize_city_cards(self):
        """Original $AFF5: palette0, compact ten city officers, begin ten-row packet producer."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xAFF5)
        self.a(0x00)
        self._mark(0xAFF7)
        m[0x0000]=r.a
        self._mark(0xAFFA)
        self.y(0x3D)
        self._mark(0xAFFC)
        yield from self.call(0xAFFC,0xEE07,inline_return=0xB001) # inline target$A015, Y selector
        self._mark(0xB001)
        self.a(0xFF)
        self._mark(0xB003)
        m[0x04E4]=r.a
        self._mark(0xB006)
        self.a(0x00)
        self._mark(0xB008)
        m[0x040C]=r.a
        self._mark(0xB00B)
        m[0x040D]=r.a
        self._mark(0xB00E)
        self.inc(0x0401)
        self._mark(0xB011)
        self.a(0x08)
        self._mark(0xB013)
        m[0x00BA]=r.a
        self._mark(0xB016)
        self.a(0x06)
        self._mark(0xB018)
        m[0x00BB]=r.a
        self._mark(0xB01B)
        self.y(0x00)
        self._mark(0xB01D)
        self.a(0xFF)
        while True:
            self._mark(0xB01F)
            m[(0x0410+r.y)&65535]=r.a
            self._mark(0xB022)
            self.y(r.y+1)
            self._mark(0xB023)
            self.cmp(r.y,0x0A)
            self._mark(0xB025)
            if not(r.p&C):
                continue
            break
        self._mark(0xB027)
        self.a(m[0x0402])
        self._mark(0xB02A)
        yield from self.call(0xB02A,0xF2AF)
        self._mark(0xB02D)
        self.x(0x00)
        self._mark(0xB02F)
        self.y(0x11)
        while True:
            self._mark(0xB031)
            self.a(m[(self.memory[0x00]|(self.memory[0x01]<<8))+r.y&65535])
            self._mark(0xB033)
            self.cmp(r.a,0xFF)
            self._mark(0xB035)
            if not(bool(r.p&Z)):
                self._mark(0xB037)
                m[(0x0410+r.x)&65535]=r.a
                self._mark(0xB03A)
                self.x(r.x+1)
            self._mark(0xB03B)
            self.y(r.y+1)
            self._mark(0xB03C)
            self.cmp(r.y,0x1B)
            self._mark(0xB03E)
            if not(r.p&C):
                continue
            break
        self._mark(0xB040)
        self.rts()
        return

    def produce_initial_detail_rows(self):
        """Original $B041: advance original producer until040D==FF then configure original split/scroll."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB041)
        yield from self.call(0xB041,0xB2D7)
        self._mark(0xB044)
        self.a(m[0x040D])
        self._mark(0xB047)
        self.cmp(r.a,0xFF)
        self._mark(0xB049)
        if not(not(r.p&Z)):
            self._mark(0xB04B)
            self.a(0x00)
            self._mark(0xB04D)
            m[0x0096]=r.a
            self._mark(0xB050)
            self.a(0x01)
            self._mark(0xB052)
            m[0x0097]=r.a
            self._mark(0xB055)
            self.a(0x00)
            self._mark(0xB057)
            m[0x0098]=r.a
            self._mark(0xB05A)
            self.a(0x01)
            self._mark(0xB05C)
            m[0x0061]=r.a
            self._mark(0xB05F)
            self.a(0x40)
            self._mark(0xB061)
            m[0x0068]=r.a
            self._mark(0xB064)
            self.a(0x18)
            self._mark(0xB066)
            m[0x006A]=r.a
            self._mark(0xB069)
            self.a(0x20)
            self._mark(0xB06B)
            m[0x006C]=r.a
            self._mark(0xB06E)
            self.a(0x1A)
            self._mark(0xB070)
            m[0x006E]=r.a
            self._mark(0xB073)
            self.a(0xF0)
            self._mark(0xB075)
            m[0x0070]=r.a
            self._mark(0xB078)
            self.a(0xF1)
            self._mark(0xB07A)
            m[0x0071]=r.a
            self._mark(0xB07D)
            self.inc(0x0401)
            self._mark(0xB080)
            self.a(0x00)
            self._mark(0xB082)
            m[0x0408]=r.a
        self._mark(0xB085)
        self.rts()
        return

    def show_selected_card_and_inputs(self):
        """Original $B086: selected officer portrait and real directional/button state."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB086)
        self.a(0xAE)
        self._mark(0xB088)
        m[0x000A]=r.a
        self._mark(0xB08B)
        self.x(m[0x0408])
        self._mark(0xB08E)
        self.a(m[(0x0410+r.x)&65535])
        self._mark(0xB091)
        m[0x0000]=r.a
        self._mark(0xB094)
        yield from self.call(0xB094,0xCE1F)
        self._mark(0xB097)
        self.a(m[0x0472])
        self._mark(0xB09A)
        if not(r.p&Z):
            self._mark(0xB0AA)
            self.a(m[0x0140])
            self._mark(0xB0AD)
            if bool(r.p&Z):
                self._mark(0xB0B0)
                self.a(m[0x0472])
                self._mark(0xB0B3)
                if bool(r.p&N):
                    self._mark(0xB0BF)
                    self.a(0x00)
                    self._mark(0xB0C1)
                    m[0x0472]=r.a
                    self._mark(0xB0C4)
                    self.rts()
                    return
                else:
                    self._mark(0xB0B5)
                    if bool(r.p&Z):
                        self._mark(0xB0C5)
                        self.a(0x80)
                        self._mark(0xB0C7)
                        m[0x0140]=r.a
                        self._mark(0xB0CA)
                        self.inc(0x0472)
                        self._mark(0xB0CD)
                        self.rts()
                        return
                    else:
                        self._mark(0xB0B7)
                        self.cmp(r.a,0x0A)
                        self._mark(0xB0B9)
                        if bool(r.p&Z):
                            self._mark(0xB0CE)
                            self.a(0x80)
                            self._mark(0xB0D0)
                            m[0x0140]=r.a
                            self._mark(0xB0D3)
                            self.a(m[0x0473])
                            self._mark(0xB0D6)
                            self.a(r.a^0x03)
                            self._mark(0xB0D8)
                            m[0x0473]=r.a
                            self._mark(0xB0DB)
                            self.a(r.a|m[0x0150])
                            self._mark(0xB0DE)
                            m[0x0150]=r.a
                            self._mark(0xB0E1)
                            self.a(0x80)
                            self._mark(0xB0E3)
                            m[0x0472]=r.a
                            self._mark(0xB0E6)
                            self.rts()
                            return
                        else:
                            self._mark(0xB0BB)
                            self.inc(0x0472)
                            self._mark(0xB0BE)
                            self.rts()
                            return
            else:
                self._mark(0xB0AF)
                self.rts()
                return
        else:
            self._mark(0xB09C)
            yield from self.call(0xB09C,0xB209)
            yield from self.confirm_or_cancel_card()
            return

    def confirm_or_cancel_card(self):
        """Original $B09F: panel readiness0140 and original confirm/cancel handling."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB09F)
        self.a(m[0x0081])
        self._mark(0xB0A2)
        self.shift_a("lsr")
        self._mark(0xB0A3)
        if not(r.p&C):
            self._mark(0xB0E7)
            self.shift_a("lsr")
            self._mark(0xB0E8)
            if not(not(r.p&C)):
                self._mark(0xB0EA)
                self.a(m[0x0470])
                self._mark(0xB0ED)
                m[0x0400]=r.a
                self._mark(0xB0F0)
                self.a(m[0x0471])
                self._mark(0xB0F3)
                m[0x0401]=r.a
                self._mark(0xB0F6)
                self.a(0x40)
                self._mark(0xB0F8)
                m[0x0068]=r.a
                self._mark(0xB0FB)
                self.a(0x14)
                self._mark(0xB0FD)
                m[0x006A]=r.a
                self._mark(0xB100)
                self.a(0x1E)
                self._mark(0xB102)
                m[0x006C]=r.a
                self._mark(0xB105)
                self.a(0x20)
                self._mark(0xB107)
                m[0x006E]=r.a
                self._mark(0xB10A)
                self.a(0x0D)
                self._mark(0xB10C)
                m[0x0070]=r.a
                self._mark(0xB10F)
                self.a(0xF2)
                self._mark(0xB111)
                m[0x0071]=r.a
                self._mark(0xB114)
                self.a(0x03)
                self._mark(0xB116)
                m[0x0061]=r.a
                self._mark(0xB119)
                self.a(0x00)
                self._mark(0xB11B)
                m[0x0096]=r.a
                self._mark(0xB11E)
                m[0x0097]=r.a
                self._mark(0xB121)
                self.a(0xA0)
                self._mark(0xB123)
                m[0x0098]=r.a
                self._mark(0xB126)
                self.a(0x00)
                self._mark(0xB128)
                m[0x04E4]=r.a
                self._mark(0xB12B)
                self.a(0x09)
                self._mark(0xB12D)
                m[0x00BB]=r.a
                self._mark(0xB130)
                self.a(0x0D)
                self._mark(0xB132)
                m[0x00BC]=r.a
            self._mark(0xB135)
            self.rts()
            return
        else:
            self._mark(0xB0A5)
            self.a(m[0x0470])
            self._mark(0xB0A8)
            if bool(r.p&Z):
                self._mark(0xB0EA)
                self.a(m[0x0470])
                self._mark(0xB0ED)
                m[0x0400]=r.a
                self._mark(0xB0F0)
                self.a(m[0x0471])
                self._mark(0xB0F3)
                m[0x0401]=r.a
                self._mark(0xB0F6)
                self.a(0x40)
                self._mark(0xB0F8)
                m[0x0068]=r.a
                self._mark(0xB0FB)
                self.a(0x14)
                self._mark(0xB0FD)
                m[0x006A]=r.a
                self._mark(0xB100)
                self.a(0x1E)
                self._mark(0xB102)
                m[0x006C]=r.a
                self._mark(0xB105)
                self.a(0x20)
                self._mark(0xB107)
                m[0x006E]=r.a
                self._mark(0xB10A)
                self.a(0x0D)
                self._mark(0xB10C)
                m[0x0070]=r.a
                self._mark(0xB10F)
                self.a(0xF2)
                self._mark(0xB111)
                m[0x0071]=r.a
                self._mark(0xB114)
                self.a(0x03)
                self._mark(0xB116)
                m[0x0061]=r.a
                self._mark(0xB119)
                self.a(0x00)
                self._mark(0xB11B)
                m[0x0096]=r.a
                self._mark(0xB11E)
                m[0x0097]=r.a
                self._mark(0xB121)
                self.a(0xA0)
                self._mark(0xB123)
                m[0x0098]=r.a
                self._mark(0xB126)
                self.a(0x00)
                self._mark(0xB128)
                m[0x04E4]=r.a
                self._mark(0xB12B)
                self.a(0x09)
                self._mark(0xB12D)
                m[0x00BB]=r.a
                self._mark(0xB130)
                self.a(0x0D)
                self._mark(0xB132)
                m[0x00BC]=r.a
                self._mark(0xB135)
                self.rts()
                return
            else:
                self._mark(0xB0AA)
                self.a(m[0x0140])
                self._mark(0xB0AD)
                if bool(r.p&Z):
                    self._mark(0xB0B0)
                    self.a(m[0x0472])
                    self._mark(0xB0B3)
                    if bool(r.p&N):
                        self._mark(0xB0BF)
                        self.a(0x00)
                        self._mark(0xB0C1)
                        m[0x0472]=r.a
                        self._mark(0xB0C4)
                        self.rts()
                        return
                    else:
                        self._mark(0xB0B5)
                        if bool(r.p&Z):
                            self._mark(0xB0C5)
                            self.a(0x80)
                            self._mark(0xB0C7)
                            m[0x0140]=r.a
                            self._mark(0xB0CA)
                            self.inc(0x0472)
                            self._mark(0xB0CD)
                            self.rts()
                            return
                        else:
                            self._mark(0xB0B7)
                            self.cmp(r.a,0x0A)
                            self._mark(0xB0B9)
                            if bool(r.p&Z):
                                self._mark(0xB0CE)
                                self.a(0x80)
                                self._mark(0xB0D0)
                                m[0x0140]=r.a
                                self._mark(0xB0D3)
                                self.a(m[0x0473])
                                self._mark(0xB0D6)
                                self.a(r.a^0x03)
                                self._mark(0xB0D8)
                                m[0x0473]=r.a
                                self._mark(0xB0DB)
                                self.a(r.a|m[0x0150])
                                self._mark(0xB0DE)
                                m[0x0150]=r.a
                                self._mark(0xB0E1)
                                self.a(0x80)
                                self._mark(0xB0E3)
                                m[0x0472]=r.a
                                self._mark(0xB0E6)
                                self.rts()
                                return
                            else:
                                self._mark(0xB0BB)
                                self.inc(0x0472)
                                self._mark(0xB0BE)
                                self.rts()
                                return
                else:
                    self._mark(0xB0AF)
                    self.rts()
                    return

    def produce_adjacent_card(self):
        """Original $B136: real adjacent card rows and portrait; next phase only when040D==FF."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB136)
        yield from self.call(0xB136,0xB2D7)
        self._mark(0xB139)
        self.a(0xAE)
        self._mark(0xB13B)
        m[0x000A]=r.a
        self._mark(0xB13E)
        self.x(m[0x0408])
        self._mark(0xB141)
        self.a(m[(0x0410+r.x)&65535])
        self._mark(0xB144)
        m[0x0000]=r.a
        self._mark(0xB147)
        yield from self.call(0xB147,0xCE1F)
        self._mark(0xB14A)
        self.a(m[0x040D])
        self._mark(0xB14D)
        self.cmp(r.a,0xFF)
        self._mark(0xB14F)
        if not(not(r.p&Z)):
            self._mark(0xB151)
            self.inc(0x0401)
        self._mark(0xB154)
        self.rts()
        return

    def animate_card_transition(self):
        """Original $B155: two portrait positions, scroll direction, eighty pixel transition."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB155)
        yield from self.call(0xB155,0xB285)
        self._mark(0xB158)
        self.a(m[0x040A])
        self._mark(0xB15B)
        if not(r.p&Z):
            self._mark(0xB1AE)
            self.a(m[0x0409])
            self._mark(0xB1B1)
            self.cmp(r.a,0x29)
            self._mark(0xB1B3)
            if not(r.p&C):
                self._mark(0xB1DA)
                self.a(0xB0)
                self._mark(0xB1DC)
                self.flag(C,False)
                self._mark(0xB1DD)
                self.add(m[0x0409])
                self._mark(0xB1E0)
                m[0x000A]=r.a
                self._mark(0xB1E3)
                self.x(m[0x0408])
                self._mark(0xB1E6)
                yield from self.call(0xB1E6,0xB1FF)
                self._mark(0xB1E9)
                self.a(0x60)
                self._mark(0xB1EB)
                self.flag(C,False)
                self._mark(0xB1EC)
                self.add(m[0x0409])
                self._mark(0xB1EF)
                m[0x000A]=r.a
                self._mark(0xB1F2)
                self.x(m[0x0408])
                self._mark(0xB1F5)
                self.x(r.x-1)
                self._mark(0xB1F6)
                yield from self.call(0xB1F6,0xB1FF)
                self._mark(0xB1F9)
                yield from self.call(0xB1F9,0xB260)
                self._mark(0xB1FC)
            else:
                self._mark(0xB1B5)
                self.a(0x60)
                self._mark(0xB1B7)
                self.flag(C,False)
                self._mark(0xB1B8)
                self.add(m[0x0409])
                self._mark(0xB1BB)
                m[0x000A]=r.a
                self._mark(0xB1BE)
                self.x(m[0x0408])
                self._mark(0xB1C1)
                self.x(r.x-1)
                self._mark(0xB1C2)
                yield from self.call(0xB1C2,0xB1FF)
                self._mark(0xB1C5)
                self.a(0xB0)
                self._mark(0xB1C7)
                self.flag(C,False)
                self._mark(0xB1C8)
                self.add(m[0x0409])
                self._mark(0xB1CB)
                m[0x000A]=r.a
                self._mark(0xB1CE)
                self.x(m[0x0408])
                self._mark(0xB1D1)
                yield from self.call(0xB1D1,0xB1FF)
                self._mark(0xB1D4)
                yield from self.call(0xB1D4,0xB260)
                self._mark(0xB1D7)
        else:
            self._mark(0xB15D)
            self.a(m[0x0409])
            self._mark(0xB160)
            self.cmp(r.a,0x29)
            self._mark(0xB162)
            if bool(r.p&C):
                self._mark(0xB189)
                self.a(0xFC)
                self._mark(0xB18B)
                self.flag(C,True)
                self._mark(0xB18C)
                self.add(m[0x0409],subtract=True)
                self._mark(0xB18F)
                m[0x000A]=r.a
                self._mark(0xB192)
                self.x(m[0x0408])
                self._mark(0xB195)
                self.x(r.x+1)
                self._mark(0xB196)
                yield from self.call(0xB196,0xB1FF)
                self._mark(0xB199)
                self.a(0xAC)
                self._mark(0xB19B)
                self.flag(C,True)
                self._mark(0xB19C)
                self.add(m[0x0409],subtract=True)
                self._mark(0xB19F)
                m[0x000A]=r.a
                self._mark(0xB1A2)
                self.x(m[0x0408])
                self._mark(0xB1A5)
                yield from self.call(0xB1A5,0xB1FF)
                self._mark(0xB1A8)
                yield from self.call(0xB1A8,0xB260)
                self._mark(0xB1AB)
            else:
                self._mark(0xB164)
                self.a(0xAC)
                self._mark(0xB166)
                self.flag(C,True)
                self._mark(0xB167)
                self.add(m[0x0409],subtract=True)
                self._mark(0xB16A)
                m[0x000A]=r.a
                self._mark(0xB16D)
                self.x(m[0x0408])
                self._mark(0xB170)
                yield from self.call(0xB170,0xB1FF)
                self._mark(0xB173)
                self.a(0xFC)
                self._mark(0xB175)
                self.flag(C,True)
                self._mark(0xB176)
                self.add(m[0x0409],subtract=True)
                self._mark(0xB179)
                m[0x000A]=r.a
                self._mark(0xB17C)
                self.x(m[0x0408])
                self._mark(0xB17F)
                self.x(r.x+1)
                self._mark(0xB180)
                yield from self.call(0xB180,0xB1FF)
                self._mark(0xB183)
                yield from self.call(0xB183,0xB260)
                self._mark(0xB186)
        yield from self.confirm_or_cancel_card()
        return

    def portrait_for_roster_slot(self):
        """Original $B1FF: portrait_for_roster_slot."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB1FF)
        self.a(m[(0x0410+r.x)&65535])
        self._mark(0xB202)
        m[0x0000]=r.a
        self._mark(0xB205)
        yield from self.call(0xB205,0xCE1F)
        self._mark(0xB208)
        self.rts()
        return

    def begin_previous_or_next_card(self):
        """Original $B209: previous/next roster boundaries, initialize next card row and scroll direction."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB209)
        self.a(m[0x0083])
        self._mark(0xB20C)
        self.a(r.a&0x10)
        self._mark(0xB20E)
        if not(bool(r.p&Z)):
            self._mark(0xB210)
            self.a(m[0x0408])
            self._mark(0xB213)
            if not(bool(r.p&Z)):
                self._mark(0xB215)
                self.a(0x00)
                self._mark(0xB217)
                m[0x0409]=r.a
                self._mark(0xB21A)
                self.a(0x01)
                self._mark(0xB21C)
                m[0x040A]=r.a
                self._mark(0xB21F)
                self.inc(0x0401)
                self._mark(0xB222)
                self.a(0x00)
                self._mark(0xB224)
                m[0x040D]=r.a
                self._mark(0xB227)
                self.a(m[0x0408])
                self._mark(0xB22A)
                self.flag(C,True)
                self._mark(0xB22B)
                self.add(0x01,subtract=True)
                self._mark(0xB22D)
                m[0x040C]=r.a
        self._mark(0xB230)
        self.a(m[0x0083])
        self._mark(0xB233)
        self.a(r.a&0x20)
        self._mark(0xB235)
        if not(bool(r.p&Z)):
            self._mark(0xB237)
            self.y(m[0x0408])
            self._mark(0xB23A)
            self.cmp(r.y,0x09)
            self._mark(0xB23C)
            if not(bool(r.p&C)):
                self._mark(0xB23E)
                self.y(r.y+1)
                self._mark(0xB23F)
                self.a(m[(0x0410+r.y)&65535])
                self._mark(0xB242)
                self.cmp(r.a,0xFF)
                self._mark(0xB244)
                if not(bool(r.p&Z)):
                    self._mark(0xB246)
                    self.a(0x00)
                    self._mark(0xB248)
                    m[0x0409]=r.a
                    self._mark(0xB24B)
                    m[0x040A]=r.a
                    self._mark(0xB24E)
                    self.inc(0x0401)
                    self._mark(0xB251)
                    self.a(0x00)
                    self._mark(0xB253)
                    m[0x040D]=r.a
                    self._mark(0xB256)
                    self.a(m[0x0408])
                    self._mark(0xB259)
                    self.flag(C,False)
                    self._mark(0xB25A)
                    self.add(0x01)
                    self._mark(0xB25C)
                    m[0x040C]=r.a
        self._mark(0xB25F)
        self.rts()
        return

    def advance_card_animation(self):
        """Original $B260: clear81 during animation, two-pixel increments and actual index change."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB260)
        self.a(0x00)
        self._mark(0xB262)
        m[0x0081]=r.a
        self._mark(0xB265)
        self.inc(0x0409)
        self._mark(0xB268)
        self.inc(0x0409)
        self._mark(0xB26B)
        self.a(m[0x0409])
        self._mark(0xB26E)
        self.cmp(r.a,0x50)
        self._mark(0xB270)
        if not(r.p&C):
            self._mark(0xB284)
            self.rts()
            return
        else:
            self._mark(0xB272)
            self.inc(0x0401,-1)
            self._mark(0xB275)
            self.inc(0x0401,-1)
            self._mark(0xB278)
            self.a(m[0x040A])
            self._mark(0xB27B)
            if not(r.p&Z):
                self._mark(0xB281)
                self.inc(0x0408,-1)
                self._mark(0xB284)
                self.rts()
                return
            else:
                self._mark(0xB27D)
                self.inc(0x0408)
                self._mark(0xB280)
                self.rts()
                return

    def update_card_scroll_and_chr(self):
        """Original $B285: CHR cache copy at original offset64/16 and 240-pixel scroll wrap."""
        r=self.registers;m=self.memory
        yield from () # coroutine carrier; no service completion implied
        self._mark(0xB285)
        self.a(m[0x040A])
        self._mark(0xB288)
        if not(r.p&Z):
            self._mark(0xB2B0)
            self.a(m[0x0409])
            self._mark(0xB2B3)
            self.cmp(r.a,0x10)
            self._mark(0xB2B5)
            if not(not(r.p&Z)):
                self._mark(0xB2B7)
                self.a(m[0x040E])
                self._mark(0xB2BA)
                m[0x00BC]=r.a
                self._mark(0xB2BD)
                self.a(m[0x040F])
                self._mark(0xB2C0)
                m[0x00BD]=r.a
            self._mark(0xB2C3)
            self.inc(0x0098,-1)
            self._mark(0xB2C6)
            self.inc(0x0098,-1)
            self._mark(0xB2C9)
            self.a(m[0x0098])
            self._mark(0xB2CC)
            self.cmp(r.a,0xF0)
            self._mark(0xB2CE)
            if not(not(r.p&C)):
                self._mark(0xB2D0)
                self.flag(C,True)
                self._mark(0xB2D1)
                self.add(0x10,subtract=True)
                self._mark(0xB2D3)
                m[0x0098]=r.a
            self._mark(0xB2D6)
            self.rts()
            return
        else:
            self._mark(0xB28A)
            self.a(m[0x0409])
            self._mark(0xB28D)
            self.cmp(r.a,0x40)
            self._mark(0xB28F)
            if not(not(r.p&Z)):
                self._mark(0xB291)
                self.a(m[0x040E])
                self._mark(0xB294)
                m[0x00BC]=r.a
                self._mark(0xB297)
                self.a(m[0x040F])
                self._mark(0xB29A)
                m[0x00BD]=r.a
            self._mark(0xB29D)
            self.inc(0x0098)
            self._mark(0xB2A0)
            self.inc(0x0098)
            self._mark(0xB2A3)
            self.a(m[0x0098])
            self._mark(0xB2A6)
            self.cmp(r.a,0xF0)
            self._mark(0xB2A8)
            if not(r.p&C):
                self._mark(0xB2D6)
                self.rts()
                return
            else:
                self._mark(0xB2AA)
                self.a(0x00)
                self._mark(0xB2AC)
                m[0x0098]=r.a
                self._mark(0xB2AF)
                self.rts()
                return

    LOCAL_ENTRIES=(0xA021,0xAFE5,0xAFF5,0xB041,0xB086,0xB09F,0xB136,0xB155,0xB1FF,0xB209,0xB260,0xB285,)

    def routine(self,entry):
        methods={0xA021:self.public_city_card,0xAFE5:self.city_card_phase_dispatch,0xAFF5:self.initialize_city_cards,0xB041:self.produce_initial_detail_rows,0xB086:self.show_selected_card_and_inputs,0xB09F:self.confirm_or_cancel_card,0xB136:self.produce_adjacent_card,0xB155:self.animate_card_transition,0xB1FF:self.portrait_for_roster_slot,0xB209:self.begin_previous_or_next_card,0xB260:self.advance_card_animation,0xB285:self.update_card_scroll_and_chr}
        yield from methods[entry]()
