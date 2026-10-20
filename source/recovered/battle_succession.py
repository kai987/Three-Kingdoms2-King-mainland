"""Actual postbattle city13 succession, player selection and faction retirement.

Direct named Python phases preserve candidate ordering, byte arithmetic,
real caller frames and explicit display/input dependencies. Native postbattle
observations select this consumer; they do not imply DomesticCA19 was called.
No ROM/IR execution, interrupt scheduling or acknowledgement is synthesized.
"""
class _ContinueLoop_A1ED(Exception):pass
class _ContinueLoop_A1F3(Exception):pass
class _ContinueLoop_BE48(Exception):pass
class _ContinueLoop_BFDE(Exception):pass
class _ContinueLoop_C01E(Exception):pass
class _ContinueLoop_C03E(Exception):pass
class _ContinueLoop_C0AB(Exception):pass
class _ContinueLoop_C0C1(Exception):pass
class _ContinueLoop_C17B(Exception):pass
class _ContinueLoop_C1E5(Exception):pass
class _ContinueLoop_C2AB(Exception):pass
class _ContinueLoop_C2CD(Exception):pass
class _ContinueLoop_C71B(Exception):pass

from dataclasses import dataclass
from .global_ui_controller import UIControlBase,UIRegisters,C,Z,I,D,B,U,V,N
from .battle_nmi_services import ServiceCall

CITY_MAIN=0x400
POSTBATTLE_PHASE=0x401
SUCCESSION_PHASE=0x402
AFFECTED_RULER=0x40A
OLD_LEADER=0x40B
SUCCESSOR_CITY=0x40C
SUCCESSOR=0x40D
FOLLOWER_CITY=0x40E
FOLLOWER_ROSTER=0x40F
RETURN_PHASE=0x470
NO_SUCCESSOR_PHASE=0x471
RETURN_MAIN=0x472
RETURN_MAIN_PHASE=0x473
NEW_BUTTONS=0x81
REPEAT_BUTTONS=0x87
GLOBAL=0x7A
NMI_SCENE=0x78
PPU_JOBS=0x7E
NOTICE_TIMER=0x4D0

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SuccessionRegisters=UIRegisters

@dataclass(frozen=True)
class SuccessionBlockBudget:
    pc:int
    reason:str='Explicit structured-control block budget; no artificial return'

class BattleSuccession(UIControlBase):
    """Physical25/26 A00C ->AD81, actual city main13 postbattle consumer.

    PUBLIC owns only the real export/body. LOCAL entries are separately
    exposed for bounded original CPU tests, not broad coordinator routing.
    The four dispatch indices are postbattle0401<7, player0402<8,
    computer0402<6 and retirement0402<3. Out-of-table fixtures are rejected
    before decoding any original table-outside bytes.
    """
    PAIR=(25,26)
    PUBLIC_ENTRIES=(0xA00C,0xAD81)
    def __init__(self,memory,rom,services=None):
        super().__init__(memory,rom,services);self._call_owner=None
    def fields(self):
        m=self.memory
        return dict(global_state=m[GLOBAL],NMI_scene=m[NMI_SCENE],city_main=m[CITY_MAIN],
            postbattle_phase=m[POSTBATTLE_PHASE],succession_phase=m[SUCCESSION_PHASE],
            affected_ruler=m[AFFECTED_RULER],old_leader=m[OLD_LEADER],
            successor=m[SUCCESSOR],successor_city=m[SUCCESSOR_CITY],
            notice_timer=m[NOTICE_TIMER],return_state=tuple(m[x]for x in range(RETURN_PHASE,RETURN_MAIN_PHASE+1)),
            cooperation_request=m[0x6F8B],PPU_jobs=m[PPU_JOBS])
    def _checkpoint(self,pc):
        self.registers.pc=pc
        if self._blocks>=self._limit:yield SuccessionBlockBudget(pc)
        self._blocks+=1
    def _drive(self):
        while True:
            if self.pending is not None:
                if isinstance(self.pending,SuccessionBlockBudget):return self._result('budget')
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def resume(self,*,max_blocks=None):
        if self._program is None:raise RuntimeError('No actual pending postbattle caller')
        if max_blocks is not None:
            if not isinstance(max_blocks,int)or max_blocks<=0:raise ValueError('Explicit positive additional block budget required')
            if not isinstance(self.pending,SuccessionBlockBudget):raise ValueError('No structured budget boundary is pending')
            self._limit=self._blocks+max_blocks;self.pending=None
        return self._drive()
    def run_entry(self,entry=0xA00C,*,registers=None,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('Supply actual caller registers and existing stack; no seeded return')
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Entry outside original bounded postbattle closure')
        if tuple(getattr(self.memory,'banks',())[1:3])!=self.PAIR:raise ValueError('Succession entry requires physical25/26 caller context')
        if not isinstance(max_blocks,int)or max_blocks<0:raise ValueError('Nonnegative explicit block budget required')
        actual_return=((self.memory[0x100+((registers.sp+1)&255)]|self.memory[0x100+((registers.sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual_return:raise ValueError('Caller returnPC must match the existing stack word')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA00C,registers=registers,**kwargs)

    LOCAL_ENTRIES=(40972, 41410, 41451, 44417, 44420, 44437, 44458, 44557, 44625, 48641, 48644, 48663, 48686, 48771, 48849, 48943, 49081, 49182, 49381, 49409, 49458, 49461, 49476, 49496, 49569, 49627, 49693, 49757, 49792, 49801, 49944, 50042, 50045, 50054, 50114, 50206, 50812, 50952)
    def _entry(self,entry):
        if entry==0xA00C:return self.postbattle_successor_entry()
        elif entry==0xA1C2:return self.draw_current_city_focus()
        elif entry==0xA1EB:return self.find_officer_city()
        elif entry==0xAD81:return self.postbattle_successor_tick()
        elif entry==0xAD84:return self.dispatch_postbattle_phase()
        elif entry==0xAD95:return self.prepare_postbattle_city()
        elif entry==0xADAA:return self.check_defeated_ruler()
        elif entry==0xAE0D:return self.check_winning_ruler()
        elif entry==0xAE51:return self.restore_city_or_ai_turn()
        elif entry==0xBE01:return self.player_succession_tick()
        elif entry==0xBE04:return self.dispatch_player_succession()
        elif entry==0xBE17:return self.announce_player_leader_death()
        elif entry==0xBE2E:return self.check_player_candidate_cities()
        elif entry==0xBE83:return self.choose_player_candidate_city()
        elif entry==0xBED1:return self.choose_player_candidate_officer()
        elif entry==0xBF2F:return self.confirm_player_successor()
        elif entry==0xBFB9:return self.classify_player_successor_family()
        elif entry==0xC01E:return self.adjust_player_followers()
        elif entry==0xC0E5:return self.await_deserter_message()
        elif entry==0xC101:return self.promote_successor_roster_head()
        elif entry==0xC132:return self.computer_succession_tick()
        elif entry==0xC135:return self.dispatch_computer_succession()
        elif entry==0xC144:return self.announce_computer_leader_death()
        elif entry==0xC158:return self.choose_family_successor()
        elif entry==0xC1A1:return self.find_family_candidate_city()
        elif entry==0xC1DB:return self.choose_highest_morality_successor()
        elif entry==0xC21D:return self.consider_city_candidates()
        elif entry==0xC25D:return self.install_computer_successor()
        elif entry==0xC280:return self.wait_computer_successor_notice()
        elif entry==0xC289:return self.adjust_computer_followers()
        elif entry==0xC318:return self.remove_low_loyalty_follower()
        elif entry==0xC37A:return self.retirement_tick()
        elif entry==0xC37D:return self.dispatch_retirement()
        elif entry==0xC386:return self.commit_leader_absence()
        elif entry==0xC3C2:return self.await_player_gameover()
        elif entry==0xC41E:return self.wait_computer_retirement_notice()
        elif entry==0xC67C:return self.navigate_city_cursor()
        elif entry==0xC708:return self.city_at_cursor()
        raise ValueError("Outside original named postbattle body")

    def postbattle_successor_entry(self):
        """$A00C: postbattle successor entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA00C)
        return (yield from self.postbattle_successor_tick())

    def draw_current_city_focus(self):
        """$A1C2: draw current city focus; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA1C2)
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        yield from self._checkpoint(0xA1C7)
        if not r.p&Z:
            yield from self._checkpoint(0xA1E5)
            self._rts();return
        else:
            self._a(0xD8)
            m[0x000A]=r.a
            self._a(0xA0)
            m[0x000C]=r.a
            self._a(0xE6)
            m[0x0000]=r.a
            self._a(0xA1)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            yield from self._checkpoint(0xA1E2)
            yield from self._external(0xA1E2,0xF1AD,None,"tail")
            return

    def find_officer_city(self):
        """$A1EB: find officer city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA1EB)
        self._x(0x00)
        while True:  # natural loop $A1ED
            try:
                self._a(r.x)
                yield from self._external(0xA1EE,0xF2AF,0xA1F1,"call",None)
                if r.pc!=0xA1F1:return  # preserve nonlocal stack return
                self._y(0x11)
                while True:  # natural loop $A1F3
                    try:
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x000A])
                        yield from self._checkpoint(0xA1F8)
                        if not r.p&Z:
                            self._y(r.y+1)
                            self._compare(r.y,0x1B)
                            yield from self._checkpoint(0xA1FF)
                            if not r.p&C:
                                continue
                            else:
                                self._x(r.x+1)
                                self._compare(r.x,0x1E)
                                yield from self._checkpoint(0xA204)
                                if not r.p&C:
                                    raise _ContinueLoop_A1ED
                                else:
                                    self._a(0x00)
                                    yield from self._checkpoint(0xA208)
                                    self._rts();return
                        else:
                            self._a(r.x)
                            yield from self._checkpoint(0xA1FB)
                            self._rts();return
                    except _ContinueLoop_A1F3:
                        continue
            except _ContinueLoop_A1ED:
                continue

    def postbattle_successor_tick(self):
        """$AD81: postbattle successor tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD81)
        self._a(m[POSTBATTLE_PHASE])
        return (yield from self.dispatch_postbattle_phase())

    def dispatch_postbattle_phase(self):
        """$AD84: dispatch postbattle phase; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD84)
        index=self._dispatch(0xAD84,(44437, 44458, 44557, 44625, 48641, 49458, 50042))
        return (yield from (self.prepare_postbattle_city,self.check_defeated_ruler,self.check_winning_ruler,self.restore_city_or_ai_turn,self.player_succession_tick,self.computer_succession_tick,self.retirement_tick,)[index]())

    def prepare_postbattle_city(self):
        """$AD95: prepare postbattle city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD95)
        self._a(0x00)
        m[0x04E4]=r.a
        self._a(0xF0)
        m[0x6F41]=r.a
        self._y(0x3D)
        yield from self._external(0xADA1,0xEE07,0xADA6,"far_call",40990)
        if r.pc!=0xADA6:return  # preserve nonlocal stack return
        m[POSTBATTLE_PHASE]=self._nz(m[POSTBATTLE_PHASE]+1)
        yield from self._checkpoint(0xADA9)
        self._rts();return

    def check_defeated_ruler(self):
        """$ADAA: check defeated ruler; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADAA)
        self._a(m[PPU_JOBS])
        yield from self._checkpoint(0xADAD)
        if r.p&Z:
            self._a(m[0x0507])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[SUCCESSOR_CITY]=r.a
            self._a(m[0x0507])
            self._a(r.a & 0x0F)
            m[AFFECTED_RULER]=r.a
            yield from self._external(0xADC2,0xF368,0xADC5,"call",None)
            if r.pc!=0xADC5:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[OLD_LEADER]=r.a
            yield from self._external(0xADCC,0xF2D7,0xADCF,"call",None)
            if r.pc!=0xADCF:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            yield from self._checkpoint(0xADD7)
            if r.p&Z:
                self._a(0x02)
                m[RETURN_PHASE]=r.a
                self._a(0x06)
                m[NO_SUCCESSOR_PHASE]=r.a
                self._a(0x0D)
                m[RETURN_MAIN]=r.a
                self._a(0x03)
                m[RETURN_MAIN_PHASE]=r.a
                self._a(0x04)
                m[POSTBATTLE_PHASE]=r.a
                self._a(0x00)
                m[SUCCESSION_PHASE]=r.a
                self._a(m[AFFECTED_RULER])
                yield from self._external(0xADFE,0xF368,0xAE01,"call",None)
                if r.pc!=0xAE01:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                yield from self._checkpoint(0xAE07)
                if r.p&Z:
                    m[POSTBATTLE_PHASE]=self._nz(m[POSTBATTLE_PHASE]+1)
                    yield from self._checkpoint(0xADDC)
                    self._rts();return
                else:
                    m[0x6F44]=r.a
                    yield from self._checkpoint(0xAE0C)
                    self._rts();return
            else:
                m[POSTBATTLE_PHASE]=self._nz(m[POSTBATTLE_PHASE]+1)
                yield from self._checkpoint(0xADDC)
                self._rts();return
        else:
            yield from self._checkpoint(0xADAF)
            self._rts();return

    def check_winning_ruler(self):
        """$AE0D: check winning ruler; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE0D)
        self._a(m[0x0507])
        self._a(r.a & 0x0F)
        m[SUCCESSOR_CITY]=r.a
        self._a(m[0x0507])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[AFFECTED_RULER]=r.a
        yield from self._external(0xAE1F,0xF368,0xAE22,"call",None)
        if r.pc!=0xAE22:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[OLD_LEADER]=r.a
        yield from self._external(0xAE29,0xF2D7,0xAE2C,"call",None)
        if r.pc!=0xAE2C:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x03)
        self._compare(r.a,0x03)
        yield from self._checkpoint(0xAE34)
        if not r.p&Z:
            m[POSTBATTLE_PHASE]=self._nz(m[POSTBATTLE_PHASE]+1)
            yield from self._checkpoint(0xAE50)
            self._rts();return
        else:
            self._a(0x03)
            m[RETURN_PHASE]=r.a
            self._a(0x06)
            m[NO_SUCCESSOR_PHASE]=r.a
            self._a(0x0B)
            m[RETURN_MAIN]=r.a
            self._a(0x00)
            m[RETURN_MAIN_PHASE]=r.a
            self._a(0x04)
            m[POSTBATTLE_PHASE]=r.a
            self._a(0x00)
            m[SUCCESSION_PHASE]=r.a
            self._a(m[AFFECTED_RULER])
            yield from self._external(0xADFE,0xF368,0xAE01,"call",None)
            if r.pc!=0xAE01:return  # preserve nonlocal stack return
            self._y(0x03)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0x03)
            yield from self._checkpoint(0xAE07)
            if r.p&Z:
                m[POSTBATTLE_PHASE]=self._nz(m[POSTBATTLE_PHASE]+1)
                yield from self._checkpoint(0xADDC)
                self._rts();return
            else:
                m[0x6F44]=r.a
                yield from self._checkpoint(0xAE0C)
                self._rts();return

    def restore_city_or_ai_turn(self):
        """$AE51: restore city or ai turn; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE51)
        self._a(0x00)
        m[RETURN_PHASE]=r.a
        m[NO_SUCCESSOR_PHASE]=r.a
        self._y(0x03)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        self._compare(r.a,0x03)
        yield from self._checkpoint(0xAE5F)
        if not r.p&Z:
            m[0x6F44]=r.a
            self._y(0x00)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            m[0x000A]=r.a
            if not (yield from self._local_call(self.find_officer_city,0xAE95,0xAE98)):return
            self._y(0x01)
            m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
            self._y(0x01)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            self._y(r.a)
            self._a(m[(0xC737+r.y)&65535])
            m[0x6F3F]=r.a
            self._a(m[(0xC755+r.y)&65535])
            self._flag(C,False)
            self._add(0x01)
            m[0x6F41]=r.a
            self._y(0x3D)
            yield from self._external(0xAEB2,0xEE07,0xAEB7,"far_call",40990)
            if r.pc!=0xAEB7:return  # preserve nonlocal stack return
            self._a(0x00)
            m[CITY_MAIN]=r.a
            m[POSTBATTLE_PHASE]=r.a
            yield from self._checkpoint(0xAEBF)
            self._rts();return
        else:
            self._a(0xBB)
            yield from self._external(0xAE63,0xF28B,0xAE66,"call",None)
            if r.pc!=0xAE66:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            m[0x042C]=r.a
            self._a(0x09)
            m[CITY_MAIN]=r.a
            self._a(0x01)
            m[POSTBATTLE_PHASE]=r.a
            self._a(0x00)
            m[SUCCESSOR_CITY]=r.a
            self._a(0x00)
            m[0x6F8B]=r.a
            m[0x6F5B]=r.a
            m[0x6F5C]=r.a
            m[0x6F62]=r.a
            yield from self._checkpoint(0xAE8A)
            self._rts();return

    def player_succession_tick(self):
        """$BE01: player succession tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBE01)
        self._a(m[SUCCESSION_PHASE])
        return (yield from self.dispatch_player_succession())

    def dispatch_player_succession(self):
        """$BE04: dispatch player succession; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBE04)
        index=self._dispatch(0xBE04,(48663, 48686, 48771, 48849, 48943, 49081, 49182, 49381))
        return (yield from (self.announce_player_leader_death,self.check_player_candidate_cities,self.choose_player_candidate_city,self.choose_player_candidate_officer,self.confirm_player_successor,self.classify_player_successor_family,self.adjust_player_followers,self.await_deserter_message,)[index]())

    def announce_player_leader_death(self):
        """$BE17: announce player leader death; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBE17)
        self._a(m[OLD_LEADER])
        m[0x042C]=r.a
        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
        self._a(0xC1)
        yield from self._external(0xBE22,0xF28B,0xBE25,"call",None)
        if r.pc!=0xBE25:return  # preserve nonlocal stack return
        yield from self._external(0xBE25,0xE57F,0xBE28,"call",None)
        if r.pc!=0xBE28:return  # preserve nonlocal stack return
        self._a(0x08)
        yield from self._external(0xBE2A,0xE683,0xBE2D,"call",None)
        if r.pc!=0xBE2D:return  # preserve nonlocal stack return
        yield from self._checkpoint(0xBE2D)
        self._rts();return

    def check_player_candidate_cities(self):
        """$BE2E: check player candidate cities; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBE2E)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xBE33)
        if not r.p&Z:
            yield from self._checkpoint(0xBE82)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            yield from self._checkpoint(0xBE3A)
            if not r.p&Z:
                yield from self._checkpoint(0xBE82)
                self._rts();return
            else:
                if not (yield from self._local_call(self.draw_current_city_focus,0xBE3C,0xBE3F)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                yield from self._checkpoint(0xBE44)
                if r.p&Z:
                    yield from self._checkpoint(0xBE82)
                    self._rts();return
                else:
                    self._x(0x00)
                    while True:  # natural loop $BE48
                        try:
                            self._a(r.x)
                            yield from self._external(0xBE49,0xF2AF,0xBE4C,"call",None)
                            if r.pc!=0xBE4C:return  # preserve nonlocal stack return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._a(r.a & 0x07)
                            self._compare(r.a,m[AFFECTED_RULER])
                            yield from self._checkpoint(0xBE55)
                            if not r.p&Z:
                                self._x(r.x+1)
                                self._compare(r.x,0x1E)
                                yield from self._checkpoint(0xBE62)
                                if not r.p&C:
                                    continue
                                else:
                                    self._a(m[NO_SUCCESSOR_PHASE])
                                    m[POSTBATTLE_PHASE]=r.a
                                    self._a(0x00)
                                    m[SUCCESSION_PHASE]=r.a
                                    yield from self._checkpoint(0xBE6F)
                                    self._rts();return
                            else:
                                self._y(0x11)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                yield from self._checkpoint(0xBE5D)
                                if not r.p&Z:
                                    m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                                    self._a(0x80)
                                    m[0x6F3F]=r.a
                                    self._a(0x41)
                                    m[0x6F41]=r.a
                                    self._a(0xD0)
                                    yield from self._checkpoint(0xBE7F)
                                    yield from self._external(0xBE7F,0xF28B,None,"tail")
                                    return
                                else:
                                    self._x(r.x+1)
                                    self._compare(r.x,0x1E)
                                    yield from self._checkpoint(0xBE62)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._a(m[NO_SUCCESSOR_PHASE])
                                        m[POSTBATTLE_PHASE]=r.a
                                        self._a(0x00)
                                        m[SUCCESSION_PHASE]=r.a
                                        yield from self._checkpoint(0xBE6F)
                                        self._rts();return
                        except _ContinueLoop_BE48:
                            continue

    def choose_player_candidate_city(self):
        """$BE83: choose player candidate city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBE83)
        if not (yield from self._local_call(self.navigate_city_cursor,0xBE83,0xBE86)):return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xBE8B)
        if not r.p&Z:
            yield from self._checkpoint(0xBEC6)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            yield from self._checkpoint(0xBE92)
            if not r.p&Z:
                yield from self._checkpoint(0xBEC6)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                yield from self._checkpoint(0xBE99)
                if r.p&Z:
                    yield from self._checkpoint(0xBEC6)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_at_cursor,0xBE9B,0xBE9E)):return
                    self._compare(r.y,0xFF)
                    yield from self._checkpoint(0xBEA0)
                    if r.p&Z:
                        self._a(0x21)
                        yield from self._checkpoint(0xBEC9)
                        yield from self._external(0xBEC9,0xF26D,None,"tail")
                        return
                    else:
                        m[SUCCESSOR_CITY]=r.y
                        self._a(r.y)
                        yield from self._external(0xBEA6,0xF2AF,0xBEA9,"call",None)
                        if r.pc!=0xBEA9:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._a(r.a & 0x07)
                        self._compare(r.a,m[AFFECTED_RULER])
                        yield from self._checkpoint(0xBEB2)
                        if not r.p&Z:
                            self._a(0x22)
                            yield from self._checkpoint(0xBECE)
                            yield from self._external(0xBECE,0xF26D,None,"tail")
                            return
                        else:
                            m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                            self._a(0x82)
                            m[0x0478]=r.a
                            self._a(0x0F)
                            m[0x047C]=r.a
                            self._a(0xD1)
                            yield from self._checkpoint(0xBEC3)
                            yield from self._external(0xBEC3,0xF26D,None,"tail")
                            return

    def choose_player_candidate_officer(self):
        """$BED1: choose player candidate officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBED1)
        self._a(m[0x0478])
        yield from self._checkpoint(0xBED4)
        if not r.p&Z:
            yield from self._checkpoint(0xBEFC)
            self._rts();return
        else:
            self._a(m[SUCCESSION_PHASE])
            self._push(r.a)
            self._a(m[SUCCESSOR_CITY])
            m[SUCCESSION_PHASE]=r.a
            self._y(0x3B)
            yield from self._external(0xBEE2,0xEE07,0xBEE7,"far_call",40966)
            if r.pc!=0xBEE7:return  # preserve nonlocal stack return
            self._a(self._pop())
            m[SUCCESSION_PHASE]=r.a
            self._a(m[0x047C])
            yield from self._checkpoint(0xBEEE)
            if not r.p&N:
                yield from self._checkpoint(0xBEFC)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                yield from self._checkpoint(0xBEF2)
                if not r.p&Z:
                    self._a(0x00)
                    m[0x008F]=r.a
                    self._a(0x03)
                    m[0x0061]=r.a
                    self._a(0x00)
                    m[0x00B2]=r.a
                    self._a(0x05)
                    m[0x00B3]=r.a
                    self._a(0x09)
                    m[0x00B4]=r.a
                    m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                    self._a(m[0x0481])
                    m[0x042C]=r.a
                    m[SUCCESSOR]=r.a
                    self._a(0x00)
                    m[0x0424]=r.a
                    m[0x0425]=r.a
                    self._a(0xD2)
                    yield from self._checkpoint(0xBF2C)
                    yield from self._external(0xBF2C,0xF28B,None,"tail")
                    return
                else:
                    m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]-1)
                    self._a(0xD0)
                    yield from self._checkpoint(0xBEF9)
                    yield from self._external(0xBEF9,0xF26D,None,"tail")
                    return

    def confirm_player_successor(self):
        """$BF2F: confirm player successor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBF2F)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xBF34)
        if not r.p&Z:
            yield from self._checkpoint(0xBF84)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            yield from self._checkpoint(0xBF3B)
            if not r.p&Z:
                yield from self._checkpoint(0xBF84)
                self._rts();return
            else:
                self._a(0xAC)
                m[0x0010]=r.a
                self._a(0xBF)
                m[0x0011]=r.a
                self._a(0x00)
                m[0x0012]=r.a
                yield from self._external(0xBF4C,0xED1E,0xBF4F,"call",None)
                if r.pc!=0xBF4F:return  # preserve nonlocal stack return
                self._a(0xB0)
                m[0x0010]=r.a
                self._a(0xBF)
                m[0x0011]=r.a
                self._a(0xB4)
                m[0x0000]=r.a
                self._a(0xBF)
                m[0x0001]=r.a
                self._a(m[0x0012])
                yield from self._external(0xBF66,0xEDF5,0xBF69,"call",None)
                if r.pc!=0xBF69:return  # preserve nonlocal stack return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                yield from self._checkpoint(0xBF6D)
                if r.p&C:
                    self._a(m[0x0012])
                    yield from self._checkpoint(0xBF88)
                    if not r.p&Z:
                        self._a(0x82)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]-1)
                        self._a(0xD1)
                        yield from self._external(0xBF81,0xF26D,0xBF84,"call",None)
                        if r.pc!=0xBF84:return  # preserve nonlocal stack return
                        yield from self._checkpoint(0xBF84)
                        self._rts();return
                    else:
                        self._a(m[AFFECTED_RULER])
                        yield from self._external(0xBF8D,0xF368,0xBF90,"call",None)
                        if r.pc!=0xBF90:return  # preserve nonlocal stack return
                        self._a(m[SUCCESSOR])
                        m[0x042C]=r.a
                        self._y(0x00)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(m[SUCCESSOR_CITY])
                        self._y(0x01)
                        m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
                        if not (yield from self._local_call(self.promote_successor_roster_head,0xBFA1,0xBFA4)):return
                        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                        self._a(0xD3)
                        yield from self._checkpoint(0xBFA9)
                        yield from self._external(0xBFA9,0xF28B,None,"tail")
                        return
                else:
                    r.a=self._shift(r.a,False,rotate=False)
                    yield from self._checkpoint(0xBF70)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x82)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]-1)
                        self._a(0xD1)
                        yield from self._external(0xBF81,0xF26D,0xBF84,"call",None)
                        if r.pc!=0xBF84:return  # preserve nonlocal stack return
                        pass
                    yield from self._checkpoint(0xBF84)
                    self._rts();return

    def classify_player_successor_family(self):
        """$BFB9: classify player successor family; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBFB9)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xBFBE)
        if not r.p&Z:
            yield from self._checkpoint(0xC01D)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            yield from self._checkpoint(0xBFC5)
            if not r.p&Z:
                yield from self._checkpoint(0xC01D)
                self._rts();return
            else:
                if not (yield from self._local_call(self.draw_current_city_focus,0xBFC7,0xBFCA)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                yield from self._checkpoint(0xBFCF)
                if r.p&Z:
                    yield from self._checkpoint(0xC01D)
                    self._rts();return
                else:
                    self._a(m[AFFECTED_RULER])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._y(r.a)
                    self._flag(C,False)
                    self._add(0x08)
                    m[0x0010]=r.a
                    while True:  # natural loop $BFDE
                        try:
                            self._a(m[(0xC342+r.y)&65535])
                            self._compare(r.a,0xFF)
                            yield from self._checkpoint(0xBFE3)
                            if not r.p&Z:
                                self._compare(r.a,m[SUCCESSOR])
                                yield from self._checkpoint(0xBFF6)
                                if r.p&Z:
                                    self._a(m[SUCCESSOR])
                                    yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                    if r.pc!=0xC004:return  # preserve nonlocal stack return
                                    self._y(0x03)
                                    self._a(0x64)
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    self._a(m[RETURN_PHASE])
                                    m[POSTBATTLE_PHASE]=r.a
                                    self._a(0x00)
                                    m[SUCCESSION_PHASE]=r.a
                                    yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                    if r.pc!=0xC018:return  # preserve nonlocal stack return
                                    self._a(0x81)
                                    yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                    if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                    yield from self._checkpoint(0xC01D)
                                    self._rts();return
                                else:
                                    self._y(r.y+1)
                                    self._compare(r.y,m[0x0010])
                                    yield from self._checkpoint(0xBFFC)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._a(m[SUCCESSOR])
                                        yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                        if r.pc!=0xC004:return  # preserve nonlocal stack return
                                        self._y(0x03)
                                        self._a(0x64)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._a(m[RETURN_PHASE])
                                        m[POSTBATTLE_PHASE]=r.a
                                        self._a(0x00)
                                        m[SUCCESSION_PHASE]=r.a
                                        yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                        if r.pc!=0xC018:return  # preserve nonlocal stack return
                                        self._a(0x81)
                                        yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                        if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                        yield from self._checkpoint(0xC01D)
                                        self._rts();return
                            else:
                                self._a(0x00)
                                m[FOLLOWER_CITY]=r.a
                                self._a(0x11)
                                m[FOLLOWER_ROSTER]=r.a
                                m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                                yield from self._checkpoint(0xBFF2)
                                self._rts();return
                        except _ContinueLoop_BFDE:
                            continue

    def adjust_player_followers(self):
        """$C01E: adjust player followers; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $C01E
            try:
                yield from self._checkpoint(0xC01E)
                self._a(m[FOLLOWER_CITY])
                yield from self._external(0xC021,0xF2AF,0xC024,"call",None)
                if r.pc!=0xC024:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[AFFECTED_RULER])
                yield from self._checkpoint(0xC02D)
                if not r.p&Z:
                    m[FOLLOWER_CITY]=self._nz(m[FOLLOWER_CITY]+1)
                    self._a(0x11)
                    m[FOLLOWER_ROSTER]=r.a
                    self._a(m[FOLLOWER_CITY])
                    self._compare(r.a,0x1E)
                    yield from self._checkpoint(0xC08C)
                    if not r.p&C:
                        continue
                    else:
                        self._a(m[SUCCESSOR])
                        yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                        if r.pc!=0xC004:return  # preserve nonlocal stack return
                        self._y(0x03)
                        self._a(0x64)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(m[RETURN_PHASE])
                        m[POSTBATTLE_PHASE]=r.a
                        self._a(0x00)
                        m[SUCCESSION_PHASE]=r.a
                        yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                        if r.pc!=0xC018:return  # preserve nonlocal stack return
                        self._a(0x81)
                        yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                        if r.pc!=0xC01D:return  # preserve nonlocal stack return
                        yield from self._checkpoint(0xC01D)
                        self._rts();return
                else:
                    self._a(m[0x0000])
                    m[0x0010]=r.a
                    self._a(m[0x0001])
                    m[0x0011]=r.a
                    self._y(m[FOLLOWER_ROSTER])
                    while True:  # natural loop $C03E
                        try:
                            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            yield from self._checkpoint(0xC042)
                            if r.p&Z:
                                m[FOLLOWER_CITY]=self._nz(m[FOLLOWER_CITY]+1)
                                self._a(0x11)
                                m[FOLLOWER_ROSTER]=r.a
                                self._a(m[FOLLOWER_CITY])
                                self._compare(r.a,0x1E)
                                yield from self._checkpoint(0xC08C)
                                if not r.p&C:
                                    raise _ContinueLoop_C01E
                                else:
                                    self._a(m[SUCCESSOR])
                                    yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                    if r.pc!=0xC004:return  # preserve nonlocal stack return
                                    self._y(0x03)
                                    self._a(0x64)
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    self._a(m[RETURN_PHASE])
                                    m[POSTBATTLE_PHASE]=r.a
                                    self._a(0x00)
                                    m[SUCCESSION_PHASE]=r.a
                                    yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                    if r.pc!=0xC018:return  # preserve nonlocal stack return
                                    self._a(0x81)
                                    yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                    if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                    yield from self._checkpoint(0xC01D)
                                    self._rts();return
                            else:
                                m[0x0031]=r.a
                                self._a(m[SUCCESSOR])
                                m[0x0030]=r.a
                                self._a(m[AFFECTED_RULER])
                                m[0x0032]=r.a
                                self._a(m[OLD_LEADER])
                                m[0x0033]=r.a
                                self._y(0x2A)
                                yield from self._external(0xC05B,0xEE07,0xC060,"far_call",40969)
                                if r.pc!=0xC060:return  # preserve nonlocal stack return
                                self._a(m[0x0031])
                                yield from self._external(0xC063,0xF2D7,0xC066,"call",None)
                                if r.pc!=0xC066:return  # preserve nonlocal stack return
                                self._y(0x03)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._compare(r.a,0x1F)
                                yield from self._checkpoint(0xC06C)
                                if r.p&C:
                                    m[FOLLOWER_ROSTER]=self._nz(m[FOLLOWER_ROSTER]+1)
                                    self._y(m[FOLLOWER_ROSTER])
                                    self._compare(r.y,0x1B)
                                    yield from self._checkpoint(0xC07D)
                                    if not r.p&C:
                                        continue
                                    else:
                                        m[FOLLOWER_CITY]=self._nz(m[FOLLOWER_CITY]+1)
                                        self._a(0x11)
                                        m[FOLLOWER_ROSTER]=r.a
                                        self._a(m[FOLLOWER_CITY])
                                        self._compare(r.a,0x1E)
                                        yield from self._checkpoint(0xC08C)
                                        if not r.p&C:
                                            raise _ContinueLoop_C01E
                                        else:
                                            self._a(m[SUCCESSOR])
                                            yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                            if r.pc!=0xC004:return  # preserve nonlocal stack return
                                            self._y(0x03)
                                            self._a(0x64)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._a(m[RETURN_PHASE])
                                            m[POSTBATTLE_PHASE]=r.a
                                            self._a(0x00)
                                            m[SUCCESSION_PHASE]=r.a
                                            yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                            if r.pc!=0xC018:return  # preserve nonlocal stack return
                                            self._a(0x81)
                                            yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                            if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                            yield from self._checkpoint(0xC01D)
                                            self._rts();return
                                else:
                                    yield from self._external(0xC06E,0xE843,0xC071,"call",None)
                                    if r.pc!=0xC071:return  # preserve nonlocal stack return
                                    self._compare(r.a,0x14)
                                    yield from self._checkpoint(0xC073)
                                    if not r.p&C:
                                        self._a(m[0x0031])
                                        self._compare(r.a,m[SUCCESSOR])
                                        yield from self._checkpoint(0xC097)
                                        if r.p&Z:
                                            m[FOLLOWER_ROSTER]=self._nz(m[FOLLOWER_ROSTER]+1)
                                            self._y(m[FOLLOWER_ROSTER])
                                            self._compare(r.y,0x1B)
                                            yield from self._checkpoint(0xC07D)
                                            if not r.p&C:
                                                continue
                                            else:
                                                m[FOLLOWER_CITY]=self._nz(m[FOLLOWER_CITY]+1)
                                                self._a(0x11)
                                                m[FOLLOWER_ROSTER]=r.a
                                                self._a(m[FOLLOWER_CITY])
                                                self._compare(r.a,0x1E)
                                                yield from self._checkpoint(0xC08C)
                                                if not r.p&C:
                                                    raise _ContinueLoop_C01E
                                                else:
                                                    self._a(m[SUCCESSOR])
                                                    yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                                    if r.pc!=0xC004:return  # preserve nonlocal stack return
                                                    self._y(0x03)
                                                    self._a(0x64)
                                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                                    self._a(m[RETURN_PHASE])
                                                    m[POSTBATTLE_PHASE]=r.a
                                                    self._a(0x00)
                                                    m[SUCCESSION_PHASE]=r.a
                                                    yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                                    if r.pc!=0xC018:return  # preserve nonlocal stack return
                                                    self._a(0x81)
                                                    yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                                    if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                                    yield from self._checkpoint(0xC01D)
                                                    self._rts();return
                                        else:
                                            self._y(0x0B)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._a(r.a & 0xFC)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(0x05)
                                            self._a(m[FOLLOWER_CITY])
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(m[FOLLOWER_ROSTER])
                                            while True:  # natural loop $C0AB
                                                try:
                                                    self._compare(r.y,0x1A)
                                                    yield from self._checkpoint(0xC0AD)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                                                        self._y(r.y-1)
                                                        m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        continue
                                                    self._a(0xFF)
                                                    m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                                                    self._x(0x00)
                                                    self._y(0x11)
                                                    while True:  # natural loop $C0C1
                                                        try:
                                                            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                                                            self._compare(r.a,0xFF)
                                                            yield from self._checkpoint(0xC0C5)
                                                            if r.p&Z:
                                                                pass
                                                            else:
                                                                self._x(r.x+1)
                                                                pass
                                                            self._y(r.y+1)
                                                            self._compare(r.y,0x1B)
                                                            yield from self._checkpoint(0xC0CB)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                pass
                                                            self._compare(r.x,0x00)
                                                            yield from self._checkpoint(0xC0CF)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                self._y(0x00)
                                                                self._a(0x07)
                                                                m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                                                                pass
                                                            m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                                                            self._a(m[0x0031])
                                                            m[0x042C]=r.a
                                                            self._a(0xD4)
                                                            yield from self._checkpoint(0xC0E2)
                                                            yield from self._external(0xC0E2,0xF28B,None,"tail")
                                                            return
                                                        except _ContinueLoop_C0C1:
                                                            continue
                                                except _ContinueLoop_C0AB:
                                                    continue
                                    else:
                                        m[FOLLOWER_ROSTER]=self._nz(m[FOLLOWER_ROSTER]+1)
                                        self._y(m[FOLLOWER_ROSTER])
                                        self._compare(r.y,0x1B)
                                        yield from self._checkpoint(0xC07D)
                                        if not r.p&C:
                                            continue
                                        else:
                                            m[FOLLOWER_CITY]=self._nz(m[FOLLOWER_CITY]+1)
                                            self._a(0x11)
                                            m[FOLLOWER_ROSTER]=r.a
                                            self._a(m[FOLLOWER_CITY])
                                            self._compare(r.a,0x1E)
                                            yield from self._checkpoint(0xC08C)
                                            if not r.p&C:
                                                raise _ContinueLoop_C01E
                                            else:
                                                self._a(m[SUCCESSOR])
                                                yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                                if r.pc!=0xC004:return  # preserve nonlocal stack return
                                                self._y(0x03)
                                                self._a(0x64)
                                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                                self._a(m[RETURN_PHASE])
                                                m[POSTBATTLE_PHASE]=r.a
                                                self._a(0x00)
                                                m[SUCCESSION_PHASE]=r.a
                                                yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                                if r.pc!=0xC018:return  # preserve nonlocal stack return
                                                self._a(0x81)
                                                yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                                if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                                yield from self._checkpoint(0xC01D)
                                                self._rts();return
                        except _ContinueLoop_C03E:
                            continue
            except _ContinueLoop_C01E:
                continue

    def await_deserter_message(self):
        """$C0E5: await deserter message; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC0E5)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xC0EA)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            yield from self._checkpoint(0xC0F1)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.draw_current_city_focus,0xC0F3,0xC0F6)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                yield from self._checkpoint(0xC0FB)
                if r.p&Z:
                    pass
                else:
                    m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]-1)
                    pass
                pass
            pass
        yield from self._checkpoint(0xC100)
        self._rts();return

    def promote_successor_roster_head(self):
        """C101..C131: swap chosen ID with city roster[0], no location write.

        Search covers all ten slots, not a compact prefix. If ID is absent,
        leave the roster untouched. The actual PHA/PLA leaves its stack byte.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC101);self._a(m[SUCCESSOR_CITY])
        yield from self._external(0xC104,0xF2AF,0xC107,'call')
        if r.pc!=0xC107:return
        self._a(m[SUCCESSOR]);m[2]=r.a;self._y(17)
        while True:
            yield from self._checkpoint(0xC10F);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[2])
            if r.p&Z:
                self._a(r.y);self._push(r.a);self._y(17);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[3]=r.a
                self._a(m[2]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
                self._a(self._pop());self._y(r.a);self._a(m[3]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;self._rts();return
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        self._rts();return

    def computer_succession_tick(self):
        """$C132: computer succession tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC132)
        self._a(m[SUCCESSION_PHASE])
        return (yield from self.dispatch_computer_succession())

    def dispatch_computer_succession(self):
        """$C135: dispatch computer succession; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC135)
        index=self._dispatch(0xC135,(49476, 49496, 49627, 49757, 49792, 49801))
        return (yield from (self.announce_computer_leader_death,self.choose_family_successor,self.choose_highest_morality_successor,self.install_computer_successor,self.wait_computer_successor_notice,self.adjust_computer_followers,)[index]())

    def announce_computer_leader_death(self):
        """$C144: announce computer leader death; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC144)
        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
        self._a(0x00)
        m[NOTICE_TIMER]=r.a
        self._a(m[OLD_LEADER])
        m[0x042C]=r.a
        self._a(0xC1)
        yield from self._external(0xC154,0xF28B,0xC157,"call",None)
        if r.pc!=0xC157:return  # preserve nonlocal stack return
        yield from self._checkpoint(0xC157)
        self._rts();return

    def choose_family_successor(self):
        """$C158: choose family successor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC158)
        m[NOTICE_TIMER]=self._nz(m[NOTICE_TIMER]+1)
        yield from self._checkpoint(0xC15B)
        if not r.p&Z:
            yield from self._checkpoint(0xC157)
            self._rts();return
        else:
            self._a(m[AFFECTED_RULER])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0010]=r.a
            self._a(0x42)
            self._flag(C,False)
            self._add(m[0x0010])
            m[0x0010]=r.a
            self._a(0xC3)
            self._add(0x00)
            m[0x0011]=r.a
            self._y(0x00)
            m[0x0012]=r.y
            while True:  # natural loop $C17B
                try:
                    self._y(m[0x0012])
                    self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xC182)
                    if r.p&Z:
                        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
                        yield from self._checkpoint(0xC1A0)
                        self._rts();return
                    else:
                        m[SUCCESSOR]=r.a
                        if not (yield from self._local_call(self.find_family_candidate_city,0xC187,0xC18A)):return
                        yield from self._checkpoint(0xC18A)
                        if r.p&C:
                            self._a(0x00)
                            m[0x0409]=r.a
                            self._a(0x03)
                            m[SUCCESSION_PHASE]=r.a
                            yield from self._checkpoint(0xC19C)
                            self._rts();return
                        else:
                            m[0x0012]=self._nz(m[0x0012]+1)
                            continue
                except _ContinueLoop_C17B:
                    continue

    def find_family_candidate_city(self):
        """C1A1..C1DA: city owner low3 and compact roster prefix only.

        HP, officer status and record byte5 are not candidate predicates.
        Matching the candidate precedes the FF sentinel test. Success returns
        carry set and writes its city040C; failure preserves040C and clears C.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC1A1);self._x(0)
        while True:
            yield from self._checkpoint(0xC1A3);self._a(r.x)
            yield from self._external(0xC1A4,0xF2AF,0xC1A7,'call')
            if r.pc!=0xC1A7:return
            self._y(0);self._a(m[(m[0]|m[1]<<8)]);self._a(r.a&7);self._compare(r.a,m[AFFECTED_RULER])
            if r.p&Z:
                self._y(17);m[4]=r.y
                while True:
                    yield from self._checkpoint(0xC1B7);self._y(m[4]);self._a(m[((m[0]|m[1]<<8)+r.y)&65535])
                    self._compare(r.a,m[SUCCESSOR])
                    if r.p&Z:m[SUCCESSOR_CITY]=r.x;self._flag(C,True);self._rts();return
                    self._compare(r.a,255)
                    if r.p&Z:break
                    m[4]=self._nz(m[4]+1);self._a(m[4]);self._compare(r.a,27)
                    if r.p&C:break
            self._x(r.x+1);self._compare(r.x,30)
            if r.p&C:break
        self._flag(C,False);self._rts();return

    def choose_highest_morality_successor(self):
        """$C1DB: choose highest morality successor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC1DB)
        self._a(0xFF)
        m[0x0010]=r.a
        self._x(0x00)
        m[0x0011]=r.x
        while True:  # natural loop $C1E5
            try:
                self._a(r.x)
                yield from self._external(0xC1E6,0xF2AF,0xC1E9,"call",None)
                if r.pc!=0xC1E9:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[AFFECTED_RULER])
                yield from self._checkpoint(0xC1F2)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.consider_city_candidates,0xC1F4,0xC1F7)):return
                    pass
                self._x(r.x+1)
                self._compare(r.x,0x1E)
                yield from self._checkpoint(0xC1FA)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0010])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xC201)
                if r.p&Z:
                    self._a(m[NO_SUCCESSOR_PHASE])
                    m[POSTBATTLE_PHASE]=r.a
                    self._a(0x00)
                    m[SUCCESSION_PHASE]=r.a
                    yield from self._checkpoint(0xC21C)
                    self._rts();return
                else:
                    m[SUCCESSOR]=r.a
                    self._a(0x80)
                    m[0x0409]=r.a
                    self._a(0x03)
                    m[SUCCESSION_PHASE]=r.a
                    yield from self._checkpoint(0xC210)
                    self._rts();return
            except _ContinueLoop_C1E5:
                continue

    def consider_city_candidates(self):
        """C21D..C25C: choose the last officer tying the highest raw morality.

        The roster stops at its first FF, even if later slots are occupied.
        Reads officer+4 only: no health/status/location/family exclusion here.
        Scratch0010=bestID and0011=bestvalue span the caller's city scan.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC21D)
        self._a(m[0]);m[2]=r.a;self._a(m[1]);m[3]=r.a;self._y(17);m[4]=r.y
        while True:
            yield from self._checkpoint(0xC22E);self._y(m[4]);self._a(m[((m[2]|m[3]<<8)+r.y)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[0x12]=r.a;yield from self._external(0xC23A,0xF2D7,0xC23D,'call')
            if r.pc!=0xC23D:return
            self._y(4);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[0x11])
            if r.p&C:m[0x11]=r.a;self._a(m[0x12]);m[0x10]=r.a;m[SUCCESSOR_CITY]=r.x
            m[4]=self._nz(m[4]+1);self._a(m[4]);self._compare(r.a,27)
            if r.p&C:break
        self._rts();return

    def install_computer_successor(self):
        """$C25D: install computer successor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC25D)
        self._a(m[AFFECTED_RULER])
        yield from self._external(0xC260,0xF368,0xC263,"call",None)
        if r.pc!=0xC263:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[SUCCESSOR])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.promote_successor_roster_head,0xC26A,0xC26D)):return
        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
        self._a(m[SUCCESSOR])
        m[0x042C]=r.a
        self._a(0x00)
        m[NOTICE_TIMER]=r.a
        self._a(0xC2)
        yield from self._checkpoint(0xC27D)
        yield from self._external(0xC27D,0xF28B,None,"tail")
        return

    def wait_computer_successor_notice(self):
        """$C280: wait computer successor notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC280)
        m[NOTICE_TIMER]=self._nz(m[NOTICE_TIMER]+1)
        yield from self._checkpoint(0xC283)
        if not r.p&Z:
            pass
        else:
            m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
            pass
        yield from self._checkpoint(0xC288)
        self._rts();return

    def adjust_computer_followers(self):
        """$C289: adjust computer followers; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC289)
        self._a(m[0x0409])
        yield from self._checkpoint(0xC28C)
        if r.p&N:
            self._a(0x00)
            m[0x0012]=r.a
            while True:  # natural loop $C2AB
                try:
                    self._a(m[0x0012])
                    yield from self._external(0xC2AE,0xF2AF,0xC2B1,"call",None)
                    if r.pc!=0xC2B1:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[AFFECTED_RULER])
                    yield from self._checkpoint(0xC2BA)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0000])
                        m[0x0010]=r.a
                        self._a(m[0x0001])
                        m[0x0011]=r.a
                        self._y(0x11)
                        m[0x0013]=r.y
                        while True:  # natural loop $C2CD
                            try:
                                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                yield from self._checkpoint(0xC2D1)
                                if r.p&Z:
                                    pass
                                else:
                                    m[0x0031]=r.a
                                    self._a(m[SUCCESSOR])
                                    m[0x0030]=r.a
                                    self._a(m[AFFECTED_RULER])
                                    m[0x0032]=r.a
                                    self._a(m[OLD_LEADER])
                                    m[0x0033]=r.a
                                    self._y(0x2A)
                                    yield from self._external(0xC2EA,0xEE07,0xC2EF,"far_call",40969)
                                    if r.pc!=0xC2EF:return  # preserve nonlocal stack return
                                    self._y(0x03)
                                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                    self._compare(r.a,0x1F)
                                    yield from self._checkpoint(0xC2F5)
                                    if r.p&C:
                                        pass
                                    else:
                                        yield from self._external(0xC2F7,0xE843,0xC2FA,"call",None)
                                        if r.pc!=0xC2FA:return  # preserve nonlocal stack return
                                        self._compare(r.a,0x14)
                                        yield from self._checkpoint(0xC2FC)
                                        if r.p&C:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.remove_low_loyalty_follower,0xC2FE,0xC301)):return
                                            pass
                                        pass
                                    m[0x0013]=self._nz(m[0x0013]+1)
                                    self._y(m[0x0013])
                                    self._compare(r.y,0x1B)
                                    yield from self._checkpoint(0xC309)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    pass
                                m[0x0012]=self._nz(m[0x0012]+1)
                                self._a(m[0x0012])
                                self._compare(r.a,0x1E)
                                yield from self._checkpoint(0xC313)
                                if not r.p&C:
                                    raise _ContinueLoop_C2AB
                                else:
                                    pass
                                self._a(m[SUCCESSOR])
                                yield from self._external(0xC291,0xF2D7,0xC294,"call",None)
                                if r.pc!=0xC294:return  # preserve nonlocal stack return
                                self._y(0x03)
                                self._a(0x64)
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._a(m[RETURN_PHASE])
                                m[POSTBATTLE_PHASE]=r.a
                                self._a(0x00)
                                m[SUCCESSION_PHASE]=r.a
                                yield from self._checkpoint(0xC2A5)
                                self._rts();return
                            except _ContinueLoop_C2CD:
                                continue
                    m[0x0012]=self._nz(m[0x0012]+1)
                    self._a(m[0x0012])
                    self._compare(r.a,0x1E)
                    yield from self._checkpoint(0xC313)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(m[SUCCESSOR])
                    yield from self._external(0xC291,0xF2D7,0xC294,"call",None)
                    if r.pc!=0xC294:return  # preserve nonlocal stack return
                    self._y(0x03)
                    self._a(0x64)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(m[RETURN_PHASE])
                    m[POSTBATTLE_PHASE]=r.a
                    self._a(0x00)
                    m[SUCCESSION_PHASE]=r.a
                    yield from self._checkpoint(0xC2A5)
                    self._rts();return
                except _ContinueLoop_C2AB:
                    continue
        else:
            pass
        self._a(m[SUCCESSOR])
        yield from self._external(0xC291,0xF2D7,0xC294,"call",None)
        if r.pc!=0xC294:return  # preserve nonlocal stack return
        self._y(0x03)
        self._a(0x64)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._a(m[RETURN_PHASE])
        m[POSTBATTLE_PHASE]=r.a
        self._a(0x00)
        m[SUCCESSION_PHASE]=r.a
        yield from self._checkpoint(0xC2A5)
        self._rts();return

    def remove_low_loyalty_follower(self):
        """C318..C341: release non-successor and shift the remaining roster.

        AI branch clears condition low2; it does not write record byte5 or
        neutralize an empty city's owner. PlayerC01E has different effects.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC318);self._a(m[0x31]);self._compare(r.a,m[SUCCESSOR])
        if r.p&Z:self._rts();return
        self._y(11);self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535]);self._a(r.a&252);m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        self._y(m[0x13])
        while True:
            yield from self._checkpoint(0xC32C);self._compare(r.y,26)
            if r.p&Z:break
            self._y(r.y+1);self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);self._y(r.y-1);m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a;self._y(r.y+1)
        self._a(255);m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a;m[0x13]=self._nz(m[0x13]-1);self._rts();return

    def retirement_tick(self):
        """$C37A: retirement tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC37A)
        self._a(m[SUCCESSION_PHASE])
        return (yield from self.dispatch_retirement())

    def dispatch_retirement(self):
        """$C37D: dispatch retirement; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC37D)
        index=self._dispatch(0xC37D,(50054, 50114, 50206))
        return (yield from (self.commit_leader_absence,self.await_player_gameover,self.wait_computer_retirement_notice,)[index]())

    def commit_leader_absence(self):
        """$C386: commit leader absence; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC386)
        self._y(m[AFFECTED_RULER])
        self._a(m[(0xC3BB+r.y)&65535])
        m[0x042D]=r.a
        self._a(0xC3)
        yield from self._external(0xC391,0xF28B,0xC394,"call",None)
        if r.pc!=0xC394:return  # preserve nonlocal stack return
        self._a(m[AFFECTED_RULER])
        yield from self._external(0xC397,0xF368,0xC39A,"call",None)
        if r.pc!=0xC39A:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x042C]=r.a
        self._a(0xFF)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x03)
        self._compare(r.a,0x03)
        yield from self._checkpoint(0xC3AD)
        if not r.p&Z:
            pass
        else:
            m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
            self._a(0x00)
            m[NOTICE_TIMER]=r.a
            pass
        m[SUCCESSION_PHASE]=self._nz(m[SUCCESSION_PHASE]+1)
        yield from self._checkpoint(0xC3BA)
        self._rts();return

    def await_player_gameover(self):
        """$C3C2: await player gameover; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC3C2)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xC3C7)
        if not r.p&Z:
            yield from self._checkpoint(0xC3DA)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            yield from self._checkpoint(0xC3CE)
            if not r.p&Z:
                yield from self._checkpoint(0xC3DA)
                self._rts();return
            else:
                if not (yield from self._local_call(self.draw_current_city_focus,0xC3D0,0xC3D3)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                yield from self._checkpoint(0xC3D8)
                if not r.p&Z:
                    self._a(m[SUCCESSOR_CITY])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xC3E0)
                    if r.p&Z:
                        pass
                    else:
                        yield from self._external(0xC3E2,0xF368,0xC3E5,"call",None)
                        if r.pc!=0xC3E5:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        pass
                    m[0x042E]=r.a
                    self._a(m[0x6F00])
                    self._flag(C,False)
                    self._add(0x64)
                    m[0x042F]=r.a
                    self._a(0x00)
                    self._add(0x00)
                    m[0x0430]=r.a
                    self._a(m[0x6F01])
                    self._flag(C,False)
                    self._add(0x01)
                    m[0x0432]=r.a
                    self._a(0x00)
                    m[0x0431]=r.a
                    m[0x0433]=r.a
                    m[0x0434]=r.a
                    self._a(0x0D)
                    m[GLOBAL]=r.a
                    self._a(0x00)
                    m[0x0541]=r.a
                    m[0x04CA]=r.a
                    yield from self._checkpoint(0xC41D)
                    self._rts();return
                else:
                    yield from self._checkpoint(0xC3DA)
                    self._rts();return

    def wait_computer_retirement_notice(self):
        """$C41E: wait computer retirement notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC41E)
        m[NOTICE_TIMER]=self._nz(m[NOTICE_TIMER]+1)
        yield from self._checkpoint(0xC421)
        if not r.p&Z:
            pass
        else:
            self._a(m[RETURN_MAIN])
            m[CITY_MAIN]=r.a
            self._a(m[RETURN_MAIN_PHASE])
            m[POSTBATTLE_PHASE]=r.a
            self._a(0x00)
            m[SUCCESSION_PHASE]=r.a
            pass
        yield from self._checkpoint(0xC434)
        self._rts();return

    def navigate_city_cursor(self):
        """$C67C: navigate city cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC67C)
        self._a(m[0x0318])
        m[0x0000]=r.a
        self._a(m[0x0083])
        self._a(r.a & 0xF0)
        m[0x0318]=r.a
        yield from self._checkpoint(0xC68A)
        if r.p&Z:
            self._a(0x00)
            m[0x0319]=r.a
            yield from self._checkpoint(0xC6AD)
            self._rts();return
        else:
            self._compare(r.a,m[0x0000])
            yield from self._checkpoint(0xC68F)
            if not r.p&Z:
                self._a(0x00)
                m[0x0319]=r.a
                self._a(m[0x0083])
                yield from self._checkpoint(0xC6B6)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F3F])
                    self._compare(r.x,0xF8)
                    yield from self._checkpoint(0xC6BD)
                    if r.p&C:
                        pass
                    else:
                        self._push(r.a)
                        self._a(m[0x6F3F])
                        self._flag(C,False)
                        self._add(0x08)
                        m[0x6F3F]=r.a
                        self._a(self._pop())
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                yield from self._checkpoint(0xC6CB)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F3F])
                    self._compare(r.x,0x10)
                    yield from self._checkpoint(0xC6D2)
                    if not r.p&C:
                        pass
                    else:
                        self._push(r.a)
                        self._a(m[0x6F3F])
                        self._flag(C,True)
                        self._add(0x08,subtract=True)
                        m[0x6F3F]=r.a
                        self._a(self._pop())
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                yield from self._checkpoint(0xC6E0)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F41])
                    self._compare(r.x,0x94)
                    yield from self._checkpoint(0xC6E7)
                    if r.p&C:
                        pass
                    else:
                        self._push(r.a)
                        self._a(m[0x6F41])
                        self._flag(C,False)
                        self._add(0x08)
                        m[0x6F41]=r.a
                        self._a(self._pop())
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                yield from self._checkpoint(0xC6F5)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F41])
                    self._compare(r.x,0x10)
                    yield from self._checkpoint(0xC6FC)
                    if not r.p&C:
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(0x08,subtract=True)
                        m[0x6F41]=r.a
                        pass
                    pass
                yield from self._checkpoint(0xC707)
                self._rts();return
            else:
                m[0x0319]=self._nz(m[0x0319]+1)
                self._a(m[0x0319])
                self._compare(r.a,0x0F)
                yield from self._checkpoint(0xC699)
                if not r.p&C:
                    yield from self._checkpoint(0xC6A7)
                    self._rts();return
                else:
                    self._a(0x0F)
                    m[0x0319]=r.a
                    self._a(m[0x005E])
                    self._a(r.a & 0x03)
                    yield from self._checkpoint(0xC6A5)
                    if r.p&Z:
                        self._a(m[0x0083])
                        yield from self._checkpoint(0xC6B6)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F3F])
                            self._compare(r.x,0xF8)
                            yield from self._checkpoint(0xC6BD)
                            if r.p&C:
                                pass
                            else:
                                self._push(r.a)
                                self._a(m[0x6F3F])
                                self._flag(C,False)
                                self._add(0x08)
                                m[0x6F3F]=r.a
                                self._a(self._pop())
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        yield from self._checkpoint(0xC6CB)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F3F])
                            self._compare(r.x,0x10)
                            yield from self._checkpoint(0xC6D2)
                            if not r.p&C:
                                pass
                            else:
                                self._push(r.a)
                                self._a(m[0x6F3F])
                                self._flag(C,True)
                                self._add(0x08,subtract=True)
                                m[0x6F3F]=r.a
                                self._a(self._pop())
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        yield from self._checkpoint(0xC6E0)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F41])
                            self._compare(r.x,0x94)
                            yield from self._checkpoint(0xC6E7)
                            if r.p&C:
                                pass
                            else:
                                self._push(r.a)
                                self._a(m[0x6F41])
                                self._flag(C,False)
                                self._add(0x08)
                                m[0x6F41]=r.a
                                self._a(self._pop())
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        yield from self._checkpoint(0xC6F5)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F41])
                            self._compare(r.x,0x10)
                            yield from self._checkpoint(0xC6FC)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x6F41])
                                self._flag(C,True)
                                self._add(0x08,subtract=True)
                                m[0x6F41]=r.a
                                pass
                            pass
                        yield from self._checkpoint(0xC707)
                        self._rts();return
                    else:
                        yield from self._checkpoint(0xC6A7)
                        self._rts();return

    def city_at_cursor(self):
        """$C708: city at cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xC708)
        self._a(m[0x6F3F])
        self._compare(r.a,0x20)
        yield from self._checkpoint(0xC70D)
        if r.p&C:
            self._y(0x1E)
            while True:  # natural loop $C71B
                try:
                    self._a(m[0x6F3F])
                    self._flag(C,True)
                    self._add(m[(0xC737+r.y)&65535],subtract=True)
                    self._compare(r.a,0x10)
                    yield from self._checkpoint(0xC724)
                    if r.p&C:
                        self._y(r.y-1)
                        yield from self._checkpoint(0xC732)
                        if not r.p&N:
                            continue
                        else:
                            self._y(0xFF)
                            pass
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(m[(0xC755+r.y)&65535],subtract=True)
                        self._compare(r.a,0x10)
                        yield from self._checkpoint(0xC72F)
                        if not r.p&C:
                            pass
                        else:
                            self._y(r.y-1)
                            yield from self._checkpoint(0xC732)
                            if not r.p&N:
                                continue
                            else:
                                self._y(0xFF)
                                pass
                            pass
                        pass
                    yield from self._checkpoint(0xC736)
                    self._rts();return
                except _ContinueLoop_C71B:
                    continue
        else:
            self._a(m[0x6F41])
            self._compare(r.a,0x20)
            yield from self._checkpoint(0xC714)
            if r.p&C:
                self._y(0x1E)
                while True:  # natural loop $C71B
                    try:
                        self._a(m[0x6F3F])
                        self._flag(C,True)
                        self._add(m[(0xC737+r.y)&65535],subtract=True)
                        self._compare(r.a,0x10)
                        yield from self._checkpoint(0xC724)
                        if r.p&C:
                            self._y(r.y-1)
                            yield from self._checkpoint(0xC732)
                            if not r.p&N:
                                continue
                            else:
                                self._y(0xFF)
                                pass
                            pass
                        else:
                            self._a(m[0x6F41])
                            self._flag(C,True)
                            self._add(m[(0xC755+r.y)&65535],subtract=True)
                            self._compare(r.a,0x10)
                            yield from self._checkpoint(0xC72F)
                            if not r.p&C:
                                pass
                            else:
                                self._y(r.y-1)
                                yield from self._checkpoint(0xC732)
                                if not r.p&N:
                                    continue
                                else:
                                    self._y(0xFF)
                                    pass
                                pass
                            pass
                        yield from self._checkpoint(0xC736)
                        self._rts();return
                    except _ContinueLoop_C71B:
                        continue
            else:
                self._y(0xFF)
                yield from self._checkpoint(0xC718)
                self._rts();return

