"""Readable physical10/11 domestic cooperation controller.

Named original decision stages are directly implemented with Python conditions
and loops. ROM provides immutable tables and mapped data only. No opcodes, IR,
original CPU or simulated UI/IRQ acknowledgement execute in production.
"""
from .global_ui_controller import UIControlBase,UIRegisters,C,Z,I,D,B,U,V,N
from .battle_nmi_services import ServiceWait

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
RULER,AI_REQUEST,AI_PHASE,AI_BUDGET,SELECTED_CITY=0x6F03,0x6F8B,0x6F5B,0x6F5D,0x6F5E
YEAR,MONTH,DIFFICULTY,CITY_WRAP_COUNT=0x6F00,0x6F01,0x6F02,0x6F62
WEIGHT_MILITARY,WEIGHT_ASSIGNMENT,WEIGHT_DEVELOPMENT=0x6F5F,0x6F60,0x6F61
RANDOM_PRIMARY,RANDOM_SECONDARY,RANDOM_TERTIARY=0x52,0x54,0x55

class _ContinueLoop_A0E3(Exception):pass
class _ContinueLoop_A0EF(Exception):pass
class _ContinueLoop_A25A(Exception):pass
class _ContinueLoop_A272(Exception):pass
class _ContinueLoop_A31A(Exception):pass
class _ContinueLoop_A373(Exception):pass
class _ContinueLoop_A3F8(Exception):pass
class _ContinueLoop_A444(Exception):pass
class _ContinueLoop_A461(Exception):pass
class _ContinueLoop_A481(Exception):pass
class _ContinueLoop_A4CE(Exception):pass
class _ContinueLoop_A571(Exception):pass
class _ContinueLoop_A621(Exception):pass
class _ContinueLoop_A705(Exception):pass
class _ContinueLoop_A727(Exception):pass
class _ContinueLoop_A7CA(Exception):pass
class _ContinueLoop_A7DA(Exception):pass
class _ContinueLoop_A7E6(Exception):pass
class _ContinueLoop_A83B(Exception):pass
class _ContinueLoop_A938(Exception):pass
class _ContinueLoop_A9D0(Exception):pass
class _ContinueLoop_A9E4(Exception):pass
class _ContinueLoop_AA04(Exception):pass
class _ContinueLoop_AA20(Exception):pass
class _ContinueLoop_AA39(Exception):pass
class _ContinueLoop_AA8A(Exception):pass
class _ContinueLoop_AA9D(Exception):pass
class _ContinueLoop_AAE6(Exception):pass
class _ContinueLoop_AB1A(Exception):pass
class _ContinueLoop_AB2D(Exception):pass
class _ContinueLoop_AB79(Exception):pass
class _ContinueLoop_ABB8(Exception):pass
class _ContinueLoop_ABF9(Exception):pass
class _ContinueLoop_AC33(Exception):pass
class _ContinueLoop_ACF2(Exception):pass
class _ContinueLoop_ADA7(Exception):pass
class _ContinueLoop_AEC7(Exception):pass
class _ContinueLoop_AF35(Exception):pass
class _ContinueLoop_B01B(Exception):pass
class _ContinueLoop_B043(Exception):pass
class _ContinueLoop_B197(Exception):pass
class _ContinueLoop_B1AF(Exception):pass
class _ContinueLoop_B242(Exception):pass
class _ContinueLoop_B264(Exception):pass
class _ContinueLoop_B2FF(Exception):pass
class _ContinueLoop_B30B(Exception):pass
class _ContinueLoop_B367(Exception):pass
class _ContinueLoop_B393(Exception):pass
class _ContinueLoop_B3FB(Exception):pass
class _ContinueLoop_B408(Exception):pass
class _ContinueLoop_B43F(Exception):pass
class _ContinueLoop_B49C(Exception):pass
class _ContinueLoop_B4BF(Exception):pass
class _ContinueLoop_B504(Exception):pass
class _ContinueLoop_B551(Exception):pass
class _ContinueLoop_B5AC(Exception):pass
class _ContinueLoop_B5E4(Exception):pass
class _ContinueLoop_B5FC(Exception):pass
class _ContinueLoop_B639(Exception):pass
class _ContinueLoop_B68A(Exception):pass
class _ContinueLoop_B78B(Exception):pass
class _ContinueLoop_B846(Exception):pass
class _ContinueLoop_B86A(Exception):pass
class _ContinueLoop_B89F(Exception):pass
class _ContinueLoop_B8AF(Exception):pass
class _ContinueLoop_B8C6(Exception):pass
class _ContinueLoop_B8FE(Exception):pass
class _ContinueLoop_B964(Exception):pass
class _ContinueLoop_B971(Exception):pass
class _ContinueLoop_B99B(Exception):pass
class _ContinueLoop_B9E5(Exception):pass
class _ContinueLoop_BA95(Exception):pass
class _ContinueLoop_BAC0(Exception):pass
class _ContinueLoop_BB1C(Exception):pass
class _ContinueLoop_BB40(Exception):pass
class _ContinueLoop_BB53(Exception):pass
class _ContinueLoop_BB8D(Exception):pass
class _ContinueLoop_BBC1(Exception):pass
class _ContinueLoop_BBE6(Exception):pass
class _ContinueLoop_BC28(Exception):pass
class _ContinueLoop_BC3E(Exception):pass
class _ContinueLoop_BD16(Exception):pass
class _ContinueLoop_BD36(Exception):pass
class _ContinueLoop_BD4D(Exception):pass
class _ContinueLoop_BD7A(Exception):pass
class _ContinueLoop_BD8A(Exception):pass
class _ContinueLoop_BDA7(Exception):pass
class _ContinueLoop_BE48(Exception):pass
class _ContinueLoop_BEC7(Exception):pass
class _ContinueLoop_BEE6(Exception):pass
class _ContinueLoop_C1E4(Exception):pass
class _ContinueLoop_C1F6(Exception):pass
class _ContinueLoop_C252(Exception):pass
class _ContinueLoop_C298(Exception):pass
class _ContinueLoop_C2F5(Exception):pass
class _ContinueLoop_C349(Exception):pass
class _ContinueLoop_C40E(Exception):pass
class _ContinueLoop_C52D(Exception):pass
class _ContinueLoop_C586(Exception):pass
class _ContinueLoop_C59C(Exception):pass
class _ContinueLoop_C5BE(Exception):pass
class _ContinueLoop_C616(Exception):pass
class _ContinueLoop_C646(Exception):pass
class _ContinueLoop_C663(Exception):pass
class _ContinueLoop_C6FF(Exception):pass
class _ContinueLoop_C70E(Exception):pass
class _ContinueLoop_C724(Exception):pass
class _ContinueLoop_C732(Exception):pass
class _ContinueLoop_C748(Exception):pass
class _ContinueLoop_C777(Exception):pass
class _ContinueLoop_C79F(Exception):pass
class _ContinueLoop_C7BB(Exception):pass
class _ContinueLoop_C7C1(Exception):pass
class _ContinueLoop_C7FF(Exception):pass
class _ContinueLoop_C80E(Exception):pass
class _ContinueLoop_C821(Exception):pass
class _ContinueLoop_C840(Exception):pass
class _ContinueLoop_C889(Exception):pass
class _ContinueLoop_C897(Exception):pass
class _ContinueLoop_C8B6(Exception):pass
class _ContinueLoop_C8EE(Exception):pass
class _ContinueLoop_C902(Exception):pass
class _ContinueLoop_C92B(Exception):pass
class _ContinueLoop_C997(Exception):pass
class _ContinueLoop_C9C1(Exception):pass
class _ContinueLoop_CA1E(Exception):pass
class _ContinueLoop_CA7F(Exception):pass
class _ContinueLoop_CA9A(Exception):pass
class _ContinueLoop_CAB1(Exception):pass
class _ContinueLoop_CABD(Exception):pass
class _ContinueLoop_CB0F(Exception):pass
class _ContinueLoop_CB1D(Exception):pass
class _ContinueLoop_CB79(Exception):pass
class _ContinueLoop_CB8A(Exception):pass
class _ContinueLoop_CB98(Exception):pass
class _ContinueLoop_CBA8(Exception):pass
class _ContinueLoop_CC17(Exception):pass
class _ContinueLoop_CD0B(Exception):pass
class _ContinueLoop_CE69(Exception):pass
class _ContinueLoop_CEDF(Exception):pass
class _ContinueLoop_CF8C(Exception):pass
class _ContinueLoop_D08A(Exception):pass
class _ContinueLoop_D0B7(Exception):pass
class _ContinueLoop_D0E9(Exception):pass
class _ContinueLoop_D1B2(Exception):pass
class _ContinueLoop_D1C5(Exception):pass
class _ContinueLoop_D257(Exception):pass
class _ContinueLoop_D266(Exception):pass
class _ContinueLoop_D30B(Exception):pass
class _ContinueLoop_D340(Exception):pass
class _ContinueLoop_D3E4(Exception):pass
class _ContinueLoop_D3F0(Exception):pass
class _ContinueLoop_D403(Exception):pass
class _ContinueLoop_D417(Exception):pass
class _ContinueLoop_D448(Exception):pass
class _ContinueLoop_D47B(Exception):pass
class _ContinueLoop_D4B0(Exception):pass
class _ContinueLoop_D4C2(Exception):pass
class _ContinueLoop_D4CF(Exception):pass
class _ContinueLoop_D4DF(Exception):pass
class _ContinueLoop_D4F4(Exception):pass
class _ContinueLoop_D52D(Exception):pass
class _ContinueLoop_D58B(Exception):pass

class DomesticCooperationController(UIControlBase):
    """One original cooperative call, retaining real caller/stack and waits.

    A000 is the genuine main2 banked trampoline; A00F is its decision body.
    An invocation can finish, request battle/UI handling, or await6F8B==1.
    resume only observes externally generated acknowledgement; it never writes
    that flag or advances a hardware/NMI event on behalf of another owner.
    """
    PAIR=(10,11)
    PUBLIC_ENTRIES=(0xA000,0xA00F)
    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],ruler=m[RULER],
                    request=m[AI_REQUEST],phase=m[AI_PHASE],budget=m[AI_BUDGET],
                    selected_city=m[SELECTED_CITY],strategy_weights=tuple(m[0x6F5F+i]for i in range(3)),
                    city_wrap_count=m[CITY_WRAP_COUNT],ruler_city_cursor=m[0x6F83+m[RULER]]if m[RULER]<7 else None,
                    random_cursors=tuple(m[i]for i in (0x52,0x54,0x55)))
    def _dispatch(self,pc,targets):
        # D494 retains Y using20..24, unlike fixed EADE's00..04 protocol.
        r=self.registers;m=self.memory;index=r.a
        if pc not in(0xA039,0xA1BC)or index>=3:raise ValueError('Outside original three-way domestic dispatch')
        self._push((pc+2)>>8);self._push(pc+2)
        m[0x20]=r.y;r.a=self._shift(r.a,True);self._y(r.a);self._y(r.y+1)
        self._a(self._pop());m[0x21]=r.a;self._a(self._pop());m[0x22]=r.a
        self._a(m[((m[0x21]|m[0x22]<<8)+r.y)&65535]);m[0x23]=r.a
        self._y(r.y+1);self._a(m[((m[0x21]|m[0x22]<<8)+r.y)&65535]);m[0x24]=r.a
        self._y(m[0x20]);r.pc=m[0x23]|m[0x24]<<8
        if r.pc!=targets[index]:raise ValueError('Pinned inline dispatch words unavailable in current caller mapping')
        return index
    def _drive(self):
        while True:
            if self.pending is not None:
                call=self.pending
                if isinstance(call,ServiceWait):
                    if self.memory[call.address]!=call.value:return self._result('waiting')
                    self.pending=None
                else:
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
    def run_entry(self,entry=None,*,registers=None,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('An actual caller register/stack context is required')
        if tuple(getattr(self.memory,'banks',())[1:3])!=self.PAIR:raise ValueError('Domestic decision requires physical10/11 caller mapping')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)

    def _entry(self,entry):
        if entry==0xA000:return self.domestic_entry()
        elif entry==0xA00F:return self.cooperate_domestic_ai()
        elif entry==0xA042:return self.return_ai_call()
        elif entry==0xA043:return self.initialize_strategy_weights()
        elif entry==0xA0D3:return self.scan_neighbor_roster_pressure()
        elif entry==0xA19C:return self.choose_three_way_strategy()
        elif entry==0xA1C5:return self.military_strategy()
        elif entry==0xA240:return self.choose_attack_city()
        elif entry==0xA2D3:return self.diplomacy_attack_filter()
        elif entry==0xA303:return self.seek_connected_reinforcements()
        elif entry==0xA3D6:return self.select_reinforcement_officer()
        elif entry==0xA45C:return self.prepare_attack_troops()
        elif entry==0xA481:return self.fill_officer_troops()
        elif entry==0xA55C:return self.transfer_attack_gold()
        elif entry==0xA60C:return self.transfer_attack_grain()
        elif entry==0xA6BC:return self.domesticcooperationcontroller_a6bc()
        elif entry==0xA6C9:return self.choose_attack_officer_count()
        elif entry==0xA74A:return self.quote_attack_supplies()
        elif entry==0xA79C:return self.commit_attack_preparation()
        elif entry==0xA8D7:return self.consume_battle_return()
        elif entry==0xA910:return self.handle_returned_leader()
        elif entry==0xA91C:return self.handle_returned_leader_alternate()
        elif entry==0xA91F:return self.domesticcooperationcontroller_a91f()
        elif entry==0xA9CC:return self.domesticcooperationcontroller_a9cc()
        elif entry==0xAA2D:return self.domesticcooperationcontroller_aa2d()
        elif entry==0xAA80:return self.domesticcooperationcontroller_aa80()
        elif entry==0xAADE:return self.domesticcooperationcontroller_aade()
        elif entry==0xAB0C:return self.adjust_commander_loyalty()
        elif entry==0xAB10:return self.domesticcooperationcontroller_ab10()
        elif entry==0xAB71:return self.domesticcooperationcontroller_ab71()
        elif entry==0xAB9F:return self.adjust_roster_loyalty()
        elif entry==0xABA3:return self.domesticcooperationcontroller_aba3()
        elif entry==0xAC67:return self.domesticcooperationcontroller_ac67()
        elif entry==0xACD5:return self.domesticcooperationcontroller_acd5()
        elif entry==0xAEBF:return self.domesticcooperationcontroller_aebf()
        elif entry==0xAF9C:return self.domesticcooperationcontroller_af9c()
        elif entry==0xB067:return self.domesticcooperationcontroller_b067()
        elif entry==0xB180:return self.domesticcooperationcontroller_b180()
        elif entry==0xB1F9:return self.domesticcooperationcontroller_b1f9()
        elif entry==0xB1FD:return self.domesticcooperationcontroller_b1fd()
        elif entry==0xB287:return self.domesticcooperationcontroller_b287()
        elif entry==0xB433:return self.domesticcooperationcontroller_b433()
        elif entry==0xB49C:return self.city_assignment_strategy()
        elif entry==0xB53E:return self.domesticcooperationcontroller_b53e()
        elif entry==0xB7A2:return self.domesticcooperationcontroller_b7a2()
        elif entry==0xB7CE:return self.domesticcooperationcontroller_b7ce()
        elif entry==0xB837:return self.domesticcooperationcontroller_b837()
        elif entry==0xB85F:return self.domesticcooperationcontroller_b85f()
        elif entry==0xB898:return self.domesticcooperationcontroller_b898()
        elif entry==0xB90A:return self.domesticcooperationcontroller_b90a()
        elif entry==0xB923:return self.domesticcooperationcontroller_b923()
        elif entry==0xB955:return self.domesticcooperationcontroller_b955()
        elif entry==0xBB48:return self.domesticcooperationcontroller_bb48()
        elif entry==0xBB82:return self.domesticcooperationcontroller_bb82()
        elif entry==0xBD3E:return self.domesticcooperationcontroller_bd3e()
        elif entry==0xBD40:return self.domesticcooperationcontroller_bd40()
        elif entry==0xBEC7:return self.city_development_strategy()
        elif entry==0xBEE6:return self.scan_next_owned_city()
        elif entry==0xC1A7:return self.increase_governance()
        elif entry==0xC1C0:return self.increase_governance_for_population()
        elif entry==0xC1E0:return self.officer_and_equipment_stage()
        elif entry==0xC248:return self.choose_lowest_loyalty_officer()
        elif entry==0xC2EB:return self.choose_lowest_intelligence_officer()
        elif entry==0xC3A4:return self.domesticcooperationcontroller_c3a4()
        elif entry==0xC3FF:return self.choose_weapon_purchase_officer()
        elif entry==0xC451:return self.lookup_next_equipment()
        elif entry==0xC50E:return self.move_ruler_city_position()
        elif entry==0xC5B9:return self.search_and_recruit_preparation()
        elif entry==0xC5D2:return self.recruit_appearing_officers()
        elif entry==0xC66F:return self.recruitment_probability()
        elif entry==0xC6CC:return self.recruit_unaffiliated_officers()
        elif entry==0xC79A:return self.recover_owned_city_health()
        elif entry==0xC80A:return self.domesticcooperationcontroller_c80a()
        elif entry==0xC84D:return self.domesticcooperationcontroller_c84d()
        elif entry==0xC86A:return self.domesticcooperationcontroller_c86a()
        elif entry==0xC885:return self.domesticcooperationcontroller_c885()
        elif entry==0xC8C3:return self.domesticcooperationcontroller_c8c3()
        elif entry==0xC917:return self.domesticcooperationcontroller_c917()
        elif entry==0xC97A:return self.domesticcooperationcontroller_c97a()
        elif entry==0xC98F:return self.repair_owned_city_governors()
        elif entry==0xC9A5:return self.choose_city_governor()
        elif entry==0xCA19:return self.resolve_AI_leader_deaths()
        elif entry==0xCA68:return self.resolve_missing_heir()
        elif entry==0xCA7F:return self.await_extinction_acknowledgment()
        elif entry==0xCA87:return self.inspect_successor_candidates()
        elif entry==0xCAAD:return self.test_successor_candidate()
        elif entry==0xCB05:return self.release_extinct_ruler_cities()
        elif entry==0xCB52:return self.install_successor()
        elif entry==0xCB79:return self.await_successor_acknowledgment()
        elif entry==0xCB81:return self.adjust_successor_followers()
        elif entry==0xCBA3:return self.domesticcooperationcontroller_cba3()
        elif entry==0xCC12:return self.sell_grain_for_low_gold()
        elif entry==0xCCF8:return self.domesticcooperationcontroller_ccf8()
        elif entry==0xCD68:return self.domesticcooperationcontroller_cd68()
        elif entry==0xCD9A:return self.domesticcooperationcontroller_cd9a()
        elif entry==0xCDB9:return self.domesticcooperationcontroller_cdb9()
        elif entry==0xCE1B:return self.domesticcooperationcontroller_ce1b()
        elif entry==0xCE67:return self.domesticcooperationcontroller_ce67()
        elif entry==0xCEDD:return self.domesticcooperationcontroller_cedd()
        elif entry==0xCF3F:return self.recalculate_recruited_loyalty()
        elif entry==0xCF7C:return self.recalculate_other_loyalty()
        elif entry==0xD00C:return self.recalculate_shifted_loyalty()
        elif entry==0xD03A:return self.domesticcooperationcontroller_d03a()
        elif entry==0xD080:return self.domesticcooperationcontroller_d080()
        elif entry==0xD0AA:return self.domesticcooperationcontroller_d0aa()
        elif entry==0xD0E1:return self.count_enemy_neighbors()
        elif entry==0xD105:return self.city_pointer_and_resource_caps()
        elif entry==0xD152:return self.charge_task_budget()
        elif entry==0xD165:return self.charge_nested_budget_one()
        elif entry==0xD18D:return self.charge_nested_budget_three()
        elif entry==0xD1A4:return self.build_enemy_neighbor_list()
        elif entry==0xD249:return self.find_ruler_city()
        elif entry==0xD283:return self.domesticcooperationcontroller_d283()
        elif entry==0xD2AB:return self.officer_field_pointer()
        elif entry==0xD2D3:return self.domesticcooperationcontroller_d2d3()
        elif entry==0xD304:return self.count_prefix_officers()
        elif entry==0xD307:return self.domesticcooperationcontroller_d307()
        elif entry==0xD319:return self.ruler_pointer()
        elif entry==0xD336:return self.domesticcooperationcontroller_d336()
        elif entry==0xD36F:return self.pay_city_gold()
        elif entry==0xD3A9:return self.pay_city_grain()
        elif entry==0xD3DD:return self.compact_city_roster()
        elif entry==0xD40F:return self.divide_domestic_word()
        elif entry==0xD438:return self.multiply_domestic_word()
        elif entry==0xD471:return self.domesticcooperationcontroller_d471()
        elif entry==0xD4AD:return self.random_low_nibble_below()
        elif entry==0xD4BB:return self.random_below()
        elif entry==0xD4CB:return self.build_owned_connectivity()
        elif entry==0xD53E:return self.domesticcooperationcontroller_d53e()
        elif entry==0xD583:return self.common_connectivity_bits()
        elif entry==0xD5E7:return self.domesticcooperationcontroller_d5e7()
        elif entry==0xD61E:return self.domesticcooperationcontroller_d61e()
        elif entry==0xD69D:return self.cap_city_word()
        elif entry==0xD6E5:return self.domesticcooperationcontroller_d6e5()
        raise ValueError("Outside the original domestic procedure catalogue")

    def domestic_entry(self):
        """$A000: domestic entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA000)
        return (yield from self.cooperate_domestic_ai())

    def cooperate_domestic_ai(self):
        """A00F: early return, battle return, or ordered housekeeping then phase.

        The ordered preprocessing is real: connectivity, ruler placement,
        search/recruit, health, governors, ruler-city lookup, grain conversion.
        Three-way strategy selection occurs only after those persistent effects.
        """
        r=self.registers;m=self.memory;self._mark(0xA00F);self._a(m[AI_REQUEST])
        if r.p&N:return (yield from self.return_ai_call())
        self._compare(r.a,1)
        if r.p&Z:
            if not(yield from self._local_call(self.build_owned_connectivity,0xA018,0xA01B)):return
            return (yield from self.consume_battle_return())
        for method,call_pc in ((self.build_owned_connectivity,0xA01E),(self.move_ruler_city_position,0xA021),
                (self.search_and_recruit_preparation,0xA024),(self.recover_owned_city_health,0xA027)):
            if not(yield from self._local_call(method,call_pc,call_pc+3)):return
        self._a(m[RULER])
        if not(yield from self._local_call(self.repair_owned_city_governors,0xA02D,0xA030)):return
        if not(yield from self._local_call(self.find_ruler_city,0xA030,0xA033)):return
        if not(yield from self._local_call(self.sell_grain_for_low_gold,0xA033,0xA036)):return
        self._a(m[AI_PHASE]);index=self._dispatch(0xA039,(0xA043,0xA19C,0xA042))
        return (yield from (self.initialize_strategy_weights,self.choose_three_way_strategy,self.return_ai_call)[index]())

    def return_ai_call(self):
        """$A042: return ai call; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA042)
        self._rts();return

    def initialize_strategy_weights(self):
        """$A043: initialize strategy weights; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA043)
        self._a(0x00)
        m[0x0039]=r.a
        m[0x003A]=r.a
        m[0x003B]=r.a
        m[0x003C]=r.a
        m[0x003D]=r.a
        self._a(m[DIFFICULTY])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[RULER])
        self._y(r.a)
        self._a(m[(0xA133+r.y)&65535])
        m[WEIGHT_MILITARY]=r.a
        self._a(m[(0xA14B+r.y)&65535])
        m[WEIGHT_ASSIGNMENT]=r.a
        self._a(m[(0xA163+r.y)&65535])
        m[WEIGHT_DEVELOPMENT]=r.a
        if not (yield from self._local_call(self.scan_neighbor_roster_pressure,0xA070,0xA073)):return
        self._a(m[0x0038])
        m[0x0020]=r.a
        self._a(0x00)
        m[0x0021]=r.a
        m[0x0022]=r.a
        self._a(0x64)
        m[0x0023]=r.a
        if not (yield from self._local_call(self.multiply_domestic_word,0xA082,0xA085)):return
        self._a(m[0x0026])
        m[0x0021]=r.a
        self._a(m[0x0027])
        m[0x0022]=r.a
        self._a(m[0x0037])
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_domestic_word,0xA096,0xA099)):return
        self._a(m[0x0021])
        self._y(0x00)
        self._compare(r.a,0x1F)
        self._mark(0xA09F)
        if not r.p&C:
            pass
        else:
            self._y(r.y+1)
            self._compare(r.a,0x47)
            self._mark(0xA0A4)
            if not r.p&C:
                pass
            else:
                self._y(r.y+1)
                pass
            pass
        m[0x0020]=r.y
        self._a(m[DIFFICULTY])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[0x0020])
        self._y(r.a)
        self._a(m[(0xA17B+r.y)&65535])
        self._flag(C,False)
        self._add(m[WEIGHT_MILITARY])
        m[WEIGHT_MILITARY]=r.a
        self._a(m[(0xA186+r.y)&65535])
        self._flag(C,False)
        self._add(m[WEIGHT_ASSIGNMENT])
        m[WEIGHT_ASSIGNMENT]=r.a
        self._a(m[(0xA191+r.y)&65535])
        self._flag(C,False)
        self._add(m[WEIGHT_DEVELOPMENT])
        m[WEIGHT_DEVELOPMENT]=r.a
        m[AI_PHASE]=self._nz(m[AI_PHASE]+1)
        self._mark(0xA0D2)
        self._rts();return

    def scan_neighbor_roster_pressure(self):
        """$A0D3: scan neighbor roster pressure; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA0D3)
        self._y(0x30)
        yield from self._external(0xA0D5,0xF266,0xA0D8,"call",None)
        if r.pc!=0xA0D8:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0036]=r.a
        m[0x0037]=r.a
        m[0x0038]=r.a
        while True:  # natural loop $A0E3
            try:
                self._a(0x00)
                m[0x0039]=r.a
                self._a(m[0x0036])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                while True:  # natural loop $A0EF
                    try:
                        self._a(m[(0x9D72+r.y)&65535])
                        self._mark(0xA0F2)
                        if r.p&N:
                            pass
                        else:
                            m[0x0023]=r.a
                            m[0x0024]=r.y
                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA0F8,0xA0FB)):return
                            self._a(r.a & 0x07)
                            self._compare(r.a,0x07)
                            self._mark(0xA0FF)
                            if r.p&Z:
                                m[0x0037]=self._nz(m[0x0037]+1)
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.count_prefix_officers,0xA10C,0xA10F)):return
                                self._compare(r.a,0x04)
                                self._mark(0xA111)
                                if r.p&C:
                                    self._a(m[0x0023])
                                    self._y(m[0x0024])
                                    self._y(r.y+1)
                                    m[0x0039]=self._nz(m[0x0039]+1)
                                    self._x(m[0x0039])
                                    self._compare(r.x,0x08)
                                    self._mark(0xA126)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    pass
                                else:
                                    m[0x0038]=self._nz(m[0x0038]+1)
                                    pass
                                pass
                            else:
                                self._compare(r.a,m[RULER])
                                self._mark(0xA104)
                                if not r.p&Z:
                                    self._a(m[0x0023])
                                    self._y(m[0x0024])
                                    self._y(r.y+1)
                                    m[0x0039]=self._nz(m[0x0039]+1)
                                    self._x(m[0x0039])
                                    self._compare(r.x,0x08)
                                    self._mark(0xA126)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    pass
                                else:
                                    m[0x0037]=self._nz(m[0x0037]+1)
                                    self._a(m[0x0036])
                                    if not (yield from self._local_call(self.count_prefix_officers,0xA10C,0xA10F)):return
                                    self._compare(r.a,0x04)
                                    self._mark(0xA111)
                                    if r.p&C:
                                        self._a(m[0x0023])
                                        self._y(m[0x0024])
                                        self._y(r.y+1)
                                        m[0x0039]=self._nz(m[0x0039]+1)
                                        self._x(m[0x0039])
                                        self._compare(r.x,0x08)
                                        self._mark(0xA126)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        pass
                                    else:
                                        m[0x0038]=self._nz(m[0x0038]+1)
                                        pass
                                    pass
                                pass
                            pass
                        m[0x0036]=self._nz(m[0x0036]+1)
                        self._a(m[0x0036])
                        self._compare(r.a,0x1E)
                        self._mark(0xA130)
                        if not r.p&C:
                            raise _ContinueLoop_A0E3
                        else:
                            pass
                        self._mark(0xA132)
                        self._rts();return
                    except _ContinueLoop_A0EF:
                        continue
            except _ContinueLoop_A0E3:
                continue

    def choose_three_way_strategy(self):
        """$A19C: three strategies: original low4 rejection sampling then two byte thresholds; keeps real caller."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA19C)
        self._a(m[WEIGHT_MILITARY])
        self._flag(C,False)
        self._add(m[WEIGHT_ASSIGNMENT])
        m[0x0021]=r.a
        self._flag(C,False)
        self._add(m[WEIGHT_DEVELOPMENT])
        if not (yield from self._local_call(self.random_low_nibble_below,0xA1A9,0xA1AC)):return
        self._y(0x00)
        self._compare(r.a,m[WEIGHT_MILITARY])
        self._mark(0xA1B1)
        if not r.p&C:
            pass
        else:
            self._y(r.y+1)
            self._compare(r.a,m[0x0021])
            self._mark(0xA1B6)
            if not r.p&C:
                pass
            else:
                self._y(r.y+1)
                pass
            pass
        self._a(r.y)
        self._a(r.a & 0x03)
        self._mark(0xA1BC)
        index=self._dispatch(0xA1BC,(41413, 46236, 48839))
        return (yield from (self.military_strategy,self.city_assignment_strategy,self.city_development_strategy,)[index]())

    def military_strategy(self):
        """$A1C5: military strategy; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1C5)
        self._a(m[DIFFICULTY])
        self._compare(r.a,0x02)
        self._mark(0xA1CA)
        if r.p&Z:
            self._a(0x64)
            if not (yield from self._local_call(self.random_below,0xA1DA,0xA1DD)):return
            self._compare(r.a,0x1E)
            self._mark(0xA1DF)
            if r.p&C:
                self._a(m[DIFFICULTY])
                self._mark(0xA1E7)
                if r.p&Z:
                    self._a(m[YEAR])
                    self._compare(r.a,0x5A)
                    self._mark(0xA203)
                    if r.p&C:
                        self._a(0x00)
                        m[0x0044]=r.a
                        if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        self._a(m[0x0037])
                        self._compare(r.a,0x0A)
                        self._mark(0xA21E)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x0A)
                            m[0x0037]=r.a
                            pass
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                        self._compare(r.a,m[0x0037])
                        self._mark(0xA22E)
                        if r.p&C:
                            pass
                        else:
                            if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                            pass
                        if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                        if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                        if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                        self._mark(0xA23C)
                        self._rts();return
                    else:
                        return (yield from self.city_development_strategy())
                else:
                    self._compare(r.a,0x02)
                    self._mark(0xA1EB)
                    if r.p&Z:
                        self._a(0x00)
                        m[0x0044]=r.a
                        if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        self._a(m[0x0037])
                        self._compare(r.a,0x0A)
                        self._mark(0xA21E)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x0A)
                            m[0x0037]=r.a
                            pass
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                        self._compare(r.a,m[0x0037])
                        self._mark(0xA22E)
                        if r.p&C:
                            pass
                        else:
                            if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                            pass
                        if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                        if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                        if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                        self._mark(0xA23C)
                        self._rts();return
                    else:
                        self._a(m[YEAR])
                        self._compare(r.a,0x5A)
                        self._mark(0xA1F2)
                        if r.p&C:
                            self._a(0x00)
                            m[0x0044]=r.a
                            if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                            m[0x0037]=self._nz(m[0x0037]+1)
                            m[0x0037]=self._nz(m[0x0037]+1)
                            m[0x0037]=self._nz(m[0x0037]+1)
                            self._a(m[0x0037])
                            self._compare(r.a,0x0A)
                            self._mark(0xA21E)
                            if not r.p&C:
                                pass
                            else:
                                self._a(0x0A)
                                m[0x0037]=r.a
                                pass
                            self._a(m[0x003A])
                            if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                            self._compare(r.a,m[0x0037])
                            self._mark(0xA22E)
                            if r.p&C:
                                pass
                            else:
                                if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                                pass
                            if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                            if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                            if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                            self._mark(0xA23C)
                            self._rts();return
                        else:
                            self._a(m[MONTH])
                            self._compare(r.a,0x06)
                            self._mark(0xA1F9)
                            if r.p&C:
                                self._a(0x00)
                                m[0x0044]=r.a
                                if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                                m[0x0037]=self._nz(m[0x0037]+1)
                                m[0x0037]=self._nz(m[0x0037]+1)
                                m[0x0037]=self._nz(m[0x0037]+1)
                                self._a(m[0x0037])
                                self._compare(r.a,0x0A)
                                self._mark(0xA21E)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x0A)
                                    m[0x0037]=r.a
                                    pass
                                self._a(m[0x003A])
                                if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                                self._compare(r.a,m[0x0037])
                                self._mark(0xA22E)
                                if r.p&C:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                                    pass
                                if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                                if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                                if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                                self._mark(0xA23C)
                                self._rts();return
                            else:
                                return (yield from self.city_development_strategy())
            else:
                self._a(0x01)
                m[0x0044]=r.a
                if not (yield from self._local_call(self.domesticcooperationcontroller_d0aa,0xB113,0xB116)):return
                self._a(m[0x002B])
                self._mark(0xB118)
                if not r.p&Z:
                    self._a(m[0x002B])
                    m[0x0023]=r.a
                    self._a(m[0x002C])
                    m[0x0022]=r.a
                    self._a(0x00)
                    m[0x0021]=r.a
                    m[0x0024]=r.a
                    if not (yield from self._local_call(self.divide_domestic_word,0xB131,0xB134)):return
                    self._a(m[0x0022])
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d03a,0xB11A,0xB11D)):return
                    self._a(m[0x0040])
                    pass
                m[0x0040]=r.a
                self._compare(r.a,0x04)
                self._mark(0xB13B)
                if r.p&C:
                    self._a(m[0x0040])
                    self._flag(C,True)
                    self._add(0x02,subtract=True)
                    self._compare(r.a,0x10)
                    self._mark(0xB14C)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x02)
                        pass
                    self._compare(r.a,0x02)
                    self._mark(0xB152)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x02)
                        pass
                    self._flag(C,False)
                    self._add(0x02)
                    m[0x0037]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_b180,0xB15C,0xB15F)):return
                    self._a(m[0x0038])
                    self._compare(r.a,0xFF)
                    self._mark(0xB164)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xB169,0xB16C)):return
                        self._compare(r.a,m[0x0037])
                        self._mark(0xB16F)
                        if r.p&C:
                            pass
                        else:
                            if not (yield from self._local_call(self.seek_connected_reinforcements,0xB171,0xB174)):return
                            pass
                        if not (yield from self._local_call(self.domesticcooperationcontroller_b1f9,0xB174,0xB177)):return
                        if not (yield from self._local_call(self.domesticcooperationcontroller_b287,0xB177,0xB17A)):return
                        pass
                    pass
                else:
                    self._compare(r.a,0x02)
                    self._mark(0xB13F)
                    if r.p&C:
                        pass
                    else:
                        self._a(0xFF)
                        m[0x0037]=r.a
                        m[0x0038]=r.a
                        m[0x0039]=r.a
                        self._a(0x00)
                        m[0x0036]=r.a
                        while True:  # natural loop $B367
                            try:
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB36A,0xB36D)):return
                                self._a(r.a & 0x07)
                                self._compare(r.a,m[RULER])
                                self._mark(0xB372)
                                if not r.p&Z:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_b433,0xB374,0xB377)):return
                                    pass
                                m[0x0036]=self._nz(m[0x0036]+1)
                                self._a(m[0x0036])
                                self._compare(r.a,0x1E)
                                self._mark(0xB37F)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0037])
                                self._compare(r.a,0xFF)
                                self._mark(0xB386)
                                if not r.p&Z:
                                    self._a(m[0x0037])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    m[0x0024]=r.a
                                    while True:  # natural loop $B393
                                        try:
                                            self._y(m[0x0024])
                                            self._a(m[(0x9D72+r.y)&65535])
                                            self._mark(0xB398)
                                            if r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB39A,0xB39D)):return
                                                self._a(r.a & 0x07)
                                                self._compare(r.a,m[RULER])
                                                self._mark(0xB3A2)
                                                if r.p&Z:
                                                    self._y(m[0x0024])
                                                    self._a(m[(0x9D72+r.y)&65535])
                                                    m[0x0038]=r.a
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB3B1,0xB3B4)):return
                                                    self._a(m[0x0020])
                                                    m[0x0022]=r.a
                                                    self._a(m[0x0021])
                                                    m[0x0023]=r.a
                                                    self._a(m[0x0037])
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB3BF,0xB3C2)):return
                                                    self._y(0x02)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(0x04)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(0x02)
                                                    self._a(0x00)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(0x11)
                                                    m[0x0024]=r.y
                                                    m[0x0025]=r.y
                                                    self._y(0x04)
                                                    m[0x0026]=r.y
                                                    while True:  # natural loop $B3FB
                                                        try:
                                                            self._y(m[0x0024])
                                                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                            self._compare(r.a,0xFF)
                                                            self._mark(0xB401)
                                                            if r.p&Z:
                                                                pass
                                                            else:
                                                                self._push(r.a)
                                                                self._a(0xFF)
                                                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                while True:  # natural loop $B408
                                                                    try:
                                                                        self._y(m[0x0025])
                                                                        m[0x0025]=self._nz(m[0x0025]+1)
                                                                        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                        self._compare(r.a,0xFF)
                                                                        self._mark(0xB410)
                                                                        if not r.p&Z:
                                                                            continue
                                                                        else:
                                                                            pass
                                                                        self._a(self._pop())
                                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                        m[0x0026]=self._nz(m[0x0026]+1)
                                                                        m[0x0026]=self._nz(m[0x0026]+1)
                                                                        m[0x0024]=self._nz(m[0x0024]+1)
                                                                        self._y(m[0x0024])
                                                                        self._compare(r.y,0x1B)
                                                                        self._mark(0xB41F)
                                                                        if not r.p&C:
                                                                            raise _ContinueLoop_B3FB
                                                                        else:
                                                                            pass
                                                                        self._y(0x00)
                                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                        self._a(r.a & 0xF8)
                                                                        self._a(r.a | 0x07)
                                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                        self._a(m[0x0026])
                                                                        if not (yield from self._local_call(self.charge_task_budget,0xB42D,0xB430)):return
                                                                        return (yield from self.city_development_strategy())
                                                                    except _ContinueLoop_B408:
                                                                        continue
                                                            self._y(0x00)
                                                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                            self._a(r.a & 0xF8)
                                                            self._a(r.a | 0x07)
                                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                            self._a(m[0x0026])
                                                            if not (yield from self._local_call(self.charge_task_budget,0xB42D,0xB430)):return
                                                            return (yield from self.city_development_strategy())
                                                        except _ContinueLoop_B3FB:
                                                            continue
                                                else:
                                                    m[0x0024]=self._nz(m[0x0024]+1)
                                                    continue
                                            return (yield from self.city_development_strategy())
                                        except _ContinueLoop_B393:
                                            continue
                                else:
                                    pass
                                return (yield from self.city_development_strategy())
                            except _ContinueLoop_B367:
                                continue
                    pass
                return (yield from self.city_development_strategy())
        else:
            self._a(0x64)
            if not (yield from self._local_call(self.random_below,0xA1CE,0xA1D1)):return
            self._compare(r.a,0x14)
            self._mark(0xA1D3)
            if r.p&C:
                self._a(m[DIFFICULTY])
                self._mark(0xA1E7)
                if r.p&Z:
                    self._a(m[YEAR])
                    self._compare(r.a,0x5A)
                    self._mark(0xA203)
                    if r.p&C:
                        self._a(0x00)
                        m[0x0044]=r.a
                        if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        self._a(m[0x0037])
                        self._compare(r.a,0x0A)
                        self._mark(0xA21E)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x0A)
                            m[0x0037]=r.a
                            pass
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                        self._compare(r.a,m[0x0037])
                        self._mark(0xA22E)
                        if r.p&C:
                            pass
                        else:
                            if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                            pass
                        if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                        if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                        if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                        self._mark(0xA23C)
                        self._rts();return
                    else:
                        return (yield from self.city_development_strategy())
                else:
                    self._compare(r.a,0x02)
                    self._mark(0xA1EB)
                    if r.p&Z:
                        self._a(0x00)
                        m[0x0044]=r.a
                        if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        m[0x0037]=self._nz(m[0x0037]+1)
                        self._a(m[0x0037])
                        self._compare(r.a,0x0A)
                        self._mark(0xA21E)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x0A)
                            m[0x0037]=r.a
                            pass
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                        self._compare(r.a,m[0x0037])
                        self._mark(0xA22E)
                        if r.p&C:
                            pass
                        else:
                            if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                            pass
                        if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                        if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                        if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                        self._mark(0xA23C)
                        self._rts();return
                    else:
                        self._a(m[YEAR])
                        self._compare(r.a,0x5A)
                        self._mark(0xA1F2)
                        if r.p&C:
                            self._a(0x00)
                            m[0x0044]=r.a
                            if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                            m[0x0037]=self._nz(m[0x0037]+1)
                            m[0x0037]=self._nz(m[0x0037]+1)
                            m[0x0037]=self._nz(m[0x0037]+1)
                            self._a(m[0x0037])
                            self._compare(r.a,0x0A)
                            self._mark(0xA21E)
                            if not r.p&C:
                                pass
                            else:
                                self._a(0x0A)
                                m[0x0037]=r.a
                                pass
                            self._a(m[0x003A])
                            if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                            self._compare(r.a,m[0x0037])
                            self._mark(0xA22E)
                            if r.p&C:
                                pass
                            else:
                                if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                                pass
                            if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                            if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                            if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                            self._mark(0xA23C)
                            self._rts();return
                        else:
                            self._a(m[MONTH])
                            self._compare(r.a,0x06)
                            self._mark(0xA1F9)
                            if r.p&C:
                                self._a(0x00)
                                m[0x0044]=r.a
                                if not (yield from self._local_call(self.choose_attack_city,0xA20D,0xA210)):return
                                m[0x0037]=self._nz(m[0x0037]+1)
                                m[0x0037]=self._nz(m[0x0037]+1)
                                m[0x0037]=self._nz(m[0x0037]+1)
                                self._a(m[0x0037])
                                self._compare(r.a,0x0A)
                                self._mark(0xA21E)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x0A)
                                    m[0x0037]=r.a
                                    pass
                                self._a(m[0x003A])
                                if not (yield from self._local_call(self.count_prefix_officers,0xA228,0xA22B)):return
                                self._compare(r.a,m[0x0037])
                                self._mark(0xA22E)
                                if r.p&C:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.seek_connected_reinforcements,0xA230,0xA233)):return
                                    pass
                                if not (yield from self._local_call(self.prepare_attack_troops,0xA233,0xA236)):return
                                if not (yield from self._local_call(self.domesticcooperationcontroller_a6bc,0xA236,0xA239)):return
                                if not (yield from self._local_call(self.commit_attack_preparation,0xA239,0xA23C)):return
                                self._mark(0xA23C)
                                self._rts();return
                            else:
                                return (yield from self.city_development_strategy())
            else:
                self._a(0x01)
                m[0x0044]=r.a
                if not (yield from self._local_call(self.domesticcooperationcontroller_d0aa,0xB113,0xB116)):return
                self._a(m[0x002B])
                self._mark(0xB118)
                if not r.p&Z:
                    self._a(m[0x002B])
                    m[0x0023]=r.a
                    self._a(m[0x002C])
                    m[0x0022]=r.a
                    self._a(0x00)
                    m[0x0021]=r.a
                    m[0x0024]=r.a
                    if not (yield from self._local_call(self.divide_domestic_word,0xB131,0xB134)):return
                    self._a(m[0x0022])
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d03a,0xB11A,0xB11D)):return
                    self._a(m[0x0040])
                    pass
                m[0x0040]=r.a
                self._compare(r.a,0x04)
                self._mark(0xB13B)
                if r.p&C:
                    self._a(m[0x0040])
                    self._flag(C,True)
                    self._add(0x02,subtract=True)
                    self._compare(r.a,0x10)
                    self._mark(0xB14C)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x02)
                        pass
                    self._compare(r.a,0x02)
                    self._mark(0xB152)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x02)
                        pass
                    self._flag(C,False)
                    self._add(0x02)
                    m[0x0037]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_b180,0xB15C,0xB15F)):return
                    self._a(m[0x0038])
                    self._compare(r.a,0xFF)
                    self._mark(0xB164)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xB169,0xB16C)):return
                        self._compare(r.a,m[0x0037])
                        self._mark(0xB16F)
                        if r.p&C:
                            pass
                        else:
                            if not (yield from self._local_call(self.seek_connected_reinforcements,0xB171,0xB174)):return
                            pass
                        if not (yield from self._local_call(self.domesticcooperationcontroller_b1f9,0xB174,0xB177)):return
                        if not (yield from self._local_call(self.domesticcooperationcontroller_b287,0xB177,0xB17A)):return
                        pass
                    pass
                else:
                    self._compare(r.a,0x02)
                    self._mark(0xB13F)
                    if r.p&C:
                        pass
                    else:
                        self._a(0xFF)
                        m[0x0037]=r.a
                        m[0x0038]=r.a
                        m[0x0039]=r.a
                        self._a(0x00)
                        m[0x0036]=r.a
                        while True:  # natural loop $B367
                            try:
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB36A,0xB36D)):return
                                self._a(r.a & 0x07)
                                self._compare(r.a,m[RULER])
                                self._mark(0xB372)
                                if not r.p&Z:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_b433,0xB374,0xB377)):return
                                    pass
                                m[0x0036]=self._nz(m[0x0036]+1)
                                self._a(m[0x0036])
                                self._compare(r.a,0x1E)
                                self._mark(0xB37F)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0037])
                                self._compare(r.a,0xFF)
                                self._mark(0xB386)
                                if not r.p&Z:
                                    self._a(m[0x0037])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    m[0x0024]=r.a
                                    while True:  # natural loop $B393
                                        try:
                                            self._y(m[0x0024])
                                            self._a(m[(0x9D72+r.y)&65535])
                                            self._mark(0xB398)
                                            if r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB39A,0xB39D)):return
                                                self._a(r.a & 0x07)
                                                self._compare(r.a,m[RULER])
                                                self._mark(0xB3A2)
                                                if r.p&Z:
                                                    self._y(m[0x0024])
                                                    self._a(m[(0x9D72+r.y)&65535])
                                                    m[0x0038]=r.a
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB3B1,0xB3B4)):return
                                                    self._a(m[0x0020])
                                                    m[0x0022]=r.a
                                                    self._a(m[0x0021])
                                                    m[0x0023]=r.a
                                                    self._a(m[0x0037])
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB3BF,0xB3C2)):return
                                                    self._y(0x02)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(0x04)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                    self._y(0x02)
                                                    self._a(0x00)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                    self._y(0x11)
                                                    m[0x0024]=r.y
                                                    m[0x0025]=r.y
                                                    self._y(0x04)
                                                    m[0x0026]=r.y
                                                    while True:  # natural loop $B3FB
                                                        try:
                                                            self._y(m[0x0024])
                                                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                            self._compare(r.a,0xFF)
                                                            self._mark(0xB401)
                                                            if r.p&Z:
                                                                pass
                                                            else:
                                                                self._push(r.a)
                                                                self._a(0xFF)
                                                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                while True:  # natural loop $B408
                                                                    try:
                                                                        self._y(m[0x0025])
                                                                        m[0x0025]=self._nz(m[0x0025]+1)
                                                                        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                        self._compare(r.a,0xFF)
                                                                        self._mark(0xB410)
                                                                        if not r.p&Z:
                                                                            continue
                                                                        else:
                                                                            pass
                                                                        self._a(self._pop())
                                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                        m[0x0026]=self._nz(m[0x0026]+1)
                                                                        m[0x0026]=self._nz(m[0x0026]+1)
                                                                        m[0x0024]=self._nz(m[0x0024]+1)
                                                                        self._y(m[0x0024])
                                                                        self._compare(r.y,0x1B)
                                                                        self._mark(0xB41F)
                                                                        if not r.p&C:
                                                                            raise _ContinueLoop_B3FB
                                                                        else:
                                                                            pass
                                                                        self._y(0x00)
                                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                        self._a(r.a & 0xF8)
                                                                        self._a(r.a | 0x07)
                                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                        self._a(m[0x0026])
                                                                        if not (yield from self._local_call(self.charge_task_budget,0xB42D,0xB430)):return
                                                                        return (yield from self.city_development_strategy())
                                                                    except _ContinueLoop_B408:
                                                                        continue
                                                            self._y(0x00)
                                                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                            self._a(r.a & 0xF8)
                                                            self._a(r.a | 0x07)
                                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                            self._a(m[0x0026])
                                                            if not (yield from self._local_call(self.charge_task_budget,0xB42D,0xB430)):return
                                                            return (yield from self.city_development_strategy())
                                                        except _ContinueLoop_B3FB:
                                                            continue
                                                else:
                                                    m[0x0024]=self._nz(m[0x0024]+1)
                                                    continue
                                            return (yield from self.city_development_strategy())
                                        except _ContinueLoop_B393:
                                            continue
                                else:
                                    pass
                                return (yield from self.city_development_strategy())
                            except _ContinueLoop_B367:
                                continue
                    pass
                return (yield from self.city_development_strategy())

    def choose_attack_city(self):
        """$A240: choose attack city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA240)
        self._y(0x30)
        yield from self._external(0xA242,0xF266,0xA245,"call",None)
        if r.pc!=0xA245:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0036]=r.a
        self._a(0xFF)
        m[0x0037]=r.a
        m[0x0038]=r.a
        m[0x003A]=r.a
        self._a(0x00)
        m[0x0039]=r.a
        while True:  # natural loop $A25A
            try:
                self._a(m[0x0036])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA25D,0xA260)):return
                self._compare(r.a,m[RULER])
                self._mark(0xA263)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d307,0xA265,0xA268)):return
                    m[0x0026]=r.a
                    self._a(m[0x0036])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0024]=r.a
                    while True:  # natural loop $A272
                        try:
                            self._y(m[0x0024])
                            self._a(m[(0x9D72+r.y)&65535])
                            self._mark(0xA277)
                            if r.p&N:
                                pass
                            else:
                                m[0x0025]=r.a
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA27B,0xA27E)):return
                                self._a(r.a & 0x07)
                                self._compare(r.a,0x07)
                                self._mark(0xA282)
                                if r.p&Z:
                                    pass
                                else:
                                    self._compare(r.a,m[RULER])
                                    self._mark(0xA287)
                                    if r.p&Z:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.diplomacy_attack_filter,0xA289,0xA28C)):return
                                        self._mark(0xA28C)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_d307,0xA28E,0xA291)):return
                                            self._compare(r.a,m[0x0037])
                                            self._mark(0xA294)
                                            if r.p&Z:
                                                m[0x0037]=r.a
                                                self._a(m[0x0025])
                                                self._compare(r.a,m[0x0038])
                                                self._mark(0xA2A0)
                                                if not r.p&Z:
                                                    m[0x0038]=r.a
                                                    self._a(m[0x0026])
                                                    m[0x0039]=r.a
                                                    self._a(m[0x0036])
                                                    m[0x003A]=r.a
                                                    pass
                                                else:
                                                    self._a(m[0x0026])
                                                    self._compare(r.a,m[0x0039])
                                                    self._mark(0xA2A7)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[0x0039]=r.a
                                                        self._a(m[0x0036])
                                                        m[0x003A]=r.a
                                                        pass
                                                    pass
                                                pass
                                            else:
                                                self._mark(0xA296)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    m[0x0037]=r.a
                                                    self._a(m[0x0025])
                                                    self._compare(r.a,m[0x0038])
                                                    self._mark(0xA2A0)
                                                    if not r.p&Z:
                                                        m[0x0038]=r.a
                                                        self._a(m[0x0026])
                                                        m[0x0039]=r.a
                                                        self._a(m[0x0036])
                                                        m[0x003A]=r.a
                                                        pass
                                                    else:
                                                        self._a(m[0x0026])
                                                        self._compare(r.a,m[0x0039])
                                                        self._mark(0xA2A7)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[0x0039]=r.a
                                                            self._a(m[0x0036])
                                                            m[0x003A]=r.a
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                m[0x0024]=self._nz(m[0x0024]+1)
                                continue
                            m[0x0036]=self._nz(m[0x0036]+1)
                            self._a(m[0x0036])
                            self._compare(r.a,0x1E)
                            self._mark(0xA2D0)
                            if not r.p&C:
                                raise _ContinueLoop_A25A
                            else:
                                pass
                            self._mark(0xA2D2)
                            self._rts();return
                        except _ContinueLoop_A272:
                            continue
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xA2D0)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xA2D2)
                self._rts();return
            except _ContinueLoop_A25A:
                continue

    def diplomacy_attack_filter(self):
        """$A2D3: diplomacy attack filter; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2D3)
        self._push(r.a)
        self._a(m[0x0024])
        self._push(r.a)
        self._a(m[0x0025])
        self._push(r.a)
        self._a(m[RULER])
        if not (yield from self._local_call(self.ruler_pointer,0xA2DD,0xA2E0)):return
        self._a(m[0x0024])
        m[0x0022]=r.a
        self._a(m[0x0025])
        m[0x0023]=r.a
        self._a(self._pop())
        m[0x0025]=r.a
        self._a(self._pop())
        m[0x0024]=r.a
        self._a(self._pop())
        self._x(r.a)
        r.a=self._shift(r.a,False,rotate=False)
        self._flag(C,False)
        self._add(0x04)
        self._y(r.a)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._a(r.a & m[(0xA2FB+r.x)&65535])
        self._mark(0xA2FA)
        self._rts();return

    def seek_connected_reinforcements(self):
        """$A303: seek connected reinforcements; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA303)
        if not (yield from self._local_call(self.find_ruler_city,0xA303,0xA306)):return
        m[0x0045]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d03a,0xA309,0xA30C)):return
        self._y(m[RULER])
        self._a(m[(0xA3C6+r.y)&65535])
        m[0x0041]=r.a
        self._a(0x00)
        m[0x0036]=r.a
        while True:  # natural loop $A31A
            try:
                self._a(m[0x0036])
                self._compare(r.a,m[0x003A])
                self._mark(0xA320)
                if r.p&Z:
                    m[0x0036]=self._nz(m[0x0036]+1)
                    self._a(m[0x0036])
                    self._compare(r.a,0x1E)
                    self._mark(0xA363)
                    if not r.p&C:
                        continue
                    else:
                        self._y(m[RULER])
                        self._a(m[(0xA3CE+r.y)&65535])
                        m[0x0041]=r.a
                        self._a(0x00)
                        m[0x0036]=r.a
                        while True:  # natural loop $A373
                            try:
                                self._a(m[0x0036])
                                self._compare(r.a,m[0x003A])
                                self._mark(0xA379)
                                if r.p&Z:
                                    m[0x0036]=self._nz(m[0x0036]+1)
                                    self._a(m[0x0036])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xA3BF)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._a(self._pop())
                                        self._a(self._pop())
                                        return (yield from self.city_development_strategy())
                                else:
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA37B,0xA37E)):return
                                    self._compare(r.a,m[RULER])
                                    self._mark(0xA381)
                                    if not r.p&Z:
                                        m[0x0036]=self._nz(m[0x0036]+1)
                                        self._a(m[0x0036])
                                        self._compare(r.a,0x1E)
                                        self._mark(0xA3BF)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._a(self._pop())
                                            self._a(self._pop())
                                            return (yield from self.city_development_strategy())
                                    else:
                                        self._a(m[0x0036])
                                        self._compare(r.a,m[0x0045])
                                        self._mark(0xA389)
                                        if r.p&Z:
                                            self._x(m[0x003A])
                                            self._y(m[0x0036])
                                            if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                            self._compare(r.a,0xFF)
                                            self._mark(0xA39B)
                                            if not r.p&Z:
                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                self._a(m[0x0036])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xA3BF)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._a(self._pop())
                                                    self._a(self._pop())
                                                    return (yield from self.city_development_strategy())
                                            else:
                                                self._a(m[0x0036])
                                                if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                self._compare(r.a,m[0x0041])
                                                self._mark(0xA3A6)
                                                if not r.p&C:
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xA3BF)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(self._pop())
                                                        return (yield from self.city_development_strategy())
                                                else:
                                                    if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                    self._a(m[0x003A])
                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                    self._compare(r.a,m[0x0037])
                                                    self._mark(0xA3B4)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xA3B6)
                                                        self._rts();return
                                        else:
                                            if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA38B,0xA38E)):return
                                            self._mark(0xA38E)
                                            if r.p&Z:
                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                self._a(m[0x0036])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xA3BF)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._a(self._pop())
                                                    self._a(self._pop())
                                                    return (yield from self.city_development_strategy())
                                            else:
                                                self._x(m[0x003A])
                                                self._y(m[0x0036])
                                                if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                self._compare(r.a,0xFF)
                                                self._mark(0xA39B)
                                                if not r.p&Z:
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xA3BF)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(self._pop())
                                                        return (yield from self.city_development_strategy())
                                                else:
                                                    self._a(m[0x0036])
                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                    self._compare(r.a,m[0x0041])
                                                    self._mark(0xA3A6)
                                                    if not r.p&C:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                        self._a(m[0x003A])
                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                        self._compare(r.a,m[0x0037])
                                                        self._mark(0xA3B4)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._mark(0xA3B6)
                                                            self._rts();return
                            except _ContinueLoop_A373:
                                continue
                else:
                    self._compare(r.a,m[0x0045])
                    self._mark(0xA325)
                    if r.p&Z:
                        m[0x0036]=self._nz(m[0x0036]+1)
                        self._a(m[0x0036])
                        self._compare(r.a,0x1E)
                        self._mark(0xA363)
                        if not r.p&C:
                            continue
                        else:
                            self._y(m[RULER])
                            self._a(m[(0xA3CE+r.y)&65535])
                            m[0x0041]=r.a
                            self._a(0x00)
                            m[0x0036]=r.a
                            while True:  # natural loop $A373
                                try:
                                    self._a(m[0x0036])
                                    self._compare(r.a,m[0x003A])
                                    self._mark(0xA379)
                                    if r.p&Z:
                                        m[0x0036]=self._nz(m[0x0036]+1)
                                        self._a(m[0x0036])
                                        self._compare(r.a,0x1E)
                                        self._mark(0xA3BF)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._a(self._pop())
                                            self._a(self._pop())
                                            return (yield from self.city_development_strategy())
                                    else:
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA37B,0xA37E)):return
                                        self._compare(r.a,m[RULER])
                                        self._mark(0xA381)
                                        if not r.p&Z:
                                            m[0x0036]=self._nz(m[0x0036]+1)
                                            self._a(m[0x0036])
                                            self._compare(r.a,0x1E)
                                            self._mark(0xA3BF)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._a(self._pop())
                                                self._a(self._pop())
                                                return (yield from self.city_development_strategy())
                                        else:
                                            self._a(m[0x0036])
                                            self._compare(r.a,m[0x0045])
                                            self._mark(0xA389)
                                            if r.p&Z:
                                                self._x(m[0x003A])
                                                self._y(m[0x0036])
                                                if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                self._compare(r.a,0xFF)
                                                self._mark(0xA39B)
                                                if not r.p&Z:
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xA3BF)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(self._pop())
                                                        return (yield from self.city_development_strategy())
                                                else:
                                                    self._a(m[0x0036])
                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                    self._compare(r.a,m[0x0041])
                                                    self._mark(0xA3A6)
                                                    if not r.p&C:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                        self._a(m[0x003A])
                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                        self._compare(r.a,m[0x0037])
                                                        self._mark(0xA3B4)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._mark(0xA3B6)
                                                            self._rts();return
                                            else:
                                                if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA38B,0xA38E)):return
                                                self._mark(0xA38E)
                                                if r.p&Z:
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xA3BF)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(self._pop())
                                                        return (yield from self.city_development_strategy())
                                                else:
                                                    self._x(m[0x003A])
                                                    self._y(m[0x0036])
                                                    if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                    self._compare(r.a,0xFF)
                                                    self._mark(0xA39B)
                                                    if not r.p&Z:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        self._a(m[0x0036])
                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                        self._compare(r.a,m[0x0041])
                                                        self._mark(0xA3A6)
                                                        if not r.p&C:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xA3BF)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._a(self._pop())
                                                                self._a(self._pop())
                                                                return (yield from self.city_development_strategy())
                                                        else:
                                                            if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                            self._a(m[0x003A])
                                                            if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                            self._compare(r.a,m[0x0037])
                                                            self._mark(0xA3B4)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._mark(0xA3B6)
                                                                self._rts();return
                                except _ContinueLoop_A373:
                                    continue
                    else:
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA327,0xA32A)):return
                        self._compare(r.a,m[RULER])
                        self._mark(0xA32D)
                        if not r.p&Z:
                            m[0x0036]=self._nz(m[0x0036]+1)
                            self._a(m[0x0036])
                            self._compare(r.a,0x1E)
                            self._mark(0xA363)
                            if not r.p&C:
                                continue
                            else:
                                self._y(m[RULER])
                                self._a(m[(0xA3CE+r.y)&65535])
                                m[0x0041]=r.a
                                self._a(0x00)
                                m[0x0036]=r.a
                                while True:  # natural loop $A373
                                    try:
                                        self._a(m[0x0036])
                                        self._compare(r.a,m[0x003A])
                                        self._mark(0xA379)
                                        if r.p&Z:
                                            m[0x0036]=self._nz(m[0x0036]+1)
                                            self._a(m[0x0036])
                                            self._compare(r.a,0x1E)
                                            self._mark(0xA3BF)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._a(self._pop())
                                                self._a(self._pop())
                                                return (yield from self.city_development_strategy())
                                        else:
                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA37B,0xA37E)):return
                                            self._compare(r.a,m[RULER])
                                            self._mark(0xA381)
                                            if not r.p&Z:
                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                self._a(m[0x0036])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xA3BF)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._a(self._pop())
                                                    self._a(self._pop())
                                                    return (yield from self.city_development_strategy())
                                            else:
                                                self._a(m[0x0036])
                                                self._compare(r.a,m[0x0045])
                                                self._mark(0xA389)
                                                if r.p&Z:
                                                    self._x(m[0x003A])
                                                    self._y(m[0x0036])
                                                    if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                    self._compare(r.a,0xFF)
                                                    self._mark(0xA39B)
                                                    if not r.p&Z:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        self._a(m[0x0036])
                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                        self._compare(r.a,m[0x0041])
                                                        self._mark(0xA3A6)
                                                        if not r.p&C:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xA3BF)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._a(self._pop())
                                                                self._a(self._pop())
                                                                return (yield from self.city_development_strategy())
                                                        else:
                                                            if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                            self._a(m[0x003A])
                                                            if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                            self._compare(r.a,m[0x0037])
                                                            self._mark(0xA3B4)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._mark(0xA3B6)
                                                                self._rts();return
                                                else:
                                                    if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA38B,0xA38E)):return
                                                    self._mark(0xA38E)
                                                    if r.p&Z:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        self._x(m[0x003A])
                                                        self._y(m[0x0036])
                                                        if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                        self._compare(r.a,0xFF)
                                                        self._mark(0xA39B)
                                                        if not r.p&Z:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xA3BF)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._a(self._pop())
                                                                self._a(self._pop())
                                                                return (yield from self.city_development_strategy())
                                                        else:
                                                            self._a(m[0x0036])
                                                            if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                            self._compare(r.a,m[0x0041])
                                                            self._mark(0xA3A6)
                                                            if not r.p&C:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xA3BF)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._a(self._pop())
                                                                    self._a(self._pop())
                                                                    return (yield from self.city_development_strategy())
                                                            else:
                                                                if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                self._a(m[0x003A])
                                                                if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                self._compare(r.a,m[0x0037])
                                                                self._mark(0xA3B4)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._mark(0xA3B6)
                                                                    self._rts();return
                                    except _ContinueLoop_A373:
                                        continue
                        else:
                            if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA32F,0xA332)):return
                            self._mark(0xA332)
                            if not r.p&Z:
                                m[0x0036]=self._nz(m[0x0036]+1)
                                self._a(m[0x0036])
                                self._compare(r.a,0x1E)
                                self._mark(0xA363)
                                if not r.p&C:
                                    continue
                                else:
                                    self._y(m[RULER])
                                    self._a(m[(0xA3CE+r.y)&65535])
                                    m[0x0041]=r.a
                                    self._a(0x00)
                                    m[0x0036]=r.a
                                    while True:  # natural loop $A373
                                        try:
                                            self._a(m[0x0036])
                                            self._compare(r.a,m[0x003A])
                                            self._mark(0xA379)
                                            if r.p&Z:
                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                self._a(m[0x0036])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xA3BF)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._a(self._pop())
                                                    self._a(self._pop())
                                                    return (yield from self.city_development_strategy())
                                            else:
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA37B,0xA37E)):return
                                                self._compare(r.a,m[RULER])
                                                self._mark(0xA381)
                                                if not r.p&Z:
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xA3BF)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(self._pop())
                                                        return (yield from self.city_development_strategy())
                                                else:
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,m[0x0045])
                                                    self._mark(0xA389)
                                                    if r.p&Z:
                                                        self._x(m[0x003A])
                                                        self._y(m[0x0036])
                                                        if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                        self._compare(r.a,0xFF)
                                                        self._mark(0xA39B)
                                                        if not r.p&Z:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xA3BF)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._a(self._pop())
                                                                self._a(self._pop())
                                                                return (yield from self.city_development_strategy())
                                                        else:
                                                            self._a(m[0x0036])
                                                            if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                            self._compare(r.a,m[0x0041])
                                                            self._mark(0xA3A6)
                                                            if not r.p&C:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xA3BF)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._a(self._pop())
                                                                    self._a(self._pop())
                                                                    return (yield from self.city_development_strategy())
                                                            else:
                                                                if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                self._a(m[0x003A])
                                                                if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                self._compare(r.a,m[0x0037])
                                                                self._mark(0xA3B4)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._mark(0xA3B6)
                                                                    self._rts();return
                                                    else:
                                                        if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA38B,0xA38E)):return
                                                        self._mark(0xA38E)
                                                        if r.p&Z:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xA3BF)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._a(self._pop())
                                                                self._a(self._pop())
                                                                return (yield from self.city_development_strategy())
                                                        else:
                                                            self._x(m[0x003A])
                                                            self._y(m[0x0036])
                                                            if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                            self._compare(r.a,0xFF)
                                                            self._mark(0xA39B)
                                                            if not r.p&Z:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xA3BF)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._a(self._pop())
                                                                    self._a(self._pop())
                                                                    return (yield from self.city_development_strategy())
                                                            else:
                                                                self._a(m[0x0036])
                                                                if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                                self._compare(r.a,m[0x0041])
                                                                self._mark(0xA3A6)
                                                                if not r.p&C:
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1E)
                                                                    self._mark(0xA3BF)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._a(self._pop())
                                                                        self._a(self._pop())
                                                                        return (yield from self.city_development_strategy())
                                                                else:
                                                                    if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                    self._a(m[0x003A])
                                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                    self._compare(r.a,m[0x0037])
                                                                    self._mark(0xA3B4)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._mark(0xA3B6)
                                                                        self._rts();return
                                        except _ContinueLoop_A373:
                                            continue
                            else:
                                self._x(m[0x003A])
                                self._y(m[0x0036])
                                if not (yield from self._local_call(self.common_connectivity_bits,0xA33A,0xA33D)):return
                                self._compare(r.a,0xFF)
                                self._mark(0xA33F)
                                if not r.p&Z:
                                    m[0x0036]=self._nz(m[0x0036]+1)
                                    self._a(m[0x0036])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xA363)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._y(m[RULER])
                                        self._a(m[(0xA3CE+r.y)&65535])
                                        m[0x0041]=r.a
                                        self._a(0x00)
                                        m[0x0036]=r.a
                                        while True:  # natural loop $A373
                                            try:
                                                self._a(m[0x0036])
                                                self._compare(r.a,m[0x003A])
                                                self._mark(0xA379)
                                                if r.p&Z:
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xA3BF)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(self._pop())
                                                        self._a(self._pop())
                                                        return (yield from self.city_development_strategy())
                                                else:
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA37B,0xA37E)):return
                                                    self._compare(r.a,m[RULER])
                                                    self._mark(0xA381)
                                                    if not r.p&Z:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,m[0x0045])
                                                        self._mark(0xA389)
                                                        if r.p&Z:
                                                            self._x(m[0x003A])
                                                            self._y(m[0x0036])
                                                            if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                            self._compare(r.a,0xFF)
                                                            self._mark(0xA39B)
                                                            if not r.p&Z:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xA3BF)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._a(self._pop())
                                                                    self._a(self._pop())
                                                                    return (yield from self.city_development_strategy())
                                                            else:
                                                                self._a(m[0x0036])
                                                                if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                                self._compare(r.a,m[0x0041])
                                                                self._mark(0xA3A6)
                                                                if not r.p&C:
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1E)
                                                                    self._mark(0xA3BF)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._a(self._pop())
                                                                        self._a(self._pop())
                                                                        return (yield from self.city_development_strategy())
                                                                else:
                                                                    if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                    self._a(m[0x003A])
                                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                    self._compare(r.a,m[0x0037])
                                                                    self._mark(0xA3B4)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._mark(0xA3B6)
                                                                        self._rts();return
                                                        else:
                                                            if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA38B,0xA38E)):return
                                                            self._mark(0xA38E)
                                                            if r.p&Z:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xA3BF)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._a(self._pop())
                                                                    self._a(self._pop())
                                                                    return (yield from self.city_development_strategy())
                                                            else:
                                                                self._x(m[0x003A])
                                                                self._y(m[0x0036])
                                                                if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                                self._compare(r.a,0xFF)
                                                                self._mark(0xA39B)
                                                                if not r.p&Z:
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1E)
                                                                    self._mark(0xA3BF)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._a(self._pop())
                                                                        self._a(self._pop())
                                                                        return (yield from self.city_development_strategy())
                                                                else:
                                                                    self._a(m[0x0036])
                                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                                    self._compare(r.a,m[0x0041])
                                                                    self._mark(0xA3A6)
                                                                    if not r.p&C:
                                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                                        self._a(m[0x0036])
                                                                        self._compare(r.a,0x1E)
                                                                        self._mark(0xA3BF)
                                                                        if not r.p&C:
                                                                            continue
                                                                        else:
                                                                            self._a(self._pop())
                                                                            self._a(self._pop())
                                                                            return (yield from self.city_development_strategy())
                                                                    else:
                                                                        if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                        self._a(m[0x003A])
                                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                        self._compare(r.a,m[0x0037])
                                                                        self._mark(0xA3B4)
                                                                        if not r.p&C:
                                                                            continue
                                                                        else:
                                                                            self._mark(0xA3B6)
                                                                            self._rts();return
                                            except _ContinueLoop_A373:
                                                continue
                                else:
                                    self._a(m[0x0036])
                                    if not (yield from self._local_call(self.count_prefix_officers,0xA344,0xA347)):return
                                    self._compare(r.a,m[0x0041])
                                    self._mark(0xA34A)
                                    if not r.p&C:
                                        m[0x0036]=self._nz(m[0x0036]+1)
                                        self._a(m[0x0036])
                                        self._compare(r.a,0x1E)
                                        self._mark(0xA363)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._y(m[RULER])
                                            self._a(m[(0xA3CE+r.y)&65535])
                                            m[0x0041]=r.a
                                            self._a(0x00)
                                            m[0x0036]=r.a
                                            while True:  # natural loop $A373
                                                try:
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,m[0x003A])
                                                    self._mark(0xA379)
                                                    if r.p&Z:
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xA3BF)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(self._pop())
                                                            self._a(self._pop())
                                                            return (yield from self.city_development_strategy())
                                                    else:
                                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA37B,0xA37E)):return
                                                        self._compare(r.a,m[RULER])
                                                        self._mark(0xA381)
                                                        if not r.p&Z:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xA3BF)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._a(self._pop())
                                                                self._a(self._pop())
                                                                return (yield from self.city_development_strategy())
                                                        else:
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,m[0x0045])
                                                            self._mark(0xA389)
                                                            if r.p&Z:
                                                                self._x(m[0x003A])
                                                                self._y(m[0x0036])
                                                                if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                                self._compare(r.a,0xFF)
                                                                self._mark(0xA39B)
                                                                if not r.p&Z:
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1E)
                                                                    self._mark(0xA3BF)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._a(self._pop())
                                                                        self._a(self._pop())
                                                                        return (yield from self.city_development_strategy())
                                                                else:
                                                                    self._a(m[0x0036])
                                                                    if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                                    self._compare(r.a,m[0x0041])
                                                                    self._mark(0xA3A6)
                                                                    if not r.p&C:
                                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                                        self._a(m[0x0036])
                                                                        self._compare(r.a,0x1E)
                                                                        self._mark(0xA3BF)
                                                                        if not r.p&C:
                                                                            continue
                                                                        else:
                                                                            self._a(self._pop())
                                                                            self._a(self._pop())
                                                                            return (yield from self.city_development_strategy())
                                                                    else:
                                                                        if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                        self._a(m[0x003A])
                                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                        self._compare(r.a,m[0x0037])
                                                                        self._mark(0xA3B4)
                                                                        if not r.p&C:
                                                                            continue
                                                                        else:
                                                                            self._mark(0xA3B6)
                                                                            self._rts();return
                                                            else:
                                                                if not (yield from self._local_call(self.build_enemy_neighbor_list,0xA38B,0xA38E)):return
                                                                self._mark(0xA38E)
                                                                if r.p&Z:
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1E)
                                                                    self._mark(0xA3BF)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._a(self._pop())
                                                                        self._a(self._pop())
                                                                        return (yield from self.city_development_strategy())
                                                                else:
                                                                    self._x(m[0x003A])
                                                                    self._y(m[0x0036])
                                                                    if not (yield from self._local_call(self.common_connectivity_bits,0xA396,0xA399)):return
                                                                    self._compare(r.a,0xFF)
                                                                    self._mark(0xA39B)
                                                                    if not r.p&Z:
                                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                                        self._a(m[0x0036])
                                                                        self._compare(r.a,0x1E)
                                                                        self._mark(0xA3BF)
                                                                        if not r.p&C:
                                                                            continue
                                                                        else:
                                                                            self._a(self._pop())
                                                                            self._a(self._pop())
                                                                            return (yield from self.city_development_strategy())
                                                                    else:
                                                                        self._a(m[0x0036])
                                                                        if not (yield from self._local_call(self.count_prefix_officers,0xA3A0,0xA3A3)):return
                                                                        self._compare(r.a,m[0x0041])
                                                                        self._mark(0xA3A6)
                                                                        if not r.p&C:
                                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                                            self._a(m[0x0036])
                                                                            self._compare(r.a,0x1E)
                                                                            self._mark(0xA3BF)
                                                                            if not r.p&C:
                                                                                continue
                                                                            else:
                                                                                self._a(self._pop())
                                                                                self._a(self._pop())
                                                                                return (yield from self.city_development_strategy())
                                                                        else:
                                                                            if not (yield from self._local_call(self.select_reinforcement_officer,0xA3A8,0xA3AB)):return
                                                                            self._a(m[0x003A])
                                                                            if not (yield from self._local_call(self.count_prefix_officers,0xA3AE,0xA3B1)):return
                                                                            self._compare(r.a,m[0x0037])
                                                                            self._mark(0xA3B4)
                                                                            if not r.p&C:
                                                                                continue
                                                                            else:
                                                                                self._mark(0xA3B6)
                                                                                self._rts();return
                                                except _ContinueLoop_A373:
                                                    continue
                                    else:
                                        if not (yield from self._local_call(self.select_reinforcement_officer,0xA34C,0xA34F)):return
                                        self._a(m[0x003A])
                                        if not (yield from self._local_call(self.count_prefix_officers,0xA352,0xA355)):return
                                        self._compare(r.a,m[0x0037])
                                        self._mark(0xA358)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._mark(0xA35A)
                                            self._rts();return
            except _ContinueLoop_A31A:
                continue

    def select_reinforcement_officer(self):
        """$A3D6: select reinforcement officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3D6)
        self._a(m[0x0036])
        m[0x003B]=r.a
        self._a(m[0x003B])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA3DF,0xA3E2)):return
        self._a(m[RULER])
        if not (yield from self._local_call(self.ruler_pointer,0xA3E5,0xA3E8)):return
        self._y(0x00)
        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
        m[0x0027]=r.a
        self._a(0x11)
        m[0x0024]=r.a
        self._a(0x00)
        m[0x0025]=r.a
        m[0x0026]=r.a
        while True:  # natural loop $A3F8
            try:
                self._y(m[0x0024])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA3FE)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,m[0x0027])
                    self._mark(0xA402)
                    if r.p&Z:
                        pass
                    else:
                        self._x(m[0x0044])
                        self._mark(0xA407)
                        if r.p&Z:
                            self._y(0x01)
                            if not (yield from self._local_call(self.officer_field_pointer,0xA416,0xA419)):return
                            self._compare(r.a,m[0x0025])
                            self._mark(0xA41B)
                            if not r.p&C:
                                pass
                            else:
                                m[0x0025]=r.a
                                self._y(m[0x0024])
                                m[0x0026]=r.y
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                m[0x003C]=r.a
                                pass
                            pass
                        else:
                            self._x(m[0x0024])
                            self._compare(r.x,0x11)
                            self._mark(0xA40D)
                            if r.p&Z:
                                pass
                            else:
                                self._y(0x03)
                                if not (yield from self._local_call(self.officer_field_pointer,0xA416,0xA419)):return
                                self._compare(r.a,m[0x0025])
                                self._mark(0xA41B)
                                if not r.p&C:
                                    pass
                                else:
                                    m[0x0025]=r.a
                                    self._y(m[0x0024])
                                    m[0x0026]=r.y
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[0x003C]=r.a
                                    pass
                                pass
                            pass
                        pass
                    pass
                m[0x0024]=self._nz(m[0x0024]+1)
                self._a(m[0x0024])
                self._compare(r.a,0x1B)
                self._mark(0xA42E)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(m[0x0026])
                self._a(0xFF)
                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                self._a(m[0x003B])
                if not (yield from self._local_call(self.compact_city_roster,0xA439,0xA43C)):return
                self._a(m[0x003A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA43F,0xA442)):return
                self._y(0x10)
                while True:  # natural loop $A444
                    try:
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xA449)
                        if not r.p&Z:
                            continue
                        else:
                            pass
                        self._a(m[0x003C])
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._a(0x02)
                        if not (yield from self._local_call(self.charge_nested_budget_one,0xA452,0xA455)):return
                        self._a(m[0x003B])
                        m[0x0036]=r.a
                        self._mark(0xA45B)
                        self._rts();return
                    except _ContinueLoop_A444:
                        continue
            except _ContinueLoop_A3F8:
                continue

    def prepare_attack_troops(self):
        """$A45C: prepare attack troops; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA45C)
        self._a(0x11)
        m[0x003C]=r.a
        while True:  # natural loop $A461
            try:
                self._a(m[0x003A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA464,0xA467)):return
                self._y(m[0x003C])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA46E)
                if r.p&Z:
                    pass
                else:
                    m[0x003B]=r.a
                    if not (yield from self._local_call(self.fill_officer_troops,0xA473,0xA476)):return
                    pass
                m[0x003C]=self._nz(m[0x003C]+1)
                self._a(m[0x003C])
                self._compare(r.a,0x1B)
                self._mark(0xA47E)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xA480)
                self._rts();return
            except _ContinueLoop_A461:
                continue

    def fill_officer_troops(self):
        """$A481: fill officer troops; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $A481
            try:
                self._mark(0xA481)
                self._a(m[0x003A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA484,0xA487)):return
                self._a(m[0x003B])
                self._y(0x08)
                if not (yield from self._local_call(self.officer_field_pointer,0xA48C,0xA48F)):return
                m[0x002A]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                self._a(r.a & 0x03)
                m[0x002B]=r.a
                self._a(0xE8)
                self._flag(C,True)
                self._add(m[0x002A],subtract=True)
                m[0x0040]=r.a
                m[0x002C]=r.a
                self._a(0x03)
                self._add(m[0x002B],subtract=True)
                m[0x0041]=r.a
                m[0x002D]=r.a
                self._a(m[0x002C])
                self._a(r.a | m[0x002D])
                self._mark(0xA4AF)
                if not r.p&Z:
                    self._y(0x0C)
                    self._a(m[0x0040])
                    self._flag(C,True)
                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                    m[0x0042]=r.a
                    self._y(r.y+1)
                    self._a(m[0x0041])
                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                    m[0x0043]=r.a
                    self._mark(0xA4C6)
                    if not r.p&C:
                        self._y(0x0C)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(m[0x0040],subtract=True)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._add(m[0x0041],subtract=True)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        if not (yield from self._local_call(self.cap_city_word,0xA540,0xA543)):return
                        self._a(m[0x003B])
                        self._y(0x08)
                        if not (yield from self._local_call(self.officer_field_pointer,0xA548,0xA54B)):return
                        self._y(0x08)
                        self._a(0xE8)
                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._a(0x03)
                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                        self._a(0x02)
                        if not (yield from self._local_call(self.charge_nested_budget_one,0xA558,0xA55B)):return
                        self._mark(0xA55B)
                        self._rts();return
                    else:
                        self._y(0x00)
                        m[0x0028]=r.y
                        m[0x0029]=r.y
                        while True:  # natural loop $A4CE
                            try:
                                self._a(r.y)
                                self._flag(C,False)
                                self._add(0x14)
                                self._y(r.a)
                                self._a(m[0x0028])
                                self._flag(C,False)
                                self._add(0x64)
                                m[0x0028]=r.a
                                self._a(m[0x0029])
                                self._add(0x00)
                                m[0x0029]=r.a
                                self._a(m[0x0042])
                                self._flag(C,True)
                                self._add(0x64,subtract=True)
                                m[0x0042]=r.a
                                self._a(m[0x0043])
                                self._add(0x00,subtract=True)
                                m[0x0043]=r.a
                                self._mark(0xA4F1)
                                if r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(r.y)
                                m[0x0022]=r.a
                                self._a(0x00)
                                m[0x0023]=r.a
                                self._a(0x00)
                                m[0x0024]=r.a
                                self._a(m[0x003A])
                                if not (yield from self._local_call(self.pay_city_gold,0xA501,0xA504)):return
                                self._mark(0xA504)
                                if r.p&C:
                                    self._a(m[0x003A])
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA518,0xA51B)):return
                                    self._y(0x0C)
                                    self._a(m[0x0028])
                                    self._flag(C,False)
                                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._a(m[0x0029])
                                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    if not (yield from self._local_call(self.cap_city_word,0xA52B,0xA52E)):return
                                    self._y(0x0C)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(m[0x0040],subtract=True)
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._add(m[0x0041],subtract=True)
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    if not (yield from self._local_call(self.cap_city_word,0xA540,0xA543)):return
                                    self._a(m[0x003B])
                                    self._y(0x08)
                                    if not (yield from self._local_call(self.officer_field_pointer,0xA548,0xA54B)):return
                                    self._y(0x08)
                                    self._a(0xE8)
                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._a(0x03)
                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                    self._a(0x02)
                                    if not (yield from self._local_call(self.charge_nested_budget_one,0xA558,0xA55B)):return
                                    self._mark(0xA55B)
                                    self._rts();return
                                else:
                                    if not (yield from self._local_call(self.transfer_attack_gold,0xA506,0xA509)):return
                                    self._mark(0xA509)
                                    if r.p&C:
                                        raise _ContinueLoop_A481
                                    else:
                                        self._a(self._pop())
                                        self._a(self._pop())
                                        self._a(self._pop())
                                        self._a(self._pop())
                                        return (yield from self.city_development_strategy())
                            except _ContinueLoop_A4CE:
                                continue
                else:
                    self._mark(0xA4B1)
                    self._rts();return
            except _ContinueLoop_A481:
                continue

    def transfer_attack_gold(self):
        """$A55C: transfer attack gold; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA55C)
        if not (yield from self._local_call(self.find_ruler_city,0xA55C,0xA55F)):return
        m[0x0045]=r.a
        self._a(0x00)
        m[0x0036]=r.a
        m[0x002C]=r.a
        self._a(0x64)
        m[0x002B]=r.a
        self._a(0xFF)
        m[0x002A]=r.a
        while True:  # natural loop $A571
            try:
                self._a(m[0x0036])
                self._compare(r.a,m[0x003A])
                self._mark(0xA577)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA579,0xA57C)):return
                    self._compare(r.a,m[RULER])
                    self._mark(0xA57F)
                    if not r.p&Z:
                        pass
                    else:
                        self._y(0x02)
                        self._a(m[0x002B])
                        self._flag(C,True)
                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                        self._y(r.y+1)
                        self._a(m[0x002C])
                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                        self._mark(0xA58D)
                        if r.p&C:
                            pass
                        else:
                            self._y(0x02)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            m[0x002B]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            m[0x002C]=r.a
                            self._a(m[0x0036])
                            m[0x002A]=r.a
                            pass
                        pass
                    pass
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xA5A7)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x002A])
                self._compare(r.a,0xFF)
                self._mark(0xA5AD)
                if not r.p&Z:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA5B1,0xA5B4)):return
                    self._y(0x03)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._mark(0xA5B8)
                    if not r.p&Z:
                        self._y(0x02)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x64,subtract=True)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._add(0x00,subtract=True)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._a(0x64)
                        m[0x002B]=r.a
                        pass
                    else:
                        self._y(0x02)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,0xC8)
                        self._mark(0xA5C0)
                        if r.p&C:
                            self._y(0x02)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x64,subtract=True)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._add(0x00,subtract=True)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._a(0x64)
                            m[0x002B]=r.a
                            pass
                        else:
                            self._flag(C,True)
                            self._add(0x64,subtract=True)
                            m[0x002B]=r.a
                            self._y(0x02)
                            self._a(0x64)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._a(0x00)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            pass
                        pass
                    if not (yield from self._local_call(self.cap_city_word,0xA5E9,0xA5EC)):return
                    self._a(m[0x003A])
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA5EF,0xA5F2)):return
                    self._y(0x02)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x002B])
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._add(0x00)
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    if not (yield from self._local_call(self.cap_city_word,0xA602,0xA605)):return
                    self._a(0x02)
                    if not (yield from self._local_call(self.charge_nested_budget_three,0xA607,0xA60A)):return
                    self._flag(C,True)
                    self._mark(0xA60B)
                    self._rts();return
                else:
                    self._flag(C,False)
                    self._mark(0xA5B0)
                    self._rts();return
            except _ContinueLoop_A571:
                continue

    def transfer_attack_grain(self):
        """$A60C: transfer attack grain; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA60C)
        if not (yield from self._local_call(self.find_ruler_city,0xA60C,0xA60F)):return
        m[0x0045]=r.a
        self._a(0x00)
        m[0x0036]=r.a
        m[0x002C]=r.a
        self._a(0x64)
        m[0x002B]=r.a
        self._a(0xFF)
        m[0x002A]=r.a
        while True:  # natural loop $A621
            try:
                self._a(m[0x0036])
                self._compare(r.a,m[0x003A])
                self._mark(0xA627)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA629,0xA62C)):return
                    self._compare(r.a,m[RULER])
                    self._mark(0xA62F)
                    if not r.p&Z:
                        pass
                    else:
                        self._y(0x04)
                        self._a(m[0x002B])
                        self._flag(C,True)
                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                        self._y(r.y+1)
                        self._a(m[0x002C])
                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                        self._mark(0xA63D)
                        if r.p&C:
                            pass
                        else:
                            self._y(0x04)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            m[0x002B]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            m[0x002C]=r.a
                            self._a(m[0x0036])
                            m[0x002A]=r.a
                            pass
                        pass
                    pass
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xA657)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x002A])
                self._compare(r.a,0xFF)
                self._mark(0xA65D)
                if not r.p&Z:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA661,0xA664)):return
                    self._y(0x05)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._mark(0xA668)
                    if not r.p&Z:
                        self._y(0x04)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x64,subtract=True)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._add(0x00,subtract=True)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._a(0x64)
                        m[0x002B]=r.a
                        pass
                    else:
                        self._y(0x04)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,0xC8)
                        self._mark(0xA670)
                        if r.p&C:
                            self._y(0x04)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x64,subtract=True)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._add(0x00,subtract=True)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._a(0x64)
                            m[0x002B]=r.a
                            pass
                        else:
                            self._flag(C,True)
                            self._add(0x64,subtract=True)
                            m[0x002B]=r.a
                            self._y(0x04)
                            self._a(0x64)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._a(0x00)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            pass
                        pass
                    if not (yield from self._local_call(self.cap_city_word,0xA699,0xA69C)):return
                    self._a(m[0x003A])
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA69F,0xA6A2)):return
                    self._y(0x04)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x002B])
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._add(0x00)
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    if not (yield from self._local_call(self.cap_city_word,0xA6B2,0xA6B5)):return
                    self._a(0x02)
                    if not (yield from self._local_call(self.charge_nested_budget_three,0xA6B7,0xA6BA)):return
                    self._flag(C,True)
                    self._mark(0xA6BB)
                    self._rts();return
                else:
                    self._flag(C,False)
                    self._mark(0xA660)
                    self._rts();return
            except _ContinueLoop_A621:
                continue

    def domesticcooperationcontroller_a6bc(self):
        """$A6BC: domesticcooperationcontroller a6bc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6BC)
        if not (yield from self._local_call(self.choose_attack_officer_count,0xA6BC,0xA6BF)):return
        self._mark(0xA6BF)
        self._rts();return

    def choose_attack_officer_count(self):
        """$A6C9: choose attack officer count; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6C9)
        self._a(m[0x003A])
        if not (yield from self._local_call(self.count_prefix_officers,0xA6CC,0xA6CF)):return
        m[0x0039]=r.a
        self._a(0x01)
        m[0x0037]=r.a
        self._a(0x64)
        if not (yield from self._local_call(self.random_below,0xA6D9,0xA6DC)):return
        self._y(m[DIFFICULTY])
        self._x(0x04)
        self._compare(r.a,m[(0xA6C0+r.y)&65535])
        self._mark(0xA6E4)
        if not r.p&C:
            pass
        else:
            self._x(r.x-1)
            self._compare(r.a,m[(0xA6C3+r.y)&65535])
            self._mark(0xA6EA)
            if not r.p&C:
                pass
            else:
                self._x(r.x-1)
                self._compare(r.a,m[(0xA6C6+r.y)&65535])
                self._mark(0xA6F0)
                if not r.p&C:
                    pass
                else:
                    self._x(r.x-1)
                    pass
                pass
            pass
        m[0x0020]=r.x
        self._a(m[0x0039])
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        self._mark(0xA6FB)
        if not r.p&C:
            pass
        else:
            self._mark(0xA6FD)
            if r.p&Z:
                pass
            else:
                m[0x0037]=r.a
                pass
            pass
        if not (yield from self._local_call(self.quote_attack_supplies,0xA702,0xA705)):return
        while True:  # natural loop $A705
            try:
                self._a(m[0x003A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA708,0xA70B)):return
                self._y(0x02)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x003D],subtract=True)
                self._y(r.y+1)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._add(m[0x003E],subtract=True)
                self._mark(0xA719)
                if r.p&C:
                    while True:  # natural loop $A727
                        try:
                            self._a(m[0x003A])
                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA72A,0xA72D)):return
                            self._y(0x04)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._flag(C,True)
                            self._add(m[0x003B],subtract=True)
                            self._y(r.y+1)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._add(m[0x003C],subtract=True)
                            self._mark(0xA73B)
                            if r.p&C:
                                self._mark(0xA749)
                                self._rts();return
                            else:
                                if not (yield from self._local_call(self.transfer_attack_grain,0xA73D,0xA740)):return
                                self._mark(0xA740)
                                if r.p&C:
                                    continue
                                else:
                                    self._a(self._pop())
                                    self._a(self._pop())
                                    self._a(self._pop())
                                    self._a(self._pop())
                                    return (yield from self.city_development_strategy())
                        except _ContinueLoop_A727:
                            continue
                else:
                    if not (yield from self._local_call(self.transfer_attack_gold,0xA71B,0xA71E)):return
                    self._mark(0xA71E)
                    if r.p&C:
                        continue
                    else:
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        return (yield from self.city_development_strategy())
            except _ContinueLoop_A705:
                continue

    def quote_attack_supplies(self):
        """$A74A: quote attack supplies; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA74A)
        self._a(m[0x0037])
        m[0x0020]=r.a
        self._a(0x78)
        m[0x0021]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xA753,0xA756)):return
        self._a(m[0x002A])
        m[0x003B]=r.a
        self._a(m[0x002B])
        m[0x003C]=r.a
        self._a(m[0x0037])
        m[0x0020]=r.a
        self._a(0x64)
        m[0x0021]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xA769,0xA76C)):return
        self._a(0x64)
        if not (yield from self._local_call(self.random_below,0xA76E,0xA771)):return
        m[0x0021]=r.a
        yield from self._external(0xA773,0xE88A,0xA776,"call",None)
        if r.pc!=0xA776:return  # preserve nonlocal stack return
        self._compare(r.a,0x80)
        self._mark(0xA778)
        if not r.p&N:
            self._a(m[0x002A])
            self._flag(C,False)
            self._add(m[0x0021])
            m[0x003D]=r.a
            self._a(m[0x002B])
            self._add(0x00)
            m[0x003E]=r.a
            pass
        else:
            self._a(m[0x002A])
            self._flag(C,True)
            self._add(m[0x0021],subtract=True)
            m[0x003D]=r.a
            self._a(m[0x002B])
            self._add(0x00,subtract=True)
            m[0x003E]=r.a
            pass
        self._mark(0xA79B)
        self._rts();return

    def commit_attack_preparation(self):
        """$A79C: commit attack preparation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA79C)
        self._a(m[0x003A])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA79F,0xA7A2)):return
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x003D],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x003E],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(0x04)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x003B],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x003C],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(0x78)
        self._a(0xFF)
        while True:  # natural loop $A7CA
            try:
                m[(0x0600+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xA7CE)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(m[0x003A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA7D3,0xA7D6)):return
                self._a(0x00)
                m[0x002A]=r.a
                while True:  # natural loop $A7DA
                    try:
                        self._a(0x11)
                        m[0x002B]=r.a
                        self._a(0x00)
                        m[0x002C]=r.a
                        self._a(0xFF)
                        m[0x002D]=r.a
                        while True:  # natural loop $A7E6
                            try:
                                self._y(m[0x002B])
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xA7EC)
                                if r.p&Z:
                                    pass
                                else:
                                    self._y(0x03)
                                    if not (yield from self._local_call(self.officer_field_pointer,0xA7F0,0xA7F3)):return
                                    self._compare(r.a,0x64)
                                    self._mark(0xA7F5)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._y(0x01)
                                        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                        r.a=self._shift(r.a,False,rotate=False)
                                        self._y(0x03)
                                        self._flag(C,False)
                                        self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                        self._compare(r.a,m[0x002C])
                                        self._mark(0xA803)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[0x002C]=r.a
                                            self._a(m[0x002B])
                                            m[0x002D]=r.a
                                            pass
                                        pass
                                    pass
                                m[0x002B]=self._nz(m[0x002B]+1)
                                self._a(m[0x002B])
                                self._compare(r.a,0x1B)
                                self._mark(0xA811)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._y(m[0x002D])
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._push(r.a)
                                self._a(0xFF)
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._a(self._pop())
                                self._y(m[0x002A])
                                m[(0x066E+r.y)&65535]=r.a
                                m[0x002A]=self._nz(m[0x002A]+1)
                                self._y(m[0x002A])
                                self._compare(r.y,m[0x0037])
                                self._mark(0xA829)
                                if not r.p&C:
                                    raise _ContinueLoop_A7DA
                                else:
                                    pass
                                self._a(m[0x003A])
                                if not (yield from self._local_call(self.compact_city_roster,0xA82E,0xA831)):return
                                self._a(m[0x0038])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA834,0xA837)):return
                                self._x(0x00)
                                self._y(0x11)
                                while True:  # natural loop $A83B
                                    try:
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._compare(r.a,0xFF)
                                        self._mark(0xA83F)
                                        if r.p&Z:
                                            pass
                                        else:
                                            m[(0x0664+r.x)&65535]=r.a
                                            self._a(0xFF)
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            self._x(r.x+1)
                                            self._y(r.y+1)
                                            self._compare(r.y,0x1B)
                                            self._mark(0xA84C)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            pass
                                        self._y(0x02)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        m[0x0526]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        m[0x0527]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        m[0x0522]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        m[0x0523]=r.a
                                        self._y(0x02)
                                        self._a(0x00)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._a(m[RULER])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        m[0x0022]=r.a
                                        self._y(0x00)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._a(r.a & 0x07)
                                        self._a(r.a | m[0x0022])
                                        m[0x507]=r.a
                                        self._a(m[0x0038])
                                        m[0x50E]=r.a
                                        self._a(m[0x003A])
                                        m[0x0402]=r.a
                                        self._a(m[0x003B])
                                        m[0x0524]=r.a
                                        self._a(m[0x003C])
                                        m[0x0525]=r.a
                                        self._a(m[0x003D])
                                        m[0x0528]=r.a
                                        self._a(m[0x003E])
                                        m[0x0529]=r.a
                                        self._a(m[0x0038])
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA8B1,0xA8B4)):return
                                        if not (yield from self._local_call(self.ruler_pointer,0xA8B4,0xA8B7)):return
                                        self._y(0x03)
                                        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                        self._compare(r.a,0x03)
                                        self._mark(0xA8BD)
                                        if r.p&Z:
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_acd5,0xA8CC,0xA8CF)):return
                                            self._a(self._pop())
                                            self._a(self._pop())
                                            self._a(0xFD)
                                            m[AI_REQUEST]=r.a
                                            self._mark(0xA8D6)
                                            self._rts();return
                                        else:
                                            self._a(self._pop())
                                            self._a(self._pop())
                                            self._a(0xFE)
                                            m[AI_REQUEST]=r.a
                                            self._a(0x00)
                                            m[0x6F8D]=r.a
                                            self._mark(0xA8CB)
                                            self._rts();return
                                    except _ContinueLoop_A83B:
                                        continue
                            except _ContinueLoop_A7E6:
                                continue
                    except _ContinueLoop_A7DA:
                        continue
            except _ContinueLoop_A7CA:
                continue

    def consume_battle_return(self):
        """$A8D7: consume battle return; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8D7)
        self._a(m[0x6F8C])
        self._mark(0xA8DA)
        if not r.p&Z:
            pass
        else:
            if not (yield from self._local_call(self.domesticcooperationcontroller_cd68,0xA8DC,0xA8DF)):return
            pass
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA8E2,0xA8E5)):return
        m[0x003E]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_a91f,0xA8E8,0xA8EB)):return
        if not (yield from self._local_call(self.domesticcooperationcontroller_a9cc,0xA8EB,0xA8EE)):return
        if not (yield from self._local_call(self.domesticcooperationcontroller_af9c,0xA8EE,0xA8F1)):return
        self._a(m[0x6F8C])
        self._mark(0xA8F4)
        if not r.p&Z:
            if not (yield from self._local_call(self.domesticcooperationcontroller_ab10,0xA913,0xA916)):return
            if not (yield from self._local_call(self.domesticcooperationcontroller_ac67,0xA916,0xA919)):return
            if not (yield from self._local_call(self.find_ruler_city,0xA919,0xA91C)):return
            return (yield from self.handle_returned_leader_alternate())
        else:
            if not (yield from self._local_call(self.domesticcooperationcontroller_aa80,0xA8F6,0xA8F9)):return
            if not (yield from self._local_call(self.domesticcooperationcontroller_ac67,0xA8F9,0xA8FC)):return
            self._a(m[0x0038])
            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xA8FF,0xA902)):return
            self._y(0x00)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._a(r.a & 0xF8)
            self._a(r.a | m[RULER])
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            if not (yield from self._local_call(self.find_ruler_city,0xA90D,0xA910)):return
            return (yield from self.handle_returned_leader())

    def handle_returned_leader(self):
        """$A910: handle returned leader; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA910)
        return (yield from self.resolve_AI_leader_deaths())

    def handle_returned_leader_alternate(self):
        """$A91C: handle returned leader alternate; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA91C)
        return (yield from self.resolve_AI_leader_deaths())

    def domesticcooperationcontroller_a91f(self):
        """$A91F: domesticcooperationcontroller a91f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA91F)
        self._a(0x00)
        m[0x6F73]=r.a
        m[0x6F74]=r.a
        m[0x6F75]=r.a
        m[0x6F76]=r.a
        m[0x6F77]=r.a
        m[0x6F78]=r.a
        self._a(0x00)
        m[0x0040]=r.a
        while True:  # natural loop $A938
            try:
                self._y(m[0x0040])
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA940)
                if not r.p&Z:
                    self._push(r.a)
                    self._y(0x00)
                    if not (yield from self._local_call(self.officer_field_pointer,0xA948,0xA94B)):return
                    self._push(r.a)
                    self._y(0x08)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    m[0x0020]=r.a
                    m[0x0030]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    m[0x0021]=r.a
                    m[0x0031]=r.a
                    self._a(self._pop())
                    m[0x0023]=r.a
                    self._a(0x00)
                    m[0x0022]=r.a
                    if not (yield from self._local_call(self.multiply_domestic_word,0xA964,0xA967)):return
                    self._a(m[0x0026])
                    m[0x0020]=r.a
                    self._a(m[0x0027])
                    m[0x0021]=r.a
                    self._a(m[0x0028])
                    m[0x0022]=r.a
                    self._a(0x64)
                    m[0x0023]=r.a
                    self._a(0x00)
                    m[0x0024]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xA97B,0xA97E)):return
                    self._a(self._pop())
                    self._y(0x00)
                    if not (yield from self._local_call(self.officer_field_pointer,0xA981,0xA984)):return
                    self._y(0x08)
                    self._a(m[0x0020])
                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._a(r.a & 0xFC)
                    self._a(r.a | m[0x0021])
                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                    self._a(m[0x0030])
                    self._flag(C,True)
                    self._add(m[0x0020],subtract=True)
                    m[0x0030]=r.a
                    self._a(m[0x0031])
                    self._add(m[0x0021],subtract=True)
                    m[0x0031]=r.a
                    self._mark(0xA9A0)
                    if not r.p&C:
                        pass
                    else:
                        self._y(0x00)
                        self._a(m[0x0040])
                        self._compare(r.a,0x0A)
                        self._mark(0xA9A9)
                        if not r.p&C:
                            pass
                        else:
                            self._y(0x02)
                            pass
                        self._a(m[0x0030])
                        self._flag(C,False)
                        self._add(m[(0x6F73+r.y)&65535])
                        m[(0x6F73+r.y)&65535]=r.a
                        self._a(m[0x0031])
                        self._add(m[(0x6F74+r.y)&65535])
                        m[(0x6F74+r.y)&65535]=r.a
                        pass
                    pass
                else:
                    pass
                m[0x0040]=self._nz(m[0x0040]+1)
                self._a(m[0x0040])
                self._compare(r.a,0x14)
                self._mark(0xA9C6)
                if r.p&C:
                    pass
                else:
                    continue
                self._mark(0xA9CB)
                self._rts();return
            except _ContinueLoop_A938:
                continue

    def domesticcooperationcontroller_a9cc(self):
        """$A9CC: domesticcooperationcontroller a9cc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9CC)
        self._y(0x00)
        self._x(0x00)
        while True:  # natural loop $A9D0
            try:
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA9D5)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x0A)
                self._mark(0xA9DB)
                if not r.p&C:
                    continue
                else:
                    pass
                m[0x003C]=r.x
                self._y(0x00)
                self._x(0x00)
                while True:  # natural loop $A9E4
                    try:
                        self._a(m[(0x066E+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xA9E9)
                        if r.p&Z:
                            pass
                        else:
                            self._x(r.x+1)
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x0A)
                        self._mark(0xA9EF)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        m[0x003D]=r.x
                        self._a(m[0x003C])
                        self._compare(r.a,0x05)
                        self._mark(0xA9F9)
                        if not r.p&C:
                            pass
                        else:
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            self._compare(r.a,0x00)
                            self._mark(0xA9FF)
                            if r.p&Z:
                                pass
                            else:
                                m[0x6F77]=r.a
                                while True:  # natural loop $AA04
                                    try:
                                        self._push(r.a)
                                        self._a(0x00)
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_aa2d,0xAA07,0xAA0A)):return
                                        self._a(self._pop())
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xAA0E)
                                        if not r.p&Z:
                                            continue
                                        else:
                                            pass
                                        self._a(m[0x003D])
                                        self._compare(r.a,0x05)
                                        self._mark(0xAA15)
                                        if not r.p&C:
                                            pass
                                        else:
                                            r.a=self._shift(r.a,False,rotate=False)
                                            r.a=self._shift(r.a,False,rotate=False)
                                            self._compare(r.a,0x00)
                                            self._mark(0xAA1B)
                                            if r.p&Z:
                                                pass
                                            else:
                                                m[0x6F78]=r.a
                                                while True:  # natural loop $AA20
                                                    try:
                                                        self._push(r.a)
                                                        self._a(0x0A)
                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_aa2d,0xAA23,0xAA26)):return
                                                        self._a(self._pop())
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        self._mark(0xAA2A)
                                                        if not r.p&Z:
                                                            continue
                                                        else:
                                                            pass
                                                        self._mark(0xAA2C)
                                                        self._rts();return
                                                    except _ContinueLoop_AA20:
                                                        continue
                                            pass
                                        self._mark(0xAA2C)
                                        self._rts();return
                                    except _ContinueLoop_AA04:
                                        continue
                            pass
                        self._a(m[0x003D])
                        self._compare(r.a,0x05)
                        self._mark(0xAA15)
                        if not r.p&C:
                            pass
                        else:
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            self._compare(r.a,0x00)
                            self._mark(0xAA1B)
                            if r.p&Z:
                                pass
                            else:
                                m[0x6F78]=r.a
                                while True:  # natural loop $AA20
                                    try:
                                        self._push(r.a)
                                        self._a(0x0A)
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_aa2d,0xAA23,0xAA26)):return
                                        self._a(self._pop())
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xAA2A)
                                        if not r.p&Z:
                                            continue
                                        else:
                                            pass
                                        self._mark(0xAA2C)
                                        self._rts();return
                                    except _ContinueLoop_AA20:
                                        continue
                            pass
                        self._mark(0xAA2C)
                        self._rts();return
                    except _ContinueLoop_A9E4:
                        continue
            except _ContinueLoop_A9D0:
                continue

    def domesticcooperationcontroller_aa2d(self):
        """$AA2D: domesticcooperationcontroller aa2d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA2D)
        m[0x0024]=r.a
        self._a(0xFF)
        m[0x0025]=r.a
        m[0x0026]=r.a
        self._a(0x00)
        m[0x0027]=r.a
        while True:  # natural loop $AA39
            try:
                self._y(m[0x0024])
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAA40)
                if r.p&Z:
                    pass
                else:
                    self._y(0x03)
                    if not (yield from self._local_call(self.officer_field_pointer,0xAA44,0xAA47)):return
                    self._compare(r.a,0x64)
                    self._mark(0xAA49)
                    if r.p&Z:
                        pass
                    else:
                        self._y(0x01)
                        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                        self._y(0x02)
                        self._flag(C,False)
                        self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x0025])
                        self._mark(0xAA56)
                        if r.p&C:
                            pass
                        else:
                            m[0x0025]=r.a
                            self._a(m[0x0024])
                            m[0x0026]=r.a
                            pass
                        pass
                    pass
                m[0x0024]=self._nz(m[0x0024]+1)
                m[0x0027]=self._nz(m[0x0027]+1)
                self._a(m[0x0027])
                self._compare(r.a,0x0A)
                self._mark(0xAA66)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(m[0x0026])
                self._a(m[(0x0664+r.y)&65535])
                self._push(r.a)
                self._a(0xFF)
                m[(0x0664+r.y)&65535]=r.a
                self._a(self._pop())
                self._y(0x0B)
                if not (yield from self._local_call(self.officer_field_pointer,0xAA76,0xAA79)):return
                self._a(r.a & 0xFC)
                self._a(r.a | 0x03)
                m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                self._mark(0xAA7F)
                self._rts();return
            except _ContinueLoop_AA39:
                continue

    def domesticcooperationcontroller_aa80(self):
        """$AA80: domesticcooperationcontroller aa80; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA80)
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xAA83,0xAA86)):return
        self._x(0x00)
        self._y(0x11)
        while True:  # natural loop $AA8A
            try:
                self._a(m[(0x066E+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAA8F)
                if r.p&Z:
                    pass
                else:
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    pass
                self._x(r.x+1)
                self._compare(r.x,0x0A)
                self._mark(0xAA97)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x00)
                m[0x0024]=r.y
                while True:  # natural loop $AA9D
                    try:
                        self._y(m[0x0024])
                        self._a(m[(0x0664+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xAAA4)
                        if r.p&Z:
                            pass
                        else:
                            m[0x0026]=r.a
                            self._y(0x03)
                            if not (yield from self._local_call(self.officer_field_pointer,0xAAAA,0xAAAD)):return
                            self._compare(r.a,0x64)
                            self._mark(0xAAAF)
                            if r.p&Z:
                                self._a(m[0x003E])
                                m[0x0040]=r.a
                                self._a(m[0x0026])
                                m[0x0041]=r.a
                                self._a(0x01)
                                m[0x0042]=r.a
                                if not (yield from self._local_call(self.domesticcooperationcontroller_aba3,0xAAD2,0xAAD5)):return
                                pass
                            else:
                                m[0x0025]=r.a
                                self._a(0x64)
                                if not (yield from self._local_call(self.random_below,0xAAB5,0xAAB8)):return
                                self._compare(r.a,m[0x0025])
                                self._mark(0xAABA)
                                if not r.p&C:
                                    self._a(m[0x003E])
                                    m[0x0040]=r.a
                                    self._a(m[0x0026])
                                    m[0x0041]=r.a
                                    self._a(0x01)
                                    m[0x0042]=r.a
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_aba3,0xAAD2,0xAAD5)):return
                                    pass
                                else:
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_aade,0xAABC,0xAABF)):return
                                    pass
                                pass
                            pass
                        m[0x0024]=self._nz(m[0x0024]+1)
                        self._a(m[0x0024])
                        self._compare(r.a,0x0A)
                        self._mark(0xAADB)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._mark(0xAADD)
                        self._rts();return
                    except _ContinueLoop_AA9D:
                        continue
            except _ContinueLoop_AA8A:
                continue

    def domesticcooperationcontroller_aade(self):
        """$AADE: domesticcooperationcontroller aade; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAADE)
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xAAE1,0xAAE4)):return
        self._y(0x11)
        while True:  # natural loop $AAE6
            try:
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAAEA)
                if r.p&Z:
                    self._a(m[0x0026])
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    self._a(m[0x0026])
                    m[0x0020]=r.a
                    return (yield from self.adjust_commander_loyalty())
                else:
                    self._y(r.y+1)
                    self._compare(r.y,0x1B)
                    self._mark(0xAAEF)
                    if not r.p&C:
                        continue
                    else:
                        self._a(m[RULER])
                        m[0x0040]=r.a
                        self._a(m[0x0026])
                        m[0x0041]=r.a
                        self._a(0x00)
                        m[0x0042]=r.a
                        return (yield from self.domesticcooperationcontroller_aba3())
            except _ContinueLoop_AAE6:
                continue

    def adjust_commander_loyalty(self):
        """$AB0C: adjust commander loyalty; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB0C)
        if not (yield from self._local_call(self.recalculate_shifted_loyalty,0xAB0C,0xAB0F)):return
        self._mark(0xAB0F)
        self._rts();return

    def domesticcooperationcontroller_ab10(self):
        """$AB10: domesticcooperationcontroller ab10; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB10)
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xAB13,0xAB16)):return
        self._x(0x00)
        self._y(0x11)
        while True:  # natural loop $AB1A
            try:
                self._a(m[(0x0664+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAB1F)
                if r.p&Z:
                    pass
                else:
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    pass
                self._x(r.x+1)
                self._compare(r.x,0x0A)
                self._mark(0xAB27)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x00)
                m[0x0024]=r.y
                while True:  # natural loop $AB2D
                    try:
                        self._y(m[0x0024])
                        self._a(m[(0x066E+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xAB34)
                        if r.p&Z:
                            pass
                        else:
                            m[0x0026]=r.a
                            self._push(r.a)
                            self._a(0xFF)
                            m[(0x066E+r.y)&65535]=r.a
                            self._a(self._pop())
                            self._y(0x03)
                            if not (yield from self._local_call(self.officer_field_pointer,0xAB41,0xAB44)):return
                            m[0x0025]=r.a
                            self._a(0x64)
                            if not (yield from self._local_call(self.random_below,0xAB48,0xAB4B)):return
                            self._compare(r.a,m[0x0025])
                            self._mark(0xAB4D)
                            if not r.p&C:
                                self._a(m[RULER])
                                m[0x0040]=r.a
                                self._a(m[0x0026])
                                m[0x0041]=r.a
                                self._a(0x01)
                                m[0x0042]=r.a
                                if not (yield from self._local_call(self.domesticcooperationcontroller_aba3,0xAB65,0xAB68)):return
                                pass
                            else:
                                if not (yield from self._local_call(self.domesticcooperationcontroller_ab71,0xAB4F,0xAB52)):return
                                pass
                            pass
                        m[0x0024]=self._nz(m[0x0024]+1)
                        self._a(m[0x0024])
                        self._compare(r.a,0x0A)
                        self._mark(0xAB6E)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._mark(0xAB70)
                        self._rts();return
                    except _ContinueLoop_AB2D:
                        continue
            except _ContinueLoop_AB1A:
                continue

    def domesticcooperationcontroller_ab71(self):
        """$AB71: domesticcooperationcontroller ab71; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB71)
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xAB74,0xAB77)):return
        self._y(0x11)
        while True:  # natural loop $AB79
            try:
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAB7D)
                if r.p&Z:
                    self._a(m[0x0026])
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    self._a(m[0x0026])
                    m[0x0020]=r.a
                    return (yield from self.adjust_roster_loyalty())
                else:
                    self._y(r.y+1)
                    self._compare(r.y,0x1B)
                    self._mark(0xAB82)
                    if not r.p&C:
                        continue
                    else:
                        self._a(m[0x003E])
                        m[0x0040]=r.a
                        self._a(m[0x0026])
                        m[0x0041]=r.a
                        self._a(0x00)
                        m[0x0042]=r.a
                        return (yield from self.domesticcooperationcontroller_aba3())
            except _ContinueLoop_AB79:
                continue

    def adjust_roster_loyalty(self):
        """$AB9F: adjust roster loyalty; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB9F)
        if not (yield from self._local_call(self.recalculate_shifted_loyalty,0xAB9F,0xABA2)):return
        self._mark(0xABA2)
        self._rts();return

    def domesticcooperationcontroller_aba3(self):
        """$ABA3: domesticcooperationcontroller aba3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xABA3)
        self._y(0x30)
        yield from self._external(0xABA5,0xF266,0xABA8,"call",None)
        if r.pc!=0xABA8:return  # preserve nonlocal stack return
        self._a(m[0x0038])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x002A]=r.a
        self._a(0xFF)
        m[0x002B]=r.a
        m[0x002C]=r.a
        m[0x002D]=r.a
        while True:  # natural loop $ABB8
            try:
                self._y(m[0x002A])
                self._a(m[(0x9D72+r.y)&65535])
                self._mark(0xABBD)
                if r.p&N:
                    pass
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xABBF,0xABC2)):return
                    self._compare(r.a,0x07)
                    self._mark(0xABC4)
                    if not r.p&Z:
                        self._compare(r.a,m[0x0040])
                        self._mark(0xABD3)
                        if not r.p&Z:
                            pass
                        else:
                            if not (yield from self._local_call(self.domesticcooperationcontroller_d307,0xABD5,0xABD8)):return
                            self._compare(r.a,0x0A)
                            self._mark(0xABDA)
                            if r.p&C:
                                pass
                            else:
                                self._compare(r.a,m[0x002B])
                                self._mark(0xABDE)
                                if r.p&C:
                                    pass
                                else:
                                    m[0x002B]=r.a
                                    self._y(m[0x002A])
                                    self._a(m[(0x9D72+r.y)&65535])
                                    m[0x002C]=r.a
                                    pass
                                pass
                            pass
                        pass
                    else:
                        self._y(m[0x002A])
                        self._a(m[(0x9D72+r.y)&65535])
                        m[0x002D]=r.a
                        pass
                    m[0x002A]=self._nz(m[0x002A]+1)
                    continue
                self._a(m[0x002C])
                self._compare(r.a,0xFF)
                self._mark(0xABF2)
                if r.p&Z:
                    self._a(m[0x002D])
                    self._compare(r.a,0xFF)
                    self._mark(0xAC25)
                    if not r.p&Z:
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xABF4,0xABF7)):return
                        self._y(0x11)
                        while True:  # natural loop $ABF9
                            try:
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xABFD)
                                if r.p&Z:
                                    pass
                                else:
                                    self._y(r.y+1)
                                    continue
                                self._a(m[0x0041])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._y(0x00)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._a(r.a & 0xF8)
                                self._a(r.a | m[0x0040])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._a(m[0x0042])
                                self._mark(0xAC16)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._a(m[0x0041])
                                    m[0x0020]=r.a
                                    if not (yield from self._local_call(self.recalculate_shifted_loyalty,0xAC1D,0xAC20)):return
                                    pass
                                self._mark(0xAC20)
                                self._rts();return
                            except _ContinueLoop_ABF9:
                                continue
                    else:
                        self._a(m[0x0041])
                        self._y(0x0B)
                        if not (yield from self._local_call(self.officer_field_pointer,0xAC2C,0xAC2F)):return
                        self._a(r.a & 0xFC)
                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                        while True:  # natural loop $AC33
                            try:
                                yield from self._external(0xAC33,0xE89A,0xAC36,"call",None)
                                if r.pc!=0xAC36:return  # preserve nonlocal stack return
                                self._a(r.a & 0x07)
                                self._mark(0xAC38)
                                if not r.p&Z:
                                    m[0x002D]=r.a
                                    m[0x002D]=self._nz(m[0x002D]-1)
                                    self._a(m[0x0038])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._flag(C,False)
                                    self._add(m[0x002D])
                                    self._y(r.a)
                                    self._a(m[(0x9D72+r.y)&65535])
                                    self._mark(0xAC5B)
                                    if r.p&N:
                                        continue
                                    else:
                                        self._y(0x05)
                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                        self._a(0xFF)
                                        m[0x002D]=r.a
                                        self._mark(0xAC66)
                                        self._rts();return
                                else:
                                    self._y(0x05)
                                    self._a(m[0x0038])
                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                    self._a(0xFF)
                                    m[0x002D]=r.a
                                    self._mark(0xAC46)
                                    self._rts();return
                            except _ContinueLoop_AC33:
                                continue
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xABF4,0xABF7)):return
                    self._y(0x11)
                    while True:  # natural loop $ABF9
                        try:
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xABFD)
                            if r.p&Z:
                                pass
                            else:
                                self._y(r.y+1)
                                continue
                            self._a(m[0x0041])
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._y(0x00)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._a(r.a & 0xF8)
                            self._a(r.a | m[0x0040])
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._a(m[0x0042])
                            self._mark(0xAC16)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(m[0x0041])
                                m[0x0020]=r.a
                                if not (yield from self._local_call(self.recalculate_shifted_loyalty,0xAC1D,0xAC20)):return
                                pass
                            self._mark(0xAC20)
                            self._rts();return
                        except _ContinueLoop_ABF9:
                            continue
            except _ContinueLoop_ABB8:
                continue

    def domesticcooperationcontroller_ac67(self):
        """$AC67: domesticcooperationcontroller ac67; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC67)
        if not (yield from self._local_call(self.domesticcooperationcontroller_aebf,0xAC67,0xAC6A)):return
        self._a(m[0x0522])
        self._flag(C,True)
        self._add(m[0x002A],subtract=True)
        m[0x0522]=r.a
        self._a(m[0x0523])
        self._add(m[0x002B],subtract=True)
        m[0x0523]=r.a
        self._mark(0xAC7B)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x0522]=r.a
            m[0x0523]=r.a
            pass
        self._a(m[0x0524])
        self._flag(C,True)
        self._add(m[0x002C],subtract=True)
        m[0x0524]=r.a
        self._a(m[0x0525])
        self._add(m[0x002D],subtract=True)
        m[0x0525]=r.a
        self._mark(0xAC96)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x0524]=r.a
            m[0x0525]=r.a
            pass
        if not (yield from self._local_call(self.domesticcooperationcontroller_ce67,0xACA0,0xACA3)):return
        if not (yield from self._local_call(self.domesticcooperationcontroller_cedd,0xACA3,0xACA6)):return
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xACA9,0xACAC)):return
        self._y(0x04)
        self._a(m[0x0522])
        self._flag(C,False)
        self._add(m[0x0524])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[0x0523])
        self._add(m[0x0525])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(0x02)
        self._a(m[0x0526])
        self._flag(C,False)
        self._add(m[0x0528])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[0x0527])
        self._add(m[0x0529])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._mark(0xACD4)
        self._rts();return

    def domesticcooperationcontroller_acd5(self):
        """$ACD5: domesticcooperationcontroller acd5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACD5)
        self._a(0x00)
        m[0x003C]=r.a
        m[0x003D]=r.a
        m[0x003E]=r.a
        m[0x003F]=r.a
        m[0x0040]=r.a
        m[0x0041]=r.a
        m[0x0042]=r.a
        m[0x0043]=r.a
        m[0x0044]=r.a
        while True:  # natural loop $ACF2
            try:
                self._y(m[0x0040])
                self._a(m[(0x066E+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xACFA)
                if r.p&Z:
                    pass
                else:
                    self._y(0x01)
                    if not (yield from self._local_call(self.officer_field_pointer,0xACFE,0xAD01)):return
                    self._flag(C,False)
                    self._add(m[0x0041])
                    m[0x0041]=r.a
                    self._a(m[0x0042])
                    self._add(0x00)
                    m[0x0042]=r.a
                    self._y(0x08)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0043])
                    m[0x0043]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    self._add(m[0x0044])
                    m[0x0044]=r.a
                    m[0x0040]=self._nz(m[0x0040]+1)
                    self._a(m[0x0040])
                    self._compare(r.a,0x0A)
                    self._mark(0xAD2E)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    pass
                self._a(m[0x0041])
                m[0x0021]=r.a
                self._a(m[0x0042])
                m[0x0022]=r.a
                self._a(0x0A)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.divide_domestic_word,0xAD42,0xAD45)):return
                self._a(m[0x0021])
                m[0x003C]=r.a
                self._a(m[0x0043])
                m[0x0021]=r.a
                self._a(m[0x0044])
                m[0x0022]=r.a
                self._a(0x64)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.divide_domestic_word,0xAD5C,0xAD5F)):return
                self._a(m[0x003C])
                self._flag(C,False)
                self._add(m[0x0021])
                m[0x003C]=r.a
                self._a(m[0x003D])
                self._add(0x00)
                m[0x003D]=r.a
                self._a(m[0x066E])
                self._y(0x07)
                if not (yield from self._local_call(self.officer_field_pointer,0xAD75,0xAD78)):return
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                m[0x0020]=r.a
                self._a(0x0A)
                m[0x0021]=r.a
                if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xAD82,0xAD85)):return
                self._a(m[0x003C])
                self._flag(C,False)
                self._add(m[0x002A])
                m[0x003C]=r.a
                self._a(m[0x003D])
                self._add(0x00)
                m[0x003D]=r.a
                self._a(0x00)
                m[0x0040]=r.a
                m[0x0041]=r.a
                m[0x0042]=r.a
                m[0x0043]=r.a
                m[0x0044]=r.a
                while True:  # natural loop $ADA7
                    try:
                        self._y(m[0x0040])
                        self._a(m[(0x0664+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xADAF)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x01)
                            if not (yield from self._local_call(self.officer_field_pointer,0xADB3,0xADB6)):return
                            self._flag(C,False)
                            self._add(m[0x0041])
                            m[0x0041]=r.a
                            self._a(m[0x0042])
                            self._add(0x00)
                            m[0x0042]=r.a
                            self._y(0x08)
                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            self._flag(C,False)
                            self._add(m[0x0043])
                            m[0x0043]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            self._a(r.a & 0x03)
                            self._add(m[0x0044])
                            m[0x0044]=r.a
                            m[0x0040]=self._nz(m[0x0040]+1)
                            self._a(m[0x0040])
                            self._compare(r.a,0x0A)
                            self._mark(0xADE3)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            pass
                        self._a(m[0x0041])
                        m[0x0021]=r.a
                        self._a(m[0x0042])
                        m[0x0022]=r.a
                        self._a(0x0A)
                        m[0x0023]=r.a
                        self._a(0x00)
                        m[0x0024]=r.a
                        if not (yield from self._local_call(self.divide_domestic_word,0xADF7,0xADFA)):return
                        self._a(m[0x0021])
                        m[0x003E]=r.a
                        self._a(m[0x0043])
                        m[0x0021]=r.a
                        self._a(m[0x0044])
                        m[0x0022]=r.a
                        self._a(0x64)
                        m[0x0023]=r.a
                        self._a(0x00)
                        m[0x0024]=r.a
                        if not (yield from self._local_call(self.divide_domestic_word,0xAE11,0xAE14)):return
                        self._a(m[0x003E])
                        self._flag(C,False)
                        self._add(m[0x0021])
                        m[0x003E]=r.a
                        self._a(m[0x003F])
                        self._add(0x00)
                        m[0x003F]=r.a
                        self._a(m[0x0664])
                        self._y(0x07)
                        if not (yield from self._local_call(self.officer_field_pointer,0xAE2A,0xAE2D)):return
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        m[0x0020]=r.a
                        self._a(0x0A)
                        m[0x0021]=r.a
                        if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xAE37,0xAE3A)):return
                        self._a(m[0x003E])
                        self._flag(C,False)
                        self._add(m[0x002A])
                        m[0x003E]=r.a
                        self._a(m[0x003F])
                        self._add(m[0x002B])
                        m[0x003F]=r.a
                        self._a(m[0x003C])
                        m[0x0020]=r.a
                        self._a(m[0x003D])
                        m[0x0021]=r.a
                        self._a(0x00)
                        m[0x0022]=r.a
                        self._a(0x64)
                        m[0x0023]=r.a
                        if not (yield from self._local_call(self.multiply_domestic_word,0xAE5D,0xAE60)):return
                        self._a(m[0x0026])
                        m[0x0021]=r.a
                        self._a(m[0x0027])
                        m[0x0022]=r.a
                        self._a(m[0x003C])
                        self._flag(C,False)
                        self._add(m[0x003E])
                        m[0x0023]=r.a
                        self._a(m[0x003D])
                        self._add(m[0x003F])
                        m[0x0024]=r.a
                        if not (yield from self._local_call(self.divide_domestic_word,0xAE79,0xAE7C)):return
                        self._a(m[0x0021])
                        m[0x003C]=r.a
                        self._a(m[0x003C])
                        r.a=self._shift(r.a,False,rotate=False)
                        self._flag(C,True)
                        self._add(0x19,subtract=True)
                        self._mark(0xAE88)
                        if r.p&C:
                            pass
                        else:
                            self._a(r.a ^ 0xFF)
                            self._flag(C,False)
                            self._add(0x01)
                            pass
                        m[0x0020]=r.a
                        self._a(0x1E)
                        self._flag(C,True)
                        self._add(m[0x0020],subtract=True)
                        m[0x6F8D]=r.a
                        if not (yield from self._local_call(self.domesticcooperationcontroller_aebf,0xAE99,0xAE9C)):return
                        self._a(m[0x0522])
                        self._flag(C,True)
                        self._add(m[0x002A],subtract=True)
                        self._a(m[0x0523])
                        self._add(m[0x002B],subtract=True)
                        self._mark(0xAEA7)
                        if not r.p&C:
                            self._a(0x00)
                            m[0x6F8C]=r.a
                            self._mark(0xAEB8)
                            self._rts();return
                        else:
                            self._a(0x64)
                            if not (yield from self._local_call(self.random_below,0xAEAB,0xAEAE)):return
                            self._compare(r.a,m[0x003C])
                            self._mark(0xAEB1)
                            if r.p&C:
                                self._a(0x01)
                                m[0x6F8C]=r.a
                                self._mark(0xAEBE)
                                self._rts();return
                            else:
                                self._a(0x00)
                                m[0x6F8C]=r.a
                                self._mark(0xAEB8)
                                self._rts();return
                    except _ContinueLoop_ADA7:
                        continue
            except _ContinueLoop_ACF2:
                continue

    def domesticcooperationcontroller_aebf(self):
        """$AEBF: domesticcooperationcontroller aebf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAEBF)
        self._a(0x00)
        m[0x0024]=r.a
        m[0x0025]=r.a
        m[0x0026]=r.a
        while True:  # natural loop $AEC7
            try:
                self._y(m[0x0024])
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAECE)
                if r.p&Z:
                    pass
                else:
                    self._y(0x08)
                    if not (yield from self._local_call(self.officer_field_pointer,0xAED2,0xAED5)):return
                    self._flag(C,False)
                    self._add(m[0x0025])
                    m[0x0025]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._add(m[0x0026])
                    m[0x0026]=r.a
                    pass
                m[0x0024]=self._nz(m[0x0024]+1)
                self._a(m[0x0024])
                self._compare(r.a,0x0A)
                self._mark(0xAEE7)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0025])
                m[0x0021]=r.a
                self._a(m[0x0026])
                m[0x0022]=r.a
                self._a(0x64)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.divide_domestic_word,0xAEF9,0xAEFC)):return
                self._a(m[0x0021])
                m[0x0020]=r.a
                self._a(m[0x0022])
                m[0x0021]=r.a
                self._a(0x00)
                m[0x0022]=r.a
                self._a(m[0x6F8D])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0023]=r.a
                if not (yield from self._local_call(self.multiply_domestic_word,0xAF0F,0xAF12)):return
                self._a(m[0x0026])
                m[0x0021]=r.a
                self._a(m[0x0027])
                m[0x0022]=r.a
                self._a(0x0A)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.divide_domestic_word,0xAF22,0xAF25)):return
                self._a(m[0x0021])
                m[0x002A]=r.a
                self._a(m[0x0022])
                m[0x002B]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                m[0x0025]=r.a
                m[0x0026]=r.a
                while True:  # natural loop $AF35
                    try:
                        self._y(m[0x0024])
                        self._a(m[(0x066E+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xAF3C)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x08)
                            if not (yield from self._local_call(self.officer_field_pointer,0xAF40,0xAF43)):return
                            self._flag(C,False)
                            self._add(m[0x0025])
                            m[0x0025]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            self._add(m[0x0026])
                            m[0x0026]=r.a
                            pass
                        m[0x0024]=self._nz(m[0x0024]+1)
                        self._a(m[0x0024])
                        self._compare(r.a,0x0A)
                        self._mark(0xAF55)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._a(m[0x0025])
                        m[0x0021]=r.a
                        self._a(m[0x0026])
                        m[0x0022]=r.a
                        self._a(0x64)
                        m[0x0023]=r.a
                        self._a(0x00)
                        m[0x0024]=r.a
                        if not (yield from self._local_call(self.divide_domestic_word,0xAF67,0xAF6A)):return
                        self._a(m[0x0021])
                        m[0x0020]=r.a
                        self._a(m[0x0022])
                        m[0x0021]=r.a
                        self._a(0x00)
                        m[0x0022]=r.a
                        self._a(m[0x6F8D])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        m[0x0023]=r.a
                        if not (yield from self._local_call(self.multiply_domestic_word,0xAF7D,0xAF80)):return
                        self._a(m[0x0026])
                        m[0x0021]=r.a
                        self._a(m[0x0027])
                        m[0x0022]=r.a
                        self._a(0x0A)
                        m[0x0023]=r.a
                        self._a(0x00)
                        m[0x0024]=r.a
                        if not (yield from self._local_call(self.divide_domestic_word,0xAF90,0xAF93)):return
                        self._a(m[0x0021])
                        m[0x002C]=r.a
                        self._a(m[0x0022])
                        m[0x002D]=r.a
                        self._mark(0xAF9B)
                        self._rts();return
                    except _ContinueLoop_AF35:
                        continue
            except _ContinueLoop_AEC7:
                continue

    def domesticcooperationcontroller_af9c(self):
        """$AF9C: domesticcooperationcontroller af9c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF9C)
        self._a(m[0x6F77])
        m[0x0020]=r.a
        self._a(0x78)
        m[0x0021]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xAFA5,0xAFA8)):return
        self._a(m[0x002A])
        self._flag(C,False)
        self._add(m[0x6F73])
        m[0x6F73]=r.a
        self._a(m[0x002B])
        self._add(m[0x6F74])
        m[0x6F74]=r.a
        self._a(m[0x6F78])
        m[0x0020]=r.a
        self._a(0x78)
        m[0x0021]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xAFC2,0xAFC5)):return
        self._a(m[0x002A])
        self._flag(C,False)
        self._add(m[0x6F75])
        m[0x6F75]=r.a
        self._a(m[0x002B])
        self._add(m[0x6F76])
        m[0x6F76]=r.a
        self._a(m[0x6F75])
        m[0x0021]=r.a
        self._a(m[0x6F76])
        m[0x0022]=r.a
        self._a(m[0x003C])
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_domestic_word,0xAFE9,0xAFEC)):return
        self._a(m[0x0021])
        m[0x6F75]=r.a
        self._a(m[0x0022])
        m[0x6F76]=r.a
        self._a(m[0x6F73])
        m[0x0021]=r.a
        self._a(m[0x6F74])
        m[0x0022]=r.a
        self._a(m[0x003D])
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_domestic_word,0xB009,0xB00C)):return
        self._a(m[0x0021])
        m[0x6F73]=r.a
        self._a(m[0x0022])
        m[0x6F74]=r.a
        self._a(0x00)
        m[0x0036]=r.a
        while True:  # natural loop $B01B
            try:
                self._y(m[0x0036])
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB023)
                if r.p&Z:
                    pass
                else:
                    m[0x002A]=r.a
                    self._a(m[0x6F75])
                    m[0x002B]=r.a
                    self._a(m[0x6F76])
                    m[0x002C]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_b067,0xB031,0xB034)):return
                    pass
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x0A)
                self._mark(0xB03C)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0x00)
                m[0x0036]=r.a
                while True:  # natural loop $B043
                    try:
                        self._y(m[0x0036])
                        self._a(m[(0x066E+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xB04B)
                        if r.p&Z:
                            pass
                        else:
                            m[0x002A]=r.a
                            self._a(m[0x6F73])
                            m[0x002B]=r.a
                            self._a(m[0x6F74])
                            m[0x002C]=r.a
                            if not (yield from self._local_call(self.domesticcooperationcontroller_b067,0xB059,0xB05C)):return
                            pass
                        m[0x0036]=self._nz(m[0x0036]+1)
                        self._a(m[0x0036])
                        self._compare(r.a,0x0A)
                        self._mark(0xB064)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._mark(0xB066)
                        self._rts();return
                    except _ContinueLoop_B043:
                        continue
            except _ContinueLoop_B01B:
                continue

    def domesticcooperationcontroller_b067(self):
        """$B067: domesticcooperationcontroller b067; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB067)
        self._a(m[0x002A])
        self._y(0x00)
        if not (yield from self._local_call(self.officer_field_pointer,0xB06B,0xB06E)):return
        m[0x002C]=self._shift(m[0x002C],False,rotate=False)
        m[0x002B]=self._shift(m[0x002B],False,rotate=True)
        self._y(0x06)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x002B])
        m[0x002D]=r.a
        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._add(m[0x002C])
        m[0x002E]=r.a
        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        self._y(0x06)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x4F,subtract=True)
        self._y(r.y+1)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._add(0xC3,subtract=True)
        self._mark(0xB092)
        if not r.p&C:
            pass
        else:
            self._y(0x06)
            self._a(0x4F)
            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(0xC3)
            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
            pass
        self._y(0x0B)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._a(r.a & 0xF0)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._compare(r.a,0x0E)
        self._mark(0xB0AA)
        if r.p&C:
            self._mark(0xB0BB)
            self._rts();return
        else:
            self._y(r.a)
            self._a(m[0x002D])
            self._flag(C,True)
            self._add(m[(0xB0BC+r.y)&65535],subtract=True)
            self._a(m[0x002E])
            self._add(m[(0xB0BD+r.y)&65535],subtract=True)
            self._mark(0xB0B9)
            if r.p&C:
                self._a(r.y)
                r.a=self._shift(r.a,False,rotate=False)
                self._flag(C,False)
                self._add(0x01)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x002F]=r.a
                self._y(0x0B)
                self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                self._a(r.a & 0xF0)
                self._compare(r.a,m[0x002F])
                self._mark(0xB0DD)
                if r.p&C:
                    self._mark(0xB0BB)
                    self._rts();return
                else:
                    self._y(0x0B)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._a(r.a & 0x0F)
                    self._a(r.a | m[0x002F])
                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                    self._y(0x01)
                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    self._y(0x06)
                    self._compare(r.a,0x33)
                    self._mark(0xB0F1)
                    if not r.p&C:
                        self._a(r.y)
                        self._y(0x01)
                        self._flag(C,False)
                        self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                        pass
                    else:
                        self._y(0x05)
                        self._compare(r.a,0x47)
                        self._mark(0xB0F7)
                        if not r.p&C:
                            self._a(r.y)
                            self._y(0x01)
                            self._flag(C,False)
                            self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                            pass
                        else:
                            self._y(0x04)
                            self._compare(r.a,0x51)
                            self._mark(0xB0FD)
                            if not r.p&C:
                                self._a(r.y)
                                self._y(0x01)
                                self._flag(C,False)
                                self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                pass
                            else:
                                self._y(0x02)
                                self._compare(r.a,0x5A)
                                self._mark(0xB103)
                                if r.p&C:
                                    pass
                                else:
                                    self._a(r.y)
                                    self._y(0x01)
                                    self._flag(C,False)
                                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                    pass
                                pass
                            pass
                        pass
                    self._mark(0xB10D)
                    self._rts();return
            else:
                self._mark(0xB0BB)
                self._rts();return

    def domesticcooperationcontroller_b180(self):
        """$B180: domesticcooperationcontroller b180; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB180)
        self._y(0x30)
        yield from self._external(0xB182,0xF266,0xB185,"call",None)
        if r.pc!=0xB185:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0036]=r.a
        self._a(0xFF)
        m[0x0038]=r.a
        m[0x003A]=r.a
        self._a(0x00)
        m[0x0039]=r.a
        while True:  # natural loop $B197
            try:
                self._a(m[0x0036])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB19A,0xB19D)):return
                self._compare(r.a,m[RULER])
                self._mark(0xB1A0)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d307,0xB1A2,0xB1A5)):return
                    m[0x0026]=r.a
                    self._a(m[0x0036])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0024]=r.a
                    while True:  # natural loop $B1AF
                        try:
                            self._y(m[0x0024])
                            self._a(m[(0x9D72+r.y)&65535])
                            self._mark(0xB1B4)
                            if r.p&N:
                                pass
                            else:
                                m[0x0025]=r.a
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB1B8,0xB1BB)):return
                                self._a(r.a & 0x07)
                                self._compare(r.a,0x07)
                                self._mark(0xB1BF)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._a(m[0x0025])
                                    self._compare(r.a,m[0x0038])
                                    self._mark(0xB1C6)
                                    if not r.p&Z:
                                        m[0x0038]=r.a
                                        self._a(m[0x0026])
                                        m[0x0039]=r.a
                                        self._a(m[0x0036])
                                        m[0x003A]=r.a
                                        pass
                                    else:
                                        self._a(m[0x0026])
                                        self._compare(r.a,m[0x0039])
                                        self._mark(0xB1CD)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[0x0039]=r.a
                                            self._a(m[0x0036])
                                            m[0x003A]=r.a
                                            pass
                                        pass
                                    pass
                                m[0x0024]=self._nz(m[0x0024]+1)
                                continue
                            m[0x0036]=self._nz(m[0x0036]+1)
                            self._a(m[0x0036])
                            self._compare(r.a,0x1E)
                            self._mark(0xB1F6)
                            if not r.p&C:
                                raise _ContinueLoop_B197
                            else:
                                pass
                            self._mark(0xB1F8)
                            self._rts();return
                        except _ContinueLoop_B1AF:
                            continue
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xB1F6)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB1F8)
                self._rts();return
            except _ContinueLoop_B197:
                continue

    def domesticcooperationcontroller_b1f9(self):
        """$B1F9: domesticcooperationcontroller b1f9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB1F9)
        if not (yield from self._local_call(self.domesticcooperationcontroller_b1fd,0xB1F9,0xB1FC)):return
        self._mark(0xB1FC)
        self._rts();return

    def domesticcooperationcontroller_b1fd(self):
        """$B1FD: domesticcooperationcontroller b1fd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB1FD)
        if not (yield from self._local_call(self.quote_attack_supplies,0xB1FD,0xB200)):return
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB203,0xB206)):return
        self._a(m[0x003D])
        self._y(0x02)
        self._flag(C,True)
        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
        m[0x003D]=r.a
        self._y(r.y+1)
        self._a(m[0x003E])
        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
        m[0x003E]=r.a
        self._mark(0xB21A)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x003D]=r.a
            m[0x003E]=r.a
            pass
        self._a(m[0x003B])
        self._y(0x02)
        self._flag(C,True)
        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
        m[0x003B]=r.a
        self._y(r.y+1)
        self._a(m[0x003C])
        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
        m[0x003C]=r.a
        self._mark(0xB238)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x003B]=r.a
            m[0x003C]=r.a
            pass
        while True:  # natural loop $B242
            try:
                self._a(m[0x003A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB245,0xB248)):return
                self._y(0x02)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x003D],subtract=True)
                self._y(r.y+1)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._add(m[0x003E],subtract=True)
                self._mark(0xB256)
                if r.p&C:
                    while True:  # natural loop $B264
                        try:
                            self._a(m[0x003A])
                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB267,0xB26A)):return
                            self._y(0x04)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._flag(C,True)
                            self._add(m[0x003B],subtract=True)
                            self._y(r.y+1)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._add(m[0x003C],subtract=True)
                            self._mark(0xB278)
                            if r.p&C:
                                self._mark(0xB286)
                                self._rts();return
                            else:
                                if not (yield from self._local_call(self.transfer_attack_grain,0xB27A,0xB27D)):return
                                self._mark(0xB27D)
                                if r.p&C:
                                    continue
                                else:
                                    self._a(self._pop())
                                    self._a(self._pop())
                                    self._a(self._pop())
                                    self._a(self._pop())
                                    return (yield from self.city_development_strategy())
                        except _ContinueLoop_B264:
                            continue
                else:
                    if not (yield from self._local_call(self.transfer_attack_gold,0xB258,0xB25B)):return
                    self._mark(0xB25B)
                    if r.p&C:
                        continue
                    else:
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        return (yield from self.city_development_strategy())
            except _ContinueLoop_B242:
                continue

    def domesticcooperationcontroller_b287(self):
        """$B287: domesticcooperationcontroller b287; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB287)
        self._a(m[0x003A])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB28A,0xB28D)):return
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x003D],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x003E],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.cap_city_word,0xB29F,0xB2A2)):return
        self._y(0x04)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x003B],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x003C],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.cap_city_word,0xB2B4,0xB2B7)):return
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB2BA,0xB2BD)):return
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x003D])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x003E])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(0x04)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x003B])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x003C])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB2E4,0xB2E7)):return
        self._a(m[0x0020])
        m[0x0028]=r.a
        self._a(m[0x0021])
        m[0x0029]=r.a
        self._a(m[0x003A])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB2F2,0xB2F5)):return
        m[0x0037]=self._nz(m[0x0037]-1)
        m[0x0037]=self._nz(m[0x0037]-1)
        self._a(0x00)
        m[0x002A]=r.a
        while True:  # natural loop $B2FF
            try:
                self._a(0x12)
                m[0x002B]=r.a
                self._a(0x00)
                m[0x002C]=r.a
                self._a(0xFF)
                m[0x002D]=r.a
                while True:  # natural loop $B30B
                    try:
                        self._y(m[0x002B])
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xB311)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x03)
                            if not (yield from self._local_call(self.officer_field_pointer,0xB315,0xB318)):return
                            self._compare(r.a,m[0x002C])
                            self._mark(0xB31A)
                            if not r.p&C:
                                pass
                            else:
                                m[0x002C]=r.a
                                self._a(m[0x002B])
                                m[0x002D]=r.a
                                pass
                            pass
                        m[0x002B]=self._nz(m[0x002B]+1)
                        self._a(m[0x002B])
                        self._compare(r.a,0x1B)
                        self._mark(0xB328)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(m[0x002D])
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._push(r.a)
                        self._a(0xFF)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._a(m[0x002A])
                        self._flag(C,False)
                        self._add(0x11)
                        self._y(r.a)
                        self._a(self._pop())
                        m[((m[0x28]|m[0x29]<<8)+r.y)&65535]=r.a
                        m[0x002A]=self._nz(m[0x002A]+1)
                        self._y(m[0x002A])
                        self._compare(r.y,m[0x0037])
                        self._mark(0xB343)
                        if not r.p&C:
                            raise _ContinueLoop_B2FF
                        else:
                            pass
                        self._a(m[0x003A])
                        if not (yield from self._local_call(self.compact_city_roster,0xB348,0xB34B)):return
                        self._y(0x00)
                        self._a(m[((m[0x28]|m[0x29]<<8)+r.y)&65535])
                        self._a(r.a & 0xF8)
                        self._a(r.a | m[RULER])
                        m[((m[0x28]|m[0x29]<<8)+r.y)&65535]=r.a
                        self._mark(0xB356)
                        self._rts();return
                    except _ContinueLoop_B30B:
                        continue
            except _ContinueLoop_B2FF:
                continue

    def domesticcooperationcontroller_b433(self):
        """$B433: domesticcooperationcontroller b433; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB433)
        self._a(m[0x0036])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0024]=r.a
        self._a(0x00)
        m[0x0025]=r.a
        while True:  # natural loop $B43F
            try:
                self._y(m[0x0024])
                self._a(m[(0x9D72+r.y)&65535])
                self._mark(0xB444)
                if r.p&N:
                    pass
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB446,0xB449)):return
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[RULER])
                    self._mark(0xB44E)
                    if not r.p&Z:
                        pass
                    else:
                        m[0x0025]=self._nz(m[0x0025]+1)
                        pass
                    m[0x0024]=self._nz(m[0x0024]+1)
                    continue
                self._a(m[0x0025])
                self._compare(r.a,0x01)
                self._mark(0xB45B)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0036])
                    if not (yield from self._local_call(self.count_prefix_officers,0xB460,0xB463)):return
                    self._y(0x08)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    m[0x0026]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    m[0x0027]=r.a
                    self._y(0x0E)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0026])
                    m[0x0026]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._add(m[0x0027])
                    m[0x0027]=r.a
                    self._a(m[0x0026])
                    self._flag(C,True)
                    self._add(m[0x0038],subtract=True)
                    self._a(m[0x0027])
                    self._add(m[0x0039],subtract=True)
                    self._mark(0xB489)
                    if r.p&C:
                        pass
                    else:
                        self._a(m[0x0026])
                        m[0x0038]=r.a
                        self._a(m[0x0027])
                        m[0x0039]=r.a
                        self._a(m[0x0036])
                        m[0x0037]=r.a
                        pass
                    pass
                self._mark(0xB49B)
                self._rts();return
            except _ContinueLoop_B43F:
                continue

    def city_assignment_strategy(self):
        """$B49C: city assignment strategy; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $B49C
            try:
                self._mark(0xB49C)
                yield from self._external(0xB49C,0xE8AA,0xB49F,"call",None)
                if r.pc!=0xB49F:return  # preserve nonlocal stack return
                self._a(r.a & 0x7F)
                self._compare(r.a,0x32)
                self._mark(0xB4A3)
                if r.p&C:
                    continue
                else:
                    pass
                self._compare(r.a,0x0A)
                self._mark(0xB4A7)
                if r.p&C:
                    if not (yield from self._local_call(self.find_ruler_city,0xB4AC,0xB4AF)):return
                    m[0x0045]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d03a,0xB4B2,0xB4B5)):return
                    self._a(0x03)
                    m[0x0041]=r.a
                    self._a(0x00)
                    m[0x0036]=r.a
                    while True:  # natural loop $B4BF
                        try:
                            self._a(m[0x0036])
                            self._compare(r.a,m[0x0045])
                            self._mark(0xB4C5)
                            if r.p&Z:
                                pass
                            else:
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB4C7,0xB4CA)):return
                                self._compare(r.a,m[RULER])
                                self._mark(0xB4CD)
                                if not r.p&Z:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.build_enemy_neighbor_list,0xB4CF,0xB4D2)):return
                                    self._mark(0xB4D2)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._a(m[0x0036])
                                        if not (yield from self._local_call(self.count_prefix_officers,0xB4D7,0xB4DA)):return
                                        self._compare(r.a,m[0x0041])
                                        self._mark(0xB4DD)
                                        if not r.p&C:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_b53e,0xB4DF,0xB4E2)):return
                                            self._a(m[0x003D])
                                            self._compare(r.a,0xFF)
                                            self._mark(0xB4E7)
                                            if r.p&Z:
                                                pass
                                            else:
                                                continue
                                            pass
                                        pass
                                    pass
                                pass
                            m[0x0036]=self._nz(m[0x0036]+1)
                            self._a(m[0x0036])
                            self._compare(r.a,0x1E)
                            self._mark(0xB4F4)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(m[0x0040])
                            self._flag(C,False)
                            self._add(0x02)
                            m[0x0041]=r.a
                            self._a(0x00)
                            m[0x0036]=r.a
                            while True:  # natural loop $B504
                                try:
                                    self._a(m[0x0036])
                                    self._compare(r.a,m[0x0045])
                                    self._mark(0xB50A)
                                    if r.p&Z:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB50C,0xB50F)):return
                                        self._compare(r.a,m[RULER])
                                        self._mark(0xB512)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.build_enemy_neighbor_list,0xB514,0xB517)):return
                                            self._mark(0xB517)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(m[0x0036])
                                                if not (yield from self._local_call(self.count_prefix_officers,0xB51C,0xB51F)):return
                                                self._compare(r.a,m[0x0041])
                                                self._mark(0xB522)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_b53e,0xB524,0xB527)):return
                                                    self._a(m[0x003D])
                                                    self._compare(r.a,0xFF)
                                                    self._mark(0xB52C)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        continue
                                                    pass
                                                pass
                                            pass
                                        pass
                                    m[0x0036]=self._nz(m[0x0036]+1)
                                    self._a(m[0x0036])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xB539)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    while True:  # natural loop $BD7A
                                        try:
                                            self._a(0x00)
                                            m[0x0036]=r.a
                                            m[0x0037]=r.a
                                            self._a(0xFF)
                                            m[0x0038]=r.a
                                            m[0x0039]=r.a
                                            while True:  # natural loop $BD8A
                                                try:
                                                    self._a(m[0x0036])
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBD8D,0xBD90)):return
                                                    self._compare(r.a,m[RULER])
                                                    self._mark(0xBD93)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._y(0x01)
                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                        self._flag(C,True)
                                                        self._add(0x2C,subtract=True)
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                        self._add(0x01,subtract=True)
                                                        self._mark(0xBDA1)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._y(0x11)
                                                            m[0x0024]=r.y
                                                            while True:  # natural loop $BDA7
                                                                try:
                                                                    self._y(m[0x0024])
                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                    self._compare(r.a,0xFF)
                                                                    self._mark(0xBDAD)
                                                                    if r.p&Z:
                                                                        pass
                                                                    else:
                                                                        self._y(0x09)
                                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBDB1,0xBDB4)):return
                                                                        self._a(r.a & 0x03)
                                                                        self._compare(r.a,0x03)
                                                                        self._mark(0xBDB8)
                                                                        if not r.p&Z:
                                                                            self._y(m[0x0024])
                                                                            self._compare(r.y,0x11)
                                                                            self._mark(0xBDC6)
                                                                            if not r.p&Z:
                                                                                self._y(0x01)
                                                                                self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                                pass
                                                                            else:
                                                                                self._a(0x64)
                                                                                pass
                                                                            self._compare(r.a,m[0x0037])
                                                                            self._mark(0xBDD4)
                                                                            if not r.p&C:
                                                                                pass
                                                                            else:
                                                                                m[0x0037]=r.a
                                                                                self._y(m[0x0024])
                                                                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                m[0x0038]=r.a
                                                                                self._a(m[0x0036])
                                                                                m[0x0039]=r.a
                                                                                pass
                                                                            pass
                                                                        else:
                                                                            self._y(0x08)
                                                                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                            self._compare(r.a,0xE8)
                                                                            self._mark(0xBDC0)
                                                                            if r.p&Z:
                                                                                pass
                                                                            else:
                                                                                self._y(m[0x0024])
                                                                                self._compare(r.y,0x11)
                                                                                self._mark(0xBDC6)
                                                                                if not r.p&Z:
                                                                                    self._y(0x01)
                                                                                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                                    pass
                                                                                else:
                                                                                    self._a(0x64)
                                                                                    pass
                                                                                self._compare(r.a,m[0x0037])
                                                                                self._mark(0xBDD4)
                                                                                if not r.p&C:
                                                                                    pass
                                                                                else:
                                                                                    m[0x0037]=r.a
                                                                                    self._y(m[0x0024])
                                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                    m[0x0038]=r.a
                                                                                    self._a(m[0x0036])
                                                                                    m[0x0039]=r.a
                                                                                    pass
                                                                                pass
                                                                            pass
                                                                        pass
                                                                    m[0x0024]=self._nz(m[0x0024]+1)
                                                                    self._a(m[0x0024])
                                                                    self._compare(r.a,0x1B)
                                                                    self._mark(0xBDEC)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        pass
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1E)
                                                                    self._mark(0xBDF6)
                                                                    if not r.p&C:
                                                                        raise _ContinueLoop_BD8A
                                                                    else:
                                                                        pass
                                                                    self._a(m[0x0038])
                                                                    self._compare(r.a,0xFF)
                                                                    self._mark(0xBDFD)
                                                                    if not r.p&Z:
                                                                        self._a(m[0x0039])
                                                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBE05,0xBE08)):return
                                                                        self._a(m[0x0038])
                                                                        self._y(0x08)
                                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBE0D,0xBE10)):return
                                                                        m[0x002A]=r.a
                                                                        self._y(r.y+1)
                                                                        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                        self._a(r.a & 0x03)
                                                                        m[0x002B]=r.a
                                                                        self._a(0xE8)
                                                                        self._flag(C,True)
                                                                        self._add(m[0x002A],subtract=True)
                                                                        m[0x003A]=r.a
                                                                        m[0x002C]=r.a
                                                                        self._a(0x03)
                                                                        self._add(m[0x002B],subtract=True)
                                                                        m[0x003B]=r.a
                                                                        m[0x002D]=r.a
                                                                        self._y(0x0C)
                                                                        self._a(m[0x003A])
                                                                        self._flag(C,True)
                                                                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                                                                        m[0x003C]=r.a
                                                                        self._y(r.y+1)
                                                                        self._a(m[0x003B])
                                                                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                                                                        m[0x003D]=r.a
                                                                        self._mark(0xBE40)
                                                                        if not r.p&C:
                                                                            pass
                                                                        else:
                                                                            self._y(0x00)
                                                                            m[0x0028]=r.y
                                                                            m[0x0029]=r.y
                                                                            while True:  # natural loop $BE48
                                                                                try:
                                                                                    self._a(r.y)
                                                                                    self._flag(C,False)
                                                                                    self._add(0x14)
                                                                                    self._y(r.a)
                                                                                    self._a(m[0x0028])
                                                                                    self._flag(C,False)
                                                                                    self._add(0x64)
                                                                                    m[0x0028]=r.a
                                                                                    self._a(m[0x0029])
                                                                                    self._add(0x00)
                                                                                    m[0x0029]=r.a
                                                                                    self._a(m[0x003C])
                                                                                    self._flag(C,True)
                                                                                    self._add(0x64,subtract=True)
                                                                                    m[0x003C]=r.a
                                                                                    self._a(m[0x003D])
                                                                                    self._add(0x00,subtract=True)
                                                                                    m[0x003D]=r.a
                                                                                    self._mark(0xBE6B)
                                                                                    if r.p&C:
                                                                                        continue
                                                                                    else:
                                                                                        pass
                                                                                    self._a(r.y)
                                                                                    m[0x0022]=r.a
                                                                                    self._a(0x00)
                                                                                    m[0x0023]=r.a
                                                                                    self._a(0x00)
                                                                                    m[0x0024]=r.a
                                                                                    self._a(m[0x0039])
                                                                                    if not (yield from self._local_call(self.pay_city_gold,0xBE7B,0xBE7E)):return
                                                                                    self._a(m[0x0039])
                                                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBE81,0xBE84)):return
                                                                                    self._y(0x0C)
                                                                                    self._a(m[0x0028])
                                                                                    self._flag(C,False)
                                                                                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                    self._y(r.y+1)
                                                                                    self._a(m[0x0029])
                                                                                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                    if not (yield from self._local_call(self.cap_city_word,0xBE94,0xBE97)):return
                                                                                    self._y(0x0C)
                                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                    self._flag(C,True)
                                                                                    self._add(m[0x003A],subtract=True)
                                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                    self._y(r.y+1)
                                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                    self._add(m[0x003B],subtract=True)
                                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                    if not (yield from self._local_call(self.cap_city_word,0xBEA9,0xBEAC)):return
                                                                                    self._a(m[0x0038])
                                                                                    self._y(0x08)
                                                                                    if not (yield from self._local_call(self.officer_field_pointer,0xBEB1,0xBEB4)):return
                                                                                    self._y(0x08)
                                                                                    self._a(0xE8)
                                                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                                    self._y(r.y+1)
                                                                                    self._a(0x03)
                                                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                                    self._a(0x02)
                                                                                    if not (yield from self._local_call(self.charge_task_budget,0xBEC1,0xBEC4)):return
                                                                                    raise _ContinueLoop_BD7A
                                                                                except _ContinueLoop_BE48:
                                                                                    continue
                                                                        if not (yield from self._local_call(self.cap_city_word,0xBE94,0xBE97)):return
                                                                        self._y(0x0C)
                                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                        self._flag(C,True)
                                                                        self._add(m[0x003A],subtract=True)
                                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                        self._y(r.y+1)
                                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                        self._add(m[0x003B],subtract=True)
                                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                        if not (yield from self._local_call(self.cap_city_word,0xBEA9,0xBEAC)):return
                                                                        self._a(m[0x0038])
                                                                        self._y(0x08)
                                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBEB1,0xBEB4)):return
                                                                        self._y(0x08)
                                                                        self._a(0xE8)
                                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                        self._y(r.y+1)
                                                                        self._a(0x03)
                                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                        self._a(0x02)
                                                                        if not (yield from self._local_call(self.charge_task_budget,0xBEC1,0xBEC4)):return
                                                                        raise _ContinueLoop_BD7A
                                                                    else:
                                                                        pass
                                                                    return (yield from self.city_development_strategy())
                                                                except _ContinueLoop_BDA7:
                                                                    continue
                                                        pass
                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                    self._a(m[0x0036])
                                                    self._compare(r.a,0x1E)
                                                    self._mark(0xBDF6)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0038])
                                                    self._compare(r.a,0xFF)
                                                    self._mark(0xBDFD)
                                                    if not r.p&Z:
                                                        self._a(m[0x0039])
                                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBE05,0xBE08)):return
                                                        self._a(m[0x0038])
                                                        self._y(0x08)
                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBE0D,0xBE10)):return
                                                        m[0x002A]=r.a
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                        self._a(r.a & 0x03)
                                                        m[0x002B]=r.a
                                                        self._a(0xE8)
                                                        self._flag(C,True)
                                                        self._add(m[0x002A],subtract=True)
                                                        m[0x003A]=r.a
                                                        m[0x002C]=r.a
                                                        self._a(0x03)
                                                        self._add(m[0x002B],subtract=True)
                                                        m[0x003B]=r.a
                                                        m[0x002D]=r.a
                                                        self._y(0x0C)
                                                        self._a(m[0x003A])
                                                        self._flag(C,True)
                                                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                                                        m[0x003C]=r.a
                                                        self._y(r.y+1)
                                                        self._a(m[0x003B])
                                                        self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535],subtract=True)
                                                        m[0x003D]=r.a
                                                        self._mark(0xBE40)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._y(0x00)
                                                            m[0x0028]=r.y
                                                            m[0x0029]=r.y
                                                            while True:  # natural loop $BE48
                                                                try:
                                                                    self._a(r.y)
                                                                    self._flag(C,False)
                                                                    self._add(0x14)
                                                                    self._y(r.a)
                                                                    self._a(m[0x0028])
                                                                    self._flag(C,False)
                                                                    self._add(0x64)
                                                                    m[0x0028]=r.a
                                                                    self._a(m[0x0029])
                                                                    self._add(0x00)
                                                                    m[0x0029]=r.a
                                                                    self._a(m[0x003C])
                                                                    self._flag(C,True)
                                                                    self._add(0x64,subtract=True)
                                                                    m[0x003C]=r.a
                                                                    self._a(m[0x003D])
                                                                    self._add(0x00,subtract=True)
                                                                    m[0x003D]=r.a
                                                                    self._mark(0xBE6B)
                                                                    if r.p&C:
                                                                        continue
                                                                    else:
                                                                        pass
                                                                    self._a(r.y)
                                                                    m[0x0022]=r.a
                                                                    self._a(0x00)
                                                                    m[0x0023]=r.a
                                                                    self._a(0x00)
                                                                    m[0x0024]=r.a
                                                                    self._a(m[0x0039])
                                                                    if not (yield from self._local_call(self.pay_city_gold,0xBE7B,0xBE7E)):return
                                                                    self._a(m[0x0039])
                                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBE81,0xBE84)):return
                                                                    self._y(0x0C)
                                                                    self._a(m[0x0028])
                                                                    self._flag(C,False)
                                                                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                    self._y(r.y+1)
                                                                    self._a(m[0x0029])
                                                                    self._add(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                    if not (yield from self._local_call(self.cap_city_word,0xBE94,0xBE97)):return
                                                                    self._y(0x0C)
                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                    self._flag(C,True)
                                                                    self._add(m[0x003A],subtract=True)
                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                    self._y(r.y+1)
                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                    self._add(m[0x003B],subtract=True)
                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                    if not (yield from self._local_call(self.cap_city_word,0xBEA9,0xBEAC)):return
                                                                    self._a(m[0x0038])
                                                                    self._y(0x08)
                                                                    if not (yield from self._local_call(self.officer_field_pointer,0xBEB1,0xBEB4)):return
                                                                    self._y(0x08)
                                                                    self._a(0xE8)
                                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                    self._y(r.y+1)
                                                                    self._a(0x03)
                                                                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                    self._a(0x02)
                                                                    if not (yield from self._local_call(self.charge_task_budget,0xBEC1,0xBEC4)):return
                                                                    raise _ContinueLoop_BD7A
                                                                except _ContinueLoop_BE48:
                                                                    continue
                                                        if not (yield from self._local_call(self.cap_city_word,0xBE94,0xBE97)):return
                                                        self._y(0x0C)
                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                        self._flag(C,True)
                                                        self._add(m[0x003A],subtract=True)
                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                        self._add(m[0x003B],subtract=True)
                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                        if not (yield from self._local_call(self.cap_city_word,0xBEA9,0xBEAC)):return
                                                        self._a(m[0x0038])
                                                        self._y(0x08)
                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBEB1,0xBEB4)):return
                                                        self._y(0x08)
                                                        self._a(0xE8)
                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._a(0x03)
                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                        self._a(0x02)
                                                        if not (yield from self._local_call(self.charge_task_budget,0xBEC1,0xBEC4)):return
                                                        raise _ContinueLoop_BD7A
                                                    else:
                                                        pass
                                                    return (yield from self.city_development_strategy())
                                                except _ContinueLoop_BD8A:
                                                    continue
                                        except _ContinueLoop_BD7A:
                                            continue
                                except _ContinueLoop_B504:
                                    continue
                        except _ContinueLoop_B4BF:
                            continue
                else:
                    while True:  # natural loop $B5FC
                        try:
                            yield from self._external(0xB5FC,0xE89A,0xB5FF,"call",None)
                            if r.pc!=0xB5FF:return  # preserve nonlocal stack return
                            self._a(r.a & 0x7F)
                            self._compare(r.a,0x5A)
                            self._mark(0xB603)
                            if r.p&C:
                                continue
                            else:
                                pass
                            self._compare(r.a,0x1E)
                            self._mark(0xB607)
                            if not r.p&C:
                                self._a(0x00)
                                m[0x0036]=r.a
                                self._a(0xFF)
                                m[0x003D]=r.a
                                self._a(0x00)
                                m[0x003E]=r.a
                                while True:  # natural loop $BBC1
                                    try:
                                        self._a(m[0x0036])
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBBC4,0xBBC7)):return
                                        self._compare(r.a,m[RULER])
                                        self._mark(0xBBCA)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_bd3e,0xBBCC,0xBBCF)):return
                                            pass
                                        m[0x0036]=self._nz(m[0x0036]+1)
                                        self._a(m[0x0036])
                                        self._compare(r.a,0x1E)
                                        self._mark(0xBBD7)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._a(0x00)
                                        m[0x0036]=r.a
                                        m[0x0037]=r.a
                                        self._a(0xFF)
                                        m[0x0038]=r.a
                                        while True:  # natural loop $BBE6
                                            try:
                                                self._a(m[0x0036])
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBBE9,0xBBEC)):return
                                                self._compare(r.a,m[RULER])
                                                self._mark(0xBBEF)
                                                if r.p&Z:
                                                    pass
                                                else:
                                                    if not (yield from self._local_call(self.ruler_pointer,0xBBF1,0xBBF4)):return
                                                    self._y(0x03)
                                                    self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                    self._compare(r.a,0x03)
                                                    self._mark(0xBBFA)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        self._a(m[0x0036])
                                                        if not (yield from self._local_call(self.count_prefix_officers,0xBBFF,0xBC02)):return
                                                        self._compare(r.a,m[0x0037])
                                                        self._mark(0xBC05)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[0x0037]=r.a
                                                            self._a(m[0x0036])
                                                            m[0x0038]=r.a
                                                            pass
                                                        pass
                                                    pass
                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                self._a(m[0x0036])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xBC18)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[0x0037])
                                                self._compare(r.a,0x06)
                                                self._mark(0xBC1F)
                                                if r.p&C:
                                                    self._y(0x0F)
                                                    self._a(0xFF)
                                                    while True:  # natural loop $BC28
                                                        try:
                                                            m[(0x6F73+r.y)&65535]=r.a
                                                            self._y(r.y-1)
                                                            self._mark(0xBC2C)
                                                            if not r.p&N:
                                                                continue
                                                            else:
                                                                pass
                                                            self._a(m[0x0038])
                                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBC31,0xBC34)):return
                                                            self._a(0x11)
                                                            m[0x0036]=r.a
                                                            self._a(0x00)
                                                            m[0x0037]=r.a
                                                            while True:  # natural loop $BC3E
                                                                try:
                                                                    self._y(m[0x0036])
                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                    self._compare(r.a,0xFF)
                                                                    self._mark(0xBC45)
                                                                    if r.p&Z:
                                                                        pass
                                                                    else:
                                                                        self._y(0x03)
                                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBC49,0xBC4C)):return
                                                                        self._compare(r.a,0x32)
                                                                        self._mark(0xBC4E)
                                                                        if not r.p&C:
                                                                            pass
                                                                        else:
                                                                            self._compare(r.a,0x5A)
                                                                            self._mark(0xBC52)
                                                                            if r.p&C:
                                                                                pass
                                                                            else:
                                                                                self._y(m[0x0036])
                                                                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                self._y(m[0x0037])
                                                                                m[(0x6F73+r.y)&65535]=r.a
                                                                                m[0x0037]=self._nz(m[0x0037]+1)
                                                                                pass
                                                                            pass
                                                                        pass
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x1B)
                                                                    self._mark(0xBC6A)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        pass
                                                                    self._a(m[0x0037])
                                                                    self._mark(0xBC6F)
                                                                    if r.p&Z:
                                                                        pass
                                                                    else:
                                                                        self._compare(r.a,0x01)
                                                                        self._mark(0xBC73)
                                                                        if r.p&Z:
                                                                            pass
                                                                        else:
                                                                            if not (yield from self._local_call(self.random_low_nibble_below,0xBC75,0xBC78)):return
                                                                            self._flag(C,False)
                                                                            self._add(0x01)
                                                                            pass
                                                                        self._y(r.a)
                                                                        self._a(m[(0x6F72+r.y)&65535])
                                                                        m[0x0037]=r.a
                                                                        self._a(m[0x0037])
                                                                        self._y(0x02)
                                                                        if not (yield from self._local_call(self.officer_field_pointer,0xBC87,0xBC8A)):return
                                                                        m[0x0000]=r.a
                                                                        self._a(m[0x003E])
                                                                        self._flag(C,True)
                                                                        self._add(m[0x0000],subtract=True)
                                                                        self._mark(0xBC92)
                                                                        if r.p&C:
                                                                            pass
                                                                        else:
                                                                            self._a(0x00)
                                                                            pass
                                                                        self._y(m[DIFFICULTY])
                                                                        self._flag(C,False)
                                                                        self._add(m[(0xBCAB+r.y)&65535])
                                                                        m[0x002A]=r.a
                                                                        self._a(0x64)
                                                                        if not (yield from self._local_call(self.random_below,0xBCA1,0xBCA4)):return
                                                                        self._compare(r.a,m[0x002A])
                                                                        self._mark(0xBCA6)
                                                                        if not r.p&C:
                                                                            self._a(m[0x003E])
                                                                            m[0x0021]=r.a
                                                                            self._a(0x14)
                                                                            m[0x0023]=r.a
                                                                            self._a(0x00)
                                                                            m[0x0022]=r.a
                                                                            m[0x0024]=r.a
                                                                            if not (yield from self._local_call(self.divide_domestic_word,0xBCBD,0xBCC0)):return
                                                                            self._a(0x07)
                                                                            if not (yield from self._local_call(self.random_low_nibble_below,0xBCC2,0xBCC5)):return
                                                                            self._flag(C,False)
                                                                            self._add(0x01)
                                                                            self._flag(C,False)
                                                                            self._add(m[0x0021])
                                                                            m[0x0039]=r.a
                                                                            self._a(m[0x0037])
                                                                            self._y(0x03)
                                                                            if not (yield from self._local_call(self.officer_field_pointer,0xBCD3,0xBCD6)):return
                                                                            self._flag(C,True)
                                                                            self._add(m[0x0039],subtract=True)
                                                                            self._mark(0xBCDA)
                                                                            if r.p&C:
                                                                                pass
                                                                            else:
                                                                                self._a(0x00)
                                                                                pass
                                                                            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                            self._a(m[RULER])
                                                                            if not (yield from self._local_call(self.ruler_pointer,0xBCE3,0xBCE6)):return
                                                                            self._y(0x00)
                                                                            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                            m[0x0039]=r.a
                                                                            self._a(m[0x0038])
                                                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBCF0,0xBCF3)):return
                                                                            m[0x003B]=r.a
                                                                            if not (yield from self._local_call(self.ruler_pointer,0xBCF6,0xBCF9)):return
                                                                            self._y(0x00)
                                                                            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                            m[0x003A]=r.a
                                                                            self._y(0x03)
                                                                            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                            m[0x6F44]=r.a
                                                                            self._a(0x00)
                                                                            m[0x0036]=r.a
                                                                            self._a(0xFF)
                                                                            m[0x003D]=r.a
                                                                            self._a(0x00)
                                                                            m[0x003E]=r.a
                                                                            while True:  # natural loop $BD16
                                                                                try:
                                                                                    self._a(m[0x0036])
                                                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBD19,0xBD1C)):return
                                                                                    self._compare(r.a,m[0x003B])
                                                                                    self._mark(0xBD1F)
                                                                                    if not r.p&Z:
                                                                                        pass
                                                                                    else:
                                                                                        self._a(m[0x003A])
                                                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_bd40,0xBD24,0xBD27)):return
                                                                                        pass
                                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                                    self._a(m[0x0036])
                                                                                    self._compare(r.a,0x1E)
                                                                                    self._mark(0xBD2F)
                                                                                    if not r.p&C:
                                                                                        continue
                                                                                    else:
                                                                                        pass
                                                                                    self._a(0xF9)
                                                                                    m[AI_REQUEST]=r.a
                                                                                    while True:  # natural loop $BD36
                                                                                        try:
                                                                                            self._a(m[AI_REQUEST])
                                                                                            self._mark(0xBD39)
                                                                                            if not r.p&Z:
                                                                                                continue
                                                                                            else:
                                                                                                pass
                                                                                            return (yield from self.city_development_strategy())
                                                                                        except _ContinueLoop_BD36:
                                                                                            continue
                                                                                except _ContinueLoop_BD16:
                                                                                    continue
                                                                        else:
                                                                            pass
                                                                        pass
                                                                    return (yield from self.city_development_strategy())
                                                                except _ContinueLoop_BC3E:
                                                                    continue
                                                        except _ContinueLoop_BC28:
                                                            continue
                                                else:
                                                    pass
                                                return (yield from self.city_development_strategy())
                                            except _ContinueLoop_BBE6:
                                                continue
                                    except _ContinueLoop_BBC1:
                                        continue
                            else:
                                self._compare(r.a,0x3C)
                                self._mark(0xB60B)
                                if not r.p&C:
                                    self._a(0x00)
                                    m[0x0036]=r.a
                                    m[0x0039]=r.a
                                    self._a(0xFF)
                                    m[0x0037]=r.a
                                    m[0x0038]=r.a
                                    while True:  # natural loop $B99B
                                        try:
                                            self._a(m[0x0036])
                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB99E,0xB9A1)):return
                                            self._compare(r.a,m[RULER])
                                            self._mark(0xB9A4)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.domesticcooperationcontroller_bb82,0xB9A6,0xB9A9)):return
                                                self._a(m[0x0036])
                                                if not (yield from self._local_call(self.count_prefix_officers,0xB9AC,0xB9AF)):return
                                                self._compare(r.a,0x0A)
                                                self._mark(0xB9B1)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._compare(r.a,m[0x0037])
                                                    self._mark(0xB9B6)
                                                    if r.p&C:
                                                        pass
                                                    else:
                                                        m[0x0037]=r.a
                                                        self._a(m[0x0036])
                                                        m[0x0038]=r.a
                                                        pass
                                                    pass
                                                pass
                                            m[0x0036]=self._nz(m[0x0036]+1)
                                            self._a(m[0x0036])
                                            self._compare(r.a,0x1E)
                                            self._mark(0xB9C9)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._a(m[0x0038])
                                            self._compare(r.a,0xFF)
                                            self._mark(0xB9D0)
                                            if not r.p&Z:
                                                self._a(0x00)
                                                m[0x0036]=r.a
                                                self._a(0xFF)
                                                m[0x003D]=r.a
                                                m[0x003E]=r.a
                                                m[0x003F]=r.a
                                                while True:  # natural loop $B9E5
                                                    try:
                                                        self._a(m[0x0036])
                                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB9E8,0xB9EB)):return
                                                        self._compare(r.a,m[RULER])
                                                        self._mark(0xB9EE)
                                                        if r.p&Z:
                                                            pass
                                                        else:
                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_bb48,0xB9F0,0xB9F3)):return
                                                            pass
                                                        m[0x0036]=self._nz(m[0x0036]+1)
                                                        self._a(m[0x0036])
                                                        self._compare(r.a,0x1E)
                                                        self._mark(0xB9FB)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[0x003E])
                                                        self._compare(r.a,0x46)
                                                        self._mark(0xBA02)
                                                        if not r.p&C:
                                                            self._a(m[0x003D])
                                                            self._y(0x04)
                                                            if not (yield from self._local_call(self.officer_field_pointer,0xBA0C,0xBA0F)):return
                                                            m[0x0021]=r.a
                                                            self._y(0x0B)
                                                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            r.a=self._shift(r.a,False,rotate=False)
                                                            m[0x0020]=r.a
                                                            self._a(m[0x0039])
                                                            self._flag(C,True)
                                                            self._add(m[0x0020],subtract=True)
                                                            m[0x0039]=r.a
                                                            self._y(0x02)
                                                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                            self._flag(C,False)
                                                            self._add(m[0x0021])
                                                            self._a(0x14)
                                                            m[0x0023]=r.a
                                                            self._a(0x00)
                                                            m[0x0022]=r.a
                                                            m[0x0024]=r.a
                                                            if not (yield from self._local_call(self.divide_domestic_word,0xBA35,0xBA38)):return
                                                            self._a(m[0x003E])
                                                            self._y(0x00)
                                                            self._compare(r.a,0x1F)
                                                            self._mark(0xBA3F)
                                                            if not r.p&C:
                                                                pass
                                                            else:
                                                                self._y(r.y+1)
                                                                self._compare(r.a,0x33)
                                                                self._mark(0xBA44)
                                                                if not r.p&C:
                                                                    pass
                                                                else:
                                                                    self._y(r.y+1)
                                                                    pass
                                                                pass
                                                            m[0x0020]=r.y
                                                            self._a(m[DIFFICULTY])
                                                            r.a=self._shift(r.a,True,rotate=False)
                                                            r.a=self._shift(r.a,True,rotate=False)
                                                            self._a(r.a | m[0x0020])
                                                            self._y(r.a)
                                                            self._a(m[(0xBA81+r.y)&65535])
                                                            self._flag(C,False)
                                                            self._add(m[0x0021])
                                                            m[0x002A]=r.a
                                                            self._a(m[0x0039])
                                                            self._mark(0xBA5C)
                                                            if not r.p&N:
                                                                self._flag(C,False)
                                                                self._add(m[0x002A])
                                                                m[0x002A]=r.a
                                                                pass
                                                            else:
                                                                self._a(r.a ^ 0xFF)
                                                                self._flag(C,False)
                                                                self._add(0x01)
                                                                r.a=self._shift(r.a,True,rotate=False)
                                                                m[0x0020]=r.a
                                                                self._a(m[0x002A])
                                                                self._flag(C,True)
                                                                self._add(m[0x0020],subtract=True)
                                                                m[0x002A]=r.a
                                                                pass
                                                            self._a(0x64)
                                                            if not (yield from self._local_call(self.random_below,0xBA77,0xBA7A)):return
                                                            self._compare(r.a,m[0x002A])
                                                            self._mark(0xBA7C)
                                                            if not r.p&C:
                                                                self._a(m[0x0038])
                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBA90,0xBA93)):return
                                                                self._y(0x10)
                                                                while True:  # natural loop $BA95
                                                                    try:
                                                                        self._y(r.y+1)
                                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                        self._compare(r.a,0xFF)
                                                                        self._mark(0xBA9A)
                                                                        if not r.p&Z:
                                                                            continue
                                                                        else:
                                                                            pass
                                                                        self._a(m[0x003D])
                                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                        self._a(m[RULER])
                                                                        if not (yield from self._local_call(self.ruler_pointer,0xBAA4,0xBAA7)):return
                                                                        self._y(0x00)
                                                                        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                        m[0x0030]=r.a
                                                                        self._a(m[0x003D])
                                                                        m[0x0031]=r.a
                                                                        if not (yield from self._local_call(self.recalculate_recruited_loyalty,0xBAB2,0xBAB5)):return
                                                                        self._a(m[0x003F])
                                                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBAB8,0xBABB)):return
                                                                        m[0x0042]=r.a
                                                                        self._y(0x10)
                                                                        while True:  # natural loop $BAC0
                                                                            try:
                                                                                self._y(r.y+1)
                                                                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                self._compare(r.a,m[0x003D])
                                                                                self._mark(0xBAC6)
                                                                                if not r.p&Z:
                                                                                    continue
                                                                                else:
                                                                                    pass
                                                                                self._a(0xFF)
                                                                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                self._a(m[0x003F])
                                                                                if not (yield from self._local_call(self.compact_city_roster,0xBACF,0xBAD2)):return
                                                                                self._a(m[0x003F])
                                                                                if not (yield from self._local_call(self.count_prefix_officers,0xBAD5,0xBAD8)):return
                                                                                self._compare(r.a,0x00)
                                                                                self._mark(0xBADA)
                                                                                if not r.p&Z:
                                                                                    pass
                                                                                else:
                                                                                    self._y(0x00)
                                                                                    self._a(0x07)
                                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                    pass
                                                                                self._a(m[0x003D])
                                                                                m[0x0043]=r.a
                                                                                self._a(m[0x0038])
                                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBAEB,0xBAEE)):return
                                                                                if not (yield from self._local_call(self.ruler_pointer,0xBAEE,0xBAF1)):return
                                                                                self._y(0x00)
                                                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                m[0x0040]=r.a
                                                                                self._a(m[0x0042])
                                                                                if not (yield from self._local_call(self.ruler_pointer,0xBAFB,0xBAFE)):return
                                                                                self._y(0x00)
                                                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                m[0x0041]=r.a
                                                                                self._y(0x03)
                                                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                self._compare(r.a,0x03)
                                                                                self._mark(0xBB0B)
                                                                                if r.p&Z:
                                                                                    pass
                                                                                else:
                                                                                    self._a(0x00)
                                                                                    m[0x0036]=r.a
                                                                                    self._a(0xFF)
                                                                                    m[0x003D]=r.a
                                                                                    self._a(0x00)
                                                                                    m[0x003E]=r.a
                                                                                    while True:  # natural loop $BB1C
                                                                                        try:
                                                                                            self._a(m[0x0036])
                                                                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBB1F,0xBB22)):return
                                                                                            self._compare(r.a,0x07)
                                                                                            self._mark(0xBB24)
                                                                                            if r.p&Z:
                                                                                                pass
                                                                                            else:
                                                                                                self._compare(r.a,m[0x0042])
                                                                                                self._mark(0xBB29)
                                                                                                if not r.p&Z:
                                                                                                    pass
                                                                                                else:
                                                                                                    self._a(m[0x0041])
                                                                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_bd40,0xBB2E,0xBB31)):return
                                                                                                    pass
                                                                                                pass
                                                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                                                            self._a(m[0x0036])
                                                                                            self._compare(r.a,0x1E)
                                                                                            self._mark(0xBB39)
                                                                                            if not r.p&C:
                                                                                                continue
                                                                                            else:
                                                                                                pass
                                                                                            self._a(0xFA)
                                                                                            m[AI_REQUEST]=r.a
                                                                                            while True:  # natural loop $BB40
                                                                                                try:
                                                                                                    self._a(m[AI_REQUEST])
                                                                                                    self._mark(0xBB43)
                                                                                                    if not r.p&Z:
                                                                                                        continue
                                                                                                    else:
                                                                                                        pass
                                                                                                    return (yield from self.city_development_strategy())
                                                                                                except _ContinueLoop_BB40:
                                                                                                    continue
                                                                                        except _ContinueLoop_BB1C:
                                                                                            continue
                                                                                return (yield from self.city_development_strategy())
                                                                            except _ContinueLoop_BAC0:
                                                                                continue
                                                                    except _ContinueLoop_BA95:
                                                                        continue
                                                            else:
                                                                pass
                                                            pass
                                                        else:
                                                            pass
                                                        return (yield from self.city_development_strategy())
                                                    except _ContinueLoop_B9E5:
                                                        continue
                                            else:
                                                pass
                                            return (yield from self.city_development_strategy())
                                        except _ContinueLoop_B99B:
                                            continue
                                else:
                                    self._a(m[RULER])
                                    if not (yield from self._local_call(self.ruler_pointer,0xB61C,0xB61F)):return
                                    self._y(0x00)
                                    self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                    m[0x0040]=r.a
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_b837,0xB626,0xB629)):return
                                    self._a(m[0x003D])
                                    self._compare(r.a,0xFF)
                                    self._mark(0xB62E)
                                    if r.p&Z:
                                        pass
                                    else:
                                        m[0x0042]=r.a
                                        self._a(0x00)
                                        m[0x002A]=r.a
                                        m[0x002B]=r.a
                                        while True:  # natural loop $B639
                                            try:
                                                self._a(m[0x002A])
                                                if not (yield from self._local_call(self.ruler_pointer,0xB63B,0xB63E)):return
                                                self._y(0x00)
                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                self._compare(r.a,0xFF)
                                                self._mark(0xB644)
                                                if r.p&Z:
                                                    pass
                                                else:
                                                    m[0x002B]=self._nz(m[0x002B]+1)
                                                    pass
                                                m[0x002A]=self._nz(m[0x002A]+1)
                                                self._a(m[0x002A])
                                                self._compare(r.a,0x07)
                                                self._mark(0xB64E)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[0x002B])
                                                self._compare(r.a,0x03)
                                                self._mark(0xB654)
                                                if r.p&C:
                                                    self._a(m[RULER])
                                                    if not (yield from self._local_call(self.ruler_pointer,0xB65C,0xB65F)):return
                                                    self._x(0x00)
                                                    self._y(0x04)
                                                    self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                    self._y(0x05)
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                    self._y(0x06)
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                    self._y(0x07)
                                                    self._flag(C,False)
                                                    self._add(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                    self._compare(r.a,0x00)
                                                    self._mark(0xB676)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_b898,0xB678,0xB67B)):return
                                                        self._compare(r.x,0x02)
                                                        self._mark(0xB67D)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._y(0x00)
                                                            m[0x0036]=r.y
                                                            m[0x0037]=r.y
                                                            m[0x0038]=r.y
                                                            while True:  # natural loop $B68A
                                                                try:
                                                                    self._y(m[0x0036])
                                                                    self._a(m[(0x6F73+r.y)&65535])
                                                                    self._mark(0xB690)
                                                                    if not r.p&Z:
                                                                        pass
                                                                    else:
                                                                        self._a(m[0x0036])
                                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d080,0xB695,0xB698)):return
                                                                        self._a(m[0x002B])
                                                                        self._compare(r.a,m[0x0037])
                                                                        self._mark(0xB69D)
                                                                        if not r.p&C:
                                                                            pass
                                                                        else:
                                                                            m[0x0037]=r.a
                                                                            self._a(m[0x0036])
                                                                            m[0x0038]=r.a
                                                                            pass
                                                                        pass
                                                                    m[0x0036]=self._nz(m[0x0036]+1)
                                                                    self._a(m[0x0036])
                                                                    self._compare(r.a,0x07)
                                                                    self._mark(0xB6B0)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        pass
                                                                    self._a(m[RULER])
                                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_d080,0xB6B5,0xB6B8)):return
                                                                    self._a(m[0x002B])
                                                                    self._flag(C,False)
                                                                    self._add(0x02)
                                                                    self._compare(r.a,m[0x0037])
                                                                    self._mark(0xB6C0)
                                                                    if not r.p&C:
                                                                        self._a(m[0x0037])
                                                                        m[0x0020]=r.a
                                                                        self._a(0x1E)
                                                                        m[0x0021]=r.a
                                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xB6CE,0xB6D1)):return
                                                                        self._a(m[0x002A])
                                                                        self._flag(C,False)
                                                                        self._add(0x46)
                                                                        m[0x0021]=r.a
                                                                        self._a(m[0x002B])
                                                                        self._add(0x00)
                                                                        m[0x0022]=r.a
                                                                        self._a(0x0A)
                                                                        m[0x0023]=r.a
                                                                        self._a(0x00)
                                                                        m[0x0024]=r.a
                                                                        if not (yield from self._local_call(self.divide_domestic_word,0xB6E6,0xB6E9)):return
                                                                        self._a(m[0x0021])
                                                                        m[0x042F]=r.a
                                                                        self._a(m[0x0022])
                                                                        m[0x0430]=r.a
                                                                        m[0x042F]=self._shift(m[0x042F],True,rotate=False)
                                                                        m[0x0430]=self._shift(m[0x0430],True,rotate=True)
                                                                        m[0x042F]=self._shift(m[0x042F],True,rotate=False)
                                                                        m[0x0430]=self._shift(m[0x0430],True,rotate=True)
                                                                        self._a(0x00)
                                                                        m[0x0431]=r.a
                                                                        self._a(0x00)
                                                                        m[0x0039]=r.a
                                                                        self._a(0x64)
                                                                        if not (yield from self._local_call(self.random_below,0xB70B,0xB70E)):return
                                                                        self._compare(r.a,0x32)
                                                                        self._mark(0xB710)
                                                                        if not r.p&C:
                                                                            pass
                                                                        else:
                                                                            self._a(0x01)
                                                                            m[0x0039]=r.a
                                                                            self._a(m[0x0021])
                                                                            m[0x0020]=r.a
                                                                            self._a(m[0x0022])
                                                                            m[0x0021]=r.a
                                                                            self._a(0x00)
                                                                            m[0x0022]=r.a
                                                                            self._a(0x06)
                                                                            m[0x0023]=r.a
                                                                            if not (yield from self._local_call(self.multiply_domestic_word,0xB727,0xB72A)):return
                                                                            self._a(m[0x0026])
                                                                            m[0x042F]=r.a
                                                                            self._a(m[0x0027])
                                                                            m[0x0430]=r.a
                                                                            self._a(0x00)
                                                                            m[0x0431]=r.a
                                                                            pass
                                                                        self._a(m[0x042F])
                                                                        m[0x003A]=r.a
                                                                        self._a(m[0x0431])
                                                                        m[0x003B]=r.a
                                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_b7a2,0xB746,0xB749)):return
                                                                        self._mark(0xB749)
                                                                        if r.p&C:
                                                                            self._a(m[0x0038])
                                                                            if not (yield from self._local_call(self.ruler_pointer,0xB751,0xB754)):return
                                                                            self._y(0x03)
                                                                            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                            self._compare(r.a,0x03)
                                                                            self._mark(0xB75A)
                                                                            if not r.p&Z:
                                                                                self._a(m[RULER])
                                                                                if not (yield from self._local_call(self.ruler_pointer,0xB768,0xB76B)):return
                                                                                self._y(0x00)
                                                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                m[0x0040]=r.a
                                                                                self._a(m[0x0038])
                                                                                if not (yield from self._local_call(self.ruler_pointer,0xB775,0xB778)):return
                                                                                self._y(0x00)
                                                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                m[0x0041]=r.a
                                                                                self._y(0x03)
                                                                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                m[0x6F44]=r.a
                                                                                self._a(0xF8)
                                                                                m[AI_REQUEST]=r.a
                                                                                while True:  # natural loop $B78B
                                                                                    try:
                                                                                        self._a(m[AI_REQUEST])
                                                                                        self._compare(r.a,0xF8)
                                                                                        self._mark(0xB790)
                                                                                        if r.p&Z:
                                                                                            continue
                                                                                        else:
                                                                                            pass
                                                                                        self._compare(r.a,0x00)
                                                                                        self._mark(0xB794)
                                                                                        if r.p&Z:
                                                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_b90a,0xB799,0xB79C)):return
                                                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_b7ce,0xB79C,0xB79F)):return
                                                                                            pass
                                                                                        else:
                                                                                            pass
                                                                                        return (yield from self.city_development_strategy())
                                                                                    except _ContinueLoop_B78B:
                                                                                        continue
                                                                            else:
                                                                                if not (yield from self._local_call(self.domesticcooperationcontroller_b90a,0xB75C,0xB75F)):return
                                                                                if not (yield from self._local_call(self.domesticcooperationcontroller_b7ce,0xB75F,0xB762)):return
                                                                                pass
                                                                            pass
                                                                        else:
                                                                            pass
                                                                        pass
                                                                    else:
                                                                        pass
                                                                    return (yield from self.city_development_strategy())
                                                                except _ContinueLoop_B68A:
                                                                    continue
                                                        pass
                                                    pass
                                                else:
                                                    pass
                                                return (yield from self.city_development_strategy())
                                            except _ContinueLoop_B639:
                                                continue
                                    pass
                                pass
                            return (yield from self.city_development_strategy())
                        except _ContinueLoop_B5FC:
                            continue
            except _ContinueLoop_B49C:
                continue

    def domesticcooperationcontroller_b53e(self):
        """$B53E: domesticcooperationcontroller b53e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB53E)
        self._a(m[0x0036])
        m[0x003B]=r.a
        self._a(0x00)
        m[0x0036]=r.a
        self._a(0xFF)
        m[0x003C]=r.a
        m[0x003D]=r.a
        while True:  # natural loop $B551
            try:
                self._a(m[0x0036])
                self._compare(r.a,m[0x0045])
                self._mark(0xB557)
                if r.p&Z:
                    self._x(m[0x003B])
                    self._y(m[0x0036])
                    if not (yield from self._local_call(self.common_connectivity_bits,0xB56C,0xB56F)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xB571)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0036])
                        if not (yield from self._local_call(self.count_prefix_officers,0xB576,0xB579)):return
                        self._compare(r.a,m[0x003C])
                        self._mark(0xB57C)
                        if r.p&C:
                            pass
                        else:
                            self._compare(r.a,0x0A)
                            self._mark(0xB580)
                            if r.p&C:
                                pass
                            else:
                                m[0x003C]=r.a
                                self._a(m[0x0036])
                                m[0x003D]=r.a
                                pass
                            pass
                        pass
                    pass
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB559,0xB55C)):return
                    self._compare(r.a,m[RULER])
                    self._mark(0xB55F)
                    if not r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.build_enemy_neighbor_list,0xB561,0xB564)):return
                        self._mark(0xB564)
                        if r.p&Z:
                            pass
                        else:
                            self._x(m[0x003B])
                            self._y(m[0x0036])
                            if not (yield from self._local_call(self.common_connectivity_bits,0xB56C,0xB56F)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xB571)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.count_prefix_officers,0xB576,0xB579)):return
                                self._compare(r.a,m[0x003C])
                                self._mark(0xB57C)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0A)
                                    self._mark(0xB580)
                                    if r.p&C:
                                        pass
                                    else:
                                        m[0x003C]=r.a
                                        self._a(m[0x0036])
                                        m[0x003D]=r.a
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xB593)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x003D])
                self._compare(r.a,0xFF)
                self._mark(0xB59A)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x003B])
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB59F,0xB5A2)):return
                    self._a(0x11)
                    m[0x0024]=r.a
                    self._a(0x00)
                    m[0x0025]=r.a
                    m[0x0026]=r.a
                    while True:  # natural loop $B5AC
                        try:
                            self._y(m[0x0024])
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xB5B2)
                            if r.p&Z:
                                pass
                            else:
                                self._y(0x01)
                                if not (yield from self._local_call(self.officer_field_pointer,0xB5B6,0xB5B9)):return
                                self._compare(r.a,m[0x0025])
                                self._mark(0xB5BB)
                                if not r.p&C:
                                    pass
                                else:
                                    m[0x0025]=r.a
                                    self._y(m[0x0024])
                                    m[0x0026]=r.y
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[0x003A]=r.a
                                    pass
                                pass
                            m[0x0024]=self._nz(m[0x0024]+1)
                            self._a(m[0x0024])
                            self._compare(r.a,0x1B)
                            self._mark(0xB5CE)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._y(m[0x0026])
                            self._a(0xFF)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._a(m[0x003B])
                            if not (yield from self._local_call(self.compact_city_roster,0xB5D9,0xB5DC)):return
                            self._a(m[0x003D])
                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB5DF,0xB5E2)):return
                            self._y(0x10)
                            while True:  # natural loop $B5E4
                                try:
                                    self._y(r.y+1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._compare(r.a,0xFF)
                                    self._mark(0xB5E9)
                                    if not r.p&Z:
                                        continue
                                    else:
                                        pass
                                    self._a(m[0x003A])
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._a(0x02)
                                    if not (yield from self._local_call(self.charge_nested_budget_one,0xB5F2,0xB5F5)):return
                                    self._a(m[0x003B])
                                    m[0x0036]=r.a
                                    self._mark(0xB5FB)
                                    self._rts();return
                                except _ContinueLoop_B5E4:
                                    continue
                        except _ContinueLoop_B5AC:
                            continue
                self._a(m[0x003B])
                m[0x0036]=r.a
                self._mark(0xB5FB)
                self._rts();return
            except _ContinueLoop_B551:
                continue

    def domesticcooperationcontroller_b7a2(self):
        """$B7A2: domesticcooperationcontroller b7a2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB7A2)
        self._a(m[RULER])
        if not (yield from self._local_call(self.domesticcooperationcontroller_b955,0xB7A5,0xB7A8)):return
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB7A8,0xB7AB)):return
        self._a(m[0x0039])
        self._mark(0xB7AE)
        if not r.p&Z:
            self._y(0x04)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x042F],subtract=True)
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._add(m[0x0430],subtract=True)
            self._mark(0xB7CD)
            self._rts();return
        else:
            self._y(0x02)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x042F],subtract=True)
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._add(m[0x0430],subtract=True)
            self._mark(0xB7BE)
            self._rts();return

    def domesticcooperationcontroller_b7ce(self):
        """$B7CE: domesticcooperationcontroller b7ce; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB7CE)
        self._a(m[RULER])
        if not (yield from self._local_call(self.domesticcooperationcontroller_b955,0xB7D1,0xB7D4)):return
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB7D4,0xB7D7)):return
        self._a(m[0x0039])
        self._mark(0xB7DA)
        if not r.p&Z:
            self._y(0x04)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x003A],subtract=True)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._add(m[0x003B],subtract=True)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            pass
        else:
            self._y(0x02)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x003A],subtract=True)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._add(m[0x003B],subtract=True)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            pass
        self._a(m[0x0038])
        if not (yield from self._local_call(self.domesticcooperationcontroller_b955,0xB806,0xB809)):return
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB809,0xB80C)):return
        self._a(m[0x0039])
        self._mark(0xB80F)
        if not r.p&Z:
            self._y(0x04)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x003A])
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._add(m[0x003B])
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._mark(0xB836)
            self._rts();return
        else:
            self._y(0x02)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x003A])
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._add(m[0x003B])
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._mark(0xB823)
            self._rts();return

    def domesticcooperationcontroller_b837(self):
        """$B837: domesticcooperationcontroller b837; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB837)
        self._a(0x00)
        m[0x0036]=r.a
        self._a(0xFF)
        m[0x003D]=r.a
        self._a(0x00)
        m[0x003E]=r.a
        while True:  # natural loop $B846
            try:
                self._a(m[0x0036])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB849,0xB84C)):return
                self._compare(r.a,m[RULER])
                self._mark(0xB84F)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_b85f,0xB851,0xB854)):return
                    pass
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xB85C)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB85E)
                self._rts();return
            except _ContinueLoop_B846:
                continue

    def domesticcooperationcontroller_b85f(self):
        """$B85F: domesticcooperationcontroller b85f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB85F)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB862,0xB865)):return
        self._a(0x11)
        m[0x003C]=r.a
        while True:  # natural loop $B86A
            try:
                self._y(m[0x003C])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB871)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,m[0x0040])
                    self._mark(0xB876)
                    if r.p&Z:
                        pass
                    else:
                        self._y(0x03)
                        if not (yield from self._local_call(self.officer_field_pointer,0xB87A,0xB87D)):return
                        self._compare(r.a,m[0x003E])
                        self._mark(0xB880)
                        if not r.p&C:
                            pass
                        else:
                            m[0x003E]=r.a
                            self._y(m[0x003C])
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            m[0x003D]=r.a
                            pass
                        pass
                    pass
                m[0x003C]=self._nz(m[0x003C]+1)
                self._a(m[0x003C])
                self._compare(r.a,0x1B)
                self._mark(0xB895)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB897)
                self._rts();return
            except _ContinueLoop_B86A:
                continue

    def domesticcooperationcontroller_b898(self):
        """$B898: domesticcooperationcontroller b898; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB898)
        self._y(0x30)
        yield from self._external(0xB89A,0xF266,0xB89D,"call",None)
        if r.pc!=0xB89D:return  # preserve nonlocal stack return
        self._y(0x07)
        while True:  # natural loop $B89F
            try:
                self._a(0xFF)
                m[(0x6F73+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xB8A5)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(0x00)
                m[0x0036]=r.a
                m[0x0037]=r.a
                while True:  # natural loop $B8AF
                    try:
                        self._a(0x00)
                        m[0x0039]=r.a
                        self._a(m[0x0036])
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB8B7,0xB8BA)):return
                        self._compare(r.a,m[RULER])
                        self._mark(0xB8BD)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0036])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._y(r.a)
                            while True:  # natural loop $B8C6
                                try:
                                    self._a(m[(0x9D72+r.y)&65535])
                                    self._mark(0xB8C9)
                                    if r.p&N:
                                        pass
                                    else:
                                        m[0x0023]=r.a
                                        m[0x0024]=r.y
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB8CF,0xB8D2)):return
                                        self._compare(r.a,0x07)
                                        self._mark(0xB8D4)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._compare(r.a,m[RULER])
                                            self._mark(0xB8D9)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._y(r.a)
                                                self._a(0x00)
                                                m[(0x6F73+r.y)&65535]=r.a
                                                pass
                                            pass
                                        self._a(m[0x0023])
                                        self._y(m[0x0024])
                                        self._y(r.y+1)
                                        m[0x0039]=self._nz(m[0x0039]+1)
                                        self._x(m[0x0039])
                                        self._compare(r.x,0x08)
                                        self._mark(0xB8EE)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        pass
                                    m[0x0036]=self._nz(m[0x0036]+1)
                                    self._a(m[0x0036])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xB8F8)
                                    if not r.p&C:
                                        raise _ContinueLoop_B8AF
                                    else:
                                        pass
                                    self._y(0x00)
                                    self._x(0x00)
                                    while True:  # natural loop $B8FE
                                        try:
                                            self._a(m[(0x6F73+r.y)&65535])
                                            self._mark(0xB901)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._x(r.x+1)
                                                pass
                                            self._y(r.y+1)
                                            self._compare(r.y,0x07)
                                            self._mark(0xB907)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._mark(0xB909)
                                            self._rts();return
                                        except _ContinueLoop_B8FE:
                                            continue
                                except _ContinueLoop_B8C6:
                                    continue
                        m[0x0036]=self._nz(m[0x0036]+1)
                        self._a(m[0x0036])
                        self._compare(r.a,0x1E)
                        self._mark(0xB8F8)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(0x00)
                        self._x(0x00)
                        while True:  # natural loop $B8FE
                            try:
                                self._a(m[(0x6F73+r.y)&65535])
                                self._mark(0xB901)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._x(r.x+1)
                                    pass
                                self._y(r.y+1)
                                self._compare(r.y,0x07)
                                self._mark(0xB907)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xB909)
                                self._rts();return
                            except _ContinueLoop_B8FE:
                                continue
                    except _ContinueLoop_B8AF:
                        continue
            except _ContinueLoop_B89F:
                continue

    def domesticcooperationcontroller_b90a(self):
        """$B90A: domesticcooperationcontroller b90a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB90A)
        self._a(m[RULER])
        if not (yield from self._local_call(self.ruler_pointer,0xB90D,0xB910)):return
        self._a(m[0x0038])
        if not (yield from self._local_call(self.domesticcooperationcontroller_b923,0xB913,0xB916)):return
        self._a(m[0x0038])
        if not (yield from self._local_call(self.ruler_pointer,0xB919,0xB91C)):return
        self._a(m[RULER])
        if not (yield from self._local_call(self.domesticcooperationcontroller_b923,0xB91F,0xB922)):return
        self._mark(0xB922)
        self._rts();return

    def domesticcooperationcontroller_b923(self):
        """$B923: domesticcooperationcontroller b923; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB923)
        self._y(0x04)
        self._compare(r.a,0x00)
        self._mark(0xB927)
        if r.p&Z:
            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
            self._a(r.a & 0xF0)
            self._a(r.a | 0x0A)
            m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
            self._mark(0xB94B)
            self._rts();return
        else:
            self._compare(r.a,0x01)
            self._mark(0xB92B)
            if r.p&Z:
                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                self._a(r.a & 0x0F)
                self._a(r.a | 0xA0)
                m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
                self._mark(0xB954)
                self._rts();return
            else:
                self._y(0x05)
                self._compare(r.a,0x02)
                self._mark(0xB931)
                if r.p&Z:
                    self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                    self._a(r.a & 0xF0)
                    self._a(r.a | 0x0A)
                    m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
                    self._mark(0xB94B)
                    self._rts();return
                else:
                    self._compare(r.a,0x03)
                    self._mark(0xB935)
                    if r.p&Z:
                        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                        self._a(r.a & 0x0F)
                        self._a(r.a | 0xA0)
                        m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
                        self._mark(0xB954)
                        self._rts();return
                    else:
                        self._y(0x06)
                        self._compare(r.a,0x04)
                        self._mark(0xB93B)
                        if r.p&Z:
                            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                            self._a(r.a & 0xF0)
                            self._a(r.a | 0x0A)
                            m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
                            self._mark(0xB94B)
                            self._rts();return
                        else:
                            self._compare(r.a,0x05)
                            self._mark(0xB93F)
                            if r.p&Z:
                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                self._a(r.a & 0x0F)
                                self._a(r.a | 0xA0)
                                m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
                                self._mark(0xB954)
                                self._rts();return
                            else:
                                self._y(0x07)
                                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                self._a(r.a & 0xF0)
                                self._a(r.a | 0x0A)
                                m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
                                self._mark(0xB94B)
                                self._rts();return

    def domesticcooperationcontroller_b955(self):
        """$B955: domesticcooperationcontroller b955; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB955)
        m[0x002C]=r.a
        self._y(0x00)
        m[0x002B]=r.y
        if not (yield from self._local_call(self.ruler_pointer,0xB95B,0xB95E)):return
        self._y(0x00)
        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
        m[0x002A]=r.a
        while True:  # natural loop $B964
            try:
                self._a(m[0x002B])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xB966,0xB969)):return
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x002C])
                self._mark(0xB96D)
                if not r.p&Z:
                    m[0x002B]=self._nz(m[0x002B]+1)
                    self._a(m[0x002B])
                    self._compare(r.a,0x1E)
                    self._mark(0xB985)
                    if not r.p&C:
                        continue
                    else:
                        self._a(0xFF)
                        self._flag(C,False)
                        self._mark(0xB98A)
                        self._rts();return
                else:
                    self._y(0x11)
                    while True:  # natural loop $B971
                        try:
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._compare(r.a,m[0x002A])
                            self._mark(0xB975)
                            if not r.p&Z:
                                self._y(r.y+1)
                                self._compare(r.y,0x1B)
                                self._mark(0xB97D)
                                if not r.p&C:
                                    continue
                                else:
                                    m[0x002B]=self._nz(m[0x002B]+1)
                                    self._a(m[0x002B])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xB985)
                                    if not r.p&C:
                                        raise _ContinueLoop_B964
                                    else:
                                        self._a(0xFF)
                                        self._flag(C,False)
                                        self._mark(0xB98A)
                                        self._rts();return
                            else:
                                self._a(m[0x002B])
                                self._mark(0xB979)
                                self._rts();return
                        except _ContinueLoop_B971:
                            continue
            except _ContinueLoop_B964:
                continue

    def domesticcooperationcontroller_bb48(self):
        """$BB48: domesticcooperationcontroller bb48; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB48)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBB4B,0xBB4E)):return
        self._a(0x11)
        m[0x003C]=r.a
        while True:  # natural loop $BB53
            try:
                self._y(m[0x003C])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xBB5A)
                if r.p&Z:
                    pass
                else:
                    self._y(0x03)
                    if not (yield from self._local_call(self.officer_field_pointer,0xBB5E,0xBB61)):return
                    self._compare(r.a,m[0x003E])
                    self._mark(0xBB64)
                    if r.p&C:
                        pass
                    else:
                        m[0x003E]=r.a
                        self._y(m[0x003C])
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        m[0x003D]=r.a
                        self._a(m[0x0036])
                        m[0x003F]=r.a
                        pass
                    pass
                m[0x003C]=self._nz(m[0x003C]+1)
                self._a(m[0x003C])
                self._compare(r.a,0x1B)
                self._mark(0xBB7F)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xBB81)
                self._rts();return
            except _ContinueLoop_BB53:
                continue

    def domesticcooperationcontroller_bb82(self):
        """$BB82: domesticcooperationcontroller bb82; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB82)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBB85,0xBB88)):return
        self._a(0x11)
        m[0x003C]=r.a
        while True:  # natural loop $BB8D
            try:
                self._y(m[0x003C])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xBB94)
                if r.p&Z:
                    pass
                else:
                    self._y(0x0B)
                    if not (yield from self._local_call(self.officer_field_pointer,0xBB98,0xBB9B)):return
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._compare(r.a,m[0x0039])
                    self._mark(0xBBA2)
                    if not r.p&C:
                        pass
                    else:
                        m[0x0039]=r.a
                        pass
                    pass
                m[0x003C]=self._nz(m[0x003C]+1)
                self._a(m[0x003C])
                self._compare(r.a,0x1B)
                self._mark(0xBBAF)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xBBB1)
                self._rts();return
            except _ContinueLoop_BB8D:
                continue

    def domesticcooperationcontroller_bd3e(self):
        """$BD3E: domesticcooperationcontroller bd3e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD3E)
        self._a(0xFF)
        return (yield from self.domesticcooperationcontroller_bd40())

    def domesticcooperationcontroller_bd40(self):
        """$BD40: domesticcooperationcontroller bd40; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD40)
        m[0x002A]=r.a
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBD45,0xBD48)):return
        self._a(0x11)
        m[0x003C]=r.a
        while True:  # natural loop $BD4D
            try:
                self._y(m[0x003C])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xBD54)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,m[0x002A])
                    self._mark(0xBD58)
                    if r.p&Z:
                        pass
                    else:
                        self._y(0x02)
                        if not (yield from self._local_call(self.officer_field_pointer,0xBD5C,0xBD5F)):return
                        self._compare(r.a,m[0x003E])
                        self._mark(0xBD62)
                        if not r.p&C:
                            pass
                        else:
                            m[0x003E]=r.a
                            self._y(m[0x003C])
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            m[0x003D]=r.a
                            pass
                        pass
                    pass
                m[0x003C]=self._nz(m[0x003C]+1)
                self._a(m[0x003C])
                self._compare(r.a,0x1B)
                self._mark(0xBD77)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xBD79)
                self._rts();return
            except _ContinueLoop_BD4D:
                continue

    def city_development_strategy(self):
        """$BEC7: city development strategy; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $BEC7
            try:
                self._mark(0xBEC7)
                if not (yield from self._local_call(self.scan_next_owned_city,0xBEC7,0xBECA)):return
                self._a(0x50)
                if not (yield from self._local_call(self.random_below,0xBECC,0xBECF)):return
                self._push(r.a)
                self._a(m[RULER])
                self._a(r.a & 0x07)
                self._y(r.a)
                self._a(self._pop())
                self._compare(r.a,m[(0xBEDF+r.y)&65535])
                self._mark(0xBEDA)
                if not r.p&C:
                    self._a(0x64)
                    if not (yield from self._local_call(self.random_below,0xBF18,0xBF1B)):return
                    self._compare(r.a,0x28)
                    self._mark(0xBF1D)
                    if r.p&C:
                        self._compare(r.a,0x46)
                        self._mark(0xBF24)
                        if r.p&C:
                            self._compare(r.a,0x5A)
                            self._mark(0xBF2B)
                            if r.p&C:
                                self._a(0x1E)
                                m[0x0022]=r.a
                                self._a(0x00)
                                m[0x0023]=r.a
                                self._a(0x1E)
                                m[0x0024]=r.a
                                self._a(m[SELECTED_CITY])
                                if not (yield from self._local_call(self.pay_city_gold,0xC13F,0xC142)):return
                                self._mark(0xC142)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x0022])
                                    m[0x002A]=r.a
                                    self._a(m[0x0023])
                                    m[0x002B]=r.a
                                    self._a(0x1E)
                                    m[0x0022]=r.a
                                    self._a(0x00)
                                    m[0x0023]=r.a
                                    self._a(0x1E)
                                    m[0x0024]=r.a
                                    self._a(m[SELECTED_CITY])
                                    if not (yield from self._local_call(self.pay_city_grain,0xC15B,0xC15E)):return
                                    self._mark(0xC15E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(m[0x0022])
                                        self._flag(C,False)
                                        self._add(m[0x002A])
                                        m[0x002A]=r.a
                                        self._a(m[0x0023])
                                        self._add(m[0x002B])
                                        m[0x002B]=r.a
                                        self._a(m[0x002A])
                                        m[0x0021]=r.a
                                        self._a(m[0x002B])
                                        m[0x0022]=r.a
                                        self._y(m[DIFFICULTY])
                                        self._a(m[(0xC048+r.y)&65535])
                                        m[0x0023]=r.a
                                        self._a(0x00)
                                        m[0x0024]=r.a
                                        if not (yield from self._local_call(self.divide_domestic_word,0xC181,0xC184)):return
                                        self._a(m[0x0021])
                                        m[0x0023]=r.a
                                        self._a(m[SELECTED_CITY])
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC18B,0xC18E)):return
                                        self._y(0x0B)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(m[0x0023])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._compare(r.a,0x63)
                                        self._mark(0xC199)
                                        if not r.p&C:
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xC1A1,0xC1A4)):return
                                            pass
                                        else:
                                            self._a(0x63)
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xC1A1,0xC1A4)):return
                                            pass
                                        pass
                                    pass
                                pass
                            else:
                                self._a(0x0A)
                                m[0x0022]=r.a
                                self._a(0x00)
                                m[0x0023]=r.a
                                self._a(0x0A)
                                m[0x0024]=r.a
                                self._a(m[SELECTED_CITY])
                                if not (yield from self._local_call(self.pay_city_gold,0xC0DE,0xC0E1)):return
                                self._mark(0xC0E1)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x0022])
                                    m[0x0020]=r.a
                                    self._a(m[0x0023])
                                    m[0x0021]=r.a
                                    self._a(0x00)
                                    m[0x0022]=r.a
                                    self._y(m[DIFFICULTY])
                                    self._a(m[(0xC045+r.y)&65535])
                                    m[0x0023]=r.a
                                    if not (yield from self._local_call(self.multiply_domestic_word,0xC0F7,0xC0FA)):return
                                    self._a(m[0x0026])
                                    m[0x0021]=r.a
                                    self._a(m[0x0027])
                                    m[0x0022]=r.a
                                    self._a(0x0A)
                                    m[0x0023]=r.a
                                    self._a(0x00)
                                    m[0x0024]=r.a
                                    if not (yield from self._local_call(self.divide_domestic_word,0xC10A,0xC10D)):return
                                    self._a(m[0x0021])
                                    m[0x0023]=r.a
                                    self._a(m[SELECTED_CITY])
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC114,0xC117)):return
                                    self._y(0x0A)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(m[0x0023])
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._compare(r.a,0x63)
                                    self._mark(0xC122)
                                    if not r.p&C:
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC12A,0xC12D)):return
                                        pass
                                    else:
                                        self._a(0x63)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC12A,0xC12D)):return
                                        pass
                                    pass
                                pass
                            pass
                        else:
                            self._a(0x0A)
                            m[0x0022]=r.a
                            self._a(0x00)
                            m[0x0023]=r.a
                            self._a(0x0E)
                            m[0x0024]=r.a
                            self._a(m[SELECTED_CITY])
                            if not (yield from self._local_call(self.pay_city_gold,0xC05D,0xC060)):return
                            self._mark(0xC060)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x0022])
                                m[0x0020]=r.a
                                self._a(m[0x0023])
                                m[0x0021]=r.a
                                self._a(0x00)
                                m[0x0022]=r.a
                                self._y(m[DIFFICULTY])
                                self._a(m[(0xC042+r.y)&65535])
                                m[0x0023]=r.a
                                if not (yield from self._local_call(self.multiply_domestic_word,0xC076,0xC079)):return
                                self._a(m[0x0026])
                                m[0x0021]=r.a
                                self._a(m[0x0027])
                                m[0x0022]=r.a
                                self._a(0x0A)
                                m[0x0023]=r.a
                                self._a(0x00)
                                m[0x0024]=r.a
                                if not (yield from self._local_call(self.divide_domestic_word,0xC089,0xC08C)):return
                                self._a(m[0x0022])
                                m[0x0023]=r.a
                                self._a(m[0x0021])
                                m[0x0022]=r.a
                                m[0x0023]=self._shift(m[0x0023],False,rotate=False)
                                m[0x0022]=self._shift(m[0x0022],False,rotate=True)
                                self._a(m[SELECTED_CITY])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC09B,0xC09E)):return
                                if not (yield from self._local_call(self.increase_governance_for_population,0xC09E,0xC0A1)):return
                                self._y(0x06)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._flag(C,False)
                                self._add(m[0x0022])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._add(m[0x0023])
                                self._a(r.a & 0x7F)
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._compare(r.a,0x27)
                                self._mark(0xC0B5)
                                if not r.p&C:
                                    self._a(0x05)
                                    if not (yield from self._local_call(self.charge_task_budget,0xC0C9,0xC0CC)):return
                                    pass
                                else:
                                    self._y(r.y-1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._compare(r.a,0x10)
                                    self._mark(0xC0BC)
                                    if not r.p&C:
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC0C9,0xC0CC)):return
                                        pass
                                    else:
                                        self._a(0x0F)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(0x27)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC0C9,0xC0CC)):return
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    else:
                        self._a(m[MONTH])
                        self._compare(r.a,0x03)
                        self._mark(0xBF38)
                        if not r.p&C:
                            self._a(0x0A)
                            m[0x0022]=r.a
                            self._a(0x00)
                            m[0x0023]=r.a
                            self._a(0x0E)
                            m[0x0024]=r.a
                            self._a(m[SELECTED_CITY])
                            if not (yield from self._local_call(self.pay_city_gold,0xBFD2,0xBFD5)):return
                            self._mark(0xBFD5)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x0022])
                                m[0x0020]=r.a
                                self._a(m[0x0023])
                                m[0x0021]=r.a
                                self._a(0x00)
                                m[0x0022]=r.a
                                self._y(m[DIFFICULTY])
                                self._a(m[(0xC042+r.y)&65535])
                                m[0x0023]=r.a
                                if not (yield from self._local_call(self.multiply_domestic_word,0xBFEB,0xBFEE)):return
                                self._a(m[0x0026])
                                m[0x0021]=r.a
                                self._a(m[0x0027])
                                m[0x0022]=r.a
                                self._a(0x0A)
                                m[0x0023]=r.a
                                self._a(0x00)
                                m[0x0024]=r.a
                                if not (yield from self._local_call(self.divide_domestic_word,0xBFFE,0xC001)):return
                                self._a(m[0x0022])
                                m[0x0023]=r.a
                                self._a(m[0x0021])
                                m[0x0022]=r.a
                                self._a(m[SELECTED_CITY])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC00C,0xC00F)):return
                                self._a(m[0x0022])
                                if not (yield from self._local_call(self.increase_governance,0xC011,0xC014)):return
                                self._y(0x0E)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._flag(C,False)
                                self._add(m[0x0022])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._add(m[0x0023])
                                self._a(r.a & 0x03)
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._compare(r.a,0x03)
                                self._mark(0xC028)
                                if not r.p&C:
                                    self._a(0x05)
                                    if not (yield from self._local_call(self.charge_task_budget,0xC03C,0xC03F)):return
                                    pass
                                else:
                                    self._y(r.y-1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._compare(r.a,0xE7)
                                    self._mark(0xC02F)
                                    if not r.p&C:
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC03C,0xC03F)):return
                                        pass
                                    else:
                                        self._a(0xE7)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(0x03)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC03C,0xC03F)):return
                                        pass
                                    pass
                                pass
                            pass
                        else:
                            self._compare(r.a,0x08)
                            self._mark(0xBF3C)
                            if r.p&C:
                                self._a(0x0A)
                                m[0x0022]=r.a
                                self._a(0x00)
                                m[0x0023]=r.a
                                self._a(0x0E)
                                m[0x0024]=r.a
                                self._a(m[SELECTED_CITY])
                                if not (yield from self._local_call(self.pay_city_gold,0xBFD2,0xBFD5)):return
                                self._mark(0xBFD5)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x0022])
                                    m[0x0020]=r.a
                                    self._a(m[0x0023])
                                    m[0x0021]=r.a
                                    self._a(0x00)
                                    m[0x0022]=r.a
                                    self._y(m[DIFFICULTY])
                                    self._a(m[(0xC042+r.y)&65535])
                                    m[0x0023]=r.a
                                    if not (yield from self._local_call(self.multiply_domestic_word,0xBFEB,0xBFEE)):return
                                    self._a(m[0x0026])
                                    m[0x0021]=r.a
                                    self._a(m[0x0027])
                                    m[0x0022]=r.a
                                    self._a(0x0A)
                                    m[0x0023]=r.a
                                    self._a(0x00)
                                    m[0x0024]=r.a
                                    if not (yield from self._local_call(self.divide_domestic_word,0xBFFE,0xC001)):return
                                    self._a(m[0x0022])
                                    m[0x0023]=r.a
                                    self._a(m[0x0021])
                                    m[0x0022]=r.a
                                    self._a(m[SELECTED_CITY])
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC00C,0xC00F)):return
                                    self._a(m[0x0022])
                                    if not (yield from self._local_call(self.increase_governance,0xC011,0xC014)):return
                                    self._y(0x0E)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(m[0x0022])
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._add(m[0x0023])
                                    self._a(r.a & 0x03)
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._compare(r.a,0x03)
                                    self._mark(0xC028)
                                    if not r.p&C:
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC03C,0xC03F)):return
                                        pass
                                    else:
                                        self._y(r.y-1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._compare(r.a,0xE7)
                                        self._mark(0xC02F)
                                        if not r.p&C:
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xC03C,0xC03F)):return
                                            pass
                                        else:
                                            self._a(0xE7)
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._a(0x03)
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xC03C,0xC03F)):return
                                            pass
                                        pass
                                    pass
                                pass
                            else:
                                self._a(0x0A)
                                m[0x0022]=r.a
                                self._a(0x00)
                                m[0x0023]=r.a
                                self._a(0x0E)
                                m[0x0024]=r.a
                                self._a(m[SELECTED_CITY])
                                if not (yield from self._local_call(self.pay_city_gold,0xBF53,0xBF56)):return
                                self._mark(0xBF56)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x0022])
                                    m[0x0020]=r.a
                                    self._a(m[0x0023])
                                    m[0x0021]=r.a
                                    self._a(0x00)
                                    m[0x0022]=r.a
                                    self._y(m[DIFFICULTY])
                                    self._a(m[(0xC042+r.y)&65535])
                                    m[0x0023]=r.a
                                    if not (yield from self._local_call(self.multiply_domestic_word,0xBF6C,0xBF6F)):return
                                    self._a(m[0x0026])
                                    m[0x0021]=r.a
                                    self._a(m[0x0027])
                                    m[0x0022]=r.a
                                    self._a(0x0A)
                                    m[0x0023]=r.a
                                    self._a(0x00)
                                    m[0x0024]=r.a
                                    if not (yield from self._local_call(self.divide_domestic_word,0xBF7F,0xBF82)):return
                                    self._a(m[0x0022])
                                    m[0x0023]=r.a
                                    self._a(m[0x0021])
                                    m[0x0022]=r.a
                                    self._a(m[SELECTED_CITY])
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBF8D,0xBF90)):return
                                    self._a(m[0x0022])
                                    if not (yield from self._local_call(self.increase_governance,0xBF92,0xBF95)):return
                                    self._y(0x08)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(m[0x0022])
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._add(m[0x0023])
                                    self._a(r.a & 0x03)
                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                    self._compare(r.a,0x03)
                                    self._mark(0xBFA9)
                                    if not r.p&C:
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xBFBD,0xBFC0)):return
                                        pass
                                    else:
                                        self._y(r.y-1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._compare(r.a,0xE7)
                                        self._mark(0xBFB0)
                                        if not r.p&C:
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xBFBD,0xBFC0)):return
                                            pass
                                        else:
                                            self._a(0xE7)
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._a(0x03)
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xBFBD,0xBFC0)):return
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    continue
                else:
                    pass
                return (yield from self.officer_and_equipment_stage())
            except _ContinueLoop_BEC7:
                continue

    def scan_next_owned_city(self):
        """$BEE6: scan next owned city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $BEE6
            try:
                self._mark(0xBEE6)
                self._x(m[RULER])
                m[(0x6F83+r.x)&65535]=self._nz(m[(0x6F83+r.x)&65535]+1)
                self._a(m[(0x6F83+r.x)&65535])
                self._compare(r.a,0x1E)
                self._mark(0xBEF1)
                if not r.p&C:
                    m[(0x6F83+r.x)&65535]=r.a
                    m[SELECTED_CITY]=r.a
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBF0D,0xBF10)):return
                    self._compare(r.a,m[RULER])
                    self._mark(0xBF13)
                    if not r.p&Z:
                        continue
                    else:
                        self._mark(0xBF15)
                        self._rts();return
                else:
                    m[CITY_WRAP_COUNT]=self._nz(m[CITY_WRAP_COUNT]+1)
                    self._a(m[CITY_WRAP_COUNT])
                    self._compare(r.a,0x03)
                    self._mark(0xBEFB)
                    if not r.p&Z:
                        self._a(0x00)
                        m[(0x6F83+r.x)&65535]=r.a
                        m[SELECTED_CITY]=r.a
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xBF0D,0xBF10)):return
                        self._compare(r.a,m[RULER])
                        self._mark(0xBF13)
                        if not r.p&Z:
                            continue
                        else:
                            self._mark(0xBF15)
                            self._rts();return
                    else:
                        self._a(0x00)
                        m[CITY_WRAP_COUNT]=r.a
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(0x02)
                        m[AI_PHASE]=r.a
                        self._a(0xFF)
                        m[AI_REQUEST]=r.a
                        self._a(0x00)
                        m[0x6F8D]=r.a
                        self._mark(0xD151)
                        self._rts();return
            except _ContinueLoop_BEE6:
                continue

    def increase_governance(self):
        """$C1A7: increase governance; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1A7)
        self._y(0x01)
        self._compare(r.a,0x1F)
        self._mark(0xC1AB)
        if not r.p&C:
            pass
        else:
            self._y(r.y+1)
            pass
        m[0x002A]=r.y
        self._y(0x0B)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x002A])
        self._compare(r.a,0x64)
        self._mark(0xC1B9)
        if not r.p&C:
            pass
        else:
            self._a(0x64)
            pass
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._mark(0xC1BF)
        self._rts();return

    def increase_governance_for_population(self):
        """$C1C0: increase governance for population; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1C0)
        self._y(0x01)
        self._a(m[0x0022])
        self._flag(C,True)
        self._add(0xB8,subtract=True)
        self._a(m[0x0023])
        self._add(0x0B,subtract=True)
        self._mark(0xC1CB)
        if not r.p&C:
            pass
        else:
            self._y(r.y+1)
            pass
        m[0x002A]=r.y
        self._y(0x0B)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x002A])
        self._compare(r.a,0x64)
        self._mark(0xC1D9)
        if not r.p&C:
            pass
        else:
            self._a(0x64)
            pass
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._mark(0xC1DF)
        self._rts();return

    def officer_and_equipment_stage(self):
        """$C1E0: officer and equipment stage; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1E0)
        self._y(0x0F)
        self._a(0xFF)
        while True:  # natural loop $C1E4
            try:
                m[(0x6F73+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xC1E8)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(0x64)
                if not (yield from self._local_call(self.random_below,0xC1EC,0xC1EF)):return
                self._compare(r.a,0x1E)
                self._mark(0xC1F1)
                if not r.p&C:
                    while True:  # natural loop $C1F6
                        try:
                            if not (yield from self._local_call(self.choose_lowest_loyalty_officer,0xC1F6,0xC1F9)):return
                            self._a(m[0x0023])
                            self._compare(r.a,0xFF)
                            self._mark(0xC1FD)
                            if not r.p&Z:
                                m[0x0036]=r.a
                                self._y(0x03)
                                if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC207,0xC20A)):return
                                self._compare(r.a,0x46)
                                self._mark(0xC20C)
                                if r.p&C:
                                    continue
                                else:
                                    self._a(0x14)
                                    m[0x0022]=r.a
                                    self._a(0x00)
                                    m[0x0023]=r.a
                                    self._a(0x0A)
                                    m[0x0024]=r.a
                                    self._a(m[SELECTED_CITY])
                                    if not (yield from self._local_call(self.pay_city_gold,0xC21D,0xC220)):return
                                    self._mark(0xC220)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.random_low_nibble_below,0xC224,0xC227)):return
                                        self._flag(C,False)
                                        self._y(m[DIFFICULTY])
                                        self._add(m[(0xC04B+r.y)&65535])
                                        m[0x0022]=r.a
                                        self._a(m[0x0036])
                                        self._y(0x03)
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC235,0xC238)):return
                                        self._flag(C,False)
                                        self._add(m[0x0022])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d5e7,0xC23D,0xC240)):return
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_task_budget,0xC242,0xC245)):return
                                        pass
                                    pass
                                pass
                            else:
                                self._y(0x30)
                                yield from self._external(0xC339,0xF266,0xC33C,"call",None)
                                if r.pc!=0xC33C:return  # preserve nonlocal stack return
                                self._y(m[SELECTED_CITY])
                                self._a(m[(0x8FFC+r.y)&65535])
                                self._a(r.a & 0x01)
                                self._mark(0xC344)
                                if not r.p&Z:
                                    while True:  # natural loop $C349
                                        try:
                                            if not (yield from self._local_call(self.choose_weapon_purchase_officer,0xC349,0xC34C)):return
                                            self._a(m[0x0038])
                                            self._compare(r.a,0xFF)
                                            self._mark(0xC351)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(m[SELECTED_CITY])
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC356,0xC359)):return
                                                self._a(m[0x003A])
                                                self._a(r.a & 0x1F)
                                                self._mark(0xC35E)
                                                if r.p&Z:
                                                    r.a=self._shift(r.a,False,rotate=False)
                                                    r.a=self._shift(r.a,False,rotate=False)
                                                    r.a=self._shift(r.a,False,rotate=False)
                                                    r.a=self._shift(r.a,False,rotate=False)
                                                    r.a=self._shift(r.a,False,rotate=False)
                                                    self._flag(C,False)
                                                    self._add(0x0C)
                                                    r.a=self._shift(r.a,True,rotate=False)
                                                    self._x(r.a)
                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_c3a4,0xC388,0xC38B)):return
                                                    self._mark(0xC38B)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(m[0x0038])
                                                        self._y(0x0A)
                                                        if not (yield from self._local_call(self.officer_field_pointer,0xC392,0xC395)):return
                                                        self._a(r.a & 0x1F)
                                                        self._a(r.a | m[0x003A])
                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                        self._a(0x05)
                                                        if not (yield from self._local_call(self.charge_task_budget,0xC39E,0xC3A1)):return
                                                        continue
                                                    pass
                                                else:
                                                    r.a=self._shift(r.a,True,rotate=False)
                                                    self._x(r.a)
                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_c3a4,0xC362,0xC365)):return
                                                    self._mark(0xC365)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(m[0x0038])
                                                        self._y(0x0A)
                                                        if not (yield from self._local_call(self.officer_field_pointer,0xC36C,0xC36F)):return
                                                        self._a(r.a & 0xE0)
                                                        self._a(r.a | m[0x003A])
                                                        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                        self._a(0x05)
                                                        if not (yield from self._local_call(self.charge_task_budget,0xC378,0xC37B)):return
                                                        continue
                                                    pass
                                                pass
                                            return (yield from self.city_development_strategy())
                                        except _ContinueLoop_C349:
                                            continue
                                else:
                                    pass
                                pass
                            return (yield from self.city_development_strategy())
                        except _ContinueLoop_C1F6:
                            continue
                else:
                    while True:  # natural loop $C298
                        try:
                            if not (yield from self._local_call(self.choose_lowest_intelligence_officer,0xC298,0xC29B)):return
                            self._a(m[0x0023])
                            self._compare(r.a,0xFF)
                            self._mark(0xC29F)
                            if r.p&Z:
                                pass
                            else:
                                m[0x0036]=r.a
                                self._y(0x02)
                                if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC2A6,0xC2A9)):return
                                self._compare(r.a,0x32)
                                self._mark(0xC2AB)
                                if not r.p&C:
                                    continue
                                else:
                                    self._compare(r.a,0x50)
                                    self._mark(0xC2AF)
                                    if r.p&C:
                                        continue
                                    else:
                                        self._a(0x14)
                                        m[0x0022]=r.a
                                        self._a(0x00)
                                        m[0x0023]=r.a
                                        self._a(0x0A)
                                        m[0x0024]=r.a
                                        self._a(m[SELECTED_CITY])
                                        if not (yield from self._local_call(self.pay_city_gold,0xC2C0,0xC2C3)):return
                                        self._mark(0xC2C3)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.random_low_nibble_below,0xC2C7,0xC2CA)):return
                                            self._flag(C,False)
                                            self._y(m[DIFFICULTY])
                                            self._add(m[(0xC04B+r.y)&65535])
                                            m[0x0022]=r.a
                                            self._a(m[0x0036])
                                            self._y(0x02)
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC2D8,0xC2DB)):return
                                            self._flag(C,False)
                                            self._add(m[0x0022])
                                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_d5e7,0xC2E0,0xC2E3)):return
                                            self._a(0x05)
                                            if not (yield from self._local_call(self.charge_task_budget,0xC2E5,0xC2E8)):return
                                            pass
                                        pass
                                    pass
                                pass
                            return (yield from self.city_development_strategy())
                        except _ContinueLoop_C298:
                            continue
            except _ContinueLoop_C1E4:
                continue

    def choose_lowest_loyalty_officer(self):
        """$C248: choose lowest loyalty officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC248)
        self._a(0x11)
        m[0x0024]=r.a
        self._a(0xFF)
        m[0x0022]=r.a
        m[0x0023]=r.a
        while True:  # natural loop $C252
            try:
                self._a(m[SELECTED_CITY])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC255,0xC258)):return
                self._y(m[0x0024])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                m[0x0025]=r.a
                self._compare(r.a,0xFF)
                self._mark(0xC260)
                if r.p&Z:
                    pass
                else:
                    self._a(m[(0x6F62+r.y)&65535])
                    self._mark(0xC265)
                    if r.p&Z:
                        pass
                    else:
                        self._y(0x03)
                        self._a(m[0x0025])
                        if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC26B,0xC26E)):return
                        self._compare(r.a,0x64)
                        self._mark(0xC270)
                        if r.p&Z:
                            pass
                        else:
                            self._compare(r.a,m[0x0022])
                            self._mark(0xC274)
                            if r.p&C:
                                pass
                            else:
                                m[0x0022]=r.a
                                self._a(m[0x0024])
                                m[0x0023]=r.a
                                pass
                            pass
                        pass
                    pass
                m[0x0024]=self._nz(m[0x0024]+1)
                self._y(m[0x0024])
                self._compare(r.y,0x1B)
                self._mark(0xC282)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[SELECTED_CITY])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC287,0xC28A)):return
                self._y(m[0x0023])
                self._mark(0xC28C)
                if r.p&N:
                    pass
                else:
                    self._a(0x00)
                    m[(0x6F62+r.y)&65535]=r.a
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    m[0x0023]=r.a
                    pass
                self._mark(0xC297)
                self._rts();return
            except _ContinueLoop_C252:
                continue

    def choose_lowest_intelligence_officer(self):
        """$C2EB: choose lowest intelligence officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC2EB)
        self._a(0x11)
        m[0x0024]=r.a
        self._a(0xFF)
        m[0x0022]=r.a
        m[0x0023]=r.a
        while True:  # natural loop $C2F5
            try:
                self._a(m[SELECTED_CITY])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC2F8,0xC2FB)):return
                self._y(m[0x0024])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                m[0x0025]=r.a
                self._compare(r.a,0xFF)
                self._mark(0xC303)
                if r.p&Z:
                    pass
                else:
                    self._a(m[(0x6F62+r.y)&65535])
                    self._mark(0xC308)
                    if r.p&Z:
                        pass
                    else:
                        self._y(0x02)
                        self._a(m[0x0025])
                        if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC30E,0xC311)):return
                        self._compare(r.a,m[0x0022])
                        self._mark(0xC313)
                        if r.p&C:
                            pass
                        else:
                            m[0x0022]=r.a
                            self._a(m[0x0024])
                            m[0x0023]=r.a
                            pass
                        pass
                    pass
                m[0x0024]=self._nz(m[0x0024]+1)
                self._y(m[0x0024])
                self._compare(r.y,0x1B)
                self._mark(0xC321)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[SELECTED_CITY])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC326,0xC329)):return
                self._y(m[0x0023])
                self._mark(0xC32B)
                if r.p&N:
                    pass
                else:
                    self._a(0x00)
                    m[(0x6F62+r.y)&65535]=r.a
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    m[0x0023]=r.a
                    pass
                self._mark(0xC336)
                self._rts();return
            except _ContinueLoop_C2F5:
                continue

    def domesticcooperationcontroller_c3a4(self):
        """$C3A4: domesticcooperationcontroller c3a4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3A4)
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[(0xC3BF+r.x)&65535],subtract=True)
        m[0x0022]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[(0xC3C0+r.x)&65535],subtract=True)
        self._mark(0xC3B4)
        if not r.p&C:
            pass
        else:
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._a(m[0x0022])
            self._y(r.y-1)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._flag(C,True)
            pass
        self._mark(0xC3BE)
        self._rts();return

    def choose_weapon_purchase_officer(self):
        """$C3FF: choose weapon purchase officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3FF)
        self._a(0x11)
        m[0x0037]=r.a
        self._a(0xFF)
        m[0x0038]=r.a
        self._a(0x00)
        m[0x0039]=r.a
        while True:  # natural loop $C40E
            try:
                self._a(m[SELECTED_CITY])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC411,0xC414)):return
                self._y(m[0x0037])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC41B)
                if r.p&Z:
                    pass
                else:
                    m[0x003B]=r.a
                    if not (yield from self._local_call(self.lookup_next_equipment,0xC420,0xC423)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xC425)
                    if r.p&Z:
                        pass
                    else:
                        m[0x003C]=r.a
                        self._a(m[0x003B])
                        self._y(0x01)
                        if not (yield from self._local_call(self.officer_field_pointer,0xC42F,0xC432)):return
                        self._compare(r.a,m[0x0039])
                        self._mark(0xC435)
                        if not r.p&C:
                            pass
                        else:
                            m[0x0039]=r.a
                            self._a(m[0x003B])
                            m[0x0038]=r.a
                            self._a(m[0x003C])
                            m[0x003A]=r.a
                            pass
                        pass
                    pass
                m[0x0037]=self._nz(m[0x0037]+1)
                self._a(m[0x0037])
                self._compare(r.a,0x1B)
                self._mark(0xC44E)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xC450)
                self._rts();return
            except _ContinueLoop_C40E:
                continue

    def lookup_next_equipment(self):
        """$C451: lookup next equipment; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC451)
        self._y(0x0A)
        if not (yield from self._local_call(self.officer_field_pointer,0xC453,0xC456)):return
        m[0x002A]=r.a
        self._a(r.a & 0x1F)
        self._push(r.a)
        self._y(0x00)
        self._compare(r.a,0x08)
        self._mark(0xC45F)
        if not r.p&C:
            pass
        else:
            self._y(0x04)
            self._compare(r.a,0x10)
            self._mark(0xC465)
            if not r.p&C:
                pass
            else:
                self._y(0x08)
                pass
            pass
        m[0x002B]=r.y
        self._y(m[SELECTED_CITY])
        self._a(m[(0xC4D0+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x002B])
        self._y(r.a)
        self._a(self._pop())
        self._compare(r.a,m[(0xC4EE+r.y)&65535])
        self._mark(0xC47D)
        if not r.p&C:
            self._a(m[(0xC4EE+r.y)&65535])
            self._mark(0xC497)
            self._rts();return
        else:
            self._y(r.y+1)
            self._compare(r.a,m[(0xC4EE+r.y)&65535])
            self._mark(0xC483)
            if not r.p&C:
                self._a(m[(0xC4EE+r.y)&65535])
                self._mark(0xC497)
                self._rts();return
            else:
                self._y(r.y+1)
                self._compare(r.a,m[(0xC4EE+r.y)&65535])
                self._mark(0xC489)
                if not r.p&C:
                    self._a(m[(0xC4EE+r.y)&65535])
                    self._mark(0xC497)
                    self._rts();return
                else:
                    self._y(r.y+1)
                    self._compare(r.a,m[(0xC4EE+r.y)&65535])
                    self._mark(0xC48F)
                    if not r.p&C:
                        self._a(m[(0xC4EE+r.y)&65535])
                        self._mark(0xC497)
                        self._rts();return
                    else:
                        self._y(m[SELECTED_CITY])
                        self._a(m[(0xC4D0+r.y)&65535])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._flag(C,False)
                        self._add(0x0C)
                        self._y(r.a)
                        self._a(m[0x002A])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._compare(r.a,m[(0xC4EE+r.y)&65535])
                        self._mark(0xC4B0)
                        if not r.p&C:
                            self._a(m[(0xC4EE+r.y)&65535])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC4CF)
                            self._rts();return
                        else:
                            self._y(r.y+1)
                            self._compare(r.a,m[(0xC4EE+r.y)&65535])
                            self._mark(0xC4B6)
                            if not r.p&C:
                                self._a(m[(0xC4EE+r.y)&65535])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC4CF)
                                self._rts();return
                            else:
                                self._y(r.y+1)
                                self._compare(r.a,m[(0xC4EE+r.y)&65535])
                                self._mark(0xC4BC)
                                if not r.p&C:
                                    self._a(m[(0xC4EE+r.y)&65535])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC4CF)
                                    self._rts();return
                                else:
                                    self._y(r.y+1)
                                    self._compare(r.a,m[(0xC4EE+r.y)&65535])
                                    self._mark(0xC4C2)
                                    if not r.p&C:
                                        self._a(m[(0xC4EE+r.y)&65535])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xC4CF)
                                        self._rts();return
                                    else:
                                        self._a(0xFF)
                                        self._mark(0xC4C6)
                                        self._rts();return

    def move_ruler_city_position(self):
        """$C50E: move ruler city position; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC50E)
        if not (yield from self._local_call(self.find_ruler_city,0xC50E,0xC511)):return
        m[0x0045]=r.a
        self._a(m[0x0045])
        m[0x0036]=r.a
        if not (yield from self._local_call(self.build_enemy_neighbor_list,0xC51A,0xC51D)):return
        self._mark(0xC51D)
        if not r.p&Z:
            self._a(0x00)
            m[0x003B]=r.a
            m[0x003C]=r.a
            self._a(0xFF)
            m[0x003D]=r.a
            while True:  # natural loop $C52D
                try:
                    self._a(m[0x003B])
                    m[0x0036]=r.a
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC533,0xC536)):return
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[RULER])
                    self._mark(0xC53B)
                    if not r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.build_enemy_neighbor_list,0xC53D,0xC540)):return
                        self._mark(0xC540)
                        if not r.p&Z:
                            pass
                        else:
                            self._x(m[0x0045])
                            self._y(m[0x0036])
                            if not (yield from self._local_call(self.common_connectivity_bits,0xC548,0xC54B)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xC54D)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(m[0x003B])
                                if not (yield from self._local_call(self.count_prefix_officers,0xC552,0xC555)):return
                                self._compare(r.a,m[0x003C])
                                self._mark(0xC558)
                                if not r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0A)
                                    self._mark(0xC55C)
                                    if r.p&Z:
                                        pass
                                    else:
                                        m[0x003C]=r.a
                                        self._a(m[0x003B])
                                        m[0x003D]=r.a
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    m[0x003B]=self._nz(m[0x003B]+1)
                    self._a(m[0x003B])
                    self._compare(r.a,0x1E)
                    self._mark(0xC56F)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(m[0x003D])
                    self._compare(r.a,0xFF)
                    self._mark(0xC576)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[0x0045])
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC57B,0xC57E)):return
                        self._y(0x00)
                        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                        m[0x002A]=r.a
                        self._y(0x11)
                        while True:  # natural loop $C586
                            try:
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._compare(r.a,m[0x002A])
                                self._mark(0xC58A)
                                if r.p&Z:
                                    pass
                                else:
                                    self._y(r.y+1)
                                    continue
                                self._a(0xFF)
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._a(m[0x003D])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC597,0xC59A)):return
                                self._y(0x11)
                                while True:  # natural loop $C59C
                                    try:
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._compare(r.a,0xFF)
                                        self._mark(0xC5A0)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._y(r.y+1)
                                            continue
                                        self._a(m[0x002A])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._a(m[0x0045])
                                        if not (yield from self._local_call(self.compact_city_roster,0xC5AD,0xC5B0)):return
                                        self._a(0x02)
                                        if not (yield from self._local_call(self.charge_nested_budget_one,0xC5B2,0xC5B5)):return
                                        if not (yield from self._local_call(self.find_ruler_city,0xC5B5,0xC5B8)):return
                                        self._mark(0xC5B8)
                                        self._rts();return
                                    except _ContinueLoop_C59C:
                                        continue
                            except _ContinueLoop_C586:
                                continue
                    if not (yield from self._local_call(self.find_ruler_city,0xC5B5,0xC5B8)):return
                    self._mark(0xC5B8)
                    self._rts();return
                except _ContinueLoop_C52D:
                    continue
        else:
            self._mark(0xC51F)
            self._rts();return

    def search_and_recruit_preparation(self):
        """$C5B9: search and recruit preparation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5B9)
        self._a(0x00)
        m[0x0036]=r.a
        while True:  # natural loop $C5BE
            try:
                if not (yield from self._local_call(self.recruit_appearing_officers,0xC5BE,0xC5C1)):return
                if not (yield from self._local_call(self.recruit_unaffiliated_officers,0xC5C1,0xC5C4)):return
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xC5CC)
                if not r.p&C:
                    continue
                else:
                    pass
                if not (yield from self._local_call(self.find_ruler_city,0xC5CE,0xC5D1)):return
                self._mark(0xC5D1)
                self._rts();return
            except _ContinueLoop_C5BE:
                continue

    def recruit_appearing_officers(self):
        """$C5D2: recruit appearing officers; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5D2)
        self._y(0x31)
        yield from self._external(0xC5D4,0xF266,0xC5D7,"call",None)
        if r.pc!=0xC5D7:return  # preserve nonlocal stack return
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC5DA,0xC5DD)):return
        self._a(r.a & 0x07)
        self._compare(r.a,m[RULER])
        self._mark(0xC5E2)
        if not r.p&Z:
            self._mark(0xC5ED)
            self._rts();return
        else:
            self._a(0x64)
            if not (yield from self._local_call(self.random_below,0xC5E6,0xC5E9)):return
            self._compare(r.a,0x0A)
            self._mark(0xC5EB)
            if not r.p&C:
                self._a(m[0x0036])
                if not (yield from self._local_call(self.count_prefix_officers,0xC5F1,0xC5F4)):return
                self._compare(r.a,0x0A)
                self._mark(0xC5F6)
                if r.p&C:
                    self._mark(0xC5ED)
                    self._rts();return
                else:
                    self._a(m[0x0036])
                    m[0x0020]=r.a
                    self._a(0x14)
                    m[0x0021]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d471,0xC601,0xC604)):return
                    self._a(0x00)
                    m[0x0037]=r.a
                    self._a(m[0x002A])
                    self._flag(C,False)
                    self._add(0x1C)
                    m[0x0022]=r.a
                    self._a(m[0x002B])
                    self._add(0x8B)
                    m[0x0023]=r.a
                    while True:  # natural loop $C616
                        try:
                            self._y(m[0x0037])
                            m[0x0037]=self._nz(m[0x0037]+1)
                            m[0x0037]=self._nz(m[0x0037]+1)
                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            m[0x0024]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x64,subtract=True)
                            m[0x0020]=r.a
                            self._a(m[YEAR])
                            self._compare(r.a,m[0x0020])
                            self._mark(0xC630)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x0024])
                                self._y(0x0B)
                                if not (yield from self._local_call(self.domesticcooperationcontroller_d283,0xC636,0xC639)):return
                                self._a(r.a & 0x03)
                                self._compare(r.a,0x01)
                                self._mark(0xC63D)
                                if not r.p&Z:
                                    continue
                                else:
                                    self._a(m[0x0024])
                                    if not (yield from self._local_call(self.recruitment_probability,0xC641,0xC644)):return
                                    m[0x002A]=r.a
                                    while True:  # natural loop $C646
                                        try:
                                            yield from self._external(0xC646,0xE89A,0xC649,"call",None)
                                            if r.pc!=0xC649:return  # preserve nonlocal stack return
                                            self._compare(r.a,0x64)
                                            self._mark(0xC64B)
                                            if r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._compare(r.a,m[0x002A])
                                            self._mark(0xC64F)
                                            if r.p&C:
                                                raise _ContinueLoop_C616
                                            else:
                                                self._y(0x0B)
                                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                self._a(r.a & 0xFC)
                                                self._a(r.a | 0x02)
                                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                self._a(m[0x0036])
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC65E,0xC661)):return
                                                self._y(0x10)
                                                while True:  # natural loop $C663
                                                    try:
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                        self._compare(r.a,0xFF)
                                                        self._mark(0xC668)
                                                        if not r.p&Z:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[0x0024])
                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                        self._mark(0xC66E)
                                                        self._rts();return
                                                    except _ContinueLoop_C663:
                                                        continue
                                        except _ContinueLoop_C646:
                                            continue
                            self._mark(0xC66E)
                            self._rts();return
                        except _ContinueLoop_C616:
                            continue
            else:
                self._mark(0xC5ED)
                self._rts();return

    def recruitment_probability(self):
        """$C66F: recruitment probability; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC66F)
        self._y(m[RULER])
        self._compare(r.y,0x04)
        self._mark(0xC674)
        if not r.p&Z:
            self._y(m[RULER])
            self._compare(r.y,0x02)
            self._mark(0xC695)
            if not r.p&Z:
                self._y(m[RULER])
                self._compare(r.y,0x03)
                self._mark(0xC6B3)
                if not r.p&Z:
                    self._a(0x0A)
                    self._mark(0xC68C)
                    self._rts();return
                else:
                    self._compare(r.a,0x6B)
                    self._mark(0xC6B7)
                    if r.p&Z:
                        self._a(0x5A)
                        self._mark(0xC68F)
                        self._rts();return
                    else:
                        self._compare(r.a,0xEA)
                        self._mark(0xC6BB)
                        if r.p&Z:
                            self._a(0x5A)
                            self._mark(0xC68F)
                            self._rts();return
                        else:
                            self._compare(r.a,0xEB)
                            self._mark(0xC6BF)
                            if r.p&Z:
                                self._a(0x5A)
                                self._mark(0xC68F)
                                self._rts();return
                            else:
                                self._compare(r.a,0xD5)
                                self._mark(0xC6C3)
                                if r.p&Z:
                                    self._a(0x5A)
                                    self._mark(0xC68F)
                                    self._rts();return
                                else:
                                    self._compare(r.a,0x2F)
                                    self._mark(0xC6C7)
                                    if r.p&Z:
                                        self._a(0x5A)
                                        self._mark(0xC68F)
                                        self._rts();return
                                    else:
                                        self._a(0x0A)
                                        self._mark(0xC68C)
                                        self._rts();return
            else:
                self._compare(r.a,0x56)
                self._mark(0xC699)
                if r.p&Z:
                    self._a(0x5A)
                    self._mark(0xC68F)
                    self._rts();return
                else:
                    self._compare(r.a,0x63)
                    self._mark(0xC69D)
                    if r.p&Z:
                        self._a(0x5A)
                        self._mark(0xC68F)
                        self._rts();return
                    else:
                        self._compare(r.a,0x39)
                        self._mark(0xC6A1)
                        if r.p&Z:
                            self._a(0x5A)
                            self._mark(0xC68F)
                            self._rts();return
                        else:
                            self._compare(r.a,0xA5)
                            self._mark(0xC6A5)
                            if r.p&Z:
                                self._a(0x5A)
                                self._mark(0xC68F)
                                self._rts();return
                            else:
                                self._compare(r.a,0x9C)
                                self._mark(0xC6A9)
                                if r.p&Z:
                                    self._a(0x5A)
                                    self._mark(0xC68F)
                                    self._rts();return
                                else:
                                    self._a(0x0A)
                                    self._mark(0xC68C)
                                    self._rts();return
        else:
            self._compare(r.a,0x6D)
            self._mark(0xC678)
            if r.p&Z:
                self._a(0x5A)
                self._mark(0xC68F)
                self._rts();return
            else:
                self._compare(r.a,0x70)
                self._mark(0xC67C)
                if r.p&Z:
                    self._a(0x5A)
                    self._mark(0xC68F)
                    self._rts();return
                else:
                    self._compare(r.a,0x37)
                    self._mark(0xC680)
                    if r.p&Z:
                        self._a(0x5A)
                        self._mark(0xC68F)
                        self._rts();return
                    else:
                        self._compare(r.a,0xB7)
                        self._mark(0xC684)
                        if r.p&Z:
                            self._a(0x5A)
                            self._mark(0xC68F)
                            self._rts();return
                        else:
                            self._compare(r.a,0x90)
                            self._mark(0xC688)
                            if r.p&Z:
                                self._a(0x5A)
                                self._mark(0xC68F)
                                self._rts();return
                            else:
                                self._a(0x0A)
                                self._mark(0xC68C)
                                self._rts();return

    def recruit_unaffiliated_officers(self):
        """$C6CC: recruit unaffiliated officers; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC6CC)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC6CF,0xC6D2)):return
        self._a(r.a & 0x07)
        self._compare(r.a,m[RULER])
        self._mark(0xC6D7)
        if r.p&Z:
            self._a(0x64)
            if not (yield from self._local_call(self.random_below,0xC6DC,0xC6DF)):return
            self._y(m[DIFFICULTY])
            self._compare(r.a,m[(0xC795+r.y)&65535])
            self._mark(0xC6E5)
            if r.p&C:
                self._mark(0xC6D9)
                self._rts();return
            else:
                self._a(m[0x0036])
                if not (yield from self._local_call(self.count_prefix_officers,0xC6EA,0xC6ED)):return
                self._compare(r.a,0x0A)
                self._mark(0xC6EF)
                if r.p&C:
                    self._mark(0xC6D9)
                    self._rts();return
                else:
                    self._a(0x00)
                    m[0x0037]=r.a
                    self._y(0x30)
                    yield from self._external(0xC6F8,0xF266,0xC6FB,"call",None)
                    if r.pc!=0xC6FB:return  # preserve nonlocal stack return
                    self._y(0x0F)
                    self._a(0xFF)
                    while True:  # natural loop $C6FF
                        try:
                            m[(0x6F73+r.y)&65535]=r.a
                            self._y(r.y-1)
                            self._mark(0xC703)
                            if not r.p&N:
                                continue
                            else:
                                pass
                            self._a(m[0x0036])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._y(r.a)
                            self._x(0x00)
                            while True:  # natural loop $C70E
                                try:
                                    self._a(m[(0x9D72+r.y)&65535])
                                    m[(0x6F73+r.x)&65535]=r.a
                                    self._y(r.y+1)
                                    self._x(r.x+1)
                                    self._compare(r.x,0x08)
                                    self._mark(0xC718)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    self._a(0xC0)
                                    m[0x0022]=r.a
                                    self._a(0x63)
                                    m[0x0023]=r.a
                                    self._x(0x00)
                                    while True:  # natural loop $C724
                                        try:
                                            self._y(0x0B)
                                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                            self._a(r.a & 0x03)
                                            self._mark(0xC72A)
                                            if not r.p&Z:
                                                self._a(m[0x0022])
                                                self._flag(C,False)
                                                self._add(0x0C)
                                                m[0x0022]=r.a
                                                self._a(m[0x0023])
                                                self._add(0x00)
                                                m[0x0023]=r.a
                                                self._x(r.x+1)
                                                self._compare(r.x,0xED)
                                                self._mark(0xC762)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._mark(0xC764)
                                                    self._rts();return
                                            else:
                                                self._a(r.x)
                                                if not (yield from self._local_call(self.recruitment_probability,0xC72D,0xC730)):return
                                                m[0x002A]=r.a
                                                while True:  # natural loop $C732
                                                    try:
                                                        yield from self._external(0xC732,0xE89A,0xC735,"call",None)
                                                        if r.pc!=0xC735:return  # preserve nonlocal stack return
                                                        self._compare(r.a,0x64)
                                                        self._mark(0xC737)
                                                        if r.p&C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._compare(r.a,m[0x002A])
                                                        self._mark(0xC73B)
                                                        if r.p&C:
                                                            self._a(m[0x0022])
                                                            self._flag(C,False)
                                                            self._add(0x0C)
                                                            m[0x0022]=r.a
                                                            self._a(m[0x0023])
                                                            self._add(0x00)
                                                            m[0x0023]=r.a
                                                            self._x(r.x+1)
                                                            self._compare(r.x,0xED)
                                                            self._mark(0xC762)
                                                            if not r.p&C:
                                                                raise _ContinueLoop_C724
                                                            else:
                                                                self._mark(0xC764)
                                                                self._rts();return
                                                        else:
                                                            self._y(0x05)
                                                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                            self._compare(r.a,m[0x0036])
                                                            self._mark(0xC744)
                                                            if r.p&Z:
                                                                self._y(0x0B)
                                                                self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                self._a(r.a & 0xFC)
                                                                self._a(r.a | 0x02)
                                                                m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                self._a(m[0x0036])
                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC772,0xC775)):return
                                                                self._y(0x10)
                                                                while True:  # natural loop $C777
                                                                    try:
                                                                        self._y(r.y+1)
                                                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                        self._compare(r.a,0xFF)
                                                                        self._mark(0xC77C)
                                                                        if not r.p&Z:
                                                                            continue
                                                                        else:
                                                                            pass
                                                                        self._a(r.x)
                                                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                        m[0x0031]=r.a
                                                                        self._a(m[RULER])
                                                                        if not (yield from self._local_call(self.ruler_pointer,0xC786,0xC789)):return
                                                                        self._y(0x00)
                                                                        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                        m[0x0030]=r.a
                                                                        if not (yield from self._local_call(self.recalculate_recruited_loyalty,0xC78F,0xC792)):return
                                                                        self._a(self._pop())
                                                                        self._a(self._pop())
                                                                        self._mark(0xC794)
                                                                        self._rts();return
                                                                    except _ContinueLoop_C777:
                                                                        continue
                                                            else:
                                                                self._y(0x00)
                                                                while True:  # natural loop $C748
                                                                    try:
                                                                        self._compare(r.a,m[(0x6F73+r.y)&65535])
                                                                        self._mark(0xC74B)
                                                                        if r.p&Z:
                                                                            self._y(0x0B)
                                                                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                                                            self._a(r.a & 0xFC)
                                                                            self._a(r.a | 0x02)
                                                                            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                                                            self._a(m[0x0036])
                                                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC772,0xC775)):return
                                                                            self._y(0x10)
                                                                            while True:  # natural loop $C777
                                                                                try:
                                                                                    self._y(r.y+1)
                                                                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                                                                    self._compare(r.a,0xFF)
                                                                                    self._mark(0xC77C)
                                                                                    if not r.p&Z:
                                                                                        continue
                                                                                    else:
                                                                                        pass
                                                                                    self._a(r.x)
                                                                                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                                                                    m[0x0031]=r.a
                                                                                    self._a(m[RULER])
                                                                                    if not (yield from self._local_call(self.ruler_pointer,0xC786,0xC789)):return
                                                                                    self._y(0x00)
                                                                                    self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                                                                                    m[0x0030]=r.a
                                                                                    if not (yield from self._local_call(self.recalculate_recruited_loyalty,0xC78F,0xC792)):return
                                                                                    self._a(self._pop())
                                                                                    self._a(self._pop())
                                                                                    self._mark(0xC794)
                                                                                    self._rts();return
                                                                                except _ContinueLoop_C777:
                                                                                    continue
                                                                        else:
                                                                            self._y(r.y+1)
                                                                            self._compare(r.y,0x08)
                                                                            self._mark(0xC750)
                                                                            if not r.p&C:
                                                                                continue
                                                                            else:
                                                                                self._a(m[0x0022])
                                                                                self._flag(C,False)
                                                                                self._add(0x0C)
                                                                                m[0x0022]=r.a
                                                                                self._a(m[0x0023])
                                                                                self._add(0x00)
                                                                                m[0x0023]=r.a
                                                                                self._x(r.x+1)
                                                                                self._compare(r.x,0xED)
                                                                                self._mark(0xC762)
                                                                                if not r.p&C:
                                                                                    raise _ContinueLoop_C724
                                                                                else:
                                                                                    self._mark(0xC764)
                                                                                    self._rts();return
                                                                    except _ContinueLoop_C748:
                                                                        continue
                                                    except _ContinueLoop_C732:
                                                        continue
                                        except _ContinueLoop_C724:
                                            continue
                                except _ContinueLoop_C70E:
                                    continue
                        except _ContinueLoop_C6FF:
                            continue
        else:
            self._mark(0xC6D9)
            self._rts();return

    def recover_owned_city_health(self):
        """$C79A: recover owned city health; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC79A)
        self._y(0xFF)
        m[0x0036]=r.y
        while True:  # natural loop $C79F
            try:
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xC7A7)
                if not r.p&C:
                    self._a(m[0x0036])
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC7AD,0xC7B0)):return
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[RULER])
                    self._mark(0xC7B5)
                    if not r.p&Z:
                        continue
                    else:
                        self._y(0x0F)
                        self._a(0xFF)
                        while True:  # natural loop $C7BB
                            try:
                                m[(0x0540+r.y)&65535]=r.a
                                self._y(r.y-1)
                                self._mark(0xC7BF)
                                if not r.p&N:
                                    continue
                                else:
                                    pass
                                while True:  # natural loop $C7C1
                                    try:
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_c917,0xC7C1,0xC7C4)):return
                                        self._a(m[0x0022])
                                        self._mark(0xC7C6)
                                        if not r.p&Z:
                                            raise _ContinueLoop_C79F
                                        else:
                                            self._a(m[0x002B])
                                            self._compare(r.a,0x02)
                                            self._mark(0xC7CC)
                                            if not r.p&C:
                                                raise _ContinueLoop_C79F
                                            else:
                                                yield from self._external(0xC7CE,0xE88A,0xC7D1,"call",None)
                                                if r.pc!=0xC7D1:return  # preserve nonlocal stack return
                                                self._compare(r.a,m[0x0021])
                                                self._mark(0xC7D3)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._a(0x14)
                                                    m[0x0022]=r.a
                                                    self._a(0x00)
                                                    m[0x0023]=r.a
                                                    self._a(0x00)
                                                    m[0x0024]=r.a
                                                    self._a(m[0x0036])
                                                    if not (yield from self._local_call(self.pay_city_gold,0xC7E4,0xC7E7)):return
                                                    self._mark(0xC7E7)
                                                    if not r.p&C:
                                                        self._mark(0xC7FE)
                                                        self._rts();return
                                                    else:
                                                        self._y(0x30)
                                                        yield from self._external(0xC7EB,0xF266,0xC7EE,"call",None)
                                                        if r.pc!=0xC7EE:return  # preserve nonlocal stack return
                                                        self._y(m[0x0036])
                                                        self._a(m[(0x8FFC+r.y)&65535])
                                                        self._a(r.a & 0x08)
                                                        self._mark(0xC7F6)
                                                        if not r.p&Z:
                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_c97a,0xC7FF,0xC802)):return
                                                            self._a(0x05)
                                                            if not (yield from self._local_call(self.charge_nested_budget_one,0xC804,0xC807)):return
                                                            pass
                                                        else:
                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_c80a,0xC7F8,0xC7FB)):return
                                                            pass
                                                        continue
                                    except _ContinueLoop_C7C1:
                                        continue
                            except _ContinueLoop_C7BB:
                                continue
                else:
                    self._mark(0xC7A9)
                    self._rts();return
            except _ContinueLoop_C79F:
                continue

    def domesticcooperationcontroller_c80a(self):
        """$C80A: domesticcooperationcontroller c80a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC80A)
        self._y(0x0F)
        self._a(0xFF)
        while True:  # natural loop $C80E
            try:
                m[(0x6F73+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xC812)
                if not r.p&N:
                    continue
                else:
                    pass
                self._y(0x30)
                yield from self._external(0xC816,0xF266,0xC819,"call",None)
                if r.pc!=0xC819:return  # preserve nonlocal stack return
                self._a(m[0x0036])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0024]=r.a
                while True:  # natural loop $C821
                    try:
                        self._a(0x08)
                        if not (yield from self._local_call(self.random_low_nibble_below,0xC823,0xC826)):return
                        self._y(r.a)
                        self._a(m[(0x6F73+r.y)&65535])
                        self._mark(0xC82A)
                        if r.p&Z:
                            pass
                        else:
                            self._a(0x00)
                            m[(0x6F73+r.y)&65535]=r.a
                            self._a(r.y)
                            self._flag(C,False)
                            self._add(m[0x0024])
                            self._y(r.a)
                            self._a(m[(0x9D72+r.y)&65535])
                            self._mark(0xC839)
                            if r.p&N:
                                pass
                            else:
                                if not (yield from self._local_call(self.domesticcooperationcontroller_c84d,0xC83B,0xC83E)):return
                                pass
                            pass
                        self._x(0x00)
                        while True:  # natural loop $C840
                            try:
                                self._a(m[(0x6F73+r.x)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xC845)
                                if r.p&Z:
                                    raise _ContinueLoop_C821
                                else:
                                    pass
                                self._x(r.x+1)
                                self._compare(r.x,0x08)
                                self._mark(0xC84A)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xC84C)
                                self._rts();return
                            except _ContinueLoop_C840:
                                continue
                    except _ContinueLoop_C821:
                        continue
            except _ContinueLoop_C80E:
                continue

    def domesticcooperationcontroller_c84d(self):
        """$C84D: domesticcooperationcontroller c84d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC84D)
        m[0x0037]=r.a
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC850,0xC853)):return
        self._compare(r.a,m[RULER])
        self._mark(0xC856)
        if not r.p&Z:
            self._mark(0xC869)
            self._rts();return
        else:
            self._a(m[0x0037])
            if not (yield from self._local_call(self.domesticcooperationcontroller_c86a,0xC85B,0xC85E)):return
            self._mark(0xC85E)
            if not r.p&C:
                if not (yield from self._local_call(self.domesticcooperationcontroller_c885,0xC865,0xC868)):return
                self._mark(0xC868)
                self._rts();return
            else:
                self._a(self._pop())
                self._a(self._pop())
                self._a(m[0x0036])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC8E9,0xC8EC)):return
                self._y(0x10)
                while True:  # natural loop $C8EE
                    try:
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x0039])
                        self._mark(0xC8F4)
                        if not r.p&Z:
                            continue
                        else:
                            pass
                        self._a(0xFF)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._a(m[0x0037])
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC8FD,0xC900)):return
                        self._y(0x10)
                        while True:  # natural loop $C902
                            try:
                                self._y(r.y+1)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xC907)
                                if not r.p&Z:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0039])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.compact_city_roster,0xC911,0xC914)):return
                                while True:  # natural loop $C7FF
                                    try:
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_c97a,0xC7FF,0xC802)):return
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_nested_budget_one,0xC804,0xC807)):return
                                        while True:  # natural loop $C7C1
                                            try:
                                                if not (yield from self._local_call(self.domesticcooperationcontroller_c917,0xC7C1,0xC7C4)):return
                                                self._a(m[0x0022])
                                                self._mark(0xC7C6)
                                                if not r.p&Z:
                                                    while True:  # natural loop $C79F
                                                        try:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xC7A7)
                                                            if not r.p&C:
                                                                self._a(m[0x0036])
                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC7AD,0xC7B0)):return
                                                                self._a(r.a & 0x07)
                                                                self._compare(r.a,m[RULER])
                                                                self._mark(0xC7B5)
                                                                if not r.p&Z:
                                                                    continue
                                                                else:
                                                                    self._y(0x0F)
                                                                    self._a(0xFF)
                                                                    while True:  # natural loop $C7BB
                                                                        try:
                                                                            m[(0x0540+r.y)&65535]=r.a
                                                                            self._y(r.y-1)
                                                                            self._mark(0xC7BF)
                                                                            if not r.p&N:
                                                                                continue
                                                                            else:
                                                                                pass
                                                                            raise _ContinueLoop_C7C1
                                                                        except _ContinueLoop_C7BB:
                                                                            continue
                                                            else:
                                                                self._mark(0xC7A9)
                                                                self._rts();return
                                                        except _ContinueLoop_C79F:
                                                            continue
                                                else:
                                                    self._a(m[0x002B])
                                                    self._compare(r.a,0x02)
                                                    self._mark(0xC7CC)
                                                    if not r.p&C:
                                                        while True:  # natural loop $C79F
                                                            try:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xC7A7)
                                                                if not r.p&C:
                                                                    self._a(m[0x0036])
                                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC7AD,0xC7B0)):return
                                                                    self._a(r.a & 0x07)
                                                                    self._compare(r.a,m[RULER])
                                                                    self._mark(0xC7B5)
                                                                    if not r.p&Z:
                                                                        continue
                                                                    else:
                                                                        self._y(0x0F)
                                                                        self._a(0xFF)
                                                                        while True:  # natural loop $C7BB
                                                                            try:
                                                                                m[(0x0540+r.y)&65535]=r.a
                                                                                self._y(r.y-1)
                                                                                self._mark(0xC7BF)
                                                                                if not r.p&N:
                                                                                    continue
                                                                                else:
                                                                                    pass
                                                                                raise _ContinueLoop_C7C1
                                                                            except _ContinueLoop_C7BB:
                                                                                continue
                                                                else:
                                                                    self._mark(0xC7A9)
                                                                    self._rts();return
                                                            except _ContinueLoop_C79F:
                                                                continue
                                                    else:
                                                        yield from self._external(0xC7CE,0xE88A,0xC7D1,"call",None)
                                                        if r.pc!=0xC7D1:return  # preserve nonlocal stack return
                                                        self._compare(r.a,m[0x0021])
                                                        self._mark(0xC7D3)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(0x14)
                                                            m[0x0022]=r.a
                                                            self._a(0x00)
                                                            m[0x0023]=r.a
                                                            self._a(0x00)
                                                            m[0x0024]=r.a
                                                            self._a(m[0x0036])
                                                            if not (yield from self._local_call(self.pay_city_gold,0xC7E4,0xC7E7)):return
                                                            self._mark(0xC7E7)
                                                            if not r.p&C:
                                                                self._mark(0xC7FE)
                                                                self._rts();return
                                                            else:
                                                                self._y(0x30)
                                                                yield from self._external(0xC7EB,0xF266,0xC7EE,"call",None)
                                                                if r.pc!=0xC7EE:return  # preserve nonlocal stack return
                                                                self._y(m[0x0036])
                                                                self._a(m[(0x8FFC+r.y)&65535])
                                                                self._a(r.a & 0x08)
                                                                self._mark(0xC7F6)
                                                                if not r.p&Z:
                                                                    raise _ContinueLoop_C7FF
                                                                else:
                                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_c80a,0xC7F8,0xC7FB)):return
                                                                    pass
                                                                continue
                                            except _ContinueLoop_C7C1:
                                                continue
                                    except _ContinueLoop_C7FF:
                                        continue
                            except _ContinueLoop_C902:
                                continue
                    except _ContinueLoop_C8EE:
                        continue

    def domesticcooperationcontroller_c86a(self):
        """$C86A: domesticcooperationcontroller c86a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC86A)
        self._push(r.a)
        self._y(0x30)
        yield from self._external(0xC86D,0xF266,0xC870,"call",None)
        if r.pc!=0xC870:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._y(r.a)
        self._a(m[(0x8FFC+r.y)&65535])
        self._a(r.a & 0x08)
        self._mark(0xC877)
        if r.p&Z:
            self._flag(C,False)
            self._mark(0xC884)
            self._rts();return
        else:
            self._a(r.y)
            if not (yield from self._local_call(self.count_prefix_officers,0xC87A,0xC87D)):return
            self._compare(r.a,0x0A)
            self._mark(0xC87F)
            if r.p&C:
                self._flag(C,False)
                self._mark(0xC884)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xC882)
                self._rts();return

    def domesticcooperationcontroller_c885(self):
        """$C885: domesticcooperationcontroller c885; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC885)
        self._y(0x08)
        self._a(0xFF)
        while True:  # natural loop $C889
            try:
                m[(0x6F7B+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xC88D)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(m[0x0037])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0028]=r.a
                while True:  # natural loop $C897
                    try:
                        self._a(0x08)
                        if not (yield from self._local_call(self.random_low_nibble_below,0xC899,0xC89C)):return
                        self._y(r.a)
                        self._a(m[(0x6F7B+r.y)&65535])
                        self._mark(0xC8A0)
                        if r.p&Z:
                            continue
                        else:
                            pass
                        self._a(0x00)
                        m[(0x6F7B+r.y)&65535]=r.a
                        self._a(r.y)
                        self._flag(C,False)
                        self._add(m[0x0028])
                        self._y(r.a)
                        self._a(m[(0x9D72+r.y)&65535])
                        self._mark(0xC8AF)
                        if r.p&N:
                            pass
                        else:
                            if not (yield from self._local_call(self.domesticcooperationcontroller_c8c3,0xC8B1,0xC8B4)):return
                            pass
                        self._x(0x00)
                        while True:  # natural loop $C8B6
                            try:
                                self._a(m[(0x6F7B+r.x)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xC8BB)
                                if r.p&Z:
                                    raise _ContinueLoop_C897
                                else:
                                    pass
                                self._x(r.x+1)
                                self._compare(r.x,0x08)
                                self._mark(0xC8C0)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xC8C2)
                                self._rts();return
                            except _ContinueLoop_C8B6:
                                continue
                    except _ContinueLoop_C897:
                        continue
            except _ContinueLoop_C889:
                continue

    def domesticcooperationcontroller_c8c3(self):
        """$C8C3: domesticcooperationcontroller c8c3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC8C3)
        m[0x0038]=r.a
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC8C6,0xC8C9)):return
        self._compare(r.a,m[RULER])
        self._mark(0xC8CC)
        if not r.p&Z:
            self._mark(0xC8E5)
            self._rts();return
        else:
            self._a(m[0x0038])
            if not (yield from self._local_call(self.domesticcooperationcontroller_c86a,0xC8D1,0xC8D4)):return
            self._mark(0xC8D4)
            if not r.p&C:
                self._mark(0xC8E5)
                self._rts();return
            else:
                self._a(self._pop())
                self._a(self._pop())
                self._a(self._pop())
                self._a(self._pop())
                self._a(self._pop())
                self._a(self._pop())
                self._a(m[0x0038])
                m[0x0037]=r.a
                self._a(m[0x0036])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC8E9,0xC8EC)):return
                self._y(0x10)
                while True:  # natural loop $C8EE
                    try:
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x0039])
                        self._mark(0xC8F4)
                        if not r.p&Z:
                            continue
                        else:
                            pass
                        self._a(0xFF)
                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                        self._a(m[0x0037])
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC8FD,0xC900)):return
                        self._y(0x10)
                        while True:  # natural loop $C902
                            try:
                                self._y(r.y+1)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xC907)
                                if not r.p&Z:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0039])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.compact_city_roster,0xC911,0xC914)):return
                                while True:  # natural loop $C7FF
                                    try:
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_c97a,0xC7FF,0xC802)):return
                                        self._a(0x05)
                                        if not (yield from self._local_call(self.charge_nested_budget_one,0xC804,0xC807)):return
                                        while True:  # natural loop $C7C1
                                            try:
                                                if not (yield from self._local_call(self.domesticcooperationcontroller_c917,0xC7C1,0xC7C4)):return
                                                self._a(m[0x0022])
                                                self._mark(0xC7C6)
                                                if not r.p&Z:
                                                    while True:  # natural loop $C79F
                                                        try:
                                                            m[0x0036]=self._nz(m[0x0036]+1)
                                                            self._a(m[0x0036])
                                                            self._compare(r.a,0x1E)
                                                            self._mark(0xC7A7)
                                                            if not r.p&C:
                                                                self._a(m[0x0036])
                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC7AD,0xC7B0)):return
                                                                self._a(r.a & 0x07)
                                                                self._compare(r.a,m[RULER])
                                                                self._mark(0xC7B5)
                                                                if not r.p&Z:
                                                                    continue
                                                                else:
                                                                    self._y(0x0F)
                                                                    self._a(0xFF)
                                                                    while True:  # natural loop $C7BB
                                                                        try:
                                                                            m[(0x0540+r.y)&65535]=r.a
                                                                            self._y(r.y-1)
                                                                            self._mark(0xC7BF)
                                                                            if not r.p&N:
                                                                                continue
                                                                            else:
                                                                                pass
                                                                            raise _ContinueLoop_C7C1
                                                                        except _ContinueLoop_C7BB:
                                                                            continue
                                                            else:
                                                                self._mark(0xC7A9)
                                                                self._rts();return
                                                        except _ContinueLoop_C79F:
                                                            continue
                                                else:
                                                    self._a(m[0x002B])
                                                    self._compare(r.a,0x02)
                                                    self._mark(0xC7CC)
                                                    if not r.p&C:
                                                        while True:  # natural loop $C79F
                                                            try:
                                                                m[0x0036]=self._nz(m[0x0036]+1)
                                                                self._a(m[0x0036])
                                                                self._compare(r.a,0x1E)
                                                                self._mark(0xC7A7)
                                                                if not r.p&C:
                                                                    self._a(m[0x0036])
                                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC7AD,0xC7B0)):return
                                                                    self._a(r.a & 0x07)
                                                                    self._compare(r.a,m[RULER])
                                                                    self._mark(0xC7B5)
                                                                    if not r.p&Z:
                                                                        continue
                                                                    else:
                                                                        self._y(0x0F)
                                                                        self._a(0xFF)
                                                                        while True:  # natural loop $C7BB
                                                                            try:
                                                                                m[(0x0540+r.y)&65535]=r.a
                                                                                self._y(r.y-1)
                                                                                self._mark(0xC7BF)
                                                                                if not r.p&N:
                                                                                    continue
                                                                                else:
                                                                                    pass
                                                                                raise _ContinueLoop_C7C1
                                                                            except _ContinueLoop_C7BB:
                                                                                continue
                                                                else:
                                                                    self._mark(0xC7A9)
                                                                    self._rts();return
                                                            except _ContinueLoop_C79F:
                                                                continue
                                                    else:
                                                        yield from self._external(0xC7CE,0xE88A,0xC7D1,"call",None)
                                                        if r.pc!=0xC7D1:return  # preserve nonlocal stack return
                                                        self._compare(r.a,m[0x0021])
                                                        self._mark(0xC7D3)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._a(0x14)
                                                            m[0x0022]=r.a
                                                            self._a(0x00)
                                                            m[0x0023]=r.a
                                                            self._a(0x00)
                                                            m[0x0024]=r.a
                                                            self._a(m[0x0036])
                                                            if not (yield from self._local_call(self.pay_city_gold,0xC7E4,0xC7E7)):return
                                                            self._mark(0xC7E7)
                                                            if not r.p&C:
                                                                self._mark(0xC7FE)
                                                                self._rts();return
                                                            else:
                                                                self._y(0x30)
                                                                yield from self._external(0xC7EB,0xF266,0xC7EE,"call",None)
                                                                if r.pc!=0xC7EE:return  # preserve nonlocal stack return
                                                                self._y(m[0x0036])
                                                                self._a(m[(0x8FFC+r.y)&65535])
                                                                self._a(r.a & 0x08)
                                                                self._mark(0xC7F6)
                                                                if not r.p&Z:
                                                                    raise _ContinueLoop_C7FF
                                                                else:
                                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_c80a,0xC7F8,0xC7FB)):return
                                                                    pass
                                                                continue
                                            except _ContinueLoop_C7C1:
                                                continue
                                    except _ContinueLoop_C7FF:
                                        continue
                            except _ContinueLoop_C902:
                                continue
                    except _ContinueLoop_C8EE:
                        continue

    def domesticcooperationcontroller_c917(self):
        """$C917: domesticcooperationcontroller c917; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC917)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC91A,0xC91D)):return
        self._a(0x11)
        m[0x0028]=r.a
        self._a(0xFF)
        m[0x0029]=r.a
        m[0x002A]=r.a
        self._a(0x00)
        m[0x002B]=r.a
        while True:  # natural loop $C92B
            try:
                self._y(m[0x0028])
                self._a(m[(0x052F+r.y)&65535])
                self._mark(0xC930)
                if r.p&Z:
                    pass
                else:
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._compare(r.a,0xFF)
                    self._mark(0xC936)
                    if r.p&Z:
                        pass
                    else:
                        m[0x002B]=self._nz(m[0x002B]+1)
                        self._y(0x00)
                        if not (yield from self._local_call(self.officer_field_pointer,0xC93C,0xC93F)):return
                        self._compare(r.a,m[0x0029])
                        self._mark(0xC941)
                        if r.p&C:
                            pass
                        else:
                            m[0x0029]=r.a
                            self._a(m[0x0028])
                            m[0x002A]=r.a
                            pass
                        pass
                    pass
                m[0x0028]=self._nz(m[0x0028]+1)
                self._y(m[0x0028])
                self._compare(r.y,0x1B)
                self._mark(0xC94F)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(m[0x002A])
                self._a(0x00)
                m[(0x052F+r.y)&65535]=r.a
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                m[0x0039]=r.a
                self._y(0x00)
                if not (yield from self._local_call(self.domesticcooperationcontroller_d2d3,0xC95F,0xC962)):return
                self._push(r.a)
                self._a(m[0x0039])
                self._y(0x00)
                if not (yield from self._local_call(self.officer_field_pointer,0xC968,0xC96B)):return
                m[0x0022]=r.a
                self._a(self._pop())
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0021]=r.a
                m[0x0024]=r.a
                if not (yield from self._local_call(self.divide_domestic_word,0xC976,0xC979)):return
                self._mark(0xC979)
                self._rts();return
            except _ContinueLoop_C92B:
                continue

    def domesticcooperationcontroller_c97a(self):
        """$C97A: domesticcooperationcontroller c97a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC97A)
        self._a(m[0x0039])
        self._y(0x00)
        if not (yield from self._local_call(self.domesticcooperationcontroller_d2d3,0xC97F,0xC982)):return
        self._push(r.a)
        self._a(m[0x0039])
        self._y(0x00)
        if not (yield from self._local_call(self.officer_field_pointer,0xC988,0xC98B)):return
        self._a(self._pop())
        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        self._mark(0xC98E)
        self._rts();return

    def repair_owned_city_governors(self):
        """$C98F: repair owned city governors; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC98F)
        m[0x0037]=r.a
        self._a(0x00)
        m[0x0036]=r.a
        while True:  # natural loop $C997
            try:
                if not (yield from self._local_call(self.choose_city_governor,0xC997,0xC99A)):return
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xC9A2)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xC9A4)
                self._rts();return
            except _ContinueLoop_C997:
                continue

    def choose_city_governor(self):
        """$C9A5: choose city governor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9A5)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xC9A8,0xC9AB)):return
        self._a(r.a & 0x07)
        self._compare(r.a,m[0x0037])
        self._mark(0xC9B0)
        if not r.p&Z:
            self._mark(0xC9A4)
            self._rts();return
        else:
            self._a(0x11)
            m[0x003A]=r.a
            self._a(0x00)
            m[0x003B]=r.a
            self._a(0xFF)
            m[0x003C]=r.a
            while True:  # natural loop $C9C1
                try:
                    self._y(m[0x003A])
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    self._compare(r.a,0xFF)
                    self._mark(0xC9C8)
                    if r.p&Z:
                        m[0x003A]=self._nz(m[0x003A]+1)
                        self._a(m[0x003A])
                        self._compare(r.a,0x1B)
                        self._mark(0xC9F7)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        pass
                    else:
                        self._y(0x03)
                        if not (yield from self._local_call(self.officer_field_pointer,0xC9CC,0xC9CF)):return
                        self._compare(r.a,0x64)
                        self._mark(0xC9D1)
                        if not r.p&Z:
                            self._y(0x04)
                            self._flag(C,False)
                            self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            self._compare(r.a,m[0x003B])
                            self._mark(0xC9E4)
                            if not r.p&C:
                                pass
                            else:
                                m[0x003B]=r.a
                                self._a(m[0x003A])
                                m[0x003C]=r.a
                                pass
                            m[0x003A]=self._nz(m[0x003A]+1)
                            self._a(m[0x003A])
                            self._compare(r.a,0x1B)
                            self._mark(0xC9F7)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            pass
                        else:
                            self._a(m[0x003A])
                            m[0x003C]=r.a
                            pass
                        pass
                    self._a(m[0x003C])
                    self._compare(r.a,0xFF)
                    self._mark(0xC9FE)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x11)
                        self._mark(0xCA02)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x11)
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._push(r.a)
                            self._y(m[0x003C])
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._y(0x11)
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            self._a(self._pop())
                            self._y(m[0x003C])
                            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                            pass
                        pass
                    self._mark(0xCA18)
                    self._rts();return
                except _ContinueLoop_C9C1:
                    continue

    def resolve_AI_leader_deaths(self):
        """$CA19: resolve AI leader deaths; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA19)
        self._a(0x00)
        m[0x0040]=r.a
        while True:  # natural loop $CA1E
            try:
                self._a(m[0x0040])
                if not (yield from self._local_call(self.ruler_pointer,0xCA21,0xCA24)):return
                self._y(0x00)
                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCA2A)
                if r.p&Z:
                    pass
                else:
                    m[0x0038]=r.a
                    self._y(0x03)
                    self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                    self._compare(r.a,0x03)
                    self._mark(0xCA35)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0038])
                        self._y(0x0B)
                        if not (yield from self._local_call(self.officer_field_pointer,0xCA3C,0xCA3F)):return
                        self._a(r.a & 0x03)
                        self._compare(r.a,0x02)
                        self._mark(0xCA43)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x0B)
                            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                            self._a(r.a & 0xFC)
                            self._a(r.a | 0x03)
                            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                            if not (yield from self._local_call(self.resolve_missing_heir,0xCA4F,0xCA52)):return
                            pass
                        self._a(m[0x0040])
                        if not (yield from self._local_call(self.repair_owned_city_governors,0xCA55,0xCA58)):return
                        pass
                    pass
                m[0x0040]=self._nz(m[0x0040]+1)
                self._a(m[0x0040])
                self._compare(r.a,0x07)
                self._mark(0xCA60)
                if not r.p&C:
                    continue
                else:
                    pass
                if not (yield from self._local_call(self.find_ruler_city,0xCA62,0xCA65)):return
                return (yield from self.city_development_strategy())
            except _ContinueLoop_CA1E:
                continue

    def resolve_missing_heir(self):
        """$CA68: resolve missing heir; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA68)
        if not (yield from self._local_call(self.inspect_successor_candidates,0xCA68,0xCA6B)):return
        if not (yield from self._local_call(self.release_extinct_ruler_cities,0xCA6B,0xCA6E)):return
        self._a(m[0x0040])
        if not (yield from self._local_call(self.ruler_pointer,0xCA71,0xCA74)):return
        self._y(0x00)
        self._a(0xFF)
        m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
        self._a(0xFB)
        m[AI_REQUEST]=r.a
        return (yield from self.await_extinction_acknowledgment())

    def await_extinction_acknowledgment(self):
        """$CA7F: genuine cooperative wait for external6F8B==1.

        The emittedFB/FC event is retained. No implicit UI/NMI progress or fake
        acknowledgement is supplied. Resume repeats the original LDA/CMP/BNE.
        """
        r=self.registers;m=self.memory
        while True:
            self._mark(0xCA7F);self._a(m[AI_REQUEST]);self._compare(r.a,1)
            if r.p&Z:break
            r.pc=0xCA7F
            yield ServiceWait('domestic_ack',0xCA7F,AI_REQUEST,1,'Original succession/extinction acknowledgement',r.sp)
        self._rts()

    def inspect_successor_candidates(self):
        """$CA87: inspect successor candidates; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA87)
        self._a(m[0x0040])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xCAD8+r.y)&65535])
        m[0x0024]=r.a
        self._a(m[(0xCAD9+r.y)&65535])
        m[0x0025]=r.a
        self._a(0x00)
        m[0x0026]=r.a
        while True:  # natural loop $CA9A
            try:
                self._y(m[0x0026])
                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCAA0)
                if r.p&Z:
                    pass
                else:
                    m[0x0027]=r.a
                    if not (yield from self._local_call(self.test_successor_candidate,0xCAA4,0xCAA7)):return
                    m[0x0026]=self._nz(m[0x0026]+1)
                    continue
                self._mark(0xCAAC)
                self._rts();return
            except _ContinueLoop_CA9A:
                continue

    def test_successor_candidate(self):
        """$CAAD: test successor candidate; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCAAD)
        self._a(0x00)
        m[0x002A]=r.a
        while True:  # natural loop $CAB1
            try:
                self._a(m[0x002A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCAB3,0xCAB6)):return
                self._compare(r.a,m[0x0040])
                self._mark(0xCAB9)
                if not r.p&Z:
                    m[0x002A]=self._nz(m[0x002A]+1)
                    self._a(m[0x002A])
                    self._compare(r.a,0x1E)
                    self._mark(0xCACE)
                    if not r.p&C:
                        continue
                    else:
                        self._mark(0xCAD0)
                        self._rts();return
                else:
                    self._y(0x11)
                    while True:  # natural loop $CABD
                        try:
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._compare(r.a,m[0x0027])
                            self._mark(0xCAC1)
                            if r.p&Z:
                                self._a(self._pop())
                                self._a(self._pop())
                                self._a(self._pop())
                                self._a(self._pop())
                                return (yield from self.install_successor())
                            else:
                                self._y(r.y+1)
                                self._compare(r.y,0x1B)
                                self._mark(0xCAC6)
                                if not r.p&C:
                                    continue
                                else:
                                    m[0x002A]=self._nz(m[0x002A]+1)
                                    self._a(m[0x002A])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xCACE)
                                    if not r.p&C:
                                        raise _ContinueLoop_CAB1
                                    else:
                                        self._mark(0xCAD0)
                                        self._rts();return
                        except _ContinueLoop_CABD:
                            continue
            except _ContinueLoop_CAB1:
                continue

    def release_extinct_ruler_cities(self):
        """$CB05: release extinct ruler cities; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB05)
        self._a(0x00)
        m[0x002A]=r.a
        m[0x002B]=r.a
        self._a(0xFF)
        m[0x0027]=r.a
        while True:  # natural loop $CB0F
            try:
                self._a(m[0x002A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCB11,0xCB14)):return
                self._compare(r.a,m[0x0040])
                self._mark(0xCB17)
                if not r.p&Z:
                    pass
                else:
                    self._y(0x11)
                    m[0x0024]=r.y
                    while True:  # natural loop $CB1D
                        try:
                            self._y(m[0x0024])
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xCB23)
                            if r.p&Z:
                                pass
                            else:
                                self._y(0x04)
                                if not (yield from self._local_call(self.officer_field_pointer,0xCB27,0xCB2A)):return
                                self._compare(r.a,m[0x002B])
                                self._mark(0xCB2C)
                                if not r.p&C:
                                    pass
                                else:
                                    m[0x002B]=r.a
                                    self._y(m[0x0024])
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[0x0027]=r.a
                                    pass
                                pass
                            m[0x0024]=self._nz(m[0x0024]+1)
                            self._a(m[0x0024])
                            self._compare(r.a,0x1B)
                            self._mark(0xCB3C)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            m[0x002A]=self._nz(m[0x002A]+1)
                            self._a(m[0x002A])
                            self._compare(r.a,0x1E)
                            self._mark(0xCB44)
                            if not r.p&C:
                                raise _ContinueLoop_CB0F
                            else:
                                pass
                            self._a(m[0x0027])
                            self._compare(r.a,0xFF)
                            self._mark(0xCB4A)
                            if r.p&Z:
                                self._mark(0xCB51)
                                self._rts();return
                            else:
                                self._a(self._pop())
                                self._a(self._pop())
                                return (yield from self.install_successor())
                        except _ContinueLoop_CB1D:
                            continue
                m[0x002A]=self._nz(m[0x002A]+1)
                self._a(m[0x002A])
                self._compare(r.a,0x1E)
                self._mark(0xCB44)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0027])
                self._compare(r.a,0xFF)
                self._mark(0xCB4A)
                if r.p&Z:
                    self._mark(0xCB51)
                    self._rts();return
                else:
                    self._a(self._pop())
                    self._a(self._pop())
                    return (yield from self.install_successor())
            except _ContinueLoop_CB0F:
                continue

    def install_successor(self):
        """$CB52: install successor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB52)
        self._a(m[0x0040])
        if not (yield from self._local_call(self.ruler_pointer,0xCB55,0xCB58)):return
        self._y(0x00)
        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
        m[0x0033]=r.a
        self._a(m[0x0027])
        m[((m[0x24]|m[0x25]<<8)+r.y)&65535]=r.a
        self._y(0x03)
        if not (yield from self._local_call(self.officer_field_pointer,0xCB64,0xCB67)):return
        self._a(0x64)
        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        self._a(m[0x0027])
        self._push(r.a)
        if not (yield from self._local_call(self.adjust_successor_followers,0xCB6E,0xCB71)):return
        self._a(self._pop())
        m[0x0027]=r.a
        self._a(0xFC)
        m[AI_REQUEST]=r.a
        return (yield from self.await_successor_acknowledgment())

    def await_successor_acknowledgment(self):
        """$CB79: genuine cooperative wait for external6F8B==1.

        The emittedFB/FC event is retained. No implicit UI/NMI progress or fake
        acknowledgement is supplied. Resume repeats the original LDA/CMP/BNE.
        """
        r=self.registers;m=self.memory
        while True:
            self._mark(0xCB79);self._a(m[AI_REQUEST]);self._compare(r.a,1)
            if r.p&Z:break
            r.pc=0xCB79
            yield ServiceWait('domestic_ack',0xCB79,AI_REQUEST,1,'Original succession/extinction acknowledgement',r.sp)
        self._rts()

    def adjust_successor_followers(self):
        """$CB81: adjust successor followers; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB81)
        self._a(m[0x0027])
        m[0x0030]=r.a
        self._a(0x00)
        m[0x0045]=r.a
        while True:  # natural loop $CB8A
            try:
                self._a(m[0x0045])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCB8D,0xCB90)):return
                self._compare(r.a,m[0x0040])
                self._mark(0xCB93)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_cba3,0xCB95,0xCB98)):return
                    pass
                m[0x0045]=self._nz(m[0x0045]+1)
                self._a(m[0x0045])
                self._compare(r.a,0x1E)
                self._mark(0xCBA0)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xCBA2)
                self._rts();return
            except _ContinueLoop_CB8A:
                continue

    def domesticcooperationcontroller_cba3(self):
        """$CBA3: domesticcooperationcontroller cba3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBA3)
        self._a(0x11)
        m[0x0044]=r.a
        while True:  # natural loop $CBA8
            try:
                self._a(m[0x0045])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCBAB,0xCBAE)):return
                self._y(m[0x0044])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCBB5)
                if r.p&Z:
                    while True:  # natural loop $CB98
                        try:
                            m[0x0045]=self._nz(m[0x0045]+1)
                            self._a(m[0x0045])
                            self._compare(r.a,0x1E)
                            self._mark(0xCBA0)
                            if not r.p&C:
                                self._a(m[0x0045])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCB8D,0xCB90)):return
                                self._compare(r.a,m[0x0040])
                                self._mark(0xCB93)
                                if not r.p&Z:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_cba3,0xCB95,0xCB98)):return
                                    pass
                                continue
                            else:
                                pass
                            self._mark(0xCBA2)
                            self._rts();return
                        except _ContinueLoop_CB98:
                            continue
                else:
                    self._compare(r.a,m[0x0030])
                    self._mark(0xCBB9)
                    if r.p&Z:
                        while True:  # natural loop $CB98
                            try:
                                m[0x0045]=self._nz(m[0x0045]+1)
                                self._a(m[0x0045])
                                self._compare(r.a,0x1E)
                                self._mark(0xCBA0)
                                if not r.p&C:
                                    self._a(m[0x0045])
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCB8D,0xCB90)):return
                                    self._compare(r.a,m[0x0040])
                                    self._mark(0xCB93)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_cba3,0xCB95,0xCB98)):return
                                        pass
                                    continue
                                else:
                                    pass
                                self._mark(0xCBA2)
                                self._rts();return
                            except _ContinueLoop_CB98:
                                continue
                    else:
                        m[0x0031]=r.a
                        self._a(m[0x0040])
                        m[0x0032]=r.a
                        if not (yield from self._local_call(self.recalculate_other_loyalty,0xCBC2,0xCBC5)):return
                        self._a(m[0x0031])
                        self._y(0x03)
                        if not (yield from self._local_call(self.officer_field_pointer,0xCBC9,0xCBCC)):return
                        self._compare(r.a,0x1F)
                        self._mark(0xCBCE)
                        if r.p&C:
                            pass
                        else:
                            self._a(0x64)
                            if not (yield from self._local_call(self.random_below,0xCBD2,0xCBD5)):return
                            self._compare(r.a,0x14)
                            self._mark(0xCBD7)
                            if r.p&C:
                                pass
                            else:
                                self._a(m[0x0031])
                                self._y(0x0B)
                                if not (yield from self._local_call(self.officer_field_pointer,0xCBDD,0xCBE0)):return
                                self._a(r.a & 0xFC)
                                m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                self._y(0x05)
                                self._a(m[0x0045])
                                m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                                pass
                            pass
                        m[0x0044]=self._nz(m[0x0044]+1)
                        self._a(m[0x0044])
                        self._compare(r.a,0x1B)
                        self._mark(0xCBF3)
                        if not r.p&C:
                            continue
                        else:
                            self._a(m[0x0045])
                            if not (yield from self._local_call(self.compact_city_roster,0xCBF8,0xCBFB)):return
                            self._a(m[0x0045])
                            if not (yield from self._local_call(self.count_prefix_officers,0xCBFE,0xCC01)):return
                            self._compare(r.a,0x00)
                            self._mark(0xCC03)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(m[0x0045])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCC08,0xCC0B)):return
                                self._y(0x00)
                                self._a(0x07)
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                pass
                            self._mark(0xCC11)
                            self._rts();return
            except _ContinueLoop_CBA8:
                continue

    def sell_grain_for_low_gold(self):
        """$CC12: sell grain for low gold; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC12)
        self._y(0xFF)
        m[0x0036]=r.y
        while True:  # natural loop $CC17
            try:
                m[0x0036]=self._nz(m[0x0036]+1)
                self._a(m[0x0036])
                self._compare(r.a,0x1E)
                self._mark(0xCC1F)
                if not r.p&C:
                    self._a(m[0x0036])
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCC25,0xCC28)):return
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[RULER])
                    self._mark(0xCC2D)
                    if not r.p&Z:
                        pass
                    else:
                        self._y(0x02)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x32,subtract=True)
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._add(0x00,subtract=True)
                        self._mark(0xCC3B)
                        if r.p&C:
                            pass
                        else:
                            self._y(0x30)
                            yield from self._external(0xCC3F,0xF266,0xCC42,"call",None)
                            if r.pc!=0xCC42:return  # preserve nonlocal stack return
                            self._y(m[0x0036])
                            self._a(m[(0x8FFC+r.y)&65535])
                            self._a(r.a & 0x04)
                            self._mark(0xCC4A)
                            if r.p&Z:
                                pass
                            else:
                                if not (yield from self._local_call(self.domesticcooperationcontroller_ccf8,0xCC4C,0xCC4F)):return
                                self._a(m[0x0036])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCC52,0xCC55)):return
                                self._y(0x04)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._flag(C,True)
                                self._add(m[0x0039],subtract=True)
                                m[0x0039]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                self._add(m[0x003A],subtract=True)
                                m[0x003A]=r.a
                                self._mark(0xCC69)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x0039])
                                    self._flag(C,True)
                                    self._add(0x2C,subtract=True)
                                    self._a(m[0x003A])
                                    self._add(0x01,subtract=True)
                                    self._mark(0xCC76)
                                    if not r.p&C:
                                        self._y(0x04)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(m[0x0039],subtract=True)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._add(m[0x003A],subtract=True)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(0x30)
                                        yield from self._external(0xCC96,0xF266,0xCC99,"call",None)
                                        if r.pc!=0xCC99:return  # preserve nonlocal stack return
                                        self._a(m[0x0036])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0x8FC0+r.y)&65535])
                                        m[0x0023]=r.a
                                        self._a(m[0x0039])
                                        m[0x0020]=r.a
                                        self._a(m[0x003A])
                                        m[0x0021]=r.a
                                        self._a(0x00)
                                        m[0x0022]=r.a
                                        if not (yield from self._local_call(self.multiply_domestic_word,0xCCB1,0xCCB4)):return
                                        self._a(m[0x0026])
                                        m[0x0020]=r.a
                                        self._a(m[0x0027])
                                        m[0x0021]=r.a
                                        self._a(m[0x0028])
                                        m[0x0022]=r.a
                                        self._a(0x64)
                                        m[0x0023]=r.a
                                        self._a(0x00)
                                        m[0x0024]=r.a
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xCCC8,0xCCCB)):return
                                        self._a(m[0x0020])
                                        m[0x0039]=r.a
                                        self._a(m[0x0021])
                                        m[0x003A]=r.a
                                        self._a(m[0x0036])
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCCD8,0xCCDB)):return
                                        self._y(0x02)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(m[0x0039])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._add(m[0x003A])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        if not (yield from self._local_call(self.cap_city_word,0xCCED,0xCCF0)):return
                                        self._a(0x02)
                                        if not (yield from self._local_call(self.charge_nested_budget_one,0xCCF2,0xCCF5)):return
                                        pass
                                    else:
                                        self._a(0x2C)
                                        m[0x0039]=r.a
                                        self._a(0x01)
                                        m[0x003A]=r.a
                                        self._y(0x04)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(m[0x0039],subtract=True)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._add(m[0x003A],subtract=True)
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(0x30)
                                        yield from self._external(0xCC96,0xF266,0xCC99,"call",None)
                                        if r.pc!=0xCC99:return  # preserve nonlocal stack return
                                        self._a(m[0x0036])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0x8FC0+r.y)&65535])
                                        m[0x0023]=r.a
                                        self._a(m[0x0039])
                                        m[0x0020]=r.a
                                        self._a(m[0x003A])
                                        m[0x0021]=r.a
                                        self._a(0x00)
                                        m[0x0022]=r.a
                                        if not (yield from self._local_call(self.multiply_domestic_word,0xCCB1,0xCCB4)):return
                                        self._a(m[0x0026])
                                        m[0x0020]=r.a
                                        self._a(m[0x0027])
                                        m[0x0021]=r.a
                                        self._a(m[0x0028])
                                        m[0x0022]=r.a
                                        self._a(0x64)
                                        m[0x0023]=r.a
                                        self._a(0x00)
                                        m[0x0024]=r.a
                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xCCC8,0xCCCB)):return
                                        self._a(m[0x0020])
                                        m[0x0039]=r.a
                                        self._a(m[0x0021])
                                        m[0x003A]=r.a
                                        self._a(m[0x0036])
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCCD8,0xCCDB)):return
                                        self._y(0x02)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(m[0x0039])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._add(m[0x003A])
                                        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                        if not (yield from self._local_call(self.cap_city_word,0xCCED,0xCCF0)):return
                                        self._a(0x02)
                                        if not (yield from self._local_call(self.charge_nested_budget_one,0xCCF2,0xCCF5)):return
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    continue
                else:
                    pass
                self._mark(0xCC21)
                self._rts();return
            except _ContinueLoop_CC17:
                continue

    def domesticcooperationcontroller_ccf8(self):
        """$CCF8: domesticcooperationcontroller ccf8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCCF8)
        self._a(m[0x0036])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCCFB,0xCCFE)):return
        self._a(0x11)
        m[0x0037]=r.a
        self._a(0x00)
        m[0x0038]=r.a
        m[0x0039]=r.a
        while True:  # natural loop $CD0B
            try:
                self._y(m[0x0037])
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCD12)
                if r.p&Z:
                    pass
                else:
                    self._y(0x08)
                    if not (yield from self._local_call(self.officer_field_pointer,0xCD16,0xCD19)):return
                    self._flag(C,False)
                    self._add(m[0x0038])
                    m[0x0038]=r.a
                    self._y(r.y+1)
                    self._a(m[0x0039])
                    self._add(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                    m[0x0039]=r.a
                    pass
                m[0x0037]=self._nz(m[0x0037]+1)
                self._a(m[0x0037])
                self._compare(r.a,0x1B)
                self._mark(0xCD31)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0038])
                m[0x0021]=r.a
                self._a(m[0x0039])
                m[0x0022]=r.a
                m[0x0038]=self._shift(m[0x0038],True,rotate=False)
                m[0x0039]=self._shift(m[0x0039],True,rotate=True)
                self._a(m[0x0038])
                self._flag(C,False)
                self._add(m[0x0021])
                m[0x0021]=r.a
                self._a(m[0x0039])
                self._add(m[0x0022])
                m[0x0022]=r.a
                self._a(0x19)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.divide_domestic_word,0xCD5A,0xCD5D)):return
                self._a(m[0x0021])
                m[0x0039]=r.a
                self._a(m[0x0022])
                m[0x003A]=r.a
                self._mark(0xCD67)
                self._rts();return
            except _ContinueLoop_CD0B:
                continue

    def domesticcooperationcontroller_cd68(self):
        """$CD68: domesticcooperationcontroller cd68; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD68)
        self._a(0x0A)
        if not (yield from self._local_call(self.random_low_nibble_below,0xCD6A,0xCD6D)):return
        self._flag(C,False)
        self._add(0x0A)
        self._y(0x06)
        m[0x0036]=r.y
        if not (yield from self._local_call(self.domesticcooperationcontroller_cdb9,0xCD75,0xCD78)):return
        if not (yield from self._local_call(self.domesticcooperationcontroller_cd9a,0xCD78,0xCD7B)):return
        self._y(0x08)
        m[0x0036]=r.y
        if not (yield from self._local_call(self.domesticcooperationcontroller_cdb9,0xCD80,0xCD83)):return
        if not (yield from self._local_call(self.domesticcooperationcontroller_cd9a,0xCD83,0xCD86)):return
        self._y(0x0E)
        m[0x0036]=r.y
        if not (yield from self._local_call(self.domesticcooperationcontroller_cdb9,0xCD8B,0xCD8E)):return
        if not (yield from self._local_call(self.domesticcooperationcontroller_cd9a,0xCD8E,0xCD91)):return
        self._y(0x0B)
        m[0x0036]=r.y
        if not (yield from self._local_call(self.domesticcooperationcontroller_ce1b,0xCD96,0xCD99)):return
        self._mark(0xCD99)
        self._rts();return

    def domesticcooperationcontroller_cd9a(self):
        """$CD9A: domesticcooperationcontroller cd9a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD9A)
        self._y(0x0A)
        self._a(m[0x6F8D])
        self._compare(r.a,0x05)
        self._mark(0xCDA1)
        if not r.p&C:
            pass
        else:
            self._y(0x14)
            self._compare(r.a,0x0A)
            self._mark(0xCDA7)
            if not r.p&C:
                pass
            else:
                self._y(0x1E)
                self._compare(r.a,0x0F)
                self._mark(0xCDAD)
                if not r.p&C:
                    pass
                else:
                    self._y(0x28)
                    self._compare(r.a,0x14)
                    self._mark(0xCDB3)
                    if not r.p&C:
                        pass
                    else:
                        self._y(0x3C)
                        pass
                    pass
                pass
            pass
        self._a(r.y)
        self._mark(0xCDB8)
        self._rts();return

    def domesticcooperationcontroller_cdb9(self):
        """$CDB9: domesticcooperationcontroller cdb9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCDB9)
        self._push(r.a)
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCDBD,0xCDC0)):return
        self._y(m[0x0036])
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._push(r.a)
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        m[0x0021]=r.a
        self._a(self._pop())
        m[0x0020]=r.a
        self._a(self._pop())
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.multiply_domestic_word,0xCDD5,0xCDD8)):return
        self._a(m[0x0026])
        m[0x0020]=r.a
        self._a(m[0x0027])
        m[0x0021]=r.a
        self._a(m[0x0028])
        m[0x0022]=r.a
        self._a(0x64)
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xCDEC,0xCDEF)):return
        self._a(m[0x0020])
        m[0x002A]=r.a
        self._a(m[0x0021])
        m[0x002B]=r.a
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCDFA,0xCDFD)):return
        self._y(m[0x0036])
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x002A],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x002B],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._mark(0xCE0E)
        if r.p&C:
            pass
        else:
            self._y(m[0x0036])
            self._a(0x00)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            pass
        self._mark(0xCE1A)
        self._rts();return

    def domesticcooperationcontroller_ce1b(self):
        """$CE1B: domesticcooperationcontroller ce1b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE1B)
        self._push(r.a)
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCE1F,0xCE22)):return
        self._y(m[0x0036])
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        m[0x0020]=r.a
        self._a(self._pop())
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0021]=r.a
        m[0x0022]=r.a
        if not (yield from self._local_call(self.multiply_domestic_word,0xCE32,0xCE35)):return
        self._a(m[0x0026])
        m[0x0020]=r.a
        self._a(m[0x0027])
        m[0x0021]=r.a
        self._a(m[0x0028])
        m[0x0022]=r.a
        self._a(0x64)
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xCE49,0xCE4C)):return
        self._a(m[0x0020])
        m[0x002A]=r.a
        self._a(m[0x0038])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xCE53,0xCE56)):return
        self._y(m[0x0036])
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x002A],subtract=True)
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._mark(0xCE60)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            pass
        self._mark(0xCE66)
        self._rts();return

    def domesticcooperationcontroller_ce67(self):
        """$CE67: domesticcooperationcontroller ce67; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE67)
        self._y(0xFE)
        while True:  # natural loop $CE69
            try:
                self._y(r.y+1)
                self._y(r.y+1)
                self._a(m[0x0522])
                self._flag(C,True)
                self._add(m[(0xCEC9+r.y)&65535],subtract=True)
                self._a(m[0x0523])
                self._add(m[(0xCECA+r.y)&65535],subtract=True)
                self._mark(0xCE78)
                if r.p&C:
                    continue
                else:
                    pass
                self._a(r.y)
                r.a=self._shift(r.a,False,rotate=False)
                self._y(r.a)
                self._a(m[(0xCED3+r.y)&65535])
                m[0x0023]=r.a
                self._a(m[0x0522])
                m[0x0020]=r.a
                self._a(m[0x0523])
                m[0x0021]=r.a
                self._a(0x00)
                m[0x0022]=r.a
                if not (yield from self._local_call(self.multiply_domestic_word,0xCE91,0xCE94)):return
                self._a(m[0x0026])
                m[0x0020]=r.a
                self._a(m[0x0027])
                m[0x0021]=r.a
                self._a(m[0x0028])
                m[0x0022]=r.a
                self._a(0x64)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xCEA8,0xCEAB)):return
                self._a(m[0x0522])
                self._flag(C,True)
                self._add(m[0x0020],subtract=True)
                m[0x0522]=r.a
                self._a(m[0x0523])
                self._add(m[0x0021],subtract=True)
                m[0x0523]=r.a
                self._mark(0xCEBE)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[0x0522]=r.a
                    m[0x0523]=r.a
                    pass
                self._mark(0xCEC8)
                self._rts();return
            except _ContinueLoop_CE69:
                continue

    def domesticcooperationcontroller_cedd(self):
        """$CEDD: domesticcooperationcontroller cedd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCEDD)
        self._y(0xFE)
        while True:  # natural loop $CEDF
            try:
                self._y(r.y+1)
                self._y(r.y+1)
                self._a(m[0x0526])
                self._flag(C,True)
                self._add(m[(0xCEC9+r.y)&65535],subtract=True)
                self._a(m[0x0527])
                self._add(m[(0xCECA+r.y)&65535],subtract=True)
                self._mark(0xCEEE)
                if r.p&C:
                    continue
                else:
                    pass
                self._a(r.y)
                r.a=self._shift(r.a,False,rotate=False)
                self._y(r.a)
                self._a(m[(0xCED3+r.y)&65535])
                m[0x0023]=r.a
                self._a(m[0x0526])
                m[0x0020]=r.a
                self._a(m[0x0527])
                m[0x0021]=r.a
                self._a(0x00)
                m[0x0022]=r.a
                if not (yield from self._local_call(self.multiply_domestic_word,0xCF07,0xCF0A)):return
                self._a(m[0x0026])
                m[0x0020]=r.a
                self._a(m[0x0027])
                m[0x0021]=r.a
                self._a(m[0x0028])
                m[0x0022]=r.a
                self._a(0x64)
                m[0x0023]=r.a
                self._a(0x00)
                m[0x0024]=r.a
                if not (yield from self._local_call(self.domesticcooperationcontroller_d336,0xCF1E,0xCF21)):return
                self._a(m[0x0526])
                self._flag(C,True)
                self._add(m[0x0020],subtract=True)
                m[0x0526]=r.a
                self._a(m[0x0527])
                self._add(m[0x0021],subtract=True)
                m[0x0527]=r.a
                self._mark(0xCF34)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[0x0526]=r.a
                    m[0x0527]=r.a
                    pass
                self._mark(0xCF3E)
                self._rts();return
            except _ContinueLoop_CEDF:
                continue

    def recalculate_recruited_loyalty(self):
        """$CF3F: recalculate recruited loyalty; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF3F)
        self._a(m[0x0030])
        self._y(0x04)
        if not (yield from self._local_call(self.officer_field_pointer,0xCF43,0xCF46)):return
        m[0x0021]=r.a
        self._a(0x0A)
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0022]=r.a
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_domestic_word,0xCF52,0xCF55)):return
        self._a(m[0x0021])
        self._flag(C,False)
        self._add(0x46)
        self._push(r.a)
        self._a(m[0x0031])
        self._y(0x03)
        if not (yield from self._local_call(self.officer_field_pointer,0xCF5F,0xCF62)):return
        m[0x0020]=r.a
        self._a(self._pop())
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        self._compare(r.a,0x5A)
        self._mark(0xCF6A)
        if not r.p&C:
            pass
        else:
            self._a(0x5A)
            pass
        self._compare(r.a,0x0A)
        self._mark(0xCF70)
        if r.p&C:
            pass
        else:
            self._a(0x0A)
            pass
        self._y(0x03)
        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d61e,0xCF78,0xCF7B)):return
        self._mark(0xCF7B)
        self._rts();return

    def recalculate_other_loyalty(self):
        """$CF7C: recalculate other loyalty; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF7C)
        self._a(m[0x0032])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xCAD8+r.y)&65535])
        m[0x0024]=r.a
        self._a(m[(0xCAD9+r.y)&65535])
        m[0x0025]=r.a
        self._y(0xFF)
        while True:  # natural loop $CF8C
            try:
                self._y(r.y+1)
                self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCF91)
                if r.p&Z:
                    self._a(m[0x0030])
                    self._y(0x04)
                    if not (yield from self._local_call(self.officer_field_pointer,0xCF9C,0xCF9F)):return
                    m[0x0021]=r.a
                    self._a(0x05)
                    m[0x0023]=r.a
                    self._a(0x00)
                    m[0x0022]=r.a
                    m[0x0024]=r.a
                    if not (yield from self._local_call(self.divide_domestic_word,0xCFAB,0xCFAE)):return
                    self._a(m[0x0021])
                    self._push(r.a)
                    self._a(m[0x0033])
                    self._y(0x04)
                    if not (yield from self._local_call(self.officer_field_pointer,0xCFB5,0xCFB8)):return
                    m[0x0021]=r.a
                    self._a(0x05)
                    m[0x0023]=r.a
                    self._a(0x00)
                    m[0x0022]=r.a
                    m[0x0024]=r.a
                    if not (yield from self._local_call(self.divide_domestic_word,0xCFC4,0xCFC7)):return
                    self._a(self._pop())
                    self._flag(C,True)
                    self._add(m[0x0021],subtract=True)
                    self._mark(0xCFCB)
                    if not r.p&C:
                        self._a(r.a ^ 0xFF)
                        self._flag(C,False)
                        self._add(0x01)
                        m[0x0020]=r.a
                        self._a(m[0x0031])
                        self._y(0x03)
                        if not (yield from self._local_call(self.officer_field_pointer,0xCFE7,0xCFEA)):return
                        self._flag(C,True)
                        self._add(m[0x0020],subtract=True)
                        self._mark(0xCFED)
                        if r.p&C:
                            pass
                        else:
                            self._a(0x00)
                            pass
                        pass
                    else:
                        m[0x0020]=r.a
                        self._a(m[0x0031])
                        self._y(0x03)
                        if not (yield from self._local_call(self.officer_field_pointer,0xCFD3,0xCFD6)):return
                        self._flag(C,False)
                        self._add(m[0x0020])
                        pass
                    self._flag(C,True)
                    self._add(0x0A,subtract=True)
                    self._mark(0xCFF4)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        pass
                    self._compare(r.a,0x63)
                    self._mark(0xCFFA)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x63)
                        pass
                    self._compare(r.a,0x0A)
                    self._mark(0xD000)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x0A)
                        pass
                    self._y(0x03)
                    m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d61e,0xD008,0xD00B)):return
                    self._mark(0xD00B)
                    self._rts();return
                else:
                    self._compare(r.a,m[0x0030])
                    self._mark(0xCF95)
                    if not r.p&Z:
                        continue
                    else:
                        self._mark(0xCF97)
                        self._rts();return
            except _ContinueLoop_CF8C:
                continue

    def recalculate_shifted_loyalty(self):
        """$D00C: recalculate shifted loyalty; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD00C)
        self._a(m[0x0020])
        self._y(0x03)
        if not (yield from self._local_call(self.officer_field_pointer,0xD010,0xD013)):return
        m[0x0020]=r.a
        self._a(0x32)
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        self._mark(0xD01A)
        if r.p&C:
            pass
        else:
            self._a(r.a ^ 0xFF)
            self._flag(C,False)
            self._add(0x01)
            pass
        m[0x0020]=r.a
        self._a(0x33)
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        self._mark(0xD028)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            pass
        self._compare(r.a,0x0A)
        self._mark(0xD02E)
        if r.p&C:
            pass
        else:
            self._a(0x0A)
            pass
        self._y(0x03)
        m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d61e,0xD036,0xD039)):return
        self._mark(0xD039)
        self._rts();return

    def domesticcooperationcontroller_d03a(self):
        """$D03A: domesticcooperationcontroller d03a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD03A)
        self._a(m[RULER])
        if not (yield from self._local_call(self.domesticcooperationcontroller_d080,0xD03D,0xD040)):return
        self._a(m[0x002B])
        m[0x003E]=r.a
        m[0x0023]=r.a
        self._a(m[0x002C])
        m[0x003F]=r.a
        m[0x0022]=r.a
        self._a(0x00)
        m[0x0021]=r.a
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_domestic_word,0xD054,0xD057)):return
        self._a(m[0x0022])
        m[0x0040]=r.a
        self._mark(0xD05C)
        self._rts();return

    def domesticcooperationcontroller_d080(self):
        """$D080: domesticcooperationcontroller d080; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD080)
        m[0x002F]=r.a
        self._a(0x00)
        m[0x002A]=r.a
        m[0x002B]=r.a
        m[0x002C]=r.a
        while True:  # natural loop $D08A
            try:
                self._a(m[0x002A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD08C,0xD08F)):return
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x002F])
                self._mark(0xD093)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.domesticcooperationcontroller_d307,0xD095,0xD098)):return
                    self._flag(C,False)
                    self._add(m[0x002C])
                    m[0x002C]=r.a
                    m[0x002B]=self._nz(m[0x002B]+1)
                    pass
                m[0x002A]=self._nz(m[0x002A]+1)
                self._a(m[0x002A])
                self._compare(r.a,0x1E)
                self._mark(0xD0A5)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x002B])
                self._mark(0xD0A9)
                self._rts();return
            except _ContinueLoop_D08A:
                continue

    def domesticcooperationcontroller_d0aa(self):
        """$D0AA: domesticcooperationcontroller d0aa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0AA)
        self._y(0x30)
        yield from self._external(0xD0AC,0xF266,0xD0AF,"call",None)
        if r.pc!=0xD0AF:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x002A]=r.a
        m[0x002B]=r.a
        m[0x002C]=r.a
        while True:  # natural loop $D0B7
            try:
                self._a(m[0x002A])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD0B9,0xD0BC)):return
                self._a(r.a & 0x07)
                self._compare(r.a,m[RULER])
                self._mark(0xD0C1)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x002A])
                    if not (yield from self._local_call(self.count_enemy_neighbors,0xD0C5,0xD0C8)):return
                    self._mark(0xD0C8)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[0x002A])
                        if not (yield from self._local_call(self.count_prefix_officers,0xD0CC,0xD0CF)):return
                        self._flag(C,False)
                        self._add(m[0x002C])
                        m[0x002C]=r.a
                        m[0x002B]=self._nz(m[0x002B]+1)
                        pass
                    pass
                m[0x002A]=self._nz(m[0x002A]+1)
                self._a(m[0x002A])
                self._compare(r.a,0x1E)
                self._mark(0xD0DC)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x002B])
                self._mark(0xD0E0)
                self._rts();return
            except _ContinueLoop_D0B7:
                continue

    def count_enemy_neighbors(self):
        """$D0E1: count enemy neighbors; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0E1)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._x(r.a)
        self._a(0x00)
        m[0x0022]=r.a
        while True:  # natural loop $D0E9
            try:
                self._a(m[(0x9D72+r.x)&65535])
                self._mark(0xD0EC)
                if r.p&N:
                    pass
                else:
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD0EE,0xD0F1)):return
                    self._a(r.a & 0x07)
                    self._compare(r.a,0x07)
                    self._mark(0xD0F5)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,m[RULER])
                        self._mark(0xD0FA)
                        if r.p&Z:
                            pass
                        else:
                            m[0x0022]=self._nz(m[0x0022]+1)
                            pass
                        pass
                    self._x(r.x+1)
                    continue
                self._a(m[0x0022])
                self._mark(0xD104)
                self._rts();return
            except _ContinueLoop_D0E9:
                continue

    def city_pointer_and_resource_caps(self):
        """$D105: city pointer and resource caps; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD105)
        self._y(0x00)
        m[0x0021]=r.y
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        self._flag(C,False)
        self._add(0x00)
        m[0x0020]=r.a
        self._a(m[0x0021])
        self._add(0x60)
        m[0x0021]=r.a
        if not (yield from self._local_call(self.cap_city_word,0xD123,0xD126)):return
        self._y(0x00)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._a(r.a & 0x07)
        self._mark(0xD12C)
        self._rts();return

    def charge_task_budget(self):
        """$D152: task budget: byte subtract; zero or borrow discards one extra caller frame and reportsFF."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD152)
        m[0x0020]=r.a
        self._a(m[AI_BUDGET])
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        m[AI_BUDGET]=r.a
        self._mark(0xD15D)
        if r.p&Z:
            self._a(self._pop())
            self._a(self._pop())
            self._a(0x02)
            m[AI_PHASE]=r.a
            self._a(0xFF)
            m[AI_REQUEST]=r.a
            self._a(0x00)
            m[0x6F8D]=r.a
            self._mark(0xD151)
            self._rts();return
        else:
            self._mark(0xD15F)
            if r.p&C:
                self._mark(0xD164)
                self._rts();return
            else:
                self._a(self._pop())
                self._a(self._pop())
                self._a(0x02)
                m[AI_PHASE]=r.a
                self._a(0xFF)
                m[AI_REQUEST]=r.a
                self._a(0x00)
                m[0x6F8D]=r.a
                self._mark(0xD151)
                self._rts();return

    def charge_nested_budget_one(self):
        """$D165: nested budget: byte subtract; borrow discards two extra caller frames and reportsFF."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD165)
        m[0x0020]=r.a
        self._a(m[AI_BUDGET])
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        m[AI_BUDGET]=r.a
        self._mark(0xD170)
        if r.p&C:
            self._mark(0xD177)
            self._rts();return
        else:
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(0x02)
            m[AI_PHASE]=r.a
            self._a(0xFF)
            m[AI_REQUEST]=r.a
            self._a(0x00)
            m[0x6F8D]=r.a
            self._mark(0xD151)
            self._rts();return

    def charge_nested_budget_three(self):
        """$D18D: deep budget: byte subtract; borrow discards four extra caller frames and reportsFF."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD18D)
        m[0x0020]=r.a
        self._a(m[AI_BUDGET])
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        m[AI_BUDGET]=r.a
        self._mark(0xD198)
        if r.p&C:
            self._mark(0xD1A3)
            self._rts();return
        else:
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(self._pop())
            self._a(0x02)
            m[AI_PHASE]=r.a
            self._a(0xFF)
            m[AI_REQUEST]=r.a
            self._a(0x00)
            m[0x6F8D]=r.a
            self._mark(0xD151)
            self._rts();return

    def build_enemy_neighbor_list(self):
        """$D1A4: build enemy neighbor list; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1A4)
        self._a(m[RULER])
        m[0x002A]=r.a
        self._y(0x30)
        yield from self._external(0xD1AB,0xF266,0xD1AE,"call",None)
        if r.pc!=0xD1AE:return  # preserve nonlocal stack return
        self._y(0x0F)
        self._a(0xFF)
        while True:  # natural loop $D1B2
            try:
                m[(0x6F73+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xD1B6)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(0x00)
                m[0x002B]=r.a
                m[0x002C]=r.a
                self._a(m[0x0036])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                while True:  # natural loop $D1C5
                    try:
                        self._a(m[(0x9D72+r.y)&65535])
                        self._mark(0xD1C8)
                        if r.p&N:
                            pass
                        else:
                            m[0x0023]=r.a
                            m[0x0024]=r.y
                            if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD1CE,0xD1D1)):return
                            self._a(r.a & 0x07)
                            self._compare(r.a,0x07)
                            self._mark(0xD1D5)
                            if r.p&Z:
                                pass
                            else:
                                self._compare(r.a,m[0x002A])
                                self._mark(0xD1D9)
                                if r.p&Z:
                                    pass
                                else:
                                    self._y(m[0x002B])
                                    self._a(m[0x0023])
                                    m[(0x6F73+r.y)&65535]=r.a
                                    m[0x002B]=self._nz(m[0x002B]+1)
                                    pass
                                pass
                            self._a(m[0x0023])
                            self._y(m[0x0024])
                            self._y(r.y+1)
                            m[0x002C]=self._nz(m[0x002C]+1)
                            self._x(m[0x002C])
                            self._compare(r.x,0x08)
                            self._mark(0xD1EF)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            pass
                        self._a(m[0x002B])
                        self._mark(0xD1F3)
                        self._rts();return
                    except _ContinueLoop_D1C5:
                        continue
            except _ContinueLoop_D1B2:
                continue

    def find_ruler_city(self):
        """$D249: find ruler city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD249)
        if not (yield from self._local_call(self.domesticcooperationcontroller_d6e5,0xD249,0xD24C)):return
        self._a(0x00)
        m[0x0036]=r.a
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x002A]=r.a
        while True:  # natural loop $D257
            try:
                self._a(m[0x0036])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD25A,0xD25D)):return
                self._a(r.a & 0x07)
                self._compare(r.a,m[RULER])
                self._mark(0xD262)
                if not r.p&Z:
                    m[0x0036]=self._nz(m[0x0036]+1)
                    self._a(m[0x0036])
                    self._compare(r.a,0x1E)
                    self._mark(0xD27D)
                    if not r.p&C:
                        continue
                    else:
                        self._a(0xFF)
                        self._flag(C,False)
                        self._mark(0xD282)
                        self._rts();return
                else:
                    self._y(0x11)
                    while True:  # natural loop $D266
                        try:
                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                            self._compare(r.a,m[0x002A])
                            self._mark(0xD26A)
                            if not r.p&Z:
                                self._y(r.y+1)
                                self._compare(r.y,0x1B)
                                self._mark(0xD273)
                                if not r.p&C:
                                    continue
                                else:
                                    m[0x0036]=self._nz(m[0x0036]+1)
                                    self._a(m[0x0036])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xD27D)
                                    if not r.p&C:
                                        raise _ContinueLoop_D257
                                    else:
                                        self._a(0xFF)
                                        self._flag(C,False)
                                        self._mark(0xD282)
                                        self._rts();return
                            else:
                                self._a(m[0x0036])
                                self._mark(0xD26F)
                                self._rts();return
                        except _ContinueLoop_D266:
                            continue
            except _ContinueLoop_D257:
                continue

    def domesticcooperationcontroller_d283(self):
        """$D283: domesticcooperationcontroller d283; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD283)
        self._x(0x00)
        m[0x0021]=r.x
        m[0x0020]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        self._flag(C,False)
        self._add(m[0x0020])
        self._push(r.a)
        self._a(m[0x0021])
        self._add(0x00)
        m[0x0021]=r.a
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0021]=self._shift(m[0x0021],True,rotate=True)
        self._flag(C,False)
        self._add(0xC0)
        m[0x0020]=r.a
        self._a(m[0x0021])
        self._add(0x63)
        m[0x0021]=r.a
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._mark(0xD2AA)
        self._rts();return

    def officer_field_pointer(self):
        """$D2AB: officer field pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2AB)
        self._x(0x00)
        m[0x0023]=r.x
        m[0x0022]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0023]=self._shift(m[0x0023],True,rotate=True)
        self._flag(C,False)
        self._add(m[0x0022])
        self._push(r.a)
        self._a(m[0x0023])
        self._add(0x00)
        m[0x0023]=r.a
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0023]=self._shift(m[0x0023],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0023]=self._shift(m[0x0023],True,rotate=True)
        self._flag(C,False)
        self._add(0xC0)
        m[0x0022]=r.a
        self._a(m[0x0023])
        self._add(0x63)
        m[0x0023]=r.a
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._mark(0xD2D2)
        self._rts();return

    def domesticcooperationcontroller_d2d3(self):
        """$D2D3: domesticcooperationcontroller d2d3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2D3)
        m[0x0026]=r.y
        self._y(0x31)
        yield from self._external(0xD2D7,0xF266,0xD2DA,"call",None)
        if r.pc!=0xD2DA:return  # preserve nonlocal stack return
        self._x(0x00)
        m[0x0025]=r.x
        m[0x0024]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0025]=self._shift(m[0x0025],True,rotate=True)
        self._flag(C,False)
        self._add(m[0x0024])
        self._push(r.a)
        self._a(m[0x0025])
        self._add(0x00)
        m[0x0025]=r.a
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0025]=self._shift(m[0x0025],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0025]=self._shift(m[0x0025],True,rotate=True)
        self._flag(C,False)
        self._add(0x00)
        m[0x0024]=r.a
        self._a(m[0x0025])
        self._add(0x80)
        m[0x0025]=r.a
        self._y(m[0x0026])
        self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
        self._mark(0xD303)
        self._rts();return

    def count_prefix_officers(self):
        """$D304: count prefix officers; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD304)
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD304,0xD307)):return
        return (yield from self.domesticcooperationcontroller_d307())

    def domesticcooperationcontroller_d307(self):
        """$D307: domesticcooperationcontroller d307; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD307)
        self._x(0x00)
        self._y(0x11)
        while True:  # natural loop $D30B
            try:
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xD30F)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    self._y(r.y+1)
                    self._compare(r.y,0x1B)
                    self._mark(0xD315)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    pass
                self._a(r.x)
                self._mark(0xD318)
                self._rts();return
            except _ContinueLoop_D30B:
                continue

    def ruler_pointer(self):
        """$D319: ruler pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD319)
        self._a(r.a & 0x0F)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xD328+r.y)&65535])
        m[0x0024]=r.a
        self._a(m[(0xD329+r.y)&65535])
        m[0x0025]=r.a
        self._mark(0xD327)
        self._rts();return

    def domesticcooperationcontroller_d336(self):
        """$D336: domesticcooperationcontroller d336; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD336)
        self._a(0x00)
        m[0x0025]=r.a
        m[0x0026]=r.a
        m[0x0027]=r.a
        self._y(0x17)
        while True:  # natural loop $D340
            try:
                m[0x0020]=self._shift(m[0x0020],True,rotate=False)
                m[0x0021]=self._shift(m[0x0021],True,rotate=True)
                m[0x0022]=self._shift(m[0x0022],True,rotate=True)
                m[0x0025]=self._shift(m[0x0025],True,rotate=True)
                m[0x0026]=self._shift(m[0x0026],True,rotate=True)
                m[0x0027]=self._shift(m[0x0027],True,rotate=True)
                self._a(m[0x0025])
                self._flag(C,True)
                self._add(m[0x0023],subtract=True)
                m[0x0028]=r.a
                self._a(m[0x0026])
                self._add(m[0x0024],subtract=True)
                m[0x0029]=r.a
                self._a(m[0x0027])
                self._add(0x00,subtract=True)
                self._mark(0xD35D)
                if not r.p&C:
                    pass
                else:
                    m[0x0027]=r.a
                    self._a(m[0x0028])
                    m[0x0025]=r.a
                    self._a(m[0x0029])
                    m[0x0026]=r.a
                    m[0x0020]=self._nz(m[0x0020]+1)
                    pass
                self._y(r.y-1)
                self._mark(0xD36C)
                if not r.p&N:
                    continue
                else:
                    pass
                self._mark(0xD36E)
                self._rts();return
            except _ContinueLoop_D340:
                continue

    def pay_city_gold(self):
        """$D36F: pay city gold; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD36F)
        self._push(r.a)
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD370,0xD373)):return
        self._a(m[0x0024])
        self._mark(0xD375)
        if r.p&Z:
            pass
        else:
            if not (yield from self._local_call(self.random_below,0xD377,0xD37A)):return
            self._flag(C,False)
            self._add(m[0x0022])
            m[0x0022]=r.a
            self._a(m[0x0023])
            self._add(0x00)
            m[0x0023]=r.a
            pass
        self._a(self._pop())
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD386,0xD389)):return
        if not (yield from self._local_call(self.cap_city_word,0xD389,0xD38C)):return
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0022],subtract=True)
        self._push(r.a)
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x0023],subtract=True)
        self._mark(0xD399)
        if r.p&C:
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y-1)
            self._a(self._pop())
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            if not (yield from self._local_call(self.cap_city_word,0xD3A4,0xD3A7)):return
            self._flag(C,True)
            self._mark(0xD3A8)
            self._rts();return
        else:
            self._a(self._pop())
            self._flag(C,False)
            self._mark(0xD39D)
            self._rts();return

    def pay_city_grain(self):
        """$D3A9: pay city grain; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3A9)
        self._push(r.a)
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD3AA,0xD3AD)):return
        self._a(m[0x0024])
        self._mark(0xD3AF)
        if r.p&Z:
            pass
        else:
            if not (yield from self._local_call(self.random_below,0xD3B1,0xD3B4)):return
            self._flag(C,False)
            self._add(m[0x0022])
            m[0x0022]=r.a
            self._a(m[0x0023])
            self._add(0x00)
            m[0x0023]=r.a
            pass
        self._a(self._pop())
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD3C0,0xD3C3)):return
        self._y(0x04)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0022],subtract=True)
        self._push(r.a)
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x0023],subtract=True)
        self._mark(0xD3D0)
        if r.p&C:
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y-1)
            self._a(self._pop())
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._flag(C,True)
            self._mark(0xD3DC)
            self._rts();return
        else:
            self._a(self._pop())
            self._flag(C,False)
            self._mark(0xD3D4)
            self._rts();return

    def compact_city_roster(self):
        """$D3DD: compact city roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3DD)
        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD3DD,0xD3E0)):return
        self._x(0x00)
        self._a(0xFF)
        while True:  # natural loop $D3E4
            try:
                m[(0x6F73+r.x)&65535]=r.a
                self._x(r.x+1)
                self._compare(r.x,0x10)
                self._mark(0xD3EA)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x11)
                self._x(0x00)
                while True:  # natural loop $D3F0
                    try:
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xD3F4)
                        if r.p&Z:
                            pass
                        else:
                            m[(0x6F73+r.x)&65535]=r.a
                            self._x(r.x+1)
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x1B)
                        self._mark(0xD3FD)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(0x11)
                        self._x(0x00)
                        while True:  # natural loop $D403
                            try:
                                self._a(m[(0x6F73+r.x)&65535])
                                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._x(r.x+1)
                                self._compare(r.y,0x1B)
                                self._mark(0xD40C)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xD40E)
                                self._rts();return
                            except _ContinueLoop_D403:
                                continue
                    except _ContinueLoop_D3F0:
                        continue
            except _ContinueLoop_D3E4:
                continue

    def divide_domestic_word(self):
        """$D40F: divide domestic word; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD40F)
        self._a(0x00)
        m[0x0025]=r.a
        m[0x0026]=r.a
        self._y(0x0F)
        while True:  # natural loop $D417
            try:
                m[0x0021]=self._shift(m[0x0021],True,rotate=False)
                m[0x0022]=self._shift(m[0x0022],True,rotate=True)
                m[0x0025]=self._shift(m[0x0025],True,rotate=True)
                m[0x0026]=self._shift(m[0x0026],True,rotate=True)
                self._a(m[0x0025])
                self._flag(C,True)
                self._add(m[0x0023],subtract=True)
                m[0x0027]=r.a
                self._a(m[0x0026])
                self._add(m[0x0024],subtract=True)
                self._mark(0xD42A)
                if not r.p&C:
                    pass
                else:
                    m[0x0026]=r.a
                    self._a(m[0x0027])
                    m[0x0025]=r.a
                    m[0x0021]=self._nz(m[0x0021]+1)
                    pass
                self._y(r.y-1)
                self._mark(0xD435)
                if not r.p&N:
                    continue
                else:
                    pass
                self._mark(0xD437)
                self._rts();return
            except _ContinueLoop_D417:
                continue

    def multiply_domestic_word(self):
        """$D438: multiply domestic word; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD438)
        self._y(0x07)
        self._a(0x00)
        m[0x0024]=r.a
        m[0x0025]=r.a
        m[0x0026]=r.a
        m[0x0027]=r.a
        m[0x0028]=r.a
        m[0x0029]=r.a
        while True:  # natural loop $D448
            try:
                m[0x0023]=self._shift(m[0x0023],False,rotate=False)
                self._mark(0xD44A)
                if not r.p&C:
                    pass
                else:
                    self._a(m[0x0020])
                    self._flag(C,False)
                    self._add(m[0x0026])
                    m[0x0026]=r.a
                    self._a(m[0x0021])
                    self._add(m[0x0027])
                    m[0x0027]=r.a
                    self._a(m[0x0022])
                    self._add(m[0x0028])
                    m[0x0028]=r.a
                    self._a(m[0x0024])
                    self._add(m[0x0029])
                    m[0x0029]=r.a
                    pass
                m[0x0020]=self._shift(m[0x0020],True,rotate=False)
                m[0x0021]=self._shift(m[0x0021],True,rotate=True)
                m[0x0022]=self._shift(m[0x0022],True,rotate=True)
                m[0x0024]=self._shift(m[0x0024],True,rotate=True)
                self._y(r.y-1)
                self._mark(0xD46E)
                if not r.p&N:
                    continue
                else:
                    pass
                self._mark(0xD470)
                self._rts();return
            except _ContinueLoop_D448:
                continue

    def domesticcooperationcontroller_d471(self):
        """$D471: domesticcooperationcontroller d471; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD471)
        self._y(0x07)
        self._a(0x00)
        m[0x002C]=r.a
        m[0x002A]=r.a
        m[0x002B]=r.a
        while True:  # natural loop $D47B
            try:
                m[0x0021]=self._shift(m[0x0021],False,rotate=False)
                self._mark(0xD47D)
                if not r.p&C:
                    pass
                else:
                    self._a(m[0x0020])
                    self._flag(C,False)
                    self._add(m[0x002A])
                    m[0x002A]=r.a
                    self._a(m[0x002C])
                    self._add(m[0x002B])
                    m[0x002B]=r.a
                    pass
                m[0x0020]=self._shift(m[0x0020],True,rotate=False)
                m[0x002C]=self._shift(m[0x002C],True,rotate=True)
                self._y(r.y-1)
                self._mark(0xD491)
                if not r.p&N:
                    continue
                else:
                    pass
                self._mark(0xD493)
                self._rts();return
            except _ContinueLoop_D47B:
                continue

    def random_low_nibble_below(self):
        """$D4AD: random low nibble below; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4AD)
        m[0x0056]=r.a
        while True:  # natural loop $D4B0
            try:
                yield from self._external(0xD4B0,0xE88A,0xD4B3,"call",None)
                if r.pc!=0xD4B3:return  # preserve nonlocal stack return
                self._a(r.a & 0x0F)
                self._compare(r.a,m[0x0056])
                self._mark(0xD4B8)
                if r.p&C:
                    continue
                else:
                    pass
                self._mark(0xD4BA)
                self._rts();return
            except _ContinueLoop_D4B0:
                continue

    def random_below(self):
        """$D4BB: random below; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4BB)
        self._compare(r.a,0x0F)
        self._mark(0xD4BD)
        if not r.p&C:
            return (yield from self.random_low_nibble_below())
        else:
            m[0x0056]=r.a
            while True:  # natural loop $D4C2
                try:
                    yield from self._external(0xD4C2,0xE88A,0xD4C5,"call",None)
                    if r.pc!=0xD4C5:return  # preserve nonlocal stack return
                    self._compare(r.a,m[0x0056])
                    self._mark(0xD4C8)
                    if r.p&C:
                        continue
                    else:
                        pass
                    self._mark(0xD4CA)
                    self._rts();return
                except _ContinueLoop_D4C2:
                    continue

    def build_owned_connectivity(self):
        """$D4CB: build owned connectivity; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4CB)
        self._y(0x7F)
        self._a(0x00)
        while True:  # natural loop $D4CF
            try:
                m[(0x0580+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xD4D3)
                if not r.p&N:
                    continue
                else:
                    pass
                self._y(0x30)
                yield from self._external(0xD4D7,0xF266,0xD4DA,"call",None)
                if r.pc!=0xD4DA:return  # preserve nonlocal stack return
                self._a(0x1D)
                m[0x0036]=r.a
                while True:  # natural loop $D4DF
                    try:
                        self._a(m[0x0036])
                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD4E2,0xD4E5)):return
                        self._a(r.a & 0x07)
                        self._compare(r.a,m[RULER])
                        self._mark(0xD4EA)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0036])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            m[0x0024]=r.a
                            while True:  # natural loop $D4F4
                                try:
                                    self._y(m[0x0024])
                                    self._a(m[(0x9D72+r.y)&65535])
                                    self._mark(0xD4F9)
                                    if r.p&N:
                                        pass
                                    else:
                                        m[0x0025]=r.a
                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps,0xD4FD,0xD500)):return
                                        self._a(r.a & 0x07)
                                        self._compare(r.a,m[RULER])
                                        self._mark(0xD505)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._x(m[0x0025])
                                            self._a(m[0x0036])
                                            self._flag(C,False)
                                            self._add(m[(0xD5BF+r.x)&65535])
                                            self._y(r.a)
                                            self._a(m[0x0025])
                                            self._a(r.a & 0x07)
                                            self._x(r.a)
                                            self._a(m[(0xD5DF+r.x)&65535])
                                            self._a(r.a | m[(0x0580+r.y)&65535])
                                            m[(0x0580+r.y)&65535]=r.a
                                            pass
                                        m[0x0024]=self._nz(m[0x0024]+1)
                                        continue
                                    m[0x0036]=self._nz(m[0x0036]-1)
                                    self._mark(0xD527)
                                    if not r.p&N:
                                        raise _ContinueLoop_D4DF
                                    else:
                                        pass
                                    self._y(0x01)
                                    self._x(0x00)
                                    while True:  # natural loop $D52D
                                        try:
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_d53e,0xD52D,0xD530)):return
                                            self._y(r.y+1)
                                            self._compare(r.y,0x1E)
                                            self._mark(0xD533)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._x(r.x+1)
                                            self._a(r.x)
                                            self._y(r.a)
                                            self._x(r.x+1)
                                            self._compare(r.x,0x1D)
                                            self._mark(0xD53B)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._mark(0xD53D)
                                            self._rts();return
                                        except _ContinueLoop_D52D:
                                            continue
                                except _ContinueLoop_D4F4:
                                    continue
                        m[0x0036]=self._nz(m[0x0036]-1)
                        self._mark(0xD527)
                        if not r.p&N:
                            continue
                        else:
                            pass
                        self._y(0x01)
                        self._x(0x00)
                        while True:  # natural loop $D52D
                            try:
                                if not (yield from self._local_call(self.domesticcooperationcontroller_d53e,0xD52D,0xD530)):return
                                self._y(r.y+1)
                                self._compare(r.y,0x1E)
                                self._mark(0xD533)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._x(r.x+1)
                                self._a(r.x)
                                self._y(r.a)
                                self._x(r.x+1)
                                self._compare(r.x,0x1D)
                                self._mark(0xD53B)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xD53D)
                                self._rts();return
                            except _ContinueLoop_D52D:
                                continue
                    except _ContinueLoop_D4DF:
                        continue
            except _ContinueLoop_D4CF:
                continue

    def domesticcooperationcontroller_d53e(self):
        """$D53E: domesticcooperationcontroller d53e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD53E)
        self._a(m[(0x0580+r.x)&65535])
        self._a(r.a & m[(0x0580+r.y)&65535])
        self._mark(0xD544)
        if r.p&Z:
            pass
        else:
            self._a(m[(0x0580+r.x)&65535])
            self._a(r.a | m[(0x0580+r.y)&65535])
            m[(0x0580+r.y)&65535]=r.a
            pass
        self._a(m[(0x05A0+r.x)&65535])
        self._a(r.a & m[(0x05A0+r.y)&65535])
        self._mark(0xD555)
        if r.p&Z:
            pass
        else:
            self._a(m[(0x05A0+r.x)&65535])
            self._a(r.a | m[(0x05A0+r.y)&65535])
            m[(0x05A0+r.y)&65535]=r.a
            pass
        self._a(m[(0x05C0+r.x)&65535])
        self._a(r.a & m[(0x05C0+r.y)&65535])
        self._mark(0xD566)
        if r.p&Z:
            pass
        else:
            self._a(m[(0x05C0+r.x)&65535])
            self._a(r.a | m[(0x05C0+r.y)&65535])
            m[(0x05C0+r.y)&65535]=r.a
            pass
        self._a(m[(0x05E0+r.x)&65535])
        self._a(r.a & m[(0x05E0+r.y)&65535])
        self._mark(0xD577)
        if r.p&Z:
            pass
        else:
            self._a(m[(0x05E0+r.x)&65535])
            self._a(r.a | m[(0x05E0+r.y)&65535])
            m[(0x05E0+r.y)&65535]=r.a
            pass
        self._mark(0xD582)
        self._rts();return

    def common_connectivity_bits(self):
        """$D583: common connectivity bits; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD583)
        m[0x0031]=r.y
        m[0x0032]=r.x
        self._x(0x1D)
        m[0x0030]=r.x
        while True:  # natural loop $D58B
            try:
                self._y(m[0x0031])
                self._a(m[0x0030])
                self._a(r.a | m[(0xD5BF+r.y)&65535])
                self._x(r.a)
                self._a(m[0x0031])
                self._a(r.a & 0x07)
                self._y(r.a)
                self._a(m[(0x0580+r.x)&65535])
                self._a(r.a & m[(0xD5DF+r.y)&65535])
                self._mark(0xD59E)
                if r.p&Z:
                    m[0x0030]=self._nz(m[0x0030]-1)
                    self._mark(0xD5BA)
                    if not r.p&N:
                        continue
                    else:
                        self._a(0x00)
                        self._mark(0xD5BE)
                        self._rts();return
                else:
                    self._y(m[0x0032])
                    self._a(m[0x0030])
                    self._a(r.a | m[(0xD5BF+r.y)&65535])
                    self._x(r.a)
                    self._a(m[0x0032])
                    self._a(r.a & 0x07)
                    self._y(r.a)
                    self._a(m[(0x0580+r.x)&65535])
                    self._a(r.a & m[(0xD5DF+r.y)&65535])
                    self._mark(0xD5B3)
                    if r.p&Z:
                        m[0x0030]=self._nz(m[0x0030]-1)
                        self._mark(0xD5BA)
                        if not r.p&N:
                            continue
                        else:
                            self._a(0x00)
                            self._mark(0xD5BE)
                            self._rts();return
                    else:
                        self._a(0xFF)
                        self._mark(0xD5B7)
                        self._rts();return
            except _ContinueLoop_D58B:
                continue

    def domesticcooperationcontroller_d5e7(self):
        """$D5E7: domesticcooperationcontroller d5e7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD5E7)
        self._rts();return

    def domesticcooperationcontroller_d61e(self):
        """$D61E: domesticcooperationcontroller d61e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD61E)
        self._rts();return

    def cap_city_word(self):
        """$D69D: cap city word; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD69D)
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x10,subtract=True)
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(0x27,subtract=True)
        self._mark(0xD6A9)
        if not r.p&C:
            pass
        else:
            self._y(0x02)
            self._a(0x0F)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(0x27)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            pass
        self._y(0x04)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x10,subtract=True)
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(0x27,subtract=True)
        self._mark(0xD6C2)
        if not r.p&C:
            pass
        else:
            self._y(0x04)
            self._a(0x0F)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(0x27)
            m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
            pass
        self._mark(0xD6CF)
        self._rts();return

    def domesticcooperationcontroller_d6e5(self):
        """$D6E5: domesticcooperationcontroller d6e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6E5)
        self._rts();return

